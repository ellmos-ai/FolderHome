from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.application.document_versions import (
    build_archive_proposals,
    build_document_family,
    compare_document_versions,
)
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    VersionDateBasis,
    VersionDateConfidence,
    build_document_id,
)


def _record(
    source: Path,
    *,
    text: str,
    source_hash: str,
    modified_at: str,
    privacy_status: PrivacyStatus = PrivacyStatus.CLEAR,
) -> DocumentRecord:
    source.write_text(text, encoding="utf-8")
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at=modified_at,
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=privacy_status,
        privacy_summary="Synthetischer Datenschutzstatus.",
        index_status=IndexStatus.INDEXED,
        index_provider="KnowledgeDigest",
        index_ref=f"knowledge://documents/{source_hash}",
    )


def test_document_family_prefers_explicit_valid_from_date_over_file_mtime(
    tmp_path: Path,
) -> None:
    old = _record(
        tmp_path / "KFZ_Hyundai_i10_2025-01-01.txt",
        text="Gültig ab 01.01.2025. Der synthetische Beitrag beträgt 400 Euro.",
        source_hash="a" * 64,
        modified_at="2026-08-20T12:00:00Z",
    )
    new = _record(
        tmp_path / "KFZ_Hyundai_i10_2026-01-01.txt",
        text="Gültig ab 01.01.2026. Der synthetische Beitrag beträgt 420 Euro.",
        source_hash="b" * 64,
        modified_at="2026-01-02T12:00:00Z",
    )

    family = build_document_family("KFZ-Versicherung Hyundai i10", (old, new))

    assert family.latest.document.document_id == new.document_id
    assert family.latest.version_date == "2026-01-01"
    assert family.latest.date_basis is VersionDateBasis.DOCUMENT_TEXT
    assert family.latest.date_confidence is VersionDateConfidence.HIGH
    assert [version.document.filename for version in family.versions] == [
        new.filename,
        old.filename,
    ]
    assert "text" not in family.to_dict()["versions"][0]["document"]


def test_version_comparison_and_archive_proposal_are_explainable_and_non_executing(
    tmp_path: Path,
) -> None:
    old = _record(
        tmp_path / "KFZ_Hyundai_i10_2025.txt",
        text="Gültig ab 01.01.2025. Der synthetische Beitrag beträgt 400 Euro.",
        source_hash="c" * 64,
        modified_at="2025-01-02T12:00:00Z",
    )
    new = _record(
        tmp_path / "KFZ_Hyundai_i10_2026.txt",
        text="Gültig ab 01.01.2026. Der synthetische Beitrag beträgt 420 Euro.",
        source_hash="d" * 64,
        modified_at="2026-01-02T12:00:00Z",
    )
    family = build_document_family("KFZ-Versicherung Hyundai i10", (old, new))

    comparison = compare_document_versions(family.versions[1], family.versions[0])
    proposals = build_archive_proposals(family)

    assert any("400 Euro" in sentence for sentence in comparison.removed_sentences)
    assert any("420 Euro" in sentence for sentence in comparison.added_sentences)
    assert len(proposals) == 1
    assert proposals[0].source_path == old.source_path
    assert proposals[0].target_path == old.source_path.parent / "Archiv" / old.filename
    assert proposals[0].provider_id == "file-collect-sort-action"
    assert proposals[0].action == "move"
    assert proposals[0].status == "planned"
    assert proposals[0].gate_required is True
    assert proposals[0].gate_granted is False
    assert old.source_path.exists()


def test_sensitive_versions_are_not_compared(tmp_path: Path) -> None:
    old = _record(
        tmp_path / "Alt.txt",
        text="Gültig ab 01.01.2025. IBAN DE89 3704 0044 0532 0130 00.",
        source_hash="e" * 64,
        modified_at="2025-01-02T12:00:00Z",
        privacy_status=PrivacyStatus.BLOCKED,
    )
    new = _record(
        tmp_path / "Neu.txt",
        text="Gültig ab 01.01.2026. Synthetisch.",
        source_hash="f" * 64,
        modified_at="2026-01-02T12:00:00Z",
    )
    family = build_document_family("Testvertrag", (old, new))

    with pytest.raises(PermissionError, match="Datenschutzstatus"):
        compare_document_versions(family.versions[1], family.versions[0])
