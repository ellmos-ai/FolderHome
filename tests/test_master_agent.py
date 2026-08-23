from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.application.master_agent import (
    MasterAgentError,
    build_master_agent_plan,
    confirm_master_agent_plan,
    master_agent_catalog,
    master_capability_catalog,
    master_coordinator,
    master_expert_catalog,
    master_persona_catalog,
    resolve_master_route,
)
from folderhome.contracts.master_agent import MasterPlanApproval

REPOSITORY_ROOT = Path(__file__).parents[1]


def _workflow_ids() -> set[str]:
    return {
        path.stem
        for path in (REPOSITORY_ROOT / "workflows").glob("*.md")
        if not path.name.endswith(".de.md")
        and path.name not in {"README.md", "_example-workflow.md"}
    }


def test_semantic_catalog_covers_every_workflow_without_keyword_router() -> None:
    capabilities = master_capability_catalog()
    experts = {item.expert_id: item for item in master_expert_catalog()}
    coordinator = master_coordinator()
    payload = master_agent_catalog(language="de")

    assert len(capabilities) == 33
    assert {item.workflow_id for item in capabilities} == _workflow_ids()
    assert set(coordinator.expert_ids) == set(experts)
    assert all(item.workflow_id in experts[item.expert_id].workflow_ids for item in capabilities)
    assert all(not hasattr(item, "routing_terms") for item in capabilities)
    assert payload["routing_policy"] == "semantic_model_selection"
    assert payload["endpoint_resolution"] == "explicit_fail_closed"
    assert payload["keyword_router_present"] is False


def test_findcall_is_a_bounded_communication_endpoint() -> None:
    capabilities = {
        item.workflow_id: item for item in master_capability_catalog()
    }

    findcall = capabilities["findcall"]
    assert findcall.expert_id == "communication_expert"
    assert findcall.execution_mode == "approval_bound_workflow"
    assert findcall.approval_gates == ("workflow_specific_explicit_approval",)
    assert findcall.side_effects == ("simulation.findcall.fixture",)

    receipt = resolve_master_route(
        expert_id="communication_expert",
        workflow_ids=("findcall",),
        persona_id="methodical_operator",
        confidence="high",
        why="The request asks for a bounded provider inquiry.",
    )
    assert receipt.workflow_ids == ("findcall",)


def test_personas_are_style_only_and_never_grant_capabilities() -> None:
    experts = {item.expert_id: item for item in master_expert_catalog()}

    for persona in master_persona_catalog():
        assert persona.authority == "style_only"
        assert set(persona.expert_ids).issubset(experts)
        assert not hasattr(persona, "workflow_ids")


def test_model_selected_route_is_resolved_only_against_explicit_endpoints() -> None:
    receipt = resolve_master_route(
        expert_id="rights_benefits_expert",
        workflow_ids=("official-notice-understanding", "administrative-drafts"),
        persona_id="careful_reviewer",
        confidence="high",
        why="The request concerns understanding a notice and preparing a response.",
    )

    assert receipt.role_id == "folderhome_master"
    assert receipt.resolution == "explicit"
    assert receipt.workflow_ids == (
        "official-notice-understanding",
        "administrative-drafts",
    )

    with pytest.raises(MasterAgentError, match="gehört nicht"):
        resolve_master_route(
            expert_id="health_expert",
            workflow_ids=("folder-cleanup",),
            persona_id="careful_reviewer",
            confidence="low",
            why="Uncertain route.",
        )


def test_plan_builder_never_infers_intent_and_binds_selected_endpoints() -> None:
    plan = build_master_agent_plan(
        "Verstehe diesen Bescheid und entwirf danach einen Widerspruch.",
        profile_id="lukas",
        language="de",
        expert_id="rights_benefits_expert",
        workflow_ids=("official-notice-understanding", "administrative-drafts"),
        persona_id="careful_reviewer",
        confidence="high",
        why="The model selected the connected notice and drafting endpoints.",
    )

    assert [item.workflow_id for item in plan.steps] == [
        "official-notice-understanding",
        "administrative-drafts",
    ]
    assert plan.model_call_performed is False
    assert plan.execution_performed is False
    assert plan.confirmation_required is True
    assert all(item.expert_id == "rights_benefits_expert" for item in plan.steps)


def test_direct_read_only_route_stays_unapproved_but_writes_are_hash_bound() -> None:
    search = build_master_agent_plan(
        "Find my Hyundai i10 insurance document.",
        profile_id="hanna",
        language="en",
        expert_id="document_expert",
        workflow_ids=("document-library",),
        confidence="high",
        why="The model selected the verified local document search endpoint.",
    )
    cleanup = build_master_agent_plan(
        "Clean up the inbox.",
        profile_id="hanna",
        language="en",
        expert_id="document_expert",
        workflow_ids=("folder-cleanup",),
        persona_id="methodical_operator",
        confidence="high",
        why="The model selected the folder cleanup endpoint.",
    )

    assert search.steps[0].execution_mode == "direct_read_only"
    assert search.confirmation_required is False
    assert cleanup.steps[0].execution_mode == "approval_bound_workflow"
    assert cleanup.steps[0].side_effects == ("filesystem.write",)

    selected = tuple(item.step_id for item in cleanup.steps)
    approval = MasterPlanApproval(
        approval_id="approval_demo_001",
        plan_id=cleanup.plan_id,
        plan_sha256=cleanup.plan_sha256,
        step_ids=selected,
        approved_at="2026-08-22T16:30:00+02:00",
    )
    receipt = confirm_master_agent_plan(cleanup, approval)
    assert receipt.approved_step_ids == selected
    assert receipt.execution_performed is False

    with pytest.raises(MasterAgentError, match="Plan-Hash"):
        confirm_master_agent_plan(
            cleanup,
            MasterPlanApproval(
                approval_id="approval_demo_002",
                plan_id=cleanup.plan_id,
                plan_sha256="0" * 64,
                step_ids=selected,
                approved_at="2026-08-22T16:31:00+02:00",
            ),
        )
