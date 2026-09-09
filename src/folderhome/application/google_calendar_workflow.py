"""Private-resource adapter for exact Google calendar creation approvals."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from folderhome.application.calendar_connectors import (
    CalendarConnectorOutcomeUnknown,
    build_calendar_connector_plan,
    execute_calendar_connector_plan,
)
from folderhome.application.calendar_handoff import (
    analyze_folder_calendar,
    build_calendar_handoff_plan,
)
from folderhome.application.google_calendar_mutation_workflow import (
    MUTATION_SCHEMA,
    PreparedGoogleMutation,
    confirmed_event_version,
    execute_mutation,
    prepare_mutation,
)
from folderhome.application.google_calendar_resources import (
    RESOURCE_REQUIREMENTS,
    resolve_google_calendar_resources,
    verify_snapshots,
)
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionOutcomeUnknown,
    _resource_execution_envelope,
    _resource_execution_report,
    _validate_exact_request,
)
from folderhome.bridges.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarGateway,
    GoogleCalendarTransport,
)
from folderhome.bridges.google_calendar_credentials import GoogleCalendarCredentialResolver
from folderhome.contracts.calendar_connectors import (
    CalendarConnectorApproval,
    CalendarConnectorOperation,
    CalendarConnectorRequest,
    CalendarReminderSpec,
)
from folderhome.contracts.workflow_execution import WorkflowAdapterDescriptor

_RESOURCES = RESOURCE_REQUIREMENTS
_PROPERTIES = {
    **{key: {"type": "string", "minLength": 2, "maxLength": 64} for key in _RESOURCES},
    "account_id": {"type": "string", "minLength": 2, "maxLength": 64},
    "area": {"type": "string", "minLength": 1, "maxLength": 80},
    "planned_at": {"type": "string", "format": "date-time"},
    "recursive": {"type": "boolean"},
    "allow_sensitive_local_read": {"type": "boolean"},
    "reminders": {
        "type": "array",
        "maxItems": 5,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["method", "minutes_before"],
            "properties": {
                "method": {"const": "popup"},
                "minutes_before": {"type": "integer", "minimum": 0, "maximum": 40320},
            },
        },
    },
}
_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(_PROPERTIES),
    "properties": _PROPERTIES,
}


def _load(path):
    if any(
        parent.is_symlink() or getattr(parent, "is_junction", lambda: False)()
        for parent in (path, *path.parents)
    ):
        raise ValueError("Configuration links are not supported")
    with path.open("rb") as handle:
        raw = handle.read(65_537)
    if len(raw) > 65_536:
        raise ValueError("Configuration budget exceeded")
    return raw, json.loads(raw)


@dataclass(frozen=True)
class _PreparedGoogleCalendar:
    profile_id: str
    request: dict
    plan: object
    account: object
    credential_path: Path
    ledger_path: Path


class GoogleCalendarWorkflowOutcomeUnknown(WorkflowExecutionOutcomeUnknown):
    def __init__(self, *, confirmed_references=()):
        super().__init__(
            "Kalenderergebnis unklar oder unvollständig; bestätigte Einträge rücklesen."
        )
        self.confirmed_references = tuple(confirmed_references)

    def public_evidence(self) -> dict[str, object]:
        return {
            "schema": "folderhome.google-calendar-partial-evidence.v1",
            "confirmed_event_references": [ref.to_dict() for ref in self.confirmed_references],
        }


class GoogleCalendarWorkflowAdapter:
    descriptor = WorkflowAdapterDescriptor(
        workflow_id="calendar-connectors",
        adapter_id="google_calendar_resource.v1",
        status="connected",
        plan_schema="folderhome.google-calendar-resource-plan.v1",
        report_schema="folderhome.google-calendar-resource-report.v1",
        side_effects=("external.calendar.write",),
        reason="Creates appointments or applies separately reviewed version-bound mutations.",
        request_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {**_PROPERTIES, **MUTATION_SCHEMA["properties"]},
            "required": [key for key in _SCHEMA["required"] if key in MUTATION_SCHEMA["required"]],
            "oneOf": [_SCHEMA, MUTATION_SCHEMA],
        },
    )

    def __init__(
        self,
        *,
        registry,
        profiles_dir,
        extractor,
        allow_calendar_write,
        resource_registry_file=None,
        launch_calendar_resources=(),
        transport_factory=None,
    ):
        self._registry = registry
        self._profiles_dir = Path(profiles_dir)
        self._extractor = extractor
        self._allowed = allow_calendar_write is True
        self._registry_file = resource_registry_file
        self._launch_resources = tuple(launch_calendar_resources)
        if any(
            item.kind != "file"
            or item.operations != frozenset({"read"})
            or not item.purposes
            or not item.purposes <= {"calendar.configuration", "calendar.connector_accounts"}
            for item in self._launch_resources
        ):
            raise WorkflowExecutionError("Kalenderstart darf nur Konfigurationsdateien binden.")
        self._transport_factory = transport_factory or GoogleCalendarTransport

    def prepare(self, *, profile_id, request):
        if "operation" in request:
            return prepare_mutation(self, profile_id=profile_id, request=request, load=_load)
        _validate_exact_request(request, _SCHEMA, "Google-Kalenderanfrage")
        try:
            context = resolve_google_calendar_resources(
                self,
                profile_id,
                request,
                include_source=True,
                load=_load,
            )
            analysis = analyze_folder_calendar(
                context.source_path,
                profile_id=profile_id,
                area=request["area"],
                default_timezone=context.timezone,
                extractor=self._extractor,
                recursive=request["recursive"],
                allow_sensitive_local_read=request["allow_sensitive_local_read"],
            )
            handoff = build_calendar_handoff_plan(
                analysis,
                configuration=context.configuration,
                policy=context.policy,
                planned_at=request["planned_at"],
            )
            operations = (CalendarConnectorOperation.CREATE,)
            reminders = tuple(CalendarReminderSpec(**item) for item in request["reminders"])
            if reminders:
                operations += (CalendarConnectorOperation.REMIND,)
            plan = build_calendar_connector_plan(
                handoff,
                request=CalendarConnectorRequest(
                    request_id="google-resource-create",
                    profile_id=profile_id,
                    account_id=context.account.account_id,
                    operations=operations,
                    reminders=reminders,
                ),
                account=context.account,
                provider_ready=True,
            )
            if not plan.events or plan.status != "ready":
                raise ValueError("No executable non-conflicting appointments")
            verify_snapshots(context, self._profiles_dir, _load)
            public = {
                **plan.to_dict(),
                "schema": self.descriptor.plan_schema,
                "resource_binding_sha256": context.binding_sha256,
                "request": deepcopy(request),
                "paths_disclosed": False,
            }
            envelope = _resource_execution_envelope(
                descriptor=self.descriptor,
                domain_plan_id=plan.plan_id,
                public_plan=public,
                approval_kind="explicit_google_calendar_write",
            )
            return envelope, _PreparedGoogleCalendar(
                profile_id,
                deepcopy(request),
                plan,
                context.account,
                context.credential_path,
                context.ledger_path,
            )
        except Exception:
            raise WorkflowExecutionError(
                "Google-Kalenderressourcen oder Termindaten sind nicht ausführbar."
            ) from None

    def execute(self, *, envelope, domain_plan, approved_at):
        if isinstance(domain_plan, PreparedGoogleMutation):
            return execute_mutation(
                self,
                envelope=envelope,
                prepared=domain_plan,
                approved_at=approved_at,
                load=_load,
            )
        if not self._allowed or not isinstance(domain_plan, _PreparedGoogleCalendar):
            raise WorkflowExecutionError("Getrennte Freigabe --approve-calendar-write fehlt.")

        def verify():
            fresh, prepared = self.prepare(
                profile_id=domain_plan.profile_id, request=domain_plan.request
            )
            if fresh != envelope or prepared != domain_plan:
                raise WorkflowExecutionError(
                    "Kalenderplan oder Ressourcenbindung ist nicht mehr aktuell."
                )

        verify()
        credential_resolver = GoogleCalendarCredentialResolver(
            credential_file=domain_plan.credential_path,
            credential_ref=domain_plan.account.credential_ref,
            allow_network=True,
        )

        def token(reference):
            verify()
            return credential_resolver(reference)

        transport = self._transport_factory()

        class CheckedTransport:
            def request(self, *args, **kwargs):
                try:
                    verify()
                    response = transport.request(*args, **kwargs)
                    verify()
                    return response
                except WorkflowExecutionError:
                    raise GoogleCalendarError(
                        "Kalenderbindung wurde während der Ausführung ungültig."
                    ) from None

        gateway = GoogleCalendarGateway(
            account=domain_plan.account,
            ledger_path=domain_plan.ledger_path,
            token_provider=token,
            allow_network_write=True,
            transport=CheckedTransport(),
        )
        approval = CalendarConnectorApproval(
            approval_id="google-resource-" + envelope.domain_plan_sha256[:32],
            plan_id=domain_plan.plan.plan_id,
            plan_sha256=domain_plan.plan.plan_sha256,
            action_ids=tuple(action.action_id for action in domain_plan.plan.actions),
            allowed_operations=tuple(
                dict.fromkeys(action.operation for action in domain_plan.plan.actions)
            ),
            approved_at=approved_at,
            allow_network_write=True,
        )
        try:
            report = execute_calendar_connector_plan(
                domain_plan.plan, approval=approval, gateway=gateway
            )
        except CalendarConnectorOutcomeUnknown as exc:
            raise GoogleCalendarWorkflowOutcomeUnknown(
                confirmed_references=exc.confirmed_references
            ) from None
        except Exception:
            raise WorkflowExecutionError("Google-Kalenderausführung wurde abgewiesen.") from None
        try:
            by_uid = {event.event_uid: event for event in domain_plan.plan.events}
            versions = [
                confirmed_event_version(
                    domain_plan.account,
                    domain_plan.ledger_path,
                    by_uid[ref.event_uid],
                )
                for ref in report.event_references
            ]
            verify()
            return _resource_execution_report(
                envelope=envelope,
                descriptor=self.descriptor,
                approved_at=approved_at,
                public_report={
                    **report.to_dict(),
                    "schema": self.descriptor.report_schema,
                    "event_versions": versions,
                    "paths_disclosed": False,
                },
            )
        except Exception:
            raise GoogleCalendarWorkflowOutcomeUnknown(
                confirmed_references=report.event_references
            ) from None
