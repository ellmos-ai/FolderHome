from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from folderhome.application.calendar_handoff import (
    analyze_document_calendar,
    analyze_folder_calendar,
    build_calendar_handoff_plan,
    load_calendar_configuration,
)
from folderhome.application.profile_rules import (
    load_profile_configuration,
    resolve_profile_policy,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.contracts import (
    CalendarBackend,
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


class SyntheticExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        if source_path.suffix.lower() != ".txt":
            raise UnsupportedDocumentError(f"Nicht unterstützt: {source_path.suffix}")
        return _document(source_path, source_path.read_text(encoding="utf-8"))


def _document(
    source_path: Path,
    text: str,
    *,
    privacy_status: PrivacyStatus = PrivacyStatus.CLEAR,
) -> DocumentRecord:
    source_hash = sha256(source_path.read_bytes()).hexdigest()
    return DocumentRecord(
        document_id=build_document_id(source_path, source_hash),
        source_path=source_path,
        filename=source_path.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source_path.stat().st_size,
        modified_at="2026-08-22T00:00:00+02:00",
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="synthetic-test",
        extraction_method="direct",
        privacy_status=privacy_status,
        privacy_summary="Synthetischer Datenschutzstatus.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )


def _event_text(
    *,
    title: str = "Kontrolltermin",
    event_date: str = "14.09.2026",
    start_time: str = "10:30",
    end_time: str = "11:00",
) -> str:
    return (
        f"Termin: {title}\n"
        f"Datum: {event_date}\n"
        f"Uhrzeit: {start_time}\n"
        f"Ende: {end_time}\n"
        "Ort: Praxis Beispiel\n"
        "Zeitzone: Europe/Berlin\n"
        "Interne Notiz: wird nicht als Termininhalt gespeichert.\n"
    )


def _write_event(path: Path, **kwargs: str) -> DocumentRecord:
    path.write_text(_event_text(**kwargs), encoding="utf-8")
    return _document(path, path.read_text(encoding="utf-8"))


def _write_profile_configuration(root: Path, *, backend: str | None = None) -> None:
    root.mkdir()
    (root / "household.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.household-rules.v1",
                "os_account": "synthetic-family-account",
                "rules": [],
            }
        ),
        encoding="utf-8",
    )
    rules = []
    if backend is not None:
        rules.append(
            {
                "rule_id": "rule_lukas_calendar",
                "key": "calendar.backend",
                "value": backend,
                "scope": "profile_area",
                "area": "gesundheit",
            }
        )
    (root / "Lukas.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.user-profile.v1",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "os_account": "synthetic-family-account",
                "organizational_only": True,
                "rules": rules,
            }
        ),
        encoding="utf-8",
    )


def _write_calendar_configuration(root: Path, *, backend: str = "uptoday_ics") -> Path:
    root.mkdir()
    path = root / "calendar-config.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.calendar-config.v1",
                "default_backend": backend,
                "default_timezone": "Europe/Berlin",
                "uptoday_ics_directory": "handoff/uptoday",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_labeled_document_event_has_timezone_and_line_evidence(tmp_path: Path) -> None:
    source = tmp_path / "Termin.txt"
    document = _write_event(source)

    result = analyze_document_calendar(
        document,
        profile_id="lukas",
        area="gesundheit",
        default_timezone="Europe/Berlin",
    )

    assert result.status == "candidate"
    assert result.candidate is not None
    candidate = result.candidate
    assert candidate.title == "Kontrolltermin"
    assert candidate.event_date == "2026-09-14"
    assert candidate.start_time == "10:30"
    assert candidate.end_time == "11:00"
    assert candidate.timezone == "Europe/Berlin"
    assert candidate.start_at == "2026-09-14T10:30:00+02:00"
    assert candidate.all_day is False
    assert candidate.event_uid.endswith("@folderhome.local")
    assert {item.field for item in candidate.evidence} >= {
        "title",
        "event_date",
        "start_time",
        "timezone",
    }
    assert "Interne Notiz" not in str(result.to_dict())


def test_ambiguous_and_sensitive_event_needs_review(tmp_path: Path) -> None:
    source = tmp_path / "Termin.txt"
    document = _write_event(source)
    source.write_text(_event_text() + "Datum: 2026-09-15\n", encoding="utf-8")
    ambiguous = _document(source, source.read_text(encoding="utf-8"))

    ambiguous_result = analyze_document_calendar(
        ambiguous,
        profile_id="lukas",
        area="gesundheit",
        default_timezone="Europe/Berlin",
    )
    gated_result = analyze_document_calendar(
        replace(document, privacy_status=PrivacyStatus.REVIEW_REQUIRED),
        profile_id="lukas",
        area="gesundheit",
        default_timezone="Europe/Berlin",
    )

    assert ambiguous_result.status == "review_required"
    assert any("mehrfach" in issue for issue in ambiguous_result.issues)
    assert gated_result.status == "review_required"
    assert gated_result.candidate is None


