"""Bounded Strands Agents loop over FolderHome's read-only application services."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterable
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from folderhome.application.local_app import LocalApplication
from folderhome.contracts.strands_agent import (
    AgentToolEvent,
    FolderHomeAgentReport,
    StrandsAgentSettings,
)

_TOPIC = re.compile(
    r"\b(?:zur|zum|über|thema)\s+([A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9-]{2,80})",
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
        def __init__(self) -> None:
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
            available = {
                item.get("name")
                for item in (tool_specs or [])
                if isinstance(item, dict)
            }
            is_dossier = any(
                marker in prompt_text.casefold()
                for marker in ("alles", "dossier", "zusammenfass", "thema")
            )
            tool_name = (
                "build_home_theme_dossier" if is_dossier else "search_home_documents"
            )
            if tool_name not in available:
                raise FolderHomeAgentError(f"Benötigtes Strands-Tool fehlt: {tool_name}")
            query = _fixture_topic(prompt_text) if is_dossier else prompt_text.strip()
            async for event in _tool_events(tool_name, {"query": query, "limit": 5}):
                yield event

    return FixtureFolderHomeModel


def run_folderhome_agent(
    *,
    application: LocalApplication,
    prompt: str,
    profile_id: str,
    settings: StrandsAgentSettings,
) -> FolderHomeAgentReport:
    """Run one finite Strands loop over profile-bound read-only local tools."""

    if not prompt.strip() or len(prompt) > settings.max_prompt_chars:
        raise FolderHomeAgentError(
            f"Prompt benötigt 1 bis {settings.max_prompt_chars} Zeichen."
        )
    known_profiles = {item.profile_id for item in application.profiles.profiles}
    if profile_id not in known_profiles:
        raise FolderHomeAgentError("Profil ist in diesem Betriebssystemkonto nicht bekannt.")
    try:
        from strands import Agent, tool
        from strands.tools.executors import SequentialToolExecutor
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError(
            "Strands Agents SDK fehlt; installiere die Projektabhängigkeiten."
        ) from exc

    events: list[AgentToolEvent] = []

    def call_local(tool_name: str, query: str, limit: int) -> dict[str, object]:
        if len(events) >= settings.max_tool_calls:
            raise FolderHomeAgentError("Strands-Toolbudget ist ausgeschöpft.")
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
        result_bytes = _json_bytes(response.payload)
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
        return response.payload

    @tool(name="search_home_documents")
    def search_home_documents(query: str, limit: int = 5) -> dict[str, object]:
        """Search the local FolderHome document index without accepting file paths."""

        return call_local("search_home_documents", query, limit)

    @tool(name="build_home_theme_dossier")
    def build_home_theme_dossier(query: str, limit: int = 5) -> dict[str, object]:
        """Build an evidence-linked local dossier for one topic without writing files."""

        return call_local("build_home_theme_dossier", query, limit)

    model = _build_model(settings)
    agent = Agent(
        model=model,
        tools=[search_home_documents, build_home_theme_dossier],
        system_prompt=_system_prompt(profile_id),
        callback_handler=None,
        tool_executor=SequentialToolExecutor(),
        agent_id="folderhome-home-agent",
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
    return FolderHomeAgentReport(
        framework="strands-agents",
        framework_version=framework_version,
        model_provider=settings.model_provider,
        organizational_profile_id=profile_id,
        prompt_sha256=sha256(prompt.strip().encode("utf-8")).hexdigest(),
        response_text=response_text,
        stop_reason=str(result.stop_reason),
        model_turns=int(result.metrics.cycle_count),
        tool_events=tuple(events),
        network_used=settings.model_provider == "bedrock",
        sensitive_cloud_data_authorized=settings.allow_sensitive_cloud_data,
    )


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
        "tools": ["build_home_theme_dossier", "search_home_documents"],
        "tool_execution": "sequential",
        "model_call_performed": False,
        "external_network_used": False,
        "side_effects": [],
    }


def _build_model(settings: StrandsAgentSettings):
    if settings.model_provider == "fixture":
        return _fixture_model_class()()
    try:
        from strands.models import BedrockModel
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise FolderHomeAgentError("Strands-Bedrock-Provider ist nicht verfügbar.") from exc
    return BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        max_tokens=settings.max_output_tokens,
    )


def _system_prompt(profile_id: str) -> str:
    return (
        "Du bist FolderHome, ein lokaler Dokument- und Assistenzservice-Agent. "
        f"Nutze ausschließlich die bereitgestellten read-only Tools für Profil {profile_id}. "
        "Profile sind organisatorisch und keine Berechtigungsgrenzen. Gib keine Diagnose, "
        "Rechts-, Steuer- oder Leistungsentscheidung aus. Erfinde keine Fundstellen. "
        "Fordere keine freien Dateipfade an und führe keine Außenwirkung aus."
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


def _fixture_topic(prompt: str) -> str:
    match = _TOPIC.search(prompt)
    return match.group(1) if match else prompt.strip()


def _fixture_answer(payload: dict[str, object]) -> str:
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
    "plan_folderhome_agent",
    "run_folderhome_agent",
]
