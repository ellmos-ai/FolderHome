from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from folderhome.contracts.documents import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


def test_document_id_is_deterministic_for_source_and_content(tmp_path: Path) -> None:
    source = tmp_path / "Bericht.txt"
    source.write_text("Synthetischer Inhalt", encoding="utf-8")
    content_hash = "a" * 64

    first = build_document_id(source, content_hash)
    second = build_document_id(source.resolve(), content_hash)

    assert first == second
    assert first.startswith("doc_")
    assert len(first) == 4 + 64


def test_document_record_hides_text_from_default_serialization(tmp_path: Path) -> None:
    source = tmp_path / "Arztbericht.txt"
    source.write_text("Nur synthetische Testdaten.", encoding="utf-8")
    record = DocumentRecord(
        document_id=build_document_id(source, "b" * 64),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256="b" * 64,
        size_bytes=source.stat().st_size,
        modified_at="2026-08-21T18:00:00Z",
        text="Nur synthetische Testdaten.",
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="Keine sensiblen Muster erkannt.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )

    public_payload = record.to_dict()
    private_payload = record.to_dict(include_text=True)

    assert "text" not in public_payload
    assert private_payload["text"] == "Nur synthetische Testdaten."
    assert public_payload["source_path"] == str(source.resolve())
    assert public_payload["privacy"]["status"] == "clear"
    assert public_payload["index"]["status"] == "not_indexed"


def test_document_record_is_immutable_but_supports_explicit_index_transition(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Notiz.md"
    record = DocumentRecord(
        document_id=build_document_id(source, "c" * 64),
        source_path=source,
        filename=source.name,
        media_type="text/markdown",
        source_sha256="c" * 64,
        size_bytes=10,
        modified_at="2026-08-21T18:00:00Z",
        text="# Notiz",
        content_format=ContentFormat.MARKDOWN,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="Keine sensiblen Muster erkannt.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )

    with pytest.raises(FrozenInstanceError):
        record.index_status = IndexStatus.INDEXED  # type: ignore[misc]

    indexed = replace(
        record,
        index_status=IndexStatus.INDEXED,
        index_provider="KnowledgeDigest",
        index_ref="knowledge://documents/7",
    )
    assert record.index_status is IndexStatus.NOT_INDEXED
    assert indexed.index_status is IndexStatus.INDEXED


@pytest.mark.parametrize("bad_hash", ["", "abc", "g" * 64, "a" * 63])
def test_document_contract_rejects_invalid_sha256(tmp_path: Path, bad_hash: str) -> None:
    source = tmp_path / "bad.txt"

    with pytest.raises(ValueError, match="source_sha256"):
        DocumentRecord(
            document_id="doc_" + "a" * 64,
            source_path=source,
            filename=source.name,
            media_type="text/plain",
            source_sha256=bad_hash,
            size_bytes=0,
            modified_at="2026-08-21T18:00:00Z",
            text="",
            content_format=ContentFormat.TEXT,
            extraction_provider="doc-services",
            extraction_method="direct",
            privacy_status=PrivacyStatus.NOT_CHECKED,
            privacy_summary="Noch nicht geprüft.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def test_indexed_status_requires_provider_and_reference(tmp_path: Path) -> None:
    source = tmp_path / "bad-index.txt"

    with pytest.raises(ValueError, match="index_provider.*index_ref"):
        DocumentRecord(
            document_id="doc_" + "d" * 64,
            source_path=source,
            filename=source.name,
            media_type="text/plain",
            source_sha256="d" * 64,
            size_bytes=0,
            modified_at="2026-08-21T18:00:00Z",
            text="",
            content_format=ContentFormat.TEXT,
            extraction_provider="doc-services",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Keine sensiblen Muster erkannt.",
            index_status=IndexStatus.INDEXED,
            index_provider=None,
            index_ref=None,
        )
