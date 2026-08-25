"""Verified role, persona and workflow endpoints for the FolderHome master agent.

This module deliberately does not classify natural-language prompts. Semantic
selection belongs to the model; this registry only validates and resolves the
selected expert, persona and executable workflow endpoints.
"""

from __future__ import annotations

import json
from hashlib import sha256

from folderhome.contracts.master_agent import (
    CoordinatorRole,
    ExpertRole,
    MasterAgentPlan,
    MasterCapability,
    MasterConfirmationReceipt,
    MasterPlanApproval,
    MasterPlanStep,
    RoutingPersona,
    SemanticRouteReceipt,
)
from folderhome.contracts.workflow_execution import WorkflowExecutionEnvelope


class MasterAgentError(RuntimeError):
    """Raised when semantic route resolution or approval binding fails closed."""


_EXPERT_WORKFLOWS: dict[str, tuple[str, ...]] = {
    "document_expert": (
        "directory-observation",
        "document-action-execution",
        "document-action-plan",
        "document-bundle",
        "document-library",
        "document-package",
        "fcsa-dry-run",
        "folder-cleanup",
        "folder-routine",
        "routine-queue",
    ),
    "communication_expert": (
        "calendar-connectors",
        "calendar-handoff",
        "contact-register",
        "correspondence-studio",
        "findcall",
        "mail-connector",
    ),
    "finance_contract_expert": (
        "contract-cockpit",
        "finance-import",
        "tax-workpaper",
    ),
    "health_expert": ("health-dossier", "medication-intake"),
    "household_expert": ("daily-briefing", "inventory-import"),
    "rights_benefits_expert": (
        "administrative-drafts",
        "benefit-screening",
        "legal-change-monitor",
        "official-notice-understanding",
    ),
    "creative_knowledge_expert": ("artifact-studio", "personal-notes"),
    "system_expert": ("local-app", "master-agent", "scheduler-handoff", "strands-agent"),
}

_EXPERT_COPY: dict[str, tuple[str, str, str, str]] = {
    "document_expert": (
        "Document expert",
        "Dokumentenfachrolle",
        "Handles document search, folders, file plans, bundles, packages and routines.",
        "Bearbeitet Dokumentensuche, Ordner, Dateipläne, Bündel, Pakete und Routinen.",
    ),
    "communication_expert": (
        "Communication expert",
        "Kommunikationsfachrolle",
        "Prepares contacts, correspondence, bounded inquiries, mail and calendar handoffs.",
        "Bereitet Kontakte, Schreiben, begrenzte Anfragen sowie Mail- und "
        "Kalenderübergaben vor.",
    ),
    "finance_contract_expert": (
        "Finance and contract expert",
        "Finanz- und Vertragsfachrolle",
        "Structures statements, recurring costs, contracts and tax workpapers.",
        "Strukturiert Kontoauszüge, laufende Kosten, Verträge und Steuerarbeitsmappen.",
    ),
    "health_expert": (
        "Health organization expert",
        "Fachrolle Gesundheitsorganisation",
        "Organizes provided health and medication records without medical decisions.",
        "Ordnet bereitgestellte Gesundheits- und Medikationsunterlagen ohne "
        "medizinische Entscheidungen.",
    ),
    "household_expert": (
        "Household expert",
        "Haushaltsfachrolle",
        "Coordinates household inventory and local daily briefings.",
        "Koordiniert Haushaltsbestand und lokale Tagesbriefings.",
    ),
    "rights_benefits_expert": (
        "Rights and benefits expert",
        "Fachrolle Bescheide und Leistungen",
        "Supports notice understanding, draft preparation and benefit orientation "
        "without legal decisions.",
        "Unterstützt Bescheidverständnis, Entwürfe und Leistungsorientierung ohne "
        "Rechtsentscheidung.",
    ),
    "creative_knowledge_expert": (
        "Creative and knowledge expert",
        "Kreativ- und Wissensfachrolle",
        "Plans reusable artifacts and revision-safe personal notes.",
        "Plant wiederverwendbare Artefakte und revisionssichere persönliche Notizen.",
    ),
    "system_expert": (
        "Local system expert",
        "Lokale Systemfachrolle",
        "Explains and plans FolderHome app, agent and scheduler surfaces.",
        "Erklärt und plant FolderHome-App, Agenten- und Scheduler-Oberflächen.",
    ),
}

