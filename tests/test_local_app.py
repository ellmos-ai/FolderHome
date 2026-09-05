from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from folderhome.application.local_app import LocalApplication
from folderhome.application.master_agent import build_master_agent_plan
from folderhome.application.medication_intake import (
    apply_medication_import_plan,
    build_medication_import_plan,
)
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.workflow_execution import (
    FindCallWorkflowAdapter,
    MedicationIntakeWorkflowAdapter,
    PersonalNotesWorkflowAdapter,
    WorkflowExecutionError,
    WorkflowExecutionGateway,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.capabilities.medication_store import MedicationStore
from folderhome.contracts import (
    FolderMedicationPlanAnalysis,
    LocalApiResponse,
    LocalAppSettings,
    LogicalResource,
    MedicationEvidence,
    MedicationImportApproval,
    MedicationPlanAnalysisItem,
    MedicationScheduleCandidate,
    OperatingSystemIdentity,
    ResourceRegistry,
)
from folderhome.contracts.strands_agent import StrandsAgentSettings
from folderhome.local_server import LocalServerError, create_local_server
from folderhome.plugin_host import load_manifests

PROFILE_DIR = Path(__file__).parents[1] / "examples" / "profiles"
REPOSITORY_ROOT = Path(__file__).parents[1]
LLM_NOTE_ROOT = REPOSITORY_ROOT.parent / "llm-note"


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


class FailingSearcher:
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        raise RuntimeError("C:/private/index.sqlite ist nicht lesbar")


def _settings(tmp_path: Path, *, host: str = "127.0.0.1") -> LocalAppSettings:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return LocalAppSettings(
        host=host,
        port=0,
        profiles_dir=PROFILE_DIR,
        state_dir=state_dir,
        max_body_bytes=4096,
        max_query_limit=25,
        max_concurrent_requests=4,
        request_timeout_seconds=1.0,
    )


def _app(tmp_path: Path) -> LocalApplication:
    return LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="phase35-test-token-with-sufficient-entropy-123456",
    )


def _resource_app(tmp_path: Path) -> LocalApplication:
    documents = tmp_path / "private-documents"
    documents.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="insurance_documents",
                kind="directory",
                local_path=documents,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"documents.source", "insurance.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
        ),
        profile_defaults={
            "lukas": {
                "documents.source": "insurance_documents",
                "insurance.source": "insurance_documents",
            }
        },
        known_profile_ids=frozenset({"hanna", "lukas", "simon"}),
    )
    return LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="resource-test-token-with-sufficient-entropy-123456",
        resource_registry=registry,
    )


def _executable_app(tmp_path: Path) -> LocalApplication:
    app = _app(tmp_path)
    plugin = next(
        item
        for item in load_manifests(REPOSITORY_ROOT / "manifests" / "components")
        if item.plugin_id == "llm-note"
    )
    app.workflow_executor = WorkflowExecutionGateway(
        (
            FindCallWorkflowAdapter(
                profile_ids=frozenset(
                    profile.profile_id for profile in app.profiles.profiles
                ),
            ),
            PersonalNotesWorkflowAdapter(
                plugin=plugin,
                provider_root=LLM_NOTE_ROOT,
                state_dir=app.settings.state_dir,
                profile_ids=frozenset(
                    profile.profile_id for profile in app.profiles.profiles
                ),
            ),
            MedicationIntakeWorkflowAdapter(
                state_dir=app.settings.state_dir,
                profile_ids=frozenset(
                    profile.profile_id for profile in app.profiles.profiles
                ),
            ),
        )
    )
    return app


def _seed_medication_schedule(tmp_path: Path) -> str:
    source_root = tmp_path / "medication-source"
    source_root.mkdir()
    source = source_root / "DemoMed.txt"
    source.write_text("Synthetischer Medikamentenplan.\n", encoding="utf-8")
    candidate = MedicationScheduleCandidate(
        schedule_id=f"medication_schedule_{sha256(b'app-schedule').hexdigest()}",
        schedule_key=f"medication_schedule_key_{sha256(b'app-key').hexdigest()}",
        profile_id="lukas",
        medication_name="DemoMed",
        dose_quantity_milli=1000,
        dose_unit="Tablette",
        scheduled_time="08:00",
        timezone="Europe/Berlin",
        weekdays=(5,),
        valid_from="2026-08-22",
        valid_to="2026-12-31",
        inventory_item_id=f"inventory_item_{sha256(b'app-inventory').hexdigest()}",
        source_document_id=f"doc_{sha256(b'app-document').hexdigest()}",
        source_sha256=sha256(source.read_bytes()).hexdigest(),
        source_path=source,
        evidence=(MedicationEvidence("medication_name", 1, "Präparat"),),
    )
    analysis = FolderMedicationPlanAnalysis(
        source_root=source_root,
        profile_id="lukas",
        items=(
            MedicationPlanAnalysisItem(
                relative_path=source.name,
                status="ready",
                schedule=candidate,
                message="Synthetischer Testzeitplan.",
            ),
        ),
    )
    store = MedicationStore(tmp_path / "state")
    plan = build_medication_import_plan(analysis, store=store)
    approval = MedicationImportApproval(
        approval_id="seed_app_medication",
        plan_id=plan.plan_id,
        medication_revision=plan.medication_revision,
        action_ids=(plan.actions[0].action_id,),
        approved_at="2026-08-22T07:00:00+02:00",
    )
    apply_medication_import_plan(plan, approval, store=store, allow_state_write=True)
    return candidate.schedule_id


