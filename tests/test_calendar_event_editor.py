"""Guided event editing uses actual session receipts, never client-supplied identities."""

import json

import pytest
from test_google_calendar_mutation_workflow import normal_mutation_app
from test_google_calendar_workflow import setup as setup
from test_local_app import _api_headers


@pytest.fixture
def editor(setup, tmp_path, monkeypatch):
    app, body, service, registry_file, secret = normal_mutation_app(
        setup,
        tmp_path,
        monkeypatch,
        "update",
    )
    response = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(8765, app.session_token),
        body=body,
        server_port=8765,
    )
    assert response.status_code == 200
    result = app.execution_results_payload(profile_id="lukas", limit=25)["results"][0]
    request = {
        "schema": "folderhome.calendar-event-edit-request.v1",
        "profile_id": "lukas",
        "execution_id": result["execution_id"],
        "version_index": 0,
        "operation": "update",
        "changes": {"title": "Neuer geprüfter Titel"},
        "language": "de",
    }
    yield app, request, service, registry_file, secret
    app.close()


def post(app, request, **kwargs):
    return app.handle(
        method="POST",
        target="/api/v1/agent/calendar/plan",
        headers=kwargs.get("headers", _api_headers(8765, app.session_token)),
        body=json.dumps(request).encode(),
        server_port=8765,
    )


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_editor_prepares_without_network_then_uses_normal_exact_confirmation(editor, operation):
    app, request, service, _, secret = editor
    request.update(operation=operation, changes={} if operation == "delete" else request["changes"])
    old_calls = len(service.calls)
    response = post(app, request)
    assert response.status_code == 200
    assert len(service.calls) == old_calls
    plan = response.payload["plan"]
    domain = plan["steps"][0]["execution_envelope"]["domain_plan"]
    assert domain["previous_event"]["title"] == "Geprüfte Änderung"
    assert domain["operation"] == operation
    assert (
        domain["replacement"] is None
        if operation == "delete"
        else domain["replacement"]["title"] == "Neuer geprüfter Titel"
    )
    assert str(secret) not in str(response.payload)
    result = app.confirm_agent_plan(
        plan_id=plan["plan_id"],
        plan_sha256=plan["plan_sha256"],
        step_ids=tuple(step["step_id"] for step in plan["steps"]),
    )
    assert result["execution_reports"][0]["domain_report"]["mutation"]["status"] == (
        "updated" if operation == "update" else "absent"
    )
    assert len(service.mutations) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile_id", "hanna"),
        ("execution_id", "missing"),
        ("version_index", -1),
        ("version_index", True),
        ("version_index", 99),
        ("profile_id", []),
        ("language", "invalid"),
        ("changes", {"profile_id": "hanna"}),
        ("changes", {"event_uid": "other"}),
        ("changes", {"calendar_id": "other"}),
        ("changes", {"title": ""}),
        ("operation", "create"),
        ("extra", "not accepted"),
    ],
)
def test_editor_rejects_invalid_or_foreign_reference_before_provider_io(editor, field, value):
    app, request, service, *_ = editor
    request[field] = value
    calls = len(service.calls)
    assert post(app, request).status_code >= 400
    assert len(service.calls) == calls


def test_editor_does_not_read_credentials_to_prepare_and_survives_conversation_reset(editor):
    app, request, service, _, secret = editor
    secret.write_text("not readable as OAuth JSON", encoding="utf-8")
    app.reset_agent_conversation("lukas")
    calls = len(service.calls)
    assert post(app, request).status_code == 200
    assert len(service.calls) == calls


@pytest.mark.parametrize("headers", [{}, {"origin": "https://outside.invalid"}])
def test_editor_endpoint_keeps_session_and_origin_gate(editor, headers):
    app, request, service, *_ = editor
    actual = _api_headers(8765, app.session_token)
    if not headers:
        actual = {
            key: value for key, value in actual.items() if key.lower() != "x-folderhome-token"
        }
    else:
        actual.update(headers)
    calls = len(service.calls)
    assert post(app, request, headers=actual).status_code in {401, 403}
    assert len(service.calls) == calls


@pytest.mark.parametrize("stage", ["before_plan", "after_plan", "launch_gate", "old_version"])
def test_guided_edit_cannot_bypass_rights_or_version_gate(editor, stage):
    app, request, service, registry_file, _ = editor
    if stage == "before_plan":
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
        next(row for row in registry["resources"] if row["resource_id"] == "google-ledger")[
            "operations"
        ] = ["read"]
        registry_file.write_text(json.dumps(registry), encoding="utf-8")
        calls = len(service.calls)
        assert post(app, request).status_code == 409
        assert len(service.calls) == calls
        return
    plan = post(app, request).payload["plan"]
    if stage == "after_plan":
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
        next(row for row in registry["resources"] if row["resource_id"] == "google-ledger")[
            "operations"
        ] = ["read"]
        registry_file.write_text(json.dumps(registry), encoding="utf-8")
    elif stage == "launch_gate":
        app.workflow_executor._adapters["calendar-connectors"]._allowed = False
    else:
        app.confirm_agent_plan(
            plan_id=plan["plan_id"],
            plan_sha256=plan["plan_sha256"],
            step_ids=tuple(step["step_id"] for step in plan["steps"]),
        )
        calls = len(service.calls)
        request["changes"]["title"] = "Noch eine Änderung mit alter Version"
        assert post(app, request).status_code == 409
        assert len(service.calls) == calls
        return
    calls = len(service.calls)
    from folderhome.application.workflow_execution import WorkflowExecutionError

    with pytest.raises(WorkflowExecutionError):
        app.confirm_agent_plan(
            plan_id=plan["plan_id"],
            plan_sha256=plan["plan_sha256"],
            step_ids=tuple(step["step_id"] for step in plan["steps"]),
        )
    assert len(service.calls) == calls


def test_guided_editor_supports_all_day_dates_location_and_popups(editor):
    app, request, service, *_ = editor
    request["changes"] = {
        "all_day": True,
        "start": "2026-09-12",
        "end": "2026-09-13",
        "timezone": "Europe/Berlin",
        "location": "Büro",
        "reminders": [
            {"schema": "folderhome.calendar-reminder.v1", "method": "popup", "minutes_before": 30}
        ],
    }
    response = post(app, request)
    assert response.status_code == 200
    plan = response.payload["plan"]
    app.confirm_agent_plan(
        plan_id=plan["plan_id"],
        plan_sha256=plan["plan_sha256"],
        step_ids=tuple(step["step_id"] for step in plan["steps"]),
    )
    event = next(iter(service.events.values()))
    assert event["start"] == {"date": "2026-09-12"}
    assert event["location"] == "Büro"
    assert event["reminders"]["overrides"] == [{"method": "popup", "minutes": 30}]
