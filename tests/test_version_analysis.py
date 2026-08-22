from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.application.document_ingest import ingest_folder
from folderhome.application.version_analysis import (
    DocumentVersionAnalysisError,
    analyze_document_versions,
)
from folderhome.bridges.doc_services import DocServicesBridge
from folderhome.bridges.knowledge_digest import KnowledgeDigestBridge
from folderhome.capabilities.catalog import DocumentCatalogStore
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


def _prepared(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    old = inbox / "KFZ_Hyundai_i10_2025.txt"
    new = inbox / "KFZ_Hyundai_i10_2026.txt"
    old.write_text(
        "KFZ Versicherung für Hyundai i10. Gültig ab 01.01.2025. "
        "Der synthetische Beitrag beträgt 400 Euro.",
        encoding="utf-8",
    )
    new.write_text(
        "KFZ Versicherung für Hyundai i10. Gültig ab 01.01.2026. "
        "Der synthetische Beitrag beträgt 420 Euro.",
        encoding="utf-8",
    )
    extractor = DocServicesBridge(
        plugin=_plugin("doc-services"),
        provider_root=DOC_SERVICES_ROOT,
    )
    searcher = KnowledgeDigestBridge(
        plugin=_plugin("KnowledgeDigest"),
        provider_root=KNOWLEDGE_DIGEST_ROOT,
        state_dir=tmp_path / "state",
    )
    ingest = ingest_folder(
        inbox,
        extractor=extractor,
        indexer=searcher,
        allow_index_write=True,
    )
    catalog = DocumentCatalogStore(tmp_path / "state")
    catalog.merge(
        tuple(item.document for item in ingest.items if item.document is not None)
    )
    return old, new, extractor, searcher, catalog


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_version_analysis_resolves_latest_and_only_plans_archive(tmp_path: Path) -> None:
    old, new, extractor, searcher, catalog = _prepared(tmp_path)
    before = {path: path.read_bytes() for path in (old, new)}

    result = analyze_document_versions(
        "Was ist meine neueste KFZ-Versicherung für meinen Hyundai i10?",
        catalog=catalog,
        searcher=searcher,
        extractor=extractor,
    )

    assert result.family.latest.document.filename == new.name
    assert len(result.comparisons) == 1
    assert len(result.archive_proposals) == 1
    assert result.archive_proposals[0].source_path == old.resolve()
    assert result.archive_proposals[0].gate_granted is False
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / "inbox" / "Archiv").exists()


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_version_analysis_rejects_catalog_source_changed_after_ingest(tmp_path: Path) -> None:
    old, _, extractor, searcher, catalog = _prepared(tmp_path)
    old.write_text("Nachträglich veränderte synthetische Fassung.", encoding="utf-8")

    with pytest.raises(DocumentVersionAnalysisError, match="seit dem Ingest geändert"):
        analyze_document_versions(
            "KFZ Versicherung Hyundai i10",
            catalog=catalog,
            searcher=searcher,
            extractor=extractor,
        )
