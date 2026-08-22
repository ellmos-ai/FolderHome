# Workflow: Safely plan and simulate calendar connector

**English** | [Deutsch](./calendar-connectors.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** upon explicitly requested calendar handoff  
> **Duration:** planning takes a few seconds; a real connector run is not part of the acceptance

## Purpose

Generate a provider‑neutral connector plan for UpToday, Routinika, or Google from documented Phase‑17 appointment candidates and optionally test the flow without network against the synthetic provider.

## Preconditions

- Document folder, profile, area, and state folder are explicitly selected.  
- The account belongs to the profile and specifies a concrete calendar ID.  
- The configuration contains only a connector reference, no credentials.  
- Real calendar actions have a separate user approval outside this local workflow.

## Steps

1. **Inventory providers** — check revision, role, and live boundary.  

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome calendar connectors --json
   ```


2. **Create Phase‑17 handoff** — extract documents, profile fallback, verify timezone and evidence. This step remains read‑only.

3. **Generate connector plan** — load account and request; Google remains `review_required`, Routinika remains blocked and UpToday delegates to ICS.  

   ```powershell
   python -m folderhome calendar connector-plan `
     --source-dir examples\documents\calendar `
     --calendar-config examples\calendar\calendar-config-google.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-calendar-state" `
     --profile lukas --area gesundheit `
     --planned-at 2026-08-22T04:20:00+02:00 `
     --connector-accounts examples\calendar\connector-accounts.json `
     --connector-request examples\calendar\connector-request-google.json `
     --approve-sensitive-local-read --json
   ```


4. **Validate payload** — check calendar ID, solo participant list, time offset, end time, transparency, reminder, and source action reference.

5. **Simulate locally only** — the additional provider and execution switch makes the intent visible. No Google skill is invoked.  

   ```powershell
   python -m folderhome calendar connector-simulate `
     --source-dir examples\documents\calendar `
     --calendar-config examples\calendar\calendar-config-google.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-calendar-state" `
     --profile lukas --area gesundheit `
     --planned-at 2026-08-22T04:20:00+02:00 `
     --connector-accounts examples\calendar\connector-accounts.json `
     --connector-request examples\calendar\connector-request-google.json `
     --approve-sensitive-local-read --use-synthetic-provider `
     --approval-id calendar-demo `
     --approved-at 2026-08-22T04:21:00+02:00 `
     --approve-synthetic-calendar --json
   ```


6. **Validate report** — only `status=simulated`, `network_invoked=false` and `live_calendar_written=false` count as local acceptance.

## Exit-Criteria

- [ ] Account, profile, backend, and Phase‑17 handoff match.  
- [ ] Provider revision and profile rule source are visible.  
- [ ] Create, update, delete, and remind are modeled separately.  
- [ ] Google handoff contains explicit calendar ID and offset times.  
- [ ] Without an existing provider reference, update and delete remain blocked.  
- [ ] Without real user approval, neither network nor calendar were altered.

## Pitfalls

- An existing UpToday installation is not a live sync; FolderHome uses only the proven ICS file handoff.  
- A Routinika bundle is not a connector contract.  
- `primary` is an explicit Google calendar ID, not an implicit substitute for an unknown target.  
- A reminder in the event payload is not yet a proven delivery.  
- Update or delete without an existing provider event ID fails closed.  
- Recurring events later require an explicit scope decision.

## Related

- [`../docs/phase27-calendar-connector-plan.md`](../docs/phase27-calendar-connector-plan.md)  
- [`../skills/folderhome-calendar-connectors/SKILL.md`](../skills/folderhome-calendar-connectors/SKILL.md)  
- [`calendar-handoff.md`](calendar-handoff.md)

## History

- **2026-08-22** — UpToday, Routinika, and Google routes inventoried and synthetic no‑network flow locally accepted

---
