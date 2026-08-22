from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.household_inventory import (
    InventoryWorkflowError,
    analyze_folder_inventory,
    apply_inventory_import_plan,
    build_inventory_import_plan,
    build_inventory_needs_report,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.capabilities.inventory_store import InventoryStore
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    InventoryImportApproval,
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
            modified_at="2026-08-22T02:00:00+02:00",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=self.privacy_status,
            privacy_summary="Synthetischer lokaler Inventartest.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _write_observation(
    path: Path,
    *,
    name: str = "Reis",
    area: str = "Küche",
    location: str = "Vorratsschrank",
    unit: str = "kg",
    quantity: str = "1.5",
    minimum: str = "2",
    observed_on: str = "2026-08-22",
    expiry_date: str | None = "2026-09-05",
) -> None:
    lines = [
        f"Gegenstand: {name}",
        f"Bereich: {area}",
        f"Ort: {location}",
        f"Einheit: {unit}",
        f"Menge: {quantity}",
        f"Mindestbestand: {minimum}",
        f"Erfasst-am: {observed_on}",
    ]
    if expiry_date is not None:
        lines.append(f"Ablaufdatum: {expiry_date}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _approval(plan, approval_id: str) -> InventoryImportApproval:
    return InventoryImportApproval(
        approval_id=approval_id,
        plan_id=plan.plan_id,
        inventory_revision=plan.inventory_revision,
        action_ids=tuple(
            action.action_id for action in plan.actions if action.status == "planned"
        ),
        approved_at="2026-08-22T02:10:00+02:00",
    )


def test_inventory_analysis_is_decimal_exact_and_evidence_bound(tmp_path: Path) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    _write_observation(source_dir / "Reis.txt")

    analysis = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    observation = analysis.observations[0]
    assert observation.profile_id == "lukas"
    assert observation.name == "Reis"
    assert observation.area == "Küche"
    assert observation.location == "Vorratsschrank"
    assert observation.quantity_milli == 1500
    assert observation.minimum_quantity_milli == 2000
    assert observation.unit == "kg"
    assert observation.expiry_date == "2026-09-05"
    assert {evidence.line_number for evidence in observation.evidence} == set(range(1, 9))


def test_inventory_analysis_refuses_silent_decimal_rounding(tmp_path: Path) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    _write_observation(source_dir / "Reis.txt", quantity="1.2345")

    analysis = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    assert analysis.observations == ()
    assert analysis.items[0].status == "review_required"
    assert "Nachkommastellen" in analysis.items[0].message


def test_sensitive_inventory_needs_local_read_gate_and_blocked_stays_blocked(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    _write_observation(source_dir / "Reis.txt")

    review = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(PrivacyStatus.REVIEW_REQUIRED),
    )
    allowed = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(PrivacyStatus.REVIEW_REQUIRED),
        allow_sensitive_local_read=True,
    )
    blocked = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(PrivacyStatus.BLOCKED),
        allow_sensitive_local_read=True,
    )

    assert review.items[0].status == "review_required"
    assert len(allowed.observations) == 1
    assert blocked.items[0].status == "blocked"
    assert blocked.observations == ()


def test_inventory_import_requires_gate_and_appends_audited_event(tmp_path: Path) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    source = source_dir / "Reis.txt"
    _write_observation(source)
    store = InventoryStore(tmp_path / "state")
    analysis = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_inventory_import_plan(analysis, store=store)
    approval = _approval(plan, "inventory_gate")

    with pytest.raises(InventoryWorkflowError, match="State-Freigabe"):
        apply_inventory_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=False,
        )
    assert not store.path.exists()

    report = apply_inventory_import_plan(
        plan,
        approval,
        store=store,
        allow_state_write=True,
    )

    assert report.status == "executed"
    assert len(report.created_event_ids) == 1
    assert len(store.list_events(profile_id="lukas")) == 1
    assert store.count_audit_events() == 1
    assert source.is_file()
    second = build_inventory_import_plan(analysis, store=store)
    assert second.actions[0].status == "noop"


def test_changed_inventory_source_blocks_before_state_write(tmp_path: Path) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    source = source_dir / "Reis.txt"
    _write_observation(source)
    store = InventoryStore(tmp_path / "state")
    analysis = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_inventory_import_plan(analysis, store=store)
    approval = _approval(plan, "inventory_hash")
    source.write_text("geändert", encoding="utf-8")

    with pytest.raises(InventoryWorkflowError, match="Quellhash"):
        apply_inventory_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=True,
        )

    assert not store.path.exists()


