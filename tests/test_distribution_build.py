"""Exercise the real build backend on a small, isolated source tree."""

import tarfile
import zipfile
from pathlib import Path

import pytest
from hatchling.builders.sdist import SdistBuilder
from hatchling.builders.wheel import WheelBuilder

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("with_gitignore", [False, True])
def test_distributions_exclude_coordination_locks_without_losing_manifests(
    tmp_path: Path, with_gitignore: bool,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (project / "README.md").write_text("Synthetic packaging fixture\n", encoding="utf-8")
    if with_gitignore:
        (project / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
    package = project / "src" / "folderhome"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    manifests = project / "manifests" / "components"
    manifests.mkdir(parents=True)
    for source in (ROOT / "manifests" / "components").glob("*.toml"):
        (manifests / source.name).write_bytes(source.read_bytes())
    expected_manifests = {p.name for p in manifests.glob("*.toml")}
    assert expected_manifests, "exercise actual component manifests, not an empty fixture"

    # Git's machine-local info/exclude is not a distributable build policy.
    for directory in (project, package, project / "docs", manifests):
        directory.mkdir(exist_ok=True)
        for name in ("LOCK.txt", "LOCK.team.test.txt", "LOCK.user.test.txt",
                     "LOCK.until.test.txt", "LOCK.condition.test.txt", "LOCK.permissions.json"):
            (directory / name).write_text("PRIVATE-COORDINATION-CANARY", encoding="utf-8")

    output = tmp_path / "dist"
    output.mkdir()
    sdist = Path(next(SdistBuilder(str(project)).build(directory=str(output))))
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        assert not [m.name for m in members if Path(m.name).name.startswith("LOCK")]
        assert expected_manifests <= {Path(m.name).name for m in members}
        assert any(m.name.endswith("src/folderhome/__init__.py") for m in members)
    wheel = Path(next(WheelBuilder(str(project)).build(directory=str(output))))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert not [name for name in names if Path(name).name.startswith("LOCK")]
        assert expected_manifests == {
            Path(name).name for name in names if name.startswith("folderhome/component_manifests/")
        }
        assert "folderhome/__init__.py" in names
