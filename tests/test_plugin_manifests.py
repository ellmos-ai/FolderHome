from pathlib import Path

import pytest

from folderhome import plugin_host

MANIFEST_ROOT = Path(__file__).parents[1] / "manifests" / "components"


def test_repository_manifests_pin_the_reused_components() -> None:
    plugins = plugin_host.load_manifests(MANIFEST_ROOT)

    assert {plugin.plugin_id: plugin.source_revision for plugin in plugins} == {
        "doc-services": "e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2",
        "file-collect-sort-action": "8ebac2739c11c6a041abdd7b30131cef648b4753",
        "hungrycall": "2c7db533f073d07eae6d758ceab91b9423ae1dc7",
        "KnowledgeDigest": "7040c66aa9326975ad81c156acf0d49fd5dca60f",
        "law-checker": "a5b0cd51bc3666962f2fae8017c855dea0a712a2",
        "llm-note": "b5fe59fc155ded9603566aa0fb920a53181a2426",
        "ringedingeding": "d80dd81a6d7bf64298d4ef290c3b54ab5f50e990",
        "steuer-assistent": "5d39aeec98bf0a5734bf07dc35a58aa9e1331309",
    }
    assert all(plugin.license_id == "MIT" for plugin in plugins)
    assert all(plugin.interface_version == "folderhome.plugin.v1" for plugin in plugins)


def test_document_provider_manifests_expose_the_reused_boundaries() -> None:
    plugins = {plugin.plugin_id: plugin for plugin in plugin_host.load_manifests(MANIFEST_ROOT)}

    assert {item.capability_id for item in plugins["doc-services"].capabilities} == {
        "documents.extract",
        "documents.privacy_classify",
    }
    knowledge_capabilities = {
        item.capability_id: item for item in plugins["KnowledgeDigest"].capabilities
    }
    assert set(knowledge_capabilities) == {"documents.index", "documents.search"}
    assert knowledge_capabilities["documents.index"].side_effects == (
        plugin_host.SideEffect.FILESYSTEM_WRITE,
    )
    assert knowledge_capabilities["documents.index"].gate_required is True
    assert knowledge_capabilities["documents.search"].side_effects == ()
    note_capabilities = {
        item.capability_id: item for item in plugins["llm-note"].capabilities
    }
    assert set(note_capabilities) == {"notes.read", "notes.write"}
    assert note_capabilities["notes.read"].side_effects == ()
    assert note_capabilities["notes.write"].side_effects == (
        plugin_host.SideEffect.FILESYSTEM_WRITE,
    )
    assert note_capabilities["notes.write"].gate_required is True


def test_reused_plugins_default_to_dry_run_and_gate_every_side_effect() -> None:
    plugins = plugin_host.load_manifests(MANIFEST_ROOT)

    assert all(plugin.default_mode == "dry-run" for plugin in plugins)
    assert all(plugin.live_enabled is False for plugin in plugins)
    assert all(plugin.classification == "REUSED_UNCHANGED" for plugin in plugins)
    side_effecting = [
        capability
        for plugin in plugins
        for capability in plugin.capabilities
        if capability.side_effects
    ]
    assert side_effecting
    assert all(capability.dry_run_supported for capability in side_effecting)
    assert all(capability.gate_required for capability in side_effecting)


