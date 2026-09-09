from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from test_scheduler_registration_plan import registration_inputs as registration_inputs

from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionGateway,
)
from folderhome.contracts.resources import LogicalResource, ResourceRegistry


@pytest.fixture
def scheduler_environment(registration_inputs):
    inputs = registration_inputs
    handoff = inputs["handoff"]
    base = handoff.config_file.parent
    bindings = json.loads(handoff.bindings_file.read_text(encoding="utf-8"))
    bindings["bindings"][0]["target_dir"] = str(base / "routine-target")
    handoff.bindings_file.write_text(json.dumps(bindings), encoding="utf-8")
    definitions = (
        ("sched_watches", "file", handoff.config_file, "scheduler.watches", {"read"}),
        ("sched_bindings", "file", handoff.bindings_file, "scheduler.bindings", {"read"}),
        (
            "sched_store",
            "sqlite_store",
            inputs["store_path"],
            "scheduler.store",
            {"read", "state_write"},
        ),
        (
            "sched_ledger",
            "directory",
            inputs["ledger_dir"],
            "scheduler.ledger",
            {"read", "state_write"},
        ),
        ("sched_state", "directory", handoff.state_dir, "scheduler.state", {"read", "state_write"}),
        (
            "queue_source",
            "directory",
            base / "documents/inbox",
            "routine_queue.source",
            {"read", "sensitive_read", "list"},
        ),
        (
            "queue_target",
            "directory",
            base / "routine-target",
            "routine_queue.target",
            {"read", "list"},
        ),
    )
    profiles = load_profile_configuration(handoff.profiles_dir)
    registry = ResourceRegistry(
        os_account=profiles.os_account,
        known_profile_ids=frozenset(item.profile_id for item in profiles.profiles),
        profile_defaults={},
        resources=tuple(
            LogicalResource(
                resource_id=rid,
                kind=kind,
                local_path=path,
                purposes=frozenset({purpose}),
                operations=frozenset(operations),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            )
            for rid, kind, path, purpose, operations in definitions
        ),
    )
    request = {
        "watches_resource_id": "sched_watches",
        "bindings_resource_id": "sched_bindings",
        "store_resource_id": "sched_store",
        "ledger_resource_id": "sched_ledger",
        "state_resource_id": "sched_state",
        "task_name": "synthetic_queue",
        "interval_minutes": 30,
        "start_at": "2026-09-10T08:00:00+02:00",
        "timezone": "Europe/Berlin",
        "allow_sensitive_local_read": True,
    }
    return inputs, registry, request


def _adapter(environment, *, gate=True, registry=None, resource_registry_file=None):
    from folderhome.application.scheduler_workflow import SchedulerRegistrationWorkflowAdapter

    inputs, original_registry, _ = environment
    handoff = inputs["handoff"]
    return SchedulerRegistrationWorkflowAdapter(
        registry=registry or original_registry,
        profiles_dir=handoff.profiles_dir,
        manifest_root=handoff.manifest_root,
        doc_services_root=handoff.doc_services_root,
        scheduler_root=inputs["provider_root"],
        scheduler_revision=inputs["provider_revision"],
        python_executable=handoff.python_executable,
        working_directory=handoff.working_directory,
        allow_scheduler_write=gate,
        resource_registry_file=resource_registry_file,
    )


def _prepare(gateway, request):
    return gateway.prepare(workflow_id="scheduler-handoff", profile_id="lukas", request=request)


def test_scheduler_preview_is_path_free_and_creates_no_scheduler_state(scheduler_environment):
    inputs, _, request = scheduler_environment
    gateway = WorkflowExecutionGateway((_adapter(scheduler_environment),))
    envelope = _prepare(gateway, request)
    serialized = json.dumps(envelope.to_dict())
    assert json.dumps(str(inputs["handoff"].config_file.parent))[1:-1] not in serialized
    assert json.dumps(str(inputs["provider_root"]))[1:-1] not in serialized
    assert "python_executable" not in serialized
    assert envelope.domain_plan["scheduler_registered"] is False
    assert envelope.domain_plan["consumer_status"] == "not_started"
    assert envelope.domain_plan["watches"][0]["source_resource_id"] == "queue_source"
    assert envelope.side_effects == ("external.scheduler.write",)
    assert not inputs["store_path"].exists()
    assert not inputs["ledger_dir"].exists()
    assert not inputs["handoff"].state_dir.exists()


def test_confirmed_scheduler_adapter_registers_real_job_without_starting_consumer(
    scheduler_environment,
):
    inputs, _, request = scheduler_environment
    statuses = []
    for _ in range(2):
        gateway = WorkflowExecutionGateway((_adapter(scheduler_environment),))
        envelope = _prepare(gateway, request)
        report = gateway.execute(
            envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z"
        )
        statuses.append(report.domain_report["status"])
        assert report.domain_report["consumer_status"] == "not_observed"
        assert report.domain_report["scheduler_registered"] is True
        assert "attempt_file" not in json.dumps(report.to_dict())
        assert json.dumps(str(inputs["store_path"].parent.parent))[1:-1] not in json.dumps(
            report.to_dict()
        )
        with pytest.raises(WorkflowExecutionError):
            gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:01:00Z")
    assert statuses == ["registered", "already_registered"]
    with sqlite3.connect(inputs["store_path"]) as connection:
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    assert not inputs["handoff"].state_dir.exists()


