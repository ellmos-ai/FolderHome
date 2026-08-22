"""Catalog-backed analysis for latest-document and version use cases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from folderhome.application.document_ingest import DocumentExtractor
from folderhome.application.document_search import DocumentSearcher, search_documents
from folderhome.application.document_versions import (
    build_archive_proposals,
    build_document_family,
    compare_document_versions,
)
from folderhome.bridges.doc_services import DocServicesBridgeError
from folderhome.capabilities.catalog import DocumentCatalogStore
from folderhome.contracts import (
    ArchiveProposal,
    DocumentFamily,
    DocumentVersionComparison,
)


class DocumentVersionAnalysisError(RuntimeError):
    """Raised when a catalog-backed version conclusion cannot be proven."""


@dataclass(frozen=True, slots=True)
class DocumentVersionAnalysis:
    """Latest version, evidence delta, and non-executing archive proposals."""

    original_query: str
    search_query: str
    family: DocumentFamily
    comparisons: tuple[DocumentVersionComparison, ...]
    comparison_blocked_document_ids: tuple[str, ...]
    archive_proposals: tuple[ArchiveProposal, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.document-version-analysis.v1",
            "original_query": self.original_query,
            "search_query": self.search_query,
            "family": self.family.to_dict(),
            "comparisons": [item.to_dict() for item in self.comparisons],
            "comparison_blocked_document_ids": list(
                self.comparison_blocked_document_ids
            ),
            "archive_proposals": [item.to_dict() for item in self.archive_proposals],
        }


def analyze_document_versions(
    query: str,
    *,
    catalog: DocumentCatalogStore,
    searcher: DocumentSearcher,
    extractor: DocumentExtractor,
    limit: int = 100,
    archive_folder: str = "Archiv",
) -> DocumentVersionAnalysis:
    """Resolve matching catalog sources, verify them, and analyze their versions."""

    response = search_documents(query, searcher=searcher, limit=limit)
    matching_filenames = {hit.filename for hit in response.hits}
    if not matching_filenames:
        raise DocumentVersionAnalysisError(
            "Keine indexierten Dokumente passen zur Versionsanfrage."
        )

    entries = tuple(
        item
        for item in catalog.load()
        if item.get("filename") in matching_filenames
    )
    if not entries:
        raise DocumentVersionAnalysisError(
            "Suchtreffer sind nicht im FolderHome-Dokumentkatalog belegt."
        )

    documents = []
    for entry in entries:
        source_value = entry.get("source_path")
        if not isinstance(source_value, str):
            raise DocumentVersionAnalysisError(
                "Katalogeintrag enthält keinen gültigen Quellpfad."
            )
        source_path = Path(source_value)
        try:
            document = extractor.extract(source_path)
        except DocServicesBridgeError as exc:
            raise DocumentVersionAnalysisError(
                f"Katalogquelle konnte nicht erneut geprüft werden: {exc}"
            ) from exc
        if (
            document.source_sha256 != entry.get("source_sha256")
            or document.document_id != entry.get("document_id")
        ):
            raise DocumentVersionAnalysisError(
                f"Katalogquelle wurde seit dem Ingest geändert: {source_path}"
            )
        documents.append(document)

    family = build_document_family(response.search_query, tuple(documents))
    comparisons: list[DocumentVersionComparison] = []
    blocked: list[str] = []
    for older in family.versions[1:]:
        try:
            comparisons.append(compare_document_versions(older, family.latest))
        except PermissionError:
            blocked.append(older.document.document_id)
    proposals = build_archive_proposals(family, archive_folder=archive_folder)
    return DocumentVersionAnalysis(
        original_query=query,
        search_query=response.search_query,
        family=family,
        comparisons=tuple(comparisons),
        comparison_blocked_document_ids=tuple(blocked),
        archive_proposals=proposals,
    )
