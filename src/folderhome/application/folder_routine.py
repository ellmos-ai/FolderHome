"""Compose watched-folder scans with gated whole-folder cleanup runs."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path

from folderhome.application.directory_observation import (
    DirectoryObservationError,
    run_directory_scan,
)
from folderhome.application.document_action_execution import undo_document_actions
from folderhome.application.folder_cleanup import (
    CleanupDocumentExtractor,
    FolderCleanupError,
    build_folder_cleanup_plan,
    execute_folder_cleanup,
    validate_folder_cleanup_execution,
)
from folderhome.contracts import (
    ActionUndoApproval,
    DirectoryChangeKind,
    FolderCleanupApproval,
    FolderRoutineExecutionReport,
    FolderRoutineMode,
    FolderRoutinePlan,
    ResolvedProfilePolicy,
    WatchedFolder,
)


class FolderRoutineError(RuntimeError):
    """Raised when a routine cannot be planned or completed safely."""


def build_folder_routine_plan(
    watch: WatchedFolder,
    *,
    policy: ResolvedProfilePolicy,
    target_root: Path,
    as_of: date,
    captured_at: str,
    state_dir: Path,
    extractor: CleanupDocumentExtractor,
    mode: FolderRoutineMode = FolderRoutineMode.CHANGES,
) -> FolderRoutinePlan:
    """Build a deterministic, entirely read-only observed-folder routine."""

    _validate_watch_policy(watch, policy)
    target = target_root.resolve()
    if _is_within(target, watch.source_root):
        raise FolderRoutineError(
            "Der Routinen-Zielordner muss außerhalb des beobachteten Ordners liegen."
        )
    try:
        scan = run_directory_scan(
            watch,
            captured_at=captured_at,
            state_dir=state_dir,
            allow_state_write=False,
        )
    except DirectoryObservationError as exc:
        raise FolderRoutineError(str(exc)) from exc
    eligible, status, reason = _eligible_paths(scan, mode)
    try:
        cleanup = build_folder_cleanup_plan(
            watch.source_root,
            policy=policy,
            target_root=target,
            as_of=as_of,
            extractor=extractor,
            recursive=watch.recursive,
            include_relative_paths=frozenset(eligible),
        )
    except FolderCleanupError as exc:
        raise FolderRoutineError(str(exc)) from exc
    approval_required = any(item.status == "planned" for item in cleanup.items)
    routine_id = _routine_id(mode, scan.scan_id, cleanup.batch_id, status, eligible)
    return FolderRoutinePlan(
        routine_id=routine_id,
        mode=mode,
        status=status,
        reason=reason,
        scan_report=scan,
        eligible_relative_paths=eligible,
        cleanup_plan=cleanup,
        approval_required=approval_required,
    )


def execute_folder_routine(
    plan: FolderRoutinePlan,
    approval: FolderCleanupApproval,
    *,
    completed_at: str,
    state_dir: Path,
    allow_file_write: bool,
    allow_state_write: bool,
) -> FolderRoutineExecutionReport:
    """Execute one approved batch, then checkpoint the resulting watched folder."""

    if not allow_file_write or not allow_state_write:
        raise FolderRoutineError(
            "Datei- und State-Freigaben werden für die Routine gemeinsam benötigt."
        )
    if plan.status != "planned" or not plan.approval_required:
        raise FolderRoutineError("Der Routinenplan enthält keinen freigabefähigen Batch.")
    if _timestamp(completed_at) <= _timestamp(plan.scan_report.snapshot.captured_at):
        raise FolderRoutineError(
            "completed_at muss später als der beobachtete Planzeitpunkt sein."
        )
    try:
        validate_folder_cleanup_execution(plan.cleanup_plan, approval)
        current = run_directory_scan(
            plan.scan_report.watch,
            captured_at=plan.scan_report.snapshot.captured_at,
            state_dir=state_dir,
            allow_state_write=False,
            expected_previous_snapshot_id=plan.scan_report.previous_snapshot_id,
        )
    except (DirectoryObservationError, FolderCleanupError) as exc:
        raise FolderRoutineError(str(exc)) from exc
    if current.scan_id != plan.scan_report.scan_id:
        raise FolderRoutineError(
            "Der beobachtete Ordner wurde seit der Routinenplanung verändert."
        )

    state_root = _safe_state_root(state_dir)
    execution_id = _routine_execution_id(plan, approval, completed_at)
    audit_dir = state_root / "routine-runs" / execution_id
    if audit_dir.exists() or audit_dir.is_symlink():
        raise FolderRoutineError(
            f"Routinen-Ausführungs-ID wurde bereits verwendet: {execution_id}"
        )
    _create_audit_directory(audit_dir)
    _write_new_json(
        audit_dir / "000-intent.json",
        {
            "schema": "folderhome.folder-routine-intent.v1",
            "routine_execution_id": execution_id,
            "routine_id": plan.routine_id,
            "approval": approval.to_dict(),
            "completed_at": completed_at,
            "status": "approved",
        },
    )

    try:
        cleanup_report = execute_folder_cleanup(
            plan.cleanup_plan,
            approval,
            state_dir=state_root,
            allow_file_write=True,
        )
    except FolderCleanupError as exc:
        raise FolderRoutineError(str(exc)) from exc
    if cleanup_report.status != "executed":
        return _failed_report(
            audit_dir,
            execution_id,
            plan,
            cleanup_report,
            status=cleanup_report.status,
            error=cleanup_report.error or "Batchausführung wurde nicht abgeschlossen.",
        )

    try:
        checkpoint = run_directory_scan(
            plan.scan_report.watch,
            captured_at=completed_at,
            state_dir=state_root,
            receipts=cleanup_report.placement_receipts,
            allow_state_write=True,
            expected_previous_snapshot_id=plan.scan_report.previous_snapshot_id,
        )
    except Exception as exc:
        rollback_errors = _rollback_cleanup(cleanup_report, approval.approved_at)
        status = "rolled_back" if not rollback_errors else "failed"
        return _failed_report(
            audit_dir,
            execution_id,
            plan,
            cleanup_report,
            status=status,
            error=str(exc),
            rollback_errors=rollback_errors,
        )

    completed_file = audit_dir / "100-completed.json"
    report = FolderRoutineExecutionReport(
        routine_execution_id=execution_id,
        routine_id=plan.routine_id,
        cleanup_report=cleanup_report,
        checkpoint_report=checkpoint,
        completed_file=completed_file,
        status="executed",
    )
    _write_new_json(completed_file, report.to_dict())
    return report


def _eligible_paths(scan, mode: FolderRoutineMode) -> tuple[tuple[str, ...], str, str]:
    if mode is FolderRoutineMode.FULL:
        paths = tuple(entry.relative_path for entry in scan.snapshot.files)
        return (
            paths,
            "planned" if paths else "no_changes",
            "Vollständiger Aufräummodus wurde ausdrücklich gewählt.",
        )
    if not scan.interval_due:
        return (), "not_due", "Das konfigurierte Scanintervall ist noch nicht fällig."
    if scan.diff is None:
        paths = tuple(entry.relative_path for entry in scan.snapshot.files)
        return (
            paths,
            "planned" if paths else "no_changes",
            "Erster Routinenlauf berücksichtigt den vollständigen Ausgangsbestand.",
        )
    selected = {
        change.after_path
        for change in scan.diff.changes
        if change.kind
        in {
            DirectoryChangeKind.ADDED,
            DirectoryChangeKind.MODIFIED,
            DirectoryChangeKind.MOVED,
        }
        and change.after_path is not None
    }
    paths = tuple(sorted(selected, key=lambda item: (item.casefold(), item)))
    return (
        paths,
        "planned" if paths else "no_changes",
        (
            "Fälliger Änderungslauf berücksichtigt neue, inhaltlich geänderte und "
            "eindeutig verschobene Dateien."
            if paths
            else "Fälliger Änderungslauf enthält keine relevanten Dateiänderungen."
        ),
    )


def _failed_report(
    audit_dir: Path,
    execution_id: str,
    plan: FolderRoutinePlan,
    cleanup_report,
    *,
    status: str,
    error: str,
    rollback_errors: list[str] | None = None,
) -> FolderRoutineExecutionReport:
    completed_file = audit_dir / "900-failed.json"
    report = FolderRoutineExecutionReport(
        routine_execution_id=execution_id,
        routine_id=plan.routine_id,
        cleanup_report=cleanup_report,
        checkpoint_report=None,
        completed_file=completed_file,
        status=status,
        error=error,
    )
    _write_new_json(
        completed_file,
        {**report.to_dict(), "rollback_errors": rollback_errors or []},
    )
    return report


def _rollback_cleanup(cleanup_report, approved_at: str) -> list[str]:
    errors = []
    for execution in reversed(cleanup_report.executions):
        material = f"{execution.execution_id}\0{approved_at}\0routine"
        try:
            undo_document_actions(
                execution,
                ActionUndoApproval(
                    approval_id=(
                        f"routine_{sha256(material.encode('utf-8')).hexdigest()[:40]}"
                    ),
                    execution_id=execution.execution_id,
                    document_sha256=execution.document_sha256,
                    approved_at=approved_at,
                ),
                allow_file_write=True,
            )
        except Exception as exc:
            errors.append(str(exc))
    return errors


def _validate_watch_policy(
    watch: WatchedFolder,
    policy: ResolvedProfilePolicy,
) -> None:
    if watch.profile_id != policy.profile_id or watch.area != policy.area:
        raise FolderRoutineError(
            "Beobachtungsprofil und aufgelöste Profilregeln stimmen nicht überein."
        )


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _routine_id(
    mode: FolderRoutineMode,
    scan_id: str,
    batch_id: str,
    status: str,
    paths: tuple[str, ...],
) -> str:
    material = "\0".join((mode.value, scan_id, batch_id, status, *paths))
    return f"routine_{sha256(material.encode('utf-8')).hexdigest()}"


def _routine_execution_id(
    plan: FolderRoutinePlan,
    approval: FolderCleanupApproval,
    completed_at: str,
) -> str:
    payload = {
        "routine_id": plan.routine_id,
        "approval": approval.to_dict(),
        "completed_at": completed_at,
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"routine_exec_{sha256(material).hexdigest()}"


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FolderRoutineError(f"Routinenzeitpunkt ist ungültig: {value}") from exc
    if parsed.tzinfo is None:
        raise FolderRoutineError("Routinenzeitpunkt benötigt eine Zeitzone.")
    return parsed


def _safe_state_root(state_dir: Path) -> Path:
    absolute = Path(os.path.abspath(state_dir))
    if absolute.is_symlink() or absolute.resolve(strict=False) != absolute:
        raise FolderRoutineError(
            f"State-Verzeichnis enthält einen symbolischen Link oder Alias: {absolute}"
        )
    return absolute


def _create_audit_directory(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir(exist_ok=False)
    except OSError as exc:
        raise FolderRoutineError(
            f"Routinen-Auditverzeichnis konnte nicht angelegt werden: {path}: {exc}"
        ) from exc


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
        raise FolderRoutineError(f"Routinen-Audit existiert bereits: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)
