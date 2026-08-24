"""Prepare an ignored AWS site artifact with one public quota configuration."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

_API_KEY = re.compile(r"[A-Za-z0-9]{20,128}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", type=Path, default=Path("build/aws-demo-site"))
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    output = (
        (repository / args.output).resolve()
        if not args.output.is_absolute()
        else args.output.resolve()
    )
    _require_inside(repository / "build", output)
    api_url = _validated_api_url(args.api_base_url)
    if _API_KEY.fullmatch(args.api_key) is None:
        raise ValueError("API key must be an AWS-generated alphanumeric quota key.")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(repository / "site", output)
    configuration = (
        '"use strict";\n\n'
        "// Generated deployment artifact. The API key is a public quota identifier.\n"
        "window.FOLDERHOME_LIVE_DEMO = Object.freeze({\n"
        "  enabled: true,\n"
        f"  apiBaseUrl: {json.dumps(api_url)},\n"
        f"  apiKey: {json.dumps(args.api_key)},\n"
        "});\n"
    )
    (output / "runtime-config.js").write_text(configuration, encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": "folderhome.aws-demo-site-build.v1",
                "path": str(output),
                "live_demo_enabled": True,
                "api_key_embedded": True,
                "api_key_value_logged": False,
            },
            sort_keys=True,
        )
    )
    return 0


def _validated_api_url(value: str) -> str:
    if value != value.strip() or value.endswith("/"):
        raise ValueError("API URL must have no surrounding or trailing whitespace.")
    parsed = urlsplit(value)
    expected_suffix = ".execute-api.eu-central-1.amazonaws.com"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(expected_suffix)
        or parsed.path != "/live/demo"
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port is not None
    ):
        raise ValueError("API URL must be the exact eu-central-1 live demo endpoint.")
    return value


def _require_inside(root: Path, target: Path) -> None:
    root = root.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("AWS site output must remain under the ignored build directory.") from exc
    if target == root:
        raise ValueError("AWS site output may not replace the entire build directory.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