@pytest.mark.parametrize("gate", [False, 1, "true"])
def test_scheduler_adapter_requires_strict_startup_write_gate(scheduler_environment, gate):
    inputs, _, request = scheduler_environment
    gateway = WorkflowExecutionGateway((_adapter(scheduler_environment, gate=gate),))
    envelope = _prepare(gateway, request)
    with pytest.raises(WorkflowExecutionError):
        gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z")
    assert not inputs["store_path"].exists()
    assert not inputs["ledger_dir"].exists()


@pytest.mark.parametrize(
    "mutation", ["raw_path", "profile", "source_rights", "unregistered_target", "sensitive_gate"]
)
def test_scheduler_configuration_cannot_expand_logical_resource_authority(
    scheduler_environment, mutation
):
    inputs, registry, request = scheduler_environment
    if mutation == "raw_path":
        request["python_executable"] = "unapproved-python"
    elif mutation == "profile":
        path = inputs["handoff"].config_file
        data = json.loads(path.read_text(encoding="utf-8"))
        data["watches"][0]["profile_id"] = "hanna"
        path.write_text(json.dumps(data), encoding="utf-8")
    elif mutation == "source_rights":
        registry = replace(
            registry,
            resources=tuple(
                replace(resource, operations=frozenset({"read", "list"}))
                if resource.resource_id == "queue_source"
                else resource
                for resource in registry.resources
            ),
        )
    elif mutation == "unregistered_target":
        registry = replace(
            registry,
            resources=tuple(
                resource
                for resource in registry.resources
                if resource.resource_id != "queue_target"
            ),
        )
    else:
        request["allow_sensitive_local_read"] = False
    gateway = WorkflowExecutionGateway((_adapter(scheduler_environment, registry=registry),))
    with pytest.raises(WorkflowExecutionError):
        _prepare(gateway, request)
    assert not inputs["store_path"].exists()


@pytest.mark.parametrize("mutation", ["configuration", "public_plan", "registry"])
def test_scheduler_adapter_revalidates_before_the_confirmed_insert(scheduler_environment, mutation):
    inputs, registry, request = scheduler_environment
    adapter = _adapter(scheduler_environment)
    gateway = WorkflowExecutionGateway((adapter,))
    envelope = _prepare(gateway, request)
    if mutation == "configuration":
        path = inputs["handoff"].config_file
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "public_plan":
        envelope.domain_plan["interval_minutes"] = 5
    else:
        adapter._registry = replace(
            registry,
            resources=tuple(
                resource
                for resource in registry.resources
                if resource.resource_id != "queue_source"
            ),
        )
    with pytest.raises(WorkflowExecutionError):
        gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z")
    assert not inputs["store_path"].exists()
    assert not inputs["ledger_dir"].exists()


def _persist_registry(scheduler_environment):
    inputs, registry, request = scheduler_environment
    path = inputs["handoff"].config_file.parent / "resources.json"
    for resource in registry.resources:
        if resource.kind == "directory":
            resource.local_path.mkdir(parents=True, exist_ok=True)
        elif resource.kind == "sqlite_store":
            resource.local_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": ResourceRegistry.SCHEMA,
        "os_account": registry.os_account,
        "profile_defaults": {},
        "resources": [
            {
                "resource_id": item.resource_id,
                "kind": item.kind,
                "locator": {"type": "local_path", "path": str(item.local_path)},
                "operations": sorted(item.operations),
                "purposes": sorted(item.purposes),
                "profile_ids": sorted(item.profile_ids),
                "cloud_context": item.cloud_context,
            }
            for item in registry.resources
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_scheduler_reloads_and_binds_persisted_resource_authority(scheduler_environment):
    from folderhome.application.scheduler_consumer import create_scheduler_consumer

    inputs, _, request = scheduler_environment
    path, payload = _persist_registry(scheduler_environment)
    adapter = _adapter(scheduler_environment, resource_registry_file=path)
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    assert path in prepared.plan.authorization_files
    adapter.execute(envelope=envelope, domain_plan=prepared, approved_at="2026-09-09T06:00:00Z")
    consumer = create_scheduler_consumer(
        prepared.plan,
        confirmed_plan_id=prepared.plan.plan_id,
        allow_consumer_state_write=True,
    )
    assert consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))[0]["status"] == "succeeded"
    payload["resources"] = [
        item for item in payload["resources"] if item["resource_id"] != "queue_source"
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkflowExecutionError):
        adapter.prepare(profile_id="lukas", request=request)
    from folderhome.application.scheduler_registration import SchedulerRegistrationError

    with pytest.raises(SchedulerRegistrationError):
        consumer.tick()
    with sqlite3.connect(inputs["store_path"]) as connection:
        assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 1


