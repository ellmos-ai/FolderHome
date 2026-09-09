"""Normal resource workflow, real domain plans and synthetic Google transport."""

from __future__ import annotations

import importlib
import json
from dataclasses import replace

import pytest

from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionOutcomeUnknown,
)
from folderhome.contracts.resources import LogicalResource, ResourceRegistry


def api():
    assert importlib.util.find_spec("folderhome.application.google_calendar_workflow") is not None
    return importlib.import_module("folderhome.application.google_calendar_workflow")


@pytest.fixture
def setup(tmp_path):
    from test_calendar_handoff import (
        SyntheticExtractor,
        _write_calendar_configuration,
        _write_event,
        _write_profile_configuration,
    )
    from test_google_calendar_gateway import CalendarService

    source = tmp_path / "source"
    source.mkdir()
    _write_event(source / "event.txt")
    configuration = _write_calendar_configuration(tmp_path / "config", backend="google")
    profiles = tmp_path / "profiles"
    _write_profile_configuration(profiles)
    accounts = tmp_path / "accounts.json"
    accounts.write_text(
        json.dumps(
            {
                "schema": "folderhome.calendar-connector-accounts.v1",
                "accounts": [
                    {
                        "account_id": "google-lukas",
                        "profile_id": "lukas",
                        "backend": "google",
                        "display_name": "Synthetic",
                        "provider_id": "google-calendar",
                        "provider_revision": "v3",
                        "calendar_id": "synthetic@example.invalid",
                        "credential_ref": "connector://google-calendar/google-secret",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    secret = tmp_path / "secret.json"
    secret.write_text(
        json.dumps(
            {
                "token": "synthetic-token",
                "expiry": "2100-01-01T00:00:00Z",
                "refresh_token": "synthetic-refresh",
                "client_id": "synthetic-client",
                "client_secret": "synthetic-secret",
                "type": "authorized_user",
                "scopes": ["https://www.googleapis.com/auth/calendar.events"],
            }
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "ledger"
    resources = tuple(
        LogicalResource(
            resource_id=rid,
            local_path=path,
            kind=kind,
            purposes=frozenset({purpose}),
            operations=frozenset(operations),
            profile_ids=frozenset({"lukas"}),
            cloud_context="deny",
        )
        for rid, path, kind, purpose, operations in [
            ("google-source", source, "directory", "calendar.source", {"list", "read"}),
            ("google-config", configuration, "file", "calendar.configuration", {"read"}),
            ("google-accounts", accounts, "file", "calendar.connector_accounts", {"read"}),
            ("google-secret", secret, "file", "calendar.google_credentials", {"read"}),
            (
                "google-ledger",
                ledger,
                "directory",
                "calendar.connector_ledger",
                {"read", "state_write"},
            ),
        ]
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=resources,
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    request = {
        "source_resource_id": "google-source",
        "configuration_resource_id": "google-config",
        "accounts_resource_id": "google-accounts",
        "credential_resource_id": "google-secret",
        "ledger_resource_id": "google-ledger",
        "account_id": "google-lukas",
        "area": "gesundheit",
        "planned_at": "2026-09-09T09:00:00+02:00",
        "recursive": True,
        "allow_sensitive_local_read": False,
        "reminders": [{"method": "popup", "minutes_before": 60}],
    }
    service = CalendarService()

    def build_adapter():
        return api().GoogleCalendarWorkflowAdapter(
            registry=registry,
            profiles_dir=profiles,
            extractor=SyntheticExtractor(),
            allow_calendar_write=True,
            transport_factory=lambda: service,
        )

    return build_adapter, request, service, source, accounts, secret, ledger, registry


def test_resource_preview_does_not_read_credentials_and_executes_after_exact_confirmation(setup):
    adapter, request, service, source, accounts, secret, ledger, registry = setup
    adapter = adapter()
    content = secret.read_bytes()
    secret.unlink()
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    assert not ledger.exists() and not service.calls
    assert str(secret) not in json.dumps(envelope.to_dict())
    secret.write_bytes(content)
    report = adapter.execute(
        envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"]
    )
    assert report.domain_report["status"] == "executed"
    assert report.domain_report["event_references"][0]["provider_event_id"] in service.events
    assert str(source) not in json.dumps(report.to_dict())


@pytest.mark.parametrize(
    "change", ["source", "account", "permissions", "envelope", "gate", "secret_binding"]
)
def test_stale_input_permissions_and_missing_gate_stop_before_google(setup, change):
    adapter, request, service, source, accounts, secret, ledger, registry = setup
    adapter = adapter()
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    if change == "source":
        (source / "event.txt").write_text("Termin: Changed", encoding="utf-8")
    elif change in {"account", "secret_binding"}:
        value = json.loads(accounts.read_text(encoding="utf-8"))
        value["accounts"][0]["calendar_id" if change == "account" else "credential_ref"] = (
            "foreign@example.invalid"
            if change == "account"
            else "connector://google-calendar/other"
        )
        accounts.write_text(json.dumps(value), encoding="utf-8")
    elif change == "permissions":
        adapter._registry = replace(
            registry,
            resources=tuple(
                replace(item, operations=frozenset({"list"}))
                if item.resource_id == "google-source"
                else item
                for item in registry.resources
            ),
        )
    elif change == "envelope":
        envelope.domain_plan["account_id"] = "other"
    else:
        adapter._allowed = False
    with pytest.raises(WorkflowExecutionError):
        adapter.execute(envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"])
    assert not service.calls and not ledger.exists()


def test_unknown_effect_remains_typed_at_workflow_boundary(setup):
    adapter, request, service, *_ = setup
    adapter = adapter()
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    service.timeout_before_write = True
    with pytest.raises(WorkflowExecutionOutcomeUnknown):
        adapter.execute(envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"])
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


def test_document_changed_during_readback_blocks_the_post(setup):
    adapter, request, service, source, *_ = setup
    adapter = adapter()
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    actual = service.request

    def request_then_change(method, path, **kwargs):
        result = actual(method, path, **kwargs)
        (source / "event.txt").write_text("Changed after GET", encoding="utf-8")
        return result

    service.request = request_then_change
    with pytest.raises(WorkflowExecutionError):
        adapter.execute(envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"])
    assert all(method == "GET" for method, _, _ in service.calls)


def test_document_change_after_post_is_unknown_not_an_ordinary_rejection(setup):
    adapter, request, service, source, *_ = setup
    adapter = adapter()
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    actual = service.request

    def request_then_change(method, path, **kwargs):
        result = actual(method, path, **kwargs)
        if method == "POST":
            (source / "event.txt").write_text("Changed after POST", encoding="utf-8")
        return result

    service.request = request_then_change
    with pytest.raises(WorkflowExecutionOutcomeUnknown):
        adapter.execute(envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"])
    assert len(service.events) == 1


@pytest.mark.parametrize("change", ["source", "ledger_permission"])
def test_changed_binding_during_final_get_cannot_commit_confirmation(setup, change):
    import sqlite3

    adapter, request, service, source, accounts, secret, ledger, registry = setup
    adapter = adapter()
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    actual = service.request

    def request_then_change(method, path, **kwargs):
        result = actual(method, path, **kwargs)
        if method == "GET" and result[0] == 200:
            if change == "source":
                (source / "event.txt").write_text("Changed during final GET", encoding="utf-8")
            else:
                adapter._registry = replace(
                    registry,
                    resources=tuple(
                        replace(item, operations=frozenset({"read"}))
                        if item.resource_id == "google-ledger"
                        else item
                        for item in registry.resources
                    ),
                )
        return result

    service.request = request_then_change
    with pytest.raises(WorkflowExecutionOutcomeUnknown):
        adapter.execute(envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"])
    assert len(service.events) == 1
    with sqlite3.connect(ledger / "google-calendar.sqlite3") as connection:
        assert connection.execute("SELECT status FROM calendar_creations").fetchall() == [
            ("pending",)
        ]


@pytest.mark.parametrize("gate,revoked", [(False, False), (True, False), (True, True)])
def test_normal_app_factory_wires_google_resources_with_separate_gate(
    setup, tmp_path, monkeypatch, gate, revoked
):
    from folderhome import cli

    build, request, service, source, accounts, secret, ledger, registry = setup
    ledger.mkdir()
    registry_file = tmp_path / "resources.json"
    registry_file.write_text(
        json.dumps(
            {
                "schema": registry.SCHEMA,
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
        ),
        encoding="utf-8",
    )
    state = tmp_path / "app-state"
    state.mkdir()
    args = cli._build_parser().parse_args(
        [
            "app",
            "plan",
            "--profiles-dir",
            str(tmp_path / "profiles"),
            "--state-dir",
            str(state),
            "--resources-file",
            str(registry_file),
            *(["--approve-calendar-write"] if gate else []),
        ]
    )
    monkeypatch.setattr(api(), "GoogleCalendarTransport", lambda: service)
    app = cli._prepare_local_app(args)
    try:
        assert app.workflow_executor.descriptor("calendar-connectors").status == "connected"
        envelope = app.workflow_executor.prepare(
            workflow_id="calendar-connectors", profile_id="lukas", request=request
        )
        assert not service.calls
        if revoked:
            current = json.loads(registry_file.read_text(encoding="utf-8"))
            for resource in current["resources"]:
                if resource["resource_id"] == "google-ledger":
                    resource["operations"] = ["read"]
            registry_file.write_text(json.dumps(current), encoding="utf-8")
        if gate and not revoked:
            report = app.workflow_executor.execute(
                envelope_id=envelope.envelope_id, approved_at=request["planned_at"]
            )
            assert report.domain_report["status"] == "executed"
            assert len(service.events) == 1
        else:
            with pytest.raises(WorkflowExecutionError):
                app.workflow_executor.execute(
                    envelope_id=envelope.envelope_id, approved_at=request["planned_at"]
                )
            assert not service.calls
    finally:
        app.close()


@pytest.mark.parametrize("route", ["ordinary", "recipe"])
@pytest.mark.parametrize("confirmed_count", [0, 1])
def test_app_retains_only_confirmed_calendar_references_after_uncertain_write(
    setup, tmp_path, route, confirmed_count
):
    from test_calendar_handoff import _write_event
    from test_local_app import _api_headers, _app

    from folderhome.application.recipes import build_recipe_plan
    from folderhome.application.workflow_execution import WorkflowExecutionGateway
    from folderhome.contracts.recipes import CapabilityRecipe, CapabilityRecipeStep

    build, request, service, source, accounts, secret, ledger, registry = setup
    _write_event(source / "second.txt", title="Zweiter Termin", event_date="15.09.2026")
    gateway = WorkflowExecutionGateway((build(),))
    recipe = CapabilityRecipe(
        recipe_id="synthetic-calendar", title_en="Calendar", title_de="Kalender",
        summary_en="Two appointments", summary_de="Zwei Termine",
        lead_expert_id="communication_expert",
        steps=(CapabilityRecipeStep(
            step_ref="calendar", workflow_id="calendar-connectors",
            expert_id="communication_expert", goal_en="Create", goal_de="Erstellen",
            request=request,
        ),),
    )
    prepared = build_recipe_plan(
        recipe, profile_id="lukas", language="en",
        prepare=lambda workflow_id, request: gateway.prepare(
            workflow_id=workflow_id, profile_id="lukas", request=request,
        ),
        endpoint_statuses={"calendar-connectors": "connected"},
        known_resource_ids=frozenset(item.resource_id for item in registry.resources),
    )
    app = _app(tmp_path)
    app.workflow_executor = gateway
    app.resource_registry = registry
    app._retain_agent_plan(prepared.plan)
    if route == "recipe":
        app._recipe_plans[prepared.plan_id] = prepared
    actual = service.request

    def lose_readback_after_write(method, path, **kwargs):
        value = actual(method, path, **kwargs)
        if method == "POST" and len(service.events) > confirmed_count:
            service.unreadable = True
        return value

    service.request = lose_readback_after_write
    body = json.dumps({
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": prepared.plan_id, "plan_sha256": prepared.plan.plan_sha256,
        "step_ids": [step.step_id for step in prepared.plan.steps],
    }).encode("utf-8")
    try:
        response = app.handle(
            method="POST", target="/api/v1/agent/confirm",
            headers=_api_headers(8765, app.session_token), body=body, server_port=8765,
        )
        assert response.status_code == (409 if route == "ordinary" else 200)
        assert response.payload["execution_outcome_unknown"] is True
        results = app.execution_results_payload(profile_id="lukas", limit=25)["results"]
        assert len(results) == 1, "Uncertain runs must remain visible in the result list"
        result = results[0]
        assert result["status"] == "uncertain" and result["retry_safe"] is False
        assert result["plan_id"] == prepared.plan_id
        assert result["profile_id"] == "lukas"
        assert result["workflow_id"] == "calendar-connectors"
        assert result["artifacts"] == []
        refs = result["evidence"]["confirmed_event_references"]
        assert len(refs) == confirmed_count
        assert all(ref["provider_event_id"] in service.events for ref in refs)
        assert len(service.events) == confirmed_count + 1  # Not the confirmed count!
        assert response.payload["uncertain_results"] == results
        assert app.execution_results_payload(profile_id="hanna", limit=25)["results"] == []
        public = json.dumps(response.payload) + json.dumps(results)
        assert str(secret) not in public and "synthetic-token" not in public
        assert "private readback text" not in public
        if confirmed_count:
            response.payload["uncertain_results"][0]["evidence"]["confirmed_event_references"][0][
                "provider_event_id"
            ] = "NEVER-CONFIRMED"
            results[0]["evidence"]["confirmed_event_references"].clear()
            retained = app.execution_results_payload(profile_id="lukas", limit=25)["results"]
            retained_refs = retained[0]["evidence"]["confirmed_event_references"]
            assert len(retained_refs) == 1, "Returned evidence must not mutate retained evidence"
            assert retained_refs[0]["provider_event_id"] in service.events
        calls = len(service.calls)
        repeated = app.handle(
            method="POST", target="/api/v1/agent/confirm",
            headers=_api_headers(8765, app.session_token), body=body, server_port=8765,
        )
        assert repeated.status_code >= 400
        assert len(service.calls) == calls
    finally:
        app.close()
