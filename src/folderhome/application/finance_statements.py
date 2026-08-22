"""Analyze statement documents and build local recurring-cost evidence."""

from __future__ import annotations

import calendar
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.finance_store import FinanceStore, FinanceStoreError
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    AccountStatementCandidate,
    DocumentRecord,
    FinanceEvidence,
    FinanceImportAction,
    FinanceImportApproval,
    FinanceImportPlan,
    FinanceImportReport,
    FinanceTransactionCandidate,
    FolderStatementAnalysis,
    PrivacyStatus,
    RecurringCostCandidate,
    RecurringCostReport,
    StatementAnalysisItem,
)

_LINE = re.compile(r"^\s*([^:]{1,48}):\s*(\S(?:.*\S)?)\s*$")
_LABELS = {
    "kontokennung": "account_ref",
    "institut": "institution",
    "konto-endung": "account_suffix",
    "zeitraum": "period",
    "anfangssaldo": "opening_balance",
    "endsaldo": "closing_balance",
}


class FinanceWorkflowError(RuntimeError):
    """Raised when finance evidence or execution state is unsafe."""


class StatementDocumentExtractor(Protocol):
    def extract(self, source_path: Path) -> DocumentRecord: ...


def analyze_folder_statements(
    source_dir: Path,
    *,
    profile_id: str,
    extractor: StatementDocumentExtractor,
    recursive: bool = True,
    allow_sensitive_local_read: bool = False,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderStatementAnalysis:
    """Analyze visible statement files without writing finance state."""

    root = source_dir.resolve()
    if root.is_symlink() or not root.is_dir():
        raise FinanceWorkflowError(f"Auszugsordner fehlt oder ist ein Link: {root}")
    try:
        inventory = inventory_files(root, recursive=recursive, policy=resource_policy)
    except (ResourceLimitExceeded, ValueError) as exc:
        raise FinanceWorkflowError(str(exc)) from exc
    paths = inventory.all_paths
    items = []
    text_budget = ResourceBudget(resource_policy)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            items.append(
                StatementAnalysisItem(
                    relative,
                    "skipped",
                    None,
                    "Symbolischer Link ausgelassen.",
                )
            )
            continue
        try:
            document = extractor.extract(path)
            text_budget.consume_extracted_text(len(document.text))
            statement, status, message = _analyze_document(
                document,
                profile_id=profile_id,
                allow_sensitive_local_read=allow_sensitive_local_read,
            )
            items.append(StatementAnalysisItem(relative, status, statement, message))
        except UnsupportedDocumentError as exc:
            items.append(StatementAnalysisItem(relative, "skipped", None, str(exc)))
        except DocServicesBridgeError as exc:
            items.append(StatementAnalysisItem(relative, "failed", None, str(exc)))
        except ResourceLimitExceeded as exc:
            raise FinanceWorkflowError(str(exc)) from exc
    return FolderStatementAnalysis(root, profile_id, tuple(items))


def build_finance_import_plan(
    analysis: FolderStatementAnalysis,
    *,
    store: FinanceStore,
) -> FinanceImportPlan:
    """Plan new statement imports against current immutable finance state."""

    revision = store.revision()
    existing_statement_ids = {item.statement_id for item in store.list_statements()}
    existing_references = store.booking_references()
    incoming_references = Counter(
        (statement.account_ref, transaction.booking_reference)
        for statement in analysis.statements
        for transaction in statement.transactions
    )
    incoming_ids = {statement.statement_id for statement in analysis.statements}
    continuity_conflicts: set[str] = set()
    by_account = defaultdict(list)
    for statement in (*store.list_statements(), *analysis.statements):
        by_account[statement.account_ref].append(statement)
    for statements in by_account.values():
        ordered = sorted(statements, key=lambda item: (item.period_start, item.statement_id))
        for first, second in zip(ordered, ordered[1:], strict=False):
            if (
                date.fromisoformat(second.period_start)
                == date.fromisoformat(first.period_end) + timedelta(days=1)
                and first.closing_balance_cents != second.opening_balance_cents
            ):
                continuity_conflicts.update(
                    statement_id
                    for statement_id in (first.statement_id, second.statement_id)
                    if statement_id in incoming_ids
                )
    actions = []
    for statement in sorted(analysis.statements, key=lambda item: item.statement_id):
        if statement.statement_id in existing_statement_ids:
            status = "noop"
            message = "Identischer Kontoauszug ist bereits importiert."
        elif statement.statement_id in continuity_conflicts:
            status = "blocked"
            message = "Saldo ist zu einem angrenzenden Auszug nicht kontinuierlich."
        elif any(
            incoming_references[(statement.account_ref, transaction.booking_reference)] > 1
            for transaction in statement.transactions
        ):
            status = "blocked"
            message = "Buchungsreferenz erscheint in mehreren neuen Auszügen."
        elif any(
            (statement.account_ref, transaction.booking_reference) in existing_references
            for transaction in statement.transactions
        ):
            status = "blocked"
            message = "Buchungsreferenz ist im Finanz-State bereits belegt."
        else:
            status = "planned"
            message = "Centgenauen Auszug nach separater State-Freigabe importieren."
        material = {
            "revision": revision,
            "statement_id": statement.statement_id,
            "status": status,
        }
        actions.append(
            FinanceImportAction(
                action_id=f"finance_action_{_json_hash(material)[:32]}",
                statement=statement,
                status=status,
                message=message,
            )
        )
    action_tuple = tuple(actions)
    payload = {
        "schema": FinanceImportPlan.SCHEMA,
        "finance_revision": revision,
        "analysis": analysis.to_dict(),
        "actions": [action.to_dict() for action in action_tuple],
    }
    return FinanceImportPlan(
        plan_id=f"finance_plan_{_json_hash(payload)}",
        finance_revision=revision,
        analysis=analysis,
        actions=action_tuple,
    )


def apply_finance_import_plan(
    plan: FinanceImportPlan,
    approval: FinanceImportApproval,
    *,
    store: FinanceStore,
    allow_state_write: bool,
) -> FinanceImportReport:
    """Recheck source/revision and atomically append selected statements."""

    if not allow_state_write:
        raise FinanceWorkflowError("Finanzimport benötigt eine State-Freigabe.")
    if approval.plan_id != plan.plan_id:
        raise FinanceWorkflowError("Finanzfreigabe gehört nicht zu diesem Plan.")
    if approval.finance_revision != plan.finance_revision:
        raise FinanceWorkflowError("Finanzfreigabe bindet eine andere Revision.")
    action_by_id = {action.action_id: action for action in plan.actions}
    try:
        selected = tuple(action_by_id[action_id] for action_id in approval.action_ids)
    except KeyError as exc:
        raise FinanceWorkflowError(
            f"Finanzfreigabe enthält eine unbekannte Aktion: {exc.args[0]}"
        ) from exc
    if any(action.status != "planned" for action in selected):
        raise FinanceWorkflowError("Nur geplante Finanzaktionen dürfen ausgeführt werden.")
    try:
        store.validate_execution(
            expected_revision=plan.finance_revision,
            approval_id=approval.approval_id,
        )
    except FinanceStoreError as exc:
        raise FinanceWorkflowError(str(exc)) from exc
    for action in selected:
        _verify_source(action.statement)
    try:
        statement_ids, transaction_ids, revision_after = store.apply(
            expected_revision=plan.finance_revision,
            actions=selected,
            approval=approval,
        )
    except FinanceStoreError as exc:
        raise FinanceWorkflowError(str(exc)) from exc
    payload = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "statement_ids": list(statement_ids),
        "transaction_ids": list(transaction_ids),
        "revision_after": revision_after,
    }
    return FinanceImportReport(
        report_id=f"finance_report_{_json_hash(payload)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        revision_before=plan.finance_revision,
        revision_after=revision_after,
        created_statement_ids=statement_ids,
        created_transaction_ids=transaction_ids,
        state_path=store.path,
    )


