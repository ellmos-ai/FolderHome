from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.household_inventory import (
    analyze_folder_inventory,
    apply_inventory_import_plan,
    build_inventory_import_plan,
)
from folderhome.application.medication_intake import (
    MedicationWorkflowError,
    analyze_folder_medication_plans,
    apply_medication_import_plan,
    build_medication_day_report,
    build_medication_import_plan,
    confirm_medication_intake,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.capabilities.inventory_store import InventoryStore
from folderhome.capabilities.medication_store import MedicationStore
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    InventoryImportApproval,
    MedicationImportApproval,
    MedicationIntakeConfirmation,
    PrivacyStatus,
    build_document_id,
)


class SyntheticExtractor:
    def __init__(self, privacy_status: PrivacyStatus = PrivacyStatus.CLEAR) -> None:
        self.privacy_status = privacy_status

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
            modified_at="2026-08-22T02:45:00+02:00",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=self.privacy_status,
            privacy_summary="Synthetischer lokaler Medikamententest.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _write_plan(
    path: Path,
    *,
    medication: str = "DemoMed",
    dose: str = "1",
    dose_unit: str = "Tablette",
    scheduled_time: str = "08:00",
    weekdays: str = "täglich",
    valid_from: str = "2026-08-22",
    valid_to: str | None = "2026-12-31",
) -> None:
    lines = [
        f"Präparat: {medication}",
        f"Dosis: {dose}",
        f"Dosiseinheit: {dose_unit}",
        f"Zeitpunkt: {scheduled_time}",
        "Zeitzone: Europe/Berlin",
        f"Wochentage: {weekdays}",
        f"Gültig-von: {valid_from}",
    ]
    if valid_to is not None:
        lines.append(f"Gültig-bis: {valid_to}")
    lines.extend(
        [
            "Bestandsbereich: Gesundheit",
            f"Bestandsgegenstand: {medication}",
            f"Bestandseinheit: {dose_unit}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plan_approval(plan, approval_id: str) -> MedicationImportApproval:
    return MedicationImportApproval(
        approval_id=approval_id,
        plan_id=plan.plan_id,
        medication_revision=plan.medication_revision,
        action_ids=tuple(
            action.action_id for action in plan.actions if action.status == "planned"
        ),
        approved_at="2026-08-22T02:50:00+02:00",
    )


def _import_plan(source_dir: Path, store: MedicationStore) -> None:
    analysis = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_medication_import_plan(analysis, store=store)
    apply_medication_import_plan(
        plan,
        _plan_approval(plan, f"medication_{len(store.list_schedules())}"),
        store=store,
        allow_state_write=True,
    )


def test_medication_plan_is_exact_timezone_bound_and_evidenced(tmp_path: Path) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "DemoMed.txt", dose="0.5", weekdays="Montag, Samstag")

    analysis = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    schedule = analysis.schedules[0]
    assert schedule.medication_name == "DemoMed"
    assert schedule.dose_quantity_milli == 500
    assert schedule.dose_unit == "Tablette"
    assert schedule.scheduled_time == "08:00"
    assert schedule.timezone == "Europe/Berlin"
    assert schedule.weekdays == (0, 5)
    assert schedule.inventory_item_id.startswith("inventory_item_")
    assert {item.line_number for item in schedule.evidence} == set(range(1, 12))


def test_as_needed_and_excess_precision_require_review(tmp_path: Path) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "Bedarf.txt", weekdays="bei Bedarf")
    _write_plan(source_dir / "Genauigkeit.txt", medication="Anderes", dose="0.1234")

    analysis = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    assert analysis.schedules == ()
    assert all(item.status == "review_required" for item in analysis.items)


def test_sensitive_medication_plan_requires_local_read_gate(tmp_path: Path) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "DemoMed.txt")

    denied = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(PrivacyStatus.REVIEW_REQUIRED),
    )
    allowed = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(PrivacyStatus.REVIEW_REQUIRED),
        allow_sensitive_local_read=True,
    )

    assert denied.items[0].status == "review_required"
    assert len(allowed.schedules) == 1


def test_medication_import_requires_gate_and_rechecks_source(tmp_path: Path) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    source = source_dir / "DemoMed.txt"
    _write_plan(source)
    store = MedicationStore(tmp_path / "state")
    analysis = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_medication_import_plan(analysis, store=store)
    approval = _plan_approval(plan, "medication_gate")

    with pytest.raises(MedicationWorkflowError, match="State-Freigabe"):
        apply_medication_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=False,
        )
    assert not store.path.exists()

    source.write_text("geändert", encoding="utf-8")
    with pytest.raises(MedicationWorkflowError, match="Quellhash"):
        apply_medication_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=True,
        )
    assert not store.path.exists()


