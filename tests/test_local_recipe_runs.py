"""Product boundary for section recipes, using the real gateway and stub adapters."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_local_recipes import confirm, recipe_app, request
from test_recipe_results import payload
from test_recipe_runs import Gateway, core_gateway

from folderhome.application.local_app import LocalAppError
from folderhome.application.recipes import parse_recipe
from folderhome.contracts.recipes import CapabilityRecipeError

ROUTE = "/api/v1/agent/recipes"


@pytest.fixture
def app(tmp_path, monkeypatch):
    application = recipe_app(tmp_path)
    driver = Gateway()
    application.workflow_executor = core_gateway(driver)
    recipe = parse_recipe(payload())
    monkeypatch.setattr("folderhome.application.local_app.load_bundled_recipe", lambda _: recipe)
    monkeypatch.setattr("folderhome.application.local_app.load_bundled_recipes", lambda: (recipe,))
    return application, driver


def start(application):
    return application.propose_recipe(
        profile_id="lukas", recipe_id="accident-aftercare", language="de"
    )


def post_run(application, action, run_id, profile_id="lukas", **extra):
    return request(
        application,
        ROUTE + "/" + action,
        payload={
            "schema": f"folderhome.local-recipe-{action}-request.v1",
            "profile_id": profile_id,
            "run_id": run_id,
            **extra,
        },
    )


def test_normal_plan_confirmation_then_next_section_uses_actual_source(app):
    application, driver = app
    first = start(application)
    public = first.to_dict()
    assert public["schema"] == "folderhome.recipe-stage-plan.v1"
    run_id = public["run"]["run_id"]
    assert len(first.plan.steps) == 1
    assert driver.executed == []
    result = confirm(application, first)
    assert result["recipe_run"]["status"] == "ready"
    assert result["execution_performed"] is True
    assert len(application.execution_results_payload(profile_id="lukas", limit=25)["results"]) == 1
    second = post_run(application, "next", run_id)
    assert second.status_code == 200
    plan = second.payload["plan"]
    assert len(driver.prepared) == 4
    assert driver.executed == ["contact-register"]
    assert plan["approval_context"]["result_bindings"][0]["value"] == "Müller"
    result = application.confirm_agent_plan(
        plan_id=plan["plan_id"],
        plan_sha256=plan["plan_sha256"],
        step_ids=tuple(step["step_id"] for step in plan["steps"]),
    )
    assert result["recipe_run"]["status"] == "completed"
    assert post_run(application, "next", run_id).status_code == 400
    assert len(application.execution_results_payload(profile_id="lukas", limit=25)["results"]) == 4


def test_catalog_and_run_status_are_scoped_and_token_gated(app):
    application, driver = app
    item = application.recipe_catalog_payload(profile_id="lukas", language="en")["recipes"][0]
    assert item["approval_mode"] == "per_section"
    first = start(application)
    route = ROUTE + "/runs?profile_id=lukas"
    assert request(application, route, token=False).status_code == 401
    status = request(application, route)
    assert status.status_code == 200
    assert status.payload["runs"][0]["run_id"] == first.run_id
    assert request(application, ROUTE + "/runs?profile_id=hanna").payload["runs"] == []
    assert request(application, route + "&profile_id=hanna").status_code == 400
    assert driver.executed == []


@pytest.mark.parametrize("action", ["next", "close"])
def test_run_actions_reject_other_profiles_unknown_fields_and_wrong_methods(app, action):
    application, driver = app
    first = start(application)
    assert post_run(application, action, first.run_id, "hanna").status_code == 400
    assert post_run(application, action, first.run_id, path="C:/private").status_code == 400
    assert request(application, ROUTE + "/" + action).status_code == 405
    assert driver.executed == []
    assert application.proposed_agent_plan(first.plan_id) is not None


@pytest.mark.parametrize("action", ["reset", "close", "shutdown", "evict"])
def test_lifecycle_invalidates_pending_section_without_effects(app, monkeypatch, action):
    application, driver = app
    first = start(application)
    if action == "reset":
        application.reset_agent_conversation("lukas")
    elif action == "close":
        assert post_run(application, "close", first.run_id).status_code == 200
    elif action == "shutdown":
        application.close()
    else:
        monkeypatch.setattr("folderhome.application.local_app._MAX_PROPOSED_AGENT_PLANS", 1)
        second = start(application)
        assert second.run_id != first.run_id
    with pytest.raises((LocalAppError, CapabilityRecipeError)):
        confirm(application, first)
    assert post_run(application, "next", first.run_id).status_code == 400
    assert driver.executed == []


def test_concurrent_approval_runs_one_section_once_and_cannot_replay(app):
    application, driver = app
    first = start(application)

    def attempt():
        try:
            return confirm(application, first)
        except (LocalAppError, CapabilityRecipeError):
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert driver.executed == ["contact-register"]


def test_failed_section_is_consumed_private_details_hidden_and_no_next(app):
    application, driver = app
    first = start(application)
    driver.fail_execute = "contact-register"
    result = confirm(application, first)
    assert result["recipe_execution"]["status"] == "aborted"
    assert result["execution_outcome_unknown"] is True
    assert "C:/secret" not in json.dumps(result)
    assert post_run(application, "next", first.run_id).status_code == 400


def test_failed_model_turn_releases_unretained_recipe_scope(app):
    application, driver = app
    first = application.prepare_recipe(
        profile_id="lukas", recipe_id="accident-aftercare", language="de"
    )
    application.discard_recipe_preparations((first,))
    assert post_run(application, "next", first.run_id).status_code == 400
    assert driver.executed == []


def test_partial_provider_evidence_survives_without_becoming_a_binding_source(app, monkeypatch):
    from folderhome.application.workflow_execution import WorkflowExecutionOutcomeUnknown

    class Unknown(WorkflowExecutionOutcomeUnknown):
        def public_evidence(self):
            return {"confirmed_event_ids": ["own-event"], "outcome": "uncertain"}

    application, driver = app
    first = start(application)

    def uncertain(*args):
        raise Unknown("PRIVATE provider response")

    monkeypatch.setattr(driver, "execute", uncertain)
    result = confirm(application, first)
    assert result["execution_reports"] == []
    assert result["uncertain_results"][0]["evidence"]["confirmed_event_ids"] == ["own-event"]
    assert result["recipe_run"]["completed_step_refs"] == []
    assert "PRIVATE" not in json.dumps(result)
    stored = application.execution_results_payload(profile_id="lukas", limit=25)["results"]
    assert stored[0]["status"] == "uncertain"


def test_chat_can_start_list_and_prepare_a_followup_but_never_confirm(app, monkeypatch):
    from folderhome.application import strands_agent

    application, driver = app
    calls = [("propose_home_recipe", {"recipe_id": "accident-aftercare", "language": "de"})]

    class Model(strands_agent._fixture_model_class()):
        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            if calls:
                tool_name, args = calls.pop(0)
                async for event in strands_agent._tool_events(tool_name, args):
                    yield event
            else:
                async for event in strands_agent._text_events("Abschnitt zur Bestätigung bereit."):
                    yield event

    monkeypatch.setattr(strands_agent, "_build_model", lambda *args, **kwargs: Model())
    first = application.run_agent_chat(profile_id="lukas", message="Ablauf vorbereiten.")
    assert len(first.proposed_recipes) == 1
    proposal = first.proposed_recipes[0]
    assert driver.executed == []
    confirm(application, proposal)
    calls.extend(
        [
            ("list_home_recipe_runs", {}),
            ("propose_next_recipe_stage", {"run_id": proposal.run_id}),
        ]
    )
    second = application.run_agent_chat(profile_id="lukas", message="Nächsten Abschnitt prüfen.")
    assert [event.tool_name for event in second.tool_events] == [
        "list_home_recipe_runs",
        "propose_next_recipe_stage",
    ]
    assert len(second.proposed_recipes) == 1
    assert second.proposed_recipes[0].run_id == proposal.run_id
    assert len(second.proposed_plans[0].steps) == 3
    assert driver.executed == ["contact-register"]


def test_duplicate_pending_proposal_failure_cannot_close_retained_run(app):
    application, driver = app
    first = start(application)
    duplicate = application.prepare_recipe_stage(profile_id="lukas", run_id=first.run_id)
    assert duplicate.plan_id == first.plan_id
    application.discard_recipe_preparations((duplicate,))
    result = confirm(application, first)
    assert result["recipe_run"]["status"] == "ready"
    assert driver.executed == ["contact-register"]


def test_pending_budget_and_run_budget_fail_before_new_preparation(app, monkeypatch):
    application, driver = app
    first = start(application)
    count = len(driver.prepared)
    monkeypatch.setattr("folderhome.application.local_app._MAX_RECIPE_RUNS", 1)
    with pytest.raises(LocalAppError, match="budget"):
        start(application)
    assert len(driver.prepared) == count
    monkeypatch.setattr("folderhome.application.local_app._MAX_PROPOSED_AGENT_PLANS", 0)
    with pytest.raises(LocalAppError, match="Budget"):
        application.prepare_recipe_stage(profile_id="lukas", run_id=first.run_id)
    assert len(driver.prepared) == count


def test_public_proposal_mutation_cannot_change_retained_approval(app):
    application, driver = app
    first = start(application)
    first.plan.approval_context["result_bindings"].append({"invented": True})
    # The server retains the original consent material, not the returned object.
    result = application.confirm_agent_plan(
        plan_id=first.plan_id,
        plan_sha256=first.plan.plan_sha256,
        step_ids=tuple(s.step_id for s in first.plan.steps),
    )
    assert result["recipe_run"]["status"] == "ready"
    assert driver.executed == ["contact-register"]


def test_shutdown_cleanup_failure_still_stops_own_scheduler_and_allows_cleanup_retry(app):
    from types import SimpleNamespace

    application, driver = app
    first = start(application)
    run = application._recipe_runs[first.run_id]
    discarded = run._discard
    closed = []
    application.scheduler_controller = SimpleNamespace(close=lambda: closed.append(True))

    def fail(_):
        raise OSError("private cleanup path")

    run._discard = fail
    with pytest.raises(CapabilityRecipeError):
        application.close()
    assert closed == [True]
    assert application.proposed_agent_plan(first.plan_id) is None
    run._discard = discarded
    application.close()
    assert first.run_id not in application._recipe_runs
    assert driver.executed == []


def test_uncertain_result_delivery_failure_preserves_no_retry_response(app, monkeypatch):
    from folderhome.application.workflow_execution import WorkflowExecutionOutcomeUnknown

    application, driver = app
    first = start(application)

    def uncertain(*args):
        raise WorkflowExecutionOutcomeUnknown("private provider path")

    def cannot_retain(**kwargs):
        raise OSError("private result path")

    monkeypatch.setattr(driver, "execute", uncertain)
    monkeypatch.setattr(application, "_retain_uncertain_result", cannot_retain)
    response = request(
        application,
        "/api/v1/agent/confirm",
        payload={
            "schema": "folderhome.local-agent-confirmation-request.v1",
            "plan_id": first.plan_id,
            "plan_sha256": first.plan.plan_sha256,
            "step_ids": [s.step_id for s in first.plan.steps],
        },
    )
    assert response.status_code == 200
    assert response.payload["execution_outcome_unknown"] is True
    assert response.payload["retry_safe"] is False
    assert response.payload["result_delivery_incomplete"] is True
    assert response.payload["recipe_execution"]["uncertain_steps"]
    assert "private" not in json.dumps(response.payload)


def test_invalid_partial_evidence_callback_cannot_strand_consumed_run(app, monkeypatch):
    from folderhome.application.workflow_execution import WorkflowExecutionOutcomeUnknown

    class BrokenEvidence(WorkflowExecutionOutcomeUnknown):
        def public_evidence(self):
            raise OSError("private evidence path")

    application, driver = app
    first = start(application)

    def uncertain(*args):
        raise BrokenEvidence("private provider path")

    monkeypatch.setattr(driver, "execute", uncertain)
    response = confirm(application, first)
    assert response["recipe_run"]["status"] == "aborted"
    assert response["execution_outcome_unknown"] is True
    assert response["recipe_execution"]["uncertain_steps"][0]["evidence_unavailable"] is True
    assert "private" not in json.dumps(response)


def test_missing_recipe_metadata_never_falls_through_to_ordinary_execution(app):
    application, driver = app
    first = start(application)
    # An equal ID can independently exist in the ordinary preparation store.
    application.workflow_executor.prepare(
        workflow_id="contact-register", profile_id="lukas", request=payload()["steps"][0]["request"]
    )
    application._recipe_plans.pop(first.plan_id)
    with pytest.raises(LocalAppError):
        confirm(application, first)
    assert driver.executed == []


def test_closing_v2_run_leaves_equal_ordinary_preparation_available(app):
    application, driver = app
    first = start(application)
    ordinary = application.workflow_executor.prepare(
        workflow_id="contact-register", profile_id="lukas", request=payload()["steps"][0]["request"]
    )
    assert ordinary.envelope_id == first.plan.steps[0].execution_envelope.envelope_id
    application.close_recipe_run(profile_id="lukas", run_id=first.run_id)
    report = application.workflow_executor.execute(
        envelope_id=ordinary.envelope_id, approved_at="2026-09-09T13:00:00+02:00"
    )
    assert report.status == "executed"


def test_failed_followup_model_turn_keeps_confirmed_run_and_can_reprepare(app):
    application, driver = app
    first = start(application)
    confirm(application, first)
    second = application.prepare_recipe_stage(profile_id="lukas", run_id=first.run_id)
    application.discard_recipe_preparations((second,))
    listed = application.recipe_runs_payload(profile_id="lukas")["runs"]
    assert len(listed) == 1
    assert listed[0]["status"] == "ready"
    assert listed[0]["completed_step_refs"] == ["contacts"]
    assert listed[0]["pending_plan_id"] is None
    retried = application.propose_recipe_stage(profile_id="lukas", run_id=first.run_id)
    assert retried.run_id == first.run_id
    assert driver.executed == ["contact-register"]
    assert confirm(application, retried)["recipe_run"]["status"] == "completed"