def _api_headers(port: int, token: str) -> dict[str, str]:
    return {
        "Host": f"127.0.0.1:{port}",
        "Origin": f"http://127.0.0.1:{port}",
        "Content-Type": "application/json",
        "X-FolderHome-Token": token,
    }


def test_settings_reject_non_loopback_and_overlapping_profile_state(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="127.0.0.1"):
        _settings(tmp_path, host="0.0.0.0")
    with pytest.raises(ValueError, match="überlappen"):
        LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=PROFILE_DIR / "state",
        )
    with pytest.raises(ValueError, match="max_concurrent_requests"):
        LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=tmp_path / "state-limit",
            max_concurrent_requests=0,
        )
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=tmp_path / "state-timeout",
            request_timeout_seconds=0,
        )


def test_api_requires_token_exact_host_and_same_origin(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765

    missing = app.handle(
        method="GET",
        target="/api/v1/status",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    wrong_host = app.handle(
        method="GET",
        target="/api/v1/status",
        headers={
            "Host": f"localhost:{port}",
            "X-FolderHome-Token": app.session_token,
        },
        body=b"",
        server_port=port,
    )
    wrong_origin = app.handle(
        method="GET",
        target="/api/v1/status",
        headers={
            "Host": f"127.0.0.1:{port}",
            "Origin": "https://example.invalid",
            "X-FolderHome-Token": app.session_token,
        },
        body=b"",
        server_port=port,
    )

    assert missing.status_code == 401
    assert wrong_host.status_code == 403
    assert wrong_origin.status_code == 403


def test_status_and_profiles_expose_organizational_boundary(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)

    status = app.handle(
        method="GET",
        target="/api/v1/status",
        headers=headers,
        body=b"",
        server_port=port,
    )
    profiles = app.handle(
        method="GET",
        target="/api/v1/profiles",
        headers=headers,
        body=b"",
        server_port=port,
    )

    assert status.status_code == 200
    assert status.payload["security_boundary"] == "operating_system_account"
    assert status.payload["profiles_are_authorization_boundaries"] is False
    assert status.payload["network_scope"] == "loopback_only"
    assert status.payload["read_only_api"] is False
    assert status.payload["chat_is_approval"] is False
    assert status.payload["approval_bound_execution"] is True
    assert status.payload["conversation_memory"] == "process_only"
    assert status.payload["model_connection"] == {
        "schema": "folderhome.model-connection-status.v1",
        "provider": "fixture",
        "mode": "deterministic_fixture",
        "runtime_topology": "local_only_fixture",
        "application_runtime": "local_loopback",
        "document_runtime": "local_state",
        "model_inference_location": "local_fixture",
        "connection_status": "fixture_only",
        "live_model_configured": False,
        "live_model_verified_in_process": False,
        "successful_live_model_turns": 0,
        "semantic_routing_mode": "deterministic_fixture",
        "model_id": None,
        "aws_region": None,
        "ollama_host": None,
        "network_authorized": False,
        "sensitive_cloud_data_authorized": False,
        "status_probe_performed": False,
    }
    assert "session_token" not in status.payload
    assert {item["profile_id"] for item in profiles.payload["profiles"]} == {
        "hanna",
        "lukas",
        "simon",
    }
    assert all(item["organizational_only"] for item in profiles.payload["profiles"])


def test_bedrock_status_requires_a_successful_turn_before_claiming_live_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="bedrock-status-test-token-with-sufficient-entropy-123",
        agent_settings=StrandsAgentSettings(
            model_provider="bedrock",
            bedrock_model_id="eu.anthropic.synthetic-sonnet-v1:0",
            aws_region="eu-central-1",
            allow_network=True,
            allow_sensitive_cloud_data=True,
        ),
    )
    port = 8765
    headers = _api_headers(port, app.session_token)

    before = app.handle(
        method="GET",
        target="/api/v1/status",
        headers=headers,
        body=b"",
        server_port=port,
    )

    assert before.payload["model_connection"]["connection_status"] == (
        "configured_not_verified"
    )
    assert before.payload["model_connection"]["live_model_configured"] is True
    assert before.payload["model_connection"]["live_model_verified_in_process"] is False
    assert before.payload["model_connection"]["runtime_topology"] == (
        "local_first_hybrid"
    )
    assert before.payload["model_connection"]["application_runtime"] == (
        "local_loopback"
    )
    assert before.payload["model_connection"]["document_runtime"] == "local_state"
    assert before.payload["model_connection"]["model_inference_location"] == (
        "aws_cloud"
    )

    def successful_turn(**_kwargs):
        return SimpleNamespace(proposed_plans=()), ()

    monkeypatch.setattr(
        "folderhome.application.strands_agent.run_folderhome_agent_turn",
        successful_turn,
    )
    app.run_agent_chat(profile_id="lukas", message="Synthetischer Live-Modelltest")
    after = app.handle(
        method="GET",
        target="/api/v1/status",
        headers=headers,
        body=b"",
        server_port=port,
    )

    assert after.payload["model_connection"]["connection_status"] == (
        "verified_in_process"
    )
    assert after.payload["model_connection"]["live_model_verified_in_process"] is True
    assert after.payload["model_connection"]["successful_live_model_turns"] == 1


def test_executor_catalog_exposes_connected_read_only_and_missing_coverage(
    tmp_path: Path,
) -> None:
    app = _executable_app(tmp_path)
    port = 8765
    response = app.handle(
        method="GET",
        target="/api/v1/agent/executors",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )

    assert response.status_code == 200
    assert response.payload["coverage"] == {
        "connected": 3,
        "direct_read_only": 1,
        "planning_only": 3,
        "not_connected": 26,
        "total": 33,
    }
    workflows = {item["workflow_id"]: item for item in response.payload["workflows"]}
    assert workflows["personal-notes"]["status"] == "connected"
    assert workflows["medication-intake"]["status"] == "connected"
    assert workflows["medication-intake"]["request_schema"][
        "additionalProperties"
    ] is False
    assert workflows["document-library"]["status"] == "direct_read_only"
    assert workflows["folder-cleanup"]["status"] == "not_connected"
    assert "logical resource IDs" in workflows["folder-cleanup"]["reason"]
    assert "external connector" in workflows["mail-connector"]["reason"]
    assert workflows["findcall"]["status"] == "connected"
    assert workflows["findcall"]["adapter_id"] == "findcall_fixture.v1"
    assert workflows["findcall"]["side_effects"] == ["simulation.findcall.fixture"]


def test_resource_catalog_is_profile_scoped_and_never_discloses_local_paths(
    tmp_path: Path,
) -> None:
    app = _resource_app(tmp_path)
    port = 8765

    response = app.handle(
        method="GET",
        target="/api/v1/resources?profile_id=lukas",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )

    assert response.status_code == 200
    assert response.payload["profile_id"] == "lukas"
    assert response.payload["paths_disclosed"] is False
    assert response.payload["defaults"]["insurance.source"] == (
        "insurance_documents"
    )
    assert response.payload["resources"][0]["resource_id"] == (
        "insurance_documents"
    )
    serialized = json.dumps(response.payload, ensure_ascii=False)
    assert "private-documents" not in serialized
    assert str(tmp_path) not in serialized

    missing_profile = app.handle(
        method="GET",
        target="/api/v1/resources",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    assert missing_profile.status_code == 400

    unknown_profile = app.handle(
        method="GET",
        target="/api/v1/resources?profile_id=unknown",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    assert unknown_profile.status_code == 400


def test_search_and_dossier_reuse_existing_services_without_paths(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)
    search_body = json.dumps(
        {
            "schema": "folderhome.local-search-request.v1",
            "profile_id": "lukas",
            "query": "Ich suche nach einem Dokument über meine Krankenversicherung.",
            "limit": 10,
        }
    ).encode("utf-8")
    dossier_body = json.dumps(
        {
            "schema": "folderhome.local-dossier-request.v1",
            "profile_id": "hanna",
            "topic": "Krankenversicherung",
            "limit": 10,
        }
    ).encode("utf-8")

    search = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=search_body,
        server_port=port,
    )
    dossier = app.handle(
        method="POST",
        target="/api/v1/documents/dossier",
        headers=headers,
        body=dossier_body,
        server_port=port,
    )

    assert search.status_code == 200
    assert search.payload["result"]["total_hits"] == 1
    assert search.payload["profile_id"] == "lukas"
    assert "source_path" not in json.dumps(search.payload)
    assert dossier.status_code == 200
    assert "Themendossier: Krankenversicherung" in dossier.payload["result"]["markdown"]
    assert dossier.payload["profile_id"] == "hanna"


def test_gui_chat_uses_the_same_master_agent_service_without_side_effects(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    port = 8765
    response = app.handle(
        method="POST",
        target="/api/v1/agent/chat",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-chat-request.v1",
                "profile_id": "lukas",
                "message": "Gib mir alles zum Thema Krankenversicherung.",
            }
        ).encode("utf-8"),
        server_port=port,
    )

    assert response.status_code == 200
    assert response.payload["schema"] == "folderhome.local-agent-chat-response.v1"
    assert response.payload["agent"]["model_provider"] == "fixture"
    assert response.payload["agent"]["tool_events"][0]["tool_name"] == (
        "build_home_theme_dossier"
    )
    assert response.payload["agent"]["side_effects"] == []
    assert response.payload["profiles_are_authorization_boundaries"] is False


def test_gui_chat_keeps_bounded_profile_local_context_and_resets_explicitly(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)

    def chat(profile_id: str, *, remember: str | None, recall: bool):
        message = json.dumps(
            {
                "schema": "folderhome.fixture-conversation-turn.v1",
                "remember": remember,
                "recall": recall,
            },
            ensure_ascii=False,
        )
        return app.handle(
            method="POST",
            target="/api/v1/agent/chat",
            headers=headers,
            body=json.dumps(
                {
                    "schema": "folderhome.local-agent-chat-request.v1",
                    "profile_id": profile_id,
                    "message": message,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            server_port=port,
        )

    remembered = chat("lukas", remember="Krankenversicherung", recall=False)
    recalled = chat("lukas", remember=None, recall=True)
    isolated = chat("hanna", remember=None, recall=True)

    assert remembered.status_code == 200
    assert recalled.status_code == 200
    assert "Krankenversicherung" in recalled.payload["agent"]["response_text"]
    assert "No retained fixture context" in isolated.payload["agent"]["response_text"]
    assert remembered.payload["conversation"]["turn"] == 1
    assert recalled.payload["conversation"]["turn"] == 2
    assert recalled.payload["conversation"]["conversation_id"] == (
        remembered.payload["conversation"]["conversation_id"]
    )
    assert isolated.payload["conversation"]["conversation_id"] != (
        recalled.payload["conversation"]["conversation_id"]
    )
    assert recalled.payload["conversation"]["retained_messages"] <= (
        recalled.payload["conversation"]["max_messages"]
    )
    assert recalled.payload["conversation"]["persistence"] == "process_memory_only"

    lukas_plan = build_master_agent_plan(
        "Plan for Lukas.",
        profile_id="lukas",
        language="en",
        expert_id="document_expert",
        workflow_ids=("folder-cleanup",),
        persona_id="methodical_operator",
        confidence="high",
        why="Exact fixture plan for reset coverage.",
    )
    hanna_plan = build_master_agent_plan(
        "Plan for Hanna.",
        profile_id="hanna",
        language="en",
        expert_id="document_expert",
        workflow_ids=("folder-cleanup",),
        persona_id="methodical_operator",
        confidence="high",
        why="Exact fixture plan for profile isolation coverage.",
    )
    app._proposed_agent_plans[lukas_plan.plan_id] = lukas_plan
    app._proposed_agent_plans[hanna_plan.plan_id] = hanna_plan

    reset = app.handle(
        method="POST",
        target="/api/v1/agent/conversation/reset",
        headers=headers,
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-conversation-reset-request.v1",
                "profile_id": "lukas",
            }
        ).encode("utf-8"),
        server_port=port,
    )
    after_reset = chat("lukas", remember=None, recall=True)

    assert reset.status_code == 200
    assert reset.payload["conversation"]["turn"] == 0
    assert reset.payload["conversation"]["retained_messages"] == 0
    assert reset.payload["discarded_plan_ids"] == [lukas_plan.plan_id]
    assert reset.payload["side_effects"] == ["memory.agent_conversation.clear"]
    assert app.proposed_agent_plan(lukas_plan.plan_id) is None
    assert app.proposed_agent_plan(hanna_plan.plan_id) == hanna_plan
    assert "No retained fixture context" in after_reset.payload["agent"]["response_text"]
    assert after_reset.payload["conversation"]["turn"] == 1


def test_agent_conversation_window_stays_finite(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app.agent_settings = StrandsAgentSettings(
        model_provider="fixture",
        max_conversation_messages=4,
    )
    port = 8765
    headers = _api_headers(port, app.session_token)

    def chat(*, remember: str | None, recall: bool):
        return app.handle(
            method="POST",
            target="/api/v1/agent/chat",
            headers=headers,
            body=json.dumps(
                {
                    "schema": "folderhome.local-agent-chat-request.v1",
                    "profile_id": "lukas",
                    "message": json.dumps(
                        {
                            "schema": "folderhome.fixture-conversation-turn.v1",
                            "remember": remember,
                            "recall": recall,
                        }
                    ),
                }
            ).encode("utf-8"),
            server_port=port,
        )

    assert chat(remember="first", recall=False).status_code == 200
    assert chat(remember="second", recall=False).status_code == 200
    recalled = chat(remember=None, recall=True)

    assert recalled.status_code == 200
    assert "second" in recalled.payload["agent"]["response_text"]
    assert recalled.payload["conversation"]["retained_messages"] <= 4
    assert recalled.payload["conversation"]["max_messages"] == 4


def test_gui_confirmation_is_a_separate_hash_bound_action_without_execution(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    plan = build_master_agent_plan(
        "Clean up my inbox.",
        profile_id="lukas",
        language="en",
        expert_id="document_expert",
        workflow_ids=("folder-cleanup",),
        persona_id="methodical_operator",
        confidence="high",
        why="The agent selected the explicit folder cleanup endpoint.",
    )
    app._proposed_agent_plans[plan.plan_id] = plan
    port = 8765
    request = {
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": plan.plan_id,
        "plan_sha256": plan.plan_sha256,
        "step_ids": [item.step_id for item in plan.steps],
    }

    confirmed = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(request).encode("utf-8"),
        server_port=port,
    )
    request["plan_sha256"] = "0" * 64
    stale = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(request).encode("utf-8"),
        server_port=port,
    )

    assert confirmed.status_code == 200
    assert confirmed.payload["receipt"]["status"] == "confirmed_for_workflow_handoff"
    assert confirmed.payload["execution_performed"] is False
    assert confirmed.payload["side_effects"] == []
    assert stale.status_code == 400
    assert "Plan-Hash" in stale.payload["message"]


def test_gui_chat_confirms_findcall_fixture_without_call_or_commitment(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    app.workflow_executor = WorkflowExecutionGateway(
        (FindCallWorkflowAdapter(profile_ids=frozenset({"lukas", "hanna"})),)
    )
    port = 8765
    raw_phone = "+4915111111111"
    specialist_request = {
        "schema": "folderhome.fixture-specialist-request.v1",
        "expert_id": "communication_expert",
        "workflow_id": "findcall",
        "persona_id": "methodical_operator",
        "language": "de",
        "request": {
            "action": "simulate",
            "planned_at": "2026-08-23T00:20:00+02:00",
            "area": "mobilität",
            "kind": "quote",
            "service": "Bremsenprüfung Hyundai i10",
            "location": "Beispielstadt",
            "windows": [
                {
                    "start_at": "2026-09-16T09:00:00+02:00",
                    "end_at": "2026-09-16T12:00:00+02:00",
                }
            ],
            "max_distance_km": 20.0,
            "max_price_eur": 180.0,
            "candidates": [
                {
                    "name": "Synthetische Werkstatt",
                    "phone_e164": raw_phone,
                    "services": ["Bremsenprüfung Hyundai i10"],
                    "distance_km": 4.0,
                    "priority": 1,
                    "fixture": {
                        "status": "COMPLETED",
                        "service_confirmed": True,
                        "available": True,
                        "offered_window": {
                            "start_at": "2026-09-16T10:00:00+02:00",
                            "end_at": "2026-09-16T11:00:00+02:00",
                        },
                        "price_known": True,
                        "price_eur": 175.0,
                        "commitment_made": False,
                        "summary": "Synthetisches Angebot innerhalb der Grenze.",
                    },
                }
            ],
        },
    }
    chat = app.handle(
        method="POST",
        target="/api/v1/agent/chat",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-chat-request.v1",
                "profile_id": "lukas",
                "message": json.dumps(specialist_request, ensure_ascii=False),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        server_port=port,
    )

    assert chat.status_code == 200
    plan = chat.payload["agent"]["proposed_plans"][0]
    envelope = plan["steps"][0]["execution_envelope"]
    assert envelope["adapter_id"] == "findcall_fixture.v1"
    assert envelope["side_effects"] == ["simulation.findcall.fixture"]
    assert raw_phone not in json.dumps(chat.payload, ensure_ascii=False)
    assert envelope["domain_plan"]["phone_calls_placed"] is False

    approval = {
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["plan_sha256"],
        "step_ids": [plan["steps"][0]["step_id"]],
    }
    confirmed = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(approval).encode("utf-8"),
        server_port=port,
    )
    replay = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(approval).encode("utf-8"),
        server_port=port,
    )

    assert confirmed.status_code == 200
    assert confirmed.payload["execution_performed"] is True
    assert confirmed.payload["side_effects"] == ["simulation.findcall.fixture"]
    report = confirmed.payload["execution_reports"][0]["domain_report"]
    assert report["simulated"] is True
    assert report["network_used"] is False
    assert report["phone_calls_placed"] is False
    assert report["commitment_made"] is False
    assert replay.status_code == 409


