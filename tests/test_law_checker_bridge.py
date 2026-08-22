from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.bridges.law_checker import LawCheckerBridge, LawCheckerBridgeError
from folderhome.contracts import PluginDescriptor

PROVIDER_ROOT = Path(__file__).parents[2] / "law-checker"
REVISION = "06fb8d57ff90638cc50f5e33c50dbba455ac6f1b"


def _plugin(*, revision: str = REVISION) -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="law-checker",
        name="law-checker",
        version="0.2.2",
        source_repository="https://github.com/ellmos-ai/law-checker.git",
        source_revision=revision,
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
        classification="REUSED_UNCHANGED",
        default_mode="dry-run",
        live_enabled=False,
    )


def test_bridge_qualifies_registry_without_claiming_legal_api() -> None:
    bridge = LawCheckerBridge(plugin=_plugin(), provider_root=PROVIDER_ROOT)

    qualification = bridge.qualification()
    assert qualification["provider_revision"] == REVISION
    assert qualification["registry_version"] == 5
    assert "sgb_v" in qualification["active_registry_keys"]
    assert qualification["legal_review_api_available"] is False
    assert qualification["network_invoked"] is False
    assert bridge.require_registry_key("sgb_v")["kurz"] == "SGB V"


def test_bridge_rejects_wrong_revision_and_missing_registry_key() -> None:
    with pytest.raises(LawCheckerBridgeError, match="Revision"):
        LawCheckerBridge(plugin=_plugin(revision="a" * 40), provider_root=PROVIDER_ROOT)

    bridge = LawCheckerBridge(plugin=_plugin(), provider_root=PROVIDER_ROOT)
    with pytest.raises(LawCheckerBridgeError, match="nicht registriert"):
        bridge.require_registry_key("sgb_x")
