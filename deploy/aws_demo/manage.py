"""Preflight and deploy the quota-bounded FolderHome AWS demonstration."""

from __future__ import annotations

import argparse
import base64
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
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from folderhome.cloud_demo.budget import CloudDemoBudget
from folderhome.cloud_demo.proxy import (
    CloudDemoProxySettings,
    budget_policy_sha256,
    initial_budget_item,
)

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
    subparsers.add_parser("cost-profile", help="Print the runtime cost profile and hash offline.")
    subparsers.add_parser("preflight", help="Run read-only local and AWS checks.")
    deploy = subparsers.add_parser("deploy", help="Create the explicitly approved demo.")
    deploy.add_argument("--budget-alert-email", required=True)
    deploy.add_argument("--budget-usd", default="5")
    deploy.add_argument("--approval-token", required=True)
    deploy.add_argument("--budget-review", type=Path, required=True)
    verify = subparsers.add_parser(
        "verify",
        help="Run one approved live E2E journey and read back all deployment gates.",
    )
    verify.add_argument("--budget-usd", default="5")
    verify.add_argument("--approval-token", required=True)
    verify.add_argument("--budget-review", type=Path, required=True)
    migrate = subparsers.add_parser(
        "migrate",
        help="Bring the existing demo under the reviewed budget without a second runtime.",
    )
    migrate.add_argument("--budget-usd", default="5")
    migrate.add_argument("--approval-token", required=True)
    migrate.add_argument("--budget-review", type=Path, required=True)
    migrate.add_argument("--publish-site", action="store_true")
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    if args.command == "cost-profile":
        profile = runtime_cost_profile()
        result = {
            "schema": "folderhome.cloud-runtime-cost-profile.v1",
            "profile": profile,
            "sha256": hashlib.sha256(
                json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
    elif args.command == "preflight":
        result = preflight(repository)
    elif args.command == "deploy":
        require_cost_approval(args.approval_token, args.budget_usd)
        result = deploy_demo(
            repository,
            budget_alert_email=args.budget_alert_email,
            budget_usd=args.budget_usd,
            budget_review=args.budget_review,
        )
    elif args.command == "migrate":
        require_cost_approval(args.approval_token, args.budget_usd)
        result = migrate_demo(
            repository,
            budget_usd=args.budget_usd,
            budget_review=args.budget_review,
            publish_site=args.publish_site,
        )
    else:
        require_cost_approval(args.approval_token, args.budget_usd)
        result = verify_demo(
            repository, budget_usd=args.budget_usd, budget_review=args.budget_review
        )
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


def load_budget_review(
    repository: Path,
    path: Path | None,
    *,
    budget_usd: str,
) -> dict[str, str]:
    """Validate an explicit, artifact-bound monetary review without any AWS call.

    This validates the record, not the truth of its cost derivation. A human
    deployment review still has to substantiate the available funds and bounds.
    """
    if path is None:
        raise DeploymentError("Budget review is required before any AWS operation.")
    fields = {
        "schema",
        "approved",
        "available_funds_microusd",
        "other_costs_reserved_microusd",
        "total_microusd",
        "forward_microusd",
        "start_utc",
        "end_utc",
        "agentcore_zip_sha256",
        "proxy_zip_sha256",
        "runtime_profile_sha256",
        "basis",
    }
    try:
        with path.open("rb") as handle:
            raw = handle.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("Review exceeds 16 KiB.")
        review = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_review_fields)
        if not isinstance(review, dict) or set(review) != fields:
            raise ValueError("Review fields do not match the closed schema.")
        if (
            review["schema"] != "folderhome.cloud-budget-review.v1"
            or review["approved"] is not True
        ):
            raise ValueError("Review must be explicitly approved.")
        for key in (
            "available_funds_microusd",
            "other_costs_reserved_microusd",
            "total_microusd",
            "forward_microusd",
        ):
            if type(review[key]) is not int or not 0 <= review[key] <= 1_000_000_000_000:
                raise ValueError("Review amounts must be bounded integer micro-USD.")
        if not isinstance(review["basis"], str) or not review["basis"].strip():
            raise ValueError("Review must identify the cost derivation and evidence.")
        profile_sha256 = hashlib.sha256(
            json.dumps(runtime_cost_profile(), sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        if review["runtime_profile_sha256"] != profile_sha256:
            raise ValueError("Runtime model or lifecycle differs from the reviewed cost profile.")
        for key in ("start_utc", "end_utc"):
            if (
                not isinstance(review[key], str)
                or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", review[key]) is None
            ):
                raise ValueError("Review dates require YYYY-MM-DD UTC.")
        budget = CloudDemoBudget(
            review["total_microusd"],
            review["forward_microusd"],
            date.fromisoformat(review["start_utc"]),
            date.fromisoformat(review["end_utc"]),
        )
        funds = review["available_funds_microusd"]
        alert = Decimal(budget_usd) * 1_000_000
        if not alert.is_finite() or funds != alert:
            raise ValueError("Available allocation and approved budget alert must agree.")
        if budget.total_microusd + review["other_costs_reserved_microusd"] > funds:
            raise ValueError("Invocation allocation plus other-cost reserve exceeds funds.")
        for key, filename in (
            ("agentcore_zip_sha256", "agentcore-direct.zip"),
            ("proxy_zip_sha256", "aws-demo-proxy.zip"),
        ):
            if review[key] != _zip_evidence(repository / "build" / filename)["sha256"]:
                raise ValueError("Build artifact differs from the reviewed cost profile.")
    except (OSError, UnicodeError, ValueError, TypeError, InvalidOperation) as exc:
        raise DeploymentError(
            "Budget review is invalid or does not cover these artifacts."
        ) from exc
    return {
        "FOLDERHOME_BUDGET_TOTAL_MICROUSD": str(budget.total_microusd),
        "FOLDERHOME_BUDGET_FORWARD_MICROUSD": str(budget.forward_microusd),
        "FOLDERHOME_BUDGET_START_UTC": budget.start_utc.isoformat(),
        "FOLDERHOME_BUDGET_END_UTC": budget.end_utc.isoformat(),
        "FOLDERHOME_BUDGET_REVIEW_SHA256": hashlib.sha256(raw).hexdigest(),
    }


def _unique_review_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate budget review field.")
        result[key] = value
    return result


def runtime_cost_profile() -> dict[str, Any]:
    """Canonical deployable model/lifecycle limits, hashed into the cost review."""
    return {
        "networkConfiguration": {"networkMode": "PUBLIC"},
        "protocolConfiguration": {"serverProtocol": "HTTP"},
        "lifecycleConfiguration": {"idleRuntimeSessionTimeout": 60, "maxLifetime": 1800},
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


def preflight(repository: Path) -> dict[str, object]:
    """Verify packages, templates, identity, model access, and name availability."""

    artifacts = {
        "agentcore": repository / "build" / "agentcore-direct.zip",
        "proxy": repository / "build" / "aws-demo-proxy.zip",
    }
    artifact_evidence = {name: _zip_evidence(path) for name, path in artifacts.items()}
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
    budget_review: Path | None = None,
) -> dict[str, object]:
    """Create a fresh runtime and application after the explicit cost gate."""

    budget_environment = load_budget_review(repository, budget_review, budget_usd=budget_usd)
    try:
        CloudDemoBudget.from_environment(budget_environment).accrued_microusd(datetime.now(UTC))
    except ValueError as exc:
        raise DeploymentError("Budget review window is not currently active.") from exc
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", budget_alert_email) is None:
        raise DeploymentError("Budget notification email is invalid.")
    evidence = preflight(repository)
    if evidence["status"] != "ready":
        raise DeploymentError("FolderHome runtime name already exists; refusing replacement.")
    stacks = _aws_json(["cloudformation", "list-stacks"]).get("StackSummaries")
    if not isinstance(stacks, list):
        raise DeploymentError("Existing application history could not be verified.")
    if any(item.get("StackName") == _APPLICATION_STACK for item in stacks):
        raise DeploymentError(
            "Existing application requires a reviewed ledger migration, not a fresh budget."
        )
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
            **{f"FoundationModelArn{index}": arn for index, arn in enumerate(model_arns, start=1)},
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
        **runtime_cost_profile(),
        "agentRuntimeArtifact": artifact,
        "roleArn": runtime_role_arn,
        "description": "FolderHome synthetic accident demo with a Strands master agent",
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
    budget_endpoint = f"budget_v{updated_version}"
    _aws_json(
        [
            "bedrock-agentcore-control",
            "create-agent-runtime-endpoint",
            "--agent-runtime-id",
            runtime_id,
            "--agent-runtime-version",
            updated_version,
            "--name",
            budget_endpoint,
        ]
    )
    _wait_endpoint(runtime_id, budget_endpoint, expected_version=updated_version)
    _cloudformation_deploy(
        stack_name=_APPLICATION_STACK,
        template=repository / "deploy" / "aws_demo" / "application.yaml",
        parameters={
            "AgentRuntimeArn": runtime_arn,
            "AgentRuntimeEndpoint": budget_endpoint,
            "AgentRuntimeVersion": updated_version,
            "BudgetReviewSha256": budget_environment["FOLDERHOME_BUDGET_REVIEW_SHA256"],
            "BudgetTotalMicrousd": budget_environment["FOLDERHOME_BUDGET_TOTAL_MICROUSD"],
            "BudgetForwardMicrousd": budget_environment["FOLDERHOME_BUDGET_FORWARD_MICROUSD"],
            "BudgetStartUtc": budget_environment["FOLDERHOME_BUDGET_START_UTC"],
            "BudgetEndUtc": budget_environment["FOLDERHOME_BUDGET_END_UTC"],
            "ProxyCodeBucket": artifact_bucket,
            "ProxyCodeKey": proxy_key,
            "ProxyCodeVersion": proxy_version,
        },
        capabilities=("CAPABILITY_IAM",),
    )
    application = _stack_outputs(_APPLICATION_STACK)
    settings = CloudDemoProxySettings.from_environment(
        {
            **budget_environment,
            "AWS_REGION": _REGION,
            "FOLDERHOME_AGENT_RUNTIME_ARN": runtime_arn,
            "FOLDERHOME_AGENT_RUNTIME_ENDPOINT": budget_endpoint,
            "FOLDERHOME_AGENT_RUNTIME_VERSION": updated_version,
            "FOLDERHOME_DAILY_QUOTA_LIMIT": "20",
            "FOLDERHOME_DAILY_QUOTA_TABLE": application["DailyQuotaTableName"],
            "FOLDERHOME_PUBLIC_ORIGIN": application["SiteUrl"].removesuffix("/"),
        }
    )
    _initialize_budget_ledger(settings)
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
            "runtime_endpoint": budget_endpoint,
            "runtime_version": updated_version,
            "runtime_artifact": artifact,
            "budget_review_sha256": budget_environment["FOLDERHOME_BUDGET_REVIEW_SHA256"],
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
        "budget_ledger_initialized": True,
        "budget_total_microusd": settings.budget.total_microusd,
        "budget_forward_microusd": settings.budget.forward_microusd,
        "budget_end_utc_exclusive": settings.budget.end_utc.isoformat(),
        "api_key_value_logged": False,
    }


def migrate_demo(
    repository: Path,
    *,
    budget_usd: str,
    budget_review: Path | None = None,
    publish_site: bool = False,
) -> dict[str, object]:
    """Bring the existing demo under the reviewed budget without a second runtime.

    Fail-closed preconditions: both stacks complete, exactly one runtime named
    ``FolderHomeDemo`` and no ``_budget_v1`` ledger item yet. A ledger that already
    holds reserved money needs a migration that carries it; this one refuses.
    The static site is republished (browser agent enabled) only with
    ``publish_site``; otherwise the current ``runtime-config.js`` stays untouched.
    """

    budget_environment = load_budget_review(repository, budget_review, budget_usd=budget_usd)
    try:
        CloudDemoBudget.from_environment(budget_environment).accrued_microusd(datetime.now(UTC))
    except ValueError as exc:
        raise DeploymentError("Budget review window is not currently active.") from exc
    bootstrap = _stack_outputs(_BOOTSTRAP_STACK)
    application = _stack_outputs(_APPLICATION_STACK)
    runtimes = _aws_json(
        ["bedrock-agentcore-control", "list-agent-runtimes", "--max-results", "100"]
    )
    named = [
        item
        for item in runtimes.get("agentRuntimes", [])
        if item.get("agentRuntimeName") == _RUNTIME_NAME
    ]
    if len(named) != 1:
        raise DeploymentError("Migration needs exactly one existing FolderHome runtime.")
    runtime_id = _required_text(named[0], "agentRuntimeId")
    runtime_arn = _required_text(named[0], "agentRuntimeArn")
    existing = _aws_json(
        [
            "dynamodb",
            "get-item",
            "--table-name",
            application["DailyQuotaTableName"],
            "--key",
            json.dumps({"quota_day": {"S": "_budget_v1"}}, separators=(",", ":")),
            "--consistent-read",
        ]
    )
    if existing.get("Item"):
        raise DeploymentError(
            "Existing budget ledger holds reserved money; carry it with a reviewed migration."
        )
    artifact_bucket = bootstrap["ArtifactBucketName"]
    direct_key, direct_version = _upload_versioned(
        artifact_bucket, "agentcore", repository / "build" / "agentcore-direct.zip"
    )
    proxy_key, proxy_version = _upload_versioned(
        artifact_bucket, "proxy", repository / "build" / "aws-demo-proxy.zip"
    )
    artifact = _runtime_artifact(bucket=artifact_bucket, key=direct_key, version_id=direct_version)
    updated = _aws_json(
        [
            "bedrock-agentcore-control",
            "update-agent-runtime",
            "--cli-input-json",
            json.dumps(
                {
                    "agentRuntimeId": runtime_id,
                    **runtime_cost_profile(),
                    "agentRuntimeArtifact": artifact,
                    "roleArn": bootstrap["AgentRuntimeRoleArn"],
                    "description": "FolderHome synthetic accident demo with a Strands master agent",
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
        raise DeploymentError("Runtime readback does not match the migrated version.")
    if runtime.get("metadataConfiguration", {}).get("requireMMDSV2") is not True:
        raise DeploymentError("Runtime became ready without the required IMDSv2 setting.")
    budget_endpoint = f"budget_v{updated_version}"
    _aws_json(
        [
            "bedrock-agentcore-control",
            "create-agent-runtime-endpoint",
            "--agent-runtime-id",
            runtime_id,
            "--agent-runtime-version",
            updated_version,
            "--name",
            budget_endpoint,
        ]
    )
    _wait_endpoint(runtime_id, budget_endpoint, expected_version=updated_version)
    _cloudformation_deploy(
        stack_name=_APPLICATION_STACK,
        template=repository / "deploy" / "aws_demo" / "application.yaml",
        parameters={
            "AgentRuntimeArn": runtime_arn,
            "AgentRuntimeEndpoint": budget_endpoint,
            "AgentRuntimeVersion": updated_version,
            "BudgetReviewSha256": budget_environment["FOLDERHOME_BUDGET_REVIEW_SHA256"],
            "BudgetTotalMicrousd": budget_environment["FOLDERHOME_BUDGET_TOTAL_MICROUSD"],
            "BudgetForwardMicrousd": budget_environment["FOLDERHOME_BUDGET_FORWARD_MICROUSD"],
            "BudgetStartUtc": budget_environment["FOLDERHOME_BUDGET_START_UTC"],
            "BudgetEndUtc": budget_environment["FOLDERHOME_BUDGET_END_UTC"],
            "ProxyCodeBucket": artifact_bucket,
            "ProxyCodeKey": proxy_key,
            "ProxyCodeVersion": proxy_version,
        },
        capabilities=("CAPABILITY_IAM",),
    )
    application = _stack_outputs(_APPLICATION_STACK)
    settings = CloudDemoProxySettings.from_environment(
        {
            **budget_environment,
            "AWS_REGION": _REGION,
            "FOLDERHOME_AGENT_RUNTIME_ARN": runtime_arn,
            "FOLDERHOME_AGENT_RUNTIME_ENDPOINT": budget_endpoint,
            "FOLDERHOME_AGENT_RUNTIME_VERSION": updated_version,
            "FOLDERHOME_DAILY_QUOTA_LIMIT": "20",
            "FOLDERHOME_DAILY_QUOTA_TABLE": application["DailyQuotaTableName"],
            "FOLDERHOME_PUBLIC_ORIGIN": application["SiteUrl"].removesuffix("/"),
        }
    )
    _initialize_budget_ledger(settings)
    invalidation_id = None
    if publish_site:
        api_key = _aws_json(
            ["apigateway", "get-api-key", "--api-key", application["ApiKeyId"], "--include-value"]
        )
        site_build = repository / "build" / "aws-demo-site"
        prepare_site(
            [
                "--api-base-url",
                application["ApiBaseUrl"],
                "--api-key",
                _required_text(api_key, "value"),
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
        invalidation_id = invalidation.get("Invalidation", {}).get("Id")
    _write_state(
        repository,
        {
            "phase": "deployed",
            "runtime_id": runtime_id,
            "runtime_endpoint": budget_endpoint,
            "runtime_version": updated_version,
            "runtime_artifact": artifact,
            "budget_review_sha256": budget_environment["FOLDERHOME_BUDGET_REVIEW_SHA256"],
            "site_url": application["SiteUrl"],
            "api_base_url": application["ApiBaseUrl"],
            "distribution_id": application["CloudFrontDistributionId"],
            "invalidation_id": invalidation_id,
            "site_published": publish_site,
        },
    )
    return {
        "schema": "folderhome.aws-demo-migration.v1",
        "status": "migrated_pending_e2e",
        "region": _REGION,
        "runtime_id": runtime_id,
        "runtime_version": updated_version,
        "runtime_endpoint": budget_endpoint,
        "runtime_status": runtime.get("status"),
        "daily_request_quota": 20,
        "hard_agentcore_forward_limit": 20,
        "budget_limit_usd": budget_usd,
        "budget_ledger_initialized": True,
        "budget_total_microusd": settings.budget.total_microusd,
        "budget_forward_microusd": settings.budget.forward_microusd,
        "budget_end_utc_exclusive": settings.budget.end_utc.isoformat(),
        "site_published": publish_site,
        "api_key_value_logged": False,
    }


def _initialize_budget_ledger(settings: CloudDemoProxySettings) -> None:
    item = initial_budget_item(settings)
    _aws_json(
        [
            "dynamodb",
            "put-item",
            "--table-name",
            settings.daily_quota_table,
            "--item",
            json.dumps(item, separators=(",", ":")),
            "--condition-expression",
            "attribute_not_exists(quota_day)",
        ]
    )
    readback = _aws_json(
        [
            "dynamodb",
            "get-item",
            "--table-name",
            settings.daily_quota_table,
            "--key",
            json.dumps({"quota_day": {"S": "_budget_v1"}}, separators=(",", ":")),
            "--consistent-read",
        ]
    )
    if readback.get("Item") != item:
        raise DeploymentError("Initial budget ledger readback does not match approval.")


def verify_budget_before_invocation(
    application: dict[str, str],
    state: dict[str, Any],
    budget_environment: dict[str, str],
    *,
    proxy_zip_sha256: str,
) -> CloudDemoProxySettings:
    """Read the deployed policy, ledger, endpoint and concurrency before paid probes."""
    configuration = _aws_json(
        [
            "lambda",
            "get-function-configuration",
            "--function-name",
            application["ProxyFunctionName"],
        ]
    )
    try:
        if configuration.get("CodeSha256") != base64.b64encode(
            bytes.fromhex(proxy_zip_sha256)
        ).decode("ascii"):
            raise ValueError("Deployed proxy code differs from the reviewed ZIP.")
        environment = {**configuration["Environment"]["Variables"], "AWS_REGION": _REGION}
        settings = CloudDemoProxySettings.from_environment(environment)
        if any(environment.get(key) != value for key, value in budget_environment.items()):
            raise ValueError("Deployed monetary policy differs from the reviewed artifact.")
        if (
            settings.daily_quota_table != application["DailyQuotaTableName"]
            or settings.public_origin != application["SiteUrl"].removesuffix("/")
            or settings.agent_runtime_arn.rsplit("/", 1)[-1] != state["runtime_id"]
            or settings.runtime_endpoint != state["runtime_endpoint"]
            or settings.runtime_version != state["runtime_version"]
            or settings.budget_review_sha256 != state["budget_review_sha256"]
            or settings.daily_quota_limit != 20
        ):
            raise ValueError("Deployment identity differs from approved budget state.")
        remaining = settings.budget.accrued_microusd(datetime.now(UTC)) - _read_budget_reserved(
            settings
        )
        if remaining < 2 * settings.budget.forward_microusd:
            raise ValueError("Budget cannot reserve the two live verification forwards.")
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentError("Deployed budget policy is unavailable or inconsistent.") from exc
    endpoint = _aws_json(
        [
            "bedrock-agentcore-control",
            "get-agent-runtime-endpoint",
            "--agent-runtime-id",
            state["runtime_id"],
            "--endpoint-name",
            settings.runtime_endpoint,
        ]
    )
    if (
        endpoint.get("status") != "READY"
        or endpoint.get("liveVersion") != settings.runtime_version
        or endpoint.get("targetVersion", settings.runtime_version) != settings.runtime_version
    ):
        raise DeploymentError("Reviewed budget runtime endpoint has drifted.")
    concurrency = _aws_json(
        [
            "lambda",
            "get-function-concurrency",
            "--function-name",
            application["ProxyFunctionName"],
        ]
    )
    if concurrency.get("ReservedConcurrentExecutions") is not None:
        raise DeploymentError("Lambda concurrency differs from the reviewed unreserved template.")
    runtime = _aws_json(
        [
            "bedrock-agentcore-control",
            "get-agent-runtime",
            "--agent-runtime-id",
            state["runtime_id"],
            "--agent-runtime-version",
            settings.runtime_version,
        ]
    )
    if (
        runtime.get("status") != "READY"
        or runtime.get("agentRuntimeVersion") != settings.runtime_version
        or runtime.get("metadataConfiguration", {}).get("requireMMDSV2") is not True
        or not state.get("runtime_artifact")
        or runtime.get("agentRuntimeArtifact") != state["runtime_artifact"]
        or any(runtime.get(key) != value for key, value in runtime_cost_profile().items())
    ):
        raise DeploymentError("Deployed runtime artifact or cost profile differs from approval.")
    return settings


def _read_budget_reserved(settings: CloudDemoProxySettings) -> int:
    item = _aws_json(
        [
            "dynamodb",
            "get-item",
            "--table-name",
            settings.daily_quota_table,
            "--key",
            json.dumps({"quota_day": {"S": "_budget_v1"}}, separators=(",", ":")),
            "--consistent-read",
        ]
    ).get("Item", {})
    try:
        raw = item["reserved_microusd"]["N"]
        if not isinstance(raw, str) or re.fullmatch(r"[0-9]{1,13}", raw) is None:
            raise ValueError("Invalid reservation amount.")
        reserved = int(raw)
        if (
            item.get("policy_sha256") != {"S": budget_policy_sha256(settings)}
            or "expires_at" in item
            or reserved > settings.budget.total_microusd
        ):
            raise ValueError("Ledger differs from approved persistent budget.")
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentError("Persistent monetary ledger is missing or invalid.") from exc
    return reserved


def verify_demo(
    repository: Path,
    *,
    budget_usd: str,
    budget_review: Path | None = None,
) -> dict[str, object]:
    """Exercise one live synthetic journey and verify every operational boundary."""

    budget_environment = load_budget_review(repository, budget_review, budget_usd=budget_usd)
    state = _load_state(repository)
    if state.get("phase") != "deployed":
        raise DeploymentError("Deployment state is not ready for live verification.")
    runtime_id = _required_text(state, "runtime_id")
    bootstrap = _stack_outputs(_BOOTSTRAP_STACK)
    application = _stack_outputs(_APPLICATION_STACK)
    settings = verify_budget_before_invocation(
        application,
        state,
        budget_environment,
        proxy_zip_sha256=_zip_evidence(repository / "build" / "aws-demo-proxy.zip")["sha256"],
    )
    reserved_before = _read_budget_reserved(settings)
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
            "--agent-runtime-version",
            settings.runtime_version,
        ]
    )
    endpoint = _aws_json(
        [
            "bedrock-agentcore-control",
            "get-agent-runtime-endpoint",
            "--agent-runtime-id",
            runtime_id,
            "--endpoint-name",
            settings.runtime_endpoint,
        ]
    )
    if runtime.get("status") != "READY" or endpoint.get("status") != "READY":
        raise DeploymentError("AgentCore runtime or reviewed endpoint is not ready.")
    if (
        endpoint.get("liveVersion") != settings.runtime_version
        or runtime.get("agentRuntimeVersion") != settings.runtime_version
    ):
        raise DeploymentError("Runtime is not serving the reviewed cost-profile version.")
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
    if concurrency.get("ReservedConcurrentExecutions") is not None:
        raise DeploymentError("Lambda concurrency differs from the reviewed unreserved template.")
    reserved_after = _read_budget_reserved(settings)
    if reserved_after < reserved_before + 2 * settings.budget.forward_microusd:
        raise DeploymentError("Live journey lacks its two monetary reservations.")
    proxy_logs = _aws_json(
        [
            "logs",
            "describe-log-groups",
            "--log-group-name-prefix",
            application["ProxyLogGroupName"],
        ]
    ).get("logGroups", [])
    exact_proxy_logs = [
        item for item in proxy_logs if item.get("logGroupName") == application["ProxyLogGroupName"]
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
    if Decimal(str(budget.get("BudgetLimit", {}).get("Amount"))) != Decimal(budget_usd):
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
        "lambda_reserved_concurrency": None,
        "budget_reserved_microusd": reserved_after,
        "budget_total_microusd": settings.budget.total_microusd,
        "budget_review_sha256": settings.budget_review_sha256,
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
            readback = {item.get("logGroupName"): item.get("retentionInDays") for item in verified}
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
            "code": {"s3": {"bucket": bucket, "prefix": key, "versionId": version_id}},
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
    payload = _aws_json(["cloudformation", "describe-stacks", "--stack-name", stack_name])
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