@pytest.mark.skipif(not LLM_NOTE_ROOT.is_dir(), reason="llm-note checkout unavailable")
def test_gui_chat_plans_then_confirmation_executes_existing_note_workflow_once(
    tmp_path: Path,
) -> None:
    app = _executable_app(tmp_path)
    port = 8765
    database = app.settings.state_dir / "personal-notes" / "llm-note.db"
    specialist_request = {
        "schema": "folderhome.fixture-specialist-request.v1",
        "expert_id": "creative_knowledge_expert",
        "workflow_id": "personal-notes",
        "persona_id": "creative_guide",
        "language": "de",
        "request": {
            "action": "create",
            "notebook_id": "gesundheit",
            "area": "gesundheit",
            "title": "Fragen für den Hausarzt",
            "human_content": "Ich möchte drei Fragen für den Termin festhalten.",
            "note_id": None,
            "expected_revision": None,
            "revert_to_revision": None,
            "references": [],
        },
    }
    chat = app.handle(
        method="POST",
        target="/api/v1/agent/chat",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-chat-request.v1",
                "profile_id": "lukas",
                "message": json.dumps(specialist_request, ensure_ascii=False),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        server_port=port,
    )

    assert chat.status_code == 200
    assert chat.payload["agent"]["delegation_events"][0]["workflow_id"] == (
        "personal-notes"
    )
    assert "begrenzter Fachworkflow-Plan" in chat.payload["agent"]["response_text"]
    plan = chat.payload["agent"]["proposed_plans"][0]
    envelope = plan["steps"][0]["execution_envelope"]
    assert envelope["workflow_id"] == "personal-notes"
    assert envelope["domain_plan"]["proposed_content"] == (
        "Ich möchte drei Fragen für den Termin festhalten."
    )
    assert not database.exists()

    approval = {
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["plan_sha256"],
        "step_ids": [plan["steps"][0]["step_id"]],
    }
    confirmed = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(approval).encode("utf-8"),
        server_port=port,
    )
    replay = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(approval).encode("utf-8"),
        server_port=port,
    )

    assert confirmed.status_code == 200
    assert confirmed.payload["execution_performed"] is True
    assert confirmed.payload["execution_reports"][0]["status"] == "executed"
    assert confirmed.payload["side_effects"] == ["state.personal_notes.append"]
    assert database.is_file()
    assert replay.status_code == 409
    assert "bereits ausgeführt" in replay.payload["message"]


