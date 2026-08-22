from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from folderhome.application.directory_snapshot import (
    DirectorySnapshotError,
    build_directory_diff,
    build_learning_examples,
    read_directory_snapshot,
    snapshot_directory,
    write_directory_snapshot,
)
from folderhome.capabilities.resource_budget import DEFAULT_RESOURCE_POLICY
from folderhome.contracts import DirectoryChangeKind, PlacementReceipt


def test_snapshot_contains_only_sorted_metadata_and_hashes(tmp_path: Path) -> None:
    root = tmp_path / "Dokumente"
    nested = root / "Unterordner"
    nested.mkdir(parents=True)
    first = root / "B.txt"
    second = nested / "A.txt"
    first.write_text("Geheimer Rohtext B.", encoding="utf-8")
    second.write_text("Geheimer Rohtext A.", encoding="utf-8")
    state_dir = tmp_path / "state"

    snapshot = snapshot_directory(
        root,
        captured_at="2026-08-21T20:30:00Z",
    )

    assert [entry.relative_path for entry in snapshot.files] == [
        "B.txt",
        "Unterordner/A.txt",
    ]
    assert all(len(entry.source_sha256) == 64 for entry in snapshot.files)
    assert not state_dir.exists()
    payload = snapshot.to_dict()
    assert payload["schema"] == "folderhome.directory-snapshot.v1"
    assert "Geheimer Rohtext" not in str(payload)
    assert all("text" not in entry for entry in payload["files"])


def test_diff_detects_move_modify_remove_add_and_metadata_change(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Dokumente"
    root.mkdir()
    moved = root / "Eingang" / "Police.txt"
    moved.parent.mkdir()
    modified = root / "Bearbeiten.txt"
    removed = root / "Entfernt.txt"
    metadata = root / "Metadaten.txt"
    moved.write_text("Gleicher Inhalt.", encoding="utf-8")
    modified.write_text("Vorher.", encoding="utf-8")
    removed.write_text("Wird entfernt.", encoding="utf-8")
    metadata.write_text("Inhalt bleibt.", encoding="utf-8")
    before = snapshot_directory(root, captured_at="2026-08-21T20:30:00Z")

    corrected = root / "Versicherungen" / "Police.txt"
    corrected.parent.mkdir()
    moved.rename(corrected)
    modified.write_text("Nachher.", encoding="utf-8")
    removed.unlink()
    added = root / "Neu.txt"
    added.write_text("Neu hinzugefügt.", encoding="utf-8")
    old_stat = metadata.stat()
    os.utime(
        metadata,
        ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 1_000_000_000),
    )
    after = snapshot_directory(root, captured_at="2026-08-21T20:31:00Z")

    diff = build_directory_diff(before, after)

    assert {change.kind for change in diff.changes} == {
        DirectoryChangeKind.ADDED,
        DirectoryChangeKind.METADATA_CHANGED,
        DirectoryChangeKind.MODIFIED,
        DirectoryChangeKind.MOVED,
        DirectoryChangeKind.REMOVED,
    }
    move = next(
        change for change in diff.changes if change.kind is DirectoryChangeKind.MOVED
    )
    assert move.before_path == "Eingang/Police.txt"
    assert move.after_path == "Versicherungen/Police.txt"
    assert move.confidence == "high"
    assert move.before_sha256 == move.after_sha256
    assert "text" not in diff.to_dict()


def test_ambiguous_duplicate_hashes_are_not_claimed_as_moves(tmp_path: Path) -> None:
    root = tmp_path / "Dokumente"
    old = root / "Alt"
    old.mkdir(parents=True)
    for name in ("A.txt", "B.txt"):
        (old / name).write_text("Identischer Inhalt.", encoding="utf-8")
    before = snapshot_directory(root, captured_at="2026-08-21T20:30:00Z")
    new = root / "Neu"
    new.mkdir()
    for source in sorted(old.iterdir()):
        source.rename(new / source.name)
    old.rmdir()
    after = snapshot_directory(root, captured_at="2026-08-21T20:31:00Z")

    diff = build_directory_diff(before, after)

    assert all(change.kind is not DirectoryChangeKind.MOVED for change in diff.changes)
    assert sum(change.kind is DirectoryChangeKind.ADDED for change in diff.changes) == 2
    assert sum(change.kind is DirectoryChangeKind.REMOVED for change in diff.changes) == 2


