import argparse
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import strands.models
from strands.models import Model

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.pseudonymization import (
    PseudonymizingModel,
    PseudonymVault,
    seed_vault_from_application,
)
from folderhome.application.strands_agent import StrandsAgentSettings, run_folderhome_agent
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.contracts import LocalAppSettings
from folderhome.local_server import LocalServer

PROFILE_DIR = Path(__file__).parents[1] / "examples" / "profiles"


class StubSearcher:
    def search(self, query: str, *, limit: int = 20):
        return (
            KnowledgeDigestSearchHit(
                source="document",
                filename="synthetic.txt",
                file_type="txt",
                snippet=query,
                relevance=-1.0,
                word_count=1,
            ),
        )[:limit]


class CapturingModel(Model):
    def __init__(self, **_kwargs) -> None:
        self.captured = None
        self._config = {"model_id": "remote-stub", "context_window_limit": 8192}

    def update_config(self, **model_config) -> None:
        self._config.update(model_config)

    def get_config(self):
        return dict(self._config)

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        del output_model, prompt, system_prompt, kwargs
        if False:
            yield {}
        raise NotImplementedError

    async def stream(
        self,
        messages,
        tool_specs=None,
        system_prompt=None,
        **kwargs,
    ):
        self.captured = {
            "messages": messages,
            "tool_specs": tool_specs,
            "system_prompt": system_prompt,
            "kwargs": kwargs,
        }
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": "Hallo ⟨PER"}}}
        yield {"contentBlockDelta": {"delta": {"text": "SON_1⟩"}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "metrics": {"latencyMs": 0},
            }
        }


class ToolArgumentModel(CapturingModel):
    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        del messages, tool_specs, system_prompt, kwargs
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "start": {"toolUse": {"toolUseId": "one", "name": "search"}}
            }
        }
        yield {
            "contentBlockDelta": {
                "delta": {"toolUse": {"input": '{"⟨PERSON_1⟩":"⟨EMAIL_'}}
            }
        }
        yield {
            "contentBlockDelta": {
                "delta": {"toolUse": {"input": "1⟩\"}"}}
            }
        }
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}


class CountingStructuredModel(CapturingModel):
    def __init__(self) -> None:
        super().__init__()
        self.count_request = None
        self.structured_request = None

    async def count_tokens(
        self,
        messages,
        tool_specs=None,
        system_prompt=None,
        system_prompt_content=None,
    ):
        self.count_request = {
            "messages": messages,
            "tool_specs": tool_specs,
            "system_prompt": system_prompt,
            "system_prompt_content": system_prompt_content,
        }
        return 17

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        self.structured_request = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "kwargs": kwargs,
        }
        del output_model
        yield {"output": {"owner": "⟨PERSON_1⟩"}}


def _app(tmp_path: Path, settings: StrandsAgentSettings | None = None) -> LocalApplication:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
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
        session_token="pseudonymization-test-token-with-sufficient-entropy",
        agent_settings=settings,
    )


def _remote_settings() -> StrandsAgentSettings:
    return StrandsAgentSettings(
        model_provider="bedrock",
        bedrock_model_id="eu.amazon.nova-micro-v1:0",
        aws_region="eu-central-1",
        allow_network=True,
        allow_sensitive_cloud_data=True,
    )


def test_vault_is_deterministic_and_known_values_precede_patterns() -> None:
    vault = PseudonymVault()
    vault.add_known("PERSON", "Lukas Beispiel")
    vault.add_known("EMAIL", "lukas.beispiel@example.invalid")
    vault.begin_turn()

    first = vault.pseudonymize(
        "Lukas Beispiel nutzt lukas.beispiel@example.invalid; Lukas Beispiel bestätigt."
    )
    second = vault.pseudonymize("LUKAS BEISPIEL")

    assert first == "⟨PERSON_1⟩ nutzt ⟨EMAIL_1⟩; ⟨PERSON_1⟩ bestätigt."
    assert second == "⟨PERSON_1⟩"
    assert vault.summary(active=True) == {
        "active": True,
        "replacements": 2,
        "kinds": {"PERSON": 1, "EMAIL": 1},
    }


def test_vault_recognizes_required_patterns_and_tolerates_changed_brackets() -> None:
    vault = PseudonymVault()
    vault.begin_turn()
    protected = vault.pseudonymize(
        "Mail lea@example.org, Telefon +49 30 12345678, IBAN DE89 3704 0044 0532 0130 00, "
        "Adresse Musterstraße 12, 12345 Berlin, Police ABC-4711, geboren am 03.04.1985 "
        "und Kennzeichen B-AB 1234 sowie SYN-POLICE-0822. International +1 212 555 0123."
    )

    for kind in ("EMAIL", "PHONE", "IBAN", "ADDRESS", "ID"):
        assert f"⟨{kind}_" in protected
    tolerant = protected.replace("⟨EMAIL_1⟩", "[EMAIL_1]").replace(
        "⟨IBAN_1⟩", "<IBAN_1>"
    )
    restored = vault.restore(tolerant)
    assert "lea@example.org" in restored
    assert "DE89 3704 0044 0532 0130 00" in restored
    assert "Musterstraße 12" in restored
    assert "ABC-4711" in restored
    assert "SYN-POLICE-0822" in restored
    assert "+1 212 555 0123" in restored


