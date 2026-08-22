from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from folderhome.application.document_ingest import (
    FolderIngestGateError,
    FolderIngestResourceError,
    IngestItemStatus,
    ingest_folder,
)
from folderhome.bridges.doc_services import DocServicesBridge
from folderhome.bridges.knowledge_digest import KnowledgeDigestBridge
from folderhome.capabilities.resource_budget import DEFAULT_RESOURCE_POLICY
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


def _bridges(tmp_path: Path) -> tuple[DocServicesBridge, KnowledgeDigestBridge]:
    return (
        DocServicesBridge(
            plugin=_plugin("doc-services"),
            provider_root=DOC_SERVICES_ROOT,
        ),
        KnowledgeDigestBridge(
            plugin=_plugin("KnowledgeDigest"),
            provider_root=KNOWLEDGE_DIGEST_ROOT,
            state_dir=tmp_path / "state",
        ),
    )


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_folder_ingest_requires_explicit_index_write_gate(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "Bericht.txt").write_text("Synthetischer Bericht.", encoding="utf-8")
    extractor, indexer = _bridges(tmp_path)

    with pytest.raises(FolderIngestGateError, match="Schreibfreigabe"):
        ingest_folder(
            inbox,
            extractor=extractor,
            indexer=indexer,
            allow_index_write=False,
        )

    assert not (tmp_path / "state").exists()


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_folder_ingest_indexes_supported_files_and_skips_unknown_types(
    tmp_path: Path,
) -> None:
    inbox = tmp_path / "inbox"
    nested = inbox / "Versicherung"
    nested.mkdir(parents=True)
    text_file = inbox / "Überblick.txt"
    markdown_file = nested / "Notiz.md"
    unknown_file = inbox / "Anlage.bin"
    text_file.write_text(
        "Synthetischer Überblick zur Hausratversicherung.",
        encoding="utf-8",
    )
    markdown_file.write_text(
        "# Notiz\n\nSynthetische Krankenversicherung.",
        encoding="utf-8",
    )
    unknown_file.write_bytes(b"synthetic")
    before = {path: path.read_bytes() for path in (text_file, markdown_file, unknown_file)}
    extractor, indexer = _bridges(tmp_path)

    result = ingest_folder(
        inbox,
        extractor=extractor,
        indexer=indexer,
        allow_index_write=True,
        recursive=True,
    )

    assert result.total_files == 3
    assert result.indexed == 2
    assert result.skipped == 1
    assert result.failed == 0
    assert [item.relative_path for item in result.items] == [
        "Anlage.bin",
        "Versicherung/Notiz.md",
        "Überblick.txt",
    ]
    assert result.items[0].status is IngestItemStatus.SKIPPED
    assert result.items[0].document is None
    assert all(
        item.document is None or item.document.index_status is IndexStatus.INDEXED
        for item in result.items
    )
    assert result.to_dict()["items"][1]["document"].get("text") is None
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / "state" / "archive").exists()


def test_folder_ingest_rejects_over_budget_before_provider_calls(tmp_path: Path) -> None:
    class UnusedProvider:
        def extract(self, source_path: Path):
            raise AssertionError(f"Extractor darf nicht aufgerufen werden: {source_path}")

        def index(self, document):
            raise AssertionError(f"Indexer darf nicht aufgerufen werden: {document}")

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "A.txt").write_text("A", encoding="utf-8")
    (inbox / "B.txt").write_text("B", encoding="utf-8")
    policy = replace(DEFAULT_RESOURCE_POLICY, max_files=1)

    with pytest.raises(FolderIngestResourceError, match="Dateianzahl-Budget"):
        ingest_folder(
            inbox,
            extractor=UnusedProvider(),
            indexer=UnusedProvider(),
            allow_index_write=True,
            resource_policy=policy,
        )
