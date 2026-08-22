"""Contracts for scheduled, explicitly gated folder cleanup routines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from folderhome.contracts.cleanup import (
    FolderCleanupExecutionReport,
    FolderCleanupPlan,
)
from folderhome.contracts.observations import DirectoryScanReport


class FolderRoutineMode(StrEnum):
    """Selection mode for one observed-folder routine."""

    CHANGES = "changes"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class FolderRoutinePlan:
    """Read-only composition of one scan and one filtered cleanup plan."""

    routine_id: str
    mode: FolderRoutineMode
    status: str
    reason: str
    scan_report: DirectoryScanReport
    eligible_relative_paths: tuple[str, ...]
    cleanup_plan: FolderCleanupPlan
    approval_required: bool

    SCHEMA = "folderhome.folder-routine-plan.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "routine_id": self.routine_id,
            "mode": self.mode.value,
            "status": self.status,
            "reason": self.reason,
            "scan_report": self.scan_report.to_dict(),
            "eligible_relative_paths": list(self.eligible_relative_paths),
            "cleanup_plan": self.cleanup_plan.to_dict(),
            "approval_required": self.approval_required,
        }


@dataclass(frozen=True, slots=True)
class FolderRoutineExecutionReport:
    """Result of one cleanup batch followed by one immutable checkpoint."""

    routine_execution_id: str
    routine_id: str
    cleanup_report: FolderCleanupExecutionReport
    checkpoint_report: DirectoryScanReport | None
    completed_file: Path
    status: str
    error: str | None = None

    SCHEMA = "folderhome.folder-routine-execution-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "completed_file", self.completed_file.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "routine_execution_id": self.routine_execution_id,
            "routine_id": self.routine_id,
            "cleanup_report": self.cleanup_report.to_dict(),
            "checkpoint_report": (
                self.checkpoint_report.to_dict() if self.checkpoint_report else None
            ),
            "completed_file": str(self.completed_file),
            "status": self.status,
            "error": self.error,
        }
