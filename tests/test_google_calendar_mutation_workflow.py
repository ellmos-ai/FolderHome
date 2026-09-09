"""Normal calendar adapter mutation plans, exact confirmation and resource revocation."""

from copy import deepcopy
from dataclasses import replace

import pytest
from test_google_calendar_mutations import MutationService
from test_google_calendar_workflow import setup as setup

from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionGateway,
    WorkflowExecutionOutcomeUnknown,
)


def prepare_existing(setup, operation):
    build, create_request, _, source, _, secret, ledger, registry = setup
    service = MutationService()
    adapter = build()
    adapter._transport_factory = lambda: service
    envelope, original = adapter.prepare(profile_id="lukas", request=create_request)
    adapter.execute(
        envelope=envelope, domain_plan=original, approved_at=create_request["planned_at"]
    )
    previous = original.plan.events[0]
    request = {
        key: create_request[key]
        for key in (
            "configuration_resource_id",
            "accounts_resource_id",
            "credential_resource_id",
            "ledger_resource_id",
            "account_id",
            "area",
        )
    }
    request.update(
        operation=operation,
        previous_event=previous.to_dict(),
        expected_etag='"v1"',
        replacement=replace(previous, title="Geprüfte Änderung", location=None).to_dict()
        if operation == "update"
        else None,
    )
    return adapter, request, service, source, secret, ledger, registry


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_mutation_preview_is_local_without_original_source_and_uses_exact_gateway_approval(
    setup, operation
):
    adapter, request, service, source, secret, _, _ = prepare_existing(setup, operation)
    for path in source.iterdir():
        path.unlink()
    source.rmdir()
    before_calls = deepcopy(service.calls)
    token_bytes = secret.read_bytes()
    secret.unlink()
    gateway = WorkflowExecutionGateway((adapter,))
    envelope = gateway.prepare(
        workflow_id="calendar-connectors", profile_id="lukas", request=request
    )
    assert not service.mutations and service.calls == before_calls
    assert envelope.domain_plan["operation"] == operation
    assert envelope.domain_plan["previous_event"] == request["previous_event"]
    assert envelope.domain_plan["replacement"] == request["replacement"]
    assert str(secret) not in str(envelope.to_dict())
    secret.write_bytes(token_bytes)
    result = gateway.execute(
        envelope_id=envelope.envelope_id, approved_at="2026-09-09T11:00:00+02:00"
    )
    assert result.domain_report["mutation"]["status"] == (
        "updated" if operation == "update" else "absent"
    )
    with pytest.raises(WorkflowExecutionError):
        gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T11:00:00+02:00")
    assert len(service.mutations) == 1


@pytest.mark.parametrize("change", ["gate", "permission", "request", "etag"])
def test_changed_mutation_approval_is_rejected_before_network(setup, change):
    adapter, request, service, _, _, _, registry = prepare_existing(setup, "update")
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    before_calls = deepcopy(service.calls)
    if change == "gate":
        adapter._allowed = False
    elif change == "permission":
        adapter._registry = replace(
            registry,
            resources=tuple(
                replace(item, operations=frozenset({"read"}))
                if item.resource_id == "google-ledger"
                else item
                for item in registry.resources
            ),
        )
    elif change == "request":
        envelope.domain_plan["replacement"]["title"] = "Not approved"
    else:
        envelope.domain_plan["expected_etag"] = '"other"'
    with pytest.raises(WorkflowExecutionError):
        adapter.execute(
            envelope=envelope, domain_plan=prepared, approved_at="2026-09-09T11:00:00+02:00"
        )
    assert service.calls == before_calls and not service.mutations


def test_uncertain_mutation_consumes_normal_workflow_approval(setup):
    adapter, request, service, *_ = prepare_existing(setup, "update")
    gateway = WorkflowExecutionGateway((adapter,))
    envelope = gateway.prepare(
        workflow_id="calendar-connectors", profile_id="lukas", request=request
    )
    service.mutation_timeout_before = True
    with pytest.raises(WorkflowExecutionOutcomeUnknown):
        gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T11:00:00+02:00")
    with pytest.raises(WorkflowExecutionError):
        gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T11:00:00+02:00")
    assert len(service.mutations) == 1


