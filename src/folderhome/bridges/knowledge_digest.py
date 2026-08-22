"""Local index and search adapter for the pinned KnowledgeDigest provider."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from types import ModuleType

from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
)
from folderhome.contracts import DocumentRecord, IndexStatus, PluginDescriptor


class KnowledgeDigestBridgeError(RuntimeError):
    """Raised when the local document index cannot be used safely."""


@dataclass(frozen=True, slots=True)
class KnowledgeDigestSearchHit:
    """Provider-neutral document search result."""

    source: str
    filename: str
    file_type: str
    snippet: str
    relevance: float
    word_count: int


class KnowledgeDigestBridge:
    """Keep KnowledgeDigest writes in one explicit FolderHome state directory."""

    def __init__(
        self,
        *,
        plugin: PluginDescriptor,
        provider_root: Path,
        state_dir: Path,
    ) -> None:
        self._plugin = plugin
        self._provider_root = provider_root.resolve()
        self._state_dir = state_dir.resolve()

    def index(self, document: DocumentRecord) -> DocumentRecord:
        """Index one unchanged source without moving or archiving the original."""

        source_path = document.source_path
        if not source_path.is_file():
            raise KnowledgeDigestBridgeError(f"Dokumentdatei fehlt: {source_path}")
        if _sha256_file(source_path) != document.source_sha256:
            raise KnowledgeDigestBridgeError(
                f"Dokument wurde seit der Extraktion geändert: {source_path}"
            )

        client = self._build_client()
        try:
            result = client.ingest(source_path, archive=False)
        except Exception as exc:
            raise KnowledgeDigestBridgeError(
                f"KnowledgeDigest konnte das Dokument nicht indexieren: {exc}"
            ) from exc
        finally:
            client.close()

        status = result.get("status")
        if status != "ok":
            detail = result.get("error") or f"unerwarteter Status {status!r}"
            raise KnowledgeDigestBridgeError(f"Dokument wurde nicht indexiert: {detail}")
        return replace(
            document,
            index_status=IndexStatus.INDEXED,
            index_provider=self._plugin.plugin_id,
            index_ref=f"knowledge://documents/{document.document_id}",
        )

    def search(self, query: str, *, limit: int = 20) -> tuple[KnowledgeDigestSearchHit, ...]:
        """Search the provider schema through a strictly read-only SQLite seam."""

        if not query.strip():
            raise KnowledgeDigestBridgeError("Suchanfrage darf nicht leer sein.")
        if limit < 1:
            raise KnowledgeDigestBridgeError("Suchlimit muss mindestens 1 sein.")
        schema_module = self._load_modules(("KnowledgeDigest.schema",))[
            "KnowledgeDigest.schema"
        ]
        database = self._state_dir / "knowledge.db"
        if not database.is_file():
            raise KnowledgeDigestBridgeError(f"KnowledgeDigest-Index fehlt: {database}")
        try:
            connection = sqlite3.connect(
                f"{database.as_uri()}?mode=ro&immutable=1",
                uri=True,
                timeout=30,
            )
            connection.row_factory = sqlite3.Row
            version_row = connection.execute(
                "SELECT value FROM schema_meta WHERE key='version'"
            ).fetchone()
            actual_version = int(version_row["value"]) if version_row else 0
            if actual_version != schema_module.SCHEMA_VERSION:
                raise KnowledgeDigestBridgeError(
                    "KnowledgeDigest-Schema stimmt nicht mit dem gepinnten Provider überein: "
                    f"erwartet {schema_module.SCHEMA_VERSION}, gefunden {actual_version}"
                )
            rows = connection.execute(
                """
                SELECT
                    d.filename,
                    d.file_type,
                    d.word_count,
                    dc.chunk_index,
                    snippet(document_fts, 1, '>>>', '<<<', '...', 30) AS snippet,
                    document_fts.rank AS relevance
                FROM document_fts
                JOIN document_chunks dc ON document_fts.rowid = dc.id
                JOIN documents d ON dc.doc_id = d.id
                WHERE document_fts MATCH ?
                ORDER BY document_fts.rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except KnowledgeDigestBridgeError:
            raise
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise KnowledgeDigestBridgeError(
                f"KnowledgeDigest-Suche ist fehlgeschlagen: {exc}"
            ) from exc
        finally:
            if "connection" in locals():
                connection.close()

        hits: list[KnowledgeDigestSearchHit] = []
        seen: set[str] = set()
        for row in rows:
            filename = str(row["filename"])
            if filename in seen:
                continue
            seen.add(filename)
            hits.append(
                KnowledgeDigestSearchHit(
                    source="document",
                    filename=filename,
                    file_type=str(row["file_type"]),
                    snippet=str(row["snippet"]),
                    relevance=float(row["relevance"]),
                    word_count=int(row["word_count"]),
                )
            )
        return tuple(hits)

    def _build_client(self) -> object:
        modules = self._load_modules(("KnowledgeDigest.config",))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        config_module = modules["KnowledgeDigest.config"]
        config = config_module.Config(self._state_dir / "provider-config.json")
        config.set("db_path", str(self._state_dir / "knowledge.db"))
        config.set("inbox_dir", str(self._state_dir / "inbox"))
        config.set("archive_dir", str(self._state_dir / "archive"))
        package = modules["KnowledgeDigest"]
        return package.KnowledgeDigest(
            db_path=self._state_dir / "knowledge.db",
            config=config,
        )

    def _load_modules(self, module_names: tuple[str, ...]) -> dict[str, ModuleType]:
        if self._plugin.plugin_id != "KnowledgeDigest":
            raise KnowledgeDigestBridgeError(
                f"Falscher Provider für die KnowledgeDigest-Bridge: {self._plugin.plugin_id}"
            )
        try:
            return load_pinned_python_modules(
                plugin=self._plugin,
                provider_root=self._provider_root,
                package_name="KnowledgeDigest",
                module_names=module_names,
                import_from_parent=True,
            )
        except ProviderCheckoutError as exc:
            raise KnowledgeDigestBridgeError(str(exc)) from exc


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
