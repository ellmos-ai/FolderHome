import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from folderhome.application import accident_demo
from folderhome.application.agentcore_runtime import AgentCoreRuntimeApplication
from folderhome.application.local_app import LocalApplication
from folderhome.contracts.strands_agent import StrandsAgentSettings

SESSION = "folderhome-cloud-sandbox-session-00000001"


def invoke(app, prompt, session=SESSION):
    return app.handle(
        method="POST",
        path="/invocations",
        headers={
            "content-type": "application/json",
            "x-amzn-bedrock-agentcore-runtime-session-id": session,
        },
        body=json.dumps({"prompt": prompt}).encode(),
    )


def memory_prompt(remember=None):
    return json.dumps(
        {
            "schema": "folderhome.fixture-conversation-turn.v1",
            "remember": remember,
            "recall": remember is None,
        }
    )


def test_agentcore_real_turn_retains_prior_messages_and_isolates_sessions(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path)
    first = invoke(app, memory_prompt("Grüner Koffer"))
    second = invoke(app, memory_prompt())
    other = invoke(app, memory_prompt(), SESSION + "-other")
    assert first.status_code == second.status_code == other.status_code == 200
    assert second.payload["response"] == (
        "Retained fixture context from this process session: Grüner Koffer"
    )
    assert second.payload["tool_events"] == []
    assert second.payload["model_turns"] == 1
    assert second.payload["plan"] is second.payload["result"] is None
    assert second.payload["session_state"] == {"turns": 2, "has_plan": False, "has_results": False}
    assert "No retained fixture context" in other.payload["response"]


def test_agentcore_copies_all_104_examples_and_searches_non_insurance_data(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path)
    response = invoke(app, "Suche Medikament")
    assert response.status_code == 200
    assert response.payload["tool_events"] == [
        {"tool_name": "search_home_documents", "status": "ok"}
    ]
    demo = app._demo_for_session(SESSION)
    originals = accident_demo._safe_files(demo.examples_root)
    copies = accident_demo._safe_files(demo.runtime_root / "examples")
    assert len(originals) == len(copies) == 104
    for source in originals:
        copy = demo.runtime_root / "examples" / source.relative_to(demo.examples_root)
        assert copy.read_bytes() == source.read_bytes()
        assert not copy.samefile(source)
    assert {p.profile_id for p in demo._application.profiles.profiles} == {
        "lukas",
        "hanna",
        "simon",
    }
    hits = demo._application.searcher.search("Medikament")
    assert hits
    assert any("medik" in hit.snippet.casefold() for hit in hits)
    assert str(tmp_path) not in json.dumps(response.payload)
    assert response.payload["plan"] is None


def test_agentcore_default_confirm_then_chat_and_reset(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path)
    prepared = invoke(app, accident_demo.DEFAULT_ACCIDENT_PROMPT)
    plan = prepared.payload["plan"]
    assert plan["plan_source"] == "deterministic_fallback"
    assert len(plan["steps"]) == 4
    assert plan["confirmation_command"] in prepared.payload["response"]
    confirmed = invoke(app, plan["confirmation_command"])
    assert confirmed.status_code == 200
    assert [item["filename"] for item in confirmed.payload["result"]["generated_results"]] == list(
        accident_demo._RESULT_FILES
    )
    assert confirmed.payload["session_state"] == {
        "turns": 1,
        "has_plan": False,
        "has_results": True,
    }
    assert invoke(app, plan["confirmation_command"]).status_code == 400
    chat = invoke(app, "Was kannst du?")
    assert chat.status_code == 200
    assert chat.payload["session_state"]["turns"] == 2
    assert chat.payload["result"] is None
    session_root = app._demo_for_session(SESSION).runtime_root.parent
    reset = invoke(app, "/reset")
    assert reset.status_code == 200
    assert not session_root.exists()
    assert reset.payload["session_state"] == {"turns": 0, "has_plan": False, "has_results": False}
    assert app._sessions == {}
    assert "No retained fixture context" in invoke(app, memory_prompt()).payload["response"]


