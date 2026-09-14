"""Token-gated local API reusing existing read-only FolderHome services."""

from __future__ import annotations

import contextlib
import getpass
import hmac
import ipaddress
import json
import os
import platform
import re
import secrets
import threading
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

from folderhome.application.document_search import build_theme_dossier, search_documents
from folderhome.application.master_agent import MasterAgentError, confirm_master_agent_plan
from folderhome.application.profile_rules import ProfileConfiguration
from folderhome.application.recipes import (
    build_recipe_plan,
    create_recipe_run,
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
    model_status_fields,
)
from folderhome.contracts.master_agent import MasterAgentPlan, MasterPlanApproval
from folderhome.contracts.recipe_results import ResultBoundRecipe
from folderhome.contracts.recipe_stages import RecipeStagePlan
from folderhome.contracts.recipes import CapabilityRecipeError, CapabilityRecipePlan
from folderhome.contracts.resources import ResourceRegistry
from folderhome.contracts.strands_agent import FolderHomeAgentReport, StrandsAgentSettings

_MAX_PROPOSED_AGENT_PLANS = 128
_MAX_RETAINED_EXECUTION_RESULTS = 128
_MAX_RECIPE_RUNS = 128
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


def _is_strict_loopback_host(host: str | None) -> bool:
    """Return True only if host is strictly a loopback address or localhost."""
    if not host or not isinstance(host, str):
        return False
    clean = host.strip("[]").lower()
    if clean == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(clean)
        return ip.is_loopback
    except ValueError:
        return False


