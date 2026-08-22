from __future__ import annotations

import json
import zipfile
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.document_package import (
    DocumentPackageError,
    prepare_folder_package,
    write_folder_package,
)
from folderhome.capabilities.resource_budget import DEFAULT_RESOURCE_POLICY
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class StubExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        text = source_path.read_text(encoding="utf-8")
        source_hash = _sha(source_path)
        return DocumentRecord(
            document_id=build_document_id(source_path, source_hash),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=source_hash,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-08-21T12:00:00Z",
            text=text,
            content_format=ContentFormat.TEXT,
            extraction_provider="stub-doc-services",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetisch und freigegeben.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _fixture(root: Path) -> tuple[Path, ...]:
    pypdf = pytest.importorskip("pypdf")
    image_module = pytest.importorskip("PIL.Image")
    nested = root / "Unterordner"
    nested.mkdir(parents=True)
    text_a = root / "A.txt"
    text_b = nested / "B.txt"
    markdown = root / "Notiz.md"
    pdf = root / "Anlage.pdf"
    image = nested / "Scan.png"
    unknown = root / "Rohdaten.bin"
    text_a.write_text("Äpfel und Öl.", encoding="utf-8")
    text_b.write_text("Zweiter Text.", encoding="utf-8")
    markdown.write_text("# Synthetische Notiz", encoding="utf-8")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=300)
    with pdf.open("wb") as handle:
        writer.write(handle)
    image_module.new("RGB", (60, 40), color=(40, 100, 160)).save(image)
    unknown.write_bytes(b"\x00\x01synthetic")
    return text_a, text_b, markdown, pdf, image, unknown


def test_package_plan_groups_types_and_keeps_unknown_sources_visible(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    sources = _fixture(source_root)
    output = tmp_path / "Ausgabe" / "Dokumentpaket.zip"
    before = {path: path.read_bytes() for path in sources}

    prepared = prepare_folder_package(
        source_root,
        output_zip=output,
        extractor=StubExtractor(),
    )

    assert [group.group_id for group in prepared.plan.groups] == [
        "images",
        "markdown",
        "pdf",
        "txt",
    ]
    assert [group.output_filename for group in prepared.plan.groups] == [
        "Bilder.pdf",
        "Markdown.txt",
        "PDFs.pdf",
        "TXT.txt",
    ]
    txt_group = prepared.plan.groups[-1]
    assert [source.relative_path for source in txt_group.sources] == [
        "A.txt",
        "Unterordner/B.txt",
    ]
    assert len(prepared.plan.unsupported) == 1
    assert prepared.plan.unsupported[0].relative_path == "Rohdaten.bin"
    assert prepared.plan.unsupported[0].source_sha256 == _sha(sources[-1])
    assert prepared.plan.gate.granted is False
    assert not output.parent.exists()
    assert {path: path.read_bytes() for path in before} == before
    serialized = prepared.plan.to_dict()
    assert serialized["schema"] == "folderhome.document-package-plan.v1"
    assert "text" not in serialized
    assert all(
        "text" not in source
        for group in serialized["groups"]
        for source in group["sources"]
    )


def test_package_write_requires_gate_and_publishes_one_atomic_zip(tmp_path: Path) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    sources = _fixture(source_root)
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Dokumentpaket.zip"
    before = {path: path.read_bytes() for path in sources}
    prepared = prepare_folder_package(
        source_root,
        output_zip=output,
        extractor=StubExtractor(),
    )

    with pytest.raises(DocumentPackageError, match="Schreibfreigabe"):
        write_folder_package(prepared, allow_output_write=False)

    result = write_folder_package(prepared, allow_output_write=True)

    assert output.is_file()
    assert result.output_sha256 == _sha(output)
    assert result.output_size_bytes == output.stat().st_size
    assert [entry.filename for entry in result.entries] == [
        "Bilder.pdf",
        "Markdown.txt",
        "PDFs.pdf",
        "TXT.txt",
    ]
    with zipfile.ZipFile(output) as package:
        assert package.namelist() == [
            "Bilder.pdf",
            "Markdown.txt",
            "PDFs.pdf",
            "TXT.txt",
            "manifest.json",
        ]
        manifest = json.loads(package.read("manifest.json").decode("utf-8"))
        assert manifest["schema"] == "folderhome.document-package-manifest.v1"
        assert manifest["unsupported"][0]["relative_path"] == "Rohdaten.bin"
        assert [entry["filename"] for entry in manifest["entries"]] == [
            "Bilder.pdf",
            "Markdown.txt",
            "PDFs.pdf",
            "TXT.txt",
        ]
        assert "Äpfel und Öl." in package.read("TXT.txt").decode("utf-8")
    assert {path: path.read_bytes() for path in before} == before
    assert [path.name for path in output_dir.iterdir()] == ["Dokumentpaket.zip"]
    with pytest.raises(DocumentPackageError, match="existiert bereits"):
        write_folder_package(prepared, allow_output_write=True)


def test_package_zip_is_byte_deterministic_for_same_plan(tmp_path: Path) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    source = source_root / "A.txt"
    source.write_text("Deterministischer Inhalt.", encoding="utf-8")
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Dokumentpaket.zip"
    prepared = prepare_folder_package(
        source_root,
        output_zip=output,
        extractor=StubExtractor(),
    )

    first = write_folder_package(prepared, allow_output_write=True)
    first_bytes = output.read_bytes()
    output.unlink()
    second = write_folder_package(prepared, allow_output_write=True)

    assert first.output_sha256 == second.output_sha256
    assert first_bytes == output.read_bytes()


def test_changed_unsupported_source_blocks_package_manifest(tmp_path: Path) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    supported = source_root / "A.txt"
    unsupported = source_root / "Rohdaten.bin"
    supported.write_text("Synthetischer Inhalt.", encoding="utf-8")
    unsupported.write_bytes(b"before")
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output = output_dir / "Dokumentpaket.zip"
    prepared = prepare_folder_package(
        source_root,
        output_zip=output,
        extractor=StubExtractor(),
    )
    unsupported.write_bytes(b"after")

    with pytest.raises(DocumentPackageError, match="seit der Planung geändert"):
        write_folder_package(prepared, allow_output_write=True)

    assert not output.exists()


def test_package_budget_blocks_before_extraction_or_output(tmp_path: Path) -> None:
    class UnusedExtractor:
        def extract(self, source_path: Path) -> DocumentRecord:
            raise AssertionError(f"Extractor darf nicht aufgerufen werden: {source_path}")

    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    (source_root / "A.txt").write_text("A", encoding="utf-8")
    (source_root / "B.txt").write_text("B", encoding="utf-8")
    output = tmp_path / "Ausgabe" / "Dokumentpaket.zip"
    policy = replace(DEFAULT_RESOURCE_POLICY, max_files=1)

    with pytest.raises(DocumentPackageError, match="Dateianzahl-Budget"):
        prepare_folder_package(
            source_root,
            output_zip=output,
            extractor=UnusedExtractor(),
            resource_policy=policy,
        )

    assert not output.exists()
