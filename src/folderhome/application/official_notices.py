"""Extract and explain explicit fields from one official notice."""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.contracts import DocumentRecord
from folderhome.contracts.official_notices import (
    NoticeConflict,
    NoticeEvidence,
    OfficialNoticeAnalysis,
    OfficialNoticeOutputReport,
)

_LABELS = {
    "Bescheidart": "notice_type",
    "Behörde": "authority",
    "Aktenzeichen": "file_reference",
    "Bescheiddatum": "notice_date",
    "Leistungszeitraum": "benefit_period",
    "Entscheidung": "decision",
    "Begründung": "reason",
    "Rechtsbehelf": "legal_remedy",
    "Fristtext": "deadline_text",
    "Explizites Fristdatum": "explicit_deadline_date",
    "Rechtsbehelfsstelle": "legal_remedy_office",
}


class OfficialNoticeError(RuntimeError):
    """Raised before an unsafe or unsupported notice operation."""


class NoticeExtractor(Protocol):
    provider_revision: str

    def extract(self, source_path: Path) -> DocumentRecord: ...


def analyze_official_notice(
    source_path: Path,
    *,
    profile_id: str,
    received_on: str | None,
    as_of: str,
    extractor: NoticeExtractor,
    allow_sensitive_local_read: bool,
) -> OfficialNoticeAnalysis:
    if not allow_sensitive_local_read:
        raise OfficialNoticeError("Sensitivitätsfreigabe für den Bescheid fehlt.")
    if not profile_id.strip():
        raise OfficialNoticeError("Bescheidanalyse benötigt ein Profil.")
    as_of_time = _aware(as_of, "as_of")
    received_date = _optional_date(received_on, "received_on")
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise OfficialNoticeError(f"Bescheiddatei fehlt: {source_path}")
    try:
        record = extractor.extract(source_path)
    except Exception as exc:
        raise OfficialNoticeError(f"Bescheid konnte nicht extrahiert werden: {exc}") from exc
    if record.source_path != source_path:
        raise OfficialNoticeError("Extractor lieferte eine abweichende Quellbindung.")
    if _file_sha(source_path) != record.source_sha256:
        raise OfficialNoticeError("Extrahierter Bescheid stimmt nicht mit dem Quellhash überein.")

    evidence = _extract_evidence(record)
    by_field: dict[str, list[NoticeEvidence]] = {}
    for item in evidence:
        by_field.setdefault(item.field_name, []).append(item)
    conflicts: list[NoticeConflict] = []
    values: dict[str, str | None] = {}
    for field in (
        "notice_type",
        "authority",
        "file_reference",
        "notice_date",
        "benefit_period",
        "decision",
        "legal_remedy",
        "deadline_text",
        "explicit_deadline_date",
        "legal_remedy_office",
    ):
        values[field] = _resolve_singleton(field, by_field.get(field, []), conflicts)
    reasons = tuple(dict.fromkeys(item.value for item in by_field.get("reason", [])))

    warnings = [
        "Fristangaben wurden extrahiert, aber nicht rechtlich berechnet oder geprüft."
    ]
    review_required = False
    notice_date = _validated_extracted_date(values["notice_date"], "Bescheiddatum", warnings)
    explicit_deadline = _validated_extracted_date(
        values["explicit_deadline_date"],
        "Explizites Fristdatum",
        warnings,
    )
    if values["notice_date"] is not None and notice_date is None:
        review_required = True
    if values["explicit_deadline_date"] is not None and explicit_deadline is None:
        review_required = True
    as_of_date = as_of_time.date()
    if notice_date is not None and date.fromisoformat(notice_date) > as_of_date:
        warnings.append("Das extrahierte Bescheiddatum liegt nach dem Analysezeitpunkt.")
        review_required = True
    if received_date is not None:
        warnings.append("Das Zugangsdatum ist eine Nutzerangabe, keine Dokumentfeststellung.")
        if received_date > as_of_date:
            warnings.append("Das angegebene Zugangsdatum liegt nach dem Analysezeitpunkt.")
            review_required = True
    if record.privacy_status.value != "clear":
        warnings.append(
            "Der Extraktionsprovider markiert den Bescheid als sensibel; "
            "die Verarbeitung blieb lokal."
        )

    days_until: int | None = None
    urgency: str | None = None
    if explicit_deadline is not None:
        days_until = (date.fromisoformat(explicit_deadline) - as_of_date).days
        urgency = _urgency(days_until)
    else:
        warnings.append("Kein ausdrücklich datiertes Fristende wurde gefunden.")

    missing = tuple(
        field
        for field, value in (
            ("notice_type", values["notice_type"]),
            ("authority", values["authority"]),
            ("decision", values["decision"]),
            ("legal_remedy", values["legal_remedy"]),
            ("explicit_deadline_date", explicit_deadline),
        )
        if value is None
    )
    status = (
        "review_required"
        if missing or conflicts or review_required
        else "ready_for_review"
    )
    core = {
        "profile_id": profile_id,
        "as_of": as_of,
        "received_on": received_on,
        "document_id": record.document_id,
        "source_sha256": record.source_sha256,
        "evidence": [item.to_dict() for item in evidence],
        "missing_fields": list(missing),
        "conflicts": [item.to_dict() for item in conflicts],
    }
    return OfficialNoticeAnalysis(
        analysis_id=f"notice_analysis_{_text_sha(_canonical(core))}",
        profile_id=profile_id,
        as_of=as_of,
        received_on=received_on,
        received_on_basis="user_provided" if received_on is not None else None,
        source_path=source_path,
        source_sha256=record.source_sha256,
        document_id=record.document_id,
        extraction_provider=record.extraction_provider,
        extraction_provider_revision=getattr(extractor, "provider_revision", "unknown"),
        privacy_status=record.privacy_status.value,
        notice_type=values["notice_type"],
        notice_type_basis="explicit_document_label" if values["notice_type"] else None,
        authority=values["authority"],
        file_reference=values["file_reference"],
        notice_date=notice_date,
        benefit_period=values["benefit_period"],
        decision=values["decision"],
        reasons=reasons,
        legal_remedy=values["legal_remedy"],
        deadline_text=values["deadline_text"],
        explicit_deadline_date=explicit_deadline,
        legal_remedy_office=values["legal_remedy_office"],
        days_until_explicit_deadline=days_until,
        deadline_urgency=urgency,
        evidence=evidence,
        missing_fields=missing,
        conflicts=tuple(conflicts),
        warnings=tuple(warnings),
        status=status,
    )


