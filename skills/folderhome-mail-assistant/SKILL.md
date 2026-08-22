---
name: folderhome-mail-assistant
description: Plan FolderHome mail fetches read-only, explicitly associate a letter with an active contact, and prepare an exactly approved, idempotent send.
---

# FolderHome Mail Assistant

**English** | [Deutsch](./SKILL.de.md)

Start with the revision-accurate provider inventory:

```powershell
python -m folderhome mail providers --json
```


Then generate an ingest plan. The plan does not read any mailbox yet and does not execute any provider:

```powershell
python -m folderhome mail ingest-plan `
  --accounts-file <mail-accounts.json> `
  --request-file <mail-ingest-request.json> `
  --profiles-dir <profiles-dir> `
  --approve-sensitive-local-read `
  --json
```


## Binding limits

- Store only `keyring://`, `env://` or synthetic secret references, never passwords or tokens in a configuration file.
- An ingest plan contains only `fetch_headers` and optionally `fetch_attachments`. Moving, deleting, flagging, and sending are separate capabilities.
- Use a draft only when the profile, account, active contact ID, recipient address, correspondence preview ID, and text hash match exactly.
- Preview does not mean sending. A send approval binds the draft ID, draft hash, recipient, and idempotency key.
- Real network read and send actions each require a separate user gate. The synthetic gateway only demonstrates the flow without network and without a real email.
- A reserved send approval is not automatically repeated. An unclear aborted run must be checked in the ledger.

UniversalDocsGrabber remains the designated IMAP document provider. Load it only at the clean revision specified in the plan. UniversalMailCleaner stays outside the read-only ingest due to its mailbox mutations. MailProcessor is a launcher, not a runtime connector. The local SMTP seam has, in phase 26, exclusively a synthetic provider.

---
