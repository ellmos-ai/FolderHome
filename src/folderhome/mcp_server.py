"""Model Context Protocol proxy over the loopback API of a running FolderHome app.

The proxy owns no state. It forwards every call to the loopback HTTP API of an
``app serve`` process, so an editor agent and the FolderHome GUI share one
process, one conversation and one set of proposed plans. stdout belongs to the
MCP transport; diagnostics go to stderr.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ACCESS_URL_ENV = "FOLDERHOME_ACCESS_URL"
_LOOPBACK_HOST = "127.0.0.1"
_REQUEST_TIMEOUT_SECONDS = 300


class McpServerError(RuntimeError):
    """Raised before an unapproved or non-loopback MCP proxy is started."""


class FolderHomeApiClient:
    """Bounded loopback client for one running FolderHome application."""

    def __init__(self, access_url: str) -> None:
        parsed = urllib.parse.urlsplit(access_url)
        if parsed.scheme != "http" or not parsed.hostname:
            raise McpServerError(
                "Zugriffs-URL benötigt die Form http://127.0.0.1:<port>/?token=<token>."
            )
        if parsed.hostname != _LOOPBACK_HOST:
            raise McpServerError(
                "MCP-Proxy spricht ausschließlich mit 127.0.0.1, nicht mit "
                f"{parsed.hostname}."
            )
        if parsed.port is None:
            raise McpServerError("Zugriffs-URL benötigt den Port der laufenden App.")
        token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
        if not token:
            raise McpServerError(
                "Zugriffs-URL enthält kein lokales Sitzungstoken; sie wechselt bei "
                "jedem Start von `app serve`."
            )
        self.base_url = f"http://{_LOOPBACK_HOST}:{parsed.port}"
        self._token = token

    def get(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        target = f"{self.base_url}{path}"
        if query:
            target = f"{target}?{urllib.parse.urlencode(query)}"
        return self._send(urllib.request.Request(target, method="GET"))

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        request.add_header("Content-Type", "application/json")
        return self._send(request)

    def _send(self, request: urllib.request.Request) -> dict[str, Any]:
        request.add_header("X-FolderHome-Token", self._token)
        try:
            with urllib.request.urlopen(
                request,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"FolderHome-API antwortet {exc.code}: {_error_message(exc)}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "FolderHome ist auf "
                f"{self.base_url} nicht erreichbar; läuft `app serve` noch? "
                f"({exc.reason})"
            ) from exc


def _error_message(error: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return error.reason or "unbekannter Fehler"
    message = payload.get("message") if isinstance(payload, dict) else None
    return message if isinstance(message, str) else str(payload)


def build_mcp_server(client: FolderHomeApiClient):
    """Register the bounded FolderHome tool surface on one FastMCP server."""

    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "folderhome",
        instructions=(
            "FolderHome is a local-first document and home assistance agent. Every "
            "tool talks to one running local FolderHome process over loopback, so "
            "answers and proposed plans are shared with its GUI. Chat is never an "
            "approval: a proposed plan only runs after folderhome_confirm_plan with "
            "its exact hash and the selected step ids."
        ),
    )

    @mcp.tool(
        name="folderhome_status",
        description="Report the local runtime boundary and the model connection.",
    )
    def status() -> dict[str, Any]:
        return client.get("/api/v1/status")

    @mcp.tool(
        name="folderhome_profiles",
        description="List the organizational profiles; they are not authorization boundaries.",
    )
    def profiles() -> dict[str, Any]:
        return client.get("/api/v1/profiles")

    @mcp.tool(
        name="folderhome_capabilities",
        description="List the capabilities and how each one is surfaced.",
    )
    def capabilities() -> dict[str, Any]:
        return client.get("/api/v1/capabilities")

    @mcp.tool(
        name="folderhome_executors",
        description="Report which workflows have a connected runtime executor.",
    )
    def executors() -> dict[str, Any]:
        return client.get("/api/v1/agent/executors")

    @mcp.tool(
        name="folderhome_resources",
        description="List the logical resources of one profile without disclosing paths.",
    )
    def resources(profile_id: str) -> dict[str, Any]:
        return client.get("/api/v1/resources", {"profile_id": profile_id})

    @mcp.tool(
        name="folderhome_results",
        description=(
            "List what this process already executed for one profile, newest "
            "first, with the artifact names it produced. Downloads run in the "
            "local GUI."
        ),
    )
    def results(profile_id: str, limit: int = 10) -> dict[str, Any]:
        return client.get(
            "/api/v1/agent/results",
            {"profile_id": profile_id, "limit": str(limit)},
        )

    @mcp.tool(
        name="folderhome_search_documents",
        description="Search the local document index read-only.",
    )
    def search_documents(
        profile_id: str,
        query: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        return client.post(
            "/api/v1/documents/search",
            {
                "schema": "folderhome.local-search-request.v1",
                "profile_id": profile_id,
                "query": query,
                "limit": limit,
            },
        )

    @mcp.tool(
        name="folderhome_topic_dossier",
        description="Summarize one topic from local documents with linked evidence.",
    )
    def topic_dossier(
        profile_id: str,
        topic: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        return client.post(
            "/api/v1/documents/dossier",
            {
                "schema": "folderhome.local-dossier-request.v1",
                "profile_id": profile_id,
                "topic": topic,
                "limit": limit,
            },
        )

    @mcp.tool(
        name="folderhome_chat",
        description=(
            "Run one bounded master-agent turn in the running process. Chat is not "
            "an approval; proposed plans need folderhome_confirm_plan."
        ),
    )
    def chat(profile_id: str, message: str) -> dict[str, Any]:
        return client.post(
            "/api/v1/agent/chat",
            {
                "schema": "folderhome.local-agent-chat-request.v1",
                "profile_id": profile_id,
                "message": message,
            },
        )

    @mcp.tool(
        name="folderhome_confirm_plan",
        description=(
            "Approve selected steps of one proposed plan; the hash must match the "
            "plan exactly."
        ),
    )
    def confirm_plan(
        plan_id: str,
        plan_sha256: str,
        step_ids: list[str],
    ) -> dict[str, Any]:
        return client.post(
            "/api/v1/agent/confirm",
            {
                "schema": "folderhome.local-agent-confirmation-request.v1",
                "plan_id": plan_id,
                "plan_sha256": plan_sha256,
                "step_ids": step_ids,
            },
        )

    @mcp.tool(
        name="folderhome_reset_conversation",
        description="Start a new process-local conversation for one profile.",
    )
    def reset_conversation(profile_id: str) -> dict[str, Any]:
        return client.post(
            "/api/v1/agent/conversation/reset",
            {
                "schema": "folderhome.local-agent-conversation-reset-request.v1",
                "profile_id": profile_id,
            },
        )

    return mcp


def serve_mcp_stdio(*, access_url: str | None, approve_mcp_server: bool) -> None:
    """Start the stdio MCP proxy after the explicit gate and URL check."""

    if not approve_mcp_server:
        raise McpServerError(
            "MCP-Server benötigt die ausdrückliche Freigabe --approve-mcp-server."
        )
    if not access_url:
        raise McpServerError(
            "MCP-Server benötigt --access-url oder die Umgebungsvariable "
            f"{ACCESS_URL_ENV}."
        )
    client = FolderHomeApiClient(access_url)
    print(
        f"FolderHome MCP proxy for {client.base_url} on stdio.",
        file=sys.stderr,
        flush=True,
    )
    build_mcp_server(client).run(transport="stdio")


def integration_plan(access_url: str | None) -> dict[str, Any]:
    """Describe how Claude Code and the Codex CLI attach this proxy."""

    url = access_url or "http://127.0.0.1:8765/?token=<token from app serve>"
    python = sys.executable
    arguments = [
        "-m",
        "folderhome",
        "mcp",
        "serve",
        "--access-url",
        url,
        "--approve-mcp-server",
    ]
    codex_arguments = ", ".join(json.dumps(item) for item in arguments)
    return {
        "schema": "folderhome.mcp-integration-plan.v1",
        "transport": "stdio",
        "access_url": url,
        "access_url_env": ACCESS_URL_ENV,
        "token_rotates_per_serve": True,
        "requires_running_app_serve": True,
        "network_scope": "loopback_only",
        "own_application_instance": False,
        "server_started": False,
        "tools": [
            "folderhome_status",
            "folderhome_profiles",
            "folderhome_capabilities",
            "folderhome_executors",
            "folderhome_resources",
            "folderhome_results",
            "folderhome_search_documents",
            "folderhome_topic_dossier",
            "folderhome_chat",
            "folderhome_confirm_plan",
            "folderhome_reset_conversation",
        ],
        "claude_code_command": (
            f'claude mcp add folderhome -- "{python}" '
            f'-m folderhome mcp serve --access-url "{url}" --approve-mcp-server'
        ),
        "codex_config_toml": (
            "[mcp_servers.folderhome]\n"
            f"command = {json.dumps(python)}\n"
            f"args = [{codex_arguments}]\n"
        ),
        "side_effects": [],
    }
