from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.master_agent import (
    MasterAgentError,
    confirm_master_agent_plan,
    master_capability_catalog,
)
from folderhome.application.recipes import (
    build_recipe_plan,
    bundled_recipe_ids,
    execute_recipe_plan,
    load_bundled_recipe,
    parse_recipe,
    recipe_sha256,
    review_recipe,
)
from folderhome.contracts.master_agent import MasterPlanApproval
from folderhome.contracts.recipes import CapabilityRecipeError
from folderhome.contracts.workflow_execution import (
    WorkflowExecutionEnvelope,
    WorkflowExecutionReport,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APPROVED_AT = "2026-08-25T09:05:00+02:00"
RESOURCE_IDS = frozenset(
    {
        "insurance_documents",
        "contact_state",
        "letter_request",
        "letter_designs",
        "letter_templates",
        "claim_output",
        "mail_draft_account",
        "follow_up_documents",
        "calendar_configuration",
        "local_calendar",
        "calendar_export",
    }
)


def _statuses(**overrides: str) -> dict[str, str]:
    statuses = {item.workflow_id: "connected" for item in master_capability_catalog()}
    statuses.update(overrides)
    return statuses


class _Gateway:
    """Minimal stand-in for the executor gateway; records what it was asked."""

    def __init__(self, *, failing_workflow: str | None = None) -> None:
        self.prepared: list[tuple[str, dict[str, object]]] = []
        self.executed: list[str] = []
        self._failing_workflow = failing_workflow
        self._by_envelope: dict[str, str] = {}

    def prepare(self, workflow_id: str, request: dict[str, object]):
        self.prepared.append((workflow_id, dict(request)))
        digest = sha256(
            json.dumps(
                {"workflow_id": workflow_id, "request": request},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{digest}",
            workflow_id=workflow_id,
            adapter_id=f"{workflow_id.replace('-', '_')}.v1",
            domain_plan_id=f"{workflow_id}_plan",
            domain_plan_schema="folderhome.stub-plan.v1",
            domain_plan_sha256=digest,
            domain_plan={"schema": "folderhome.stub-plan.v1"},
            approval_kind="explicit_stub",
            side_effects=("file.create",),
        )
        self._by_envelope[envelope.envelope_id] = workflow_id
        return envelope

    def execute(self, envelope_id: str, approved_at: str) -> WorkflowExecutionReport:
        workflow_id = self._by_envelope[envelope_id]
        if workflow_id == self._failing_workflow:
            raise RuntimeError(f"Adapter hat {workflow_id} abgelehnt.")
        self.executed.append(workflow_id)
        digest = sha256(f"{envelope_id}{approved_at}".encode()).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope_id,
            workflow_id=workflow_id,
            adapter_id=f"{workflow_id.replace('-', '_')}.v1",
            domain_report_schema="folderhome.stub-report.v1",
            domain_report={"schema": "folderhome.stub-report.v1"},
            side_effects=("file.create",),
        )


def _plan(gateway: _Gateway, **kwargs: object):
    recipe = kwargs.pop("recipe", None) or load_bundled_recipe("accident-aftercare")
    return build_recipe_plan(
        recipe,
        profile_id="lukas",
        language="en",
        prepare=gateway.prepare,
        endpoint_statuses=kwargs.pop("endpoint_statuses", None) or _statuses(),
        known_resource_ids=kwargs.pop("known_resource_ids", None) or RESOURCE_IDS,
    )


@pytest.mark.parametrize("changed_field", ["handoffs", "step_refs", "endorsement", "content"])
def test_recipe_refuses_changed_approval_material_before_any_effect(changed_field):
    gateway = _Gateway()
    prepared = _plan(gateway)
    if changed_field == "handoffs":
        prepared = replace(prepared, handoffs=())
    elif changed_field == "step_refs":
        prepared = replace(prepared, step_refs=tuple(reversed(prepared.step_refs)))
    elif changed_field == "endorsement":
        prepared = replace(prepared, endorsement=replace(
            prepared.endorsement, checks=("unreviewed_replacement",),
        ))
    else:
        prepared.plan.steps[0].execution_envelope.domain_plan["unapproved"] = True

    with pytest.raises(CapabilityRecipeError):
        execute_recipe_plan(prepared, execute=gateway.execute, approved_at=APPROVED_AT)
    assert gateway.executed == []


def test_confirmation_refuses_changed_nested_domain_plan():
    prepared = _plan(_Gateway())
    approval = MasterPlanApproval(
        approval_id="approval_nested_integrity", plan_id=prepared.plan_id,
        plan_sha256=prepared.plan.plan_sha256,
        step_ids=tuple(step.step_id for step in prepared.plan.steps), approved_at=APPROVED_AT,
    )
    prepared.plan.steps[0].execution_envelope.domain_plan["unapproved"] = {"value": 1}
    with pytest.raises(MasterAgentError):
        confirm_master_agent_plan(prepared.plan, approval)


def test_public_plan_export_does_not_allow_nested_mutation_of_approved_plan():
    gateway = _Gateway()

    def prepare(workflow_id, request):
        envelope = gateway.prepare(workflow_id, request)
        return replace(envelope, domain_plan={
            "schema": envelope.domain_plan_schema, "actions": [{"target": "original"}],
        })

    prepared = build_recipe_plan(
        load_bundled_recipe("accident-aftercare"), profile_id="lukas", language="en",
        prepare=prepare, endpoint_statuses=_statuses(), known_resource_ids=RESOURCE_IDS,
    )
    payload = prepared.to_dict()
    payload["plan"]["steps"][0]["execution_envelope"]["domain_plan"]["actions"][0][
        "target"
    ] = "unapproved"
    assert prepared.plan.steps[0].execution_envelope.domain_plan["actions"] == [
        {"target": "original"},
    ]


def test_recipe_stops_if_later_plan_content_changes_during_execution():
    gateway = _Gateway()
    prepared = _plan(gateway)

    def execute(envelope_id, approved_at):
        report = gateway.execute(envelope_id, approved_at)
        prepared.plan.steps[1].execution_envelope.domain_plan["unapproved"] = True
        return report

    report = execute_recipe_plan(prepared, execute=execute, approved_at=APPROVED_AT)
    assert [outcome.status for outcome in report.outcomes] == [
        "executed", "failed", "not_attempted", "not_attempted",
    ]
    assert gateway.executed == ["contact-register"]


def test_recipe_parser_owns_nested_requests_independently_of_input():
    raw = _raw_recipe()
    raw["steps"][0]["request"]["options"] = {"labels": ["original"]}
    recipe = parse_recipe(raw)
    raw["steps"][0]["request"]["options"]["labels"].append("unapproved")
    assert recipe.steps[0].request["options"] == {"labels": ["original"]}


def test_preparing_a_recipe_cannot_mutate_its_reviewed_request():
    raw = _raw_recipe()
    raw["steps"][0]["request"]["options"] = {"labels": ["original"]}
    recipe = parse_recipe(raw)
    gateway = _Gateway()

    def prepare(workflow_id, request):
        if "options" in request:
            request["options"]["labels"].append("adapter_normalization")
        return gateway.prepare(workflow_id, request)

    build_recipe_plan(
        recipe, profile_id="lukas", language="en", prepare=prepare,
        endpoint_statuses=_statuses(), known_resource_ids=RESOURCE_IDS,
    )
    assert recipe.steps[0].request["options"] == {"labels": ["original"]}


@pytest.mark.parametrize("direction", ["input", "export"])
def test_domain_report_keeps_its_nested_evidence_independent(direction):
    gateway = _Gateway()
    prepared = _plan(gateway)
    envelope_id = prepared.plan.steps[0].execution_envelope.envelope_id
    original = gateway.execute(envelope_id, APPROVED_AT)
    evidence = {"schema": original.domain_report_schema, "events": [{"note_id": "original"}]}
    report = replace(original, domain_report=evidence)
    if direction == "input":
        evidence["events"][0]["note_id"] = "unrelated"
    else:
        report.to_dict()["domain_report"]["events"][0]["note_id"] = "unrelated"
    assert report.to_dict()["domain_report"]["events"] == [{"note_id": "original"}]


def test_domain_envelope_owns_its_nested_public_plan():
    envelope = _plan(_Gateway()).plan.steps[0].execution_envelope
    source = {"schema": envelope.domain_plan_schema, "actions": [{"target": "original"}]}
    copied = replace(envelope, domain_plan=source)
    source["actions"][0]["target"] = "unapproved"
    assert copied.to_dict()["domain_plan"]["actions"] == [{"target": "original"}]


@pytest.mark.parametrize("field", ["envelope_id", "workflow_id", "adapter_id"])
def test_recipe_cannot_credit_a_report_from_another_execution(field):
    gateway = _Gateway()
    prepared = _plan(gateway)
    other = prepared.plan.steps[-1].execution_envelope

    def execute(envelope_id, approved_at):
        report = gateway.execute(envelope_id, approved_at)
        return replace(report, **{field: getattr(other, field)})

    report = execute_recipe_plan(prepared, execute=execute, approved_at=APPROVED_AT)
    assert report.status == "aborted"
    assert report.to_dict()["executed_step_refs"] == []
    assert report.to_dict()["failed_step_refs"] == ["contacts"]
    assert report.to_dict()["not_attempted_step_refs"] == ["letter", "draft", "appointment"]
    assert gateway.executed == ["contact-register"]


def test_the_accident_recipe_ships_inside_the_package() -> None:
    assert "accident-aftercare" in bundled_recipe_ids()

    recipe = load_bundled_recipe("accident-aftercare")

    assert [item.step_ref for item in recipe.steps] == [
        "contacts",
        "letter",
        "draft",
        "appointment",
    ]
    assert recipe.workflow_ids == (
        "contact-register",
        "correspondence-studio",
        "mail-connector",
        "calendar-handoff",
    )
    assert recipe.to_dict()["grants_new_capability"] is False


def test_recipe_parsing_fails_closed_on_unknown_fields() -> None:
    payload = json.loads(
        json.dumps(load_bundled_recipe("accident-aftercare").to_dict())
    )
    payload["title_en"] = "x"
    payload["title_de"] = "x"
    payload["summary_en"] = "x"
    payload["summary_de"] = "x"
    payload["steps"] = [
        {
            "step_ref": "only",
            "workflow_id": "contact-register",
            "expert_id": "communication_expert",
            "goal_en": "x",
            "goal_de": "x",
            "request": {},
            "escalate": True,
        }
    ]
    payload["handoffs"] = []

    with pytest.raises(CapabilityRecipeError, match="unbekannte Felder"):
        parse_recipe(payload)


def test_one_plan_carries_every_step_with_its_true_owning_expert() -> None:
    gateway = _Gateway()

    recipe_plan = _plan(gateway)

    assert len(recipe_plan.plan.steps) == 4
    assert [item.sequence for item in recipe_plan.plan.steps] == [1, 2, 3, 4]
    catalog = {item.workflow_id: item for item in master_capability_catalog()}
    for step in recipe_plan.plan.steps:
        assert step.expert_id == catalog[step.workflow_id].expert_id
        assert step.execution_envelope is not None
        assert step.confirmation_required is True
    assert recipe_plan.to_dict()["single_confirmation_command"] == (
        f"/confirm {recipe_plan.plan.plan_id}"
    )
    assert [item[0] for item in gateway.prepared] == list(recipe_plan.plan.route.workflow_ids)
    assert gateway.executed == []


def test_one_confirmation_covers_the_whole_chain_and_its_review() -> None:
    recipe_plan = _plan(_Gateway())

    approval = MasterPlanApproval(
        approval_id="approval_recipe_chain",
        plan_id=recipe_plan.plan.plan_id,
        plan_sha256=recipe_plan.plan.plan_sha256,
        step_ids=tuple(item.step_id for item in recipe_plan.plan.steps),
        approved_at=APPROVED_AT,
    )
    receipt = confirm_master_agent_plan(recipe_plan.plan, approval)

    assert receipt.execution_performed is False
    assert len(receipt.approved_step_ids) == 4


def test_the_plan_hash_covers_recipe_handoffs_and_endorsement() -> None:
    recipe = load_bundled_recipe("accident-aftercare")
    baseline = _plan(_Gateway(), recipe=recipe)

    tampered = parse_recipe(
        {
            **json.loads(json.dumps(_raw_recipe())),
            "handoffs": [],
        }
    )
    without_handoffs = _plan(_Gateway(), recipe=tampered)

    assert baseline.recipe_sha256 != without_handoffs.recipe_sha256
    assert baseline.plan.plan_sha256 != without_handoffs.plan.plan_sha256


def test_review_demands_the_endpoint_owner_declared_in_the_recipe() -> None:
    raw = _raw_recipe()
    raw["steps"][0]["expert_id"] = "finance_contract_expert"
    recipe = parse_recipe(raw)

    with pytest.raises(CapabilityRecipeError, match="gehört zu communication_expert"):
        review_recipe(
            recipe,
            endpoint_statuses=_statuses(),
            known_resource_ids=RESOURCE_IDS,
        )


def test_review_refuses_a_recipe_whose_endpoint_is_not_connected() -> None:
    recipe = load_bundled_recipe("accident-aftercare")

    with pytest.raises(CapabilityRecipeError, match="mail-connector ist nicht verbunden"):
        review_recipe(
            recipe,
            endpoint_statuses=_statuses(**{"mail-connector": "not_connected"}),
            known_resource_ids=RESOURCE_IDS,
        )


def test_review_refuses_a_resource_that_is_not_configured() -> None:
    recipe = load_bundled_recipe("accident-aftercare")

    with pytest.raises(CapabilityRecipeError, match="nicht konfiguriert: calendar_export"):
        review_recipe(
            recipe,
            endpoint_statuses=_statuses(),
            known_resource_ids=frozenset(RESOURCE_IDS - {"calendar_export"}),
        )


def test_review_refuses_a_handoff_that_binds_two_different_resources() -> None:
    raw = _raw_recipe()
    raw["steps"][2]["request"]["request_resource_id"] = "letter_designs"
    recipe = parse_recipe(raw)

    with pytest.raises(CapabilityRecipeError, match="dieselbe Ressource nennen"):
        review_recipe(
            recipe,
            endpoint_statuses=_statuses(),
            known_resource_ids=RESOURCE_IDS,
        )


def test_a_single_domain_recipe_is_signed_by_one_expert() -> None:
    raw = _raw_recipe()
    raw["steps"] = raw["steps"][:2]
    raw["handoffs"] = []
    recipe = parse_recipe(raw)

    endorsement = review_recipe(
        recipe,
        endpoint_statuses=_statuses(),
        known_resource_ids=RESOURCE_IDS,
    )

    assert endorsement.reviewer_expert_ids == ("communication_expert",)
    assert endorsement.status == "endorsed"
    assert endorsement.findings == ()


def test_a_cross_domain_recipe_is_signed_by_every_involved_expert() -> None:
    raw = _raw_recipe()
    raw["steps"].append(
        {
            "step_ref": "cockpit",
            "workflow_id": "contract-cockpit",
            "expert_id": "finance_contract_expert",
            "goal_en": "Show the matching insurance contract.",
            "goal_de": "Den passenden Versicherungsvertrag zeigen.",
            "request": {
                "state_resource_id": "contact_state",
                "output_resource_id": "claim_output",
            },
        }
    )
    recipe = parse_recipe(raw)

    endorsement = review_recipe(
        recipe,
        endpoint_statuses=_statuses(),
        known_resource_ids=RESOURCE_IDS,
    )

    assert endorsement.reviewer_expert_ids == (
        "communication_expert",
        "finance_contract_expert",
    )
    assert endorsement.to_dict()["reviewer_count"] == 2


def test_the_chain_runs_in_order_and_reports_every_step() -> None:
    gateway = _Gateway()
    recipe_plan = _plan(gateway)

    report = execute_recipe_plan(
        recipe_plan,
        execute=gateway.execute,
        approved_at=APPROVED_AT,
    )

    assert report.status == "executed"
    assert gateway.executed == [
        "contact-register",
        "correspondence-studio",
        "mail-connector",
        "calendar-handoff",
    ]
    payload = report.to_dict()
    assert payload["executed_step_refs"] == ["contacts", "letter", "draft", "appointment"]
    assert payload["failed_step_refs"] == []
    assert payload["not_attempted_step_refs"] == []


def test_the_chain_stops_at_the_first_failure_and_says_what_already_ran() -> None:
    gateway = _Gateway(failing_workflow="mail-connector")
    recipe_plan = _plan(gateway)

    report = execute_recipe_plan(
        recipe_plan,
        execute=gateway.execute,
        approved_at=APPROVED_AT,
    )

    assert report.status == "aborted"
    payload = report.to_dict()
    assert payload["executed_step_refs"] == ["contacts", "letter"]
    assert payload["failed_step_refs"] == ["draft"]
    assert payload["not_attempted_step_refs"] == ["appointment"]
    assert gateway.executed == ["contact-register", "correspondence-studio"]
    failure = next(
        item for item in report.outcomes if item.status == "failed"
    )
    assert "mail-connector" in str(failure.detail)


def _raw_recipe() -> dict[str, object]:
    recipe = load_bundled_recipe("accident-aftercare")
    return {
        "schema": "folderhome.capability-recipe.v1",
        "recipe_id": recipe.recipe_id,
        "title_en": recipe.title_en,
        "title_de": recipe.title_de,
        "summary_en": recipe.summary_en,
        "summary_de": recipe.summary_de,
        "lead_expert_id": recipe.lead_expert_id,
        "steps": [
            {
                "step_ref": item.step_ref,
                "workflow_id": item.workflow_id,
                "expert_id": item.expert_id,
                "goal_en": item.goal_en,
                "goal_de": item.goal_de,
                "request": dict(item.request),
            }
            for item in recipe.steps
        ],
        "handoffs": [
            {
                "from_step": item.from_step,
                "to_step": item.to_step,
                "from_field": item.from_field,
                "to_field": item.to_field,
            }
            for item in recipe.handoffs
        ],
    }


def test_recipe_digest_is_stable_and_language_independent() -> None:
    first = recipe_sha256(load_bundled_recipe("accident-aftercare"))
    second = recipe_sha256(parse_recipe(_raw_recipe()))

    assert first == second


def test_recipe_cli_lists_the_packaged_journey_without_touching_anything() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "folderhome", "recipes", "list", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        cwd=REPOSITORY_ROOT,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["schema"] == "folderhome.capability-recipe-catalog.v1"
    entry = next(
        item for item in payload["recipes"] if item["recipe_id"] == "accident-aftercare"
    )
    assert entry["step_count"] == 4
    assert entry["grants_new_capability"] is False
    assert entry["workflow_ids"][2] == "mail-connector"
