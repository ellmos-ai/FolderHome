"""Orchestrate private tax receipt workpapers without tax advice or submission."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from folderhome.bridges.tax_assistant import (
    ALLOWED_CATEGORIES,
    TaxAssistantBridge,
    TaxAssistantBridgeError,
)
from folderhome.contracts import FinanceTransactionRecord
from folderhome.contracts.tax import (
    TaxExportApproval,
    TaxExportPlan,
    TaxExportReport,
    TaxReceiptApproval,
    TaxReceiptPlan,
    TaxReceiptReport,
    TaxReceiptRequest,
)


class TaxWorkflowError(RuntimeError):
    """Raised before an unsafe tax-state or workpaper action."""


def load_tax_receipt_request(path: Path) -> TaxReceiptRequest:
    """Load one strict receipt request without accepting undeclared fields."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaxWorkflowError(f"Steuerbeleganfrage ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != TaxReceiptRequest.SCHEMA:
        raise TaxWorkflowError("Steuerbeleganfrage besitzt ein unbekanntes Schema.")
    expected = {
        "schema",
        "request_id",
        "profile_id",
        "tax_year",
        "receipt_date",
        "amount_cents",
        "document_id",
        "finance_transaction_id",
        "category_candidate",
        "confirmed_category",
        "note",
    }
    if set(payload) != expected:
        raise TaxWorkflowError(
            "Steuerbeleganfrage besitzt unbekannte oder fehlende Felder."
        )
    try:
        return TaxReceiptRequest(
            request_id=payload["request_id"],
            profile_id=payload["profile_id"],
            tax_year=payload["tax_year"],
            receipt_date=payload["receipt_date"],
            amount_cents=payload["amount_cents"],
            document_id=payload["document_id"],
            finance_transaction_id=payload["finance_transaction_id"],
            category_candidate=payload["category_candidate"],
            confirmed_category=payload["confirmed_category"],
            note=payload["note"],
        )
    except (TypeError, ValueError) as exc:
        raise TaxWorkflowError(f"Steuerbeleganfrage ist ungültig: {exc}") from exc


def build_tax_receipt_plan(
    request: TaxReceiptRequest,
    *,
    documents: tuple[dict[str, object], ...],
    transactions: tuple[FinanceTransactionRecord, ...],
    bridge: TaxAssistantBridge,
    allow_sensitive_local_read: bool,
) -> TaxReceiptPlan:
    if not allow_sensitive_local_read:
        raise TaxWorkflowError("Sensitivitätsfreigabe für Steuerbelege fehlt.")
    matches = [item for item in documents if item.get("document_id") == request.document_id]
    if len(matches) != 1:
        raise TaxWorkflowError("Steuerbelegdokument wurde nicht eindeutig im Katalog gefunden.")
    document = matches[0]
    if document.get("index_status") != "indexed":
        raise TaxWorkflowError("Steuerbelegdokument ist nicht vollständig katalogisiert.")
    source_path = Path(str(document.get("source_path", ""))).resolve()
    expected_sha = str(document.get("source_sha256", ""))
    if not source_path.is_file() or _file_sha(source_path) != expected_sha:
        raise TaxWorkflowError("Steuerbelegdokument stimmt nicht mit dem Dokumenthash überein.")
    if request.finance_transaction_id is not None:
        tx_matches = [
            item for item in transactions if item.transaction_id == request.finance_transaction_id
        ]
        if len(tx_matches) != 1 or tx_matches[0].profile_id != request.profile_id:
            raise TaxWorkflowError("Finanzbuchung wurde nicht eindeutig für das Profil gefunden.")
        if abs(tx_matches[0].amount_cents) != request.amount_cents:
            raise TaxWorkflowError("Finanzbuchung und Belegbetrag stimmen nicht überein.")
    for category in (request.category_candidate, request.confirmed_category):
        if category is not None and category not in ALLOWED_CATEGORIES:
            raise TaxWorkflowError(f"Unbekannte steuerliche Eingabegruppe: {category}")
    status = "ready_for_approval" if request.confirmed_category is not None else "review_required"
    store_revision = bridge.revision()
    core = {
        "request": request.to_dict(),
        "document_sha256": expected_sha,
        "provider_revision": bridge.provider_revision,
        "provider_store_revision": store_revision,
    }
    digest = _sha(_canonical(core))
    plan_id = f"tax_receipt_plan_{digest}"
    action_id = f"tax_receipt_action_{_sha(plan_id + ':add')}"
    plan_sha = _sha(_canonical({**core, "plan_id": plan_id, "action_id": action_id}))
    return TaxReceiptPlan(
        plan_id=plan_id,
        plan_sha256=plan_sha,
        action_id=action_id,
        request=request,
        document_sha256=expected_sha,
        document_source_path=source_path,
        provider_id=bridge.provider_id,
        provider_version=bridge.plugin.version,
        provider_revision=bridge.provider_revision,
        provider_store_revision=store_revision,
        category_candidate=request.category_candidate,
        confirmed_category=request.confirmed_category,
        status=status,
        provider_write_allowed=status == "ready_for_approval",
    )


