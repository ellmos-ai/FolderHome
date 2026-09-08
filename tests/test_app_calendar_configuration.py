from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from test_setup_app import _app, _post, _request

from folderhome import cli


def _calendar(tmp_path: Path) -> dict[str, object]:
    return {
        "default_backend": "folderhome_local",
        "timezone": "Europe/Berlin",
        "ics_directory": str(tmp_path / "output"),
        "accounts": [
            {
                "profile_id": "lukas",
                "backend": "folderhome_local",
                "account_id": "local-lukas",
                "display_name": "Eigener Kalender",
                "provider_id": "folderhome.local-calendar",
                "provider_revision": "phase17",
                "calendar_id": "local",
                "credential_ref": None,
            }
        ],
    }


def _save(app, request):
    planned = _post(app, "/api/v1/setup/validate", request)
    assert planned.payload["valid"], planned.payload
    saved = _post(
        app,
        "/api/v1/setup/save",
        {
            **request,
            "confirm": True,
            "plan_sha256": planned.payload["plan_sha256"],
        },
    )
    assert saved.status_code == 200, saved.payload


def test_setup_calendar_paths_reach_launch_and_survive_unrelated_save(tmp_path: Path):
    app = _app(tmp_path)
    request = _request(tmp_path, calendar=_calendar(tmp_path))
    _save(app, request)
    launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
    assert launch["calendar_config"] == str(app.calendar_file)
    assert launch["connector_accounts"] == str(app.calendar_accounts_file)
    _save(app, _request(tmp_path))
    assert json.loads(app.launch_file.read_text(encoding="utf-8")) == launch


def test_calendar_paths_are_not_model_preset_fields_and_cli_wins(tmp_path: Path):
    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    args = argparse.Namespace(launch_config=app.launch_file, calendar_config=Path("override"))
    cli._apply_launch_config(args)
    assert args.calendar_config == Path("override")
    assert args.connector_accounts == app.calendar_accounts_file
    assert "calendar_config" not in cli._PRESET_FIELDS
    assert "connector_accounts" not in cli._PRESET_FIELDS
    assert not hasattr(args, "approve_calendar_network_write")


def test_explicit_empty_accounts_retires_file_but_omitted_accounts_preserve_it(tmp_path: Path):
    app = _app(tmp_path)
    calendar = _calendar(tmp_path)
    _save(app, _request(tmp_path, calendar=calendar))
    original = app.calendar_accounts_file.read_bytes()
    _save(
        app,
        _request(
            tmp_path, calendar={key: value for key, value in calendar.items() if key != "accounts"}
        ),
    )
    assert app.calendar_accounts_file.read_bytes() == original
    request = _request(tmp_path, calendar={**calendar, "accounts": []})
    planned = _post(app, "/api/v1/setup/validate", request)
    assert planned.payload["cascade"]["calendar_account_ids"] == ["local-lukas"]
    assert str(app.calendar_accounts_file) in planned.payload["cascade"]["retired_files"]
    _save(app, request)
    assert not app.calendar_accounts_file.exists()
    assert "connector_accounts" not in json.loads(app.launch_file.read_text(encoding="utf-8"))
    assert list(app.config_dir.glob("calendar-accounts.json.bak-*"))


def test_setup_calendar_reaches_real_application_resource_catalog(tmp_path: Path):
    app = _app(tmp_path)
    request = _request(tmp_path, calendar=_calendar(tmp_path))
    request["folders"].append(
        {
            "profile_id": "lukas",
            "purpose": "calendar.source",
            "path": str(tmp_path / "documents"),
        }
    )
    _save(app, request)
    args = cli._build_parser().parse_args(
        [
            "app",
            "plan",
            "--launch-config",
            str(app.launch_file),
        ]
    )
    application = cli._prepare_local_app(args)
    catalog = application.resource_catalog_payload("lukas")
    assert {
        "calendar.configuration",
        "calendar.state",
        "calendar.source",
        "calendar.connector_accounts",
    } <= catalog["defaults"].keys()
    encoded = json.dumps(catalog)
    assert str(tmp_path) not in encoded
    assert "credential_ref" not in encoded
    assert (
        "calendar.connector_accounts"
        not in application.resource_catalog_payload("hanna")["defaults"]
    )
    # Configuration does not silently connect an external executor.
    assert (
        next(
            item
            for item in application.workflow_executor.catalog()
            if item.workflow_id == "calendar-connectors"
        ).status
        == "not_connected"
    )


