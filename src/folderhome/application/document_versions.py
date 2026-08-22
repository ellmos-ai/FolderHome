"""Explainable document version ordering, comparison, and archive proposals."""

from __future__ import annotations

import re
from datetime import datetime
from hashlib import sha256

from folderhome.contracts import (
    ArchiveProposal,
    DocumentFamily,
    DocumentRecord,
    DocumentVersion,
    DocumentVersionComparison,
    PrivacyStatus,
    VersionDateBasis,
    VersionDateConfidence,
)

_EXPLICIT_DATE = re.compile(
    r"(?i)\b(?:gültig\s+ab|vertragsstand|stand|vom)\s*:?[ \t]*"
    r"(?P<date>\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})"
)
_FILENAME_DATE = re.compile(
    r"(?P<date>\d{4}[-_.]\d{2}[-_.]\d{2}|\d{2}[.-]\d{2}[.-]\d{4})"
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")


def build_document_family(
    label: str,
    documents: tuple[DocumentRecord, ...],
) -> DocumentFamily:
    """Order matching records using explicit dates before weaker filesystem hints."""

    normalized_label = _WHITESPACE.sub(" ", label).strip()
    if not normalized_label:
        raise ValueError("Dokumentfamilie benötigt eine Bezeichnung.")
    if not documents:
        raise ValueError("Dokumentfamilie benötigt mindestens ein Dokument.")
    family_id = f"family_{sha256(normalized_label.casefold().encode('utf-8')).hexdigest()}"
    versions = tuple(
        sorted(
            (_build_version(family_id, normalized_label, document) for document in documents),
            key=lambda version: (
                version.version_date,
                version.document.modified_at,
                version.document.filename.casefold(),
            ),
            reverse=True,
        )
    )
    return DocumentFamily(family_id=family_id, label=normalized_label, versions=versions)


def compare_document_versions(
    older: DocumentVersion,
    newer: DocumentVersion,
) -> DocumentVersionComparison:
    """Return sentence deltas without semantic or legal interpretation."""

    if older.family_id != newer.family_id:
        raise ValueError("Verglichene Dokumente gehören nicht zur selben Familie.")
    if (
        older.document.privacy_status is not PrivacyStatus.CLEAR
        or newer.document.privacy_status is not PrivacyStatus.CLEAR
    ):
        raise PermissionError(
            "Versionsvergleich ist wegen des Datenschutzstatus mindestens eines Dokuments gesperrt."
        )
    older_sentences = _sentences(older.document.text)
    newer_sentences = _sentences(newer.document.text)
    older_set = set(older_sentences)
    newer_set = set(newer_sentences)
    return DocumentVersionComparison(
        older_document_id=older.document.document_id,
        newer_document_id=newer.document.document_id,
        removed_sentences=tuple(
            sentence for sentence in older_sentences if sentence not in newer_set
        ),
        added_sentences=tuple(
            sentence for sentence in newer_sentences if sentence not in older_set
        ),
    )


def build_archive_proposals(
    family: DocumentFamily,
    *,
    archive_folder: str = "Archiv",
) -> tuple[ArchiveProposal, ...]:
    """Propose reversible FCSA moves for every version except the retained latest."""

    archive_folder = _WHITESPACE.sub(" ", archive_folder).strip()
    if not archive_folder or "/" in archive_folder or "\\" in archive_folder:
        raise ValueError("archive_folder muss ein einzelner sicherer Ordnername sein.")
    retained = family.latest.document
    return tuple(
        ArchiveProposal(
            document_id=version.document.document_id,
            retained_document_id=retained.document_id,
            source_path=version.document.source_path,
            target_path=(
                version.document.source_path.parent
                / archive_folder
                / version.document.filename
            ),
        )
        for version in family.versions[1:]
    )


def _build_version(
    family_id: str,
    family_label: str,
    document: DocumentRecord,
) -> DocumentVersion:
    explicit = _EXPLICIT_DATE.search(document.text)
    if explicit:
        version_date = _parse_date(explicit.group("date"))
        basis = VersionDateBasis.DOCUMENT_TEXT
        confidence = VersionDateConfidence.HIGH
        evidence = explicit.group(0)
    else:
        filename = _FILENAME_DATE.search(document.filename)
        if filename:
            version_date = _parse_date(filename.group("date").replace("_", "-"))
            basis = VersionDateBasis.FILENAME
            confidence = VersionDateConfidence.MEDIUM
            evidence = filename.group(0)
        else:
            version_date = datetime.fromisoformat(
                document.modified_at.replace("Z", "+00:00")
            ).date()
            basis = VersionDateBasis.FILE_MODIFIED
            confidence = VersionDateConfidence.LOW
            evidence = document.modified_at
    return DocumentVersion(
        family_id=family_id,
        family_label=family_label,
        document=document,
        version_date=version_date.isoformat(),
        date_basis=basis,
        date_confidence=confidence,
        date_evidence=evidence,
    )


def _parse_date(value: str):
    for pattern in ("%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Ungültiges Versionsdatum: {value}")


def _sentences(text: str) -> tuple[str, ...]:
    normalized = _WHITESPACE.sub(" ", text).strip()
    return tuple(part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip())
