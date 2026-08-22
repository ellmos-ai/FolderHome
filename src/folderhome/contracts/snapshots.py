"""Content-free directory snapshots, diffs, and correction-learning contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DirectoryChangeKind(StrEnum):
    """Observable filesystem changes between two explicit snapshots."""

    ADDED = "added"
    METADATA_CHANGED = "metadata_changed"
    MODIFIED = "modified"
    MOVED = "moved"
    REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class DirectoryFileState:
    """One file's identity metadata without filename-derived content claims."""

    relative_path: str
    source_sha256: str
    size_bytes: int
    mtime_ns: int

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "size_bytes": self.size_bytes,
            "mtime_ns": self.mtime_ns,
        }


@dataclass(frozen=True, slots=True)
class DirectorySnapshot:
    """Deterministic inventory at one caller-supplied observation time."""

    snapshot_id: str
    source_root: Path
    captured_at: str
    recursive: bool
    files: tuple[DirectoryFileState, ...]
    skipped_symlinks: tuple[str, ...]

    SCHEMA = "folderhome.directory-snapshot.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "snapshot_id": self.snapshot_id,
            "source_root": str(self.source_root),
            "captured_at": self.captured_at,
            "recursive": self.recursive,
            "files": [entry.to_dict() for entry in self.files],
            "skipped_symlinks": list(self.skipped_symlinks),
        }


@dataclass(frozen=True, slots=True)
class DirectoryChange:
    """One explainable path/hash change; move claims require an unambiguous hash."""

    kind: DirectoryChangeKind
    before_path: str | None
    after_path: str | None
    before_sha256: str | None
    after_sha256: str | None
    confidence: str
    evidence: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "before_path": self.before_path,
            "after_path": self.after_path,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class DirectoryDiff:
    """Ordered comparison between two snapshots of the same root."""

    before_snapshot_id: str
    after_snapshot_id: str
    before_captured_at: str
    after_captured_at: str
    changes: tuple[DirectoryChange, ...]

    SCHEMA = "folderhome.directory-diff.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "before_snapshot_id": self.before_snapshot_id,
            "after_snapshot_id": self.after_snapshot_id,
            "before_captured_at": self.before_captured_at,
            "after_captured_at": self.after_captured_at,
            "changes": [change.to_dict() for change in self.changes],
        }


@dataclass(frozen=True, slots=True)
class PlacementReceipt:
    """Prior placement evidence needed before a later move counts as correction."""

    receipt_id: str
    document_sha256: str
    placed_path: str
    profile_id: str
    area: str
    source_rule_ids: tuple[str, ...]
    root_path: Path | None = None

    def __post_init__(self) -> None:
        if self.root_path is not None:
            object.__setattr__(self, "root_path", self.root_path.resolve())
            relative = Path(self.placed_path)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(
                    "placed_path muss relativ zum deklarierten root_path sein."
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.placement-receipt.v1",
            "receipt_id": self.receipt_id,
            "document_sha256": self.document_sha256,
            "placed_path": self.placed_path,
            "profile_id": self.profile_id,
            "area": self.area,
            "source_rule_ids": list(self.source_rule_ids),
            "root_path": str(self.root_path) if self.root_path else None,
        }


@dataclass(frozen=True, slots=True)
class DirectoryLearningExample:
    """Candidate preference example; never an automatically promoted rule."""

    example_id: str
    receipt_id: str
    document_sha256: str
    placed_path: str
    corrected_path: str
    profile_id: str
    area: str
    source_rule_ids: tuple[str, ...]
    observed_at: str
    status: str = "candidate"
    automatic_promotion: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.directory-learning-example.v1",
            "example_id": self.example_id,
            "receipt_id": self.receipt_id,
            "document_sha256": self.document_sha256,
            "placed_path": self.placed_path,
            "corrected_path": self.corrected_path,
            "profile_id": self.profile_id,
            "area": self.area,
            "source_rule_ids": list(self.source_rule_ids),
            "observed_at": self.observed_at,
            "status": self.status,
            "automatic_promotion": self.automatic_promotion,
        }
