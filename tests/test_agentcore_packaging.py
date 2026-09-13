"""Offline household packaging checks; no uv, Docker or network required."""

import shutil
import zipfile
from pathlib import Path

import pytest
from hatchling.builders.wheel import WheelBuilder

from deploy.agentcore import build_direct_code

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = "folderhome/demo_data/household"


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


def test_direct_code_household_copy_matches_all_examples(tmp_path: Path) -> None:
    destination = build_direct_code.copy_household_examples(ROOT, tmp_path)

    assert destination == tmp_path / PACKAGE_PATH
    expected = _files(ROOT / "examples")
    assert len(expected) == 104
    assert _files(destination) == expected


def test_direct_code_household_copy_excludes_caches_and_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    examples = repository / "examples"
    nested = examples / "nested"
    nested.mkdir(parents=True)
    (nested / "document.txt").write_bytes(b"\x00\xffhousehold\r\n")
    cache = nested / "__pycache__"
    cache.mkdir()
    (cache / "cache.txt").write_bytes(b"excluded")
    (nested / "module.pyc").write_bytes(b"excluded")
    linked_file = examples / "linked-file"
    linked_file.write_bytes(b"must not be packaged")
    linked_directory = examples / "linked-directory"
    linked_directory.mkdir()
    (linked_directory / "secret.txt").write_bytes(b"must not be traversed")
    # Mock link detection so the exclusion branch runs on Windows without
    # symlink privileges as well. The directory must be pruned before traversal.
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path in {linked_file, linked_directory} or original_is_symlink(path),
    )

    destination = build_direct_code.copy_household_examples(repository, tmp_path / "package")

    assert _files(destination) == {"nested/document.txt": b"\x00\xffhousehold\r\n"}
    assert {p.relative_to(destination).as_posix() for p in destination.rglob("*")} == {
        "nested", "nested/document.txt",
    }


@pytest.mark.parametrize("linked_root", [False, True])
def test_direct_code_household_copy_requires_real_examples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, linked_root: bool,
) -> None:
    if linked_root:
        examples = tmp_path / "examples"
        examples.mkdir()
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == examples)
    with pytest.raises(ValueError, match="real household examples directory"):
        build_direct_code.copy_household_examples(tmp_path, tmp_path / "package")
    assert not (tmp_path / "package").exists()


def test_direct_code_zip_contains_household_after_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = tmp_path / "deploy" / "agentcore" / "build_direct_code.py"
    script.parent.mkdir(parents=True)
    (script.parent / "agentcore_entrypoint.py").write_text("# fixture\n", encoding="utf-8")
    shutil.copytree(ROOT / "examples", tmp_path / "examples")
    monkeypatch.setattr(build_direct_code, "__file__", str(script))
    commands = []

    def fake_uv(command, *, cwd, check):
        assert cwd == tmp_path and check is True
        commands.append(command[:3])
        if command[:2] == ["uv", "build"]:
            wheel_root = Path(command[command.index("--out-dir") + 1])
            (wheel_root / "folderhome-fixture.whl").write_bytes(b"fixture")
        else:
            assert command[:3] == ["uv", "pip", "install"]
            target = Path(command[command.index("--target") + 1])
            assert not (target / PACKAGE_PATH).exists()
            (target / "folderhome").mkdir()

    monkeypatch.setattr(build_direct_code.subprocess, "run", fake_uv)

    assert build_direct_code.main([]) == 0
    assert commands == [["uv", "build", "--wheel"], ["uv", "pip", "install"]]
    with zipfile.ZipFile(tmp_path / "build" / "agentcore-direct.zip") as archive:
        prefix = PACKAGE_PATH + "/"
        packaged = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist() if name.startswith(prefix)
        }
    assert len(packaged) == 104
    assert packaged == _files(ROOT / "examples")


def test_docker_household_staging_survives_real_wheel_build(tmp_path: Path) -> None:
    dockerfile = (ROOT / "deploy" / "agentcore" / "Dockerfile").read_text(encoding="utf-8")
    copy = "COPY examples ./src/folderhome/demo_data/household"
    assert dockerfile.index("COPY src ./src") < dockerfile.index(copy)
    assert dockerfile.index(copy) < dockerfile.index("RUN pip install")
    # Reproduce the Docker COPY steps, then use the installed backend offline.
    project = tmp_path / "project"
    project.mkdir()
    for name in ("pyproject.toml", "README.md"):
        shutil.copy2(ROOT / name, project / name)
    shutil.copytree(ROOT / "src", project / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "examples", project / "src" / PACKAGE_PATH)
    output = tmp_path / "dist"
    output.mkdir()
    wheel = Path(next(WheelBuilder(str(project)).build(directory=str(output))))
    with zipfile.ZipFile(wheel) as archive:
        prefix = PACKAGE_PATH + "/"
        packaged = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist() if name.startswith(prefix)
        }
    assert len(packaged) == 104
    assert packaged == _files(ROOT / "examples")