def build_recurring_cost_report(
    *,
    store: FinanceStore,
    profile_id: str,
    as_of: str,
) -> RecurringCostReport:
    """Find conservative monthly repeated debit candidates from local evidence."""

    as_of_date = date.fromisoformat(as_of)
    grouped = defaultdict(list)
    for transaction in store.list_transactions(profile_id=profile_id):
        if transaction.amount_cents >= 0:
            continue
        key = (
            transaction.account_ref,
            _normalize_counterparty(transaction.counterparty),
            transaction.amount_cents,
            transaction.category.casefold(),
        )
        grouped[key].append(transaction)
    candidates = []
    for (account_ref, _, amount_cents, category), transactions in grouped.items():
        ordered = sorted(transactions, key=lambda item: item.booking_date)
        if len(ordered) < 2:
            continue
        booking_dates = [date.fromisoformat(item.booking_date) for item in ordered]
        if any(
            not 25 <= (second - first).days <= 35
            for first, second in zip(booking_dates, booking_dates[1:], strict=False)
        ):
            continue
        last = booking_dates[-1]
        if as_of_date < last:
            raise FinanceWorkflowError("Abo-Stichtag liegt vor der letzten Buchung.")
        expected = _add_month(last)
        status = (
            "active_candidate"
            if as_of_date <= expected + timedelta(days=7)
            else "inactive_candidate"
        )
        transaction_ids = tuple(item.transaction_id for item in ordered)
        material = {
            "profile_id": profile_id,
            "account_ref": account_ref,
            "transaction_ids": list(transaction_ids),
        }
        candidates.append(
            RecurringCostCandidate(
                candidate_id=f"recurring_{_json_hash(material)}",
                profile_id=profile_id,
                account_ref=account_ref,
                counterparty=ordered[0].counterparty,
                cost_type=category,
                interval="monthly",
                status=status,
                amount_cents=abs(amount_cents),
                monthly_cost_cents=abs(amount_cents),
                annualized_cost_cents=abs(amount_cents) * 12,
                first_booking_date=ordered[0].booking_date,
                last_booking_date=ordered[-1].booking_date,
                next_expected_from=(expected - timedelta(days=3)).isoformat(),
                next_expected_to=(expected + timedelta(days=3)).isoformat(),
                transaction_ids=transaction_ids,
            )
        )
    return RecurringCostReport(
        profile_id=profile_id,
        as_of=as_of,
        candidates=tuple(sorted(candidates, key=lambda item: item.candidate_id)),
    )


