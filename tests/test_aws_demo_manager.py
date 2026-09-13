import base64
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from deploy.aws_demo import manage
from deploy.aws_demo.manage import (
    DeploymentError,
    _runtime_artifact,
    _zip_evidence,
    require_cost_approval,
    validate_confirmed_response,
    validate_prepared_response,
)
from folderhome.cloud_demo.proxy import CloudDemoProxySettings, initial_budget_item

TEST_RUNTIME_PROFILE = {
    "networkConfiguration": {"networkMode": "PUBLIC"},
    "protocolConfiguration": {"serverProtocol": "HTTP"},
    "lifecycleConfiguration": {"idleRuntimeSessionTimeout": 60, "maxLifetime": 1800},
    "environmentVariables": {
        "FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "bedrock",
        "FOLDERHOME_AGENTCORE_ALLOW_BEDROCK": "1",
        "FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA": "1",
        "FOLDERHOME_AGENTCORE_BEDROCK_MODEL_ID": "eu.amazon.nova-micro-v1:0",
        "FOLDERHOME_AGENTCORE_MAX_OUTPUT_TOKENS": "512",
        "FOLDERHOME_AGENTCORE_MAX_TURNS": "4",
        "FOLDERHOME_AGENTCORE_MAX_TOOL_RESULT_BYTES": "65536",
        "FOLDERHOME_AGENTCORE_BEDROCK_CONNECT_TIMEOUT_SECONDS": "3",
        "FOLDERHOME_AGENTCORE_BEDROCK_READ_TIMEOUT_SECONDS": "18",
    },
}


def test_deployment_requires_exact_reviewed_cost_gate() -> None:
    require_cost_approval("DEPLOY_FOLDERHOME_WITH_5_USD_ALERT", "5")
    require_cost_approval("DEPLOY_FOLDERHOME_WITH_195_USD_ALERT", "195")

    with pytest.raises(DeploymentError, match="blocked"):
        require_cost_approval("yes", "5")
    with pytest.raises(DeploymentError, match="blocked"):
        require_cost_approval("DEPLOY_FOLDERHOME_WITH_5_USD_ALERT", "195")
    with pytest.raises(DeploymentError, match="positive"):
        require_cost_approval("DEPLOY_FOLDERHOME_WITH_0_USD_ALERT", "0")
    with pytest.raises(DeploymentError, match="blocked"):
        require_cost_approval("DEPLOY_FOLDERHOME_WITH_5_USD_ALERT", "5.01")
    with pytest.raises(DeploymentError, match="decimal"):
        require_cost_approval("DEPLOY_FOLDERHOME_WITH_5_USD_ALERT", "five")


def test_runtime_artifact_uses_versioned_python_direct_code() -> None:
    artifact = _runtime_artifact(
        bucket="private-artifacts",
        key="agentcore/runtime.zip",
        version_id="version-1",
    )

    configuration = artifact["codeConfiguration"]
    assert configuration["runtime"] == "PYTHON_3_12"
    assert configuration["entryPoint"] == ["agentcore_entrypoint.py"]
    assert configuration["code"]["s3"] == {
        "bucket": "private-artifacts",
        "prefix": "agentcore/runtime.zip",
        "versionId": "version-1",
    }


def test_zip_evidence_rejects_non_zip(tmp_path: Path) -> None:
    path = tmp_path / "artifact.zip"
    path.write_bytes(b"not a zip")

    with pytest.raises(DeploymentError, match="not a ZIP"):
        _zip_evidence(path)


def test_decimal_import_remains_exact() -> None:
    assert Decimal("5") == Decimal("5.00")


def test_live_e2e_response_contract_requires_bedrock_master_and_fixture_specialists() -> None:
    confirmation = validate_prepared_response(
        {
            "schema": "folderhome.agentcore-response.v1",
            "synthetic_data_only": True,
            "model_provider": "bedrock",
            "specialist_model_provider": "fixture",
            "external_network_used": True,
            "plan": {
                "status": "confirmation_required",
                "confirmation_command": "/confirm accident_demo_1234567890abcdef",
                "steps": [{}, {}, {}, {}],
                "external_actions_performed": [],
            },
        }
    )

    assert confirmation == "/confirm accident_demo_1234567890abcdef"


