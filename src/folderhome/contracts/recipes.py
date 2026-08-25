"""Contracts for declarative multi-step capability recipes.

A recipe is a journey a person recognizes — "I had an accident, sort it out" —
expressed as an ordered list of existing endpoints. It adds no new powers: every
step keeps its own adapter, its own gates and its own approval semantics. What a
recipe adds is that the whole chain becomes one plan behind one confirmation.

Data moves between steps only through logical resource IDs. A handoff declares
that the resource one step writes is the resource the next step reads, and both
sides must name the same ID. No value from a step report is ever substituted
into a later request, so every request is complete and hashable at plan time.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field

from folderhome.contracts.master_agent import MasterAgentPlan

_ID = re.compile(r"[a-z][a-z0-9_-]{2,63}")
_STEP_REF = re.compile(r"[a-z][a-z0-9_]{1,31}")
_FIELD = re.compile(r"[a-z][a-z0-9_]{1,63}")
_SHA256 = re.compile(r"[0-9a-f]{64}")

RECIPE_SCHEMA = "folderhome.capability-recipe.v1"
ENDORSEMENT_SCHEMA = "folderhome.recipe-endorsement.v1"


class CapabilityRecipeError(ValueError):
    """Raised when a recipe, a handoff, or an endorsement is not trustworthy."""


@dataclass(frozen=True, slots=True)
class CapabilityRecipeStep:
    """One endpoint call inside a recipe, complete at plan time."""

    step_ref: str
    workflow_id: str
    expert_id: str
    goal_en: str
    goal_de: str
    request: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if _STEP_REF.fullmatch(self.step_ref) is None:
            raise CapabilityRecipeError(f"Schrittname ist ungültig: {self.step_ref}")
        for value, label in (
            (self.workflow_id, "workflow_id"),
            (self.expert_id, "expert_id"),
        ):
            if _ID.fullmatch(value) is None:
                raise CapabilityRecipeError(f"{label} ist ungültig: {value}")
        for value, label in ((self.goal_en, "goal_en"), (self.goal_de, "goal_de")):
            if not value.strip() or len(value) > 500:
                raise CapabilityRecipeError(f"{label} benötigt 1 bis 500 Zeichen.")
        if not isinstance(self.request, dict):
            raise CapabilityRecipeError("Schrittanfrage muss ein Objekt sein.")
        for key in self.request:
            if not isinstance(key, str) or _FIELD.fullmatch(key) is None:
                raise CapabilityRecipeError(
                    f"Schrittanfrage besitzt ein ungültiges Feld: {key}"
                )

    def goal(self, *, language: str) -> str:
        return self.goal_de if language == "de" else self.goal_en

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        return {
            "step_ref": self.step_ref,
            "workflow_id": self.workflow_id,
            "expert_id": self.expert_id,
            "goal": self.goal(language=language),
            "request": deepcopy(self.request),
        }


@dataclass(frozen=True, slots=True)
class CapabilityHandoff:
    """One declared link between two steps, expressed as one logical resource.

    The named field of the earlier step and the named field of the later step
    must resolve to the same logical resource ID. That covers both shapes the
    chain actually uses: a store one step writes and a later step reads, and a
    source both steps must agree on so the later step works on exactly the
    material the earlier one used. It never carries a value from a step report.
    """

    from_step: str
    to_step: str
    from_field: str
    to_field: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.from_step, "from_step"),
            (self.to_step, "to_step"),
        ):
            if _STEP_REF.fullmatch(value) is None:
                raise CapabilityRecipeError(f"{label} ist ungültig: {value}")
        if self.from_step == self.to_step:
            raise CapabilityRecipeError("Eine Übergabekante braucht zwei Schritte.")
        for value, label in (
            (self.from_field, "from_field"),
            (self.to_field, "to_field"),
        ):
            if _FIELD.fullmatch(value) is None:
                raise CapabilityRecipeError(f"{label} ist ungültig: {value}")

    def to_dict(self) -> dict[str, object]:
        return {
            "from_step": self.from_step,
            "to_step": self.to_step,
            "from_field": self.from_field,
            "to_field": self.to_field,
            "carries_report_values": False,
            "carries_logical_resource_id": True,
        }


@dataclass(frozen=True, slots=True)
class CapabilityRecipe:
    """One ordered journey over existing endpoints; never a new capability."""

    recipe_id: str
    title_en: str
    title_de: str
    summary_en: str
    summary_de: str
    lead_expert_id: str
    steps: tuple[CapabilityRecipeStep, ...]
    handoffs: tuple[CapabilityHandoff, ...] = ()

    SCHEMA = RECIPE_SCHEMA

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.recipe_id) is None:
            raise CapabilityRecipeError(f"recipe_id ist ungültig: {self.recipe_id}")
        if _ID.fullmatch(self.lead_expert_id) is None:
            raise CapabilityRecipeError("lead_expert_id ist ungültig.")
        for value, label in (
            (self.title_en, "title_en"),
            (self.title_de, "title_de"),
            (self.summary_en, "summary_en"),
            (self.summary_de, "summary_de"),
        ):
            if not value.strip() or len(value) > 500:
                raise CapabilityRecipeError(f"{label} benötigt 1 bis 500 Zeichen.")
        if not self.steps:
            raise CapabilityRecipeError("Rezept benötigt mindestens einen Schritt.")
        order = [item.step_ref for item in self.steps]
        if len(order) != len(set(order)):
            raise CapabilityRecipeError("Schrittnamen müssen eindeutig sein.")
        position = {ref: index for index, ref in enumerate(order)}
        for handoff in self.handoffs:
            missing = [
                ref
                for ref in (handoff.from_step, handoff.to_step)
                if ref not in position
            ]
            if missing:
                raise CapabilityRecipeError(
                    f"Übergabekante nennt einen unbekannten Schritt: {missing[0]}"
                )
            if position[handoff.from_step] >= position[handoff.to_step]:
                raise CapabilityRecipeError(
                    "Eine Übergabe muss von einem früheren zu einem späteren Schritt gehen."
                )

    @property
    def workflow_ids(self) -> tuple[str, ...]:
        return tuple(item.workflow_id for item in self.steps)

    def title(self, *, language: str) -> str:
        return self.title_de if language == "de" else self.title_en

    def summary(self, *, language: str) -> str:
        return self.summary_de if language == "de" else self.summary_en

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "recipe_id": self.recipe_id,
            "title": self.title(language=language),
            "summary": self.summary(language=language),
            "lead_expert_id": self.lead_expert_id,
            "steps": [item.to_dict(language=language) for item in self.steps],
            "handoffs": [item.to_dict() for item in self.handoffs],
            "grants_new_capability": False,
            "paths_disclosed": False,
        }


@dataclass(frozen=True, slots=True)
class RecipeEndorsement:
    """Deterministic sign-off of one recipe plan by its responsible experts."""

    endorsement_id: str
    recipe_id: str
    reviewer_expert_ids: tuple[str, ...]
    checks: tuple[str, ...]
    status: str
    findings: tuple[str, ...] = ()

    SCHEMA = ENDORSEMENT_SCHEMA

    def __post_init__(self) -> None:
        if not self.endorsement_id.startswith("endorsement_") or _SHA256.fullmatch(
            self.endorsement_id.removeprefix("endorsement_")
        ) is None:
            raise CapabilityRecipeError("endorsement_id muss endorsement_<sha256> sein.")
        if _ID.fullmatch(self.recipe_id) is None:
            raise CapabilityRecipeError("Abnahme benötigt eine gültige recipe_id.")
        if not self.reviewer_expert_ids:
            raise CapabilityRecipeError("Abnahme benötigt mindestens eine Fachrolle.")
        if len(self.reviewer_expert_ids) != len(set(self.reviewer_expert_ids)):
            raise CapabilityRecipeError("Abnahme nennt eine Fachrolle doppelt.")
        for value in self.reviewer_expert_ids:
            if _ID.fullmatch(value) is None:
                raise CapabilityRecipeError(f"Prüfende Fachrolle ist ungültig: {value}")
        if not self.checks:
            raise CapabilityRecipeError("Abnahme benötigt mindestens eine Prüfung.")
        if self.status != "endorsed":
            raise CapabilityRecipeError(
                "Nur eine bestandene Abnahme darf als Beleg entstehen."
            )
        if self.findings:
            raise CapabilityRecipeError(
                "Eine Abnahme mit offenen Befunden darf nicht bestanden sein."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "endorsement_id": self.endorsement_id,
            "recipe_id": self.recipe_id,
            "reviewer_expert_ids": list(self.reviewer_expert_ids),
            "reviewer_count": len(self.reviewer_expert_ids),
            "checks": list(self.checks),
            "status": self.status,
            "findings": list(self.findings),
        }


@dataclass(frozen=True, slots=True)
class CapabilityRecipePlan:
    """One recipe resolved into a single, hash-bound multi-step master plan."""

    plan: MasterAgentPlan
    recipe_id: str
    recipe_sha256: str
    endorsement: RecipeEndorsement
    handoffs: tuple[CapabilityHandoff, ...]
    step_refs: tuple[str, ...]

    SCHEMA = "folderhome.capability-recipe-plan.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.recipe_id) is None:
            raise CapabilityRecipeError("Rezeptplan benötigt eine gültige recipe_id.")
        if _SHA256.fullmatch(self.recipe_sha256) is None:
            raise CapabilityRecipeError("recipe_sha256 muss ein SHA-256 sein.")
        if self.endorsement.recipe_id != self.recipe_id:
            raise CapabilityRecipeError("Abnahme gehört zu einem anderen Rezept.")
        if len(self.step_refs) != len(self.plan.steps):
            raise CapabilityRecipeError(
                "Rezeptplan benötigt genau einen Schrittnamen je Planschritt."
            )

    @property
    def plan_id(self) -> str:
        return self.plan.plan_id

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "recipe_id": self.recipe_id,
            "recipe_sha256": self.recipe_sha256,
            "plan": self.plan.to_dict(),
            "endorsement": self.endorsement.to_dict(),
            "handoffs": [item.to_dict() for item in self.handoffs],
            "step_refs": list(self.step_refs),
            "single_confirmation_command": f"/confirm {self.plan.plan_id}",
            "execution_performed": False,
        }


@dataclass(frozen=True, slots=True)
class RecipeStepOutcome:
    """What actually happened to one step of an executed recipe chain."""

    step_ref: str
    workflow_id: str
    expert_id: str
    status: str
    execution_id: str | None
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"executed", "failed", "not_attempted"}:
            raise CapabilityRecipeError(f"Unbekannter Schrittstatus: {self.status}")
        if self.status == "executed" and not self.execution_id:
            raise CapabilityRecipeError("Ein ausgeführter Schritt benötigt eine ID.")
        if self.status != "executed" and self.execution_id is not None:
            raise CapabilityRecipeError(
                "Nur ein ausgeführter Schritt darf eine Ausführungs-ID tragen."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "step_ref": self.step_ref,
            "workflow_id": self.workflow_id,
            "expert_id": self.expert_id,
            "status": self.status,
            "execution_id": self.execution_id,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class RecipeExecutionReport:
    """Honest chain result: what ran, what broke, what was never attempted."""

    report_id: str
    recipe_id: str
    plan_id: str
    status: str
    outcomes: tuple[RecipeStepOutcome, ...]

    SCHEMA = "folderhome.recipe-execution-report.v1"

    def __post_init__(self) -> None:
        if not self.report_id.startswith("recipe_execution_") or _SHA256.fullmatch(
            self.report_id.removeprefix("recipe_execution_")
        ) is None:
            raise CapabilityRecipeError(
                "report_id muss recipe_execution_<sha256> sein."
            )
        if self.status not in {"executed", "aborted"}:
            raise CapabilityRecipeError(f"Unbekannter Kettenstatus: {self.status}")
        if not self.outcomes:
            raise CapabilityRecipeError("Kettenbericht benötigt Schrittergebnisse.")
        failed = [item for item in self.outcomes if item.status == "failed"]
        skipped = [item for item in self.outcomes if item.status == "not_attempted"]
        if self.status == "executed" and (failed or skipped):
            raise CapabilityRecipeError(
                "Eine vollständige Kette darf keine offenen Schritte enthalten."
            )
        if self.status == "aborted" and len(failed) != 1:
            raise CapabilityRecipeError(
                "Eine abgebrochene Kette benennt genau einen gescheiterten Schritt."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "recipe_id": self.recipe_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "executed_step_refs": [
                item.step_ref for item in self.outcomes if item.status == "executed"
            ],
            "failed_step_refs": [
                item.step_ref for item in self.outcomes if item.status == "failed"
            ],
            "not_attempted_step_refs": [
                item.step_ref
                for item in self.outcomes
                if item.status == "not_attempted"
            ],
            "outcomes": [item.to_dict() for item in self.outcomes],
        }


__all__ = [
    "ENDORSEMENT_SCHEMA",
    "RECIPE_SCHEMA",
    "CapabilityHandoff",
    "CapabilityRecipe",
    "CapabilityRecipeError",
    "CapabilityRecipePlan",
    "CapabilityRecipeStep",
    "RecipeEndorsement",
    "RecipeExecutionReport",
    "RecipeStepOutcome",
]
