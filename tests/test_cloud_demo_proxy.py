import io
import json
from datetime import UTC, datetime

import boto3

from folderhome.cloud_demo import proxy

ORIGIN = "https://main.synthetic.amplifyapp.com"
RUNTIME_ARN = "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo"
SESSION_ID = "folderhome-public-demo-000000000000000000000001"


class _AgentCoreClient:
    def __init__(self) -> None:
        self.calls = []

    def invoke_agent_runtime(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "statusCode": 200,
            "response": io.BytesIO(
                json.dumps(
                    {
                        "response": "Synthetic plan prepared.",
                        "synthetic_data_only": True,
                    }
                ).encode("utf-8")
            ),
        }


def _event(payload: dict[str, str], *, origin: str = ORIGIN) -> dict[str, object]:
    return {
        "httpMethod": "POST",
        "headers": {"origin": origin, "content-type": "application/json"},
        "body": json.dumps(payload),
        "isBase64Encoded": False,
    }


def _environment(monkeypatch) -> None:
    monkeypatch.setenv("FOLDERHOME_AGENT_RUNTIME_ARN", RUNTIME_ARN)
    monkeypatch.setenv("FOLDERHOME_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("FOLDERHOME_DAILY_QUOTA_TABLE", "folderhome-daily-quota")
    monkeypatch.setenv("FOLDERHOME_DAILY_QUOTA_LIMIT", "20")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")


def test_cloud_demo_proxy_relays_one_bounded_synthetic_invocation(monkeypatch) -> None:
    _environment(monkeypatch)
    client = _AgentCoreClient()
    quota_calls = []
    monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: client)
    monkeypatch.setattr(proxy, "_consume_daily_quota", quota_calls.append)

    response = proxy.lambda_handler(
        _event({"prompt": "  Find   my synthetic policy. ", "session_id": SESSION_ID}),
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == ORIGIN
    assert json.loads(response["body"])["synthetic_data_only"] is True
    assert len(client.calls) == 1
    assert len(quota_calls) == 1
    assert client.calls[0]["runtimeSessionId"] == SESSION_ID
    assert json.loads(client.calls[0]["payload"])["prompt"] == "Find my synthetic policy."


def test_cloud_demo_proxy_blocks_wrong_origin_without_invocation(monkeypatch) -> None:
    _environment(monkeypatch)
    client = _AgentCoreClient()
    quota_calls = []
    monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: client)
    monkeypatch.setattr(proxy, "_consume_daily_quota", quota_calls.append)

    response = proxy.lambda_handler(
        _event(
            {"prompt": "Find my synthetic policy.", "session_id": SESSION_ID},
            origin="https://attacker.invalid",
        ),
        None,
    )

    assert response["statusCode"] == 403
    assert client.calls == []
    assert quota_calls == []
    assert "Access-Control-Allow-Origin" not in response["headers"]


def test_cloud_demo_proxy_rejects_unknown_fields_and_short_sessions(monkeypatch) -> None:
    _environment(monkeypatch)
    client = _AgentCoreClient()
    quota_calls = []
    monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: client)
    monkeypatch.setattr(proxy, "_consume_daily_quota", quota_calls.append)

    unknown = proxy.lambda_handler(
        _event(
            {
                "prompt": "Find my synthetic policy.",
                "session_id": SESSION_ID,
                "path": "C:/private",
            }
        ),
        None,
    )
    short = proxy.lambda_handler(
        _event({"prompt": "Find my synthetic policy.", "session_id": "short"}),
        None,
    )

    assert unknown["statusCode"] == 400
    assert short["statusCode"] == 400
    assert client.calls == []
    assert quota_calls == []


def test_cloud_demo_proxy_answers_cors_preflight_without_invocation(monkeypatch) -> None:
    _environment(monkeypatch)
    client = _AgentCoreClient()
    quota_calls = []
    monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: client)
    monkeypatch.setattr(proxy, "_consume_daily_quota", quota_calls.append)
    event = {
        "httpMethod": "OPTIONS",
        "headers": {"origin": ORIGIN},
        "body": "",
    }

    response = proxy.lambda_handler(event, None)

    assert response["statusCode"] == 204
    assert response["headers"]["Access-Control-Allow-Origin"] == ORIGIN
    assert client.calls == []
    assert quota_calls == []


def test_cloud_demo_proxy_bounds_sdk_timeouts_and_retries(monkeypatch) -> None:
    captured = {}

    def fake_client(service_name: str, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(boto3, "client", fake_client)

    proxy._agentcore_client("eu-central-1")

    config = captured["config"]
    assert captured["service_name"] == "bedrock-agentcore"
    assert captured["region_name"] == "eu-central-1"
    assert config.connect_timeout == 3
    assert config.read_timeout == 25
    assert config.retries["total_max_attempts"] == 1


def test_cloud_demo_proxy_consumes_one_atomic_utc_daily_slot(monkeypatch) -> None:
    captured = {}

    class DynamoDBClient:
        def update_item(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(proxy, "_dynamodb_client", lambda _region: DynamoDBClient())
    settings = proxy.CloudDemoProxySettings(
        RUNTIME_ARN,
        ORIGIN,
        "eu-central-1",
        "folderhome-daily-quota",
        20,
    )

    proxy._consume_daily_quota(
        settings,
        now=datetime(2026, 8, 24, 23, 59, tzinfo=UTC),
    )

    assert captured["TableName"] == "folderhome-daily-quota"
    assert captured["Key"] == {"quota_day": {"S": "2026-08-24"}}
    assert captured["ConditionExpression"] == (
        "attribute_not_exists(request_count) OR request_count < :limit"
    )
    assert captured["ExpressionAttributeValues"][":limit"] == {"N": "20"}


def test_cloud_demo_proxy_returns_429_without_agentcore_after_hard_quota(
    monkeypatch,
) -> None:
    _environment(monkeypatch)
    client = _AgentCoreClient()
    monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: client)

    def quota_exhausted(_settings):
        raise proxy.CloudDemoQuotaExceeded

    monkeypatch.setattr(proxy, "_consume_daily_quota", quota_exhausted)

    response = proxy.lambda_handler(
        _event({"prompt": "Find my synthetic policy.", "session_id": SESSION_ID}),
        None,
    )

    assert response["statusCode"] == 429
    assert client.calls == []
