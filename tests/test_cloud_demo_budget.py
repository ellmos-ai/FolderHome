"""Monetary admission: synthetic amounts, no account or model traffic."""

import json
from datetime import UTC, datetime, timedelta, timezone

import boto3
import pytest
from botocore.exceptions import ReadTimeoutError
from moto import mock_aws

from folderhome.cloud_demo import proxy


def environment() -> dict[str, str]:
    return {
        "FOLDERHOME_AGENT_RUNTIME_ARN": (
            "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo"
        ),
        "FOLDERHOME_PUBLIC_ORIGIN": "https://synthetic.example.org",
        "FOLDERHOME_DAILY_QUOTA_TABLE": "synthetic-budget-table",
        "AWS_REGION": "eu-central-1",
        "FOLDERHOME_BUDGET_TOTAL_MICROUSD": "1000000",
        "FOLDERHOME_BUDGET_FORWARD_MICROUSD": "100000",
        "FOLDERHOME_BUDGET_START_UTC": "2026-09-01",
        "FOLDERHOME_BUDGET_END_UTC": "2026-09-04",
        "FOLDERHOME_AGENT_RUNTIME_ENDPOINT": "budget_v4",
        "FOLDERHOME_AGENT_RUNTIME_VERSION": "4",
        "FOLDERHOME_BUDGET_REVIEW_SHA256": "c" * 64,
    }


@pytest.mark.parametrize(
    "field",
    [
        "FOLDERHOME_BUDGET_TOTAL_MICROUSD",
        "FOLDERHOME_BUDGET_FORWARD_MICROUSD",
        "FOLDERHOME_BUDGET_START_UTC",
        "FOLDERHOME_BUDGET_END_UTC",
        "FOLDERHOME_AGENT_RUNTIME_ENDPOINT",
        "FOLDERHOME_AGENT_RUNTIME_VERSION",
        "FOLDERHOME_BUDGET_REVIEW_SHA256",
    ],
)
def test_missing_monetary_policy_cannot_fall_back_to_request_count(field) -> None:
    values = environment()
    del values[field]
    with pytest.raises(ValueError):
        proxy.CloudDemoProxySettings.from_environment(values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "0"),
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "1.0"),
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "NaN"),
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "-1"),
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "９９"),
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "9" * 100),
        ("FOLDERHOME_BUDGET_FORWARD_MICROUSD", "0"),
        ("FOLDERHOME_BUDGET_FORWARD_MICROUSD", "1000001"),
        ("FOLDERHOME_BUDGET_START_UTC", "20260901"),
        ("FOLDERHOME_BUDGET_END_UTC", "2026-09-01"),
        ("FOLDERHOME_BUDGET_END_UTC", "2026-02-30"),
        ("FOLDERHOME_BUDGET_END_UTC", "2028-09-04"),
        ("FOLDERHOME_AGENT_RUNTIME_ENDPOINT", "DEFAULT"),
        ("FOLDERHOME_AGENT_RUNTIME_ENDPOINT", "../other"),
        ("FOLDERHOME_AGENT_RUNTIME_VERSION", "latest"),
        ("FOLDERHOME_AGENT_RUNTIME_VERSION", "0"),
        ("FOLDERHOME_AGENT_RUNTIME_VERSION", "100000"),
        ("FOLDERHOME_BUDGET_REVIEW_SHA256", "approved"),
    ],
)
def test_invalid_policy_is_rejected_before_any_sdk_use(field, value) -> None:
    values = environment()
    values[field] = value
    with pytest.raises(ValueError):
        proxy.CloudDemoProxySettings.from_environment(values)


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (datetime(2026, 9, 1, tzinfo=UTC), 333333),
        (datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC), 333333),
        (datetime(2026, 9, 2, tzinfo=UTC), 666666),
        (datetime(2026, 9, 3, tzinfo=UTC), 1000000),
        (datetime(2026, 9, 2, 1, tzinfo=timezone(timedelta(hours=2))), 333333),
    ],
)
def test_cumulative_entitlement_releases_only_elapsed_utc_days(instant, expected) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    assert settings.budget.accrued_microusd(instant) == expected