def _analyze_document(
    document: DocumentRecord,
    *,
    profile_id: str,
    allow_sensitive_local_read: bool,
) -> tuple[AccountStatementCandidate | None, str, str]:
    if document.privacy_status in {PrivacyStatus.BLOCKED, PrivacyStatus.NOT_CHECKED}:
        return None, "blocked", "Datenschutzstatus blockiert die Finanzanalyse."
    if (
        document.privacy_status is PrivacyStatus.REVIEW_REQUIRED
        and not allow_sensitive_local_read
    ):
        return None, "review_required", "Lokale sensible Finanzanalyse benötigt Freigabe."
    fields: dict[str, tuple[str, int, str]] = {}
    transactions_raw: list[tuple[str, int, str]] = []
    try:
        for line_number, line in enumerate(document.text.splitlines(), start=1):
            match = _LINE.fullmatch(line)
            if match is None:
                continue
            label, value = match.groups()
            normalized = label.strip().casefold()
            if normalized == "buchung":
                transactions_raw.append((value.strip(), line_number, label.strip()))
                continue
            field = _LABELS.get(normalized)
            if field is None:
                continue
            if field in fields:
                raise ValueError(f"Feld {field} ist mehrfach vorhanden.")
            fields[field] = (value.strip(), line_number, label.strip())
        missing = sorted(set(_LABELS.values()).difference(fields))
        if missing:
            raise ValueError(f"Pflichtfeld {missing[0]} fehlt.")
        account_ref = fields["account_ref"][0]
        period_start, period_end = _pipe(fields["period"][0], 2)
        opening_text, opening_currency = _pipe(fields["opening_balance"][0], 2)
        closing_text, closing_currency = _pipe(fields["closing_balance"][0], 2)
        if opening_currency != closing_currency:
            raise ValueError("Saldo-Währungen widersprechen sich.")
        transactions = []
        for raw, line_number, label in transactions_raw:
            booking_date, amount, counterparty, category, reference = _pipe(raw, 5)
            transaction_payload = {
                "account_ref": account_ref,
                "booking_reference": reference,
            }
            transactions.append(
                FinanceTransactionCandidate(
                    transaction_id=f"transaction_{_json_hash(transaction_payload)}",
                    booking_date=booking_date,
                    amount_cents=_cent_int(amount),
                    counterparty=counterparty,
                    category=category,
                    booking_reference=reference,
                    evidence=FinanceEvidence("transaction", line_number, label),
                )
            )
        evidence = tuple(
            FinanceEvidence(field, value[1], value[2])
            for field, value in sorted(fields.items())
        )
        statement_payload = {
            "profile_id": profile_id,
            "account_ref": account_ref,
            "period_start": period_start,
            "period_end": period_end,
            "source_document_id": document.document_id,
            "transactions": [item.transaction_id for item in transactions],
        }
        statement = AccountStatementCandidate(
            statement_id=f"statement_{_json_hash(statement_payload)}",
            profile_id=profile_id,
            account_ref=account_ref,
            institution=fields["institution"][0],
            account_suffix=fields["account_suffix"][0],
            period_start=period_start,
            period_end=period_end,
            opening_balance_cents=_cent_int(opening_text),
            closing_balance_cents=_cent_int(closing_text),
            currency=opening_currency,
            transactions=tuple(transactions),
            source_document_id=document.document_id,
            source_sha256=document.source_sha256,
            source_path=document.source_path,
            evidence=evidence,
        )
        return statement, "candidate", "Centgenauer Auszug mit Zeilenevidenz erkannt."
    except (KeyError, TypeError, ValueError) as exc:
        return None, "review_required", str(exc)


def _verify_source(statement: AccountStatementCandidate) -> None:
    source = statement.source_path
    if source.is_symlink() or not source.is_file():
        raise FinanceWorkflowError(f"Auszugsquelle fehlt oder ist kein reguläres File: {source}")
    digest = sha256()
    try:
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise FinanceWorkflowError(f"Auszugsquelle ist nicht lesbar: {source}: {exc}") from exc
    if digest.hexdigest() != statement.source_sha256:
        raise FinanceWorkflowError(f"Quellhash hat sich seit der Planung verändert: {source}")


def _pipe(value: str, count: int) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in value.split("|"))
    if len(parts) != count or any(not part for part in parts):
        raise ValueError(f"Erwartet werden {count} nichtleere, mit | getrennte Werte.")
    return parts


def _cent_int(value: str) -> int:
    if re.fullmatch(r"-?[0-9]+", value) is None:
        raise ValueError("Finanzbeträge müssen als ganzzahlige Cent angegeben werden.")
    return int(value)


def _normalize_counterparty(value: str) -> str:
    return " ".join(value.casefold().split())


def _add_month(value: date) -> date:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()
