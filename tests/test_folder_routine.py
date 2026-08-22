from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

import folderhome.application.folder_routine as routine_module
from folderhome.application.directory_observation import run_directory_scan
from folderhome.application.folder_routine import (
    FolderRoutineError,
    build_folder_routine_plan,
    execute_folder_routine,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.contracts import (
    BatchItemApproval,
    ContentFormat,
    DocumentRecord,
    FolderCleanupApproval,
    FolderRoutineMode,
    IndexStatus,
    PrivacyStatus,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    RuleScope,
    WatchedFolder,
    build_document_id,
)


class SyntheticExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        if source_path.suffix.lower() != ".txt":
            raise UnsupportedDocumentError(
                f"Dateityp wird nicht unterstützt: {source_path.suffix}"
            )
        source_hash = sha256(source_path.read_bytes()).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, source_hash),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=source_hash,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-01-15T10:30:00Z",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetischer Datenschutzstatus.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _watch(source_root: Path, *, interval_minutes: int = 60) -> WatchedFolder:
    return WatchedFolder(
        watch_id="family_inbox",
        source_root=source_root,
        profile_id="lukas",
        area="dokumente",
        interval_minutes=interval_minutes,
        recursive=True,
        enabled=True,
    )


def _policy() -> ResolvedProfilePolicy:
    return ResolvedProfilePolicy(
        profile_id="lukas",
        display_name="Lukas",
        area="dokumente",
        os_account="synthetic",
        organizational_only=True,
        security_boundary="Organisationsprofil, keine Zugriffsgrenze.",
        rules=(
            ResolvedProfileRule(
                key=RuleKey.SORT_TARGET,
                value="Sortiert",
                scope=RuleScope.PROFILE_AREA,
                source_rule_ids=("rule_sort",),
                overridden_rule_ids=(),
            ),
        ),
    )


def _checkpoint(source_root: Path, state_dir: Path, captured_at: str) -> None:
    run_directory_scan(
        _watch(source_root),
        captured_at=captured_at,
        state_dir=state_dir,
        allow_state_write=True,
    )


def _build(
    source_root: Path,
    state_dir: Path,
    target_root: Path,
    *,
    captured_at: str,
    mode: FolderRoutineMode = FolderRoutineMode.CHANGES,
):
    return build_folder_routine_plan(
        _watch(source_root),
        policy=_policy(),
        target_root=target_root,
        as_of=date(2026, 8, 21),
        captured_at=captured_at,
        state_dir=state_dir,
        extractor=SyntheticExtractor(),
        mode=mode,
    )


def _approve(plan) -> FolderCleanupApproval:
    planned = [item for item in plan.cleanup_plan.items if item.status == "planned"]
    return FolderCleanupApproval(
        approval_id="routine_approval",
        batch_id=plan.cleanup_plan.batch_id,
        items=tuple(
            BatchItemApproval(
                document_id=item.document_id,
                plan_id=item.action_plan.plan_id,
                document_sha256=item.source_sha256,
                action_ids=item.executable_action_ids,
            )
            for item in planned
            if item.document_id is not None and item.action_plan is not None
        ),
        approved_at="2026-08-21T21:02:00Z",
    )


def test_changes_routine_is_read_only_and_skips_not_due_scan(tmp_path: Path) -> None:
    source_root = tmp_path / "Eingang"
    source_root.mkdir()
    (source_root / "Alt.txt").write_text("Alt", encoding="utf-8")
    state_dir = tmp_path / "state"
    _checkpoint(source_root, state_dir, "2026-08-21T20:00:00Z")
    added = source_root / "Neu.txt"
    added.write_text("Neu", encoding="utf-8")
    before_state = sorted(path.read_bytes() for path in state_dir.rglob("*.json"))

    plan = _build(
        source_root,
        state_dir,
        tmp_path / "Ablage",
        captured_at="2026-08-21T20:30:00Z",
    )

    assert plan.status == "not_due"
    assert plan.eligible_relative_paths == ()
    assert plan.cleanup_plan.items == ()
    assert plan.scan_report.interval_due is False
    assert plan.scan_report.checkpoint_file is None
    assert sorted(path.read_bytes() for path in state_dir.rglob("*.json")) == before_state
    assert added.read_text(encoding="utf-8") == "Neu"


