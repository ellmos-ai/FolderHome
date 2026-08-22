from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.contract_cockpit import build_contract_cockpit
from folderhome.application.document_versions import (
    build_archive_proposals,
    build_document_family,
)
from folderhome.application.version_analysis import DocumentVersionAnalysis
from folderhome.contracts import (
    CalendarEventRecord,
    ContactRecord,
    ContentFormat,
    ContractCockpitRequest,
    DateRange,
    DocumentRecord,
    FinanceCoverage,
    IndexStatus,
    PrivacyStatus,
    RecurringCostCandidate,
    RecurringCostReport,
    build_document_id,
)


def _document(path: Path, text: str) -> DocumentRecord:
    path.write_text(text, encoding="utf-8")
    digest = sha256(path.read_bytes()).hexdigest()
    return DocumentRecord(
        document_id=build_document_id(path, digest),
        source_path=path,
        filename=path.name,
        media_type="text/plain",
        source_sha256=digest,
        size_bytes=path.stat().st_size,
        modified_at="2026-01-01T00:00:00Z",
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="synthetic",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="GRÜN",
        index_status=IndexStatus.INDEXED,
        index_provider="synthetic-index",
        index_ref=path.name,
    )


def _request(*, archive_older_versions: bool = True) -> ContractCockpitRequest:
    return ContractCockpitRequest(
        profile_id="lukas",
        area="versicherungen",
        display_name="KFZ-Versicherung Hyundai i10",
        document_query="KFZ Versicherung Hyundai i10",
        object_ref="Hyundai i10",
        counterparty_terms=("Beispiel Versicherung",),
        calendar_terms=("Hyundai i10", "KFZ-Versicherung"),
        account_refs=("giro-lukas",),
        coverage_start="2026-01-01",
        as_of="2026-08-22",
        archive_older_versions=archive_older_versions,
    )


def test_contract_cockpit_combines_existing_evidence_without_writes(tmp_path: Path) -> None:
    old = _document(
        tmp_path / "KFZ_Hyundai_i10_2025.txt",
        "KFZ Versicherung Hyundai i10. Gültig ab 01.01.2025.",
    )
    new = _document(
        tmp_path / "KFZ_Hyundai_i10_2026.txt",
        "KFZ Versicherung Hyundai i10. Gültig ab 01.01.2026.",
    )
    family = build_document_family("KFZ Versicherung Hyundai i10", (old, new))
    version_analysis = DocumentVersionAnalysis(
        original_query="KFZ Versicherung Hyundai i10",
        search_query="KFZ Versicherung Hyundai i10",
        family=family,
        comparisons=(),
        comparison_blocked_document_ids=(),
        archive_proposals=build_archive_proposals(family),
    )
    contact = ContactRecord(
        contact_id=f"contact_{'1' * 64}",
        candidate_id=f"contact_candidate_{'2' * 64}",
        profile_id="lukas",
        area="versicherungen",
        organization="Beispiel Versicherung AG",
        contact_name="Erika Beispiel",
        role="Kundenservice",
        purpose="KFZ-Versicherung",
        object_ref="Hyundai i10",
        email="erika@example.invalid",
        phone="+49 30 123456",
        effective_date="2026-08-01",
        source_document_id=new.document_id,
        source_sha256=new.source_sha256,
        source_path=new.source_path,
        status="active",
        created_at="2026-08-01T10:00:00Z",
        updated_at="2026-08-01T10:00:00Z",
    )
    unrelated_contact = ContactRecord(
        contact_id=f"contact_{'3' * 64}",
        candidate_id=f"contact_candidate_{'4' * 64}",
        profile_id="lukas",
        area="versicherungen",
        organization="Andere AG",
        contact_name=None,
        role=None,
        purpose="Hausrat",
        object_ref="Wohnung",
        email="andere@example.invalid",
        phone=None,
        effective_date="2026-08-01",
        source_document_id=new.document_id,
        source_sha256=new.source_sha256,
        source_path=new.source_path,
        status="active",
        created_at="2026-08-01T10:00:00Z",
        updated_at="2026-08-01T10:00:00Z",
    )
    cost = RecurringCostCandidate(
        candidate_id=f"recurring_{'5' * 64}",
        profile_id="lukas",
        account_ref="giro-lukas",
        counterparty="Beispiel Versicherung AG",
        cost_type="versicherung",
        interval="monthly",
        status="active_candidate",
        amount_cents=4200,
        monthly_cost_cents=4200,
        annualized_cost_cents=50400,
        first_booking_date="2026-06-05",
        last_booking_date="2026-08-05",
        next_expected_from="2026-09-02",
        next_expected_to="2026-09-08",
        transaction_ids=(f"transaction_{'6' * 64}", f"transaction_{'7' * 64}"),
    )
    unrelated_cost = RecurringCostCandidate(
        candidate_id=f"recurring_{'8' * 64}",
        profile_id="lukas",
        account_ref="giro-lukas",
        counterparty="StreamFlix",
        cost_type="subscription",
        interval="monthly",
        status="active_candidate",
        amount_cents=1299,
        monthly_cost_cents=1299,
        annualized_cost_cents=15588,
        first_booking_date="2026-06-05",
        last_booking_date="2026-08-05",
        next_expected_from="2026-09-02",
        next_expected_to="2026-09-08",
        transaction_ids=(f"transaction_{'9' * 64}", f"transaction_{'a' * 64}"),
    )
    event = CalendarEventRecord(
        event_id=f"calendar_event_{'b' * 64}",
        event_uid=f"{'c' * 64}@folderhome.local",
        candidate_id=f"calendar_candidate_{'d' * 64}",
        profile_id="lukas",
        area="versicherungen",
        title="Kündigungsprüfung KFZ-Versicherung Hyundai i10",
        event_date="2026-11-01",
        start_time=None,
        end_time=None,
        timezone="Europe/Berlin",
        location=None,
        source_document_id=new.document_id,
        source_sha256=new.source_sha256,
        source_path=new.source_path,
        status="active",
        created_at="2026-08-01T10:00:00Z",
        updated_at="2026-08-01T10:00:00Z",
    )
    coverage = FinanceCoverage(
        account_ref="giro-lukas",
        requested_range=DateRange("2026-01-01", "2026-08-22"),
        covered_ranges=(DateRange("2026-01-01", "2026-03-31"),),
        gaps=(DateRange("2026-04-01", "2026-08-22"),),
        complete=False,
    )
    before = {path: path.read_bytes() for path in (old.source_path, new.source_path)}

    report = build_contract_cockpit(
        _request(),
        version_analysis=version_analysis,
        contacts=(contact, unrelated_contact),
        recurring_report=RecurringCostReport(
            profile_id="lukas",
            as_of="2026-08-22",
            candidates=(cost, unrelated_cost),
        ),
        calendar_events=(event,),
        finance_coverages=(coverage,),
        component_revisions={
            "contacts": f"contact_revision_{'e' * 64}",
            "finance": f"finance_revision_{'f' * 64}",
            "calendar": f"calendar_revision_{'1' * 64}",
        },
    )

    assert report.latest_version.document.document_id == new.document_id
    assert [item.document.document_id for item in report.older_versions] == [
        old.document_id
    ]
    assert len(report.archive_proposals) == 1
    assert report.archive_proposals[0].gate_granted is False
    assert report.current_contacts == (contact,)
    assert report.prior_contacts == ()
    assert report.recurring_costs == (cost,)
    assert report.calendar_events == (event,)
    assert report.finance_coverages == (coverage,)
    assert report.component_issues == ()
    assert report.read_only is True
    assert report.contract_status_proven is False
    assert report.automatic_archive_executed is False
    assert "Aktuelle belegte Fassung" in report.markdown
    assert "Erika Beispiel" in report.markdown
    assert "42,00 EUR" in report.markdown
    assert "2026-04-01 bis 2026-08-22" in report.markdown
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / "Archiv").exists()
    assert "text" not in report.to_dict()["latest_version"]["document"]