@pytest.mark.skipif(not LLM_NOTE_ROOT.is_dir(), reason="llm-note checkout unavailable")
def test_gui_chat_plans_then_confirmation_records_medication_intake_once(
    tmp_path: Path,
) -> None:
    app = _executable_app(tmp_path)
    schedule_id = _seed_medication_schedule(tmp_path)
    store = MedicationStore(app.settings.state_dir)
    port = 8765
    specialist_request = {
        "schema": "folderhome.fixture-specialist-request.v1",
        "expert_id": "health_expert",
        "workflow_id": "medication-intake",
        "persona_id": "careful_reviewer",
        "language": "de",
        "request": {
            "action": "confirm_taken",
            "schedule_id": schedule_id,
            "scheduled_date": "2026-08-22",
            "confirmed_at": "2026-08-22T08:05:00+02:00",
        },
    }
    chat = app.handle(
        method="POST",
        target="/api/v1/agent/chat",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-chat-request.v1",
                "profile_id": "lukas",
                "message": json.dumps(specialist_request, ensure_ascii=False),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        server_port=port,
    )

    assert chat.status_code == 200
    plan = chat.payload["agent"]["proposed_plans"][0]
    envelope = plan["steps"][0]["execution_envelope"]
    assert envelope["workflow_id"] == "medication-intake"
    assert envelope["domain_plan_schema"] == (
        "folderhome.medication-intake-confirmation.v1"
    )
    assert store.list_intake_events(profile_id="lukas") == ()

    approval = {
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["plan_sha256"],
        "step_ids": [plan["steps"][0]["step_id"]],
    }
    confirmed = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(approval).encode("utf-8"),
        server_port=port,
    )
    replay = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(approval).encode("utf-8"),
        server_port=port,
    )

    assert confirmed.status_code == 200
    assert confirmed.payload["execution_performed"] is True
    report = confirmed.payload["execution_reports"][0]
    assert report["domain_report_schema"] == (
        "folderhome.medication-confirmation-report.v1"
    )
    assert report["domain_report"]["medical_advice"] is False
    assert "state_path" not in report["domain_report"]
    assert len(store.list_intake_events(profile_id="lukas")) == 1
    assert replay.status_code == 409


