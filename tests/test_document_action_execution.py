from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.document_action_execution import (
    DocumentActionExecutionError,
    execute_document_actions,
    read_action_execution_report,
    undo_document_actions,
)
from folderhome.application.document_action_plan import build_document_action_plan
from folderhome.contracts import (
    ActionExecutionApproval,
    ActionUndoApproval,
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    RuleScope,
    build_document_id,
)


def _record(source: Path) -> DocumentRecord:
    source_hash = sha256(source.read_bytes()).hexdigest()
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at="2026-01-15T10:30:00Z",
        text="Synthetischer Versicherungsinhalt.",
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
        area="versicherungen",
        os_account="synthetic",
        organizational_only=True,
        security_boundary="Organisationsprofil, keine Zugriffsgrenze.",
        rules=(
            ResolvedProfileRule(
                key=RuleKey.NAMING_TEMPLATE,
                value="{date}_{name}",
                scope=RuleScope.PROFILE_AREA,
                source_rule_ids=("rule_name",),
                overridden_rule_ids=(),
            ),
            ResolvedProfileRule(
                key=RuleKey.SORT_TARGET,
                value="Versicherungen/KFZ",
                scope=RuleScope.PROFILE_AREA,
                source_rule_ids=("rule_sort",),
                overridden_rule_ids=(),
            ),
        ),
    )


def _plan(tmp_path: Path):
    source = tmp_path / "Eingang" / "Police.txt"
    source.parent.mkdir(parents=True)
    source.write_text("Synthetischer Versicherungsinhalt.", encoding="utf-8")
    return build_document_action_plan(
        _record(source),
        _policy(),
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )


def _approval(plan) -> ActionExecutionApproval:
    return ActionExecutionApproval(
        approval_id="approval_phase11",
        plan_id=plan.plan_id,
        action_ids=tuple(step.action_id for step in plan.steps),
        document_sha256=plan.document.source_sha256,
        approved_at="2026-08-21T21:00:00Z",
    )


def test_execution_requires_exact_plan_and_explicit_gate(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    source = plan.document.source_path
    before = source.read_bytes()
    approval = _approval(plan)

    with pytest.raises(DocumentActionExecutionError, match="Schreibfreigabe"):
        execute_document_actions(
            plan,
            approval,
            state_dir=tmp_path / "state",
            allow_file_write=False,
        )
    with pytest.raises(DocumentActionExecutionError, match="Plan-ID"):
        execute_document_actions(
            plan,
            ActionExecutionApproval(
                approval_id="approval_wrong",
                plan_id="plan_" + "0" * 64,
                action_ids=approval.action_ids,
                document_sha256=approval.document_sha256,
                approved_at=approval.approved_at,
            ),
            state_dir=tmp_path / "state",
            allow_file_write=True,
        )

    assert source.read_bytes() == before
    assert not (tmp_path / "state").exists()
    assert not plan.target_root.exists()


def test_rename_sort_execute_and_undo_roundtrip_is_hash_bound(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    approval = _approval(plan)
    original = plan.document.source_path
    before = original.read_bytes()

    report = execute_document_actions(
        plan,
        approval,
        state_dir=tmp_path / "state",
        allow_file_write=True,
    )

    final_target = plan.steps[-1].target_path
    assert final_target is not None
    assert not original.exists()
    assert final_target.read_bytes() == before
    assert report.status == "executed"
    assert report.plan_id == plan.plan_id
    assert report.final_target == final_target
    assert report.placement_receipt.root_path == plan.target_root
    assert report.placement_receipt.placed_path == (
        "Versicherungen/KFZ/2026-01-15_Police.txt"
    )
    assert [step.executor_id for step in report.steps] == [
        "folderhome.filesystem-transaction",
        "folderhome.filesystem-transaction",
    ]
    assert report.completed_file.is_file()
    assert "Synthetischer Versicherungsinhalt" not in str(report.to_dict())
    loaded = read_action_execution_report(report.completed_file)
    assert loaded == report

    undo = undo_document_actions(
        loaded,
        ActionUndoApproval(
            approval_id="undo_phase11",
            execution_id=report.execution_id,
            document_sha256=plan.document.source_sha256,
            approved_at="2026-08-21T21:01:00Z",
        ),
        allow_file_write=True,
    )

    assert undo.status == "undone"
    assert original.read_bytes() == before
    assert not final_target.exists()
    assert undo.completed_file.is_file()


def test_execution_refuses_changed_source_before_writing_audit(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    source = plan.document.source_path
    source.write_text("Nach der Planung geändert.", encoding="utf-8")

    with pytest.raises(DocumentActionExecutionError, match="Quellhash"):
        execute_document_actions(
            plan,
            _approval(plan),
            state_dir=tmp_path / "state",
            allow_file_write=True,
        )

    assert source.read_text(encoding="utf-8") == "Nach der Planung geändert."
    assert not (tmp_path / "state").exists()


def test_existing_final_target_blocks_entire_chain_without_overwrite(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    original = plan.document.source_path
    before = original.read_bytes()
    final_target = plan.steps[-1].target_path
    assert final_target is not None
    final_target.parent.mkdir(parents=True)
    final_target.write_text("Fremde Zieldatei.", encoding="utf-8")
    foreign = final_target.read_bytes()

    with pytest.raises(DocumentActionExecutionError, match="Ziel existiert"):
        execute_document_actions(
            plan,
            _approval(plan),
            state_dir=tmp_path / "state",
            allow_file_write=True,
        )

    assert original.read_bytes() == before
    assert final_target.read_bytes() == foreign
    assert not (tmp_path / "state").exists()


def test_tampered_completed_report_is_rejected_against_immutable_intent(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    report = execute_document_actions(
        plan,
        _approval(plan),
        state_dir=tmp_path / "state",
        allow_file_write=True,
    )
    payload = json.loads(report.completed_file.read_text(encoding="utf-8"))
    decoy = tmp_path / "Täuschung.txt"
    decoy.write_bytes(report.final_target.read_bytes())
    payload["final_target"] = str(decoy)
    payload["steps"][-1]["target_path"] = str(decoy)
    report.completed_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DocumentActionExecutionError, match="Intent"):
        read_action_execution_report(report.completed_file)


def test_undo_refuses_changed_final_hash_without_writing_intent(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    report = execute_document_actions(
        plan,
        _approval(plan),
        state_dir=tmp_path / "state",
        allow_file_write=True,
    )
    report.final_target.write_text("Nach der Ausführung geändert.", encoding="utf-8")

    with pytest.raises(DocumentActionExecutionError, match="Zielhash"):
        undo_document_actions(
            report,
            ActionUndoApproval(
                approval_id="undo_changed",
                execution_id=report.execution_id,
                document_sha256=report.document_sha256,
                approved_at="2026-08-21T21:01:00Z",
            ),
            allow_file_write=True,
        )

    assert not (report.completed_file.parent / "200-undo-intent.json").exists()
