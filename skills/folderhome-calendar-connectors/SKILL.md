---
name: folderhome-calendar-connectors
description: Plan FolderHome calendar handoffs from evidenced document-derived appointments, route them to UpToday, Routinika, or Google, and verify them against a synthetic provider without using a live calendar.
---

# FolderHome Calendar Connectors

**English** | [Deutsch](./SKILL.de.md)

Start with the revision‑accurate provider inventory:

```powershell
python -m folderhome calendar connectors --json
```


Build each connector plan on the existing Phase‑17 calendar handoff.  
Never generate a second document, profile, timezone, or  
duplicate logic in parallel.

```powershell
python -m folderhome calendar connector-plan `
  --source-dir <documents-dir> `
  --calendar-config <calendar-config.json> `
  --profiles-dir <profiles-dir> --state-dir <state-dir> `
  --profile <profile-id> --area <area> --planned-at <timestamp-with-offset> `
  --connector-accounts <calendar-accounts.json> `
  --connector-request <connector-request.json> `
  --approve-sensitive-local-read --json
```


## Binding Limits

- Configurations may contain only `connector://` references, never tokens, passwords, or cookies.  
- Account, profile, backend, and Phase‑17 handoff must match exactly.  
- A plan does not invoke any connector and does not write to a calendar.  
- UpToday creation remains at the existing ICS handoff; it is not a live sync.  
- Routinika remains blocked without a verified live contract.  
- A Google handoff requires an explicit `calendar_id`, `attendees=[]`, `transparency=opaque`, offset times, and explicit reminders.  
- Update and delete operations first require an existing provider event reference. For recurring events, a master or single instance must later be selected as well.  
- The synthetic provider requires `--use-synthetic-provider` and `--approve-synthetic-calendar`. It only demonstrates the flow without network and without a real calendar entry.  
- Appointment detection and reminder delivery have no completeness guarantee.

For a real Google run, pass the verified payload to the `google-calendar` skill only after a separate user approval. First repeat the validation of calendar ID, event time, reminders, participants, and operation scope. A `review_required` plan is not an execution approval.

---