def test_live_e2e_response_contract_rejects_unproved_cloud_execution() -> None:
    with pytest.raises(DeploymentError, match="master-agent evidence"):
        validate_prepared_response(
            {
                "schema": "folderhome.agentcore-response.v1",
                "synthetic_data_only": True,
                "model_provider": "fixture",
                "specialist_model_provider": "fixture",
                "external_network_used": False,
                "plan": {
                    "status": "confirmation_required",
                    "confirmation_command": "/confirm accident_demo_1234",
                    "steps": [{}, {}, {}, {}],
                    "external_actions_performed": [],
                },
            }
        )


def test_live_e2e_confirmation_proves_four_local_results_and_no_external_effects() -> None:
    generated = validate_confirmed_response(
        {
            "schema": "folderhome.agentcore-response.v1",
            "synthetic_data_only": True,
            "model_provider": "bedrock",
            "specialist_model_provider": "fixture",
            "result": {
                "status": "executed",
                "external_actions_performed": [],
                "mail_sent": False,
                "external_calendar_used": False,
                "phone_call_made": False,
                "generated_results": [{"sha256": str(index) * 64} for index in range(1, 5)],
            },
        }
    )

    assert len(generated) == 4


def _review_file(tmp_path):
    build = tmp_path / "build"
    build.mkdir(exist_ok=True)
    for name in ("agentcore-direct.zip", "aws-demo-proxy.zip"):
        with zipfile.ZipFile(build / name, "w") as archive:
            archive.writestr("synthetic.txt", "Synthetic artifact, not deployable.")
    review = {
        "schema": "folderhome.cloud-budget-review.v1",
        "approved": True,
        "available_funds_microusd": 5000000,
        "other_costs_reserved_microusd": 4000000,
        "total_microusd": 1000000,
        "forward_microusd": 100000,
        "start_utc": "2026-09-01",
        "end_utc": "2026-09-04",
        "agentcore_zip_sha256": hashlib.sha256(
            (build / "agentcore-direct.zip").read_bytes()
        ).hexdigest(),
        "proxy_zip_sha256": hashlib.sha256((build / "aws-demo-proxy.zip").read_bytes()).hexdigest(),
        "basis": "Synthetic test only: reviewed upper bound including model and runtime lifecycle.",
        "runtime_profile_sha256": hashlib.sha256(
            json.dumps(TEST_RUNTIME_PROFILE, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review), encoding="utf-8")
    return path, review


def test_deploy_without_monetary_review_stops_before_aws(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing monetary approval must stop before any AWS call")

    monkeypatch.setattr(manage, "_aws_raw", forbidden)
    monkeypatch.setattr(manage, "preflight", forbidden)
    with pytest.raises(DeploymentError, match="[Bb]udget.*review"):
        manage.deploy_demo(tmp_path, budget_alert_email="test@example.org", budget_usd="5")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approved", False),
        ("forward_microusd", 0),
        ("total_microusd", True),
        ("available_funds_microusd", 900000),
        ("other_costs_reserved_microusd", -1),
        ("other_costs_reserved_microusd", 4900000),
        ("available_funds_microusd", 5000001),
        ("agentcore_zip_sha256", "0" * 64),
        ("proxy_zip_sha256", "0" * 64),
        ("end_utc", "2026-09-01"),
        ("basis", ""),
        ("runtime_profile_sha256", "0" * 64),
    ],
)
def test_monetary_review_rejects_unfunded_unreviewed_or_stale_artifacts(tmp_path, field, value):
    path, review = _review_file(tmp_path)
    review[field] = value
    path.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(DeploymentError):
        manage.load_budget_review(tmp_path, path, budget_usd="5")


