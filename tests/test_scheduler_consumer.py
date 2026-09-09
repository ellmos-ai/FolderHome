from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import fields
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from test_scheduler_registration_plan import registration_inputs as registration_inputs

from folderhome.application import scheduler_registration as registration
from folderhome.application.scheduler_handoff import build_scheduler_handoff

INVOCATION_ID = "a" * 32


def _api():
    from folderhome.application import scheduler_consumer

    return scheduler_consumer


@pytest.fixture
def approved_plan(registration_inputs):
    handoff = registration_inputs["handoff"]
    bindings = json.loads(handoff.bindings_file.read_text(encoding="utf-8"))
    bindings["bindings"][0]["target_dir"] = str(handoff.config_file.parent / "routine-output")
    handoff.bindings_file.write_text(json.dumps(bindings), encoding="utf-8")
    plan = registration.build_scheduler_registration_plan(**registration_inputs)
    report = registration.register_scheduler_job(
        plan, confirmed_plan_id=plan.plan_id, allow_scheduler_write=True
    )
    assert report.status == "registered"
    return plan


def _consumer(plan, **kwargs):
    return _api().create_scheduler_consumer(
        plan, confirmed_plan_id=plan.plan_id, allow_consumer_state_write=True, **kwargs
    )


def _runs(plan):
    with sqlite3.connect(plan.store_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM runs")]


@pytest.mark.parametrize("gate", [False, 1, "true"])
def test_consumer_requires_separate_strict_start_gate(registration_inputs, gate):
    api = _api()
    plan = registration.build_scheduler_registration_plan(**registration_inputs)
    with pytest.raises(registration.SchedulerRegistrationError):
        api.create_scheduler_consumer(
            plan, confirmed_plan_id=plan.plan_id, allow_consumer_state_write=gate
        )
    assert not plan.store_path.parent.exists()
    assert not plan.ledger_dir.exists()


def test_consumer_never_initializes_an_unregistered_store(registration_inputs):
    plan = registration.build_scheduler_registration_plan(**registration_inputs)
    with pytest.raises(registration.SchedulerRegistrationError):
        _consumer(plan)
    assert not plan.store_path.parent.exists()
    assert not plan.handoff.state_dir.exists()


def test_constructing_consumer_does_not_run_or_claim_a_job(approved_plan):
    consumer = _consumer(approved_plan)
    assert consumer.last_observation is None
    assert _runs(approved_plan) == []
    assert not approved_plan.handoff.state_dir.exists()


@pytest.mark.parametrize("with_document, expected_exit", [(False, 0), (True, 10)])
def test_real_provider_tick_runs_the_read_only_child_and_accepts_attention(
    approved_plan, with_document, expected_exit
):
    plan = approved_plan
    consumer = _consumer(plan)
    source = plan.handoff.config_file.parent / "documents/inbox/synthetic.txt"
    if with_document:
        # A document appearing after registration is authorized; configuration is unchanged.
        source.write_text("Synthetic insurance note without personal data.", encoding="utf-8")
    results = consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    assert len(results) == 1
    assert results[0]["status"] == "succeeded"
    assert results[0]["exit_code"] == expected_exit
    runs = _runs(plan)
    assert len(runs) == 1 and runs[0]["status"] == "succeeded"
    output = json.loads(runs[0]["output"])
    assert output["registration_plan_id"] == plan.plan_id
    assert output["report"]["document_side_effects"] == []
    assert output["report"]["checkpoint_written"] is False
    assert consumer.last_observation["status"] == "tick_completed"
    assert consumer.last_observation["runs"][0]["run_id"] == results[0]["run_id"]
    if with_document:
        assert (
            source.read_text(encoding="utf-8") == "Synthetic insurance note without personal data."
        )
    assert not (plan.handoff.config_file.parent / "routine-output").exists()


def test_consumer_does_not_claim_other_jobs_in_the_same_store(approved_plan):
    consumer = _consumer(approved_plan)
    import ellmos_scheduler

    store = ellmos_scheduler.SchedulerStore(approved_plan.store_path)
    store.add_job(
        "foreign",
        {"kind": "interval", "seconds": 300},
        "noop",
        {"message": "foreign"},
        next_due_at=datetime(2026, 9, 10, 5, 0, tzinfo=UTC),
    )
    consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    assert all(run["job_id"] != "foreign" for run in _runs(approved_plan))
    foreign = next(row for row in store.list_jobs() if row["id"] == "foreign")
    assert foreign["next_due_at"] == "2026-09-10T05:00:00Z"


@pytest.mark.parametrize("change", ["configuration", "payload"])
def test_consumer_revalidates_approved_inputs_before_each_claim(approved_plan, change):
    plan = approved_plan
    consumer = _consumer(plan)
    if change == "configuration":
        plan.handoff.config_file.write_bytes(plan.handoff.config_file.read_bytes() + b"\n")
    else:
        with sqlite3.connect(plan.store_path) as conn:
            conn.execute("UPDATE jobs SET payload_json = ?", ('{"foreign": true}',))
    with pytest.raises(registration.SchedulerRegistrationError):
        consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    assert _runs(plan) == []
    assert not plan.handoff.state_dir.exists()


def test_changed_payload_after_claim_cannot_launch_an_unapproved_child(approved_plan, monkeypatch):
    consumer = _consumer(approved_plan)
    import ellmos_scheduler

    original = ellmos_scheduler.SchedulerStore.claim_due

    def change_after_claim(self, *args, **kwargs):
        jobs = original(self, *args, **kwargs)
        for job in jobs:
            job["payload_json"] = '{"foreign": true}'
        return jobs

    monkeypatch.setattr(ellmos_scheduler.SchedulerStore, "claim_due", change_after_claim)
    results = consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    assert results[0]["status"] == "failed"
    assert not approved_plan.handoff.state_dir.exists()


def test_child_timeout_is_not_reported_as_a_successful_queue_run(approved_plan, monkeypatch):
    api = _api()
    consumer = _consumer(approved_plan)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("synthetic child", 600)

    monkeypatch.setattr(api, "_run_queue_process", timeout)
    results = consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    assert results[0]["status"] == "timed_out"
    assert _runs(approved_plan)[0]["error"]
    assert not approved_plan.handoff.state_dir.exists()


@pytest.mark.parametrize(
    "change", ["plan_id", "report_schema", "queue", "effects", "exit_code", "persisted_path"]
)
def test_invalid_child_report_is_not_accepted_even_with_success_exit(approved_plan, change):
    api = _api()
    envelope = api.execute_approved_queue(
        approved_plan.to_dict(),
        confirmed_plan_id=approved_plan.plan_id,
        allow_scheduler_state_write=True,
        invocation_id=INVOCATION_ID,
    )
    if change == "plan_id":
        envelope["registration_plan_id"] = "another-plan"
    elif change == "report_schema":
        envelope["report"]["schema"] = "other-schema"
    elif change == "queue":
        envelope["report"]["queue"] = {}
    elif change == "effects":
        envelope["report"]["document_side_effects"] = ["unexpected"]
    elif change == "exit_code":
        envelope["report"]["exit_code"] = True
    else:
        envelope["report"]["completed_file"] = str(approved_plan.handoff.config_file)

    response = subprocess.CompletedProcess([], 0, json.dumps(envelope), "")
    with pytest.raises(registration.SchedulerRegistrationError):
        api._verify_child_report(approved_plan, response, invocation_id=INVOCATION_ID)


def test_old_valid_child_envelope_cannot_satisfy_a_later_run(approved_plan, monkeypatch):
    api = _api()
    consumer = _consumer(approved_plan)
    original = api._run_queue_process
    cached = None

    def replay_after_first_call(*args, **kwargs):
        nonlocal cached
        if cached is None:
            cached = original(*args, **kwargs)
        return cached

    monkeypatch.setattr(api, "_run_queue_process", replay_after_first_call)
    first = consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))[0]
    second = consumer.tick(now=datetime(2026, 9, 10, 6, 30, tzinfo=UTC))[0]
    assert first["status"] == "succeeded"
    assert second["status"] == "failed"
    assert first["run_id"] != second["run_id"]
    assert len(list((approved_plan.handoff.state_dir / "scheduler-runs").glob("*.json"))) == 1


