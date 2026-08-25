# Workflow: Safely hand over document appointment to calendar

**English** | [Deutsch](./calendar-handoff.de.md)

> **Last verified:** 2026-08-25  
> **Frequency:** for new or changed documents with appointment information  
> **Duration:** a few seconds per document folder

## Purpose

Check labeled appointment data from an explicitly selected document folder and, after exact approval, transfer it to the local FolderHome calendar or adopt it as new ICS files for UpToday.

## Preconditions

- Document folder, calendar configuration, profiles and separate state are defined.  
- The doc‑services revision matches the pinned manifest.  
- For `review_required` the local sensitive processing is explicitly permitted.  
- For ICS a dedicated, non‑overlapping output path is available.

## Steps

1. **Create plan** — execute `calendar plan` with source, profile, area, state, configuration and timezone timestamp.  
2. **Check evidence** — verify title, date, time, location, timezone, document hash and line numbers.  
3. **Check conflicts** — run `blocked` and do not skip unclear documents; existing identical local UIDs must be `noop`.  
4. **Create approval** — record schema, plan ID, calendar revision, desired action IDs, stable approval ID and timezone timestamp.  
5. **Rebuild plan** — start `calendar apply` with identical planning inputs and the approval file.  
6. **Release state** — set `--approve-state-write` only for the event and audit.  
7. **Release ICS separately** — only when using backend `uptoday_ics` additionally set `--approve-output-write`.  
8. **Check result** — read event ID or ICS path and hash against the report.  
9. **Query local calendar** — use `calendar list` by profile, area and optional date range.

## Optional ICS export through the chat executor

The connected chat endpoint can hand the recorded appointments back as one importable file. Pass `export_resource_id` and `export_basename` together; leave both out and nothing is exported.

- The output directory is a registry resource with purpose `calendar.export_output` and operation `create`; it must not overlap the source folder or the calendar state.  
- All approved appointments land in **one** RFC 5545 file, because that is what a phone or mail calendar imports in a single step.  
- The plan already carries `export_sha256`, so the exact file content is bound by the same confirmation hash as the state write.  
- The export never overwrites: an existing target file aborts the run, and a failed state write rolls the published file back. State and file are written together or not at all.  
- No connector is involved. FolderHome writes a local file; the user imports it into their calendar program by hand.  

## Exit criteria

- [ ] Plan, approval, calendar revision and source hash match.  
- [ ] Source documents remained byte‑identical.  
- [ ] Local events and audit were written together or not at all.  
- [ ] All ICS files have the planned hash; nothing was overwritten.  
- [ ] `connector_invoked` is `false`; an UpToday import was not claimed.  
- [ ] An optional export wrote exactly one file with the planned hash, or none.

## Pitfalls

- `--approve-sensitive-local-read` is not a calendar or network release.  
- A changed source, revision or existing target file invalidates the plan.  
- State, source and ICS output must not overlap.  
- Routinika and Google remain blocked until own verified connectors are available.  
- Appointment detection is best effort and does not guarantee completeness.

## Related

- [`../docs/phase17-calendar-reuse-and-plan.md`](../docs/phase17-calendar-reuse-and-plan.md)  
- [`./document-library.md`](./document-library.md) — local document extraction  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑17 data flow  

## History

- **2026-08-22** — Created after Phase‑17 end‑to‑end acceptance  
- **2026-08-25** — Optional registry-bound ICS export of the recorded appointments added