def test_agentcore_first_model_plan_requires_exact_confirmation(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path)
    # Real Strands fixture specialist -> real retained, hash-bound adapter envelope.
    workflow, expert, persona, request = accident_demo._REQUESTS[-1]
    prompt = json.dumps(
        {
            "schema": "folderhome.fixture-specialist-request.v1",
            "workflow_id": workflow,
            "expert_id": expert,
            "persona_id": persona,
            "language": "de",
            "request": request,
        }
    )
    prepared = invoke(app, prompt)
    assert prepared.status_code == 200
    plan = prepared.payload["plan"]
    assert plan["plan_source"] == "master_agent"
    assert len(plan["steps"]) == 1
    assert not list(tmp_path.rglob("Hyundai-i10-claim-letter.md"))
    assert invoke(app, "/confirm unknown").status_code == 400
    assert invoke(app, plan["confirmation_command"], SESSION + "-other").status_code == 400
    confirmed = invoke(app, plan["confirmation_command"])
    assert confirmed.status_code == 200
    assert confirmed.payload["result"]["status"] == "executed"
    assert len(confirmed.payload["result"]["generated_results"]) == 2
    assert all(item["inline"] for item in confirmed.payload["result"]["generated_results"])
    assert invoke(app, plan["confirmation_command"]).status_code == 400


def test_agentcore_generated_files_are_deltas_and_events_are_projected(tmp_path, monkeypatch):
    original = LocalApplication.run_agent_chat

    def with_outputs(self, **kwargs):
        report = original(self, **kwargs)
        outputs = self.settings.state_dir.parent / "outputs"
        (outputs / "Übersicht.txt").write_text(kwargs["message"], encoding="utf-8")
        (outputs / "unchanged.txt").write_text("same", encoding="utf-8")
        (self.settings.state_dir / "private.txt").write_text("do not export", encoding="utf-8")
        return replace(
            report,
            tool_events=(
                SimpleNamespace(
                    tool_name="search_home_documents",
                    status="executed",
                    arguments={"secret": str(tmp_path)},
                    content="secret",
                ),
                SimpleNamespace(tool_name=str(tmp_path), status="failed"),
            ),
        )

    monkeypatch.setattr(LocalApplication, "run_agent_chat", with_outputs)
    app = AgentCoreRuntimeApplication(tmp_path)
    first = invoke(app, "Hallo")
    second = invoke(app, "Guten Tag")
    assert len(first.payload["result"]["generated_results"]) == 2
    entries = second.payload["result"]["generated_results"]
    assert len(entries) == 1
    assert entries[0]["filename"] == "Übersicht.txt"
    assert entries[0]["content"] == "Guten Tag"
    assert entries[0]["sha256"] == sha256(b"Guten Tag").hexdigest()
    assert second.payload["tool_events"] == [
        {"tool_name": "search_home_documents", "status": "ok"},
        {"tool_name": "unknown_tool", "status": "error"},
    ]
    assert str(tmp_path) not in second.content.decode()


def test_agentcore_file_count_inline_and_json_escape_response_limits(tmp_path, monkeypatch):
    original = LocalApplication.run_agent_chat

    def with_outputs(self, **kwargs):
        report = original(self, **kwargs)
        outputs = self.settings.state_dir.parent / "outputs"
        for index in range(14):
            (outputs / f"{index:02}.txt").write_bytes(b"\x01" * 262_144)
        return report

    monkeypatch.setattr(LocalApplication, "run_agent_chat", with_outputs)
    response = invoke(AgentCoreRuntimeApplication(tmp_path), "Hallo")
    assert response.status_code == 200
    assert len(response.content) < 1_572_864
    entries = response.payload["result"]["generated_results"]
    assert len(entries) == 12
    assert any(e.get("inline_skipped_reason") == "response_size_limit" for e in entries)
    assert all(e["size_bytes"] == 262_144 for e in entries)
    assert json.loads(response.content) == response.payload