def test_child_uses_this_installation_even_when_working_directory_shadows_it(
    approved_plan, tmp_path
):
    shadow = tmp_path / "shadow-import"
    package = shadow / "folderhome"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        'raise RuntimeError("WRONG_FOLDERHOME_CHECKOUT")\n', encoding="utf-8"
    )
    inputs = {
        field.name: getattr(approved_plan.handoff, field.name)
        for field in fields(approved_plan.handoff)
        if field.name not in {"schedule_id", "portable_argv", "windows_task_xml"}
    }
    inputs["working_directory"] = shadow
    plan = registration.build_scheduler_registration_plan(
        handoff=build_scheduler_handoff(**inputs),
        store_path=approved_plan.store_path,
        ledger_dir=approved_plan.ledger_dir,
        provider_root=approved_plan.provider_root,
        provider_revision=approved_plan.provider_revision,
    )
    assert (
        registration.register_scheduler_job(
            plan, confirmed_plan_id=plan.plan_id, allow_scheduler_write=True
        ).status
        == "registered"
    )
    result = _consumer(plan).tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))[0]
    assert result["status"] == "succeeded"
    assert result["exit_code"] == 0


@pytest.mark.parametrize("count", [True, 1.0])
def test_child_summary_count_types_are_not_coerced_into_valid_evidence(approved_plan, count):
    api = _api()
    envelope = api.execute_approved_queue(
        approved_plan.to_dict(),
        confirmed_plan_id=approved_plan.plan_id,
        allow_scheduler_state_write=True,
        invocation_id=INVOCATION_ID,
    )
    assert envelope["report"]["queue"]["summary"] == {"empty": 1}
    envelope["report"]["queue"]["summary"]["empty"] = count
    response = subprocess.CompletedProcess([], 0, json.dumps(envelope), "")
    with pytest.raises(registration.SchedulerRegistrationError):
        api._verify_child_report(approved_plan, response, invocation_id=INVOCATION_ID)


