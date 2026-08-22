"""Contracts for explicit calendar connector routes and reminders."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from folderhome.contracts.calendar import CalendarBackend

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_PROVIDER_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{1,95}")
_PROVIDER_REVISION = re.compile(r"[^\s\r\n]{1,160}")
_PLAN_ID = re.compile(r"calendar_connector_plan_[0-9a-f]{64}")
_PLAN_SHA = re.compile(r"[0-9a-f]{64}")
_ACTION_ID = re.compile(r"calendar_connector_action_[0-9a-f]{64}")
_HANDOFF_PLAN_ID = re.compile(r"calendar_plan_[0-9a-f]{64}")
_HANDOFF_ACTION_ID = re.compile(r"calendar_action_[0-9a-f]{32}")
_EVENT_UID = re.compile(r"[0-9a-f]{64}@folderhome\.local")
_REPORT_ID = re.compile(r"calendar_connector_report_[0-9a-f]{64}")
_EVENT_REF_ID = re.compile(r"calendar_provider_event_[0-9a-f]{64}")
_CREDENTIAL_REF = re.compile(r"connector://[^\s]{3,240}")


def _timestamp(value: str, *, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} benötigt eine Zeitzone.")


class CalendarConnectorOperation(StrEnum):
    """Calendar effects approved independently."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REMIND = "remind"


@dataclass(frozen=True, slots=True)
class CalendarConnectorAccount:
    account_id: str
    profile_id: str
    backend: CalendarBackend
    display_name: str
    provider_id: str
    provider_revision: str
    calendar_id: str
    credential_ref: str | None

    SCHEMA = "folderhome.calendar-connector-account.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.account_id) is None:
            raise ValueError("Kalenderkonto-ID ist ungültig.")
        if not self.profile_id.strip() or not self.display_name.strip():
            raise ValueError("Kalenderkonto benötigt Profil und Bezeichnung.")
        if _PROVIDER_ID.fullmatch(self.provider_id) is None or _PROVIDER_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("Kalenderkonto besitzt ungültige Provideridentität.")
        if not self.calendar_id.strip() or any(char in self.calendar_id for char in "\r\n"):
            raise ValueError("Kalenderkonto benötigt eine explizite Kalender-ID.")
        if self.credential_ref is not None and _CREDENTIAL_REF.fullmatch(
            self.credential_ref
        ) is None:
            raise ValueError("Kalenderkonto benötigt eine Connector-Secret-Referenz.")
        if self.backend is CalendarBackend.GOOGLE and self.credential_ref is None:
            raise ValueError("Google-Kalenderkonto benötigt eine Connector-Referenz.")
        if self.backend is not CalendarBackend.GOOGLE and self.credential_ref is not None:
            raise ValueError("Lokale Kalenderkonten dürfen keine Credential-Referenz tragen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "account_id": self.account_id,
            "profile_id": self.profile_id,
            "backend": self.backend.value,
            "display_name": self.display_name,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "calendar_id": self.calendar_id,
            "credential_ref": self.credential_ref,
        }


