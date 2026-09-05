# FolderHome

**Tagline:** A local-first desktop Strands agent that gives household documents
a home, with optional AWS capabilities when they add value.

**Track:** Everyday Agents

**Source repository:** <https://github.com/ellmos-ai/FolderHome>

**Demo video:** <https://youtu.be/wPb1wBJcLjQ>

## Inspiration

Household administration rarely arrives as a clean database. It arrives as a
photo of a letter, an old PDF, a bank statement, a medical report, an email
attachment or a document saved in the wrong folder. The hard part is not one
question. It is repeatedly finding the right version, understanding the
context, preserving evidence, and deciding what may safely happen next.

FolderHome was built for people who want help with that work without turning
their entire home folder into an opaque cloud prompt or granting an agent
unlimited authority.

## What it does

FolderHome is a local document and assistance service agent. Its Strands
Agents loop can search the local document index and assemble an evidence-linked
topic dossier from a natural request. Around that core, reusable modules cover:

The complete competition workflow runs locally. Optional Bedrock, AgentCore
and service connectors can be added when they provide a concrete benefit;
privacy and approval gates remain background safeguards rather than the
product's main job.

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

Consequential actions remain separate from understanding. FolderHome plans
first, records provenance and hashes, asks for a narrow approval, checks the
inputs again and never silently upgrades a suggestion into a real-world act.

## One end-to-end demo journey

The competition demo follows one synthetic household problem instead of a
feature montage. After a Hyundai i10 accident, the user asks FolderHome to find
the current insurance policy, identify the right contact and prepare the next
steps. The master agent searches both current and older documents, keeps the
older policy as evidence, and returns a hash-bound plan. Only the exact
`/confirm <plan_id>` command may execute it. The packaged `accident-aftercare`
recipe resolves contact, claim letter, draft-only IMAP mailbox and local
calendar/ICS work into one reviewed plan. It never sends the message, places a
call, changes an external calendar or silently archives the older policy.

## How we built it

The required agent layer uses `strands-agents==1.53.0`. One conversational
master serves both GUI and CLI through four bounded tools: local document
search, an evidence-linked topic dossier, capability discovery, and scoped
specialist consultation. The model selects an expert semantically; FolderHome
then resolves the selected workflow endpoint deterministically and fail-closed.
A short-lived specialist sees one plan-only tool. Optional personas change
communication style but never grant capability or permission. The same runtime
can use Amazon Bedrock after separate explicit network and local-data-disclosure
gates. A third provider runs the same loop against an Ollama server, where the
gates follow the transport rather than the vendor: a model on the loopback
interface needs no approval because nothing leaves the machine, while a remote
Ollama host needs exactly the two gates Bedrock needs. For judges and automated
tests, a deterministic Strands model adapter executes the real loop without
credentials or network access.

An explicit executor catalog keeps runtime coverage honest. A chat message can
only produce a plan. After a separate confirmation bound to the exact plan hash
and steps, a connected typed envelope may call its existing domain executor and
return that executor's report. Without a private resource registry, the
connected executors reuse personal notes, scheduled medication confirmation and
the strictly local FindCall fixture. A configured registry adds 23 typed
resource adapters for the complete local document and assistance stack,
including organization, health, finance, social law, inventory, tax, briefing,
design, FCSA and routines. Each publishes a closed request schema to its scoped
specialist. A registry that also declares `mail.draft_account` reports, across
all 33 endpoints, 27 connected, one direct read-only, three planning-only and
two visibly unconnected endpoints instead of falling back to a generic command
runner. Draft-only mail has no send path and requires its own approval.
External calendars and scheduler registration remain unconnected.

The application core is Python 3.11+, with stable data contracts, a CLI, a
loopback-only API and a responsive local web interface. SQLite stores use
append-only events or immutable read access where appropriate. Existing
ellmos modules are connected through exact revisions and capability manifests;
their source code is not copied into FolderHome.

