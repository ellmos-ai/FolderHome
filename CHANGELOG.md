# Changelog

**English** | [Deutsch](./CHANGELOG.de.md)

**Current short version:** 0.47 / 2026-08-23  
**Direct predecessor:**  
[`docs/archive/CHANGELOG-through-phase35.md`](./docs/archive/CHANGELOG-through-phase35.md)

All relevant changes are documented in this file. The detailed phase‑by‑phase history up to Phase 35 remains unchanged in the archive.

## [Unreleased]

### Added

- English-default dashboard localization with a persistent English/German switch
- persistent light and dark dashboard themes with accessible keyboard controls
- bilingual runtime model-status card distinguishing deterministic fixture,
  configured-but-unverified Bedrock, and a Bedrock connection verified by a
  successful in-process model turn
- machine-readable local-only versus local-first-hybrid runtime topology;
  FolderHome state and workflows stay local while optional Bedrock inference
  uses the AWS cloud
- one GUI-first FolderHome master agent shared by browser and CLI, with
  one-shot `agent chat` and an in-process interactive `agent session`
- bounded process-local Strands conversation continuity per organizational
  profile, with GUI and CLI reset that also discards unconfirmed plans and
  their unexecuted typed envelopes
- semantic expert selection, explicit fail-closed workflow endpoint resolution and style-only personas
- on-demand specialist agents restricted to one planning endpoint
- separate hash-bound GUI/API plan confirmation without false execution claims
- typed, fail-closed executor catalog for all 33 master workflows, with visible
  connected, direct-read-only, planning-only and not-connected states
- first end-to-end chat execution adapter for the existing append-only llm-note
  personal-notes workflow, including one-time replay protection and a domain report
- second end-to-end GUI/CLI chat adapter for confirming an existing scheduled
  medication dose, reusing the revision-bound medication workflow without
  exposing state paths, providing medical advice, or changing medication
- closed machine-readable request schemas in the executor catalog and bounded
  specialist prompt for every connected adapter
- private, schema-validated logical resource registry with profile scope,
  purpose binding, least-privilege operations and a model-safe path-free catalog
- 23 typed resource-ID adapters completing the local document and assistance
  stack: document actions, cleanup, observation, packages, routines, FCSA,
  contacts, correspondence, local calendar, contracts, design, health, finance,
  social law, inventory, tax and Daily Briefing
- fail-closed runtime classification of the three remaining gaps: mail,
  external calendars and scheduler registration require configured external
  connectors with separate live-effect approvals
- typed, approval-bound execution of the existing strictly local FindCall
  fixture cascade, with masked numbers and no network, calls, booking, or
  commitment
- real, finally limited Strands agent with profile‑specific document search and topic dossier
- deterministic no‑network model adapter over the public Strands‑ `Model` interface
- optional Amazon Bedrock path with separate network and data transfer gates
- explicit Bedrock connect/read timeouts and one total SDK attempt per model call
- reproducible synthetic competition demo with four hashed artifacts
- `agent plan`, `agent run`, `agent chat`, `agent session` and `demo run` in the CLI
- reusable resource budget contract for file count, bytes and runtime
- publisher‑bound HTTPS trust verification for official performance handoffs
- connection limits, socket timeout and overload rejection in the loopback server
- `SECURITY.md`, English submission package and 36‑phase completion audit
- new skills `folderhome-strands-agent` and `folderhome-master-agent` with their
  associated workflows
- Windows runtime dependency `tzdata==2026.3`

### Changed

- Runtime binds `strands-agents==1.53.0` exactly
- Dev dependency requires at least `pytest 9.0.3`
- Ingest, Snapshot, Transformation, Package, Contacts, Calendar, Finance, Cleanup, Health, Inventory and Medication use shared budgets
- README, architecture, feature analysis, provenance and license register updated to Phase 36
- Overly long project documents archived and replaced with short current versions with direct predecessor reference
- Workflow router updated to 33 playbooks
- English is now the default for 122 documentation pages; the preserved German versions use the `.de.md` suffix and include reciprocal language links
- Workflow router generation now synchronizes 33 English and 33 German playbooks without counting localized mirrors twice
- Local agent instructions, task lists, state files and implementation plans are retained locally but excluded from Git

### Security

- Security scan of 357 files and 12/12 surfaces completed
- three findings fixed: unrestricted document processing, arbitrary official hosts and unrestricted loopback threads
- additional adversarial URL cases for trailing dot, percent‑encoding and explicit port added
- potentially sensitive local search hits may reach Bedrock only after a data transfer release separated from the technical network gate
- the downstream 66‑file delta audit confirmed this approval gap as the fourth, now fixed finding
- `pip-audit` after update of local testing tools without known vulnerabilities

### Verified

- 394 automated tests passed; three external live-checkout pin tests were
  deliberately deselected because the current local HungryCall and
  Ringedingeding revisions differ from their pinned manifests
- English/light and German/dark dashboard states visually inspected at 1440 × 1100; focused GUI tests and JavaScript syntax check passed
- Ruff and Compileall with no findings
- 8/8 plugin manifests valid; the master-agent skill is covered by the current repository skill checks
- 33 workflows synchronized
- the configured EU Nova Micro inference profile was active, but the single
  bounded synthetic FolderHome turn returned neither response nor error within
  60 seconds; it was terminated without retry and is not claimed verified
- synthetic Strands run: two scenarios, no network, no side‑effects; repeat blocked at the Never‑overwrite gate
- Wheel contains agent, demo, resource budget, host verification and GUI

## Historical Milestones

| Phases | Result |
|---|---|
| 1–8 | integration core, FCSA, document library, versions, profiles, actions, transformation and type packages |
| 9–15 | folder monitoring, correction learning, scans, execution/undo, routines, queue and scheduler handoff |
| 16–21 | contacts, calendar, FindCall, finance, household and medication |
| 22–30 | health, contracts, correspondence, Office/Design, mail, calendar connectors, notes, taxes and Daily Brief |
| 31–35 | official notices, administrative drafts, benefit and funding pre‑screen, legal changes and local GUI/API |
| 36 | hardening, Strands agent, competition demo and submission‑ready local package |

The individual changes and the test states at that time are in the direct predecessor; the current requirement evidence is in [`docs/phase36-completion-audit.md`](./docs/phase36-completion-audit.md).

---
