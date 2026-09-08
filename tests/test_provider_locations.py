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