@pytest.mark.skipif(not LLM_NOTE_ROOT.is_dir(), reason="llm-note checkout unavailable")
def test_conversation_reset_discards_connected_unconfirmed_envelope(
    tmp_path: Path,
) -> None:
    app = _executable_app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)
    chat = app.handle(
        method="POST",
        target="/api/v1/agent/chat",
        headers=headers,
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-chat-request.v1",
                "profile_id": "lukas",
                "message": json.dumps(
                    {
                        "schema": "folderhome.fixture-specialist-request.v1",
                        "expert_id": "creative_knowledge_expert",
                        "workflow_id": "personal-notes",
                        "persona_id": "creative_guide",
                        "language": "de",
                        "request": {
                            "action": "create",
                            "notebook_id": "gesundheit",
                            "area": "gesundheit",
                            "title": "Noch nicht freigegebene Notiz",
                            "human_content": "Nach Reset darf nichts ausführbar bleiben.",
                            "note_id": None,
                            "expected_revision": None,
                            "revert_to_revision": None,
                            "references": [],
                        },
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        server_port=port,
    )
    plan = chat.payload["agent"]["proposed_plans"][0]
    envelope_id = plan["steps"][0]["execution_envelope"]["envelope_id"]

    reset = app.handle(
        method="POST",
        target="/api/v1/agent/conversation/reset",
        headers=headers,
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-conversation-reset-request.v1",
                "profile_id": "lukas",
            }
        ).encode(),
        server_port=port,
    )

    assert reset.status_code == 200
    assert reset.payload["discarded_plan_ids"] == [plan["plan_id"]]
    with pytest.raises(WorkflowExecutionError, match="nicht vorbereitet"):
        app.workflow_executor.execute(
            envelope_id=envelope_id,
            approved_at="2026-08-22T19:03:00+02:00",
        )
    assert not (app.settings.state_dir / "personal-notes" / "llm-note.db").exists()