def test_child_rejects_changed_configuration_before_source_or_state_work(approved_plan):
    api = _api()
    payload = approved_plan.to_dict()
    approved_plan.handoff.config_file.write_bytes(
        approved_plan.handoff.config_file.read_bytes() + b"\n"
    )
    with pytest.raises(registration.SchedulerRegistrationError):
        api.execute_approved_queue(
            payload,
            confirmed_plan_id=approved_plan.plan_id,
            allow_scheduler_state_write=True,
            invocation_id=INVOCATION_ID,
        )
    assert not approved_plan.handoff.state_dir.exists()


def test_existing_provider_serve_loop_runs_bound_consumer_and_stops_in_the_test(
    approved_plan, monkeypatch
):
    consumer = _consumer(approved_plan)
    import ellmos_scheduler.service as service_module
    import ellmos_scheduler.store as store_module

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 10, 6, 0, tzinfo=UTC).astimezone(tz)

    class EndSyntheticLoop(Exception):
        pass

    def stop_after_iteration(seconds):
        raise EndSyntheticLoop

    monkeypatch.setattr(store_module, "datetime", FrozenDatetime)
    monkeypatch.setattr(service_module, "time", SimpleNamespace(sleep=stop_after_iteration))
    with pytest.raises(EndSyntheticLoop):
        consumer.serve(poll_seconds=0.01)
    runs = _runs(approved_plan)
    assert len(runs) == 1
    assert runs[0]["status"] == "succeeded"
    assert consumer.last_observation["runs"][0]["run_id"] == runs[0]["run_id"]


def test_missing_invocation_receipt_does_not_confirm_a_child_run(approved_plan, monkeypatch):
    api = _api()
    consumer = _consumer(approved_plan)
    original = api._run_queue_process

    def lose_receipt(*args, **kwargs):
        completed = original(*args, **kwargs)
        assert completed.returncode == 0
        (approved_plan.ledger_dir / f"invocation-{kwargs['invocation_id']}.json").unlink()
        return completed

    monkeypatch.setattr(api, "_run_queue_process", lose_receipt)
    result = consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))[0]
    assert result["status"] == "failed"
    assert _runs(approved_plan)[0]["error"]


def test_failed_observation_persistence_is_reported_separately_from_completed_run(
    approved_plan, monkeypatch
):
    api = _api()
    consumer = _consumer(approved_plan)
    original = api._write_new_json

    def fail_observation(path, payload):
        if path.name.startswith("consumer-"):
            raise OSError("synthetic ledger failure")
        return original(path, payload)

    monkeypatch.setattr(api, "_write_new_json", fail_observation)
    result = consumer.tick(now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))[0]
    assert result["status"] == "succeeded"
    observation = consumer.last_observation
    assert observation["status"] == "uncertain"
    assert observation["error"]
    assert observation["runs"][0]["run_id"] == result["run_id"]
    assert not list(approved_plan.ledger_dir.glob("consumer-*.json"))
