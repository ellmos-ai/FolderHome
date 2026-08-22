"""Reusable, hash-bound single-file moves with strict never-overwrite semantics."""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class FilesystemTransactionError(RuntimeError):
    """Raised when an exact file move cannot be completed without ambiguity."""


@dataclass(frozen=True, slots=True)
class FileMoveResult:
    """Evidence returned after one same-volume link-and-unlink move."""

    source_path: Path
    target_path: Path
    source_sha256: str
    created_directories: tuple[Path, ...]


def validate_move_target(target_path: Path) -> None:
    """Check one target without creating it or any parent directory."""

    target = _absolute_path(target_path)
    if _lexists(target):
        raise FilesystemTransactionError(f"Ziel existiert bereits: {target}")
    _validate_parent_chain(target.parent)


def move_file_no_overwrite(
    source_path: Path,
    target_path: Path,
    *,
    expected_sha256: str,
) -> FileMoveResult:
    """Move one regular file without overwrite or cross-volume fallback."""

    source = _absolute_path(source_path)
    target = _absolute_path(target_path)
    if source == target:
        raise FilesystemTransactionError("Quell- und Zielpfad sind identisch.")
    if source.resolve(strict=False) != source or source.is_symlink() or not source.is_file():
        raise FilesystemTransactionError(
            f"Quelle fehlt, ist kein reguläres Dokument oder ist ein Link: {source}"
        )
    actual_hash = _sha256_file(source)
    if actual_hash != expected_sha256:
        raise FilesystemTransactionError(
            f"Quellhash stimmt nicht mit der Freigabe überein: {source}"
        )
    validate_move_target(target)
    created = _create_parent_chain(target.parent)
    linked = False
    try:
        os.link(source, target, follow_symlinks=False)
        linked = True
        if _sha256_file(target) != expected_sha256:
            raise FilesystemTransactionError(
                f"Zielhash stimmt nach dem Anlegen nicht überein: {target}"
            )
        source.unlink()
    except FileExistsError as exc:
        raise FilesystemTransactionError(f"Ziel existiert bereits: {target}") from exc
    except OSError as exc:
        raise FilesystemTransactionError(
            "Datei konnte nicht als sichere Same-Volume-Transaktion verschoben "
            f"werden: {source} -> {target}: {exc}"
        ) from exc
    finally:
        if linked and source.exists() and target.exists():
            with suppress(OSError):
                target.unlink()
        if source.exists():
            remove_empty_directories(created)
    return FileMoveResult(
        source_path=source,
        target_path=target,
        source_sha256=expected_sha256,
        created_directories=created,
    )


def remove_empty_directories(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    """Remove only exact directories created by a transaction and still empty."""

    removed = []
    for path in sorted(paths, key=lambda item: len(item.parts), reverse=True):
        candidate = _absolute_path(path)
        if candidate.resolve(strict=False) != candidate or candidate.is_symlink():
            continue
        try:
            candidate.rmdir()
        except (FileNotFoundError, OSError):
            continue
        removed.append(candidate)
    return tuple(removed)


def _create_parent_chain(parent: Path) -> tuple[Path, ...]:
    _validate_parent_chain(parent)
    missing = []
    cursor = parent
    while not cursor.exists():
        missing.append(cursor)
        if cursor == cursor.parent:
            raise FilesystemTransactionError(
                f"Kein bestehender Zielvorfahr gefunden: {parent}"
            )
        cursor = cursor.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FilesystemTransactionError(
            f"Zielordner konnte nicht sicher angelegt werden: {parent}: {exc}"
        ) from exc
    _validate_parent_chain(parent)
    return tuple(reversed(missing))


def _validate_parent_chain(parent: Path) -> None:
    canonical = parent.resolve(strict=False)
    if canonical != parent:
        raise FilesystemTransactionError(
            f"Zielordner enthält einen symbolischen Link oder Alias: {parent}"
        )
    cursor = parent
    while not cursor.exists():
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    if cursor.is_symlink() or not cursor.is_dir():
        raise FilesystemTransactionError(
            f"Bestehender Zielvorfahr ist kein sicherer Ordner: {cursor}"
        )


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
