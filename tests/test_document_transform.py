from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.document_transform import (
    DocumentTransformError,
    plan_document_bundle,
    write_document_bundle,
)
from folderhome.capabilities.resource_budget import DEFAULT_RESOURCE_POLICY
from folderhome.contracts import (
    BundleFormat,
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    TransformTreatment,
    build_document_id,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _record(
    source: Path,
    *,
    text: str,
    media_type: str = "text/plain",
    privacy_status: PrivacyStatus = PrivacyStatus.CLEAR,
) -> DocumentRecord:
    source_hash = _sha(source)
    return DocumentRecord(
        document_id=build_document_id(source, source_hash),
        source_path=source,
        filename=source.name,
        media_type=media_type,
        source_sha256=source_hash,
        size_bytes=source.stat().st_size,
        modified_at="2026-08-21T12:00:00Z",
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="doc-services",
        extraction_method="direct",
        privacy_status=privacy_status,
        privacy_summary="Synthetischer Datenschutzstatus.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )


def test_text_bundle_plan_is_deterministic_private_and_read_only(tmp_path: Path) -> None:
    source_root = tmp_path / "Dokumente"
    nested = source_root / "Unterordner"
    nested.mkdir(parents=True)
    first = source_root / "B.txt"
    second = nested / "A.md"
    first.write_text("Zweiter Inhalt.", encoding="utf-8")
    second.write_text("Erster Inhalt.", encoding="utf-8")
    records = (
        _record(first, text="Zweiter Inhalt."),
        _record(second, text="Erster Inhalt.", media_type="text/markdown"),
    )
    output = tmp_path / "Ausgabe" / "Sammlung.txt"
    before = {path: path.read_bytes() for path in (first, second)}

    plan = plan_document_bundle(
        records,
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.TXT,
    )

    assert [source.relative_path for source in plan.sources] == [
        "B.txt",
        "Unterordner/A.md",
    ]
    assert all(
        source.treatment is TransformTreatment.EXTRACTED_TEXT
        for source in plan.sources
    )
    assert all(source.lossy is True for source in plan.sources)
    assert plan.gate.required is True
    assert plan.gate.granted is False
    assert plan.output_path == output.resolve()
    assert not output.parent.exists()
    assert {path: path.read_bytes() for path in before} == before
    serialized = plan.to_dict()
    assert serialized["schema"] == "folderhome.document-bundle-plan.v1"
    assert "text" not in serialized
    assert all("text" not in source for source in serialized["sources"])
    assert all("source_sha256" in source for source in serialized["sources"])


def test_text_bundle_requires_gate_and_publishes_new_file_atomically(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    first = source_root / "A.txt"
    second = source_root / "B.txt"
    first.write_text("Äpfel und Öl.", encoding="utf-8")
    second.write_text("Zweiter Inhalt.", encoding="utf-8")
    records = (
        _record(first, text="Äpfel und Öl."),
        _record(second, text="Zweiter Inhalt."),
    )
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Sammlung.txt"
    plan = plan_document_bundle(
        records,
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.TXT,
    )

    with pytest.raises(DocumentTransformError, match="Schreibfreigabe"):
        write_document_bundle(plan, records, allow_output_write=False)

    result = write_document_bundle(plan, records, allow_output_write=True)

    content = output.read_text(encoding="utf-8")
    assert content == (
        "# FolderHome-Dokumentbündel\n\n"
        "## A.txt\n\nÄpfel und Öl.\n\n"
        "## B.txt\n\nZweiter Inhalt.\n"
    )
    assert result.output_sha256 == _sha(output)
    assert result.output_size_bytes == output.stat().st_size
    assert result.page_count is None
    assert result.source_document_ids == tuple(
        source.document_id for source in plan.sources
    )
    assert first.exists() and second.exists()
    with pytest.raises(DocumentTransformError, match="existiert bereits"):
        write_document_bundle(plan, records, allow_output_write=True)


def test_changed_source_blocks_bundle_before_output_write(tmp_path: Path) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    source = source_root / "A.txt"
    source.write_text("Ursprünglich.", encoding="utf-8")
    record = _record(source, text="Ursprünglich.")
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Sammlung.txt"
    plan = plan_document_bundle(
        (record,),
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.TXT,
    )
    source.write_text("Nachträglich geändert.", encoding="utf-8")

    with pytest.raises(DocumentTransformError, match="seit der Planung geändert"):
        write_document_bundle(plan, (record,), allow_output_write=True)

    assert not output.exists()


def test_pdf_bundle_preserves_pdf_pages_and_marks_reflowed_text_loss(
    tmp_path: Path,
) -> None:
    pypdf = pytest.importorskip("pypdf")
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    pdf_source = source_root / "Anlage.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=300)
    with pdf_source.open("wb") as handle:
        writer.write(handle)
    text_source = source_root / "Notiz.txt"
    text_source.write_text("Synthetische Notiz mit Umlaut: Öl.", encoding="utf-8")
    records = (
        _record(pdf_source, text="", media_type="application/pdf"),
        _record(text_source, text="Synthetische Notiz mit Umlaut: Öl."),
    )
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Sammlung.pdf"

    plan = plan_document_bundle(
        records,
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.PDF,
    )
    result = write_document_bundle(plan, records, allow_output_write=True)

    treatments = {source.relative_path: source.treatment for source in plan.sources}
    assert treatments == {
        "Anlage.pdf": TransformTreatment.PRESERVE_PDF_PAGES,
        "Notiz.txt": TransformTreatment.REFLOW_TEXT,
    }
    assert plan.sources[0].lossy is False
    assert plan.sources[1].lossy is True
    assert result.page_count == 2
    rendered = pypdf.PdfReader(output)
    assert len(rendered.pages) == 2
    assert "Öl" in "\n".join(page.extract_text() or "" for page in rendered.pages)
    assert pdf_source.exists() and text_source.exists()


def test_privacy_status_blocks_content_bundle(tmp_path: Path) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    source = source_root / "A.txt"
    source.write_text("Synthetisch sensibel.", encoding="utf-8")
    record = _record(
        source,
        text="Synthetisch sensibel.",
        privacy_status=PrivacyStatus.REVIEW_REQUIRED,
    )

    with pytest.raises(DocumentTransformError, match="Datenschutzstatus"):
        plan_document_bundle(
            (record,),
            source_root=source_root,
            output_path=tmp_path / "Ausgabe.txt",
            output_format=BundleFormat.TXT,
        )


def test_image_is_bundled_as_rasterized_pdf_page_without_source_change(
    tmp_path: Path,
) -> None:
    image_module = pytest.importorskip("PIL.Image")
    pypdf = pytest.importorskip("pypdf")
    source_root = tmp_path / "Bilder"
    source_root.mkdir()
    source = source_root / "Scan.png"
    image_module.new("RGB", (80, 60), color=(20, 80, 140)).save(source)
    record = _record(
        source,
        text="",
        media_type="image/png",
        privacy_status=PrivacyStatus.NOT_CHECKED,
    )
    before = source.read_bytes()
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Bilder.pdf"

    plan = plan_document_bundle(
        (record,),
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.PDF,
    )
    result = write_document_bundle(plan, (record,), allow_output_write=True)

    assert plan.sources[0].treatment is TransformTreatment.RASTERIZE_IMAGE
    assert plan.sources[0].lossy is True
    assert plan.sources[0].privacy_status is PrivacyStatus.NOT_CHECKED
    assert result.page_count == 1
    assert len(pypdf.PdfReader(output).pages) == 1
    assert source.read_bytes() == before


def test_reflowed_pdf_output_is_byte_deterministic(tmp_path: Path) -> None:
    pytest.importorskip("pypdf")
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    source = source_root / "Notiz.txt"
    source.write_text("Deterministischer Inhalt mit Öl.", encoding="utf-8")
    record = _record(source, text="Deterministischer Inhalt mit Öl.")
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    first_output = output_dir / "Erster-Lauf.pdf"
    second_output = output_dir / "Zweiter-Lauf.pdf"
    first_plan = plan_document_bundle(
        (record,),
        source_root=source_root,
        output_path=first_output,
        output_format=BundleFormat.PDF,
    )
    second_plan = plan_document_bundle(
        (record,),
        source_root=source_root,
        output_path=second_output,
        output_format=BundleFormat.PDF,
    )

    first_result = write_document_bundle(
        first_plan,
        (record,),
        allow_output_write=True,
    )
    second_result = write_document_bundle(
        second_plan,
        (record,),
        allow_output_write=True,
    )

    assert first_result.output_sha256 == second_result.output_sha256
    assert first_output.read_bytes() == second_output.read_bytes()


def test_text_bundle_resource_budget_blocks_before_output_publication(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    source = source_root / "A.txt"
    source.write_text("Langer synthetischer Inhalt.", encoding="utf-8")
    record = _record(source, text="Langer synthetischer Inhalt.")
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Sammlung.txt"
    plan = plan_document_bundle(
        (record,),
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.TXT,
    )
    policy = replace(DEFAULT_RESOURCE_POLICY, max_extracted_text_chars=8)

    with pytest.raises(DocumentTransformError, match="Textzeichen-Budget"):
        write_document_bundle(
            plan,
            (record,),
            allow_output_write=True,
            resource_policy=policy,
        )

    assert not output.exists()


def test_pdf_page_budget_blocks_before_output_publication(tmp_path: Path) -> None:
    pypdf = pytest.importorskip("pypdf")
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    source = source_root / "Anlage.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.add_blank_page(width=200, height=300)
    with source.open("wb") as handle:
        writer.write(handle)
    record = _record(source, text="", media_type="application/pdf")
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Sammlung.pdf"
    plan = plan_document_bundle(
        (record,),
        source_root=source_root,
        output_path=output,
        output_format=BundleFormat.PDF,
    )
    policy = replace(DEFAULT_RESOURCE_POLICY, max_pdf_pages=1)

    with pytest.raises(DocumentTransformError, match="PDF-Seiten-Budget"):
        write_document_bundle(
            plan,
            (record,),
            allow_output_write=True,
            resource_policy=policy,
        )

    assert not output.exists()
