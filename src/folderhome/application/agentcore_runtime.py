"""AWS Bedrock AgentCore HTTP adapter for the synthetic accident journey."""

from __future__ import annotations

import json
import threading
from hashlib import sha256
from pathlib import Path

from folderhome.application.accident_demo import (
    SyntheticAccidentDemo,
    SyntheticAccidentDemoError,
)
from folderhome.contracts.local_app import LocalApiResponse
from folderhome.contracts.strands_agent import StrandsAgentSettings

_SESSION_HEADER = "x-amzn-bedrock-agentcore-runtime-session-id"
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class AgentCoreRuntimeApplication:
    """Map the AgentCore HTTP contract to isolated synthetic demo sessions."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        max_body_bytes: int = 32_768,
        max_sessions: int = 32,
        max_concurrent_requests: int = 8,
        request_timeout_seconds: float = 30.0,
        agent_settings: StrandsAgentSettings | None = None,
        specialist_agent_settings: StrandsAgentSettings | None = None,
    ) -> None:
        root = workspace_root.resolve()
        if root == Path(root.anchor):
            raise ValueError("AgentCore workspace may not be a filesystem root.")
        if not isinstance(max_body_bytes, int) or isinstance(
            max_body_bytes, bool
        ) or not 1_024 <= max_body_bytes <= 1_048_576:
            raise ValueError("AgentCore body limit must be between 1024 and 1048576 bytes.")
        if not isinstance(max_sessions, int) or isinstance(
            max_sessions, bool
        ) or not 1 <= max_sessions <= 256:
            raise ValueError("AgentCore session capacity must be between 1 and 256.")
        if (
            not isinstance(max_concurrent_requests, int)
            or isinstance(max_concurrent_requests, bool)
            or not 1 <= max_concurrent_requests <= 64
        ):
            raise ValueError("AgentCore concurrency limit must be between 1 and 64.")
        if (
            not isinstance(request_timeout_seconds, (int, float))
            or isinstance(request_timeout_seconds, bool)
            or not 0.1 <= request_timeout_seconds <= 60.0
        ):
            raise ValueError("AgentCore request timeout must be between 0.1 and 60 seconds.")
        self.workspace_root = root
        self.max_body_bytes = max_body_bytes
        self.max_sessions = max_sessions
        self.max_concurrent_requests = max_concurrent_requests
        self.request_timeout_seconds = float(request_timeout_seconds)
        self.agent_settings = agent_settings or StrandsAgentSettings(
            model_provider="fixture",
            max_conversation_messages=64,
        )
        self.model_provider = self.agent_settings.model_provider
        self.specialist_agent_settings = (
            specialist_agent_settings or self.agent_settings
        )
        self.specialist_model_provider = self.specialist_agent_settings.model_provider
        self._sessions: dict[str, SyntheticAccidentDemo] = {}
        self._lock = threading.RLock()

    def handle(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
    ) -> LocalApiResponse:
        folded_headers = {key.casefold(): value for key, value in headers.items()}
        if method.upper() == "GET" and path == "/ping":
            return self._json(200, {"status": "Healthy"})
        if path != "/invocations":
            return self._error(404, "Unknown AgentCore endpoint.")
        if method.upper() != "POST":
            return self._error(405, "Only POST is allowed for /invocations.")
        if len(body) > self.max_body_bytes:
            return self._error(413, "Invocation body exceeds the configured limit.")
        if not folded_headers.get("content-type", "").casefold().startswith(
            "application/json"
        ):
            return self._error(415, "Content-Type must be application/json.")
        try:
            session_id = self._session_id(folded_headers)
            prompt = self._prompt(body)
            demo = self._demo_for_session(session_id)
            if prompt == "/reset":
                reset = demo.reset()
                self._drop_session(session_id)
                return self._json(
                    200,
                    {
                        "schema": "folderhome.agentcore-response.v1",
                        "response": "The synthetic accident workspace was reset.",
                        "reset": reset,
                        "synthetic_data_only": True,
                        "external_network_used": False,
                        "model_provider": self.model_provider,
                        "specialist_model_provider": self.specialist_model_provider,
                    },
                )
            if prompt.startswith("/confirm"):
                result = demo.confirm(prompt)
                return self._json(
                    200,
                    {
                        "schema": "folderhome.agentcore-response.v1",
                        "response": (
                            "The exact plan was confirmed and executed with local, "
                            "reversible FolderHome adapters."
                        ),
                        "result": result,
                        "synthetic_data_only": True,
                        "external_network_used": result["network_used"],
                        "model_provider": self.model_provider,
                        "specialist_model_provider": self.specialist_model_provider,
                    },
                )
            plan = demo.prepare(prompt)
            return self._json(
                200,
                {
                    "schema": "folderhome.agentcore-response.v1",
                    "response": (
                        "I found the synthetic current and older Hyundai i10 policies. "
                        f"Review the plan, then send {plan['confirmation_command']} exactly."
                    ),
                    "plan": plan,
                    "synthetic_data_only": True,
                    "external_network_used": plan["network_used"],
                    "model_provider": self.model_provider,
                    "specialist_model_provider": self.specialist_model_provider,
                },
            )
        except AgentCoreRuntimeCapacityError as exc:
            return self._error(503, str(exc))
        except (SyntheticAccidentDemoError, UnicodeError, ValueError) as exc:
            return self._error(400, str(exc))
        except OSError:
            return self._error(500, "The synthetic runtime workspace is unavailable.")

    @staticmethod
    def _session_id(headers: dict[str, str]) -> str:
        value = headers.get(_SESSION_HEADER, "")
        if not 33 <= len(value) <= 512 or value != value.strip():
            raise ValueError(
                "A valid AgentCore runtime session header of at least 33 characters is required."
            )
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("AgentCore runtime session header contains control characters.")
        return value

    @staticmethod
    def _prompt(body: bytes) -> str:
        try:
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object)
        except json.JSONDecodeError as exc:
            raise ValueError("Invocation body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invocation body must be a JSON object.")
        if set(payload) == {"prompt"}:
            prompt = payload["prompt"]
        elif set(payload) == {"input"} and isinstance(payload["input"], dict):
            nested = payload["input"]
            if set(nested) != {"prompt"}:
                raise ValueError("Nested input must contain exactly prompt.")
            prompt = nested["prompt"]
        else:
            raise ValueError("Invocation must contain exactly prompt or input.prompt.")
        if not isinstance(prompt, str):
            raise ValueError("Invocation prompt must be text.")
        normalized = " ".join(prompt.split())
        if not 1 <= len(normalized) <= 1_000:
            raise ValueError("Invocation prompt must contain 1 to 1000 characters.")
        return normalized

    def _demo_for_session(self, session_id: str) -> SyntheticAccidentDemo:
        fingerprint = sha256(session_id.encode("utf-8")).hexdigest()
        with self._lock:
            demo = self._sessions.get(fingerprint)
            if demo is None:
                if len(self._sessions) >= self.max_sessions:
                    raise AgentCoreRuntimeCapacityError(
                        "AgentCore process-local session capacity is exhausted; reset an "
                        "existing synthetic session or start a fresh runtime."
                    )
                demo = SyntheticAccidentDemo(
                    self.workspace_root / fingerprint,
                    agent_settings=self.agent_settings,
                    specialist_agent_settings=self.specialist_agent_settings,
                )
                self._sessions[fingerprint] = demo
            return demo

    def _drop_session(self, session_id: str) -> None:
        fingerprint = sha256(session_id.encode("utf-8")).hexdigest()
        with self._lock:
            self._sessions.pop(fingerprint, None)

    @staticmethod
    def _json(status: int, payload: dict[str, object]) -> LocalApiResponse:
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return LocalApiResponse(
            status,
            "application/json; charset=utf-8",
            content,
            dict(_SECURITY_HEADERS),
            payload,
        )

    @classmethod
    def _error(cls, status: int, message: str) -> LocalApiResponse:
        return cls._json(
            status,
            {
                "schema": "folderhome.agentcore-error.v1",
                "status": "blocked",
                "error": message,
            },
        )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"Duplicate JSON key is not allowed: {key}")
        payload[key] = value
    return payload


class AgentCoreRuntimeCapacityError(RuntimeError):
    """Raised when a bounded AgentCore process has no free session slot."""
