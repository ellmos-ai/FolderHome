# Synthetic Mail Configuration

**English** | [Deutsch](./README.de.md)

The examples contain only reserved `example.invalid` addresses and Secret references. No credentials are stored and no real mailboxes are accessed.

The standard plan checks the revision‑accurate UniversalDocsGrabber checkout and remains blocked when the checkout is missing, deviating, or altered:

```powershell
python -m folderhome mail ingest-plan `
  --accounts-file examples/mail/accounts.json `
  --request-file examples/mail/ingest-request.json `
  --profiles-dir examples/profiles `
  --approve-sensitive-local-read --json
```


For local testing the same plan can be approved without network using `--use-synthetic-provider`. This plan also does not call any provider yet. Mailbox deletion, moving, and sending are not ingest operations.

---
