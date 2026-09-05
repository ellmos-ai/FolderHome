"""Bounded Strands Agents loop over FolderHome's read-only application services."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterable
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from folderhome.application.capability_index import capability_index_prompt_excerpt
from folderhome.application.local_app import LocalApplication
from folderhome.application.master_agent import (
    MasterAgentError,
    build_master_agent_plan,
    master_agent_catalog,
    master_expert_catalog,
    master_persona_catalog,
    resolve_master_route,
)
from folderhome.application.workflow_execution import WorkflowExecutionError
from folderhome.contracts.strands_agent import (
    AgentDelegationEvent,
    AgentToolEvent,
    FolderHomeAgentReport,
    StrandsAgentSettings,
)

_TOPIC = re.compile(
    r"\b(?:zum\s+thema|zur|zum|über|thema)\s+"
    r"([A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9-]{2,80})",
    re.IGNORECASE,
)


class FolderHomeAgentError(RuntimeError):
    """Raised when the agent boundary or a bounded tool call fails closed."""


def _fixture_model_class():
    try:
        from strands.models import Model
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError(
            "Strands Agents SDK fehlt; installiere die Projektabhängigkeiten."
        ) from exc

    class FixtureFolderHomeModel(Model):
        def __init__(self, *, specialist_workflow_id: str | None = None) -> None:
            self._specialist_workflow_id = specialist_workflow_id
            self._config: dict[str, object] = {
                "model_id": "folderhome-deterministic-fixture-v1",
                "context_window_limit": 8_192,
            }

        def update_config(self, **model_config: Any) -> None:
            self._config.update(model_config)

        def get_config(self) -> dict[str, object]:
            return dict(self._config)

        async def structured_output(
            self,
            output_model,
            prompt,
            system_prompt: str | None = None,
            **kwargs: Any,
        ):
            del output_model, prompt, system_prompt, kwargs
            if False:  # pragma: no cover - keeps this an async generator
                yield {}
            raise NotImplementedError("Fixture-Modell unterstützt keine strukturierte Ausgabe.")

        async def stream(
            self,
            messages,
            tool_specs=None,
            system_prompt: str | None = None,
            **kwargs: Any,
        ) -> AsyncIterable[dict[str, object]]:
            del system_prompt, kwargs
            tool_payload = _latest_tool_result(messages)
            if tool_payload is not None:
                async for event in _text_events(_fixture_answer(tool_payload)):
                    yield event
                return
            prompt_text = _latest_user_text(messages)
            conversation_answer = _fixture_conversation_answer(messages)
            if conversation_answer is not None:
                async for event in _text_events(conversation_answer):
                    yield event
                return
            available = {
                item.get("name")
                for item in (tool_specs or [])
                if isinstance(item, dict)
            }
            if self._specialist_workflow_id is not None:
                tool_name = "propose_home_workflow"
                if tool_name not in available:
                    raise FolderHomeAgentError(
                        f"Benötigtes Strands-Tool fehlt: {tool_name}"
                    )
                payload = {"goal": prompt_text.strip()}
                try:
                    typed_request = json.loads(prompt_text)
                except json.JSONDecodeError:
                    typed_request = None
                if isinstance(typed_request, dict):
                    payload["request_json"] = prompt_text.strip()
                async for event in _tool_events(tool_name, payload):
                    yield event
                return
            specialist_request = _fixture_specialist_request(prompt_text)
            if specialist_request is not None:
                tool_name = "consult_home_specialist"
                if tool_name not in available:
                    raise FolderHomeAgentError(
                        f"Benötigtes Strands-Tool fehlt: {tool_name}"
                    )
                async for event in _tool_events(tool_name, specialist_request):
                    yield event
                return
            folded = prompt_text.casefold()
            is_resource = any(
                marker in folded for marker in ("logical resource", "ressource", "resource")
            )
            is_dossier = any(
                marker in folded for marker in ("alles", "dossier", "zusammenfass", "thema")
            )
            is_search = any(
                marker in folded
                for marker in ("suche", "such", "find", "looking", "dokument")
            )
            tool_name = (
                "list_home_resources"
                if is_resource
                else "build_home_theme_dossier"
                if is_dossier
                else "search_home_documents"
                if is_search
                else "list_home_capabilities"
            )
            if tool_name not in available:
                raise FolderHomeAgentError(f"Benötigtes Strands-Tool fehlt: {tool_name}")
            payload = (
                {"language": "de" if _looks_german(prompt_text) else "en"}
                if tool_name == "list_home_capabilities"
                else {}
                if tool_name == "list_home_resources"
                else {
                    "query": _fixture_topic(prompt_text) if is_dossier else prompt_text.strip(),
                    "limit": 5,
                }
            )
            async for event in _tool_events(tool_name, payload):
                yield event

    return FixtureFolderHomeModel


def run_folderhome_agent(
    *,
    application: LocalApplication,
    prompt: str,
    profile_id: str,
    settings: StrandsAgentSettings,
) -> FolderHomeAgentReport:
    """Run one stateless finite Strands loop for one-shot callers and tests."""

    report, _ = run_folderhome_agent_turn(
        application=application,
        prompt=prompt,
        profile_id=profile_id,
        settings=settings,
    )
    return report


def run_folderhome_agent_turn(
    *,
    application: LocalApplication,
    prompt: str,
    profile_id: str,
    settings: StrandsAgentSettings,
    prior_messages: tuple[dict[str, Any], ...] = (),
) -> tuple[FolderHomeAgentReport, tuple[dict[str, Any], ...]]:
    """Run one bounded turn and return process-local Strands conversation state."""

    if not prompt.strip() or len(prompt) > settings.max_prompt_chars:
        raise FolderHomeAgentError(
            f"Prompt benötigt 1 bis {settings.max_prompt_chars} Zeichen."
        )
    known_profiles = {item.profile_id for item in application.profiles.profiles}
    if profile_id not in known_profiles:
        raise FolderHomeAgentError("Profil ist in diesem Betriebssystemkonto nicht bekannt.")
    try:
        from strands import Agent, tool
        from strands.agent.conversation_manager import SlidingWindowConversationManager
        from strands.tools.executors import SequentialToolExecutor
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError(
            "Strands Agents SDK fehlt; installiere die Projektabhängigkeiten."
        ) from exc

    events: list[AgentToolEvent] = []
    delegations: list[AgentDelegationEvent] = []
    proposed_plans = []

    def ensure_tool_budget() -> None:
        if len(events) >= settings.max_tool_calls:
            raise FolderHomeAgentError("Strands-Toolbudget ist ausgeschöpft.")

    def record_tool(
        tool_name: str,
        payload: dict[str, object],
        result: dict[str, object],
    ) -> None:
        ensure_tool_budget()
        payload_bytes = _json_bytes(payload)
        result_bytes = _json_bytes(result)
        if len(result_bytes) > settings.max_tool_result_bytes:
            raise FolderHomeAgentError("Strands-Toolergebnis überschreitet das Größenbudget.")
        events.append(
            AgentToolEvent(
                sequence=len(events) + 1,
                tool_name=tool_name,
                input_sha256=sha256(payload_bytes).hexdigest(),
                result_sha256=sha256(result_bytes).hexdigest(),
            )
        )

    def call_local(tool_name: str, query: str, limit: int) -> dict[str, object]:
        ensure_tool_budget()
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise FolderHomeAgentError("Toollimit muss eine Ganzzahl sein.")
        endpoint = (
            "/api/v1/documents/dossier"
            if tool_name == "build_home_theme_dossier"
            else "/api/v1/documents/search"
        )
        text_key = "topic" if tool_name == "build_home_theme_dossier" else "query"
        schema = (
            "folderhome.local-dossier-request.v1"
            if text_key == "topic"
            else "folderhome.local-search-request.v1"
        )
        payload = {
            "schema": schema,
            "profile_id": profile_id,
            text_key: query,
            "limit": limit,
        }
        payload_bytes = _json_bytes(payload)
        response = application.handle(
            method="POST",
            target=endpoint,
            headers={
                "Host": f"{application.settings.host}:{application.settings.port}",
                "Origin": (
                    f"http://{application.settings.host}:{application.settings.port}"
                ),
                "Content-Type": "application/json",
                "X-FolderHome-Token": application.session_token,
            },
            body=payload_bytes,
            server_port=application.settings.port,
        )
        if response.status_code != 200 or response.payload is None:
            message = (
                response.payload.get("message", "Lokaler Dienst hat die Anfrage blockiert.")
                if response.payload
                else "Lokaler Dienst hat keine strukturierte Antwort geliefert."
            )
            raise FolderHomeAgentError(str(message))
        record_tool(tool_name, payload, response.payload)
        return response.payload

    @tool(name="search_home_documents")
    def search_home_documents(query: str, limit: int = 5) -> dict[str, object]:
        """Search the local FolderHome document index without accepting file paths."""

        return call_local("search_home_documents", query, limit)

    @tool(name="build_home_theme_dossier")
    def build_home_theme_dossier(query: str, limit: int = 5) -> dict[str, object]:
        """Build an evidence-linked local dossier for one topic without writing files."""

        return call_local("build_home_theme_dossier", query, limit)

    @tool(name="list_home_capabilities")
    def list_home_capabilities(language: str = "en") -> dict[str, object]:
        """List verified FolderHome roles, personas and endpoints; do not infer intent."""

        ensure_tool_budget()
        if language not in {"de", "en"}:
            raise FolderHomeAgentError("Sprache muss de oder en sein.")
        payload = {"language": language}
        result = _runtime_agent_catalog(application, language=language)
        record_tool("list_home_capabilities", payload, result)
        return result

    @tool(name="list_home_resources")
    def list_home_resources() -> dict[str, object]:
        """List profile-scoped logical resource IDs without revealing local paths."""

        ensure_tool_budget()
        payload: dict[str, object] = {}
        result = application.resource_catalog_payload(profile_id)
        record_tool("list_home_resources", payload, result)
        return result

    @tool(name="consult_home_specialist")
    def consult_home_specialist(
        expert_id: str,
        workflow_id: str,
        request: str,
        persona_id: str = "",
        language: str = "en",
    ) -> dict[str, object]:
        """Create one scoped planning-only specialist for a verified workflow endpoint."""

        ensure_tool_budget()
        result, plan, delegation = consult_folderhome_specialist(
            application=application,
            request=request,
            profile_id=profile_id,
            expert_id=expert_id,
            workflow_id=workflow_id,
            persona_id=persona_id or None,
            language=language,
            settings=settings,
        )
        payload = {
            "expert_id": expert_id,
            "workflow_id": workflow_id,
            "request": request,
            "persona_id": persona_id,
            "language": language,
        }
        record_tool("consult_home_specialist", payload, result)
        proposed_plans.append(plan)
        delegations.append(delegation)
        return result

    model = _build_model(settings)
    messages = _validated_prior_messages(
        prior_messages,
        max_messages=settings.max_conversation_messages,
    )
    agent = Agent(
        model=model,
        messages=messages,
        tools=[
            search_home_documents,
            build_home_theme_dossier,
            list_home_capabilities,
            list_home_resources,
            consult_home_specialist,
        ],
        system_prompt=_system_prompt(profile_id),
        callback_handler=None,
        conversation_manager=SlidingWindowConversationManager(
            window_size=settings.max_conversation_messages,
            should_truncate_results=True,
        ),
        tool_executor=SequentialToolExecutor(),
        agent_id="folderhome-master-agent",
        name="FolderHome",
        description="Lokaler Dokument- und Assistenzservice-Agent.",
    )
    result = agent(
        prompt.strip(),
        limits={
            "turns": settings.max_turns,
            "output_tokens": settings.max_output_tokens,
        },
    )
    response_text = str(result).strip()
    if len(response_text) > settings.max_response_chars:
        raise FolderHomeAgentError("Agentenantwort überschreitet das Zeichenbudget.")
    try:
        framework_version = version("strands-agents")
    except PackageNotFoundError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError("Strands-Paketversion ist nicht feststellbar.") from exc
    report = FolderHomeAgentReport(
        framework="strands-agents",
        framework_version=framework_version,
        model_provider=settings.model_provider,
        organizational_profile_id=profile_id,
        prompt_sha256=sha256(prompt.strip().encode("utf-8")).hexdigest(),
        response_text=response_text,
        stop_reason=str(result.stop_reason),
        model_turns=int(result.metrics.cycle_count),
        tool_events=tuple(events),
        network_used=settings.network_used,
        sensitive_cloud_data_authorized=settings.allow_sensitive_cloud_data,
        delegation_events=tuple(delegations),
        proposed_plans=tuple(proposed_plans),
    )
    retained_messages = tuple(deepcopy(agent.messages))
    if len(retained_messages) > settings.max_conversation_messages:
        raise FolderHomeAgentError("Gesprächsverlauf überschreitet das Nachrichtenbudget.")
    return report, retained_messages


def consult_folderhome_specialist(
    *,
    application: LocalApplication,
    request: str,
    profile_id: str,
    expert_id: str,
    workflow_id: str,
    persona_id: str | None,
    language: str,
    settings: StrandsAgentSettings,
):
    """Run one short-lived specialist with one allowlisted planning tool."""

    if language not in {"de", "en"}:
        raise FolderHomeAgentError("Sprache muss de oder en sein.")
    if profile_id not in {item.profile_id for item in application.profiles.profiles}:
        raise FolderHomeAgentError("Profil ist in diesem Betriebssystemkonto nicht bekannt.")
    try:
        route = resolve_master_route(
            expert_id=expert_id,
            workflow_ids=(workflow_id,),
            persona_id=persona_id,
            confidence="medium",
            why="The master agent selected this explicit expert and workflow endpoint.",
        )
    except (MasterAgentError, ValueError) as exc:
        raise FolderHomeAgentError(str(exc)) from exc
    try:
        from strands import Agent, tool
        from strands.tools.executors import SequentialToolExecutor
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError(
            "Strands Agents SDK fehlt; installiere die Projektabhängigkeiten."
        ) from exc

    workflow_descriptor = application.workflow_executor.descriptor(workflow_id)
    resource_contract = json.dumps(
        application.resource_catalog_payload(profile_id),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if workflow_descriptor.status == "connected":
        request_contract = json.dumps(
            workflow_descriptor.request_schema,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    else:
        request_contract = (
            "No typed executor is connected. Pass the empty JSON object {} and only "
            "produce a planning-only proposal."
        )
    plans = []

    @tool(name="propose_home_workflow")
    def propose_home_workflow(
        goal: str,
        request_json: str = "{}",
    ) -> dict[str, object]:
        """Build a non-executing, approval-bound plan for the one scoped workflow."""

        try:
            execution_envelopes = {}
            if workflow_descriptor.status == "connected":
                try:
                    request_payload = json.loads(request_json)
                except json.JSONDecodeError as exc:
                    raise FolderHomeAgentError(
                        "Fachagent lieferte keine gültigen typisierten Workflowdaten."
                    ) from exc
                if not isinstance(request_payload, dict):
                    raise FolderHomeAgentError(
                        "Typisierte Workflowdaten müssen ein JSON-Objekt sein."
                    )
                execution_envelopes[workflow_id] = application.workflow_executor.prepare(
                    workflow_id=workflow_id,
                    profile_id=profile_id,
                    request=request_payload,
                )
            public_goal = goal
            if execution_envelopes:
                public_goal = (
                    f"Vorbereiteten typisierten Fachplan für {workflow_id} ausführen."
                    if language == "de"
                    else f"Execute the prepared typed domain plan for {workflow_id}."
                )
            plan = build_master_agent_plan(
                public_goal,
                profile_id=profile_id,
                language=language,
                expert_id=expert_id,
                workflow_ids=(workflow_id,),
                persona_id=persona_id,
                confidence="medium",
                why="The scoped specialist proposed its single verified workflow endpoint.",
                execution_envelopes=execution_envelopes,
            )
        except (MasterAgentError, WorkflowExecutionError, ValueError) as exc:
            raise FolderHomeAgentError(str(exc)) from exc
        plans.append(plan)
        return plan.to_dict()

    persona_style = ""
    if persona_id is not None:
        personas = {item.persona_id: item for item in master_persona_catalog()}
        persona = personas[persona_id]
        persona_style = persona.style_de if language == "de" else persona.style_en
    experts = {item.expert_id: item for item in master_expert_catalog()}
    expert = experts[expert_id]
    expert_description = (
        expert.description_de if language == "de" else expert.description_en
    )
    subagent_id = f"folderhome-{expert_id}-{workflow_id}"
    agent = Agent(
        model=_build_model(settings, specialist_workflow_id=workflow_id),
        tools=[propose_home_workflow],
        system_prompt=(
            f"You are the bounded FolderHome specialist {expert_id}. {expert_description} "
            f"You may only propose workflow {workflow_id}. Call propose_home_workflow once. "
            f"The exact request_json contract is: {request_contract} "
            f"The profile-scoped logical resource catalog is: {resource_contract} "
            "For a connected workflow, request_json must satisfy that closed contract; "
            "never add unknown fields. "
            "Never execute, approve, broaden permissions, request arbitrary paths, "
            "or claim a result. "
            f"Persona overlay, which changes style only: {persona_style or 'none'}."
        ),
        callback_handler=None,
        tool_executor=SequentialToolExecutor(),
        agent_id=subagent_id,
        name=expert.title_en,
        description=expert.description_en,
    )
    result = agent(
        request.strip(),
        limits={"turns": settings.max_turns, "output_tokens": settings.max_output_tokens},
    )
    if len(plans) != 1:
        raise FolderHomeAgentError(
            "Fachagent hat keinen eindeutigen, geprüften Workflow-Plan erzeugt."
        )
    plan = plans[0]
    payload = {
        "schema": "folderhome.specialist-consultation.v1",
        "status": "planned",
        "subagent_id": subagent_id,
        "route": route.to_dict(),
        "response_text": str(result).strip(),
        "plan": plan.to_dict(),
        "execution_performed": False,
        "side_effects": [],
    }
    delegation = AgentDelegationEvent(
        sequence=1,
        expert_id=expert_id,
        workflow_id=workflow_id,
        persona_id=persona_id,
        request_sha256=sha256(request.strip().encode("utf-8")).hexdigest(),
        result_sha256=sha256(_json_bytes(payload)).hexdigest(),
        subagent_id=subagent_id,
    )
    return payload, plan, delegation


def plan_folderhome_agent(
    *,
    application: LocalApplication,
    settings: StrandsAgentSettings,
) -> dict[str, object]:
    """Describe the bounded agent surface without constructing or calling a model."""

    try:
        framework_version = version("strands-agents")
    except PackageNotFoundError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError("Strands-Paketversion ist nicht feststellbar.") from exc
    return {
        "schema": "folderhome.strands-agent-plan.v1",
        "framework": "strands-agents",
        "framework_version": framework_version,
        "settings": settings.to_dict(),
        "profile_ids": sorted(item.profile_id for item in application.profiles.profiles),
        "security_boundary": "operating_system_account",
        "profiles_are_authorization_boundaries": False,
        "agent_role": "folderhome_master",
        "routing_policy": "semantic_model_selection",
        "endpoint_resolution": "explicit_fail_closed",
        "specialist_lifecycle": "spawn_on_demand_planning_only",
        "executor_coverage": _executor_coverage(application),
        "tools": [
            "build_home_theme_dossier",
            "consult_home_specialist",
            "list_home_capabilities",
            "list_home_resources",
            "search_home_documents",
        ],
        "tool_execution": "sequential",
        "model_call_performed": False,
        "external_network_used": False,
        "side_effects": [],
    }


def _build_model(
    settings: StrandsAgentSettings,
    *,
    specialist_workflow_id: str | None = None,
):
    if settings.model_provider == "fixture":
        return _fixture_model_class()(
            specialist_workflow_id=specialist_workflow_id
        )
    if settings.model_provider == "ollama":
        try:
            from strands.models.ollama import OllamaModel
        except ImportError as exc:  # pragma: no cover - dependency contract
            raise FolderHomeAgentError(
                "Strands-Ollama-Provider ist nicht installiert: pip install 'folderhome[ollama]'"
            ) from exc
        return OllamaModel(
            settings.ollama_host,
            model_id=settings.ollama_model_id,
            max_tokens=settings.max_output_tokens,
        )
    try:
        from botocore.config import Config as BotocoreConfig
        from strands.models import BedrockModel
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError("Strands-Bedrock-Provider ist nicht verfügbar.") from exc
    return BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        max_tokens=settings.max_output_tokens,
        boto_client_config=BotocoreConfig(
            connect_timeout=settings.bedrock_connect_timeout_seconds,
            read_timeout=settings.bedrock_read_timeout_seconds,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )


def _system_prompt(profile_id: str) -> str:
    return (
        "You are FolderHome, the single conversational master agent for local document and "
        f"home assistance in organizational profile {profile_id}. Select domains and experts "
        "semantically from the user's meaning, never with a keyword table. Use direct read-only "
        "tools for simple document work. For bounded domain planning, call "
        "consult_home_specialist with an expert and workflow from list_home_capabilities. "
        "Use list_home_resources when a workflow needs configured local data or output; "
        "logical IDs never disclose or grant arbitrary paths. "
        "Respect each runtime executor status; never claim that not_connected or "
        "planning_only endpoints can execute. "
        "A persona changes communication style only; it never grants a tool or permission. "
        "Profiles organize information but are not authorization boundaries. Conversation is "
        "process-local and may be used to resolve follow-up references, but it is never an "
        "approval. Never execute a proposed workflow, invent evidence, diagnose, make "
        "legal, tax or benefit decisions, request arbitrary file paths, use a shell, or create "
        "external effects. Reply in the user's language.\n\n"
        "Endpoint index (purpose, required inputs, effect class). It states what "
        "exists in the code, not what this installation has configured; always "
        "confirm the live status through list_home_capabilities before promising "
        "execution:\n"
        f"{capability_index_prompt_excerpt(language='en')}"
    )


def _latest_user_text(messages) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        values = [
            block.get("text", "")
            for block in message.get("content", [])
            if isinstance(block, dict) and "text" in block
        ]
        if values:
            return "\n".join(values)
    raise FolderHomeAgentError("Fixture-Modell erhielt keinen Nutzerprompt.")


def _latest_tool_result(messages) -> dict[str, object] | None:
    for message in reversed(messages):
        if message.get("role") == "user" and any(
            isinstance(block, dict) and isinstance(block.get("text"), str)
            for block in message.get("content", [])
        ):
            return None
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            result = block["toolResult"]
            for content in result.get("content", []):
                if isinstance(content, dict) and isinstance(content.get("json"), dict):
                    return content["json"]
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    try:
                        payload = json.loads(content["text"])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict):
                        return payload
    return None


def _fixture_conversation_answer(messages) -> str | None:
    """Exercise retained Strands messages through one exact fixture-only schema."""

    current = _fixture_conversation_turn(_latest_user_text(messages))
    if current is None:
        return None
    remember, recall = current
    if remember is not None:
        return f"Stored fixture context for this process session: {remember}"
    if not recall:
        return "No retained fixture context is available."
    skipped_current = False
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        for block in reversed(message.get("content", [])):
            text = block.get("text") if isinstance(block, dict) else None
            if not isinstance(text, str):
                continue
            if not skipped_current:
                skipped_current = True
                continue
            previous = _fixture_conversation_turn(text)
            if previous is not None and previous[0] is not None:
                return f"Retained fixture context from this process session: {previous[0]}"
    return "No retained fixture context is available."


def _fixture_conversation_turn(prompt: str) -> tuple[str | None, bool] | None:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("schema") != (
        "folderhome.fixture-conversation-turn.v1"
    ):
        return None
    if set(payload) != {"schema", "remember", "recall"}:
        raise FolderHomeAgentError(
            "Fixture-Gesprächsanfrage besitzt unbekannte oder fehlende Felder."
        )
    remember = payload["remember"]
    recall = payload["recall"]
    if remember is not None and (
        not isinstance(remember, str) or not remember.strip() or len(remember) > 200
    ):
        raise FolderHomeAgentError("Fixture-Gesprächsanfrage besitzt ungültigen Kontext.")
    if not isinstance(recall, bool) or (remember is None) == (not recall):
        raise FolderHomeAgentError(
            "Fixture-Gesprächsanfrage muss genau speichern oder erinnern."
        )
    return remember.strip() if isinstance(remember, str) else None, recall


def _validated_prior_messages(
    messages: tuple[dict[str, Any], ...],
    *,
    max_messages: int,
) -> list[dict[str, Any]]:
    if len(messages) > max_messages:
        raise FolderHomeAgentError("Gesprächsverlauf überschreitet das Nachrichtenbudget.")
    copied = deepcopy(list(messages))
    for message in copied:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), list)
        ):
            raise FolderHomeAgentError("Gesprächsverlauf besitzt ein ungültiges Nachrichtenformat.")
    return copied


def _fixture_topic(prompt: str) -> str:
    match = _TOPIC.search(prompt)
    return match.group(1) if match else prompt.strip()


def _fixture_specialist_request(prompt: str) -> dict[str, object] | None:
    """Parse the exact deterministic QA schema without acting as an intent router."""

    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("schema") != (
        "folderhome.fixture-specialist-request.v1"
    ):
        return None
    expected = {
        "schema",
        "expert_id",
        "workflow_id",
        "persona_id",
        "language",
        "request",
    }
    if set(payload) != expected:
        raise FolderHomeAgentError(
            "Fixture-Fachanfrage besitzt unbekannte oder fehlende Felder."
        )
    for key in ("expert_id", "workflow_id", "language"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise FolderHomeAgentError(f"Fixture-Fachanfrage benötigt {key}.")
    persona_id = payload["persona_id"]
    if persona_id is not None and (
        not isinstance(persona_id, str) or not persona_id.strip()
    ):
        raise FolderHomeAgentError("Fixture-Fachanfrage besitzt keine gültige persona_id.")
    request = payload["request"]
    if not isinstance(request, dict):
        raise FolderHomeAgentError("Fixture-Fachanfrage benötigt ein request-Objekt.")
    return {
        "expert_id": payload["expert_id"],
        "workflow_id": payload["workflow_id"],
        "request": json.dumps(
            request,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        "persona_id": persona_id or "",
        "language": payload["language"],
    }


def _looks_german(prompt: str) -> bool:
    folded = f" {prompt.casefold()} "
    return any(
        marker in folded
        for marker in (
            " ich ",
            " meine ",
            " bitte ",
            " über ",
            " suche ",
            " erstelle ",
            " was ",
            " kannst ",
        )
    )


def _fixture_answer(payload: dict[str, object]) -> str:
    schema = payload.get("schema")
    if schema == "folderhome.logical-resource-catalog.v1":
        resources = payload.get("resources", [])
        resource_ids = (
            [
                item.get("resource_id")
                for item in resources
                if isinstance(item, dict)
                and isinstance(item.get("resource_id"), str)
            ]
            if isinstance(resources, list)
            else []
        )
        return "Configured logical resources: " + ", ".join(resource_ids)
    if schema == "folderhome.semantic-agent-catalog.v1":
        experts = payload.get("experts", [])
        gaps = payload.get("gaps", [])
        if payload.get("language") == "de":
            return (
                "FolderHome hat seinen geprüften Fähigkeitskatalog geladen. "
                f"{len(experts) if isinstance(experts, list) else 0} begrenzte "
                "Fachrollen sind verfügbar; "
                f"{len(gaps) if isinstance(gaps, list) else 0} sichtbare "
                "Adapterlücken bleiben bestehen."
            )
        return (
            "FolderHome has loaded its verified capability catalog. "
            f"{len(experts) if isinstance(experts, list) else 0} bounded expert "
            "roles are available; "
            f"{len(gaps) if isinstance(gaps, list) else 0} runtime adapter gaps "
            "remain visible."
        )
    if schema == "folderhome.master-agent-plan.v2":
        if payload.get("language") == "de":
            return (
                "Ein begrenzter Workflow-Plan wurde vorbereitet: "
                f"{payload.get('plan_id', 'unbekannt')}"
            )
        return f"A bounded workflow plan was prepared: {payload.get('plan_id', 'unknown')}"
    if schema == "folderhome.specialist-consultation.v1":
        plan = payload.get("plan")
        plan_id = plan.get("plan_id", "unknown") if isinstance(plan, dict) else "unknown"
        if isinstance(plan, dict) and plan.get("language") == "de":
            return f"Ein begrenzter Fachworkflow-Plan wurde vorbereitet: {plan_id}"
        return f"A bounded specialist workflow plan was prepared: {plan_id}"
    result = payload.get("result")
    if not isinstance(result, dict):
        return "Der lokale FolderHome-Dienst lieferte kein auswertbares Ergebnis."
    markdown = result.get("markdown")
    if isinstance(markdown, str):
        return "Der Strands-Agent hat das lokale Themendossier erstellt.\n\n" + markdown
    hits = result.get("hits")
    filenames = []
    if isinstance(hits, list):
        filenames = [
            item.get("filename")
            for item in hits
            if isinstance(item, dict) and isinstance(item.get("filename"), str)
        ]
    lines = ["Der Strands-Agent hat den lokalen Dokumentenindex durchsucht."]
    lines.extend(f"- {filename}" for filename in filenames)
    return "\n".join(lines)


async def _tool_events(tool_name: str, payload: dict[str, object]):
    yield {"messageStart": {"role": "assistant"}}
    yield {
        "contentBlockStart": {
            "start": {
                "toolUse": {
                    "toolUseId": "folderhome-fixture-tool-0001",
                    "name": tool_name,
                }
            }
        }
    }
    yield {
        "contentBlockDelta": {
            "delta": {"toolUse": {"input": json.dumps(payload, ensure_ascii=False)}}
        }
    }
    yield {"contentBlockStop": {}}
    yield {"messageStop": {"stopReason": "tool_use"}}
    yield {
        "metadata": {
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "metrics": {"latencyMs": 0},
        }
    }


async def _text_events(text: str):
    yield {"messageStart": {"role": "assistant"}}
    yield {"contentBlockStart": {"start": {}}}
    yield {"contentBlockDelta": {"delta": {"text": text}}}
    yield {"contentBlockStop": {}}
    yield {"messageStop": {"stopReason": "end_turn"}}
    yield {
        "metadata": {
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "metrics": {"latencyMs": 0},
        }
    }


def _runtime_agent_catalog(
    application: LocalApplication,
    *,
    language: str,
) -> dict[str, object]:
    catalog = master_agent_catalog(language=language)
    executors = [item.to_dict() for item in application.workflow_executor.catalog()]
    catalog["executors"] = executors
    catalog["executor_coverage"] = _executor_coverage(application)
    catalog["gaps"] = [
        item["workflow_id"]
        for item in executors
        if item["status"] == "not_connected"
    ]
    return catalog


def _executor_coverage(application: LocalApplication) -> dict[str, int]:
    return application.workflow_executor.coverage()


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


__all__ = [
    "FolderHomeAgentError",
    "StrandsAgentSettings",
    "consult_folderhome_specialist",
    "plan_folderhome_agent",
    "run_folderhome_agent",
    "run_folderhome_agent_turn",
]
