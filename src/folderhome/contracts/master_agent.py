"""Contracts for semantic FolderHome agent routing and approval-bound plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from folderhome.contracts.workflow_execution import WorkflowExecutionEnvelope

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.\-_]{2,95}")
_HASH = re.compile(r"[0-9a-f]{64}")
_LANGUAGES = {"de", "en"}
_CONFIDENCE = {"high", "medium", "low"}
_EXECUTION_MODES = {"direct_read_only", "approval_bound_workflow", "planning_only"}
_RESOLUTIONS = {"explicit", "live_resolver", "gap"}


def _validate_identifier(value: str, label: str) -> None:
    if _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{label} ist ungültig: {value}")


def _validate_text(value: str, label: str, *, maximum: int = 2_000) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} benötigt 1 bis {maximum} Zeichen.")


def _validate_unique_ids(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} enthält doppelte Werte.")
    for value in values:
        _validate_identifier(value, label)


def _validate_language(language: str) -> None:
    if language not in _LANGUAGES:
        raise ValueError("language muss de oder en sein.")


@dataclass(frozen=True, slots=True)
class CoordinatorRole:
    """The single semantic coordinator visible to a FolderHome user."""

    role_id: str
    title_en: str
    title_de: str
    description_en: str
    description_de: str
    expert_ids: tuple[str, ...]

    SCHEMA = "folderhome.coordinator-role.v1"

    def __post_init__(self) -> None:
        _validate_identifier(self.role_id, "role_id")
        _validate_unique_ids(self.expert_ids, "expert_ids")
        for value, label in (
            (self.title_en, "title_en"),
            (self.title_de, "title_de"),
            (self.description_en, "description_en"),
            (self.description_de, "description_de"),
        ):
            _validate_text(value, label)

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        _validate_language(language)
        return {
            "schema": self.SCHEMA,
            "role_id": self.role_id,
            "title": self.title_de if language == "de" else self.title_en,
            "description": self.description_de if language == "de" else self.description_en,
            "expert_ids": list(self.expert_ids),
        }


@dataclass(frozen=True, slots=True)
class ExpertRole:
    """A bounded domain role whose executable endpoints are resolved separately."""

    expert_id: str
    parent_role_id: str
    title_en: str
    title_de: str
    description_en: str
    description_de: str
    workflow_ids: tuple[str, ...]
    persona_ids: tuple[str, ...]

    SCHEMA = "folderhome.expert-role.v1"

    def __post_init__(self) -> None:
        _validate_identifier(self.expert_id, "expert_id")
        _validate_identifier(self.parent_role_id, "parent_role_id")
        _validate_unique_ids(self.workflow_ids, "workflow_ids")
        _validate_unique_ids(self.persona_ids, "persona_ids")
        if not self.workflow_ids:
            raise ValueError("Fachrolle benötigt mindestens einen Workflow-Endpunkt.")
        for value, label in (
            (self.title_en, "title_en"),
            (self.title_de, "title_de"),
            (self.description_en, "description_en"),
            (self.description_de, "description_de"),
        ):
            _validate_text(value, label)

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        _validate_language(language)
        return {
            "schema": self.SCHEMA,
            "expert_id": self.expert_id,
            "parent_role_id": self.parent_role_id,
            "title": self.title_de if language == "de" else self.title_en,
            "description": self.description_de if language == "de" else self.description_en,
            "workflow_ids": list(self.workflow_ids),
            "persona_ids": list(self.persona_ids),
        }


@dataclass(frozen=True, slots=True)
class RoutingPersona:
    """Optional communication overlay; never a capability or permission source."""

    persona_id: str
    title_en: str
    title_de: str
    style_en: str
    style_de: str
    expert_ids: tuple[str, ...]
    authority: str = "style_only"

    SCHEMA = "folderhome.routing-persona.v2"

    def __post_init__(self) -> None:
        _validate_identifier(self.persona_id, "persona_id")
        _validate_unique_ids(self.expert_ids, "expert_ids")
        if self.authority != "style_only":
            raise ValueError("Personas dürfen ausschließlich den Kommunikationsstil prägen.")
        for value, label in (
            (self.title_en, "title_en"),
            (self.title_de, "title_de"),
            (self.style_en, "style_en"),
            (self.style_de, "style_de"),
        ):
            _validate_text(value, label)

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        _validate_language(language)
        return {
            "schema": self.SCHEMA,
            "persona_id": self.persona_id,
            "title": self.title_de if language == "de" else self.title_en,
            "style": self.style_de if language == "de" else self.style_en,
            "expert_ids": list(self.expert_ids),
            "authority": self.authority,
        }


@dataclass(frozen=True, slots=True)
class MasterCapability:
    """A verified local workflow endpoint, never an intent classification rule."""

    capability_id: str
    workflow_id: str
    expert_id: str
    endpoint_skill_ids: tuple[str, ...]
    execution_mode: str
    cli_commands: tuple[str, ...]
    boundaries: tuple[str, ...]
    approval_gates: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    resolution: str = "explicit"

    SCHEMA = "folderhome.master-capability.v2"

    def __post_init__(self) -> None:
        for value, label in (
            (self.capability_id, "capability_id"),
            (self.workflow_id, "workflow_id"),
            (self.expert_id, "expert_id"),
        ):
            _validate_identifier(value, label)
        _validate_unique_ids(self.endpoint_skill_ids, "endpoint_skill_ids")
        if self.execution_mode not in _EXECUTION_MODES:
            raise ValueError("Unbekannter execution_mode.")
        if self.resolution not in _RESOLUTIONS:
            raise ValueError("Unbekannte Endpoint-Auflösung.")
        if not self.cli_commands or not self.boundaries:
            raise ValueError("Fähigkeit benötigt CLI-Hinweise und Grenzen.")
        for values, label in (
            (self.cli_commands, "cli_commands"),
            (self.boundaries, "boundaries"),
            (self.approval_gates, "approval_gates"),
            (self.side_effects, "side_effects"),
        ):
            if len(values) != len(set(values)) or any(not item.strip() for item in values):
                raise ValueError(f"{label} enthält leere oder doppelte Werte.")
        if self.execution_mode == "direct_read_only" and (
            self.approval_gates or self.side_effects
        ):
            raise ValueError("Read-only-Endpunkte dürfen keine Side Effects deklarieren.")
        if self.side_effects and not self.approval_gates:
            raise ValueError("Side Effects benötigen ausdrückliche Freigabegates.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "capability_id": self.capability_id,
            "workflow_id": self.workflow_id,
            "expert_id": self.expert_id,
            "endpoint_skill_ids": list(self.endpoint_skill_ids),
            "execution_mode": self.execution_mode,
            "cli_commands": list(self.cli_commands),
            "boundaries": list(self.boundaries),
            "approval_gates": list(self.approval_gates),
            "side_effects": list(self.side_effects),
            "resolution": self.resolution,
        }


@dataclass(frozen=True, slots=True)
class SemanticRouteReceipt:
    """Auditable receipt for a model-selected route with resolved endpoints."""

    role_id: str
    expert_id: str
    workflow_ids: tuple[str, ...]
    persona_id: str | None
    resolution: str
    confidence: str
    why: str
    gaps: tuple[str, ...] = ()

    SCHEMA = "folderhome.semantic-route-receipt.v1"

    def __post_init__(self) -> None:
        _validate_identifier(self.role_id, "role_id")
        _validate_identifier(self.expert_id, "expert_id")
        _validate_unique_ids(self.workflow_ids, "workflow_ids")
        if self.persona_id is not None:
            _validate_identifier(self.persona_id, "persona_id")
        if self.resolution not in _RESOLUTIONS:
            raise ValueError("Unbekannte Endpoint-Auflösung.")
        if self.confidence not in _CONFIDENCE:
            raise ValueError("confidence muss high, medium oder low sein.")
        _validate_text(self.why, "why", maximum=500)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "role_id": self.role_id,
            "expert_id": self.expert_id,
            "workflow_ids": list(self.workflow_ids),
            "persona_id": self.persona_id,
            "resolution": self.resolution,
            "confidence": self.confidence,
            "why": self.why,
            "gaps": list(self.gaps),
        }


@dataclass(frozen=True, slots=True)
class MasterPlanStep:
    """One endpoint-bound step selected by the agent and built deterministically."""

    step_id: str
    sequence: int
    workflow_id: str
    expert_id: str
    goal: str
    execution_mode: str
    confirmation_required: bool
    approval_gates: tuple[str, ...]
    side_effects: tuple[str, ...]
    boundaries: tuple[str, ...]
    cli_commands: tuple[str, ...]
    execution_envelope: WorkflowExecutionEnvelope | None = None
    status: str = "planned"

    SCHEMA = "folderhome.master-plan-step.v2"

    def __post_init__(self) -> None:
        for value, label in (
            (self.step_id, "step_id"),
            (self.workflow_id, "workflow_id"),
            (self.expert_id, "expert_id"),
        ):
            _validate_identifier(value, label)
        _validate_text(self.goal, "goal")
        if self.sequence < 1:
            raise ValueError("sequence muss positiv sein.")
        if self.execution_mode not in _EXECUTION_MODES:
            raise ValueError("Unbekannter execution_mode.")
        expected = bool(self.approval_gates or self.side_effects)
        if self.confirmation_required != expected:
            raise ValueError("Bestätigungsstatus passt nicht zu Gates und Side Effects.")
        if self.status != "planned":
            raise ValueError("Ein neuer Master-Schritt muss planned sein.")
        if self.execution_envelope is not None:
            if self.execution_envelope.workflow_id != self.workflow_id:
                raise ValueError("Ausführungshülle gehört nicht zum Workflow-Schritt.")
            if self.execution_mode != "approval_bound_workflow":
                raise ValueError("Ausführungshülle benötigt einen freigabegebundenen Workflow.")
            if not self.confirmation_required:
                raise ValueError("Ausführungshülle benötigt eine explizite Bestätigung.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "step_id": self.step_id,
            "sequence": self.sequence,
            "workflow_id": self.workflow_id,
            "expert_id": self.expert_id,
            "goal": self.goal,
            "execution_mode": self.execution_mode,
            "confirmation_required": self.confirmation_required,
            "approval_gates": list(self.approval_gates),
            "side_effects": list(self.side_effects),
            "boundaries": list(self.boundaries),
            "cli_commands": list(self.cli_commands),
            "execution_envelope": (
                self.execution_envelope.to_dict()
                if self.execution_envelope is not None
                else None
            ),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class MasterAgentPlan:
    """Hash-bound plan created only after a model or user selected endpoints."""

    plan_id: str
    plan_sha256: str
    request_sha256: str
    profile_id: str
    language: str
    summary: str
    steps: tuple[MasterPlanStep, ...]
    route: SemanticRouteReceipt
    model_call_performed: bool = False
    execution_performed: bool = False
    side_effects: tuple[str, ...] = ()
    security_boundary: str = "operating_system_account"
    profiles_are_authorization_boundaries: bool = False

    SCHEMA = "folderhome.master-agent-plan.v2"

    def __post_init__(self) -> None:
        _validate_identifier(self.plan_id, "plan_id")
        for value, label in (
            (self.plan_sha256, "plan_sha256"),
            (self.request_sha256, "request_sha256"),
        ):
            if _HASH.fullmatch(value) is None:
                raise ValueError(f"{label} muss ein SHA-256 sein.")
        _validate_identifier(self.profile_id, "profile_id")
        _validate_language(self.language)
        _validate_text(self.summary, "summary")
        if not self.steps:
            raise ValueError("Masterplan benötigt mindestens einen aufgelösten Schritt.")
        if self.model_call_performed or self.execution_performed or self.side_effects:
            raise ValueError(
                "Planerstellung darf keine Modell- oder Workflow-Ausführung behaupten."
            )

    @property
    def confirmation_required(self) -> bool:
        return any(item.confirmation_required for item in self.steps)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "request_sha256": self.request_sha256,
            "profile_id": self.profile_id,
            "language": self.language,
            "summary": self.summary,
            "route": self.route.to_dict(),
            "steps": [item.to_dict() for item in self.steps],
            "model_call_performed": self.model_call_performed,
            "execution_performed": self.execution_performed,
            "confirmation_required": self.confirmation_required,
            "side_effects": list(self.side_effects),
            "security_boundary": self.security_boundary,
            "profiles_are_authorization_boundaries": self.profiles_are_authorization_boundaries,
        }


@dataclass(frozen=True, slots=True)
class MasterPlanApproval:
    """Exact human confirmation of selected master-plan steps."""

    approval_id: str
    plan_id: str
    plan_sha256: str
    step_ids: tuple[str, ...]
    approved_at: str

    SCHEMA = "folderhome.master-plan-approval.v1"

    def __post_init__(self) -> None:
        _validate_identifier(self.approval_id, "approval_id")
        _validate_identifier(self.plan_id, "plan_id")
        if _HASH.fullmatch(self.plan_sha256) is None:
            raise ValueError("plan_sha256 muss ein SHA-256 sein.")
        if not self.step_ids:
            raise ValueError("Masterfreigabe benötigt mindestens einen step_id.")
        _validate_unique_ids(self.step_ids, "step_ids")
        try:
            parsed = datetime.fromisoformat(self.approved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("approved_at muss ISO-8601 sein.") from exc
        if parsed.tzinfo is None:
            raise ValueError("approved_at benötigt eine Zeitzone.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "step_ids": list(self.step_ids),
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class MasterConfirmationReceipt:
    """Proof of exact approval without falsely claiming endpoint execution."""

    receipt_id: str
    approval_id: str
    plan_id: str
    plan_sha256: str
    approved_step_ids: tuple[str, ...]
    execution_performed: bool = False
    side_effects: tuple[str, ...] = ()
    status: str = "confirmed_for_workflow_handoff"

    SCHEMA = "folderhome.master-confirmation-receipt.v1"

    def __post_init__(self) -> None:
        for value, label in (
            (self.receipt_id, "receipt_id"),
            (self.approval_id, "approval_id"),
            (self.plan_id, "plan_id"),
        ):
            _validate_identifier(value, label)
        if _HASH.fullmatch(self.plan_sha256) is None:
            raise ValueError("plan_sha256 muss ein SHA-256 sein.")
        if self.execution_performed or self.side_effects:
            raise ValueError("Bestätigungsbeleg darf keine Ausführung behaupten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "receipt_id": self.receipt_id,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "approved_step_ids": list(self.approved_step_ids),
            "execution_performed": self.execution_performed,
            "side_effects": list(self.side_effects),
            "status": self.status,
        }