def test_request_schema_size_profile_and_content_type_fail_closed(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)
    unknown_field = json.dumps(
        {
            "schema": "folderhome.local-search-request.v1",
            "profile_id": "lukas",
            "query": "Versicherung",
            "limit": 10,
            "path": "C:/private",
        }
    ).encode("utf-8")
    unknown_profile = json.dumps(
        {
            "schema": "folderhome.local-search-request.v1",
            "profile_id": "admin",
            "query": "Versicherung",
            "limit": 10,
        }
    ).encode("utf-8")

    injected = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=unknown_field,
        server_port=port,
    )
    profile = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=unknown_profile,
        server_port=port,
    )
    too_large = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=b"x" * 4097,
        server_port=port,
    )
    wrong_type_headers = dict(headers)
    wrong_type_headers["Content-Type"] = "text/plain"
    wrong_type = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=wrong_type_headers,
        body=b"{}",
        server_port=port,
    )

    assert injected.status_code == 400
    assert profile.status_code == 400
    assert too_large.status_code == 413
    assert wrong_type.status_code == 415
    assert all(
        response.payload["schema"] == "folderhome.local-api-error.v1"
        for response in (injected, profile, too_large, wrong_type)
    )


def test_provider_failure_is_sanitized_and_contracts_are_public(tmp_path: Path) -> None:
    app = LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=FailingSearcher(),
        session_token="phase35-provider-failure-token-with-sufficient-entropy",
    )
    port = 8765
    response = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-search-request.v1",
                "profile_id": "lukas",
                "query": "Krankenversicherung",
                "limit": 10,
            }
        ).encode("utf-8"),
        server_port=port,
    )

    assert response.status_code == 503
    assert "C:/private" not in response.payload["message"]
    assert LocalApiResponse.__module__ == "folderhome.contracts.local_app"
    assert LocalAppSettings.__module__ == "folderhome.contracts.local_app"
    assert OperatingSystemIdentity.__module__ == "folderhome.contracts.local_app"


