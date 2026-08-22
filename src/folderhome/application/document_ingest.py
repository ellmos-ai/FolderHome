"""Folder-level document ingest orchestration across reusable providers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestBridgeError
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import DocumentRecord, IndexStatus


class FolderIngestGateError(PermissionError):
    """Raised before the local index is written without explicit approval."""


class FolderIngestResourceError(RuntimeError):
    """Raised before folder work can exceed its finite resource policy."""


class IngestItemStatus(StrEnum):
    """Outcome for one source file in a folder ingest."""

    INDEXED = "indexed"
    SKIPPED = "skipped"
    FAILED = "failed"


class DocumentExtractor(Protocol):
    """Read-only extraction port."""

    def extract(self, source_path: Path) -> DocumentRecord: ...


class DocumentIndexer(Protocol):
    """Local index write port."""

    def index(self, document: DocumentRecord) -> DocumentRecord: ...


@dataclass(frozen=True, slots=True)
class FolderIngestItem:
    """One deterministic folder-ingest outcome."""

    relative_path: str
    status: IngestItemStatus
    document: DocumentRecord | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status.value,
            "document": self.document.to_dict() if self.document else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderIngestResult:
    """Aggregate result without embedding extracted document text."""

    source_dir: Path
    recursive: bool
    items: tuple[FolderIngestItem, ...]

    @property
    def total_files(self) -> int:
        return len(self.items)

    @property
    def indexed(self) -> int:
        return sum(item.status is IngestItemStatus.INDEXED for item in self.items)

    @property
    def skipped(self) -> int:
        return sum(item.status is IngestItemStatus.SKIPPED for item in self.items)

    @property
    def failed(self) -> int:
        return sum(item.status is IngestItemStatus.FAILED for item in self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.folder-ingest.v1",
            "source_dir": str(self.source_dir),
            "recursive": self.recursive,
            "total_files": self.total_files,
            "indexed": self.indexed,
            "skipped": self.skipped,
            "failed": self.failed,
            "items": [item.to_dict() for item in self.items],
        }


def ingest_folder(
    source_dir: Path,
    *,
    extractor: DocumentExtractor,
    indexer: DocumentIndexer,
    allow_index_write: bool,
    recursive: bool = True,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderIngestResult:
    """Extract and index folder files only after an explicit local-write gate."""

    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        raise ValueError(f"Dokumentenordner fehlt: {source_dir}")
    if not allow_index_write:
        raise FolderIngestGateError(
            "Die lokale Index-Schreibfreigabe fehlt; es wurden keine Dokumente verarbeitet."
        )

    try:
        inventory = inventory_files(
            source_dir,
            recursive=recursive,
            policy=resource_policy,
        )
    except ResourceLimitExceeded as exc:
        raise FolderIngestResourceError(str(exc)) from exc
    files = sorted(
        (*inventory.files, *inventory.symlinks),
        key=lambda path: (
            path.relative_to(source_dir).as_posix().casefold(),
            path.relative_to(source_dir).as_posix(),
        ),
    )
    items: list[FolderIngestItem] = []
    text_budget = ResourceBudget(resource_policy)
    for source_path in files:
        relative_path = source_path.relative_to(source_dir).as_posix()
        if source_path.is_symlink():
            items.append(
                FolderIngestItem(
                    relative_path=relative_path,
                    status=IngestItemStatus.SKIPPED,
                    document=None,
                    message="Symbolischer Link wurde nicht verarbeitet.",
                )
            )
            continue
        try:
            extracted = extractor.extract(source_path)
        except UnsupportedDocumentError as exc:
            items.append(
                FolderIngestItem(
                    relative_path=relative_path,
                    status=IngestItemStatus.SKIPPED,
                    document=None,
                    message=str(exc),
                )
            )
            continue
        except DocServicesBridgeError as exc:
            items.append(
                FolderIngestItem(
                    relative_path=relative_path,
                    status=IngestItemStatus.FAILED,
                    document=None,
                    message=str(exc),
                )
            )
            continue

        try:
            text_budget.consume_extracted_text(len(extracted.text))
        except ResourceLimitExceeded as exc:
            items.append(
                FolderIngestItem(
                    relative_path=relative_path,
                    status=IngestItemStatus.FAILED,
                    document=None,
                    message=str(exc),
                )
            )
            break

        try:
            indexed = indexer.index(extracted)
        except KnowledgeDigestBridgeError as exc:
            items.append(
                FolderIngestItem(
                    relative_path=relative_path,
                    status=IngestItemStatus.FAILED,
                    document=replace(extracted, index_status=IndexStatus.FAILED),
                    message=str(exc),
                )
            )
            continue
        items.append(
            FolderIngestItem(
                relative_path=relative_path,
                status=IngestItemStatus.INDEXED,
                document=indexed,
                message="Dokument lokal indexiert; Quelldatei blieb unverändert.",
            )
        )
    return FolderIngestResult(
        source_dir=source_dir,
        recursive=recursive,
        items=tuple(items),
    )