The GUI and the interactive `agent session` share one application service. The
CLI retains prepared plans in-process and accepts approval only through an
explicit `/confirm <plan_id>` command; ordinary conversation never counts as
approval.
Both surfaces retain a finite Strands message window per organizational profile
for natural follow-up questions. The history never leaves process memory and a
new-conversation action clears it together with unconfirmed plans.

A third surface attaches coding agents. An MCP proxy speaks stdio to Claude Code
or the Codex CLI and forwards eleven tools to a running local server. It starts
no application of its own, so there is never a second state; it refuses any
address that is not loopback, and it keeps its diagnostics on stderr because
stdout is the protocol. Chat over MCP is no more an approval than chat in the
GUI: a plan still executes only through the confirm tool with its exact hash.
What those runs produce is collectable. Executed reports stay in a bounded
in-process buffer, and the GUI lists them per profile with file name and size.
Artifacts are fetched by index rather than by a path parameter, so no physical
path travels in the API. Configuration itself is written by a separate
installer on its own port and token, and the app GUI keeps no write path to it
at all.

An isolated HTTP adapter maps the same application contract to AgentCore. The
quota-bounded direct-code Runtime is deployed and `READY`; a synthetic fixture
roundtrip reached `confirmation_required`. The public CloudFront configuration
keeps the browser agent disabled, and the submission does not claim a
Bedrock-backed AgentCore journey while the applied Nova Micro quotas remain
zero. A fresh 2026-08-27 readback again found the Runtime `READY`, version 4,
the model profile `ACTIVE`, and all three real-time quotas at zero; CloudWatch
showed one throttled request and no successful invocation over 24 hours. Because
the cloud runtime exposes only `/ping` and `/invocations`, result files are
returned inline in the AgentCore response, so a browser can save them without a
storage service. That path is implemented and tested locally and is not yet
deployed.

## Safety and privacy by construction

- The operating-system account and its file permissions are the security
  boundary; household profiles are explicitly organizational only.
- The local server binds to `127.0.0.1`, requires a short-lived token and
  enforces exact Host and Origin checks.
- File, parser, renderer, HTTP and agent work all have finite hard ceilings.
- Sensitive workflows require explicit local-read gates.
- Files and outputs are hash-bound, never overwritten and reversible where
  the underlying action supports it.
- Official benefit links are bound to reviewed publishers and exact HTTPS
  hosts.
- The repository and demo contain synthetic data only.

FolderHome does not claim to diagnose, provide legal or tax advice, determine
benefit eligibility, prove a payment or guarantee that every document event
was detected.

## Challenges

The main engineering challenge was combining many useful capabilities without
creating one giant permission boundary. Search should not grant mail access;
reading a date should not create a calendar event; finding an old policy should
not archive it automatically; a topic match in a law should not become a legal
judgment. We solved this with typed contracts, explicit provenance, separate
plan and execution stages, narrow approvals, deterministic reports and
provider-specific gates.

Another challenge was reproducibility. A cloud-only demo would make reviewers
depend on our credentials. The deterministic model adapter therefore drives
the real Strands loop and real FolderHome tools while using synthetic local
data. It is evidence of orchestration, not a claim about model quality.

## Accomplishments

- A coherent local product surface rather than a prompt collection.
- A real Strands tool loop that is reproducible without AWS credentials.
- Thirty-six implementation phases with tests for success and fail-closed
  behavior.
- Reusable capabilities for documents, household administration, finance,
  health organization and administrative assistance.
- Explicit disclosure of every reused module and every capability boundary.
- Security remediation for bounded document work, trusted official links and
  bounded loopback connections.

## What we learned

An agent is more trustworthy when uncertainty is part of its data model. We
found that the most useful output is often not “done,” but a precise state such
as “ready for review,” “source stale,” “missing evidence,” “provider blocked,”
or “planned but not approved.” Those states let one agent coordinate broad
household work without pretending that all domains have the same risk.

We also learned that reuse works best when the boundary is declared first:
which revision, which public API, which side effects and which evidence prove
that the bridge is still valid.

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
