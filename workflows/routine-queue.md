# Workflow: Evaluate Multiple Observation Routines Read-Only

**English** | [Deutsch](./routine-queue.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** on every scheduled or manual check run  
> **Duration:** depends on the number of watches and documents

## Purpose

Schedule all activated watches at a specific point in time, bundle comparable states, and detect conflicts across watch boundaries, without modifying files, checkpoints, or the operating system scheduler.

## Preconditions

- Watch, binding, and profile configurations are locally readable.
- Each active watch has at most one binding.
- Observation time, deadline, and state directory are explicit.
- The doc-services provider matches the pinned manifest.

## Steps

1. **Load watches** — validate IDs, roots, profile, scopes, and intervals.  
2. **Load bindings** — resolve target roots relative to the binding file and check the `changes`-/`full` mode.  
3. **Check mapping** — reject multiple and unknown bindings; visibly block missing or disabled bindings.  
4. **Plan individual routines** — for each active watch, generate the Phase-13 plan fully read-only.  
5. **Assign status** — classify results as `ready`, `not_due`, `empty`, or `blocked`.  
6. **Check total set** — block input overlaps, targets in other watch inputs, and shared action targets.  
7. **Output queue** — serialize deterministic ID, summary, and plan evidence to stdout.  
8. **Check side effects** — `side_effects=[]` and `scheduler_registered=false` must be preserved.

## Exit-Criteria

- [ ] Each active watch appears exactly once in the queue.  
- [ ] Missing bindings and cross‑watch conflicts are visibly blocked.  
- [ ] The queue contains no raw document text.  
- [ ] State, sources, and targets have remained byte‑ or path‑identical.  
- [ ] No operating system task has been registered.

## Pitfalls

- A `ready` entry is not a batch approval.  
- Two individually conflict‑free routines can use the same target.  
- A target in the input of another watch creates a later re‑entry loop.  
- Shell redirection or an external scheduler can have side effects itself; these are not part of the `routine-queue` contract.

## Related

- [`./folder-routine.md`](./folder-routine.md) — single observation routine  
- [`./folder-cleanup.md`](./folder-cleanup.md) — folder‑wide batch plan  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-14 data flow

## History

- **2026-08-21** — Created after Phase-14 end‑to‑end acceptance
