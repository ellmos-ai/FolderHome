"""The installed setup must offer the same family templates as the checkout."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from hatchling.builders.wheel import WheelBuilder

from folderhome import setup_app

ROOT = Path(__file__).parents[1]
NAMES = ("Hanna", "Lukas", "Simon")


def _expected_templates():
    directory = ROOT / "examples" / "profiles"
    return {
        "household": json.loads((directory / "household.json").read_text(encoding="utf-8")),
        "profiles": {
            name: json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
            for name in NAMES
        },
    }


def test_real_wheel_offers_complete_setup_templates_outside_checkout(tmp_path):
    output = tmp_path / "dist"
    output.mkdir()
    wheel = Path(next(WheelBuilder(str(ROOT)).build(directory=str(output))))
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)
    script = (
        "import sys,json; from pathlib import Path; "
        f"site=Path({str(installed)!r}); sys.path.insert(0,str(site)); "
        "from folderhome import setup_app; "
        "assert Path(setup_app.__file__).is_relative_to(site); "
        "print(json.dumps(setup_app.profile_templates()))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-c", script], cwd=tmp_path,
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == _expected_templates()
    for name in (*NAMES, "household"):
        packaged = installed / "folderhome" / "setup_templates" / "profiles" / f"{name}.json"
        example = ROOT / "examples" / "profiles" / f"{name}.json"
        assert packaged.read_bytes() == example.read_bytes()


def test_setup_does_not_read_legacy_checkout_or_demo_templates(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "household.json").write_text("{}", encoding="utf-8")
    (legacy / "Unexpected.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(setup_app, "_TEMPLATE_DIRECTORIES", (legacy,))

    assert setup_app.profile_templates() == _expected_templates()


def test_setup_family_templates_do_not_expand_the_separate_demo():
    demo = Path(setup_app.__file__).parent / "demo_data" / "profiles"
    assert sorted(path.name for path in demo.glob("*.json")) == ["Lukas.json", "household.json"]


@pytest.mark.parametrize("failure", ["missing", "invalid"])
def test_incomplete_setup_templates_do_not_fall_back_to_a_different_family(
    tmp_path, monkeypatch, failure,
):
    for name in (*NAMES, "household"):
        if failure == "missing" and name == "Simon":
            continue
        payload = (ROOT / "examples" / "profiles" / f"{name}.json").read_bytes()
        if failure == "invalid" and name == "Hanna":
            payload = b"not-json"
        (tmp_path / f"{name}.json").write_bytes(payload)
    monkeypatch.setattr(setup_app, "_SETUP_TEMPLATES_DIRECTORY", tmp_path)

    assert setup_app.profile_templates() == {"household": None, "profiles": {}}
