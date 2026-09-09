"""Process-local v2 runs with exact, single-use approval for each concrete section.

There is deliberately no deserializer for execution reports. Only this run's
executor callback can produce source evidence, after its own exact approval.
"""

from __future__ import annotations

import json
import secrets
import threading
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256

from folderhome.application.master_agent import (
    MasterAgentError,
    confirm_master_agent_plan,
    master_capability_catalog,
)
from folderhome.application.recipes import recipe_sha256, review_recipe
from folderhome.application.workflow_execution import WorkflowExecutionGateway
from folderhome.contracts.master_agent import (
    MasterAgentPlan,
    MasterPlanApproval,
    MasterPlanStep,
    SemanticRouteReceipt,
    _validate_identifier,
    _validate_language,
)
from folderhome.contracts.recipe_results import ResultBoundRecipe
from folderhome.contracts.recipes import CapabilityRecipeError
from folderhome.contracts.workflow_execution import (
    WorkflowExecutionEnvelope,
    WorkflowExecutionReport,
)


def _digest(value: object) -> str:
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise CapabilityRecipeError("Rezeptnachweis ist nicht als JSON prüfbar.") from exc
    return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class _StepResult:
    plan_id: str
    envelope: WorkflowExecutionEnvelope
    report: WorkflowExecutionReport
    report_sha256: str

    def verify(self) -> None:
        self.report.verify_envelope(self.envelope)
        if self.report_sha256 != _digest(self.report.to_dict()):
            raise CapabilityRecipeError("Gespeicherter Rezeptbericht wurde verändert.")


