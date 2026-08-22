# FolderHome Testing Instructions

These instructions exercise the submitted project without AWS credentials,
network access or real personal data.

## Platform

- Windows, macOS or Linux desktop
- Python 3.11 or newer
- About 1 GB free disk space for a virtual environment and dependencies

## Install

```powershell
git clone https://github.com/ellmos-ai/FolderHome.git
cd FolderHome
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,transform]"
```

On macOS or Linux, replace `.venv\Scripts\python.exe` with
`.venv/bin/python`.

The exact required agent dependency is `strands-agents==1.53.0`.

## Thirty-second reproducible agent demo

Choose a new output directory:

```powershell
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir .local-demo\competition `
  --approve-output-write --json
```

Expected result:

- exit code `0`;
- JSON status `passed`;
- framework `strands-agents`, version `1.53.0`;
- scenarios `document-search` and `theme-dossier` both `passed`;
- `network_used=false` and an empty `side_effects` list;
- four new files in `.local-demo/competition`:
  `01-document-search.json`, `02-theme-dossier.json`, `DEMO.md` and
  `EVIDENCE.json`.

Open `DEMO.md` and inspect `EVIDENCE.json`. The evidence file records SHA-256
values for the generated artifacts. Re-running against the same directory must
fail instead of overwriting the first result.

## Full verification

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m folderhome plugins validate --json
.venv\Scripts\python.exe _tools\doc-lint
.venv\Scripts\python.exe _tools\workflows-sync --check
```

The final verified counts and hashes are recorded in
`docs/phase36-completion-audit.md`.

## What the fixture proves

The fixture is a deterministic model implementation of the Strands `Model`
interface. It runs through the actual Strands `Agent`, sequential tool
executor, tool decorator, FolderHome local application boundary and document
services. It proves the framework and tool loop without requiring reviewer
credentials.

It does not prove Bedrock availability or model quality. Bedrock mode exists
behind explicit `--bedrock-model-id`, `--aws-region`, `--allow-network` and
`--approve-sensitive-cloud-data` arguments. Network access and disclosure of
local search results are separate approvals. Bedrock is intentionally not
required for this offline acceptance run.

## Privacy

Every included profile, document name and result is synthetic. Do not replace
the examples with real health, financial, identity or contact data when
recording public evidence.
