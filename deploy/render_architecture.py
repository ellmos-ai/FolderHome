"""Render a trusted local SVG to PNG; --check detects drift without writes.

Install the dev extra first. Font availability affects raster output: use the
same font files and resvg version for generation and verification.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path

import resvg_py


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font-file", type=Path, action="append", default=[])
    parser.add_argument("--no-system-fonts", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("source and output must differ")
    for font in args.font_file:
        if not font.is_file():
            parser.error(f"font file does not exist: {font}")
    source = args.source.read_text(encoding="utf-8")
    png = resvg_py.svg_to_bytes(
        svg_string=source,
        skip_system_fonts=args.no_system_fonts,
        font_files=[str(path) for path in args.font_file],
    )
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != png:
            print("STALE: PNG differs from this SVG, renderer or font environment")
            return 1
    else:
        args.output.write_bytes(png)
    print(f"OK: {len(png)} bytes; sha256={sha256(png).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
