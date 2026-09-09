"""The real setup save binds private paths without reading credentials or calling Google."""

import json
from pathlib import Path

import pytest
from test_setup_app import _app, _request


def google_request(tmp_path):
    request = _request(tmp_path)
    credential = tmp_path / "oauth.json"
    credential.write_text("synthetic-secret-not-json", encoding="utf-8")
    ledger = tmp_path / "calendar-receipts"
    ledger.mkdir()
    request["folders"].append(
        {
            "profile_id": "lukas",
            "purpose": "calendar.source",
            "path": str(tmp_path / "documents"),
        }
    )
    request["calendar"] = {
        "default_backend": "google",
        "timezone": "Europe/Berlin",
        "ics_directory": str(tmp_path / "output"),
        "accounts": [
            {
                "profile_id": "lukas",
                "backend": "google",
                "account_id": "google-lukas",
                "display_name": "Kalender",
                "provider_id": "google-calendar",
                "provider_revision": "v3",
                "calendar_id": "synthetic@example.invalid",
                "credential_ref": "connector://google-calendar/google-secret",
                "bind_private_resources": True,
                "credential_file": str(credential),
                "ledger_dir": str(ledger),
            }
        ],
    }
    return request, credential, ledger


def test_google_setup_saves_private_bindings_without_reading_secret(tmp_path, monkeypatch):
    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    original = Path.open

    def guard(path, *args, **kwargs):
        if path == credential:
            pytest.fail("Setup must not open the credential file")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guard)
    plan = app.plan(request)
    assert plan["valid"], plan["errors"]
    assert list(app.config_dir.iterdir()) == []
    assert list(ledger.iterdir()) == []
    declarations = plan["resources_json"]["resources"]
    private = {
        purpose: item
        for item in declarations
        for purpose in item["purposes"]
        if purpose in {"calendar.google_credentials", "calendar.connector_ledger"}
    }
    assert set(private) == {"calendar.google_credentials", "calendar.connector_ledger"}
    assert private["calendar.google_credentials"]["resource_id"] == "google-secret"
    assert private["calendar.google_credentials"]["operations"] == ["read"]
    assert private["calendar.connector_ledger"]["operations"] == ["read", "state_write"]
    for item in private.values():
        assert item["profile_ids"] == ["lukas"]
        assert item["cloud_context"] == "deny"
    saved = app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
    assert saved["written"]
    account = json.loads(app.calendar_accounts_file.read_text())["accounts"][0]
    assert "credential_file" not in account and "bind_private_resources" not in account
    assert "approve_calendar_write" not in json.loads(app.launch_file.read_text())
    assert "synthetic-secret-not-json" not in json.dumps(saved)
    assert list(ledger.iterdir()) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("bind_private_resources", False),
        ("bind_private_resources", "true"),
        ("calendar_id", "primary"),
        ("provider_revision", "v4"),
        ("credential_file", "relative.json"),
        ("credential_ref", "connector://google-calendar/"),
    ],
)
def test_google_setup_rejects_unapproved_or_invalid_binding(tmp_path, field, value):
    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    request["calendar"]["accounts"][0][field] = value
    plan = app.plan(request)
    assert not plan["valid"]
    assert list(app.config_dir.iterdir()) == []
    assert list(ledger.iterdir()) == []


def test_google_setup_does_not_restore_restricted_existing_rights(tmp_path):
    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    plan = app.plan(request)
    assert plan["valid"]
    app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
    data = json.loads(app.resources_file.read_text())
    for item in data["resources"]:
        if "calendar.connector_ledger" in item["purposes"]:
            item["operations"] = ["read"]
    app.resources_file.write_text(json.dumps(data), encoding="utf-8")
    assert not app.plan(request)["valid"]
    preserved = app.plan(_request(tmp_path))
    assert preserved["valid"], preserved["errors"]
    assert next(
        item
        for item in preserved["resources_json"]["resources"]
        if "calendar.connector_ledger" in item["purposes"]
    )["operations"] == ["read"]


def test_google_setup_cannot_bypass_existing_ledger_rights_with_another_id(tmp_path):
    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    plan = app.plan(request)
    app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
    data = json.loads(app.resources_file.read_text())
    for item in data["resources"]:
        if "calendar.connector_ledger" in item["purposes"]:
            item["resource_id"] = "manually-bound-ledger"
            item["operations"] = ["read"]
    app.resources_file.write_text(json.dumps(data), encoding="utf-8")
    plan = app.plan(request)
    assert not plan["valid"]


@pytest.mark.parametrize(
    "kind",
    [
        "credential_source",
        "credential_output",
        "credential_setup",
        "ledger_source",
        "ledger_parent",
        "missing",
    ],
)
def test_google_setup_rejects_exposed_missing_or_overlapping_private_paths(tmp_path, kind):
    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    account = request["calendar"]["accounts"][0]
    if kind.startswith("credential_"):
        parent = {
            "credential_source": tmp_path / "documents",
            "credential_output": tmp_path / "output",
            "credential_setup": app.config_dir,
        }[kind]
        target = parent / "secret.json"
        target.write_text("private", encoding="utf-8")
        account["credential_file"] = str(target)
    elif kind == "ledger_source":
        account["ledger_dir"] = str(tmp_path / "documents")
    elif kind == "ledger_parent":
        account["ledger_dir"] = str(tmp_path)
    else:
        account["credential_file"] = str(tmp_path / "missing.json")
    before = list(app.config_dir.iterdir())
    plan = app.plan(request)
    assert not plan["valid"]
    assert list(app.config_dir.iterdir()) == before


