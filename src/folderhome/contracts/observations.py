"""Contracts for declarative watched folders and read-only scan reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from folderhome.contracts.snapshots import (
    DirectoryDiff,
    DirectoryLearningExample,
    DirectorySnapshot,
)

if TYPE_CHECKING:
    from folderhome.contracts import GateDecision


@dataclass(frozen=True, slots=True)
class WatchedFolder:
    """One explicitly configured local folder observation target."""

    watch_id: str
    source_root: Path
    profile_id: str
    area: str
    interval_minutes: int
    recursive: bool
    enabled: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "watch_id": self.watch_id,
            "source_root": str(self.source_root),
            "profile_id": self.profile_id,
            "area": self.area,
            "interval_minutes": self.interval_minutes,
            "recursive": self.recursive,
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class DirectoryScanReport:
    """One scan result; the only optional write is its immutable checkpoint."""

    scan_id: str
    watch: WatchedFolder
    snapshot: DirectorySnapshot
    previous_snapshot_id: str | None
    diff: DirectoryDiff | None
    learning_examples: tuple[DirectoryLearningExample, ...]
    interval_due: bool
    elapsed_minutes: int | None
    gate: GateDecision
    checkpoint_file: Path | None

    SCHEMA = "folderhome.directory-scan-report.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "scan_id": self.scan_id,
            "watch": self.watch.to_dict(),
            "snapshot": self.snapshot.to_dict(),
            "previous_snapshot_id": self.previous_snapshot_id,
            "diff": self.diff.to_dict() if self.diff else None,
            "learning_examples": [
                example.to_dict() for example in self.learning_examples
            ],
            "automatic_promotion": False,
            "interval_due": self.interval_due,
            "elapsed_minutes": self.elapsed_minutes,
            "gate": self.gate.to_dict(),
            "checkpoint_file": (
                str(self.checkpoint_file) if self.checkpoint_file else None
            ),
        }
