#!/usr/bin/env python3
"""Interactive and headless start menu for FolderHome and Setup.

Delegates to folderhome.starter module, providing backward compatibility
and script-level access from scripts/START.cmd.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path when running from a git checkout
_repo_root = Path(__file__).resolve().parent.parent
_src = _repo_root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from folderhome.starter import *  # noqa: E402, F403
from folderhome.starter import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
