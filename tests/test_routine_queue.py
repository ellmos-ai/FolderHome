from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.directory_observation import (
    load_watched_folder_configuration,
    run_directory_scan,
)
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.routine_queue import (
    RoutineQueueError,
    build_folder_routine_queue,
    load_folder_routine_bindings,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)

REPO_ROOT = Path(__file__).parents[1]


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
            modified_at="2026-08-21T18:00:00Z",
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


def _write_watches(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {"schema": "folderhome.watched-folders.v1", "watches": entries}
        ),
        encoding="utf-8",
    )


def _watch_item(watch_id: str, source: Path) -> dict[str, object]:
    return {
        "watch_id": watch_id,
        "source_dir": str(source),
        "profile_id": "hanna",
        "area": "haushalt",
        "interval_minutes": 60,
        "recursive": True,
        "enabled": True,
    }


def _write_bindings(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {"schema": "folderhome.routine-bindings.v1", "bindings": entries}
        ),
        encoding="utf-8",
    )


def _binding(binding_id: str, watch_id: str, target: str) -> dict[str, object]:
    return {
        "binding_id": binding_id,
        "watch_id": watch_id,
        "target_dir": target,
        "mode": "changes",
        "enabled": True,
    }


def test_binding_configuration_resolves_relative_targets_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "routine-bindings.json"
    _write_bindings(
        path,
        [
            _binding("inbox_cleanup", "family_inbox", "Ablage"),
        ],
    )

    configuration = load_folder_routine_bindings(path)

    assert configuration.bindings[0].target_root == (tmp_path / "Ablage").resolve()
    assert configuration.bindings[0].mode.value == "changes"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["bindings"].append(
        _binding("second_cleanup", "family_inbox", "Andere-Ablage")
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RoutineQueueError, match="mehrfach"):
        load_folder_routine_bindings(path)


def test_queue_distinguishes_ready_not_due_empty_and_missing_binding(
    tmp_path: Path,
) -> None:
    roots = {
        name: tmp_path / name
        for name in ("Ready", "NotDue", "Empty", "Missing")
    }
    for root in roots.values():
        root.mkdir()
    (roots["Ready"] / "Neu.txt").write_text("Neu", encoding="utf-8")
    (roots["NotDue"] / "Alt.txt").write_text("Alt", encoding="utf-8")
    watches_file = tmp_path / "watches.json"
    _write_watches(
        watches_file,
        [
            _watch_item("ready_watch", roots["Ready"]),
            _watch_item("not_due_watch", roots["NotDue"]),
            _watch_item("empty_watch", roots["Empty"]),
            _watch_item("missing_watch", roots["Missing"]),
        ],
    )
    watches = load_watched_folder_configuration(watches_file)
    state_dir = tmp_path / "state"
    by_id = {watch.watch_id: watch for watch in watches.watches}
    run_directory_scan(
        by_id["not_due_watch"],
        captured_at="2026-08-21T20:30:00Z",
        state_dir=state_dir,
        allow_state_write=True,
    )
    run_directory_scan(
        by_id["empty_watch"],
        captured_at="2026-08-21T20:00:00Z",
        state_dir=state_dir,
        allow_state_write=True,
    )
    bindings_file = tmp_path / "bindings.json"
    _write_bindings(
        bindings_file,
        [
            _binding("ready_binding", "ready_watch", "Targets/Ready"),
            _binding("not_due_binding", "not_due_watch", "Targets/NotDue"),
            _binding("empty_binding", "empty_watch", "Targets/Empty"),
        ],
    )
    before_state = {
        path: path.read_bytes() for path in state_dir.rglob("*.json")
    }

    queue = build_folder_routine_queue(
        watches,
        load_folder_routine_bindings(bindings_file),
        profiles=load_profile_configuration(REPO_ROOT / "examples" / "profiles"),
        as_of=date(2026, 8, 21),
        captured_at="2026-08-21T21:01:00Z",
        state_dir=state_dir,
        extractor=SyntheticExtractor(),
    )

    items = {item.watch_id: item for item in queue.items}
    assert items["ready_watch"].status == "ready"
    assert items["ready_watch"].plan is not None
    assert items["not_due_watch"].status == "not_due"
    assert items["empty_watch"].status == "empty"
    assert items["missing_watch"].status == "blocked"
    assert items["missing_watch"].plan is None
    assert queue.summary == {
        "blocked": 1,
        "empty": 1,
        "not_due": 1,
        "ready": 1,
    }
    assert {path: path.read_bytes() for path in state_dir.rglob("*.json")} == (
        before_state
    )
    assert not (tmp_path / "Targets").exists()


def test_queue_blocks_cross_watch_target_collision(tmp_path: Path) -> None:
    first = tmp_path / "First"
    second = tmp_path / "Second"
    first.mkdir()
    second.mkdir()
    (first / "Police.txt").write_text("A", encoding="utf-8")
    (second / "Police.txt").write_text("B", encoding="utf-8")
    watches_file = tmp_path / "watches.json"
    _write_watches(
        watches_file,
        [
            _watch_item("first_watch", first),
            _watch_item("second_watch", second),
        ],
    )
    bindings_file = tmp_path / "bindings.json"
    _write_bindings(
        bindings_file,
        [
            _binding("first_binding", "first_watch", str(tmp_path / "Ablage")),
            _binding("second_binding", "second_watch", str(tmp_path / "Ablage")),
        ],
    )

    queue = build_folder_routine_queue(
        load_watched_folder_configuration(watches_file),
        load_folder_routine_bindings(bindings_file),
        profiles=load_profile_configuration(REPO_ROOT / "examples" / "profiles"),
        as_of=date(2026, 8, 21),
        captured_at="2026-08-21T21:01:00Z",
        state_dir=tmp_path / "state",
        extractor=SyntheticExtractor(),
    )

    assert {item.status for item in queue.items} == {"blocked"}
    assert all("gemeinsame Ziel" in item.reason for item in queue.items)
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / "Ablage").exists()
