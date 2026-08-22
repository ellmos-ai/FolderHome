from __future__ import annotations

from pathlib import Path

import pytest

from folderhome.application.archive_fcsa_plan import validate_archive_proposals
from folderhome.application.document_versions import (
    build_archive_proposals,
    build_document_family,
)
from folderhome.bridges.fcsa import FcsaDryRunBridge
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)
from folderhome.plugin_host import load_manifests

REPO_ROOT = Path(__file__).parents[1]
FCSA_ROOT = REPO_ROOT.parent / "file-collect-sort-action"
MANIFEST_ROOT = REPO_ROOT / "manifests" / "components"


def _record(source: Path, *, text: str, source_hash: str) -> DocumentRecord:
    source.write_text(text, encoding="utf-8")
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at="2026-01-02T12:00:00Z",
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=PrivacyStatus.CLEAR,
        privacy_summary="Synthetisch.",
        index_status=IndexStatus.INDEXED,
        index_provider="KnowledgeDigest",
        index_ref=f"knowledge://documents/{source_hash}",
    )


@pytest.mark.skipif(not FCSA_ROOT.is_dir(), reason="pinned FCSA checkout unavailable")
def test_archive_proposal_is_validated_by_real_fcsa_without_moving_files(
    tmp_path: Path,
) -> None:
    old = _record(
        tmp_path / "Police_2025.txt",
        text="Gültig ab 01.01.2025. Synthetische alte Police.",
        source_hash="a" * 64,
    )
    new = _record(
        tmp_path / "Police_2026.txt",
        text="Gültig ab 01.01.2026. Synthetische neue Police.",
        source_hash="b" * 64,
    )
    family = build_document_family("KFZ Hyundai i10", (old, new))
    proposals = build_archive_proposals(family)
    plugin = next(
        item
        for item in load_manifests(MANIFEST_ROOT)
        if item.plugin_id == "file-collect-sort-action"
    )
    bridge = FcsaDryRunBridge(plugin=plugin, provider_root=FCSA_ROOT)

    plans = validate_archive_proposals(proposals, bridge=bridge)

    assert len(plans) == 1
    assert plans[0].document_id == old.document_id
    assert plans[0].provider_id == "file-collect-sort-action"
    assert plans[0].source_path == old.source_path
    assert plans[0].target_directory == old.source_path.parent / "Archiv"
    assert plans[0].planned_actions == ("duplicate_check", "move")
    assert plans[0].would_mutate_fs is True
    assert plans[0].gate_granted is False
    assert old.source_path.exists() and new.source_path.exists()
    assert not (tmp_path / "Archiv").exists()
