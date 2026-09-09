"""Local API recipe orchestration; adapter effects are synthetic test doubles."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_local_app import _app
from test_recipes import RESOURCE_IDS, _Gateway, _statuses

from folderhome.application.local_app import LocalAppError
from folderhome.application.master_agent import build_master_agent_plan
from folderhome.application.recipes import load_bundled_recipe
from folderhome.application.workflow_execution import WorkflowExecutionError
from folderhome.contracts import LogicalResource, ResourceRegistry


class RecipeGateway(_Gateway):
    def __init__(self, *, failing_workflow=None):
        super().__init__(failing_workflow=failing_workflow)
        self.discarded = []

    def catalog(self):
        return [
            SimpleNamespace(workflow_id=key, status=value) for key, value in _statuses().items()
        ]

    def prepare(self, *, workflow_id, profile_id, request):
        assert profile_id == "lukas"
        return super().prepare(workflow_id, request)

    def execute(self, *, envelope_id, approved_at):
        return super().execute(envelope_id, approved_at)

    def discard_unexecuted(self, envelope_ids):
        self.discarded.extend(envelope_ids)
        return envelope_ids


def recipe_app(tmp_path, *, failing_workflow=None):
    app = _app(tmp_path)
    app.workflow_executor = RecipeGateway(failing_workflow=failing_workflow)
    app.resource_registry = ResourceRegistry(
        os_account=app.profiles.os_account,
        resources=tuple(
            LogicalResource(
                resource_id=key, kind="directory", local_path=tmp_path / key,
                operations=frozenset({"read", "list"}),
                purposes=frozenset({"documents.source"}),
                profile_ids=frozenset({"lukas"}), cloud_context="deny",
            ) for key in sorted(RESOURCE_IDS)
        ),
        profile_defaults={}, known_profile_ids=app._profile_ids,
    )
    return app


def propose(app):
    return app.propose_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="en")


def confirm(app, recipe_plan, **changes):
    arguments = dict(
        plan_id=recipe_plan.plan_id,
        plan_sha256=recipe_plan.plan.plan_sha256,
        step_ids=tuple(step.step_id for step in recipe_plan.plan.steps),
    )
    arguments.update(changes)
    return app.confirm_agent_plan(**arguments)


def test_recipe_catalog_is_profile_scoped_and_non_executing(tmp_path: Path):
    app = recipe_app(tmp_path)
    catalog = app.recipe_catalog_payload(profile_id="lukas", language="en")
    assert catalog["recipes"][0]["available"] is True
    assert app.recipe_catalog_payload(profile_id="hanna", language="de")["recipes"][0][
        "available"
    ] is False
    assert str(tmp_path) not in str(catalog)
    assert app.workflow_executor.prepared == []
    assert app.workflow_executor.executed == []


def test_recipe_proposal_retains_the_whole_chain_without_execution(tmp_path: Path):
    app = recipe_app(tmp_path)
    recipe_plan = propose(app)
    assert app.proposed_agent_plan(recipe_plan.plan_id) == recipe_plan.plan
    assert len(recipe_plan.plan.steps) == 4
    assert app.workflow_executor.executed == []


@pytest.mark.parametrize("change", ["partial", "hash"])
def test_recipe_confirmation_cannot_change_the_chain(tmp_path: Path, change: str):
    app = recipe_app(tmp_path)
    recipe_plan = propose(app)
    changes = {"plan_sha256": "0" * 64} if change == "hash" else {
        "step_ids": (recipe_plan.plan.steps[-1].step_id,)
    }
    with pytest.raises(LocalAppError):
        confirm(app, recipe_plan, **changes)
    assert app.workflow_executor.executed == []


def test_recipe_confirmation_reports_partial_execution_and_stops(tmp_path: Path):
    app = recipe_app(tmp_path, failing_workflow="correspondence-studio")
    recipe_plan = propose(app)
    result = confirm(app, recipe_plan)
    assert result["recipe_execution"]["status"] == "aborted"
    assert result["recipe_execution"]["executed_step_refs"] == ["contacts"]
    assert result["recipe_execution"]["failed_step_refs"] == ["letter"]
    assert result["recipe_execution"]["not_attempted_step_refs"] == ["draft", "appointment"]
    assert len(result["execution_reports"]) == 1
    assert len(app.execution_results_payload(profile_id="lukas", limit=25)["results"]) == 1
    with pytest.raises((LocalAppError, WorkflowExecutionError)):
        confirm(app, recipe_plan)
    assert app.workflow_executor.executed == ["contact-register"]


def test_concurrent_recipe_confirmation_executes_the_chain_only_once(tmp_path: Path):
    app = recipe_app(tmp_path)
    recipe_plan = propose(app)

    def attempt():
        try:
            return confirm(app, recipe_plan)
        except (LocalAppError, WorkflowExecutionError):
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert app.workflow_executor.executed == list(
        load_bundled_recipe("accident-aftercare").workflow_ids
    )


def test_reset_discards_recipe_and_blocks_old_confirmation(tmp_path: Path):
    app = recipe_app(tmp_path)
    recipe_plan = propose(app)
    app.reset_agent_conversation("lukas")
    with pytest.raises(LocalAppError):
        confirm(app, recipe_plan)
    assert len(app.workflow_executor.discarded) == 4


def test_recipe_unknown_id_and_unconfigured_profile_fail_closed(tmp_path: Path):
    app = recipe_app(tmp_path)
    with pytest.raises(ValueError, match="Rezept"):
        app.propose_recipe(profile_id="lukas", recipe_id="../private", language="en")
    with pytest.raises(ValueError, match="Ressource"):
        app.propose_recipe(profile_id="hanna", recipe_id="accident-aftercare", language="en")
    assert app.workflow_executor.prepared == []


def test_evicting_plan_does_not_discard_envelopes_shared_with_new_plan(tmp_path, monkeypatch):
    app = recipe_app(tmp_path)
    monkeypatch.setattr("folderhome.application.local_app._MAX_PROPOSED_AGENT_PLANS", 1)
    old = propose(app)
    new = app.propose_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="de")
    assert app.proposed_agent_plan(old.plan_id) is None
    assert app.proposed_agent_plan(new.plan_id) == new.plan
    assert app.workflow_executor.discarded == []


def request(app, target, *, payload=None, token=True, method=None):
    headers = {"host": "127.0.0.1:8765", "content-type": "application/json"}
    if token:
        headers["x-folderhome-token"] = app.session_token
    return app.handle(
        method=method or ("POST" if payload is not None else "GET"), target=target,
        headers=headers, body=json.dumps(payload).encode() if payload is not None else b"",
        server_port=8765,
    )


def test_recipe_routes_use_existing_authentication_and_strict_request_schema(tmp_path):
    app = recipe_app(tmp_path)
    route = "/api/v1/agent/recipes"
    assert request(app, route + "?profile_id=lukas&language=en", token=False).status_code == 401
    catalog = request(app, route + "?profile_id=lukas&language=en")
    assert catalog.status_code == 200
    assert catalog.payload["recipes"][0]["available"] is True
    payload = {
        "schema": "folderhome.local-recipe-plan-request.v1", "profile_id": "lukas",
        "language": "en", "recipe_id": "accident-aftercare",
    }
    invalid = request(app, route + "/plan", payload={**payload, "path": "C:/private"})
    assert invalid.status_code == 400
    result = request(app, route + "/plan", payload=payload)
    assert result.status_code == 200
    assert result.payload["recipe_id"] == "accident-aftercare"
    assert result.payload["execution_performed"] is False
    assert request(app, route + "/plan").status_code == 405
    assert request(app, route, payload=payload).status_code == 405
    assert request(app, route + "?profile_id=lukas&profile_id=hanna").status_code == 400


def test_recipe_failure_details_do_not_expose_private_adapter_data(tmp_path, monkeypatch):
    app = recipe_app(tmp_path)
    plan = propose(app)

    def fail(**kwargs):
        raise RuntimeError("C:/private/secret.txt mailbox=private@example.invalid")

    monkeypatch.setattr(app.workflow_executor, "execute", fail)
    result = confirm(app, plan)
    assert result["recipe_execution"]["status"] == "aborted"
    assert "private" not in json.dumps(result)


def test_strands_chat_can_propose_a_recipe_without_executing_it(tmp_path, monkeypatch):
    from folderhome.application import strands_agent

    class RecipeModel(strands_agent._fixture_model_class()):
        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            if any("toolResult" in block for item in messages for block in item["content"]):
                async for event in strands_agent._text_events("Recipe prepared; await approval."):
                    yield event
            else:
                async for event in strands_agent._tool_events("propose_home_recipe", {
                    "recipe_id": "accident-aftercare", "language": "en",
                }):
                    yield event

    monkeypatch.setattr(strands_agent, "_build_model", lambda *args, **kwargs: RecipeModel())
    app = recipe_app(tmp_path)
    report = app.run_agent_chat(profile_id="lukas", message="Prepare the accident journey.")
    assert len(report.proposed_plans) == 1
    assert len(report.proposed_plans[0].steps) == 4
    assert report.tool_events[0].tool_name == "propose_home_recipe"
    assert report.network_used is False
    assert app.workflow_executor.executed == []
    assert app.proposed_agent_plan(report.proposed_plans[0].plan_id) is not None


def test_recipe_prepare_failure_is_redacted_at_http_boundary(tmp_path, monkeypatch):
    app = recipe_app(tmp_path)

    def fail(**kwargs):
        raise WorkflowExecutionError("C:/private/secret.txt mailbox=private@example.invalid")

    monkeypatch.setattr(app.workflow_executor, "prepare", fail)
    result = request(app, "/api/v1/agent/recipes/plan", payload={
        "schema": "folderhome.local-recipe-plan-request.v1", "profile_id": "lukas",
        "language": "en", "recipe_id": "accident-aftercare",
    })
    assert result.status_code == 409
    assert "private" not in result.content.decode()


def test_recipe_attempt_invalidates_other_plans_sharing_its_envelopes(tmp_path):
    app = recipe_app(tmp_path, failing_workflow="contact-register")
    first = propose(app)
    other = app.propose_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="de")
    result = confirm(app, first)
    assert result["invalidated_plan_ids"] == [other.plan_id]
    assert app.proposed_agent_plan(other.plan_id) is None
    with pytest.raises(LocalAppError):
        confirm(app, other)


@pytest.mark.parametrize("mail_gate", [True, False])
def test_local_recipe_api_runs_real_local_adapters_with_synthetic_mail(tmp_path, mail_gate):
    from test_workflow_execution import _recipe_environment

    app = _app(tmp_path)
    gateway, registry, transport, export, output = _recipe_environment(
        tmp_path, allow_mail_draft=mail_gate,
    )
    app.workflow_executor = gateway
    app.resource_registry = registry
    proposal = request(app, "/api/v1/agent/recipes/plan", payload={
        "schema": "folderhome.local-recipe-plan-request.v1", "profile_id": "lukas",
        "language": "en", "recipe_id": "accident-aftercare",
    })
    assert proposal.status_code == 200, proposal.payload
    plan = proposal.payload["plan"]
    assert not (output / "Schadensmeldung.txt").exists()
    assert transport.appended == []
    result = request(app, "/api/v1/agent/confirm", payload={
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": plan["plan_id"], "plan_sha256": plan["plan_sha256"],
        "step_ids": [step["step_id"] for step in plan["steps"]],
    })
    assert result.status_code == 200, result.payload
    assert result.payload["recipe_execution"]["status"] == ("executed" if mail_gate else "aborted")
    assert (output / "Schadensmeldung.txt").is_file()
    assert (export / "Unfall-Folgetermin.ics").exists() is mail_gate
    assert len(transport.appended) == (1 if mail_gate else 0)
    retained = app.execution_results_payload(profile_id="lukas", limit=25)["results"]
    assert len(retained) == (4 if mail_gate else 2)
    assert any(item["artifacts"] for item in retained)


def test_changed_recipe_context_cannot_consume_confirmation_or_write_real_artifacts(tmp_path):
    from test_workflow_execution import _recipe_environment

    app = _app(tmp_path)
    gateway, registry, transport, export, output = _recipe_environment(
        tmp_path, allow_mail_draft=True,
    )
    app.workflow_executor = gateway
    app.resource_registry = registry
    prepared = propose(app)
    changed = replace(prepared, handoffs=())
    app._recipe_plans[prepared.plan_id] = changed

    with pytest.raises(LocalAppError):
        confirm(app, changed)
    assert not (output / "Schadensmeldung.txt").exists()
    assert not (export / "Unfall-Folgetermin.ics").exists()
    assert transport.appended == []

    # Rejected validation is not an execution attempt and must not burn the valid plan.
    app._recipe_plans[prepared.plan_id] = prepared
    result = confirm(app, prepared)
    assert result["recipe_execution"]["status"] == "executed"
    assert (output / "Schadensmeldung.txt").is_file()
    assert (export / "Unfall-Folgetermin.ics").is_file()
    assert len(transport.appended) == 1


def test_ordinary_chain_rechecks_content_and_keeps_completed_evidence(tmp_path, monkeypatch):
    from test_workflow_execution import _recipe_environment

    app = _app(tmp_path)
    gateway, registry, transport, export, output = _recipe_environment(
        tmp_path, allow_mail_draft=True,
    )
    app.workflow_executor = gateway
    app.resource_registry = registry
    prepared = propose(app)
    steps = prepared.plan.steps[:2]
    plan = build_master_agent_plan(
        "Prepare contact and letter.", profile_id="lukas", language="en",
        expert_id="communication_expert", workflow_ids=tuple(s.workflow_id for s in steps),
        confidence="high", why="Two explicitly selected communication workflows.",
        execution_envelopes={s.workflow_id: s.execution_envelope for s in steps},
    )
    app._retain_agent_plan(plan)
    real_execute = gateway.execute

    def execute(*, envelope_id, approved_at):
        report = real_execute(envelope_id=envelope_id, approved_at=approved_at)
        steps[1].execution_envelope.domain_plan["unapproved_change"] = True
        return report

    monkeypatch.setattr(gateway, "execute", execute)
    with pytest.raises(LocalAppError):
        app.confirm_agent_plan(
            plan_id=plan.plan_id, plan_sha256=plan.plan_sha256,
            step_ids=tuple(s.step_id for s in plan.steps),
        )
    assert not (output / "Schadensmeldung.txt").exists()
    assert transport.appended == []
    retained = app.execution_results_payload(profile_id="lukas", limit=25)["results"]
    assert len(retained) == 1
    assert retained[0]["workflow_id"] == "contact-register"


def test_local_recipe_does_not_store_an_unrelated_report_as_success(tmp_path, monkeypatch):
    app = recipe_app(tmp_path)
    prepared = propose(app)
    gateway = app.workflow_executor
    real_execute = gateway.execute
    other = prepared.plan.steps[-1].execution_envelope

    def execute(*, envelope_id, approved_at):
        report = real_execute(envelope_id=envelope_id, approved_at=approved_at)
        return replace(report, envelope_id=other.envelope_id)

    monkeypatch.setattr(gateway, "execute", execute)
    result = confirm(app, prepared)
    assert result["recipe_execution"]["status"] == "aborted"
    assert result["execution_reports"] == []
    assert result["execution_outcome_unknown"] is True
    assert result["result_delivery_incomplete"] is True
    assert app.execution_results_payload(profile_id="lukas", limit=25)["results"] == []
    with pytest.raises(LocalAppError):
        confirm(app, prepared)
    assert gateway.executed == ["contact-register"]


def test_ordinary_plan_refuses_unrelated_execution_evidence(tmp_path, monkeypatch):
    app = recipe_app(tmp_path)
    prepared = propose(app)
    step = prepared.plan.steps[0]
    plan = build_master_agent_plan(
        "Prepare contact.", profile_id="lukas", language="en",
        expert_id=step.expert_id, workflow_ids=(step.workflow_id,), confidence="high",
        why="One explicitly selected workflow.",
        execution_envelopes={step.workflow_id: step.execution_envelope},
    )
    app._retain_agent_plan(plan)
    real_execute = app.workflow_executor.execute

    def execute(*, envelope_id, approved_at):
        report = real_execute(envelope_id=envelope_id, approved_at=approved_at)
        return replace(report, workflow_id="calendar-handoff")

    monkeypatch.setattr(app.workflow_executor, "execute", execute)
    with pytest.raises(LocalAppError):
        app.confirm_agent_plan(
            plan_id=plan.plan_id, plan_sha256=plan.plan_sha256,
            step_ids=tuple(item.step_id for item in plan.steps),
        )
    assert app.execution_results_payload(profile_id="lukas", limit=25)["results"] == []


def test_web_recipe_controls_have_bilingual_review_and_aborted_outcomes():
    root = Path(__file__).parents[1] / "src" / "folderhome" / "web_ui"
    html = (root / "index.html").read_text(encoding="utf-8")
    script = (root / "app.js").read_text(encoding="utf-8")
    for element in ("recipe-form", "recipe-select", "prepare-recipe", "recipe-hint"):
        assert f'id="{element}"' in html
    for key in ("recipeLabel", "recipePrepare", "recipeAborted", "recipeReview", "planDetails"):
        assert script.count(f"    {key}:") == 2
    assert "Deterministische Rezeptprüfung" in script
    assert "result.not_attempted_step_refs" in script
    assert "proposed_recipes: [recipe]" in script


def test_chat_retention_protects_envelopes_in_later_plans_of_the_same_report(tmp_path, monkeypatch):
    from dataclasses import replace

    from folderhome.application import strands_agent

    app = recipe_app(tmp_path)
    old = propose(app)
    later = app.prepare_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="de")
    unrelated = replace(
        old.plan, plan_id="plan_" + "b" * 20,
        steps=tuple(replace(step, execution_envelope=None) for step in old.plan.steps),
    )
    report = SimpleNamespace(proposed_plans=(unrelated, later.plan), proposed_recipes=(later,))
    monkeypatch.setattr(strands_agent, "run_folderhome_agent_turn", lambda **kwargs: (report, ()))
    monkeypatch.setattr("folderhome.application.local_app._MAX_PROPOSED_AGENT_PLANS", 1)
    app.run_agent_chat(profile_id="lukas", message="Prepare two plans.")
    assert app.proposed_agent_plan(later.plan_id) is not None
    assert app.workflow_executor.discarded == []


def test_failed_second_preparation_preserves_first_in_flight_recipe(tmp_path, monkeypatch):
    app = recipe_app(tmp_path)
    first = app.prepare_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="en")
    prepare = app.workflow_executor.prepare
    calls = 0

    def fail_second(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise WorkflowExecutionError("synthetic preparation failure")
        return prepare(**kwargs)

    monkeypatch.setattr(app.workflow_executor, "prepare", fail_second)
    with pytest.raises(WorkflowExecutionError):
        app.prepare_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="de")
    assert app.workflow_executor.discarded == []
    app.discard_recipe_preparations((first,))
    assert len(app.workflow_executor.discarded) == 4
    assert app._pending_recipe_plans == {}


def test_failed_model_turn_releases_pending_recipe_preparations(tmp_path, monkeypatch):
    from strands.types.exceptions import EventLoopException

    from folderhome.application import strands_agent

    class FailingModel(strands_agent._fixture_model_class()):
        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            if any("toolResult" in block for item in messages for block in item["content"]):
                raise RuntimeError("synthetic model failure after successful preparation")
            async for event in strands_agent._tool_events("propose_home_recipe", {
                "recipe_id": "accident-aftercare", "language": "en",
            }):
                yield event

    monkeypatch.setattr(strands_agent, "_build_model", lambda *args, **kwargs: FailingModel())
    app = recipe_app(tmp_path)
    with pytest.raises(EventLoopException):
        app.run_agent_chat(profile_id="lukas", message="Prepare the accident journey.")
    assert app._pending_recipe_plans == {}
    assert app._proposed_agent_plans == {}
    assert len(app.workflow_executor.discarded) == 4
    assert app.workflow_executor.executed == []


def test_failed_recipe_preserves_an_in_flight_ordinary_specialist_plan(tmp_path, monkeypatch):
    from folderhome.application.master_agent import build_master_agent_plan

    app = recipe_app(tmp_path)
    step = load_bundled_recipe("accident-aftercare").steps[0]
    envelope = app.workflow_executor.prepare(
        workflow_id=step.workflow_id, profile_id="lukas", request=step.request,
    )
    plan = build_master_agent_plan(
        "Prepare contacts", profile_id="lukas", language="en",
        expert_id="communication_expert", workflow_ids=(step.workflow_id,),
        persona_id=None, confidence="high", why="Explicit synthetic test",
        execution_envelopes={step.workflow_id: envelope},
    )
    app.protect_agent_preparation(plan)
    prepare = app.workflow_executor.prepare

    def fail_later(**kwargs):
        if kwargs["workflow_id"] != "contact-register":
            raise WorkflowExecutionError("synthetic failure")
        return prepare(**kwargs)

    monkeypatch.setattr(app.workflow_executor, "prepare", fail_later)
    with pytest.raises(WorkflowExecutionError):
        app.prepare_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="en")
    assert app.workflow_executor.discarded == []
    app.discard_agent_preparations((plan,))
    assert app.workflow_executor.discarded == [envelope.envelope_id]


def test_reset_also_releases_standalone_pending_preparations(tmp_path):
    app = recipe_app(tmp_path)
    pending = app.prepare_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="en")
    result = app.reset_agent_conversation("lukas")
    assert pending.plan_id in result["discarded_plan_ids"]
    assert app._pending_agent_plans == {}
    assert app._pending_recipe_plans == {}
    assert len(app.workflow_executor.discarded) == 4


def test_failed_duplicate_preparation_does_not_release_another_owners_plan(tmp_path):
    from dataclasses import replace

    app = recipe_app(tmp_path)
    recipe = app.prepare_recipe(profile_id="lukas", recipe_id="accident-aftercare", language="en")
    duplicate = replace(recipe.plan)
    app.protect_agent_preparation(duplicate)
    app.discard_agent_preparations((duplicate,))
    assert app.workflow_executor.discarded == []
    app.discard_agent_preparations((recipe.plan,))
    assert len(app.workflow_executor.discarded) == 4