_EXPERT_SKILLS: dict[str, tuple[str, ...]] = {
    "document_expert": ("file-collect-sort-action", "docs-analysis"),
    "communication_expert": ("privat-mail-writer",),
    "finance_contract_expert": ("steuer-assistent",),
    "health_expert": ("arzt-dr-moritz-medizin",),
    "household_expert": ("haushalt-manager",),
    "rights_benefits_expert": ("law-checker",),
    "creative_knowledge_expert": ("doc",),
    "system_expert": ("semantic-persona-routing",),
}

_PERSONAS = (
    RoutingPersona(
        persona_id="clear_companion",
        title_en="Clear companion",
        title_de="Klarer Begleiter",
        style_en="Warm, concise and explicit about the next decision.",
        style_de="Zugewandt, knapp und klar über die nächste Entscheidung.",
        expert_ids=tuple(_EXPERT_WORKFLOWS),
    ),
    RoutingPersona(
        persona_id="careful_reviewer",
        title_en="Careful reviewer",
        title_de="Sorgfältiger Prüfer",
        style_en="Evidence-led, precise and explicit about uncertainty and professional limits.",
        style_de="Evidenzorientiert, präzise und klar über Unsicherheit und fachliche Grenzen.",
        expert_ids=("finance_contract_expert", "health_expert", "rights_benefits_expert"),
    ),
    RoutingPersona(
        persona_id="methodical_operator",
        title_en="Methodical operator",
        title_de="Methodischer Operator",
        style_en="Stepwise, operational and explicit about approvals and side effects.",
        style_de="Schrittweise, handlungsnah und klar über Freigaben und Nebenwirkungen.",
        expert_ids=(
            "document_expert",
            "communication_expert",
            "household_expert",
            "system_expert",
        ),
    ),
    RoutingPersona(
        persona_id="creative_guide",
        title_en="Creative guide",
        title_de="Kreativer Gestalter",
        style_en="Exploratory and visual while preserving the requested format and constraints.",
        style_de="Erkundend und visuell, bei Wahrung des gewünschten Formats und der Grenzen.",
        expert_ids=("creative_knowledge_expert",),
    ),
)

_PERSONA_IDS_BY_EXPERT = {
    expert_id: tuple(
        persona.persona_id for persona in _PERSONAS if expert_id in persona.expert_ids
    )
    for expert_id in _EXPERT_WORKFLOWS
}

_PLANNING_ONLY = {"local-app", "master-agent", "strands-agent"}
_DIRECT_READ_ONLY = {"document-library"}
_EXTERNAL_EFFECTS = {
    "calendar-connectors": ("external.calendar.write",),
    "calendar-handoff": ("external.calendar.write",),
    "findcall": ("simulation.findcall.fixture",),
    "mail-connector": ("external.mailbox.draft_write",),
    "scheduler-handoff": ("external.scheduler.write",),
}


def master_coordinator() -> CoordinatorRole:
    """Return the one user-facing coordination role."""

    return CoordinatorRole(
        role_id="folderhome_master",
        title_en="FolderHome master agent",
        title_de="FolderHome-Master-Agent",
        description_en="One conversational entry point for local document and home assistance.",
        description_de="Ein Gesprächseinstieg für lokale Dokument- und Alltagsassistenz.",
        expert_ids=tuple(_EXPERT_WORKFLOWS),
    )


def master_persona_catalog() -> tuple[RoutingPersona, ...]:
    return _PERSONAS


def master_expert_catalog() -> tuple[ExpertRole, ...]:
    return tuple(
        ExpertRole(
            expert_id=expert_id,
            parent_role_id="folderhome_master",
            title_en=_EXPERT_COPY[expert_id][0],
            title_de=_EXPERT_COPY[expert_id][1],
            description_en=_EXPERT_COPY[expert_id][2],
            description_de=_EXPERT_COPY[expert_id][3],
            workflow_ids=workflow_ids,
            persona_ids=_PERSONA_IDS_BY_EXPERT[expert_id],
        )
        for expert_id, workflow_ids in _EXPERT_WORKFLOWS.items()
    )