def test_medication_schedule_import_is_append_only_and_conflicts_fail_closed(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "DemoMed-a.txt", dose="1")
    _write_plan(source_dir / "DemoMed-b.txt", dose="2")
    store = MedicationStore(tmp_path / "state")
    analysis = analyze_folder_medication_plans(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_medication_import_plan(analysis, store=store)

    assert [action.status for action in plan.actions] == ["blocked", "blocked"]
    assert not store.path.exists()

    safe_dir = tmp_path / "Sicher"
    safe_dir.mkdir()
    _write_plan(safe_dir / "DemoMed.txt")
    _import_plan(safe_dir, store)
    assert len(store.list_schedules(profile_id="lukas")) == 1
    assert store.count_audit_events() == 1


def test_day_report_is_read_only_and_separates_plan_from_confirmation(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "DemoMed.txt", weekdays="Samstag")
    store = MedicationStore(tmp_path / "state")
    _import_plan(source_dir, store)
    before = store.path.read_bytes()

    report = build_medication_day_report(
        store=store,
        profile_id="lukas",
        on_date="2026-08-22",
        as_of="2026-08-22T07:00:00+02:00",
    )

    assert len(report.doses) == 1
    assert report.doses[0].status == "upcoming"
    assert report.doses[0].confirmed_at is None
    assert report.automatic_reminder_sent is False
    assert store.path.read_bytes() == before


def test_confirmation_is_gated_idempotent_and_never_changes_inventory(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "DemoMed.txt", weekdays="Samstag")
    medication_store = MedicationStore(tmp_path / "state")
    _import_plan(source_dir, medication_store)

    inventory_dir = tmp_path / "Bestand"
    inventory_dir.mkdir()
    inventory_source = inventory_dir / "DemoMed.txt"
    inventory_source.write_text(
        "Gegenstand: DemoMed\n"
        "Bereich: Gesundheit\n"
        "Ort: Medikamentenschrank\n"
        "Einheit: Tablette\n"
        "Menge: 10\n"
        "Mindestbestand: 5\n"
        "Erfasst-am: 2026-08-22\n",
        encoding="utf-8",
    )
    inventory_store = InventoryStore(tmp_path / "state")
    inventory_analysis = analyze_folder_inventory(
        inventory_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    inventory_plan = build_inventory_import_plan(inventory_analysis, store=inventory_store)
    inventory_approval = InventoryImportApproval(
        approval_id="inventory_medication",
        plan_id=inventory_plan.plan_id,
        inventory_revision=inventory_plan.inventory_revision,
        action_ids=(inventory_plan.actions[0].action_id,),
        approved_at="2026-08-22T02:55:00+02:00",
    )
    apply_inventory_import_plan(
        inventory_plan,
        inventory_approval,
        store=inventory_store,
        allow_state_write=True,
    )
    inventory_before = inventory_store.path.read_bytes()

    day = build_medication_day_report(
        store=medication_store,
        inventory_store=inventory_store,
        profile_id="lukas",
        on_date="2026-08-22",
        as_of="2026-08-22T09:00:00+02:00",
    )
    dose = day.doses[0]
    assert dose.status == "confirmation_pending"
    assert dose.inventory_status == "available_candidate"
    confirmation = MedicationIntakeConfirmation(
        confirmation_id="medication_taken",
        medication_revision=day.medication_revision,
        dose_id=dose.dose_id,
        schedule_id=dose.schedule_id,
        scheduled_date=dose.scheduled_date,
        confirmed_at="2026-08-22T08:05:00+02:00",
    )

    with pytest.raises(MedicationWorkflowError, match="State-Freigabe"):
        confirm_medication_intake(
            confirmation,
            store=medication_store,
            allow_state_write=False,
        )

    executed = confirm_medication_intake(
        confirmation,
        store=medication_store,
        allow_state_write=True,
    )
    assert executed.status == "executed"
    assert executed.created_event_id is not None
    assert inventory_store.path.read_bytes() == inventory_before

    refreshed = build_medication_day_report(
        store=medication_store,
        profile_id="lukas",
        on_date="2026-08-22",
        as_of="2026-08-22T09:00:00+02:00",
    )
    assert refreshed.doses[0].status == "confirmed"
    duplicate = MedicationIntakeConfirmation(
        confirmation_id="medication_taken_again",
        medication_revision=refreshed.medication_revision,
        dose_id=dose.dose_id,
        schedule_id=dose.schedule_id,
        scheduled_date=dose.scheduled_date,
        confirmed_at="2026-08-22T08:06:00+02:00",
    )
    noop = confirm_medication_intake(
        duplicate,
        store=medication_store,
        allow_state_write=True,
    )
    assert noop.status == "noop"
    assert noop.created_event_id is None
    assert len(medication_store.list_intake_events()) == 1


def test_non_scheduled_weekday_produces_no_dose(tmp_path: Path) -> None:
    source_dir = tmp_path / "Pläne"
    source_dir.mkdir()
    _write_plan(source_dir / "DemoMed.txt", weekdays="Montag")
    store = MedicationStore(tmp_path / "state")
    _import_plan(source_dir, store)

    report = build_medication_day_report(
        store=store,
        profile_id="lukas",
        on_date="2026-08-22",
        as_of="2026-08-22T09:00:00+02:00",
    )

    assert report.doses == ()
