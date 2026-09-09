from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from folderhome.bridges._provider import ProviderCheckoutError, load_pinned_python_modules
from folderhome.contracts import PluginDescriptor
from folderhome.provider_locations import default_provider_root


@pytest.fixture
def provider(tmp_path: Path):
    root = tmp_path / "provider"
    package = root / "src" / "folderhome_test_provider"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    (package / "api.py").write_text('def answer():\n    return "pinned"\n', encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    for args in (
        ["init", "--quiet"],
        ["add", "."],
        [
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    plugin = PluginDescriptor(
        plugin_id="fixture",
        name="fixture",
        version="1.2.3",
        source_repository="https://example.invalid/fixture",
        source_revision=revision,
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
    )
    yield root, plugin
    for name in tuple(sys.modules):
        if name == "folderhome_test_provider" or name.startswith("folderhome_test_provider."):
            del sys.modules[name]


def _load(root, plugin, **kwargs):
    return load_pinned_python_modules(
        plugin=plugin,
        provider_root=root,
        package_name="folderhome_test_provider",
        module_names=("folderhome_test_provider.api",),
        src_layout=True,
        **kwargs,
    )


def test_src_layout_imports_the_pinned_api_and_restores_search_path(provider):
    root, plugin = provider
    before = sys.path.copy()
    modules = _load(root, plugin)
    assert modules["folderhome_test_provider.api"].answer() == "pinned"
    assert Path(modules["folderhome_test_provider.api"].__file__).is_relative_to(root / "src")
    assert sys.path == before


def test_src_layout_rejects_ambiguous_parent_import_before_loading(provider):
    root, plugin = provider
    with pytest.raises(ProviderCheckoutError, match="Layout"):
        _load(root, plugin, import_from_parent=True)
    assert "folderhome_test_provider" not in sys.modules


@pytest.mark.parametrize("change", ["dirty", "revision", "version"])
def test_src_layout_retains_checkout_and_version_gates(provider, change):
    root, plugin = provider
    if change == "dirty":
        (root / "unexpected.txt").write_text("foreign edit", encoding="utf-8")
    elif change == "revision":
        plugin = replace(plugin, source_revision="0" * 40)
    else:
        plugin = replace(plugin, version="9.9.9")
    with pytest.raises(ProviderCheckoutError):
        _load(root, plugin)


def test_src_layout_rejects_preloaded_foreign_submodule(provider, monkeypatch, tmp_path):
    root, plugin = provider
    foreign = ModuleType("folderhome_test_provider.api")
    foreign.__file__ = str(tmp_path / "foreign.py")
    monkeypatch.setitem(sys.modules, "folderhome_test_provider.api", foreign)
    with pytest.raises(ProviderCheckoutError, match="anderer"):
        _load(root, plugin)
    assert sys.modules["folderhome_test_provider.api"] is foreign


def test_provider_loader_rejects_modules_outside_the_named_package(provider):
    root, plugin = provider
    with pytest.raises(ProviderCheckoutError, match="Paket"):
        load_pinned_python_modules(
            plugin=plugin,
            provider_root=root,
            package_name="folderhome_test_provider",
            module_names=("os",),
            src_layout=True,
        )


def test_root_only_import_rejects_preloaded_foreign_transitive_module(
    provider, monkeypatch, tmp_path
):
    root, plugin = provider
    foreign = ModuleType("folderhome_test_provider.store")
    foreign.__file__ = str(tmp_path / "other-checkout" / "store.py")
    monkeypatch.setitem(sys.modules, foreign.__name__, foreign)
    with pytest.raises(ProviderCheckoutError, match="anderer"):
        load_pinned_python_modules(
            plugin=plugin,
            provider_root=root,
            package_name="folderhome_test_provider",
            src_layout=True,
        )
    assert "folderhome_test_provider" not in sys.modules


def test_pinned_ellmos_scheduler_src_import_does_not_create_a_store(tmp_path):
    root = default_provider_root(Path(__file__).parents[1], "ellmos-scheduler")
    plugin = PluginDescriptor(
        plugin_id="ellmos-scheduler",
        name="ellmos-scheduler",
        version="0.3.1",
        source_repository="https://github.com/ellmos-ai/ellmos-scheduler.git",
        source_revision="d5103b9a733701f6db80dd08cfae408bf0af8ac5",
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
    )
    modules = load_pinned_python_modules(
        plugin=plugin,
        provider_root=root,
        package_name="ellmos_scheduler",
        src_layout=True,
    )
    # Constructing the real provider is safe; connect/list/init would write.
    modules["ellmos_scheduler"].SchedulerStore(tmp_path / "state" / "scheduler.db")
    assert not (tmp_path / "state").exists()
