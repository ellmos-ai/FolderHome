"""Provider-neutral contracts for document families and version plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from folderhome.contracts.documents import DocumentRecord

_FAMILY_ID_PATTERN = re.compile(r"family_[0-9a-f]{64}")
_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class VersionDateBasis(StrEnum):
    """Evidence used to order one document version."""

    DOCUMENT_TEXT = "document_text"
    FILENAME = "filename"
    FILE_MODIFIED = "file_modified"


class VersionDateConfidence(StrEnum):
    """Conservative confidence in the inferred ordering date."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    """One document interpreted as a dated version of a user-named family."""

    family_id: str
    family_label: str
    document: DocumentRecord
    version_date: str
    date_basis: VersionDateBasis
    date_confidence: VersionDateConfidence
    date_evidence: str

    def __post_init__(self) -> None:
        if _FAMILY_ID_PATTERN.fullmatch(self.family_id) is None:
            raise ValueError("family_id must use family_<sha256>")
        if not self.family_label.strip():
            raise ValueError("family_label must not be empty")
        if _ISO_DATE_PATTERN.fullmatch(self.version_date) is None:
            raise ValueError("version_date must use YYYY-MM-DD")
        if not self.date_evidence:
            raise ValueError("date_evidence must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "family_id": self.family_id,
            "family_label": self.family_label,
            "document": self.document.to_dict(),
            "version_date": self.version_date,
            "date_basis": self.date_basis.value,
            "date_confidence": self.date_confidence.value,
            "date_evidence": self.date_evidence,
        }


@dataclass(frozen=True, slots=True)
class DocumentFamily:
    """Ordered versions belonging to one explicit user subject."""

    family_id: str
    label: str
    versions: tuple[DocumentVersion, ...]

    def __post_init__(self) -> None:
        if not self.versions:
            raise ValueError("DocumentFamily requires at least one version")
        if any(version.family_id != self.family_id for version in self.versions):
            raise ValueError("all versions must use the family id")

    @property
    def latest(self) -> DocumentVersion:
        return self.versions[0]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.document-family.v1",
            "family_id": self.family_id,
            "label": self.label,
            "latest_document_id": self.latest.document.document_id,
            "versions": [version.to_dict() for version in self.versions],
        }


@dataclass(frozen=True, slots=True)
class DocumentVersionComparison:
    """Sentence-level, source-grounded delta between two versions."""

    older_document_id: str
    newer_document_id: str
    removed_sentences: tuple[str, ...]
    added_sentences: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.document-version-comparison.v1",
            "older_document_id": self.older_document_id,
            "newer_document_id": self.newer_document_id,
            "removed_sentences": list(self.removed_sentences),
            "added_sentences": list(self.added_sentences),
        }


@dataclass(frozen=True, slots=True)
class ArchiveProposal:
    """Non-executing move proposal for an older document version."""

    document_id: str
    retained_document_id: str
    source_path: Path
    target_path: Path
    provider_id: str = "file-collect-sort-action"
    capability_id: str = "documents.collect_sort"
    action: str = "move"
    collision_policy: str = "rename"
    status: str = "planned"
    gate_required: bool = True
    gate_granted: bool = False
    undo_action: str = "move_back"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        object.__setattr__(self, "target_path", self.target_path.resolve())
        if self.status != "planned" or self.gate_granted:
            raise ValueError("archive proposals must remain planned and ungranted")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.archive-proposal.v1",
            "document_id": self.document_id,
            "retained_document_id": self.retained_document_id,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path),
            "provider_id": self.provider_id,
            "capability_id": self.capability_id,
            "action": self.action,
            "collision_policy": self.collision_policy,
            "status": self.status,
            "gate": {"required": self.gate_required, "granted": self.gate_granted},
            "undo_action": self.undo_action,
        }
