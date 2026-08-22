"""Compare local legal-source snapshots and route explicit review interests."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from folderhome.bridges.law_checker import LawCheckerBridge, LawCheckerBridgeError
from folderhome.contracts.legal_change_monitor import (
    LegalChangeMonitorReport,
    LegalChangeOutputReport,
    LegalInterest,
    LegalInterestSnapshot,
    LegalProvisionChange,
    LegalProvisionSnapshot,
    LegalReviewCandidate,
    LegalSourceSnapshot,
)

_TOPIC_LABELS = {
    "beitraege": "Beiträge",
    "kfz-versicherung": "Kfz-Versicherung",
    "krankenversicherung": "Krankenversicherung",
    "mietrecht": "Mietrecht",
}


class LegalChangeMonitorError(RuntimeError):
    """Raised when legal source comparison cannot preserve its safety boundaries."""


def load_legal_source_snapshot(
    path: Path,
    *,
    allow_test_fixture: bool = False,
) -> LegalSourceSnapshot:
    payload = _load_json(path, "Rechtsquellensnapshot")
    expected = {
        "schema",
        "law_id",
        "law_title",
        "law_checker_registry_key",
        "publication_stage",
        "publisher",
        "official_url",
        "checked_at",
        "source_date",
        "authoritative",
        "fixture_only",
        "complete",
        "coverage_statement",
        "provisions",
    }
    if set(payload) != expected:
        raise LegalChangeMonitorError(
            "Rechtsquellensnapshot besitzt unbekannte oder fehlende Felder."
        )
    if payload.get("schema") != LegalSourceSnapshot.SCHEMA:
        raise LegalChangeMonitorError("Rechtsquellensnapshot verwendet ein unbekanntes Schema.")
    fixture_only = _boolean(payload, "fixture_only")
    if fixture_only and not allow_test_fixture:
        raise LegalChangeMonitorError("Testfixture-Freigabe für Rechtsquelle fehlt.")
    provisions_raw = payload.get("provisions")
    if not isinstance(provisions_raw, list):
        raise LegalChangeMonitorError("Rechtsquellensnapshot benötigt eine provisions-Liste.")
    try:
        provisions = tuple(_parse_provision(item) for item in provisions_raw)
        digest = _file_sha(path)
        registry_key = payload.get("law_checker_registry_key")
        if registry_key is not None and not isinstance(registry_key, str):
            raise ValueError("law_checker_registry_key benötigt Text oder null.")
        return LegalSourceSnapshot(
            snapshot_id=f"law_snapshot_{digest}",
            law_id=_text(payload, "law_id"),
            law_title=_text(payload, "law_title"),
            law_checker_registry_key=registry_key,
            publication_stage=_text(payload, "publication_stage"),
            publisher=_text(payload, "publisher"),
            official_url=_text(payload, "official_url"),
            checked_at=_text(payload, "checked_at"),
            source_date=_text(payload, "source_date"),
            authoritative=_boolean(payload, "authoritative"),
            fixture_only=fixture_only,
            complete=_boolean(payload, "complete"),
            coverage_statement=_text(payload, "coverage_statement"),
            source_path=path,
            source_sha256=digest,
            provisions=provisions,
        )
    except (TypeError, ValueError) as exc:
        raise LegalChangeMonitorError(f"Rechtsquellensnapshot ist ungültig: {exc}") from exc


def load_legal_interest_snapshot(
    path: Path,
    *,
    allow_sensitive_local_read: bool,
) -> LegalInterestSnapshot:
    if not allow_sensitive_local_read:
        raise LegalChangeMonitorError("Sensitivitätsfreigabe für Rechtsinteressen fehlt.")
    payload = _load_json(path, "Rechtsinteressensnapshot")
    if set(payload) != {"schema", "profile_id", "provided_on", "interests"}:
        raise LegalChangeMonitorError(
            "Rechtsinteressensnapshot besitzt unbekannte oder fehlende Felder."
        )
    if payload.get("schema") != LegalInterestSnapshot.SCHEMA:
        raise LegalChangeMonitorError("Rechtsinteressensnapshot verwendet ein unbekanntes Schema.")
    interests_raw = payload.get("interests")
    if not isinstance(interests_raw, list):
        raise LegalChangeMonitorError("Rechtsinteressensnapshot benötigt eine interests-Liste.")
    try:
        interests = tuple(_parse_interest(item) for item in interests_raw)
        ids = [item.interest_id for item in interests]
        if len(ids) != len(set(ids)):
            raise ValueError("Rechtsinteressen müssen eindeutige IDs besitzen.")
        digest = _file_sha(path)
        return LegalInterestSnapshot(
            snapshot_id=f"legal_interests_{digest}",
            profile_id=_text(payload, "profile_id"),
            provided_on=_text(payload, "provided_on"),
            source_path=path,
            source_sha256=digest,
            interests=interests,
        )
    except (TypeError, ValueError) as exc:
        raise LegalChangeMonitorError(f"Rechtsinteressensnapshot ist ungültig: {exc}") from exc


def compare_legal_source_snapshots(
    before: LegalSourceSnapshot,
    after: LegalSourceSnapshot,
    interests: LegalInterestSnapshot,
    *,
    as_of: str,
    max_source_age_days: int,
    allow_sensitive_local_read: bool,
    allow_test_fixture: bool = False,
    law_checker: LawCheckerBridge | None = None,
) -> LegalChangeMonitorReport:
    if not allow_sensitive_local_read:
        raise LegalChangeMonitorError("Sensitivitätsfreigabe für Rechtsänderungsmonitor fehlt.")
    if isinstance(max_source_age_days, bool) or max_source_age_days < 1:
        raise LegalChangeMonitorError("max_source_age_days muss positiv sein.")
    if (before.fixture_only or after.fixture_only) and not allow_test_fixture:
        raise LegalChangeMonitorError("Testfixture-Freigabe für Rechtsvergleich fehlt.")
    _verify_bound_file(before.source_path, before.source_sha256, "Vorher-Snapshot-Hash")
    _verify_bound_file(after.source_path, after.source_sha256, "Nachher-Snapshot-Hash")
    _verify_bound_file(interests.source_path, interests.source_sha256, "Interessen-Snapshot-Hash")
    if before.law_id != after.law_id:
        raise LegalChangeMonitorError("Rechtsquellensnapshots betreffen verschiedene Gesetze.")
    if before.fixture_only != after.fixture_only:
        raise LegalChangeMonitorError("Test- und Produktivquellen dürfen nicht verglichen werden.")

    as_of_time = _aware(as_of, "as_of")
    before_checked = _aware(before.checked_at, "before.checked_at")
    after_checked = _aware(after.checked_at, "after.checked_at")
    for label, checked in (("Vorher-Quelle", before_checked), ("Nachher-Quelle", after_checked)):
        age = (as_of_time.date() - checked.date()).days
        if age < 0:
            raise LegalChangeMonitorError(f"{label} liegt aus Sicht von as_of in der Zukunft.")
        if age > max_source_age_days:
            raise LegalChangeMonitorError(
                f"{label} ist mit {age} Tagen veraltet; Vergleich wird blockiert."
            )
    if before_checked > after_checked or before.source_date > after.source_date:
        raise LegalChangeMonitorError("Rechtsquellenstände sind nicht chronologisch geordnet.")

    provider_id, provider_revision, coverage = _qualify_law_checker(
        before,
        after,
        law_checker,
    )
    changes = _compare_provisions(before, after)
    candidates = _build_candidates(changes, interests)
    status = "no_change"
    if changes:
        status = (
            "proposal_review_required"
            if after.publication_stage == "legislative_proposal"
            else "review_required"
        )
    warnings = [
        "Nur die explizit erfassten Normabschnitte wurden technisch verglichen.",
        "Themen-Treffer sind Prüfkandidaten und keine festgestellte rechtliche Betroffenheit.",
        "Keine Rechtswirkung, Übergangsregel, Frist oder Einzelfallanwendung wurde geprüft.",
        "Es wurde keine Benachrichtigung versandt und kein Netzwerkzugriff ausgeführt.",
    ]
    if after.publication_stage == "legislative_proposal":
        warnings.insert(
            0,
            "Der Nachher-Stand ist ein Entwurf und keine verkündete oder geltende Rechtsänderung.",
        )
    if before.fixture_only:
        warnings.insert(0, "Synthetischer Testfall; keine amtliche Rechtsquelle.")
    identity = {
        "as_of": as_of,
        "before": before.snapshot_id,
        "after": after.snapshot_id,
        "interests": interests.snapshot_id,
        "provider_revision": provider_revision,
        "changes": [item.to_dict() for item in changes],
        "candidates": [item.to_dict() for item in candidates],
    }
    report_id = f"legal_monitor_{_json_sha(identity)}"
    return LegalChangeMonitorReport(
        report_id=report_id,
        status=status,
        as_of=as_of,
        law_id=before.law_id,
        publication_stage=after.publication_stage,
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        before_path=before.source_path,
        after_path=after.source_path,
        interests_path=interests.source_path,
        before_sha256=before.source_sha256,
        after_sha256=after.source_sha256,
        interests_sha256=interests.source_sha256,
        provider_id=provider_id,
        provider_revision=provider_revision,
        registry_coverage_status=coverage,
        changes=changes,
        candidates=candidates,
        warnings=tuple(warnings),
    )


def write_legal_change_report(
    report: LegalChangeMonitorReport,
    *,
    markdown_file: Path,
    json_file: Path,
    allow_output_write: bool,
) -> LegalChangeOutputReport:
    if not allow_output_write:
        raise LegalChangeMonitorError("Output-Gate für Rechtsänderungsbericht fehlt.")
    _verify_bound_file(report.before_path, report.before_sha256, "Vorher-Snapshot-Hash")
    _verify_bound_file(report.after_path, report.after_sha256, "Nachher-Snapshot-Hash")
    _verify_bound_file(report.interests_path, report.interests_sha256, "Interessen-Snapshot-Hash")
    markdown_file = markdown_file.resolve()
    json_file = json_file.resolve()
    if markdown_file == json_file:
        raise LegalChangeMonitorError("Markdown- und JSON-Ausgabe müssen getrennt sein.")
    for path in (markdown_file, json_file):
        if path.exists():
            raise LegalChangeMonitorError(f"Ausgabedatei existiert bereits: {path}")
    markdown = _render_markdown(report)
    json_text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    markdown_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with markdown_file.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)
        with json_file.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json_text)
    except OSError as exc:
        raise LegalChangeMonitorError(f"Rechtsänderungsausgabe ist fehlgeschlagen: {exc}") from exc
    markdown_sha = _file_sha(markdown_file)
    json_sha = _file_sha(json_file)
    output_id = f"legal_output_{_json_sha([report.report_id, markdown_sha, json_sha])}"
    return LegalChangeOutputReport(
        output_id=output_id,
        report_id=report.report_id,
        status="executed",
        markdown_file=markdown_file,
        json_file=json_file,
        markdown_sha256=markdown_sha,
        json_sha256=json_sha,
    )


def _qualify_law_checker(
    before: LegalSourceSnapshot,
    after: LegalSourceSnapshot,
    law_checker: LawCheckerBridge | None,
) -> tuple[str | None, str | None, str]:
    if before.law_checker_registry_key != after.law_checker_registry_key:
        raise LegalChangeMonitorError(
            "law-checker-Registry-Bindung hat sich zwischen Ständen geändert."
        )
    key = after.law_checker_registry_key
    if key is not None and law_checker is None:
        raise LegalChangeMonitorError("law-checker-Provider für Registry-Bindung fehlt.")
    if law_checker is None:
        return None, None, "not_declared"
    try:
        if key is not None:
            law_checker.require_registry_key(key)
            coverage = "covered_active"
        else:
            coverage = "not_declared"
    except LawCheckerBridgeError as exc:
        raise LegalChangeMonitorError(str(exc)) from exc
    return law_checker.provider_id, law_checker.provider_revision, coverage


def _compare_provisions(
    before: LegalSourceSnapshot,
    after: LegalSourceSnapshot,
) -> tuple[LegalProvisionChange, ...]:
    old = {item.provision_id: item for item in before.provisions}
    new = {item.provision_id: item for item in after.provisions}
    changes: list[LegalProvisionChange] = []
    for provision_id in sorted(set(old) | set(new)):
        left = old.get(provision_id)
        right = new.get(provision_id)
        if left is not None and right is not None and left.text_sha256 == right.text_sha256:
            continue
        kind = "modified"
        if left is None:
            kind = "added"
        elif right is None:
            kind = "removed"
        topics = tuple(
            sorted(set(left.topics if left else ()) | set(right.topics if right else ()))
        )
        changes.append(
            LegalProvisionChange(
                provision_id=provision_id,
                heading_before=left.heading if left else None,
                heading_after=right.heading if right else None,
                change_kind=kind,
                before_text_sha256=left.text_sha256 if left else None,
                after_text_sha256=right.text_sha256 if right else None,
                topics=topics,
            )
        )
    return tuple(changes)


def _build_candidates(
    changes: tuple[LegalProvisionChange, ...],
    interests: LegalInterestSnapshot,
) -> tuple[LegalReviewCandidate, ...]:
    candidates: list[LegalReviewCandidate] = []
    for interest in interests.interests:
        relevant = [item for item in changes if set(item.topics) & set(interest.topics)]
        if not relevant:
            continue
        matching = tuple(
            sorted(set(interest.topics) & {topic for item in relevant for topic in item.topics})
        )
        identity = _json_sha(
            [interest.interest_id, [item.provision_id for item in relevant], matching]
        )
        candidates.append(
            LegalReviewCandidate(
                candidate_id=f"candidate-{identity[:24]}",
                interest_id=interest.interest_id,
                subject_kind=interest.subject_kind,
                subject_ref=interest.subject_ref,
                provision_ids=tuple(item.provision_id for item in relevant),
                matching_topics=matching,
            )
        )
    return tuple(candidates)


def _parse_provision(value: object) -> LegalProvisionSnapshot:
    expected = {"provision_id", "heading", "text", "text_sha256", "topics"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Normabschnitt besitzt unbekannte oder fehlende Felder.")
    text = _text(value, "text")
    text_hash = _text(value, "text_sha256")
    if _text_sha(text) != text_hash:
        raise ValueError("Normabschnitt-Text stimmt nicht mit seinem Hash überein.")
    return LegalProvisionSnapshot(
        provision_id=_text(value, "provision_id"),
        heading=_text(value, "heading"),
        text=text,
        topics=_text_list(value, "topics", allow_empty=False),
        text_sha256=text_hash,
    )


def _parse_interest(value: object) -> LegalInterest:
    expected = {"interest_id", "subject_kind", "subject_ref", "topics", "basis"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Rechtsinteresse besitzt unbekannte oder fehlende Felder.")
    return LegalInterest(
        interest_id=_text(value, "interest_id"),
        subject_kind=_text(value, "subject_kind"),
        subject_ref=_text(value, "subject_ref"),
        topics=_text_list(value, "topics", allow_empty=False),
        basis=_text(value, "basis"),
    )


def _render_markdown(report: LegalChangeMonitorReport) -> str:
    lines = [
        "# Rechtsänderungsmonitor",
        "",
        f"**Status:** `{report.status}`  ",
        f"**Gesetz:** `{_md(report.law_id)}`  ",
        f"**Veröffentlichungsstufe:** `{report.publication_stage}`  ",
        f"**Stand:** `{report.as_of}`",
        "",
        "## Technisch erkannte Änderungen",
        "",
    ]
    if not report.changes:
        lines.append("Keine Änderung in den erfassten Normabschnitten.")
    for change in report.changes:
        heading = change.heading_after or change.heading_before or change.provision_id
        lines.append(
            f"- `{change.change_kind}` — {_md(heading)} "
            f"(Themen: {_md(', '.join(_topic_label(item) for item in change.topics))})"
        )
    lines.extend(["", "## Prüfkandidaten", ""])
    if not report.candidates:
        lines.append("Keine Übereinstimmung mit explizit hinterlegten Interessen.")
    for candidate in report.candidates:
        lines.append(
            f"- `{candidate.subject_kind}` {_md(candidate.subject_ref)}: "
            f"`review_candidate` über "
            f"{_md(', '.join(_topic_label(item) for item in candidate.matching_topics))}"
        )
    lines.extend(["", "## Grenzen", ""])
    lines.extend(f"- {_md(item)}" for item in report.warnings)
    lines.extend(
        [
            "",
            "**Keine Rechtswirkung geprüft.** Kein Treffer stellt Betroffenheit fest; es wurden "
            "keine Frist berechnet und keine Nachricht versandt.",
            "",
            "---",
            "<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LegalChangeMonitorError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise LegalChangeMonitorError(f"{label} muss ein JSON-Objekt sein.")
    return payload


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} benötigt Text.")
    return value


def _boolean(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} benötigt einen booleschen Wert.")
    return value


def _text_list(
    payload: dict[str, object],
    key: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{key} benötigt eine Liste.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{key} enthält ungültige Einträge.")
    return tuple(value)


def _aware(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise LegalChangeMonitorError(f"{field} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise LegalChangeMonitorError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _verify_bound_file(path: Path, expected: str, label: str) -> None:
    if _file_sha(path) != expected:
        raise LegalChangeMonitorError(f"{label} hat sich geändert.")


def _file_sha(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise LegalChangeMonitorError(f"Datei ist nicht lesbar: {path}: {exc}") from exc
    return digest.hexdigest()


def _text_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _json_sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _md(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("|", "*", "_", "`", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r", " ").replace("\n", " ")


def _topic_label(value: str) -> str:
    return _TOPIC_LABELS.get(value, value.replace("_", " ").replace("-", " ").capitalize())
