"""Reference-bound mutation plans through the normal workflow approval boundary."""

import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256

from folderhome.application.google_calendar_resources import resolve_google_calendar_resources
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionOutcomeUnknown,
    _canonical_json,
    _resource_execution_envelope,
    _resource_execution_report,
    _validate_exact_request,
)
from folderhome.bridges.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarGateway,
    GoogleCalendarOutcomeUnknown,
    _valid_etag,
)
from folderhome.bridges.google_calendar_credentials import GoogleCalendarCredentialResolver
from folderhome.bridges.google_calendar_mutations import _marked
from folderhome.contracts.calendar_connectors import CalendarConnectorEvent, CalendarReminderSpec

_STR = {"type": "string", "minLength": 1, "maxLength": 8192}
_EVENT_PROPERTIES = {
    "schema": {"const": CalendarConnectorEvent.SCHEMA},
    **{
        key: _STR
        for key in (
            "event_uid",
            "profile_id",
            "calendar_id",
            "title",
            "start",
            "timezone",
            "source_handoff_action_id",
        )
    },
    "end": {"type": ["string", "null"]},
    "location": {"type": ["string", "null"]},
    "all_day": {"type": "boolean"},
    "attendees": {"type": "array", "maxItems": 0},
    "transparency": {"const": "opaque"},
    "reminders": {
        "type": "array",
        "maxItems": 5,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["schema", "method", "minutes_before"],
            "properties": {
                "schema": {"const": CalendarReminderSpec.SCHEMA},
                "method": {"const": "popup"},
                "minutes_before": {"type": "integer", "minimum": 0, "maximum": 40320},
            },
        },
    },
}
EVENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(_EVENT_PROPERTIES),
    "properties": _EVENT_PROPERTIES,
}
_PROPERTIES = {
    **{
        key: {"type": "string", "minLength": 2, "maxLength": 64}
        for key in (
            "configuration_resource_id",
            "accounts_resource_id",
            "credential_resource_id",
            "ledger_resource_id",
            "account_id",
        )
    },
    "area": {"type": "string", "minLength": 1, "maxLength": 80},
    "operation": {"enum": ["update", "delete"]},
    "previous_event": EVENT_SCHEMA,
    "expected_etag": {"type": "string", "minLength": 3, "maxLength": 512},
    "replacement": {"oneOf": [EVENT_SCHEMA, {"type": "null"}]},
}
MUTATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(_PROPERTIES),
    "properties": _PROPERTIES,
}


@dataclass(frozen=True)
class PreparedGoogleMutation:
    profile_id: str
    request: dict
    context: object
    previous_event: CalendarConnectorEvent
    replacement: CalendarConnectorEvent | None


class GoogleMutationOutcomeUnknown(WorkflowExecutionOutcomeUnknown):
    def __init__(self, result=None):
        super().__init__("Kalenderänderung unklar; keine erneute Schreibfreigabe ohne Prüfung.")
        self.result = deepcopy(result)

    def public_evidence(self):
        return {
            "schema": "folderhome.google-calendar-mutation-evidence.v1",
            "confirmed_mutation": deepcopy(self.result),
        }


def _event(value):
    if not isinstance(value, dict) or set(value) != set(_EVENT_PROPERTIES):
        raise ValueError("Invalid event fields")
    if value["schema"] != CalendarConnectorEvent.SCHEMA or type(value["all_day"]) is not bool:
        raise ValueError("Invalid event types")
    for key in _EVENT_PROPERTIES.keys() - {"all_day", "reminders", "attendees"}:
        if key in {"end", "location"} and value[key] is None:
            continue
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= 8192:
            raise ValueError("Invalid event text")
    if (
        value["attendees"] != []
        or not isinstance(value["reminders"], list)
        or len(value["reminders"]) > 5
    ):
        raise ValueError("Invalid solo event")
    reminders = []
    for item in value["reminders"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"schema", "method", "minutes_before"}
            or item["schema"] != CalendarReminderSpec.SCHEMA
            or item["method"] != "popup"
            or type(item["minutes_before"]) is not int
        ):
            raise ValueError("Invalid reminder")
        reminders.append(CalendarReminderSpec(item["method"], item["minutes_before"]))
    fields = {
        key: item for key, item in value.items() if key not in {"schema", "attendees", "reminders"}
    }
    return CalendarConnectorEvent(**fields, attendees=(), reminders=tuple(reminders))


def _read_version(account, path, event_id):
    if not path.is_file() or any(
        parent.is_symlink() or getattr(parent, "is_junction", lambda: False)()
        for parent in (path, *path.parents)
    ):
        raise ValueError("Missing private version receipt")
    from folderhome.bridges.google_calendar import _hash

    namespace = _hash(["google-calendar", account.calendar_id])
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
        row = connection.execute(
            "SELECT payload_hash,status,etag FROM calendar_creations "
            "WHERE namespace=? AND event_id=?",
            (namespace, event_id),
        ).fetchone()
    return row


def _check_confirmed_version(context, event_id, fingerprint, etag):
    if _read_version(context.account, context.ledger_path, event_id) != (
        fingerprint,
        "confirmed",
        etag,
    ):
        raise ValueError("Prior event is not the confirmed own version")


def confirmed_event_version(account, ledger_path, event):
    """Expose a confirmed local receipt, never manufacture a provider version."""
    validator = GoogleCalendarGateway(
        account=account,
        ledger_path=ledger_path,
        token_provider=lambda _: None,
        allow_network_write=False,
    )
    payload, fingerprint = _marked(validator, event)
    row = _read_version(account, ledger_path, payload["id"])
    if not row or row[:2] != (fingerprint, "confirmed") or not _valid_etag(row[2]):
        raise ValueError("Confirmed event version unavailable")
    return {
        "schema": "folderhome.google-calendar-event-version.v1",
        "provider_event_id": payload["id"],
        "etag": row[2],
        "event": event.to_dict(),
    }


