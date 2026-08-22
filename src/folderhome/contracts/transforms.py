"""Reusable document-bundle planning and result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from folderhome.contracts import GateDecision, UndoDescriptor
    from folderhome.contracts.documents import PrivacyStatus


class BundleFormat(StrEnum):
    """First bounded output formats of the reusable transform core."""

    TXT = "txt"
    PDF = "pdf"


class TransformTreatment(StrEnum):
    """How one source contributes to a bundle output."""

    EXTRACTED_TEXT = "extracted_text"
    PRESERVE_PDF_PAGES = "preserve_pdf_pages"
    RASTERIZE_IMAGE = "rasterize_image"
    REFLOW_TEXT = "reflow_text"


@dataclass(frozen=True, slots=True)
class BundleSource:
    """Source metadata and disclosed fidelity boundary without raw content."""

    document_id: str
    source_path: Path
    relative_path: str
    source_sha256: str
    size_bytes: int
    media_type: str
    privacy_status: PrivacyStatus
    treatment: TransformTreatment
    lossy: bool
    loss_notice: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if not self.document_id or not self.relative_path or not self.source_sha256:
            raise ValueError("Bündelquellen benötigen Identität, Relativpfad und Hash.")
        if self.size_bytes < 0 or not self.media_type or not self.loss_notice.strip():
            raise ValueError("Bündelquellen benötigen gültige Metadaten und Verlusthinweis.")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "source_path": str(self.source_path),
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "privacy_status": self.privacy_status.value,
            "treatment": self.treatment.value,
            "lossy": self.lossy,
            "loss_notice": self.loss_notice,
        }


@dataclass(frozen=True, slots=True)
class DocumentBundlePlan:
    """Deterministic, non-executing plan for one new TXT or PDF bundle."""

    bundle_id: str
    provider_id: str
    source_root: Path
    output_path: Path
    output_format: BundleFormat
    sources: tuple[BundleSource, ...]
    gate: GateDecision
    undo: UndoDescriptor

    SCHEMA = "folderhome.document-bundle-plan.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())
        object.__setattr__(self, "output_path", self.output_path.resolve())
        if not self.bundle_id or not self.provider_id or not self.sources:
            raise ValueError("Bündelplan benötigt ID, Provider und mindestens eine Quelle.")
        if not self.gate.required or self.gate.granted:
            raise ValueError("Bündelpläne müssen mit geschlossenem Schreib-Gate starten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "bundle_id": self.bundle_id,
            "provider_id": self.provider_id,
            "source_root": str(self.source_root),
            "output_path": str(self.output_path),
            "output_format": self.output_format.value,
            "sources": [source.to_dict() for source in self.sources],
            "gate": self.gate.to_dict(),
            "undo": self.undo.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DocumentBundleResult:
    """Verified publication result used by later original-handling gates."""

    bundle_id: str
    provider_id: str
    output_path: Path
    output_sha256: str
    output_size_bytes: int
    page_count: int | None
    source_document_ids: tuple[str, ...]

    SCHEMA = "folderhome.document-bundle-result.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", self.output_path.resolve())
        if self.output_size_bytes < 1 or not self.output_sha256:
            raise ValueError("Transformationsergebnis benötigt eine nichtleere Ausgabe.")
        if self.page_count is not None and self.page_count < 1:
            raise ValueError("PDF-Ausgaben benötigen mindestens eine Seite.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "bundle_id": self.bundle_id,
            "provider_id": self.provider_id,
            "output_path": str(self.output_path),
            "output_sha256": self.output_sha256,
            "output_size_bytes": self.output_size_bytes,
            "page_count": self.page_count,
            "source_document_ids": list(self.source_document_ids),
            "status": "executed",
        }
