from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from folderhome.application.document_action_plan import build_document_action_plan
from folderhome.application.policy_fcsa_plan import validate_fcsa_policy_actions
from folderhome.bridges.fcsa import FcsaDryRunBridge
from folderhome.contracts import (
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
from folderhome.plugin_host import load_manifests

REPO_ROOT = Path(__file__).parents[1]
FCSA_ROOT = REPO_ROOT.parent / "file-collect-sort-action"
MANIFEST_ROOT = REPO_ROOT / "manifests" / "components"


def _record(source: Path) -> DocumentRecord:
    source.write_text("Synthetisches Altdokument.", encoding="utf-8")
    source_hash = "b" * 64
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at="2020-01-01T00:00:00Z",
        text="Synthetisches Altdokument.",
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="Synthetisch.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )


def _policy(*rules: tuple[RuleKey, str | int]) -> ResolvedProfilePolicy:
    return ResolvedProfilePolicy(
        profile_id="lukas",
        display_name="Lukas",
        area="versicherung",
        os_account="synthetic",
        organizational_only=True,
        security_boundary="Organisationsprofil, keine Zugriffsgrenze.",
        rules=tuple(
            ResolvedProfileRule(
                key=key,
                value=value,
                scope=RuleScope.PROFILE_AREA,
                source_rule_ids=(f"rule_{index}",),
                overridden_rule_ids=(),
            )
            for index, (key, value) in enumerate(rules, start=1)
        ),
    )


def _bridge() -> FcsaDryRunBridge:
    plugin = next(
        item
        for item in load_manifests(MANIFEST_ROOT)
        if item.plugin_id == "file-collect-sort-action"
    )
    return FcsaDryRunBridge(plugin=plugin, provider_root=FCSA_ROOT)


@pytest.mark.skipif(not FCSA_ROOT.is_dir(), reason="pinned FCSA checkout unavailable")
@pytest.mark.parametrize(
    ("rules", "expected_actions"),
    (
        (
            (
                (RuleKey.ARCHIVE_AFTER_DAYS, 365),
                (RuleKey.ARCHIVE_FOLDER, "Archiv"),
            ),
            ("duplicate_check", "move"),
        ),
        (
            (
                (RuleKey.DELETE_AFTER_DAYS, 365),
                (RuleKey.DELETE_MODE, "recycle_bin"),
            ),
            ("delete",),
        ),
    ),
)
def test_archive_and_recycle_plans_are_confirmed_by_real_fcsa_dry_run(
    tmp_path: Path,
    rules: tuple[tuple[RuleKey, str | int], ...],
    expected_actions: tuple[str, ...],
) -> None:
    source = tmp_path / "Alt.txt"
    document = _record(source)
    before = source.read_bytes()
    target_root = tmp_path / "Ablage"
    plan = build_document_action_plan(
        document,
        _policy(*rules),
        target_root=target_root,
        as_of=date(2026, 8, 21),
    )

    validations = validate_fcsa_policy_actions(plan, bridge=_bridge())

    assert len(validations) == 1
    assert validations[0].action_id == plan.steps[0].action_id
    assert validations[0].provider_id == "file-collect-sort-action"
    assert validations[0].planned_actions == expected_actions
    assert validations[0].would_mutate_fs is True
    assert validations[0].gate_granted is False
    assert source.read_bytes() == before
    assert not target_root.exists()
