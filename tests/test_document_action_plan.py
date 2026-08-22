from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.document_action_plan import (
    DocumentActionPlanError,
    build_document_action_plan,
    release_original_handling,
)
from folderhome.contracts import (
    ContentFormat,
    DocumentBundleResult,
    DocumentRecord,
    IndexStatus,
    PolicyActionKind,
    PolicyActionStatus,
    PrivacyStatus,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    RuleScope,
    SideEffect,
    build_document_id,
)


def _record(source: Path, *, modified_at: str = "2026-01-15T10:30:00Z") -> DocumentRecord:
    source.write_text("Synthetischer Versicherungsinhalt.", encoding="utf-8")
    source_hash = "a" * 64
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at=modified_at,
        text="Synthetischer Versicherungsinhalt.",
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="Synthetischer Datenschutzstatus.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )


def _rule(
    key: RuleKey,
    value: str | int | bool,
    *,
    source_id: str,
    scope: RuleScope = RuleScope.PROFILE_AREA,
) -> ResolvedProfileRule:
    return ResolvedProfileRule(
        key=key,
        value=value,
        scope=scope,
        source_rule_ids=(source_id,),
        overridden_rule_ids=(f"old_{source_id}",),
    )


def _policy(*rules: ResolvedProfileRule) -> ResolvedProfilePolicy:
    return ResolvedProfilePolicy(
        profile_id="lukas",
        display_name="Lukas",
        area="versicherung",
        os_account="ASUS-GEI\\User",
        organizational_only=True,
        security_boundary="Organisationsprofil, keine Zugriffsgrenze.",
        rules=rules,
    )


