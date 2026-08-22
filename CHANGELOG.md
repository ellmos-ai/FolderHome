# Changelog

**English** | [Deutsch](./CHANGELOG.de.md)

**Current short version:** 0.36 / 2026-08-22  
**Direct predecessor:**  
[`docs/archive/CHANGELOG-through-phase35.md`](./docs/archive/CHANGELOG-through-phase35.md)

All relevant changes are documented in this file. The detailed phase‑by‑phase history up to Phase 35 remains unchanged in the archive.

## [Unreleased]

### Added

- real, finally limited Strands agent with profile‑specific document search and topic dossier
- deterministic no‑network model adapter over the public Strands‑ `Model` interface
- optional Amazon Bedrock path with separate network and data transfer gates
- reproducible synthetic competition demo with four hashed artifacts
- `agent plan`, `agent run` and `demo run` in the CLI
- reusable resource budget contract for file count, bytes and runtime
- publisher‑bound HTTPS trust verification for official performance handoffs
- connection limits, socket timeout and overload rejection in the loopback server
- `SECURITY.md`, English submission package and 36‑phase completion audit
- new skill `folderhome-strands-agent` and associated workflow
- Windows runtime dependency `tzdata==2026.3`

### Changed

- Runtime binds `strands-agents==1.53.0` exactly
- Dev dependency requires at least `pytest 9.0.3`
- Ingest, Snapshot, Transformation, Package, Contacts, Calendar, Finance, Cleanup, Health, Inventory and Medication use shared budgets
- README, architecture, feature analysis, provenance and license register updated to Phase 36
- Overly long project documents archived and replaced with short current versions with direct predecessor reference
- Workflow router updated to 31 playbooks
- English is now the default for 122 documentation pages; the preserved German versions use the `.de.md` suffix and include reciprocal language links
- Workflow router generation now synchronizes 31 English and 31 German playbooks without counting localized mirrors twice
- Local agent instructions, task lists, state files and implementation plans are retained locally but excluded from Git

### Security

- Security scan of 357 files and 12/12 surfaces completed
- three findings fixed: unrestricted document processing, arbitrary official hosts and unrestricted loopback threads
- additional adversarial URL cases for trailing dot, percent‑encoding and explicit port added
- potentially sensitive local search hits may reach Bedrock only after a data transfer release separated from the technical network gate
- the downstream 66‑file delta audit confirmed this approval gap as the fourth, now fixed finding
- `pip-audit` after update of local testing tools without known vulnerabilities

### Verified

- 333/333 automated tests
- Ruff and Compileall with no findings
- 8/8 plugin manifests and 12/12 skills valid
- 31 workflows synchronized
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
