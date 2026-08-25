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

The complete fail-closed run is `415 passed, 3 failed`; all three failures are
the documented local HungryCall/Ringedingeding checkout revision mismatches.
The bounded acceptance run with exactly those three external pin probes
deselected is `415 passed, 3 deselected`.

The final wheel was then installed into a new virtual environment outside the
repository. Its smoke test verified the packaged bilingual GUI assets, the
confirmed four-result accident journey, AgentCore `/ping` with HTTP 200, zero
network use and zero external actions. The tested wheel SHA-256 is
`8b5929c855226a4c2c78223b65e85adc12dcd4b5aa61445d010e7fdf8d0eb24a`.

This fail-closed result is intentional: the local HungryCall checkout was
`2c7db533f073d07eae6d758ceab91b9423ae1dc7` instead of the disclosed manifest
revision `2c7db533f073d07eae6d758ceab91b9423ae1dc7`; Ringedingeding was
`55f426598d716991b0fae8c5e1c092aceb8c4da8` instead of
`55f426598d716991b0fae8c5e1c092aceb8c4da8`. FolderHome does not silently load
either changed provider.

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