def master_capability_catalog() -> tuple[MasterCapability, ...]:
    """Return verified endpoints without lexical intent or prompt terms."""

    items: list[MasterCapability] = []
    for expert_id, workflow_ids in _EXPERT_WORKFLOWS.items():
        for workflow_id in workflow_ids:
            if workflow_id in _DIRECT_READ_ONLY:
                execution_mode = "direct_read_only"
                approval_gates: tuple[str, ...] = ()
                side_effects: tuple[str, ...] = ()
            elif workflow_id in _PLANNING_ONLY:
                execution_mode = "planning_only"
                approval_gates = ()
                side_effects = ()
            else:
                execution_mode = "approval_bound_workflow"
                approval_gates = ("workflow_specific_explicit_approval",)
                side_effects = _EXTERNAL_EFFECTS.get(workflow_id, ("filesystem.write",))
            items.append(
                MasterCapability(
                    capability_id=workflow_id,
                    workflow_id=workflow_id,
                    expert_id=expert_id,
                    endpoint_skill_ids=_EXPERT_SKILLS[expert_id],
                    execution_mode=execution_mode,
                    cli_commands=(
                        "folderhome agent session",
                        "folderhome agent chat",
                    ),
                    boundaries=(
                        "operating_system_account",
                        "typed_workflow_endpoint_only",
                        "no_arbitrary_shell_or_path_tool",
                    ),
                    approval_gates=approval_gates,
                    side_effects=side_effects,
                )
            )
    return tuple(items)


def master_agent_catalog(*, language: str = "en") -> dict[str, object]:
    """Return the compact map given to the model and shown in the GUI."""

    return {
        "schema": "folderhome.semantic-agent-catalog.v1",
        "language": language,
        "routing_policy": "semantic_model_selection",
        "endpoint_resolution": "explicit_fail_closed",
        "coordinator": master_coordinator().to_dict(language=language),
        "experts": [item.to_dict(language=language) for item in master_expert_catalog()],
        "personas": [item.to_dict(language=language) for item in _PERSONAS],
        "capabilities": [item.to_dict() for item in master_capability_catalog()],
        "gaps": [],
        "keyword_router_present": False,
    }


def resolve_master_route(
    *,
    expert_id: str,
    workflow_ids: tuple[str, ...],
    persona_id: str | None,
    confidence: str,
    why: str,
) -> SemanticRouteReceipt:
    """Validate a route selected semantically by a model or explicitly by a user."""

    experts = {item.expert_id: item for item in master_expert_catalog()}
    expert = experts.get(expert_id)
    if expert is None:
        raise MasterAgentError(f"Unbekannte Fachrolle: {expert_id}")
    if not workflow_ids:
        raise MasterAgentError("Route benötigt mindestens einen Workflow-Endpunkt.")
    unknown = tuple(item for item in workflow_ids if item not in expert.workflow_ids)
    if unknown:
        raise MasterAgentError(
            "Workflow-Endpunkt gehört nicht zur gewählten Fachrolle: " + ", ".join(unknown)
        )
    if persona_id is not None and persona_id not in expert.persona_ids:
        raise MasterAgentError("Persona ist mit der gewählten Fachrolle nicht verbunden.")
    return SemanticRouteReceipt(
        role_id="folderhome_master",
        expert_id=expert_id,
        workflow_ids=workflow_ids,
        persona_id=persona_id,
        resolution="explicit",
        confidence=confidence,
        why=why,
    )


