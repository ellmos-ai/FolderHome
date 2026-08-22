"""Contracts for the bounded Strands Agents orchestration layer."""

from __future__ import annotations

import re
from dataclasses import dataclass

_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,254}")
_AWS_REGION = re.compile(r"[a-z]{2}(?:-gov)?-[a-z]+-\d")


@dataclass(frozen=True, slots=True)
class StrandsAgentSettings:
    """Finite execution and provider policy for one FolderHome agent."""

    model_provider: str = "fixture"
    bedrock_model_id: str | None = None
    aws_region: str | None = None
    allow_network: bool = False
    allow_sensitive_cloud_data: bool = False
    max_turns: int = 4
    max_tool_calls: int = 4
    max_prompt_chars: int = 1_000
    max_response_chars: int = 20_000
    max_tool_result_bytes: int = 1_048_576
    max_output_tokens: int = 4_096

    SCHEMA = "folderhome.strands-agent-settings.v1"

    def __post_init__(self) -> None:
        if self.model_provider not in {"fixture", "bedrock"}:
            raise ValueError("model_provider muss fixture oder bedrock sein.")
        limits = {
            "max_turns": (self.max_turns, 1, 8),
            "max_tool_calls": (self.max_tool_calls, 1, 8),
            "max_prompt_chars": (self.max_prompt_chars, 1, 4_000),
            "max_response_chars": (self.max_response_chars, 1, 100_000),
            "max_tool_result_bytes": (self.max_tool_result_bytes, 1, 2_097_152),
            "max_output_tokens": (self.max_output_tokens, 1, 8_192),
        }
        for name, (value, minimum, maximum) in limits.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise ValueError(f"{name} muss zwischen {minimum} und {maximum} liegen.")
        if self.model_provider == "fixture":
            if (
                self.allow_network
                or self.allow_sensitive_cloud_data
                or self.bedrock_model_id is not None
                or self.aws_region is not None
            ):
                raise ValueError("Fixture-Modus darf keine Netzwerk- oder Bedrock-Angaben tragen.")
            return
        if not self.allow_network:
            raise ValueError("Bedrock benötigt eine ausdrückliche Netzwerkfreigabe.")
        if not self.allow_sensitive_cloud_data:
            raise ValueError(
                "Bedrock benötigt eine getrennte ausdrückliche Datenweitergabefreigabe."
            )
        if self.bedrock_model_id is None or _MODEL_ID.fullmatch(self.bedrock_model_id) is None:
            raise ValueError("Bedrock benötigt eine gültige explizite Modell-ID.")
        if self.aws_region is None or _AWS_REGION.fullmatch(self.aws_region) is None:
            raise ValueError("Bedrock benötigt eine gültige explizite AWS-Region.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "model_provider": self.model_provider,
            "bedrock_model_id": self.bedrock_model_id,
            "aws_region": self.aws_region,
            "allow_network": self.allow_network,
            "allow_sensitive_cloud_data": self.allow_sensitive_cloud_data,
            "max_turns": self.max_turns,
            "max_tool_calls": self.max_tool_calls,
            "max_prompt_chars": self.max_prompt_chars,
            "max_response_chars": self.max_response_chars,
            "max_tool_result_bytes": self.max_tool_result_bytes,
            "max_output_tokens": self.max_output_tokens,
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
            "side_effects": list(self.side_effects),
            "security_boundary": self.security_boundary,
            "profiles_are_authorization_boundaries": (
                self.profiles_are_authorization_boundaries
            ),
        }
