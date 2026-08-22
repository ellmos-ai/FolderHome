"""Execute and undo an explicitly approved prefix of planned document moves."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from hashlib import sha256
from pathlib import Path

from folderhome.capabilities.filesystem_transaction import (
    FileMoveResult,
    FilesystemTransactionError,
    move_file_no_overwrite,
    remove_empty_directories,
    validate_move_target,
)
from folderhome.contracts import (
    ActionExecutionApproval,
    ActionExecutionReport,
    ActionUndoApproval,
    ActionUndoReport,
    DocumentPolicyActionPlan,
    ExecutedActionStep,
    PlacementReceipt,
    PolicyActionKind,
    PolicyActionStatus,
    PolicyActionStep,
    SideEffect,
    build_document_id,
)

_EXECUTOR_ID = "folderhome.filesystem-transaction"
_SUPPORTED_KINDS = {
    PolicyActionKind.RENAME,
    PolicyActionKind.SORT,
    PolicyActionKind.ARCHIVE,
    PolicyActionKind.HANDLE_ORIGINAL,
}


class DocumentActionExecutionError(RuntimeError):
    """Raised when approval, filesystem state, or audit state is unsafe."""


def execute_document_actions(
    plan: DocumentPolicyActionPlan,
    approval: ActionExecutionApproval,
    *,
    state_dir: Path,
    allow_file_write: bool,
) -> ActionExecutionReport:
    """Execute an approved contiguous move prefix and append immutable audit events."""

    if not allow_file_write:
        raise DocumentActionExecutionError(
            "Explizite Schreibfreigabe für die Dateiausführung fehlt."
        )
    steps = validate_document_execution(plan, approval)

    source = plan.document.source_path.resolve()
    source_hash = plan.document.source_sha256
    execution_id = _execution_id(approval)
    state_root = _safe_state_root(state_dir)
    audit_root = state_root / "action-executions"
    execution_dir = audit_root / execution_id
    if execution_dir.exists() or execution_dir.is_symlink():
        raise DocumentActionExecutionError(
            f"Ausführungs-ID wurde bereits verwendet: {execution_id}"
        )
    completed_file = execution_dir / "100-completed.json"
    intent = {
        "schema": "folderhome.action-execution-intent.v1",
        "execution_id": execution_id,
        "plan_id": plan.plan_id,
        "document_id": plan.document.document_id,
        "document_sha256": source_hash,
        "approval": approval.to_dict(),
        "actions": [step.to_dict() for step in steps],
        "executor_id": _EXECUTOR_ID,
        "status": "approved",
    }
    _create_execution_directory(execution_dir)
    try:
        _write_new_json(execution_dir / "000-intent.json", intent)
    except Exception:
        _remove_empty_audit_directory(execution_dir, audit_root)
        raise

    move_results: list[FileMoveResult] = []
    executed_steps: list[ExecutedActionStep] = []
    try:
        for step in steps:
            assert step.target_path is not None
            result = move_file_no_overwrite(
                step.source_path,
                step.target_path,
                expected_sha256=source_hash,
            )
            move_results.append(result)
            executed_steps.append(
                ExecutedActionStep(
                    action_id=step.action_id,
                    sequence=step.sequence,
                    kind=step.kind,
                    source_path=step.source_path,
                    target_path=step.target_path,
                    planner_provider_id=step.provider_id or "",
                    executor_id=_EXECUTOR_ID,
                    source_sha256=source_hash,
                )
            )
        final_target = executed_steps[-1].target_path
        created_directories = _unique_created_directories(move_results)
        receipt = _placement_receipt(
            plan,
            approval,
            final_target,
            source_hash,
            steps,
        )
        report = ActionExecutionReport(
            execution_id=execution_id,
            plan_id=plan.plan_id,
            document_id=plan.document.document_id,
            document_sha256=source_hash,
            profile_id=plan.profile_id,
            area=plan.area,
            approval=approval,
            original_source=source,
            final_target=final_target,
            steps=tuple(executed_steps),
            placement_receipt=receipt,
            created_directories=created_directories,
            completed_file=completed_file,
        )
        _write_new_json(completed_file, report.to_dict())
        return report
    except Exception as exc:
        rollback_errors = _rollback_moves(move_results, source_hash)
        failure = {
            "schema": "folderhome.action-execution-failure.v1",
            "execution_id": execution_id,
            "plan_id": plan.plan_id,
            "document_sha256": source_hash,
            "status": "rolled_back" if not rollback_errors else "failed",
            "error": str(exc),
            "rollback_errors": rollback_errors,
        }
        with suppress(Exception):
            _write_new_json(execution_dir / "900-failed.json", failure)
        if isinstance(exc, DocumentActionExecutionError):
            raise
        raise DocumentActionExecutionError(
            f"Dateiausführung fehlgeschlagen; Rückweg wurde versucht: {exc}"
        ) from exc


def validate_document_execution(
    plan: DocumentPolicyActionPlan,
    approval: ActionExecutionApproval,
) -> tuple[PolicyActionStep, ...]:
    """Perform all read-only approval, source, and target preflight checks."""

    if approval.plan_id != plan.plan_id:
        raise DocumentActionExecutionError("Freigabe und Plan-ID stimmen nicht überein.")
    if approval.document_sha256 != plan.document.source_sha256:
        raise DocumentActionExecutionError(
            "Freigabe und dokumentierter Quellhash stimmen nicht überein."
        )
    source = plan.document.source_path.resolve()
    if source.is_symlink() or not source.is_file():
        raise DocumentActionExecutionError(
            f"Plandokument fehlt, ist kein reguläres Dokument oder ist ein Link: {source}"
        )
    source_hash = _sha256_file(source)
    if source_hash != plan.document.source_sha256:
        raise DocumentActionExecutionError(
            f"Quellhash hat sich seit der Planung geändert: {source}"
        )
    if build_document_id(source, source_hash) != plan.document.document_id:
        raise DocumentActionExecutionError(
            "Dokument-ID stimmt nicht mit Quellpfad und Quellhash überein."
        )
    steps = _approved_steps(plan, approval)
    _preflight_chain(plan, steps)
    return steps


def undo_document_actions(
    report: ActionExecutionReport,
    approval: ActionUndoApproval,
    *,
    allow_file_write: bool,
) -> ActionUndoReport:
    """Undo one completed execution only while its final hash/path still match."""

    if not allow_file_write:
        raise DocumentActionExecutionError(
            "Explizite Schreibfreigabe für Undo fehlt."
        )
    if approval.execution_id != report.execution_id:
        raise DocumentActionExecutionError(
            "Undo-Freigabe und Ausführungs-ID stimmen nicht überein."
        )
    if approval.document_sha256 != report.document_sha256:
        raise DocumentActionExecutionError(
            "Undo-Freigabe und Dokumenthash stimmen nicht überein."
        )
    if report.status != "executed":
        raise DocumentActionExecutionError("Nur eine ausgeführte Aktion kann rückgängig werden.")
    execution_dir = report.completed_file.parent
    undo_completed = execution_dir / "300-undone.json"
    if undo_completed.exists() or undo_completed.is_symlink():
        raise DocumentActionExecutionError(
            f"Ausführung wurde bereits rückgängig gemacht: {report.execution_id}"
        )
    final_target = report.final_target.resolve()
    original = report.original_source.resolve()
    if final_target.is_symlink() or not final_target.is_file():
        raise DocumentActionExecutionError(
            f"Undo-Quelle fehlt oder ist kein reguläres Dokument: {final_target}"
        )
    if _sha256_file(final_target) != report.document_sha256:
        raise DocumentActionExecutionError(
            f"Zielhash hat sich seit der Ausführung geändert: {final_target}"
        )
    try:
        validate_move_target(original)
    except FilesystemTransactionError as exc:
        raise DocumentActionExecutionError(str(exc)) from exc
    undo_id = _undo_id(approval)
    _write_new_json(
        execution_dir / "200-undo-intent.json",
        {
            "schema": "folderhome.action-undo-intent.v1",
            "undo_id": undo_id,
            "execution_id": report.execution_id,
            "document_sha256": report.document_sha256,
            "approval": approval.to_dict(),
            "source_path": str(final_target),
            "restored_path": str(original),
            "status": "approved",
        },
    )
    moved = False
    try:
        move_file_no_overwrite(
            final_target,
            original,
            expected_sha256=report.document_sha256,
        )
        moved = True
        removed = remove_empty_directories(report.created_directories)
        undo_report = ActionUndoReport(
            undo_id=undo_id,
            execution_id=report.execution_id,
            document_sha256=report.document_sha256,
            approval=approval,
            source_path=final_target,
            restored_path=original,
            removed_directories=removed,
            completed_file=undo_completed,
        )
        _write_new_json(undo_completed, undo_report.to_dict())
        return undo_report
    except Exception as exc:
        recovery_error = None
        if moved and original.exists() and not final_target.exists():
            try:
                move_file_no_overwrite(
                    original,
                    final_target,
                    expected_sha256=report.document_sha256,
                )
            except Exception as recovery_exc:
                recovery_error = str(recovery_exc)
        with suppress(Exception):
            _write_new_json(
                execution_dir / "290-undo-failed.json",
                {
                    "schema": "folderhome.action-undo-failure.v1",
                    "undo_id": undo_id,
                    "execution_id": report.execution_id,
                    "status": "restored_execution" if recovery_error is None else "failed",
                    "error": str(exc),
                    "recovery_error": recovery_error,
                },
            )
        raise DocumentActionExecutionError(
            f"Undo fehlgeschlagen; Wiederherstellung wurde versucht: {exc}"
        ) from exc


def read_action_execution_report(path: Path) -> ActionExecutionReport:
    """Read and cross-check one immutable completed execution report."""

    path = path.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DocumentActionExecutionError(
            f"Ausführungsbericht ist nicht lesbar: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        ActionExecutionReport.SCHEMA
    ):
        raise DocumentActionExecutionError(
            "Ausführungsbericht verwendet ein unbekanntes Schema."
        )
    try:
        approval_payload = _mapping(payload["approval"], "approval")
        approval = ActionExecutionApproval(
            approval_id=_text(approval_payload, "approval_id"),
            plan_id=_text(approval_payload, "plan_id"),
            action_ids=tuple(_string_list(approval_payload, "action_ids")),
            document_sha256=_text(approval_payload, "document_sha256"),
            approved_at=_text(approval_payload, "approved_at"),
        )
        step_payloads = _list(payload, "steps")
        steps = tuple(_read_executed_step(item) for item in step_payloads)
        receipt_payload = _mapping(payload["placement_receipt"], "placement_receipt")
        receipt = PlacementReceipt(
            receipt_id=_text(receipt_payload, "receipt_id"),
            document_sha256=_text(receipt_payload, "document_sha256"),
            placed_path=_text(receipt_payload, "placed_path"),
            profile_id=_text(receipt_payload, "profile_id"),
            area=_text(receipt_payload, "area"),
            source_rule_ids=tuple(_string_list(receipt_payload, "source_rule_ids")),
            root_path=Path(_text(receipt_payload, "root_path")),
        )
        report = ActionExecutionReport(
            execution_id=_text(payload, "execution_id"),
            plan_id=_text(payload, "plan_id"),
            document_id=_text(payload, "document_id"),
            document_sha256=_text(payload, "document_sha256"),
            profile_id=_text(payload, "profile_id"),
            area=_text(payload, "area"),
            approval=approval,
            original_source=Path(_text(payload, "original_source")),
            final_target=Path(_text(payload, "final_target")),
            steps=steps,
            placement_receipt=receipt,
            created_directories=tuple(
                Path(value) for value in _string_list(payload, "created_directories")
            ),
            completed_file=Path(_text(payload, "completed_file")),
            status=_text(payload, "status"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DocumentActionExecutionError(
            f"Ausführungsbericht ist ungültig: {exc}"
        ) from exc
    _validate_loaded_report(report, path)
    _validate_report_against_intent(report)
    return report


def executable_action_prefix(
    plan: DocumentPolicyActionPlan,
) -> tuple[PolicyActionStep, ...]:
    """Return the maximal contiguous move prefix supported by the executor."""

    candidates = []
    for step in plan.steps:
        if (
            step.status is PolicyActionStatus.PLANNED
            and step.kind in _SUPPORTED_KINDS
            and step.target_path is not None
            and step.capability_id in {"rename", "move"}
        ):
            candidates.append(step)
            continue
        if step.status is PolicyActionStatus.PLANNED and step.side_effects:
            break
    return tuple(candidates)


def _approved_steps(
    plan: DocumentPolicyActionPlan,
    approval: ActionExecutionApproval,
) -> tuple[PolicyActionStep, ...]:
    candidates = executable_action_prefix(plan)
    approved_count = len(approval.action_ids)
    if tuple(step.action_id for step in candidates[:approved_count]) != approval.action_ids:
        raise DocumentActionExecutionError(
            "Freigegebene Aktions-IDs sind kein lückenloser ausführbarer Planpräfix."
        )
    if approved_count > len(candidates):
        raise DocumentActionExecutionError("Freigabe enthält unbekannte Aktions-IDs.")
    return tuple(candidates[:approved_count])


def _preflight_chain(plan: DocumentPolicyActionPlan, steps: tuple[object, ...]) -> None:
    current = plan.document.source_path.resolve()
    for step in steps:
        if step.source_path != current:
            raise DocumentActionExecutionError(
                f"Aktionskette ist am Schritt {step.action_id} nicht zusammenhängend."
            )
        if step.target_path is None or step.provider_id is None:
            raise DocumentActionExecutionError(
                f"Aktion besitzt kein eindeutiges Ziel oder keinen Planprovider: {step.action_id}"
            )
        if step.gate.required is not True or step.gate.granted is not False:
            raise DocumentActionExecutionError(
                f"Plan-Gate hat einen unerwarteten Zustand: {step.action_id}"
            )
        if step.side_effects != (SideEffect.FILESYSTEM_WRITE,):
            raise DocumentActionExecutionError(
                f"Aktion deklariert unerwartete Side-Effects: {step.action_id}"
            )
        target = step.target_path.resolve()
        if step.kind is PolicyActionKind.RENAME:
            if target.parent != current.parent:
                raise DocumentActionExecutionError(
                    f"Rename verlässt den Quellordner: {step.action_id}"
                )
        elif not target.is_relative_to(plan.target_root):
            raise DocumentActionExecutionError(
                f"Move-Ziel verlässt target_root: {step.action_id}"
            )
        try:
            validate_move_target(target)
        except FilesystemTransactionError as exc:
            raise DocumentActionExecutionError(str(exc)) from exc
        current = target


def _placement_receipt(
    plan: DocumentPolicyActionPlan,
    approval: ActionExecutionApproval,
    final_target: Path,
    source_hash: str,
    steps: tuple[object, ...],
) -> PlacementReceipt:
    if final_target.is_relative_to(plan.target_root):
        root = plan.target_root
    else:
        root = plan.document.source_path.parent.resolve()
    placed_path = final_target.relative_to(root).as_posix()
    source_rule_ids = tuple(
        dict.fromkeys(
            rule_id
            for step in steps
            for rule in step.rules
            for rule_id in rule.source_rule_ids
        )
    )
    material = "\0".join(
        (approval.approval_id, plan.plan_id, source_hash, str(final_target))
    )
    return PlacementReceipt(
        receipt_id=f"receipt_{sha256(material.encode('utf-8')).hexdigest()}",
        document_sha256=source_hash,
        placed_path=placed_path,
        profile_id=plan.profile_id,
        area=plan.area,
        source_rule_ids=source_rule_ids,
        root_path=root,
    )


def _rollback_moves(results: list[FileMoveResult], source_hash: str) -> list[str]:
    errors = []
    for result in reversed(results):
        try:
            move_file_no_overwrite(
                result.target_path,
                result.source_path,
                expected_sha256=source_hash,
            )
            remove_empty_directories(result.created_directories)
        except Exception as exc:
            errors.append(str(exc))
    return errors


def _unique_created_directories(
    results: list[FileMoveResult],
) -> tuple[Path, ...]:
    unique = {}
    for result in results:
        for path in result.created_directories:
            unique[str(path)] = path
    return tuple(sorted(unique.values(), key=lambda item: len(item.parts)))


def _execution_id(approval: ActionExecutionApproval) -> str:
    material = json.dumps(
        approval.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"exec_{sha256(material).hexdigest()}"


def _undo_id(approval: ActionUndoApproval) -> str:
    material = json.dumps(
        approval.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"undo_{sha256(material).hexdigest()}"


def _create_execution_directory(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir(exist_ok=False)
    except OSError as exc:
        raise DocumentActionExecutionError(
            f"Auditverzeichnis konnte nicht sicher angelegt werden: {path}: {exc}"
        ) from exc


def _safe_state_root(state_dir: Path) -> Path:
    absolute = Path(os.path.abspath(state_dir))
    if absolute.is_symlink() or absolute.resolve(strict=False) != absolute:
        raise DocumentActionExecutionError(
            f"State-Verzeichnis enthält einen symbolischen Link oder Alias: {absolute}"
        )
    return absolute


def _remove_empty_audit_directory(path: Path, audit_root: Path) -> None:
    for candidate in (path, audit_root):
        with suppress(OSError):
            candidate.rmdir()


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
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise DocumentActionExecutionError(
                f"Auditereignis existiert bereits: {path}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _read_executed_step(value: object) -> ExecutedActionStep:
    item = _mapping(value, "step")
    return ExecutedActionStep(
        action_id=_text(item, "action_id"),
        sequence=_integer(item, "sequence"),
        kind=PolicyActionKind(_text(item, "kind")),
        source_path=Path(_text(item, "source_path")),
        target_path=Path(_text(item, "target_path")),
        planner_provider_id=_text(item, "planner_provider_id"),
        executor_id=_text(item, "executor_id"),
        source_sha256=_text(item, "source_sha256"),
    )


def _validate_loaded_report(report: ActionExecutionReport, path: Path) -> None:
    if report.completed_file != path:
        raise DocumentActionExecutionError(
            "Ausführungsbericht verweist nicht auf seine eigene Auditdatei."
        )
    if report.status != "executed" or not report.steps:
        raise DocumentActionExecutionError(
            "Ausführungsbericht ist nicht als abgeschlossene Aktion belegt."
        )
    if report.execution_id != _execution_id(report.approval):
        raise DocumentActionExecutionError(
            "execution_id stimmt nicht mit der Freigabe überein."
        )
    if report.plan_id != report.approval.plan_id:
        raise DocumentActionExecutionError("Planbezug im Bericht ist widersprüchlich.")
    if report.document_sha256 != report.approval.document_sha256:
        raise DocumentActionExecutionError("Hashbezug im Bericht ist widersprüchlich.")
    if tuple(step.action_id for step in report.steps) != report.approval.action_ids:
        raise DocumentActionExecutionError("Aktionsbezug im Bericht ist widersprüchlich.")
    if report.original_source != report.steps[0].source_path:
        raise DocumentActionExecutionError("Ursprung passt nicht zum ersten Aktionsschritt.")
    if report.final_target != report.steps[-1].target_path:
        raise DocumentActionExecutionError("Ziel passt nicht zum letzten Aktionsschritt.")
    if any(
        step.source_sha256 != report.document_sha256
        or step.executor_id != _EXECUTOR_ID
        for step in report.steps
    ):
        raise DocumentActionExecutionError(
            "Executor- oder Hashprovenienz im Bericht ist widersprüchlich."
        )
    if report.placement_receipt.document_sha256 != report.document_sha256:
        raise DocumentActionExecutionError("Ablagebeleg verwendet einen anderen Hash.")


def _validate_report_against_intent(report: ActionExecutionReport) -> None:
    intent_path = report.completed_file.parent / "000-intent.json"
    try:
        intent = json.loads(intent_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DocumentActionExecutionError(
            f"Ausführungs-Intent ist nicht lesbar: {exc}"
        ) from exc
    if not isinstance(intent, dict) or intent.get("schema") != (
        "folderhome.action-execution-intent.v1"
    ):
        raise DocumentActionExecutionError(
            "Ausführungs-Intent verwendet ein unbekanntes Schema."
        )
    try:
        if (
            _text(intent, "execution_id") != report.execution_id
            or _text(intent, "plan_id") != report.plan_id
            or _text(intent, "document_id") != report.document_id
            or _text(intent, "document_sha256") != report.document_sha256
            or intent["approval"] != report.approval.to_dict()
            or _text(intent, "executor_id") != _EXECUTOR_ID
            or _text(intent, "status") != "approved"
        ):
            raise DocumentActionExecutionError(
                "Ausführungsbericht widerspricht seinem unveränderlichen Intent."
            )
        actions = _list(intent, "actions")
        if len(actions) != len(report.steps):
            raise DocumentActionExecutionError(
                "Ausführungsbericht widerspricht der Aktionszahl im Intent."
            )
        for action_value, executed in zip(actions, report.steps, strict=True):
            action = _mapping(action_value, "intent action")
            if (
                _text(action, "action_id") != executed.action_id
                or _integer(action, "sequence") != executed.sequence
                or _text(action, "kind") != executed.kind.value
                or Path(_text(action, "source_path")).resolve()
                != executed.source_path
                or Path(_text(action, "target_path")).resolve()
                != executed.target_path
                or _text(action, "provider_id") != executed.planner_provider_id
            ):
                raise DocumentActionExecutionError(
                    "Ausführungsbericht widerspricht einem Aktionsschritt im Intent."
                )
    except (KeyError, TypeError, ValueError) as exc:
        raise DocumentActionExecutionError(
            f"Ausführungs-Intent ist ungültig: {exc}"
        ) from exc


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} muss ein JSON-Objekt sein.")
    return value


def _list(item: dict[str, object], field: str) -> list[object]:
    value = item[field]
    if not isinstance(value, list):
        raise ValueError(f"{field} muss eine JSON-Liste sein.")
    return value


def _string_list(item: dict[str, object], field: str) -> list[str]:
    values = _list(item, field)
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError(f"{field} muss ausschließlich nichtleere Texte enthalten.")
    return values


def _text(item: dict[str, object], field: str) -> str:
    value = item[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} muss ein nichtleerer Text sein.")
    return value


def _integer(item: dict[str, object], field: str) -> int:
    value = item[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} muss eine Ganzzahl sein.")
    return value


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
