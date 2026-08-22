"""Plan and execute safe, selective cleanup runs over whole folders."""

from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.application.document_action_execution import (
    DocumentActionExecutionError,
    executable_action_prefix,
    execute_document_actions,
    undo_document_actions,
    validate_document_execution,
)
from folderhome.application.document_action_plan import (
    DocumentActionPlanError,
    build_document_action_plan,
)
from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    ActionExecutionApproval,
    ActionUndoApproval,
    BatchItemApproval,
    CleanupConflict,
    DocumentRecord,
    FolderCleanupApproval,
    FolderCleanupExecutionReport,
    FolderCleanupItem,
    FolderCleanupPlan,
    ResolvedProfilePolicy,
)


class FolderCleanupError(RuntimeError):
    """Raised when a folder plan or selective batch cannot be trusted."""


class CleanupDocumentExtractor(Protocol):
    """Read-only document extraction port used by folder planning."""

    def extract(self, source_path: Path) -> DocumentRecord: ...


def build_folder_cleanup_plan(
    source_dir: Path,
    *,
    policy: ResolvedProfilePolicy,
    target_root: Path,
    as_of: date,
    extractor: CleanupDocumentExtractor,
    recursive: bool = True,
    include_relative_paths: frozenset[str] | None = None,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderCleanupPlan:
    """Build per-document plans, then detect conflicts across the whole folder."""

    source_root = source_dir.resolve()
    target_root = target_root.resolve()
    if source_root.is_symlink() or not source_root.is_dir():
        raise FolderCleanupError(f"Quellordner fehlt oder ist ein Link: {source_root}")
    try:
        inventory = inventory_files(
            source_root,
            recursive=recursive,
            policy=resource_policy,
        )
    except (ResourceLimitExceeded, ValueError) as exc:
        raise FolderCleanupError(str(exc)) from exc
    paths = list(inventory.all_paths)
    if include_relative_paths is not None:
        _validate_relative_path_filter(include_relative_paths)
        available = {
            path.relative_to(source_root).as_posix(): path for path in paths
        }
        missing = sorted(
            include_relative_paths.difference(available),
            key=lambda item: (item.casefold(), item),
        )
        if missing:
            raise FolderCleanupError(
                "Ausgewählte Quelldateien fehlen oder wurden während der Planung "
                f"verändert: {', '.join(missing)}"
            )
        paths = [available[relative] for relative in include_relative_paths]
        paths.sort(
            key=lambda path: (
                path.relative_to(source_root).as_posix().casefold(),
                path.relative_to(source_root).as_posix(),
            )
        )
    text_budget = ResourceBudget(resource_policy)
    items = [
        _plan_source(
            path,
            source_root,
            policy,
            target_root,
            as_of,
            extractor,
            text_budget,
        )
        for path in paths
    ]
    conflicts = _cross_document_conflicts(items)
    conflict_ids_by_document: dict[str, list[str]] = defaultdict(list)
    for conflict in conflicts:
        for document_id in conflict.document_ids:
            conflict_ids_by_document[document_id].append(conflict.conflict_id)
    updated_items = []
    for item in items:
        conflict_ids = (
            tuple(sorted(conflict_ids_by_document.get(item.document_id, ())))
            if item.document_id
            else ()
        )
        if conflict_ids:
            updated_items.append(
                replace(
                    item,
                    status="blocked",
                    conflict_ids=conflict_ids,
                    message=(
                        "Ordnerweiter Ziel- oder Abhängigkeitskonflikt; "
                        "keine Batchausführung zulässig."
                    ),
                )
            )
        else:
            updated_items.append(item)
    finalized_items = tuple(updated_items)
    batch_id = _cleanup_batch_id(
        source_root=source_root,
        target_root=target_root,
        profile_id=policy.profile_id,
        area=policy.area,
        as_of=as_of.isoformat(),
        recursive=recursive,
        items=finalized_items,
        conflicts=conflicts,
    )
    return FolderCleanupPlan(
        batch_id=batch_id,
        source_root=source_root,
        target_root=target_root,
        profile_id=policy.profile_id,
        area=policy.area,
        as_of=as_of.isoformat(),
        recursive=recursive,
        items=finalized_items,
        conflicts=conflicts,
    )


def execute_folder_cleanup(
    plan: FolderCleanupPlan,
    approval: FolderCleanupApproval,
    *,
    state_dir: Path,
    allow_file_write: bool,
) -> FolderCleanupExecutionReport:
    """Execute selected items; roll completed items back if a later item fails."""

    if not allow_file_write:
        raise FolderCleanupError(
            "Explizite Schreibfreigabe für die Batchausführung fehlt."
        )
    selected = validate_folder_cleanup_execution(plan, approval)

    state_root = _safe_state_root(state_dir)
    batch_execution_id = _batch_execution_id(approval)
    audit_dir = state_root / "cleanup-runs" / batch_execution_id
    if audit_dir.exists() or audit_dir.is_symlink():
        raise FolderCleanupError(
            f"Batch-Ausführungs-ID wurde bereits verwendet: {batch_execution_id}"
        )
    _create_audit_directory(audit_dir)
    _write_new_json(
        audit_dir / "000-intent.json",
        {
            "schema": "folderhome.folder-cleanup-intent.v1",
            "batch_execution_id": batch_execution_id,
            "batch_id": plan.batch_id,
            "approval": approval.to_dict(),
            "selected_documents": [item.document_id for item, _ in selected],
            "status": "approved",
        },
    )

    executions = []
    try:
        for item, action_approval in selected:
            assert item.action_plan is not None
            executions.append(
                execute_document_actions(
                    item.action_plan,
                    action_approval,
                    state_dir=state_root,
                    allow_file_write=True,
                )
            )
    except Exception as exc:
        rollback_errors = _rollback_batch(executions, approval.approved_at)
        failed_file = audit_dir / "900-failed.json"
        report = FolderCleanupExecutionReport(
            batch_execution_id=batch_execution_id,
            batch_id=plan.batch_id,
            approval=approval,
            executions=tuple(executions),
            placement_receipts=(),
            completed_file=failed_file,
            status="rolled_back" if not rollback_errors else "failed",
            error=str(exc),
        )
        _write_new_json(
            failed_file,
            {
                **report.to_dict(),
                "rollback_errors": rollback_errors,
            },
        )
        return report

    completed_file = audit_dir / "100-completed.json"
    report = FolderCleanupExecutionReport(
        batch_execution_id=batch_execution_id,
        batch_id=plan.batch_id,
        approval=approval,
        executions=tuple(executions),
        placement_receipts=tuple(
            execution.placement_receipt for execution in executions
        ),
        completed_file=completed_file,
        status="executed",
    )
    try:
        _write_new_json(completed_file, report.to_dict())
    except Exception as exc:
        rollback_errors = _rollback_batch(executions, approval.approved_at)
        raise FolderCleanupError(
            "Batchabschluss konnte nicht protokolliert werden; Rückweg wurde "
            f"versucht ({len(rollback_errors)} Fehler): {exc}"
        ) from exc
    return report


def validate_folder_cleanup_execution(
    plan: FolderCleanupPlan,
    approval: FolderCleanupApproval,
) -> tuple[tuple[FolderCleanupItem, ActionExecutionApproval], ...]:
    """Validate an exact selective approval without creating state."""

    if approval.batch_id != plan.batch_id:
        raise FolderCleanupError("Freigabe und Batch-ID stimmen nicht überein.")
    item_map = {
        item.document_id: item for item in plan.items if item.document_id is not None
    }
    selected: list[tuple[FolderCleanupItem, ActionExecutionApproval]] = []
    for index, item_approval in enumerate(approval.items):
        item = item_map.get(item_approval.document_id)
        if item is None or item.action_plan is None:
            raise FolderCleanupError(
                f"Freigabe nennt ein unbekanntes Plandokument: {item_approval.document_id}"
            )
        if item.status == "blocked" or item.conflict_ids:
            raise FolderCleanupError(
                f"Konflikt blockiert das Plandokument: {item.relative_path}"
            )
        if item.status != "planned":
            raise FolderCleanupError(
                f"Plandokument ist nicht ausführbar: {item.relative_path} ({item.status})"
            )
        if (
            item_approval.plan_id != item.action_plan.plan_id
            or item_approval.document_sha256 != item.source_sha256
        ):
            raise FolderCleanupError(
                f"Freigabe passt nicht zum Plandokument: {item.relative_path}"
            )
        action_approval = ActionExecutionApproval(
            approval_id=_item_approval_id(approval, item_approval, index),
            plan_id=item_approval.plan_id,
            action_ids=item_approval.action_ids,
            document_sha256=item_approval.document_sha256,
            approved_at=approval.approved_at,
        )
        try:
            validate_document_execution(item.action_plan, action_approval)
        except DocumentActionExecutionError as exc:
            raise FolderCleanupError(
                f"Batch-Preflight scheiterte für {item.relative_path}: {exc}"
            ) from exc
        selected.append((item, action_approval))

    return tuple(selected)


def _validate_relative_path_filter(paths: frozenset[str]) -> None:
    for value in paths:
        path = Path(value)
        if not value or path.is_absolute() or ".." in path.parts:
            raise FolderCleanupError(
                f"Ausgewählter Relativpfad ist unsicher: {value!r}"
            )
        if path.as_posix() != value:
            raise FolderCleanupError(
                f"Ausgewählter Relativpfad ist nicht normalisiert: {value!r}"
            )


def _plan_source(
    source_path: Path,
    source_root: Path,
    policy: ResolvedProfilePolicy,
    target_root: Path,
    as_of: date,
    extractor: CleanupDocumentExtractor,
    resource_budget: ResourceBudget,
) -> FolderCleanupItem:
    relative_path = source_path.relative_to(source_root).as_posix()
    if source_path.is_symlink():
        return FolderCleanupItem(
            relative_path=relative_path,
            source_path=source_path,
            source_sha256=sha256(b"symbolic-link-skipped").hexdigest(),
            document_id=None,
            status="skipped",
            action_plan=None,
            executable_action_ids=(),
            conflict_ids=(),
            message="Symbolischer Link wurde nicht verarbeitet.",
        )
    source_hash = _sha256_file(source_path)
    try:
        document = extractor.extract(source_path)
        resource_budget.consume_extracted_text(len(document.text))
        plan = build_document_action_plan(
            document,
            policy,
            target_root=target_root,
            as_of=as_of,
        )
    except ResourceLimitExceeded as exc:
        raise FolderCleanupError(str(exc)) from exc
    except UnsupportedDocumentError as exc:
        return FolderCleanupItem(
            relative_path=relative_path,
            source_path=source_path,
            source_sha256=source_hash,
            document_id=None,
            status="skipped",
            action_plan=None,
            executable_action_ids=(),
            conflict_ids=(),
            message=str(exc),
        )
    except (DocServicesBridgeError, DocumentActionPlanError, ValueError) as exc:
        return FolderCleanupItem(
            relative_path=relative_path,
            source_path=source_path,
            source_sha256=source_hash,
            document_id=None,
            status="failed",
            action_plan=None,
            executable_action_ids=(),
            conflict_ids=(),
            message=str(exc),
        )
    prefix = executable_action_prefix(plan)
    if prefix:
        status = "planned"
        message = "Ausführbarer Einzelplan; Batchfreigabe bleibt geschlossen."
    elif plan.steps:
        status = "blocked"
        message = "Plan enthält keinen durchgehenden unterstützten Move-Präfix."
    else:
        status = "noop"
        message = "Für dieses Dokument ist keine Aktion fällig."
    return FolderCleanupItem(
        relative_path=relative_path,
        source_path=source_path,
        source_sha256=document.source_sha256,
        document_id=document.document_id,
        status=status,
        action_plan=plan,
        executable_action_ids=tuple(step.action_id for step in prefix),
        conflict_ids=(),
        message=message,
    )


def _cross_document_conflicts(
    items: list[FolderCleanupItem],
) -> tuple[CleanupConflict, ...]:
    planned = [
        item
        for item in items
        if item.action_plan is not None and item.executable_action_ids
    ]
    sources = {
        item.source_path: item.document_id for item in planned if item.document_id
    }
    targets: dict[Path, list[str]] = defaultdict(list)
    for item in planned:
        assert item.action_plan is not None
        approved_ids = set(item.executable_action_ids)
        for step in item.action_plan.steps:
            if step.action_id in approved_ids and step.target_path is not None:
                targets[step.target_path].append(item.document_id or "")
    conflicts = []
    for target, document_ids in sorted(targets.items(), key=lambda pair: str(pair[0]).casefold()):
        unique_ids = tuple(sorted(set(document_ids)))
        if len(unique_ids) > 1:
            conflicts.append(
                _conflict(
                    "duplicate_target",
                    unique_ids,
                    (target,),
                    "Mehrere Dokumentpläne verwenden dasselbe Ziel.",
                )
            )
            continue
        source_owner = sources.get(target)
        if source_owner is not None and source_owner not in unique_ids:
            conflicts.append(
                _conflict(
                    "target_is_other_source",
                    tuple(sorted((*unique_ids, source_owner))),
                    (target,),
                    "Ein geplantes Ziel ist die Quelle eines anderen Dokuments.",
                )
            )
        elif target.exists() or target.is_symlink():
            conflicts.append(
                _conflict(
                    "existing_target",
                    unique_ids,
                    (target,),
                    "Ein geplantes Ziel existiert bereits.",
                )
            )
    conflicts.sort(key=lambda item: item.conflict_id)
    return tuple(conflicts)


def _conflict(
    kind: str,
    document_ids: tuple[str, ...],
    paths: tuple[Path, ...],
    message: str,
) -> CleanupConflict:
    material = "\0".join((kind, *document_ids, *(str(path) for path in paths)))
    return CleanupConflict(
        conflict_id=f"conflict_{sha256(material.encode('utf-8')).hexdigest()}",
        kind=kind,
        document_ids=document_ids,
        paths=paths,
        message=message,
    )


def _cleanup_batch_id(
    *,
    source_root: Path,
    target_root: Path,
    profile_id: str,
    area: str,
    as_of: str,
    recursive: bool,
    items: tuple[FolderCleanupItem, ...],
    conflicts: tuple[CleanupConflict, ...],
) -> str:
    payload = {
        "schema": FolderCleanupPlan.SCHEMA,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "profile_id": profile_id,
        "area": area,
        "as_of": as_of,
        "recursive": recursive,
        "items": [item.to_dict() for item in items],
        "conflicts": [conflict.to_dict() for conflict in conflicts],
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"cleanup_{sha256(material).hexdigest()}"


def _item_approval_id(
    approval: FolderCleanupApproval,
    item: BatchItemApproval,
    index: int,
) -> str:
    material = f"{approval.approval_id}\0{item.document_id}\0{index}"
    return f"batch_{sha256(material.encode('utf-8')).hexdigest()[:40]}"


def _batch_execution_id(approval: FolderCleanupApproval) -> str:
    material = json.dumps(
        approval.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"cleanup_exec_{sha256(material).hexdigest()}"


def _rollback_batch(executions: list[object], approved_at: str) -> list[str]:
    errors = []
    for execution in reversed(executions):
        material = f"{execution.execution_id}\0{approved_at}"
        try:
            undo_document_actions(
                execution,
                ActionUndoApproval(
                    approval_id=(
                        f"rollback_{sha256(material.encode('utf-8')).hexdigest()[:40]}"
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


def _safe_state_root(state_dir: Path) -> Path:
    absolute = Path(os.path.abspath(state_dir))
    if absolute.is_symlink() or absolute.resolve(strict=False) != absolute:
        raise FolderCleanupError(
            f"State-Verzeichnis enthält einen symbolischen Link oder Alias: {absolute}"
        )
    return absolute


def _create_audit_directory(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir(exist_ok=False)
    except OSError as exc:
        raise FolderCleanupError(
            f"Batch-Auditverzeichnis konnte nicht angelegt werden: {path}: {exc}"
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
        raise FolderCleanupError(f"Batch-Audit existiert bereits: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
