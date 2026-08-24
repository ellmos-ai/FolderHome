from decimal import Decimal
from pathlib import Path

import pytest

from deploy.aws_demo.manage import (
    DeploymentError,
    _runtime_artifact,
    _zip_evidence,
    require_cost_approval,
    validate_confirmed_response,
    validate_prepared_response,
)


def test_deployment_requires_exact_reviewed_cost_gate() -> None:
    require_cost_approval("DEPLOY_FOLDERHOME_WITH_5_USD_ALERT", "5")

    with pytest.raises(DeploymentError, match="blocked"):
        require_cost_approval("yes", "5")
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
                "generated_results": [
                    {"sha256": str(index) * 64} for index in range(1, 5)
                ],
            },
        }
    )

    assert len(generated) == 4
