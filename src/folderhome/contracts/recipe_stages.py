"""Public proposal for one concrete section, not approval of a future journey."""

from copy import deepcopy
from dataclasses import dataclass

from folderhome.contracts.master_agent import MasterAgentPlan
from folderhome.contracts.recipes import CapabilityRecipeError


@dataclass(frozen=True, slots=True)
class RecipeStagePlan:
    plan: MasterAgentPlan
    run_state: dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_state", deepcopy(self.run_state))
        self.verify_integrity()

    @property
    def plan_id(self) -> str:
        return self.plan.plan_id

    @property
    def run_id(self) -> str:
        return self.plan.approval_context["run_id"]

    @property
    def recipe_id(self) -> str:
        return self.plan.approval_context["recipe_id"]

    def verify_integrity(self) -> None:
        self.plan.verify_integrity()
        context = self.plan.approval_context
        if (
            context.get("schema") != "folderhome.recipe-stage-context.v1"
            or self.run_state.get("run_id") != context.get("run_id")
            or self.run_state.get("recipe_id") != context.get("recipe_id")
            or self.run_state.get("profile_id") != self.plan.profile_id
            or self.run_state.get("pending_plan_id") != self.plan_id
            or self.run_state.get("status") != "awaiting_approval"
        ):
            raise CapabilityRecipeError("Abschnittsvorschlag gehört nicht zu diesem Lauf.")

    def to_dict(self) -> dict[str, object]:
        self.verify_integrity()
        return {
            "schema": "folderhome.recipe-stage-plan.v1",
            "recipe_id": self.recipe_id,
            "plan": self.plan.to_dict(),
            "run": deepcopy(self.run_state),
            "endorsement": deepcopy(self.plan.approval_context["endorsement"]),
            "single_confirmation_command": f"/confirm {self.plan_id}",
            "execution_performed": False,
        }
