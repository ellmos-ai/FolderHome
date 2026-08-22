# Workflow: Create FCSA Sorting Plan

**English** | [Deutsch](./fcsa-dry-run.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad-hoc  
> **Duration:** dependent on folder size

## Purpose

Inspect an existing document folder with the pinned FCSA component and create a traceable sorting plan without modifying the inbox folder, the target folders, or the configured FCSA state.

## Preconditions

- The three FCSA configuration files are present and reference only explicitly approved scan paths.  
- The FCSA version in use matches the pinned FolderHome manifest.  
- Only the capability `documents.collect_sort` is invoked in the dry run; a live execution is not part of this workflow.

## Steps

1. **Check provider** — Verify the FCSA version and, for a local checkout, also the Git revision against the component manifest.  
2. **Validate configuration** — FCSA loads the three configuration files using its own fail-closed rules.  
3. **Create shadow state** — `state_dir` and `trash_dir` are redirected to a temporary directory for this run.  
4. **Execute dry run** — Each configured scan path is analyzed through the public FCSA pipeline.  
5. **Check immutability** — Neither source files may be moved nor target or productive state files written.  
6. **Translate plan** — Categories and planned actions are transferred into the FolderHome run contract with provenance, gates, and evidence.  
7. **Write report atomically** — The complete JSON report is published only after successful creation.

## Exit-Criteria

- [ ] The provider matches the pinned manifest.  
- [ ] The report uses `ellmos.home-agent.run-report.v1`.  
- [ ] Inbox, target, and productive state folders are unchanged.  
- [ ] Every planned filesystem action remains `planned` and requires a gate.  
- [ ] Errors are captured as a failed, atomically written report.

## Pitfalls

- FCSA's own dry run normally writes a confirmation to `state_dir`. FolderHome must redirect this confirmation to a temporary shadow state so that the plan does not masquerade as a later live release.  
- The FCSA CLI does not yet provide JSON output in the pinned revision. Therefore, the adapter uses the documented Python pipeline and never parses human‑readable terminal output.  
- A family profile within the same OS account is not a security boundary.

## Related

- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Component and security boundaries  
- [`../SECURITY.md`](../SECURITY.md) — Gates and atomic reports  
- [`../manifests/components/file-collect-sort-action.toml`](../manifests/components/file-collect-sort-action.toml) — Provider pin  

## History

- **2026-08-21** — Initial Phase‑2 contract created