def test_agentcore_lru_respects_recent_use_and_busy_sessions(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path, max_sessions=2)
    a = app._demo_for_session(SESSION)
    b = app._demo_for_session(SESSION + "-b")
    app._demo_for_session(SESSION)
    app._demo_for_session(SESSION + "-c")
    assert a.runtime_root.exists()
    assert not b.runtime_root.parent.exists()
    with app._session_lease(SESSION), app._session_lease(SESSION + "-c"):
        assert invoke(app, "hello", SESSION + "-d").status_code == 503
        assert invoke(app, "/reset").status_code == 503
        assert a.runtime_root.exists()
    assert invoke(app, "/reset").status_code == 200


def test_agentcore_hardlink_blocks_chat_export_and_reset_without_touching_target(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path / "sessions")
    demo = app._demo_for_session(SESSION)
    foreign = tmp_path / "foreign.txt"
    foreign.write_text("foreign", encoding="utf-8")
    link = demo.runtime_root / "outputs" / "linked.txt"
    link.hardlink_to(foreign)
    assert invoke(app, "hello").status_code == 400
    assert invoke(app, "/reset").status_code == 400
    assert foreign.read_text(encoding="utf-8") == "foreign"
    link.unlink()
    assert invoke(app, "/reset").status_code == 200


@pytest.mark.parametrize("prompt", ["", "x" * 1001, "/unknown"])
def test_agentcore_rejects_invalid_prompts(tmp_path, prompt):
    response = invoke(AgentCoreRuntimeApplication(tmp_path), prompt)
    assert response.status_code == 400


@pytest.mark.parametrize("mime", ["application/octet-stream", "text/plain", "application/json"])
def test_agentcore_path_guard_includes_slashes_escaped_json_and_binary(tmp_path, mime):
    path = str(tmp_path / "private.txt").replace("\\", "/")
    for content in (path.encode(), json.dumps({"path": path}).encode()):
        entry = accident_demo._inline_content(content, mime, workspace=str(tmp_path))
        assert entry == {"inline": False, "inline_skipped_reason": "local_paths"}


def test_agentcore_two_turn_budget_supports_one_tool_and_answer(tmp_path):
    app = AgentCoreRuntimeApplication(
        tmp_path,
        agent_settings=StrandsAgentSettings(
            model_provider="fixture",
            max_turns=2,
            max_tool_result_bytes=65_536,
        ),
    )
    response = invoke(app, "Suche Medikament")
    assert response.status_code == 200
    assert response.payload["model_turns"] == 2
    assert response.payload["response"]
    assert len(response.payload["tool_events"]) == 1


def test_agentcore_partially_executed_plan_is_not_reported_as_complete(tmp_path, monkeypatch):
    app = AgentCoreRuntimeApplication(tmp_path)
    demo = app._demo_for_session(SESSION)
    demo._application = SimpleNamespace(
        proposed_agent_plan=lambda plan_id: SimpleNamespace(
            plan_sha256="a" * 64,
            steps=(
                SimpleNamespace(
                    step_id="step_one",
                    workflow_id="correspondence-studio",
                    confirmation_required=True,
                    execution_envelope=SimpleNamespace(envelope_id="envelope_one"),
                ),
                SimpleNamespace(
                    step_id="step_two",
                    workflow_id="unconnected",
                    confirmation_required=True,
                    execution_envelope=None,
                ),
            ),
        ),
        confirm_agent_plan=lambda **kw: {
            "execution_performed": True,
            "side_effects": ["file.create"],
            "execution_reports": [{"envelope_id": "envelope_one", "execution_performed": True}],
        },
    )
    demo._prepared = {
        "plan_id": "plan_partial",
        "plan_sha256": "a" * 64,
        "plan_source": "master_agent",
    }
    monkeypatch.setattr(demo, "_output_snapshot", lambda: {})
    response = invoke(app, "/confirm plan_partial")
    assert response.status_code == 200
    assert response.payload["result"]["status"] == "partially_executed"
    assert [step["status"] for step in response.payload["result"]["executions"]] == [
        "executed",
        "not_executed",
    ]
    assert "only partly executed" in response.payload["response"]


