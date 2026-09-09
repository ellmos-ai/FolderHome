# Phase 15: Portable Scheduler Handoff

**English** | [Deutsch](./phase15-scheduler-handoff-plan.de.md)

**As of:** 2026-09-09  
**Status:** handoff, runner and gated app registration implemented; consumer setup remains open

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

The private `application.scheduler_consumer.create_scheduler_consumer` API now
constructs a **stopped**, single-job consumer after separate exact-plan approval.
An explicit `tick()` checks one due job; explicit `serve()` reuses the provider's
polling loop. Registration and construction never start either operation.
Each claim revalidates the configuration and stored job; the isolated executor
registry cannot run arbitrary shell jobs or claim other jobs in the same store.

The queue runs in a bounded child process pinned to this FolderHome installation,
including when the working directory contains another checkout. Exit 0 or 10 is
accepted only with a matching structured queue report, its persisted file, and
a fresh invocation ID bound to its own immutable receipt. An old valid report
cannot establish a new run. Timeouts and missing evidence are not success; a
failed observation write is marked `uncertain` separately from the run result.
Documents remain unchanged, and no checkpoint or cleanup action is released.

The `scheduler-handoff` adapter is connected in the normal app/agent/recipe
factory when a private `scheduler.store` resource is configured. The startup
flag `--approve-scheduler-write` and a separate exact plan confirmation are both
required for registration. A launch file cannot grant the startup flag. The
result distinguishes registered from consumer observed; no daemon starts.

The request contains resource IDs, task name, interval, start time, timezone and
`allow_sensitive_local_read=true`, never arbitrary paths or executables. See the
[synthetic request](../examples/observation/scheduler-request.json). Declare these
resources in the existing private resource registry:

| Request field / directory | Purpose | Kind | Required operations |
|---|---|---|---|
| `watches_resource_id` | `scheduler.watches` | file | read |
| `bindings_resource_id` | `scheduler.bindings` | file | read |
| `store_resource_id` | `scheduler.store` | sqlite_store | read, state_write |
| `ledger_resource_id` | `scheduler.ledger` | directory | read, state_write |
| `state_resource_id` | `scheduler.state` | directory | read, state_write |
| Every enabled watch source | `routine_queue.source` | directory | read, sensitive_read, list |
| Every enabled binding target | `routine_queue.target` | directory | read, list |

Each active watch must belong to the requested profile and match an explicitly
registered source/target. Directories must already exist when loading the
registry. The app binds the exact registry file bytes into the registration
plan and rereads authority before confirmation. Later changes invalidate the
consumer before another claim. Earlier private proposals require a new preview.
An uncertain provider response remains explicitly unknown in ordinary HTTP and
recipe confirmation; it is never presented as proof that no job was written.

The Setup UI prepares the private resources without registering or starting a job.
The normal EN/DE UI provides consumer preview, separate start confirmation,
status refresh and stop. Changing profile invalidates the visible preview.
The existing `scheduler plan/run` behavior is unchanged. Tests use temporary stores
and require the clean pinned scheduler checkout; no real user job is registered.

### Process-owned consumer control API

The normal app resolves exactly one `scheduler.request` file for the selected
profile, using the saved Setup request and the existing registration validator.
Starting requires `--approve-scheduler-consumer` at app launch **and** a separate
confirmation of the current preview. `--approve-scheduler-write` alone is not enough.
Neither flag automatically starts a worker; a matching registration must already exist.

| Endpoint | Method | Request |
|---|---|---|
| `/api/v1/scheduler/status` | GET | Exactly one `profile_id` query parameter |
| `/api/v1/scheduler/preview` | POST | `schema`, `profile_id` |
| `/api/v1/scheduler/start` | POST | `schema`, `profile_id`, `plan_id`, `plan_sha256` |
| `/api/v1/scheduler/stop` | POST | `schema`, `profile_id`, `worker_id` |

POST schemas are `folderhome.scheduler-consumer-<action>-request.v1`.
Use the existing session-token header and same-origin JSON request boundary.
Caller-supplied paths, commands and extra fields are rejected. Start rereads the
saved request and resource authority; changed plans and reused confirmations fail.
Preview does not inspect the job database (`registration_checked: false`);
the exact registered job is validated at start, without creating a missing job.

Status describes **this app instance only**; other instances remain `not_observed`.
Stop accepts only this instance's worker ID, signals its existing provider loop,
and reports `stopping` until the current bounded check drains. App/server close
signals all owned workers too. A running check is not force-killed and may outlive
the short close wait; no detached service or OS task is installed. Document actions
remain unauthorized. Browser acceptance and package-wide final verification are pending.

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
