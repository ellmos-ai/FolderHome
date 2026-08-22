from __future__ import annotations

import json
from pathlib import Path

import pytest

import folderhome
from folderhome.application.competition_demo import (
    _PROFILE_DIR,
    CompetitionDemoError,
    run_competition_demo,
)


def test_competition_demo_profiles_are_part_of_the_installable_package() -> None:
    package_root = Path(folderhome.__file__).resolve().parent

    assert _PROFILE_DIR.is_relative_to(package_root)
    assert (_PROFILE_DIR / "household.json").is_file()
    assert (_PROFILE_DIR / "Lukas.json").is_file()


def test_competition_demo_runs_two_strands_workflows_and_writes_evidence(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "demo"

    report = run_competition_demo(output_dir, allow_output_write=True)

    assert report.status == "passed"
    assert report.framework == "strands-agents"
    assert report.framework_version == "1.53.0"
    assert report.network_used is False
    assert report.side_effects == ()
    assert [item.scenario_id for item in report.scenarios] == [
        "document-search",
        "theme-dossier",
    ]
    assert all(item.status == "passed" for item in report.scenarios)
    assert {path.name for path in output_dir.iterdir()} == {
        "01-document-search.json",
        "02-theme-dossier.json",
        "DEMO.md",
        "EVIDENCE.json",
    }
    evidence = json.loads((output_dir / "EVIDENCE.json").read_text(encoding="utf-8"))
    assert evidence["schema"] == "folderhome.competition-demo-evidence.v1"
    assert evidence["checks"]["strands_agent_loop"] is True
    assert evidence["checks"]["external_network_used"] is False
    assert evidence["checks"]["real_personal_data_used"] is False
    assert all(len(value) == 64 for value in evidence["artifact_sha256"].values())
    markdown = (output_dir / "DEMO.md").read_text(encoding="utf-8")
    assert "Synthetische Wettbewerbsdemo" in markdown
    assert "Krankenversicherung" in markdown
    assert "keine echten personenbezogenen Daten" in markdown


def test_competition_demo_is_deterministic_and_never_overwrites(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run_competition_demo(first, allow_output_write=True)
    run_competition_demo(second, allow_output_write=True)

    for filename in (
        "01-document-search.json",
        "02-theme-dossier.json",
        "DEMO.md",
        "EVIDENCE.json",
    ):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()

    with pytest.raises(CompetitionDemoError, match="existiert bereits"):
        run_competition_demo(first, allow_output_write=True)


def test_competition_demo_requires_explicit_output_gate(tmp_path: Path) -> None:
    output_dir = tmp_path / "blocked"

    with pytest.raises(CompetitionDemoError, match="Ausgabefreigabe"):
        run_competition_demo(output_dir, allow_output_write=False)

    assert not output_dir.exists()
