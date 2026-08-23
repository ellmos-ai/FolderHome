# FolderHome

**Tagline:** A local-first Strands agent that turns scattered household
documents into searchable, explainable and safely actionable workflows.

**Track:** Everyday Agents

**Source repository:** <https://github.com/ellmos-ai/FolderHome>

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

## How we built it

The required agent layer uses `strands-agents==1.53.0`. One conversational
master serves both GUI and CLI through four bounded tools: local document
search, an evidence-linked topic dossier, capability discovery, and scoped
specialist consultation. The model selects an expert semantically; FolderHome
then resolves the selected workflow endpoint deterministically and fail-closed.
A short-lived specialist sees one plan-only tool. Optional personas change
communication style but never grant capability or permission. The same runtime
can use Amazon Bedrock after separate explicit network and local-data-disclosure
gates. For judges and automated tests, a deterministic Strands model adapter
executes the real loop without credentials or network access.

An explicit executor catalog keeps runtime coverage honest. A chat message can
only produce a plan. After a separate confirmation bound to the exact plan hash
and steps, a connected typed envelope may call its existing domain executor and
return that executor's report. Without a private resource registry, the
connected executors reuse personal notes, scheduled medication confirmation and
the strictly local FindCall fixture. A configured registry adds 23 typed
resource adapters for the complete local document and assistance stack,
including organization, health, finance, social law, inventory, tax, briefing,
design, FCSA and routines. Each publishes a closed request schema to its scoped
specialist. This configuration reports 26 connected and three visibly
unconnected endpoints instead of falling back to a generic command runner. Only
mail, external calendars and scheduler registration still need explicit
external connector configuration with live-effect gates.

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