def test_naming_sorting_and_conversion_are_only_planned_with_rule_provenance(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Eingang" / "Police alt.txt"
    source.parent.mkdir()
    document = _record(source)
    before = source.read_bytes()
    target_root = tmp_path / "Ablage"
    policy = _policy(
        _rule(
            RuleKey.NAMING_TEMPLATE,
            "{date}_{name}_{profile}.{ext}",
            source_id="lukas_versicherung_name",
        ),
        _rule(
            RuleKey.SORT_TARGET,
            "Versicherungen/KFZ",
            source_id="lukas_versicherung_sort",
        ),
        _rule(RuleKey.FORMAT_REQUIRED, "pdf", source_id="global_format"),
        _rule(
            RuleKey.CONVERSION_ORIGINAL,
            "gardener_storage",
            source_id="global_original",
        ),
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=target_root,
        as_of=date(2026, 8, 21),
    )

    assert [step.kind for step in plan.steps] == [
        PolicyActionKind.RENAME,
        PolicyActionKind.SORT,
        PolicyActionKind.CONVERT,
        PolicyActionKind.HANDLE_ORIGINAL,
    ]
    assert plan.steps[0].target_path.name == "2026-01-15_Police alt_lukas.txt"
    assert plan.steps[1].target_path == (
        target_root / "Versicherungen" / "KFZ" / plan.steps[0].target_path.name
    ).resolve()
    assert plan.steps[2].status is PolicyActionStatus.PLANNED
    assert plan.steps[2].provider_id == "folderhome.document-transform"
    assert plan.steps[3].status is PolicyActionStatus.BLOCKED
    assert all(step.gate.required for step in plan.steps)
    assert all(step.gate.granted is False for step in plan.steps)
    assert all(step.side_effects == (SideEffect.FILESYSTEM_WRITE,) for step in plan.steps)
    assert plan.steps[0].rules[0].source_rule_ids == ("lukas_versicherung_name",)
    assert plan.steps[0].rules[0].overridden_rule_ids == (
        "old_lukas_versicherung_name",
    )
    assert source.read_bytes() == before
    assert not target_root.exists()
    serialized = plan.to_dict()
    assert "text" not in serialized["document"]
    assert serialized["schema"] == "folderhome.document-policy-action-plan.v1"
    assert serialized["plan_id"] == plan.plan_id
    assert plan.plan_id.startswith("plan_")


def test_due_archive_is_planned_for_fcsa_without_creating_archive_directory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    document = _record(source, modified_at="2024-01-01T00:00:00Z")
    target_root = tmp_path / "Ablage"
    policy = _policy(
        _rule(RuleKey.ARCHIVE_AFTER_DAYS, 365, source_id="archive_age"),
        _rule(RuleKey.ARCHIVE_FOLDER, "Archiv", source_id="archive_folder"),
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=target_root,
        as_of=date(2026, 8, 21),
    )

    assert len(plan.steps) == 1
    action = plan.steps[0]
    assert action.kind is PolicyActionKind.ARCHIVE
    assert action.status is PolicyActionStatus.PLANNED
    assert action.provider_id == "file-collect-sort-action"
    assert action.capability_id == "move"
    assert action.target_path == (target_root / "Archiv" / source.name).resolve()
    assert action.undo.supported is True
    assert action.undo.action == "move-back-to-source"
    assert {rule.key for rule in action.rules} == {
        RuleKey.ARCHIVE_AFTER_DAYS,
        RuleKey.ARCHIVE_FOLDER,
    }
    assert source.exists()
    assert not target_root.exists()


def test_unsupported_output_format_remains_visibly_blocked(tmp_path: Path) -> None:
    source = tmp_path / "Police.txt"
    document = _record(source)
    policy = _policy(
        _rule(RuleKey.FORMAT_REQUIRED, "docx", source_id="docx_format")
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )

    assert plan.steps[0].kind is PolicyActionKind.CONVERT
    assert plan.steps[0].status is PolicyActionStatus.BLOCKED
    assert plan.steps[0].provider_id is None
    assert "kein geprüfter Provider" in plan.steps[0].message


def test_verified_transform_result_releases_only_original_handling(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    document = _record(source)
    policy = _policy(
        _rule(RuleKey.FORMAT_REQUIRED, "pdf", source_id="pdf_format"),
        _rule(
            RuleKey.CONVERSION_ORIGINAL,
            "gardener_storage",
            source_id="original_storage",
        ),
    )
    plan = build_document_action_plan(
        document,
        policy,
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )
    converted = source.with_suffix(".pdf")
    converted.write_bytes(b"synthetic converted output")
    output_hash = sha256(converted.read_bytes()).hexdigest()
    result = DocumentBundleResult(
        bundle_id="bundle_synthetic",
        provider_id="folderhome.document-transform",
        output_path=converted,
        output_sha256=output_hash,
        output_size_bytes=converted.stat().st_size,
        page_count=1,
        source_document_ids=(document.document_id,),
    )

    released = release_original_handling(plan, result)

    assert released.steps[0].kind is PolicyActionKind.CONVERT
    assert released.steps[0].status is PolicyActionStatus.PLANNED
    assert released.steps[1].kind is PolicyActionKind.HANDLE_ORIGINAL
    assert released.steps[1].status is PolicyActionStatus.PLANNED
    assert "nachgewiesen" in released.steps[1].message


def test_naming_template_without_ext_placeholder_preserves_source_extension(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    document = _record(source)
    policy = _policy(
        _rule(
            RuleKey.NAMING_TEMPLATE,
            "{date}_{name}",
            source_id="global_name",
        )
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )

    assert plan.steps[0].target_path.name == "2026-01-15_Police.txt"


def test_default_lifecycle_rules_without_durations_are_valid_noop(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    document = _record(source)
    policy = _policy(
        _rule(RuleKey.ARCHIVE_FOLDER, "Archiv", source_id="archive_folder"),
        _rule(RuleKey.DELETE_MODE, "review_only", source_id="delete_mode"),
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )

    assert plan.steps == ()


def test_review_only_deletion_creates_non_mutating_review_step(tmp_path: Path) -> None:
    source = tmp_path / "Alt.txt"
    document = _record(source, modified_at="2020-01-01T00:00:00Z")
    policy = _policy(
        _rule(RuleKey.DELETE_AFTER_DAYS, 365, source_id="delete_age"),
        _rule(RuleKey.DELETE_MODE, "review_only", source_id="delete_mode"),
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )

    assert len(plan.steps) == 1
    action = plan.steps[0]
    assert action.kind is PolicyActionKind.REVIEW
    assert action.status is PolicyActionStatus.REVIEW_REQUIRED
    assert action.side_effects == ()
    assert action.gate.required is True
    assert action.gate.granted is False
    assert action.undo.supported is False
    assert source.exists()


def test_archive_and_recycle_conflict_fails_closed_in_visible_plan(tmp_path: Path) -> None:
    source = tmp_path / "Alt.txt"
    document = _record(source, modified_at="2020-01-01T00:00:00Z")
    policy = _policy(
        _rule(RuleKey.ARCHIVE_AFTER_DAYS, 365, source_id="archive_age"),
        _rule(RuleKey.ARCHIVE_FOLDER, "Archiv", source_id="archive_folder"),
        _rule(RuleKey.DELETE_AFTER_DAYS, 730, source_id="delete_age"),
        _rule(RuleKey.DELETE_MODE, "recycle_bin", source_id="delete_mode"),
    )

    plan = build_document_action_plan(
        document,
        policy,
        target_root=tmp_path / "Ablage",
        as_of=date(2026, 8, 21),
    )

    assert [step.kind for step in plan.steps] == [
        PolicyActionKind.ARCHIVE,
        PolicyActionKind.RECYCLE,
        PolicyActionKind.REVIEW,
    ]
    assert all(step.status is PolicyActionStatus.BLOCKED for step in plan.steps[:2])
    assert plan.steps[2].status is PolicyActionStatus.REVIEW_REQUIRED
    assert "Konflikt" in plan.steps[2].message
    assert source.exists()


@pytest.mark.parametrize(
    "template",
    (
        "../{name}.{ext}",
        "{name}/{profile}.{ext}",
        "{unknown}_{name}.{ext}",
        "{name}:illegal.{ext}",
    ),
)
def test_unsafe_naming_template_fails_closed_without_source_change(
    tmp_path: Path,
    template: str,
) -> None:
    source = tmp_path / "Eingang.txt"
    document = _record(source)
    before = source.read_bytes()
    policy = _policy(
        _rule(RuleKey.NAMING_TEMPLATE, template, source_id="unsafe_name")
    )

    with pytest.raises(DocumentActionPlanError):
        build_document_action_plan(
            document,
            policy,
            target_root=tmp_path / "Ablage",
            as_of=date(2026, 8, 21),
        )

    assert source.read_bytes() == before
    assert not (tmp_path / "Ablage").exists()