def test_contract_cockpit_keeps_missing_components_and_archive_setting_visible(
    tmp_path: Path,
) -> None:
    document = _document(
        tmp_path / "KFZ_Hyundai_i10_2026.txt",
        "KFZ Versicherung Hyundai i10. Gültig ab 01.01.2026.",
    )
    family = build_document_family("KFZ Versicherung Hyundai i10", (document,))
    analysis = DocumentVersionAnalysis(
        original_query="KFZ Versicherung Hyundai i10",
        search_query="KFZ Versicherung Hyundai i10",
        family=family,
        comparisons=(),
        comparison_blocked_document_ids=(),
        archive_proposals=(),
    )

    report = build_contract_cockpit(
        _request(archive_older_versions=False),
        version_analysis=analysis,
        contacts=(),
        recurring_report=RecurringCostReport("lukas", "2026-08-22", ()),
        calendar_events=(),
        finance_coverages=(),
        component_revisions={},
    )

    assert report.archive_proposals == ()
    assert {item.component for item in report.component_issues} == {
        "contacts",
        "costs",
        "calendar",
        "finance_coverage",
    }
    assert all(item.status == "not_available" for item in report.component_issues)
    assert "Keine passende Evidenz" in report.markdown


def test_contract_cockpit_request_rejects_implicit_or_future_ranges() -> None:
    with pytest.raises(ValueError, match="object_ref"):
        ContractCockpitRequest(
            profile_id="lukas",
            area="versicherungen",
            display_name="KFZ",
            document_query="KFZ",
            object_ref="",
            counterparty_terms=(),
            calendar_terms=(),
            account_refs=(),
            coverage_start="2026-01-01",
            as_of="2026-08-22",
            archive_older_versions=False,
        )
    with pytest.raises(ValueError, match="coverage_start"):
        _ = ContractCockpitRequest(
            profile_id="lukas",
            area="versicherungen",
            display_name="KFZ",
            document_query="KFZ",
            object_ref="Hyundai i10",
            counterparty_terms=(),
            calendar_terms=(),
            account_refs=(),
            coverage_start="2026-09-01",
            as_of=date(2026, 8, 22).isoformat(),
            archive_older_versions=False,
        )
