"""Build one deterministic ZIP containing one bundle per document type."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from folderhome.application.document_transform import (
    IMAGE_SUFFIXES,
    BundleDocumentExtractor,
    build_passthrough_record,
    plan_document_bundle,
)
from folderhome.capabilities.document_transform import (
    DocumentTransformCapabilityError,
    publish_new_bytes,
    render_document_bundle,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    BoundedBytesIO,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    BundleFormat,
    DocumentBundlePlan,
    DocumentPackageEntryResult,
    DocumentPackageGroup,
    DocumentPackagePlan,
    DocumentPackageResult,
    DocumentRecord,
    GateDecision,
    UndoDescriptor,
    UnsupportedPackageSource,
)

_PROVIDER_ID = "folderhome.document-package"
_EXTRACTABLE_SUFFIXES = {
    ".csv",
    ".doc",
    ".docx",
    ".eml",
    ".epub",
    ".htm",
    ".html",
    ".md",
    ".markdown",
    ".msg",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
}
_GROUP_ALIASES = {
    ".htm": "html",
    ".html": "html",
    ".markdown": "markdown",
    ".md": "markdown",
}


class DocumentPackageError(RuntimeError):
    """Raised when a grouped package cannot be planned or safely published."""


@dataclass(frozen=True, slots=True)
class PreparedDocumentPackage:
    """Serializable plan plus in-memory records retained for gated rendering."""

    plan: DocumentPackagePlan
    documents: tuple[DocumentRecord, ...]


def prepare_folder_package(
    source_dir: Path,
    *,
    output_zip: Path,
    extractor: BundleDocumentExtractor,
    recursive: bool = True,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> PreparedDocumentPackage:
    """Group sources and prepare bundle plans without creating output paths."""

    root = source_dir.resolve()
    output = output_zip.resolve()
    if not root.is_dir() or root.is_symlink():
        raise DocumentPackageError(f"Quellordner fehlt oder ist ein Link: {root}")
    if output.suffix.lower() != ".zip":
        raise DocumentPackageError("Paketausgabe muss auf .zip enden.")
    if output.exists():
        raise DocumentPackageError(f"Paketausgabe existiert bereits: {output}")

    try:
        inventory = inventory_files(
            root,
            recursive=recursive,
            policy=resource_policy,
            exclude_paths=(output,),
        )
    except ResourceLimitExceeded as exc:
        raise DocumentPackageError(str(exc)) from exc
    if inventory.symlinks:
        raise DocumentPackageError(
            f"Symbolischer Link ist nicht zulässig: {inventory.symlinks[0]}"
        )
    files = inventory.files
    records_by_group: dict[str, list[DocumentRecord]] = {}
    unsupported = []
    text_budget = ResourceBudget(resource_policy)
    for source in files:
        suffix = source.suffix.lower()
        group_id = _group_id(suffix)
        if group_id is None:
            unsupported.append(
                UnsupportedPackageSource(
                    source_path=source,
                    relative_path=source.relative_to(root).as_posix(),
                    source_sha256=_sha256_file(source),
                    size_bytes=source.stat().st_size,
                    suffix=suffix,
                    reason="Für diesen Dateityp ist kein Transformationspfad gebunden.",
                )
            )
            continue
        try:
            record = (
                build_passthrough_record(source)
                if suffix == ".pdf" or suffix in IMAGE_SUFFIXES
                else extractor.extract(source)
            )
        except Exception as exc:
            raise DocumentPackageError(
                f"Dokumentgruppe {group_id} konnte {source.name} nicht lesen: {exc}"
            ) from exc
        try:
            text_budget.consume_extracted_text(len(record.text))
        except ResourceLimitExceeded as exc:
            raise DocumentPackageError(str(exc)) from exc
        records_by_group.setdefault(group_id, []).append(record)

    if not records_by_group:
        raise DocumentPackageError(
            "Der Quellordner enthält keine unterstützte Dokumentgruppe."
        )
    groups = []
    ordered_documents = []
    virtual_root = output.parent / f".{output.name}.contents"
    for group_id in sorted(records_by_group):
        records = tuple(records_by_group[group_id])
        output_format = (
            BundleFormat.PDF if group_id in {"images", "pdf"} else BundleFormat.TXT
        )
        output_filename = _output_filename(group_id, output_format)
        try:
            bundle_plan = plan_document_bundle(
                records,
                source_root=root,
                output_path=virtual_root / output_filename,
                output_format=output_format,
                resource_policy=resource_policy,
            )
        except Exception as exc:
            raise DocumentPackageError(
                f"Dokumentgruppe {group_id} ist nicht bündelbar: {exc}"
            ) from exc
        groups.append(
            DocumentPackageGroup(
                group_id=group_id,
                bundle_id=bundle_plan.bundle_id,
                output_filename=output_filename,
                output_format=output_format,
                sources=bundle_plan.sources,
            )
        )
        ordered_documents.extend(records)

    material = "\0".join(
        (
            _PROVIDER_ID,
            str(output),
            *(group.bundle_id for group in groups),
            *(item.source_sha256 for item in unsupported),
        )
    )
    plan = DocumentPackagePlan(
        package_id=f"package_{sha256(material.encode('utf-8')).hexdigest()}",
        provider_id=_PROVIDER_ID,
        source_root=root,
        output_zip=output,
        groups=tuple(groups),
        unsupported=tuple(unsupported),
        gate=GateDecision(
            required=True,
            granted=False,
            reason="Das ZIP-Paket benötigt eine explizite Schreibfreigabe.",
        ),
        undo=UndoDescriptor(True, "delete-created-zip"),
    )
    return PreparedDocumentPackage(plan=plan, documents=tuple(ordered_documents))


def write_folder_package(
    prepared: PreparedDocumentPackage,
    *,
    allow_output_write: bool,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> DocumentPackageResult:
    """Render every group, embed a manifest, and atomically publish one ZIP."""

    if not allow_output_write:
        raise DocumentPackageError(
            "Schreibfreigabe fehlt; das Dokumentpaket wurde nicht erzeugt."
        )
    plan = prepared.plan
    output = plan.output_zip.resolve()
    if output.exists():
        raise DocumentPackageError(f"Paketausgabe existiert bereits: {output}")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise DocumentPackageError(
            f"Ausgabeordner fehlt oder ist ein symbolischer Link: {output.parent}"
        )
    records = {document.document_id: document for document in prepared.documents}
    expected_ids = {
        source.document_id for group in plan.groups for source in group.sources
    }
    if set(records) != expected_ids or len(records) != len(prepared.documents):
        raise DocumentPackageError(
            "Ausführungsdokumente stimmen nicht vollständig mit dem Paketplan überein."
        )
    budget = ResourceBudget(resource_policy)
    for group in plan.groups:
        for source in group.sources:
            try:
                budget.consume_source(source.size_bytes)
                budget.consume_extracted_text(len(records[source.document_id].text))
            except ResourceLimitExceeded as exc:
                raise DocumentPackageError(str(exc)) from exc
            if (
                not source.source_path.is_file()
                or source.source_path.is_symlink()
                or _sha256_file(source.source_path) != source.source_sha256
            ):
                raise DocumentPackageError(
                    f"Paketquelle wurde seit der Planung geändert: {source.relative_path}"
                )
    for source in plan.unsupported:
        try:
            budget.consume_source(source.size_bytes)
        except ResourceLimitExceeded as exc:
            raise DocumentPackageError(str(exc)) from exc
        if (
            not source.source_path.is_file()
            or source.source_path.is_symlink()
            or _sha256_file(source.source_path) != source.source_sha256
        ):
            raise DocumentPackageError(
                f"Nicht unterstützte Quelle wurde seit der Planung geändert: "
                f"{source.relative_path}"
            )

    entries = []
    payloads = []
    try:
        for group in plan.groups:
            bundle_plan = DocumentBundlePlan(
                bundle_id=group.bundle_id,
                provider_id="folderhome.document-transform",
                source_root=plan.source_root,
                output_path=output.parent / group.output_filename,
                output_format=group.output_format,
                sources=group.sources,
                gate=GateDecision(
                    required=True,
                    granted=False,
                    reason="Paketinterne Ausgabe wird nur innerhalb des ZIP veröffentlicht.",
                ),
                undo=UndoDescriptor(True, "delete-created-output"),
            )
            group_records = {
                source.document_id: records[source.document_id]
                for source in group.sources
            }
            payload, page_count = render_document_bundle(
                bundle_plan,
                group_records,
                resource_policy=resource_policy,
            )
            budget.consume_output(len(payload))
            payloads.append((group.output_filename, payload))
            entries.append(
                DocumentPackageEntryResult(
                    group_id=group.group_id,
                    filename=group.output_filename,
                    output_sha256=sha256(payload).hexdigest(),
                    output_size_bytes=len(payload),
                    page_count=page_count,
                    source_document_ids=tuple(
                        source.document_id for source in group.sources
                    ),
                )
            )
        manifest = _manifest_bytes(plan, tuple(entries))
        package_bytes = _zip_bytes(
            (*payloads, ("manifest.json", manifest)),
            resource_policy=resource_policy,
        )
        publish_new_bytes(output, package_bytes)
    except (DocumentTransformCapabilityError, ResourceLimitExceeded) as exc:
        raise DocumentPackageError(str(exc)) from exc
    return DocumentPackageResult(
        package_id=plan.package_id,
        provider_id=plan.provider_id,
        output_zip=output,
        output_sha256=_sha256_file(output),
        output_size_bytes=output.stat().st_size,
        entries=tuple(entries),
    )


def _group_id(suffix: str) -> str | None:
    if suffix in IMAGE_SUFFIXES:
        return "images"
    if suffix == ".pdf":
        return "pdf"
    if suffix not in _EXTRACTABLE_SUFFIXES:
        return None
    return _GROUP_ALIASES.get(suffix, suffix.removeprefix("."))


def _output_filename(group_id: str, output_format: BundleFormat) -> str:
    names = {
        "images": "Bilder.pdf",
        "markdown": "Markdown.txt",
        "pdf": "PDFs.pdf",
        "txt": "TXT.txt",
    }
    return names.get(group_id, f"{group_id.upper()}.{output_format.value}")


def _manifest_bytes(
    plan: DocumentPackagePlan,
    entries: tuple[DocumentPackageEntryResult, ...],
) -> bytes:
    payload = {
        "schema": "folderhome.document-package-manifest.v1",
        "package_id": plan.package_id,
        "provider_id": plan.provider_id,
        "source_root": str(plan.source_root),
        "groups": [group.to_dict() for group in plan.groups],
        "unsupported": [source.to_dict() for source in plan.unsupported],
        "entries": [entry.to_dict() for entry in entries],
    }
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _zip_bytes(
    entries: tuple[tuple[str, bytes], ...],
    *,
    resource_policy: ResourcePolicy,
) -> bytes:
    buffer = BoundedBytesIO(
        resource_policy.max_archive_bytes,
        budget_name="Archivbyte-Budget",
    )
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for filename, payload in entries:
            info = zipfile.ZipInfo(filename=filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            info.flag_bits |= 0x800
            archive.writestr(info, payload, compresslevel=9)
    return buffer.getvalue()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