def test_agentcore_model_and_workflow_errors_stay_json_and_path_free(tmp_path, monkeypatch):
    from folderhome.application.local_app import LocalAppError
    from folderhome.application.strands_agent import FolderHomeAgentError
    from folderhome.application.workflow_execution import WorkflowExecutionOutcomeUnknown

    app = AgentCoreRuntimeApplication(tmp_path)
    demo = app._demo_for_session(SESSION)
    for error, expected in (
        (LocalAppError, 409),
        (FolderHomeAgentError, 503),
        (WorkflowExecutionOutcomeUnknown, 409),
    ):

        def fail(prompt, error_type=error):
            raise error_type(str(tmp_path / "private.txt"))

        monkeypatch.setattr(demo, "chat", fail)
        response = invoke(app, "hello")
        assert response.status_code == expected
        assert response.payload["schema"] == "folderhome.agentcore-error.v1"
        assert str(tmp_path) not in response.content.decode()


def test_agentcore_two_sequential_tools_need_more_than_two_turns(tmp_path, monkeypatch):
    from folderhome.application import strands_agent

    class TwoToolModel(strands_agent._fixture_model_class()):
        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            latest = strands_agent._latest_tool_result(messages)
            if latest is None:
                events = strands_agent._tool_events("list_home_resources", {})
            elif latest.get("schema") == "folderhome.logical-resource-catalog.v1":
                events = strands_agent._tool_events(
                    "search_home_documents",
                    {
                        "query": "Medikament",
                        "limit": 5,
                    },
                )
            else:
                events = strands_agent._text_events("Two tools completed; final answer.")
            async for event in events:
                yield event

    monkeypatch.setattr(strands_agent, "_build_model", lambda *a, **kw: TwoToolModel())
    results = []
    for maximum in (2, 4):
        app = AgentCoreRuntimeApplication(
            tmp_path / str(maximum),
            agent_settings=StrandsAgentSettings(
                model_provider="fixture",
                max_turns=maximum,
                max_tool_result_bytes=65_536,
            ),
        )
        results.append(invoke(app, "Find household information."))
    assert results[1].status_code == 200
    assert results[1].payload["response"] == "Two tools completed; final answer."
    assert results[1].payload["model_turns"] == 3
    assert results[0].payload.get("response") != "Two tools completed; final answer."


def test_agentcore_default_passes_unchanged_deployment_verifiers_offline(tmp_path, monkeypatch):
    from deploy.aws_demo.manage import validate_confirmed_response, validate_prepared_response
    from folderhome.application import strands_agent

    # Provider boundary is a fixture, explicitly NOT a Bedrock integration test.
    monkeypatch.setattr(
        strands_agent,
        "_build_model",
        lambda settings, **kwargs: strands_agent._fixture_model_class()(**kwargs),
    )
    app = AgentCoreRuntimeApplication(
        tmp_path,
        agent_settings=StrandsAgentSettings(
            model_provider="bedrock",
            bedrock_model_id="eu.amazon.nova-micro-v1:0",
            aws_region="eu-central-1",
            allow_network=True,
            allow_sensitive_cloud_data=True,
            max_turns=2,
            max_output_tokens=512,
            max_tool_result_bytes=65_536,
        ),
        specialist_agent_settings=StrandsAgentSettings(
            model_provider="fixture", max_conversation_messages=64
        ),
    )
    prepared = invoke(app, accident_demo.DEFAULT_ACCIDENT_PROMPT)
    assert prepared.status_code == 200
    command = validate_prepared_response(prepared.payload)
    confirmed = invoke(app, command)
    assert confirmed.status_code == 200
    assert len(validate_confirmed_response(confirmed.payload)) == 4


def test_agentcore_missing_examples_fail_without_creating_session(tmp_path):
    app = AgentCoreRuntimeApplication(tmp_path / "sessions", examples_root=tmp_path / "missing")
    response = invoke(app, "hello")
    assert response.status_code == 400
    assert "examples are unavailable" in response.payload["error"]
    assert not app.workspace_root.exists()


