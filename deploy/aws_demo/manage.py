"""Preflight and deploy the quota-bounded FolderHome AWS demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

try:
    from .prepare_site import main as prepare_site
except ImportError:  # Direct execution from deploy/aws_demo.
    from prepare_site import main as prepare_site

_REGION = "eu-central-1"
_RUNTIME_NAME = "FolderHomeDemo"
_MODEL_ID = "eu.amazon.nova-micro-v1:0"
_BOOTSTRAP_STACK = "folderhome-demo-bootstrap"
_APPLICATION_STACK = "folderhome-demo-application"
_APPROVAL_TOKEN = "DEPLOY_FOLDERHOME_WITH_5_USD_ALERT"
_E2E_PROMPT = (
    "I had an accident with my Hyundai i10. Find my current car insurance, "
    "compare it with older policies, identify the right contact, prepare a claim "
    "letter, and save the next follow-up locally."
)
_FAILURE_STATUSES = {
    "CREATE_FAILED",
    "DELETE_FAILED",
    "DELETING",
    "UPDATE_FAILED",
}


class DeploymentError(RuntimeError):
    """Raised when a bounded deployment phase cannot be verified."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight", help="Run read-only local and AWS checks.")
    deploy = subparsers.add_parser("deploy", help="Create the explicitly approved demo.")
    deploy.add_argument("--budget-alert-email", required=True)
    deploy.add_argument("--budget-usd", default="5")
    deploy.add_argument("--approval-token", required=True)
    verify = subparsers.add_parser(
        "verify",
        help="Run one approved live E2E journey and read back all deployment gates.",
    )
    verify.add_argument("--budget-usd", default="5")
    verify.add_argument("--approval-token", required=True)
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    if args.command == "preflight":
        result = preflight(repository)
    elif args.command == "deploy":
        require_cost_approval(args.approval_token, args.budget_usd)
        result = deploy_demo(
            repository,
            budget_alert_email=args.budget_alert_email,
            budget_usd=args.budget_usd,
        )
    else:
        require_cost_approval(args.approval_token, args.budget_usd)
        result = verify_demo(repository, budget_usd=args.budget_usd)
    print(json.dumps(result, sort_keys=True))
    return 0


def require_cost_approval(token: str, budget_usd: str) -> None:
    """Require a deliberate exact token and the reviewed USD 5 alert threshold."""

    try:
        limit = Decimal(budget_usd)
    except InvalidOperation as exc:
        raise DeploymentError("Budget limit must be a decimal USD amount.") from exc
    if token != _APPROVAL_TOKEN or limit != Decimal("5"):
        raise DeploymentError(
            "AWS creation is blocked without the exact USD 5 alert approval and limit."
        )


def preflight(repository: Path) -> dict[str, object]:
    """Verify packages, templates, identity, model access, and name availability."""

    artifacts = {
        "agentcore": repository / "build" / "agentcore-direct.zip",
        "proxy": repository / "build" / "aws-demo-proxy.zip",
    }
    artifact_evidence = {
        name: _zip_evidence(path) for name, path in artifacts.items()
    }
    for template in (
        repository / "deploy" / "aws_demo" / "bootstrap.yaml",
        repository / "deploy" / "aws_demo" / "application.yaml",
    ):
        _aws_json(
            [
                "cloudformation",
                "validate-template",
                "--template-body",
                _file_uri(template),
            ]
        )
    identity = _aws_json(["sts", "get-caller-identity"])
    if not str(identity.get("Account", "")).isdigit():
        raise DeploymentError("AWS identity did not return a valid account.")
    profile = _model_profile()
    runtimes = _aws_json(
        ["bedrock-agentcore-control", "list-agent-runtimes", "--max-results", "100"]
    )
    named = [
        item
        for item in runtimes.get("agentRuntimes", [])
        if item.get("agentRuntimeName") == _RUNTIME_NAME
    ]
    return {
        "schema": "folderhome.aws-demo-preflight.v1",
        "status": "ready" if not named else "runtime_name_in_use",
        "region": _REGION,
        "aws_identity_verified": True,
        "model_id": _MODEL_ID,
        "model_status": profile["status"],
        "model_resource_count": len(profile["model_arns"]),
        "runtime_name_available": not named,
        "cloudformation_templates_valid": True,
        "artifacts": artifact_evidence,
        "mutations_performed": False,
    }


