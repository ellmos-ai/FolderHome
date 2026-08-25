"""Resolve a declarative capability recipe into one hash-bound multi-step plan.

This is the agentic chaining layer. It does not add powers: every step is an
existing typed endpoint with its own adapter, its own gates and its own request
schema. What changes is the unit of consent — the user confirms one plan for the
whole journey instead of confirming four unrelated plans in a row.

Three rules keep that safe:

* Every step is validated against the capability catalog, so an endpoint can
  only appear under the expert that actually owns it.
* Data moves only through logical resource IDs. A handoff declares that two
  steps must name the same logical resource — a store one writes and a later
  one reads, or a source both must agree on. No value from a step report is
  ever substituted into a later request, so every request is complete and
  hashable before anything runs.
* A deterministic review runs before the plan is shown, and its verdict is part
  of the plan hash, so the confirmation covers the review as well.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from importlib import resources

from folderhome.application.master_agent import (
    master_capability_catalog,
    master_expert_catalog,
)
from folderhome.contracts.master_agent import (
    MasterAgentPlan,
    MasterPlanStep,
    SemanticRouteReceipt,
)
from folderhome.contracts.recipes import (
    RECIPE_SCHEMA,
    CapabilityHandoff,
    CapabilityRecipe,
    CapabilityRecipeError,
    CapabilityRecipePlan,
    CapabilityRecipeStep,
    RecipeEndorsement,
    RecipeExecutionReport,
    RecipeStepOutcome,
)
from folderhome.contracts.workflow_execution import (
    WorkflowExecutionEnvelope,
    WorkflowExecutionReport,
)

_RECIPE_PACKAGE = "folderhome.recipes"
_RESOURCE_FIELD_SUFFIX = "_resource_id"

_RECIPE_FIELDS = {
    "schema",
    "recipe_id",
    "title_en",
    "title_de",
    "summary_en",
    "summary_de",
    "lead_expert_id",
    "steps",
    "handoffs",
}
_STEP_FIELDS = {"step_ref", "workflow_id", "expert_id", "goal_en", "goal_de", "request"}
_HANDOFF_FIELDS = {"from_step", "to_step", "from_field", "to_field"}

PrepareStep = Callable[[str, dict[str, object]], WorkflowExecutionEnvelope]
ExecuteStep = Callable[[str, str], WorkflowExecutionReport]


def parse_recipe(payload: object) -> CapabilityRecipe:
    """Parse one strict recipe document; unknown fields fail closed."""

    if not isinstance(payload, dict):
        raise CapabilityRecipeError("Rezept muss ein JSON-Objekt sein.")
    _strict(payload, _RECIPE_FIELDS, "Rezept")
    if payload.get("schema") != RECIPE_SCHEMA:
        raise CapabilityRecipeError("Rezept verwendet ein unbekanntes Schema.")
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise CapabilityRecipeError("Rezept benötigt eine nichtleere Schrittliste.")
    raw_handoffs = payload.get("handoffs")
    if not isinstance(raw_handoffs, list):
        raise CapabilityRecipeError("Rezept benötigt eine handoffs-Liste.")
    steps = tuple(_parse_step(item, index) for index, item in enumerate(raw_steps))
    handoffs = tuple(
        _parse_handoff(item, index) for index, item in enumerate(raw_handoffs)
    )
    return CapabilityRecipe(
        recipe_id=_text(payload, "recipe_id", "Rezept"),
        title_en=_text(payload, "title_en", "Rezept"),
        title_de=_text(payload, "title_de", "Rezept"),
        summary_en=_text(payload, "summary_en", "Rezept"),
        summary_de=_text(payload, "summary_de", "Rezept"),
        lead_expert_id=_text(payload, "lead_expert_id", "Rezept"),
        steps=steps,
        handoffs=handoffs,
    )


def bundled_recipe_ids() -> tuple[str, ...]:
    """List the recipes shipped inside the package, not next to the checkout."""

    root = resources.files(_RECIPE_PACKAGE)
    return tuple(
        sorted(
            item.name.removesuffix(".json")
            for item in root.iterdir()
            if item.name.endswith(".json")
        )
    )


def load_bundled_recipe(recipe_id: str) -> CapabilityRecipe:
    """Load one packaged recipe by ID."""

    if recipe_id not in bundled_recipe_ids():
        raise CapabilityRecipeError(f"Unbekanntes Rezept: {recipe_id}")
    text = (
        resources.files(_RECIPE_PACKAGE)
        .joinpath(f"{recipe_id}.json")
        .read_text(encoding="utf-8")
    )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CapabilityRecipeError(f"Rezept ist nicht lesbar: {exc}") from exc
    recipe = parse_recipe(payload)
    if recipe.recipe_id != recipe_id:
        raise CapabilityRecipeError("Rezeptdatei und recipe_id stimmen nicht überein.")
    return recipe


def load_bundled_recipes() -> tuple[CapabilityRecipe, ...]:
    return tuple(load_bundled_recipe(item) for item in bundled_recipe_ids())


def recipe_sha256(recipe: CapabilityRecipe) -> str:
    return sha256(_canonical(recipe.to_dict(language="en"))).hexdigest()


def review_recipe(
    recipe: CapabilityRecipe,
    *,
    endpoint_statuses: Mapping[str, str],
    known_resource_ids: frozenset[str],
) -> RecipeEndorsement:
    """Check one recipe deterministically before a human ever sees the plan.

    Every responsible expert signs off: one for a single-domain recipe, all of
    them for a recipe that spans domains. The verdict later becomes part of the
    plan hash, so an approval covers the review too.
    """

    capabilities = {item.workflow_id: item for item in master_capability_catalog()}
    known_experts = {item.expert_id for item in master_expert_catalog()}
    findings: list[str] = []

    if recipe.lead_expert_id not in known_experts:
        findings.append(f"Unbekannte führende Fachrolle: {recipe.lead_expert_id}")

    for step in recipe.steps:
        capability = capabilities.get(step.workflow_id)
        if capability is None:
            findings.append(f"Unbekannter Endpunkt: {step.workflow_id}")
            continue
        if capability.expert_id != step.expert_id:
            findings.append(
                f"Endpunkt {step.workflow_id} gehört zu {capability.expert_id}, "
                f"nicht zu {step.expert_id}."
            )
        if capability.side_effects and not capability.approval_gates:
            findings.append(
                f"Endpunkt {step.workflow_id} wirkt nach außen, nennt aber kein Gate."
            )
        status = endpoint_statuses.get(step.workflow_id)
        if status != "connected":
            findings.append(
                f"Endpunkt {step.workflow_id} ist nicht verbunden: {status or 'unbekannt'}"
            )
        findings.extend(_resource_findings(step, known_resource_ids))

    findings.extend(_handoff_findings(recipe))

    if findings:
        raise CapabilityRecipeError(
            "Rezeptabnahme ist gescheitert: " + "; ".join(sorted(set(findings)))
        )

    reviewers = tuple(sorted({item.expert_id for item in recipe.steps}))
    checks = (
        "endpoint_owned_by_declared_expert",
        "endpoint_connected_at_runtime",
        "side_effects_have_approval_gates",
        "referenced_resources_are_registered",
        "handoffs_bind_the_same_logical_resource",
    )
    material = _canonical(
        {
            "recipe_sha256": recipe_sha256(recipe),
            "reviewers": list(reviewers),
            "checks": list(checks),
        }
    )
    return RecipeEndorsement(
        endorsement_id=f"endorsement_{sha256(material).hexdigest()}",
        recipe_id=recipe.recipe_id,
        reviewer_expert_ids=reviewers,
        checks=checks,
        status="endorsed",
    )


def build_recipe_plan(
    recipe: CapabilityRecipe,
    *,
    profile_id: str,
    language: str,
    prepare: PrepareStep,
    endpoint_statuses: Mapping[str, str],
    known_resource_ids: frozenset[str],
) -> CapabilityRecipePlan:
    """Resolve one recipe into a single plan with one confirmation for the chain."""

    endorsement = review_recipe(
        recipe,
        endpoint_statuses=endpoint_statuses,
        known_resource_ids=known_resource_ids,
    )
    capabilities = {item.workflow_id: item for item in master_capability_catalog()}
    digest = recipe_sha256(recipe)
    steps: list[MasterPlanStep] = []
    for sequence, step in enumerate(recipe.steps, start=1):
        capability = capabilities[step.workflow_id]
        envelope = prepare(step.workflow_id, dict(step.request))
        if envelope.workflow_id != step.workflow_id:
            raise CapabilityRecipeError(
                "Vorbereitete Hülle gehört nicht zum geplanten Endpunkt."
            )
        steps.append(
            MasterPlanStep(
                step_id=f"step_{sequence}_{digest[:12]}_{step.step_ref}",
                sequence=sequence,
                workflow_id=step.workflow_id,
                expert_id=capability.expert_id,
                goal=step.goal(language=language),
                execution_mode=capability.execution_mode,
                confirmation_required=bool(
                    capability.approval_gates or capability.side_effects
                ),
                approval_gates=capability.approval_gates,
                side_effects=capability.side_effects,
                boundaries=capability.boundaries,
                cli_commands=capability.cli_commands,
                execution_envelope=envelope,
            )
        )
    route = SemanticRouteReceipt(
        role_id="folderhome_master",
        expert_id=recipe.lead_expert_id,
        workflow_ids=recipe.workflow_ids,
        persona_id=None,
        resolution="explicit",
        confidence="high",
        why=(
            "Every step was resolved from a declared recipe and validated against "
            "the endpoint owner in the capability catalog."
        ),
    )
    request_sha256 = sha256(
        f"recipe:{recipe.recipe_id}".encode()
    ).hexdigest()
    hash_material = {
        "request_sha256": request_sha256,
        "profile_id": profile_id,
        "language": language,
        "route": route.to_dict(),
        "steps": [item.to_dict() for item in steps],
        "recipe_id": recipe.recipe_id,
        "recipe_sha256": digest,
        "handoffs": [item.to_dict() for item in recipe.handoffs],
        "endorsement": endorsement.to_dict(),
    }
    plan_sha256 = sha256(_canonical(hash_material)).hexdigest()
    summary = (
        f"{recipe.title(language=language)}: {len(steps)} verkettete Schritte, "
        "eine Bestätigung."
        if language == "de"
        else f"{recipe.title(language=language)}: {len(steps)} chained steps, "
        "one confirmation."
    )
    plan = MasterAgentPlan(
        plan_id=f"plan_{plan_sha256[:20]}",
        plan_sha256=plan_sha256,
        request_sha256=request_sha256,
        profile_id=profile_id,
        language=language,
        summary=summary,
        steps=tuple(steps),
        route=route,
    )
    return CapabilityRecipePlan(
        plan=plan,
        recipe_id=recipe.recipe_id,
        recipe_sha256=digest,
        endorsement=endorsement,
        handoffs=recipe.handoffs,
        step_refs=tuple(item.step_ref for item in recipe.steps),
    )


def execute_recipe_plan(
    recipe_plan: CapabilityRecipePlan,
    *,
    execute: ExecuteStep,
    approved_at: str,
) -> RecipeExecutionReport:
    """Run the confirmed chain in order and stop at the first failing step.

    The report is returned rather than raised, because a caller that only saw an
    exception could not tell which steps already took effect.
    """

    outcomes: list[RecipeStepOutcome] = []
    aborted = False
    for step_ref, step in zip(
        recipe_plan.step_refs, recipe_plan.plan.steps, strict=True
    ):
        if aborted:
            outcomes.append(
                RecipeStepOutcome(
                    step_ref=step_ref,
                    workflow_id=step.workflow_id,
                    expert_id=step.expert_id,
                    status="not_attempted",
                    execution_id=None,
                    detail="Ein früherer Schritt der Kette ist gescheitert.",
                )
            )
            continue
        envelope = step.execution_envelope
        if envelope is None:
            raise CapabilityRecipeError(
                "Rezeptschritt besitzt keine vorbereitete Ausführungshülle."
            )
        try:
            report = execute(envelope.envelope_id, approved_at)
        except Exception as exc:  # noqa: BLE001 - the chain reports every failure
            aborted = True
            outcomes.append(
                RecipeStepOutcome(
                    step_ref=step_ref,
                    workflow_id=step.workflow_id,
                    expert_id=step.expert_id,
                    status="failed",
                    execution_id=None,
                    detail=str(exc),
                )
            )
            continue
        outcomes.append(
            RecipeStepOutcome(
                step_ref=step_ref,
                workflow_id=step.workflow_id,
                expert_id=step.expert_id,
                status="executed",
                execution_id=report.execution_id,
            )
        )
    status = "aborted" if aborted else "executed"
    material = _canonical(
        {
            "plan_id": recipe_plan.plan_id,
            "approved_at": approved_at,
            "status": status,
            "outcomes": [item.to_dict() for item in outcomes],
        }
    )
    return RecipeExecutionReport(
        report_id=f"recipe_execution_{sha256(material).hexdigest()}",
        recipe_id=recipe_plan.recipe_id,
        plan_id=recipe_plan.plan_id,
        status=status,
        outcomes=tuple(outcomes),
    )


def _resource_findings(
    step: CapabilityRecipeStep,
    known_resource_ids: frozenset[str],
) -> list[str]:
    findings: list[str] = []
    for key, value in step.request.items():
        if not key.endswith(_RESOURCE_FIELD_SUFFIX) or value is None:
            continue
        if not isinstance(value, str):
            findings.append(f"Ressourcenfeld {key} muss eine logische ID sein.")
            continue
        if value not in known_resource_ids:
            findings.append(f"Ressource ist nicht konfiguriert: {value}")
    return findings


def _handoff_findings(recipe: CapabilityRecipe) -> list[str]:
    by_ref = {item.step_ref: item for item in recipe.steps}
    findings: list[str] = []
    for handoff in recipe.handoffs:
        source = by_ref[handoff.from_step]
        target = by_ref[handoff.to_step]
        produced = source.request.get(handoff.from_field)
        consumed = target.request.get(handoff.to_field)
        if not isinstance(produced, str) or not isinstance(consumed, str):
            findings.append(
                f"Übergabe {handoff.from_step}->{handoff.to_step} nennt keine "
                "logischen Ressourcen-IDs."
            )
            continue
        if produced != consumed:
            findings.append(
                f"Übergabe {handoff.from_step}->{handoff.to_step} verbindet "
                f"{produced} mit {consumed}; beide Seiten müssen dieselbe "
                "Ressource nennen."
            )
    return findings


def _parse_step(payload: object, index: int) -> CapabilityRecipeStep:
    label = f"Rezeptschritt {index + 1}"
    if not isinstance(payload, dict):
        raise CapabilityRecipeError(f"{label} muss ein Objekt sein.")
    _strict(payload, _STEP_FIELDS, label)
    request = payload.get("request")
    if not isinstance(request, dict):
        raise CapabilityRecipeError(f"{label}.request muss ein Objekt sein.")
    return CapabilityRecipeStep(
        step_ref=_text(payload, "step_ref", label),
        workflow_id=_text(payload, "workflow_id", label),
        expert_id=_text(payload, "expert_id", label),
        goal_en=_text(payload, "goal_en", label),
        goal_de=_text(payload, "goal_de", label),
        request=dict(request),
    )


def _parse_handoff(payload: object, index: int) -> CapabilityHandoff:
    label = f"Übergabekante {index + 1}"
    if not isinstance(payload, dict):
        raise CapabilityRecipeError(f"{label} muss ein Objekt sein.")
    _strict(payload, _HANDOFF_FIELDS, label)
    return CapabilityHandoff(
        from_step=_text(payload, "from_step", label),
        to_step=_text(payload, "to_step", label),
        from_field=_text(payload, "from_field", label),
        to_field=_text(payload, "to_field", label),
    )


def _strict(payload: dict[str, object], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload).difference(allowed))
    missing = sorted(allowed.difference(payload))
    if unknown:
        raise CapabilityRecipeError(
            f"{label} enthält unbekannte Felder: {', '.join(unknown)}"
        )
    if missing:
        raise CapabilityRecipeError(f"{label} benötigt Felder: {', '.join(missing)}")


def _text(payload: dict[str, object], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityRecipeError(f"{label}.{key} muss nichtleerer Text sein.")
    return value


def _canonical(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


__all__ = [
    "ExecuteStep",
    "PrepareStep",
    "build_recipe_plan",
    "bundled_recipe_ids",
    "execute_recipe_plan",
    "load_bundled_recipe",
    "load_bundled_recipes",
    "parse_recipe",
    "recipe_sha256",
    "review_recipe",
]
