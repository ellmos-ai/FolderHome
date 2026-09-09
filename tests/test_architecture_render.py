"""Exercise the real diagram export CLI, without browser or network access."""

import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


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