def deploy_demo(
    repository: Path,
    *,
    budget_alert_email: str,
    budget_usd: str,
) -> dict[str, object]:
    """Create a fresh runtime and application after the explicit cost gate."""

    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", budget_alert_email) is None:
        raise DeploymentError("Budget notification email is invalid.")
    evidence = preflight(repository)
    if evidence["status"] != "ready":
        raise DeploymentError("FolderHome runtime name already exists; refusing replacement.")
    profile = _model_profile()
    model_arns = profile["model_arns"]
    if len(model_arns) != 4:
        raise DeploymentError("Nova Micro profile must resolve to exactly four model ARNs.")
    _cloudformation_deploy(
        stack_name=_BOOTSTRAP_STACK,
        template=repository / "deploy" / "aws_demo" / "bootstrap.yaml",
        parameters={
            "AgentRuntimeName": _RUNTIME_NAME,
            "BudgetLimitUsd": budget_usd,
            "BudgetAlertEmail": budget_alert_email,
            "InferenceProfileArn": profile["profile_arn"],
            **{
                f"FoundationModelArn{index}": arn
                for index, arn in enumerate(model_arns, start=1)
            },
        },
        capabilities=("CAPABILITY_IAM",),
    )
    bootstrap = _stack_outputs(_BOOTSTRAP_STACK)
    artifact_bucket = bootstrap["ArtifactBucketName"]
    runtime_role_arn = bootstrap["AgentRuntimeRoleArn"]
    direct_zip = repository / "build" / "agentcore-direct.zip"
    proxy_zip = repository / "build" / "aws-demo-proxy.zip"
    direct_key, direct_version = _upload_versioned(artifact_bucket, "agentcore", direct_zip)
    proxy_key, proxy_version = _upload_versioned(artifact_bucket, "proxy", proxy_zip)
    artifact = _runtime_artifact(
        bucket=artifact_bucket,
        key=direct_key,
        version_id=direct_version,
    )
    runtime_common = {
        "agentRuntimeArtifact": artifact,
        "roleArn": runtime_role_arn,
        "networkConfiguration": {"networkMode": "PUBLIC"},
        "description": "FolderHome synthetic accident demo with a Strands master agent",
        "protocolConfiguration": {"serverProtocol": "HTTP"},
        "lifecycleConfiguration": {
            "idleRuntimeSessionTimeout": 60,
            "maxLifetime": 1800,
        },
        "environmentVariables": {
            "FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "bedrock",
            "FOLDERHOME_AGENTCORE_ALLOW_BEDROCK": "1",
            "FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA": "1",
            "FOLDERHOME_AGENTCORE_BEDROCK_MODEL_ID": _MODEL_ID,
            "FOLDERHOME_AGENTCORE_MAX_OUTPUT_TOKENS": "512",
            "FOLDERHOME_AGENTCORE_BEDROCK_CONNECT_TIMEOUT_SECONDS": "3",
            "FOLDERHOME_AGENTCORE_BEDROCK_READ_TIMEOUT_SECONDS": "18",
        },
    }
    created = _aws_json(
        [
            "bedrock-agentcore-control",
            "create-agent-runtime",
            "--cli-input-json",
            json.dumps(
                {
                    "agentRuntimeName": _RUNTIME_NAME,
                    **runtime_common,
                    "clientToken": str(uuid.uuid4()),
                    "tags": {"Project": "FolderHome", "DataClass": "SyntheticOnly"},
                },
                separators=(",", ":"),
            ),
        ]
    )
    runtime_id = _required_text(created, "agentRuntimeId")
    runtime_arn = _required_text(created, "agentRuntimeArn")
    _write_state(repository, {"phase": "runtime_created", "runtime_id": runtime_id})
    _wait_runtime(runtime_id)
    updated = _aws_json(
        [
            "bedrock-agentcore-control",
            "update-agent-runtime",
            "--cli-input-json",
            json.dumps(
                {
                    "agentRuntimeId": runtime_id,
                    **runtime_common,
                    "metadataConfiguration": {"requireMMDSV2": True},
                    "clientToken": str(uuid.uuid4()),
                },
                separators=(",", ":"),
            ),
        ]
    )
    updated_version = _required_text(updated, "agentRuntimeVersion")
    runtime = _wait_runtime(runtime_id)
    if runtime.get("agentRuntimeVersion") != updated_version:
        raise DeploymentError("Runtime readback does not match the IMDSv2 version.")
    if runtime.get("metadataConfiguration", {}).get("requireMMDSV2") is not True:
        raise DeploymentError("Runtime became ready without the required IMDSv2 setting.")
    endpoint = _wait_endpoint(runtime_id, "DEFAULT", expected_version=updated_version)
    if endpoint.get("status") != "READY":
        raise DeploymentError("AgentCore DEFAULT endpoint did not become ready.")
    _cloudformation_deploy(
        stack_name=_APPLICATION_STACK,
        template=repository / "deploy" / "aws_demo" / "application.yaml",
        parameters={
            "AgentRuntimeArn": runtime_arn,
            "ProxyCodeBucket": artifact_bucket,
            "ProxyCodeKey": proxy_key,
            "ProxyCodeVersion": proxy_version,
        },
        capabilities=("CAPABILITY_IAM",),
    )
    application = _stack_outputs(_APPLICATION_STACK)
    api_key = _aws_json(
        [
            "apigateway",
            "get-api-key",
            "--api-key",
            application["ApiKeyId"],
            "--include-value",
        ]
    )
    key_value = _required_text(api_key, "value")
    site_build = repository / "build" / "aws-demo-site"
    prepare_site(
        [
            "--api-base-url",
            application["ApiBaseUrl"],
            "--api-key",
            key_value,
            "--output",
            str(site_build),
        ]
    )
    _aws_raw(
        [
            "s3",
            "sync",
            str(site_build),
            f"s3://{application['SiteBucketName']}",
            "--delete",
            "--cache-control",
            "no-cache,no-store,must-revalidate",
        ]
    )
    invalidation = _aws_json(
        [
            "cloudfront",
            "create-invalidation",
            "--distribution-id",
            application["CloudFrontDistributionId"],
            "--paths",
            "/*",
        ]
    )
    _write_state(
        repository,
        {
            "phase": "deployed",
            "runtime_id": runtime_id,
            "site_url": application["SiteUrl"],
            "api_base_url": application["ApiBaseUrl"],
            "distribution_id": application["CloudFrontDistributionId"],
            "invalidation_id": invalidation.get("Invalidation", {}).get("Id"),
        },
    )
    return {
        "schema": "folderhome.aws-demo-deployment.v1",
        "status": "deployed_pending_e2e",
        "region": _REGION,
        "site_url": application["SiteUrl"],
        "runtime_status": runtime.get("status"),
        "endpoint_status": endpoint.get("status"),
        "daily_request_quota": 20,
        "hard_agentcore_forward_limit": 20,
        "budget_limit_usd": budget_usd,
        "api_key_value_logged": False,
    }


