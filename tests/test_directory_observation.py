from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.application.directory_observation import (
    DirectoryObservationError,
    load_watched_folder_configuration,
    run_directory_scan,
)
from folderhome.contracts import DirectoryChangeKind, PlacementReceipt


def _write_config(path: Path, source_dir: Path, *, enabled: bool = True) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.watched-folders.v1",
                "watches": [
                    {
                        "watch_id": "family_inbox",
                        "source_dir": str(source_dir),
                        "profile_id": "lukas",
                        "area": "versicherungen",
                        "interval_minutes": 60,
                        "recursive": True,
                        "enabled": enabled,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_watch_configuration_resolves_paths_and_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Dokumente"
    source.mkdir()
    config_file = tmp_path / "watched-folders.json"
    _write_config(config_file, Path("Dokumente"))

    configuration = load_watched_folder_configuration(config_file)

    assert configuration.watches[0].source_root == source.resolve()
    assert configuration.watches[0].interval_minutes == 60
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    payload["watches"].append(dict(payload["watches"][0]))
    config_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DirectoryObservationError, match="nicht eindeutig"):
        load_watched_folder_configuration(config_file)


def test_scan_without_gate_is_read_only_and_reports_initial_state(tmp_path: Path) -> None:
    source = tmp_path / "Dokumente"
    source.mkdir()
    document = source / "Police.txt"
    document.write_text("Synthetischer Inhalt.", encoding="utf-8")
    before_bytes = document.read_bytes()
    config_file = tmp_path / "watched-folders.json"
    _write_config(config_file, source)
    watch = load_watched_folder_configuration(config_file).watches[0]
    state_dir = tmp_path / "state"

    report = run_directory_scan(
        watch,
        captured_at="2026-08-21T20:40:00Z",
        state_dir=state_dir,
        allow_state_write=False,
    )

    assert report.previous_snapshot_id is None
    assert report.diff is None
    assert report.checkpoint_file is None
    assert report.gate.required is True
    assert report.gate.granted is False
    assert not state_dir.exists()
    assert document.read_bytes() == before_bytes
    assert "Synthetischer Inhalt" not in str(report.to_dict())


def test_two_gated_scans_diff_and_create_only_evidenced_learning_candidate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Dokumente"
    placed = source / "Eingang" / "Police.txt"
    placed.parent.mkdir(parents=True)
    placed.write_text("Unveränderter Inhalt.", encoding="utf-8")
    before_bytes = placed.read_bytes()
    config_file = tmp_path / "watched-folders.json"
    _write_config(config_file, source)
    watch = load_watched_folder_configuration(config_file).watches[0]
    state_dir = tmp_path / "state"
    first = run_directory_scan(
        watch,
        captured_at="2026-08-21T20:40:00Z",
        state_dir=state_dir,
        allow_state_write=True,
    )
    source_hash = first.snapshot.files[0].source_sha256
    corrected = source / "Versicherungen" / "Police.txt"
    corrected.parent.mkdir()
    placed.rename(corrected)
    receipt = PlacementReceipt(
        receipt_id="receipt_policy",
        document_sha256=source_hash,
        placed_path="Eingang/Police.txt",
        profile_id="lukas",
        area="versicherungen",
        source_rule_ids=("rule_sort_inbox",),
    )

    second = run_directory_scan(
        watch,
        captured_at="2026-08-21T20:41:00Z",
        state_dir=state_dir,
        receipts=(receipt,),
        allow_state_write=True,
    )

    assert second.previous_snapshot_id == first.snapshot.snapshot_id
    assert second.interval_due is False
    assert second.elapsed_minutes == 1
    assert second.diff is not None
    assert [change.kind for change in second.diff.changes] == [
        DirectoryChangeKind.MOVED
    ]
    assert second.learning_examples[0].corrected_path == (
        "Versicherungen/Police.txt"
    )
    assert second.learning_examples[0].automatic_promotion is False
    assert second.checkpoint_file is not None
    assert second.checkpoint_file.is_file()
    assert len(list((state_dir / "directory-snapshots").glob("*.json"))) == 2
    assert corrected.read_bytes() == before_bytes


def test_scan_fails_closed_for_disabled_watch_and_non_monotonic_time(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Dokumente"
    source.mkdir()
    (source / "A.txt").write_text("A", encoding="utf-8")
    config_file = tmp_path / "watched-folders.json"
    _write_config(config_file, source, enabled=False)
    watch = load_watched_folder_configuration(config_file).watches[0]
    with pytest.raises(DirectoryObservationError, match="deaktiviert"):
        run_directory_scan(
            watch,
            captured_at="2026-08-21T20:40:00Z",
            state_dir=tmp_path / "state",
            allow_state_write=False,
        )

    _write_config(config_file, source)
    watch = load_watched_folder_configuration(config_file).watches[0]
    run_directory_scan(
        watch,
        captured_at="2026-08-21T20:40:00Z",
        state_dir=tmp_path / "state",
        allow_state_write=True,
    )
    with pytest.raises(DirectoryObservationError, match="später"):
        run_directory_scan(
            watch,
            captured_at="2026-08-21T20:39:00Z",
            state_dir=tmp_path / "state",
            allow_state_write=False,
        )
