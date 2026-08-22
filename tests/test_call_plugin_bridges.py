from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from folderhome.bridges.call_plugins import CallPluginBridge, CallPluginBridgeError
from folderhome.plugin_host import load_manifests

REPO_ROOT = Path(__file__).parents[1]
MANIFEST_ROOT = REPO_ROOT / "manifests" / "components"


def _plugin(plugin_id: str):
    return next(
        plugin
        for plugin in load_manifests(MANIFEST_ROOT)
        if plugin.plugin_id == plugin_id
    )


@pytest.mark.parametrize(
    ("plugin_id", "provider_root", "expected_pattern"),
    (
        ("hungrycall", REPO_ROOT.parent / "hungrycall", "sequential_early_stop"),
        ("ringedingeding", REPO_ROOT.parent / "ringedingeding", "group_poll"),
    ),
)
def test_pinned_call_plugin_probe_is_local_and_dry_run_only(
    plugin_id: str,
    provider_root: Path,
    expected_pattern: str,
) -> None:
    if not provider_root.is_dir():
        pytest.skip(f"pinned {plugin_id} checkout unavailable")
    result = CallPluginBridge(
        plugin=_plugin(plugin_id),
        provider_root=provider_root,
    ).probe()

    assert result.plugin_id == plugin_id
    assert result.pattern == expected_pattern
    assert result.runtime_imported is True
    assert result.dry_run_available is True
    assert result.live_invoked is False
    assert result.network_used is False
    assert result.phone_calls_placed is False


def test_call_plugin_probe_rejects_revision_mismatch() -> None:
    if not (REPO_ROOT.parent / "hungrycall").is_dir():
        pytest.skip("pinned hungrycall checkout unavailable")
    plugin = replace(_plugin("hungrycall"), source_revision="0" * 40)

    with pytest.raises(CallPluginBridgeError, match="Git-Revision"):
        CallPluginBridge(
            plugin=plugin,
            provider_root=REPO_ROOT.parent / "hungrycall",
        ).probe()
