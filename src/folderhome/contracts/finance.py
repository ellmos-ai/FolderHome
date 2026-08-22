"""Contracts for evidenced bank statements and conservative recurring costs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

_ACTION_ID = re.compile(r"finance_action_[0-9a-f]{32}")
_APPROVAL_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"finance_plan_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"finance_report_[0-9a-f]{64}")
_REVISION = re.compile(r"finance_revision_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_STATEMENT_ID = re.compile(r"statement_[0-9a-f]{64}")
_TRANSACTION_ID = re.compile(r"transaction_[0-9a-f]{64}")
_RECURRING_ID = re.compile(r"recurring_[0-9a-f]{64}")
_ACCOUNT_SUFFIX = re.compile(r"[0-9]{4}")


@dataclass(frozen=True, slots=True)
class FinanceEvidence:
    """Exact labeled source line supporting one finance field."""

    field: str
    line_number: int
    label: str

    def __post_init__(self) -> None:
        if not self.field or self.line_number < 1 or not self.label:
            raise ValueError("Finanzevidenz benötigt Feld, Zeilennummer und Label.")

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "line_number": self.line_number,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class FinanceTransactionCandidate:
    """One cent-exact booking bound to a statement line."""

    transaction_id: str
    booking_date: str
    amount_cents: int
    counterparty: str
    category: str
    booking_reference: str
    evidence: FinanceEvidence

    def __post_init__(self) -> None:
        if _TRANSACTION_ID.fullmatch(self.transaction_id) is None:
            raise ValueError("transaction_id muss transaction_<sha256> verwenden.")
        date.fromisoformat(self.booking_date)
        if not isinstance(self.amount_cents, int) or isinstance(self.amount_cents, bool):
            raise ValueError("amount_cents muss eine Ganzzahl sein.")
        if not self.counterparty or not self.category or not self.booking_reference:
            raise ValueError("Buchung benötigt Gegenüber, Kategorie und Referenz.")

    def to_dict(self) -> dict[str, object]:
        return {
            "transaction_id": self.transaction_id,
            "booking_date": self.booking_date,
            "amount_cents": self.amount_cents,
            "counterparty": self.counterparty,
            "category": self.category,
            "booking_reference": self.booking_reference,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class AccountStatementCandidate:
    """One internally consistent statement with immutable document provenance."""

    statement_id: str
    profile_id: str
    account_ref: str
    institution: str
    account_suffix: str
    period_start: str
    period_end: str
    opening_balance_cents: int
    closing_balance_cents: int
    currency: str
    transactions: tuple[FinanceTransactionCandidate, ...]
    source_document_id: str
    source_sha256: str
    source_path: Path
    evidence: tuple[FinanceEvidence, ...]

    SCHEMA = "folderhome.account-statement-candidate.v1"

    def __post_init__(self) -> None:
        if _STATEMENT_ID.fullmatch(self.statement_id) is None:
            raise ValueError("statement_id muss statement_<sha256> verwenden.")
        if _DOCUMENT_ID.fullmatch(self.source_document_id) is None:
            raise ValueError("source_document_id ist ungültig.")
        if _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("source_sha256 ist ungültig.")
        if _ACCOUNT_SUFFIX.fullmatch(self.account_suffix) is None:
            raise ValueError("Konto-Endung muss genau vier Ziffern enthalten.")
        start = date.fromisoformat(self.period_start)
        end = date.fromisoformat(self.period_end)
        if end < start:
            raise ValueError("Auszugszeitraum ist umgekehrt.")
        if self.currency != "EUR":
            raise ValueError("Auszugsformat V1 unterstützt ausschließlich EUR.")
        if not self.profile_id or not self.account_ref or not self.institution:
            raise ValueError("Auszug benötigt Profil, Kontokennung und Institut.")
        if not self.transactions:
            raise ValueError("Auszug benötigt mindestens eine Buchung.")
        if self.opening_balance_cents + sum(
            transaction.amount_cents for transaction in self.transactions
        ) != self.closing_balance_cents:
            raise ValueError("Saldo stimmt nicht mit den centgenauen Buchungen überein.")
        if len({item.booking_reference for item in self.transactions}) != len(
            self.transactions
        ):
            raise ValueError("Buchungsreferenzen müssen im Auszug eindeutig sein.")
        if any(
            not start <= date.fromisoformat(item.booking_date) <= end
            for item in self.transactions
        ):
            raise ValueError("Buchungsdatum liegt außerhalb des Auszugszeitraums.")
        object.__setattr__(self, "source_path", self.source_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "statement_id": self.statement_id,
            "profile_id": self.profile_id,
            "account_ref": self.account_ref,
            "institution": self.institution,
            "account_suffix": self.account_suffix,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "opening_balance_cents": self.opening_balance_cents,
            "closing_balance_cents": self.closing_balance_cents,
            "currency": self.currency,
            "transactions": [item.to_dict() for item in self.transactions],
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class StatementAnalysisItem:
    """One visible source-file outcome in folder statement analysis."""

    relative_path: str
    status: str
    statement: AccountStatementCandidate | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status,
            "statement": self.statement.to_dict() if self.statement else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderStatementAnalysis:
    """Read-only statement candidates for an explicit local folder."""

    source_root: Path
    profile_id: str
    items: tuple[StatementAnalysisItem, ...]

    SCHEMA = "folderhome.folder-statement-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    @property
    def statements(self) -> tuple[AccountStatementCandidate, ...]:
        return tuple(item.statement for item in self.items if item.statement is not None)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "source_root": str(self.source_root),
            "profile_id": self.profile_id,
            "statement_count": len(self.statements),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class FinanceImportAction:
    """One statement import decision."""

    action_id: str
    statement: AccountStatementCandidate
    status: str
    message: str

    def __post_init__(self) -> None:
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("action_id muss finance_action_<hex> verwenden.")
        if self.status not in {"planned", "noop", "blocked"}:
            raise ValueError("Finanzaktionsstatus ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "statement": self.statement.to_dict(),
            "status": self.status,
            "message": self.message,
            "side_effect": "local_finance_state" if self.status == "planned" else "none",
        }


@dataclass(frozen=True, slots=True)
class FinanceImportPlan:
    """Revision-bound statement plan with no write side effect."""

    plan_id: str
    finance_revision: str
    analysis: FolderStatementAnalysis
    actions: tuple[FinanceImportAction, ...]

    SCHEMA = "folderhome.finance-import-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss finance_plan_<sha256> verwenden.")
        if _REVISION.fullmatch(self.finance_revision) is None:
            raise ValueError("finance_revision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "finance_revision": self.finance_revision,
            "analysis": self.analysis.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "automatic_bank_access": False,
            "financial_advice": False,
        }


@dataclass(frozen=True, slots=True)
class FinanceImportApproval:
    """Exact user approval for selected new statement actions."""

    approval_id: str
    plan_id: str
    finance_revision: str
    action_ids: tuple[str, ...]
    approved_at: str

    SCHEMA = "folderhome.finance-import-approval.v1"

    def __post_init__(self) -> None:
        if _APPROVAL_ID.fullmatch(self.approval_id) is None:
            raise ValueError("approval_id ist ungültig.")
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id ist ungültig.")
        if _REVISION.fullmatch(self.finance_revision) is None:
            raise ValueError("finance_revision ist ungültig.")
        if not self.action_ids or len(self.action_ids) != len(set(self.action_ids)):
            raise ValueError("action_ids müssen nichtleer und eindeutig sein.")
        if any(_ACTION_ID.fullmatch(value) is None for value in self.action_ids):
            raise ValueError("action_ids enthalten eine ungültige ID.")
        _aware_datetime(self.approved_at)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "finance_revision": self.finance_revision,
            "action_ids": list(self.action_ids),
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class FinanceImportReport:
    """Audited result of one atomic local statement import."""

    report_id: str
    plan_id: str
    approval_id: str
    revision_before: str
    revision_after: str
    created_statement_ids: tuple[str, ...]
    created_transaction_ids: tuple[str, ...]
    state_path: Path
    status: str = "executed"

    SCHEMA = "folderhome.finance-import-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("report_id muss finance_report_<sha256> verwenden.")
        object.__setattr__(self, "state_path", self.state_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "revision_before": self.revision_before,
            "revision_after": self.revision_after,
            "created_statement_ids": list(self.created_statement_ids),
            "created_transaction_ids": list(self.created_transaction_ids),
            "state_path": str(self.state_path),
            "status": self.status,
            "bank_access_performed": False,
            "deleted_transaction_ids": [],
        }


@dataclass(frozen=True, slots=True)
class FinanceStatementRecord:
    statement_id: str
    profile_id: str
    account_ref: str
    institution: str
    account_suffix: str
    period_start: str
    period_end: str
    opening_balance_cents: int
    closing_balance_cents: int
    currency: str
    source_document_id: str
    source_sha256: str
    source_path: Path
    imported_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "statement_id": self.statement_id,
            "profile_id": self.profile_id,
            "account_ref": self.account_ref,
            "institution": self.institution,
            "account_suffix": self.account_suffix,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "opening_balance_cents": self.opening_balance_cents,
            "closing_balance_cents": self.closing_balance_cents,
            "currency": self.currency,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "imported_at": self.imported_at,
        }


@dataclass(frozen=True, slots=True)
class FinanceTransactionRecord:
    transaction_id: str
    statement_id: str
    profile_id: str
    account_ref: str
    booking_date: str
    amount_cents: int
    counterparty: str
    category: str
    booking_reference: str
    source_document_id: str
    source_sha256: str
    source_line: int

    def to_dict(self) -> dict[str, object]:
        return {
            "transaction_id": self.transaction_id,
            "statement_id": self.statement_id,
            "profile_id": self.profile_id,
            "account_ref": self.account_ref,
            "booking_date": self.booking_date,
            "amount_cents": self.amount_cents,
            "counterparty": self.counterparty,
            "category": self.category,
            "booking_reference": self.booking_reference,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_line": self.source_line,
        }


@dataclass(frozen=True, slots=True)
class DateRange:
    start_date: str
    end_date: str

    def __post_init__(self) -> None:
        if date.fromisoformat(self.end_date) < date.fromisoformat(self.start_date):
            raise ValueError("Datumsbereich ist umgekehrt.")

    def to_dict(self) -> dict[str, str]:
        return {"start_date": self.start_date, "end_date": self.end_date}


@dataclass(frozen=True, slots=True)
class FinanceCoverage:
    account_ref: str
    requested_range: DateRange
    covered_ranges: tuple[DateRange, ...]
    gaps: tuple[DateRange, ...]
    complete: bool
    balance_interpolated: bool = False

    SCHEMA = "folderhome.finance-coverage.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "account_ref": self.account_ref,
            "requested_range": self.requested_range.to_dict(),
            "covered_ranges": [item.to_dict() for item in self.covered_ranges],
            "gaps": [item.to_dict() for item in self.gaps],
            "complete": self.complete,
            "balance_interpolated": False,
        }


@dataclass(frozen=True, slots=True)
class FinancePeriodReport:
    """Account movements and balances limited to evidenced statement coverage."""

    account_ref: str
    date_from: str
    date_to: str
    coverage: FinanceCoverage
    statement_ids: tuple[str, ...]
    transactions: tuple[FinanceTransactionRecord, ...]
    opening_balance_cents: int | None
    closing_balance_cents: int | None
    balance_continuity_verified: bool

    SCHEMA = "folderhome.finance-period-report.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "account_ref": self.account_ref,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "coverage": self.coverage.to_dict(),
            "statement_ids": list(self.statement_ids),
            "transactions": [item.to_dict() for item in self.transactions],
            "opening_balance_cents": self.opening_balance_cents,
            "closing_balance_cents": self.closing_balance_cents,
            "balance_continuity_verified": self.balance_continuity_verified,
            "balance_interpolated": False,
        }


@dataclass(frozen=True, slots=True)
class RecurringCostCandidate:
    candidate_id: str
    profile_id: str
    account_ref: str
    counterparty: str
    cost_type: str
    interval: str
    status: str
    amount_cents: int
    monthly_cost_cents: int
    annualized_cost_cents: int
    first_booking_date: str
    last_booking_date: str
    next_expected_from: str
    next_expected_to: str
    transaction_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if _RECURRING_ID.fullmatch(self.candidate_id) is None:
            raise ValueError("Recurring-Candidate-ID ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "profile_id": self.profile_id,
            "account_ref": self.account_ref,
            "counterparty": self.counterparty,
            "cost_type": self.cost_type,
            "interval": self.interval,
            "status": self.status,
            "amount_cents": self.amount_cents,
            "monthly_cost_cents": self.monthly_cost_cents,
            "annualized_cost_cents": self.annualized_cost_cents,
            "first_booking_date": self.first_booking_date,
            "last_booking_date": self.last_booking_date,
            "next_expected_from": self.next_expected_from,
            "next_expected_to": self.next_expected_to,
            "transaction_ids": list(self.transaction_ids),
            "contract_status_proven": False,
        }


@dataclass(frozen=True, slots=True)
class RecurringCostReport:
    profile_id: str
    as_of: str
    candidates: tuple[RecurringCostCandidate, ...]
    contract_status_proven: bool = False

    SCHEMA = "folderhome.recurring-cost-report.v1"

    def __post_init__(self) -> None:
        date.fromisoformat(self.as_of)

    @property
    def total_monthly_cost_cents(self) -> int:
        return sum(item.monthly_cost_cents for item in self.candidates)

    @property
    def total_annualized_cost_cents(self) -> int:
        return sum(item.annualized_cost_cents for item in self.candidates)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "profile_id": self.profile_id,
            "as_of": self.as_of,
            "candidates": [item.to_dict() for item in self.candidates],
            "total_monthly_cost_cents": self.total_monthly_cost_cents,
            "total_annualized_cost_cents": self.total_annualized_cost_cents,
            "contract_status_proven": False,
            "prediction_is_guarantee": False,
        }


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Zeitpunkt ist ungültig: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError("Zeitpunkt benötigt eine Zeitzone.")
    return parsed