def test_setup_to_app_executes_real_local_calendar_only_after_approval(tmp_path: Path):
    from folderhome.capabilities.calendar_store import CalendarStore

    app = _app(tmp_path)
    request = _request(tmp_path, calendar=_calendar(tmp_path))
    request["folders"].append(
        {
            "profile_id": "lukas",
            "purpose": "calendar.source",
            "path": str(tmp_path / "documents"),
        }
    )
    (tmp_path / "documents" / "Termin.txt").write_text(
        "Termin: Werkstattprüfung\nDatum: 2026-09-14\nBeginn: 10:30\nEnde: 11:30\n",
        encoding="utf-8",
    )
    _save(app, request)
    application = cli._prepare_local_app(
        cli._build_parser().parse_args(
            [
                "app",
                "plan",
                "--launch-config",
                str(app.launch_file),
            ]
        )
    )
    defaults = application.resource_catalog_payload("lukas")["defaults"]
    gateway = application.workflow_executor
    envelope = gateway.prepare(
        workflow_id="calendar-handoff",
        profile_id="lukas",
        request={
            "source_resource_id": defaults["calendar.source"],
            "configuration_resource_id": defaults["calendar.configuration"],
            "state_resource_id": defaults["calendar.state"],
            "area": "termine",
            "planned_at": "2026-09-09T01:00:00+02:00",
            "recursive": False,
            "allow_sensitive_local_read": False,
        },
    )
    store = CalendarStore(tmp_path / "state")
    assert store.list_events() == ()
    assert envelope.domain_plan["planned_action_count"] == 1
    report = gateway.execute(
        envelope_id=envelope.envelope_id, approved_at="2026-09-09T01:01:00+02:00"
    )
    assert len(store.list_events(profile_id="lukas")) == 1
    assert report.domain_report["connector_invoked"] is False
    assert report.side_effects == ("state.calendar.write",)


