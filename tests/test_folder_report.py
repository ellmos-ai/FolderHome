from __future__ import annotations

from pathlib import Path

from folderhome.application.document_ingest import (
    FolderIngestItem,
    FolderIngestResult,
    IngestItemStatus,
)
from folderhome.application.folder_report import build_folder_report
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


def _record(
    source: Path,
    *,
    text: str,
    privacy_status: PrivacyStatus = PrivacyStatus.CLEAR,
) -> DocumentRecord:
    source.write_text(text, encoding="utf-8")
    source_hash = "a" * 64
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at="2026-08-21T18:00:00Z",
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=privacy_status,
        privacy_summary="Synthetischer Datenschutzstatus.",
        index_status=IndexStatus.INDEXED,
        index_provider="KnowledgeDigest",
        index_ref="knowledge://documents/test",
    )


def test_folder_report_lists_document_name_and_three_source_sentences(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    record = _record(
        inbox / "Versicherung.txt",
        text=(
            "Die Police ist rein synthetisch. Sie betrifft einen Hyundai i10. "
            "Der Beitrag wird jährlich bezahlt. Ein vierter Satz bleibt außerhalb."
        ),
    )
    ingest = FolderIngestResult(
        source_dir=inbox,
        recursive=True,
        items=(
            FolderIngestItem(
                relative_path="Versicherung.txt",
                status=IngestItemStatus.INDEXED,
                document=record,
                message="indexiert",
            ),
        ),
    )

    report = build_folder_report(ingest, title="Versicherungsordner")

    assert report.entries[0].filename == "Versicherung.txt"
    assert report.entries[0].summary.count(".") == 3
    assert "Ein vierter Satz" not in report.entries[0].summary
    assert "# Versicherungsordner" in report.markdown
    assert "### Versicherung.txt" in report.markdown
    assert report.entries[0].summary in report.markdown


def test_folder_report_does_not_copy_blocked_document_content(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    secret = "IBAN DE89 3704 0044 0532 0130 00"
    record = _record(
        inbox / "Zahlung.txt",
        text=f"Synthetische Testangabe {secret}.",
        privacy_status=PrivacyStatus.BLOCKED,
    )
    ingest = FolderIngestResult(
        source_dir=inbox,
        recursive=False,
        items=(
            FolderIngestItem(
                relative_path="Zahlung.txt",
                status=IngestItemStatus.INDEXED,
                document=record,
                message="indexiert",
            ),
        ),
    )

    report = build_folder_report(ingest)

    assert secret not in report.markdown
    assert "Datenschutzstatus" in report.entries[0].summary
    assert "text" not in report.to_dict()["entries"][0]
