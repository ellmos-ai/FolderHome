"""Exercise the real diagram export CLI, without browser or network access."""

import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("name", ["ARCHITECTURE_DIAGRAM", "PRODUCT_ARCHITECTURE"])
def test_committed_diagram_has_accessible_source_and_matching_png_dimensions(name: str) -> None:
    directory = ROOT / "docs" / "submission"
    source = ET.fromstring((directory / f"{name}.svg").read_bytes())
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    assert source.find("svg:title", namespace) is not None
    assert source.find("svg:desc", namespace) is not None
    assert source.attrib["role"] == "img"
    labelled_ids = source.attrib["aria-labelledby"].split()
    elements = {node.attrib["id"]: node for node in source.iter() if "id" in node.attrib}
    assert labelled_ids and all(elements[key].text.strip() for key in labelled_ids)
    # Exports must be self-contained; remote images/fonts/scripts cannot be required.
    for node in source.iter():
        assert node.tag.rsplit("}", 1)[-1] not in {"script", "image", "foreignObject"}
        for key, value in node.attrib.items():
            if key.rsplit("}", 1)[-1] == "href":
                assert value.startswith("#")
    png = (directory / f"{name}.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (
        int(source.attrib["width"]),
        int(source.attrib["height"]),
    )


def test_diagram_export_renders_dimensions_and_detects_stale_png(tmp_path: Path) -> None:
    source = tmp_path / "source.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="32">'
        '<rect width="64" height="32" fill="#112233"/></svg>',
        encoding="utf-8",
    )
    output = tmp_path / "export.png"
    command = [
        sys.executable,
        str(ROOT / "deploy" / "render_architecture.py"),
        "--source",
        str(source),
        "--output",
        str(output),
        "--no-system-fonts",
    ]
    result = subprocess.run(command, capture_output=True, text=True, env=os.environ, timeout=30)
    assert result.returncode == 0, result.stderr
    data = output.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (64, 32)
    check = subprocess.run(command + ["--check"], capture_output=True, text=True, timeout=30)
    assert check.returncode == 0, check.stderr
    output.write_bytes(b"stale export")
    stale = subprocess.run(command + ["--check"], capture_output=True, text=True, timeout=30)
    assert stale.returncode == 1
    assert output.read_bytes() == b"stale export", "check must not repair the file"
    assert source.read_text(encoding="utf-8").endswith("</svg>")
