# Workflow: Securely read, assign, and approve Mail

**English** | [Deutsch](./mail-connector.de.md)

> **Last verified:** 2026-08-25  
> **Frequency:** when mail fetch or draft placement is explicitly triggered  
> **Duration:** plan under one second; provider runtime depends on mailbox  

## Purpose

Plan a mailbox fetch without changing the mailbox, adopt incoming message references in a provider‑neutral way, and place one prepared letter as a draft into the user's own mailbox — never as a delivery to a third party.

## Preconditions

- Mail account contains only secret references and belongs to the selected profile.  
- Mailbox, search query, and attachment target have been explicitly selected.  
- For a draft, an active contact and an unchanged correspondence preview are available.  
- Real network actions require a separate approval.  

## Draft placement through the chat executor

The connected endpoint is draft-only. It renders exactly one correspondence preview into an RFC 5322 message and appends it to the configured drafts folder of the user's own IMAP mailbox. There is no SMTP path in this endpoint, so no recipient is contacted.

1. **Declare the mailbox in the private registry** — one `file` resource with purpose `mail.draft_account` that points at a `folderhome.mail-draft-account.v1` document. Template: [`../examples/mail/draft-account.example.json`](../examples/mail/draft-account.example.json). The document carries host, port, username, the ASCII IMAP drafts folder and `password_file`, an absolute path to a local file holding the password. The password value never appears in a plan, a report, the chat or the repository.  

2. **Prepare** — the executor resolves the mailbox, the letter request, the designs and the templates by logical resource ID, rebuilds the correspondence preview and renders one deterministic draft. The plan discloses subject and hashes, never the body, the recipient address, the host or the password location.  

3. **Approve exactly once** — `/confirm <plan_id>` executes the prepared, hash-bound envelope one single time.  

4. **Live-effect gate** — without `--approve-mail-draft` the endpoint plans but refuses to touch the mailbox. With the gate the transport reads the password from its configured file, appends the message with the `\Draft` flag and logs out.  

5. **Ledger** — a local SQLite ledger reserves the deterministic idempotency key before the append and records `drafted` or `failed`. The same draft cannot be appended to the same mailbox twice.  

Attachments are refused fail-closed in this version: the draft carries text only, and enclosures named in the letter must be attached by hand before sending. Without a declared `mail.draft_account` resource the endpoint stays honestly `not_connected`.

## Steps

1. **Inventory providers** — Distinguish Launcher, IMAP ingest, Cleaner, invoice archive, and synthetic gateway from each other.  

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome mail providers --json
   ```
  

2. **Read configuration** — only after approval; embedded passwords and unknown fields are blocked.  

3. **Create read‑only plan** — Verify provider revision, account, folder, search, and maximum count. A blocked checkout terminates the run.  

   ```powershell
   python -m folderhome mail ingest-plan `
     --accounts-file examples\mail\accounts.json `
     --request-file examples\mail\ingest-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```
  

4. **Release ingest precisely** — Bind plan ID and plan hash. Allow network reads and local writing of attachments separately. The gateway must guarantee `read_only_ingest=true`.  

5. **Explicitly bind recipient** — Active contact ID and email address must match the profile assignment and the recipient of the letter preview.  

6. **Validate draft** — Fully verify subject, sender, recipient, letter text, attachments, and hashes. A preview does not trigger any transport.  

7. **Approve sending separately** — Confirm draft ID, draft hash, exact recipient, and deterministic idempotency key. For a real gateway also allow network transmission.  

8. **Check ledger** — Read status `simulated` or `sent` and transport ID. The same approval or the same idempotency key must not be used a second time.  

## Exit-Criteria

- [ ] Account and profile match; no credentials are present in the JSON.  
- [ ] Ingest contains no move, delete, flag, or send operation.  
- [ ] Provider revision and checkout status are visible.  
- [ ] Contact and correspondence are exact and explicitly bound.  
- [ ] Send approval and ledger prevent a repeat run.  
- [ ] Without a real user gate, neither network nor email was triggered.  
- [ ] The draft endpoint appended at most one message and sent nothing.  
- [ ] Password, host and password location stayed out of plan, report and chat.  

## Pitfalls

- MailProcessor launches other programs but does not itself perform an IMAP fetch for FolderHome.  
- An existing UniversalDocsGrabber folder is not evidence of a clean, appropriate revision.  
- UniversalMailCleaner must not be treated as a read‑only ingest gateway due to delete/move functionalities.  
- `simulated` explicitly means that no email was sent.  
- `reserved` after an abort is a verification state, not an invitation to automatically retry.  

## Related

- [`../docs/phase26-mail-connector-plan.md`](../docs/phase26-mail-connector-plan.md)  
- [`../skills/folderhome-mail-assistant/SKILL.md`](../skills/folderhome-mail-assistant/SKILL.md)  

## History

- **2026-08-22** — Provider inventory, read‑only ingest, and synthetic draft/sending flow first approved locally  
- **2026-08-25** — Draft-only IMAP endpoint connected to the chat executor behind `--approve-mail-draft`; no send path added  

---