@pytest.mark.parametrize("gate", [False, True])
def test_normal_app_factory_connects_scheduler_resources_with_separate_gate(
    scheduler_environment, gate
):
    from folderhome import cli

    inputs, _, request = scheduler_environment
    registry_path, _ = _persist_registry(scheduler_environment)
    app_state = inputs["handoff"].config_file.parent / "app-state"
    app_state.mkdir()
    args = cli._build_parser().parse_args(
        [
            "app",
            "plan",
            "--profiles-dir",
            str(inputs["handoff"].profiles_dir),
            "--state-dir",
            str(app_state),
            "--resources-file",
            str(registry_path),
            "--manifest-root",
            str(inputs["handoff"].manifest_root),
            "--doc-services-root",
            str(inputs["handoff"].doc_services_root),
            "--scheduler-root",
            str(inputs["provider_root"]),
            *(["--approve-scheduler-write"] if gate else []),
        ]
    )
    app = cli._prepare_local_app(args)
    assert app.workflow_executor.descriptor("scheduler-handoff").status == "connected"
    envelope = _prepare(app.workflow_executor, request)
    assert not inputs["store_path"].exists()
    if gate:
        result = app.workflow_executor.execute(
            envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z"
        )
        assert result.domain_report["status"] == "registered"
        with sqlite3.connect(inputs["store_path"]) as connection:
            assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    else:
        with pytest.raises(WorkflowExecutionError):
            app.workflow_executor.execute(
                envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z"
            )
        assert not inputs["store_path"].exists()


@pytest.mark.parametrize("route", ["recipe", "http"])
@pytest.mark.parametrize("outcome", ["uncertain", "exception_after_commit", "gate_denied"])
def test_scheduler_unknown_effect_survives_the_application_boundary(
    scheduler_environment, tmp_path, monkeypatch, route, outcome
):
    from test_local_app import _api_headers, _app

    from folderhome.application import scheduler_workflow
    from folderhome.application.recipes import build_recipe_plan
    from folderhome.contracts.recipes import CapabilityRecipe, CapabilityRecipeStep

    inputs, registry, request = scheduler_environment
    gateway = WorkflowExecutionGateway(
        (_adapter(scheduler_environment, gate=outcome != "gate_denied"),)
    )
    recipe = CapabilityRecipe(
        recipe_id="scheduler-review",
        title_en="Synthetic scheduler",
        title_de="Synthetischer Scheduler",
        summary_en="One synthetic registration",
        summary_de="Eine synthetische Registrierung",
        lead_expert_id="system_expert",
        steps=(
            CapabilityRecipeStep(
                step_ref="register",
                workflow_id="scheduler-handoff",
                expert_id="system_expert",
                goal_en="Register synthetic queue",
                goal_de="Synthetische Queue registrieren",
                request=request,
            ),
        ),
    )
    recipe_plan = build_recipe_plan(
        recipe,
        profile_id="lukas",
        language="en",
        prepare=lambda workflow_id, request: gateway.prepare(
            workflow_id=workflow_id, profile_id="lukas", request=request
        ),
        endpoint_statuses={"scheduler-handoff": "connected"},
        known_resource_ids=frozenset(item.resource_id for item in registry.resources),
    )
    app = _app(tmp_path)
    app.workflow_executor = gateway
    app.resource_registry = registry
    app._retain_agent_plan(recipe_plan.plan)
    if route == "recipe":
        app._recipe_plans[recipe_plan.plan_id] = recipe_plan
    original = scheduler_workflow.register_scheduler_job

    def committed_but_unknown(*args, **kwargs):
        result = original(*args, **kwargs)
        assert result.status == "registered"
        if outcome == "exception_after_commit":
            raise OSError("C:/private/scheduler-secret.json")
        return replace(result, status="uncertain", error="C:/private/scheduler-secret.json")

    monkeypatch.setattr(scheduler_workflow, "register_scheduler_job", committed_but_unknown)
    confirmation = {
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": recipe_plan.plan_id,
        "plan_sha256": recipe_plan.plan.plan_sha256,
        "step_ids": [step.step_id for step in recipe_plan.plan.steps],
    }
    response = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(8765, app.session_token),
        body=json.dumps(confirmation).encode("utf-8"),
        server_port=8765,
    )
    assert "scheduler-secret" not in json.dumps(response.payload)
    if outcome == "gate_denied":
        assert not inputs["store_path"].exists()
        assert response.payload.get("execution_outcome_unknown", False) is False
    else:
        with sqlite3.connect(inputs["store_path"]) as connection:
            assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
        assert response.payload["execution_outcome_unknown"] is True
        if route == "recipe":
            assert response.payload["result_delivery_incomplete"] is True
        else:
            assert response.status_code == 409
            assert response.payload["status"] == "uncertain"
