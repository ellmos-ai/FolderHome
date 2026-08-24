import json
import re
from pathlib import Path

import pytest

from folderhome.application.agentcore_runtime import AgentCoreRuntimeApplication
from folderhome.contracts.strands_agent import StrandsAgentSettings

SESSION_A = "folderhome-agentcore-session-000000000001"
SESSION_B = "folderhome-agentcore-session-000000000002"


def _invoke(
    app: AgentCoreRuntimeApplication,
    payload: dict[str, object],
    *,
    session_id: str = SESSION_A,
):
    return app.handle(
        method="POST",
        path="/invocations",
        headers={
            "content-type": "application/json",
            "x-amzn-bedrock-agentcore-runtime-session-id": session_id,
        },
        body=json.dumps(payload).encode("utf-8"),
    )


def test_agentcore_runtime_exposes_current_http_contract(tmp_path: Path) -> None:
    app = AgentCoreRuntimeApplication(tmp_path)

    ping = app.handle(method="GET", path="/ping", headers={}, body=b"")
    missing_session = app.handle(
        method="POST",
        path="/invocations",
        headers={"content-type": "application/json"},
        body=b'{"prompt":"hello"}',
    )
    unknown = app.handle(method="GET", path="/unknown", headers={}, body=b"")

    assert ping.status_code == 200
    assert ping.payload == {"status": "Healthy"}
    assert missing_session.status_code == 400
    assert unknown.status_code == 404
    assert ping.headers["X-Content-Type-Options"] == "nosniff"
    assert ping.headers["X-Frame-Options"] == "DENY"
    assert ping.headers["Cache-Control"] == "no-store"


def test_agentcore_runtime_runs_confirmed_synthetic_journey_per_session(
    tmp_path: Path,
) -> None:
    app = AgentCoreRuntimeApplication(tmp_path)

    prepared = _invoke(
        app,
        {
            "prompt": (
                "I had an accident with my Hyundai i10. Find the current insurance "
                "and prepare the next steps."
            )
        },
    )
    plan = prepared.payload["plan"]
    other_session = _invoke(
        app,
        {"prompt": plan["confirmation_command"]},
        session_id=SESSION_B,
    )
    confirmed = _invoke(app, {"prompt": plan["confirmation_command"]})

    assert prepared.status_code == 200
    assert plan["status"] == "confirmation_required"
    assert prepared.payload["synthetic_data_only"] is True
    assert prepared.payload["external_network_used"] is False
    assert other_session.status_code == 400
    assert confirmed.status_code == 200
    assert confirmed.payload["result"]["status"] == "executed"
    assert confirmed.payload["result"]["network_used"] is False
    assert "C:\\" not in json.dumps(confirmed.payload)
    assert str(tmp_path) not in json.dumps(confirmed.payload)


def test_agentcore_runtime_accepts_nested_prompt_and_reset(tmp_path: Path) -> None:
    app = AgentCoreRuntimeApplication(tmp_path)

    prepared = _invoke(app, {"input": {"prompt": "Find my Hyundai insurance."}})
    reset = _invoke(app, {"prompt": "/reset"})
    oversized = app.handle(
        method="POST",
        path="/invocations",
        headers={
            "content-type": "application/json",
            "x-amzn-bedrock-agentcore-runtime-session-id": SESSION_A,
        },
        body=b"x" * 32_769,
    )

    assert prepared.status_code == 200
    assert reset.status_code == 200
    assert reset.payload["reset"]["status"] == "reset"
    assert oversized.status_code == 413


def test_agentcore_runtime_bounds_process_local_session_workspaces(
    tmp_path: Path,
) -> None:
    app = AgentCoreRuntimeApplication(tmp_path, max_sessions=1)

    first = _invoke(app, {"prompt": "Find my Hyundai insurance."})
    overflow = _invoke(
        app,
        {"prompt": "Find my Hyundai insurance."},
        session_id=SESSION_B,
    )

    assert first.status_code == 200
    assert overflow.status_code == 503
    assert "session capacity" in overflow.payload["error"].casefold()


def test_agentcore_runtime_passes_explicit_provider_settings_to_synthetic_session(
    tmp_path: Path,
) -> None:
    settings = StrandsAgentSettings(
        model_provider="bedrock",
        bedrock_model_id="eu.amazon.nova-micro-v1:0",
        aws_region="eu-central-1",
        allow_network=True,
        allow_sensitive_cloud_data=True,
        max_output_tokens=1_024,
    )
    app = AgentCoreRuntimeApplication(tmp_path, agent_settings=settings)

    demo = app._demo_for_session(SESSION_A)

    assert demo.agent_settings is settings
    assert app.model_provider == "bedrock"


def test_agentcore_runtime_can_keep_specialist_execution_deterministic(
    tmp_path: Path,
) -> None:
    master_settings = StrandsAgentSettings(
        model_provider="bedrock",
        bedrock_model_id="eu.amazon.nova-micro-v1:0",
        aws_region="eu-central-1",
        allow_network=True,
        allow_sensitive_cloud_data=True,
        max_output_tokens=512,
    )
    specialist_settings = StrandsAgentSettings(
        model_provider="fixture",
        max_conversation_messages=64,
    )
    app = AgentCoreRuntimeApplication(
        tmp_path,
        agent_settings=master_settings,
        specialist_agent_settings=specialist_settings,
    )

    demo = app._demo_for_session(SESSION_A)

    assert demo.agent_settings is master_settings
    assert demo.specialist_agent_settings is specialist_settings
    assert app.model_provider == "bedrock"
    assert app.specialist_model_provider == "fixture"


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("max_body_bytes", True),
        ("max_sessions", "32"),
        ("max_concurrent_requests", 1.5),
        ("request_timeout_seconds", "30"),
    ],
)
def test_agentcore_runtime_rejects_ambiguous_limit_types(
    tmp_path: Path,
    option: str,
    value: object,
) -> None:
    with pytest.raises(ValueError, match="AgentCore"):
        AgentCoreRuntimeApplication(tmp_path, **{option: value})


def test_agentcore_deployment_files_pin_arm64_non_root_contract() -> None:
    root = Path(__file__).parents[1]
    dockerfile = (root / "deploy" / "agentcore" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    readme = (root / "deploy" / "agentcore" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "--platform=linux/arm64" in dockerfile
    assert len(re.findall(r"python:3\.12\.11-slim-bookworm@sha256:[0-9a-f]{64}", dockerfile)) == 2
    assert "USER folderhome" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert 'CMD ["python", "-m", "folderhome.agentcore_server"]' in dockerfile
    assert "/ping" in readme
    assert "/invocations" in readme
    assert "synthetic" in readme.casefold()
    assert "do not expose" in readme.casefold()
    assert "**English** | [Deutsch](./README.de.md)" in readme
    german = (root / "deploy" / "agentcore" / "README.de.md").read_text(
        encoding="utf-8"
    )
    assert "[English](./README.md) | **Deutsch**" in german
    assert "ausdrücklich" in german
