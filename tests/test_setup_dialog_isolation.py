"""The OS folder chooser must not import code from documents or inherited paths."""

import subprocess
import sys
from pathlib import Path

import pytest
from test_setup_app import _app, _pick

from folderhome import setup_app


@pytest.fixture(scope="module", autouse=True)
def isolated_toolkit_available():
    probe = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-c", "import tkinter, tkinter.filedialog"],
        capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
    )
    if probe.returncode:
        pytest.skip("Optional tkinter is unavailable in the isolated interpreter")


def _headless_dialog(monkeypatch, chosen):
    # Only replace the graphical interaction, inside the actual child interpreter.
    # Imports, subprocess startup and the production dialog script remain real.
    prologue = (
        "import tkinter, tkinter.filedialog\n"
        "from types import SimpleNamespace\n"
        "tkinter.Tk = lambda: SimpleNamespace(\n"
        "    withdraw=lambda: None, attributes=lambda *args: None, destroy=lambda: None)\n"
        f"tkinter.filedialog.askdirectory = lambda **kwargs: {str(chosen)!r}\n"
    )
    monkeypatch.setattr(setup_app, "_PICK_FOLDER_SCRIPT", prologue + setup_app._PICK_FOLDER_SCRIPT)


@pytest.mark.parametrize("source", ["cwd", "pythonpath"])
def test_folder_dialog_does_not_execute_shadow_toolkit(tmp_path: Path, monkeypatch, source):
    app = _app(tmp_path)
    chosen = tmp_path / "selected"
    chosen.mkdir()
    shadow = tmp_path / "untrusted-documents"
    shadow.mkdir()
    marker = tmp_path / "unexpected-import.txt"
    (shadow / "tkinter.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        "raise RuntimeError('untrusted toolkit executed')\n",
        encoding="utf-8",
    )
    if source == "cwd":
        monkeypatch.chdir(shadow)
    else:
        monkeypatch.setenv("PYTHONPATH", str(shadow))
    _headless_dialog(monkeypatch, chosen)

    response = _pick(app)

    assert not marker.exists(), "An unrelated document directory supplied executable dialog code"
    assert response.status_code == 200, response.payload
    assert response.payload["path"] == str(chosen)
    assert not app._dialog_lock.locked()


def test_folder_dialog_returns_unicode_even_with_inherited_legacy_output_encoding(
    tmp_path: Path, monkeypatch,
):
    app = _app(tmp_path)
    chosen = tmp_path / "Prüfung äöü"
    chosen.mkdir()
    _headless_dialog(monkeypatch, chosen)
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")

    response = _pick(app)

    assert response.status_code == 200, response.payload
    assert response.payload["path"] == str(chosen)
    assert not app._dialog_lock.locked()
