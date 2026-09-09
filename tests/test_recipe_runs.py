"""Section approval, real result lineage, failure stops and preparation lifetime."""

import traceback
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace

import pytest
from test_recipe_results import payload
from test_recipes import APPROVED_AT, RESOURCE_IDS, _Gateway, _statuses

from folderhome.application import recipes
from folderhome.application.workflow_execution import WorkflowExecutionGateway
from folderhome.contracts.master_agent import MasterPlanApproval
from folderhome.contracts.recipes import CapabilityRecipeError
from folderhome.contracts.workflow_execution import WorkflowAdapterDescriptor


class Adapter:
    """Stub domain boundary; the preparation and execution gateway itself is real."""

    def __init__(self, driver, workflow_id):
        self.driver = driver
        self.workflow_id = workflow_id
        self.descriptor = WorkflowAdapterDescriptor(
            workflow_id=workflow_id,
            adapter_id=workflow_id.replace("-", "_") + ".v1",
            status="connected",
            plan_schema="folderhome.stub-plan.v1",
            report_schema="folderhome.stub-report.v1",
            side_effects=("file.create",),
            reason="Synthetic domain adapter",
            request_schema={
                "type": "object",
                "additionalProperties": False,
                "required": [],
                "properties": {},
            },
        )

    def prepare(self, *, profile_id, request):
        return self.driver.prepare(self.workflow_id, request), None

    def execute(self, *, envelope, domain_plan, approved_at):
        return self.driver.execute(envelope.envelope_id, approved_at)


def core_gateway(driver):
    return WorkflowExecutionGateway(
        tuple(
            Adapter(driver, name)
            for name in (
                "contact-register",
                "correspondence-studio",
                "mail-connector",
                "calendar-handoff",
            )
        )
    )


class Gateway(_Gateway):
    def __init__(self):
        super().__init__()
        self.discarded = []
        self.returned = []
        self.fail_prepare = None
        self.fail_execute = None
        self.bad_report = False
        self.after_execute = None

    def prepare(self, workflow_id, request):
        if workflow_id == self.fail_prepare:
            raise ValueError("private location must not escape: C:/secret")
        result = super().prepare(workflow_id, request)
        return replace(
            result, domain_plan={"schema": result.domain_plan_schema, "request": deepcopy(request)}
        )

    def execute(self, envelope_id, approved_at):
        if self._by_envelope[envelope_id] == self.fail_execute:
            raise RuntimeError("private location must not escape: C:/secret")
        report = super().execute(envelope_id, approved_at)
        report = replace(
            report,
            domain_report={
                "schema": report.domain_report_schema,
                "contacts": [{"name": "Müller"}],
                "revision": 2,
            },
        )
        if self.bad_report:
            report = replace(report, envelope_id="workflow_envelope_" + "0" * 64)
        self.returned.append(report)
        if self.after_execute:
            self.after_execute()
        return report

    def discard(self, ids):
        self.discarded.extend(ids)


def run(gateway, *, raw=None, profile="lukas"):
    # Public construction lives beside the existing recipe API.
    factory = getattr(recipes, "create_recipe_run", None)
    assert callable(factory), "Recipe-v2 needs a section runner, not the v1 whole-chain planner"
    journey = factory(
        recipes.parse_recipe(raw or payload()),
        profile_id=profile,
        language="de",
        gateway=core_gateway(gateway),
    )
    original_discard = journey._discard

    def observed_discard(ids):
        gateway.discard(ids)
        return original_discard(ids)

    journey._discard = observed_discard
    return journey


def plan(run):
    return run.plan_next(endpoint_statuses=_statuses(), known_resource_ids=RESOURCE_IDS)


def approval(plan, **changes):
    values = dict(
        approval_id="approval_recipe_stage",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        step_ids=tuple(s.step_id for s in plan.steps),
        approved_at=APPROVED_AT,
    )
    values.update(changes)
    return MasterPlanApproval(**values)