def test_longer_pattern_prevents_known_substring_leak() -> None:
    vault = PseudonymVault()
    vault.add_known("ID", "User")
    vault.add_known("PERSON", "Ada")
    vault.begin_turn()

    protected = vault.pseudonymize("user@example.org and ada@example.org")

    assert protected == "⟨EMAIL_1⟩ and ⟨EMAIL_2⟩"
    assert "@example.org" not in protected


def test_model_wrapper_protects_all_outbound_content_and_restores_split_deltas() -> None:
    vault = PseudonymVault()
    vault.add_known("PERSON", "Lukas Beispiel")
    vault.add_known("EMAIL", "lukas@example.org")
    vault.begin_turn()
    inner = CapturingModel()
    model = PseudonymizingModel(inner, vault)
    messages = [
        {"role": "user", "content": [{"text": "Lukas Beispiel: lukas@example.org"}]},
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "1",
                        "status": "success",
                        "content": [{"json": {"Lukas Beispiel": "lukas@example.org"}}],
                    }
                }
            ],
        },
    ]

    async def collect():
        return [
            event
            async for event in model.stream(
                messages,
                system_prompt="Assist Lukas Beispiel.",
            )
        ]

    events = asyncio.run(collect())
    outbound = json.dumps(inner.captured, ensure_ascii=False)
    assert "Lukas Beispiel" not in outbound
    assert "lukas@example.org" not in outbound
    assert "⟨PERSON_1⟩" in outbound
    assert "⟨EMAIL_1⟩" in outbound
    assert any(
        event.get("contentBlockDelta", {}).get("delta", {}).get("text")
        == "Hallo Lukas Beispiel"
        for event in events
    )

    tool_model = PseudonymizingModel(ToolArgumentModel(), vault)

    async def collect_tool_args():
        return [event async for event in tool_model.stream([])]

    tool_events = asyncio.run(collect_tool_args())
    restored_input = next(
        event["contentBlockDelta"]["delta"]["toolUse"]["input"]
        for event in tool_events
        if "toolUse" in event.get("contentBlockDelta", {}).get("delta", {})
    )
    assert json.loads(restored_input) == {"Lukas Beispiel": "lukas@example.org"}


def test_count_tokens_and_structured_output_use_the_same_boundary() -> None:
    vault = PseudonymVault()
    vault.add_known("PERSON", "Lukas Beispiel")
    vault.begin_turn()
    inner = CountingStructuredModel()
    model = PseudonymizingModel(inner, vault)

    count = asyncio.run(model.count_tokens(
        [{"role": "user", "content": [{"text": "Lukas Beispiel"}]}],
        system_prompt="Assist Lukas Beispiel",
        system_prompt_content=[{"text": "Owner Lukas Beispiel"}],
    ))

    async def collect_structured():
        return [
            event
            async for event in model.structured_output(
                dict,
                [{"role": "user", "content": [{"text": "Lukas Beispiel"}]}],
                system_prompt="Assist Lukas Beispiel",
            )
        ]

    events = asyncio.run(collect_structured())
    assert count == 17
    assert "Lukas Beispiel" not in json.dumps(inner.count_request, ensure_ascii=False)
    assert "Lukas Beispiel" not in json.dumps(inner.structured_request, ensure_ascii=False)
    assert events == [{"output": {"owner": "Lukas Beispiel"}}]


