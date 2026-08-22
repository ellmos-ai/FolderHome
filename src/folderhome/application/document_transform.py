"""Plan and publish deterministic document bundles with explicit write gates."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.capabilities.document_transform import (
    DocumentTransformCapabilityError,
    publish_new_bytes,
    render_document_bundle,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    BundleFormat,
    BundleSource,
    ContentFormat,
    DocumentBundlePlan,
    DocumentBundleResult,
    DocumentRecord,
    GateDecision,
    IndexStatus,
    PrivacyStatus,
    TransformTreatment,
    UndoDescriptor,
    build_document_id,
)

IMAGE_SUFFIXES = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
_PROVIDER_ID = "folderhome.document-transform"


class DocumentTransformError(RuntimeError):
    """Raised before or during a transform that cannot satisfy safety rules."""


class BundleDocumentExtractor(Protocol):
    """Read-only extraction port used for sources that need text."""

    def extract(self, source_path: Path) -> DocumentRecord: ...


def collect_bundle_documents(
    source_dir: Path,
    *,
    output_path: Path,
    output_format: BundleFormat,
    extractor: BundleDocumentExtractor,
    recursive: bool = True,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> tuple[DocumentRecord, ...]:
    """Collect deterministic records; preserve PDF/image sources without OCR."""

    source_dir = source_dir.resolve()
    output_path = output_path.resolve()
    if not source_dir.is_dir() or source_dir.is_symlink():
        raise DocumentTransformError(
            f"Dokumentenordner fehlt oder ist ein Link: {source_dir}"
        )
    try:
        inventory = inventory_files(
            source_dir,
            recursive=recursive,
            policy=resource_policy,
            exclude_paths=(output_path,),
        )
    except ResourceLimitExceeded as exc:
        raise DocumentTransformError(str(exc)) from exc
    if inventory.symlinks:
        raise DocumentTransformError(
            f"Symbolischer Link ist nicht zulässig: {inventory.symlinks[0]}"
        )
    files = inventory.files
    records = []
    text_budget = ResourceBudget(resource_policy)
    for path in files:
        if output_format is BundleFormat.PDF and (
            path.suffix.lower() == ".pdf" or path.suffix.lower() in IMAGE_SUFFIXES
        ):
            record = build_passthrough_record(path)
        else:
            record = extractor.extract(path)
        try:
            text_budget.consume_extracted_text(len(record.text))
        except ResourceLimitExceeded as exc:
            raise DocumentTransformError(str(exc)) from exc
        records.append(record)
    if not records:
        raise DocumentTransformError("Der Dokumentenordner enthält keine Bündelquellen.")
    return tuple(records)


def plan_document_bundle(
    documents: tuple[DocumentRecord, ...],
    *,
    source_root: Path,
    output_path: Path,
    output_format: BundleFormat,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> DocumentBundlePlan:
    """Create a content-free bundle plan without creating the output directory."""

    if not documents:
        raise DocumentTransformError("Mindestens ein Dokument ist erforderlich.")
    root = source_root.resolve()
    output = output_path.resolve()
    if not root.is_dir() or root.is_symlink():
        raise DocumentTransformError(f"Quellwurzel fehlt oder ist ein Link: {root}")
    if output.suffix.lower() != f".{output_format.value}":
        raise DocumentTransformError(
            f"Ausgabedatei muss auf .{output_format.value} enden."
        )
    if output.exists():
        raise DocumentTransformError(f"Ausgabedatei existiert bereits: {output}")

    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    sources = []
    budget = ResourceBudget(resource_policy)
    for document in documents:
        try:
            budget.consume_source(document.size_bytes)
            budget.consume_extracted_text(len(document.text))
        except ResourceLimitExceeded as exc:
            raise DocumentTransformError(str(exc)) from exc
        source = document.source_path.resolve()
        if document.document_id in seen_ids or source in seen_paths:
            raise DocumentTransformError("Dokumente dürfen im Bündel nicht doppelt vorkommen.")
        seen_ids.add(document.document_id)
        seen_paths.add(source)
        if not source.is_file() or source.is_symlink():
            raise DocumentTransformError(f"Bündelquelle fehlt oder ist ein Link: {source}")
        if not source.is_relative_to(root):
            raise DocumentTransformError(f"Bündelquelle verlässt source_root: {source}")
        if source == output:
            raise DocumentTransformError("Ausgabedatei darf keine Quelldatei ersetzen.")
        actual_hash = _sha256_file(source)
        if actual_hash != document.source_sha256:
            raise DocumentTransformError(
                f"Quelle passt nicht zum extrahierten Dokumentstand: {source}"
            )
        treatment, lossy, notice = _treatment(document, output_format)
        if (
            treatment
            in {TransformTreatment.EXTRACTED_TEXT, TransformTreatment.REFLOW_TEXT}
            and document.privacy_status is not PrivacyStatus.CLEAR
        ):
            raise DocumentTransformError(
                f"Datenschutzstatus blockiert Inhaltsbündel: {document.filename}"
            )
        sources.append(
            BundleSource(
                document_id=document.document_id,
                source_path=source,
                relative_path=source.relative_to(root).as_posix(),
                source_sha256=document.source_sha256,
                size_bytes=document.size_bytes,
                media_type=document.media_type,
                privacy_status=document.privacy_status,
                treatment=treatment,
                lossy=lossy,
                loss_notice=notice,
            )
        )
    sources.sort(key=lambda item: (item.relative_path.casefold(), item.relative_path))
    material = "\0".join(
        (
            _PROVIDER_ID,
            output_format.value,
            str(output),
            *(f"{item.relative_path}:{item.source_sha256}" for item in sources),
        )
    )
    return DocumentBundlePlan(
        bundle_id=f"bundle_{sha256(material.encode('utf-8')).hexdigest()}",
        provider_id=_PROVIDER_ID,
        source_root=root,
        output_path=output,
        output_format=output_format,
        sources=tuple(sources),
        gate=GateDecision(
            required=True,
            granted=False,
            reason="Die neue Ausgabedatei benötigt eine explizite Schreibfreigabe.",
        ),
        undo=UndoDescriptor(True, "delete-created-output"),
    )


def write_document_bundle(
    plan: DocumentBundlePlan,
    documents: tuple[DocumentRecord, ...],
    *,
    allow_output_write: bool,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> DocumentBundleResult:
    """Publish one new bundle atomically after revalidating every source."""

    if not allow_output_write:
        raise DocumentTransformError(
            "Schreibfreigabe fehlt; die Bündelausgabe wurde nicht erzeugt."
        )
    output = plan.output_path.resolve()
    if output.exists():
        raise DocumentTransformError(f"Ausgabedatei existiert bereits: {output}")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise DocumentTransformError(
            f"Ausgabeordner fehlt oder ist ein symbolischer Link: {output.parent}"
        )
    records = {document.document_id: document for document in documents}
    expected_ids = {source.document_id for source in plan.sources}
    if set(records) != expected_ids or len(records) != len(documents):
        raise DocumentTransformError(
            "Ausführungsdokumente stimmen nicht vollständig mit dem Plan überein."
        )
    budget = ResourceBudget(resource_policy)
    for source in plan.sources:
        document = records[source.document_id]
        try:
            budget.consume_source(source.size_bytes)
            budget.consume_extracted_text(len(document.text))
        except ResourceLimitExceeded as exc:
            raise DocumentTransformError(str(exc)) from exc
        if document.source_path.resolve() != source.source_path:
            raise DocumentTransformError(
                f"Quellpfad stimmt nicht mehr mit dem Plan überein: {source.relative_path}"
            )
        if not source.source_path.is_file() or source.source_path.is_symlink():
            raise DocumentTransformError(f"Bündelquelle fehlt: {source.source_path}")
        if _sha256_file(source.source_path) != source.source_sha256:
            raise DocumentTransformError(
                f"Quelle wurde seit der Planung geändert: {source.relative_path}"
            )
        if (
            source.treatment
            in {TransformTreatment.EXTRACTED_TEXT, TransformTreatment.REFLOW_TEXT}
            and document.privacy_status is not PrivacyStatus.CLEAR
        ):
            raise DocumentTransformError(
                f"Datenschutzstatus blockiert Inhaltsbündel: {source.relative_path}"
            )

    try:
        payload, page_count = render_document_bundle(
            plan,
            records,
            resource_policy=resource_policy,
        )
        publish_new_bytes(output, payload)
    except (DocumentTransformCapabilityError, ResourceLimitExceeded) as exc:
        raise DocumentTransformError(str(exc)) from exc
    return DocumentBundleResult(
        bundle_id=plan.bundle_id,
        provider_id=plan.provider_id,
        output_path=output,
        output_sha256=_sha256_file(output),
        output_size_bytes=output.stat().st_size,
        page_count=page_count,
        source_document_ids=tuple(source.document_id for source in plan.sources),
    )


def _treatment(
    document: DocumentRecord,
    output_format: BundleFormat,
) -> tuple[TransformTreatment, bool, str]:
    if output_format is BundleFormat.TXT:
        return (
            TransformTreatment.EXTRACTED_TEXT,
            True,
            "Nur extrahierter Text wird übernommen; ursprüngliches Layout und Bilder entfallen.",
        )
    suffix = document.source_path.suffix.lower()
    if suffix == ".pdf":
        return (
            TransformTreatment.PRESERVE_PDF_PAGES,
            False,
            "Vorhandene PDF-Seiten werden ohne inhaltliche Neusetzung montiert.",
        )
    if suffix in IMAGE_SUFFIXES:
        return (
            TransformTreatment.RASTERIZE_IMAGE,
            True,
            "Das Bild wird als PDF-Seite gerastert; editierbare Struktur entsteht nicht.",
        )
    return (
        TransformTreatment.REFLOW_TEXT,
        True,
        "Extrahierter Text wird neu gesetzt; Layout, Tabellen und Bilder können verloren gehen.",
    )


def build_passthrough_record(path: Path) -> DocumentRecord:
    source_hash = _sha256_file(path)
    stat = path.stat()
    is_pdf = path.suffix.lower() == ".pdf"
    return DocumentRecord(
        document_id=build_document_id(path, source_hash),
        source_path=path,
        filename=path.name,
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        source_sha256=source_hash,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat().replace(
            "+00:00", "Z"
        ),
        text="",
        content_format=ContentFormat.TEXT,
        extraction_provider=_PROVIDER_ID,
        extraction_method=("preserve_pdf_pages" if is_pdf else "rasterize_image"),
        privacy_status=PrivacyStatus.NOT_CHECKED,
        privacy_summary=(
            "Inhalt wird lokal seitengetreu übernommen; keine Textprüfung erforderlich."
            if is_pdf
            else "Bild wird lokal gerastert übernommen; OCR und Textprüfung sind deaktiviert."
        ),
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
