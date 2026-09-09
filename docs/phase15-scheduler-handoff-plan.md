# Phase 15: Portable Scheduler Handoff

**English** | [Deutsch](./phase15-scheduler-handoff-plan.de.md)

**As of:** 2026-09-09  
**Status:** handoff and runner implemented; registration integration remains open

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

- Before operational writes, the runner reconstructs the complete handoff,
  compares it and retains an independent snapshot. The state gate must be the
  boolean `true`, and intervals must be whole minutes.
- Existing redirects in the lock/report directories are rejected; report paths
  are rechecked after extraction and timestamp filenames are normalized. Cleanup
  preserves replaced owners and removes only the runner's own lock. A failed
  audit write never yields a claimed `completed_file`.
- These checks do not create an isolation boundary against malicious code or
  concurrent filesystem tampering within the same operating-system account.
  The handoff binds configuration paths, not later changes to their contents;
  persistent registration needs a separate content-bound approval.
- No installation or registration of an operating‑system scheduler.  
- No automatic batch release and no document action.  
- No checkpoint writing by the scheduler run.  
- No automatic removal of foreign or orphaned locks.  
- Absolute paths are stored as individual `argv` elements, not as a combined shell command.  
- The schedule binds watch, binding, profile, state, and provider paths into a deterministic schedule ID.

## Use Cases

### Registration extension in progress

The private Python planning boundary in `application.scheduler_registration`
now binds the complete handoff, scheduler checkout revision, store/ledger paths,
the resolved watch/binding directories, and the membership and SHA-256 content
of watch, binding, profile and component manifest files. Revalidation rejects
drift, including retargeted directory links; new documents inside an approved
watch do not invalidate this configuration snapshot. Planning creates no store,
ledger, or consumer. The shared provider loader supports pinned `src` layouts
and rejects preloaded foreign modules throughout the named package family.

The private `register_scheduler_job` API now requires the exact plan ID and a
separate boolean write approval. It publishes an immutable attempt record before
opening the provider store, inserts one deterministic job through the pinned
`ellmos-scheduler` 0.3.1 API, then checks the stored definition and due time.
Registration does **not** start a consumer; `consumer_status` remains
`not_observed`. Store, ledger and runner outputs cannot be inside watched inputs.

Repeated confirmations only read back the same job. A lost response after a
committed insert can be reconciled; an absent job after an earlier attempt stays
`uncertain`, with no automatic second insert. Unknown existing databases and
orphaned SQLite companion files are preserved, not initialized or migrated.
Each later observation gets its own immutable receipt. Failing to persist the
result is reported as uncertain even when the job might already exist.

Due-time verification reads the job and run history in one transaction. It
accepts provider-evidenced interval progression and abandoned retry slots, not
arbitrary manual rescheduling. These are cooperative-process safeguards, not
protection against malicious code with the same operating-system permissions.

The confirmation adapter, limited consumer, resource setup and app/CLI wiring
remain under development. The existing `scheduler plan/run` behavior and the
public capability catalog are unchanged. Integration tests use temporary stores
and require the clean pinned scheduler checkout; no real user job is registered.

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
