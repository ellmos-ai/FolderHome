# Workflow: Medication Plan and Confirmed Intake

**English** | [Deutsch](./medication-intake.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** according to an explicitly provided plan or an intake confirmation  
> **Duration:** a few seconds  

## Purpose

Adopt a provided medication plan locally and evidence‑based, read the organizational daily view, and confirm an explicit intake as a separate append‑only event.

## Preconditions

- Plan folder and separate FolderHome state are defined.  
- Profile and doc‑services PIN are valid.  
- Each input file conforms to the declarative V1 format.  
- The data are explicitly provided; FolderHome does not verify medical correctness.

## Steps

1. **Create plan** — Execute `medication plan` with source, state, profile and `--approve-sensitive-local-read`.  
2. **Check evidence** — Verify medication, documented dose/unit, time, timezone, weekdays, validity, inventory reference, document hash, and line numbers.  
3. **Check for conflicts** — Do not override contradictory versions with the same start and time.  
4. **Create import approval** — Record plan ID, medication revision, specific action IDs, approval ID, and timezone timestamp.  
5. **Adopt schedule** — Execute `medication apply` with identical inputs, approval file and `--approve-state-write`.  
6. **Read daily view** — Execute `medication day` with date and explicit evaluation timestamp. Optionally, a FolderHome inventory state can be checked only against existing inventory evidence.  
7. **Select dose** — Use only the stable dose ID from this daily view.  
8. **Create confirmation** — Record confirmation ID, current medication revision, dose ID, schedule ID, planned day, and actual confirmation timestamp in `folderhome.medication-intake-confirmation.v1`.  
9. **Confirm intake** — Execute `medication confirm` with confirmation file and `--approve-state-write`.  
10. **Check history** — `medication history` must show the schedule and exactly one intake event; the inventory state remains unchanged.

## Exit-Criteria

- [ ] Plan, approval, medication revision, and source hashes match.  
- [ ] Schedule version and audit were added together or not at all.  
- [ ] Daily view did not write any state.  
- [ ] Confirmation is bound to dose, schedule, day, and revision.  
- [ ] A repeat does not create a second intake event.  
- [ ] No inventory and no source were altered.

## Pitfalls

- FolderHome does not decide a dose and does not check interactions.  
- “Confirmation pending” is an organizational status indicator, not a medical warning or statement about actual intake.  
- `bei Bedarf` is not automatically terminated in V1.  
- No reminders, messages, calendar actions, or orders are triggered.  
- Profiles are not an access boundary within the same operating system account.

## Related

- [`../docs/phase21-medication-intake-reuse-and-plan.md`](../docs/phase21-medication-intake-reuse-and-plan.md)  
- [`./inventory-import.md`](./inventory-import.md) — local household inventory  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑21 data flow  

## History

- **2026-08-22** — Created after Phase‑21 end‑to‑end implementation
