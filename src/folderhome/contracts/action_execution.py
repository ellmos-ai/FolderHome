"""Hash-bound execution and undo contracts for planned document moves."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from folderhome.contracts.action_plans import PolicyActionKind
from folderhome.contracts.snapshots import PlacementReceipt

_APPROVAL_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_ACTION_ID_PATTERN = re.compile(r"act_[0-9a-f]{24}")
_EXECUTION_ID_PATTERN = re.compile(r"exec_[0-9a-f]{64}")
_PLAN_ID_PATTERN = re.compile(r"plan_[0-9a-f]{64}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class ActionExecutionApproval:
    """Explicit approval bound to one plan, source hash, and ordered actions."""

    approval_id: str
    plan_id: str
    action_ids: tuple[str, ...]
    document_sha256: str
    approved_at: str

    def __post_init__(self) -> None:
        _validate_approval_id(self.approval_id)
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss plan_<sha256> verwenden.")
        if not self.action_ids or any(
            _ACTION_ID_PATTERN.fullmatch(action_id) is None
            for action_id in self.action_ids
        ):
            raise ValueError("action_ids müssen gültige, nichtleere Aktions-IDs sein.")
        if len(self.action_ids) != len(set(self.action_ids)):
            raise ValueError("action_ids dürfen keine Duplikate enthalten.")
        _validate_sha256(self.document_sha256)
        _validate_timestamp(self.approved_at)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.action-execution-approval.v1",
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "action_ids": list(self.action_ids),
            "document_sha256": self.document_sha256,
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class ActionUndoApproval:
    """Explicit approval bound to one completed execution and content hash."""

    approval_id: str
    execution_id: str
    document_sha256: str
    approved_at: str

    def __post_init__(self) -> None:
        _validate_approval_id(self.approval_id)
        if _EXECUTION_ID_PATTERN.fullmatch(self.execution_id) is None:
            raise ValueError("execution_id muss exec_<sha256> verwenden.")
        _validate_sha256(self.document_sha256)
        _validate_timestamp(self.approved_at)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.action-undo-approval.v1",
            "approval_id": self.approval_id,
            "execution_id": self.execution_id,
            "document_sha256": self.document_sha256,
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class ExecutedActionStep:
    """One completed move with planner and actual executor provenance."""

    action_id: str
    sequence: int
    kind: PolicyActionKind
    source_path: Path
    target_path: Path
    planner_provider_id: str
    executor_id: str
    source_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        object.__setattr__(self, "target_path", self.target_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "sequence": self.sequence,
            "kind": self.kind.value,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path),
            "planner_provider_id": self.planner_provider_id,
            "executor_id": self.executor_id,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class ActionExecutionReport:
    """Completed action chain and append-only audit location, without raw text."""

    execution_id: str
    plan_id: str
    document_id: str
    document_sha256: str
    profile_id: str
    area: str
    approval: ActionExecutionApproval
    original_source: Path
    final_target: Path
    steps: tuple[ExecutedActionStep, ...]
    placement_receipt: PlacementReceipt
    created_directories: tuple[Path, ...]
    completed_file: Path
    status: str = "executed"

    SCHEMA = "folderhome.action-execution-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "original_source", self.original_source.resolve())
        object.__setattr__(self, "final_target", self.final_target.resolve())
        object.__setattr__(
            self,
            "created_directories",
            tuple(path.resolve() for path in self.created_directories),
        )
        object.__setattr__(self, "completed_file", self.completed_file.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "document_id": self.document_id,
            "document_sha256": self.document_sha256,
            "profile_id": self.profile_id,
            "area": self.area,
            "approval": self.approval.to_dict(),
            "original_source": str(self.original_source),
            "final_target": str(self.final_target),
            "steps": [step.to_dict() for step in self.steps],
            "placement_receipt": self.placement_receipt.to_dict(),
            "created_directories": [str(path) for path in self.created_directories],
            "completed_file": str(self.completed_file),
            "status": self.status,
            "undo": {
                "supported": True,
                "action": "move-final-target-back-to-original-source",
                "requires_hash": self.document_sha256,
            },
        }


@dataclass(frozen=True, slots=True)
class ActionUndoReport:
    """Completed inverse move for one exact execution report."""

    undo_id: str
    execution_id: str
    document_sha256: str
    approval: ActionUndoApproval
    source_path: Path
    restored_path: Path
    removed_directories: tuple[Path, ...]
    completed_file: Path
    status: str = "undone"

    SCHEMA = "folderhome.action-undo-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        object.__setattr__(self, "restored_path", self.restored_path.resolve())
        object.__setattr__(
            self,
            "removed_directories",
            tuple(path.resolve() for path in self.removed_directories),
        )
        object.__setattr__(self, "completed_file", self.completed_file.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "undo_id": self.undo_id,
            "execution_id": self.execution_id,
            "document_sha256": self.document_sha256,
            "approval": self.approval.to_dict(),
            "source_path": str(self.source_path),
            "restored_path": str(self.restored_path),
            "removed_directories": [str(path) for path in self.removed_directories],
            "completed_file": str(self.completed_file),
            "status": self.status,
        }


def _validate_approval_id(value: str) -> None:
    if _APPROVAL_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("approval_id muss eine stabile Kleinbuchstaben-ID sein.")


def _validate_sha256(value: str) -> None:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError("document_sha256 muss ein kleingeschriebener SHA-256 sein.")


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"approved_at ist kein ISO-Zeitpunkt: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError("approved_at benötigt eine Zeitzone.")
