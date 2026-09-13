# FolderHome

**Tagline:** A local-first desktop Strands agent that gives household documents
a home, with optional AWS capabilities when they add value.

**Track:** Everyday Agents

**Source repository:** <https://github.com/ellmos-ai/FolderHome>

**Demo video:** <https://youtu.be/wPb1wBJcLjQ>

### At a glance

- **Local-first.** The whole competition workflow runs on the user's machine;
  documents never have to leave it.
- **Plan, then approve, then act.** Chat is never approval. Only the exact
  `/confirm <plan_id>` command, bound to the plan's hash, may execute a plan.
- **Real Strands loop, reproducible without credentials.** A deterministic
  model adapter drives the same agent loop and the same tools for judges and tests.
- **Hosted demo you can actually use.** The public page runs the real master
  agent on Amazon Bedrock over a synthetic household of 104 example documents:
  a guided insurance case *and* a free chat in your own words, every generated
  file viewable and downloadable, every turn budget-metered.
- **Optional AWS.** The same runtime runs on Amazon Bedrock; the AgentCore
  Runtime was verified live on 2026-09-13 and re-verified after every deploy
  (runtime version 25 at the time of writing).
- **Tested.** 1,863 automated tests passed on 2026-09-13 (commit `169a2f4`,
  warnings treated as errors; the scheduler-bridge tests run against the pinned
  provider checkout).

## Inspiration

Household administration rarely arrives as a clean database. It arrives as a
photo of a letter, an old PDF, a bank statement, a medical report, an email
attachment or a document saved in the wrong folder. **The hard part is not one
question.** It is repeatedly finding the right version, understanding the
context, preserving evidence, and deciding what may safely happen next.

FolderHome was built for people who want help with that work **without turning
their entire home folder into an opaque cloud prompt** or granting an agent
unlimited authority.

## What it does

FolderHome is a **local document and assistance service agent**. Its Strands
Agents loop can search the local document index and assemble an evidence-linked
topic dossier from a natural request. Around that core, reusable modules cover:

- document collection, sorting plans, folder cleanup, versions and reversible
  actions;
- family-specific organizational profiles under the operating-system account;
- contacts and appointment candidates found in documents;
- virtual accounts, statement coverage and recurring-cost candidates;
- household inventory, medication schedules and health-document dossiers;
- insurance and contract overviews;
- controlled letters, designs, mail and calendar handoffs;
- personal notes, tax workpapers, daily briefings and FindCall planning;
- administrative-notice understanding, draft letters, benefit routing and
  legal-change review candidates.

The complete competition workflow runs locally. Optional Bedrock, AgentCore
and service connectors can be added when they provide a concrete benefit;
privacy and approval gates remain background safeguards rather than the
product's main job.

> **Consequential actions remain separate from understanding.** FolderHome
> plans first, records provenance and hashes, asks for a narrow approval,
> checks the inputs again and never silently upgrades a suggestion into a
> real-world act.

## One end-to-end demo journey

The competition demo follows **one synthetic household problem** instead of a
feature montage. After a Hyundai i10 accident, the user asks FolderHome to find
the current insurance policy, identify the right contact and prepare the next
steps.

1. **Search.** The master agent searches both current and older documents and
   keeps the older policy as evidence.
2. **Plan.** It returns a hash-bound plan. Only the exact `/confirm <plan_id>`
   command may execute it.
3. **Execute locally.** In the hosted demo the confirmed plan runs four local
   steps inside the synthetic household: contact register, calendar handoff,
   contract cockpit and correspondence studio, and the four generated files can
   be viewed and downloaded right on the page. On a privately configured
   installation the packaged `accident-aftercare` recipe follows the same
   pattern and adds a draft-only IMAP mailbox.

Neither path **ever** sends a message, places a call, changes an external
calendar or silently archives the older policy.

### Hosted demo: a real conversation on a synthetic household

The public page offers **two entrances**:

- **Try the test case.** The guided Hyundai i10 insurance claim: four bounded
  steps, a hash-bound plan, the exact `/confirm`, four synthetic result files.
- **Try it in your own words.** A free chat with the real FolderHome master
  agent (Amazon Bedrock Nova Micro) over a synthetic household of **104 example
  documents**: insurance, health, taxes, contracts, calendar and more. The agent
  searches the local index itself, builds dossiers, lists its capabilities and
  proposes plans; the page shows which tools ran and how many model turns a
  reply took.

Nothing in that household is real data, external actions stay disabled, and
each turn reserves **2 cents** in the cumulative money ledger under a **195 USD**
cap for the whole review window. Your own folders never enter the cloud: for
real documents you install FolderHome locally and bring your own model.

## How we built it

### The Strands agent layer

The required agent layer uses `strands-agents==1.53.0`. One conversational
master serves both GUI and CLI through **nine bounded tools, all read-only or
plan-only**, among them local document search, an evidence-linked topic dossier,
capability discovery, and scoped specialist consultation. The model selects an expert semantically; FolderHome
then resolves the selected workflow endpoint deterministically and fail-closed.
A short-lived specialist sees one plan-only tool. Optional personas change
communication style but **never grant capability or permission**.

