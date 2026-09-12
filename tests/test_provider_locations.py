from pathlib import Path

from folderhome.provider_locations import default_provider_root


def test_default_provider_keeps_legacy_sibling_layout(tmp_path: Path) -> None:
    repository = tmp_path / "FolderHome"
    repository.mkdir()

    assert default_provider_root(repository, "doc-services") == tmp_path / "doc-services"


def test_isolated_provider_takes_precedence_without_touching_sibling(tmp_path: Path) -> None:
    repository = tmp_path / "FolderHome"
    isolated = repository / ".providers" / "doc-services"
    isolated.mkdir(parents=True)
    sibling = tmp_path / "doc-services"
    sibling.mkdir()
    marker = sibling / "user-work.txt"
    marker.write_text("leave intact", encoding="utf-8")

    assert default_provider_root(repository, "doc-services") == isolated
    assert marker.read_text(encoding="utf-8") == "leave intact"


def test_invalid_isolated_target_does_not_silently_fall_back(tmp_path: Path) -> None:
    repository = tmp_path / "FolderHome"
    isolated = repository / ".providers" / "doc-services"
    isolated.parent.mkdir(parents=True)
    isolated.write_text("not a checkout", encoding="utf-8")

    # Selection is not verification: the normal revision gate must reject this.
    assert default_provider_root(repository, "doc-services") == isolated


def test_cli_defaults_route_every_provider_through_default_provider_root() -> None:
    from folderhome import cli

    expected = {
        "DEFAULT_FCSA_PROVIDER_ROOT": "file-collect-sort-action",
        "DEFAULT_DOC_SERVICES_PROVIDER_ROOT": "doc-services",
        "DEFAULT_SCHEDULER_PROVIDER_ROOT": "ellmos-scheduler",
        "DEFAULT_KNOWLEDGE_DIGEST_PROVIDER_ROOT": "KnowledgeDigest",
        "DEFAULT_HUNGRYCALL_PROVIDER_ROOT": "hungrycall",
        "DEFAULT_RINGEDINGEDING_PROVIDER_ROOT": "ringedingeding",
        "DEFAULT_AI_MEDIA_EDITOR_ROOT": "ai-media-editor",
        "DEFAULT_DOCS_GRABBER_ROOT": "UniversalDocsGrabber",
        "DEFAULT_UPTODAY_PROVIDER_ROOT": "UpToday",
        "DEFAULT_LLM_NOTE_PROVIDER_ROOT": "llm-note",
        "DEFAULT_TAX_ASSISTANT_PROVIDER_ROOT": "steuer-assistent",
        "DEFAULT_LAW_CHECKER_PROVIDER_ROOT": "law-checker",
    }
    for attribute, name in expected.items():
        expected_root = default_provider_root(cli.REPOSITORY_ROOT, name)
        assert getattr(cli, attribute) == expected_root, attribute

    # No provider default may bypass the isolated-checkout selection by hardcoding the sibling.
    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert 'REPOSITORY_ROOT.parent / "' not in source
