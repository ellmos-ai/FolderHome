"""Build a local, extractive health dossier from explicitly selected documents."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import DocumentRecord, PrivacyStatus
from folderhome.contracts.health import (
    HealthConflictCandidate,
    HealthCoverage,
    HealthDossierReport,
    HealthEvidence,
    HealthMissingPeriod,
    HealthSource,
    HealthTimelineEntry,
)

_LABELED_LINE = re.compile(r"^([^:\n]{1,80}):\s*(.+)$")
_DOCUMENTED_FACT = re.compile(r"^([^=]{1,80})\s*=\s*(.+)$")
_WHITESPACE = re.compile(r"\s+")
_CONTENT_LABELS = {
    "befund": ("finding", "Befund"),
    "ergebnis": ("finding", "Ergebnis"),
    "medikament": ("medication", "Medikament"),
    "medikation": ("medication", "Medikation"),
    "termin": ("appointment", "Termin"),
    "offene frage": ("question", "Offene Frage"),
    "frage": ("question", "Frage"),
    "diagnose": ("documented_fact", "Dokumentierte Diagnose"),
    "maßnahme": ("documented_fact", "Dokumentierte Maßnahme"),
}
_DATE_LABELS = {"dokumentdatum", "berichtsdatum", "datum"}
_TYPE_LABELS = {"dokumenttyp", "dokumentart"}
_SPECIALTY_LABELS = {"fachbereich", "fachrichtung"}


class HealthDossierGateError(PermissionError):
    """Raised before any health document is read without explicit approval."""


class HealthDocumentExtractor(Protocol):
    """Read-only document extraction port used by the dossier core."""

    def extract(self, source_path: Path) -> DocumentRecord: ...


@dataclass(frozen=True, slots=True)
class _ParsedLine:
    kind: str
    label: str
    statement: str
    line_number: int
    excerpt: str
    conflict_field: str | None = None
    conflict_value: str | None = None


@dataclass(frozen=True, slots=True)
class _ParsedDocument:
    documented_date: date | None
    invalid_date: bool
    document_type: str | None
    specialty: str | None
    lines: tuple[_ParsedLine, ...]


def build_health_dossier(
    source_dir: Path,
    *,
    profile_id: str,
    as_of: date,
    extractor: HealthDocumentExtractor,
    allow_sensitive_local_read: bool,
    recursive: bool = True,
    gap_threshold_days: int = 90,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> HealthDossierReport:
    """Extract selected local files into a claim-neutral, evidence-bound dossier."""

    source_root = source_dir.resolve()
    if not profile_id.strip():
        raise ValueError("profile_id darf nicht leer sein.")
    if gap_threshold_days < 1:
        raise ValueError("gap_threshold_days muss mindestens 1 sein.")
    if not source_root.is_dir():
        raise ValueError(f"Gesundheitsordner fehlt: {source_root}")
    if not allow_sensitive_local_read:
        raise HealthDossierGateError(
            "Sensitivitätsfreigabe fehlt; Gesundheitsdokumente wurden nicht gelesen."
        )

    inventory = inventory_files(
        source_root,
        recursive=recursive,
        policy=resource_policy,
    )
    files = inventory.all_paths
    sources: list[HealthSource] = []
    timeline: list[HealthTimelineEntry] = []
    conflict_values: dict[
        str, list[tuple[str, HealthEvidence]]
    ] = defaultdict(list)
    dated_sources: list[date] = []
    text_budget = ResourceBudget(resource_policy)

    for source_path in files:
        relative_path = source_path.relative_to(source_root).as_posix()
        if source_path.is_symlink():
            sources.append(
                _source_status(
                    relative_path,
                    status="unsupported",
                    message="Symbolischer Link wurde nicht verarbeitet.",
                )
            )
            continue
        try:
            document = extractor.extract(source_path)
            text_budget.consume_extracted_text(len(document.text))
        except UnsupportedDocumentError as exc:
            sources.append(
                _source_status(relative_path, status="unsupported", message=str(exc))
            )
            continue
        except (DocServicesBridgeError, OSError) as exc:
            sources.append(
                _source_status(relative_path, status="unreadable", message=str(exc))
            )
            continue

        if not _may_process_locally(document):
            sources.append(
                _source_status(
                    relative_path,
                    status="blocked",
                    message=(
                        "Datenschutzstatus blockiert die inhaltliche Übernahme; "
                        "die Quelle bleibt nur als Status sichtbar."
                    ),
                    document=document,
                )
            )
            continue

        parsed = _parse_document(document.text)
        if parsed.invalid_date:
            sources.append(
                _source_status(
                    relative_path,
                    status="invalid_date",
                    message="Dokumentdatum ist ungültig oder innerhalb der Quelle widersprüchlich.",
                    document=document,
                    parsed=parsed,
                )
            )
            continue
        if parsed.documented_date is None:
            sources.append(
                _source_status(
                    relative_path,
                    status="missing_date",
                    message=(
                        "Kein eindeutiges Dokumentdatum; Inhalt wurde nicht zeitlich "
                        "eingeordnet."
                    ),
                    document=document,
                    parsed=parsed,
                )
            )
            continue
        if parsed.documented_date > as_of:
            sources.append(
                _source_status(
                    relative_path,
                    status="future_date",
                    message="Dokumentdatum liegt nach dem Auswertungsstichtag.",
                    document=document,
                    parsed=parsed,
                )
            )
            continue

        sources.append(
            _source_status(
                relative_path,
                status="included",
                message="Lokal und extraktiv in das Dossier aufgenommen.",
                document=document,
                parsed=parsed,
            )
        )
        dated_sources.append(parsed.documented_date)
        for parsed_line in parsed.lines:
            evidence = HealthEvidence(
                document_id=document.document_id,
                relative_path=relative_path,
                source_sha256=document.source_sha256,
                line_number=parsed_line.line_number,
                label=parsed_line.label,
                excerpt=parsed_line.excerpt,
            )
            entry_id = _stable_id(
                "health_entry",
                document.document_id,
                str(parsed_line.line_number),
                parsed_line.kind,
                parsed_line.statement,
            )
            timeline.append(
                HealthTimelineEntry(
                    entry_id=entry_id,
                    documented_date=parsed.documented_date.isoformat(),
                    kind=parsed_line.kind,
                    label=parsed_line.label,
                    statement=parsed_line.statement,
                    specialty=parsed.specialty,
                    evidence=evidence,
                )
            )
            if parsed_line.conflict_field and parsed_line.conflict_value:
                conflict_values[parsed_line.conflict_field.casefold()].append(
                    (parsed_line.conflict_value, evidence)
                )

    timeline.sort(
        key=lambda item: (
            item.documented_date,
            item.evidence.relative_path.casefold(),
            item.evidence.line_number,
            item.entry_id,
        )
    )
    conflicts = _build_conflicts(conflict_values)
    coverage = _build_coverage(dated_sources, gap_threshold_days=gap_threshold_days)
    report_id = _stable_id(
        "health_dossier",
        profile_id,
        str(source_root).casefold(),
        as_of.isoformat(),
        str(gap_threshold_days),
        *(item.source_sha256 or f"{item.relative_path}:{item.status}" for item in sources),
    )
    markdown = _render_markdown(
        profile_id=profile_id,
        as_of=as_of,
        sources=tuple(sources),
        timeline=tuple(timeline),
        conflicts=conflicts,
        coverage=coverage,
    )
    return HealthDossierReport(
        report_id=report_id,
        profile_id=profile_id,
        source_root=source_root,
        as_of=as_of.isoformat(),
        sources=tuple(sources),
        timeline=tuple(timeline),
        conflicts=conflicts,
        coverage=coverage,
        markdown=markdown,
    )


def _parse_document(text: str) -> _ParsedDocument:
    dates: list[date] = []
    invalid_date = False
    document_type: str | None = None
    specialty: str | None = None
    content: list[_ParsedLine] = []
    fallback_lines: list[_ParsedLine] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        normalized = _one_line(raw_line)
        if not normalized:
            continue
        match = _LABELED_LINE.fullmatch(normalized)
        if match is None:
            fallback_lines.append(
                _ParsedLine(
                    kind="source_excerpt",
                    label="Quellenauszug",
                    statement=normalized,
                    line_number=line_number,
                    excerpt=normalized,
                )
            )
            continue
        raw_label, value = (_one_line(part) for part in match.groups())
        key = raw_label.casefold()
        if key in _DATE_LABELS:
            try:
                dates.append(date.fromisoformat(value))
            except ValueError:
                invalid_date = True
            continue
        if key in _TYPE_LABELS:
            document_type = document_type or value
            continue
        if key in _SPECIALTY_LABELS:
            specialty = specialty or value
            continue
        if key == "dokumentierte angabe":
            fact = _DOCUMENTED_FACT.fullmatch(value)
            if fact is None:
                fallback_lines.append(
                    _ParsedLine(
                        kind="source_excerpt",
                        label=raw_label,
                        statement=value,
                        line_number=line_number,
                        excerpt=normalized,
                    )
                )
                continue
            field, fact_value = (_one_line(part) for part in fact.groups())
            content.append(
                _ParsedLine(
                    kind="documented_fact",
                    label=field,
                    statement=f"{field} = {fact_value}",
                    line_number=line_number,
                    excerpt=normalized,
                    conflict_field=field,
                    conflict_value=fact_value,
                )
            )
            continue
        mapped = _CONTENT_LABELS.get(key)
        if mapped is not None:
            kind, label = mapped
            content.append(
                _ParsedLine(
                    kind=kind,
                    label=label,
                    statement=value,
                    line_number=line_number,
                    excerpt=normalized,
                )
            )
            continue
        fallback_lines.append(
            _ParsedLine(
                kind="source_excerpt",
                label=raw_label,
                statement=value,
                line_number=line_number,
                excerpt=normalized,
            )
        )

    distinct_dates = tuple(dict.fromkeys(dates))
    if len(distinct_dates) > 1:
        invalid_date = True
    return _ParsedDocument(
        documented_date=distinct_dates[0] if len(distinct_dates) == 1 else None,
        invalid_date=invalid_date,
        document_type=document_type,
        specialty=specialty,
        lines=tuple(content or fallback_lines[:3]),
    )


def _may_process_locally(document: DocumentRecord) -> bool:
    """Allow local health processing, but never override unrelated red findings."""

    if document.privacy_status in {PrivacyStatus.CLEAR, PrivacyStatus.REVIEW_REQUIRED}:
        return True
    if document.privacy_status is not PrivacyStatus.BLOCKED:
        return False
    red_findings = tuple(
        line.strip()
        for line in document.privacy_summary.splitlines()
        if line.strip().startswith("[ROT]")
    )
    return bool(red_findings) and all(
        finding.startswith("[ROT] Gesundheitsdaten:") for finding in red_findings
    )


def _source_status(
    relative_path: str,
    *,
    status: str,
    message: str,
    document: DocumentRecord | None = None,
    parsed: _ParsedDocument | None = None,
) -> HealthSource:
    return HealthSource(
        relative_path=relative_path,
        status=status,
        message=_one_line(message),
        document_id=document.document_id if document else None,
        source_sha256=document.source_sha256 if document else None,
        documented_date=(
            parsed.documented_date.isoformat()
            if parsed is not None and parsed.documented_date is not None
            else None
        ),
        document_type=parsed.document_type if parsed else None,
        specialty=parsed.specialty if parsed else None,
        privacy_status=document.privacy_status.value if document else None,
    )


def _build_conflicts(
    candidates: dict[str, list[tuple[str, HealthEvidence]]],
) -> tuple[HealthConflictCandidate, ...]:
    conflicts: list[HealthConflictCandidate] = []
    for _, observations in sorted(candidates.items()):
        distinct: dict[str, tuple[str, HealthEvidence]] = {}
        for value, evidence in observations:
            distinct.setdefault(value.casefold(), (value, evidence))
        if len(distinct) < 2:
            continue
        values = tuple(item[0] for item in distinct.values())
        evidence = tuple(item[1] for item in distinct.values())
        field = evidence[0].label
        conflicts.append(
            HealthConflictCandidate(
                conflict_id=_stable_id(
                    "health_conflict",
                    field.casefold(),
                    *(value.casefold() for value in values),
                ),
                field=field,
                values=values,
                evidence=evidence,
            )
        )
    return tuple(conflicts)


def _build_coverage(
    documented_dates: list[date],
    *,
    gap_threshold_days: int,
) -> HealthCoverage:
    dates = sorted(set(documented_dates))
    missing: list[HealthMissingPeriod] = []
    for previous, following in zip(dates, dates[1:], strict=False):
        distance = (following - previous).days
        if distance <= gap_threshold_days:
            continue
        missing.append(
            HealthMissingPeriod(
                start=(previous + timedelta(days=1)).isoformat(),
                end=(following - timedelta(days=1)).isoformat(),
                days_without_document=distance,
                previous_document_date=previous.isoformat(),
                next_document_date=following.isoformat(),
            )
        )
    return HealthCoverage(
        first_document_date=dates[0].isoformat() if dates else None,
        last_document_date=dates[-1].isoformat() if dates else None,
        gap_threshold_days=gap_threshold_days,
        missing_periods=tuple(missing),
    )


def _render_markdown(
    *,
    profile_id: str,
    as_of: date,
    sources: tuple[HealthSource, ...],
    timeline: tuple[HealthTimelineEntry, ...],
    conflicts: tuple[HealthConflictCandidate, ...],
    coverage: HealthCoverage,
) -> str:
    lines = [
        f"# Gesundheitsdossier für {_safe_inline(profile_id)}",
        "",
        f"**Auswertungsstichtag:** {as_of.isoformat()}",
        "",
        "> Lokal und extraktiv erzeugt. Keine Diagnose oder medizinische Empfehlung. ",
        "> Das Dossier kann unvollständig sein; jede Aussage verweist auf eine Quelle.",
        "",
        "## Zeitlinie",
        "",
    ]
    if not timeline:
        lines.append("Keine datierten, übernehmbaren Aussagen gefunden.")
    for entry in timeline:
        specialty = f" · {_safe_inline(entry.specialty)}" if entry.specialty else ""
        lines.extend(
            (
                f"- **{entry.documented_date} · {_safe_inline(entry.label)}{specialty}:** "
                f"{_safe_inline(entry.statement)} ",
                f"  Quelle: `{_safe_code(entry.evidence.relative_path)}:"
                f"{entry.evidence.line_number}` · `{entry.evidence.document_id}`",
            )
        )

    lines.extend(("", "## Direkte Feldkonflikte", ""))
    if not conflicts:
        lines.append("Keine direkten Konflikte in gelabelten Angaben erkannt.")
    for conflict in conflicts:
        lines.append(
            f"- **{_safe_inline(conflict.field)}:** "
            f"{' ↔ '.join(_safe_inline(value) for value in conflict.values)} "
            "— menschliche Prüfung erforderlich."
        )
        for evidence in conflict.evidence:
            lines.append(
                f"  - `{_safe_code(evidence.relative_path)}:{evidence.line_number}`"
            )

    lines.extend(("", "## Belegte Zeitabdeckung", ""))
    if coverage.first_document_date is None:
        lines.append("Keine datierte Quelle; eine Zeitabdeckung kann nicht angegeben werden.")
    else:
        lines.append(
            f"Datierte Quellen: {coverage.first_document_date} bis "
            f"{coverage.last_document_date}. Das ist kein Vollständigkeitsnachweis."
        )
    if not coverage.missing_periods:
        lines.append(
            f"Keine Abstände über {coverage.gap_threshold_days} Tage zwischen datierten "
            "Quellen erkannt."
        )
    for item in coverage.missing_periods:
        lines.append(
            f"- {item.start} bis {item.end}: {item.days_without_document} Tage "
            "zwischen zwei datierten Quellen; Dokumente können fehlen."
        )

    lines.extend(("", "## Quellenstatus", ""))
    for source in sources:
        lines.append(
            f"- `{_safe_code(source.relative_path)}` — `{source.status}`: "
            f"{_safe_inline(source.message)}"
        )
    if not sources:
        lines.append("Keine Dateien im ausgewählten Ordner gefunden.")
    return "\n".join(lines).rstrip() + "\n"


def _stable_id(prefix: str, *parts: str) -> str:
    material = "\0".join((f"folderhome.{prefix}.v1", *parts))
    return f"{prefix}_{sha256(material.encode('utf-8')).hexdigest()}"


def _one_line(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


def _safe_inline(value: str) -> str:
    return _one_line(value).replace("`", "'").replace("*", "\\*")


def _safe_code(value: str) -> str:
    return _one_line(value).replace("`", "'")
