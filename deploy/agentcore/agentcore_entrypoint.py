"""Direct-code entry point for the FolderHome AgentCore HTTP server."""

from __future__ import annotations

import os

from folderhome.agentcore_server import main

os.environ.setdefault("FOLDERHOME_AGENTCORE_CONTAINER", "1")


if __name__ == "__main__":
    raise SystemExit(main())
