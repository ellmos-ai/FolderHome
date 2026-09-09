"""Setup configuration must be usable by the real scheduler, without registering it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_setup_app import _app, _post, _request

from folderhome.application.directory_observation import load_watched_folder_configuration
from folderhome.application.resource_registry import load_resource_registry, parse_resource_registry
from folderhome.application.routine_queue import load_folder_routine_bindings


def scheduler_request(tmp_path):
    return _request(
        tmp_path,
        scheduler={
            "profile_id": "lukas",
            "source_dir": str(tmp_path / "documents"),
            "target_dir": str(tmp_path / "output"),
            "area": "versicherungen",
            "interval_minutes": 30,
            "start_at": "2026-09-10T08:00:00+02:00",
            "timezone": "Europe/Berlin",
            "recursive": True,
            "allow_sensitive_local_read": True,
            "confirm_outside_home": False,
        },
    )


def save(app, request):
    plan = app.plan(request)
    assert plan["valid"], plan["errors"]
    return app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))


def test_setup_scheduler_preview_then_save_produces_consumable_configuration(tmp_path):
    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    planned = app.plan(request)
    assert planned["valid"], planned["errors"]
    assert planned.get("scheduler") is not None
    assert planned["scheduler"]["registration_performed"] is False
    assert planned["scheduler"]["consumer_started"] is False
    assert list(app.config_dir.iterdir()) == []
    result = save(app, request)
    assert result["written"] is True
    registry = load_resource_registry(
        app.resources_file,
        expected_os_account=app.profiles.os_account,
        known_profile_ids=frozenset({"lukas", "hanna", "simon"}),
    )
    by_purpose = {
        purpose: item
        for item in registry.resources
        for purpose in item.purposes
        if purpose.startswith("scheduler.")
    }
    watches = load_watched_folder_configuration(by_purpose["scheduler.watches"].local_path)
    bindings = load_folder_routine_bindings(by_purpose["scheduler.bindings"].local_path)
    assert watches.watches[0].source_root == tmp_path / "documents"
    assert watches.watches[0].profile_id == "lukas"
    assert watches.watches[0].interval_minutes == 30
    assert bindings.bindings[0].target_root == tmp_path / "output"
    assert bindings.bindings[0].watch_id == watches.watches[0].watch_id
    assert not by_purpose["scheduler.store"].local_path.exists()
    assert list(by_purpose["scheduler.ledger"].local_path.iterdir()) == []
    assert list(by_purpose["scheduler.state"].local_path.iterdir()) == []
    stored = app.state_payload()["current_schedulers"]["lukas"]
    assert stored["source_dir"] == str(tmp_path / "documents")
    assert stored["interval_minutes"] == 30
    assert "approve_scheduler_write" not in json.loads(app.launch_file.read_text())


def test_scheduler_preview_does_not_disable_runtime_missing_file_checks(tmp_path):
    app = _app(tmp_path)
    plan = app.plan(scheduler_request(tmp_path))
    from folderhome.contracts.resources import ResourceRegistryError

    with pytest.raises(ResourceRegistryError):
        parse_resource_registry(
            plan["resources_json"],
            expected_os_account=app.profiles.os_account,
            known_profile_ids=frozenset({"lukas", "hanna", "simon"}),
        )


def test_unedited_scheduler_files_and_custom_resources_survive_setup_save(tmp_path):
    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    first = save(app, request)
    files = [Path(item["path"]) for item in first["scheduler"]["documents"]]
    before = {path: path.read_bytes() for path in files}
    registry = json.loads(app.resources_file.read_text())
    custom = dict(registry["resources"][0], resource_id="custom_preserved", cloud_context="deny")
    custom["purposes"] = ["custom.read"]
    registry["resources"].append(custom)
    app.resources_file.write_text(json.dumps(registry), encoding="utf-8")
    saved = save(app, _request(tmp_path))
    assert saved["scheduler"] is None
    assert {path: path.read_bytes() for path in files} == before
    assert custom in json.loads(app.resources_file.read_text())["resources"]
    assert app.state_payload()["current_schedulers"]["lukas"]["interval_minutes"] == 30


def test_scheduler_save_rejects_changed_plan_and_rolls_back_failed_writes(tmp_path, monkeypatch):
    from folderhome import setup_app
    from folderhome.setup_app import SetupAppError

    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    plan = app.plan(request)
    request["scheduler"]["interval_minutes"] = 60
    with pytest.raises(SetupAppError):
        app.save(dict(request, confirm=True, plan_sha256=plan["plan_sha256"]))
    assert list(app.config_dir.iterdir()) == []
    original = setup_app._commit_staged
    calls = []

    def fail_after_first(temporary, target):
        calls.append(target)
        if len(calls) == 2:
            raise OSError("synthetic write failure")
        return original(temporary, target)

    monkeypatch.setattr(setup_app, "_commit_staged", fail_after_first)
    with pytest.raises(OSError, match="synthetic write failure"):
        save(app, request)
    assert list(app.config_dir.iterdir()) == []


@pytest.mark.parametrize("change", ["extra_watch", "stricter_grant", "file_drift"])
def test_scheduler_setup_does_not_overwrite_foreign_or_stale_changes(tmp_path, change):
    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    saved = save(app, request)
    checked = app.plan(request)
    watch_path = Path(saved["scheduler"]["documents"][0]["path"])
    if change == "stricter_grant":
        path = app.resources_file
        document = json.loads(path.read_text())
        for item in document["resources"]:
            if "scheduler.store" in item["purposes"]:
                item["operations"] = ["read"]
    else:
        path = watch_path
        document = json.loads(path.read_text())
        if change == "extra_watch":
            document["watches"].append(dict(document["watches"][0], watch_id="other_watch"))
        else:
            document["watches"][0]["area"] = "private_change"
    path.write_text(json.dumps(document), encoding="utf-8")
    before = path.read_bytes()
    from folderhome.setup_app import SetupAppError

    with pytest.raises(SetupAppError):
        app.save(dict(request, confirm=True, plan_sha256=checked["plan_sha256"]))
    if change != "file_drift":
        assert app.plan(request)["valid"] is False
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_id", "unknown"),
        ("interval_minutes", 4),
        ("interval_minutes", 1441),
        ("interval_minutes", True),
        ("allow_sensitive_local_read", False),
        ("recursive", "true"),
        ("start_at", "2026-09-10T08:00:00"),
        ("timezone", "Invalid/Zone"),
        ("start_at", "2026-09-10T08:00:00+00:00"),
        ("python_executable", "arbitrary.exe"),
    ],
)
def test_invalid_scheduler_settings_cannot_be_saved(tmp_path, field, value):
    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    request["scheduler"][field] = value
    response = _post(app, "/api/v1/setup/validate", request)
    assert response.payload["valid"] is False
    assert any(error["field"].startswith("scheduler") for error in response.payload["errors"])
    assert list(app.config_dir.iterdir()) == []


def test_corrupted_staged_registry_is_rejected_before_any_live_file_is_replaced(
    tmp_path, monkeypatch
):
    from folderhome import setup_app
    from folderhome.contracts.resources import ResourceRegistryError
    from folderhome.setup_app import SetupAppError

    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    original_stage, original_commit = setup_app._stage_json, setup_app._commit_staged
    committed = []

    def corrupt_stage(target, document):
        temporary = original_stage(target, document)
        if target == app.resources_file:
            temporary.write_text("{}", encoding="utf-8")
        return temporary

    def observe_commit(temporary, target):
        committed.append(target)
        return original_commit(temporary, target)

    monkeypatch.setattr(setup_app, "_stage_json", corrupt_stage)
    monkeypatch.setattr(setup_app, "_commit_staged", observe_commit)
    with pytest.raises((ResourceRegistryError, SetupAppError)):
        save(app, request)
    assert committed == []
    assert list(app.config_dir.iterdir()) == []


@pytest.mark.parametrize("malformed", [None, [], 12])
def test_malformed_existing_watch_returns_a_field_error_not_an_unhandled_exception(
    tmp_path, malformed
):
    app = _app(tmp_path)
    request = scheduler_request(tmp_path)
    saved = save(app, request)
    path = Path(saved["scheduler"]["documents"][0]["path"])
    document = json.loads(path.read_text())
    document["watches"] = [malformed]
    path.write_text(json.dumps(document), encoding="utf-8")
    plan = app.plan(request)
    assert plan["valid"] is False
    assert any(error["field"] == "scheduler" for error in plan["errors"])


def test_setup_launch_reaches_actual_scheduler_adapter_with_separate_write_gate(tmp_path):
    import sqlite3

    from folderhome import cli
    from folderhome.application.workflow_execution import WorkflowExecutionError

    setup = _app(tmp_path)
    request = scheduler_request(tmp_path)
    saved = save(setup, request)
    arguments = ["app", "plan", "--launch-config", str(setup.launch_file)]
    app = cli._prepare_local_app(cli._build_parser().parse_args(arguments))
    envelope = app.workflow_executor.prepare(
        workflow_id="scheduler-handoff",
        profile_id="lukas",
        request=saved["scheduler"]["request"],
    )
    registry = json.loads(setup.resources_file.read_text())
    store = next(
        Path(item["locator"]["path"])
        for item in registry["resources"]
        if "scheduler.store" in item["purposes"]
    )
    assert not store.exists()
    with pytest.raises(WorkflowExecutionError):
        app.workflow_executor.execute(
            envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z"
        )
    assert not store.exists()
    approved = cli._prepare_local_app(
        cli._build_parser().parse_args(arguments + ["--approve-scheduler-write"])
    )
    envelope = approved.workflow_executor.prepare(
        workflow_id="scheduler-handoff",
        profile_id="lukas",
        request=saved["scheduler"]["request"],
    )
    report = approved.workflow_executor.execute(
        envelope_id=envelope.envelope_id, approved_at="2026-09-09T06:00:00Z"
    )
    assert report.domain_report["status"] == "registered"
    assert report.domain_report["consumer_status"] == "not_observed"
    with sqlite3.connect(store) as connection:
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    assert setup.plan(request)["valid"] is False  # Setup must not edit a registered job.


@pytest.mark.parametrize("field", ["source_dir", "target_dir"])
@pytest.mark.parametrize("directory", [0, 1, 2])
def test_setup_rejects_document_folders_inside_generated_runtime_paths(tmp_path, field, directory):
    setup = _app(tmp_path)
    request = scheduler_request(tmp_path)
    saved = save(setup, request)
    request["scheduler"][field] = saved["scheduler"]["directories"][directory]
    plan = setup.plan(request)
    assert plan["valid"] is False
    assert any(error["field"] == "scheduler" for error in plan["errors"])


def test_scheduler_form_reload_profile_selection_and_explicit_write_intent():
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not available")
    result = subprocess.run(
        [node, "--test", str(Path(__file__).parent / "js/setup_scheduler.test.cjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
