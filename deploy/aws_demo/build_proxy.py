"""Build a reproducible Linux ARM64 Lambda proxy ZIP for the AWS demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

_BOTO3_VERSION = "1.43.78"
_FILE_MODE = 0o100644 << 16


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/aws-demo-proxy.zip"))
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    output = (
        (repository / args.output).resolve()
        if not args.output.is_absolute()
        else args.output.resolve()
    )
    build_root = (repository / "build" / "aws-demo-proxy-package").resolve()
    _require_inside(repository, output)
    _require_inside(repository, build_root)
    if build_root.exists():
        shutil.rmtree(build_root)
    build_root.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)
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
            f"boto3=={_BOTO3_VERSION}",
        ],
        cwd=repository,
        check=True,
    )
    source_package = repository / "src" / "folderhome"
    destination_package = build_root / "folderhome"
    destination_cloud_demo = destination_package / "cloud_demo"
    destination_cloud_demo.mkdir(parents=True)
    shutil.copy2(source_package / "__init__.py", destination_package / "__init__.py")
    shutil.copy2(
        source_package / "cloud_demo" / "__init__.py",
        destination_cloud_demo / "__init__.py",
    )
    shutil.copy2(
        source_package / "cloud_demo" / "proxy.py",
        destination_cloud_demo / "proxy.py",
    )
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(build_root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = path.relative_to(build_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 24, 0, 0, 0))
            info.create_system = 3
            info.external_attr = _FILE_MODE
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    payload = output.read_bytes()
    print(
        json.dumps(
            {
                "schema": "folderhome.aws-demo-proxy-build.v1",
                "path": str(output),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "python_runtime": "python3.12",
                "platform": "arm64",
                "handler": "folderhome.cloud_demo.proxy.lambda_handler",
                "boto3_version": _BOTO3_VERSION,
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