def test_profile_backend_overrides_uptoday_configuration_fallback(tmp_path: Path) -> None:
    config_path = _write_calendar_configuration(tmp_path / "config")
    profiles_dir = tmp_path / "profiles"
    _write_profile_configuration(profiles_dir, backend="folderhome_local")
    configuration = load_calendar_configuration(config_path)
    policy = resolve_profile_policy(
        load_profile_configuration(profiles_dir),
        profile_id="lukas",
        area="gesundheit",
    )

    assert configuration.default_backend is CalendarBackend.UPTODAY_ICS
    assert policy.rules[0].key.value == "calendar.backend"
    assert policy.rules[0].value == "folderhome_local"


def test_uptoday_plan_is_deterministic_read_only_ics_handoff(tmp_path: Path) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    source = source_dir / "Termin.txt"
    before = _write_event(source).source_sha256
    config = load_calendar_configuration(
        _write_calendar_configuration(tmp_path / "config")
    )
    profiles_dir = tmp_path / "profiles"
    _write_profile_configuration(profiles_dir)
    policy = resolve_profile_policy(
        load_profile_configuration(profiles_dir),
        profile_id="lukas",
        area="gesundheit",
    )
    analysis = analyze_folder_calendar(
        source_dir,
        profile_id="lukas",
        area="gesundheit",
        default_timezone=config.default_timezone,
        extractor=SyntheticExtractor(),
    )

    first = build_calendar_handoff_plan(
        analysis,
        configuration=config,
        policy=policy,
        planned_at="2026-08-22T00:30:00+02:00",
    )
    second = build_calendar_handoff_plan(
        analysis,
        configuration=config,
        policy=policy,
        planned_at="2026-08-22T00:30:00+02:00",
    )

    assert first.to_dict() == second.to_dict()
    assert first.backend is CalendarBackend.UPTODAY_ICS
    assert first.backend_source == "config_default"
    assert len(first.actions) == 1
    action = first.actions[0]
    assert action.status == "planned"
    assert action.target_path is not None
    assert action.target_path.suffix == ".ics"
    assert action.side_effect == "new_ics_file"
    assert action.content_sha256 is not None
    assert not action.target_path.exists()
    assert sha256(source.read_bytes()).hexdigest() == before


def test_routinika_remains_visibly_blocked_without_connector(tmp_path: Path) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    _write_event(source_dir / "Termin.txt")
    config = load_calendar_configuration(
        _write_calendar_configuration(tmp_path / "config", backend="routinika")
    )
    profiles_dir = tmp_path / "profiles"
    _write_profile_configuration(profiles_dir)
    policy = resolve_profile_policy(
        load_profile_configuration(profiles_dir),
        profile_id="lukas",
        area="gesundheit",
    )
    analysis = analyze_folder_calendar(
        source_dir,
        profile_id="lukas",
        area="gesundheit",
        default_timezone=config.default_timezone,
        extractor=SyntheticExtractor(),
    )

    plan = build_calendar_handoff_plan(
        analysis,
        configuration=config,
        policy=policy,
        planned_at="2026-08-22T00:30:00+02:00",
    )

    assert plan.backend is CalendarBackend.ROUTINIKA
    assert plan.actions[0].status == "blocked"
    assert "kein geprüfter Routinika-Connector" in plan.actions[0].message
    assert plan.actions[0].target_path is None


def test_same_start_conflict_blocks_all_folder_candidates(tmp_path: Path) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    _write_event(source_dir / "A.txt", title="Kontrolltermin")
    _write_event(source_dir / "B.txt", title="Werkstatttermin")
    config = load_calendar_configuration(
        _write_calendar_configuration(tmp_path / "config")
    )
    profiles_dir = tmp_path / "profiles"
    _write_profile_configuration(profiles_dir)
    policy = resolve_profile_policy(
        load_profile_configuration(profiles_dir),
        profile_id="lukas",
        area="gesundheit",
    )
    analysis = analyze_folder_calendar(
        source_dir,
        profile_id="lukas",
        area="gesundheit",
        default_timezone=config.default_timezone,
        extractor=SyntheticExtractor(),
    )

    plan = build_calendar_handoff_plan(
        analysis,
        configuration=config,
        policy=policy,
        planned_at="2026-08-22T00:30:00+02:00",
    )

    assert len(plan.actions) == 2
    assert all(action.status == "blocked" for action in plan.actions)
    assert all("Zeitkonflikt" in action.message for action in plan.actions)
