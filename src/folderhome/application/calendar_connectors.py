"""Plan explicit calendar connector routes on top of the Phase-17 handoff."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from folderhome.capabilities.calendar_connector_gateway import (
    CalendarConnectorGatewayError,
)
from folderhome.contracts.calendar import CalendarBackend, CalendarCandidate, CalendarHandoffPlan
from folderhome.contracts.calendar_connectors import (
    CalendarConnectorAccount,
    CalendarConnectorAction,
    CalendarConnectorApproval,
    CalendarConnectorEvent,
    CalendarConnectorExecutionReport,
    CalendarConnectorOperation,
    CalendarConnectorPlan,
    CalendarConnectorRequest,
    CalendarConnectorRoute,
    CalendarProviderEventReference,
    CalendarReminderSpec,
)


class CalendarConnectorError(RuntimeError):
    """Raised when a connector route, request, or approval is unsafe."""


class CalendarConnectorGateway(Protocol):
    provider_id: str
    provider_revision: str | None
    network_required: bool
    simulated: bool

    def create_event(
        self,
        event: CalendarConnectorEvent,
        *,
        idempotency_key: str,
    ) -> str: ...


def load_calendar_connector_accounts(path: Path) -> tuple[CalendarConnectorAccount, ...]:
    payload = _load_json_object(path, "Kalenderconnectorkonten")
    _strict_fields(payload, {"schema", "accounts"}, "Kalenderconnectorkonten")
    if payload.get("schema") != "folderhome.calendar-connector-accounts.v1":
        raise CalendarConnectorError(
            "Kalenderconnectorkonten verwenden ein unbekanntes Schema."
        )
    raw_accounts = payload.get("accounts")
    if not isinstance(raw_accounts, list) or not raw_accounts:
        raise CalendarConnectorError(
            "Kalenderconnectorkonten benötigen eine nichtleere accounts-Liste."
        )
    accounts = tuple(
        _parse_account(item, index) for index, item in enumerate(raw_accounts)
    )
    ids = [item.account_id for item in accounts]
    if len(ids) != len(set(ids)):
        raise CalendarConnectorError("Kalenderconnectorkonto-IDs müssen eindeutig sein.")
    return accounts


def load_calendar_connector_request(path: Path) -> CalendarConnectorRequest:
    payload = _load_json_object(path, "Kalenderconnector-Anfrage")
    _strict_fields(
        payload,
        {"schema", "request_id", "profile_id", "account_id", "operations", "reminders"},
        "Kalenderconnector-Anfrage",
    )
    if payload.get("schema") != CalendarConnectorRequest.SCHEMA:
        raise CalendarConnectorError(
            "Kalenderconnector-Anfrage verwendet ein unbekanntes Schema."
        )
    raw_operations = payload.get("operations")
    raw_reminders = payload.get("reminders")
    if not isinstance(raw_operations, list) or not all(
        isinstance(item, str) for item in raw_operations
    ):
        raise CalendarConnectorError("Kalenderconnector-Anfrage benötigt Operationen.")
    if not isinstance(raw_reminders, list):
        raise CalendarConnectorError("Kalenderconnector-Anfrage benötigt Erinnerungen.")
    try:
        operations = tuple(CalendarConnectorOperation(item) for item in raw_operations)
        reminders = tuple(
            _parse_reminder(item, index) for index, item in enumerate(raw_reminders)
        )
        return CalendarConnectorRequest(
            request_id=_text(payload, "request_id", "Kalenderconnector-Anfrage"),
            profile_id=_text(payload, "profile_id", "Kalenderconnector-Anfrage"),
            account_id=_text(payload, "account_id", "Kalenderconnector-Anfrage"),
            operations=operations,
            reminders=reminders,
        )
    except ValueError as exc:
        raise CalendarConnectorError(
            f"Kalenderconnector-Anfrage ist ungültig: {exc}"
        ) from exc


def build_calendar_connector_plan(
    handoff: CalendarHandoffPlan,
    *,
    request: CalendarConnectorRequest,
    account: CalendarConnectorAccount,
    provider_ready: bool,
    synthetic_override: bool = False,
) -> CalendarConnectorPlan:
    """Route a Phase-17 handoff without invoking a calendar connector."""

    if handoff.analysis.profile_id != request.profile_id:
        raise CalendarConnectorError("Kalenderhandoff und Connector-Anfrage nutzen andere Profile.")
    if account.profile_id != request.profile_id or account.account_id != request.account_id:
        raise CalendarConnectorError("Kalenderkonto passt nicht zur Connector-Anfrage.")
    if account.backend is not handoff.backend:
        raise CalendarConnectorError(
            "Kalenderkonto weicht vom durch Konfiguration und Profil aufgelösten Backend ab."
        )
    route = _build_route(account, provider_ready=provider_ready, synthetic=synthetic_override)
    events = tuple(
        _build_event(action.candidate, action.action_id, account, request.reminders)
        for action in handoff.actions
    )
    actions = tuple(
        _build_action(
            event,
            operation,
            backend=handoff.backend,
            source_status=source_action.status,
            provider_ready=provider_ready,
            synthetic=synthetic_override,
        )
        for source_action, event in zip(handoff.actions, events, strict=True)
        for operation in request.operations
    )
    if any(item.status == "blocked" for item in actions):
        status = "blocked"
    elif any(item.status == "review_required" for item in actions):
        status = "review_required"
    else:
        status = "ready"
    material = {
        "handoff_plan_id": handoff.plan_id,
        "request": request.to_dict(),
        "account": account.to_dict(),
        "backend_source": handoff.backend_source,
        "source_rule_ids": list(handoff.source_rule_ids),
        "route": route.to_dict(),
        "events": [item.to_dict() for item in events],
        "actions": [item.to_dict() for item in actions],
        "status": status,
    }
    plan_sha256 = _json_hash(material)
    return CalendarConnectorPlan(
        plan_id=f"calendar_connector_plan_{plan_sha256}",
        plan_sha256=plan_sha256,
        handoff_plan_id=handoff.plan_id,
        profile_id=request.profile_id,
        account_id=account.account_id,
        backend=handoff.backend,
        backend_source=handoff.backend_source,
        source_rule_ids=handoff.source_rule_ids,
        route=route,
        events=events,
        actions=actions,
        status=status,
    )


def execute_calendar_connector_plan(
    plan: CalendarConnectorPlan,
    *,
    approval: CalendarConnectorApproval,
    gateway: CalendarConnectorGateway,
) -> CalendarConnectorExecutionReport:
    """Execute only exact planned create/remind actions through one bound gateway."""

    if plan.status != "ready":
        raise CalendarConnectorError(
            "Nur ein bereiter Kalenderconnector-Plan darf ausgeführt werden."
        )
    if approval.plan_id != plan.plan_id or approval.plan_sha256 != plan.plan_sha256:
        raise CalendarConnectorError("Kalenderconnector-Freigabe bindet einen anderen Plan.")
    if (
        gateway.provider_id != plan.route.provider_id
        or gateway.provider_revision != plan.route.provider_revision
    ):
        raise CalendarConnectorError(
            "Kalendergateway stimmt nicht mit dem freigegebenen Provider überein."
        )
    if gateway.network_required and not approval.allow_network_write:
        raise CalendarConnectorError("Netzwerk-Kalenderfreigabe fehlt.")
    action_by_id = {item.action_id: item for item in plan.actions}
    try:
        selected = tuple(action_by_id[item] for item in approval.action_ids)
    except KeyError as exc:
        raise CalendarConnectorError(
            f"Kalenderconnector-Freigabe enthält eine unbekannte Aktion: {exc.args[0]}"
        ) from exc
    if any(item.status != "planned" for item in selected):
        raise CalendarConnectorError("Nur geplante Connectoraktionen dürfen laufen.")
    selected_operations = tuple(dict.fromkeys(item.operation for item in selected))
    if set(selected_operations) != set(approval.allowed_operations):
        raise CalendarConnectorError(
            "Kalenderconnector-Freigabe bindet andere Operationen als ihre Aktionen."
        )
    by_event: dict[str, set[CalendarConnectorOperation]] = {}
    for action in selected:
        by_event.setdefault(action.event_uid, set()).add(action.operation)
    if any(
        CalendarConnectorOperation.CREATE not in operations
        for operations in by_event.values()
    ):
        raise CalendarConnectorError(
            "Erinnern, Aktualisieren oder Löschen ist ohne freigegebene Erstellung blockiert."
        )
    event_by_uid = {item.event_uid: item for item in plan.events}
    references = []
    try:
        for event_uid, operations in sorted(by_event.items()):
            if operations.difference(
                {CalendarConnectorOperation.CREATE, CalendarConnectorOperation.REMIND}
            ):
                raise CalendarConnectorError(
                    "Dieser Connectorlauf unterstützt nur Erstellung und Erinnerung."
                )
            event = event_by_uid[event_uid]
            if CalendarConnectorOperation.REMIND not in operations:
                event = replace(event, reminders=())
            idempotency_key = _json_hash(
                {
                    "plan_id": plan.plan_id,
                    "event_uid": event_uid,
                    "operations": sorted(item.value for item in operations),
                }
            )
            provider_event_id = gateway.create_event(
                event,
                idempotency_key=idempotency_key,
            )
            payload_sha256 = _json_hash(event.to_dict())
            reference_material = {
                "event_uid": event_uid,
                "account_id": plan.account_id,
                "calendar_id": event.calendar_id,
                "provider_id": gateway.provider_id,
                "provider_event_id": provider_event_id,
                "payload_sha256": payload_sha256,
            }
            references.append(
                CalendarProviderEventReference(
                    reference_id=(
                        f"calendar_provider_event_{_json_hash(reference_material)}"
                    ),
                    event_uid=event_uid,
                    account_id=plan.account_id,
                    calendar_id=event.calendar_id,
                    provider_id=gateway.provider_id,
                    provider_event_id=provider_event_id,
                    payload_sha256=payload_sha256,
                )
            )
    except CalendarConnectorGatewayError as exc:
        raise CalendarConnectorError(str(exc)) from exc
    status = "simulated" if gateway.simulated else "executed"
    report_material = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "references": [item.to_dict() for item in references],
    }
    return CalendarConnectorExecutionReport(
        report_id=f"calendar_connector_report_{_json_hash(report_material)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        provider_id=gateway.provider_id,
        provider_revision=gateway.provider_revision,
        status=status,
        event_references=tuple(references),
        network_invoked=gateway.network_required,
        live_calendar_written=not gateway.simulated,
    )


def _build_route(
    account: CalendarConnectorAccount,
    *,
    provider_ready: bool,
    synthetic: bool,
) -> CalendarConnectorRoute:
    if synthetic:
        return CalendarConnectorRoute(
            backend=account.backend,
            provider_id="folderhome.synthetic-calendar",
            provider_revision=None,
            status="ready",
            reason="Synthetischer No-Network-Provider ist für die lokale Abnahme bereit.",
            supported_operations=(
                CalendarConnectorOperation.CREATE,
                CalendarConnectorOperation.REMIND,
            ),
            live_supported=False,
        )
    supported = {
        CalendarBackend.FOLDERHOME_LOCAL: (CalendarConnectorOperation.CREATE,),
        CalendarBackend.UPTODAY_ICS: (CalendarConnectorOperation.CREATE,),
        CalendarBackend.ROUTINIKA: (CalendarConnectorOperation.CREATE,),
        CalendarBackend.GOOGLE: tuple(CalendarConnectorOperation),
    }[account.backend]
    if account.backend is CalendarBackend.GOOGLE:
        status = "review_required" if provider_ready else "blocked"
        reason = (
            "Google-Calendar-Skill ist verfügbar; jede Mutation bleibt gesondert freizugeben."
            if provider_ready
            else "Google-Calendar-Connector ist nicht nachweisbar verfügbar."
        )
        live_supported = provider_ready
    elif account.backend is CalendarBackend.UPTODAY_ICS:
        status = "ready" if provider_ready else "blocked"
        reason = (
            "Vorhandener Phase-17-ICS-Handoff wird ohne Live-Sync wiederverwendet."
            if provider_ready
            else "UpToday-Revision ist nicht sauber nachweisbar verfügbar."
        )
        live_supported = False
    elif account.backend is CalendarBackend.FOLDERHOME_LOCAL:
        status = "ready"
        reason = "Vorhandener lokaler Phase-17-Kalenderstore wird wiederverwendet."
        live_supported = False
    else:
        status = "blocked"
        reason = "Routinika besitzt nur einen dateibasierten Bundle-Vertrag, keinen Live-Connector."
        live_supported = False
    return CalendarConnectorRoute(
        backend=account.backend,
        provider_id=account.provider_id,
        provider_revision=account.provider_revision,
        status=status,
        reason=reason,
        supported_operations=supported,
        live_supported=live_supported,
    )


def _build_event(
    candidate: CalendarCandidate,
    source_action_id: str,
    account: CalendarConnectorAccount,
    reminders: tuple[CalendarReminderSpec, ...],
) -> CalendarConnectorEvent:
    if candidate.all_day:
        start = candidate.event_date
        end = (date.fromisoformat(candidate.event_date) + timedelta(days=1)).isoformat()
    else:
        assert candidate.start_time is not None
        start_dt = datetime.fromisoformat(
            f"{candidate.event_date}T{candidate.start_time}:00"
        ).replace(tzinfo=ZoneInfo(candidate.timezone))
        start = start_dt.isoformat()
        if candidate.end_time is None:
            end = None
        else:
            end = datetime.fromisoformat(
                f"{candidate.event_date}T{candidate.end_time}:00"
            ).replace(tzinfo=ZoneInfo(candidate.timezone)).isoformat()
    return CalendarConnectorEvent(
        event_uid=candidate.event_uid,
        profile_id=candidate.profile_id,
        calendar_id=account.calendar_id,
        title=candidate.title,
        start=start,
        end=end,
        timezone=candidate.timezone,
        all_day=candidate.all_day,
        location=candidate.location,
        attendees=(),
        transparency="opaque",
        reminders=reminders,
        source_handoff_action_id=source_action_id,
    )


def _build_action(
    event: CalendarConnectorEvent,
    operation: CalendarConnectorOperation,
    *,
    backend: CalendarBackend,
    source_status: str,
    provider_ready: bool,
    synthetic: bool,
) -> CalendarConnectorAction:
    delegated = False
    if operation in {
        CalendarConnectorOperation.UPDATE,
        CalendarConnectorOperation.DELETE,
    }:
        status = "blocked"
        reason = (
            "Update und Löschen benötigen zuerst eine bestehende Provider-Ereignisreferenz."
        )
    elif event.end is None and operation is CalendarConnectorOperation.CREATE:
        status = "blocked"
        reason = "Connector-Erstellung benötigt eine belegte Endzeit."
    elif synthetic:
        status = "planned"
        reason = "Synthetische Connectoraktion ist ohne Netzwerk ausführbar."
    elif backend in {CalendarBackend.UPTODAY_ICS, CalendarBackend.FOLDERHOME_LOCAL}:
        if operation is CalendarConnectorOperation.CREATE and source_status == "planned":
            status = "delegated"
            delegated = True
            reason = "Erstellung bleibt beim bereits freigegebenen Phase-17-Handoff."
        else:
            status = "blocked"
            reason = "Dieses lokale Backend besitzt keinen geprüften Reminder-Connector."
    elif backend is CalendarBackend.GOOGLE and provider_ready:
        status = "review_required"
        reason = "Google-Operation benötigt eine exakte gesonderte Connectorfreigabe."
    elif backend is CalendarBackend.GOOGLE:
        status = "blocked"
        reason = "Google-Calendar-Connector ist nicht verfügbar."
    else:
        status = "blocked"
        reason = "Routinika besitzt keinen geprüften Live-Connector."
    material = {
        "event_uid": event.event_uid,
        "source_handoff_action_id": event.source_handoff_action_id,
        "operation": operation.value,
        "status": status,
    }
    return CalendarConnectorAction(
        action_id=f"calendar_connector_action_{_json_hash(material)}",
        event_uid=event.event_uid,
        source_handoff_action_id=event.source_handoff_action_id,
        operation=operation,
        status=status,
        reason=reason,
        delegated_to_existing_handoff=delegated,
    )


def _parse_account(raw: object, index: int) -> CalendarConnectorAccount:
    label = f"Kalenderconnectorkonto {index + 1}"
    if not isinstance(raw, dict):
        raise CalendarConnectorError(f"{label} muss ein Objekt sein.")
    _strict_fields(
        raw,
        {
            "account_id",
            "profile_id",
            "backend",
            "display_name",
            "provider_id",
            "provider_revision",
            "calendar_id",
            "credential_ref",
        },
        label,
    )
    try:
        return CalendarConnectorAccount(
            account_id=_text(raw, "account_id", label),
            profile_id=_text(raw, "profile_id", label),
            backend=CalendarBackend(_text(raw, "backend", label)),
            display_name=_text(raw, "display_name", label),
            provider_id=_text(raw, "provider_id", label),
            provider_revision=_text(raw, "provider_revision", label),
            calendar_id=_text(raw, "calendar_id", label),
            credential_ref=_optional_text(raw, "credential_ref", label),
        )
    except ValueError as exc:
        raise CalendarConnectorError(f"{label} ist ungültig: {exc}") from exc


def _parse_reminder(raw: object, index: int) -> CalendarReminderSpec:
    label = f"Kalendererinnerung {index + 1}"
    if not isinstance(raw, dict):
        raise CalendarConnectorError(f"{label} muss ein Objekt sein.")
    _strict_fields(raw, {"method", "minutes_before"}, label)
    return CalendarReminderSpec(
        method=_text(raw, "method", label),
        minutes_before=_integer(raw, "minutes_before", label),
    )


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise CalendarConnectorError(f"{label} fehlt oder ist kein reguläres File: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CalendarConnectorError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise CalendarConnectorError(f"{label} muss ein JSON-Objekt sein.")
    return payload


def _strict_fields(payload: dict[str, object], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload).difference(allowed))
    missing = sorted(allowed.difference(payload))
    if unknown:
        raise CalendarConnectorError(
            f"{label} enthält unbekannte Felder: {', '.join(unknown)}"
        )
    if missing:
        raise CalendarConnectorError(f"{label} benötigt Felder: {', '.join(missing)}")


def _text(payload: dict[str, object], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CalendarConnectorError(f"{label}.{key} muss nichtleerer Text sein.")
    return value


def _optional_text(payload: dict[str, object], key: str, label: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CalendarConnectorError(f"{label}.{key} muss Text oder null sein.")
    return value


def _integer(payload: dict[str, object], key: str, label: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CalendarConnectorError(f"{label}.{key} muss eine Ganzzahl sein.")
    return value


def _json_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