def test_agentcore_symbolic_parent_rejected_before_resolving(tmp_path, monkeypatch):
    from pathlib import Path

    parent = tmp_path / "linked"
    real_is_link = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == parent or real_is_link(self))
    with pytest.raises(accident_demo.SyntheticAccidentDemoError, match="symbolic link"):
        AgentCoreRuntimeApplication(parent / "session")


def test_agentcore_default_proxy_ledger_delta_is_exactly_two_forwards(tmp_path, monkeypatch):
    import io
    from datetime import UTC, datetime

    import boto3
    from moto import mock_aws

    from folderhome.cloud_demo import proxy

    environment = {
        "FOLDERHOME_AGENT_RUNTIME_ARN": (
            "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo"
        ),
        "FOLDERHOME_PUBLIC_ORIGIN": "https://synthetic.example.org",
        "FOLDERHOME_DAILY_QUOTA_TABLE": "synthetic-budget-table",
        "AWS_REGION": "eu-central-1",
        "FOLDERHOME_BUDGET_TOTAL_MICROUSD": "195000000",
        "FOLDERHOME_BUDGET_FORWARD_MICROUSD": "10000",
        "FOLDERHOME_BUDGET_START_UTC": "2026-09-13",
        "FOLDERHOME_BUDGET_END_UTC": "2026-10-16",
        "FOLDERHOME_AGENT_RUNTIME_ENDPOINT": "budget_test",
        "FOLDERHOME_AGENT_RUNTIME_VERSION": "12",
        "FOLDERHOME_BUDGET_REVIEW_SHA256": "c" * 64,
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    settings = proxy.CloudDemoProxySettings.from_environment(environment)
    app = AgentCoreRuntimeApplication(tmp_path)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 13, tzinfo=UTC)

    class RuntimeClient:
        calls = 0

        def invoke_agent_runtime(self, **kwargs):
            self.calls += 1
            response = invoke(
                app, json.loads(kwargs["payload"])["prompt"], kwargs["runtimeSessionId"]
            )
            return {"statusCode": response.status_code, "response": io.BytesIO(response.content)}

    def through_proxy(prompt):
        response = proxy.lambda_handler(
            {
                "httpMethod": "POST",
                "headers": {"origin": settings.public_origin, "content-type": "application/json"},
                "body": json.dumps({"prompt": prompt, "session_id": SESSION}),
                "isBase64Encoded": False,
            },
            None,
        )
        assert response["statusCode"] == 200
        return json.loads(response["body"])

    with mock_aws():
        ledger = boto3.client("dynamodb", region_name="eu-central-1")
        ledger.create_table(
            TableName=settings.daily_quota_table,
            KeySchema=[{"AttributeName": "quota_day", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "quota_day", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ledger.put_item(
            TableName=settings.daily_quota_table, Item=proxy.initial_budget_item(settings)
        )
        client = RuntimeClient()
        monkeypatch.setattr(proxy, "_dynamodb_client", lambda _region: ledger)
        monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: client)
        monkeypatch.setattr(proxy, "_verify_runtime_target", lambda _settings: None)
        monkeypatch.setattr(proxy, "datetime", Clock)
        prepared = through_proxy(accident_demo.DEFAULT_ACCIDENT_PROMPT)
        confirmed = through_proxy(prepared["plan"]["confirmation_command"])
        assert len(confirmed["result"]["generated_results"]) == 4
        assert client.calls == 2
        money = ledger.get_item(
            TableName=settings.daily_quota_table, Key={"quota_day": {"S": "_budget_v1"}}
        )["Item"]
        day = ledger.get_item(
            TableName=settings.daily_quota_table, Key={"quota_day": {"S": "2026-09-13"}}
        )["Item"]
        assert money["reserved_microusd"] == {"N": "20000"}
        assert day["request_count"] == {"N": "2"}
