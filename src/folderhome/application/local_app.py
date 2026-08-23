"""Token-gated local API reusing existing read-only FolderHome services."""

from __future__ import annotations

import getpass
import hmac
import json
import os
import platform
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
from folderhome.application.workflow_execution import (
    WorkflowExecutionError,
    WorkflowExecutionGateway,
)
from folderhome.contracts.local_app import (
    LocalApiResponse,
    LocalAppSettings,
    OperatingSystemIdentity,
)
from folderhome.contracts.master_agent import MasterAgentPlan, MasterPlanApproval
from folderhome.contracts.resources import ResourceRegistry
from folderhome.contracts.strands_agent import FolderHomeAgentReport, StrandsAgentSettings

_MAX_PROPOSED_AGENT_PLANS = 128


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
        self.session_token = token
        self._token_sha256 = sha256(token.encode("utf-8")).hexdigest()
        self._identity = capture_os_identity()
        self._profile_ids = frozenset(profile_ids)
        self._proposed_agent_plans: dict[str, MasterAgentPlan] = {}
        self._agent_plan_lock = threading.RLock()
        self._agent_conversation_messages: dict[
            str, tuple[dict[str, Any], ...]
        ] = {profile_id: () for profile_id in profile_ids}
        self._agent_conversation_turns = {profile_id: 0 for profile_id in profile_ids}
        self._agent_conversation_locks = {
            profile_id: threading.RLock() for profile_id in profile_ids
        }
        self._successful_live_model_turns = 0
        self._model_status_lock = threading.RLock()
        self._asset_root = Path(__file__).parents[1] / "web_ui"

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
            if self.agent_settings.model_provider == "bedrock":
                with self._model_status_lock:
                    self._successful_live_model_turns += 1
            self._agent_conversation_messages[request["profile_id"]] = retained_messages
            self._agent_conversation_turns[request["profile_id"]] += 1
            with self._agent_plan_lock:
                for plan in report.proposed_plans:
                    if (
                        plan.plan_id not in self._proposed_agent_plans
                        and len(self._proposed_agent_plans) >= _MAX_PROPOSED_AGENT_PLANS
                    ):
                        oldest_plan_id = next(iter(self._proposed_agent_plans))
                        oldest_plan = self._proposed_agent_plans.pop(oldest_plan_id)
                        self.workflow_executor.discard_unexecuted(
                            _plan_envelope_ids((oldest_plan,))
                        )
                    self._proposed_agent_plans[plan.plan_id] = plan
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
                for plan_id in discarded:
                    del self._proposed_agent_plans[plan_id]
                self.workflow_executor.discard_unexecuted(
                    _plan_envelope_ids(discarded_plans)
                )
            return {
                "schema": "folderhome.local-agent-conversation-reset-response.v1",
                "conversation": self.agent_conversation_payload(profile_id),
                "discarded_plan_ids": list(discarded),
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
        if plan is None:
            raise LocalAppError("Plan ist in dieser lokalen Sitzung nicht bekannt.")
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
        for step in plan.steps:
            if step.step_id not in approved_step_ids or step.execution_envelope is None:
                continue
            execution_reports.append(
                self.workflow_executor.execute(
                    envelope_id=step.execution_envelope.envelope_id,
                    approved_at=approved_at,
                )
            )
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

        if method == "GET" and parsed.path == "/api/v1/status":
            return self._json_response(self._status_payload(server_port))
        if method == "GET" and parsed.path == "/api/v1/profiles":
            return self._json_response(self._profiles_payload())
        if method == "GET" and parsed.path == "/api/v1/capabilities":
            return self._json_response(self._capabilities_payload())
        if method == "GET" and parsed.path == "/api/v1/agent/executors":
            return self._json_response(self.executor_catalog_payload())
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
            "/api/v1/agent/confirm",
            "/api/v1/agent/conversation/reset",
        }:
            return self._error(405, "Lokaler Dienst benötigt eine POST-JSON-Anfrage.")
        return self._error(404, "Unbekannter lokaler Endpunkt.")

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
        is_live_provider = self.agent_settings.model_provider == "bedrock"
        return {
            "schema": "folderhome.model-connection-status.v1",
            "provider": self.agent_settings.model_provider,
            "mode": "network_model" if is_live_provider else "deterministic_fixture",
            "runtime_topology": (
                "local_first_hybrid" if is_live_provider else "local_only_fixture"
            ),
            "application_runtime": "local_loopback",
            "document_runtime": "local_state",
            "model_inference_location": (
                "aws_cloud" if is_live_provider else "local_fixture"
            ),
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
            "model_id": self.agent_settings.bedrock_model_id,
            "aws_region": self.agent_settings.aws_region,
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