def test_only_concrete_prefix_is_prepared_and_execution_does_not_plan_ahead():
    gateway = Gateway()
    journey = run(gateway)
    first = plan(journey)
    assert [s.workflow_id for s in first.steps] == ["contact-register"]
    assert first.approval_context["step_refs"] == ["contacts"]
    assert gateway.executed == []
    result = journey.confirm(approval(first))
    assert result["run_status"] == "ready"
    assert result["completed_step_refs"] == ["contacts"]
    assert gateway.executed == ["contact-register"]
    assert [w for w, _ in gateway.prepared] == ["contact-register"]
    second = plan(journey)
    assert [s.workflow_id for s in second.steps] == [
        "correspondence-studio",
        "mail-connector",
        "calendar-handoff",
    ]
    assert second.steps[0].execution_envelope.domain_plan["request"]["recipient"] == "Müller"
    provenance = second.approval_context["result_bindings"][0]
    assert provenance["from_step"] == "contacts"
    assert provenance["source_plan_id"] == first.plan_id
    assert provenance["source_execution_id"] == result["execution_reports"][0]["execution_id"]
    assert provenance["value"] == "Müller"
    with pytest.raises(CapabilityRecipeError):
        journey.confirm(approval(first))
    assert gateway.executed == ["contact-register"]
    assert journey.confirm(approval(second))["run_status"] == "completed"
    with pytest.raises(CapabilityRecipeError):
        plan(journey)


def test_three_dependency_stages_require_three_distinct_approvals():
    raw = payload()
    raw["result_bindings"].append(
        {
            "from_step": "letter",
            "to_step": "draft",
            "source_path": ["revision"],
            "target_field": "expected_revision",
            "value_type": "integer",
        }
    )
    gateway = Gateway()
    journey = run(gateway, raw=raw)
    refs = []
    for _ in range(3):
        section = plan(journey)
        refs.append(section.approval_context["step_refs"])
        journey.confirm(approval(section))
    assert refs == [["contacts"], ["letter"], ["draft", "appointment"]]
    assert gateway.prepared[2][1]["expected_revision"] == 2


@pytest.mark.parametrize("difference", ["run", "profile"])
def test_approval_from_another_run_or_profile_is_rejected(difference):
    one = run(Gateway())
    other_gateway = Gateway()
    other = run(other_gateway, profile="hanna" if difference == "profile" else "lukas")
    first, second = plan(one), plan(other)
    assert first.plan_id != second.plan_id
    with pytest.raises(CapabilityRecipeError):
        other.confirm(approval(first))
    assert other_gateway.executed == []


def test_exported_plan_result_and_adapter_report_mutation_cannot_change_handoff():
    gateway = Gateway()
    journey = run(gateway)
    first = plan(journey)
    first.approval_context["recipe_id"] = "foreign"
    result = journey.confirm(approval(first))  # Returned objects are detached.
    result["execution_reports"][0]["domain_report"]["contacts"][0]["name"] = "forged"
    gateway.returned[0].domain_report["contacts"][0]["name"] = "changed later"
    snapshot = journey.snapshot()
    snapshot["last_execution"]["execution_reports"].clear()
    following = plan(journey)
    assert following.approval_context["result_bindings"][0]["value"] == "Müller"
    assert len(journey.snapshot()["last_execution"]["execution_reports"]) == 1


@pytest.mark.parametrize("failure", ["exception", "wrong_report"])
def test_uncertain_source_stops_run_and_consumes_approval(failure):
    gateway = Gateway()
    journey = run(gateway)
    first = plan(journey)
    gateway.fail_execute = "contact-register" if failure == "exception" else None
    gateway.bad_report = failure == "wrong_report"
    result = journey.confirm(approval(first))
    assert result["run_status"] == "aborted"
    assert result["execution_outcome_unknown"] is True
    assert result["execution_reports"] == []
    assert result["retry_safe"] is False
    assert "secret" not in str(result)
    with pytest.raises(CapabilityRecipeError):
        journey.confirm(approval(first))
    with pytest.raises(CapabilityRecipeError):
        plan(journey)


