from __future__ import annotations

from pathlib import Path

import pytest
import strands.models

import folderhome.application.strands_agent as strands_module
from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.strands_agent import (
    FolderHomeAgentError,
    StrandsAgentSettings,
    consult_folderhome_specialist,
    run_folderhome_agent,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.contracts import (
    LocalAppSettings,
    LogicalResource,
    ResourceRegistry,
)

PROFILE_DIR = Path(__file__).parents[1] / "examples" / "profiles"


class StubSearcher:
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        return (
            KnowledgeDigestSearchHit(
                source="document",
                filename="Krankenversicherung.txt",
                file_type="txt",
                snippet=f"Fundstelle für >>>{query}<<<",
                relevance=-1.0,
                word_count=42,
            ),
        )[:limit]


def _app(tmp_path: Path) -> LocalApplication:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return LocalApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=state_dir,
            max_query_limit=10,
        ),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="phase36-strands-test-token-with-sufficient-entropy",
    )


def _resource_app(tmp_path: Path) -> LocalApplication:
    application = _app(tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    application.resource_registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="insurance_documents",
                kind="directory",
                local_path=documents,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"insurance.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
        ),
        profile_defaults={"lukas": {"insurance.source": "insurance_documents"}},
        known_profile_ids=frozenset({"hanna", "lukas", "simon"}),
    )
    return application


def test_fixture_agent_uses_real_strands_loop_and_dossier_tool(tmp_path: Path) -> None:
    report = run_folderhome_agent(
        application=_app(tmp_path),
        prompt="Gib mir alles, was in meinen Dokumenten zur Krankenversicherung steht.",
        profile_id="lukas",
        settings=StrandsAgentSettings(model_provider="fixture"),
    )

    assert report.framework == "strands-agents"
    assert report.framework_version == "1.53.0"
    assert report.model_provider == "fixture"
    assert report.stop_reason == "end_turn"
    assert [item.tool_name for item in report.tool_events] == [
        "build_home_theme_dossier"
    ]
    assert "Krankenversicherung.txt" in report.response_text
    assert report.network_used is False
    assert report.sensitive_cloud_data_authorized is False
    assert report.side_effects == ()
    assert report.profiles_are_authorization_boundaries is False


def test_fixture_master_capability_answer_uses_runtime_executor_catalog(
    tmp_path: Path,
) -> None:
    application = _app(tmp_path)
    report = run_folderhome_agent(
        application=application,
        prompt="What can you do?",
        profile_id="lukas",
        settings=StrandsAgentSettings(model_provider="fixture"),
    )

    assert [item.tool_name for item in report.tool_events] == ["list_home_capabilities"]
    assert "8 bounded expert roles" in report.response_text
    assert "29 runtime adapter gaps" in report.response_text

    german = run_folderhome_agent(
        application=application,
        prompt="Was kannst du?",
        profile_id="lukas",
        settings=StrandsAgentSettings(model_provider="fixture"),
    )
    assert "8 begrenzte Fachrollen" in german.response_text
    assert "29 sichtbare Adapterlücken" in german.response_text


def test_fixture_agent_can_list_profile_resources_without_receiving_paths(
    tmp_path: Path,
) -> None:
    application = _resource_app(tmp_path)
    report = run_folderhome_agent(
        application=application,
        prompt="Which logical resources are configured for me?",
        profile_id="lukas",
        settings=StrandsAgentSettings(model_provider="fixture"),
    )

    assert [item.tool_name for item in report.tool_events] == ["list_home_resources"]
    assert "insurance_documents" in report.response_text
    assert str(tmp_path) not in report.response_text
    assert "documents" not in report.response_text.replace(
        "insurance_documents", ""
    )


def test_fixture_agent_selects_natural_document_search_without_path_access(
    tmp_path: Path,
) -> None:
    report = run_folderhome_agent(
        application=_app(tmp_path),
        prompt=(
            "Ich suche nach einem Dokument, in dem ich Informationen über meine "
            "Krankenversicherung abgelegt habe."
        ),
        profile_id="hanna",
        settings=StrandsAgentSettings(model_provider="fixture"),
    )

    assert [item.tool_name for item in report.tool_events] == ["search_home_documents"]
    assert report.tool_events[0].status == "executed"
    assert report.tool_events[0].side_effects == ()
    assert report.organizational_profile_id == "hanna"
    assert "source_path" not in report.response_text


