import pytest

from folderhome.agentcore_server import agent_settings_from_environment


def test_agentcore_environment_defaults_to_fixture() -> None:
    settings = agent_settings_from_environment({})

    assert settings.model_provider == "fixture"
    assert settings.allow_network is False
    assert settings.allow_sensitive_cloud_data is False


def test_agentcore_environment_enables_bedrock_only_with_both_explicit_gates() -> None:
    settings = agent_settings_from_environment(
        {
            "FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "bedrock",
            "FOLDERHOME_AGENTCORE_ALLOW_BEDROCK": "1",
            "FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA": "1",
            "FOLDERHOME_AGENTCORE_BEDROCK_MODEL_ID": "eu.amazon.nova-micro-v1:0",
            "AWS_REGION": "eu-central-1",
            "FOLDERHOME_AGENTCORE_MAX_OUTPUT_TOKENS": "1024",
            "FOLDERHOME_AGENTCORE_MAX_TURNS": "2",
            "FOLDERHOME_AGENTCORE_MAX_TOOL_RESULT_BYTES": "65536",
        }
    )

    assert settings.model_provider == "bedrock"
    assert settings.bedrock_model_id == "eu.amazon.nova-micro-v1:0"
    assert settings.aws_region == "eu-central-1"
    assert settings.allow_network is True
    assert settings.allow_sensitive_cloud_data is True
    assert settings.max_output_tokens == 1_024
    assert settings.max_turns == 2
    assert settings.max_tool_result_bytes == 65_536


@pytest.mark.parametrize(
    "environment",
    [
        {"FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "unknown"},
        {
            "FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "bedrock",
            "FOLDERHOME_AGENTCORE_ALLOW_BEDROCK": "1",
            "FOLDERHOME_AGENTCORE_BEDROCK_MODEL_ID": "eu.amazon.nova-micro-v1:0",
            "AWS_REGION": "eu-central-1",
        },
        {
            "FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "bedrock",
            "FOLDERHOME_AGENTCORE_ALLOW_BEDROCK": "1",
            "FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA": "1",
            "FOLDERHOME_AGENTCORE_BEDROCK_MODEL_ID": "eu.amazon.nova-micro-v1:0",
            "AWS_REGION": "eu-central-1",
            "FOLDERHOME_AGENTCORE_MAX_OUTPUT_TOKENS": "unbounded",
        },
        {
            "FOLDERHOME_AGENTCORE_MODEL_PROVIDER": "bedrock",
            "FOLDERHOME_AGENTCORE_ALLOW_BEDROCK": "1",
            "FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA": "1",
            "FOLDERHOME_AGENTCORE_BEDROCK_MODEL_ID": "eu.amazon.nova-micro-v1:0",
            "AWS_REGION": "eu-central-1",
            "FOLDERHOME_AGENTCORE_MAX_TURNS": "many",
        },
    ],
)
def test_agentcore_environment_fails_closed_for_ambiguous_bedrock_configuration(
    environment: dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        agent_settings_from_environment(environment)
