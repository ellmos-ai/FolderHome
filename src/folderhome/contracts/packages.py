"""Contracts for deterministic type-grouped document ZIP packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from folderhome.contracts.transforms import BundleFormat, BundleSource

if TYPE_CHECKING:
    from folderhome.contracts import GateDecision, UndoDescriptor


@dataclass(frozen=True, slots=True)
class DocumentPackageGroup:
    """One source-type group and its single target document inside the ZIP."""

    group_id: str
    bundle_id: str
    output_filename: str
    output_format: BundleFormat
    sources: tuple[BundleSource, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "group_id": self.group_id,
            "bundle_id": self.bundle_id,
            "output_filename": self.output_filename,
            "output_format": self.output_format.value,
            "sources": [source.to_dict() for source in self.sources],
        }


@dataclass(frozen=True, slots=True)
class UnsupportedPackageSource:
    """Hashed source intentionally retained in the manifest but not transformed."""

    source_path: Path
    relative_path: str
    source_sha256: str
    size_bytes: int
    suffix: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "source_path": str(self.source_path),
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "size_bytes": self.size_bytes,
            "suffix": self.suffix,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DocumentPackagePlan:
    """Read-only plan for several grouped documents in one ZIP file."""

    package_id: str
    provider_id: str
    source_root: Path
    output_zip: Path
    groups: tuple[DocumentPackageGroup, ...]
    unsupported: tuple[UnsupportedPackageSource, ...]
    gate: GateDecision
    undo: UndoDescriptor

    SCHEMA = "folderhome.document-package-plan.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())
        object.__setattr__(self, "output_zip", self.output_zip.resolve())
        if not self.package_id or not self.provider_id or not self.groups:
            raise ValueError("Dokumentpaket benötigt ID, Provider und Gruppen.")
        if not self.gate.required or self.gate.granted:
            raise ValueError("Dokumentpakete starten mit geschlossenem Schreib-Gate.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "package_id": self.package_id,
            "provider_id": self.provider_id,
            "source_root": str(self.source_root),
            "output_zip": str(self.output_zip),
            "groups": [group.to_dict() for group in self.groups],
            "unsupported": [source.to_dict() for source in self.unsupported],
            "gate": self.gate.to_dict(),
            "undo": self.undo.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DocumentPackageEntryResult:
    """Verified metadata for one generated member of the ZIP package."""

    group_id: str
    filename: str
    output_sha256: str
    output_size_bytes: int
    page_count: int | None
    source_document_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "group_id": self.group_id,
            "filename": self.filename,
            "output_sha256": self.output_sha256,
            "output_size_bytes": self.output_size_bytes,
            "page_count": self.page_count,
            "source_document_ids": list(self.source_document_ids),
        }


@dataclass(frozen=True, slots=True)
class DocumentPackageResult:
    """Verified ZIP publication result."""

    package_id: str
    provider_id: str
    output_zip: Path
    output_sha256: str
    output_size_bytes: int
    entries: tuple[DocumentPackageEntryResult, ...]

    SCHEMA = "folderhome.document-package-result.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_zip", self.output_zip.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "package_id": self.package_id,
            "provider_id": self.provider_id,
            "output_zip": str(self.output_zip),
            "output_sha256": self.output_sha256,
            "output_size_bytes": self.output_size_bytes,
            "entries": [entry.to_dict() for entry in self.entries],
            "status": "executed",
        }
