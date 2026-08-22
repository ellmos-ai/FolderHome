"""Atomic, never-overwrite ICS handoff publishing for calendar integrations."""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from folderhome.contracts import CalendarCandidate


class CalendarIcsError(RuntimeError):
    """Raised when an ICS batch cannot be safely published or rolled back."""


@dataclass(frozen=True, slots=True)
class IcsArtifact:
    """One planned immutable ICS payload and its exact target."""

    target_path: Path
    content: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class PublishedIcs:
    """One verified output owned by the current execution."""

    target_path: Path
    content_sha256: str


@dataclass(frozen=True, slots=True)
class IcsPublishResult:
    """Published outputs plus directories created by this execution."""

    outputs: tuple[PublishedIcs, ...]
    created_directories: tuple[Path, ...]


def render_calendar_ics(candidate: CalendarCandidate, planned_at: str) -> str:
    """Render a deterministic RFC5545-compatible event payload."""

    timestamp = datetime.fromisoformat(planned_at.replace("Z", "+00:00"))
    dtstamp = timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FolderHome//Calendar Handoff 1.0//DE",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{candidate.event_uid}",
        f"DTSTAMP:{dtstamp}",
    ]
    compact_date = candidate.event_date.replace("-", "")
    if candidate.start_time is None:
        next_date = (date.fromisoformat(candidate.event_date) + timedelta(days=1)).strftime(
            "%Y%m%d"
        )
        lines.extend(
            (
                f"DTSTART;VALUE=DATE:{compact_date}",
                f"DTEND;VALUE=DATE:{next_date}",
            )
        )
    else:
        compact_start = candidate.start_time.replace(":", "")
        lines.append(
            f"DTSTART;TZID={candidate.timezone}:{compact_date}T{compact_start}00"
        )
        if candidate.end_time is not None:
            compact_end = candidate.end_time.replace(":", "")
            lines.append(
                f"DTEND;TZID={candidate.timezone}:{compact_date}T{compact_end}00"
            )
    lines.append(f"SUMMARY:{_escape_ics(candidate.title)}")
    if candidate.location:
        lines.append(f"LOCATION:{_escape_ics(candidate.location)}")
    lines.extend(("END:VEVENT", "END:VCALENDAR"))
    return "\r\n".join(lines) + "\r\n"


def publish_ics_batch(artifacts: tuple[IcsArtifact, ...]) -> IcsPublishResult:
    """Publish an entire ICS batch atomically per file and roll back on failure."""

    if not artifacts:
        raise CalendarIcsError("ICS-Ausführung enthält keine Dateien.")
    targets = tuple(Path(os.path.abspath(item.target_path)) for item in artifacts)
    if len(targets) != len(set(targets)):
        raise CalendarIcsError("ICS-Zieldateien müssen eindeutig sein.")
    for artifact, target in zip(artifacts, targets, strict=True):
        if sha256(artifact.content.encode("utf-8")).hexdigest() != artifact.content_sha256:
            raise CalendarIcsError("ICS-Inhalt stimmt nicht mit dem geplanten Hash überein.")
        if target.exists() or target.is_symlink():
            raise CalendarIcsError(f"ICS-Zieldatei existiert bereits: {target}")

    created_directories: list[Path] = []
    staged: list[Path] = []
    published: list[PublishedIcs] = []
    try:
        for artifact, target in zip(artifacts, targets, strict=True):
            _ensure_directory(target.parent, created_directories)
            temporary = target.parent / f".{target.name}.folderhome-{uuid4().hex}.tmp"
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            with os.fdopen(os.open(temporary, flags, 0o600), "wb") as handle:
                handle.write(artifact.content.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            staged.append(temporary)
            if _file_hash(temporary) != artifact.content_sha256:
                raise CalendarIcsError("Temporäre ICS-Datei konnte nicht verifiziert werden.")
            os.link(temporary, target)
            receipt = PublishedIcs(target, artifact.content_sha256)
            published.append(receipt)
            if _file_hash(target) != artifact.content_sha256:
                raise CalendarIcsError("Publizierte ICS-Datei konnte nicht verifiziert werden.")
        return IcsPublishResult(tuple(published), tuple(created_directories))
    except BaseException as exc:
        rollback_error = _remove_owned_outputs(tuple(published), tuple(created_directories))
        if rollback_error is not None:
            raise CalendarIcsError(f"{exc}; Rücknahmefehler: {rollback_error}") from exc
        if isinstance(exc, CalendarIcsError):
            raise
        raise CalendarIcsError(str(exc)) from exc
    finally:
        for temporary in staged:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def rollback_published_ics(result: IcsPublishResult) -> None:
    """Remove only unchanged outputs owned by this execution."""

    error = _remove_owned_outputs(result.outputs, result.created_directories)
    if error is not None:
        raise CalendarIcsError(error)


def _remove_owned_outputs(
    outputs: tuple[PublishedIcs, ...],
    directories: tuple[Path, ...],
) -> str | None:
    errors: list[str] = []
    for output in reversed(outputs):
        try:
            if not output.target_path.is_file() or output.target_path.is_symlink():
                errors.append(f"Ausgabe fehlt oder ist kein reguläres File: {output.target_path}")
            elif _file_hash(output.target_path) != output.content_sha256:
                errors.append(f"Ausgabe wurde nach Publikation verändert: {output.target_path}")
            else:
                output.target_path.unlink()
        except OSError as exc:
            errors.append(f"{output.target_path}: {exc}")
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except OSError:
            if directory.exists() and not any(directory.iterdir()):
                errors.append(f"Leeres Ausgabeverzeichnis blieb bestehen: {directory}")
    return "; ".join(errors) if errors else None


def _ensure_directory(path: Path, created: list[Path]) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current.is_symlink():
            raise CalendarIcsError(f"ICS-Verzeichnis ist ein symbolischer Link: {current}")
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise CalendarIcsError(f"ICS-Elternpfad ist kein sicheres Verzeichnis: {current}")
    for directory in reversed(missing):
        directory.mkdir()
        created.append(directory)


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _escape_ics(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )
