from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.contracts import LocalAppSettings
from folderhome.local_server import create_local_server
from folderhome.mcp_server import (
    FolderHomeApiClient,
    McpServerError,
    build_mcp_server,
    serve_mcp_stdio,
)

PROFILE_DIR = Path(__file__).parents[1] / "examples" / "profiles"


class StubSearcher:
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        return (
            KnowledgeDigestSearchHit(
                source="document",
                filename="Krankenversicherung.txt",
                file_type="txt",
                snippet=f"Fundstelle für >>>{query}<<<",
                relevance=-1.0,
                word_count=42,
            ),
        )[:limit]


@contextmanager
def _running_app(tmp_path: Path):
    """Serve one real fixture-mode FolderHome app on a free loopback port."""

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    application = LocalApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=0,
            profiles_dir=PROFILE_DIR,
            state_dir=state_dir,
            max_query_limit=10,
        ),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="mcp-proxy-test-token-with-sufficient-entropy-12345",
    )
    server = create_local_server(application, allow_loopback_server=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _call(access_url: str, calls: Callable[[Any], Any]) -> Any:
    """Run one in-memory MCP client session against the stdio tool surface."""

    async def scenario() -> Any:
        mcp = build_mcp_server(FolderHomeApiClient(access_url))
        async with create_connected_server_and_client_session(mcp) as session:
            return await calls(session)

    return asyncio.run(scenario())


def _payload(result: Any) -> dict[str, object]:
    assert result.isError is False, _text(result)
    return json.loads(_text(result))


def _text(result: Any) -> str:
    return "\n".join(
        block.text for block in result.content if getattr(block, "text", None)
    )


def test_mcp_tools_expose_the_bounded_folderhome_surface(tmp_path: Path) -> None:
    with _running_app(tmp_path) as server:

        async def calls(session):
            return await session.list_tools()

        listed = _call(server.access_url, calls)

    assert {item.name for item in listed.tools} == {
        "folderhome_status",
        "folderhome_profiles",
        "folderhome_capabilities",
        "folderhome_executors",
        "folderhome_resources",
        "folderhome_search_documents",
        "folderhome_topic_dossier",
        "folderhome_chat",
        "folderhome_confirm_plan",
        "folderhome_reset_conversation",
    }


def test_mcp_read_only_tools_pass_through_the_running_local_app(tmp_path: Path) -> None:
    with _running_app(tmp_path) as server:

        async def calls(session):
            return (
                await session.call_tool("folderhome_status", {}),
                await session.call_tool("folderhome_profiles", {}),
                await session.call_tool("folderhome_executors", {}),
                await session.call_tool(
                    "folderhome_resources", {"profile_id": "lukas"}
                ),
                await session.call_tool(
                    "folderhome_search_documents",
                    {"profile_id": "lukas", "query": "Krankenversicherung"},
                ),
            )

        status, profiles, executors, resources, search = _call(server.access_url, calls)

    assert _payload(status)["network_scope"] == "loopback_only"
    assert {item["profile_id"] for item in _payload(profiles)["profiles"]} == {
        "hanna",
        "lukas",
        "simon",
    }
    assert _payload(executors)["schema"] == (
        "folderhome.local-agent-executor-catalog.v1"
    )
    assert _payload(resources)["profile_id"] == "lukas"
    found = _payload(search)
    assert found["schema"] == "folderhome.local-search-response.v1"
    assert found["side_effects"] == []


def test_mcp_chat_shares_the_conversation_of_the_running_process(
    tmp_path: Path,
) -> None:
    with _running_app(tmp_path) as server:

        async def calls(session):
            return await session.call_tool(
                "folderhome_chat",
                {"profile_id": "lukas", "message": "What can you do?"},
            )

        answered = _call(server.access_url, calls)

    payload = _payload(answered)
    assert payload["schema"] == "folderhome.local-agent-chat-response.v1"
    assert payload["agent"]["model_provider"] == "fixture"
    assert payload["side_effects"] == []


def test_mcp_confirm_plan_forwards_the_local_api_refusal(tmp_path: Path) -> None:
    specialist_request = json.dumps(
        {
            "schema": "folderhome.fixture-specialist-request.v1",
            "expert_id": "document_expert",
            "workflow_id": "folder-cleanup",
            "persona_id": "methodical_operator",
            "language": "en",
            "request": {"goal": "Prepare a safe cleanup plan for my inbox."},
        }
    )
    with _running_app(tmp_path) as server:

        async def calls(session):
            proposed = await session.call_tool(
                "folderhome_chat",
                {"profile_id": "lukas", "message": specialist_request},
            )
            plan = json.loads(_text(proposed))["agent"]["proposed_plans"][0]
            stale = await session.call_tool(
                "folderhome_confirm_plan",
                {
                    "plan_id": plan["plan_id"],
                    "plan_sha256": "0" * 64,
                    "step_ids": [item["step_id"] for item in plan["steps"]],
                },
            )
            return plan, stale

        plan, stale = _call(server.access_url, calls)

    assert plan["confirmation_required"] is True
    assert stale.isError is True
    assert "Plan-Hash" in _text(stale)


def test_mcp_client_refuses_urls_outside_the_loopback_interface() -> None:
    with pytest.raises(McpServerError, match="127.0.0.1"):
        FolderHomeApiClient("http://192.0.2.10:8765/?token=abc")
    with pytest.raises(McpServerError, match="127.0.0.1"):
        FolderHomeApiClient("http://localhost:8765/?token=abc")
    with pytest.raises(McpServerError, match="Sitzungstoken"):
        FolderHomeApiClient("http://127.0.0.1:8765/")
    with pytest.raises(McpServerError, match="Zugriffs-URL"):
        FolderHomeApiClient("127.0.0.1:8765/?token=abc")


def test_mcp_serve_needs_the_gate_and_writes_nothing_to_stdout(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access_url = "http://127.0.0.1:8765/?token=mcp-stdout-test-token"
    with pytest.raises(McpServerError, match="Freigabe"):
        serve_mcp_stdio(access_url=access_url, approve_mcp_server=False)

    started: list[str] = []
    monkeypatch.setattr(
        "mcp.server.fastmcp.FastMCP.run",
        lambda self, transport="stdio", mount_path=None: started.append(transport),
    )
    serve_mcp_stdio(access_url=access_url, approve_mcp_server=True)

    captured = capsys.readouterr()
    assert started == ["stdio"]
    assert captured.out == ""
