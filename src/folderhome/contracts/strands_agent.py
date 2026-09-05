"""Contracts for the bounded Strands Agents orchestration layer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from folderhome.contracts.master_agent import MasterAgentPlan

_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,254}")
_AWS_REGION = re.compile(r"[a-z]{2}(?:-gov)?-[a-z]+-\d")
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
# Which settings belong to which provider. Every other provider field must stay
# unset, so one table replaces a growing cross product of pairwise checks.
_PROVIDER_FIELDS: dict[str, tuple[str, ...]] = {
    "fixture": (),
    "bedrock": ("bedrock_model_id", "aws_region"),
    "ollama": ("ollama_host", "ollama_model_id"),
    "anthropic": ("anthropic_model_id",),
    "openai": ("openai_model_id", "openai_base_url"),
}
_PROVIDER_LABELS = {
    "fixture": "Fixture",
    "bedrock": "Bedrock",
    "ollama": "Ollama",
    "anthropic": "Anthropic",
    "openai": "OpenAI",
}
# Providers that answer from someone else's machine, whatever their address.
_HOSTED_PROVIDERS = frozenset({"bedrock", "anthropic", "openai"})


def _parsed_model_host(value: str | None) -> SplitResult | None:
    """Return the parsed host only when it is an explicit http(s) endpoint."""

    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return parsed


@dataclass(frozen=True, slots=True)
class StrandsAgentSettings:
    """Finite execution and provider policy for one FolderHome agent."""

    model_provider: str = "fixture"
    bedrock_model_id: str | None = None
    aws_region: str | None = None
    ollama_host: str | None = None
    ollama_model_id: str | None = None
    anthropic_model_id: str | None = None
    openai_model_id: str | None = None
    openai_base_url: str | None = None
    allow_network: bool = False
    allow_sensitive_cloud_data: bool = False
    max_turns: int = 4
    max_tool_calls: int = 4
    max_prompt_chars: int = 1_000
    max_response_chars: int = 20_000
    max_tool_result_bytes: int = 1_048_576
    max_output_tokens: int = 4_096
    max_conversation_messages: int = 24
    bedrock_connect_timeout_seconds: int = 5
    bedrock_read_timeout_seconds: int = 30

    SCHEMA = "folderhome.strands-agent-settings.v1"

    def __post_init__(self) -> None:
        if self.model_provider not in _PROVIDER_FIELDS:
            raise ValueError(
                "model_provider muss "
                + ", ".join(sorted(_PROVIDER_FIELDS))
                + " sein."
            )
        limits = {
            "max_turns": (self.max_turns, 1, 8),
            "max_tool_calls": (self.max_tool_calls, 1, 8),
            "max_prompt_chars": (self.max_prompt_chars, 1, 4_000),
            "max_response_chars": (self.max_response_chars, 1, 100_000),
            "max_tool_result_bytes": (self.max_tool_result_bytes, 1, 2_097_152),
            "max_output_tokens": (self.max_output_tokens, 1, 8_192),
            "max_conversation_messages": (
                self.max_conversation_messages,
                4,
                64,
            ),
            "bedrock_connect_timeout_seconds": (
                self.bedrock_connect_timeout_seconds,
                1,
                30,
            ),
            "bedrock_read_timeout_seconds": (
                self.bedrock_read_timeout_seconds,
                1,
                120,
            ),
        }
        for name, (value, minimum, maximum) in limits.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise ValueError(f"{name} muss zwischen {minimum} und {maximum} liegen.")
        label = _PROVIDER_LABELS[self.model_provider]
        own = _PROVIDER_FIELDS[self.model_provider]
        foreign = [
            name
            for fields in _PROVIDER_FIELDS.values()
            for name in fields
            if name not in own and getattr(self, name) is not None
        ]
        if foreign:
            raise ValueError(
                f"{label}-Modus darf keine fremden Provider-Angaben tragen: "
                + ", ".join(sorted(foreign))
                + "."
            )
        if self.model_provider == "fixture":
            if self.allow_network or self.allow_sensitive_cloud_data:
                raise ValueError("Fixture-Modus darf keine Netzwerkfreigaben tragen.")
            return
        if self.model_provider == "ollama":
            if (
                self.ollama_model_id is None
                or _MODEL_ID.fullmatch(self.ollama_model_id) is None
            ):
                raise ValueError("Ollama benötigt eine gültige explizite Modell-ID.")
            if _parsed_model_host(self.ollama_host) is None:
                raise ValueError(
                    "Ollama benötigt einen expliziten Host mit http:// oder https://."
                )
            if not self.network_used:
                return
            if not self.allow_network:
                raise ValueError(
                    "Ollama außerhalb der Loopback-Adresse benötigt eine ausdrückliche "
                    "Netzwerkfreigabe."
                )
            if not self.allow_sensitive_cloud_data:
                raise ValueError(
                    "Ollama außerhalb der Loopback-Adresse benötigt eine getrennte "
                    "ausdrückliche Datenweitergabefreigabe."
                )
            return
        if not self.allow_network:
            raise ValueError(f"{label} benötigt eine ausdrückliche Netzwerkfreigabe.")
        if not self.allow_sensitive_cloud_data:
            raise ValueError(
                f"{label} benötigt eine getrennte ausdrückliche Datenweitergabefreigabe."
            )
        if self.model_provider == "anthropic":
            if _MODEL_ID.fullmatch(self.anthropic_model_id or "") is None:
                raise ValueError("Anthropic benötigt eine gültige explizite Modell-ID.")
            return
        if self.model_provider == "openai":
            if _MODEL_ID.fullmatch(self.openai_model_id or "") is None:
                raise ValueError("OpenAI benötigt eine gültige explizite Modell-ID.")
            if (
                self.openai_base_url is not None
                and _parsed_model_host(self.openai_base_url) is None
            ):
                raise ValueError(
                    "OpenAI-Basis-URL benötigt http:// oder https://."
                )
            return
        if self.bedrock_model_id is None or _MODEL_ID.fullmatch(self.bedrock_model_id) is None:
            raise ValueError("Bedrock benötigt eine gültige explizite Modell-ID.")
        if self.aws_region is None or _AWS_REGION.fullmatch(self.aws_region) is None:
            raise ValueError("Bedrock benötigt eine gültige explizite AWS-Region.")

    @property
    def network_used(self) -> bool:
        """Report whether this provider leaves the loopback interface."""

        if self.model_provider in _HOSTED_PROVIDERS:
            return True
        if self.model_provider != "ollama":
            return False
        parsed = _parsed_model_host(self.ollama_host)
        return parsed is None or parsed.hostname.lower() not in _LOOPBACK_HOSTS

    @property
    def is_live_model(self) -> bool:
        """Report whether a real model answers instead of the deterministic fixture."""

        return self.model_provider != "fixture"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "model_provider": self.model_provider,
            "bedrock_model_id": self.bedrock_model_id,
            "aws_region": self.aws_region,
            "ollama_host": self.ollama_host,
            "ollama_model_id": self.ollama_model_id,
            "anthropic_model_id": self.anthropic_model_id,
            "openai_model_id": self.openai_model_id,
            "openai_base_url": self.openai_base_url,
            "network_used": self.network_used,
            "allow_network": self.allow_network,
            "allow_sensitive_cloud_data": self.allow_sensitive_cloud_data,
            "max_turns": self.max_turns,
            "max_tool_calls": self.max_tool_calls,
            "max_prompt_chars": self.max_prompt_chars,
            "max_response_chars": self.max_response_chars,
            "max_tool_result_bytes": self.max_tool_result_bytes,
            "max_output_tokens": self.max_output_tokens,
            "max_conversation_messages": self.max_conversation_messages,
            "bedrock_connect_timeout_seconds": self.bedrock_connect_timeout_seconds,
            "bedrock_read_timeout_seconds": self.bedrock_read_timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class AgentToolEvent:
    """One bounded, hash-bound read-only tool execution."""

    sequence: int
    tool_name: str
    input_sha256: str
    result_sha256: str
    status: str = "executed"
    side_effects: tuple[str, ...] = ()

    SCHEMA = "folderhome.strands-tool-event.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "input_sha256": self.input_sha256,
            "result_sha256": self.result_sha256,
            "status": self.status,
            "side_effects": list(self.side_effects),
        }


@dataclass(frozen=True, slots=True)
class AgentDelegationEvent:
    """One bounded specialist agent created by the master agent."""

    sequence: int
    expert_id: str
    workflow_id: str
    persona_id: str | None
    request_sha256: str
    result_sha256: str
    subagent_id: str
    status: str = "planned"
    side_effects: tuple[str, ...] = ()

    SCHEMA = "folderhome.agent-delegation-event.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "sequence": self.sequence,
            "expert_id": self.expert_id,
            "workflow_id": self.workflow_id,
            "persona_id": self.persona_id,
            "request_sha256": self.request_sha256,
            "result_sha256": self.result_sha256,
            "subagent_id": self.subagent_id,
            "status": self.status,
            "side_effects": list(self.side_effects),
        }


@dataclass(frozen=True, slots=True)
class FolderHomeAgentReport:
    """Auditable result of one Strands-driven FolderHome request."""

    framework: str
    framework_version: str
    model_provider: str
    organizational_profile_id: str
    prompt_sha256: str
    response_text: str
    stop_reason: str
    model_turns: int
    tool_events: tuple[AgentToolEvent, ...]
    network_used: bool
    sensitive_cloud_data_authorized: bool
    delegation_events: tuple[AgentDelegationEvent, ...] = ()
    proposed_plans: tuple[MasterAgentPlan, ...] = ()
    side_effects: tuple[str, ...] = ()
    security_boundary: str = "operating_system_account"
    profiles_are_authorization_boundaries: bool = False

    SCHEMA = "folderhome.strands-agent-report.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "model_provider": self.model_provider,
            "organizational_profile_id": self.organizational_profile_id,
            "prompt_sha256": self.prompt_sha256,
            "response_text": self.response_text,
            "stop_reason": self.stop_reason,
            "model_turns": self.model_turns,
            "tool_events": [item.to_dict() for item in self.tool_events],
            "network_used": self.network_used,
            "sensitive_cloud_data_authorized": self.sensitive_cloud_data_authorized,
            "delegation_events": [item.to_dict() for item in self.delegation_events],
            "proposed_plans": [item.to_dict() for item in self.proposed_plans],
            "side_effects": list(self.side_effects),
            "security_boundary": self.security_boundary,
            "profiles_are_authorization_boundaries": (
                self.profiles_are_authorization_boundaries
            ),
        }
