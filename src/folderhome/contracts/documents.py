"""Provider-neutral document identity and processing contracts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_DOCUMENT_ID_PATTERN = re.compile(r"doc_[0-9a-f]{64}")


class ContentFormat(StrEnum):
    """Shape of extracted text retained for downstream consumers."""

    TEXT = "text"
    MARKDOWN = "markdown"


class PrivacyStatus(StrEnum):
    """Fail-closed privacy state before content leaves the local pipeline."""

    NOT_CHECKED = "not_checked"
    CLEAR = "clear"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class IndexStatus(StrEnum):
    """State of one document at the search-provider boundary."""

    NOT_INDEXED = "not_indexed"
    INDEXED = "indexed"
    SKIPPED = "skipped"
    FAILED = "failed"


def build_document_id(source_path: Path, source_sha256: str) -> str:
    """Build a stable identity from canonical source location and file content."""

    _validate_sha256(source_sha256, field_name="source_sha256")
    canonical_path = os.path.normcase(str(source_path.resolve()))
    material = f"folderhome.document.v1\0{canonical_path}\0{source_sha256}"
    return f"doc_{sha256(material.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """One extracted document without implicit disclosure of its raw text."""

    document_id: str
    source_path: Path
    filename: str
    media_type: str
    source_sha256: str
    size_bytes: int
    modified_at: str
    text: str
    content_format: ContentFormat
    extraction_provider: str
    extraction_method: str
    privacy_status: PrivacyStatus
    privacy_summary: str
    index_status: IndexStatus
    index_provider: str | None
    index_ref: str | None

    def __post_init__(self) -> None:
        source_path = self.source_path.resolve()
        object.__setattr__(self, "source_path", source_path)
        if _DOCUMENT_ID_PATTERN.fullmatch(self.document_id) is None:
            raise ValueError("document_id must use doc_<sha256>")
        _validate_sha256(self.source_sha256, field_name="source_sha256")
        if not self.filename:
            raise ValueError("filename must not be empty")
        if not self.media_type:
            raise ValueError("media_type must not be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        if not self.modified_at:
            raise ValueError("modified_at must not be empty")
        if not self.extraction_provider or not self.extraction_method:
            raise ValueError("extraction_provider and extraction_method are required")
        if not self.privacy_summary:
            raise ValueError("privacy_summary must not be empty")
        if self.index_status is IndexStatus.INDEXED and not (
            self.index_provider and self.index_ref
        ):
            raise ValueError("indexed documents require index_provider and index_ref")

    def to_dict(self, *, include_text: bool = False) -> dict[str, object]:
        """Serialize metadata; raw text is opt-in to prevent accidental leakage."""

        payload: dict[str, object] = {
            "document_id": self.document_id,
            "source_path": str(self.source_path),
            "filename": self.filename,
            "media_type": self.media_type,
            "source_sha256": self.source_sha256,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "content_format": self.content_format.value,
            "extraction": {
                "provider": self.extraction_provider,
                "method": self.extraction_method,
            },
            "privacy": {
                "status": self.privacy_status.value,
                "summary": self.privacy_summary,
            },
            "index": {
                "status": self.index_status.value,
                "provider": self.index_provider,
                "ref": self.index_ref,
            },
        }
        if include_text:
            payload["text"] = self.text
        return payload


def _validate_sha256(value: str, *, field_name: str) -> None:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase 64-character sha256")
