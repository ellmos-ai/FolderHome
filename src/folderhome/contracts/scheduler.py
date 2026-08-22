"""Contracts for portable, installation-free scheduler handoffs and runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from folderhome.contracts.routine_queue import FolderRoutineQueue


@dataclass(frozen=True, slots=True)
class SchedulerHandoffPlan:
    """One deterministic scheduler definition that performs no registration."""

    schedule_id: str
    task_name: str
    interval_minutes: int
    start_at: str
    timezone: str
    config_file: Path
    bindings_file: Path
    profiles_dir: Path
    state_dir: Path
    manifest_root: Path
    doc_services_root: Path
    python_executable: Path
    working_directory: Path
    portable_argv: tuple[str, ...]
    windows_task_xml: str

    SCHEMA = "folderhome.scheduler-handoff-plan.v1"

    def __post_init__(self) -> None:
        for field in (
            "config_file",
            "bindings_file",
            "profiles_dir",
            "state_dir",
            "manifest_root",
            "doc_services_root",
            "python_executable",
            "working_directory",
        ):
            object.__setattr__(self, field, getattr(self, field).resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "schedule_id": self.schedule_id,
            "task_name": self.task_name,
            "interval_minutes": self.interval_minutes,
            "start_at": self.start_at,
            "timezone": self.timezone,
            "config_file": str(self.config_file),
            "bindings_file": str(self.bindings_file),
            "profiles_dir": str(self.profiles_dir),
            "state_dir": str(self.state_dir),
            "manifest_root": str(self.manifest_root),
            "doc_services_root": str(self.doc_services_root),
            "python_executable": str(self.python_executable),
            "working_directory": str(self.working_directory),
            "portable_argv": list(self.portable_argv),
            "windows_task_xml": self.windows_task_xml,
            "installation_supported": False,
            "registration_performed": False,
            "side_effects": [],
        }


@dataclass(frozen=True, slots=True)
class SchedulerRunReport:
    """Audited result of one headless read-only routine-queue invocation."""

    run_id: str
    schedule_id: str
    captured_at: str
    status: str
    exit_code: int
    queue: FolderRoutineQueue | None
    completed_file: Path | None
    error: str | None = None

    SCHEMA = "folderhome.scheduler-run-report.v1"

    def __post_init__(self) -> None:
        if self.completed_file is not None:
            object.__setattr__(self, "completed_file", self.completed_file.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "schedule_id": self.schedule_id,
            "captured_at": self.captured_at,
            "status": self.status,
            "exit_code": self.exit_code,
            "queue": self.queue.to_dict() if self.queue else None,
            "completed_file": str(self.completed_file) if self.completed_file else None,
            "error": self.error,
            "document_side_effects": [],
            "checkpoint_written": False,
            "scheduler_registered": False,
        }
