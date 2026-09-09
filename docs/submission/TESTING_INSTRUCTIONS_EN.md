# FolderHome Testing Instructions

These instructions exercise the local fixture without AWS credentials or real
personal data. Downloading the source and dependencies requires network access;
the fixture itself makes no external requests.

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

## Interactive synthetic accident journey

Start the token-gated loopback UI:

```powershell
.venv\Scripts\python.exe -m folderhome demo accident-serve `
  --workspace-dir .local-demo\accident `
  --port 8767 --approve-loopback-server --json
```

Open the emitted `access_url`, submit the prefilled Hyundai i10 accident
request, review the four-step plan and use the exact displayed
`/confirm <plan_id>` command. Expected local results are a current purpose-bound
claims contact, a claim-letter draft, a contract overview and a local follow-up
appointment. The page must continue to show synthetic fixture mode, no external
network and no automatic send or archive action. **Reset case** returns the
owned fixture workspace to its initial state.

The public page in `site/` is a scripted browser walkthrough and says so on the
page. It is useful for product orientation, but the command above is the real
adapter execution proof.

## AgentCore HTTP contract

`deploy/agentcore/` contains an ARM64, non-root container candidate. Without an
AWS deployment, its exact application contract is still tested locally:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_agentcore_runtime.py -q
```

It verifies `GET /ping`, `POST /invocations`, body limits, session isolation,
exact confirmation, synthetic-only data and path-free responses. Passing this
test is not a claim that an ECR image or AgentCore endpoint exists.

## Full verification

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m folderhome plugins validate --json
.venv\Scripts\python.exe _tools\doc-lint
.venv\Scripts\python.exe _tools\workflows-sync --check
```

The full regression suite also checks optional provider integrations against
their exact disclosed revisions. A fresh clone does not supply those external
checkouts. Follow [the provider checkout guide](../provider-checkouts.md) for
authorized local sources; do not reset an existing checkout or remove a failing
pin check to obtain a green result. The credential-free fixture above is a
separate, smaller acceptance path, not a substitute for the full suite.

## Installed-package check

Build both the source archive and a wheel from it (`python -m build` after
installing the `build` development tool). Install that wheel into a **new virtual
environment**, clear any checkout-specific `PYTHONPATH`, and run the following
from outside the repository:

```powershell
python -I -m folderhome plugins validate --json
python -I -m folderhome demo run --output-dir <new-demo-directory> --approve-output-write --json
```

Manifest validation must report all **nine** component IDs, not an empty list.
A missing or empty manifest directory must fail. Keep the generated evidence
and the hash of the exact wheel tested; a hash from an earlier release does not
certify the current source tree.

Inspect both archives before sharing them: local coordination locks, provider
checkouts, credentials and private reports must not be included. The build
regression in `tests/test_distribution_build.py` exercises real source and wheel
archives, including locks nested beside the component manifests. Package checks
are separate from tests that deliberately import `src/`; those source tests
alone do not certify an installed wheel.

## Recipe integration

The local app offers **Multi-step journey** below its chat. Preparation and
confirmation are separate. Missing configured resources disable preparation;
individual live-effect gates still apply at execution. See
[Capability recipes](../capability-recipes.md) for the API and CLI contracts.

`tests/test_local_recipes.py` exercises the local API with real contact, letter
and calendar adapters, synthetic input data and a synthetic mail transport.
With mail approval absent, it verifies that the chain stops after the local
letter and does not create a mail draft or calendar event. These tests do not
certify browser clicks, live-model routing quality or a real mailbox connection.

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
