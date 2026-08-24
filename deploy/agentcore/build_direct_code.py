"""Build a reproducible Linux ARM64 AgentCore direct-code ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

_FILE_MODE = 0o100644 << 16


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/agentcore-direct.zip"))
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    output = (
        (repository / args.output).resolve()
        if not args.output.is_absolute()
        else args.output.resolve()
    )
    build_root = (repository / "build" / "agentcore-direct-package").resolve()
    wheel_root = (repository / "build" / "agentcore-direct-wheel").resolve()
    _require_inside(repository, output)
    _require_inside(repository, build_root)
    _require_inside(repository, wheel_root)
    if build_root.exists():
        shutil.rmtree(build_root)
    if wheel_root.exists():
        shutil.rmtree(wheel_root)
    build_root.mkdir(parents=True)
    wheel_root.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_root)],
        cwd=repository,
        check=True,
    )
    wheels = tuple(wheel_root.glob("folderhome-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one FolderHome wheel.")
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python-platform",
            "aarch64-manylinux2014",
            "--python-version",
            "3.12",
            "--target",
            str(build_root),
            "--only-binary=:all:",
            str(wheels[0]),
        ],
        cwd=repository,
        check=True,
    )
    shutil.copy2(Path(__file__).with_name("agentcore_entrypoint.py"), build_root)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(build_root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = path.relative_to(build_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 23, 0, 0, 0))
            info.create_system = 3
            info.external_attr = _FILE_MODE
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    payload = output.read_bytes()
    print(
        json.dumps(
            {
                "schema": "folderhome.agentcore-direct-code-build.v1",
                "path": str(output),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "python_runtime": "PYTHON_3_12",
                "platform": "aarch64-manylinux2014",
                "entry_point": ["agentcore_entrypoint.py"],
            },
            sort_keys=True,
        )
    )
    return 0


def _require_inside(repository: Path, target: Path) -> None:
    try:
        target.relative_to(repository)
    except ValueError as exc:
        raise ValueError("Build output must remain inside the FolderHome repository.") from exc
    if target == repository:
        raise ValueError("Build output may not be the repository root.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
