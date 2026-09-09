"""Real local dispatcher and provider; only synthetic future jobs are started."""

from __future__ import annotations

import json

import pytest
from test_local_app import StubSearcher, _settings
from test_scheduler_control import control_plan as control_plan
from test_scheduler_registration_plan import registration_inputs as registration_inputs

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.scheduler_control import SchedulerConsumerController
from folderhome.local_server import create_local_server


@pytest.fixture
def controlled_app(tmp_path, control_plan):
    control = SchedulerConsumerController(
        profile_ids=frozenset({"lukas", "hanna", "simon"}),
        allow_consumer_start=True,
        poll_seconds=0.01,
        plan_provider=lambda profile_id: control_plan,
    )
    settings = _settings(tmp_path)
    app = LocalApplication(
        settings=settings,
        profiles=load_profile_configuration(settings.profiles_dir),
        searcher=StubSearcher(),
        scheduler_controller=control,
    )
    try:
        yield app, control
    finally:
        control.close(timeout=5)


def request(app, action, *, payload=None, method="POST", headers=None):
    return app.handle(
        method=method,
        target=f"/api/v1/scheduler/{action}",
        server_port=8765,
        headers={
            "Host": "127.0.0.1:8765",
            "X-FolderHome-Token": app.session_token,
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            **(headers or {}),
        },
        body=json.dumps(payload or {}).encode("utf-8"),
    )


def preview_request():
    return {"schema": "folderhome.scheduler-consumer-preview-request.v1", "profile_id": "lukas"}


def test_scheduler_browser_control_logic():
    import shutil
    import subprocess
    from pathlib import Path

    node = shutil.which("node")
    assert node is not None, "Node is required for scheduler UI acceptance tests"
    result = subprocess.run(
        [node, "--test", str(Path(__file__).parent / "js/scheduler_control.test.cjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_api_preview_start_status_stop_and_server_close_own_real_worker(controlled_app):
    app, control = controlled_app
    before = request(app, "status?profile_id=lukas", method="GET")
    assert before.status_code == 200
    assert before.payload["status"] == "not_started_in_this_app"
    preview = request(app, "preview", payload=preview_request())
    assert preview.status_code == 200
    confirmation = {
        "schema": "folderhome.scheduler-consumer-start-request.v1",
        "profile_id": "lukas",
        "plan_id": preview.payload["plan_id"],
        "plan_sha256": preview.payload["plan_sha256"],
    }
    started = request(app, "start", payload=confirmation)
    assert started.status_code == 200
    assert started.payload["status"] == "running"
    assert request(app, "start", payload=confirmation).status_code == 409
    stopped = request(
        app,
        "stop",
        payload={
            "schema": "folderhome.scheduler-consumer-stop-request.v1",
            "profile_id": "lukas",
            "worker_id": started.payload["worker_id"],
        },
    )
    assert stopped.status_code == 200
    assert stopped.payload["status"] in {"stopping", "stopped"}
    # A fresh start is possible after the old worker has drained; closing the server
    # must close the controller even without an explicit Stop click.
    control._workers["lukas"].thread.join(timeout=5)
    proposal = request(app, "preview", payload=preview_request()).payload
    confirmation.update(plan_id=proposal["plan_id"], plan_sha256=proposal["plan_sha256"])
    assert request(app, "start", payload=confirmation).status_code == 200
    server = create_local_server(app, allow_loopback_server=True)
    server.server_close()
    assert control.status(profile_id="lukas")["status"] == "stopped"
    assert request(app, "preview", payload=preview_request()).status_code == 409


@pytest.mark.parametrize(
    "headers,code",
    [
        ({"X-FolderHome-Token": "wrong"}, 401),
        ({"Origin": "https://foreign.example"}, 403),
    ],
)
def test_api_scheduler_uses_existing_token_and_origin_gates(controlled_app, headers, code):
    app, control = controlled_app
    assert request(app, "preview", payload=preview_request(), headers=headers).status_code == code
    assert control.status(profile_id="lukas")["status"] == "not_started_in_this_app"


@pytest.mark.parametrize(
    "action,payload",
    [
        ("preview", {**preview_request(), "source_dir": "C:/private"}),
        ("preview", {**preview_request(), "profile_id": []}),
        (
            "start",
            {
                "schema": "folderhome.scheduler-consumer-start-request.v1",
                "profile_id": "lukas",
                "plan_id": "ü",
                "plan_sha256": "ä",
            },
        ),
        (
            "stop",
            {
                "schema": "folderhome.scheduler-consumer-stop-request.v1",
                "profile_id": "lukas",
                "worker_id": "ö",
            },
        ),
    ],
)
def test_api_scheduler_rejects_untrusted_shape_without_effects(controlled_app, action, payload):
    app, control = controlled_app
    response = request(app, action, payload=payload)
    assert response.status_code == 400
    assert control.status(profile_id="lukas")["status"] == "not_started_in_this_app"
    assert b"C:/private" not in response.content


def test_api_scheduler_configuration_errors_are_path_free(controlled_app, monkeypatch):
    app, control = controlled_app

    def unreadable(profile_id):
        raise ValueError("C:/private/scheduler.json")

    monkeypatch.setattr(control, "_plan_provider", unreadable)
    response = request(app, "preview", payload=preview_request())
    assert response.status_code == 409
    assert b"C:/private" not in response.content


@pytest.mark.parametrize("approve_consumer", [False, True])
def test_real_setup_launch_connects_saved_request_and_separate_start_gate(
    tmp_path, approve_consumer
):
    from pathlib import Path

    from test_scheduler_setup import save, scheduler_request
    from test_setup_app import _app

    from folderhome import cli

    setup = _app(tmp_path)
    setup_request = scheduler_request(tmp_path)
    setup_request["scheduler"].update(start_at="2100-01-01T00:00:00+00:00", timezone="UTC")
    saved = save(setup, setup_request)
    arguments = [
        "app",
        "plan",
        "--launch-config",
        str(setup.launch_file),
        "--approve-scheduler-write",
    ]
    if approve_consumer:
        arguments.append("--approve-scheduler-consumer")
    app = cli._prepare_local_app(cli._build_parser().parse_args(arguments))
    preview = request(app, "preview", payload=preview_request())
    assert preview.status_code == 200
    assert preview.payload["live_effect_approved"] is approve_consumer
    assert preview.payload["registration_checked"] is False
    confirmation = {
        "schema": "folderhome.scheduler-consumer-start-request.v1",
        "profile_id": "lukas",
        "plan_id": preview.payload["plan_id"],
        "plan_sha256": preview.payload["plan_sha256"],
    }
    # A missing registration is never created by starting the consumer.
    assert request(app, "start", payload=confirmation).status_code == 409
    envelope = app.workflow_executor.prepare(
        workflow_id="scheduler-handoff",
        profile_id="lukas",
        request=saved["scheduler"]["request"],
    )
    app.workflow_executor.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-09-09T06:00:00Z",
    )
    try:
        if approve_consumer:
            registry = json.loads(setup.resources_file.read_text())
            saved_request = next(
                Path(item["locator"]["path"])
                for item in registry["resources"]
                if "scheduler.request" in item["purposes"]
            )
            original = saved_request.read_bytes()
            changed = json.loads(original)
            changed["request"]["interval_minutes"] = 45
            saved_request.write_text(json.dumps(changed), encoding="utf-8")
            assert request(app, "start", payload=confirmation).status_code == 409
            saved_request.write_bytes(original)
        started = request(app, "start", payload=confirmation)
        assert started.status_code == (200 if approve_consumer else 409)
        if approve_consumer:
            assert started.payload["status"] == "running"
    finally:
        app.close()
