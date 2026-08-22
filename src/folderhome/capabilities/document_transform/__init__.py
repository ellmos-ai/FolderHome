"""Reusable TXT/PDF rendering and atomic publication capability."""

from __future__ import annotations

import os
import tempfile
import textwrap
from io import BytesIO
from pathlib import Path

from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    BoundedBytesIO,
    ResourceBudget,
    ResourcePolicy,
)
from folderhome.contracts import (
    BundleFormat,
    DocumentBundlePlan,
    DocumentRecord,
    TransformTreatment,
)


class DocumentTransformCapabilityError(RuntimeError):
    """Raised when a renderer dependency or publication primitive fails."""


def render_document_bundle(
    plan: DocumentBundlePlan,
    records: dict[str, DocumentRecord],
    *,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> tuple[bytes, int | None]:
    """Render an in-memory payload; source handling remains in the application layer."""

    budget = ResourceBudget(resource_policy)
    for source in plan.sources:
        budget.consume_source(source.size_bytes)
        if source.treatment in {
            TransformTreatment.EXTRACTED_TEXT,
            TransformTreatment.REFLOW_TEXT,
        }:
            budget.consume_extracted_text(len(records[source.document_id].text))
    if plan.output_format is BundleFormat.TXT:
        payload = _text_payload(plan, records).encode("utf-8")
        budget.consume_output(len(payload))
        return payload, None
    if plan.output_format is BundleFormat.PDF:
        return _pdf_payload(plan, records, budget)
    raise DocumentTransformCapabilityError(
        f"Nicht unterstütztes Ausgabeformat: {plan.output_format}"
    )


def publish_new_bytes(path: Path, payload: bytes) -> None:
    """Publish bytes atomically without replacing an existing destination."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise DocumentTransformCapabilityError(
                f"Ausgabedatei existiert bereits: {path}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _text_payload(
    plan: DocumentBundlePlan,
    records: dict[str, DocumentRecord],
) -> str:
    sections = ["# FolderHome-Dokumentbündel"]
    for source in plan.sources:
        text = records[source.document_id].text.strip()
        sections.append(f"## {source.relative_path}\n\n{text}")
    return "\n\n".join(sections) + "\n"


def _pdf_payload(
    plan: DocumentBundlePlan,
    records: dict[str, DocumentRecord],
    budget: ResourceBudget,
) -> tuple[bytes, int]:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise DocumentTransformCapabilityError(
            "PDF-Bündel benötigen die optionale Abhängigkeit pypdf."
        ) from exc

    writer = PdfWriter()
    for source in plan.sources:
        if source.treatment is TransformTreatment.PRESERVE_PDF_PAGES:
            reader = PdfReader(source.source_path)
        elif source.treatment is TransformTreatment.RASTERIZE_IMAGE:
            reader = PdfReader(BytesIO(_image_as_pdf(source.source_path, budget)))
        else:
            document = records[source.document_id]
            reader = PdfReader(
                BytesIO(_text_as_pdf(source.relative_path, document.text, budget))
            )
        budget.consume_pdf_pages(len(reader.pages))
        for page in reader.pages:
            writer.add_page(page)
    buffer = BoundedBytesIO(
        budget.policy.max_output_bytes,
        budget_name="Einzelausgabe-Budget",
    )
    writer.write(buffer)
    payload = buffer.getvalue()
    budget.consume_output(len(payload))
    return payload, len(writer.pages)


def _image_as_pdf(path: Path, budget: ResourceBudget) -> bytes:
    try:
        from PIL import Image, ImageSequence
    except ImportError as exc:
        raise DocumentTransformCapabilityError(
            "Bild-PDF-Bündel benötigen die optionale Abhängigkeit Pillow."
        ) from exc
    buffer = BoundedBytesIO(
        budget.policy.max_output_bytes,
        budget_name="Bild-Zwischenausgabe-Budget",
    )
    with Image.open(path) as image:
        frames = []
        for frame in ImageSequence.Iterator(image):
            width, height = frame.size
            budget.consume_image(frames=1, decoded_pixels=width * height)
            frames.append(frame.convert("RGB"))
        if not frames:
            raise DocumentTransformCapabilityError("Bild enthält keine renderbare Seite.")
        first, *rest = frames
        first.save(buffer, format="PDF", save_all=True, append_images=rest)
    return buffer.getvalue()


def _text_as_pdf(title: str, text: str, budget: ResourceBudget) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise DocumentTransformCapabilityError(
            "Text-PDF-Bündel benötigen die optionale Abhängigkeit reportlab."
        ) from exc
    buffer = BoundedBytesIO(
        budget.policy.max_output_bytes,
        budget_name="Text-PDF-Zwischenausgabe-Budget",
    )
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1, invariant=1)
    _, height = A4
    margin = 56
    y = height - margin

    def draw_line(line: str, *, bold: bool = False) -> None:
        nonlocal y
        if y < margin:
            pdf.showPage()
            y = height - margin
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 12 if bold else 10)
        pdf.drawString(margin, y, line)
        y -= 18 if bold else 14

    draw_line(title, bold=True)
    y -= 8
    normalized = text.strip() or "[Kein extrahierter Text]"
    for paragraph in normalized.splitlines() or [normalized]:
        lines = textwrap.wrap(paragraph, width=92) or [""]
        for line in lines:
            draw_line(line)
        y -= 5
    pdf.save()
    return buffer.getvalue()