def test_scoped_specialist_can_only_propose_its_verified_workflow(tmp_path: Path) -> None:
    app = _app(tmp_path)
    payload, plan, delegation = consult_folderhome_specialist(
        application=app,
        request="Prepare a safe cleanup plan for my inbox.",
        profile_id="lukas",
        expert_id="document_expert",
        workflow_id="folder-cleanup",
        persona_id="methodical_operator",
        language="en",
        settings=StrandsAgentSettings(model_provider="fixture"),
    )

    assert payload["status"] == "planned"
    assert payload["execution_performed"] is False
    assert payload["side_effects"] == []
    assert [item.workflow_id for item in plan.steps] == ["folder-cleanup"]
    assert plan.confirmation_required is True
    assert delegation.expert_id == "document_expert"
    assert delegation.workflow_id == "folder-cleanup"
    assert delegation.side_effects == ()

    with pytest.raises(FolderHomeAgentError, match="gehört nicht"):
        consult_folderhome_specialist(
            application=app,
            request="Clean up my inbox.",
            profile_id="lukas",
            expert_id="health_expert",
            workflow_id="folder-cleanup",
            persona_id="careful_reviewer",
            language="en",
            settings=StrandsAgentSettings(model_provider="fixture"),
        )


def test_agent_gates_unknown_profiles_prompt_budget_and_bedrock_network(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    with pytest.raises(FolderHomeAgentError, match="Profil"):
        run_folderhome_agent(
            application=app,
            prompt="Suche meine Versicherung.",
            profile_id="admin",
            settings=StrandsAgentSettings(model_provider="fixture"),
        )
    with pytest.raises(FolderHomeAgentError, match="Prompt"):
        run_folderhome_agent(
            application=app,
            prompt="x" * 1001,
            profile_id="lukas",
            settings=StrandsAgentSettings(model_provider="fixture"),
        )
    with pytest.raises(ValueError, match="Netzwerkfreigabe"):
        StrandsAgentSettings(
            model_provider="bedrock",
            bedrock_model_id="eu.anthropic.claude-sonnet-4-20250514-v1:0",
            aws_region="eu-central-1",
            allow_network=False,
        )
    with pytest.raises(ValueError, match="max_conversation_messages"):
        StrandsAgentSettings(max_conversation_messages=3)


def test_bedrock_requires_separate_sensitive_cloud_data_approval() -> None:
    common = {
        "model_provider": "bedrock",
        "bedrock_model_id": "eu.anthropic.claude-sonnet-4-20250514-v1:0",
        "aws_region": "eu-central-1",
        "allow_network": True,
    }

    with pytest.raises(ValueError, match="Datenweitergabefreigabe"):
        StrandsAgentSettings(**common)

    settings = StrandsAgentSettings(
        **common,
        allow_sensitive_cloud_data=True,
    )
    assert settings.allow_sensitive_cloud_data is True

    with pytest.raises(ValueError, match="Fixture-Modus"):
        StrandsAgentSettings(
            model_provider="fixture",
            allow_sensitive_cloud_data=True,
        )


def test_agent_settings_keep_turns_tools_and_output_finite() -> None:
    with pytest.raises(ValueError, match="max_turns"):
        StrandsAgentSettings(model_provider="fixture", max_turns=0)
    with pytest.raises(ValueError, match="max_tool_calls"):
        StrandsAgentSettings(model_provider="fixture", max_tool_calls=9)
    with pytest.raises(ValueError, match="max_response_chars"):
        StrandsAgentSettings(model_provider="fixture", max_response_chars=0)


def test_bedrock_model_uses_explicit_timeouts_and_one_sdk_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeBedrockModel:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(strands.models, "BedrockModel", FakeBedrockModel)
    settings = StrandsAgentSettings(
        model_provider="bedrock",
        bedrock_model_id="eu.amazon.nova-micro-v1:0",
        aws_region="eu-central-1",
        allow_network=True,
        allow_sensitive_cloud_data=True,
        bedrock_connect_timeout_seconds=4,
        bedrock_read_timeout_seconds=20,
    )

    strands_module._build_model(settings)

    config = captured["boto_client_config"]
    assert config.connect_timeout == 4
    assert config.read_timeout == 20
    assert config.retries["total_max_attempts"] == 1
    assert captured["max_tokens"] == settings.max_output_tokens


def test_loopback_ollama_needs_no_network_or_cloud_data_gate() -> None:
    settings = StrandsAgentSettings(
        model_provider="ollama",
        ollama_host="http://127.0.0.1:11434",
        ollama_model_id="qwen3.8:27b-mlx",
    )

    assert settings.network_used is False
    assert settings.is_live_model is True
    assert settings.allow_network is False
    assert settings.allow_sensitive_cloud_data is False
    payload = settings.to_dict()
    assert payload["schema"] == "folderhome.strands-agent-settings.v1"
    assert payload["ollama_host"] == "http://127.0.0.1:11434"
    assert payload["ollama_model_id"] == "qwen3.8:27b-mlx"
    assert payload["network_used"] is False


def test_ollama_outside_loopback_requires_both_explicit_gates() -> None:
    common = {
        "model_provider": "ollama",
        "ollama_host": "http://100.119.69.90:11434",
        "ollama_model_id": "qwen3.8:27b-mlx",
    }

    with pytest.raises(ValueError, match="Netzwerkfreigabe"):
        StrandsAgentSettings(**common)
    with pytest.raises(ValueError, match="Datenweitergabefreigabe"):
        StrandsAgentSettings(**common, allow_network=True)

    settings = StrandsAgentSettings(
        **common,
        allow_network=True,
        allow_sensitive_cloud_data=True,
    )
    assert settings.network_used is True
    assert settings.to_dict()["network_used"] is True


def test_ollama_settings_reject_missing_model_id_and_foreign_provider_fields() -> None:
    with pytest.raises(ValueError, match="Modell-ID"):
        StrandsAgentSettings(
            model_provider="ollama",
            ollama_host="http://127.0.0.1:11434",
        )
    with pytest.raises(ValueError, match="Host"):
        StrandsAgentSettings(
            model_provider="ollama",
            ollama_host="127.0.0.1:11434",
            ollama_model_id="qwen3.8:27b-mlx",
        )
    with pytest.raises(ValueError, match="Ollama-Modus"):
        StrandsAgentSettings(
            model_provider="ollama",
            ollama_host="http://127.0.0.1:11434",
            ollama_model_id="qwen3.8:27b-mlx",
            aws_region="eu-central-1",
        )
    with pytest.raises(ValueError, match="Fixture-Modus"):
        StrandsAgentSettings(
            model_provider="fixture",
            ollama_host="http://127.0.0.1:11434",
        )
    with pytest.raises(ValueError, match="Bedrock-Modus"):
        StrandsAgentSettings(
            model_provider="bedrock",
            bedrock_model_id="eu.amazon.nova-micro-v1:0",
            aws_region="eu-central-1",
            allow_network=True,
            allow_sensitive_cloud_data=True,
            ollama_model_id="qwen3.8:27b-mlx",
        )


def test_network_used_and_is_live_model_separate_provider_from_transport() -> None:
    fixture = StrandsAgentSettings(model_provider="fixture")
    bedrock = StrandsAgentSettings(
        model_provider="bedrock",
        bedrock_model_id="eu.amazon.nova-micro-v1:0",
        aws_region="eu-central-1",
        allow_network=True,
        allow_sensitive_cloud_data=True,
    )

    assert (fixture.network_used, fixture.is_live_model) == (False, False)
    assert (bedrock.network_used, bedrock.is_live_model) == (True, True)


def test_ollama_model_receives_host_model_id_and_output_budget() -> None:
    ollama_models = pytest.importorskip("strands.models.ollama")
    settings = StrandsAgentSettings(
        model_provider="ollama",
        ollama_host="http://127.0.0.1:11434",
        ollama_model_id="qwen3.8:27b-mlx",
        max_output_tokens=2_048,
    )

    model = strands_module._build_model(settings)

    assert isinstance(model, ollama_models.OllamaModel)
    assert model.host == "http://127.0.0.1:11434"
    assert model.get_config()["model_id"] == "qwen3.8:27b-mlx"
    assert model.get_config()["max_tokens"] == 2_048


def test_hosted_api_providers_need_both_gates_and_never_hold_the_key() -> None:
    for provider, fields in (
        ("anthropic", {"anthropic_model_id": "claude-sonnet-4-5-20250929"}),
        ("openai", {"openai_model_id": "gpt-4o"}),
    ):
        common = {"model_provider": provider, **fields}
        with pytest.raises(ValueError, match="Netzwerkfreigabe"):
            StrandsAgentSettings(**common)
        with pytest.raises(ValueError, match="Datenweitergabefreigabe"):
            StrandsAgentSettings(**common, allow_network=True)

        settings = StrandsAgentSettings(
            **common,
            allow_network=True,
            allow_sensitive_cloud_data=True,
        )
        assert (settings.network_used, settings.is_live_model) == (True, True)
        payload = settings.to_dict()
        assert payload["model_provider"] == provider
        # An API key is not a setting; nothing here may carry one.
        assert not any("key" in str(name).casefold() for name in payload)


def test_hosted_api_providers_reject_missing_and_foreign_fields() -> None:
    gates = {"allow_network": True, "allow_sensitive_cloud_data": True}
    with pytest.raises(ValueError, match="Modell-ID"):
        StrandsAgentSettings(model_provider="anthropic", **gates)
    with pytest.raises(ValueError, match="Modell-ID"):
        StrandsAgentSettings(model_provider="openai", **gates)
    with pytest.raises(ValueError, match="Anthropic-Modus"):
        StrandsAgentSettings(
            model_provider="anthropic",
            anthropic_model_id="claude-sonnet-4-5-20250929",
            aws_region="eu-central-1",
            **gates,
        )
    with pytest.raises(ValueError, match="OpenAI-Modus"):
        StrandsAgentSettings(
            model_provider="openai",
            openai_model_id="gpt-4o",
            ollama_model_id="qwen3.8:27b-mlx",
            **gates,
        )
    with pytest.raises(ValueError, match="Basis-URL"):
        StrandsAgentSettings(
            model_provider="openai",
            openai_model_id="gpt-4o",
            openai_base_url="gateway.example/v1",
            **gates,
        )
    with pytest.raises(ValueError, match="Fixture-Modus"):
        StrandsAgentSettings(model_provider="fixture", openai_model_id="gpt-4o")


def test_hosted_api_providers_name_the_missing_key_without_printing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("strands.models.anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = StrandsAgentSettings(
        model_provider="anthropic",
        anthropic_model_id="claude-sonnet-4-5-20250929",
        allow_network=True,
        allow_sensitive_cloud_data=True,
    )

    with pytest.raises(strands_module.FolderHomeAgentError, match="ANTHROPIC_API_KEY"):
        strands_module._build_model(settings)


def test_anthropic_model_receives_key_model_id_and_output_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anthropic_models = pytest.importorskip("strands.models.anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-secret")
    settings = StrandsAgentSettings(
        model_provider="anthropic",
        anthropic_model_id="claude-sonnet-4-5-20250929",
        max_output_tokens=2_048,
        allow_network=True,
        allow_sensitive_cloud_data=True,
    )

    model = strands_module._build_model(settings)

    assert isinstance(model, anthropic_models.AnthropicModel)
    assert model.get_config()["model_id"] == "claude-sonnet-4-5-20250929"
    assert model.get_config()["max_tokens"] == 2_048


def test_openai_model_receives_key_model_id_base_url_and_output_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_models = pytest.importorskip("strands.models.openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-secret")
    settings = StrandsAgentSettings(
        model_provider="openai",
        openai_model_id="gpt-4o",
        openai_base_url="https://gateway.example/v1",
        max_output_tokens=2_048,
        allow_network=True,
        allow_sensitive_cloud_data=True,
    )

    model = strands_module._build_model(settings)

    assert isinstance(model, openai_models.OpenAIModel)
    assert model.get_config()["model_id"] == "gpt-4o"
    assert model.get_config()["params"]["max_tokens"] == 2_048
