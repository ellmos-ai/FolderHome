"""Create scheduler artifacts and run locked, read-only routine queues."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from contextlib import suppress
from datetime import datetime
from hashlib import sha256
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from folderhome.application.directory_observation import WatchedFolderConfiguration
from folderhome.application.folder_cleanup import CleanupDocumentExtractor
from folderhome.application.profile_rules import ProfileConfiguration
from folderhome.application.routine_queue import (
    FolderRoutineBindingConfiguration,
    build_folder_routine_queue,
)
from folderhome.contracts import SchedulerHandoffPlan, SchedulerRunReport

EXIT_IDLE = 0
EXIT_ATTENTION = 10
EXIT_BLOCKED = 20
EXIT_ALREADY_RUNNING = 30

_TASK_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{1,63}")


class SchedulerHandoffError(RuntimeError):
    """Raised when a scheduler plan or operational state cannot be trusted."""


def build_scheduler_handoff(
    *,
    task_name: str,
    interval_minutes: int,
    start_at: str,
    timezone: str,
    config_file: Path,
    bindings_file: Path,
    profiles_dir: Path,
    state_dir: Path,
    manifest_root: Path,
    doc_services_root: Path,
    python_executable: Path,
    working_directory: Path,
) -> SchedulerHandoffPlan:
    """Build portable argv and Windows XML without writing or registering them."""

    if _TASK_NAME_PATTERN.fullmatch(task_name) is None:
        raise SchedulerHandoffError(
            "task_name muss eine stabile ID aus Buchstaben, Zahlen, Punkt, "
            "Bindestrich oder Unterstrich sein."
        )
    if isinstance(interval_minutes, bool) or not 5 <= interval_minutes <= 1440:
        raise SchedulerHandoffError("interval_minutes muss zwischen 5 und 1440 liegen.")
    start = _timestamp(start_at, "start_at")
    zone = _timezone(timezone)
    if start.astimezone(zone).utcoffset() != start.utcoffset():
        raise SchedulerHandoffError(
            "start_at-Zeitzonenoffset passt nicht zur angegebenen IANA-Zeitzone."
        )
    paths = {
        "config_file": config_file.resolve(),
        "bindings_file": bindings_file.resolve(),
        "profiles_dir": profiles_dir.resolve(),
        "state_dir": state_dir.resolve(),
        "manifest_root": manifest_root.resolve(),
        "doc_services_root": doc_services_root.resolve(),
        "python_executable": python_executable.resolve(),
        "working_directory": working_directory.resolve(),
    }
    schedule_id = _schedule_id(
        task_name=task_name,
        interval_minutes=interval_minutes,
        start_at=start_at,
        timezone=timezone,
        paths=paths,
    )
    argv = _portable_argv(
        schedule_id=schedule_id,
        task_name=task_name,
        interval_minutes=interval_minutes,
        start_at=start_at,
        timezone=timezone,
        paths=paths,
    )
    xml = _windows_task_xml(
        task_name=task_name,
        interval_minutes=interval_minutes,
        start_at=start_at,
        executable=paths["python_executable"],
        working_directory=paths["working_directory"],
        argv=argv,
    )
    return SchedulerHandoffPlan(
        schedule_id=schedule_id,
        task_name=task_name,
        interval_minutes=interval_minutes,
        start_at=start_at,
        timezone=timezone,
        config_file=paths["config_file"],
        bindings_file=paths["bindings_file"],
        profiles_dir=paths["profiles_dir"],
        state_dir=paths["state_dir"],
        manifest_root=paths["manifest_root"],
        doc_services_root=paths["doc_services_root"],
        python_executable=paths["python_executable"],
        working_directory=paths["working_directory"],
        portable_argv=argv,
        windows_task_xml=xml,
    )


def run_scheduler_queue(
    plan: SchedulerHandoffPlan,
    *,
    captured_at: str,
    watches: WatchedFolderConfiguration,
    bindings: FolderRoutineBindingConfiguration,
    profiles: ProfileConfiguration,
    extractor: CleanupDocumentExtractor,
    allow_scheduler_state_write: bool,
) -> SchedulerRunReport:
    """Run one queue behind an operational lock; never act on documents."""

    if not allow_scheduler_state_write:
        raise SchedulerHandoffError(
            "Explizite State-Freigabe für Scheduler-Lock und Laufbericht fehlt."
        )
    captured = _timestamp(captured_at, "captured_at")
    state_root = _safe_state_root(plan.state_dir)
    lock_dir = state_root / "scheduler-locks" / plan.schedule_id
    run_id = _run_id(plan.schedule_id, captured_at)
    try:
        lock_dir.parent.mkdir(parents=True, exist_ok=True)
        lock_dir.mkdir(exist_ok=False)
    except FileExistsError:
        return SchedulerRunReport(
            run_id=run_id,
            schedule_id=plan.schedule_id,
            captured_at=captured_at,
            status="already_running",
            exit_code=EXIT_ALREADY_RUNNING,
            queue=None,
            completed_file=None,
            error="Schedule-spezifisches Lock existiert bereits.",
        )
    except OSError as exc:
        raise SchedulerHandoffError(
            f"Scheduler-Lock konnte nicht angelegt werden: {lock_dir}: {exc}"
        ) from exc

    owner_file = lock_dir / "owner.json"
    try:
        _write_new_json(
            owner_file,
            {
                "schema": "folderhome.scheduler-lock.v1",
                "schedule_id": plan.schedule_id,
                "run_id": run_id,
                "captured_at": captured_at,
                "process_id": os.getpid(),
            },
        )
        as_of = captured.astimezone(_timezone(plan.timezone)).date()
        queue = build_folder_routine_queue(
            watches,
            bindings,
            profiles=profiles,
            as_of=as_of,
            captured_at=captured_at,
            state_dir=state_root,
            extractor=extractor,
        )
        status, exit_code = _run_status(queue.summary)
        completed_file = (
            state_root
            / "scheduler-runs"
            / f"{_safe_timestamp(captured_at)}_{run_id}.json"
        )
        completed_file.parent.mkdir(parents=True, exist_ok=True)
        report = SchedulerRunReport(
            run_id=run_id,
            schedule_id=plan.schedule_id,
            captured_at=captured_at,
            status=status,
            exit_code=exit_code,
            queue=queue,
            completed_file=completed_file,
        )
        _write_new_json(completed_file, report.to_dict())
        return report
    except Exception as exc:
        failed_file = (
            state_root
            / "scheduler-runs"
            / f"{_safe_timestamp(captured_at)}_{run_id}_failed.json"
        )
        failed_file.parent.mkdir(parents=True, exist_ok=True)
        report = SchedulerRunReport(
            run_id=run_id,
            schedule_id=plan.schedule_id,
            captured_at=captured_at,
            status="blocked",
            exit_code=EXIT_BLOCKED,
            queue=None,
            completed_file=failed_file,
            error=str(exc),
        )
        with suppress(Exception):
            _write_new_json(failed_file, report.to_dict())
        return report
    finally:
        with suppress(OSError):
            owner_file.unlink()
        with suppress(OSError):
            lock_dir.rmdir()


def _schedule_id(
    *,
    task_name: str,
    interval_minutes: int,
    start_at: str,
    timezone: str,
    paths: dict[str, Path],
) -> str:
    payload = {
        "schema": SchedulerHandoffPlan.SCHEMA,
        "task_name": task_name,
        "interval_minutes": interval_minutes,
        "start_at": start_at,
        "timezone": timezone,
        "paths": {key: str(value) for key, value in sorted(paths.items())},
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"schedule_{sha256(material).hexdigest()}"


def _portable_argv(
    *,
    schedule_id: str,
    task_name: str,
    interval_minutes: int,
    start_at: str,
    timezone: str,
    paths: dict[str, Path],
) -> tuple[str, ...]:
    return (
        str(paths["python_executable"]),
        "-m",
        "folderhome",
        "scheduler",
        "run",
        "--schedule-id",
        schedule_id,
        "--task-name",
        task_name,
        "--interval-minutes",
        str(interval_minutes),
        "--start-at",
        start_at,
        "--timezone",
        timezone,
        "--config-file",
        str(paths["config_file"]),
        "--bindings-file",
        str(paths["bindings_file"]),
        "--profiles-dir",
        str(paths["profiles_dir"]),
        "--state-dir",
        str(paths["state_dir"]),
        "--manifest-root",
        str(paths["manifest_root"]),
        "--doc-services-root",
        str(paths["doc_services_root"]),
        "--python-executable",
        str(paths["python_executable"]),
        "--working-directory",
        str(paths["working_directory"]),
        "--captured-at",
        "auto",
        "--approve-scheduler-state-write",
        "--json",
    )


def _windows_task_xml(
    *,
    task_name: str,
    interval_minutes: int,
    start_at: str,
    executable: Path,
    working_directory: Path,
    argv: tuple[str, ...],
) -> str:
    arguments = subprocess.list2cmdline(list(argv[1:]))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Task version="1.4" '
        'xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        "  <RegistrationInfo>\n"
        f"    <Description>{escape(task_name)} "
        "(nicht registrierter FolderHome-Plan)</Description>\n"
        "  </RegistrationInfo>\n"
        "  <Principals>\n"
        "    <Principal id=\"Author\">\n"
        "      <LogonType>InteractiveToken</LogonType>\n"
        "      <RunLevel>LeastPrivilege</RunLevel>\n"
        "    </Principal>\n"
        "  </Principals>\n"
        "  <Triggers>\n"
        "    <CalendarTrigger>\n"
        f"      <StartBoundary>{escape(start_at)}</StartBoundary>\n"
        "      <Enabled>true</Enabled>\n"
        "      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>\n"
        "      <Repetition>\n"
        f"        <Interval>PT{interval_minutes}M</Interval>\n"
        "        <StopAtDurationEnd>false</StopAtDurationEnd>\n"
        "      </Repetition>\n"
        "    </CalendarTrigger>\n"
        "  </Triggers>\n"
        "  <Settings>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>\n"
        "    <Enabled>true</Enabled>\n"
        "  </Settings>\n"
        "  <Actions Context=\"Author\">\n"
        "    <Exec>\n"
        f"      <Command>{escape(str(executable))}</Command>\n"
        f"      <Arguments>{escape(arguments)}</Arguments>\n"
        f"      <WorkingDirectory>{escape(str(working_directory))}</WorkingDirectory>\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )


def _run_status(summary: dict[str, int]) -> tuple[str, int]:
    if summary.get("blocked", 0):
        return "blocked", EXIT_BLOCKED
    if summary.get("ready", 0):
        return "attention", EXIT_ATTENTION
    return "idle", EXIT_IDLE


def _run_id(schedule_id: str, captured_at: str) -> str:
    material = f"{schedule_id}\0{captured_at}"
    return f"scheduled_{sha256(material.encode('utf-8')).hexdigest()}"


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchedulerHandoffError(f"{field} ist kein ISO-Zeitpunkt: {value}") from exc
    if parsed.tzinfo is None:
        raise SchedulerHandoffError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise SchedulerHandoffError(f"Unbekannte IANA-Zeitzone: {value}") from exc


def _safe_state_root(state_dir: Path) -> Path:
    absolute = Path(os.path.abspath(state_dir))
    if absolute.is_symlink() or absolute.resolve(strict=False) != absolute:
        raise SchedulerHandoffError(
            f"State-Verzeichnis enthält einen symbolischen Link oder Alias: {absolute}"
        )
    return absolute


def _safe_timestamp(value: str) -> str:
    return value.replace(":", "-").replace("+", "_")


def _write_new_json(path: Path, payload: dict[str, object]) -> None:
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise SchedulerHandoffError(f"Scheduler-Audit existiert bereits: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)
