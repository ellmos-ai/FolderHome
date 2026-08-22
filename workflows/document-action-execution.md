# Workflow: Approve and Undo Document Action

**English** | [Deutsch](./document-action-execution.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad-hoc after human plan review  
> **Duration:** a few seconds per document on the same storage medium

## Purpose

Execute a previously verified rename/move prefix for exactly one document, bound to plan, hash, and action, log it without gaps, and, if needed, revert it via a separate approval.

## Preconditions

- Source, profile rules, target root, and `as_of` match the verified plan.  
- The plan ID and each action ID to be approved were read from `documents plan` and deliberately selected.  
- Source and target reside on the same storage medium; cross-volume fallback is not allowed.  
- Local state folder and file write gates are explicitly chosen.  
- The approval does not apply to conversion, recycle bin, review, or blocked actions.

## Steps

1. **Recreate plan** — `documents execute` extracts the source again, resolves the same profile rules, and computes the full `plan_id`.  
2. **Bind approval** — `--approve-plan-id` and all repeated `--approve-action-id` must form a seamless executable plan prefix; `--approved-at` requires a time zone.  
3. **Verify source** — Document ID and SHA-256 must still match the original path.  
4. **Check entire target chain** — each target must be unoccupied, symlink‑free, and, according to the action type, within the allowed scope.  
5. **Write intent** — before the first file action, a new `000-intent.json` without raw text is published in the state folder.  
6. **Execute steps** — the transaction core creates the target without overwriting, verifies its hash, and only then removes the source.  
7. **Check completion** — `100-completed.json` displays the plan provider, executor, paths, hashes, rules, and storage evidence.  
8. **Optionally grant undo** — `documents undo` requires a completion file, execution ID, hash, new approval ID, timestamp, and write gate.  
9. **Verify undo** — target hash and intent must match; the original must not exist. Only then is the inverse move executed.

## Exit-Criteria

- [ ] Plan ID, source hash, and approved action IDs match exactly.  
- [ ] No existing target was overwritten or renamed.  
- [ ] Intent and completion report reside in the execution folder in append‑only mode.  
- [ ] The evidence contains root, relative path, profile, scope, and rules.  
- [ ] Plan provider and actual executor are listed separately.  
- [ ] Without a file write gate, no source was altered.  
- [ ] After a successful undo, the original content resides at the source and no longer at the final target.

## Pitfalls

- A plan ID is not the approval itself; concrete action IDs and the filesystem gate are additionally required.  
- File content changed after planning invalidates the approval.  
- FCSA confirms sorting semantics in the dry run but does not execute this exact single‑document move live. Therefore the report names the FolderHome transaction core as the executor.  
- Cross‑volume moves are not replaced by copy‑and‑delete.  
- Undo is not an overwrite: if the source reappears, it is blocked.

## Related

- [`./document-action-plan.md`](./document-action-plan.md) — generate plan and rule provenance  
- [`./directory-observation.md`](./directory-observation.md) — detect later user corrections based on the evidence  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑11 data flow  

## History

- **2026-08-21** — Created after Phase‑11 end‑to‑end roundtrip