def write_official_notice_report(
    analysis: OfficialNoticeAnalysis,
    *,
    markdown_path: Path,
    json_path: Path,
    allow_output_write: bool,
) -> OfficialNoticeOutputReport:
    if not allow_output_write:
        raise OfficialNoticeError("Ausgabefreigabe für den Bescheidbericht fehlt.")
    markdown_path = markdown_path.resolve()
    json_path = json_path.resolve()
    if markdown_path.suffix.lower() != ".md" or json_path.suffix.lower() != ".json":
        raise OfficialNoticeError("Bescheidbericht benötigt eine Markdown- und JSON-Datei.")
    if len({markdown_path, json_path, analysis.source_path}) != 3:
        raise OfficialNoticeError("Bescheidausgaben müssen getrennt von der Quelle liegen.")
    for target in (markdown_path, json_path):
        if target.exists():
            raise OfficialNoticeError(f"Bescheidausgabe existiert bereits: {target}")
    if _file_sha(analysis.source_path) != analysis.source_sha256:
        raise OfficialNoticeError("Bescheid-Quellhash hat sich seit der Analyse geändert.")
    markdown = _render_markdown(analysis)
    json_text = json.dumps(
        analysis.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    created: list[Path] = []
    try:
        for path, content in ((markdown_path, markdown), (json_path, json_text)):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            created.append(path)
    except (OSError, UnicodeError) as exc:
        for path in created:
            with suppress(OSError):
                path.unlink()
        raise OfficialNoticeError(
            f"Bescheidbericht konnte nicht geschrieben werden: {exc}"
        ) from exc
    markdown_sha = _file_sha(markdown_path)
    json_sha = _file_sha(json_path)
    report_material = f"{analysis.analysis_id}:{markdown_sha}:{json_sha}"
    report_id = f"notice_output_report_{_text_sha(report_material)}"
    return OfficialNoticeOutputReport(
        report_id=report_id,
        analysis_id=analysis.analysis_id,
        markdown_path=markdown_path,
        markdown_sha256=markdown_sha,
        json_path=json_path,
        json_sha256=json_sha,
        status="executed",
    )


def _extract_evidence(record: DocumentRecord) -> tuple[NoticeEvidence, ...]:
    evidence = []
    for line_number, raw_line in enumerate(record.text.splitlines(), start=1):
        if ":" not in raw_line:
            continue
        label, value = (part.strip() for part in raw_line.split(":", 1))
        field = _LABELS.get(label)
        if field is None or not value:
            continue
        evidence.append(
            NoticeEvidence(
                field_name=field,
                value=value,
                line_number=line_number,
                document_id=record.document_id,
                source_sha256=record.source_sha256,
            )
        )
    return tuple(evidence)


def _resolve_singleton(
    field: str,
    items: list[NoticeEvidence],
    conflicts: list[NoticeConflict],
) -> str | None:
    unique: dict[str, int] = {}
    for item in items:
        unique.setdefault(item.value, item.line_number)
    if len(unique) == 1:
        return next(iter(unique))
    if len(unique) > 1:
        conflicts.append(
            NoticeConflict(
                field_name=field,
                values=tuple(unique),
                evidence_lines=tuple(unique.values()),
            )
        )
    return None


def _validated_extracted_date(
    value: str | None,
    label: str,
    warnings: list[str],
) -> str | None:
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        warnings.append(f"{label} ist kein eindeutiges ISO-Datum: {value}")
        return None
    return value


def _urgency(days_until: int) -> str:
    if days_until < 0:
        return "overdue"
    if days_until == 0:
        return "today"
    if days_until <= 3:
        return "urgent"
    if days_until <= 14:
        return "soon"
    return "later"


def _render_markdown(analysis: OfficialNoticeAnalysis) -> str:
    missing_fields = ", ".join(analysis.missing_fields) if analysis.missing_fields else None
    conflict_fields = (
        ", ".join(item.field_name for item in analysis.conflicts)
        if analysis.conflicts
        else None
    )
    lines = [
        "# Bescheid verständlich zusammengefasst",
        "",
        f"**Status:** `{analysis.status}`  ",
        f"**Profil:** {_md(analysis.profile_id)}  ",
        f"**Quelle:** `{analysis.source_path}`  ",
        f"**Dokument-ID:** `{analysis.document_id}`  ",
        f"**Quellhash:** `{analysis.source_sha256}`",
        "",
        "## Was ausdrücklich im Dokument steht",
        "",
        f"- Bescheidart: {_display(analysis.notice_type)}",
        f"- Behörde: {_display(analysis.authority)}",
        f"- Aktenzeichen: {_display(analysis.file_reference)}",
        f"- Bescheiddatum: {_display(analysis.notice_date)}",
        f"- Leistungszeitraum: {_display(analysis.benefit_period)}",
        f"- Entscheidung: {_display(analysis.decision)}",
        f"- Begründungen: {_display('; '.join(analysis.reasons) if analysis.reasons else None)}",
        "",
        "## Rechtsbehelf und Fristangaben",
        "",
        f"- Gedruckter Rechtsbehelf: {_display(analysis.legal_remedy)}",
        f"- Gedruckter Fristtext: {_display(analysis.deadline_text)}",
        f"- Ausdrücklich gedrucktes Fristdatum: {_display(analysis.explicit_deadline_date)}",
        "- Rein rechnerische Tage bis zu diesem Datum: "
        f"{_display_number(analysis.days_until_explicit_deadline)}",
        f"- Dringlichkeitsanzeige: {_display(analysis.deadline_urgency)}",
        f"- Genannte Stelle: {_display(analysis.legal_remedy_office)}",
        f"- Nutzerseitig angegebenes Zugangsdatum: {_display(analysis.received_on)}",
        "",
        "## Prüfbedarf",
        "",
        f"- Fehlende Felder: {_display(missing_fields)}",
        f"- Konflikte: {_display(conflict_fields)}",
    ]
    lines.extend(f"- Warnung: {_md(item)}" for item in analysis.warnings)
    lines.extend(
        [
            "",
            "## Evidenz",
            "",
            "| Feld | Wert | Zeile |",
            "|---|---|---:|",
        ]
    )
    lines.extend(
        f"| `{item.field_name}` | {_md(item.value)} | {item.line_number} |"
        for item in analysis.evidence
    )
    lines.extend(
        [
            "",
            "## Grenzen",
            "",
            "**Keine Rechtsprüfung durchgeführt.** Der Bericht erklärt ausschließlich "
            "explizit gelabelte Dokumentangaben. Er berechnet keine gesetzliche Frist, "
            "bewertet den Bescheid nicht rechtlich und erstellt keine Antwort oder "
            "einen Widerspruch. Bei laufenden oder unklaren Fristen ist unverzüglich "
            "qualifizierte sozialrechtliche Hilfe einzubeziehen.",
            "",
            "---",
            "<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->",
            "",
        ]
    )
    return "\n".join(lines)


def _display(value: str | None) -> str:
    return _md(value) if value else "_nicht eindeutig ermittelt_"


def _display_number(value: int | None) -> str:
    return str(value) if value is not None else "_nicht berechnet_"


def _md(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("|", "*", "_", "`", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r", " ").replace("\n", " ")


def _optional_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise OfficialNoticeError(f"{field} muss ein ISO-Datum sein.") from exc


def _aware(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise OfficialNoticeError(f"{field} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise OfficialNoticeError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _file_sha(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise OfficialNoticeError(f"Datei ist nicht lesbar: {path}: {exc}") from exc
    return digest.hexdigest()


def _text_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
