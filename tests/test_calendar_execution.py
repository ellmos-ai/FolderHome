from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.calendar_handoff import (
    CalendarWorkflowError,
    analyze_folder_calendar,
    apply_calendar_handoff_plan,
    build_calendar_handoff_plan,
    load_calendar_configuration,
)
from folderhome.application.profile_rules import (
    load_profile_configuration,
    resolve_profile_policy,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.capabilities.calendar_store import CalendarStore
from folderhome.contracts import (
    CalendarHandoffApproval,
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
        source_hash = sha256(source_path.read_bytes()).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, source_hash),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=source_hash,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-08-22T00:00:00+02:00",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetischer Datenschutzstatus.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _write_event(
    path: Path,
    *,
    title: str = "Kontrolltermin",
    event_date: str = "2026-09-14",
    start_time: str = "10:30",
    end_time: str = "11:00",
) -> None:
    path.write_text(
        (
            f"Termin: {title}\n"
            f"Datum: {event_date}\n"
            f"Uhrzeit: {start_time}\n"
            f"Ende: {end_time}\n"
            "Ort: Praxis Beispiel\n"
            "Zeitzone: Europe/Berlin\n"
        ),
        encoding="utf-8",
    )


def _write_configuration(tmp_path: Path, backend: str) -> tuple[Path, Path]:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    handoff_dir = tmp_path / "handoff" / "uptoday"
    config_file = config_dir / "calendar-config.json"
    config_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.calendar-config.v1",
                "default_backend": backend,
                "default_timezone": "Europe/Berlin",
                "uptoday_ics_directory": str(handoff_dir),
            }
        ),
        encoding="utf-8",
    )
    return config_file, handoff_dir


def _write_profiles(tmp_path: Path) -> Path:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "household.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.household-rules.v1",
                "os_account": "synthetic-family-account",
                "rules": [],
            }
        ),
        encoding="utf-8",
    )
    (profiles / "Lukas.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.user-profile.v1",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "os_account": "synthetic-family-account",
                "organizational_only": True,
                "rules": [],
            }
        ),
        encoding="utf-8",
    )
    return profiles


def _build_plan(
    tmp_path: Path,
    *,
    backend: str,
    store: CalendarStore,
    second_event: bool = False,
):
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    _write_event(source_dir / "Termin-A.txt")
    if second_event:
        _write_event(
            source_dir / "Termin-B.txt",
            title="Werkstatttermin",
            event_date="2026-09-15",
        )
    config_file, handoff_dir = _write_configuration(tmp_path, backend)
    configuration = load_calendar_configuration(config_file)
    policy = resolve_profile_policy(
        load_profile_configuration(_write_profiles(tmp_path)),
        profile_id="lukas",
        area="gesundheit",
    )
    analysis = analyze_folder_calendar(
        source_dir,
        profile_id="lukas",
        area="gesundheit",
        default_timezone="Europe/Berlin",
        extractor=SyntheticExtractor(),
    )
    plan = build_calendar_handoff_plan(
        analysis,
        configuration=configuration,
        policy=policy,
        planned_at="2026-08-22T00:30:00+02:00",
        calendar_revision=store.revision(),
        existing_events=store.list_events(),
    )
    return plan, source_dir, handoff_dir


def _approval(plan, *, approval_id: str = "calendar_approval"):
    return CalendarHandoffApproval(
        approval_id=approval_id,
        plan_id=plan.plan_id,
        calendar_revision=plan.calendar_revision,
        action_ids=tuple(
            action.action_id for action in plan.actions if action.status == "planned"
        ),
        approved_at="2026-08-22T00:35:00+02:00",
    )


def test_calendar_execution_requires_exact_state_and_output_gates(tmp_path: Path) -> None:
    store = CalendarStore(tmp_path / "state")
    plan, _, handoff_dir = _build_plan(
        tmp_path,
        backend="uptoday_ics",
        store=store,
    )
    approval = _approval(plan)

    with pytest.raises(CalendarWorkflowError, match="State-Freigabe"):
        apply_calendar_handoff_plan(
            plan,
            approval,
            store=store,
            allow_state_write=False,
            allow_output_write=True,
        )
    with pytest.raises(CalendarWorkflowError, match="Output-Freigabe"):
        apply_calendar_handoff_plan(
            plan,
            approval,
            store=store,
            allow_state_write=True,
            allow_output_write=False,
        )

    assert not store.path.exists()
    assert not handoff_dir.exists()