### Three model providers, gates that follow the transport

The same runtime can use **Amazon Bedrock** after separate explicit network and
local-data-disclosure gates. A third provider runs the same loop against an
**Ollama** server, where the gates follow the transport rather than the vendor:
a model on the loopback interface needs no approval because nothing leaves the
machine, while a remote Ollama host needs exactly the two gates Bedrock needs.
For judges and automated tests, a **deterministic Strands model adapter**
executes the real loop without credentials or network access.

### Executors, approvals and the resource registry

An explicit **executor catalog** keeps runtime coverage honest. A chat message
can only produce a plan. After a separate confirmation bound to the exact plan
hash and steps, a connected typed envelope may call its existing domain executor
and return that executor's report.

- Without a private resource registry, the connected executors reuse personal
  notes, scheduled medication confirmation and the strictly local FindCall fixture.
- A configured registry adds **23 typed resource adapters** for the complete
  local document and assistance stack, including organization, health, finance,
  social law, inventory, tax, briefing, design, FCSA and routines. Each
  publishes a closed request schema to its scoped specialist.
- The runtime catalog reports **actual configured coverage** rather than
  falling back to a generic command runner.

Private resources can additionally connect own-mail drafts, Google calendar and
scheduler registration. **Draft-only mail has no send path.** Google creation
and conditional update/delete require a private OAuth grant, a separate write
gate and exact approval; strong ETags, durable receipts and readback preserve
conflicts and uncertain outcomes. Scheduler registration and app-owned consumer
start require separate gates and confirmations; its queues do not authorize
document changes. Synthetic tests cover these integrations; first OAuth login
and live-account acceptance remain open.

### Recipes and bounded tools

The master has **nine bounded tools, all read-only or plan-only**. A v1 recipe
prepares its whole chain; a v2 recipe prepares separately approved sections with
typed values from verified prior execution reports. The shipped
letter-to-mail-draft journey binds the confirmed letter preview before proposing
an own-mail draft. **Every new section requires a new exact approval.** Runs are
process-local; no imported reports, automatic continuation or blind retry grants
effects.

### Application core

The application core is **Python 3.11+**, with stable data contracts, a CLI, a
loopback-only API and a responsive local web interface. SQLite stores use
append-only events or immutable read access where appropriate. Existing
ellmos modules are connected through **exact revisions and capability
manifests**; their source code is not copied into FolderHome.

### GUI and CLI share one conversation

The GUI and the interactive `agent session` share one application service. The
CLI retains prepared plans in-process and accepts approval only through an
explicit `/confirm <plan_id>` command; **ordinary conversation never counts as
approval.** Both surfaces retain a finite Strands message window per
organizational profile for natural follow-up questions. The history never leaves
process memory and a new-conversation action clears it together with
unconfirmed plans.

### Coding agents over MCP

A third surface attaches coding agents. An **MCP proxy** speaks stdio to Claude
Code or the Codex CLI and forwards **eleven tools** to a running local server.
It starts no application of its own, so there is never a second state; it
refuses any address that is not loopback, and it keeps its diagnostics on stderr
because stdout is the protocol. Chat over MCP is no more an approval than chat
in the GUI: a plan still executes only through the confirm tool with its exact
hash.

What those runs produce is **collectable**. Executed reports stay in a bounded
in-process buffer, and the GUI lists them per profile with file name and size.
Artifacts are fetched by index rather than by a path parameter, so **no physical
path travels in the API**. Configuration itself is written by a separate
installer on its own port and token, and the app GUI keeps no write path to it
at all.

### The installer owns models, keys and folders

That installer became the place where the model lives too. **Five providers**
are selectable: the deterministic fixture, Ollama on this machine or on another
host, Bedrock, Anthropic and OpenAI. Everything from the third onwards leaves
the machine and therefore carries both the network and the sensitive-data gate.
Named presets in `launch.json` turn switching models into an activation rather
than an edit.

**An API key is never a setting:** it goes into a `.env` file beside that
config under one of two known names, and it appears in no plan hash, no status,
no report and no log. A native folder dialog runs in a child process so a
household can point at a folder instead of typing a path, a source purpose
accepts several folders, and the calendar files are written through the same
confirm-verify-replace path as everything else, though only the calendar
commands read them and the running app does not.

### Profiles a household can keep

The installer also owns the profiles now, which turned out to be **the
difference between a demo and something a household can keep**. It adds,
renames and deletes them, edits their rules against the closed key set the
contract accepts, and keeps its own profile folder instead of borrowing the
examples in the repository.

A deletion is the interesting case: folder bindings that would then belong to
nobody fall away in the same plan, the calendar accounts of that profile leave
their file, the preview names everything that goes, and the profile file itself
is **moved into a dated folder rather than deleted**, because a profile file is
the only place its rules live.

### Subscriptions: your agent is the brain

