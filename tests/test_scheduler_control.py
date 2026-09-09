from __future__ import annotations

import importlib.util
import json
import sqlite3

import pytest
from test_scheduler_registration_plan import registration_inputs as registration_inputs

from folderhome.application.scheduler_handoff import build_scheduler_handoff
from folderhome.application.scheduler_registration import (
    build_scheduler_registration_plan,
    register_scheduler_job,
)


@pytest.fixture
def control_plan(registration_inputs):
    inputs = registration_inputs
    original = inputs["handoff"]
    bindings = json.loads(original.bindings_file.read_text(encoding="utf-8"))
    bindings["bindings"][0]["target_dir"] = str(original.config_file.parent / "routine-output")
    original.bindings_file.write_text(json.dumps(bindings), encoding="utf-8")
    inputs["handoff"] = build_scheduler_handoff(
        task_name=original.task_name,
        interval_minutes=30,
        start_at="2100-01-01T00:00:00+00:00",
        timezone="UTC",
        config_file=original.config_file,
        bindings_file=original.bindings_file,
        profiles_dir=original.profiles_dir,
        state_dir=original.state_dir,
        manifest_root=original.manifest_root,
        doc_services_root=original.doc_services_root,
        python_executable=original.python_executable,
        working_directory=original.working_directory,
    )
    plan = build_scheduler_registration_plan(**inputs)
    register_scheduler_job(plan, confirmed_plan_id=plan.plan_id, allow_scheduler_write=True)
    return plan


def controller(*, enabled=True):
    assert importlib.util.find_spec("folderhome.application.scheduler_control") is not None, (
        "App-owned lifecycle controller is required"
    )
    from folderhome.application.scheduler_control import SchedulerConsumerController

    return SchedulerConsumerController(
        profile_ids=frozenset({"lukas", "hanna"}),
        allow_consumer_start=enabled,
        poll_seconds=0.01,
    )


def start(control, plan):
    preview = control.preview(profile_id="lukas", plan=plan)
    return control.start(
        profile_id="lukas",
        plan_id=preview["plan_id"],
        plan_sha256=preview["plan_sha256"],
    )


def test_preview_and_status_do_not_start_a_worker_or_modify_registration(control_plan):
    control = controller()
    before = control_plan.store_path.read_bytes()
    preview = control.preview(profile_id="lukas", plan=control_plan)
    status = control.status(profile_id="lukas")
    assert status["status"] == "not_started_in_this_app"
    assert status["other_instances"] == "not_observed"
    assert preview["registration_plan_id"] == control_plan.plan_id
    assert preview["document_actions_authorized"] is False
    assert str(control_plan.store_path) not in json.dumps(preview)
    assert control_plan.store_path.read_bytes() == before
    assert not list(control_plan.ledger_dir.glob("consumer-*.json"))


@pytest.mark.parametrize("profile_id", ["lukas", "hanna"])
def test_preview_rejects_plan_without_active_profile_binding(registration_inputs, profile_id):
    path = registration_inputs["handoff"].config_file
    config = json.loads(path.read_text(encoding="utf-8"))
    for watch in config["watches"]:
        watch["enabled"] = False
    path.write_text(json.dumps(config), encoding="utf-8")
    plan = build_scheduler_registration_plan(**registration_inputs)
    control = controller()
    with pytest.raises(ValueError, match="aktive"):
        control.preview(profile_id=profile_id, plan=plan)
    assert control.status(profile_id=profile_id)["status"] == "not_started_in_this_app"


@pytest.mark.parametrize("enabled", [False, 1, "true"])
def test_start_requires_its_own_strict_process_gate(control_plan, enabled):
    control = controller(enabled=enabled)
    with pytest.raises(ValueError):
        start(control, control_plan)
    assert not list(control_plan.ledger_dir.glob("consumer-*.json"))


def test_exact_start_then_stop_owns_one_worker_and_never_replays_old_approval(control_plan):
    control = controller()
    preview = control.preview(profile_id="lukas", plan=control_plan)
    args = dict(profile_id="lukas", plan_id=preview["plan_id"], plan_sha256=preview["plan_sha256"])
    try:
        running = control.start(**args)
        assert running["status"] == "running"
        assert running["worker_id"]
        with pytest.raises(ValueError):
            control.start(**args)
        assert control.status(profile_id="lukas")["worker_id"] == running["worker_id"]
        stopping = control.stop(profile_id="lukas", worker_id=running["worker_id"])
        assert stopping["status"] in {"stopping", "stopped"}
    finally:
        control.close(timeout=5)
    assert control.status(profile_id="lukas")["status"] == "stopped"
    with pytest.raises(ValueError):
        control.start(**args)
    with sqlite3.connect(control_plan.store_path) as connection:
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