@pytest.mark.parametrize(
    "instant",
    [
        datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC),
        datetime(2026, 9, 4, tzinfo=UTC),
        datetime(2026, 9, 1),
    ],
)
def test_budget_rejects_outside_window_or_ambiguous_clock(instant) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    with pytest.raises(ValueError):
        settings.budget.accrued_microusd(instant)


@pytest.fixture
def ledger(monkeypatch):
    # Moto interprets the real DynamoDB expressions locally. No AWS credential
    # discovery, socket, or model call is needed for these accounting tests.
    with mock_aws(config={"core": {"service_whitelist": ["dynamodb"]}}):
        client = boto3.client("dynamodb", region_name="eu-central-1")
        client.create_table(
            TableName="synthetic-budget-table",
            KeySchema=[{"AttributeName": "quota_day", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "quota_day", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setattr(proxy, "_dynamodb_client", lambda _region: client)
        yield client


def seed(ledger, settings) -> None:
    # This represents separately approved deployment initialization, not the
    # public handler: only the deployment identity may create this record.
    ledger.put_item(
        TableName=settings.daily_quota_table,
        Item=proxy.initial_budget_item(settings),
        ConditionExpression="attribute_not_exists(quota_day)",
    )


def record(ledger, key):
    return ledger.get_item(
        TableName="synthetic-budget-table",
        Key={"quota_day": {"S": key}},
        ConsistentRead=True,
    ).get("Item", {})


def test_absent_ledger_cannot_be_treated_as_an_unspent_budget(ledger) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 1, tzinfo=UTC))
    assert record(ledger, "2026-09-01") == {}


def test_unspent_money_carries_across_idle_days_without_minting_extra_credit(ledger) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    seed(ledger, settings)
    for _ in range(3):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 1, tzinfo=UTC))
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 1, tzinfo=UTC))
    assert record(ledger, "2026-09-01")["request_count"] == {"N": "3"}
    # No call on day two: day three inherits all remaining 700,000 micro-USD.
    for _ in range(7):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 3, tzinfo=UTC))
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 3, tzinfo=UTC))
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "1000000"}
    assert record(ledger, "2026-09-03")["request_count"] == {"N": "7"}
    assert "expires_at" not in record(ledger, "_budget_v1")


def test_money_is_the_only_daily_ceiling_and_rejection_cannot_charge(ledger) -> None:
    values = environment()
    values["FOLDERHOME_BUDGET_FORWARD_MICROUSD"] = "10000"
    settings = proxy.CloudDemoProxySettings.from_environment(values)
    seed(ledger, settings)
    # Day one releases one third of 1,000,000 micro-USD: 33 forwards of 10,000,
    # far beyond the former fixed count of 20. The 34th is refused by money alone,
    # and the refusal neither reserves money nor counts a request.
    for _ in range(33):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 1, tzinfo=UTC))
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 1, tzinfo=UTC))
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "330000"}
    assert record(ledger, "2026-09-01")["request_count"] == {"N": "33"}
    proxy._consume_daily_quota(settings, now=datetime(2026, 9, 2, tzinfo=UTC))
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "340000"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("FOLDERHOME_BUDGET_TOTAL_MICROUSD", "2000000"),
        ("FOLDERHOME_BUDGET_FORWARD_MICROUSD", "1"),
        ("FOLDERHOME_BUDGET_START_UTC", "2026-08-31"),
        ("FOLDERHOME_BUDGET_END_UTC", "2026-09-03"),
        ("FOLDERHOME_AGENT_RUNTIME_ENDPOINT", "another_endpoint"),
        ("FOLDERHOME_AGENT_RUNTIME_VERSION", "5"),
        ("FOLDERHOME_BUDGET_REVIEW_SHA256", "d" * 64),
        (
            "FOLDERHOME_AGENT_RUNTIME_ARN",
            "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/another",
        ),
    ],
)
def test_configuration_drift_never_resets_or_reuses_old_approval(ledger, field, value) -> None:
    values = environment()
    seed(ledger, proxy.CloudDemoProxySettings.from_environment(values))
    values[field] = value
    changed = proxy.CloudDemoProxySettings.from_environment(values)
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(changed, now=datetime(2026, 9, 1, tzinfo=UTC))
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "0"}
    assert record(ledger, "2026-09-01") == {}