def verify_demo(repository: Path, *, budget_usd: str) -> dict[str, object]:
    """Exercise one live synthetic journey and verify every operational boundary."""

    state = _load_state(repository)
    if state.get("phase") != "deployed":
        raise DeploymentError("Deployment state is not ready for live verification.")
    runtime_id = _required_text(state, "runtime_id")
    bootstrap = _stack_outputs(_BOOTSTRAP_STACK)
    application = _stack_outputs(_APPLICATION_STACK)
    api_key = _aws_json(
        [
            "apigateway",
            "get-api-key",
            "--api-key",
            application["ApiKeyId"],
            "--include-value",
        ]
    )
    key_value = _required_text(api_key, "value")
    site_url = application["SiteUrl"]
    site_origin = site_url.removesuffix("/")
    _wait_public_site(site_url)
    missing_key_status, _ = _http_json(
        application["ApiBaseUrl"],
        method="POST",
        payload={"prompt": _E2E_PROMPT, "session_id": _session_id()},
        headers={"Origin": site_origin},
    )
    if missing_key_status not in {403, 429}:
        raise DeploymentError("Direct demo API accepted a request without its quota key.")
    session_id = _session_id()
    status, prepared = _http_json(
        application["ApiBaseUrl"],
        method="POST",
        payload={"prompt": _E2E_PROMPT, "session_id": session_id},
        headers={"Origin": site_origin, "X-Api-Key": key_value},
    )
    if status != 200:
        raise DeploymentError(f"Live plan request returned HTTP {status}.")
    confirmation = validate_prepared_response(prepared)
    status, confirmed = _http_json(
        application["ApiBaseUrl"],
        method="POST",
        payload={"prompt": confirmation, "session_id": session_id},
        headers={"Origin": site_origin, "X-Api-Key": key_value},
    )
    if status != 200:
        raise DeploymentError(f"Live confirmation request returned HTTP {status}.")
    generated_results = validate_confirmed_response(confirmed)
    runtime = _aws_json(
        [
            "bedrock-agentcore-control",
            "get-agent-runtime",
            "--agent-runtime-id",
            runtime_id,
        ]
    )
    endpoint = _aws_json(
        [
            "bedrock-agentcore-control",
            "get-agent-runtime-endpoint",
            "--agent-runtime-id",
            runtime_id,
            "--endpoint-name",
            "DEFAULT",
        ]
    )
    if runtime.get("status") != "READY" or endpoint.get("status") != "READY":
        raise DeploymentError("AgentCore runtime or DEFAULT endpoint is not ready.")
    if endpoint.get("liveVersion") != runtime.get("agentRuntimeVersion"):
        raise DeploymentError("DEFAULT endpoint is not serving the latest runtime version.")
    if runtime.get("metadataConfiguration", {}).get("requireMMDSV2") is not True:
        raise DeploymentError("AgentCore runtime does not require IMDSv2.")
    usage_plan = _aws_json(
        ["apigateway", "get-usage-plan", "--usage-plan-id", application["UsagePlanId"]]
    )
    quota = usage_plan.get("quota", {})
    if quota.get("limit") != 20 or quota.get("period") != "DAY":
        raise DeploymentError("Public API daily quota does not match the reviewed limit.")
    quota_item = _aws_json(
        [
            "dynamodb",
            "get-item",
            "--table-name",
            application["DailyQuotaTableName"],
            "--key",
            json.dumps(
                {"quota_day": {"S": datetime.now(UTC).date().isoformat()}},
                separators=(",", ":"),
            ),
            "--consistent-read",
        ]
    ).get("Item", {})
    try:
        forwarded_today = int(quota_item["request_count"]["N"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentError("Atomic daily quota counter is unavailable.") from exc
    if not 2 <= forwarded_today <= 20:
        raise DeploymentError("Atomic daily quota counter is outside its hard bounds.")
    concurrency = _aws_json(
        [
            "lambda",
            "get-function-concurrency",
            "--function-name",
            application["ProxyFunctionName"],
        ]
    )
    if concurrency.get("ReservedConcurrentExecutions") != 2:
        raise DeploymentError("Lambda reserved concurrency is not two.")
    proxy_logs = _aws_json(
        [
            "logs",
            "describe-log-groups",
            "--log-group-name-prefix",
            application["ProxyLogGroupName"],
        ]
    ).get("logGroups", [])
    exact_proxy_logs = [
        item
        for item in proxy_logs
        if item.get("logGroupName") == application["ProxyLogGroupName"]
    ]
    if len(exact_proxy_logs) != 1 or exact_proxy_logs[0].get("retentionInDays") != 7:
        raise DeploymentError("Lambda log retention is not seven days.")
    runtime_log_groups = _set_runtime_log_retention(runtime_id)
    distribution = _aws_json(
        [
            "cloudfront",
            "get-distribution",
            "--id",
            application["CloudFrontDistributionId"],
        ]
    )
    if distribution.get("Distribution", {}).get("Status") != "Deployed":
        raise DeploymentError("CloudFront distribution is not deployed.")
    public_access = _aws_json(
        [
            "s3api",
            "get-public-access-block",
            "--bucket",
            application["SiteBucketName"],
        ]
    ).get("PublicAccessBlockConfiguration", {})
    if not all(
        public_access.get(key) is True
        for key in (
            "BlockPublicAcls",
            "IgnorePublicAcls",
            "BlockPublicPolicy",
            "RestrictPublicBuckets",
        )
    ):
        raise DeploymentError("Static site bucket public-access block is incomplete.")
    identity = _aws_json(["sts", "get-caller-identity"])
    budget = _aws_json(
        [
            "budgets",
            "describe-budget",
            "--account-id",
            _required_text(identity, "Account"),
            "--budget-name",
            bootstrap["BudgetName"],
        ]
    ).get("Budget", {})
    if Decimal(str(budget.get("BudgetLimit", {}).get("Amount"))) != Decimal(
        budget_usd
    ):
        raise DeploymentError("AWS budget warning threshold does not match approval.")
    _write_state(
        repository,
        {
            **state,
            "phase": "verified",
            "e2e_verified": True,
            "generated_result_count": len(generated_results),
            "runtime_log_group_count": len(runtime_log_groups),
        },
    )
    return {
        "schema": "folderhome.aws-demo-verification.v1",
        "status": "verified",
        "site_url": site_url,
        "synthetic_e2e_completed": True,
        "model_provider": "bedrock",
        "specialist_model_provider": "fixture",
        "generated_result_count": len(generated_results),
        "runtime_and_endpoint_ready": True,
        "imds_v2_required": True,
        "daily_request_quota": 20,
        "hard_agentcore_forward_limit": 20,
        "agentcore_forwards_today": forwarded_today,
        "lambda_reserved_concurrency": 2,
        "log_retention_days": 7,
        "site_bucket_private": True,
        "budget_alert_usd": budget_usd,
        "api_key_value_logged": False,
    }


def validate_prepared_response(payload: dict[str, Any]) -> str:
    """Validate the exact evidence expected from the live master-agent turn."""

    plan = payload.get("plan")
    if not isinstance(plan, dict):
        raise DeploymentError("Live plan response is missing its plan.")
    confirmation = plan.get("confirmation_command")
    if (
        payload.get("schema") != "folderhome.agentcore-response.v1"
        or payload.get("synthetic_data_only") is not True
        or payload.get("model_provider") != "bedrock"
        or payload.get("specialist_model_provider") != "fixture"
        or payload.get("external_network_used") is not True
        or plan.get("status") != "confirmation_required"
        or not isinstance(confirmation, str)
        or not confirmation.startswith("/confirm accident_demo_")
        or len(plan.get("steps", [])) != 4
        or plan.get("external_actions_performed") != []
    ):
        raise DeploymentError("Live master-agent evidence is incomplete or inconsistent.")
    return confirmation


def validate_confirmed_response(payload: dict[str, Any]) -> list[dict[str, object]]:
    """Validate deterministic local execution and the absence of external effects."""

    result = payload.get("result")
    if not isinstance(result, dict):
        raise DeploymentError("Live confirmation response is missing its result.")
    generated = result.get("generated_results")
    if (
        payload.get("schema") != "folderhome.agentcore-response.v1"
        or payload.get("synthetic_data_only") is not True
        or payload.get("model_provider") != "bedrock"
        or payload.get("specialist_model_provider") != "fixture"
        or result.get("status") != "executed"
        or result.get("external_actions_performed") != []
        or result.get("mail_sent") is not False
        or result.get("external_calendar_used") is not False
        or result.get("phone_call_made") is not False
        or not isinstance(generated, list)
        or len(generated) != 4
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("sha256"), str)
            or len(item["sha256"]) != 64
            for item in generated
        )
    ):
        raise DeploymentError("Live deterministic execution evidence is inconsistent.")
    return generated


