"""Contracts for private tax receipt workpapers without tax advice."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_TRANSACTION_ID = re.compile(r"transaction_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"tax_receipt_plan_[0-9a-f]{64}")
_ACTION_ID = re.compile(r"tax_receipt_action_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"tax_receipt_report_[0-9a-f]{64}")
_EXPORT_PLAN_ID = re.compile(r"tax_export_plan_[0-9a-f]{64}")
_EXPORT_REPORT_ID = re.compile(r"tax_export_report_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _aware(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Zeitstempel benötigt eine Zeitzone.")


@dataclass(frozen=True, slots=True)
class TaxReceiptRequest:
    request_id: str
    profile_id: str
    tax_year: int
    receipt_date: str
    amount_cents: int
    document_id: str
    finance_transaction_id: str | None
    category_candidate: str | None
    confirmed_category: str | None
    note: str | None

    SCHEMA = "folderhome.tax-receipt-request.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or _ID.fullmatch(self.request_id) is None:
            raise ValueError("Steuerbeleganfrage besitzt ungültige IDs.")
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("Steuerbeleganfrage besitzt ungültige IDs.")
        if not isinstance(self.tax_year, int) or isinstance(self.tax_year, bool):
            raise ValueError("Steuerjahr muss eine Ganzzahl sein.")
        if not isinstance(self.receipt_date, str):
            raise ValueError("Belegdatum muss ein ISO-Datum sein.")
        parsed = date.fromisoformat(self.receipt_date)
        if parsed.year != self.tax_year:
            raise ValueError("Belegdatum und Steuerjahr stimmen nicht überein.")
        if not isinstance(self.amount_cents, int) or isinstance(self.amount_cents, bool):
            raise ValueError("Belegbetrag muss eine ganzzahlige Centzahl sein.")
        if self.amount_cents <= 0:
            raise ValueError("Belegbetrag muss positiv sein.")
        if not isinstance(self.document_id, str) or _DOCUMENT_ID.fullmatch(
            self.document_id
        ) is None:
            raise ValueError("Steuerbeleganfrage benötigt eine Dokument-ID.")
        if self.finance_transaction_id is not None and (
            not isinstance(self.finance_transaction_id, str)
            or (
                _TRANSACTION_ID.fullmatch(self.finance_transaction_id) is None
            )
        ):
            raise ValueError("Steuerbeleganfrage besitzt eine ungültige Buchungs-ID.")
        for value in (self.category_candidate, self.confirmed_category, self.note):
            if value is not None and not isinstance(value, str):
                raise ValueError("Optionale Steuerbelegangaben müssen Text sein.")
        if self.note is not None and len(self.note) > 500:
            raise ValueError("Steuerbelegnotiz ist zu lang.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "tax_year": self.tax_year,
            "receipt_date": self.receipt_date,
            "amount_cents": self.amount_cents,
            "document_id": self.document_id,
            "finance_transaction_id": self.finance_transaction_id,
            "category_candidate": self.category_candidate,
            "confirmed_category": self.confirmed_category,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class TaxReceiptPlan:
    plan_id: str
    plan_sha256: str
    action_id: str
    request: TaxReceiptRequest
    document_sha256: str
    document_source_path: Path
    provider_id: str
    provider_version: str
    provider_revision: str
    provider_store_revision: str
    category_candidate: str | None
    confirmed_category: str | None
    status: str
    provider_write_allowed: bool
    deductibility_assessed: bool = False
    tax_advice: bool = False
    portal_submission_supported: bool = False

    SCHEMA = "folderhome.tax-receipt-plan.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_source_path", self.document_source_path.resolve())
        if _PLAN_ID.fullmatch(self.plan_id) is None or _SHA256.fullmatch(
            self.plan_sha256
        ) is None:
            raise ValueError("Steuerbelegplan besitzt eine ungültige Planbindung.")
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("Steuerbelegplan besitzt eine ungültige Aktion.")
        if _SHA256.fullmatch(self.document_sha256) is None or _SHA256.fullmatch(
            self.provider_store_revision
        ) is None:
            raise ValueError("Steuerbelegplan besitzt ungültige Hashbindungen.")
        if self.status not in {"ready_for_approval", "review_required"}:
            raise ValueError("Steuerbelegplan besitzt einen unbekannten Status.")
        if self.provider_write_allowed != (self.status == "ready_for_approval"):
            raise ValueError("Steuerbelegplan besitzt eine inkonsistente Schreibgrenze.")
        if self.deductibility_assessed or self.tax_advice or self.portal_submission_supported:
            raise ValueError("Steuerbelegplan überschreitet die Arbeitsunterlagengrenze.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "action_id": self.action_id,
            "request": self.request.to_dict(),
            "document_sha256": self.document_sha256,
            "document_source_path": str(self.document_source_path),
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "provider_revision": self.provider_revision,
            "provider_store_revision": self.provider_store_revision,
            "category_candidate": self.category_candidate,
            "confirmed_category": self.confirmed_category,
            "status": self.status,
            "provider_write_allowed": self.provider_write_allowed,
            "deductibility_assessed": False,
            "tax_advice": False,
            "portal_submission_supported": False,
        }


@dataclass(frozen=True, slots=True)
class TaxReceiptApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    action_id: str
    provider_store_revision: str
    approved_at: str
    allow_local_tax_write: bool

    SCHEMA = "folderhome.tax-receipt-approval.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.approval_id) is None or _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Steuerbelegfreigabe besitzt ungültige IDs.")
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("Steuerbelegfreigabe besitzt eine ungültige Aktion.")
        if _SHA256.fullmatch(self.plan_sha256) is None or _SHA256.fullmatch(
            self.provider_store_revision
        ) is None:
            raise ValueError("Steuerbelegfreigabe besitzt ungültige Hashbindungen.")
        _aware(self.approved_at)


@dataclass(frozen=True, slots=True)
class TaxReceiptReport:
    report_id: str
    plan_id: str
    approval_id: str
    provider_id: str
    provider_revision: str
    provider_receipt_number: str
    status: str
    network_invoked: bool = False
    portal_submitted: bool = False

    SCHEMA = "folderhome.tax-receipt-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None or self.status != "executed":
            raise ValueError("Steuerbelegbericht besitzt einen ungültigen Status.")
        if self.network_invoked or self.portal_submitted:
            raise ValueError("Steuerbelegbericht darf keine externe Wirkung ausweisen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "provider_receipt_number": self.provider_receipt_number,
            "status": self.status,
            "network_invoked": False,
            "portal_submitted": False,
        }


@dataclass(frozen=True, slots=True)
class TaxExportPlan:
    plan_id: str
    plan_sha256: str
    profile_id: str
    tax_year: int
    output_path: Path
    provider_store_revision: str
    receipt_count: int
    status: str = "review_required"
    official_format: bool = False
    portal_submission_supported: bool = False

    SCHEMA = "folderhome.tax-export-plan.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", self.output_path.resolve())
        if _EXPORT_PLAN_ID.fullmatch(self.plan_id) is None or _SHA256.fullmatch(
            self.plan_sha256
        ) is None:
            raise ValueError("Steuerexportplan besitzt eine ungültige Identität.")
        if not self.profile_id.strip():
            raise ValueError("Steuerexportplan benötigt ein Profil.")
        if self.status != "review_required" or self.official_format:
            raise ValueError("Steuerexportplan muss private Arbeitsunterlage bleiben.")
        if self.portal_submission_supported:
            raise ValueError("Steuerexportplan darf keine Portalübermittlung anbieten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "profile_id": self.profile_id,
            "tax_year": self.tax_year,
            "output_path": str(self.output_path),
            "provider_store_revision": self.provider_store_revision,
            "receipt_count": self.receipt_count,
            "status": self.status,
            "official_format": False,
            "portal_submission_supported": False,
        }


@dataclass(frozen=True, slots=True)
class TaxExportApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    provider_store_revision: str
    approved_at: str
    allow_local_tax_state_write: bool
    allow_output_write: bool

    SCHEMA = "folderhome.tax-export-approval.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.approval_id) is None or _EXPORT_PLAN_ID.fullmatch(
            self.plan_id
        ) is None:
            raise ValueError("Steuerexportfreigabe besitzt ungültige IDs.")
        if _SHA256.fullmatch(self.plan_sha256) is None or _SHA256.fullmatch(
            self.provider_store_revision
        ) is None:
            raise ValueError("Steuerexportfreigabe besitzt ungültige Hashbindungen.")
        _aware(self.approved_at)


@dataclass(frozen=True, slots=True)
class TaxExportReport:
    report_id: str
    plan_id: str
    approval_id: str
    output_path: Path
    output_sha256: str
    status: str
    official_format: bool = False
    portal_submitted: bool = False
    network_invoked: bool = False

    SCHEMA = "folderhome.tax-export-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", self.output_path.resolve())
        if _EXPORT_REPORT_ID.fullmatch(self.report_id) is None or _SHA256.fullmatch(
            self.output_sha256
        ) is None:
            raise ValueError("Steuerexportbericht besitzt eine ungültige Identität.")
        if self.status != "executed" or self.official_format:
            raise ValueError("Steuerexportbericht muss private Arbeitsunterlage bleiben.")
        if self.portal_submitted or self.network_invoked:
            raise ValueError("Steuerexportbericht darf keine externe Wirkung ausweisen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "output_path": str(self.output_path),
            "output_sha256": self.output_sha256,
            "status": self.status,
            "official_format": False,
            "portal_submitted": False,
            "network_invoked": False,
        }
