"""Read-only adapter for the pinned doc-services provider."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
)
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PluginDescriptor,
    PrivacyStatus,
    build_document_id,
)


class DocServicesBridgeError(RuntimeError):
    """Raised when doc-services cannot safely extract one document."""


class UnsupportedDocumentError(DocServicesBridgeError):
    """Raised when doc-services has no declared format for the source."""


class DocServicesBridge:
    """Translate doc-services results into the stable FolderHome document contract."""

    def __init__(
        self,
        *,
        plugin: PluginDescriptor,
        provider_root: Path,
        allow_ocr: bool = False,
    ) -> None:
        self._plugin = plugin
        self._provider_root = provider_root.resolve()
        self._allow_ocr = allow_ocr

    @property
    def provider_revision(self) -> str:
        return self._plugin.source_revision

    def extract(self, source_path: Path) -> DocumentRecord:
        source_path = source_path.resolve()
        if not source_path.is_file():
            raise DocServicesBridgeError(f"Dokumentdatei fehlt: {source_path}")
        try:
            package = load_pinned_python_modules(
                plugin=self._plugin,
                provider_root=self._provider_root,
                package_name="doc_services",
            )["doc_services"]
            if package.format_von(source_path) is None:
                raise UnsupportedDocumentError(
                    f"Dateityp wird nicht unterstützt: {source_path.suffix or '(ohne Endung)'}"
                )
            registry = package.Registry()
            if not self._allow_ocr:
                disabled = registry.config.setdefault("disabled", [])
                if "ocr-tesseract" not in disabled:
                    disabled.append("ocr-tesseract")
            result = package.extrahieren(source_path, reg=registry, lernen=False)
            _, privacy = package.darf_weitergegeben_werden(result.text, ist_text=True)
            path_hint = package.Klassifikator().pfad(source_path)
        except UnsupportedDocumentError:
            raise
        except ProviderCheckoutError as exc:
            raise DocServicesBridgeError(str(exc)) from exc
        except Exception as exc:
            raise DocServicesBridgeError(f"Dokument konnte nicht extrahiert werden: {exc}") from exc

        source_hash = _sha256_file(source_path)
        privacy_status = _privacy_status(package, privacy.ampel, path_hint)
        privacy_summary = privacy.bericht().replace("GRUEN", "GRÜN")
        if path_hint and privacy_status is PrivacyStatus.REVIEW_REQUIRED:
            privacy_summary = f"{privacy_summary}\nPfadprüfung: {path_hint}"
        stat = source_path.stat()
        content_format = (
            ContentFormat.MARKDOWN
            if result.produces == ContentFormat.MARKDOWN.value
            else ContentFormat.TEXT
        )
        return DocumentRecord(
            document_id=build_document_id(source_path, source_hash),
            source_path=source_path,
            filename=source_path.name,
            media_type=mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
            source_sha256=source_hash,
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat().replace(
                "+00:00", "Z"
            ),
            text=result.text,
            content_format=content_format,
            extraction_provider=self._plugin.plugin_id,
            extraction_method=_extraction_method(result.backend),
            privacy_status=privacy_status,
            privacy_summary=privacy_summary,
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _privacy_status(package: object, ampel: str, path_hint: str | None) -> PrivacyStatus:
    if ampel == package.ROT:
        return PrivacyStatus.BLOCKED
    if ampel == package.GELB or path_hint:
        return PrivacyStatus.REVIEW_REQUIRED
    if ampel == package.GRUEN:
        return PrivacyStatus.CLEAR
    return PrivacyStatus.BLOCKED


def _extraction_method(provider_method: str) -> str:
    """Normalize provider vocabulary at the FolderHome contract boundary."""

    return {"direkt": "direct"}.get(provider_method, provider_method)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
