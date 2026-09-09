from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from test_scheduler_registration_plan import registration_inputs as registration_inputs

from folderhome.application import scheduler_registration as api


def _register(plan, **kwargs):
    return api.register_scheduler_job(
        plan, confirmed_plan_id=plan.plan_id, allow_scheduler_write=True, **kwargs
    )


def _rows(path):
    # Only our temporary provider database, after authorized creation.
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM jobs")]


@pytest.mark.parametrize("approval", [False, None, 1, "true"])
def test_registration_requires_strict_write_gate_before_creating_any_state(
    registration_inputs, approval
):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    with pytest.raises(api.SchedulerRegistrationError):
        api.register_scheduler_job(
            plan, confirmed_plan_id=plan.plan_id, allow_scheduler_write=approval
        )
    assert not plan.store_path.parent.exists()
    assert not plan.ledger_dir.exists()


def test_wrong_confirmation_or_changed_configuration_cannot_open_provider(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    with pytest.raises(api.SchedulerRegistrationError):
        api.register_scheduler_job(
            plan, confirmed_plan_id="another-plan", allow_scheduler_write=True
        )
    plan.handoff.config_file.write_bytes(plan.handoff.config_file.read_bytes() + b"\n")
    with pytest.raises(api.SchedulerRegistrationError):
        _register(plan)
    assert not plan.store_path.parent.exists()
    assert not plan.ledger_dir.exists()


def test_real_provider_registration_is_exact_and_does_not_start_a_consumer(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    before = plan.handoff.config_file.read_bytes()
    report = _register(plan)
    assert report.status == "registered"
    assert report.consumer_status == "not_observed"
    rows = _rows(plan.store_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == report.job_id
    assert row["executor"] == "folderhome.routine-queue.v1"
    assert json.loads(row["schedule_json"]) == {"kind": "interval", "seconds": 1800}
    assert row["next_due_at"] == "2026-09-10T06:00:00Z"
    assert row["enabled"] == 1
    payload = json.loads(row["payload_json"])
    assert payload["registration_plan"]["plan_id"] == plan.plan_id
    assert payload["registration_plan"]["handoff"]["interval_minutes"] == 30
    assert json.loads(report.attempt_file.read_text(encoding="utf-8"))["plan"] == plan.to_dict()
    receipts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in plan.ledger_dir.glob("result-*.json")
    ]
    assert receipts == [report.to_dict()]
    assert not plan.handoff.state_dir.exists()
    assert plan.handoff.config_file.read_bytes() == before
    with sqlite3.connect(plan.store_path) as conn:
        assert conn.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


def test_repeat_confirmation_reads_existing_job_instead_of_inserting(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    first = _register(plan)
    rows = _rows(plan.store_path)
    second = _register(plan)
    assert second.status == "already_registered"
    assert second.job_id == first.job_id
    assert _rows(plan.store_path) == rows


def test_changed_first_due_is_not_accepted_as_existing_approved_job(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    first = _register(plan)
    with sqlite3.connect(plan.store_path) as conn:
        conn.execute(
            "UPDATE jobs SET next_due_at = ? WHERE id = ?", ("2099-01-01T00:00:00Z", first.job_id)
        )
    before = _rows(plan.store_path)
    assert _register(plan).status == "conflict"
    assert _rows(plan.store_path) == before


def test_legitimate_due_progress_requires_matching_provider_history(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    first = _register(plan)
    import ellmos_scheduler

    store = ellmos_scheduler.SchedulerStore(plan.store_path)
    # Claim only synthetic data, no executor, service or document reads.
    store.claim_due(worker_id="synthetic-worker", now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    assert _rows(plan.store_path)[0]["next_due_at"] == "2026-09-10T06:30:00Z"
    assert _register(plan).status == "already_registered"
    with sqlite3.connect(plan.store_path) as conn:
        conn.execute(
            "UPDATE jobs SET next_due_at = ? WHERE id = ?", ("2026-09-10T07:00:00Z", first.job_id)
        )
    assert _register(plan).status == "conflict"


def test_abandoned_paused_run_retains_its_provider_retry_time(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    _register(plan)
    import ellmos_scheduler

    store = ellmos_scheduler.SchedulerStore(plan.store_path)
    store.claim_due(worker_id="synthetic-worker", now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    store.set_pause("global", True)
    store.claim_due(worker_id="synthetic-worker", now=datetime(2026, 9, 10, 6, 16, tzinfo=UTC))
    assert _rows(plan.store_path)[0]["next_due_at"] == "2026-09-10T06:00:00Z"
    assert _register(plan).status == "already_registered"


def test_older_abandoned_slot_can_become_due_after_a_newer_completed_run(registration_inputs):
    from folderhome.application.scheduler_handoff import build_scheduler_handoff

    handoff = registration_inputs["handoff"]
    inputs = {
        **registration_inputs,
        "handoff": build_scheduler_handoff(
            **{**vars_from_handoff(handoff), "interval_minutes": 5}, task_name=handoff.task_name
        ),
    }
    plan = api.build_scheduler_registration_plan(**inputs)
    _register(plan)
    import ellmos_scheduler

    store = ellmos_scheduler.SchedulerStore(plan.store_path)
    store.claim_due(worker_id="synthetic-worker", now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))
    newer = store.claim_due(
        worker_id="synthetic-worker", now=datetime(2026, 9, 10, 6, 5, tzinfo=UTC)
    )[0]
    store.start_run(newer["run_id"])
    store.finish_run(newer["run_id"], "succeeded", exit_code=0)
    store.set_pause("global", True)
    store.claim_due(worker_id="synthetic-worker", now=datetime(2026, 9, 10, 6, 16, tzinfo=UTC))
    assert _rows(plan.store_path)[0]["next_due_at"] == "2026-09-10T06:00:00Z"
    assert _register(plan).status == "already_registered"


@pytest.mark.parametrize("check_number", [1, 2])
def test_transient_attempt_path_alias_stays_uncertain_without_opening_store(
    registration_inputs, monkeypatch, check_number
):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    if check_number == 2:
        plan.ledger_dir.mkdir()
        (plan.ledger_dir / f"attempt-{plan.plan_id}.json").write_text(
            json.dumps(
                {"schema": "folderhome.scheduler-registration-attempt.v1", "plan": plan.to_dict()}
            ),
            encoding="utf-8",
        )
    original = api._safe_state_root
    checks = 0

    def during_atomic_publication(path):
        nonlocal checks
        if path.name.startswith("attempt-"):
            checks += 1
            if checks == check_number:
                raise api.SchedulerHandoffError("synthetic concurrent publication alias")
        return original(path)

    monkeypatch.setattr(api, "_safe_state_root", during_atomic_publication)
    report = _register(plan)
    assert report.status == "uncertain"
    assert report.attempt_file is None
    assert not plan.store_path.parent.exists()


def test_unknown_existing_database_is_not_initialized_or_modified(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    plan.store_path.parent.mkdir()
    plan.store_path.write_bytes(b"foreign database - must remain byte-identical")
    before = plan.store_path.read_bytes()
    report = _register(plan)
    assert report.status == "conflict"
    assert plan.store_path.read_bytes() == before
    assert not plan.store_path.with_name(plan.store_path.name + "-wal").exists()


def test_foreign_job_definition_is_never_overwritten(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    first = _register(plan)
    with sqlite3.connect(plan.store_path) as conn:
        conn.execute(
            "UPDATE jobs SET payload_json = ? WHERE id = ?", ('{"foreign": true}', first.job_id)
        )
    before = _rows(plan.store_path)
    second = _register(plan)
    assert second.status == "conflict"
    assert _rows(plan.store_path) == before


def test_timeout_after_committed_insert_is_reconciled_without_retry(
    registration_inputs, monkeypatch
):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    # Load once via a successful registration in a different temporary store.
    other = api.build_scheduler_registration_plan(
        **{**registration_inputs, "store_path": plan.store_path.with_name("other.db")}
    )
    _register(other)
    import ellmos_scheduler

    original = ellmos_scheduler.SchedulerStore.add_job

    def committed_then_timeout(self, *args, **kwargs):
        assert any(
            json.loads(path.read_text(encoding="utf-8"))["plan"] == plan.to_dict()
            for path in plan.ledger_dir.glob("attempt-*.json")
        )
        original(self, *args, **kwargs)
        raise TimeoutError("synthetic response loss after commit")

    monkeypatch.setattr(ellmos_scheduler.SchedulerStore, "add_job", committed_then_timeout)
    report = _register(plan)
    assert report.status == "registered"
    assert report.reconciled is True
    assert len(_rows(plan.store_path)) == 1
    assert _register(plan).status == "already_registered"


def test_failed_insert_without_job_stays_uncertain_and_is_not_blindly_retried(
    registration_inputs, monkeypatch
):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    other = api.build_scheduler_registration_plan(
        **{**registration_inputs, "store_path": plan.store_path.with_name("other.db")}
    )
    _register(other)
    import ellmos_scheduler

    original = ellmos_scheduler.SchedulerStore.add_job

    def unavailable(self, *args, **kwargs):
        raise TimeoutError("synthetic storage outage")

    monkeypatch.setattr(ellmos_scheduler.SchedulerStore, "add_job", unavailable)
    assert _register(plan).status == "uncertain"
    monkeypatch.setattr(ellmos_scheduler.SchedulerStore, "add_job", original)
    assert _register(plan).status == "uncertain"
    assert _rows(plan.store_path) == []


def test_distinct_approved_jobs_can_share_an_owned_store(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    _register(plan)
    from folderhome.application.scheduler_handoff import build_scheduler_handoff

    handoff = build_scheduler_handoff(
        **vars_from_handoff(plan.handoff),
        task_name="second_synthetic_queue",
    )
    other = api.build_scheduler_registration_plan(**{**registration_inputs, "handoff": handoff})
    assert _register(other).status == "registered"
    assert len(_rows(plan.store_path)) == 2


def vars_from_handoff(handoff):
    from dataclasses import fields

    excluded = {"schedule_id", "task_name", "portable_argv", "windows_task_xml"}
    return {
        field.name: getattr(handoff, field.name)
        for field in fields(handoff)
        if field.name not in excluded
    }


def test_concurrent_confirmation_creates_at_most_one_job(registration_inputs):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(lambda _: _register(plan), range(2)))
    assert any(report.status == "registered" for report in reports)
    assert all(
        report.status in {"registered", "already_registered", "uncertain"} for report in reports
    )
    assert len(_rows(plan.store_path)) == 1


@pytest.mark.parametrize("output", ["store", "ledger", "state"])
def test_registration_outputs_cannot_pollute_approved_document_sources(registration_inputs, output):
    inputs = dict(registration_inputs)
    source = inputs["handoff"].config_file.parent / "documents" / "inbox"
    if output == "store":
        inputs["store_path"] = source / "jobs.db"
    elif output == "ledger":
        inputs["ledger_dir"] = source / "ledger"
    else:
        from folderhome.application.scheduler_handoff import build_scheduler_handoff

        handoff = inputs["handoff"]
        inputs["handoff"] = build_scheduler_handoff(
            **{**vars_from_handoff(handoff), "state_dir": source / "queue-state"},
            task_name=handoff.task_name,
        )
    with pytest.raises(api.SchedulerRegistrationError):
        api.build_scheduler_registration_plan(**inputs)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_orphaned_sqlite_files_are_not_adopted_by_new_database(registration_inputs, suffix):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    plan.store_path.parent.mkdir()
    foreign = plan.store_path.with_name(plan.store_path.name + suffix)
    foreign.write_bytes(b"foreign sqlite state")
    report = _register(plan)
    assert report.status == "conflict"
    assert not plan.store_path.exists()
    assert foreign.read_bytes() == b"foreign sqlite state"


def test_failed_attempt_persistence_prevents_database_creation(registration_inputs, monkeypatch):
    plan = api.build_scheduler_registration_plan(**registration_inputs)

    def failed_write(*args, **kwargs):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(api, "_write_new_json", failed_write)
    with pytest.raises(OSError):
        _register(plan)
    assert not plan.store_path.parent.exists()


def test_result_persistence_failure_does_not_hide_possible_effects(
    registration_inputs, monkeypatch
):
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    original = api._write_new_json

    def failed_result(path, payload):
        if path.name.startswith("result-"):
            raise OSError("synthetic result disk failure")
        return original(path, payload)

    monkeypatch.setattr(api, "_write_new_json", failed_result)
    report = _register(plan)
    assert report.status == "uncertain"
    assert len(_rows(plan.store_path)) == 1
    monkeypatch.setattr(api, "_write_new_json", original)
    assert _register(plan).status == "already_registered"