def _load_state(repository: Path) -> dict[str, Any]:
    state = repository / "build" / "aws-demo-deployment-state.json"
    if not state.is_file():
        raise DeploymentError("Ignored AWS deployment state is missing.")
    try:
        payload = json.loads(state.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeploymentError("AWS deployment state is invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise DeploymentError("AWS deployment state must be a JSON object.")
    return payload


def _session_id() -> str:
    return f"folderhome-public-e2e-{uuid.uuid4().hex}"


def _wait_public_site(site_url: str) -> None:
    for _ in range(60):
        try:
            request = urllib.request.Request(site_url, method="GET")
            with urllib.request.urlopen(request, timeout=10) as response:
                content = response.read(1_048_577)
                if (
                    response.status == 200
                    and len(content) <= 1_048_576
                    and b"FolderHome" in content
                ):
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(10)
    raise DeploymentError("CloudFront site did not become readable within ten minutes.")


def _http_json(
    url: str,
    *,
    method: str,
    payload: dict[str, str],
    headers: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            status = response.status
            content = response.read(2_097_153)
    except urllib.error.HTTPError as exc:
        status = exc.code
        content = exc.read(2_097_153)
    except (OSError, urllib.error.URLError) as exc:
        raise DeploymentError("Live demo HTTP request failed.") from exc
    if len(content) > 2_097_152:
        raise DeploymentError("Live demo HTTP response exceeds two MiB.")
    try:
        decoded = json.loads(content.decode("utf-8")) if content else {}
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeploymentError("Live demo HTTP response is not valid JSON.") from exc
    if not isinstance(decoded, dict):
        raise DeploymentError("Live demo HTTP response must be a JSON object.")
    return status, decoded


def _set_runtime_log_retention(runtime_id: str) -> list[str]:
    prefix = f"/aws/bedrock-agentcore/runtimes/{runtime_id}-"
    for _ in range(12):
        payload = _aws_json(
            [
                "logs",
                "describe-log-groups",
                "--log-group-name-prefix",
                prefix,
            ]
        )
        names = [
            item.get("logGroupName")
            for item in payload.get("logGroups", [])
            if isinstance(item.get("logGroupName"), str)
            and "bedrock-agentcore" in item["logGroupName"]
            and item["logGroupName"].startswith(prefix)
        ]
        if names:
            for name in names:
                _aws_raw(
                    [
                        "logs",
                        "put-retention-policy",
                        "--log-group-name",
                        name,
                        "--retention-in-days",
                        "7",
                    ]
                )
            verified = _aws_json(
                [
                    "logs",
                    "describe-log-groups",
                    "--log-group-name-prefix",
                    prefix,
                ]
            ).get("logGroups", [])
            readback = {
                item.get("logGroupName"): item.get("retentionInDays")
                for item in verified
            }
            if all(readback.get(name) == 7 for name in names):
                return names
            raise DeploymentError("AgentCore log retention readback failed.")
        time.sleep(5)
    raise DeploymentError("AgentCore runtime log groups were not created after E2E.")


def _model_profile() -> dict[str, object]:
    payload = _aws_json(
        [
            "bedrock",
            "get-inference-profile",
            "--inference-profile-identifier",
            _MODEL_ID,
        ]
    )
    if payload.get("status") != "ACTIVE":
        raise DeploymentError("Nova Micro inference profile is not active.")
    model_arns = [
        item.get("modelArn")
        for item in payload.get("models", [])
        if isinstance(item, dict) and isinstance(item.get("modelArn"), str)
    ]
    return {
        "status": payload["status"],
        "profile_arn": _required_text(payload, "inferenceProfileArn"),
        "model_arns": model_arns,
    }


def _runtime_artifact(*, bucket: str, key: str, version_id: str) -> dict[str, object]:
    return {
        "codeConfiguration": {
            "code": {
                "s3": {"bucket": bucket, "prefix": key, "versionId": version_id}
            },
            "runtime": "PYTHON_3_12",
            "entryPoint": ["agentcore_entrypoint.py"],
        }
    }


def _wait_runtime(runtime_id: str) -> dict[str, Any]:
    for _ in range(90):
        payload = _aws_json(
            [
                "bedrock-agentcore-control",
                "get-agent-runtime",
                "--agent-runtime-id",
                runtime_id,
            ]
        )
        status = payload.get("status")
        if status == "READY":
            return payload
        if status in _FAILURE_STATUSES:
            raise DeploymentError(f"AgentCore runtime stopped in status {status}.")
        time.sleep(10)
    raise DeploymentError("AgentCore runtime did not become ready within 15 minutes.")


def _wait_endpoint(
    runtime_id: str,
    name: str,
    *,
    expected_version: str,
) -> dict[str, Any]:
    for _ in range(60):
        try:
            payload = _aws_json(
                [
                    "bedrock-agentcore-control",
                    "get-agent-runtime-endpoint",
                    "--agent-runtime-id",
                    runtime_id,
                    "--endpoint-name",
                    name,
                ]
            )
        except DeploymentError:
            time.sleep(5)
            continue
        status = payload.get("status")
        if status == "READY" and payload.get("liveVersion") == expected_version:
            return payload
        if status in _FAILURE_STATUSES:
            raise DeploymentError(f"AgentCore endpoint stopped in status {status}.")
        time.sleep(5)
    raise DeploymentError("AgentCore DEFAULT endpoint did not become ready within 5 minutes.")


def _cloudformation_deploy(
    *,
    stack_name: str,
    template: Path,
    parameters: dict[str, str],
    capabilities: tuple[str, ...],
) -> None:
    command = [
        "cloudformation",
        "deploy",
        "--stack-name",
        stack_name,
        "--template-file",
        str(template),
        "--no-fail-on-empty-changeset",
        "--parameter-overrides",
        *(f"{key}={value}" for key, value in parameters.items()),
    ]
    if capabilities:
        command.extend(("--capabilities", *capabilities))
    _aws_raw(command)


def _stack_outputs(stack_name: str) -> dict[str, str]:
    payload = _aws_json(
        ["cloudformation", "describe-stacks", "--stack-name", stack_name]
    )
    stacks = payload.get("Stacks", [])
    if len(stacks) != 1 or stacks[0].get("StackStatus") not in {
        "CREATE_COMPLETE",
        "UPDATE_COMPLETE",
    }:
        raise DeploymentError(f"CloudFormation stack {stack_name} is not complete.")
    outputs = {
        item["OutputKey"]: item["OutputValue"]
        for item in stacks[0].get("Outputs", [])
        if "OutputKey" in item and "OutputValue" in item
    }
    return outputs


def _upload_versioned(bucket: str, prefix: str, path: Path) -> tuple[str, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    key = f"{prefix}/{path.stem}-{digest[:16]}.zip"
    response = _aws_json(
        [
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--body",
            str(path),
            "--server-side-encryption",
            "AES256",
        ]
    )
    return key, _required_text(response, "VersionId")


def _zip_evidence(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise DeploymentError(f"Required build artifact is missing: {path.name}")
    try:
        with zipfile.ZipFile(path) as archive:
            first_bad = archive.testzip()
            entries = len(archive.infolist())
    except zipfile.BadZipFile as exc:
        raise DeploymentError(f"Build artifact is not a ZIP file: {path.name}") from exc
    if first_bad is not None:
        raise DeploymentError(f"Build artifact contains a corrupt member: {first_bad}")
    payload = path.read_bytes()
    return {
        "filename": path.name,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "entries": entries,
    }


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise DeploymentError(f"AWS response is missing {key}.")
    return value


def _write_state(repository: Path, payload: dict[str, object]) -> None:
    state = repository / "build" / "aws-demo-deployment-state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    temporary = state.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(state)


def _file_uri(path: Path) -> str:
    return "file://" + path.resolve().as_posix()


def _aws_json(arguments: list[str]) -> dict[str, Any]:
    output = _aws_raw(arguments, output="json")
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise DeploymentError("AWS CLI returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise DeploymentError("AWS CLI response must be a JSON object.")
    return payload


def _aws_raw(arguments: list[str], *, output: str | None = None) -> str:
    executable = shutil.which("aws")
    if executable is None:
        raise DeploymentError("AWS CLI is not installed.")
    command = [executable, *arguments, "--region", _REGION, "--no-cli-pager"]
    if output is not None:
        command.extend(("--output", output))
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = completed.stderr.strip().splitlines()
        summary = message[-1] if message else "AWS CLI command failed."
        raise DeploymentError(summary)
    return completed.stdout


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