def prepare_mutation(adapter, *, profile_id, request, load, check_ledger=True):
    try:
        _validate_exact_request(request, MUTATION_SCHEMA, "Kalenderänderung")
        if request["operation"] not in {"update", "delete"} or not _valid_etag(
            request["expected_etag"]
        ):
            raise ValueError("Invalid mutation operation/version")
        if (request["operation"] == "delete") != (request["replacement"] is None):
            raise ValueError("Replacement does not match operation")
        for key in _PROPERTIES.keys() - {
            "operation",
            "expected_etag",
            "previous_event",
            "replacement",
        }:
            if not isinstance(request[key], str) or not 1 <= len(request[key]) <= 80:
                raise ValueError("Invalid resource text")
        context = resolve_google_calendar_resources(
            adapter,
            profile_id,
            request,
            include_source=False,
            load=load,
        )
        previous = _event(request["previous_event"])
        replacement = None if request["replacement"] is None else _event(request["replacement"])
        validator = GoogleCalendarGateway(
            account=context.account,
            ledger_path=context.ledger_path,
            token_provider=lambda _: None,
            allow_network_write=False,
        )
        before, fingerprint = _marked(validator, previous)
        if replacement is not None:
            after, new_hash = _marked(validator, replacement)
            if after["id"] != before["id"] or new_hash == fingerprint:
                raise ValueError("Mutation changes identity or contains no change")
        if check_ledger:
            _check_confirmed_version(context, before["id"], fingerprint, request["expected_etag"])
        public = {
            "schema": adapter.descriptor.plan_schema,
            "profile_id": profile_id,
            "account_id": context.account.account_id,
            "provider_event_id": before["id"],
            "operation": request["operation"],
            "expected_etag": request["expected_etag"],
            "previous_event": previous.to_dict(),
            "replacement": None if replacement is None else replacement.to_dict(),
            "resource_binding_sha256": context.binding_sha256,
            "request": deepcopy(request),
            "paths_disclosed": False,
        }
        digest = sha256(_canonical_json(public)).hexdigest()
        envelope = _resource_execution_envelope(
            descriptor=adapter.descriptor,
            domain_plan_id="google_calendar_mutation_" + digest,
            public_plan=public,
            approval_kind="explicit_google_calendar_" + request["operation"],
        )
        return envelope, PreparedGoogleMutation(
            profile_id, deepcopy(request), context, previous, replacement
        )
    except Exception:
        raise WorkflowExecutionError(
            "Kalenderänderung benötigt gültige Rechte und eine bestätigte Version."
        ) from None


def execute_mutation(adapter, *, envelope, prepared, approved_at, load):
    if not adapter._allowed or not isinstance(prepared, PreparedGoogleMutation):
        raise WorkflowExecutionError("Getrennte Freigabe --approve-calendar-write fehlt.")

    def verify(*, check_ledger=False):
        fresh, current = prepare_mutation(
            adapter,
            profile_id=prepared.profile_id,
            request=prepared.request,
            load=load,
            check_ledger=check_ledger,
        )
        if fresh != envelope or current != prepared:
            raise WorkflowExecutionError(
                "Kalenderänderungsplan oder Ressourcenrechte sind nicht mehr aktuell."
            )

    verify(check_ledger=True)
    resolver = GoogleCalendarCredentialResolver(
        credential_file=prepared.context.credential_path,
        credential_ref=prepared.context.account.credential_ref,
        allow_network=True,
    )

    def token(reference):
        verify()
        return resolver(reference)

    transport = adapter._transport_factory()

    class CheckedTransport:
        def request(self, *args, **kwargs):
            try:
                verify()
                result = transport.request(*args, **kwargs)
                verify()
                return result
            except WorkflowExecutionError:
                raise GoogleCalendarError(
                    "Kalenderressourcen wurden während der Änderung ungültig."
                ) from None

    gateway = GoogleCalendarGateway(
        account=prepared.context.account,
        ledger_path=prepared.context.ledger_path,
        token_provider=token,
        allow_network_write=True,
        transport=CheckedTransport(),
    )
    try:
        arguments = {
            "expected_etag": prepared.request["expected_etag"],
            "idempotency_key": envelope.domain_plan_sha256,
        }
        if prepared.replacement is None:
            result = gateway.delete_event(prepared.previous_event, **arguments)
        else:
            result = gateway.update_event(
                prepared.replacement, previous_event=prepared.previous_event, **arguments
            )
    except GoogleCalendarOutcomeUnknown:
        raise GoogleMutationOutcomeUnknown() from None
    except Exception:
        raise WorkflowExecutionError(
            "Kalenderänderung wurde abgewiesen; Version und Rechte prüfen."
        ) from None
    try:
        versions = (
            []
            if prepared.replacement is None
            else [
                confirmed_event_version(
                    prepared.context.account,
                    prepared.context.ledger_path,
                    prepared.replacement,
                )
            ]
        )
        if versions and versions[0]["etag"] != result["etag"]:
            raise ValueError("Receipt changed after mutation readback")
        verify()
    except Exception:
        raise GoogleMutationOutcomeUnknown(result) from None
    return _resource_execution_report(
        envelope=envelope,
        descriptor=adapter.descriptor,
        approved_at=approved_at,
        public_report={
            "schema": adapter.descriptor.report_schema,
            "mutation": result,
            "event_versions": versions,
            "paths_disclosed": False,
        },
    )
