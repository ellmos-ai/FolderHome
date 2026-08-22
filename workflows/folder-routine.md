# Workflow: Planned cleanup of observed folder

**English** | [Deutsch](./folder-routine.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** after an explicitly triggered scan point  
> **Duration:** depending on file count and extraction formats  

## Purpose

Check a declared observed folder against its last checkpoint, plan a due set of changes or the full inventory, and execute a deliberately approved batch with a subsequent checkpoint.

## Preconditions

- Watch ID, profile rules, target root, reference date, and observation time are explicit.  
- The target root is outside the observed folder.  
- The last checkpoint is identity‑verified and unambiguous.  
- Batch approval, file gate, and state gate are present for execution.

## Steps

1. **Load watch** — Verify root, profile, scope, interval, recursion, and active status.  
2. **Read-only scan** — compare the current content‑free snapshot against the last checkpoint without writing a new checkpoint.  
3. **Apply mode** — limit `changes` to new, changed, and uniquely moved paths only when due; apply `full` explicitly to all files.  
4. **Plan cleanup** — run only the selected paths through the folder‑wide conflict and document action planning.  
5. **Validate plan** — check routine ID, status, selection, batch ID, conflicts, and release‑eligible documents.  
6. **Approve batch** — create a separate approval file for the deliberately selected document, plan, hash, and action IDs.  
7. **Preflight execution** — reconfirm the expected last checkpoint and full scan ID without write access.  
8. **Execute batch** — write intent and execute the approved individual transactions.  
9. **Finalize checkpoint** — only after successful batch, store the resulting folder state immutably and write the routine report.  
10. **Check errors** — if the checkpoint fails, file actions must run backwards and the report must indicate `rolled_back` or `failed`.

## Exit-Criteria

- [ ] `routine-plan` has not altered sources, targets, or state.  
- [ ] `not_due`, `no_changes`, and `planned` are clearly distinguishable.  
- [ ] Full mode was explicitly selected and bypasses no approval.  
- [ ] An execution matches the routine, scan, and batch state.  
- [ ] A successful run possesses routine intent, batch audit, and checkpoint.  
- [ ] A checkpoint error leaves a documented return status.

## Pitfalls

- A routine plan is not an approval and does not write a checkpoint.  
- Pure timestamp changes do not trigger processing in change mode.  
- A target within the observed root can cause an endless resumption and is therefore blocked.  
- A modified folder or competing checkpoint invalidates the plan.  
- Phase 13 does not register an operating system scheduler.

## Related

- [`./directory-observation.md`](./directory-observation.md) — Scan and checkpoint  
- [`./folder-cleanup.md`](./folder-cleanup.md) — folder‑wide batch plan  
- [`./document-action-execution.md`](./document-action-execution.md) — Undo  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-13 data flow  

## History

- **2026-08-21** — Created after Phase-13 end-to-end acceptance