A section called **Subscriptions** closes the loop for people who already pay
for an agent. Claude Code with a Claude subscription and the Codex CLI with a
ChatGPT subscription drive FolderHome as a tool, which means **the agent is the
brain and FolderHome needs no key of its own**. The installer shows both editor
entries ready to copy, generated from the same integration plan the CLI prints.
And because an agent may arrive without a human reading a README first,
`llms.txt` states the MCP and HTTP entry points, the safety model and the
providers in one file at the repository root; a test asserts that every route,
schema and tool it names really exists in the service.

### AgentCore and the cumulative money ledger

An isolated HTTP adapter maps the same application contract to **AgentCore**.
The direct-code Runtime is deployed on ARM64 and, on **2026-09-13**, completed
one Bedrock-backed synthetic journey end to end through the public proxy:

- the **Nova Micro** master agent (EU inference profile, up to six bounded
  model turns and 1,536 output tokens per reply) searched the synthetic policies,
- the plan stopped at `/confirm`,
- and the confirmed run produced **four result files with no external actions**.

Admission is governed by a **cumulative daily money ledger** (unspent
entitlement carries forward) rather than a fixed request count, and the ledger
is bound to the exact runtime version and cost review. AWS Support had reported
the Bedrock access issue resolved on 2026-09-08; the local app verified a real
Bedrock turn on 2026-09-12. Because the cloud runtime exposes only `/ping` and
`/invocations`, result files are returned inline in the AgentCore response, so a
browser can save them without a storage service. Since 2026-09-13 the public
CloudFront page has the browser agent **enabled**: every plain prompt is a
real master-agent turn over a per-session copy of the synthetic household,
the default accident prompt keeps its deterministic four-step plan as the
regression path, and `manage.py verify` re-proves the whole journey (exact
ledger delta of two forwards) after each deploy.

## Safety and privacy by construction

- **Security boundary:** the operating-system account and its file
  permissions; household profiles are explicitly organizational only.
- **Loopback only:** the local server binds to `127.0.0.1`, requires a
  short-lived token and enforces exact Host and Origin checks.
- **Finite ceilings:** file, parser, renderer, HTTP and agent work all have
  hard limits.
- **Explicit gates:** sensitive workflows require explicit local-read gates.
- **Hash-bound outputs:** files and outputs are never overwritten and are
  reversible where the underlying action supports it.
- **Trusted links only:** official benefit links are bound to reviewed
  publishers and exact HTTPS hosts.
- **Synthetic data:** the repository and demo contain synthetic data only.

FolderHome does **not** claim to diagnose, provide legal or tax advice,
determine benefit eligibility, prove a payment or guarantee that every document
event was detected.

## Challenges

**Many capabilities, no giant permission boundary.** Search should not grant
mail access; reading a date should not create a calendar event; finding an old
policy should not archive it automatically; a topic match in a law should not
become a legal judgment. We solved this with typed contracts, explicit
provenance, separate plan and execution stages, narrow approvals, deterministic
reports and provider-specific gates.

**Reproducibility.** A cloud-only demo would make reviewers depend on our
credentials. The deterministic model adapter therefore drives the real Strands
loop and real FolderHome tools while using synthetic local data. It is evidence
of orchestration, not a claim about model quality.

## Accomplishments

- A **coherent local product surface** rather than a prompt collection.
- A **real Strands tool loop** that is reproducible without AWS credentials.
- **Thirty-six implementation phases** with tests for success and fail-closed
  behavior; 1,465 tests passed on 2026-09-13.
- **Reusable capabilities** for documents, household administration, finance,
  health organization and administrative assistance.
- **Explicit disclosure** of every reused module and every capability boundary.
- **Security remediation** for bounded document work, trusted official links
  and bounded loopback connections.

## What we learned

**An agent is more trustworthy when uncertainty is part of its data model.** We
found that the most useful output is often not “done,” but a precise state such
as “ready for review,” “source stale,” “missing evidence,” “provider blocked,”
or “planned but not approved.” Those states let one agent coordinate broad
household work without pretending that all domains have the same risk.

**Reuse works best when the boundary is declared first:** which revision, which
public API, which side effects and which evidence prove that the bridge is
still valid.

## What's next

After the competition, FolderHome can remain as a reduced public edition while
its reusable modules are integrated into FolderHome-Sovereign. Future work can
add separately reviewed live connectors, richer office renderers and OCR
intake. Those additions will retain the same plan, approval, evidence and
least-authority contracts.

## Built with

- Python
- Strands Agents SDK 1.53.0
- Amazon Bedrock integration path
- Ollama for local and self-hosted models
- Model Context Protocol Python SDK
- SQLite
- HTML, CSS and JavaScript local interface
- file-collect-sort-action
- doc-services
- KnowledgeDigest
- pytest and Ruff

## Pre-existing work disclosure

FolderHome and its `NEW_CORE`/`NEW_BRIDGE` code were created during the
submission period. The project incorporates or references pre-existing modules
only through the exact disclosures in `COMPETITION_CODE_MAP.md`, component
manifests and `THIRD_PARTY_LICENSES.md`. No pre-existing module is presented as
new FolderHome code.