def normal_mutation_app(setup, tmp_path, monkeypatch, operation, gate=True):
    import json

    from folderhome import cli
    from folderhome.application import google_calendar_workflow
    from folderhome.application.recipes import build_recipe_plan
    from folderhome.contracts.recipes import CapabilityRecipe, CapabilityRecipeStep

    _, request, service, source, secret, _, registry = prepare_existing(setup, operation)
    second_profile = json.loads((tmp_path / "profiles" / "Lukas.json").read_text(encoding="utf-8"))
    second_profile.update(profile_id="hanna", display_name="Hanna Beispiel")
    (tmp_path / "profiles" / "Hanna.json").write_text(json.dumps(second_profile), encoding="utf-8")
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
    monkeypatch.setattr(google_calendar_workflow, "GoogleCalendarTransport", lambda: service)
    app = cli._prepare_local_app(args)
    try:
        recipe = CapabilityRecipe(
            recipe_id="synthetic-calendar-mutation",
            title_en="Mutation",
            title_de="Änderung",
            summary_en="One mutation",
            summary_de="Eine Änderung",
            lead_expert_id="communication_expert",
            steps=(
                CapabilityRecipeStep(
                    step_ref="mutation",
                    workflow_id="calendar-connectors",
                    expert_id="communication_expert",
                    goal_en=operation,
                    goal_de=operation,
                    request=request,
                ),
            ),
        )
        prepared = build_recipe_plan(
            recipe,
            profile_id="lukas",
            language="en",
            prepare=lambda workflow_id, request: app.workflow_executor.prepare(
                workflow_id=workflow_id,
                profile_id="lukas",
                request=request,
            ),
            endpoint_statuses={"calendar-connectors": "connected"},
            known_resource_ids=frozenset(item.resource_id for item in registry.resources),
        )
        app._retain_agent_plan(prepared.plan)
        body = json.dumps(
            {
                "schema": "folderhome.local-agent-confirmation-request.v1",
                "plan_id": prepared.plan_id,
                "plan_sha256": prepared.plan.plan_sha256,
                "step_ids": [step.step_id for step in prepared.plan.steps],
            }
        ).encode()
    except Exception:
        app.close()
        raise
    return app, body, service, registry_file, secret


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_normal_factory_api_delivers_and_retains_confirmed_mutation(
    setup, tmp_path, monkeypatch, operation
):
    from test_local_app import _api_headers

    app, body, service, _, secret = normal_mutation_app(setup, tmp_path, monkeypatch, operation)
    try:
        response = app.handle(
            method="POST",
            target="/api/v1/agent/confirm",
            headers=_api_headers(8765, app.session_token),
            body=body,
            server_port=8765,
        )
        assert response.status_code == 200
        mutation = response.payload["execution_reports"][0]["domain_report"]["mutation"]
        assert mutation["status"] == ("updated" if operation == "update" else "absent")
        results = app.execution_results_payload(profile_id="lukas", limit=25)["results"]
        assert results[0]["evidence"]["confirmed_mutation"] == mutation
        versions = response.payload["execution_reports"][0]["domain_report"]["event_versions"]
        assert results[0]["evidence"]["event_versions"] == versions
        if operation == "update":
            assert len(versions) == 1 and versions[0]["etag"] == mutation["etag"]
            assert versions[0]["event"]["title"] == "Geprüfte Änderung"
            results[0]["evidence"]["event_versions"][0]["event"]["title"] = "tampered"
            assert (
                app.execution_results_payload(profile_id="lukas", limit=25)["results"][0][
                    "evidence"
                ]["event_versions"]
                == versions
            )
        else:
            assert versions == []
        assert app.execution_results_payload(profile_id="hanna", limit=25)["results"] == []
        results[0]["evidence"]["confirmed_mutation"]["provider_event_id"] = "tampered"
        assert (
            app.execution_results_payload(profile_id="lukas", limit=25)["results"][0]["evidence"][
                "confirmed_mutation"
            ]
            == mutation
        )
        assert str(secret) not in str(response.payload) and "synthetic-token" not in str(
            response.payload
        )
        assert len(service.mutations) == 1
    finally:
        app.close()


