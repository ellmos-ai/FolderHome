"""Private-resource adapter for exact Google calendar creation approvals."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from folderhome.application.calendar_connectors import (
    CalendarConnectorOutcomeUnknown,
    build_calendar_connector_plan,
    execute_calendar_connector_plan,
    parse_calendar_connector_accounts,
)
from folderhome.application.calendar_handoff import (
    analyze_folder_calendar,
    build_calendar_handoff_plan,
    parse_calendar_configuration,
    resolve_calendar_preferences,
)
from folderhome.application.profile_rules import parse_profile_configuration, resolve_profile_policy
from folderhome.application.resource_registry import parse_resource_registry
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionOutcomeUnknown,
    _canonical_json,
    _require_separate_resources,
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
from folderhome.contracts.calendar import CalendarBackend
from folderhome.contracts.calendar_connectors import (
    CalendarConnectorApproval,
    CalendarConnectorOperation,
    CalendarConnectorRequest,
    CalendarReminderSpec,
)
from folderhome.contracts.workflow_execution import WorkflowAdapterDescriptor

_RESOURCES = {
    "source_resource_id": ("calendar.source", "directory", {"read", "list"}),
    "configuration_resource_id": ("calendar.configuration", "file", {"read"}),
    "accounts_resource_id": ("calendar.connector_accounts", "file", {"read"}),
    "credential_resource_id": ("calendar.google_credentials", "file", {"read"}),
    "ledger_resource_id": ("calendar.connector_ledger", "directory", {"read", "state_write"}),
}
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
        reason="Creates reviewed appointments in an explicitly configured Google calendar.",
        request_schema=_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry,
        profiles_dir,
        extractor,
        allow_calendar_write,
        resource_registry_file=None,
        transport_factory=None,
    ):
        self._registry = registry
        self._profiles_dir = Path(profiles_dir)
        self._extractor = extractor
        self._allowed = allow_calendar_write is True
        self._registry_file = resource_registry_file
        self._transport_factory = transport_factory or GoogleCalendarTransport

    def prepare(self, *, profile_id, request):
        _validate_exact_request(request, _SCHEMA, "Google-Kalenderanfrage")
        try:
            snapshots = {}

            def document(path):
                raw, payload = _load(path)
                snapshots[path] = raw
                return payload

            registry = self._registry
            if self._registry_file is not None:
                registry = parse_resource_registry(
                    document(self._registry_file),
                    expected_os_account=registry.os_account,
                    known_profile_ids=registry.known_profile_ids,
                )
            resources = {}
            for key, (purpose, kind, operations) in _RESOURCES.items():
                required = set(operations)
                if key == "source_resource_id" and request["allow_sensitive_local_read"]:
                    required.add("sensitive_read")
                resources[key] = registry.resolve(
                    resource_id=request[key],
                    profile_id=profile_id,
                    purpose=purpose,
                    required_kind=kind,
                    required_operations=frozenset(required),
                )
            source = resources["source_resource_id"].local_path
            ledger = resources["ledger_resource_id"].local_path
            credential = resources["credential_resource_id"].local_path
            _require_separate_resources(source, ledger)
            _require_separate_resources(source, credential)
            _require_separate_resources(ledger, credential)
            profile_files = sorted(self._profiles_dir.glob("*.json"))
            household = self._profiles_dir / "household.json"
            profiles = parse_profile_configuration(
                document(household),
                {
                    path.name: document(path)
                    for path in profile_files
                    if path.name.casefold() != "household.json"
                },
            )
            if profiles.os_account != registry.os_account:
                raise ValueError("Profile and resource account differ")
            configuration_path = resources["configuration_resource_id"].local_path
            configuration = parse_calendar_configuration(
                document(configuration_path), config_path=configuration_path
            )
            accounts = parse_calendar_connector_accounts(
                document(resources["accounts_resource_id"].local_path)
            )
            account = next(item for item in accounts if item.account_id == request["account_id"])
            if (
                account.profile_id != profile_id
                or account.provider_id != "google-calendar"
                or account.provider_revision != "v3"
                or account.calendar_id == "primary"
                or account.credential_ref
                != "connector://google-calendar/" + request["credential_resource_id"]
            ):
                raise ValueError("Invalid Google account binding")
            policy = resolve_profile_policy(profiles, profile_id=profile_id, area=request["area"])
            backend, _, timezone, _ = resolve_calendar_preferences(configuration, policy)
            if backend is not CalendarBackend.GOOGLE:
                raise ValueError("Profile does not select Google")
            analysis = analyze_folder_calendar(
                source,
                profile_id=profile_id,
                area=request["area"],
                default_timezone=timezone,
                extractor=self._extractor,
                recursive=request["recursive"],
                allow_sensitive_local_read=request["allow_sensitive_local_read"],
            )
            handoff = build_calendar_handoff_plan(
                analysis,
                configuration=configuration,
                policy=policy,
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
                    account_id=account.account_id,
                    operations=operations,
                    reminders=reminders,
                ),
                account=account,
                provider_ready=True,
            )
            if not plan.events or plan.status != "ready":
                raise ValueError("No executable non-conflicting appointments")
            if profile_files != sorted(self._profiles_dir.glob("*.json")) or any(
                _load(path)[0] != raw for path, raw in snapshots.items()
            ):
                raise ValueError("Configuration changed during preparation")
            binding = {
                "files": [(str(path), sha256(raw).hexdigest()) for path, raw in snapshots.items()],
                "resources": [
                    {
                        "id": item.resource_id,
                        "path": str(item.local_path),
                        "operations": sorted(item.operations),
                        "profiles": sorted(item.profile_ids),
                        "purposes": sorted(item.purposes),
                        "kind": item.kind,
                        "cloud_context": item.cloud_context,
                    }
                    for item in resources.values()
                ],
            }
            public = {
                **plan.to_dict(),
                "schema": self.descriptor.plan_schema,
                "resource_binding_sha256": sha256(_canonical_json(binding)).hexdigest(),
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
                account,
                credential,
                ledger / "google-calendar.sqlite3",
            )
        except Exception:
            raise WorkflowExecutionError(
                "Google-Kalenderressourcen oder Termindaten sind nicht ausführbar."
            ) from None

    def execute(self, *, envelope, domain_plan, approved_at):
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
            verify()
            return _resource_execution_report(
                envelope=envelope,
                descriptor=self.descriptor,
                approved_at=approved_at,
                public_report={
                    **report.to_dict(),
                    "schema": self.descriptor.report_schema,
                    "paths_disclosed": False,
                },
            )
        except Exception:
            raise GoogleCalendarWorkflowOutcomeUnknown(
                confirmed_references=report.event_references
            ) from None