def test_partial_section_reports_confirmed_effects_and_never_runs_remaining_step():
    gateway = Gateway()
    journey = run(gateway)
    journey.confirm(approval(plan(journey)))
    second = plan(journey)
    gateway.fail_execute = "mail-connector"
    result = journey.confirm(approval(second))
    assert result["completed_step_refs"] == ["contacts", "letter"]
    assert [(x["step_ref"], x["status"]) for x in result["outcomes"]] == [
        ("letter", "executed"),
        ("draft", "failed"),
        ("appointment", "not_attempted"),
    ]
    assert gateway.executed == ["contact-register", "correspondence-studio"]
    assert len(result["execution_reports"]) == 1


def test_concurrent_confirmation_executes_once():
    gateway = Gateway()
    journey = run(gateway)
    exact = approval(plan(journey))

    def attempt():
        try:
            return journey.confirm(exact)
        except CapabilityRecipeError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(item is not None for item in results) == 1
    assert gateway.executed == ["contact-register"]


def test_failed_preparation_discards_new_envelopes_and_allows_safe_replan():
    gateway = Gateway()
    journey = run(gateway)
    journey.confirm(approval(plan(journey)))
    gateway.fail_prepare = "mail-connector"
    before = len(gateway.discarded)
    with pytest.raises(CapabilityRecipeError):
        plan(journey)
    assert len(gateway.discarded) == before + 1
    assert journey.snapshot()["status"] == "ready"
    gateway.fail_prepare = None
    assert plan(journey).approval_context["step_refs"] == ["letter", "draft", "appointment"]


def test_closing_run_discards_pending_plan_and_refuses_further_actions():
    gateway = Gateway()
    journey = run(gateway)
    first = plan(journey)
    journey.close()
    assert first.steps[0].execution_envelope.envelope_id in gateway.discarded
    with pytest.raises(CapabilityRecipeError):
        journey.confirm(approval(first))
    with pytest.raises(CapabilityRecipeError):
        plan(journey)
    assert gateway.executed == []


def test_missing_result_value_blocks_following_preparation_without_replaying_source():
    raw = payload()
    raw["result_bindings"][0]["source_path"] = ["missing"]
    gateway = Gateway()
    journey = run(gateway, raw=raw)
    journey.confirm(approval(plan(journey)))
    with pytest.raises(CapabilityRecipeError):
        plan(journey)
    assert [w for w, _ in gateway.prepared] == ["contact-register"]
    assert gateway.executed == ["contact-register"]


def test_repeated_plan_read_is_stable_and_does_not_reprepare():
    gateway = Gateway()
    journey = run(gateway)
    first = plan(journey)
    assert plan(journey).plan_id == first.plan_id
    assert len(gateway.prepared) == 1


def test_run_does_not_reverse_adapter_redaction_in_approval_context():
    gateway = Gateway()
    raw = payload()
    raw["steps"][0]["request"]["private_hint"] = "private-raw-phone-49123456"
    base_prepare = gateway.prepare

    def redacting(workflow_id, request):
        envelope = base_prepare(workflow_id, request)
        return replace(
            envelope,
            domain_plan={
                "schema": envelope.domain_plan_schema,
                "summary": "Redacted contact registration",
            },
        )

    gateway.prepare = redacting
    first = plan(run(gateway, raw=raw))
    assert "private-raw-phone-49123456" not in str(first.to_dict())


def test_integrity_is_rechecked_between_effects():
    gateway = Gateway()
    journey = run(gateway)
    journey.confirm(approval(plan(journey)))
    second = plan(journey)
    # Simulate an accidental in-process mutation, not mutation of a detached export.
    pending = journey._pending
    gateway.after_execute = lambda: pending.steps[1].execution_envelope.domain_plan.update(
        forged=True
    )
    result = journey.confirm(approval(second))
    assert result["run_status"] == "aborted"
    assert gateway.executed == ["contact-register", "correspondence-studio"]


