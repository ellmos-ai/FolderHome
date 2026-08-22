from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

import folderhome.application.folder_cleanup as cleanup_module
from folderhome.application.folder_cleanup import (
    FolderCleanupError,
    build_folder_cleanup_plan,
    execute_folder_cleanup,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.contracts import (
    BatchItemApproval,
    ContentFormat,
    DocumentRecord,
    FolderCleanupApproval,
    IndexStatus,
    PrivacyStatus,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    RuleScope,
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


def test_cleanup_plan_is_deterministic_and_keeps_unsupported_visible(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Los"
    source_root.mkdir()
    (source_root / "B.txt").write_text("B", encoding="utf-8")
    (source_root / "A.txt").write_text("A", encoding="utf-8")
    (source_root / "Roh.bin").write_bytes(b"raw")
    before = {path: path.read_bytes() for path in source_root.iterdir()}

    first = build_folder_cleanup_plan(
        source_root,
        policy=_policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
        extractor=SyntheticExtractor(),
    )
    second = build_folder_cleanup_plan(
        source_root,
        policy=_policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
        extractor=SyntheticExtractor(),
    )

    assert first == second
    assert first.batch_id.startswith("cleanup_")
    assert [item.relative_path for item in first.items] == [
        "A.txt",
        "B.txt",
        "Roh.bin",
    ]
    assert [item.status for item in first.items] == ["planned", "planned", "skipped"]
    assert first.items[-1].source_sha256 == sha256(b"raw").hexdigest()
    assert "raw" not in str(first.to_dict())
    assert {path: path.read_bytes() for path in source_root.iterdir()} == before
    assert not (tmp_path / "Ablage").exists()


def test_cleanup_plan_blocks_cross_document_target_collision(tmp_path: Path) -> None:
    source_root = tmp_path / "Los"
    (source_root / "A").mkdir(parents=True)
    (source_root / "B").mkdir()
    (source_root / "A" / "Police.txt").write_text("A", encoding="utf-8")
    (source_root / "B" / "Police.txt").write_text("B", encoding="utf-8")

    plan = build_folder_cleanup_plan(
        source_root,
        policy=_policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
        extractor=SyntheticExtractor(),
    )

    assert len(plan.conflicts) == 1
    assert plan.conflicts[0].kind == "duplicate_target"
    assert {item.status for item in plan.items} == {"blocked"}
    assert (source_root / "A" / "Police.txt").is_file()
    assert (source_root / "B" / "Police.txt").is_file()


def test_selective_batch_execution_moves_only_approved_document(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Los"
    source_root.mkdir()
    first_source = source_root / "A.txt"
    second_source = source_root / "B.txt"
    first_source.write_text("A", encoding="utf-8")
    second_source.write_text("B", encoding="utf-8")
    plan = build_folder_cleanup_plan(
        source_root,
        policy=_policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
        extractor=SyntheticExtractor(),
    )
    first_item = plan.items[0]
    assert first_item.action_plan is not None
    approval = FolderCleanupApproval(
        approval_id="cleanup_approval",
        batch_id=plan.batch_id,
        items=(
            BatchItemApproval(
                document_id=first_item.document_id,
                plan_id=first_item.action_plan.plan_id,
                document_sha256=first_item.source_sha256,
                action_ids=first_item.executable_action_ids,
            ),
        ),
        approved_at="2026-08-21T21:10:00Z",
    )

    with pytest.raises(FolderCleanupError, match="Schreibfreigabe"):
        execute_folder_cleanup(
            plan,
            approval,
            state_dir=tmp_path / "state",
            allow_file_write=False,
        )
    assert not (tmp_path / "state").exists()
    assert first_source.is_file()
    assert second_source.is_file()

    report = execute_folder_cleanup(
        plan,
        approval,
        state_dir=tmp_path / "state",
        allow_file_write=True,
    )

    assert report.status == "executed"
    assert len(report.executions) == 1
    assert len(report.placement_receipts) == 1
    assert not first_source.exists()
    assert (tmp_path / "Ablage" / "Sortiert" / "A.txt").read_text(
        encoding="utf-8"
    ) == "A"
    assert second_source.read_text(encoding="utf-8") == "B"
    assert report.completed_file.is_file()


def test_batch_execution_rejects_conflicted_or_mismatched_selection_before_state_write(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Los"
    (source_root / "A").mkdir(parents=True)
    (source_root / "B").mkdir()
    (source_root / "A" / "Police.txt").write_text("A", encoding="utf-8")
    (source_root / "B" / "Police.txt").write_text("B", encoding="utf-8")
    plan = build_folder_cleanup_plan(
        source_root,
        policy=_policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
        extractor=SyntheticExtractor(),
    )
    item = plan.items[0]
    assert item.action_plan is not None
    approval = FolderCleanupApproval(
        approval_id="cleanup_conflict",
        batch_id=plan.batch_id,
        items=(
            BatchItemApproval(
                document_id=item.document_id,
                plan_id=item.action_plan.plan_id,
                document_sha256=item.source_sha256,
                action_ids=item.executable_action_ids,
            ),
        ),
        approved_at="2026-08-21T21:10:00Z",
    )

    with pytest.raises(FolderCleanupError, match="Konflikt"):
        execute_folder_cleanup(
            plan,
            approval,
            state_dir=tmp_path / "state",
            allow_file_write=True,
        )

    assert not (tmp_path / "state").exists()
    assert (source_root / "A" / "Police.txt").is_file()
    assert (source_root / "B" / "Police.txt").is_file()


def test_batch_failure_rolls_back_already_completed_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "Los"
    source_root.mkdir()
    sources = (source_root / "A.txt", source_root / "B.txt")
    for source, content in zip(sources, ("A", "B"), strict=True):
        source.write_text(content, encoding="utf-8")
    plan = build_folder_cleanup_plan(
        source_root,
        policy=_policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
        extractor=SyntheticExtractor(),
    )
    selected = [item for item in plan.items if item.status == "planned"]
    approval = FolderCleanupApproval(
        approval_id="cleanup_rollback",
        batch_id=plan.batch_id,
        items=tuple(
            BatchItemApproval(
                document_id=item.document_id,
                plan_id=item.action_plan.plan_id,
                document_sha256=item.source_sha256,
                action_ids=item.executable_action_ids,
            )
            for item in selected
            if item.document_id is not None and item.action_plan is not None
        ),
        approved_at="2026-08-21T21:10:00Z",
    )
    real_execute = cleanup_module.execute_document_actions
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FolderCleanupError("Synthetischer Fehler im zweiten Dokument.")
        return real_execute(*args, **kwargs)

    monkeypatch.setattr(cleanup_module, "execute_document_actions", fail_second)

    report = execute_folder_cleanup(
        plan,
        approval,
        state_dir=tmp_path / "state",
        allow_file_write=True,
    )

    assert report.status == "rolled_back"
    assert report.completed_file.name == "900-failed.json"
    assert report.completed_file.is_file()
    assert all(source.is_file() for source in sources)
    assert not (tmp_path / "Ablage").exists()
