"""API Gateway to AgentCore proxy for the quota-bounded public demo."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from .budget import CloudDemoBudget

_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{32,127}")
_MAX_REQUEST_BYTES = 4_096
_MAX_RESPONSE_BYTES = 2_097_152
_TABLE_NAME = re.compile(r"[A-Za-z0-9_.-]{3,255}")


@dataclass(frozen=True, slots=True)
class CloudDemoProxySettings:
    """Non-secret deployment configuration for one public demo proxy."""

    agent_runtime_arn: str
    public_origin: str
    aws_region: str
    daily_quota_table: str
    budget: CloudDemoBudget | None = None
    runtime_endpoint: str = ""
    runtime_version: str = ""
    budget_review_sha256: str = ""

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
    ) -> CloudDemoProxySettings:
        runtime_arn = environment.get("FOLDERHOME_AGENT_RUNTIME_ARN", "")
        public_origin = environment.get("FOLDERHOME_PUBLIC_ORIGIN", "")
        aws_region = environment.get("AWS_REGION", "")
        quota_table = environment.get("FOLDERHOME_DAILY_QUOTA_TABLE", "")
        if not runtime_arn.startswith("arn:aws:bedrock-agentcore:"):
            raise ValueError("Public proxy requires an explicit AgentCore runtime ARN.")
        if not public_origin.startswith("https://") or public_origin.endswith("/"):
            raise ValueError("Public proxy requires one exact HTTPS origin without slash.")
        if not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", aws_region):
            raise ValueError("Public proxy requires an explicit AWS region.")
        if _TABLE_NAME.fullmatch(quota_table) is None:
            raise ValueError("Public proxy requires an explicit DynamoDB quota table.")
        endpoint = environment.get("FOLDERHOME_AGENT_RUNTIME_ENDPOINT", "")
        version = environment.get("FOLDERHOME_AGENT_RUNTIME_VERSION", "")
        review = environment.get("FOLDERHOME_BUDGET_REVIEW_SHA256", "")
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,47}", endpoint) is None or endpoint == "DEFAULT":
            raise ValueError("Public proxy requires a dedicated reviewed runtime endpoint.")
        if re.fullmatch(r"[1-9][0-9]{0,4}", version) is None:
            raise ValueError("Public proxy requires an explicit runtime version.")
        if re.fullmatch(r"[0-9a-f]{64}", review) is None:
            raise ValueError("Public proxy requires the cost-review artifact SHA-256.")
        return cls(
            runtime_arn,
            public_origin,
            aws_region,
            quota_table,
            CloudDemoBudget.from_environment(environment),
            endpoint,
            version,
            review,
        )


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, object]:
    """Validate one browser request and relay it to the IAM-only runtime."""

    try:
        settings = CloudDemoProxySettings.from_environment(os.environ)
    except ValueError:
        return _response(500, {"error": "Cloud demo configuration is unavailable."})
    headers = {
        str(key).casefold(): str(value)
        for key, value in (event.get("headers") or {}).items()
        if value is not None
    }
    origin = headers.get("origin", "")
    cors = _cors_headers(settings.public_origin) if origin == settings.public_origin else {}
    method = str(event.get("httpMethod", "")).upper()
    if method == "OPTIONS" and origin == settings.public_origin:
        return _response(204, None, headers=cors)
    if method != "POST":
        return _response(405, {"error": "Only POST is allowed."}, headers=cors)
    if origin != settings.public_origin:
        return _response(403, {"error": "Browser origin is not allowed."})
    if not headers.get("content-type", "").casefold().startswith("application/json"):
        return _response(
            415,
            {"error": "Content-Type must be application/json."},
            headers=cors,
        )
    try:
        request = _request_payload(event)
        _verify_runtime_target(settings)
        _consume_daily_quota(settings)
        client = _agentcore_client(settings.aws_region)
        result = client.invoke_agent_runtime(
            agentRuntimeArn=settings.agent_runtime_arn,
            qualifier=settings.runtime_endpoint,
            runtimeSessionId=request["session_id"],
            contentType="application/json",
            accept="application/json",
            payload=json.dumps(
                {"prompt": request["prompt"]},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8"),
        )
        content = result["response"].read(_MAX_RESPONSE_BYTES + 1)
        if len(content) > _MAX_RESPONSE_BYTES:
            raise ValueError("AgentCore response exceeds the public demo limit.")
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(payload, dict):
            raise ValueError("AgentCore response is not a JSON object.")
        status = int(result.get("statusCode", 200))
        return _response(status, payload, headers=cors)
    except CloudDemoRuntimeDrift:
        return _response(
            503,
            {"error": "The reviewed cloud demo runtime is unavailable."},
            headers=cors,
        )
    except CloudDemoQuotaExceeded:
        return _response(
            429,
            {"error": "The public demo's UTC quota or monetary budget is unavailable."},
            headers=cors,
        )
    except (KeyError, TypeError, UnicodeError, ValueError):
        return _response(400, {"error": "Public demo request is invalid."}, headers=cors)
    except Exception as exc:  # AWS SDK exceptions vary by runtime version.
        if exc.__class__.__module__.startswith(("botocore", "boto3")):
            return _response(
                503,
                {"error": "AgentCore is temporarily unavailable."},
                headers=cors,
            )
        raise


def _request_payload(event: Mapping[str, object]) -> dict[str, str]:
    raw = event.get("body", "")
    if not isinstance(raw, str):
        raise ValueError("Request body must be text.")
    if event.get("isBase64Encoded") is True:
        body = base64.b64decode(raw, validate=True)
    else:
        body = raw.encode("utf-8")
    if not 1 <= len(body) <= _MAX_REQUEST_BYTES:
        raise ValueError("Request body exceeds the public demo limit.")
    payload = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(payload, dict) or set(payload) != {"prompt", "session_id"}:
        raise ValueError("Request must contain exactly prompt and session_id.")
    prompt = payload["prompt"]
    session_id = payload["session_id"]
    if not isinstance(prompt, str) or not isinstance(session_id, str):
        raise ValueError("Prompt and session ID must be text.")
    normalized = " ".join(prompt.split())
    if not 1 <= len(normalized) <= 1_000:
        raise ValueError("Prompt length is invalid.")
    if _SESSION_ID.fullmatch(session_id) is None:
        raise ValueError("Session ID is invalid.")
    return {"prompt": normalized, "session_id": session_id}


def _agentcore_client(region: str):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-agentcore",
        region_name=region,
        config=Config(
            connect_timeout=3,
            read_timeout=25,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )


def _dynamodb_client(region: str):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "dynamodb",
        region_name=region,
        config=Config(
            connect_timeout=2,
            read_timeout=3,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )


def _runtime_control_client(region: str):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-agentcore-control",
        region_name=region,
        config=Config(
            connect_timeout=2,
            read_timeout=3,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )


def _verify_runtime_target(settings: CloudDemoProxySettings) -> None:
    endpoint = _runtime_control_client(settings.aws_region).get_agent_runtime_endpoint(
        agentRuntimeId=settings.agent_runtime_arn.rsplit("/", 1)[-1],
        endpointName=settings.runtime_endpoint,
    )
    if (
        endpoint.get("status") != "READY"
        or endpoint.get("liveVersion") != settings.runtime_version
        or endpoint.get("targetVersion", settings.runtime_version) != settings.runtime_version
    ):
        raise CloudDemoRuntimeDrift


class CloudDemoRuntimeDrift(RuntimeError):
    """The dedicated endpoint is not serving the reviewed runtime version."""


def _consume_daily_quota(
    settings: CloudDemoProxySettings,
    *,
    now: datetime | None = None,
) -> None:
    instant = now or datetime.now(UTC)
    if settings.budget is None:
        raise CloudDemoQuotaExceeded("Explicit monetary policy is required.")
    try:
        accrued = settings.budget.accrued_microusd(instant)
    except ValueError as exc:
        raise CloudDemoQuotaExceeded("The budget window is not active.") from exc
    utc_instant = instant.astimezone(UTC)
    reservation = settings.budget.forward_microusd
    if accrued < reservation:
        raise CloudDemoQuotaExceeded("Not enough monetary entitlement for one forward.")
    try:
        # The per-day counter is telemetry only; the money ledger below is the
        # single daily ceiling (policy P-010: cumulative entitlement with carry-over).
        # One transaction, no check-then-write race. Never refund: a timeout
        # does not establish that AgentCore or the model did no billable work.
        _dynamodb_client(settings.aws_region).transact_write_items(
            ClientRequestToken=str(uuid4()),
            TransactItems=[
                {
                    "Update": {
                        "TableName": settings.daily_quota_table,
                        "Key": {"quota_day": {"S": utc_instant.date().isoformat()}},
                        "UpdateExpression": (
                            "SET request_count = if_not_exists(request_count, :zero) + :one, "
                            "expires_at = :expires"
                        ),
                        "ConditionExpression": (
                            "attribute_not_exists(request_count) OR request_count >= :zero"
                        ),
                        "ExpressionAttributeValues": {
                            ":zero": {"N": "0"},
                            ":one": {"N": "1"},
                            ":expires": {
                                "N": str(int((utc_instant + timedelta(days=2)).timestamp()))
                            },
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": settings.daily_quota_table,
                        "Key": {"quota_day": {"S": "_budget_v1"}},
                        "UpdateExpression": "SET reserved_microusd = reserved_microusd + :reserve",
                        "ConditionExpression": (
                            "policy_sha256 = :policy AND attribute_not_exists(expires_at) AND "
                            "reserved_microusd >= :zero AND reserved_microusd <= :maximum"
                        ),
                        "ExpressionAttributeValues": {
                            ":policy": {"S": budget_policy_sha256(settings)},
                            ":zero": {"N": "0"},
                            ":maximum": {"N": str(accrued - reservation)},
                            ":reserve": {"N": str(reservation)},
                        },
                    }
                },
            ],
        )
    except Exception as exc:  # AWS SDK exception classes are generated per client.
        error = getattr(exc, "response", {}).get("Error", {})
        reasons = getattr(exc, "response", {}).get("CancellationReasons", [])
        if error.get("Code") == "TransactionCanceledException" and any(
            item.get("Code") == "ConditionalCheckFailed" for item in reasons
        ):
            raise CloudDemoQuotaExceeded from exc
        raise


def budget_policy_sha256(settings: CloudDemoProxySettings) -> str:
    """Bind the finite allocation to this exact proxy configuration."""
    if settings.budget is None:
        raise ValueError("Explicit monetary policy is required.")
    policy = {
        "schema": "folderhome.cloud-budget.v1",
        "runtime_arn": settings.agent_runtime_arn,
        "runtime_endpoint": settings.runtime_endpoint,
        "runtime_version": settings.runtime_version,
        "cost_review_sha256": settings.budget_review_sha256,
        "origin": settings.public_origin,
        "region": settings.aws_region,
        "quota_table": settings.daily_quota_table,
        "total_microusd": settings.budget.total_microusd,
        "forward_microusd": settings.budget.forward_microusd,
        "start_utc": settings.budget.start_utc.isoformat(),
        "end_utc": settings.budget.end_utc.isoformat(),
    }
    return hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def initial_budget_item(settings: CloudDemoProxySettings) -> dict[str, Any]:
    """Build an explicit deployment seed; the public proxy never creates it.

    Operators must use a conditional create and carry previously spent money
    into the approved allocation. Lost/replaced tables are not fresh budgets.
    """
    return {
        "quota_day": {"S": "_budget_v1"},
        "policy_sha256": {"S": budget_policy_sha256(settings)},
        "reserved_microusd": {"N": "0"},
    }


class CloudDemoQuotaExceeded(RuntimeError):
    """The finite budget or approved ledger cannot admit a forward."""


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Vary": "Origin",
    }


def _response(
    status: int,
    payload: dict[str, object] | None,
    *,
    headers: Mapping[str, str] | None = None,
) -> dict[str, object]:
    response_headers = {
        "Cache-Control": "no-store",
        "Content-Type": "application/json; charset=utf-8",
        "X-Content-Type-Options": "nosniff",
        **dict(headers or {}),
    }
    return {
        "statusCode": status,
        "headers": response_headers,
        "body": "" if payload is None else json.dumps(payload, ensure_ascii=False),
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"Duplicate JSON key is not allowed: {key}")
        payload[key] = value
    return payload


__all__ = ["CloudDemoProxySettings", "lambda_handler"]