def test_partial_approval_does_not_consume_valid_pending_plan():
    gateway = Gateway()
    journey = run(gateway)
    journey.confirm(approval(plan(journey)))
    second = plan(journey)
    with pytest.raises(CapabilityRecipeError):
        journey.confirm(approval(second, step_ids=(second.steps[0].step_id,)))
    assert journey.snapshot()["status"] == "awaiting_approval"
    assert gateway.executed == ["contact-register"]


@pytest.mark.parametrize("change", ["clear", "extend"])
def test_changed_step_reference_list_still_returns_partial_report_and_cleans_up(change):
    gateway = Gateway()
    journey = run(gateway)
    journey.confirm(approval(plan(journey)))
    second = plan(journey)
    refs = journey._pending.approval_context["step_refs"]
    gateway.after_execute = lambda: refs.clear() if change == "clear" else refs.extend(["forged"])
    result = journey.confirm(approval(second))
    assert result["run_status"] == "aborted"
    assert len(result["execution_reports"]) == 1
    assert journey.snapshot()["status"] == "aborted"
    assert all(s.execution_envelope.envelope_id in gateway.discarded for s in second.steps)


def test_failed_preparation_cleanup_is_neutral_and_cannot_replan():
    gateway = Gateway()
    journey = run(gateway)
    journey.confirm(approval(plan(journey)))
    gateway.fail_prepare = "mail-connector"

    def broken_cleanup(ids):
        raise OSError("C:/secret/cleanup-path")

    journey._discard = broken_cleanup
    with pytest.raises(CapabilityRecipeError) as caught:
        plan(journey)
    assert "secret" not in str(caught.value)
    assert journey.snapshot()["status"] == "aborted"
    with pytest.raises(CapabilityRecipeError):
        plan(journey)


def test_close_failure_keeps_cleanup_targets_for_safe_retry():
    gateway = Gateway()
    journey = run(gateway)
    first = plan(journey)

    def broken_cleanup(ids):
        raise OSError("C:/secret/cleanup-path")

    journey._discard = broken_cleanup
    with pytest.raises(CapabilityRecipeError):
        journey.close()
    assert journey.snapshot()["cleanup_pending_count"] == 1
    journey._discard = gateway.discard
    journey.close()
    assert journey.snapshot()["cleanup_pending_count"] == 0
    assert first.steps[0].execution_envelope.envelope_id in gateway.discarded


def test_real_note_create_then_revision_bound_edit_uses_new_approval(tmp_path):
    from test_workflow_execution import _gateway

    gateway = _gateway(tmp_path)
    raw = {
        "schema": "folderhome.capability-recipe.v2",
        "recipe_id": "note-follow-up",
        "title_en": "Record and expand a note",
        "title_de": "Notiz festhalten und ergänzen",
        "summary_en": "Two separately approved revisions",
        "summary_de": "Zwei getrennt bestätigte Revisionen",
        "lead_expert_id": "personal_notes_expert",
        "handoffs": [],
        "steps": [
            {
                "step_ref": "create",
                "workflow_id": "personal-notes",
                "expert_id": "personal_notes_expert",
                "goal_en": "Record the note",
                "goal_de": "Notiz festhalten",
                "request": {
                    "action": "create",
                    "notebook_id": "alltag",
                    "area": "alltag",
                    "title": "Plan für morgen",
                    "human_content": "Erste bestätigte Notiz.",
                },
            },
            {
                "step_ref": "edit",
                "workflow_id": "personal-notes",
                "expert_id": "personal_notes_expert",
                "goal_en": "Expand the note",
                "goal_de": "Notiz ergänzen",
                "request": {
                    "action": "edit",
                    "notebook_id": "alltag",
                    "area": "alltag",
                    "title": "Plan für morgen",
                    "human_content": "Ergänzte bestätigte Notiz.",
                },
            },
        ],
        "result_bindings": [
            {
                "from_step": "create",
                "to_step": "edit",
                "source_path": ["note_id"],
                "target_field": "note_id",
                "value_type": "string",
            },
            {
                "from_step": "create",
                "to_step": "edit",
                "source_path": ["revision"],
                "target_field": "expected_revision",
                "value_type": "integer",
            },
        ],
    }
    # Read the actual catalog owner; this test exercises adapters, not an invented role.
    from folderhome.application.master_agent import master_capability_catalog

    owner = next(
        c.expert_id for c in master_capability_catalog() if c.workflow_id == "personal-notes"
    )
    raw["lead_expert_id"] = owner
    for step in raw["steps"]:
        step["expert_id"] = owner
    journey = recipes.create_recipe_run(
        recipes.parse_recipe(raw), profile_id="lukas", language="de", gateway=gateway
    )
    database = tmp_path / "state/personal-notes/llm-note.db"
    first = plan(journey)
    assert not database.exists()
    created = journey.confirm(approval(first))
    assert created["run_status"] == "ready"
    original = created["execution_reports"][0]["domain_report"]
    assert original["revision"] == 1
    assert database.is_file()
    second = plan(journey)
    domain_plan = second.steps[0].execution_envelope.domain_plan
    assert domain_plan["note_id"] == original["note_id"]
    assert domain_plan["parent_revision"] == 1
    assert domain_plan["proposed_content"] == "Ergänzte bestätigte Notiz."
    assert journey.snapshot()["completed_step_refs"] == ["create"]
    changed = journey.confirm(approval(second))
    assert changed["run_status"] == "completed"
    report = changed["execution_reports"][0]["domain_report"]
    assert report["note_id"] == original["note_id"]
    assert report["revision"] == 2
    assert report["network_invoked"] is False
    assert report["external_sync_invoked"] is False