def test_inventory_import_rejects_stale_revision(tmp_path: Path) -> None:
    store = InventoryStore(tmp_path / "state")
    stale_dir = tmp_path / "Stale"
    stale_dir.mkdir()
    _write_observation(stale_dir / "Reis.txt")
    stale_analysis = analyze_folder_inventory(
        stale_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    stale_plan = build_inventory_import_plan(stale_analysis, store=store)

    other_dir = tmp_path / "Andere"
    other_dir.mkdir()
    _write_observation(other_dir / "Nudeln.txt", name="Nudeln", unit="Packung")
    other_analysis = analyze_folder_inventory(
        other_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    other_plan = build_inventory_import_plan(other_analysis, store=store)
    apply_inventory_import_plan(
        other_plan,
        _approval(other_plan, "inventory_other"),
        store=store,
        allow_state_write=True,
    )

    with pytest.raises(InventoryWorkflowError, match="seit der Planung"):
        apply_inventory_import_plan(
            stale_plan,
            _approval(stale_plan, "inventory_stale"),
            store=store,
            allow_state_write=True,
        )

    assert len(store.list_events()) == 1


def test_new_observation_appends_history_and_current_view_uses_latest(
    tmp_path: Path,
) -> None:
    store = InventoryStore(tmp_path / "state")
    first_dir = tmp_path / "Erste"
    first_dir.mkdir()
    _write_observation(
        first_dir / "Reis.txt",
        quantity="2",
        observed_on="2026-08-20",
    )
    first_analysis = analyze_folder_inventory(
        first_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    first_plan = build_inventory_import_plan(first_analysis, store=store)
    apply_inventory_import_plan(
        first_plan,
        _approval(first_plan, "inventory_first"),
        store=store,
        allow_state_write=True,
    )

    second_dir = tmp_path / "Zweite"
    second_dir.mkdir()
    _write_observation(
        second_dir / "Reis.txt",
        quantity="1",
        observed_on="2026-08-22",
    )
    second_analysis = analyze_folder_inventory(
        second_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    second_plan = build_inventory_import_plan(second_analysis, store=store)
    apply_inventory_import_plan(
        second_plan,
        _approval(second_plan, "inventory_second"),
        store=store,
        allow_state_write=True,
    )

    history = store.list_events(profile_id="lukas")
    current = store.current_items(profile_id="lukas")
    assert len(history) == 2
    assert len(current) == 1
    assert current[0].quantity_milli == 1000
    assert history[0].event_id != history[1].event_id


def test_same_day_conflicting_observations_are_blocked(tmp_path: Path) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    _write_observation(source_dir / "Reis-a.txt", quantity="1")
    _write_observation(source_dir / "Reis-b.txt", quantity="2")
    store = InventoryStore(tmp_path / "state")
    analysis = analyze_folder_inventory(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    plan = build_inventory_import_plan(analysis, store=store)

    assert [action.status for action in plan.actions] == ["blocked", "blocked"]
    assert all("widersprüch" in action.message for action in plan.actions)
    assert not store.path.exists()


def test_inventory_needs_are_profile_scoped_and_review_only(tmp_path: Path) -> None:
    store = InventoryStore(tmp_path / "state")
    for profile_id, quantity, approval_id in (
        ("lukas", "1.5", "inventory_lukas"),
        ("hanna", "3", "inventory_hanna"),
    ):
        source_dir = tmp_path / profile_id
        source_dir.mkdir()
        _write_observation(source_dir / "Reis.txt", quantity=quantity)
        analysis = analyze_folder_inventory(
            source_dir,
            profile_id=profile_id,
            extractor=SyntheticExtractor(),
        )
        plan = build_inventory_import_plan(analysis, store=store)
        apply_inventory_import_plan(
            plan,
            _approval(plan, approval_id),
            store=store,
            allow_state_write=True,
        )

    report = build_inventory_needs_report(
        store=store,
        profile_id="lukas",
        as_of="2026-08-22",
        expiry_horizon_days=30,
    )

    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.profile_id == "lukas"
    assert candidate.shortfall_quantity_milli == 500
    assert candidate.reasons == ("below_minimum", "expires_soon")
    assert report.automatic_purchase is False
    assert store.current_items(profile_id="hanna")[0].quantity_milli == 3000
