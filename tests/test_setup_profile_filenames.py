"""Profile ids come from the documents; file names may differ in letter case.

Live finding 2026-09-13: the installed configuration carried the shipped example files
``Hanna.json``/``Lukas.json``/``Simon.json`` (documents say ``hanna``/``lukas``/``simon``).
The save path derived ids from the stems and failed with "Unzulässige Profil-ID: Hanna".
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from folderhome.setup_app import _existing_profile_ids, _profile_path

EXAMPLE_PROFILES = Path(__file__).parents[1] / "examples" / "profiles"


def _installed_layout(tmp_path: Path) -> Path:
    directory = tmp_path / "profiles"
    directory.mkdir()
    for name in ("Hanna.json", "Lukas.json", "Simon.json", "household.json"):
        shutil.copy2(EXAMPLE_PROFILES / name, directory / name)
    return directory


def test_shipped_examples_use_capitalised_file_names_with_lowercase_ids() -> None:
    hanna = json.loads((EXAMPLE_PROFILES / "Hanna.json").read_text(encoding="utf-8"))
    assert hanna["profile_id"] == "hanna"


def test_existing_profile_ids_are_read_from_the_documents(tmp_path: Path) -> None:
    directory = _installed_layout(tmp_path)
    assert _existing_profile_ids(directory) == ["hanna", "lukas", "simon"]


def test_existing_profile_ids_fall_back_to_the_lowercased_stem(tmp_path: Path) -> None:
    directory = tmp_path / "profiles"
    directory.mkdir()
    (directory / "Gast.json").write_text("{}", encoding="utf-8")
    (directory / "broken.json").write_text("not json", encoding="utf-8")
    (directory / "household.json").write_text("{}", encoding="utf-8")
    assert _existing_profile_ids(directory) == ["broken", "gast"]


def test_profile_path_reuses_an_existing_file_in_any_letter_case(tmp_path: Path) -> None:
    directory = _installed_layout(tmp_path)
    assert _profile_path(directory, "hanna").name == "Hanna.json"
    # A brand-new profile gets the canonical lowercase file name.
    assert _profile_path(directory, "neu").name == "neu.json"
    # No directory yet: canonical path, nothing created.
    assert _profile_path(tmp_path / "missing", "hanna") == tmp_path / "missing" / "hanna.json"
