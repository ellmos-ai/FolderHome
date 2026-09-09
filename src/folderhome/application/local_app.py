"""Token-gated local API reusing existing read-only FolderHome services."""

from __future__ import annotations

import getpass
import hmac
import json
import os
import platform
import re
import secrets
import threading
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, quote, urlsplit

from folderhome.application.document_search import build_theme_dossier, search_documents
from folderhome.application.master_agent import MasterAgentError, confirm_master_agent_plan
from folderhome.application.profile_rules import ProfileConfiguration
from folderhome.application.recipes import (
    build_recipe_plan,
    execute_recipe_plan,
    load_bundled_recipe,
    load_bundled_recipes,
    review_recipe,
)
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionGateway,
    WorkflowExecutionOutcomeUnknown,
)
from folderhome.contracts.local_app import (
    LocalApiResponse,
    LocalAppSettings,
    OperatingSystemIdentity,
)
from folderhome.contracts.master_agent import MasterAgentPlan, MasterPlanApproval
from folderhome.contracts.recipes import CapabilityRecipeError, CapabilityRecipePlan
from folderhome.contracts.resources import ResourceRegistry
from folderhome.contracts.strands_agent import FolderHomeAgentReport, StrandsAgentSettings

_MAX_PROPOSED_AGENT_PLANS = 128
_MAX_RETAINED_EXECUTION_RESULTS = 128
_MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
_ARTIFACT_ROUTE = re.compile(
    r"/api/v1/agent/results/(workflow_execution_[0-9a-f]{64})/artifacts/(\d{1,4})"
)
_ARTIFACT_CONTENT_TYPES = {
    ".csv": "text/csv; charset=utf-8",
    ".ics": "text/calendar; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".zip": "application/zip",
}


def _result_limit(query: dict[str, list[str]], maximum: int) -> int:
    raw = query.get("limit", [])
    if not raw:
        return maximum
    try:
        limit = int(raw[0])
    except ValueError as exc:
        raise LocalAppError("limit muss eine ganze Zahl sein.") from exc
    if not 1 <= limit <= maximum:
        raise LocalAppError(f"limit muss zwischen 1 und {maximum} liegen.")
    return limit


def _declared_output_names(value: object, root: Path) -> list[str]:
    """Collect file names a public report declares, without reading any path."""

    names: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str):
                if (key == "name" or key.endswith("_name")) and Path(item).suffix:
                    names.append(item)
                elif key.endswith("basename") and not set(item) & set("*?[]"):
                    names.extend(path.name for path in root.glob(f"{item}.*"))
            else:
                names.extend(_declared_output_names(item, root))
    elif isinstance(value, list):
        for item in value:
            names.extend(_declared_output_names(item, root))
    return names


class LocalDocumentSearcher(Protocol):
    def search(self, query: str, *, limit: int = 20) -> tuple[object, ...]: ...


class LocalAppError(RuntimeError):
    """Raised when the local app boundary cannot be established safely."""


