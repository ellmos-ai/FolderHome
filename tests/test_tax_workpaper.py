import json
from pathlib import Path

import pytest

from folderhome.application.tax_workpaper import (
    TaxWorkflowError,
    apply_tax_receipt_plan,
    build_tax_export_plan,
    build_tax_receipt_plan,
    export_tax_workpaper,
    load_tax_receipt_request,
)
from folderhome.bridges.tax_assistant import TaxAssistantBridge
from folderhome.contracts import (
    PluginDescriptor,
    TaxExportApproval,
    TaxReceiptApproval,
    TaxReceiptRequest,
)

PROVIDER_ROOT = Path(__file__).parents[2] / "steuer-assistent"
REVISION = "5d39aeec98bf0a5734bf07dc35a58aa9e1331309"


def _plugin() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="steuer-assistent",
        name="steuer-assistent",
        version="0.2.3",
        source_repository="https://github.com/ellmos-ai/steuer-assistent.git",
        source_revision=REVISION,
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
        classification="REUSED_UNCHANGED",
        default_mode="dry-run",
        live_enabled=False,
    )


def _bridge(tmp_path: Path) -> TaxAssistantBridge:
    return TaxAssistantBridge(
        plugin=_plugin(),
        provider_root=PROVIDER_ROOT,
        db_path=tmp_path / "tax" / "steuer.db",
    )


def _document(tmp_path: Path) -> dict[str, object]:
    source = tmp_path / "Arbeitsmittel.txt"
    source.write_text("Synthetischer Beleg über 49,90 EUR.", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "document_id": "doc_" + "a" * 64,
        "source_sha256": digest,
        "source_path": str(source),
        "index_status": "indexed",
        "privacy_status": "review_required",
    }


def _request(*, confirmed: str | None = "Arbeitsmittel") -> TaxReceiptRequest:
    return TaxReceiptRequest(
        request_id="tax-receipt-demo",
        profile_id="lukas",
        tax_year=2026,
        receipt_date="2026-03-15",
        amount_cents=4990,
        document_id="doc_" + "a" * 64,
        finance_transaction_id=None,
        category_candidate="Arbeitsmittel",
        confirmed_category=confirmed,
        note="Synthetischer USB-Hub",
    )


def _approval(plan) -> TaxReceiptApproval:
    return TaxReceiptApproval(
        approval_id="tax-receipt-approval",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        action_id=plan.action_id,
        provider_store_revision=plan.provider_store_revision,
        approved_at="2026-08-22T06:00:00+02:00",
        allow_local_tax_write=True,
    )


def test_category_candidate_is_not_a_confirmed_tax_classification(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    plan = build_tax_receipt_plan(
        _request(confirmed=None),
        documents=(_document(tmp_path),),
        transactions=(),
        bridge=bridge,
        allow_sensitive_local_read=True,
    )

    assert plan.status == "review_required"
    assert plan.category_candidate == "Arbeitsmittel"
    assert plan.confirmed_category is None
    assert plan.provider_write_allowed is False
    assert plan.deductibility_assessed is False
    assert plan.tax_advice is False
    assert not bridge.db_path.exists()


def test_receipt_request_loader_rejects_undeclared_fields(tmp_path: Path) -> None:
    request_file = tmp_path / "request.json"
    payload = _request().to_dict()
    payload["automatic_deductibility"] = True
    request_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TaxWorkflowError, match="unbekannte oder fehlende"):
        load_tax_receipt_request(request_file)


def test_confirmed_receipt_is_evidence_bound_and_plan_is_read_only(tmp_path: Path) -> None:
    document = _document(tmp_path)
    bridge = _bridge(tmp_path)
    plan = build_tax_receipt_plan(
        _request(),
        documents=(document,),
        transactions=(),
        bridge=bridge,
        allow_sensitive_local_read=True,
    )

    assert plan.status == "ready_for_approval"
    assert plan.document_sha256 == document["source_sha256"]
    assert plan.provider_revision == REVISION
    assert plan.provider_write_allowed is True
    assert plan.portal_submission_supported is False
    assert not bridge.db_path.exists()


def test_receipt_apply_is_exact_idempotent_and_uses_provider(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    plan = build_tax_receipt_plan(
        _request(),
        documents=(_document(tmp_path),),
        transactions=(),
        bridge=bridge,
        allow_sensitive_local_read=True,
    )

    report = apply_tax_receipt_plan(
        plan,
        _approval(plan),
        bridge=bridge,
        allow_state_write=True,
    )

    assert report.status == "executed"
    assert report.provider_id == "steuer-assistent"
    assert report.provider_receipt_number.startswith("B-20260315-")
    assert report.network_invoked is False
    assert bridge.has_plan(plan.plan_id) is True
    with pytest.raises(TaxWorkflowError, match="bereits angewendet"):
        apply_tax_receipt_plan(
            plan,
            _approval(plan),
            bridge=bridge,
            allow_state_write=True,
        )


def test_changed_document_or_provider_state_blocks_before_write(tmp_path: Path) -> None:
    document = _document(tmp_path)
    bridge = _bridge(tmp_path)
    plan = build_tax_receipt_plan(
        _request(),
        documents=(document,),
        transactions=(),
        bridge=bridge,
        allow_sensitive_local_read=True,
    )
    Path(str(document["source_path"])).write_text("geändert", encoding="utf-8")

    with pytest.raises(TaxWorkflowError, match="Dokumenthash"):
        apply_tax_receipt_plan(
            plan,
            _approval(plan),
            bridge=bridge,
            allow_state_write=True,
        )
    assert not bridge.db_path.exists()


def test_private_export_has_separate_output_gate_and_no_portal(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    receipt_plan = build_tax_receipt_plan(
        _request(),
        documents=(_document(tmp_path),),
        transactions=(),
        bridge=bridge,
        allow_sensitive_local_read=True,
    )
    apply_tax_receipt_plan(
        receipt_plan,
        _approval(receipt_plan),
        bridge=bridge,
        allow_state_write=True,
    )
    output = tmp_path / "STEUER_UNTERLAGEN_2026.zip"
    export_plan = build_tax_export_plan(
        2026,
        profile_id="lukas",
        output_path=output,
        bridge=bridge,
    )
    approval = TaxExportApproval(
        approval_id="tax-export-approval",
        plan_id=export_plan.plan_id,
        plan_sha256=export_plan.plan_sha256,
        provider_store_revision=export_plan.provider_store_revision,
        approved_at="2026-08-22T06:05:00+02:00",
        allow_local_tax_state_write=True,
        allow_output_write=True,
    )

    with pytest.raises(TaxWorkflowError, match="Ausgabefreigabe"):
        export_tax_workpaper(
            export_plan,
            approval,
            bridge=bridge,
            allow_state_write=True,
            allow_output_write=False,
        )
    report = export_tax_workpaper(
        export_plan,
        approval,
        bridge=bridge,
        allow_state_write=True,
        allow_output_write=True,
    )

    assert output.is_file()
    assert report.status == "executed"
    assert report.official_format is False
    assert report.portal_submitted is False
    assert report.network_invoked is False