def test_expired_window_never_writes_or_invokes(ledger, monkeypatch) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    seed(ledger, settings)
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 4, tzinfo=UTC))
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "0"}
    assert record(ledger, "2026-09-04") == {}


@pytest.mark.parametrize(
    "corruption",
    [
        {"reserved_microusd": {"N": "-1"}},
        {"reserved_microusd": {"N": "1000001"}},
        {"expires_at": {"N": "1"}},
    ],
)
def test_corrupt_or_expiring_ledger_fails_closed(ledger, corruption) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    ledger.put_item(
        TableName=settings.daily_quota_table,
        Item={**proxy.initial_budget_item(settings), **corruption},
    )
    with pytest.raises(proxy.CloudDemoQuotaExceeded):
        proxy._consume_daily_quota(settings, now=datetime(2026, 9, 1, tzinfo=UTC))
    assert record(ledger, "2026-09-01") == {}


def test_model_timeout_keeps_reservation_and_never_retries(ledger, monkeypatch) -> None:
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    seed(ledger, settings)
    for key, value in environment().items():
        monkeypatch.setenv(key, value)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    class UnavailableAgent:
        calls = 0

        def invoke_agent_runtime(self, **kwargs):
            self.calls += 1
            raise ReadTimeoutError(endpoint_url="https://synthetic.invalid")

    agent = UnavailableAgent()
    monkeypatch.setattr(proxy, "datetime", Clock)
    monkeypatch.setattr(proxy, "_agentcore_client", lambda _region: agent)
    monkeypatch.setattr(proxy, "_verify_runtime_target", lambda _settings: None)
    response = proxy.lambda_handler(
        {
            "httpMethod": "POST",
            "headers": {
                "origin": environment()["FOLDERHOME_PUBLIC_ORIGIN"],
                "content-type": "application/json",
            },
            "body": json.dumps({"prompt": "synthetic", "session_id": "s" * 33}),
        },
        None,
    )
    assert response["statusCode"] == 503
    assert agent.calls == 1
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "100000"}
    assert record(ledger, "2026-09-01")["request_count"] == {"N": "1"}


@pytest.mark.parametrize(
    "endpoint",
    [
        {"status": "READY", "liveVersion": "5", "targetVersion": "5"},
        {"status": "UPDATING", "liveVersion": "4", "targetVersion": "5"},
        {"status": "READY", "liveVersion": "4", "targetVersion": "5"},
        {"status": "READY"},
    ],
)
def test_runtime_version_drift_is_rejected_before_cost_or_model(ledger, monkeypatch, endpoint):
    settings = proxy.CloudDemoProxySettings.from_environment(environment())
    seed(ledger, settings)
    for key, value in environment().items():
        monkeypatch.setenv(key, value)

    class RuntimeControl:
        def get_agent_runtime_endpoint(self, **kwargs):
            assert kwargs == {"agentRuntimeId": "demo", "endpointName": "budget_v4"}
            return endpoint

    def forbidden(_region):
        pytest.fail("A drifted runtime must not be invoked")

    monkeypatch.setattr(proxy, "_runtime_control_client", lambda _region: RuntimeControl())
    monkeypatch.setattr(proxy, "_agentcore_client", forbidden)
    response = proxy.lambda_handler(
        {
            "httpMethod": "POST",
            "headers": {
                "origin": environment()["FOLDERHOME_PUBLIC_ORIGIN"],
                "content-type": "application/json",
            },
            "body": json.dumps({"prompt": "synthetic", "session_id": "s" * 33}),
        },
        None,
    )
    assert response["statusCode"] == 503
    assert record(ledger, "_budget_v1")["reserved_microusd"] == {"N": "0"}
