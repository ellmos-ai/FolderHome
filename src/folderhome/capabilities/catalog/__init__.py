"""Local metadata catalog for indexed FolderHome documents."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from folderhome.contracts import DocumentRecord, IndexStatus


class DocumentCatalogError(RuntimeError):
    """Raised when catalog state is invalid or cannot be persisted safely."""


class DocumentCatalogStore:
    """Persist document metadata atomically without raw extracted text."""

    SCHEMA = "folderhome.document-catalog.v1"

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir.resolve()
        self.path = self.state_dir / "folderhome-catalog.json"

    def load(self) -> tuple[dict[str, object], ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DocumentCatalogError(f"Dokumentkatalog ist nicht lesbar: {exc}") from exc
        if payload.get("schema") != self.SCHEMA:
            raise DocumentCatalogError(
                f"Unbekanntes Dokumentkatalog-Schema: {payload.get('schema')!r}"
            )
        documents = payload.get("documents")
        if not isinstance(documents, list):
            raise DocumentCatalogError("Dokumentkatalog enthält keine gültige Dokumentliste.")
        validated: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in documents:
            if not isinstance(item, dict):
                raise DocumentCatalogError("Dokumentkatalog enthält einen ungültigen Eintrag.")
            document_id = item.get("document_id")
            if not isinstance(document_id, str) or document_id in seen:
                raise DocumentCatalogError(
                    "Dokumentkatalog enthält eine fehlende oder doppelte Dokument-ID."
                )
            if "text" in item:
                raise DocumentCatalogError("Dokumentkatalog darf keinen Rohtext enthalten.")
            seen.add(document_id)
            validated.append(item)
        return tuple(validated)

    def merge(self, documents: tuple[DocumentRecord, ...]) -> None:
        current = {str(item["document_id"]): item for item in self.load()}
        for document in documents:
            if document.index_status is not IndexStatus.INDEXED:
                raise DocumentCatalogError(
                    f"Nur indexierte Dokumente dürfen katalogisiert werden: {document.filename}"
                )
            current[document.document_id] = document.to_dict()
        payload = {
            "schema": self.SCHEMA,
            "documents": [current[key] for key in sorted(current)],
        }
        self._write(payload)

    def _write(self, payload: dict[str, object]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.state_dir,
                prefix=".folderhome-catalog.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        except OSError as exc:
            raise DocumentCatalogError(
                f"Dokumentkatalog konnte nicht geschrieben werden: {exc}"
            ) from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
