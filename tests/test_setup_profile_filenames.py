"""Profile ids come from the documents; file names may differ in letter case.

Live finding 2026-09-13: the installed configuration carried the shipped example files
``Hanna.json``/``Lukas.json``/``Simon.json`` (documents say ``hanna``/``lukas``/``simon``).
The save path derived ids from the stems and failed with "Unzulässige Profil-ID: Hanna".
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

from folderhome.setup_app import _existing_profile_ids, _profile_path

EXAMPLE_PROFILES = Path(__file__).parents[1] / "examples" / "profiles"
EXAMPLE_FILES = ("Hanna.json", "Lukas.json", "Simon.json", "household.json")


def _installed_layout(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name in EXAMPLE_FILES:
        shutil.copy2(EXAMPLE_PROFILES / name, directory / name)
    return directory


def _setup_helpers():
    """Reuse the request/post helpers of the main setup test module (tests is not a package)."""

    spec = importlib.util.spec_from_file_location(
        "setup_app_test_helpers", Path(__file__).with_name("test_setup_app.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_shipped_examples_use_capitalised_file_names_with_lowercase_ids() -> None:
    hanna = json.loads((EXAMPLE_PROFILES / "Hanna.json").read_text(encoding="utf-8"))
    assert hanna["profile_id"] == "hanna"


def test_existing_profile_ids_are_read_from_the_documents(tmp_path: Path) -> None:
    directory = _installed_layout(tmp_path / "profiles")
    assert _existing_profile_ids(directory) == ["hanna", "lukas", "simon"]


def test_existing_profile_ids_fall_back_to_the_lowercased_stem(tmp_path: Path) -> None:
    directory = tmp_path / "profiles"
    directory.mkdir()
    (directory / "Gast.json").write_text("{}", encoding="utf-8")
    (directory / "broken.json").write_text("not json", encoding="utf-8")
    (directory / "household.json").write_text("{}", encoding="utf-8")
    assert _existing_profile_ids(directory) == ["broken", "gast"]


def test_profile_path_reuses_an_existing_file_in_any_letter_case(tmp_path: Path) -> None:
    directory = _installed_layout(tmp_path / "profiles")
    assert _profile_path(directory, "hanna").name == "Hanna.json"
    # A brand-new profile gets the canonical lowercase file name.
    assert _profile_path(directory, "neu").name == "neu.json"
    # No directory yet: canonical path, nothing created.
    assert _profile_path(tmp_path / "missing", "hanna") == tmp_path / "missing" / "hanna.json"


def test_installed_layout_validates_and_saves_through_the_setup_api(tmp_path: Path) -> None:
    """The user's configuration: example files with capitalised names in the profiles dir."""

    helpers = _setup_helpers()
    config_dir = tmp_path / "config"
    profiles_dir = _installed_layout(config_dir / "profiles")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    # Same construction as the main test helper, but the profiles directory is the
    # installed copy with the capitalised example file names, not the repository.
    app = helpers.SetupApplication(
        settings=helpers.LocalAppSettings(
            host="127.0.0.1", port=0, profiles_dir=profiles_dir, state_dir=state_dir
        ),
        profiles=helpers.load_profile_configuration(profiles_dir),
        config_dir=config_dir,
        session_token=helpers.TOKEN,
    )
    assert app.profiles_dir == profiles_dir
    request = helpers._request(tmp_path)

    planned = helpers._post(app, "/api/v1/setup/validate", request)
    assert planned.payload["valid"] is True, planned.payload["errors"]

    saved = helpers._post(
        app,
        "/api/v1/setup/save",
        {**request, "confirm": True, "plan_sha256": planned.payload["plan_sha256"]},
    )
    assert saved.status_code == 200, saved.payload

    remaining = sorted(
        path.name.casefold()
        for path in app.profiles_dir.glob("*.json")
        if path.name.casefold() != "household.json"
    )
    # Profiles the plan keeps are written to their existing file, retired ones move to
    # the dated attic; no second lowercase copy appears next to a capitalised file.
    assert len(remaining) == len(set(remaining))
    attic = [path for path in app.profiles_dir.iterdir() if path.name.startswith(".deleted-")]
    assert "hanna.json" in remaining or attic, (remaining, attic)
