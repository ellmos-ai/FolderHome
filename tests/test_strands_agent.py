from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.strands_agent import (
    FolderHomeAgentError,
    StrandsAgentSettings,
    run_folderhome_agent,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.contracts import LocalAppSettings

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