def test_review_is_bound_to_exact_artifacts_and_generates_proxy_money_configuration(tmp_path):
    path, _ = _review_file(tmp_path)
    result = manage.load_budget_review(tmp_path, path, budget_usd="5")
    assert result["FOLDERHOME_BUDGET_TOTAL_MICROUSD"] == "1000000"
    assert result["FOLDERHOME_BUDGET_FORWARD_MICROUSD"] == "100000"
    assert result["FOLDERHOME_BUDGET_START_UTC"] == "2026-09-01"
    assert result["FOLDERHOME_BUDGET_END_UTC"] == "2026-09-04"
    assert (
        result["FOLDERHOME_BUDGET_REVIEW_SHA256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_changed_model_profile_invalidates_old_review_even_with_identical_zips(
    tmp_path, monkeypatch
):
    path, _ = _review_file(tmp_path)
    monkeypatch.setattr(manage, "_MODEL_ID", "unreviewed-model")
    with pytest.raises(DeploymentError):
        manage.load_budget_review(tmp_path, path, budget_usd="5")


def test_cost_profile_command_is_offline_and_hashes_the_deployable_profile(monkeypatch, capsys):
    monkeypatch.setattr(manage, "_aws_raw", lambda *a, **k: pytest.fail("Must be offline"))
    assert manage.main(["cost-profile"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["profile"] == TEST_RUNTIME_PROFILE
    assert (
        result["sha256"]
        == hashlib.sha256(
            json.dumps(TEST_RUNTIME_PROFILE, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


def test_cli_deploy_cannot_omit_budget_review_file(monkeypatch):
    monkeypatch.setattr(manage, "deploy_demo", lambda *args, **kwargs: pytest.fail("No review"))
    with pytest.raises(SystemExit) as exc:
        manage.main(
            [
                "deploy",
                "--budget-alert-email",
                "test@example.org",
                "--approval-token",
                "DEPLOY_FOLDERHOME_WITH_5_USD_ALERT",
            ]
        )
    assert exc.value.code == 2


def test_deployment_wires_and_initializes_approved_ledger_before_public_site(tmp_path, monkeypatch):
    path, _ = _review_file(tmp_path)
    saved_item = {}
    parameters = {}
    endpoint_names = []

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    monkeypatch.setattr(manage, "datetime", Clock)
    monkeypatch.setattr(manage, "preflight", lambda _root: {"status": "ready"})
    monkeypatch.setattr(
        manage,
        "_model_profile",
        lambda: {
            "profile_arn": "synthetic-profile",
            "model_arns": ["synthetic"] * 4,
        },
    )
    monkeypatch.setattr(
        manage,
        "_cloudformation_deploy",
        lambda **kw: parameters.update(
            {
                kw["stack_name"]: kw["parameters"],
            }
        ),
    )
    monkeypatch.setattr(
        manage,
        "_stack_outputs",
        lambda name: {
            "ArtifactBucketName": "synthetic-artifacts",
            "AgentRuntimeRoleArn": "synthetic-role",
            "DailyQuotaTableName": "synthetic-budget-table",
            "ApiKeyId": "synthetic-key",
            "ApiBaseUrl": "https://synthetic.invalid/demo",
            "SiteUrl": "https://synthetic.invalid/",
            "SiteBucketName": "synthetic-site",
            "CloudFrontDistributionId": "synthetic-cf",
        },
    )
    monkeypatch.setattr(manage, "_upload_versioned", lambda *args: ("artifact.zip", "v1"))
    monkeypatch.setattr(
        manage,
        "_wait_runtime",
        lambda _id: {
            "status": "READY",
            "agentRuntimeVersion": "4",
            "metadataConfiguration": {"requireMMDSV2": True},
        },
    )

    def endpoint(_id, name, **kwargs):
        endpoint_names.append(name)
        return {"status": "READY", "liveVersion": "4"}

    monkeypatch.setattr(manage, "_wait_endpoint", endpoint)

    def aws_json(args):
        if args[:2] == ["cloudformation", "list-stacks"]:
            return {"StackSummaries": []}
        if args[:2] == ["bedrock-agentcore-control", "create-agent-runtime"]:
            return {
                "agentRuntimeId": "demo",
                "agentRuntimeArn": (
                    "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo"
                ),
            }
        if args[:2] == ["bedrock-agentcore-control", "update-agent-runtime"]:
            return {"agentRuntimeVersion": "4"}
        if args[:2] == ["bedrock-agentcore-control", "create-agent-runtime-endpoint"]:
            assert args[args.index("--agent-runtime-version") + 1] == "4"
            assert args[args.index("--name") + 1] == "budget_v4"
            return {"status": "CREATING"}
        if args[:2] == ["dynamodb", "put-item"]:
            assert (
                args[args.index("--condition-expression") + 1] == "attribute_not_exists(quota_day)"
            )
            saved_item.update(json.loads(args[args.index("--item") + 1]))
            return {}
        if args[:2] == ["dynamodb", "get-item"]:
            assert "--consistent-read" in args
            return {"Item": saved_item}
        if args[:2] == ["apigateway", "get-api-key"]:
            return {"value": "synthetic-test-not-a-credential"}
        if args[:2] == ["cloudfront", "create-invalidation"]:
            return {"Invalidation": {"Id": "synthetic"}}
        pytest.fail(f"Unexpected AWS command: {args[:2]}")

    monkeypatch.setattr(manage, "_aws_json", aws_json)
    monkeypatch.setattr(manage, "_aws_raw", lambda *args, **kwargs: "")

    def prepare(_args):
        assert saved_item["reserved_microusd"] == {"N": "0"}
        assert "expires_at" not in saved_item
        return 0

    monkeypatch.setattr(manage, "prepare_site", prepare)

    result = manage.deploy_demo(
        tmp_path, budget_alert_email="test@example.org", budget_usd="5", budget_review=path
    )
    application = parameters["folderhome-demo-application"]
    assert application["BudgetTotalMicrousd"] == "1000000"
    assert application["BudgetForwardMicrousd"] == "100000"
    assert application["AgentRuntimeEndpoint"] == "budget_v4"
    assert application["AgentRuntimeVersion"] == "4"
    assert "budget_v4" in endpoint_names
    assert result["budget_ledger_initialized"] is True


def test_existing_application_cannot_be_reseeded_as_a_new_budget(tmp_path, monkeypatch):
    path, _ = _review_file(tmp_path)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    monkeypatch.setattr(manage, "datetime", Clock)
    monkeypatch.setattr(manage, "preflight", lambda _root: {"status": "ready"})
    monkeypatch.setattr(
        manage,
        "_aws_json",
        lambda args: {
            "StackSummaries": [
                {"StackName": "folderhome-demo-application", "StackStatus": "CREATE_COMPLETE"},
            ]
        },
    )
    monkeypatch.setattr(manage, "_model_profile", lambda: pytest.fail("Must stop before creation"))
    with pytest.raises(DeploymentError, match="existing|Existing"):
        manage.deploy_demo(
            tmp_path, budget_alert_email="test@example.org", budget_usd="5", budget_review=path
        )


def test_verify_requires_budget_review_before_any_aws_or_billable_probe(tmp_path, monkeypatch):
    monkeypatch.setattr(
        manage, "_load_state", lambda _root: {"phase": "deployed", "runtime_id": "demo"}
    )
    monkeypatch.setattr(
        manage, "_stack_outputs", lambda _name: pytest.fail("Review must precede AWS")
    )
    with pytest.raises(DeploymentError, match="[Bb]udget.*review"):
        manage.verify_demo(tmp_path, budget_usd="5")


@pytest.mark.parametrize(
    "failure",
    [
        "none",
        "no_ledger",
        "wrong_policy",
        "insufficient",
        "runtime_drift",
        "reserved_concurrency",
        "money_drift",
        "proxy_code_drift",
        "runtime_profile_drift",
        "runtime_artifact_drift",
    ],
)
def test_budget_preverification_checks_live_guards_without_spending(tmp_path, monkeypatch, failure):
    path, review = _review_file(tmp_path)
    budget_env = manage.load_budget_review(tmp_path, path, budget_usd="5")

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    monkeypatch.setattr(manage, "datetime", Clock)
    values = {
        **budget_env,
        "AWS_REGION": "eu-central-1",
        "FOLDERHOME_AGENT_RUNTIME_ARN": (
            "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo"
        ),
        "FOLDERHOME_AGENT_RUNTIME_ENDPOINT": "budget_v4",
        "FOLDERHOME_AGENT_RUNTIME_VERSION": "4",
        "FOLDERHOME_DAILY_QUOTA_TABLE": "synthetic-budget-table",
        "FOLDERHOME_PUBLIC_ORIGIN": "https://synthetic.invalid",
    }
    settings = CloudDemoProxySettings.from_environment(values)
    item = initial_budget_item(settings)
    if failure == "no_ledger":
        item = {}
    elif failure == "wrong_policy":
        item["policy_sha256"] = {"S": "0" * 64}
    elif failure == "insufficient":
        item["reserved_microusd"] = {"N": "200000"}
    elif failure == "money_drift":
        values["FOLDERHOME_BUDGET_FORWARD_MICROUSD"] = "1"
    calls = []

    def aws_json(args):
        calls.append(args[:2])
        if args[:2] == ["lambda", "get-function-configuration"]:
            return {
                "Environment": {"Variables": values},
                "CodeSha256": (
                    "UNREVIEWED_CODE"
                    if failure == "proxy_code_drift"
                    else base64.b64encode(bytes.fromhex(review["proxy_zip_sha256"])).decode()
                ),
            }
        if args[:2] == ["lambda", "get-function-concurrency"]:
            return {"ReservedConcurrentExecutions": 2} if failure == "reserved_concurrency" else {}
        if args[:2] == ["dynamodb", "get-item"]:
            return {"Item": item}
        if args[:2] == ["bedrock-agentcore-control", "get-agent-runtime-endpoint"]:
            return {"status": "READY", "liveVersion": "5" if failure == "runtime_drift" else "4"}
        if args[:2] == ["bedrock-agentcore-control", "get-agent-runtime"]:
            assert args[args.index("--agent-runtime-version") + 1] == "4"
            return {
                **TEST_RUNTIME_PROFILE,
                "status": "READY",
                "agentRuntimeVersion": "4",
                "metadataConfiguration": {"requireMMDSV2": True},
                "agentRuntimeArtifact": {
                    "synthetic_versioned_artifact": (
                        "unreviewed" if failure == "runtime_artifact_drift" else "v1"
                    )
                },
                "environmentVariables": {}
                if failure == "runtime_profile_drift"
                else TEST_RUNTIME_PROFILE["environmentVariables"],
            }
        pytest.fail(f"Unexpected/billable AWS command: {args[:2]}")

    monkeypatch.setattr(manage, "_aws_json", aws_json)
    application = {
        "ProxyFunctionName": "synthetic-proxy",
        "DailyQuotaTableName": "synthetic-budget-table",
        "SiteUrl": "https://synthetic.invalid/",
    }
    state = {
        "runtime_id": "demo",
        "runtime_endpoint": "budget_v4",
        "runtime_version": "4",
        "budget_review_sha256": budget_env["FOLDERHOME_BUDGET_REVIEW_SHA256"],
        "runtime_artifact": {"synthetic_versioned_artifact": "v1"},
    }
    if failure == "none":
        result = manage.verify_budget_before_invocation(
            application, state, budget_env, proxy_zip_sha256=review["proxy_zip_sha256"]
        )
        assert result == settings
        assert ["lambda", "get-function-concurrency"] in calls
    else:
        with pytest.raises(DeploymentError):
            manage.verify_budget_before_invocation(
                application, state, budget_env, proxy_zip_sha256=review["proxy_zip_sha256"]
            )


def _migration_stack_outputs(_name):
    return {
        "ArtifactBucketName": "synthetic-artifacts",
        "AgentRuntimeRoleArn": "synthetic-role",
        "DailyQuotaTableName": "synthetic-budget-table",
        "ApiKeyId": "synthetic-key",
        "ApiBaseUrl": "https://synthetic.invalid/demo",
        "SiteUrl": "https://synthetic.invalid/",
        "SiteBucketName": "synthetic-site",
        "CloudFrontDistributionId": "synthetic-cf",
    }


_EXISTING_RUNTIME = {
    "agentRuntimes": [
        {
            "agentRuntimeName": "FolderHomeDemo",
            "agentRuntimeId": "demo",
            "agentRuntimeArn": "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo",
        }
    ]
}


def test_migration_refuses_when_ledger_already_holds_money(tmp_path, monkeypatch):
    path, _ = _review_file(tmp_path)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    monkeypatch.setattr(manage, "datetime", Clock)
    monkeypatch.setattr(manage, "_stack_outputs", _migration_stack_outputs)

    def aws_json(args):
        if args[:2] == ["bedrock-agentcore-control", "list-agent-runtimes"]:
            return _EXISTING_RUNTIME
        if args[:2] == ["dynamodb", "get-item"]:
            return {"Item": {"quota_day": {"S": "_budget_v1"}, "reserved_microusd": {"N": "12"}}}
        pytest.fail(f"Unexpected AWS command before refusal: {args[:2]}")

    monkeypatch.setattr(manage, "_aws_json", aws_json)
    monkeypatch.setattr(manage, "_upload_versioned", lambda *a: pytest.fail("Must not mutate"))
    monkeypatch.setattr(manage, "_aws_raw", lambda *a, **k: pytest.fail("Must not mutate"))

    with pytest.raises(manage.DeploymentError, match="reserved money"):
        manage.migrate_demo(tmp_path, budget_usd="5", budget_review=path)


def test_migration_updates_existing_runtime_and_wires_budget_without_publishing(
    tmp_path, monkeypatch
):
    path, _ = _review_file(tmp_path)
    saved_item = {}
    parameters = {}
    endpoint_names = []
    raw_calls = []

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    monkeypatch.setattr(manage, "datetime", Clock)
    monkeypatch.setattr(manage, "_stack_outputs", _migration_stack_outputs)
    monkeypatch.setattr(
        manage,
        "_cloudformation_deploy",
        lambda **kw: parameters.update({kw["stack_name"]: kw["parameters"]}),
    )
    monkeypatch.setattr(manage, "_upload_versioned", lambda *args: ("artifact.zip", "v2"))
    monkeypatch.setattr(
        manage,
        "_wait_runtime",
        lambda _id: {
            "status": "READY",
            "agentRuntimeVersion": "5",
            "metadataConfiguration": {"requireMMDSV2": True},
        },
    )

    def endpoint(_id, name, **kwargs):
        endpoint_names.append(name)
        return {"status": "READY", "liveVersion": "5"}

    monkeypatch.setattr(manage, "_wait_endpoint", endpoint)
    monkeypatch.setattr(
        manage, "_stack_parameters", lambda name: {"AgentRuntimeEndpoint": "budget_v4"}
    )
    deleted = []

    def aws_json(args):
        if args[:2] == ["bedrock-agentcore-control", "list-agent-runtimes"]:
            return _EXISTING_RUNTIME
        if args[:2] == ["bedrock-agentcore-control", "list-agent-runtime-endpoints"]:
            return {
                "runtimeEndpoints": [
                    {"name": "DEFAULT"},
                    {"name": "budget_v3"},
                    {"name": "budget_v4"},
                ]
            }
        if args[:2] == ["bedrock-agentcore-control", "delete-agent-runtime-endpoint"]:
            deleted.append(args[args.index("--endpoint-name") + 1])
            return {}
        if args[:2] == ["bedrock-agentcore-control", "create-agent-runtime"]:
            pytest.fail("Migration must never create a second runtime")
        if args[:2] == ["bedrock-agentcore-control", "update-agent-runtime"]:
            payload = json.loads(args[args.index("--cli-input-json") + 1])
            assert payload["agentRuntimeId"] == "demo"
            assert payload["metadataConfiguration"] == {"requireMMDSV2": True}
            return {"agentRuntimeVersion": "5"}
        if args[:2] == ["bedrock-agentcore-control", "create-agent-runtime-endpoint"]:
            assert args[args.index("--agent-runtime-version") + 1] == "5"
            assert args[args.index("--name") + 1] == "budget_v5"
            return {"status": "CREATING"}
        if args[:2] == ["dynamodb", "put-item"]:
            assert (
                args[args.index("--condition-expression") + 1] == "attribute_not_exists(quota_day)"
            )
            saved_item.update(json.loads(args[args.index("--item") + 1]))
            return {}
        if args[:2] == ["dynamodb", "get-item"]:
            assert "--consistent-read" in args
            return {"Item": saved_item} if saved_item else {}
        if args[:2] == ["apigateway", "get-api-key"]:
            pytest.fail("Site must not be published without --publish-site")
        pytest.fail(f"Unexpected AWS command: {args[:2]}")

    monkeypatch.setattr(manage, "_aws_json", aws_json)
    monkeypatch.setattr(manage, "_aws_raw", lambda *args, **kwargs: raw_calls.append(args) or "")
    monkeypatch.setattr(manage, "prepare_site", lambda _args: pytest.fail("No site publish"))

    result = manage.migrate_demo(tmp_path, budget_usd="5", budget_review=path)

    application = parameters["folderhome-demo-application"]
    assert application["BudgetTotalMicrousd"] == "1000000"
    assert application["BudgetForwardMicrousd"] == "100000"
    assert application["AgentRuntimeEndpoint"] == "budget_v5"
    assert application["AgentRuntimeVersion"] == "5"
    assert application["ProxyCodeVersion"] == "v2"
    assert endpoint_names == ["budget_v5"]
    assert deleted == ["budget_v3"]
    assert result["pruned_endpoints"] == ["budget_v3"]
    assert saved_item["reserved_microusd"] == {"N": "0"}
    assert raw_calls == []
    assert result["budget_ledger_initialized"] is True
    assert result["site_published"] is False
    assert result["runtime_version"] == "5"
    state = json.loads((tmp_path / "build" / "aws-demo-deployment-state.json").read_text())
    assert state["phase"] == "deployed"
    assert state["runtime_endpoint"] == "budget_v5"
    assert state["site_published"] is False


def test_aws_json_treats_empty_cli_output_as_missing_item(monkeypatch):
    # Live behaviour 2026-09-13: `aws dynamodb get-item` for an absent key exits 0 with 0 bytes.
    monkeypatch.setattr(manage, "_aws_raw", lambda *args, **kwargs: "")
    assert manage._aws_json(["dynamodb", "get-item"]) == {}
    monkeypatch.setattr(manage, "_aws_raw", lambda *args, **kwargs: "not json")
    with pytest.raises(manage.DeploymentError):
        manage._aws_json(["dynamodb", "get-item"])


def test_migration_carries_existing_reservation_only_with_flag(tmp_path, monkeypatch):
    path, _ = _review_file(tmp_path)
    previous = "a" * 64
    ledger = {
        "quota_day": {"S": "_budget_v1"},
        "policy_sha256": {"S": previous},
        "reserved_microusd": {"N": "10000"},
    }
    saved = {}

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, tzinfo=UTC)

    monkeypatch.setattr(manage, "datetime", Clock)
    monkeypatch.setattr(manage, "_stack_outputs", _migration_stack_outputs)
    monkeypatch.setattr(manage, "_cloudformation_deploy", lambda **kw: None)
    monkeypatch.setattr(manage, "_upload_versioned", lambda *args: ("artifact.zip", "v3"))
    monkeypatch.setattr(
        manage,
        "_wait_runtime",
        lambda _id: {
            "status": "READY",
            "agentRuntimeVersion": "6",
            "metadataConfiguration": {"requireMMDSV2": True},
        },
    )
    monkeypatch.setattr(
        manage, "_wait_endpoint", lambda _id, name, **kw: {"status": "READY", "liveVersion": "6"}
    )
    monkeypatch.setattr(
        manage, "_stack_parameters", lambda name: {"AgentRuntimeEndpoint": "budget_v5"}
    )

    def aws_json(args):
        if args[:2] == ["bedrock-agentcore-control", "list-agent-runtimes"]:
            return _EXISTING_RUNTIME
        if args[:2] == ["bedrock-agentcore-control", "list-agent-runtime-endpoints"]:
            return {"runtimeEndpoints": [{"name": "DEFAULT"}, {"name": "budget_v5"}]}
        if args[:2] == ["bedrock-agentcore-control", "delete-agent-runtime-endpoint"]:
            pytest.fail("The wired endpoint must never be deleted")
        if args[:2] == ["bedrock-agentcore-control", "update-agent-runtime"]:
            return {"agentRuntimeVersion": "6"}
        if args[:2] == ["bedrock-agentcore-control", "create-agent-runtime-endpoint"]:
            return {"status": "CREATING"}
        if args[:2] == ["dynamodb", "put-item"]:
            condition = args[args.index("--condition-expression") + 1]
            assert condition == "policy_sha256 = :previous AND reserved_microusd = :reserved"
            values = json.loads(args[args.index("--expression-attribute-values") + 1])
            assert values == {":previous": {"S": previous}, ":reserved": {"N": "10000"}}
            saved.update(json.loads(args[args.index("--item") + 1]))
            return {}
        if args[:2] == ["dynamodb", "get-item"]:
            return {"Item": saved or ledger}
        pytest.fail(f"Unexpected AWS command: {args[:2]}")

    monkeypatch.setattr(manage, "_aws_json", aws_json)
    monkeypatch.setattr(manage, "_aws_raw", lambda *a, **k: pytest.fail("No raw calls"))

    with pytest.raises(manage.DeploymentError, match="carry-ledger"):
        manage.migrate_demo(tmp_path, budget_usd="5", budget_review=path)

    result = manage.migrate_demo(tmp_path, budget_usd="5", budget_review=path, carry_ledger=True)

    assert saved["reserved_microusd"] == {"N": "10000"}
    assert saved["policy_sha256"] != {"S": previous}
    assert result["budget_ledger_carried_microusd"] == 10000
    assert result["runtime_endpoint"] == "budget_v6"
