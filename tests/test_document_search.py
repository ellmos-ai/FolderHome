from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.application.document_ingest import ingest_folder
from folderhome.application.document_search import (
    build_theme_dossier,
    normalize_document_query,
    search_documents,
)
from folderhome.bridges.doc_services import DocServicesBridge
from folderhome.bridges.knowledge_digest import KnowledgeDigestBridge
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


def _indexed_bridge(tmp_path: Path) -> KnowledgeDigestBridge:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "Krankenkasse.txt").write_text(
        "Die synthetische Krankenversicherung kostet monatlich 210 Euro.",
        encoding="utf-8",
    )
    (inbox / "Hausrat.txt").write_text(
        "Die synthetische Hausratversicherung kostet jährlich 80 Euro.",
        encoding="utf-8",
    )
    extractor = DocServicesBridge(
        plugin=_plugin("doc-services"),
        provider_root=DOC_SERVICES_ROOT,
    )
    indexer = KnowledgeDigestBridge(
        plugin=_plugin("KnowledgeDigest"),
        provider_root=KNOWLEDGE_DIGEST_ROOT,
        state_dir=tmp_path / "state",
    )
    ingest_folder(
        inbox,
        extractor=extractor,
        indexer=indexer,
        allow_index_write=True,
    )
    return indexer


def test_natural_document_query_is_reduced_to_meaningful_terms() -> None:
    normalized = normalize_document_query(
        "Ich suche nach einem Dokument, in dem ich Informationen über meine "
        "Krankenversicherung abgelegt habe."
    )

    assert normalized == "Krankenversicherung"


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_natural_document_search_returns_only_matching_document(tmp_path: Path) -> None:
    bridge = _indexed_bridge(tmp_path)

    response = search_documents(
        "Ich suche nach einem Dokument, in dem ich Informationen über meine "
        "Krankenversicherung abgelegt habe.",
        searcher=bridge,
    )

    assert response.search_query == "Krankenversicherung"
    assert response.total_hits == 1
    assert response.hits[0].filename == "Krankenkasse.txt"
    assert response.to_dict()["hits"][0]["snippet"]


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_theme_dossier_lists_evidence_and_marks_possible_truncation(tmp_path: Path) -> None:
    bridge = _indexed_bridge(tmp_path)

    dossier = build_theme_dossier(
        "Krankenversicherung",
        searcher=bridge,
        limit=1,
    )

    assert dossier.total_hits == 1
    assert dossier.potentially_truncated is True
    assert "# Themendossier: Krankenversicherung" in dossier.markdown
    assert "Fundstellen" in dossier.markdown
    assert dossier.hits[0].filename in dossier.markdown
    assert "möglicherweise gekürzt" in dossier.markdown
