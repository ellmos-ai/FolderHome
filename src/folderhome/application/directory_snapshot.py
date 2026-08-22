"""Create, compare, and persist content-free directory snapshots."""

from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    DirectoryChange,
    DirectoryChangeKind,
    DirectoryDiff,
    DirectoryFileState,
    DirectoryLearningExample,
    DirectorySnapshot,
    PlacementReceipt,
)


class DirectorySnapshotError(RuntimeError):
    """Raised when snapshot identity, history, or write safety is violated."""


def snapshot_directory(
    source_dir: Path,
    *,
    captured_at: str,
    recursive: bool = True,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> DirectorySnapshot:
    """Hash one directory without retaining document contents or writing state."""

    root = source_dir.resolve()
    _validate_timestamp(captured_at)
    if not root.is_dir() or root.is_symlink():
        raise DirectorySnapshotError(f"Quellordner fehlt oder ist ein Link: {root}")
    try:
        inventory = inventory_files(root, recursive=recursive, policy=resource_policy)
    except ResourceLimitExceeded as exc:
        raise DirectorySnapshotError(str(exc)) from exc
    files = []
    skipped = [path.relative_to(root).as_posix() for path in inventory.symlinks]
    for path in inventory.files:
        relative = path.relative_to(root).as_posix()
        stat = path.stat()
        files.append(
            DirectoryFileState(
                relative_path=relative,
                source_sha256=_sha256_file(path),
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
        )
    files.sort(key=lambda item: (item.relative_path.casefold(), item.relative_path))
    skipped.sort(key=lambda item: (item.casefold(), item))
    snapshot_id = _snapshot_id(
        root,
        captured_at,
        recursive,
        tuple(files),
        tuple(skipped),
    )
    return DirectorySnapshot(
        snapshot_id=snapshot_id,
        source_root=root,
        captured_at=captured_at,
        recursive=recursive,
        files=tuple(files),
        skipped_symlinks=tuple(skipped),
    )


def build_directory_diff(
    before: DirectorySnapshot,
    after: DirectorySnapshot,
) -> DirectoryDiff:
    """Explain path/hash changes and claim only unambiguous one-to-one moves."""

    if before.source_root != after.source_root:
        raise DirectorySnapshotError("Snapshots gehören nicht zum selben Quellordner.")
    before_by_path = {entry.relative_path: entry for entry in before.files}
    after_by_path = {entry.relative_path: entry for entry in after.files}
    changes = []
    common_paths = set(before_by_path).intersection(after_by_path)
    for path in sorted(common_paths, key=str.casefold):
        old = before_by_path[path]
        new = after_by_path[path]
        if old.source_sha256 != new.source_sha256:
            changes.append(
                _change(
                    DirectoryChangeKind.MODIFIED,
                    old,
                    new,
                    "exact",
                    "Gleicher Relativpfad, aber unterschiedlicher SHA-256.",
                )
            )
        elif old.mtime_ns != new.mtime_ns or old.size_bytes != new.size_bytes:
            changes.append(
                _change(
                    DirectoryChangeKind.METADATA_CHANGED,
                    old,
                    new,
                    "exact",
                    "SHA-256 ist gleich; Dateisystemmetadaten haben sich geändert.",
                )
            )

    removed = {
        path: before_by_path[path] for path in set(before_by_path).difference(after_by_path)
    }
    added = {
        path: after_by_path[path] for path in set(after_by_path).difference(before_by_path)
    }
    removed_by_hash: dict[str, list[DirectoryFileState]] = defaultdict(list)
    added_by_hash: dict[str, list[DirectoryFileState]] = defaultdict(list)
    for entry in removed.values():
        removed_by_hash[entry.source_sha256].append(entry)
    for entry in added.values():
        added_by_hash[entry.source_sha256].append(entry)
    moved_before_paths = set()
    moved_after_paths = set()
    for source_hash in sorted(set(removed_by_hash).intersection(added_by_hash)):
        old_candidates = removed_by_hash[source_hash]
        new_candidates = added_by_hash[source_hash]
        if len(old_candidates) != 1 or len(new_candidates) != 1:
            continue
        old = old_candidates[0]
        new = new_candidates[0]
        moved_before_paths.add(old.relative_path)
        moved_after_paths.add(new.relative_path)
        changes.append(
            _change(
                DirectoryChangeKind.MOVED,
                old,
                new,
                "high",
                "Eindeutiger, unveränderter SHA-256 an genau einem neuen Pfad.",
            )
        )
    for path, entry in removed.items():
        if path not in moved_before_paths:
            changes.append(
                _change(
                    DirectoryChangeKind.REMOVED,
                    entry,
                    None,
                    "exact",
                    "Relativpfad fehlt im späteren Snapshot; kein eindeutiges Hash-Ziel.",
                )
            )
    for path, entry in added.items():
        if path not in moved_after_paths:
            changes.append(
                _change(
                    DirectoryChangeKind.ADDED,
                    None,
                    entry,
                    "exact",
                    "Relativpfad existiert nur im späteren Snapshot.",
                )
            )
    changes.sort(
        key=lambda item: (
            item.kind.value,
            (item.after_path or item.before_path or "").casefold(),
            item.after_path or item.before_path or "",
        )
    )
    return DirectoryDiff(
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        before_captured_at=before.captured_at,
        after_captured_at=after.captured_at,
        changes=tuple(changes),
    )


def build_learning_examples(
    diff: DirectoryDiff,
    receipts: tuple[PlacementReceipt, ...],
) -> tuple[DirectoryLearningExample, ...]:
    """Link user moves to prior placements without promoting any automatic rule."""

    receipts_by_placement: dict[
        tuple[str, str], list[PlacementReceipt]
    ] = defaultdict(list)
    for receipt in receipts:
        receipts_by_placement[
            (receipt.document_sha256, receipt.placed_path)
        ].append(receipt)
    examples = []
    for change in diff.changes:
        if (
            change.kind is not DirectoryChangeKind.MOVED
            or change.before_sha256 is None
            or change.before_path is None
            or change.after_path is None
        ):
            continue
        matching_receipts = receipts_by_placement.get(
            (change.before_sha256, change.before_path),
            [],
        )
        if len(matching_receipts) != 1:
            continue
        receipt = matching_receipts[0]
        material = "\0".join(
            (
                receipt.receipt_id,
                change.before_sha256,
                change.before_path,
                change.after_path,
                diff.after_snapshot_id,
            )
        )
        examples.append(
            DirectoryLearningExample(
                example_id=f"learn_{sha256(material.encode('utf-8')).hexdigest()}",
                receipt_id=receipt.receipt_id,
                document_sha256=change.before_sha256,
                placed_path=change.before_path,
                corrected_path=change.after_path,
                profile_id=receipt.profile_id,
                area=receipt.area,
                source_rule_ids=receipt.source_rule_ids,
                observed_at=diff.after_captured_at,
            )
        )
    return tuple(examples)


def write_directory_snapshot(
    snapshot: DirectorySnapshot,
    state_dir: Path,
    *,
    allow_state_write: bool,
) -> Path:
    """Append one immutable snapshot file after an explicit local-state gate."""

    if not allow_state_write:
        raise DirectorySnapshotError(
            "Schreibfreigabe für den Snapshot-Zustand fehlt."
        )
    history_dir = state_dir.resolve() / "directory-snapshots"
    history_dir.mkdir(parents=True, exist_ok=True)
    safe_time = snapshot.captured_at.replace(":", "-")
    target = history_dir / f"{safe_time}_{snapshot.snapshot_id}.json"
    if target.exists():
        raise DirectorySnapshotError(f"Snapshot-Historie existiert bereits: {target}")
    payload = (
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    _publish_new_bytes(target, payload)
    return target


def read_directory_snapshot(path: Path) -> DirectorySnapshot:
    """Read and identity-check one stored snapshot."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DirectorySnapshotError(f"Snapshot ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != DirectorySnapshot.SCHEMA:
        raise DirectorySnapshotError("Snapshot verwendet ein unbekanntes Schema.")
    try:
        files = tuple(
            DirectoryFileState(
                relative_path=str(item["relative_path"]),
                source_sha256=str(item["source_sha256"]),
                size_bytes=int(item["size_bytes"]),
                mtime_ns=int(item["mtime_ns"]),
            )
            for item in payload["files"]
        )
        snapshot = DirectorySnapshot(
            snapshot_id=str(payload["snapshot_id"]),
            source_root=Path(str(payload["source_root"])),
            captured_at=str(payload["captured_at"]),
            recursive=bool(payload["recursive"]),
            files=files,
            skipped_symlinks=tuple(str(item) for item in payload["skipped_symlinks"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DirectorySnapshotError(f"Snapshot-Vertrag ist ungültig: {exc}") from exc
    expected_id = _snapshot_id(
        snapshot.source_root,
        snapshot.captured_at,
        snapshot.recursive,
        snapshot.files,
        snapshot.skipped_symlinks,
    )
    if snapshot.snapshot_id != expected_id:
        raise DirectorySnapshotError("Snapshot-ID stimmt nicht mit den Metadaten überein.")
    return snapshot


def _change(
    kind: DirectoryChangeKind,
    before: DirectoryFileState | None,
    after: DirectoryFileState | None,
    confidence: str,
    evidence: str,
) -> DirectoryChange:
    return DirectoryChange(
        kind=kind,
        before_path=before.relative_path if before else None,
        after_path=after.relative_path if after else None,
        before_sha256=before.source_sha256 if before else None,
        after_sha256=after.source_sha256 if after else None,
        confidence=confidence,
        evidence=evidence,
    )


def _snapshot_id(
    root: Path,
    captured_at: str,
    recursive: bool,
    files: tuple[DirectoryFileState, ...],
    skipped: tuple[str, ...],
) -> str:
    material = "\0".join(
        (
            str(root.resolve()),
            captured_at,
            str(recursive),
            *(
                f"{entry.relative_path}:{entry.source_sha256}:"
                f"{entry.size_bytes}:{entry.mtime_ns}"
                for entry in files
            ),
            *(f"symlink:{item}" for item in skipped),
        )
    )
    return f"snapshot_{sha256(material.encode('utf-8')).hexdigest()}"


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DirectorySnapshotError(f"captured_at ist kein ISO-Zeitpunkt: {value}") from exc
    if parsed.tzinfo is None:
        raise DirectorySnapshotError("captured_at benötigt eine Zeitzone.")


def _publish_new_bytes(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise DirectorySnapshotError(
                f"Snapshot-Historie existiert bereits: {path}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