@dataclass(frozen=True, slots=True)
class CalendarReminderSpec:
    method: str
    minutes_before: int

    SCHEMA = "folderhome.calendar-reminder.v1"

    def __post_init__(self) -> None:
        if self.method not in {"popup", "local_notification"}:
            raise ValueError("Kalendererinnerung verwendet eine unbekannte Methode.")
        if not 0 <= self.minutes_before <= 40320:
            raise ValueError("Kalendererinnerung muss zwischen 0 und 40320 Minuten liegen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "method": self.method,
            "minutes_before": self.minutes_before,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorRequest:
    request_id: str
    profile_id: str
    account_id: str
    operations: tuple[CalendarConnectorOperation, ...]
    reminders: tuple[CalendarReminderSpec, ...]

    SCHEMA = "folderhome.calendar-connector-request.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.request_id) is None or _ID.fullmatch(self.account_id) is None:
            raise ValueError("Kalenderconnector-Anfrage besitzt ungültige IDs.")
        if not self.profile_id.strip() or not self.operations:
            raise ValueError("Kalenderconnector-Anfrage benötigt Profil und Operationen.")
        if len(self.operations) != len(set(self.operations)):
            raise ValueError("Kalenderoperationen müssen eindeutig sein.")
        has_remind = CalendarConnectorOperation.REMIND in self.operations
        if has_remind != bool(self.reminders):
            raise ValueError("Reminder-Operation und Erinnerungen müssen gemeinsam auftreten.")
        reminder_keys = {(item.method, item.minutes_before) for item in self.reminders}
        if len(reminder_keys) != len(self.reminders):
            raise ValueError("Kalendererinnerungen müssen eindeutig sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "account_id": self.account_id,
            "operations": [item.value for item in self.operations],
            "reminders": [item.to_dict() for item in self.reminders],
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorEvent:
    event_uid: str
    profile_id: str
    calendar_id: str
    title: str
    start: str
    end: str | None
    timezone: str
    all_day: bool
    location: str | None
    attendees: tuple[str, ...]
    transparency: str
    reminders: tuple[CalendarReminderSpec, ...]
    source_handoff_action_id: str

    SCHEMA = "folderhome.calendar-connector-event.v1"

    def __post_init__(self) -> None:
        if _EVENT_UID.fullmatch(self.event_uid) is None:
            raise ValueError("Connectorereignis besitzt eine ungültige UID.")
        if not all(
            value.strip()
            for value in (self.profile_id, self.calendar_id, self.title, self.start)
        ):
            raise ValueError("Connectorereignis besitzt leere Pflichtfelder.")
        if self.attendees:
            raise ValueError("FolderHome-Dokumenttermine sind Solo-Ereignisse ohne Teilnehmer.")
        if self.transparency != "opaque":
            raise ValueError("FolderHome-Dokumenttermine müssen Zeit blockieren.")
        if _HANDOFF_ACTION_ID.fullmatch(self.source_handoff_action_id) is None:
            raise ValueError("Connectorereignis benötigt eine Phase-17-Aktionsreferenz.")

    def google_create_payload(self) -> dict[str, object]:
        if self.end is None:
            raise ValueError("Google-Ereignis benötigt eine belegte Endzeit.")
        if self.all_day:
            start: dict[str, str] = {"date": self.start}
            end: dict[str, str] = {"date": self.end}
        else:
            start = {"dateTime": self.start, "timeZone": self.timezone}
            end = {"dateTime": self.end, "timeZone": self.timezone}
        return {
            "calendar_id": self.calendar_id,
            "summary": self.title,
            "location": self.location,
            "start": start,
            "end": end,
            "attendees": [],
            "transparency": self.transparency,
            "reminders": {
                "use_default": False,
                "overrides": [
                    {"method": item.method, "minutes": item.minutes_before}
                    for item in self.reminders
                ],
            },
            "folderhome_event_uid": self.event_uid,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "event_uid": self.event_uid,
            "profile_id": self.profile_id,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "timezone": self.timezone,
            "all_day": self.all_day,
            "location": self.location,
            "attendees": [],
            "transparency": self.transparency,
            "reminders": [item.to_dict() for item in self.reminders],
            "source_handoff_action_id": self.source_handoff_action_id,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorRoute:
    backend: CalendarBackend
    provider_id: str
    provider_revision: str | None
    status: str
    reason: str
    supported_operations: tuple[CalendarConnectorOperation, ...]
    live_supported: bool
    connector_invoked: bool = False

    SCHEMA = "folderhome.calendar-connector-route.v1"

    def __post_init__(self) -> None:
        if self.status not in {"ready", "review_required", "blocked"}:
            raise ValueError("Kalenderconnector-Route besitzt ungültigen Status.")
        if not self.reason or not self.supported_operations:
            raise ValueError("Kalenderconnector-Route benötigt Grund und Operationen.")
        if self.provider_revision is not None and _PROVIDER_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("Kalenderconnector-Route besitzt eine ungültige Revision.")
        if self.connector_invoked:
            raise ValueError("Kalenderconnector-Route darf keinen Provider ausführen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "backend": self.backend.value,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "status": self.status,
            "reason": self.reason,
            "supported_operations": [item.value for item in self.supported_operations],
            "live_supported": self.live_supported,
            "connector_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorAction:
    action_id: str
    event_uid: str
    source_handoff_action_id: str
    operation: CalendarConnectorOperation
    status: str
    reason: str
    delegated_to_existing_handoff: bool
    connector_invoked: bool = False

    SCHEMA = "folderhome.calendar-connector-action.v1"

    def __post_init__(self) -> None:
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("Kalenderconnector-Aktion besitzt eine ungültige ID.")
        if _EVENT_UID.fullmatch(self.event_uid) is None:
            raise ValueError("Kalenderconnector-Aktion besitzt eine ungültige UID.")
        if self.status not in {"planned", "delegated", "review_required", "blocked"}:
            raise ValueError("Kalenderconnector-Aktion besitzt ungültigen Status.")
        if not self.reason or self.connector_invoked:
            raise ValueError("Kalenderconnector-Aktion ist nicht nebenwirkungsfrei.")
        if self.delegated_to_existing_handoff != (self.status == "delegated"):
            raise ValueError("Delegationsstatus der Kalenderconnector-Aktion ist inkonsistent.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "action_id": self.action_id,
            "event_uid": self.event_uid,
            "source_handoff_action_id": self.source_handoff_action_id,
            "operation": self.operation.value,
            "status": self.status,
            "reason": self.reason,
            "delegated_to_existing_handoff": self.delegated_to_existing_handoff,
            "connector_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorPlan:
    plan_id: str
    plan_sha256: str
    handoff_plan_id: str
    profile_id: str
    account_id: str
    backend: CalendarBackend
    backend_source: str
    source_rule_ids: tuple[str, ...]
    route: CalendarConnectorRoute
    events: tuple[CalendarConnectorEvent, ...]
    actions: tuple[CalendarConnectorAction, ...]
    status: str
    connector_invoked: bool = False
    live_calendar_written: bool = False

    SCHEMA = "folderhome.calendar-connector-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None or _PLAN_SHA.fullmatch(
            self.plan_sha256
        ) is None:
            raise ValueError("Kalenderconnector-Plan besitzt ungültige Identität.")
        if _HANDOFF_PLAN_ID.fullmatch(self.handoff_plan_id) is None:
            raise ValueError("Kalenderconnector-Plan benötigt eine Phase-17-Planreferenz.")
        if self.status not in {"ready", "review_required", "blocked"}:
            raise ValueError("Kalenderconnector-Plan besitzt ungültigen Status.")
        if self.connector_invoked or self.live_calendar_written:
            raise ValueError("Kalenderconnector-Plan muss nebenwirkungsfrei sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "handoff_plan_id": self.handoff_plan_id,
            "profile_id": self.profile_id,
            "account_id": self.account_id,
            "backend": self.backend.value,
            "backend_source": self.backend_source,
            "source_rule_ids": list(self.source_rule_ids),
            "route": self.route.to_dict(),
            "events": [item.to_dict() for item in self.events],
            "actions": [item.to_dict() for item in self.actions],
            "status": self.status,
            "connector_invoked": False,
            "live_calendar_written": False,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    action_ids: tuple[str, ...]
    allowed_operations: tuple[CalendarConnectorOperation, ...]
    approved_at: str
    allow_network_write: bool

    SCHEMA = "folderhome.calendar-connector-approval.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.approval_id) is None or _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Kalenderconnector-Freigabe besitzt ungültige IDs.")
        if _PLAN_SHA.fullmatch(self.plan_sha256) is None:
            raise ValueError("Kalenderconnector-Freigabe benötigt einen Planhash.")
        if not self.action_ids or len(self.action_ids) != len(set(self.action_ids)):
            raise ValueError("Kalenderconnector-Freigabe benötigt eindeutige Aktionen.")
        if any(_ACTION_ID.fullmatch(item) is None for item in self.action_ids):
            raise ValueError("Kalenderconnector-Freigabe enthält ungültige Aktionen.")
        if not self.allowed_operations or len(self.allowed_operations) != len(
            set(self.allowed_operations)
        ):
            raise ValueError("Kalenderconnector-Freigabe benötigt eindeutige Operationen.")
        _timestamp(self.approved_at, label="Kalenderconnector-Freigabezeit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "action_ids": list(self.action_ids),
            "allowed_operations": [item.value for item in self.allowed_operations],
            "approved_at": self.approved_at,
            "allow_network_write": self.allow_network_write,
        }


@dataclass(frozen=True, slots=True)
class CalendarProviderEventReference:
    reference_id: str
    event_uid: str
    account_id: str
    calendar_id: str
    provider_id: str
    provider_event_id: str
    payload_sha256: str

    SCHEMA = "folderhome.calendar-provider-event-ref.v1"

    def __post_init__(self) -> None:
        if _EVENT_REF_ID.fullmatch(self.reference_id) is None:
            raise ValueError("Provider-Ereignisreferenz besitzt eine ungültige ID.")
        if _EVENT_UID.fullmatch(self.event_uid) is None or _PLAN_SHA.fullmatch(
            self.payload_sha256
        ) is None:
            raise ValueError("Provider-Ereignisreferenz besitzt ungültige Bindungen.")
        if not self.provider_event_id.strip():
            raise ValueError("Provider-Ereignisreferenz benötigt eine externe Ereignis-ID.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "reference_id": self.reference_id,
            "event_uid": self.event_uid,
            "account_id": self.account_id,
            "calendar_id": self.calendar_id,
            "provider_id": self.provider_id,
            "provider_event_id": self.provider_event_id,
            "payload_sha256": self.payload_sha256,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorExecutionReport:
    report_id: str
    plan_id: str
    approval_id: str
    provider_id: str
    provider_revision: str | None
    status: str
    event_references: tuple[CalendarProviderEventReference, ...]
    network_invoked: bool
    live_calendar_written: bool

    SCHEMA = "folderhome.calendar-connector-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Kalenderconnector-Report besitzt eine ungültige ID.")
        if self.status not in {"simulated", "executed"}:
            raise ValueError("Kalenderconnector-Report besitzt ungültigen Status.")
        if self.live_calendar_written != (self.status == "executed"):
            raise ValueError("Kalenderconnector-Status und Live-Wirkung widersprechen sich.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "status": self.status,
            "event_references": [item.to_dict() for item in self.event_references],
            "network_invoked": self.network_invoked,
            "live_calendar_written": self.live_calendar_written,
        }