def test_due_changes_routine_selects_added_modified_and_moved_files(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Eingang"
    source_root.mkdir()
    modified = source_root / "Geändert.txt"
    moved = source_root / "Altort.txt"
    unchanged = source_root / "Unverändert.txt"
    modified.write_text("Vorher", encoding="utf-8")
    moved.write_text("Verschoben", encoding="utf-8")
    unchanged.write_text("Gleich", encoding="utf-8")
    state_dir = tmp_path / "state"
    _checkpoint(source_root, state_dir, "2026-08-21T20:00:00Z")
    modified.write_text("Nachher", encoding="utf-8")
    moved.rename(source_root / "Neuort.txt")
    (source_root / "Neu.txt").write_text("Neu", encoding="utf-8")

    plan = _build(
        source_root,
        state_dir,
        tmp_path / "Ablage",
        captured_at="2026-08-21T21:01:00Z",
    )

    assert plan.status == "planned"
    assert plan.eligible_relative_paths == (
        "Geändert.txt",
        "Neu.txt",
        "Neuort.txt",
    )
    assert tuple(item.relative_path for item in plan.cleanup_plan.items) == (
        "Geändert.txt",
        "Neu.txt",
        "Neuort.txt",
    )
    assert plan.approval_required is True
    assert plan.scan_report.checkpoint_file is None
    assert unchanged.is_file()


def test_full_routine_plans_every_file_even_when_interval_is_not_due(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Eingang"
    source_root.mkdir()
    (source_root / "A.txt").write_text("A", encoding="utf-8")
    (source_root / "B.txt").write_text("B", encoding="utf-8")
    state_dir = tmp_path / "state"
    _checkpoint(source_root, state_dir, "2026-08-21T20:00:00Z")

    plan = _build(
        source_root,
        state_dir,
        tmp_path / "Ablage",
        captured_at="2026-08-21T20:01:00Z",
        mode=FolderRoutineMode.FULL,
    )

    assert plan.status == "planned"
    assert plan.scan_report.interval_due is False
    assert plan.eligible_relative_paths == ("A.txt", "B.txt")
    assert len(plan.cleanup_plan.items) == 2


def test_routine_rejects_target_inside_watched_source(tmp_path: Path) -> None:
    source_root = tmp_path / "Eingang"
    source_root.mkdir()

    with pytest.raises(FolderRoutineError, match="außerhalb"):
        _build(
            source_root,
            tmp_path / "state",
            source_root / "Sortiert",
            captured_at="2026-08-21T20:00:00Z",
            mode=FolderRoutineMode.FULL,
        )


def test_approved_routine_executes_batch_then_writes_checkpoint_and_report(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Eingang"
    source_root.mkdir()
    state_dir = tmp_path / "state"
    _checkpoint(source_root, state_dir, "2026-08-21T20:00:00Z")
    source = source_root / "Police.txt"
    source.write_text("Synthetische Police", encoding="utf-8")
    plan = _build(
        source_root,
        state_dir,
        tmp_path / "Ablage",
        captured_at="2026-08-21T21:01:00Z",
    )
    approval = _approve(plan)

    with pytest.raises(FolderRoutineError, match="Freigaben"):
        execute_folder_routine(
            plan,
            approval,
            completed_at="2026-08-21T21:03:00Z",
            state_dir=state_dir,
            allow_file_write=False,
            allow_state_write=True,
        )
    assert source.is_file()

    report = execute_folder_routine(
        plan,
        approval,
        completed_at="2026-08-21T21:03:00Z",
        state_dir=state_dir,
        allow_file_write=True,
        allow_state_write=True,
    )

    assert report.status == "executed"
    assert report.cleanup_report.status == "executed"
    assert report.checkpoint_report is not None
    assert report.checkpoint_report.checkpoint_file is not None
    assert report.checkpoint_report.snapshot.files == ()
    assert report.completed_file.is_file()
    assert not source.exists()
    assert (tmp_path / "Ablage" / "Sortiert" / "Police.txt").is_file()
    assert len(list((state_dir / "directory-snapshots").glob("*.json"))) == 2


def test_checkpoint_failure_rolls_back_routine_file_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "Eingang"
    source_root.mkdir()
    state_dir = tmp_path / "state"
    _checkpoint(source_root, state_dir, "2026-08-21T20:00:00Z")
    source = source_root / "Police.txt"
    source.write_text("Synthetische Police", encoding="utf-8")
    plan = _build(
        source_root,
        state_dir,
        tmp_path / "Ablage",
        captured_at="2026-08-21T21:01:00Z",
    )
    approval = _approve(plan)
    real_scan = routine_module.run_directory_scan
    calls = 0

    def fail_post_action_scan(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FolderRoutineError("Synthetischer Checkpointfehler.")
        return real_scan(*args, **kwargs)

    monkeypatch.setattr(routine_module, "run_directory_scan", fail_post_action_scan)

    report = execute_folder_routine(
        plan,
        approval,
        completed_at="2026-08-21T21:03:00Z",
        state_dir=state_dir,
        allow_file_write=True,
        allow_state_write=True,
    )

    assert report.status == "rolled_back"
    assert report.error == "Synthetischer Checkpointfehler."
    assert report.completed_file.name == "900-failed.json"
    assert source.read_text(encoding="utf-8") == "Synthetische Police"
    assert not (tmp_path / "Ablage").exists()