@pytest.mark.parametrize("kind", ["credential", "ledger"])
@pytest.mark.parametrize("source_type", ["scheduler", "later_document"])
def test_final_setup_resources_cannot_expose_google_private_files(tmp_path, kind, source_type):
    from test_scheduler_setup import scheduler_request

    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    private = tmp_path / "private"
    private.mkdir()
    credential = private / "oauth.json"
    credential.write_text("synthetic", encoding="utf-8")
    request["calendar"]["accounts"][0]["credential_file"] = str(credential)
    exposed = private if kind == "credential" else ledger
    if source_type == "scheduler":
        request["scheduler"] = scheduler_request(tmp_path)["scheduler"]
        request["scheduler"]["source_dir"] = str(exposed)
    else:
        plan = app.plan(request)
        assert plan["valid"]
        app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
        request = _request(tmp_path)
        request["folders"].append(
            {"profile_id": "lukas", "purpose": "documents.source", "path": str(exposed)}
        )
    assert not app.plan(request)["valid"]


@pytest.mark.parametrize("gate", [False, True])
def test_saved_google_setup_reaches_real_app_with_separate_execution_gate(
    tmp_path, monkeypatch, gate
):
    from test_calendar_handoff import _write_event
    from test_google_calendar_gateway import CalendarService

    from folderhome import cli
    from folderhome.application import google_calendar_workflow
    from folderhome.application.workflow_execution import WorkflowExecutionError

    setup = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    credential.write_text(
        json.dumps(
            {
                "type": "authorized_user",
                "token": "synthetic-token",
                "expiry": "2100-01-01T00:00:00Z",
                "refresh_token": "synthetic-refresh",
                "client_id": "synthetic-client",
                "client_secret": "synthetic-secret",
                "scopes": ["https://www.googleapis.com/auth/calendar.events"],
            }
        ),
        encoding="utf-8",
    )
    _write_event(tmp_path / "documents" / "appointment.txt")
    plan = setup.plan(request)
    assert plan["valid"], plan["errors"]
    setup.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
    service = CalendarService()
    monkeypatch.setattr(google_calendar_workflow, "GoogleCalendarTransport", lambda: service)
    arguments = ["app", "plan", "--launch-config", str(setup.launch_file)]
    if gate:
        arguments.append("--approve-calendar-write")
    app = cli._prepare_local_app(cli._build_parser().parse_args(arguments))
    try:
        resources = {
            purpose: resource.resource_id
            for resource in app.resource_registry.resources
            if "lukas" in resource.profile_ids
            for purpose in resource.purposes
        }
        request = {
            "source_resource_id": resources["calendar.source"],
            "configuration_resource_id": resources["calendar.configuration"],
            "accounts_resource_id": resources["calendar.connector_accounts"],
            "credential_resource_id": resources["calendar.google_credentials"],
            "ledger_resource_id": resources["calendar.connector_ledger"],
            "account_id": "google-lukas",
            "area": "gesundheit",
            "planned_at": "2026-09-09T10:00:00+02:00",
            "recursive": True,
            "allow_sensitive_local_read": False,
            "reminders": [],
        }
        envelope = app.workflow_executor.prepare(
            workflow_id="calendar-connectors",
            profile_id="lukas",
            request=request,
        )
        assert not service.calls and list(ledger.iterdir()) == []
        if gate:
            result = app.workflow_executor.execute(
                envelope_id=envelope.envelope_id,
                approved_at=request["planned_at"],
            )
            assert result.domain_report["status"] == "executed"
            assert len(service.events) == 1
            assert (ledger / "google-calendar.sqlite3").is_file()
        else:
            with pytest.raises(WorkflowExecutionError):
                app.workflow_executor.execute(
                    envelope_id=envelope.envelope_id,
                    approved_at=request["planned_at"],
                )
            assert not service.calls and list(ledger.iterdir()) == []
    finally:
        app.close()


@pytest.mark.parametrize("purpose", ["documents.source", "documents.output"])
@pytest.mark.parametrize("kind", ["credential", "ledger"])
def test_single_file_document_binding_cannot_expose_google_private_data(tmp_path, purpose, kind):
    app = _app(tmp_path)
    request, credential, ledger = google_request(tmp_path)
    plan = app.plan(request)
    app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
    target = credential
    if kind == "ledger":
        target = ledger / "private-receipt.txt"
        target.write_text("private", encoding="utf-8")
    data = json.loads(app.resources_file.read_text())
    data["resources"].append(
        {
            "resource_id": "single-document",
            "kind": "file",
            "locator": {"type": "local_path", "path": str(target)},
            "operations": ["read"],
            "purposes": [purpose],
            "profile_ids": ["lukas"],
            "cloud_context": "deny",
        }
    )
    app.resources_file.write_text(json.dumps(data), encoding="utf-8")
    plan = app.plan(request)
    assert not plan["valid"]
