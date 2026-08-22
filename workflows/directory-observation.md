# Workflow: Scan Observed Folder and Verify Corrections

**English** | [Deutsch](./directory-observation.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad‑hoc, later per scheduled scan run  
> **Duration:** dependent on file count and file size  

## Purpose

Check a declared folder (without raw document text) against its last verified checkpoint, explain changes, and emit documented manual moves as learning candidates that require review.

## Preconditions

- `folderhome.watched-folders.v1` contains root, profile, scope, interval, recursion, and active status.  
- Local state folder and observation timestamp are explicitly selected.  
- The observation timestamp is an ISO timestamp with time zone.  
- The state gate applies only to the new snapshot files.  
- For correction learning, a JSON file conforming to schema `folderhome.placement-receipts.v1` is available.

## Steps

1. **Select observation** — Load configuration and choose exactly one active `watch_id` with resolved root.  
2. **Check last checkpoint** — Validate existing snapshot IDs and determine the temporally latest unique state of the same root.  
3. **Capture current state** — Use the explicit timestamp and collect only path, size, filesystem timestamp, hash, and symlink exclusions.  
4. **Compare states** — The scan distinguishes addition, removal, content change, metadata change, and unique move.  
5. **Assign storage evidence** — Link optional evidence to previous storages using hash, source path, profile, scope, and rule sources.  
6. **Review scan report** — Check interval due‑ness, diff, and appropriate learning candidates; `automatic_promotion` must be `false`.  
7. **Decide checkpoint** — Without `--approve-state-write` the run remains read‑only; with the gate, after a re‑verification of history, exactly one new snapshot is added.

## Exit‑Criteria

- [ ] Observation and all existing snapshot IDs have been validated.  
- [ ] The previous and current snapshots belong to the same source folder.  
- [ ] Ambiguous hash duplicates were not claimed as a move.  
- [ ] Each learning candidate has a matching prior storage evidence.  
- [ ] `automatic_promotion` is global and per candidate `false`.  
- [ ] Documents and profile rules have not been altered.

## Pitfalls

- An identical hash does not prove a specific source and destination path when there are multiple identical copies; therefore this case is intentionally left ambiguous.  
- An observed move without storage evidence may indicate a user action, but it does not constitute a violation of a FolderHome rule.  
- A scan started before the interval expires is permissible, but it exhibits `interval_due=false`; Phase 10 does not install a scheduler.  
- `mtime_ns` is a filesystem metadata field, not a document or contract date.  
- The snapshot contains hashes and paths; it is content‑free but still contains household metadata that must be protected.

## Related

- [`./document-action-plan.md`](./document-action-plan.md) — Source of the storage evidence needed later  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑9 / Phase‑10 data flow  

## History

- **2026-08-21** — Created after Phase‑9 end‑to‑end acceptance  
- **2026-08-21** — Extended for declarative Phase‑10 scan runs
