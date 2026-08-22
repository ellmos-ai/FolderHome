"""Deterministic folder reports built from already extracted document records."""

from __future__ import annotations

import re
from dataclasses import dataclass

from folderhome.application.document_ingest import FolderIngestResult
from folderhome.contracts import DocumentRecord, PrivacyStatus

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class FolderReportEntry:
    """Short extractive description of one document."""

    document_id: str
    relative_path: str
    filename: str
    summary: str
    privacy_status: str
    index_status: str
    source_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "relative_path": self.relative_path,
            "filename": self.filename,
            "summary": self.summary,
            "privacy_status": self.privacy_status,
            "index_status": self.index_status,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class FolderReport:
    """Structured and Markdown views of one local folder report."""

    title: str
    source_dir: str
    entries: tuple[FolderReportEntry, ...]
    unprocessed: tuple[str, ...]
    markdown: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.folder-report.v1",
            "title": self.title,
            "source_dir": self.source_dir,
            "document_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
            "unprocessed": list(self.unprocessed),
            "markdown": self.markdown,
        }


def build_folder_report(
    ingest: FolderIngestResult,
    *,
    title: str | None = None,
    sentence_limit: int = 3,
) -> FolderReport:
    """Create one report with filename and up to three source-grounded sentences."""

    if sentence_limit not in {2, 3}:
        raise ValueError("sentence_limit muss 2 oder 3 sein.")
    report_title = _one_line(title or f"Ordnerbericht: {ingest.source_dir.name}")
    entries = tuple(
        FolderReportEntry(
            document_id=item.document.document_id,
            relative_path=item.relative_path,
            filename=item.document.filename,
            summary=_summarize(item.document, sentence_limit=sentence_limit),
            privacy_status=item.document.privacy_status.value,
            index_status=item.document.index_status.value,
            source_sha256=item.document.source_sha256,
        )
        for item in ingest.items
        if item.document is not None
    )
    unprocessed = tuple(
        item.relative_path for item in ingest.items if item.document is None
    )
    markdown = _render_markdown(report_title, entries, unprocessed)
    return FolderReport(
        title=report_title,
        source_dir=str(ingest.source_dir),
        entries=entries,
        unprocessed=unprocessed,
        markdown=markdown,
    )


def _summarize(document: DocumentRecord, *, sentence_limit: int) -> str:
    if document.privacy_status is not PrivacyStatus.CLEAR:
        return (
            "Der Inhalt wird wegen des Datenschutzstatus nicht automatisch in den "
            "Ordnerbericht übernommen. Bitte prüfe das Dokument lokal."
        )
    normalized = _WHITESPACE.sub(" ", document.text).strip()
    if not normalized:
        return "Das Dokument enthält keinen extrahierbaren Text."
    sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip()]
    return " ".join(sentences[:sentence_limit])


def _render_markdown(
    title: str,
    entries: tuple[FolderReportEntry, ...],
    unprocessed: tuple[str, ...],
) -> str:
    lines = [
        f"# {title}",
        "",
        "> Lokal und extraktiv erzeugt: Aussagen stammen aus den erfassten Dokumenten.",
        "",
        "## Dokumente",
        "",
    ]
    if not entries:
        lines.append("Keine Dokumente konnten in den Bericht aufgenommen werden.")
    for entry in entries:
        lines.extend(
            (
                f"### {_one_line(entry.filename)}",
                "",
                entry.summary,
                "",
                f"- Quelle: `{entry.relative_path}`",
                f"- Indexstatus: `{entry.index_status}`",
                "",
            )
        )
    if unprocessed:
        lines.extend(("## Nicht verarbeitet", ""))
        lines.extend(f"- `{path}`" for path in unprocessed)
    return "\n".join(lines).rstrip() + "\n"


def _one_line(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()