def test_gui_is_local_token_gated_and_contains_no_remote_assets(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    root = app.handle(
        method="GET",
        target=f"/?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    blocked_asset = app.handle(
        method="GET",
        target="/assets/app.css",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    favicon = app.handle(
        method="GET",
        target=f"/assets/favicon.svg?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )

    assert root.status_code == 200
    html = root.content.decode("utf-8")
    assert "FolderHome" in html
    assert "Operating-system account" in html
    assert "https://" not in html
    assert "http://" not in html
    assert blocked_asset.status_code == 401
    assert favicon.status_code == 200
    assert favicon.content_type.startswith("image/svg+xml")
    assert root.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert root.headers["Referrer-Policy"] == "no-referrer"


def test_gui_defaults_to_english_and_offers_german_localization(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    root = app.handle(
        method="GET",
        target=f"/?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    script = app.handle(
        method="GET",
        target=f"/assets/app.js?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )

    html = root.content.decode("utf-8")
    javascript = script.content.decode("utf-8")
    assert '<html lang="en">' in html
    assert 'id="language-switch"' in html
    assert 'data-language="en"' in html
    assert 'data-language="de"' in html
    assert "Your documents." in html
    assert 'id="agent-form"' in html
    assert 'id="model-status"' in html
    assert "FolderHome agent" in html
    assert "Checking model" in html
    assert "/api/v1/agent/chat" in javascript
    assert "/api/v1/agent/confirm" in javascript
    assert "Demo model (fixture)" in javascript
    assert "Demomodell (Fixture)" in javascript
    assert "Kein Live-LLM ist verbunden" in javascript
    assert "FolderHome and its files stay local" in javascript
    assert "FolderHome und seine Dateien bleiben lokal" in javascript
    assert "/api/v1/agent/conversation/reset" in javascript
    assert "/api/v1/agent/executors" in javascript
    assert "payload.execution_performed" in javascript
    assert "confirmExecute" in javascript
    assert "executionCompleted" in javascript
    assert "workflowNotConnected" in javascript
    assert "Ein Gespräch ist niemals eine Freigabe." in javascript
    assert "Neue Unterhaltung" in javascript
    assert "Deine Dokumente." in javascript
    assert 'id="new-conversation"' in html
    assert "FolderHome language" in html
    assert "folderhome.language" in javascript
    assert 'document.documentElement.lang = language' in javascript


def test_gui_supports_persistent_light_and_dark_modes(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    root = app.handle(
        method="GET",
        target=f"/?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    script = app.handle(
        method="GET",
        target=f"/assets/app.js?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )

    html = root.content.decode("utf-8")
    javascript = script.content.decode("utf-8")
    assert 'id="theme-switch"' in html
    assert 'data-theme-mode="light"' in html
    assert 'data-theme-mode="dark"' in html
    assert "folderhome.theme" in javascript
    assert 'document.documentElement.dataset.theme = theme' in javascript


def test_real_loopback_server_requires_gate_and_serves_authenticated_api(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    with pytest.raises(LocalServerError, match="Serverfreigabe"):
        create_local_server(app, allow_loopback_server=False)

    server = create_local_server(app, allow_loopback_server=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(server.access_url, timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Server"].strip() == "FolderHome"
            assert "FolderHome agent" in html

        request = urllib.request.Request(
            f"{server.base_url}/api/v1/status",
            headers={
                "X-FolderHome-Token": app.session_token,
                "Origin": server.base_url,
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["network_scope"] == "loopback_only"

        with pytest.raises(urllib.error.HTTPError) as unauthorized:
            urllib.request.urlopen(f"{server.base_url}/api/v1/status", timeout=5)
        assert unauthorized.value.code == 401
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_loopback_server_bounds_slow_connections_before_token_dispatch(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    app = LocalApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=0,
            profiles_dir=PROFILE_DIR,
            state_dir=state_dir,
            max_body_bytes=4096,
            max_query_limit=25,
            max_concurrent_requests=1,
            request_timeout_seconds=0.2,
        ),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="phase36-bounded-loopback-token-with-sufficient-entropy",
    )
    server = create_local_server(app, allow_loopback_server=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    first = socket.create_connection(server.address, timeout=2)
    second = None
    try:
        first.sendall(b"G")
        deadline = time.monotonic() + 2
        while server.active_request_count != 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.active_request_count == 1

        second = socket.create_connection(server.address, timeout=2)
        second.settimeout(1)
        second.sendall(b"GET / HTTP/1.1\r\n")
        try:
            rejected = second.recv(1)
        except ConnectionAbortedError:
            rejected = b""
        assert rejected == b""

        deadline = time.monotonic() + 2
        while server.active_request_count and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.active_request_count == 0

        with urllib.request.urlopen(server.access_url, timeout=2) as response:
            assert response.status == 200
    finally:
        first.close()
        if second is not None:
            second.close()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_loopback_ollama_status_reports_local_inference_without_cloud_claims(
    tmp_path: Path,
) -> None:
    app = LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="ollama-status-test-token-with-sufficient-entropy-1234",
        agent_settings=StrandsAgentSettings(
            model_provider="ollama",
            ollama_host="http://127.0.0.1:11434",
            ollama_model_id="qwen3.8:27b-mlx",
        ),
    )
    port = 8765

    status = app.handle(
        method="GET",
        target="/api/v1/status",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )

    connection = status.payload["model_connection"]
    assert connection["provider"] == "ollama"
    assert connection["live_model_configured"] is True
    assert connection["model_inference_location"] == "local_ollama_host"
    assert connection["model_id"] == "qwen3.8:27b-mlx"
    assert connection["ollama_host"] == "http://127.0.0.1:11434"
    assert connection["aws_region"] is None
    assert connection["connection_status"] == "configured_not_verified"
    assert connection["network_authorized"] is False


def _calendar_export_app(tmp_path: Path) -> tuple[LocalApplication, Path, str]:
    """One app whose confirmed calendar plan really writes an ICS export."""

    from test_workflow_execution import (
        _local_calendar_export_gateway,
        _local_calendar_export_request,
    )

    app = _app(tmp_path)
    calendar_root = tmp_path / "calendar"
    calendar_root.mkdir()
    gateway, _state, export, registry = _local_calendar_export_gateway(calendar_root)
    app.workflow_executor = gateway
    app.resource_registry = registry
    prepared = gateway.prepare(
        workflow_id="calendar-handoff",
        profile_id="lukas",
        request=_local_calendar_export_request(),
    )
    plan = build_master_agent_plan(
        "Export my recorded appointments as one calendar file.",
        profile_id="lukas",
        language="en",
        expert_id="communication_expert",
        workflow_ids=("calendar-handoff",),
        persona_id="methodical_operator",
        execution_envelopes={"calendar-handoff": prepared},
    )
    app._proposed_agent_plans[plan.plan_id] = plan
    return app, export, plan.plan_id


def _confirm(app: LocalApplication, plan_id: str, port: int) -> dict[str, object]:
    plan = app._proposed_agent_plans[plan_id]
    response = app.handle(
        method="POST",
        target="/api/v1/agent/confirm",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-agent-confirmation-request.v1",
                "plan_id": plan.plan_id,
                "plan_sha256": plan.plan_sha256,
                "step_ids": [item.step_id for item in plan.steps],
            }
        ).encode("utf-8"),
        server_port=port,
    )
    assert response.status_code == 200, response.payload
    return response.payload


def test_executed_results_are_listed_for_the_profile_without_any_path(
    tmp_path: Path,
) -> None:
    app, export, plan_id = _calendar_export_app(tmp_path)
    port = 8765
    confirmed = _confirm(app, plan_id, port)

    listed = app.handle(
        method="GET",
        target="/api/v1/agent/results?profile_id=lukas",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    other = app.handle(
        method="GET",
        target="/api/v1/agent/results?profile_id=hanna",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )

    assert confirmed["execution_performed"] is True
    assert listed.status_code == 200
    assert listed.payload["schema"] == "folderhome.local-agent-result-list.v1"
    assert listed.payload["paths_disclosed"] is False
    entry = listed.payload["results"][0]
    assert entry["workflow_id"] == "calendar-handoff"
    assert entry["plan_id"] == plan_id
    assert entry["status"] == "executed"
    assert entry["side_effects"] == ["state.calendar.write", "file.create"]
    assert [item["name"] for item in entry["artifacts"]] == [
        "Hyundai-i10-Termine.ics"
    ]
    assert entry["artifacts"][0]["size_bytes"] == (
        export / "Hyundai-i10-Termine.ics"
    ).stat().st_size
    serialized = json.dumps(listed.payload, ensure_ascii=False)
    assert str(export) not in serialized
    assert str(tmp_path) not in serialized
    assert "_path" not in serialized
    assert other.payload["results"] == []


def test_result_artifact_download_returns_exactly_the_created_bytes(
    tmp_path: Path,
) -> None:
    app, export, plan_id = _calendar_export_app(tmp_path)
    port = 8765
    _confirm(app, plan_id, port)
    listed = app.handle(
        method="GET",
        target="/api/v1/agent/results?profile_id=lukas",
        headers=_api_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    execution_id = listed.payload["results"][0]["execution_id"]

    def fetch(target: str, headers: dict[str, str] | None = None):
        return app.handle(
            method="GET",
            target=target,
            headers=headers
            if headers is not None
            else _api_headers(port, app.session_token),
            body=b"",
            server_port=port,
        )

    downloaded = fetch(f"/api/v1/agent/results/{execution_id}/artifacts/0")
    missing_index = fetch(f"/api/v1/agent/results/{execution_id}/artifacts/7")
    unknown = fetch(
        "/api/v1/agent/results/workflow_execution_"
        + "0" * 64
        + "/artifacts/0"
    )
    unauthorized = fetch(
        f"/api/v1/agent/results/{execution_id}/artifacts/0",
        headers={"Host": f"127.0.0.1:{port}"},
    )

    assert downloaded.status_code == 200
    assert downloaded.content == (export / "Hyundai-i10-Termine.ics").read_bytes()
    assert downloaded.content_type == "text/calendar; charset=utf-8"
    assert downloaded.headers["Content-Disposition"] == (
        'attachment; filename="Hyundai-i10-Termine.ics"'
    )
    assert missing_index.status_code == 404
    assert unknown.status_code == 404
    assert unauthorized.status_code == 401
