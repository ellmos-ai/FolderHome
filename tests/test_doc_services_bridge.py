from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.bridges.doc_services import DocServicesBridge
from folderhome.contracts import ContentFormat, IndexStatus, PrivacyStatus
from folderhome.plugin_host import load_manifests

REPO_ROOT = Path(__file__).parents[1]
PROVIDER_ROOT = REPO_ROOT.parent / "doc-services"
MANIFEST_ROOT = REPO_ROOT / "manifests" / "components"


def _plugin():
    return next(
        plugin
        for plugin in load_manifests(MANIFEST_ROOT)
        if plugin.plugin_id == "doc-services"
    )


@pytest.mark.skipif(not PROVIDER_ROOT.is_dir(), reason="pinned doc-services checkout unavailable")
def test_doc_services_bridge_extracts_without_changing_the_source(tmp_path: Path) -> None:
    source = tmp_path / "Bericht.txt"
    source.write_text("Synthetischer Bericht über eine Hausratversicherung.", encoding="utf-8")
    before = source.read_bytes()
    bridge = DocServicesBridge(plugin=_plugin(), provider_root=PROVIDER_ROOT)

    record = bridge.extract(source)

    assert source.read_bytes() == before
    assert record.filename == "Bericht.txt"
    assert record.text == "Synthetischer Bericht über eine Hausratversicherung."
    assert record.content_format is ContentFormat.TEXT
    assert record.extraction_provider == "doc-services"
    assert record.extraction_method == "direct"
    assert record.privacy_status is PrivacyStatus.CLEAR
    assert record.index_status is IndexStatus.NOT_INDEXED
    assert record.source_sha256


@pytest.mark.skipif(not PROVIDER_ROOT.is_dir(), reason="pinned doc-services checkout unavailable")
def test_doc_services_bridge_maps_sensitive_content_to_blocked(tmp_path: Path) -> None:
    source = tmp_path / "Zahlung.txt"
    source.write_text(
        "Nur Testdaten: IBAN DE89 3704 0044 0532 0130 00",
        encoding="utf-8",
    )
    bridge = DocServicesBridge(plugin=_plugin(), provider_root=PROVIDER_ROOT)

    record = bridge.extract(source)

    assert record.privacy_status is PrivacyStatus.BLOCKED
    assert "DE89 3704" not in record.privacy_summary
    assert "ROT" in record.privacy_summary