def test_closing_one_run_cannot_discard_another_runs_identical_envelope():
    driver = Gateway()
    gateway = core_gateway(driver)
    recipe = recipes.parse_recipe(payload())
    first = recipes.create_recipe_run(recipe, profile_id="lukas", language="de", gateway=gateway)
    second = recipes.create_recipe_run(recipe, profile_id="lukas", language="de", gateway=gateway)
    one, two = plan(first), plan(second)
    assert (
        one.steps[0].execution_envelope.envelope_id == two.steps[0].execution_envelope.envelope_id
    )
    first.close()
    assert second.confirm(approval(two))["run_status"] == "ready"
    assert driver.executed == ["contact-register"]


def test_reentrant_close_during_prepare_cannot_resurrect_a_pending_plan():
    driver = Gateway()
    journey = run(driver)
    base_prepare = driver.prepare

    def closing_prepare(workflow_id, request):
        journey.close()
        return base_prepare(workflow_id, request)

    driver.prepare = closing_prepare
    with pytest.raises(CapabilityRecipeError):
        plan(journey)
    assert journey.snapshot()["pending_plan_id"] is None


@pytest.mark.parametrize("profile", ["not a profile", "", None])
def test_invalid_profile_is_rejected_before_any_preparation(profile):
    driver = Gateway()
    with pytest.raises(CapabilityRecipeError):
        run(driver, profile=profile)
    assert driver.prepared == []


def test_invalid_language_is_rejected_before_any_preparation():
    driver = Gateway()
    with pytest.raises(CapabilityRecipeError):
        recipes.create_recipe_run(
            recipes.parse_recipe(payload()),
            profile_id="lukas",
            language="fr",
            gateway=core_gateway(driver),
        )
    assert driver.prepared == []


@pytest.mark.parametrize("phase", ["prepare", "cleanup"])
def test_public_error_traceback_does_not_include_private_adapter_exception(phase):
    driver = Gateway()
    journey = run(driver)
    if phase == "prepare":
        driver.fail_prepare = "contact-register"
        def action():
            return plan(journey)
    else:
        plan(journey)

        def failing(ids):
            raise OSError("private location C:/secret")

        journey._discard = failing
        action = journey.close
    with pytest.raises(CapabilityRecipeError) as caught:
        action()
    rendered = "".join(traceback.format_exception(caught.value))
    assert "C:/secret" not in rendered