class RecipeRun:
    """One bounded journey using the configured gateway's domain adapters."""

    def __init__(
        self,
        recipe: ResultBoundRecipe,
        *,
        profile_id: str,
        language: str,
        gateway: WorkflowExecutionGateway,
    ) -> None:
        if not isinstance(recipe, ResultBoundRecipe):
            raise CapabilityRecipeError("Abschnittsausführung benötigt ein v2-Rezept.")
        try:
            _validate_identifier(profile_id, "profile_id")
            _validate_language(language)
        except (TypeError, ValueError) as exc:
            raise CapabilityRecipeError(
                "Rezeptlauf benötigt ein gültiges Profil und eine Sprache."
            ) from exc
        self._recipe = deepcopy(recipe)
        self._recipe.__post_init__()
        self._recipe_sha256 = recipe_sha256(self._recipe)
        self._profile_id = profile_id
        self._language = language
        self._run_id = f"recipe_run_{secrets.token_hex(16)}"
        scope = gateway.new_preparation_scope()
        self._prepare = lambda workflow_id, request: scope.prepare(
            workflow_id=workflow_id,
            profile_id=self._profile_id,
            request=request,
        )
        self._execute = lambda envelope_id, timestamp: scope.execute(
            envelope_id=envelope_id,
            approved_at=timestamp,
        )
        self._discard = scope.discard_unexecuted
        self._lock = threading.RLock()
        self._status = "ready"
        self._pending: MasterAgentPlan | None = None
        self._results: dict[str, _StepResult] = {}
        self._stage_ids: list[str] = []
        self._last_execution: dict[str, object] | None = None
        self._cleanup_pending: tuple[str, ...] = ()

    def _cleanup(self, ids: tuple[str, ...]) -> None:
        self._cleanup_pending = tuple(dict.fromkeys((*self._cleanup_pending, *ids)))
        if not self._cleanup_pending:
            return
        try:
            self._discard(self._cleanup_pending)
        except Exception:
            raise CapabilityRecipeError(
                "Offene Rezeptvorbereitungen konnten nicht bereinigt werden."
            ) from None
        self._cleanup_pending = ()

    def _verify_sources(self) -> None:
        if recipe_sha256(self._recipe) != self._recipe_sha256:
            raise CapabilityRecipeError("Rezept wurde während des Laufs verändert.")
        for result in self._results.values():
            result.verify()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "schema": "folderhome.recipe-run-state.v1",
                "run_id": self._run_id,
                "recipe_id": self._recipe.recipe_id,
                "profile_id": self._profile_id,
                "status": self._status,
                "completed_step_refs": list(self._results),
                "pending_plan_id": self._pending.plan_id if self._pending else None,
                "cleanup_pending_count": len(self._cleanup_pending),
                "last_execution": deepcopy(self._last_execution),
            }

    def plan_next(
        self,
        *,
        endpoint_statuses: Mapping[str, str],
        known_resource_ids: frozenset[str],
    ) -> MasterAgentPlan:
        with self._lock:
            if self._status not in {"ready", "awaiting_approval"}:
                raise CapabilityRecipeError("Dieser Rezeptlauf kann keinen neuen Abschnitt planen.")
            self._verify_sources()
            endorsement = review_recipe(
                self._recipe,
                endpoint_statuses=endpoint_statuses,
                known_resource_ids=known_resource_ids,
            )
            if self._pending is not None:
                self._pending.verify_integrity()
                return deepcopy(self._pending)
            resolved = []
            lineage = []
            for step in self._recipe.steps[len(self._results) :]:
                bindings = [b for b in self._recipe.result_bindings if b.to_step == step.step_ref]
                if any(b.from_step not in self._results for b in bindings):
                    break
                request = deepcopy(step.request)
                for binding in bindings:
                    source = self._results[binding.from_step]
                    value = binding.select_value(source.report.domain_report)
                    request[binding.target_field] = value
                    lineage.append(
                        {
                            **binding.to_dict(),
                            "value": deepcopy(value),
                            "source_plan_id": source.plan_id,
                            "source_envelope_id": source.envelope.envelope_id,
                            "source_execution_id": source.report.execution_id,
                            "source_report_sha256": source.report_sha256,
                        }
                    )
                resolved.append(replace(step, request=request))
            if not resolved:
                raise CapabilityRecipeError("Kein vollständig aufgelöster Abschnitt verfügbar.")
            prepared_ids: list[str] = []
            self._status = "preparing"
            try:
                capabilities = {c.workflow_id: c for c in master_capability_catalog()}
                steps = []
                for sequence, step in enumerate(resolved, 1):
                    envelope = self._prepare(step.workflow_id, deepcopy(step.request))
                    prepared_ids.append(envelope.envelope_id)
                    capability = capabilities[step.workflow_id]
                    steps.append(
                        MasterPlanStep(
                            step_id=f"step_{sequence}_{step.step_ref}",
                            sequence=sequence,
                            workflow_id=step.workflow_id,
                            expert_id=step.expert_id,
                            goal=step.goal(language=self._language),
                            execution_mode=capability.execution_mode,
                            confirmation_required=bool(
                                capability.approval_gates or capability.side_effects
                            ),
                            approval_gates=capability.approval_gates,
                            side_effects=capability.side_effects,
                            boundaries=capability.boundaries,
                            cli_commands=capability.cli_commands,
                            execution_envelope=deepcopy(envelope),
                        )
                    )
                context = {
                    "schema": "folderhome.recipe-stage-context.v1",
                    "run_id": self._run_id,
                    "recipe_id": self._recipe.recipe_id,
                    "recipe_sha256": self._recipe_sha256,
                    "stage_number": len(self._stage_ids) + 1,
                    "previous_stage_ids": list(self._stage_ids),
                    "completed_step_refs": list(self._results),
                    "step_refs": [s.step_ref for s in resolved],
                    "resolved_request_hashes": [
                        {"step_ref": s.step_ref, "request_sha256": _digest(s.request)}
                        for s in resolved
                    ],
                    "result_bindings": lineage,
                    "endorsement": endorsement.to_dict(),
                }
                route = SemanticRouteReceipt(
                    role_id="folderhome_master",
                    expert_id=self._recipe.lead_expert_id,
                    workflow_ids=tuple(dict.fromkeys(s.workflow_id for s in resolved)),
                    persona_id=None,
                    resolution="explicit",
                    confidence="high",
                    why="Concrete section resolved from this run's verified execution reports.",
                )
                number = len(self._stage_ids) + 1
                summary = (
                    f"{self._recipe.title(language=self._language)}: Abschnitt {number}, "
                    "eigene Bestätigung erforderlich."
                    if self._language == "de"
                    else f"{self._recipe.title(language=self._language)}: section {number}, "
                    "separate confirmation required."
                )
                pending = MasterAgentPlan.create(
                    request_sha256=_digest(context),
                    profile_id=self._profile_id,
                    language=self._language,
                    summary=summary,
                    steps=tuple(steps),
                    route=route,
                    approval_context=context,
                )
                self._verify_sources()
            except Exception:
                try:
                    self._cleanup(tuple(prepared_ids))
                except CapabilityRecipeError:
                    self._status = "aborted"
                    raise
                self._status = "ready"
                raise CapabilityRecipeError(
                    "Rezeptabschnitt konnte nicht vorbereitet werden."
                ) from None
            self._pending = pending
            self._status = "awaiting_approval"
            return deepcopy(pending)

    def confirm(self, approval: MasterPlanApproval) -> dict[str, object]:
        with self._lock:
            if self._status != "awaiting_approval" or self._pending is None:
                raise CapabilityRecipeError("Kein offener Rezeptabschnitt für diese Freigabe.")
            plan = self._pending
            try:
                self._verify_sources()
                receipt = confirm_master_agent_plan(plan, approval)
                if set(approval.step_ids) != {s.step_id for s in plan.steps}:
                    raise CapabilityRecipeError("Alle Abschnittsschritte müssen bestätigt werden.")
                pairs = tuple(zip(plan.approval_context["step_refs"], plan.steps, strict=True))
            except (MasterAgentError, ValueError) as exc:
                raise CapabilityRecipeError(
                    "Freigabe passt nicht zum aktuellen Rezeptabschnitt."
                ) from exc
            self._pending = None
            self._status = "running"  # Consume before calling an adapter, including exceptions.
            self._stage_ids.append(plan.plan_id)
            outcomes = []
            reports = []
            failed = False
            for ref, step in pairs:
                if failed:
                    outcomes.append(
                        {"step_ref": ref, "status": "not_attempted", "execution_id": None}
                    )
                    continue
                try:
                    plan.verify_integrity()
                    self._verify_sources()
                    envelope = step.execution_envelope
                    if envelope is None:
                        raise CapabilityRecipeError("Rezeptschritt besitzt keine Ausführungshülle.")
                    report = deepcopy(self._execute(envelope.envelope_id, approval.approved_at))
                    report.verify_envelope(envelope)
                    evidence = _StepResult(
                        plan.plan_id, deepcopy(envelope), report, _digest(report.to_dict())
                    )
                    self._results[ref] = evidence
                    reports.append(report.to_dict())
                    outcomes.append(
                        {"step_ref": ref, "status": "executed", "execution_id": report.execution_id}
                    )
                except Exception:
                    failed = True
                    outcomes.append(
                        {
                            "step_ref": ref,
                            "status": "failed",
                            "execution_id": None,
                            "detail": "Ergebnis unklar; gestoppt, nicht automatisch wiederholen.",
                        }
                    )
            cleanup_incomplete = False
            try:
                self._cleanup(
                    tuple(
                        s.execution_envelope.envelope_id
                        for s in plan.steps
                        if s.execution_envelope is not None
                    )
                )
            except Exception:
                cleanup_incomplete = True
            self._status = (
                "aborted"
                if failed or cleanup_incomplete
                else "completed"
                if len(self._results) == len(self._recipe.steps)
                else "ready"
            )
            result = {
                "schema": "folderhome.recipe-stage-execution.v1",
                "run_id": self._run_id,
                "plan_id": plan.plan_id,
                "receipt": receipt.to_dict(),
                "status": "aborted" if failed or cleanup_incomplete else "executed",
                "run_status": self._status,
                "completed_step_refs": list(self._results),
                "outcomes": outcomes,
                "execution_reports": reports,
                "execution_outcome_unknown": failed,
                "cleanup_incomplete": cleanup_incomplete,
                "retry_safe": False,
            }
            self._last_execution = deepcopy(result)
            return result

    def close(self) -> None:
        with self._lock:
            if self._status in {"running", "preparing"}:
                raise CapabilityRecipeError(
                    "Ein laufender oder vorbereitender Abschnitt kann nicht geschlossen werden."
                )
            pending = self._pending
            self._pending = None
            self._status = "closed"
            if pending is not None:
                self._cleanup(
                    tuple(
                        s.execution_envelope.envelope_id
                        for s in pending.steps
                        if s.execution_envelope is not None
                    )
                )
            else:
                self._cleanup(())