def test_existing_calendar_resource_without_default_is_not_bypassed(tmp_path: Path):
    from folderhome.application.app_calendar_configuration import bind_app_calendar_resources
    from folderhome.contracts.resources import LogicalResource, ResourceRegistry

    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    custom = LogicalResource(
        resource_id="read_only_calendar",
        kind="local_calendar",
        local_path=tmp_path / "state",
        operations=frozenset({"read"}),
        purposes=frozenset({"calendar.state"}),
        profile_ids=frozenset({"lukas"}),
        cloud_context="deny",
    )
    registry = ResourceRegistry(
        os_account=app.profiles.os_account,
        resources=(custom,),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    result = bind_app_calendar_resources(
        registry,
        calendar_config=app.calendar_file,
        connector_accounts=None,
        state_dir=tmp_path / "state",
        os_account=registry.os_account,
        profile_ids=registry.known_profile_ids,
    )
    assert [r for r in result.resources if "calendar.state" in r.purposes] == [custom]
    assert result.profile_defaults["lukas"]["calendar.state"] == custom.resource_id
    assert registry.profile_defaults == {}


def test_setup_state_restores_saved_calendar_and_accounts(tmp_path: Path):
    from test_setup_app import _headers

    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    response = app.handle(
        method="GET",
        target="/api/v1/setup/state",
        headers=_headers(8766),
        body=b"",
        server_port=8766,
    )
    calendar = response.payload["current_calendar"]
    assert calendar["default_backend"] == "folderhome_local"
    assert calendar["timezone"] == "Europe/Berlin"
    assert calendar["ics_directory"] == str(tmp_path / "output")
    assert calendar["accounts"][0]["account_id"] == "local-lukas"
    assert response.payload["calendar_read_by_app"] is True
    ui = (Path(__file__).parents[1] / "src/folderhome/setup_ui/app.js").read_text(encoding="utf-8")
    assert "state.current_calendar" in ui
    assert "calendarAccounts.replaceChildren" in ui


@pytest.mark.parametrize("invalid", ["missing", "oversized", "unknown_field", "timezone"])
def test_invalid_calendar_configuration_blocks_app_without_leaking_values(
    tmp_path: Path, invalid: str
):
    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    if invalid == "missing":
        app.calendar_file.unlink()
    elif invalid == "oversized":
        app.calendar_file.write_text("x" * 65_537, encoding="utf-8")
    else:
        payload = json.loads(app.calendar_file.read_text(encoding="utf-8"))
        payload["private_secret" if invalid == "unknown_field" else "default_timezone"] = (
            "private-value-not-for-errors"
        )
        app.calendar_file.write_text(json.dumps(payload), encoding="utf-8")
    args = cli._build_parser().parse_args(
        [
            "app",
            "plan",
            "--launch-config",
            str(app.launch_file),
        ]
    )
    with pytest.raises(ValueError) as caught:
        cli._prepare_local_app(args)
    assert "private-value-not-for-errors" not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_invalid_saved_accounts_are_not_echoed_into_setup_state(tmp_path: Path):
    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    accounts = json.loads(app.calendar_accounts_file.read_text(encoding="utf-8"))
    accounts["accounts"][0]["access_token"] = "private-value-not-for-errors"
    app.calendar_accounts_file.write_text(json.dumps(accounts), encoding="utf-8")
    payload = app.state_payload()
    assert payload["calendar_load_error"] is True
    assert payload["current_calendar"] is None
    assert "private-value-not-for-errors" not in json.dumps(payload)


def test_calendar_adoption_is_idempotent_and_preserves_explicit_defaults(tmp_path: Path):
    from folderhome.application.app_calendar_configuration import bind_app_calendar_resources
    from folderhome.contracts.resources import LogicalResource, ResourceRegistry

    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    custom = LogicalResource(
        resource_id="custom_config",
        kind="file",
        local_path=app.calendar_file,
        operations=frozenset({"read"}),
        purposes=frozenset({"calendar.configuration"}),
        profile_ids=frozenset({"lukas"}),
        cloud_context="deny",
    )
    original = ResourceRegistry(
        os_account=app.profiles.os_account,
        resources=(custom,),
        profile_defaults={"lukas": {"calendar.configuration": "custom_config"}},
        known_profile_ids=frozenset({"lukas"}),
    )
    kwargs = dict(
        calendar_config=app.calendar_file,
        connector_accounts=app.calendar_accounts_file,
        state_dir=tmp_path / "state",
        os_account=original.os_account,
        profile_ids=original.known_profile_ids,
    )
    first = bind_app_calendar_resources(original, **kwargs)
    assert bind_app_calendar_resources(first, **kwargs) == first
    assert first.profile_defaults["lukas"]["calendar.configuration"] == "custom_config"
    assert len(original.resources) == 1


def test_setup_reload_reads_effective_custom_calendar_paths_and_keeps_them(tmp_path: Path):
    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    custom_config = tmp_path / "custom-calendar.json"
    custom_accounts = tmp_path / "custom-accounts.json"
    config = json.loads(app.calendar_file.read_text(encoding="utf-8"))
    config["default_timezone"] = "UTC"
    custom_config.write_text(json.dumps(config), encoding="utf-8")
    custom_accounts.write_bytes(app.calendar_accounts_file.read_bytes())
    app.calendar_accounts_file.unlink()
    launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
    launch.update(calendar_config=str(custom_config), connector_accounts=str(custom_accounts))
    app.launch_file.write_text(json.dumps(launch), encoding="utf-8")
    snapshot = app.state_payload()
    assert snapshot["current_calendar"]["timezone"] == "UTC"
    assert snapshot["current_calendar"]["accounts"][0]["account_id"] == "local-lukas"
    assert snapshot["calendar_external_configuration"] is True
    _save(app, _request(tmp_path))
    saved = json.loads(app.launch_file.read_text(encoding="utf-8"))
    assert saved["calendar_config"] == str(custom_config)
    assert saved["connector_accounts"] == str(custom_accounts)


@pytest.mark.parametrize("invalid", ["unknown_field", "missing_custom_file", "unknown_profile"])
def test_setup_reload_rejects_invalid_effective_calendar_without_echoing_it(
    tmp_path: Path, invalid: str
):
    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    if invalid == "unknown_field":
        payload = json.loads(app.calendar_file.read_text(encoding="utf-8"))
        payload["private_extension"] = "private-value-not-for-errors"
        app.calendar_file.write_text(json.dumps(payload), encoding="utf-8")
    elif invalid == "unknown_profile":
        payload = json.loads(app.calendar_accounts_file.read_text(encoding="utf-8"))
        payload["accounts"][0]["profile_id"] = "stranger"
        app.calendar_accounts_file.write_text(json.dumps(payload), encoding="utf-8")
    else:
        launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
        launch["calendar_config"] = str(tmp_path / "missing-custom.json")
        app.launch_file.write_text(json.dumps(launch), encoding="utf-8")
    snapshot = app.state_payload()
    assert snapshot["calendar_load_error"] is True
    assert snapshot["current_calendar"] is None
    assert "private-value-not-for-errors" not in json.dumps(snapshot)


def test_setup_calendar_javascript_behavior():
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not available")
    result = subprocess.run(
        [node, "--test", str(Path(__file__).parent / "js/setup_calendar.test.cjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("keep_account", [False, True])
def test_profile_deletion_cascades_active_external_accounts_without_editing_source(
    tmp_path: Path,
    keep_account: bool,
):
    from test_setup_app import _empty_profile_app, _profile_request, _reopened

    app = _empty_profile_app(tmp_path)
    calendar = _calendar(tmp_path)
    calendar["accounts"].append(
        {**calendar["accounts"][0], "profile_id": "simon", "account_id": "local-simon"}
    )
    if not keep_account:
        calendar["accounts"] = calendar["accounts"][1:]
    request = _profile_request(tmp_path, app, calendar=calendar)
    _save(app, request)
    external = tmp_path / "external-accounts.json"
    original = app.calendar_accounts_file.read_bytes()
    external.write_bytes(original)
    app.calendar_accounts_file.unlink()
    launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
    launch["connector_accounts"] = str(external)
    app.launch_file.write_text(json.dumps(launch), encoding="utf-8")
    reopened = _reopened(tmp_path, app)
    removal = {key: value for key, value in request.items() if key != "calendar"}
    removal["profiles"] = [item for item in request["profiles"] if item["profile_id"] != "simon"]
    plan = reopened.plan(removal)
    assert plan["valid"], plan["errors"]
    assert plan["cascade"]["calendar_account_ids"] == ["local-simon"]
    assert str(external) not in plan["cascade"]["retired_files"]
    _save(reopened, removal)
    assert external.read_bytes() == original
    saved_launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
    if keep_account:
        assert saved_launch["connector_accounts"] == str(app.calendar_accounts_file)
        remaining = json.loads(app.calendar_accounts_file.read_text(encoding="utf-8"))
        assert [item["account_id"] for item in remaining["accounts"]] == ["local-lukas"]
    else:
        assert "connector_accounts" not in saved_launch


@pytest.mark.parametrize("invalid", ["missing", "profile", "secret"])
def test_invalid_explicit_calendar_accounts_block_app_start(tmp_path: Path, invalid: str):
    app = _app(tmp_path)
    _save(app, _request(tmp_path, calendar=_calendar(tmp_path)))
    if invalid == "missing":
        app.calendar_accounts_file.unlink()
    else:
        payload = json.loads(app.calendar_accounts_file.read_text(encoding="utf-8"))
        if invalid == "profile":
            payload["accounts"][0]["profile_id"] = "stranger"
        else:
            payload["accounts"][0]["access_token"] = "private-value-not-for-errors"
        app.calendar_accounts_file.write_text(json.dumps(payload), encoding="utf-8")
    args = cli._build_parser().parse_args(
        [
            "app",
            "plan",
            "--launch-config",
            str(app.launch_file),
        ]
    )
    with pytest.raises(ValueError) as caught:
        cli._prepare_local_app(args)
    assert "private-value-not-for-errors" not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_profile_cascade_cannot_save_accounts_for_an_unknown_profile(tmp_path: Path):
    from test_setup_app import _empty_profile_app, _profile_request, _reopened

    app = _empty_profile_app(tmp_path)
    calendar = _calendar(tmp_path)
    calendar["accounts"] = [
        {**calendar["accounts"][0], "profile_id": "simon", "account_id": "local-simon"}
    ]
    request = _profile_request(tmp_path, app, calendar=calendar)
    _save(app, request)
    external = tmp_path / "external-accounts.json"
    accounts = json.loads(app.calendar_accounts_file.read_text(encoding="utf-8"))
    accounts["accounts"].append(
        {**accounts["accounts"][0], "profile_id": "stranger", "account_id": "unknown-account"}
    )
    external.write_text(json.dumps(accounts), encoding="utf-8")
    launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
    launch["connector_accounts"] = str(external)
    app.launch_file.write_text(json.dumps(launch), encoding="utf-8")
    before = {
        path: path.read_bytes() for path in (external, app.launch_file, app.calendar_accounts_file)
    }
    removal = {key: value for key, value in request.items() if key != "calendar"}
    removal["profiles"] = [item for item in request["profiles"] if item["profile_id"] != "simon"]
    reopened = _reopened(tmp_path, app)
    plan = reopened.plan(removal)
    assert plan["valid"] is False
    assert any(item["field"] == "calendar.accounts" for item in plan["errors"])
    response = _post(
        reopened,
        "/api/v1/setup/save",
        {**removal, "confirm": True, "plan_sha256": plan["plan_sha256"]},
    )
    assert response.status_code != 200
    assert all(path.read_bytes() == content for path, content in before.items())
