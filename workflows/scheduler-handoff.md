# Workflow: Prepare a read‑only queue for a scheduler

**English** | [Deutsch](./scheduler-handoff.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** once per schedule and when configuration changes  
> **Duration:** plan under one second; runtime depends on document count

## Purpose

Create a portable invocation and a Windows‑task artifact and safely coordinate a headless queue run without registering an operating‑system task or performing document actions.

## Preconditions

- Watch, binding, profile, state, and provider paths are explicit.  
- Task name, interval, IANA time zone, and start time are defined.  
- The scheduler‑state gate is granted for a real queue run.  
- A later installation requires a separate user decision.

## Steps

1. **Plan handoff** — invoke `scheduler plan` with all paths and the schedule.  
2. **Verify identity** — check schedule ID, task name, start time, interval, and time zone.  
3. **Check artifacts** — verify portable `argv` list and Windows XML against local paths, `LeastPrivilege`, `IgnoreNew`, and runtime limit.  
4. **Check non‑registration** — confirm `registration_performed=false`, `installation_supported=false`, and missing installation commands.  
5. **Start headless run** — invoke `scheduler run` only with the same schedule ID and the tight scheduler‑state gate.  
6. **Check lock** — an existing lock must return exit code 30 and remain untouched.  
7. **Check queue** — trace `idle`/0, `attention`/10, or `blocked`/20 based on the serialized queue content.  
8. **Check completion** — append‑only report present, own lock removed, documents, targets, and checkpoints unchanged.

## Exit‑Criteria

- [ ] The handoff was only output and not installed.  
- [ ] The schedule ID matches the newly created plan during the run.  
- [ ] The run report documents queue, status, and exit code.  
- [ ] An existing lock was not removed or overwritten.  
- [ ] There were no document, target, or checkpoint changes.

## Pitfalls

- An XML artifact is not yet a registered Windows task.  
- Exit code 10 indicates human approval is required, not a technical error.  
- A residual lock must not be automatically deleted based on its age.  
- The state gate does not grant batch or file release.  
- Installation remains separate even if the XML is syntactically correct.

## Related

- [`./routine-queue.md`](./routine-queue.md) — read‑only multi‑watch queue  
- [`./folder-routine.md`](./folder-routine.md) — approval‑required execution  
- [`../docs/phase15-scheduler-handoff-plan.md`](../docs/phase15-scheduler-handoff-plan.md)  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑15 data flow

## History

- **2026-08-21** — Created after Phase‑15 end‑to‑end acceptance