class LocalApplication:
    """Pure request dispatcher between local HTTP and existing app services."""

    def __init__(
        self,
        *,
        settings: LocalAppSettings,
        profiles: ProfileConfiguration,
        searcher: LocalDocumentSearcher,
        session_token: str | None = None,
        agent_settings: StrandsAgentSettings | None = None,
        workflow_executor: WorkflowExecutionGateway | None = None,
        resource_registry: ResourceRegistry | None = None,
        scheduler_controller=None,
    ) -> None:
        if profiles.os_account.strip() == "":
            raise LocalAppError("Profilkonfiguration besitzt kein OS-Konto-Label.")
        profile_ids = [item.profile_id for item in profiles.profiles]
        if not profile_ids or len(profile_ids) != len(set(profile_ids)):
            raise LocalAppError("Lokale App benötigt eindeutige organisatorische Profile.")
        token = session_token or secrets.token_urlsafe(32)
        if len(token) < 32:
            raise LocalAppError("Lokales Sitzungstoken ist zu kurz.")
        self.settings = settings
        self.profiles = profiles
        self.searcher = searcher
        self.agent_settings = agent_settings or StrandsAgentSettings(model_provider="fixture")
        self.workflow_executor = workflow_executor or WorkflowExecutionGateway()
        if resource_registry is not None:
            if resource_registry.os_account != profiles.os_account:
                raise LocalAppError(
                    "Ressourcenregister und Profilkonfiguration gehören nicht zum selben OS-Konto."
                )
            if resource_registry.known_profile_ids != frozenset(profile_ids):
                raise LocalAppError(
                    "Ressourcenregister und Profilkonfiguration besitzen andere Profile."
                )
        self.resource_registry = resource_registry
        self.scheduler_controller = scheduler_controller
        self.session_token = token
        self._token_sha256 = sha256(token.encode("utf-8")).hexdigest()
        self._identity = capture_os_identity()
        self._profile_ids = frozenset(profile_ids)
        self._proposed_agent_plans: dict[str, MasterAgentPlan] = {}
        self._recipe_plans: dict[str, CapabilityRecipePlan] = {}
        # Object identity is a process-local preparation lease: two equal hashes
        # from different tool calls must not release each other's references.
        self._pending_recipe_plans: dict[int, CapabilityRecipePlan] = {}
        self._pending_agent_plans: dict[int, MasterAgentPlan] = {}
        self._started_recipe_plans: set[str] = set()
        self._agent_plan_lock = threading.RLock()
        self._agent_conversation_messages: dict[
            str, tuple[dict[str, Any], ...]
        ] = {profile_id: () for profile_id in profile_ids}
        self._agent_conversation_turns = {profile_id: 0 for profile_id in profile_ids}
        self._agent_conversation_locks = {
            profile_id: threading.RLock() for profile_id in profile_ids
        }
        self._execution_results: dict[str, dict[str, object]] = {}
        self._execution_artifacts: dict[str, tuple[Path, ...]] = {}
        self._execution_results_lock = threading.RLock()
        self._successful_live_model_turns = 0
        self._model_status_lock = threading.RLock()
        self._asset_root = Path(__file__).parents[1] / "web_ui"

    def close(self) -> None:
        """Stop only background work owned by this application instance."""
        if self.scheduler_controller is not None:
            self.scheduler_controller.close()

    def plan(self) -> dict[str, object]:
        return {
            "schema": "folderhome.local-app-plan.v1",
            "settings": self.settings.to_dict(),
            "os_identity": self._identity.to_public_dict(),
            "profile_account_label": self.profiles.os_account,
            "profile_ids": sorted(self._profile_ids),
            "security_boundary": "operating_system_account",
            "profiles_are_authorization_boundaries": False,
            "session_token_generated": True,
            "session_token_disclosed_in_plan": False,
            "shell_execution_available": False,
            "request_paths_allowed": False,
            "cors_enabled": False,
            "external_resources": False,
            "logical_resources_configured": self.resource_registry is not None,
            "agent": {
                "role": "folderhome_master",
                "model_provider": self.agent_settings.model_provider,
                "routing_policy": "semantic_model_selection",
                "executor_coverage": _executor_coverage(self.workflow_executor),
                "model_connection": self._model_connection_payload(),
            },
            "server_started": False,
        }

    def executor_catalog_payload(self) -> dict[str, object]:
        """Return the same exact runtime coverage used by HTTP and CLI clients."""

        return {
            "schema": "folderhome.local-agent-executor-catalog.v1",
            "coverage": _executor_coverage(self.workflow_executor),
            "workflows": [
                item.to_dict() for item in self.workflow_executor.catalog()
            ],
        }

    def resource_catalog_payload(self, profile_id: str) -> dict[str, object]:
        """Return model-safe logical resource metadata for one profile."""

        if profile_id not in self._profile_ids:
            raise LocalAppError("Unbekanntes organisatorisches Profil.")
        if self.resource_registry is None:
            return {
                "schema": "folderhome.logical-resource-catalog.v1",
                "profile_id": profile_id,
                "security_boundary": "operating_system_account",
                "profiles_are_authorization_boundaries": False,
                "paths_disclosed": False,
                "resources": [],
                "defaults": {},
                "configured": False,
            }
        payload = self.resource_registry.to_public_dict(profile_id=profile_id)
        payload["configured"] = True
        return payload

    def _recipe_context(self, profile_id: str, language: str):
        if profile_id not in self._profile_ids or language not in {"en", "de"}:
            raise LocalAppError("Rezept benötigt ein bekanntes Profil und Sprache en/de.")
        resources = frozenset(
            item.resource_id for item in self.resource_registry.resources
            if profile_id in item.profile_ids
        ) if self.resource_registry else frozenset()
        statuses = {item.workflow_id: item.status for item in self.workflow_executor.catalog()}
        return resources, statuses

    def recipe_catalog_payload(self, *, profile_id: str, language: str) -> dict[str, object]:
        """Describe packaged journeys without preparing or executing an adapter."""

        resource_ids, statuses = self._recipe_context(profile_id, language)
        entries = []
        for recipe in load_bundled_recipes():
            reason = None
            try:
                review_recipe(recipe, endpoint_statuses=statuses, known_resource_ids=resource_ids)
            except CapabilityRecipeError as exc:
                reason = str(exc)
            entries.append({
                "recipe_id": recipe.recipe_id,
                "title": recipe.title(language=language),
                "summary": recipe.summary(language=language),
                "workflow_ids": list(recipe.workflow_ids),
                "available": reason is None,
                "unavailable_reason": reason,
            })
        return {
            "schema": "folderhome.local-recipe-catalog.v1", "profile_id": profile_id,
            "recipes": entries, "paths_disclosed": False, "execution_performed": False,
        }

    def _retain_agent_plan(
        self, plan: MasterAgentPlan, *, pending_envelopes: tuple[str, ...] = (),
    ) -> None:
        """Retain plans and recipe metadata under the same bounded session budget."""

        with self._agent_plan_lock:
            self._pending_recipe_plans.pop(id(plan), None)
            self._pending_agent_plans.pop(id(plan), None)
            oldest = None
            if (
                plan.plan_id not in self._proposed_agent_plans
                and len(self._proposed_agent_plans) >= _MAX_PROPOSED_AGENT_PLANS
            ):
                oldest_id = next(iter(self._proposed_agent_plans))
                oldest = self._proposed_agent_plans.pop(oldest_id)
                self._recipe_plans.pop(oldest_id, None)
            self._proposed_agent_plans[plan.plan_id] = plan
            if oldest is not None:
                self._discard_unreferenced_envelopes(
                    _plan_envelope_ids((oldest,)), protected=pending_envelopes,
                )

    def _discard_unreferenced_envelopes(
        self, envelope_ids: tuple[str, ...], *, protected: tuple[str, ...] = (),
    ) -> None:
        pending = tuple(self._pending_agent_plans.values())
        retained = set(_plan_envelope_ids(
            tuple(self._proposed_agent_plans.values()) + pending
        )) | set(protected)
        self.workflow_executor.discard_unexecuted(tuple(
            item for item in envelope_ids if item not in retained
        ))

    def discard_recipe_preparations(self, recipes: tuple[CapabilityRecipePlan, ...]) -> None:
        """Release unretained recipe preparations when a model turn fails."""

        self.discard_agent_preparations(tuple(item.plan for item in recipes))

    def protect_agent_preparation(self, plan: MasterAgentPlan) -> None:
        """Protect every in-flight plan, including an ordinary specialist proposal."""

        with self._agent_plan_lock:
            if (
                id(plan) not in self._pending_agent_plans
                and len(self._pending_agent_plans) >= _MAX_PROPOSED_AGENT_PLANS
            ):
                self._discard_unreferenced_envelopes(_plan_envelope_ids((plan,)))
                raise LocalAppError("Budget für laufende Planvorbereitungen ist belegt.")
            self._pending_agent_plans[id(plan)] = plan

    def discard_agent_preparations(self, plans: tuple[MasterAgentPlan, ...]) -> None:
        with self._agent_plan_lock:
            for plan in plans:
                self._pending_recipe_plans.pop(id(plan), None)
                self._pending_agent_plans.pop(id(plan), None)
            self._discard_unreferenced_envelopes(_plan_envelope_ids(plans))

    def propose_recipe(
        self, *, profile_id: str, recipe_id: str, language: str,
    ) -> CapabilityRecipePlan:
        """Prepare and retain a journey under the same lock as conversation reset."""

        self._recipe_context(profile_id, language)
        with self._agent_conversation_locks[profile_id], self._agent_plan_lock:
            result = self.prepare_recipe(
                profile_id=profile_id, recipe_id=recipe_id, language=language,
            )
            self._retain_agent_plan(result.plan)
            self._recipe_plans[result.plan_id] = result
            return result

    def prepare_recipe(
        self, *, profile_id: str, recipe_id: str, language: str,
    ) -> CapabilityRecipePlan:
        """Prepare only; a Strands tool thread must not acquire its caller's conversation lock."""

        resource_ids, statuses = self._recipe_context(profile_id, language)
        recipe = load_bundled_recipe(recipe_id)
        prepared_ids = []

        def prepare(workflow_id, request):
            try:
                envelope = self.workflow_executor.prepare(
                    workflow_id=workflow_id, profile_id=profile_id, request=request,
                )
            except Exception as exc:
                raise WorkflowExecutionError(
                    f"Rezeptschritt {workflow_id} konnte nicht vorbereitet werden. "
                    "Konfiguration und lokale Daten prüfen."
                ) from exc
            prepared_ids.append(envelope.envelope_id)
            return envelope

        with self._agent_plan_lock:
            if len(self._started_recipe_plans) >= _MAX_PROPOSED_AGENT_PLANS:
                raise LocalAppError("Rezeptbudget ist belegt; neue App-Sitzung erforderlich.")
            if len(self._pending_recipe_plans) >= _MAX_PROPOSED_AGENT_PLANS:
                raise LocalAppError("Budget für laufende Rezeptvorbereitungen ist belegt.")
            try:
                result = build_recipe_plan(
                    recipe, profile_id=profile_id, language=language, prepare=prepare,
                    endpoint_statuses=statuses, known_resource_ids=resource_ids,
                )
                if result.plan_id in self._started_recipe_plans:
                    raise LocalAppError("Dieser Rezeptplan wurde bereits gestartet.")
                self.protect_agent_preparation(result.plan)
            except BaseException:
                self._discard_unreferenced_envelopes(tuple(prepared_ids))
                raise
            self._pending_recipe_plans[id(result.plan)] = result
            return result

    def run_agent_chat(
        self,
        *,
        profile_id: str,
        message: str,
    ) -> FolderHomeAgentReport:
        """Run one bounded master-agent turn without treating chat as approval."""

        request = self._validated_agent_chat(profile_id=profile_id, message=message)
        from folderhome.application.strands_agent import run_folderhome_agent_turn

        with self._agent_conversation_locks[request["profile_id"]]:
            report, retained_messages = run_folderhome_agent_turn(
                application=self,
                prompt=request["message"],
                profile_id=request["profile_id"],
                settings=self.agent_settings,
                prior_messages=self._agent_conversation_messages[request["profile_id"]],
            )
            if self.agent_settings.is_live_model:
                with self._model_status_lock:
                    self._successful_live_model_turns += 1
            self._agent_conversation_messages[request["profile_id"]] = retained_messages
            self._agent_conversation_turns[request["profile_id"]] += 1
            with self._agent_plan_lock:
                pending_envelopes = _plan_envelope_ids(report.proposed_plans)
                for plan in report.proposed_plans:
                    self._retain_agent_plan(plan, pending_envelopes=pending_envelopes)
                for recipe_plan in report.proposed_recipes:
                    if recipe_plan.plan_id in self._proposed_agent_plans:
                        self._recipe_plans[recipe_plan.plan_id] = recipe_plan
                self._discard_unreferenced_envelopes(pending_envelopes)
        return report

    def agent_conversation_payload(self, profile_id: str) -> dict[str, object]:
        """Describe bounded process-local context without exposing message content."""

        if profile_id not in self._profile_ids:
            raise LocalAppError("Unbekanntes organisatorisches Profil.")
        with self._agent_conversation_locks[profile_id]:
            conversation_digest = sha256(
                f"{self._token_sha256}:{profile_id}".encode()
            ).hexdigest()[:24]
            return {
                "schema": "folderhome.agent-conversation-state.v1",
                "conversation_id": f"conversation_{conversation_digest}",
                "profile_id": profile_id,
                "turn": self._agent_conversation_turns[profile_id],
                "retained_messages": len(self._agent_conversation_messages[profile_id]),
                "max_messages": self.agent_settings.max_conversation_messages,
                "persistence": "process_memory_only",
                "profiles_are_authorization_boundaries": False,
            }

    def reset_agent_conversation(self, profile_id: str) -> dict[str, object]:
        """Clear one profile's process-local messages and unconfirmed plans."""

        if profile_id not in self._profile_ids:
            raise LocalAppError("Unbekanntes organisatorisches Profil.")
        with self._agent_conversation_locks[profile_id]:
            self._agent_conversation_messages[profile_id] = ()
            self._agent_conversation_turns[profile_id] = 0
            with self._agent_plan_lock:
                discarded = tuple(
                    plan_id
                    for plan_id, plan in self._proposed_agent_plans.items()
                    if plan.profile_id == profile_id
                )
                discarded_plans = tuple(
                    self._proposed_agent_plans[plan_id] for plan_id in discarded
                )
                pending = tuple(
                    plan for plan in self._pending_agent_plans.values()
                    if plan.profile_id == profile_id
                )
                for plan in pending:
                    self._pending_agent_plans.pop(id(plan), None)
                    self._pending_recipe_plans.pop(id(plan), None)
                for plan_id in discarded:
                    del self._proposed_agent_plans[plan_id]
                    self._recipe_plans.pop(plan_id, None)
                self._discard_unreferenced_envelopes(
                    _plan_envelope_ids(discarded_plans + pending)
                )
            return {
                "schema": "folderhome.local-agent-conversation-reset-response.v1",
                "conversation": self.agent_conversation_payload(profile_id),
                "discarded_plan_ids": list(dict.fromkeys(
                    (*discarded, *(plan.plan_id for plan in pending))
                )),
                "side_effects": ["memory.agent_conversation.clear"],
            }

    def proposed_agent_plan(self, plan_id: str) -> MasterAgentPlan | None:
        """Return one immutable plan retained in this local process session."""

        with self._agent_plan_lock:
            return self._proposed_agent_plans.get(plan_id)

    def confirm_agent_plan(
        self,
        *,
        plan_id: str,
        plan_sha256: str,
        step_ids: tuple[str, ...],
    ) -> dict[str, object]:
        """Confirm and, where connected, execute one exact retained plan."""

        request = self._agent_confirmation_request(
            {
                "schema": "folderhome.local-agent-confirmation-request.v1",
                "plan_id": plan_id,
                "plan_sha256": plan_sha256,
                "step_ids": list(step_ids),
            }
        )
        with self._agent_plan_lock:
            plan = self._proposed_agent_plans.get(request["plan_id"])
            recipe_plan = self._recipe_plans.get(request["plan_id"])
        if plan is None:
            raise LocalAppError("Plan ist in dieser lokalen Sitzung nicht bekannt.")
        if recipe_plan is not None:
            return self._confirm_recipe_plan(recipe_plan, request)
        approved_at = datetime.now(UTC).isoformat()
        try:
            receipt = confirm_master_agent_plan(
                plan,
                MasterPlanApproval(
                    approval_id=f"approval_{secrets.token_hex(10)}",
                    plan_id=request["plan_id"],
                    plan_sha256=request["plan_sha256"],
                    step_ids=request["step_ids"],
                    approved_at=approved_at,
                ),
            )
        except (MasterAgentError, ValueError) as exc:
            raise LocalAppError(str(exc)) from exc
        approved_step_ids = set(receipt.approved_step_ids)
        execution_reports = []
        unknown_outcome = None
        try:
            for step in plan.steps:
                if step.step_id not in approved_step_ids or step.execution_envelope is None:
                    continue
                try:
                    plan.verify_integrity()
                except ValueError as exc:
                    raise LocalAppError(str(exc)) from exc
                report = self.workflow_executor.execute(
                    envelope_id=step.execution_envelope.envelope_id,
                    approved_at=approved_at,
                )
                try:
                    report.verify_envelope(step.execution_envelope)
                except ValueError as exc:
                    raise LocalAppError(str(exc)) from exc
                execution_reports.append(report)
        except WorkflowExecutionOutcomeUnknown as exc:
            unknown_outcome = exc
            raise
        finally:
            # A rejected later step must not erase evidence of an earlier real effect.
            try:
                self._retain_execution_results(
                    profile_id=plan.profile_id,
                    plan_id=plan.plan_id,
                    reports=execution_reports,
                    executed_at=approved_at,
                )
            except Exception:
                # Secondary evidence failure must not hide a possibly committed effect.
                if unknown_outcome is not None:
                    raise unknown_outcome from None
                raise
        return {
            "schema": "folderhome.local-agent-confirmation-response.v1",
            "receipt": receipt.to_dict(),
            "execution_reports": [item.to_dict() for item in execution_reports],
            "execution_performed": bool(execution_reports),
            "side_effects": list(
                dict.fromkeys(
                    effect
                    for report in execution_reports
                    for effect in report.side_effects
                )
            ),
        }

    def _confirm_recipe_plan(self, recipe_plan, request) -> dict[str, object]:
        plan = recipe_plan.plan
        with self._agent_conversation_locks[plan.profile_id], self._agent_plan_lock:
            if self._recipe_plans.get(plan.plan_id) is not recipe_plan:
                raise LocalAppError("Rezeptplan ist nicht mehr in dieser Sitzung vorhanden.")
            if plan.plan_id in self._started_recipe_plans:
                raise LocalAppError("Dieser Rezeptplan wurde bereits gestartet.")
            if set(request["step_ids"]) != {step.step_id for step in plan.steps}:
                raise LocalAppError("Ein Rezept benötigt die Bestätigung aller Schritte.")
            approved_at = datetime.now(UTC).isoformat()
            try:
                recipe_plan.verify_integrity()
                receipt = confirm_master_agent_plan(plan, MasterPlanApproval(
                    approval_id=f"approval_{secrets.token_hex(10)}",
                    plan_id=request["plan_id"], plan_sha256=request["plan_sha256"],
                    step_ids=request["step_ids"], approved_at=approved_at,
                ))
            except (MasterAgentError, ValueError) as exc:
                raise LocalAppError(str(exc)) from exc
            self._started_recipe_plans.add(plan.plan_id)
            reports = []
            delivery_incomplete = False
            execution_outcome_unknown = False
            envelopes = {
                step.execution_envelope.envelope_id: step.execution_envelope
                for step in plan.steps if step.execution_envelope is not None
            }

            def execute(envelope_id, timestamp):
                nonlocal delivery_incomplete, execution_outcome_unknown
                try:
                    report = self.workflow_executor.execute(
                        envelope_id=envelope_id, approved_at=timestamp,
                    )
                except Exception as exc:
                    # Adapter messages may contain private filesystem paths or mailbox data.
                    if isinstance(exc, WorkflowExecutionOutcomeUnknown):
                        execution_outcome_unknown = True
                        delivery_incomplete = True
                        raise WorkflowExecutionOutcomeUnknown(
                            "Ergebnis unklar; eine Wirkung ist möglich. "
                            "Nicht automatisch wiederholen."
                        ) from exc
                    raise WorkflowExecutionError(
                        "Rezeptschritt gescheitert; keine weiteren Schritte gestartet."
                    ) from exc
                try:
                    report.verify_envelope(envelopes[envelope_id])
                except ValueError as exc:
                    execution_outcome_unknown = True
                    delivery_incomplete = True
                    raise WorkflowExecutionError(str(exc)) from exc
                reports.append(report)
                try:
                    self._retain_execution_results(
                        profile_id=plan.profile_id, plan_id=plan.plan_id,
                        reports=[report], executed_at=approved_at,
                    )
                except OSError:
                    delivery_incomplete = True
                return report

            result = execute_recipe_plan(recipe_plan, execute=execute, approved_at=approved_at)
            # Do not leave failed or unattempted envelopes available for later execution.
            self.workflow_executor.discard_unexecuted(_plan_envelope_ids((plan,)))
            invalidated_ids = []
            used_ids = set(_plan_envelope_ids((plan,)))
            for other_id, other_plan in tuple(self._proposed_agent_plans.items()):
                if other_id != plan.plan_id and used_ids.intersection(
                    _plan_envelope_ids((other_plan,))
                ):
                    del self._proposed_agent_plans[other_id]
                    self._recipe_plans.pop(other_id, None)
                    invalidated_ids.append(other_id)
            return {
                "schema": "folderhome.local-agent-confirmation-response.v1",
                "receipt": receipt.to_dict(), "recipe_execution": result.to_dict(),
                "execution_reports": [item.to_dict() for item in reports],
                "execution_performed": bool(reports),
                "result_delivery_incomplete": delivery_incomplete,
                "execution_outcome_unknown": execution_outcome_unknown,
                "invalidated_plan_ids": invalidated_ids,
                "side_effects": list(dict.fromkeys(
                    effect for report in reports for effect in report.side_effects
                )),
            }

    def _retain_execution_results(
        self,
        *,
        profile_id: str,
        plan_id: str,
        reports: list[object],
        executed_at: str,
    ) -> None:
        """Keep a bounded record of what really ran so a GUI can fetch it later."""

        with self._execution_results_lock:
            for report in reports:
                artifacts = self._artifact_paths(
                    profile_id=profile_id,
                    domain_report=report.domain_report,
                )
                self._execution_results[report.execution_id] = {
                    "execution_id": report.execution_id,
                    "plan_id": plan_id,
                    "profile_id": profile_id,
                    "workflow_id": report.workflow_id,
                    "adapter_id": report.adapter_id,
                    "status": report.status,
                    "executed_at": executed_at,
                    "side_effects": list(report.side_effects),
                    "artifacts": [
                        {
                            "index": index,
                            "name": item.name,
                            "size_bytes": item.stat().st_size,
                            "sha256": sha256(item.read_bytes()).hexdigest(),
                        }
                        for index, item in enumerate(artifacts)
                    ],
                }
                self._execution_artifacts[report.execution_id] = artifacts
            while len(self._execution_results) > _MAX_RETAINED_EXECUTION_RESULTS:
                oldest = next(iter(self._execution_results))
                self._execution_results.pop(oldest)
                self._execution_artifacts.pop(oldest, None)

    def _artifact_paths(
        self,
        *,
        profile_id: str,
        domain_report: dict[str, object],
    ) -> tuple[Path, ...]:
        """Resolve names the report declares inside this profile's output areas."""

        if self.resource_registry is None:
            return ()
        found: list[Path] = []
        for resource in self.resource_registry.resources:
            if "create" not in resource.operations:
                continue
            if profile_id not in resource.profile_ids:
                continue
            root = resource.local_path
            if not root.is_dir():
                continue
            for name in _declared_output_names(domain_report, root):
                candidate = root / name
                if (
                    candidate.parent == root
                    and not candidate.is_symlink()
                    and candidate.is_file()
                    and candidate not in found
                ):
                    found.append(candidate)
        return tuple(found)

    def execution_results_payload(
        self,
        *,
        profile_id: str,
        limit: int,
    ) -> dict[str, object]:
        """List what this process executed for one profile, newest first."""

        if profile_id not in self._profile_ids:
            raise LocalAppError("Unbekanntes organisatorisches Profil.")
        with self._execution_results_lock:
            results = [
                dict(item)
                for item in self._execution_results.values()
                if item["profile_id"] == profile_id
            ]
        results.reverse()
        return {
            "schema": "folderhome.local-agent-result-list.v1",
            "profile_id": profile_id,
            "security_boundary": "operating_system_account",
            "paths_disclosed": False,
            "results": results[:limit],
            "side_effects": [],
        }

    def _artifact_response(self, execution_id: str, index: int) -> LocalApiResponse:
        with self._execution_results_lock:
            artifacts = self._execution_artifacts.get(execution_id, ())
        if index >= len(artifacts):
            return self._error(404, "Ergebnisdatei ist in dieser Sitzung nicht bekannt.")
        target = artifacts[index]
        expected = str(
            self._execution_results[execution_id]["artifacts"][index]["sha256"]
        )
        try:
            if target.is_symlink() or not target.is_file():
                return self._error(404, "Ergebnisdatei existiert nicht mehr.")
            if target.stat().st_size > _MAX_ARTIFACT_BYTES:
                return self._error(413, "Ergebnisdatei überschreitet die Download-Grenze.")
            content = target.read_bytes()
        except OSError:
            return self._error(404, "Ergebnisdatei ist nicht mehr lesbar.")
        if sha256(content).hexdigest() != expected:
            return self._error(409, "Ergebnisdatei wurde seit der Ausführung verändert.")
        headers = self._security_headers()
        headers["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(target.name, safe='')}"
        )
        return LocalApiResponse(
            status_code=200,
            content_type=_ARTIFACT_CONTENT_TYPES.get(
                target.suffix.casefold(),
                "application/octet-stream",
            ),
            content=content,
            headers=headers,
        )

    def handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        try:
            return self._handle(
                method=method.upper(),
                target=target,
                headers={key.casefold(): value for key, value in headers.items()},
                body=body,
                server_port=server_port,
            )
        except _HttpError as exc:
            return self._error(exc.status_code, str(exc))
        except LocalAppError as exc:
            return self._error(400, str(exc))
        except WorkflowExecutionOutcomeUnknown:
            return self._json_response(
                {
                    "schema": "folderhome.local-api-error.v1",
                    "status": "uncertain",
                    "status_code": 409,
                    "message": (
                        "Ergebnis unklar; eine Wirkung ist möglich. "
                        "Privaten Nachweis prüfen, nicht automatisch wiederholen."
                    ),
                    "execution_outcome_unknown": True,
                    "retry_safe": False,
                },
                status_code=409,
            )
        except WorkflowExecutionError as exc:
            return self._error(409, str(exc))
        except ValueError as exc:
            return self._error(422, f"Lokaler Dienst konnte die Anfrage nicht ausführen: {exc}")
        except OSError:
            return self._error(503, "Lokale Datenquelle ist derzeit nicht verfügbar.")
        except RuntimeError:
            return self._error(503, "Lokaler Dokumentdienst ist derzeit nicht verfügbar.")

    def _handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        if capture_os_identity().identity_sha256 != self._identity.identity_sha256:
            return self._error(403, "Betriebssystemidentität des Prozesses hat sich geändert.")
        expected_host = f"{self.settings.host}:{server_port}"
        if headers.get("host") != expected_host:
            return self._error(403, "HTTP-Host stimmt nicht mit der Loopback-Bindung überein.")
        expected_origin = f"http://{expected_host}"
        origin = headers.get("origin")
        if origin is not None and origin != expected_origin:
            return self._error(403, "Browser-Origin liegt außerhalb der lokalen App.")
        parsed = urlsplit(target)
        is_api = parsed.path.startswith("/api/")
        supplied_token = headers.get("x-folderhome-token", "") if is_api else (
            parse_qs(parsed.query).get("token", [""])[0]
        )
        if not hmac.compare_digest(supplied_token, self.session_token):
            return self._error(401, "Lokales Sitzungstoken fehlt oder ist ungültig.")

        if method == "GET" and parsed.path == "/":
            return self._asset_response(
                "index.html",
                "text/html; charset=utf-8",
                replacements={"__FOLDERHOME_TOKEN__": quote(self.session_token, safe="")},
            )
        if method == "GET" and parsed.path == "/assets/app.css":
            return self._asset_response("app.css", "text/css; charset=utf-8")
        if method == "GET" and parsed.path == "/assets/app.js":
            return self._asset_response("app.js", "text/javascript; charset=utf-8")
        if method == "GET" and parsed.path == "/assets/favicon.svg":
            return self._asset_response("favicon.svg", "image/svg+xml; charset=utf-8")
        if parsed.path in {
            "/",
            "/assets/app.css",
            "/assets/app.js",
            "/assets/favicon.svg",
        }:
            return self._error(405, "Methode ist für diese lokale Ressource nicht erlaubt.")

        if parsed.path in {
            "/api/v1/scheduler/status", "/api/v1/scheduler/preview",
            "/api/v1/scheduler/start", "/api/v1/scheduler/stop",
        }:
            return self._scheduler_response(method, parsed, headers, body)
        if method == "GET" and parsed.path == "/api/v1/status":
            return self._json_response(self._status_payload(server_port))
        if method == "GET" and parsed.path == "/api/v1/profiles":
            return self._json_response(self._profiles_payload())
        if method == "GET" and parsed.path == "/api/v1/capabilities":
            return self._json_response(self._capabilities_payload())
        if method == "GET" and parsed.path == "/api/v1/agent/executors":
            return self._json_response(self.executor_catalog_payload())
        if method == "GET" and parsed.path == "/api/v1/agent/recipes":
            query = parse_qs(parsed.query, keep_blank_values=True)
            if (
                set(query).difference({"profile_id", "language"})
                or len(query.get("profile_id", [])) != 1
                or len(query.get("language", ["en"])) != 1
            ):
                raise LocalAppError("Rezeptkatalog benötigt genau ein Profil und eine Sprache.")
            return self._json_response(self.recipe_catalog_payload(
                profile_id=query["profile_id"][0], language=query.get("language", ["en"])[0],
            ))
        if method == "GET" and parsed.path == "/api/v1/agent/results":
            query = parse_qs(parsed.query)
            profile_ids = query.get("profile_id", [])
            if len(profile_ids) != 1 or not profile_ids[0].strip():
                raise LocalAppError("Ergebnisliste benötigt genau eine profile_id.")
            return self._json_response(
                self.execution_results_payload(
                    profile_id=profile_ids[0],
                    limit=_result_limit(query, self.settings.max_query_limit),
                )
            )
        artifact = _ARTIFACT_ROUTE.fullmatch(parsed.path)
        if artifact is not None:
            if method != "GET":
                return self._error(405, "Ergebnisdateien sind nur per GET abrufbar.")
            return self._artifact_response(artifact.group(1), int(artifact.group(2)))
        if method == "GET" and parsed.path == "/api/v1/resources":
            profile_ids = parse_qs(parsed.query).get("profile_id", [])
            if len(profile_ids) != 1 or not profile_ids[0].strip():
                raise LocalAppError("Ressourcenkatalog benötigt genau eine profile_id.")
            return self._json_response(self.resource_catalog_payload(profile_ids[0]))
        if parsed.path in {
            "/api/v1/status",
            "/api/v1/profiles",
            "/api/v1/capabilities",
            "/api/v1/agent/executors",
            "/api/v1/agent/recipes",
            "/api/v1/agent/results",
            "/api/v1/resources",
        }:
            return self._error(405, "API-Endpunkt ist ausschließlich read-only per GET verfügbar.")
        if method == "POST" and parsed.path == "/api/v1/documents/search":
            payload = self._json_request(headers, body)
            request = self._search_request(payload)
            result = search_documents(
                request["query"],
                searcher=self.searcher,
                limit=request["limit"],
            )
            return self._json_response(
                {
                    "schema": "folderhome.local-search-response.v1",
                    "profile_id": request["profile_id"],
                    "organizational_context_only": True,
                    "result": result.to_dict(),
                    "side_effects": [],
                }
            )
        if method == "POST" and parsed.path == "/api/v1/documents/dossier":
            payload = self._json_request(headers, body)
            request = self._dossier_request(payload)
            result = build_theme_dossier(
                request["topic"],
                searcher=self.searcher,
                limit=request["limit"],
            )
            return self._json_response(
                {
                    "schema": "folderhome.local-dossier-response.v1",
                    "profile_id": request["profile_id"],
                    "organizational_context_only": True,
                    "result": result.to_dict(),
                    "side_effects": [],
                }
            )
        if method == "POST" and parsed.path == "/api/v1/agent/chat":
            payload = self._json_request(headers, body)
            request = self._agent_chat_request(payload)
            report = self.run_agent_chat(
                profile_id=request["profile_id"],
                message=request["message"],
            )
            return self._json_response(
                {
                    "schema": "folderhome.local-agent-chat-response.v1",
                    "profile_id": request["profile_id"],
                    "organizational_context_only": True,
                    "profiles_are_authorization_boundaries": False,
                    "agent": report.to_dict(),
                    "conversation": self.agent_conversation_payload(request["profile_id"]),
                    "side_effects": [],
                }
            )
        if method == "POST" and parsed.path == "/api/v1/agent/recipes/plan":
            payload = self._json_request(headers, body)
            if (
                set(payload) != {"schema", "profile_id", "recipe_id", "language"}
                or payload.get("schema") != "folderhome.local-recipe-plan-request.v1"
                or not all(isinstance(payload[key], str) for key in payload)
            ):
                raise LocalAppError("Rezeptanfrage besitzt unbekannte oder ungültige Felder.")
            return self._json_response(self.propose_recipe(
                profile_id=payload["profile_id"], recipe_id=payload["recipe_id"],
                language=payload["language"],
            ).to_dict())
        if method == "POST" and parsed.path == "/api/v1/agent/conversation/reset":
            payload = self._json_request(headers, body)
            profile_id = self._agent_conversation_reset_request(payload)
            return self._json_response(self.reset_agent_conversation(profile_id))
        if method == "POST" and parsed.path == "/api/v1/agent/confirm":
            payload = self._json_request(headers, body)
            request = self._agent_confirmation_request(payload)
            return self._json_response(
                self.confirm_agent_plan(
                    plan_id=request["plan_id"],
                    plan_sha256=request["plan_sha256"],
                    step_ids=request["step_ids"],
                )
            )
        if parsed.path in {
            "/api/v1/documents/search",
            "/api/v1/documents/dossier",
            "/api/v1/agent/chat",
            "/api/v1/agent/recipes/plan",
            "/api/v1/agent/confirm",
            "/api/v1/agent/conversation/reset",
        }:
            return self._error(405, "Lokaler Dienst benötigt eine POST-JSON-Anfrage.")
        return self._error(404, "Unbekannter lokaler Endpunkt.")

    def _scheduler_response(self, method, parsed, headers, body):
        action = parsed.path.rsplit("/", 1)[-1]
        if method != ("GET" if action == "status" else "POST"):
            return self._error(405, "Methode für diese Scheduler-Aktion nicht erlaubt.")
        if self.scheduler_controller is None:
            return self._error(503, "Scheduler-Steuerung ist in dieser App nicht eingerichtet.")
        if action == "status":
            query = parse_qs(parsed.query, keep_blank_values=True)
            if set(query) != {"profile_id"} or len(query["profile_id"]) != 1:
                raise LocalAppError("Scheduler-Status benötigt genau ein Profil.")
            payload = {"profile_id": query["profile_id"][0]}
        else:
            if parsed.query:
                raise LocalAppError("Scheduler-Aktionen akzeptieren keine Query-Parameter.")
            payload = self._json_request(headers, body)
            fields = {"schema", "profile_id"}
            if action == "start":
                fields.update({"plan_id", "plan_sha256"})
            elif action == "stop":
                fields.add("worker_id")
            if (
                set(payload) != fields
                or payload.get("schema") != f"folderhome.scheduler-consumer-{action}-request.v1"
                or not all(isinstance(value, str) for value in payload.values())
            ):
                raise LocalAppError("Scheduler-Anfrage besitzt ungültige Felder.")
            for key, pattern in {
                "plan_id": r"consumer_start_[0-9a-f]{32}",
                "plan_sha256": r"[0-9a-f]{64}",
                "worker_id": r"consumer_worker_[0-9a-f]{32}",
            }.items():
                if key in payload and re.fullmatch(pattern, payload[key]) is None:
                    raise LocalAppError("Scheduler-Bestätigung besitzt ungültige Kennungen.")
        profile_id = payload["profile_id"]
        if profile_id not in self._profile_ids:
            raise LocalAppError("Scheduler-Anfrage nennt kein bekanntes Profil.")
        control = self.scheduler_controller
        try:
            if action == "status":
                result = control.status(profile_id=profile_id)
            elif action == "preview":
                result = control.preview_configured(profile_id=profile_id)
            elif action == "start":
                result = control.start(profile_id=profile_id, plan_id=payload["plan_id"],
                                       plan_sha256=payload["plan_sha256"])
            else:
                result = control.stop(profile_id=profile_id, worker_id=payload["worker_id"])
        except (ValueError, WorkflowExecutionError):
            return self._error(409, "Scheduler-Konfiguration oder Bestätigung nicht mehr gültig.")
        except (OSError, RuntimeError):
            return self._error(503, "Scheduler-Dienst ist derzeit nicht verfügbar.")
        return self._json_response(result)

    def _status_payload(self, server_port: int) -> dict[str, object]:
        return {
            "schema": "folderhome.local-app-status.v1",
            "status": "ready",
            "base_url": f"http://{self.settings.host}:{server_port}",
            "network_scope": "loopback_only",
            "security_boundary": "operating_system_account",
            "profiles_are_authorization_boundaries": False,
            "profile_account_label": self.profiles.os_account,
            "process_identity": self._identity.to_public_dict(),
            "session_token_sha256": self._token_sha256,
            "session_token_disclosed": False,
            "read_only_api": False,
            "chat_is_approval": False,
            "approval_bound_execution": True,
            "conversation_memory": "process_only",
            "model_connection": self._model_connection_payload(),
            "shell_execution_available": False,
            "request_paths_allowed": False,
            "cors_enabled": False,
        }

    def _model_connection_payload(self) -> dict[str, object]:
        with self._model_status_lock:
            successful_turns = self._successful_live_model_turns
        is_live_provider = self.agent_settings.is_live_model
        provider = self.agent_settings.model_provider
        is_local_model = provider == "ollama" and not self.agent_settings.network_used
        inference_location = {
            "bedrock": "aws_cloud",
            "anthropic": "anthropic_api",
            # The base URL may point at any compatible endpoint, so do not claim OpenAI.
            "openai": "openai_compatible_api",
            "ollama": (
                "remote_ollama_host"
                if self.agent_settings.network_used
                else "local_ollama_host"
            ),
        }.get(provider, "local_fixture")
        return {
            "schema": "folderhome.model-connection-status.v1",
            "provider": self.agent_settings.model_provider,
            "mode": (
                "local_model" if is_local_model
                else "network_model" if is_live_provider else "deterministic_fixture"
            ),
            "runtime_topology": (
                "local_only_model" if is_local_model
                else "local_first_hybrid" if is_live_provider else "local_only_fixture"
            ),
            "application_runtime": "local_loopback",
            "document_runtime": "local_state",
            "model_inference_location": inference_location,
            "connection_status": (
                "verified_in_process"
                if successful_turns > 0
                else "configured_not_verified"
                if is_live_provider
                else "fixture_only"
            ),
            "live_model_configured": is_live_provider,
            "live_model_verified_in_process": successful_turns > 0,
            "successful_live_model_turns": successful_turns,
            "semantic_routing_mode": (
                "live_model" if is_live_provider else "deterministic_fixture"
            ),
            "model_id": (
                self.agent_settings.bedrock_model_id
                or self.agent_settings.ollama_model_id
                or self.agent_settings.anthropic_model_id
                or self.agent_settings.openai_model_id
            ),
            "aws_region": self.agent_settings.aws_region,
            "ollama_host": self.agent_settings.ollama_host,
            "network_authorized": self.agent_settings.allow_network,
            "sensitive_cloud_data_authorized": (
                self.agent_settings.allow_sensitive_cloud_data
            ),
            "status_probe_performed": False,
        }

    def _profiles_payload(self) -> dict[str, object]:
        return {
            "schema": "folderhome.local-profile-list.v1",
            "security_boundary": "operating_system_account",
            "profiles": [
                {
                    "profile_id": item.profile_id,
                    "display_name": item.display_name,
                    "organizational_only": True,
                    "authorization_boundary": False,
                }
                for item in sorted(self.profiles.profiles, key=lambda value: value.profile_id)
            ],
        }

    @staticmethod
    def _capabilities_payload() -> dict[str, object]:
        interactive = {"documents.search", "documents.theme_dossier"}
        capabilities = (
            ("documents.search", "Dokumentensuche"),
            ("documents.theme_dossier", "Themendossier"),
            ("folders.organize", "Ordner organisieren"),
            ("documents.create", "Dokumente und Präsentationen erstellen"),
            ("communications.manage", "Briefe, Mail und Kontakte"),
            ("calendar.manage", "Termine und Kalenderhandoffs"),
            ("finance.overview", "Finanzen und Verträge überblicken"),
            ("health.organize", "Gesundheitsunterlagen organisieren"),
            ("legal.orient", "Bescheide und Rechtsänderungen orientieren"),
            ("household.manage", "Haushalt und Medikamente verwalten"),
        )
        return {
            "schema": "folderhome.local-capability-list.v1",
            "capabilities": [
                {
                    "capability_id": capability_id,
                    "title": title,
                    "surface_status": (
                        "interactive_read_only"
                        if capability_id in interactive
                        else "agent_guided"
                    ),
                    "side_effects": [],
                }
                for capability_id, title in capabilities
            ],
        }

    def _json_request(self, headers: dict[str, str], body: bytes) -> dict[str, object]:
        if len(body) > self.settings.max_body_bytes:
            raise _HttpError(413, "JSON-Anfrage überschreitet die lokale Größenbegrenzung.")
        content_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
        if content_type != "application/json":
            raise _HttpError(415, "API akzeptiert ausschließlich application/json.")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise LocalAppError(f"JSON-Anfrage ist ungültig: {exc}") from exc
        if not isinstance(payload, dict):
            raise LocalAppError("JSON-Anfrage muss ein Objekt sein.")
        return payload

    def _search_request(self, payload: dict[str, object]) -> dict[str, object]:
        expected = {"schema", "profile_id", "query", "limit"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-search-request.v1"
        ):
            raise LocalAppError("Suchanfrage besitzt unbekannte oder fehlende Felder.")
        return self._validated_request(payload, text_key="query")

    def _dossier_request(self, payload: dict[str, object]) -> dict[str, object]:
        expected = {"schema", "profile_id", "topic", "limit"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-dossier-request.v1"
        ):
            raise LocalAppError("Dossieranfrage besitzt unbekannte oder fehlende Felder.")
        return self._validated_request(payload, text_key="topic")

    def _agent_chat_request(self, payload: dict[str, object]) -> dict[str, str]:
        expected = {"schema", "profile_id", "message"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-agent-chat-request.v1"
        ):
            raise LocalAppError("Agentenanfrage besitzt unbekannte oder fehlende Felder.")
        return self._validated_agent_chat(
            profile_id=payload.get("profile_id"),
            message=payload.get("message"),
        )

    def _validated_agent_chat(
        self,
        *,
        profile_id: object,
        message: object,
    ) -> dict[str, str]:
        if not isinstance(profile_id, str) or profile_id not in self._profile_ids:
            raise LocalAppError("Anfrage nennt kein bekanntes organisatorisches Profil.")
        if (
            not isinstance(message, str)
            or not message.strip()
            or len(message) > self.agent_settings.max_prompt_chars
        ):
            raise LocalAppError(
                f"message benötigt 1 bis {self.agent_settings.max_prompt_chars} Zeichen."
            )
        return {"profile_id": profile_id, "message": message.strip()}

    @staticmethod
    def _agent_confirmation_request(payload: dict[str, object]) -> dict[str, object]:
        expected = {"schema", "plan_id", "plan_sha256", "step_ids"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-agent-confirmation-request.v1"
        ):
            raise LocalAppError("Planfreigabe besitzt unbekannte oder fehlende Felder.")
        plan_id = payload.get("plan_id")
        plan_sha256 = payload.get("plan_sha256")
        step_ids = payload.get("step_ids")
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise LocalAppError("Planfreigabe benötigt eine plan_id.")
        if not isinstance(plan_sha256, str) or len(plan_sha256) != 64:
            raise LocalAppError("Planfreigabe benötigt einen Plan-Hash.")
        if (
            not isinstance(step_ids, list)
            or not step_ids
            or not all(isinstance(item, str) for item in step_ids)
        ):
            raise LocalAppError("Planfreigabe benötigt ausgewählte step_ids.")
        return {
            "plan_id": plan_id,
            "plan_sha256": plan_sha256,
            "step_ids": tuple(step_ids),
        }

    def _agent_conversation_reset_request(self, payload: dict[str, object]) -> str:
        expected = {"schema", "profile_id"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-agent-conversation-reset-request.v1"
        ):
            raise LocalAppError(
                "Gesprächsreset besitzt unbekannte oder fehlende Felder."
            )
        profile_id = payload.get("profile_id")
        if not isinstance(profile_id, str) or profile_id not in self._profile_ids:
            raise LocalAppError("Gesprächsreset nennt kein bekanntes Profil.")
        return profile_id

    def _validated_request(
        self,
        payload: dict[str, object],
        *,
        text_key: str,
    ) -> dict[str, object]:
        profile_id = payload.get("profile_id")
        text = payload.get(text_key)
        limit = payload.get("limit")
        if not isinstance(profile_id, str) or profile_id not in self._profile_ids:
            raise LocalAppError("Anfrage nennt kein bekanntes organisatorisches Profil.")
        if not isinstance(text, str) or not text.strip() or len(text) > 500:
            raise LocalAppError(f"{text_key} benötigt 1 bis 500 Zeichen.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not (
            1 <= limit <= self.settings.max_query_limit
        ):
            raise LocalAppError("Suchlimit liegt außerhalb der lokalen Grenze.")
        return {"profile_id": profile_id, text_key: text.strip(), "limit": limit}

    def _asset_response(
        self,
        filename: str,
        content_type: str,
        *,
        replacements: dict[str, str] | None = None,
    ) -> LocalApiResponse:
        path = self._asset_root / filename
        if not path.is_file():
            return self._error(500, "Lokales GUI-Asset fehlt.")
        content = path.read_text(encoding="utf-8")
        for old, new in (replacements or {}).items():
            content = content.replace(old, new)
        return LocalApiResponse(
            status_code=200,
            content_type=content_type,
            content=content.encode("utf-8"),
            headers=self._security_headers(),
        )

    def _json_response(
        self,
        payload: dict[str, object],
        status_code: int = 200,
    ) -> LocalApiResponse:
        content = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        ).encode("utf-8")
        return LocalApiResponse(
            status_code=status_code,
            content_type="application/json; charset=utf-8",
            content=content,
            headers=self._security_headers(),
            payload=payload,
        )

    def _error(self, status_code: int, message: str) -> LocalApiResponse:
        return self._json_response(
            {
                "schema": "folderhome.local-api-error.v1",
                "status": "blocked" if status_code in {401, 403} else "error",
                "status_code": status_code,
                "message": message,
            },
            status_code=status_code,
        )

    @staticmethod
    def _security_headers() -> dict[str, str]:
        return {
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            ),
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }


class _HttpError(LocalAppError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def _executor_coverage(gateway: WorkflowExecutionGateway) -> dict[str, int]:
    return gateway.coverage()


def _plan_envelope_ids(plans: tuple[MasterAgentPlan, ...]) -> tuple[str, ...]:
    return tuple(
        step.execution_envelope.envelope_id
        for plan in plans
        for step in plan.steps
        if step.execution_envelope is not None
    )


def capture_os_identity() -> OperatingSystemIdentity:
    account = getpass.getuser().strip()
    if os.name == "nt":
        domain = os.environ.get("USERDOMAIN", "").strip()
        if domain and "\\" not in account:
            account = f"{domain}\\{account}"
    home = Path.home().resolve()
    material = f"{platform.system()}\0{account.casefold()}\0{os.path.normcase(str(home))}"
    return OperatingSystemIdentity(
        account_name=account,
        platform=platform.system().casefold(),
        home_path=home,
        identity_sha256=sha256(material.encode("utf-8")).hexdigest(),
    )
