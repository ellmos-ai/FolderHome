# Workflow: Safely clean up a batch folder

**English** | [Deutsch](./folder-cleanup.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad-hoc, later as part of an observed routine  
> **Duration:** dependent on document count and extraction formats

## Purpose

Fully plan an explicitly selected folder, identify target conflicts across all documents, and then execute only a deliberately chosen subset with automatic rollback on partial failures.

## Preconditions

- Source folder, profile, area, target root, and `as_of` are explicitly selected.  
- Profiles and the pinned doc-services checkout have been verified.  
- The plan may read sources but must not modify either sources or targets.  
- A batch execution requires a separate approval file and the filesystem gate.

## Steps

1. **Capture folder** — deterministically sort relative paths; symlinks are visibly omitted.  
2. **Extract documents** — process known types read‑only via doc‑services; record unknown types and errors with hash and reason.  
3. **Create individual plans** — for each document use the same profile, plan, and provider contracts as with `documents plan`.  
4. **Validate targets collectively** — compare each intermediate and final target against all other plans and against the current file inventory.  
5. **Review batch plan** — `folders cleanup-plan` must display the batch ID, document status, conflicts, and executable action IDs without raw text.  
6. **Approve subset** — create an approval file containing the batch ID and, for each selected document, the document ID, hash, plan ID, and action IDs.  
7. **Execute batch** — `folders cleanup-execute` rebuilds the plan, fully validates the approval file, and first writes a batch intent.  
8. **Check individual audits** — each selected document uses the Phase‑11 executor and generates its own final report.  
9. **Validate batch completion** — only on complete success are active storage receipts collected; on partial failures earlier actions are rolled back.

## Exit-Criteria

- [ ] Each source file appears as `planned`, `blocked`, `noop`, `skipped`, or `failed`.  
- [ ] No source or target was modified during `cleanup-plan`.  
- [ ] Shared or existing targets are blocked before approval.  
- [ ] The approval file contains only deliberately selected documents.  
- [ ] Successful batches have an intent, a final report, and for each document a storage receipt.  
- [ ] After `rolled_back`, previously executed documents are back at their origins and there are no active batch storage receipts.

## Pitfalls

- A conflict‑free individual plan can still collide with another target or its source in the overall folder.  
- File name or processing order must not silently resolve a conflict.  
- An approval file becomes invalid as soon as the source, profile rule, or any plan‑relevant field changes.  
- `rolled_back` is an occupied error exit, not a successful batch.

## Related

- [`./document-action-plan.md`](./document-action-plan.md) — individual planning  
- [`./document-action-execution.md`](./document-action-execution.md) — single transaction and undo  
- [`./directory-observation.md`](./directory-observation.md) — observed states and corrective learning  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑12 data flow  

## History

- **2026-08-21** — created after Phase‑12 end‑to‑end acceptance
