from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from folderhome.bridges.doc_services import DocServicesBridge
from folderhome.bridges.knowledge_digest import (
    KnowledgeDigestBridge,
    KnowledgeDigestBridgeError,
)
from folderhome.contracts import IndexStatus
from folderhome.plugin_host import load_manifests

REPO_ROOT = Path(__file__).parents[1]
DOC_SERVICES_ROOT = REPO_ROOT.parent / "doc-services"
KNOWLEDGE_DIGEST_ROOT = REPO_ROOT.parent / "KnowledgeDigest"
MANIFEST_ROOT = REPO_ROOT / "manifests" / "components"


def _plugin(plugin_id: str):
    return next(
        plugin
        for plugin in load_manifests(MANIFEST_ROOT)
        if plugin.plugin_id == plugin_id
    )


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_knowledge_digest_indexes_and_searches_without_archiving_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "inbox" / "Versicherungsstatus.txt"
    source.parent.mkdir()
    source.write_text(
        "Die synthetische Krankenversicherung läuft unverändert weiter.",
        encoding="utf-8",
    )
    before = source.read_bytes()
    extracted = DocServicesBridge(
        plugin=_plugin("doc-services"),
        provider_root=DOC_SERVICES_ROOT,
    ).extract(source)
    bridge = KnowledgeDigestBridge(
        plugin=_plugin("KnowledgeDigest"),
        provider_root=KNOWLEDGE_DIGEST_ROOT,
        state_dir=tmp_path / "state",
    )

    indexed = bridge.index(extracted)
    database_before_search = (tmp_path / "state" / "knowledge.db").read_bytes()
    results = bridge.search("Krankenversicherung")

    assert source.exists()
    assert source.read_bytes() == before
    assert indexed.index_status is IndexStatus.INDEXED
    assert indexed.index_provider == "KnowledgeDigest"
    assert indexed.index_ref == f"knowledge://documents/{indexed.document_id}"
    assert (tmp_path / "state" / "knowledge.db").is_file()
    assert (tmp_path / "state" / "knowledge.db").read_bytes() == database_before_search
    assert not (tmp_path / "state" / "archive").exists()
    assert [result.filename for result in results] == ["Versicherungsstatus.txt"]
    assert results[0].source == "document"
    assert "Krankenversicherung" in results[0].snippet


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_knowledge_digest_rejects_document_changed_after_extraction(tmp_path: Path) -> None:
    source = tmp_path / "Hinweis.txt"
    source.write_text("Synthetische Erstfassung.", encoding="utf-8")
    extracted = DocServicesBridge(
        plugin=_plugin("doc-services"),
        provider_root=DOC_SERVICES_ROOT,
    ).extract(source)
    source.write_text("Synthetische Zweitfassung.", encoding="utf-8")
    bridge = KnowledgeDigestBridge(
        plugin=_plugin("KnowledgeDigest"),
        provider_root=KNOWLEDGE_DIGEST_ROOT,
        state_dir=tmp_path / "state",
    )

    with pytest.raises(KnowledgeDigestBridgeError, match="seit der Extraktion geändert"):
        bridge.index(extracted)

    assert not (tmp_path / "state" / "knowledge.db").exists()


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_knowledge_digest_rejects_wrong_provider_pin(tmp_path: Path) -> None:
    plugin = replace(_plugin("KnowledgeDigest"), source_revision="0" * 40)
    bridge = KnowledgeDigestBridge(
        plugin=plugin,
        provider_root=KNOWLEDGE_DIGEST_ROOT,
        state_dir=tmp_path / "state",
    )

    with pytest.raises(KnowledgeDigestBridgeError, match="Git-Revision"):
        bridge.search("Test")