def test_approved_ics_handoff_writes_verified_files_and_append_only_audit(
    tmp_path: Path,
) -> None:
    store = CalendarStore(tmp_path / "state")
    plan, source_dir, _ = _build_plan(
        tmp_path,
        backend="uptoday_ics",
        store=store,
        second_event=True,
    )
    sources_before = {path: path.read_bytes() for path in source_dir.iterdir()}

    report = apply_calendar_handoff_plan(
        plan,
        _approval(plan),
        store=store,
        allow_state_write=True,
        allow_output_write=True,
    )

    assert report.status == "executed"
    assert report.backend.value == "uptoday_ics"
    assert len(report.items) == 2
    assert report.created_event_ids == ()
    assert all(item.output_path is not None for item in report.items)
    for item in report.items:
        assert item.output_path is not None
        assert item.output_path.is_file()
        assert sha256(item.output_path.read_bytes()).hexdigest() == item.output_sha256
        content = item.output_path.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "@folderhome.local" in content
        assert item.undo_supported is True
    assert store.count_actions() == 2
    assert store.list_events() == ()
    assert {path: path.read_bytes() for path in source_dir.iterdir()} == sources_before


def test_changed_source_blocks_ics_before_state_or_output_write(tmp_path: Path) -> None:
    store = CalendarStore(tmp_path / "state")
    plan, source_dir, handoff_dir = _build_plan(
        tmp_path,
        backend="uptoday_ics",
        store=store,
    )
    next(source_dir.iterdir()).write_text("geändert", encoding="utf-8")

    with pytest.raises(CalendarWorkflowError, match="Quellhash"):
        apply_calendar_handoff_plan(
            plan,
            _approval(plan),
            store=store,
            allow_state_write=True,
            allow_output_write=True,
        )

    assert not store.path.exists()
    assert not handoff_dir.exists()


def test_local_calendar_roundtrip_is_revision_bound_and_idempotent(tmp_path: Path) -> None:
    store = CalendarStore(tmp_path / "state")
    plan, source_dir, handoff_dir = _build_plan(
        tmp_path,
        backend="folderhome_local",
        store=store,
    )

    report = apply_calendar_handoff_plan(
        plan,
        _approval(plan, approval_id="calendar_local"),
        store=store,
        allow_state_write=True,
        allow_output_write=False,
    )

    assert report.status == "executed"
    assert len(report.created_event_ids) == 1
    events = store.list_events(profile_id="lukas", area="gesundheit")
    assert len(events) == 1
    assert events[0].title == "Kontrolltermin"
    assert events[0].event_date == "2026-09-14"
    assert events[0].status == "active"
    assert store.count_actions() == 1
    assert not handoff_dir.exists()

    configuration = plan.configuration
    policy = resolve_profile_policy(
        load_profile_configuration(tmp_path / "profiles"),
        profile_id="lukas",
        area="gesundheit",
    )
    analysis = analyze_folder_calendar(
        source_dir,
        profile_id="lukas",
        area="gesundheit",
        default_timezone="Europe/Berlin",
        extractor=SyntheticExtractor(),
    )
    second = build_calendar_handoff_plan(
        analysis,
        configuration=configuration,
        policy=policy,
        planned_at="2026-08-22T00:40:00+02:00",
        calendar_revision=store.revision(),
        existing_events=store.list_events(),
    )

    assert second.actions[0].status == "noop"
    assert "bereits" in second.actions[0].message


def test_ics_batch_failure_removes_earlier_owned_outputs_and_leaves_no_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = CalendarStore(tmp_path / "state")
    plan, _, handoff_dir = _build_plan(
        tmp_path,
        backend="uptoday_ics",
        store=store,
        second_event=True,
    )
    real_link = os.link
    calls = 0

    def fail_second_link(source: str | bytes, target: str | bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetischer Publikationsfehler")
        real_link(source, target)

    monkeypatch.setattr(os, "link", fail_second_link)

    with pytest.raises(CalendarWorkflowError, match="synthetischer Publikationsfehler"):
        apply_calendar_handoff_plan(
            plan,
            _approval(plan, approval_id="calendar_rollback"),
            store=store,
            allow_state_write=True,
            allow_output_write=True,
        )

    assert not store.path.exists()
    assert not handoff_dir.exists() or list(handoff_dir.iterdir()) == []


def test_calendar_approval_requires_timezone_aware_timestamp(tmp_path: Path) -> None:
    store = CalendarStore(tmp_path / "state")
    plan, _, _ = _build_plan(
        tmp_path,
        backend="folderhome_local",
        store=store,
    )

    with pytest.raises(ValueError, match="Zeitzone"):
        CalendarHandoffApproval(
            approval_id="calendar_time",
            plan_id=plan.plan_id,
            calendar_revision=plan.calendar_revision,
            action_ids=(plan.actions[0].action_id,),
            approved_at="2026-08-22T00:35:00",
        )
