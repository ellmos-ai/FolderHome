"""Reusable finite work budgets for local files, parsers, and renderers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


class ResourceLimitExceeded(ValueError):
    """Raised before or while work would exceed a declared finite budget."""


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    """Finite, non-disableable ceilings for one local workflow invocation."""

    max_directory_entries: int = 20_000
    max_files: int = 5_000
    max_file_bytes: int = 128 * 1024 * 1024
    max_total_source_bytes: int = 512 * 1024 * 1024
    max_pdf_pages: int = 2_500
    max_image_frames: int = 250
    max_decoded_pixels: int = 120_000_000
    max_extracted_text_chars: int = 12_000_000
    max_output_bytes: int = 256 * 1024 * 1024
    max_total_output_bytes: int = 512 * 1024 * 1024
    max_archive_bytes: int = 512 * 1024 * 1024

    SCHEMA = "folderhome.resource-policy.v1"

    def __post_init__(self) -> None:
        ceilings = {
            "max_directory_entries": 20_000,
            "max_files": 5_000,
            "max_file_bytes": 128 * 1024 * 1024,
            "max_total_source_bytes": 512 * 1024 * 1024,
            "max_pdf_pages": 2_500,
            "max_image_frames": 250,
            "max_decoded_pixels": 120_000_000,
            "max_extracted_text_chars": 12_000_000,
            "max_output_bytes": 256 * 1024 * 1024,
            "max_total_output_bytes": 512 * 1024 * 1024,
            "max_archive_bytes": 512 * 1024 * 1024,
        }
        for name, ceiling in ceilings.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= ceiling:
                raise ValueError(f"{name} muss zwischen 1 und {ceiling} liegen.")
        if self.max_total_source_bytes < self.max_file_bytes:
            raise ValueError(
                "max_total_source_bytes darf max_file_bytes nicht unterschreiten."
            )
        if self.max_total_output_bytes < self.max_output_bytes:
            raise ValueError(
                "max_total_output_bytes darf max_output_bytes nicht unterschreiten."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "max_directory_entries": self.max_directory_entries,
            "max_files": self.max_files,
            "max_file_bytes": self.max_file_bytes,
            "max_total_source_bytes": self.max_total_source_bytes,
            "max_pdf_pages": self.max_pdf_pages,
            "max_image_frames": self.max_image_frames,
            "max_decoded_pixels": self.max_decoded_pixels,
            "max_extracted_text_chars": self.max_extracted_text_chars,
            "max_output_bytes": self.max_output_bytes,
            "max_total_output_bytes": self.max_total_output_bytes,
            "max_archive_bytes": self.max_archive_bytes,
        }


DEFAULT_RESOURCE_POLICY = ResourcePolicy()


@dataclass(frozen=True, slots=True)
class FileInventory:
    """Deterministic, resource-bounded file inventory without document content."""

    root: Path
    files: tuple[Path, ...]
    symlinks: tuple[Path, ...]
    entries_seen: int
    total_source_bytes: int

    @property
    def all_paths(self) -> tuple[Path, ...]:
        return tuple(
            sorted(
                (*self.files, *self.symlinks),
                key=lambda path: (
                    path.relative_to(self.root).as_posix().casefold(),
                    path.relative_to(self.root).as_posix(),
                ),
            )
        )


@dataclass(slots=True)
class ResourceBudget:
    """Incremental counters shared across parsers and rendering stages."""

    policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY
    directory_entries: int = 0
    files: int = 0
    source_bytes: int = 0
    pdf_pages: int = 0
    image_frames: int = 0
    decoded_pixels: int = 0
    extracted_text_chars: int = 0
    output_bytes: int = 0

    def consume_directory_entry(self) -> None:
        self.directory_entries += 1
        _require_within(
            "Verzeichnis-Eintragsbudget",
            self.directory_entries,
            self.policy.max_directory_entries,
        )

    def consume_source(self, size_bytes: int) -> None:
        _require_non_negative("Quelldateigröße", size_bytes)
        _require_within(
            "Einzeldateigrößen-Budget",
            size_bytes,
            self.policy.max_file_bytes,
        )
        self.files += 1
        _require_within("Dateianzahl-Budget", self.files, self.policy.max_files)
        self.source_bytes += size_bytes
        _require_within(
            "Gesamtquellgrößen-Budget",
            self.source_bytes,
            self.policy.max_total_source_bytes,
        )

    def consume_pdf_pages(self, count: int) -> None:
        _require_non_negative("PDF-Seitenzahl", count)
        self.pdf_pages += count
        _require_within("PDF-Seiten-Budget", self.pdf_pages, self.policy.max_pdf_pages)

    def consume_image(self, *, frames: int, decoded_pixels: int) -> None:
        _require_non_negative("Bildframezahl", frames)
        _require_non_negative("Dekodierte Bildpixel", decoded_pixels)
        self.image_frames += frames
        self.decoded_pixels += decoded_pixels
        _require_within(
            "Bildframe-Budget",
            self.image_frames,
            self.policy.max_image_frames,
        )
        _require_within(
            "Bildpixel-Budget",
            self.decoded_pixels,
            self.policy.max_decoded_pixels,
        )

    def consume_extracted_text(self, character_count: int) -> None:
        _require_non_negative("Extrahierte Textzeichen", character_count)
        self.extracted_text_chars += character_count
        _require_within(
            "Textzeichen-Budget",
            self.extracted_text_chars,
            self.policy.max_extracted_text_chars,
        )

    def consume_output(self, size_bytes: int) -> None:
        _require_non_negative("Ausgabegröße", size_bytes)
        _require_within(
            "Einzelausgabe-Budget",
            size_bytes,
            self.policy.max_output_bytes,
        )
        self.output_bytes += size_bytes
        _require_within(
            "Gesamtausgabe-Budget",
            self.output_bytes,
            self.policy.max_total_output_bytes,
        )


class BoundedBytesIO(BytesIO):
    """Seekable byte buffer that refuses growth beyond an explicit ceiling."""

    def __init__(self, maximum_bytes: int, *, budget_name: str) -> None:
        if isinstance(maximum_bytes, bool) or maximum_bytes < 1:
            raise ValueError("maximum_bytes muss eine positive Ganzzahl sein.")
        if not budget_name.strip():
            raise ValueError("budget_name darf nicht leer sein.")
        super().__init__()
        self._maximum_bytes = maximum_bytes
        self._budget_name = budget_name

    def write(self, data: bytes | bytearray | memoryview) -> int:
        resulting_size = max(self.getbuffer().nbytes, self.tell() + len(data))
        _require_within(self._budget_name, resulting_size, self._maximum_bytes)
        return super().write(data)

    def truncate(self, size: int | None = None) -> int:
        requested = self.tell() if size is None else size
        _require_within(self._budget_name, requested, self._maximum_bytes)
        return super().truncate(size)


def inventory_files(
    root: Path,
    *,
    recursive: bool,
    policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
    exclude_paths: Iterable[Path] = (),
) -> FileInventory:
    """Inventory one tree incrementally and stop before a work budget is exceeded."""

    root = root.resolve()
    if not root.is_dir() or _is_link_or_junction(root):
        raise ValueError(f"Inventurwurzel fehlt oder ist ein Link: {root}")
    excluded = {path.resolve() for path in exclude_paths}
    candidates = root.rglob("*") if recursive else root.iterdir()
    budget = ResourceBudget(policy)
    files: list[Path] = []
    symlinks: list[Path] = []
    for candidate in candidates:
        budget.consume_directory_entry()
        if _is_link_or_junction(candidate):
            symlinks.append(candidate)
            continue
        if not candidate.is_file():
            continue
        path = candidate.resolve()
        if not path.is_relative_to(root):
            raise ResourceLimitExceeded(f"Dateipfad verlässt die Inventurwurzel: {candidate}")
        if path in excluded:
            continue
        budget.consume_source(path.stat().st_size)
        files.append(path)
    def order(path: Path) -> tuple[str, str]:
        relative = path.relative_to(root).as_posix()
        return relative.casefold(), relative

    files.sort(key=order)
    symlinks.sort(key=order)
    return FileInventory(
        root=root,
        files=tuple(files),
        symlinks=tuple(symlinks),
        entries_seen=budget.directory_entries,
        total_source_bytes=budget.source_bytes,
    )


def _is_link_or_junction(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _require_non_negative(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} muss eine nichtnegative Ganzzahl sein.")


def _require_within(name: str, actual: int, maximum: int) -> None:
    if actual > maximum:
        raise ResourceLimitExceeded(
            f"{name} überschritten: {actual} > {maximum}. Verarbeitung wurde gestoppt."
        )