def apply_tax_receipt_plan(
    plan: TaxReceiptPlan,
    approval: TaxReceiptApproval,
    *,
    bridge: TaxAssistantBridge,
    allow_state_write: bool,
) -> TaxReceiptReport:
    if not plan.provider_write_allowed:
        raise TaxWorkflowError("Steuerkategorie ist nur ein Vorschlag und nicht bestätigt.")
    if not allow_state_write or not approval.allow_local_tax_write:
        raise TaxWorkflowError("Lokale Steuerablage benötigt beide Schreibfreigaben.")
    if (
        approval.plan_id != plan.plan_id
        or approval.plan_sha256 != plan.plan_sha256
        or approval.action_id != plan.action_id
        or approval.provider_store_revision != plan.provider_store_revision
    ):
        raise TaxWorkflowError("Steuerbelegfreigabe stimmt nicht exakt mit dem Plan überein.")
    if bridge.has_plan(plan.plan_id):
        raise TaxWorkflowError("Steuerbelegplan wurde bereits angewendet.")
    if bridge.revision() != plan.provider_store_revision:
        raise TaxWorkflowError("Steuer-Providerstore hat sich seit dem Plan geändert.")
    if _file_sha(plan.document_source_path) != plan.document_sha256:
        raise TaxWorkflowError(
            "Steuerbelegdokument stimmt nicht mehr mit dem Dokumenthash überein."
        )
    try:
        number = bridge.add_receipt(plan)
    except TaxAssistantBridgeError as exc:
        raise TaxWorkflowError(str(exc)) from exc
    report_id = f"tax_receipt_report_{_sha(plan.plan_id + ':' + number)}"
    return TaxReceiptReport(
        report_id=report_id,
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        provider_id=bridge.provider_id,
        provider_revision=bridge.provider_revision,
        provider_receipt_number=number,
        status="executed",
    )


def build_tax_export_plan(
    tax_year: int,
    *,
    profile_id: str,
    output_path: Path,
    bridge: TaxAssistantBridge,
) -> TaxExportPlan:
    if not profile_id.strip():
        raise TaxWorkflowError("Steuerexport benötigt ein Profil.")
    if tax_year < 2000 or tax_year > 2100:
        raise TaxWorkflowError("Steuerexportjahr muss zwischen 2000 und 2100 liegen.")
    if output_path.suffix.lower() != ".zip":
        raise TaxWorkflowError("Private Steuer-Arbeitsunterlage muss eine ZIP-Datei sein.")
    if output_path.exists():
        raise TaxWorkflowError("Steuerexportziel existiert bereits.")
    revision = bridge.revision()
    core = {
        "profile_id": profile_id,
        "tax_year": tax_year,
        "output_path": str(output_path.resolve()),
        "provider_store_revision": revision,
        "receipt_count": bridge.receipt_count(tax_year),
    }
    digest = _sha(_canonical(core))
    plan_id = f"tax_export_plan_{digest}"
    return TaxExportPlan(
        plan_id=plan_id,
        plan_sha256=_sha(_canonical({**core, "plan_id": plan_id})),
        profile_id=profile_id,
        tax_year=tax_year,
        output_path=output_path,
        provider_store_revision=revision,
        receipt_count=core["receipt_count"],
    )


def export_tax_workpaper(
    plan: TaxExportPlan,
    approval: TaxExportApproval,
    *,
    bridge: TaxAssistantBridge,
    allow_state_write: bool,
    allow_output_write: bool,
) -> TaxExportReport:
    if not allow_output_write or not approval.allow_output_write:
        raise TaxWorkflowError("Ausgabefreigabe für private Steuer-Arbeitsunterlage fehlt.")
    if not allow_state_write or not approval.allow_local_tax_state_write:
        raise TaxWorkflowError("State-Freigabe für Exportprotokoll fehlt.")
    if (
        approval.plan_id != plan.plan_id
        or approval.plan_sha256 != plan.plan_sha256
        or approval.provider_store_revision != plan.provider_store_revision
    ):
        raise TaxWorkflowError("Steuerexportfreigabe stimmt nicht exakt mit dem Plan überein.")
    if bridge.revision() != plan.provider_store_revision:
        raise TaxWorkflowError("Steuer-Providerstore hat sich seit dem Exportplan geändert.")
    if plan.output_path.exists():
        raise TaxWorkflowError("Steuerexportziel existiert bereits.")
    try:
        output = bridge.export_workpaper(plan.tax_year, plan.output_path)
    except TaxAssistantBridgeError as exc:
        raise TaxWorkflowError(str(exc)) from exc
    output_sha = _file_sha(output)
    return TaxExportReport(
        report_id=f"tax_export_report_{_sha(plan.plan_id + ':' + output_sha)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        output_path=output,
        output_sha256=output_sha,
        status="executed",
    )


def _file_sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
