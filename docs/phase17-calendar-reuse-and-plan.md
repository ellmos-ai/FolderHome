# Phase 17: Calendar Reuse and Blueprint

**English** | [Deutsch](./phase17-calendar-reuse-and-plan.de.md)

**As of:** 2026-08-22  
**Status:** candidates, planning and approved local/ICS execution completed

The final state has been locally accepted with 159 FolderHome tests. Planning remains read‑only. Execution requires an exact Approval file and a State Gate; ICS additionally requires an Output Gate. Neither UpToday nor any other external connector is invoked.

## User Goal

FolderHome shall capture date and appointment information from explicitly selected documents as verifiable candidates. Which calendar is used should be determined via a global configuration and optionally via profile rules. Detection is best‑effort and must not claim completeness nor modify a calendar without its own approval.

## Reuse Evaluation

### Source Skill `assist/kalender` 0.1.0

- The MIT‑licensed skill already defines the correct selection principle: a local SQLite calendar as well as optional back‑ends for Google, Routinika, and UpToday via a user preference.  
- Its Python core implements only the local store. UpToday and Routinika are explicitly marked as “not implemented” in the skill.  
- The core is not a safe direct runtime dependency for FolderHome: it has no Git pin, creates the store alongside the skill, generates random IDs, opens the database in write mode even for read accesses, and allows immediate hard‑delete without a plan, hash, or approval contract.  
- Therefore, the backend selection, local base fields, and the ICS concept are reused, not the core as a writing adapter.

### UpToday, Revision `7582ca87e17e458bb99a7379d2c54003c15415a4`

- The local checkout was clean during the inventory, has no configured remote, and is under the MIT license.  
- UpToday implements a file‑based RFC‑5545 channel without cloud sync. Imported ICS sources are not written back; UIDs and content hashes prevent duplicates and enable local updates.  
- `build_ics` and the atomic file export are useful references. However, the direct import modifies the UpToday database and is not a stable FolderHome connector contract.  
- Phase 17 therefore initially plans its own deterministic ICS handoff. A later UpToday import remains a separately approved adapter action.

### Routinika/RoutineMaster

- No standalone extracted Routinika connector and no implemented skill backend path were found.  
- UpToday contains only a “deprecated / unused” marked RoutineMaster bridge. It searches old local paths and does not open SQLite read‑only; its own header requires retrofitting before reactivation.  
- The backend remains selectable in the contract, but only up to a versioned, verified adapter visible as `blocked`.

### TerminPilot and Google Calendar

- TerminPilot coordinates multi‑person polls and is not a personal calendar. Its checkout also contains foreign, uncommitted changes; FolderHome does not read it further and does not modify it.  
- Google Calendar is an external connector with its own data‑privacy and network boundary. It does not belong in the local Phase‑17 standard path.

## Declarative Document Format V1

V1 evaluates only uniquely labeled single lines:

```text
Termin: Kontrolltermin
Datum: 2026-09-14
Uhrzeit: 10:30
Ende: 11:00
Ort: Praxis Beispiel
Zeitzone: Europe/Berlin
```


Title and date are required. A missing time results in an all‑day appointment; a missing end time is not replaced by an invented duration. Ambiguous values, invalid timestamps, or an unknown time zone generate `review_required` instead of an executable candidate.

## Configuration and Profile Resolution

1. `folderhome.calendar-config.v1` sets `default_backend` and `default_timezone` for the current OS account.  
2. The existing profile inheritance receives `calendar.backend` and `calendar.timezone` as typed rules.  
3. Profile rules override the general fallback according to the same fixed order: global → domain → profile → profile domain.  
4. Supported values are initially `folderhome_local`, `uptoday_ics`, `routinika`, and `google`; only the first two can lead to a local plan in Phase 17.  
5. The synthetic example fallback is `uptoday_ics`, as requested by the user. This creates only a handoff artifact and imports nothing.

## Candidate and Action Contract

1. Each candidate binds profile, domain, title, date/time, time zone, location, document ID, source hash, path, and line evidence.  
2. A stable UID is derived from the candidate content and document identity; random IDs are excluded.  
3. Planning remains read‑only and lists backend, provider status, target type, side‑effects, conflicts, and required gates.  
4. `folderhome_local` plans an entry in the encapsulated local calendar store.  
5. `uptoday_ics` plans a new never‑overwrite ICS file with a deterministic UID; UpToday import is not part of the same approval.  
6. `routinika` and `google` remain blocked until a dedicated pinned connector contract and its data‑privacy/network approval are available.  
7. Before each execution, the plan ID, source hash, calendar revision, target conflict, and approval are re‑checked.  
8. Appointment detection is explicitly not complete; omitted or ambiguous documents remain visible in the analysis report.

## Execution Boundary

1. `folderhome.calendar-handoff-approval.v1` binds a stable approval to the plan ID, calendar revision, concrete action IDs, and a timestamp with time zone.  
2. Each execution writes an append‑only audit. Therefore, both the local calendar and the ICS handoff require `--approve-state-write`.  
3. The local store writes selected events and audit rows in a SQLite transaction. It provides no delete operation.  
4. ICS additionally requires `--approve-output-write`. All files are first hashed, then published via never‑overwrite, and read again.  
5. If a later element of the batch fails, FolderHome removes already published files only if the path and hash still match its own execution record.  
6. The result reports, per action, the event ID or output path/hash and the available rollback path. An UpToday import remains a separate operation.

## Usecases

### USECASE 017-1: Detect Appointment from Document

- **Input:** Synthetic document with title, date, time, and location.  
- **Expectation:** Evidence‑bound candidate; no calendar or file writing.

### USECASE 017-2: Resolve Profile Backend

- **Input:** Fallback `uptoday_ics`, profile rule `folderhome_local`.  
- **Expectation:** Profile rule wins with full rule provenance.

### USECASE 017-3: Plan UpToday Handoff

- **Input:** Unambiguous candidate and `uptoday_ics`.  
- **Expectation:** Deterministic ICS preview and target path; no import and no modification of the UpToday database.

### USECASE 017-4: Block Missing Routinika Backend

- **Input:** Profile rule `routinika`.  
- **Expectation:** Visible blocked plan with missing provider revision; no silent fallback to another calendar.

### USECASE 017-5: Adopt Local Appointment with Approval

- **Input:** Unambiguous candidate, current calendar state, exact Approval file and State Gate.  
- **Expectation:** An active event and an audit row in the same transaction; identical replanning will be `noop`.

### USECASE 017-6: Safely Publish Multiple ICS Files

- **Input:** Two unambiguous candidates as well as State and Output Gates.  
- **Expectation:** Both files have the planned hash. A synthetic error in file two removes file one again and leaves no audit.