def test_manual_move_after_placement_becomes_candidate_not_automatic_rule(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Dokumente"
    planned = root / "Eingang" / "Police.txt"
    planned.parent.mkdir(parents=True)
    planned.write_text("Gleicher Inhalt.", encoding="utf-8")
    before = snapshot_directory(root, captured_at="2026-08-21T20:30:00Z")
    corrected = root / "Versicherungen" / "KFZ" / "Police.txt"
    corrected.parent.mkdir(parents=True)
    planned.rename(corrected)
    after = snapshot_directory(root, captured_at="2026-08-21T20:31:00Z")
    move = next(
        change
        for change in build_directory_diff(before, after).changes
        if change.kind is DirectoryChangeKind.MOVED
    )
    receipt = PlacementReceipt(
        receipt_id="receipt_policy",
        document_sha256=move.before_sha256,
        placed_path="Eingang/Police.txt",
        profile_id="lukas",
        area="versicherungen",
        source_rule_ids=("rule_sort_inbox",),
    )

    examples = build_learning_examples(
        build_directory_diff(before, after),
        (receipt,),
    )

    assert len(examples) == 1
    assert examples[0].corrected_path == "Versicherungen/KFZ/Police.txt"
    assert examples[0].status == "candidate"
    assert examples[0].automatic_promotion is False
    assert examples[0].source_rule_ids == ("rule_sort_inbox",)


def test_ambiguous_placement_receipts_do_not_create_learning_example(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Dokumente"
    placed = root / "Eingang" / "Police.txt"
    placed.parent.mkdir(parents=True)
    placed.write_text("Gleicher Inhalt.", encoding="utf-8")
    before = snapshot_directory(root, captured_at="2026-08-21T20:30:00Z")
    corrected = root / "Versicherungen" / "Police.txt"
    corrected.parent.mkdir()
    placed.rename(corrected)
    after = snapshot_directory(root, captured_at="2026-08-21T20:31:00Z")
    source_hash = before.files[0].source_sha256
    receipts = tuple(
        PlacementReceipt(
            receipt_id=receipt_id,
            document_sha256=source_hash,
            placed_path="Eingang/Police.txt",
            profile_id="lukas",
            area="versicherungen",
            source_rule_ids=("rule_sort_inbox",),
        )
        for receipt_id in ("receipt_a", "receipt_b")
    )

    examples = build_learning_examples(build_directory_diff(before, after), receipts)

    assert examples == ()


def test_snapshot_history_write_requires_gate_and_never_overwrites(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Dokumente"
    root.mkdir()
    (root / "A.txt").write_text("Synthetisch.", encoding="utf-8")
    snapshot = snapshot_directory(root, captured_at="2026-08-21T20:30:00Z")
    state_dir = tmp_path / "state"

    with pytest.raises(DirectorySnapshotError, match="Schreibfreigabe"):
        write_directory_snapshot(snapshot, state_dir, allow_state_write=False)
    assert not state_dir.exists()

    written = write_directory_snapshot(snapshot, state_dir, allow_state_write=True)

    assert written.is_file()
    assert read_directory_snapshot(written) == snapshot
    with pytest.raises(DirectorySnapshotError, match="existiert bereits"):
        write_directory_snapshot(snapshot, state_dir, allow_state_write=True)


def test_snapshot_rejects_source_tree_over_resource_budget(tmp_path: Path) -> None:
    root = tmp_path / "Dokumente"
    root.mkdir()
    (root / "A.txt").write_bytes(b"1234")
    (root / "B.txt").write_bytes(b"5678")
    policy = replace(
        DEFAULT_RESOURCE_POLICY,
        max_file_bytes=7,
        max_total_source_bytes=7,
    )

    with pytest.raises(DirectorySnapshotError, match="Gesamtquellgrößen-Budget"):
        snapshot_directory(
            root,
            captured_at="2026-08-21T20:30:00Z",
            resource_policy=policy,
        )