def _redact_url_credentials(value: str | None) -> str | None:
    """Redact userinfo, query, and fragment from a model URL for public exposure."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return value
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if not parsed.scheme or not hostname:
        return None
    if port is not None and not (1 <= port <= 65535):
        return None
    host = f"[{hostname}]" if ":" in hostname else hostname
    port_str = f":{port}" if port is not None else ""
    netloc = f"{host}{port_str}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


_CAPABILITY_WORKFLOWS: dict[str, tuple[str, ...]] = {
    "documents.search": ("document-library",),
    "documents.theme_dossier": ("document-library",),
    "folders.organize": (
        "directory-observation",
        "document-action-execution",
        "document-action-plan",
        "folder-cleanup",
        "folder-routine",
        "routine-queue",
    ),
    "documents.create": (
        "artifact-studio",
        "document-bundle",
        "document-package",
    ),
    "communications.manage": (
        "calendar-connectors",
        "calendar-handoff",
        "contact-register",
        "correspondence-studio",
        "findcall",
        "mail-connector",
    ),
    "calendar.manage": (
        "calendar-connectors",
        "calendar-handoff",
    ),
    "finance.overview": (
        "contract-cockpit",
        "finance-import",
        "tax-workpaper",
    ),
    "health.organize": (
        "health-dossier",
        "medication-intake",
    ),
    "legal.orient": (
        "administrative-drafts",
        "benefit-screening",
        "legal-change-monitor",
        "official-notice-understanding",
    ),
    "household.manage": (
        "daily-briefing",
        "inventory-import",
    ),
}


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
        launch_config_path: Path | str | None = None,
        running_preset: str | None = None,
        startup_allow_network: bool | None = None,
        startup_allow_sensitive_cloud_data: bool | None = None,
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
        self._startup_allow_network = (
            startup_allow_network
            if startup_allow_network is not None
            else bool(self.agent_settings.allow_network)
        )
        self._startup_allow_sensitive_cloud_data = (
            startup_allow_sensitive_cloud_data
            if startup_allow_sensitive_cloud_data is not None
            else bool(self.agent_settings.allow_sensitive_cloud_data)
        )
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
        self._launch_config_path = (
            Path(launch_config_path).resolve() if launch_config_path else None
        )
        if running_preset is not None:
            self._running_preset = running_preset
        elif self._launch_config_path is not None:
            saved = self._read_saved_preset()
            self._running_preset = saved or "no preset / flags"
        else:
            self._running_preset = "no preset / flags"
        self._proposed_agent_plans: dict[str, MasterAgentPlan] = {}
        self._recipe_plans: dict[str, CapabilityRecipePlan | RecipeStagePlan] = {}
        self._recipe_runs = {}
        self._recipe_sessions_closed = False
        # Object identity is a process-local preparation lease: two equal hashes
        # from different tool calls must not release each other's references.
        self._pending_recipe_plans: dict[int, CapabilityRecipePlan | RecipeStagePlan] = {}
        self._pending_agent_plans: dict[int, MasterAgentPlan] = {}
        self._started_recipe_plans: set[str] = set()
        self._active_transaction_discarded_envelopes: set[str] | None = None
        self._active_transaction_discarded_plans: set[str] | None = None
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
        self._reload_lock = threading.RLock()
        self._asset_root = Path(__file__).parents[1] / "web_ui"

    def close(self) -> None:
        """Stop only background work owned by this application instance."""
        with self._agent_plan_lock:
            self._recipe_sessions_closed = True
        try:
            for profile_id in sorted(self._profile_ids):
                with self._agent_conversation_locks[profile_id], self._agent_plan_lock:
                    for state in self.recipe_runs_payload(profile_id=profile_id)["runs"]:
                        self._close_recipe_run(state["run_id"])
        finally:
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
                "approval_mode": (
                    "per_section" if isinstance(recipe, ResultBoundRecipe) else "whole_chain"
                ),
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
                run_id = oldest.approval_context.get("run_id")
                if run_id in self._recipe_runs:
                    self._close_recipe_run(run_id)
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
        to_discard = tuple(
            item for item in envelope_ids if item not in retained
        )
        if to_discard:
            self.workflow_executor.discard_unexecuted(to_discard)
            if self._active_transaction_discarded_envelopes is not None:
                self._active_transaction_discarded_envelopes.update(to_discard)

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
            referenced_runs = {
                plan.approval_context.get("run_id") for plan in (
                    *self._proposed_agent_plans.values(), *self._pending_agent_plans.values()
                )
            }
            for plan in plans:
                run_id = plan.approval_context.get("run_id")
                if run_id in self._recipe_runs and run_id not in referenced_runs:
                    run = self._recipe_runs[run_id]
                    if run.snapshot()["completed_step_refs"]:
                        run.discard_pending()
                    else:
                        self._close_recipe_run(run_id)
            self._discard_unreferenced_envelopes(_plan_envelope_ids(plans))

    def recipe_runs_payload(self, *, profile_id: str) -> dict[str, object]:
        self._recipe_context(profile_id, "en")
        with self._agent_plan_lock:
            return {
                "schema": "folderhome.local-recipe-runs.v1", "profile_id": profile_id,
                "persistence": "process_memory_only",
                "runs": [state for run in self._recipe_runs.values()
                         if (state := run.snapshot())["profile_id"] == profile_id],
                "execution_performed": False,
            }

    def _recipe_run(self, profile_id, run_id):
        run = self._recipe_runs.get(run_id)
        if run is None or run.snapshot()["profile_id"] != profile_id:
            raise LocalAppError("Rezeptlauf ist in diesem Profil nicht verfügbar.")
        return run

    def _close_recipe_run(self, run_id):
        run = self._recipe_runs[run_id]
        saved_proposed = {
            key: plan for key, plan in self._proposed_agent_plans.items()
            if plan.approval_context.get("run_id") == run_id
        }
        for key in saved_proposed:
            self._proposed_agent_plans.pop(key, None)
            self._recipe_plans.pop(key, None)
        for key in [
            key for key, plan in self._pending_agent_plans.items()
            if plan.approval_context.get("run_id") == run_id
        ]:
            self._pending_agent_plans.pop(key, None)
            self._pending_recipe_plans.pop(key, None)

        if self._active_transaction_discarded_plans is not None:
            self._active_transaction_discarded_plans.update(saved_proposed.keys())
        pending_plan = getattr(run, "_pending", None)
        if pending_plan is not None:
            pending_envs = tuple(
                s.execution_envelope.envelope_id
                for s in getattr(pending_plan, "steps", ())
                if getattr(s, "execution_envelope", None) is not None
            )
            if self._active_transaction_discarded_envelopes is not None:
                self._active_transaction_discarded_envelopes.update(pending_envs)
            if self._active_transaction_discarded_plans is not None:
                self._active_transaction_discarded_plans.add(pending_plan.plan_id)
        if (
            hasattr(run, "_cleanup_pending")
            and run._cleanup_pending
            and self._active_transaction_discarded_envelopes is not None
        ):
            self._active_transaction_discarded_envelopes.update(run._cleanup_pending)

        try:
            run.close()
        except Exception:
            raise
        state = run.snapshot()
        self._recipe_runs.pop(run_id)
        return state

    def close_recipe_run(self, *, profile_id: str, run_id: str):
        self._recipe_context(profile_id, "en")
        with self._agent_conversation_locks[profile_id], self._agent_plan_lock:
            self._recipe_run(profile_id, run_id)
            return {"schema": "folderhome.local-recipe-close-response.v1",
                    "recipe_run": self._close_recipe_run(run_id), "execution_performed": False}

    def prepare_recipe_stage(self, *, profile_id: str, run_id: str) -> RecipeStagePlan:
        """Tool-safe preparation; the caller owns conversation serialization."""
        self._recipe_context(profile_id, "en")
        with self._agent_plan_lock:
            run = self._recipe_run(profile_id, run_id)
            if self._recipe_sessions_closed or run.snapshot()["status"] not in {
                "ready", "awaiting_approval",
            }:
                raise LocalAppError("Dieser Rezeptlauf kann keinen neuen Abschnitt planen.")
            resources, statuses = self._recipe_context(profile_id, run.snapshot()["language"])
            if len(self._pending_agent_plans) >= _MAX_PROPOSED_AGENT_PLANS:
                raise LocalAppError("Budget für laufende Planvorbereitungen ist belegt.")
            plan = run.plan_next(endpoint_statuses=statuses, known_resource_ids=resources)
            result = RecipeStagePlan(plan, run.snapshot())
            self.protect_agent_preparation(plan)
            self._pending_recipe_plans[id(plan)] = result
            return result

    def propose_recipe_stage(self, *, profile_id: str, run_id: str) -> RecipeStagePlan:
        self._recipe_context(profile_id, "en")
        with self._agent_conversation_locks[profile_id], self._agent_plan_lock:
            result = self.prepare_recipe_stage(profile_id=profile_id, run_id=run_id)
            self._retain_agent_plan(result.plan)
            self._recipe_plans[result.plan_id] = result
            return deepcopy(result)

    def propose_calendar_edit(self, payload):
        """Plan a retained own event edit without performing a provider write."""
        from folderhome.application.calendar_event_editor import (
            mutation_request_from_result,
            validate_edit_request,
        )
        from folderhome.application.master_agent import build_master_agent_plan

        payload = validate_edit_request(payload)
        profile_id = payload["profile_id"]
        if profile_id not in self._profile_ids:
            raise LocalAppError("Unbekanntes organisatorisches Profil.")
        with self._agent_conversation_locks[profile_id], self._agent_plan_lock:
            with self._execution_results_lock:
                result = deepcopy(self._execution_results.get(payload["execution_id"]))
            request = mutation_request_from_result(payload, result)
            envelope = self.workflow_executor.prepare(
                workflow_id="calendar-connectors", profile_id=profile_id, request=request,
            )
            try:
                deleting = payload["operation"] == "delete"
                goal = (
                    ("Ausgewählten Termin löschen." if deleting else "Ausgewählten Termin ändern.")
                    if payload["language"] == "de" else
                    ("Delete the selected event." if deleting else "Update the selected event.")
                )
                plan = build_master_agent_plan(
                    goal, profile_id=profile_id, language=payload["language"],
                    expert_id="communication_expert", workflow_ids=("calendar-connectors",),
                    confidence="high", execution_envelopes={"calendar-connectors": envelope},
                )
                self._retain_agent_plan(plan, pending_envelopes=(envelope.envelope_id,))
            except BaseException:
                self._discard_unreferenced_envelopes((envelope.envelope_id,))
                raise
        return {"schema": "folderhome.calendar-event-edit-plan.v1",
                "plan": plan.to_dict(), "side_effects": []}

    def propose_recipe(
        self, *, profile_id: str, recipe_id: str, language: str,
    ) -> CapabilityRecipePlan | RecipeStagePlan:
        """Prepare and retain a journey under the same lock as conversation reset."""

        self._recipe_context(profile_id, language)
        with self._agent_conversation_locks[profile_id], self._agent_plan_lock:
            result = self.prepare_recipe(
                profile_id=profile_id, recipe_id=recipe_id, language=language,
            )
            self._retain_agent_plan(result.plan)
            self._recipe_plans[result.plan_id] = result
            return deepcopy(result)

    def prepare_recipe(
        self, *, profile_id: str, recipe_id: str, language: str,
    ) -> CapabilityRecipePlan | RecipeStagePlan:
        """Prepare only; a Strands tool thread must not acquire its caller's conversation lock."""

        resource_ids, statuses = self._recipe_context(profile_id, language)
        recipe = load_bundled_recipe(recipe_id)
        if isinstance(recipe, ResultBoundRecipe):
            with self._agent_plan_lock:
                if len(self._recipe_runs) >= _MAX_RECIPE_RUNS:
                    raise LocalAppError("Rezeptlaufbudget ist belegt; zuerst alte Läufe schließen.")
                run = create_recipe_run(
                    recipe, profile_id=profile_id, language=language,
                    gateway=self.workflow_executor,
                )
                run_id = run.snapshot()["run_id"]
                self._recipe_runs[run_id] = run
                try:
                    return self.prepare_recipe_stage(profile_id=profile_id, run_id=run_id)
                except BaseException:
                    self._close_recipe_run(run_id)
                    raise
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
                if self._active_transaction_discarded_plans is not None:
                    self._active_transaction_discarded_plans.update(discarded)
                    self._active_transaction_discarded_plans.update(
                        getattr(p, "plan_id", str(id(p))) for p in pending
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
                for state in self.recipe_runs_payload(profile_id=profile_id)["runs"]:
                    self._close_recipe_run(state["run_id"])
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
        if plan.approval_context.get("schema") == "folderhome.recipe-stage-context.v1":
            raise LocalAppError("Rezeptabschnitt besitzt keinen gültigen Laufkontext.")
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
            exc.uncertain_results = [self._capture_uncertain_result(
                profile_id=plan.profile_id, plan_id=plan.plan_id,
                envelope=step.execution_envelope, executed_at=approved_at, error=exc,
            )]
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
        if isinstance(recipe_plan, RecipeStagePlan):
            return self._confirm_recipe_stage(recipe_plan, request)
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
            uncertain_results = []
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
                        uncertain_results.append(self._capture_uncertain_result(
                            profile_id=plan.profile_id, plan_id=plan.plan_id,
                            envelope=envelopes[envelope_id], executed_at=approved_at, error=exc,
                        ))
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
                "uncertain_results": uncertain_results,
                "retry_safe": False,
                "invalidated_plan_ids": invalidated_ids,
                "side_effects": list(dict.fromkeys(
                    effect for report in reports for effect in report.side_effects
                )),
            }

    def _confirm_recipe_stage(self, proposal, request):
        plan = proposal.plan
        with self._agent_conversation_locks[plan.profile_id], self._agent_plan_lock:
            if self._recipe_sessions_closed or self._recipe_plans.get(plan.plan_id) is not proposal:
                raise LocalAppError("Rezeptabschnitt ist nicht mehr verfügbar.")
            proposal.verify_integrity()
            run = self._recipe_run(plan.profile_id, proposal.run_id)
            approved_at = datetime.now(UTC).isoformat()
            result = run.confirm(MasterPlanApproval(
                approval_id=f"approval_{secrets.token_hex(10)}",
                plan_id=request["plan_id"], plan_sha256=request["plan_sha256"],
                step_ids=request["step_ids"], approved_at=approved_at,
            ))
            self._proposed_agent_plans.pop(plan.plan_id, None)
            self._recipe_plans.pop(plan.plan_id, None)
            uncertain_results = []
            delivery_incomplete = False
            for item in result["uncertain_steps"]:
                envelope = next(step.execution_envelope for step in plan.steps
                                if step.execution_envelope.envelope_id == item["envelope_id"])
                try:
                    uncertain_results.append(self._retain_uncertain_result(
                        profile_id=plan.profile_id, plan_id=plan.plan_id, envelope=envelope,
                        executed_at=approved_at, evidence=item["evidence"],
                    ))
                except Exception:
                    # The response still carries the original typed partial evidence.
                    delivery_incomplete = True
                delivery_incomplete = delivery_incomplete or item["evidence_unavailable"]
            try:
                self._retain_execution_results(
                    profile_id=plan.profile_id, plan_id=plan.plan_id,
                    reports=run.confirmed_reports(plan.plan_id), executed_at=approved_at,
                )
            except Exception:
                delivery_incomplete = True
            return {
                "schema": "folderhome.local-agent-confirmation-response.v1",
                "receipt": result["receipt"], "recipe_execution": result,
                "recipe_run": run.snapshot(), "execution_reports": result["execution_reports"],
                "execution_performed": bool(result["execution_reports"]),
                "execution_outcome_unknown": result["execution_outcome_unknown"],
                "result_delivery_incomplete": delivery_incomplete,
                "uncertain_results": uncertain_results, "retry_safe": False,
                "side_effects": list(dict.fromkeys(
                    effect for report in result["execution_reports"]
                    for effect in report["side_effects"]
                )),
            }

    def _retain_uncertain_result(
        self, *, profile_id, plan_id, envelope, executed_at, error=None, evidence=None,
    ) -> dict[str, object]:
        """Retain an attempted run, without manufacturing a successful report."""
        result = self._uncertain_result(
            profile_id=profile_id, plan_id=plan_id, envelope=envelope,
            executed_at=executed_at, error=error, evidence=evidence,
        )
        with self._execution_results_lock:
            self._execution_results[result["execution_id"]] = result
            while len(self._execution_results) > _MAX_RETAINED_EXECUTION_RESULTS:
                oldest = next(iter(self._execution_results))
                self._execution_results.pop(oldest)
                self._execution_artifacts.pop(oldest, None)
        return deepcopy(result)

    def _capture_uncertain_result(self, **kwargs) -> dict[str, object]:
        """Return partial evidence even when retaining it fails."""
        try:
            return self._retain_uncertain_result(**kwargs)
        except Exception:
            result = self._uncertain_result(**kwargs)
            result["result_delivery_incomplete"] = True
            return result

    @staticmethod
    def _uncertain_result(
        *, profile_id, plan_id, envelope, executed_at, error=None, evidence=None,
    ) -> dict[str, object]:
        evidence_unavailable = False
        try:
            partial_evidence = deepcopy(
                evidence if evidence is not None else error.public_evidence()
            )
            if not isinstance(partial_evidence, dict):
                raise ValueError("Partial evidence must be an object.")
            json.dumps(partial_evidence, allow_nan=False)
        except Exception:
            partial_evidence = {}
            evidence_unavailable = True
        result = {
            "execution_id": f"workflow_attempt_{secrets.token_hex(16)}",
            "plan_id": plan_id,
            "profile_id": profile_id,
            "workflow_id": envelope.workflow_id,
            "adapter_id": envelope.adapter_id,
            "status": "uncertain",
            "executed_at": executed_at,
            "side_effects": [],
            "possible_side_effects": list(envelope.side_effects),
            "retry_safe": False,
            "artifacts": [],
            "evidence": partial_evidence,
            "evidence_unavailable": evidence_unavailable,
            "result_delivery_incomplete": evidence_unavailable,
        }
        return result

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
                mutation = report.domain_report.get("mutation")
                if (
                    report.workflow_id == "calendar-connectors"
                    and isinstance(mutation, dict)
                    and mutation.get("schema") == "folderhome.google-calendar-mutation-result.v1"
                ):
                    self._execution_results[report.execution_id]["evidence"] = {
                        "confirmed_mutation": deepcopy(mutation),
                    }
                versions = report.domain_report.get("event_versions")
                if report.workflow_id == "calendar-connectors" and isinstance(versions, list):
                    evidence = self._execution_results[report.execution_id].setdefault(
                        "evidence", {}
                    )
                    evidence["event_versions"] = deepcopy(versions)
                    context = report.domain_report.get("calendar_edit_context")
                    if isinstance(context, dict):
                        evidence["calendar_edit_context"] = deepcopy(context)
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
                deepcopy(item)
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
        except WorkflowExecutionOutcomeUnknown as exc:
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
                    "uncertain_results": exc.uncertain_results,
                    "result_delivery_incomplete": any(
                        item.get("result_delivery_incomplete", False)
                        for item in exc.uncertain_results
                    ),
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
        if parsed.path == "/api/v1/agent/recipes/runs":
            if method != "GET":
                return self._error(405, "Rezeptläufe sind nur per GET abrufbar.")
            query = parse_qs(parsed.query, keep_blank_values=True)
            if set(query) != {"profile_id"} or len(query["profile_id"]) != 1:
                raise LocalAppError("Rezeptläufe benötigen genau ein Profil.")
            return self._json_response(self.recipe_runs_payload(profile_id=query["profile_id"][0]))
        if parsed.path in {"/api/v1/agent/recipes/next", "/api/v1/agent/recipes/close"}:
            if method != "POST":
                return self._error(405, "Rezeptaktionen benötigen POST.")
            action = parsed.path.rsplit("/", 1)[-1]
            payload = self._json_request(headers, body)
            if (
                parsed.query or set(payload) != {"schema", "profile_id", "run_id"}
                or payload.get("schema") != f"folderhome.local-recipe-{action}-request.v1"
                or not all(isinstance(value, str) for value in payload.values())
                or re.fullmatch(r"recipe_run_[0-9a-f]{32}", payload["run_id"]) is None
            ):
                raise LocalAppError("Rezeptaktion besitzt unbekannte oder ungültige Felder.")
            args = {"profile_id": payload["profile_id"], "run_id": payload["run_id"]}
            result = (self.propose_recipe_stage(**args).to_dict() if action == "next"
                      else self.close_recipe_run(**args))
            return self._json_response(result)
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
        if method == "POST" and parsed.path == "/api/v1/agent/calendar/plan":
            return self._json_response(
                self.propose_calendar_edit(self._json_request(headers, body))
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
        if method == "POST" and parsed.path == "/api/v1/settings/reload":
            payload = self._json_request(headers, body)
            return self._reload_settings(payload)
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
            "/api/v1/agent/calendar/plan",
            "/api/v1/agent/conversation/reset",
            "/api/v1/settings/reload",
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

    def _read_saved_preset(self) -> str | None:
        if self._launch_config_path is None or not self._launch_config_path.is_file():
            return None
        try:
            payload = json.loads(self._launch_config_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                name = payload.get("model_preset")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        except (OSError, json.JSONDecodeError):
            return None
        return None

    def _status_payload(self, server_port: int) -> dict[str, object]:
        with self._model_status_lock:
            current_settings = self.agent_settings
            successful_turns = self._successful_live_model_turns
            running_preset = self._running_preset
            connection = self._build_model_connection_payload(
                current_settings, successful_turns
            )
            status_fields = model_status_fields(
                current_settings, successful_turns
            )
        saved_preset = self._read_saved_preset()
        settings_stale = bool(
            self._launch_config_path is not None
            and saved_preset is not None
            and saved_preset != running_preset
        )
        setup_file = self.settings.state_dir / "setup-server.json"
        setup_url = None
        if setup_file.is_file():
            try:
                setup_data = json.loads(setup_file.read_text(encoding="utf-8"))
                if isinstance(setup_data, dict):
                    raw_candidate = setup_data.get("access_url")
                    if not raw_candidate and "port" in setup_data and "token" in setup_data:
                        raw_port = setup_data["port"]
                        raw_token = setup_data["token"]
                        if (
                            isinstance(raw_port, int)
                            and (1 <= raw_port <= 65535)
                            and isinstance(raw_token, str)
                            and raw_token.strip()
                        ):
                            raw_candidate = (
                                f"http://127.0.0.1:{raw_port}/?token={quote(raw_token.strip())}"
                            )
                    if isinstance(raw_candidate, str) and raw_candidate.strip():
                        try:
                            parsed = urlsplit(raw_candidate)
                            if parsed.scheme.lower() == "http":
                                h = parsed.hostname.lower() if parsed.hostname else ""
                                is_loopback = _is_strict_loopback_host(h)
                                p = parsed.port
                                if is_loopback and p is not None and (1 <= p <= 65535):
                                    q = parse_qs(parsed.query, keep_blank_values=True)
                                    tokens = q.get("token")
                                    if tokens and tokens[0].strip():
                                        setup_url = raw_candidate
                        except (ValueError, Exception):
                            setup_url = None
            except Exception:
                setup_url = None
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
            "model_connection": connection,
            **status_fields,
            "launch_config_path": (
                self._launch_config_path.name
                if self._launch_config_path is not None
                else None
            ),
            "running_preset": running_preset,
            "saved_preset": saved_preset,
            "settings_stale": settings_stale,
            "setup_url": setup_url,
            "shell_execution_available": False,
            "request_paths_allowed": False,
            "cors_enabled": False,
        }

    def _model_connection_payload(self) -> dict[str, object]:
        with self._model_status_lock:
            return self._build_model_connection_payload(
                self.agent_settings, self._successful_live_model_turns
            )

    def _build_model_connection_payload(
        self, agent_settings: StrandsAgentSettings, successful_turns: int
    ) -> dict[str, object]:
        is_live_provider = agent_settings.is_live_model
        provider = agent_settings.model_provider
        is_local_model = provider == "ollama" and not agent_settings.network_used
        inference_location = {
            "bedrock": "aws_cloud",
            "anthropic": "anthropic_api",
            # The base URL may point at any compatible endpoint, so do not claim OpenAI.
            "openai": "openai_compatible_api",
            "ollama": (
                "remote_ollama_host"
                if agent_settings.network_used
                else "local_ollama_host"
            ),
        }.get(provider, "local_fixture")
        return {
            "schema": "folderhome.model-connection-status.v1",
            "provider": agent_settings.model_provider,
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
                agent_settings.bedrock_model_id
                or agent_settings.ollama_model_id
                or agent_settings.anthropic_model_id
                or agent_settings.openai_model_id
            ),
            "aws_region": agent_settings.aws_region,
            "ollama_host": _redact_url_credentials(agent_settings.ollama_host),
            "openai_base_url": (
                _redact_url_credentials(agent_settings.openai_base_url)
                if agent_settings.openai_base_url
                else None
            ),
            "network_authorized": agent_settings.allow_network,
            "sensitive_cloud_data_authorized": (
                agent_settings.allow_sensitive_cloud_data
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

    def _capabilities_payload(self) -> dict[str, object]:
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
        catalog = (
            {item.workflow_id: item.status for item in self.workflow_executor.catalog()}
            if self.workflow_executor is not None
            else {}
        )
        items = []
        for capability_id, title in capabilities:
            wf_ids = _CAPABILITY_WORKFLOWS.get(capability_id, ())
            if capability_id in interactive:
                surface_status = "interactive_read_only"
            else:
                statuses = [catalog.get(wid, "not_connected") for wid in wf_ids]
                if not statuses:
                    surface_status = "not_connected"
                elif all(s == "connected" for s in statuses):
                    surface_status = "agent_guided"
                elif all(s in {"connected", "planning_only"} for s in statuses):
                    surface_status = "planning_only"
                else:
                    surface_status = "not_connected"
            items.append(
                {
                    "capability_id": capability_id,
                    "title": title,
                    "surface_status": surface_status,
                    "workflow_ids": list(wf_ids),
                    "side_effects": [],
                }
            )
        return {
            "schema": "folderhome.local-capability-list.v1",
            "capabilities": items,
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

    @staticmethod
    def _settings_reload_request(payload: dict[str, object]) -> None:
        expected = {"schema"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-settings-reload-request.v1"
        ):
            raise LocalAppError("Reload-Anfrage besitzt unbekannte oder fehlende Felder.")

    def _reload_settings(self, payload: dict[str, object]) -> LocalApiResponse:
        with self._reload_lock:
            self._settings_reload_request(payload)
            if self._launch_config_path is None or not self._launch_config_path.is_file():
                raise _HttpError(
                    409,
                    "Keine gespeicherte Startkonfiguration (launch.json) vorhanden.",
                )
            from folderhome.cli import ReloadGateError, build_reloaded_agent_settings

            staging_env: dict[str, str] = {}
            try:
                new_settings, new_preset = build_reloaded_agent_settings(
                    self._launch_config_path,
                    self.agent_settings,
                    target_environ=staging_env,
                    startup_allow_network=self._startup_allow_network,
                    startup_allow_sensitive_cloud_data=self._startup_allow_sensitive_cloud_data,
                )
            except ReloadGateError as exc:
                raise _HttpError(409, str(exc)) from exc
            except (ValueError, OSError) as exc:
                raise _HttpError(
                    409,
                    f"Startkonfiguration konnte nicht geladen werden: {exc}",
                ) from exc

            # Validate staging_env before mutating anything
            for name, value in staging_env.items():
                if (
                    not isinstance(name, str)
                    or not isinstance(value, str)
                    or not name
                    or "=" in name
                    or "\0" in name
                    or "\0" in value
                ):
                    raise _HttpError(
                        500,
                        "Ungültige Umgebungsvariablen in der Startkonfiguration.",
                    )

            with contextlib.ExitStack() as stack:
                for profile_id in sorted(self._profile_ids):
                    stack.enter_context(self._agent_conversation_locks[profile_id])
                stack.enter_context(self._agent_plan_lock)
                stack.enter_context(self._model_status_lock)
                stack.enter_context(self._execution_results_lock)

                # Fail closed: reject reload before any mutating cleanup action if any recipe run
                # is active, awaiting approval with a pending plan, or has uncleaned preparations.
                for run in self._recipe_runs.values():
                    run_snapshot = (
                        run.snapshot()
                        if hasattr(run, "snapshot")
                        else {"status": getattr(run, "status", None)}
                    )
                    run_status = run_snapshot.get("status")
                    if run_status in {"running", "preparing"}:
                        raise _HttpError(
                            409,
                            "Laufende Rezeptabschnitte verhindern das Neuladen.",
                        )
                    if (
                        run_snapshot.get("pending_plan_id") is not None
                        or run_status == "awaiting_approval"
                    ):
                        raise _HttpError(
                            409,
                            "Offene Rezeptabschnitte verhindern das Neuladen.",
                        )
                    if (run_snapshot.get("cleanup_pending_count") or 0) > 0:
                        raise _HttpError(
                            409,
                            "Ausstehende Bereinigungen von Rezeptabschnitten "
                            "verhindern das Neuladen.",
                        )

                old_messages = {
                    pid: self._agent_conversation_messages[pid] for pid in self._profile_ids
                }
                old_turns = dict(self._agent_conversation_turns)
                old_proposed = dict(self._proposed_agent_plans)
                old_recipe_plans = dict(self._recipe_plans)
                old_pending_agent = dict(self._pending_agent_plans)
                old_pending_recipe = dict(self._pending_recipe_plans)
                old_started = set(self._started_recipe_plans)
                old_runs = dict(self._recipe_runs)
                old_runs_state = {}
                for r_id, r in self._recipe_runs.items():
                    lock = getattr(r, "_lock", None)
                    if lock is not None:
                        with lock:
                            old_runs_state[r_id] = {
                                "run": r,
                                "status": getattr(r, "_status", None),
                                "pending": getattr(r, "_pending", None),
                                "results": dict(getattr(r, "_results", {})),
                                "stage_ids": list(getattr(r, "_stage_ids", [])),
                                "last_execution": deepcopy(getattr(r, "_last_execution", None)),
                                "cleanup_pending": getattr(r, "_cleanup_pending", ()),
                            }
                    else:
                        old_runs_state[r_id] = {
                            "run": r,
                            "status": getattr(r, "status", None),
                        }

                self._active_transaction_discarded_envelopes = set()
                self._active_transaction_discarded_plans = set()

                def _rollback_state() -> None:
                    # Determine all discarded envelope IDs and plan IDs across the transaction
                    discarded_envs: set[str] = set(
                        self._active_transaction_discarded_envelopes or ()
                    )
                    discarded_pids: set[str] = set(self._active_transaction_discarded_plans or ())

                    # Also mark runs that were closed or whose cleanup was pending
                    invalidated_run_ids: set[str] = set()
                    for r_id, r_state in old_runs_state.items():
                        r = r_state["run"]
                        current_status = getattr(r, "_status", getattr(r, "status", None))
                        has_pending_cleanup = (
                            hasattr(r, "_cleanup_pending") and bool(r._cleanup_pending)
                        )
                        if (
                            r_id not in self._recipe_runs
                            or current_status in {"closed", "aborted"}
                            or has_pending_cleanup
                        ):
                            invalidated_run_ids.add(r_id)

                    def _plan_is_discarded(plan_obj: Any) -> bool:
                        if not plan_obj:
                            return True
                        pid = getattr(plan_obj, "plan_id", None)
                        if pid and pid in discarded_pids:
                            return True
                        # Check direct envelope
                        direct_env = getattr(plan_obj, "execution_envelope", None)
                        direct_env_id = (
                            getattr(direct_env, "envelope_id", None) if direct_env else None
                        )
                        if direct_env_id and direct_env_id in discarded_envs:
                            return True
                        # Check step envelopes
                        steps = (
                            getattr(plan_obj, "steps", None)
                            or getattr(plan_obj, "recipe_steps", None)
                        )
                        if steps:
                            for s in steps:
                                env = getattr(s, "execution_envelope", None)
                                env_id = getattr(env, "envelope_id", None) if env else None
                                if env_id and env_id in discarded_envs:
                                    return True
                        inner = getattr(plan_obj, "plan", None)
                        if inner is not None and inner is not plan_obj:
                            return _plan_is_discarded(inner)
                        return False

                    # Identify all plan IDs associated with invalidated runs or discarded envelopes
                    for plan_id, plan in old_proposed.items():
                        run_id = (
                            plan.approval_context.get("run_id")
                            if plan.approval_context
                            else None
                        )
                        if (
                            plan_id not in self._proposed_agent_plans
                            or (run_id and run_id in invalidated_run_ids)
                            or _plan_is_discarded(plan)
                        ):
                            discarded_pids.add(plan_id)

                    for plan_id, plan in old_pending_agent.items():
                        run_id = (
                            plan.approval_context.get("run_id")
                            if plan.approval_context
                            else None
                        )
                        if (run_id and run_id in invalidated_run_ids) or _plan_is_discarded(plan):
                            discarded_pids.add(getattr(plan, "plan_id", str(plan_id)))

                    self._agent_conversation_messages = {
                        pid: old_messages[pid] for pid in self._profile_ids
                    }
                    self._agent_conversation_turns = dict(old_turns)

                    # Restore ONLY plans and pending items that were NOT discarded externally
                    self._proposed_agent_plans = {
                        k: v for k, v in old_proposed.items()
                        if k not in discarded_pids and not _plan_is_discarded(v)
                    }
                    self._recipe_plans = {
                        k: v for k, v in old_recipe_plans.items()
                        if k not in discarded_pids and not _plan_is_discarded(v)
                    }
                    self._pending_agent_plans = {
                        k: v for k, v in old_pending_agent.items()
                        if getattr(v, "plan_id", None) not in discarded_pids
                        and not _plan_is_discarded(v)
                    }
                    self._pending_recipe_plans = {
                        k: v for k, v in old_pending_recipe.items()
                        if getattr(v, "plan_id", None) not in discarded_pids
                        and not _plan_is_discarded(v)
                    }
                    self._started_recipe_plans = set(old_started)

                    # For recipe runs: invalidated runs or runs with discarded
                    # pending plans stay closed/aborted
                    self._recipe_runs = {}
                    for r_id, r in old_runs.items():
                        if r_id in invalidated_run_ids:
                            r_state = old_runs_state[r_id]
                            run_obj = r_state["run"]
                            current_status = getattr(
                                run_obj, "_status", getattr(run_obj, "status", None)
                            )
                            if current_status != "closed":
                                self._recipe_runs[r_id] = r
                        else:
                            self._recipe_runs[r_id] = r

                    for r_id, r_state in old_runs_state.items():
                        r = r_state["run"]
                        lock = getattr(r, "_lock", None)
                        ctx = lock if lock is not None else contextlib.nullcontext()
                        with ctx:
                            pending_plan = r_state.get("pending")
                            pending_discarded = _plan_is_discarded(pending_plan)
                            if r_id in invalidated_run_ids or pending_discarded:
                                current_status = getattr(
                                    r, "_status", getattr(r, "status", None)
                                )
                                target_status = (
                                    "closed" if current_status == "closed" else "aborted"
                                )
                                if hasattr(r, "_status"):
                                    r._status = target_status
                                elif hasattr(r, "status"):
                                    r.status = target_status
                                if hasattr(r, "_pending"):
                                    r._pending = None
                            else:
                                if r_state["status"] is not None:
                                    if hasattr(r, "_status"):
                                        r._status = r_state["status"]
                                    elif hasattr(r, "status"):
                                        r.status = r_state["status"]
                                if hasattr(r, "_pending"):
                                    r._pending = r_state["pending"]
                                if hasattr(r, "_results"):
                                    r._results = r_state["results"]
                                if hasattr(r, "_stage_ids"):
                                    r._stage_ids = r_state["stage_ids"]
                                if hasattr(r, "_last_execution"):
                                    r._last_execution = r_state["last_execution"]
                                if hasattr(r, "_cleanup_pending"):
                                    r._cleanup_pending = r_state["cleanup_pending"]

                try:
                    try:
                        for profile_id in sorted(self._profile_ids):
                            self.reset_agent_conversation(profile_id)
                    except Exception as exc:
                        _rollback_state()
                        if isinstance(exc, _HttpError):
                            raise
                        raise _HttpError(
                            500,
                            "Gesprächs- und Rezeptbereinigung beim Neuladen fehlgeschlagen.",
                        ) from exc

                    env_revert: list[str] = []
                    try:
                        for name, value in staging_env.items():
                            if name not in os.environ:
                                env_revert.append(name)
                                os.environ[name] = value
                    except Exception as exc:
                        for name in env_revert:
                            os.environ.pop(name, None)
                        _rollback_state()
                        raise _HttpError(
                            500,
                            f"Umgebungsvariablen konnten nicht gesetzt werden: {exc}",
                        ) from exc

                    self.agent_settings = new_settings
                    self._running_preset = new_preset or "no preset / flags"
                    self._successful_live_model_turns = 0
                finally:
                    self._active_transaction_discarded_envelopes = None
                    self._active_transaction_discarded_plans = None

            expected_model_state = (
                "fixture_only"
                if self.agent_settings.model_provider == "fixture"
                else "configured_unverified"
            )
            return self._json_response(
                {
                    "schema": "folderhome.local-settings-reload-response.v1",
                    "status": "reloaded",
                    "model_provider": self.agent_settings.model_provider,
                    "model_state": expected_model_state,
                    "running_preset": self._running_preset,
                }
            )

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
        # v2 preparations belong to a separate gateway, even when IDs coincide.
        if plan.approval_context.get("schema") != "folderhome.recipe-stage-context.v1"
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