@pytest.mark.parametrize("change", ["hash", "config", "profile", "missing_job"])
def test_changed_or_unregistered_start_is_rejected_without_a_worker(control_plan, change):
    control = controller()
    preview = control.preview(profile_id="lukas", plan=control_plan)
    args = dict(profile_id="lukas", plan_id=preview["plan_id"], plan_sha256=preview["plan_sha256"])
    if change == "hash":
        args["plan_sha256"] = "0" * 64
    elif change == "profile":
        args["profile_id"] = "hanna"
    elif change == "config":
        path = control_plan.handoff.config_file
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        with sqlite3.connect(control_plan.store_path) as connection:
            connection.execute("DELETE FROM jobs")
    try:
        with pytest.raises(ValueError):
            control.start(**args)
        assert control.status(profile_id="lukas")["status"] == "not_started_in_this_app"
    finally:
        control.close(timeout=5)


def test_stop_rejects_another_worker_and_close_prevents_future_start(control_plan):
    control = controller()
    try:
        running = start(control, control_plan)
        with pytest.raises(ValueError):
            control.stop(profile_id="lukas", worker_id="foreign-worker")
        assert control.status(profile_id="lukas")["worker_id"] == running["worker_id"]
    finally:
        control.close(timeout=5)
    assert control.status(profile_id="lukas")["status"] == "stopped"
    with pytest.raises(ValueError):
        start(control, control_plan)


def test_concurrent_confirmations_create_only_one_owned_worker(control_plan):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    control = controller()
    preview = control.preview(profile_id="lukas", plan=control_plan)
    ready = Barrier(2)

    def confirm():
        ready.wait(timeout=5)
        try:
            return control.start(
                profile_id="lukas", plan_id=preview["plan_id"], plan_sha256=preview["plan_sha256"]
            )["worker_id"]
        except ValueError:
            return None

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: confirm(), range(2)))
        assert sum(item is not None for item in results) == 1
        assert control.status(profile_id="lukas")["worker_id"] in results
    finally:
        control.close(timeout=5)


def test_stop_reports_draining_until_the_real_worker_has_returned(control_plan, monkeypatch):
    from threading import Event

    control = controller()
    from folderhome.application import scheduler_control

    factory = scheduler_control.create_scheduler_consumer
    reached, release = Event(), Event()

    def paused_consumer(*args, **kwargs):
        consumer = factory(*args, **kwargs)
        tick = consumer.tick

        def paused_tick(**options):
            result = tick(**options)
            reached.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Synthetic bounded drain wait expired")
            return result

        consumer.tick = paused_tick
        return consumer

    monkeypatch.setattr(scheduler_control, "create_scheduler_consumer", paused_consumer)
    try:
        running = start(control, control_plan)
        assert reached.wait(timeout=5)
        stopped = control.stop(profile_id="lukas", worker_id=running["worker_id"])
        assert stopped["status"] == "stopping"
        assert control.status(profile_id="lukas")["status"] == "stopping"
    finally:
        release.set()
        control.close(timeout=5)
    assert control.status(profile_id="lukas")["status"] == "stopped"


def test_failed_worker_is_not_reported_as_a_successful_stop_or_exposed_as_a_path(
    control_plan, monkeypatch
):
    control = controller()
    from folderhome.application import scheduler_control

    factory = scheduler_control.create_scheduler_consumer

    def broken_consumer(*args, **kwargs):
        consumer = factory(*args, **kwargs)

        def fail(**options):
            raise OSError("private/scheduler/path is unavailable")

        consumer.serve = fail
        return consumer

    monkeypatch.setattr(scheduler_control, "create_scheduler_consumer", broken_consumer)
    try:
        start(control, control_plan)
    finally:
        control.close(timeout=5)
    status = control.status(profile_id="lukas")
    assert status["status"] == "failed"
    assert "private/scheduler/path" not in json.dumps(status)


def test_saved_configuration_is_rechecked_before_start(control_plan):
    from dataclasses import replace

    from folderhome.application.scheduler_control import SchedulerConsumerController

    selected = [control_plan]
    control = SchedulerConsumerController(
        profile_ids=frozenset({"lukas"}),
        allow_consumer_start=True,
        plan_provider=lambda profile_id: selected[0],
    )
    preview = control.preview_configured(profile_id="lukas")
    selected[0] = replace(control_plan, plan_id="changed_saved_request")
    try:
        with pytest.raises(ValueError):
            control.start(
                profile_id="lukas", plan_id=preview["plan_id"], plan_sha256=preview["plan_sha256"]
            )
        assert control.status(profile_id="lukas")["status"] == "not_started_in_this_app"
    finally:
        control.close(timeout=5)
