"""Natural document search and evidence-based theme dossiers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit

_TOKEN_PATTERN = re.compile(r"[^\W\d_][^\W_]*", re.UNICODE)
_QUOTED_PATTERN = re.compile(r"[\"„“](.+?)[\"“]", re.DOTALL)
_STOPWORDS = {
    "abgelegt",
    "alle",
    "alles",
    "dem",
    "dokument",
    "einem",
    "einen",
    "finden",
    "für",
    "gib",
    "habe",
    "ich",
    "informationen",
    "ist",
    "meine",
    "meiner",
    "meinen",
    "mir",
    "nach",
    "neueste",
    "neuesten",
    "steht",
    "suche",
    "thema",
    "über",
    "was",
    "welchem",
    "welche",
    "welcher",
    "welches",
    "zu",
}


class DocumentSearcher(Protocol):
    """Search port implemented by a local document index."""

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]: ...


@dataclass(frozen=True, slots=True)
class DocumentSearchResponse:
    """Search response retaining the original and normalized user wording."""

    original_query: str
    search_query: str
    limit: int
    hits: tuple[KnowledgeDigestSearchHit, ...]

    @property
    def total_hits(self) -> int:
        return len(self.hits)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.document-search.v1",
            "original_query": self.original_query,
            "search_query": self.search_query,
            "limit": self.limit,
            "total_hits": self.total_hits,
            "hits": [_hit_to_dict(hit) for hit in self.hits],
        }


@dataclass(frozen=True, slots=True)
class ThemeDossier:
    """Evidence list for a topic without pretending to be an LLM synthesis."""

    topic: str
    search_query: str
    limit: int
    hits: tuple[KnowledgeDigestSearchHit, ...]
    potentially_truncated: bool
    markdown: str

    @property
    def total_hits(self) -> int:
        return len(self.hits)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.theme-dossier.v1",
            "topic": self.topic,
            "search_query": self.search_query,
            "limit": self.limit,
            "total_hits": self.total_hits,
            "potentially_truncated": self.potentially_truncated,
            "hits": [_hit_to_dict(hit) for hit in self.hits],
            "markdown": self.markdown,
        }


def normalize_document_query(value: str) -> str:
    """Reduce conversational German wording to safe FTS search terms."""

    value = value.strip()
    if not value:
        raise ValueError("Suchanfrage darf nicht leer sein.")
    quoted = _QUOTED_PATTERN.search(value)
    candidate = quoted.group(1) if quoted else value
    terms = [
        token
        for token in _TOKEN_PATTERN.findall(candidate)
        if token.casefold() not in _STOPWORDS and len(token) > 2
    ]
    if not terms:
        raise ValueError("Die Suchanfrage enthält keinen auswertbaren Suchbegriff.")
    return " ".join(dict.fromkeys(terms))


def search_documents(
    query: str,
    *,
    searcher: DocumentSearcher,
    limit: int = 20,
) -> DocumentSearchResponse:
    """Search the local index using normalized user wording."""

    search_query = normalize_document_query(query)
    hits = searcher.search(search_query, limit=limit)
    return DocumentSearchResponse(
        original_query=query,
        search_query=search_query,
        limit=limit,
        hits=hits,
    )


def build_theme_dossier(
    topic: str,
    *,
    searcher: DocumentSearcher,
    limit: int = 100,
) -> ThemeDossier:
    """Build a local evidence dossier from every returned topic match."""

    response = search_documents(topic, searcher=searcher, limit=limit)
    potentially_truncated = response.total_hits >= limit
    markdown = _render_dossier(
        topic=topic.strip(),
        hits=response.hits,
        potentially_truncated=potentially_truncated,
    )
    return ThemeDossier(
        topic=topic.strip(),
        search_query=response.search_query,
        limit=limit,
        hits=response.hits,
        potentially_truncated=potentially_truncated,
        markdown=markdown,
    )


def _render_dossier(
    *,
    topic: str,
    hits: tuple[KnowledgeDigestSearchHit, ...],
    potentially_truncated: bool,
) -> str:
    lines = [
        f"# Themendossier: {topic}",
        "",
        "> Lokale Fundstellen aus dem FolderHome-Dokumentindex; keine Rechts-, Finanz- "
        "oder Medizinbewertung.",
        "",
        "## Fundstellen",
        "",
    ]
    if not hits:
        lines.append("Keine passende Fundstelle im derzeit indexierten Bestand.")
    for hit in hits:
        snippet = hit.snippet.replace(">>>", "**").replace("<<<", "**")
        lines.extend((f"### {hit.filename}", "", snippet or "Keine Vorschau verfügbar.", ""))
    if potentially_truncated:
        lines.extend(
            (
                "## Abdeckungsgrenze",
                "",
                "Die Trefferliste ist möglicherweise gekürzt, weil das Suchlimit erreicht wurde.",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _hit_to_dict(hit: KnowledgeDigestSearchHit) -> dict[str, object]:
    return {
        "source": hit.source,
        "filename": hit.filename,
        "file_type": hit.file_type,
        "snippet": hit.snippet,
        "relevance": hit.relevance,
        "word_count": hit.word_count,
    }