def test_unknown_side_effect_fails_closed_with_manifest_context(tmp_path: Path) -> None:
    manifest = tmp_path / "unsafe.toml"
    manifest.write_text(
        """
schema = "folderhome.component-manifest.v1"
id = "unsafe"
name = "Unsafe"
version = "0.1.0"
license = "MIT"
interface_version = "folderhome.plugin.v1"
classification = "REUSED_UNCHANGED"
default_mode = "dry-run"
live_enabled = false
[source]
repository = "https://example.invalid/unsafe.git"
revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
[[capabilities]]
id = "unsafe.act"
title = "Unsichere Aktion"
side_effects = ["unknown.effect"]
dry_run_supported = true
gate_required = true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(plugin_host.ManifestValidationError, match="unknown.effect.*unsafe.toml"):
        plugin_host.load_manifests(tmp_path)


def test_side_effect_without_dry_run_and_gate_fails_closed(tmp_path: Path) -> None:
    manifest = tmp_path / "ungated.toml"
    manifest.write_text(
        """
schema = "folderhome.component-manifest.v1"
id = "ungated"
name = "Ungated"
version = "0.1.0"
license = "MIT"
interface_version = "folderhome.plugin.v1"
classification = "REUSED_UNCHANGED"
default_mode = "dry-run"
live_enabled = false
[source]
repository = "https://example.invalid/ungated.git"
revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
[[capabilities]]
id = "ungated.act"
title = "Nicht abgesicherte Aktion"
side_effects = ["filesystem.write"]
dry_run_supported = false
gate_required = false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(plugin_host.ManifestValidationError, match="ungated.act.*dry-run.*gate"):
        plugin_host.load_manifests(tmp_path)


def test_unrecognized_manifest_schema_fails_closed_before_loading(tmp_path: Path) -> None:
    manifest = tmp_path / "future.toml"
    manifest.write_text(
        """
schema = "folderhome.component-manifest.v99"
id = "future"
name = "Future"
version = "0.1.0"
license = "MIT"
interface_version = "folderhome.plugin.v1"
classification = "REUSED_UNCHANGED"
default_mode = "dry-run"
live_enabled = false
[source]
repository = "https://example.invalid/future.git"
revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
capabilities = []
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        plugin_host.ManifestValidationError,
        match="folderhome.component-manifest.v99.*future.toml",
    ):
        plugin_host.load_manifests(tmp_path)


def test_incomplete_manifest_fails_closed_with_filename(tmp_path: Path) -> None:
    manifest = tmp_path / "incomplete.toml"
    manifest.write_text(
        'schema = "folderhome.component-manifest.v1"\nid = "incomplete"\n',
        encoding="utf-8",
    )

    with pytest.raises(
        plugin_host.ManifestValidationError,
        match="Missing required field.*incomplete.toml",
    ):
        plugin_host.load_manifests(tmp_path)


def test_live_enabled_manifest_is_rejected_by_the_foundation_host(tmp_path: Path) -> None:
    manifest = tmp_path / "live.toml"
    manifest.write_text(
        """
schema = "folderhome.component-manifest.v1"
id = "live"
name = "Live"
version = "0.1.0"
license = "MIT"
interface_version = "folderhome.plugin.v1"
classification = "REUSED_UNCHANGED"
default_mode = "dry-run"
live_enabled = true
capabilities = []
[source]
repository = "https://example.invalid/live.git"
revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(plugin_host.ManifestValidationError, match="live_enabled.*live.toml"):
        plugin_host.load_manifests(tmp_path)


def test_unpinned_source_revision_is_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "floating.toml"
    manifest.write_text(
        """
schema = "folderhome.component-manifest.v1"
id = "floating"
name = "Floating"
version = "0.1.0"
license = "MIT"
interface_version = "folderhome.plugin.v1"
classification = "REUSED_UNCHANGED"
default_mode = "dry-run"
live_enabled = false
capabilities = []
[source]
repository = "https://example.invalid/floating.git"
revision = "main"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(plugin_host.ManifestValidationError, match="40-character.*floating.toml"):
        plugin_host.load_manifests(tmp_path)


def test_duplicate_plugin_ids_are_rejected(tmp_path: Path) -> None:
    source = (MANIFEST_ROOT / "hungrycall.toml").read_text(encoding="utf-8")
    (tmp_path / "first.toml").write_text(source, encoding="utf-8")
    (tmp_path / "second.toml").write_text(source, encoding="utf-8")

    with pytest.raises(
        plugin_host.ManifestValidationError,
        match="Duplicate plugin id.*hungrycall",
    ):
        plugin_host.load_manifests(tmp_path)
