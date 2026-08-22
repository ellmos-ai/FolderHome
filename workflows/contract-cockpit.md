# Workflow — Insurance and Contract Cockpit

**English** | [Deutsch](./contract-cockpit.de.md)

## Purpose

Answer a request such as “What is my latest car insurance for my Hyundai i10?” as a read‑only overview. The cockpit combines existing document versions, contact registers, recurring costs, calendar events, and bank statement coverage. Missing evidence remains visible.

## Synthetic Run

```powershell
$env:PYTHONPATH = "src"
$demoState = Join-Path $env:TEMP "folderhome-contract-demo"

python -m folderhome documents ingest `
  --source-dir examples\contracts\documents `
  --state-dir $demoState `
  --approve-index-write --json

python -m folderhome contracts cockpit `
  --request-file examples\contracts\cockpit-hyundai-i10.json `
  --state-dir $demoState `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read `
  --output-markdown "$env:TEMP\FolderHome-Vertragscockpit.md" `
  --output-json "$env:TEMP\FolderHome-Vertragscockpit.json" `
  --json
```


If the same state was previously populated via the approved contact, finance, or calendar workflows, matching entries appear additionally. The cockpit does not generate these states itself.

## Explicit Mapping

The request declares:

- Document search request and contract object
- Counterparty terms for cost candidates
- Terms for calendar events
- Account identifiers and desired coverage period
- whether older versions should appear as archival candidates

No fuzzy or LLM‑based linking is performed silently.

## Security Boundaries

- Without a sensitivity approval, no document, contact, finance, or calendar state is read.
- The cockpit run does not modify the shared state.
- Archiving suggestions remain unapproved and are not executed.
- Contacts are not switched or deleted.
- Appointments are not created and messages are not sent.
- Costs are documented candidates or projections; contract status, coverage, termination, and future debits are not proven.
- Bank statement gaps remain visible; balances are not interpolated.
- JSON contains no extracted document raw text.

---
