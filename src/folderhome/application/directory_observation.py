"""Load watched folders and run non-intervening directory observations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from folderhome.application.directory_snapshot import (
    DirectorySnapshotError,
    build_directory_diff,
    build_learning_examples,
    read_directory_snapshot,
    snapshot_directory,
    write_directory_snapshot,
)
from folderhome.contracts import GateDecision, PlacementReceipt
from folderhome.contracts.observations import DirectoryScanReport, WatchedFolder
from folderhome.contracts.snapshots import DirectorySnapshot

_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_UNSPECIFIED_PREVIOUS = object()


class DirectoryObservationError(ValueError):
    """Raised when watch configuration or checkpoint history is ambiguous."""


@dataclass(frozen=True, slots=True)
class WatchedFolderConfiguration:
    """Validated set of uniquely identified local folder observations."""

    watches: tuple[WatchedFolder, ...]


def load_watched_folder_configuration(path: Path) -> WatchedFolderConfiguration:
    """Load one strict watched-folders JSON file and resolve relative roots."""

    path = path.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DirectoryObservationError(
            f"Beobachtungsprofil ist nicht lesbar: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        "folderhome.watched-folders.v1"
    ):
        raise DirectoryObservationError(
            "Beobachtungsprofil verwendet ein unbekanntes Schema."
        )
    items = payload.get("watches")
    if not isinstance(items, list) or not items:
        raise DirectoryObservationError(
            "Beobachtungsprofil benötigt eine nichtleere watches-Liste."
        )
    watches = tuple(_parse_watch(item, path, index) for index, item in enumerate(items))
    watch_ids = [watch.watch_id for watch in watches]
    if len(watch_ids) != len(set(watch_ids)):
        raise DirectoryObservationError("watch_id ist nicht eindeutig.")
    return WatchedFolderConfiguration(watches=watches)


def run_directory_scan(
    watch: WatchedFolder,
    *,
    captured_at: str,
    state_dir: Path,
    receipts: tuple[PlacementReceipt, ...] = (),
    allow_state_write: bool,
    expected_previous_snapshot_id: str | None | object = _UNSPECIFIED_PREVIOUS,
    expected_current_snapshot_id: str | object = _UNSPECIFIED_PREVIOUS,
) -> DirectoryScanReport:
    """Compare a configured folder to its latest immutable checkpoint."""

    if not watch.enabled:
        raise DirectoryObservationError(f"Beobachtungsordner ist deaktiviert: {watch.watch_id}")
    state_dir = state_dir.resolve()
    previous = _latest_snapshot(state_dir, watch.source_root)
    previous_id = previous.snapshot_id if previous else None
    if (
        expected_previous_snapshot_id is not _UNSPECIFIED_PREVIOUS
        and previous_id != expected_previous_snapshot_id
    ):
        raise DirectoryObservationError(
            "Snapshot-Historie stimmt nicht mit dem erwarteten Checkpoint überein."
        )
    try:
        current = snapshot_directory(
            watch.source_root,
            captured_at=captured_at,
            recursive=watch.recursive,
        )
    except DirectorySnapshotError as exc:
        raise DirectoryObservationError(str(exc)) from exc
    if (
        expected_current_snapshot_id is not _UNSPECIFIED_PREVIOUS
        and current.snapshot_id != expected_current_snapshot_id
    ):
        raise DirectoryObservationError(
            "Beobachteter Ordner stimmt nicht mehr mit dem geplanten Snapshot überein."
        )
    diff = None
    learning_examples = ()
    elapsed_minutes = None
    interval_due = True
    if previous is not None:
        if previous.recursive != current.recursive:
            raise DirectoryObservationError(
                "Rekursionseinstellung weicht vom letzten Checkpoint ab."
            )
        previous_time = _timestamp(previous.captured_at)
        current_time = _timestamp(current.captured_at)
        if current_time <= previous_time:
            raise DirectoryObservationError(
                "captured_at muss später als der letzte Checkpoint sein."
            )
        elapsed_minutes = int((current_time - previous_time).total_seconds() // 60)
        interval_due = elapsed_minutes >= watch.interval_minutes
        diff = build_directory_diff(previous, current)
        eligible_receipts = tuple(
            receipt
            for receipt in receipts
            if receipt.profile_id == watch.profile_id and receipt.area == watch.area
            and (receipt.root_path is None or receipt.root_path == watch.source_root)
        )
        learning_examples = build_learning_examples(diff, eligible_receipts)

    checkpoint_file = None
    if allow_state_write:
        latest_before_write = _latest_snapshot(state_dir, watch.source_root)
        expected_id = previous.snapshot_id if previous else None
        actual_id = latest_before_write.snapshot_id if latest_before_write else None
        if actual_id != expected_id:
            raise DirectoryObservationError(
                "Snapshot-Historie wurde während des Scanlaufs verändert."
            )
        try:
            checkpoint_file = write_directory_snapshot(
                current,
                state_dir,
                allow_state_write=True,
            )
        except DirectorySnapshotError as exc:
            raise DirectoryObservationError(str(exc)) from exc
    gate = GateDecision(
        required=True,
        granted=allow_state_write,
        reason=(
            "Explizite Freigabe für genau einen neuen Checkpoint erteilt."
            if allow_state_write
            else "Keine State-Schreibfreigabe; Scanbericht bleibt read-only."
        ),
    )
    scan_id = _scan_id(watch, current, previous)
    return DirectoryScanReport(
        scan_id=scan_id,
        watch=watch,
        snapshot=current,
        previous_snapshot_id=previous_id,
        diff=diff,
        learning_examples=learning_examples,
        interval_due=interval_due,
        elapsed_minutes=elapsed_minutes,
        gate=gate,
        checkpoint_file=checkpoint_file,
    )


def _parse_watch(item: object, origin: Path, index: int) -> WatchedFolder:
    if not isinstance(item, dict):
        raise DirectoryObservationError(
            f"Beobachtung {index} muss ein JSON-Objekt sein."
        )
    watch_id = _required_id(item, "watch_id", index)
    profile_id = _required_id(item, "profile_id", index)
    area = _required_id(item, "area", index)
    source_value = item.get("source_dir")
    if not isinstance(source_value, str) or not source_value.strip():
        raise DirectoryObservationError(
            f"Beobachtung {index} benötigt einen source_dir."
        )
    source_root = Path(source_value)
    if not source_root.is_absolute():
        source_root = origin.parent / source_root
    interval = item.get("interval_minutes")
    if isinstance(interval, bool) or not isinstance(interval, int) or interval < 1:
        raise DirectoryObservationError(
            f"Beobachtung {index} benötigt interval_minutes >= 1."
        )
    recursive = item.get("recursive")
    enabled = item.get("enabled")
    if not isinstance(recursive, bool) or not isinstance(enabled, bool):
        raise DirectoryObservationError(
            f"Beobachtung {index} benötigt boolesche recursive/enabled-Werte."
        )
    return WatchedFolder(
        watch_id=watch_id,
        source_root=source_root,
        profile_id=profile_id,
        area=area,
        interval_minutes=interval,
        recursive=recursive,
        enabled=enabled,
    )


def _required_id(item: dict[str, object], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise DirectoryObservationError(
            f"{field} in Beobachtung {index} ist keine stabile Kleinbuchstaben-ID."
        )
    return value


def _latest_snapshot(state_dir: Path, source_root: Path) -> DirectorySnapshot | None:
    history_dir = state_dir / "directory-snapshots"
    if not history_dir.exists():
        return None
    if not history_dir.is_dir() or history_dir.is_symlink():
        raise DirectoryObservationError(
            f"Snapshot-Historie ist kein sicherer Ordner: {history_dir}"
        )
    matching = []
    for path in sorted(history_dir.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            snapshot = read_directory_snapshot(path)
        except DirectorySnapshotError as exc:
            raise DirectoryObservationError(str(exc)) from exc
        if snapshot.source_root == source_root.resolve():
            matching.append(snapshot)
    if not matching:
        return None
    latest_time = max(_timestamp(snapshot.captured_at) for snapshot in matching)
    latest = [
        snapshot
        for snapshot in matching
        if _timestamp(snapshot.captured_at) == latest_time
    ]
    if len(latest) != 1:
        raise DirectoryObservationError(
            "Letzter Checkpoint ist wegen gleicher Zeitstempel mehrdeutig."
        )
    return latest[0]


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DirectoryObservationError(
            f"Snapshot-Zeitpunkt ist ungültig: {value}"
        ) from exc
    if parsed.tzinfo is None:
        raise DirectoryObservationError("Snapshot-Zeitpunkt benötigt eine Zeitzone.")
    return parsed


def _scan_id(
    watch: WatchedFolder,
    current: DirectorySnapshot,
    previous: DirectorySnapshot | None,
) -> str:
    material = "\0".join(
        (
            watch.watch_id,
            current.snapshot_id,
            previous.snapshot_id if previous else "",
        )
    )
    return f"scan_{sha256(material.encode('utf-8')).hexdigest()}"
