# Phase 15: Portable Scheduler Handoff

**English** | [Deutsch](./phase15-scheduler-handoff-plan.de.md)

**As of:** 2026-08-21  
**Status:** implemented and accepted with 133 FolderHome tests

## User Goal

FolderHome shall be able to regularly check the read‑only routine queue headlessly, without independently registering a Windows task or releasing file actions during planning.

## Functional Contract

1. `scheduler plan` generates a deterministic handoff with schedule, portable argument list, and Windows task XML exclusively on stdout.  
2. The plan includes `registration_performed=false` and contains no installation or `schtasks /Create` call.  
3. `scheduler run` loads the same watch, binding, and profile contracts and creates exactly one read‑only multi‑watch queue.  
4. A run requires an explicit gate to write only operational scheduler state and an append‑only run report.  
5. A schedule‑specific lock prevents concurrent runs. It does not lock observed folders or user documents.  
6. An existing lock is not automatically removed or taken over; the run ends fail‑closed as `already_running`.  
7. The lock is removed again after its own completed run.  
8. Exit codes differentiate `idle`, `attention`, `blocked`, `already_running`, and invalid inputs.

## Exitcodes

| Code | Meaning |
|---:|---|
| 0 | Queue contains neither releasable nor blocked entries |
| 10 | At least one queue entry is `ready` and requires human release |
| 20 | At least one entry or the queue run is `blocked`/`failed` |
| 30 | The same schedule is already running or left an unresolved lock |
| 2 | CLI input or configuration is invalid |

## Safety Boundaries

- No installation or registration of an operating‑system scheduler.  
- No automatic batch release and no document action.  
- No checkpoint writing by the scheduler run.  
- No automatic removal of foreign or orphaned locks.  
- Absolute paths are stored as individual `argv` elements, not as a combined shell command.  
- The schedule binds watch, binding, profile, state, and provider paths into a deterministic schedule ID.

## Use Cases

### USECASE 015-1: Verify Installation‑Free Handoff

- **Precondition:** Synthetic configuration paths and explicit start time.  
- **Input:** Interval, time zone, task name, and local paths.  
- **Expectation:** Portable `argv`, Windows XML, stable ID, and no file writing.

### USECASE 015-2: Headless Queue Run

- **Precondition:** An active synthetic watch and a free scheduler lock.  
- **Input:** Handoff, explicit runtime, and scheduler‑state gate.  
- **Expectation:** Queue report, exit code 10 on `ready`, released lock, unchanged documents, and no target folders.

### USECASE 015-3: Block Concurrent Run

- **Precondition:** Schedule‑specific lock already exists.  
- **Input:** The same handoff.  
- **Expectation:** Exit code 30, no queue run, no takeover or deletion of the existing lock.