@pytest.mark.parametrize("stage", ["gate", "before", "after_write", "after_receipt"])
def test_normal_api_revocation_preserves_unknown_and_partial_evidence(
    setup, tmp_path, monkeypatch, stage
):
    import json

    from test_local_app import _api_headers

    from folderhome.bridges import google_calendar_mutations

    app, body, service, registry_file, _ = normal_mutation_app(
        setup,
        tmp_path,
        monkeypatch,
        "update",
        gate=stage != "gate",
    )

    def revoke():
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        for item in data["resources"]:
            if item["resource_id"] == "google-ledger":
                item["operations"] = ["read"]
        registry_file.write_text(json.dumps(data), encoding="utf-8")

    if stage == "before":
        revoke()
    elif stage == "after_write":
        original = service.request

        def request_then_revoke(method, path, **kwargs):
            result = original(method, path, **kwargs)
            if method == "PATCH":
                revoke()
            return result

        service.request = request_then_revoke
    elif stage == "after_receipt":
        original = google_calendar_mutations._finish

        def finish_then_revoke(*args):
            original(*args)
            revoke()

        monkeypatch.setattr(google_calendar_mutations, "_finish", finish_then_revoke)
    try:
        response = app.handle(
            method="POST",
            target="/api/v1/agent/confirm",
            headers=_api_headers(8765, app.session_token),
            body=body,
            server_port=8765,
        )
        if stage in {"gate", "before"}:
            assert response.status_code >= 400
            assert not service.mutations
        else:
            assert response.status_code == 409
            retained = app.execution_results_payload(profile_id="lukas", limit=25)["results"][0]
            assert retained["status"] == "uncertain" and retained["retry_safe"] is False
            partial = retained["evidence"]["confirmed_mutation"]
            assert (partial is not None) is (stage == "after_receipt")
            if partial:
                assert partial["status"] == "updated"
                partial["provider_event_id"] = "tampered"
                assert (
                    app.execution_results_payload(profile_id="lukas", limit=25)["results"][0][
                        "evidence"
                    ]["confirmed_mutation"]["provider_event_id"]
                    != "tampered"
                )
            assert len(service.mutations) == 1
            calls = len(service.calls)
            repeated = app.handle(
                method="POST",
                target="/api/v1/agent/confirm",
                headers=_api_headers(8765, app.session_token),
                body=body,
                server_port=8765,
            )
            assert repeated.status_code >= 400 and len(service.calls) == calls
    finally:
        app.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_etag", "*"),
        ("operation", "create"),
        ("operation", []),
        ("previous_event", {}),
        ("replacement", None),
        ("extra", "unexpected"),
    ],
)
def test_invalid_mutation_request_is_rejected_without_credential_or_provider_io(
    setup, field, value
):
    adapter, request, service, _, secret, _, _ = prepare_existing(setup, "update")
    request[field] = value
    secret.unlink()
    calls = deepcopy(service.calls)
    with pytest.raises(WorkflowExecutionError):
        adapter.prepare(profile_id="lukas", request=request)
    assert not service.mutations and service.calls == calls


