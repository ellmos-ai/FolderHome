from __future__ import annotations

import json
from pathlib import Path

from folderhome.capabilities.catalog import DocumentCatalogStore
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


def _record(source: Path, source_hash: str) -> DocumentRecord:
    source.write_text("Synthetischer Vertragsinhalt.", encoding="utf-8")
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at="2026-08-21T18:00:00Z",
        text="Synthetischer Vertragsinhalt.",
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="Keine sensiblen Muster erkannt.",
        index_status=IndexStatus.INDEXED,
        index_provider="KnowledgeDigest",
        index_ref="knowledge://documents/test",
    )


def test_catalog_atomically_merges_metadata_without_raw_text(tmp_path: Path) -> None:
    state = tmp_path / "state"
    source = tmp_path / "Police.txt"
    first = _record(source, "a" * 64)
    store = DocumentCatalogStore(state)

    store.merge((first,))
    loaded = store.load()
    payload = json.loads((state / "folderhome-catalog.json").read_text(encoding="utf-8"))

    assert loaded == (first.to_dict(),)
    assert payload["schema"] == "folderhome.document-catalog.v1"
    assert payload["documents"] == [first.to_dict()]
    assert "text" not in payload["documents"][0]
    assert not list(state.glob("*.tmp"))


def test_catalog_merge_is_idempotent_by_document_id(tmp_path: Path) -> None:
    state = tmp_path / "state"
    source = tmp_path / "Police.txt"
    record = _record(source, "b" * 64)
    store = DocumentCatalogStore(state)

    store.merge((record,))
    store.merge((record,))

    assert len(store.load()) == 1