def build_master_agent_plan(
    request: str,
    *,
    profile_id: str,
    language: str,
    expert_id: str,
    workflow_ids: tuple[str, ...],
    persona_id: str | None = None,
    confidence: str = "medium",
    why: str = "The selected endpoints were explicitly resolved against the live catalog.",
    execution_envelopes: dict[str, WorkflowExecutionEnvelope] | None = None,
) -> MasterAgentPlan:
    """Build a plan from an already selected route; never infer intent here."""

    normalized = " ".join(request.split())
    if not normalized or len(normalized) > 2_000:
        raise MasterAgentError("Anfrage benötigt 1 bis 2000 Zeichen.")
    route = resolve_master_route(
        expert_id=expert_id,
        workflow_ids=workflow_ids,
        persona_id=persona_id,
        confidence=confidence,
        why=why,
    )
    capabilities = {item.workflow_id: item for item in master_capability_catalog()}
    envelopes = dict(execution_envelopes or {})
    unknown_envelopes = sorted(set(envelopes).difference(workflow_ids))
    if unknown_envelopes:
        raise MasterAgentError(
            "Ausführungshülle gehört nicht zu einem ausgewählten Workflow: "
            + ", ".join(unknown_envelopes)
        )
    steps = tuple(
        MasterPlanStep(
            step_id=(
                f"step_{sequence}_"
                f"{sha256((workflow_id + normalized).encode('utf-8')).hexdigest()[:12]}"
            ),
            sequence=sequence,
            workflow_id=workflow_id,
            expert_id=expert_id,
            goal=normalized,
            execution_mode=capabilities[workflow_id].execution_mode,
            confirmation_required=bool(
                capabilities[workflow_id].approval_gates
                or capabilities[workflow_id].side_effects
            ),
            approval_gates=capabilities[workflow_id].approval_gates,
            side_effects=capabilities[workflow_id].side_effects,
            boundaries=capabilities[workflow_id].boundaries,
            cli_commands=capabilities[workflow_id].cli_commands,
            execution_envelope=envelopes.get(workflow_id),
        )
        for sequence, workflow_id in enumerate(workflow_ids, start=1)
    )
    request_sha256 = sha256(normalized.encode("utf-8")).hexdigest()
    hash_material = {
        "request_sha256": request_sha256,
        "profile_id": profile_id,
        "language": language,
        "route": route.to_dict(),
        "steps": [item.to_dict() for item in steps],
    }
    plan_sha256 = sha256(_json_bytes(hash_material)).hexdigest()
    summary = (
        f"{len(steps)} geprüfte Workflow-Schritte wurden vorgeschlagen."
        if language == "de"
        else f"{len(steps)} verified workflow steps were proposed."
    )
    return MasterAgentPlan(
        plan_id=f"plan_{plan_sha256[:20]}",
        plan_sha256=plan_sha256,
        request_sha256=request_sha256,
        profile_id=profile_id,
        language=language,
        summary=summary,
        steps=steps,
        route=route,
    )


def confirm_master_agent_plan(
    plan: MasterAgentPlan,
    approval: MasterPlanApproval,
) -> MasterConfirmationReceipt:
    """Bind exact human approval to a plan without executing any workflow."""

    if approval.plan_id != plan.plan_id:
        raise MasterAgentError("Freigabe gehört nicht zu diesem Plan.")
    if approval.plan_sha256 != plan.plan_sha256:
        raise MasterAgentError("Freigabe enthält nicht den aktuellen Plan-Hash.")
    known = {item.step_id for item in plan.steps}
    if any(step_id not in known for step_id in approval.step_ids):
        raise MasterAgentError("Freigabe enthält einen unbekannten Planschritt.")
    required = {item.step_id for item in plan.steps if item.confirmation_required}
    if not required.issubset(approval.step_ids):
        raise MasterAgentError("Nicht alle freigabepflichtigen Schritte wurden bestätigt.")
    material = _json_bytes(approval.to_dict())
    return MasterConfirmationReceipt(
        receipt_id=f"receipt_{sha256(material).hexdigest()[:20]}",
        approval_id=approval.approval_id,
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        approved_step_ids=approval.step_ids,
    )


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


__all__ = [
    "MasterAgentError",
    "build_master_agent_plan",
    "confirm_master_agent_plan",
    "master_agent_catalog",
    "master_capability_catalog",
    "master_coordinator",
    "master_expert_catalog",
    "master_persona_catalog",
    "resolve_master_route",
]