def test_create_report_supplies_a_version_reference_for_followup_without_database_access(setup):
    build, request, *_ = setup
    adapter = build()
    service = MutationService()
    adapter._transport_factory = lambda: service
    envelope, original = adapter.prepare(profile_id="lukas", request=request)
    result = adapter.execute(
        envelope=envelope, domain_plan=original, approved_at=request["planned_at"]
    )
    version = result.domain_report["event_versions"][0]
    assert version["schema"] == "folderhome.google-calendar-event-version.v1"
    assert version["event"] == original.plan.events[0].to_dict()
    assert version["etag"] == '"v1"'
    assert version["provider_event_id"] in service.events
    next_request = {
        key: request[key]
        for key in (
            "configuration_resource_id",
            "accounts_resource_id",
            "credential_resource_id",
            "ledger_resource_id",
            "account_id",
            "area",
        )
    }
    next_request.update(
        operation="delete",
        previous_event=version["event"],
        expected_etag=version["etag"],
        replacement=None,
    )
    deletion, prepared = adapter.prepare(profile_id="lukas", request=next_request)
    assert (
        adapter.execute(
            envelope=deletion, domain_plan=prepared, approved_at=request["planned_at"]
        ).domain_report["mutation"]["status"]
        == "absent"
    )


def test_changed_mutation_version_after_receipt_is_uncertain_not_a_new_version_claim(
    setup, monkeypatch
):
    from folderhome.application import google_calendar_mutation_workflow as workflow

    adapter, request, service, *_ = prepare_existing(setup, "update")
    original = workflow.confirmed_event_version

    def changed_version(*args):
        version = original(*args)
        version["etag"] = '"newer-version"'
        return version

    monkeypatch.setattr(workflow, "confirmed_event_version", changed_version)
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    with pytest.raises(WorkflowExecutionOutcomeUnknown) as raised:
        adapter.execute(
            envelope=envelope, domain_plan=prepared, approved_at="2026-09-09T11:00:00+02:00"
        )
    assert raised.value.public_evidence()["confirmed_mutation"]["etag"] != '"newer-version"'
    assert len(service.mutations) == 1


@pytest.mark.parametrize("change", ["hash", "deleted", "weak_etag"])
def test_create_version_lookup_rejects_unconfirmed_or_changed_receipts(setup, monkeypatch, change):
    from folderhome.application import google_calendar_mutation_workflow as workflow

    build, request, *_ = setup
    adapter = build()
    service = MutationService()
    adapter._transport_factory = lambda: service
    original = workflow._read_version

    def changed_receipt(*args):
        fingerprint, status, etag = original(*args)
        return (
            "0" * 64 if change == "hash" else fingerprint,
            "deleted" if change == "deleted" else status,
            'W/"v1"' if change == "weak_etag" else etag,
        )

    monkeypatch.setattr(workflow, "_read_version", changed_receipt)
    envelope, prepared = adapter.prepare(profile_id="lukas", request=request)
    with pytest.raises(WorkflowExecutionOutcomeUnknown) as raised:
        adapter.execute(envelope=envelope, domain_plan=prepared, approved_at=request["planned_at"])
    assert len(raised.value.public_evidence()["confirmed_event_references"]) == 1


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("operation", ["update", "delete"])
def test_normal_cli_session_exposes_mutation_receipts_and_followup_versions(
    setup,
    tmp_path,
    monkeypatch,
    capsys,
    as_json,
    operation,
):
    import json
    from argparse import Namespace
    from io import StringIO

    from folderhome import cli

    app, body, service, _, secret = normal_mutation_app(setup, tmp_path, monkeypatch, operation)
    plan_id = json.loads(body)["plan_id"]
    monkeypatch.setattr(cli, "_prepare_local_app", lambda args: app)
    monkeypatch.setattr(cli.sys, "stdin", StringIO(f"/confirm {plan_id}\n/quit\n"))
    try:
        assert cli._run_strands_agent_session(Namespace(profile_id="lukas", as_json=as_json)) == 0
        output = capsys.readouterr().out
        assert "folderhome.google-calendar-mutation-result.v1" in output
        if operation == "update":
            assert "folderhome.google-calendar-event-version.v1" in output
            assert "Geprüfte Änderung" in output
        assert str(secret) not in output and "synthetic-token" not in output
        assert len(service.mutations) == 1
    finally:
        app.close()
