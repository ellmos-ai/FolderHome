"""Contracts for deterministic folder-wide cleanup planning and execution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from folderhome.contracts.action_execution import ActionExecutionReport
from folderhome.contracts.action_plans import DocumentPolicyActionPlan
from folderhome.contracts.snapshots import PlacementReceipt

_ACTION_ID_PATTERN = re.compile(r"act_[0-9a-f]{24}")
_APPROVAL_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_BATCH_ID_PATTERN = re.compile(r"cleanup_[0-9a-f]{64}")
_DOCUMENT_ID_PATTERN = re.compile(r"doc_[0-9a-f]{64}")
_PLAN_ID_PATTERN = re.compile(r"plan_[0-9a-f]{64}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class CleanupConflict:
    """One cross-document ambiguity that blocks every referenced item."""

    conflict_id: str
    kind: str
    document_ids: tuple[str, ...]
    paths: tuple[Path, ...]
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "paths", tuple(path.resolve() for path in self.paths))

    def to_dict(self) -> dict[str, object]:
        return {
            "conflict_id": self.conflict_id,
            "kind": self.kind,
            "document_ids": list(self.document_ids),
            "paths": [str(path) for path in self.paths],
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderCleanupItem:
    """One folder source and its content-free per-document planning outcome."""

    relative_path: str
    source_path: Path
    source_sha256: str
    document_id: str | None
    status: str
    action_plan: DocumentPolicyActionPlan | None
    executable_action_ids: tuple[str, ...]
    conflict_ids: tuple[str, ...]
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "document_id": self.document_id,
            "status": self.status,
            "action_plan": self.action_plan.to_dict() if self.action_plan else None,
            "executable_action_ids": list(self.executable_action_ids),
            "conflict_ids": list(self.conflict_ids),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderCleanupPlan:
    """Whole-folder plan with deterministic identity and global conflicts."""

    batch_id: str
    source_root: Path
    target_root: Path
    profile_id: str
    area: str
    as_of: str
    recursive: bool
    items: tuple[FolderCleanupItem, ...]
    conflicts: tuple[CleanupConflict, ...]

    SCHEMA = "folderhome.folder-cleanup-plan.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())
        object.__setattr__(self, "target_root", self.target_root.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "batch_id": self.batch_id,
            "source_root": str(self.source_root),
            "target_root": str(self.target_root),
            "profile_id": self.profile_id,
            "area": self.area,
            "as_of": self.as_of,
            "recursive": self.recursive,
            "items": [item.to_dict() for item in self.items],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


@dataclass(frozen=True, slots=True)
class BatchItemApproval:
    """Selective approval for one exact item plan and executable action prefix."""

    document_id: str
    plan_id: str
    document_sha256: str
    action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if _DOCUMENT_ID_PATTERN.fullmatch(self.document_id) is None:
            raise ValueError("document_id muss doc_<sha256> verwenden.")
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss plan_<sha256> verwenden.")
        if _SHA256_PATTERN.fullmatch(self.document_sha256) is None:
            raise ValueError("document_sha256 muss ein kleingeschriebener SHA-256 sein.")
        if not self.action_ids or any(
            _ACTION_ID_PATTERN.fullmatch(action_id) is None
            for action_id in self.action_ids
        ):
            raise ValueError("action_ids müssen gültige, nichtleere Aktions-IDs sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "plan_id": self.plan_id,
            "document_sha256": self.document_sha256,
            "action_ids": list(self.action_ids),
        }


@dataclass(frozen=True, slots=True)
class FolderCleanupApproval:
    """Explicit selective approval for one exact whole-folder batch plan."""

    approval_id: str
    batch_id: str
    items: tuple[BatchItemApproval, ...]
    approved_at: str

    def __post_init__(self) -> None:
        if _APPROVAL_ID_PATTERN.fullmatch(self.approval_id) is None:
            raise ValueError("approval_id muss eine stabile Kleinbuchstaben-ID sein.")
        if _BATCH_ID_PATTERN.fullmatch(self.batch_id) is None:
            raise ValueError("batch_id muss cleanup_<sha256> verwenden.")
        if not self.items:
            raise ValueError("Eine Batchfreigabe benötigt mindestens ein Dokument.")
        document_ids = [item.document_id for item in self.items]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("Eine Batchfreigabe darf Dokumente nicht doppelt nennen.")
        try:
            timestamp = datetime.fromisoformat(self.approved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                f"approved_at ist kein ISO-Zeitpunkt: {self.approved_at}"
            ) from exc
        if timestamp.tzinfo is None:
            raise ValueError("approved_at benötigt eine Zeitzone.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.folder-cleanup-approval.v1",
            "approval_id": self.approval_id,
            "batch_id": self.batch_id,
            "items": [item.to_dict() for item in self.items],
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class FolderCleanupExecutionReport:
    """Batch outcome with per-document execution reports and receipts."""

    batch_execution_id: str
    batch_id: str
    approval: FolderCleanupApproval
    executions: tuple[ActionExecutionReport, ...]
    placement_receipts: tuple[PlacementReceipt, ...]
    completed_file: Path
    status: str
    error: str | None = None

    SCHEMA = "folderhome.folder-cleanup-execution-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "completed_file", self.completed_file.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "batch_execution_id": self.batch_execution_id,
            "batch_id": self.batch_id,
            "approval": self.approval.to_dict(),
            "executions": [execution.to_dict() for execution in self.executions],
            "placement_receipts": [
                receipt.to_dict() for receipt in self.placement_receipts
            ],
            "completed_file": str(self.completed_file),
            "status": self.status,
            "error": self.error,
        }