def test_known_values_are_loaded_through_existing_stores(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from folderhome.application import pseudonymization

    class Contacts:
        def __init__(self, _state_dir):
            pass

        def list_contacts(self, *, profile_id):
            assert profile_id == "lukas"
            return (
                SimpleNamespace(
                    contact_name="Ada Beispiel",
                    email="ada@example.org",
                    phone="+49 30 76543210",
                ),
            )

    class Documents:
        def __init__(self, _state_dir):
            pass

        def load(self):
            return (
                {
                    "document_id": "doc_" + "a" * 64,
                    "metadata": {"insurance_number": "VERS-4711-TEST"},
                },
            )

    monkeypatch.setattr(pseudonymization, "ContactRegisterStore", Contacts)
    monkeypatch.setattr(pseudonymization, "DocumentCatalogStore", Documents)
    application = _app(tmp_path)
    vault = PseudonymVault()
    vault.begin_turn()
    seed_vault_from_application(vault, application, profile_id="lukas")
    protected = vault.pseudonymize(
        "Ada Beispiel ada@example.org +49 30 76543210 "
        + "doc_"
        + "a" * 64
        + " VERS-4711-TEST"
    )

    assert "⟨PERSON_" in protected
    assert "⟨EMAIL_" in protected
    assert "⟨PHONE_" in protected
    assert "⟨DOC_" in protected
    assert "⟨ID_" in protected


def test_remote_agent_report_contains_counts_but_never_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = CapturingModel()

    class StubBedrockModel(CapturingModel):
        def __new__(cls, **_kwargs):
            return built

    monkeypatch.setattr(strands.models, "BedrockModel", StubBedrockModel)
    report = run_folderhome_agent(
        application=_app(tmp_path),
        prompt="Antworte Lukas Beispiel.",
        profile_id="lukas",
        settings=_remote_settings(),
    )

    assert report.response_text == "Hallo Lukas Beispiel"
    assert report.pseudonymization["active"] is True
    assert report.pseudonymization["replacements"] >= 1
    assert report.pseudonymization["kinds"]["PERSON"] >= 1
    serialized = json.dumps(report.pseudonymization, ensure_ascii=False)
    assert "Lukas" not in serialized


def test_fixture_and_loopback_models_are_not_wrapped() -> None:
    from folderhome.application import strands_agent

    fixture = strands_agent._build_model(StrandsAgentSettings(model_provider="fixture"))
    assert not isinstance(fixture, PseudonymizingModel)

    pytest.importorskip("strands.models.ollama")
    loopback = strands_agent._build_model(
        StrandsAgentSettings(
            model_provider="ollama",
            ollama_host="http://127.0.0.1:11434",
            ollama_model_id="qwen3.8:27b-mlx",
        )
    )
    assert not isinstance(loopback, PseudonymizingModel)


def test_remote_pseudonymization_can_be_deliberately_disabled(tmp_path: Path) -> None:
    from folderhome.application import strands_agent

    settings = StrandsAgentSettings(
        model_provider="bedrock",
        bedrock_model_id="eu.amazon.nova-micro-v1:0",
        aws_region="eu-central-1",
        allow_network=True,
        allow_sensitive_cloud_data=True,
        cloud_pseudonymization="off",
    )
    inner = CapturingModel()
    assert strands_agent._protect_remote_model(settings, inner, PseudonymVault()) is inner
    application = _app(tmp_path, settings)
    status = application._status_payload(8765)
    assert status["cloud_pseudonymization"] == "off"
    assert "clear text" in status["cloud_pseudonymization_warning"]

    server = LocalServer.__new__(LocalServer)
    server._server = SimpleNamespace(  # type: ignore[attr-defined]
        application=application,
        server_address=("127.0.0.1", 8765),
    )
    assert "clear text" in server.to_public_dict()["warning"]


def test_pseudonymization_setting_defaults_validates_and_loads(tmp_path: Path) -> None:
    from folderhome.cli import _apply_launch_config

    assert StrandsAgentSettings().cloud_pseudonymization == "on"
    with pytest.raises(ValueError, match="on oder off"):
        StrandsAgentSettings(cloud_pseudonymization="invalid")  # type: ignore[arg-type]

    launch = tmp_path / "launch.json"
    base = {
        "schema": "folderhome.launch-config.v1",
        "profiles_dir": str(PROFILE_DIR),
        "state_dir": str(tmp_path),
    }
    launch.write_text(json.dumps(base), encoding="utf-8")
    args = argparse.Namespace(launch_config=str(launch))
    _apply_launch_config(args)
    assert args.cloud_pseudonymization == "on"

    launch.write_text(
        json.dumps({**base, "cloud_pseudonymization": "off"}),
        encoding="utf-8",
    )
    args = argparse.Namespace(launch_config=str(launch))
    _apply_launch_config(args)
    assert args.cloud_pseudonymization == "off"


def test_status_contract_distinguishes_remote_and_local_pseudonymization(
    tmp_path: Path,
) -> None:
    remote = _app(tmp_path / "remote", _remote_settings())
    local = _app(
        tmp_path / "local",
        StrandsAgentSettings(model_provider="fixture"),
    )

    remote_status = remote._status_payload(8765)
    local_status = local._status_payload(8765)
    assert remote_status["cloud_pseudonymization"] == "active"
    assert remote_status["cloud_pseudonymization_replacements"] == 0
    assert remote_status["cloud_pseudonymization_kinds"] == {}
    assert local_status["cloud_pseudonymization"] == "not_needed_local"


def test_web_ui_exposes_bilingual_pseudonymization_status() -> None:
    root = Path(__file__).parents[1] / "src" / "folderhome" / "web_ui"
    html = (root / "index.html").read_text(encoding="utf-8")
    javascript = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "app.css").read_text(encoding="utf-8")

    assert html.count('id="pseudonymization-status"') == 1
    assert "Cloud pseudonymization: active" in javascript
    assert "Cloud-Pseudonymisierung: aktiv" in javascript
    assert 'data-state="off"' in css
