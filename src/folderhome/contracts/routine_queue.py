"""Contracts for read-only multi-watch routine queues."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from folderhome.contracts.routines import FolderRoutineMode, FolderRoutinePlan


@dataclass(frozen=True, slots=True)
class FolderRoutineBinding:
    """Declarative target and mode for one existing watched folder."""

    binding_id: str
    watch_id: str
    target_root: Path
    mode: FolderRoutineMode
    enabled: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_root", self.target_root.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "watch_id": self.watch_id,
            "target_root": str(self.target_root),
            "mode": self.mode.value,
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class FolderRoutineQueueItem:
    """One active watch's planning outcome in a scheduler-neutral queue."""

    watch_id: str
    binding_id: str | None
    target_root: Path | None
    mode: FolderRoutineMode | None
    status: str
    reason: str
    plan: FolderRoutinePlan | None

    def __post_init__(self) -> None:
        if self.target_root is not None:
            object.__setattr__(self, "target_root", self.target_root.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "watch_id": self.watch_id,
            "binding_id": self.binding_id,
            "target_root": str(self.target_root) if self.target_root else None,
            "mode": self.mode.value if self.mode else None,
            "status": self.status,
            "reason": self.reason,
            "plan": self.plan.to_dict() if self.plan else None,
        }


@dataclass(frozen=True, slots=True)
class FolderRoutineQueue:
    """Deterministic read-only result for all active watched folders."""

    queue_id: str
    captured_at: str
    as_of: str
    items: tuple[FolderRoutineQueueItem, ...]

    SCHEMA = "folderhome.folder-routine-queue.v1"

    @property
    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.status] = counts.get(item.status, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "queue_id": self.queue_id,
            "captured_at": self.captured_at,
            "as_of": self.as_of,
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "side_effects": [],
            "scheduler_registered": False,
        }
