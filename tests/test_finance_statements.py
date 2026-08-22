from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.finance_statements import (
    FinanceWorkflowError,
    analyze_folder_statements,
    apply_finance_import_plan,
    build_finance_import_plan,
    build_recurring_cost_report,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.capabilities.finance_store import FinanceStore
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    FinanceImportApproval,
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
            modified_at="2026-08-22T01:10:00+02:00",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetischer lokaler Finanztest.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _write_statement(
    path: Path,
    *,
    period_start: str,
    period_end: str,
    booking_date: str,
    amount_cents: int = -1299,
    counterparty: str = "StreamFlix",
    category: str = "subscription",
    reference: str,
    opening_cents: int = 100000,
) -> None:
    closing_cents = opening_cents + amount_cents
    path.write_text(
        (
            "Kontokennung: giro-lukas\n"
            "Institut: Beispielbank\n"
            "Konto-Endung: 1234\n"
            f"Zeitraum: {period_start} | {period_end}\n"
            f"Anfangssaldo: {opening_cents} | EUR\n"
            f"Endsaldo: {closing_cents} | EUR\n"
            f"Buchung: {booking_date} | {amount_cents} | {counterparty} | "
            f"{category} | {reference}\n"
        ),
        encoding="utf-8",
    )


def _plan_and_apply(source_dir: Path, store: FinanceStore):
    analysis = analyze_folder_statements(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_finance_import_plan(analysis, store=store)
    approval = FinanceImportApproval(
        approval_id=f"finance_{len(store.list_statements())}",
        plan_id=plan.plan_id,
        finance_revision=plan.finance_revision,
        action_ids=tuple(
            action.action_id for action in plan.actions if action.status == "planned"
        ),
        approved_at="2026-08-22T01:15:00+02:00",
    )
    report = apply_finance_import_plan(
        plan,
        approval,
        store=store,
        allow_state_write=True,
    )
    return analysis, plan, report


def test_statement_analysis_is_cent_exact_and_evidence_bound(tmp_path: Path) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    _write_statement(
        source_dir / "Juni.txt",
        period_start="2026-06-01",
        period_end="2026-06-30",
        booking_date="2026-06-05",
        reference="tx-juni-stream",
    )

    analysis = analyze_folder_statements(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    statement = analysis.statements[0]
    assert statement.account_ref == "giro-lukas"
    assert statement.account_suffix == "1234"
    assert statement.currency == "EUR"
    assert statement.opening_balance_cents == 100000
    assert statement.closing_balance_cents == 98701
    assert statement.transactions[0].amount_cents == -1299
    assert statement.transactions[0].booking_reference == "tx-juni-stream"
    assert {evidence.line_number for evidence in statement.evidence} == {1, 2, 3, 4, 5, 6}
    assert statement.transactions[0].evidence.line_number == 7


def test_statement_balance_mismatch_requires_review_instead_of_adjustment(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    source = source_dir / "Fehler.txt"
    _write_statement(
        source,
        period_start="2026-06-01",
        period_end="2026-06-30",
        booking_date="2026-06-05",
        reference="tx-fehler",
    )
    source.write_text(
        source.read_text(encoding="utf-8").replace("Endsaldo: 98701", "Endsaldo: 99999"),
        encoding="utf-8",
    )

    analysis = analyze_folder_statements(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    assert analysis.statements == ()
    assert analysis.items[0].status == "review_required"
    assert "Saldo" in analysis.items[0].message


def test_finance_import_requires_gate_rechecks_hash_and_writes_atomically(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    source = source_dir / "Juni.txt"
    _write_statement(
        source,
        period_start="2026-06-01",
        period_end="2026-06-30",
        booking_date="2026-06-05",
        reference="tx-juni-stream",
    )
    store = FinanceStore(tmp_path / "state")
    analysis = analyze_folder_statements(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_finance_import_plan(analysis, store=store)
    approval = FinanceImportApproval(
        approval_id="finance_gate",
        plan_id=plan.plan_id,
        finance_revision=plan.finance_revision,
        action_ids=(plan.actions[0].action_id,),
        approved_at="2026-08-22T01:15:00+02:00",
    )

    with pytest.raises(FinanceWorkflowError, match="State-Freigabe"):
        apply_finance_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=False,
        )
    assert not store.path.exists()

    report = apply_finance_import_plan(
        plan,
        approval,
        store=store,
        allow_state_write=True,
    )

    assert report.status == "executed"
    assert len(report.created_statement_ids) == 1
    assert len(store.list_transactions(account_ref="giro-lukas")) == 1
    assert store.count_audit_events() == 1
    assert source.is_file()

    second = build_finance_import_plan(analysis, store=store)
    assert second.actions[0].status == "noop"
    assert "bereits" in second.actions[0].message


def test_changed_statement_blocks_before_finance_state_write(tmp_path: Path) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    source = source_dir / "Juni.txt"
    _write_statement(
        source,
        period_start="2026-06-01",
        period_end="2026-06-30",
        booking_date="2026-06-05",
        reference="tx-juni-stream",
    )
    store = FinanceStore(tmp_path / "state")
    analysis = analyze_folder_statements(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )
    plan = build_finance_import_plan(analysis, store=store)
    approval = FinanceImportApproval(
        approval_id="finance_hash",
        plan_id=plan.plan_id,
        finance_revision=plan.finance_revision,
        action_ids=(plan.actions[0].action_id,),
        approved_at="2026-08-22T01:15:00+02:00",
    )
    source.write_text("geändert", encoding="utf-8")

    with pytest.raises(FinanceWorkflowError, match="Quellhash"):
        apply_finance_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=True,
        )

    assert not store.path.exists()


def test_adjacent_statement_balance_discontinuity_blocks_both_new_imports(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    _write_statement(
        source_dir / "Januar.txt",
        period_start="2026-01-01",
        period_end="2026-01-31",
        booking_date="2026-01-05",
        reference="tx-jan",
        opening_cents=100000,
    )
    _write_statement(
        source_dir / "Februar.txt",
        period_start="2026-02-01",
        period_end="2026-02-28",
        booking_date="2026-02-05",
        reference="tx-feb",
        opening_cents=100000,
    )
    store = FinanceStore(tmp_path / "state")
    analysis = analyze_folder_statements(
        source_dir,
        profile_id="lukas",
        extractor=SyntheticExtractor(),
    )

    plan = build_finance_import_plan(analysis, store=store)

    assert [action.status for action in plan.actions] == ["blocked", "blocked"]
    assert all("kontinuierlich" in action.message for action in plan.actions)
    assert not store.path.exists()


def test_finance_coverage_keeps_missing_month_visible(tmp_path: Path) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    _write_statement(
        source_dir / "Januar.txt",
        period_start="2026-01-01",
        period_end="2026-01-31",
        booking_date="2026-01-05",
        reference="tx-jan-stream",
    )
    _write_statement(
        source_dir / "März.txt",
        period_start="2026-03-01",
        period_end="2026-03-31",
        booking_date="2026-03-05",
        reference="tx-mar-stream",
    )
    store = FinanceStore(tmp_path / "state")
    _plan_and_apply(source_dir, store)

    coverage = store.coverage(
        account_ref="giro-lukas",
        date_from="2026-01-01",
        date_to="2026-03-31",
    )

    assert [item.to_dict() for item in coverage.covered_ranges] == [
        {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        {"start_date": "2026-03-01", "end_date": "2026-03-31"},
    ]
    assert [item.to_dict() for item in coverage.gaps] == [
        {"start_date": "2026-02-01", "end_date": "2026-02-28"}
    ]
    assert coverage.complete is False
    assert coverage.balance_interpolated is False


def test_monthly_subscription_candidate_has_evidence_and_conservative_prediction(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    for name, start, end, booking, reference in (
        ("Januar", "2026-01-01", "2026-01-31", "2026-01-05", "tx-jan"),
        ("Februar", "2026-02-01", "2026-02-28", "2026-02-05", "tx-feb"),
        ("März", "2026-03-01", "2026-03-31", "2026-03-05", "tx-mar"),
    ):
        opening = {
            "Januar": 100000,
            "Februar": 98701,
            "März": 97402,
        }[name]
        _write_statement(
            source_dir / f"{name}.txt",
            period_start=start,
            period_end=end,
            booking_date=booking,
            reference=reference,
            opening_cents=opening,
        )
    store = FinanceStore(tmp_path / "state")
    _plan_and_apply(source_dir, store)

    report = build_recurring_cost_report(
        store=store,
        profile_id="lukas",
        as_of="2026-04-10",
    )

    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.counterparty == "StreamFlix"
    assert candidate.cost_type == "subscription"
    assert candidate.interval == "monthly"
    assert candidate.status == "active_candidate"
    assert candidate.monthly_cost_cents == 1299
    assert candidate.annualized_cost_cents == 15588
    assert candidate.next_expected_from == "2026-04-02"
    assert candidate.next_expected_to == "2026-04-08"
    assert len(candidate.transaction_ids) == 3
    assert report.contract_status_proven is False
    assert report.total_monthly_cost_cents == 1299
    assert report.total_annualized_cost_cents == 15588

    period = store.period_report(
        account_ref="giro-lukas",
        date_from="2026-01-01",
        date_to="2026-03-31",
    )
    assert period.balance_continuity_verified is True
    assert period.opening_balance_cents == 100000
    assert period.closing_balance_cents == 96103


def test_variable_amounts_do_not_become_one_subscription_candidate(tmp_path: Path) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    _write_statement(
        source_dir / "Januar.txt",
        period_start="2026-01-01",
        period_end="2026-01-31",
        booking_date="2026-01-05",
        reference="tx-jan",
        amount_cents=-1299,
    )
    _write_statement(
        source_dir / "Februar.txt",
        period_start="2026-02-01",
        period_end="2026-02-28",
        booking_date="2026-02-05",
        reference="tx-feb",
        amount_cents=-1499,
        opening_cents=98701,
    )
    store = FinanceStore(tmp_path / "state")
    _plan_and_apply(source_dir, store)

    report = build_recurring_cost_report(
        store=store,
        profile_id="lukas",
        as_of="2026-03-10",
    )

    assert report.candidates == ()
