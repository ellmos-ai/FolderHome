from folderhome import application, contracts


def test_synthetic_success_produces_an_executed_dry_run_with_evidence() -> None:
    report = application.run_synthetic("success", run_id="run_success")

    assert report.run_id == "run_success"
    assert report.status is contracts.RunStatus.EXECUTED
    assert report.dry_run is True
    assert [action.action_id for action in report.actions] == ["run_success:0001"]
    assert report.actions[0].status is contracts.RunStatus.EXECUTED
    assert report.actions[0].evidence[0].uri == "fixture://success"
    assert report.actions[0].side_effects == ()


def test_synthetic_side_effect_stays_blocked_without_human_gate() -> None:
    report = application.run_synthetic("blocked", run_id="run_blocked")

    assert report.status is contracts.RunStatus.BLOCKED
    assert report.actions[0].status is contracts.RunStatus.BLOCKED
    assert report.actions[0].side_effects == (contracts.SideEffect.PHONE_CALL,)
    assert report.actions[0].gate == contracts.GateDecision(
        required=True,
        granted=False,
        reason="human approval missing",
    )
    assert report.decisions[0].status is contracts.DecisionStatus.PENDING
    assert report.actions[0].evidence == ()


def test_synthetic_failure_is_recorded_instead_of_escaping_unreported() -> None:
    report = application.run_synthetic("failure", run_id="run_failure")

    assert report.status is contracts.RunStatus.FAILED
    assert report.actions[0].status is contracts.RunStatus.FAILED
    assert report.actions[0].message == "synthetic failure"
    assert report.actions[0].gate.granted is True


def test_resume_reuses_run_id_without_duplicate_action_ids() -> None:
    failed = application.run_synthetic("failure", run_id="run_restart")

    resumed = application.resume_synthetic(failed, "success")

    assert resumed.run_id == "run_restart"
    assert resumed.started_at == failed.started_at
    assert resumed.status is contracts.RunStatus.EXECUTED
    assert [action.action_id for action in resumed.actions] == [
        "run_restart:0001",
        "run_restart:0002",
    ]
    assert len({action.action_id for action in resumed.actions}) == 2
