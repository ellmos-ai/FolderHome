"""Logical-resource registration adapter; never starts a scheduler consumer."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from folderhome.application.directory_observation import load_watched_folder_configuration
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.resource_registry import parse_resource_registry
from folderhome.application.routine_queue import load_folder_routine_bindings
from folderhome.application.scheduler_handoff import build_scheduler_handoff
from folderhome.application.scheduler_registration import (
    SchedulerRegistrationPlan,
    build_scheduler_registration_plan,
    register_scheduler_job,
)
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionOutcomeUnknown,
    _canonical_json,
    _resource_execution_envelope,
    _resource_execution_report,
    _text,
    _validate_exact_request,
)
from folderhome.contracts.resources import ResourceRegistry
from folderhome.contracts.workflow_execution import (
    WorkflowAdapterDescriptor,
    WorkflowExecutionEnvelope,
)

_RESOURCE_CONTRACTS = {
    "watches_resource_id": ("scheduler.watches", "file", frozenset({"read"})),
    "bindings_resource_id": ("scheduler.bindings", "file", frozenset({"read"})),
    "store_resource_id": ("scheduler.store", "sqlite_store", frozenset({"read", "state_write"})),
    "ledger_resource_id": ("scheduler.ledger", "directory", frozenset({"read", "state_write"})),
    "state_resource_id": ("scheduler.state", "directory", frozenset({"read", "state_write"})),
}
_REQUEST_PROPERTIES = {
    **{name: {"type": "string", "minLength": 2, "maxLength": 64} for name in _RESOURCE_CONTRACTS},
    "task_name": {"type": "string", "minLength": 2, "maxLength": 64},
    "interval_minutes": {"type": "integer", "minimum": 5, "maximum": 1440},
    "start_at": {"type": "string", "format": "date-time"},
    "timezone": {"type": "string"},
    "allow_sensitive_local_read": {"type": "boolean"},
}
_REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(_REQUEST_PROPERTIES),
    "properties": _REQUEST_PROPERTIES,
}


@dataclass(frozen=True, slots=True)
class _PreparedSchedulerRegistration:
    plan: SchedulerRegistrationPlan
    profile_id: str
    request: dict[str, object]


class SchedulerRegistrationWorkflowAdapter:
    """Prepare through registered IDs, then register only under a separate startup gate."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="scheduler-handoff",
        adapter_id="scheduler_registration_resource.v1",
        status="connected",
        plan_schema="folderhome.scheduler-registration-resource-plan.v1",
        report_schema="folderhome.scheduler-registration-resource-report.v1",
        side_effects=("external.scheduler.write",),
        reason=(
            "Registers one approved read-only queue job; "
            "does not start a consumer or perform document actions."
        ),
        request_schema=_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles_dir: Path,
        manifest_root: Path,
        doc_services_root: Path,
        scheduler_root: Path,
        scheduler_revision: str,
        python_executable: Path,
        working_directory: Path,
        allow_scheduler_write: bool,
        resource_registry_file: Path | None = None,
    ):
        self._registry = registry
        self._profiles_dir = profiles_dir
        self._manifest_root = manifest_root
        self._doc_services_root = doc_services_root
        self._scheduler_root = scheduler_root
        self._scheduler_revision = scheduler_revision
        self._python_executable = python_executable
        self._working_directory = working_directory
        self._allow_scheduler_write = allow_scheduler_write
        self._resource_registry_file = resource_registry_file

    def prepare(self, *, profile_id: str, request: dict[str, object]):
        _validate_exact_request(request, _REQUEST_SCHEMA, "Scheduler-Anfrage")
        if request["allow_sensitive_local_read"] is not True:
            raise WorkflowExecutionError(
                "Scheduler benötigt eine ausdrückliche lokale Lesefreigabe."
            )
        try:
            registry = self._registry
            authorization_files = ()
            registry_bytes = None
            if self._resource_registry_file is not None:
                registry_bytes = self._resource_registry_file.read_bytes()
                registry = parse_resource_registry(
                    json.loads(registry_bytes),
                    expected_os_account=registry.os_account,
                    known_profile_ids=registry.known_profile_ids,
                )
                authorization_files = (self._resource_registry_file.resolve(),)
            resources = {
                name: registry.resolve(
                    resource_id=_text(request[name], name),
                    profile_id=profile_id,
                    purpose=purpose,
                    required_kind=kind,
                    required_operations=operations,
                )
                for name, (purpose, kind, operations) in _RESOURCE_CONTRACTS.items()
            }
            profiles = load_profile_configuration(self._profiles_dir)
            if (
                profiles.os_account != registry.os_account
                or frozenset(item.profile_id for item in profiles.profiles)
                != registry.known_profile_ids
            ):
                raise ValueError("Profil- und Ressourcenregister passen nicht zusammen.")
            handoff = build_scheduler_handoff(
                task_name=_text(request["task_name"], "task_name"),
                interval_minutes=request["interval_minutes"],
                start_at=_text(request["start_at"], "start_at"),
                timezone=_text(request["timezone"], "timezone"),
                config_file=resources["watches_resource_id"].local_path,
                bindings_file=resources["bindings_resource_id"].local_path,
                profiles_dir=self._profiles_dir,
                state_dir=resources["state_resource_id"].local_path,
                manifest_root=self._manifest_root,
                doc_services_root=self._doc_services_root,
                python_executable=self._python_executable,
                working_directory=self._working_directory,
            )
            plan = build_scheduler_registration_plan(
                handoff=handoff,
                store_path=resources["store_resource_id"].local_path,
                ledger_dir=resources["ledger_resource_id"].local_path,
                provider_root=self._scheduler_root,
                provider_revision=self._scheduler_revision,
                authorization_files=authorization_files,
            )
            if (
                registry_bytes is not None
                and dict(plan.configuration_files)[str(authorization_files[0])]
                != sha256(registry_bytes).hexdigest()
            ):
                raise ValueError("Ressourcenfreigabe wurde während des Ladens verändert.")
            watches = self._authorized_watches(plan, profile_id, registry)
            # Close the configuration-load window without inspecting document contents.
            current = build_scheduler_registration_plan(
                handoff=handoff,
                store_path=plan.store_path,
                ledger_dir=plan.ledger_dir,
                provider_root=plan.provider_root,
                provider_revision=plan.provider_revision,
                authorization_files=authorization_files,
            )
            if current != plan:
                raise ValueError("Konfiguration wurde während der Vorschau verändert.")
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            # Configuration/provider exceptions may contain physical paths. They
            # are useful locally, but never belong in a model-visible response.
            raise WorkflowExecutionError(
                "Scheduler-Vorschau abgewiesen: "
                "Konfiguration, Ressourcenrechte oder Provider prüfen."
            ) from exc
        public_plan = {
            "schema": self.descriptor.plan_schema,
            "registration_plan_id": plan.plan_id,
            "profile_id": profile_id,
            **{name: resource.resource_id for name, resource in resources.items()},
            "task_name": handoff.task_name,
            "interval_minutes": handoff.interval_minutes,
            "start_at": handoff.start_at,
            "timezone": handoff.timezone,
            "watches": watches,
            "provider_revision": plan.provider_revision,
            "live_effect_approved": self._allow_scheduler_write is True,
            "scheduler_registered": False,
            "consumer_status": "not_started",
            "document_actions_authorized": False,
            "paths_disclosed": False,
        }
        envelope = _resource_execution_envelope(
            descriptor=self.descriptor,
            domain_plan_id=plan.plan_id,
            public_plan=public_plan,
            approval_kind="explicit_scheduler_registration",
        )
        return envelope, _PreparedSchedulerRegistration(plan, profile_id, deepcopy(request))

    def _authorized_watches(self, plan, profile_id, registry):
        watches = load_watched_folder_configuration(plan.handoff.config_file).watches
        bindings = {
            item.watch_id: item
            for item in load_folder_routine_bindings(plan.handoff.bindings_file).bindings
            if item.enabled
        }
        result = []
        for watch in watches:
            if not watch.enabled:
                continue
            if watch.profile_id != profile_id or watch.watch_id not in bindings:
                raise ValueError("Aktiver Watch benötigt passendes Profil und aktive Bindung.")
            binding = bindings[watch.watch_id]
            source = self._directory_resource(
                registry,
                watch.source_root,
                profile_id,
                "routine_queue.source",
                {"read", "sensitive_read", "list"},
            )
            target = self._directory_resource(
                registry, binding.target_root, profile_id, "routine_queue.target", {"read", "list"}
            )
            result.append(
                {
                    "watch_id": watch.watch_id,
                    "binding_id": binding.binding_id,
                    "source_resource_id": source.resource_id,
                    "target_resource_id": target.resource_id,
                    "recursive": watch.recursive,
                    "mode": binding.mode.value,
                }
            )
        if not result:
            raise ValueError("Keine aktiven freigegebenen Watches.")
        return result

    def _directory_resource(self, registry, path, profile_id, purpose, operations):
        candidates = [
            resource
            for resource in registry.resources
            if resource.local_path == path
            and resource.kind == "directory"
            and purpose in resource.purposes
            and profile_id in resource.profile_ids
        ]
        if len(candidates) != 1:
            raise ValueError("Watch-Verzeichnis besitzt keine eindeutige logische Freigabe.")
        return registry.resolve(
            resource_id=candidates[0].resource_id,
            profile_id=profile_id,
            purpose=purpose,
            required_kind="directory",
            required_operations=frozenset(operations),
        )

    def execute(
        self, *, envelope: WorkflowExecutionEnvelope, domain_plan: object, approved_at: str
    ):
        if not isinstance(domain_plan, _PreparedSchedulerRegistration):
            raise WorkflowExecutionError(
                "Vorbereitete Scheduler-Registrierung besitzt falschen Typ."
            )
        if self._allow_scheduler_write is not True:
            raise WorkflowExecutionError(
                "Scheduler benötigt die getrennte Startfreigabe --approve-scheduler-write."
            )
        fresh_envelope, current = self.prepare(
            profile_id=domain_plan.profile_id, request=domain_plan.request
        )
        if (
            _canonical_json(fresh_envelope.to_dict()) != _canonical_json(envelope.to_dict())
            or current.plan != domain_plan.plan
        ):
            raise WorkflowExecutionError(
                "Scheduler-Freigabe ist veraltet oder verändert; neu planen."
            )
        try:
            result = register_scheduler_job(
                current.plan,
                confirmed_plan_id=current.plan.plan_id,
                allow_scheduler_write=True,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise WorkflowExecutionOutcomeUnknown(
                "Scheduler-Registrierung nicht bestätigt; "
                "privaten Nachweis prüfen, nicht blind wiederholen."
            ) from exc
        if result.status not in {"registered", "already_registered"}:
            raise WorkflowExecutionOutcomeUnknown(
                "Scheduler-Registrierung unklar; möglicherweise gespeichert. "
                "Privaten Nachweis prüfen."
            )
        return _resource_execution_report(
            envelope=envelope,
            descriptor=self.descriptor,
            approved_at=approved_at,
            public_report={
                "schema": self.descriptor.report_schema,
                "registration_plan_id": result.plan_id,
                "job_id": result.job_id,
                "status": result.status,
                "store_resource_id": current.request["store_resource_id"],
                "ledger_resource_id": current.request["ledger_resource_id"],
                "scheduler_registered": True,
                "consumer_status": result.consumer_status,
                "reconciled": result.reconciled,
                "document_actions_performed": False,
                "paths_disclosed": False,
            },
        )
