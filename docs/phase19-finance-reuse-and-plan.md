# Phase 19: Bank Statements, Virtual Accounts and Subscriptions

**English** | [Deutsch](./phase19-finance-reuse-and-plan.de.md)

**As of:** 2026-08-22  
**Status:** Financial core, Approval import, coverage and cost candidates completed

## User Goal

From explicitly provided bank statements, FolderHome shall reconstruct a local virtual account: documented transactions, opening/closing balances, and covered periods. Gaps must remain visible. Recurring charges shall appear as audit‑required subscription, insurance, or other cost candidates with monthly/annual totals and a cautious forecast.

## Reuse Verification

### Document pipeline

- The pinned `doc-services` bridge already provides text, document ID, source hash, extraction provenance, and privacy status for TXT, PDF, and other formats.
- Therefore FolderHome does not build a second PDF/OCR or privacy path. Phase 19 processes exclusively the already normalized `DocumentRecord` and re‑verifies the source hash before writing.

### Tax Assistant, revision `5d39aeec98bf0a5734bf07dc35a58aa9e1331309`

- The clean MIT checkout is extracted from BACH and occupies a local SQLite store, integer‑cent amounts, data‑sparing CLI output, and a never‑overwrite export.
- Its runtime is technically a self‑categorized private tax worksheet for evidence. It does not import bank statements, reconstruct balances, or detect subscriptions.
- Reused are cent‑level accuracy, local storage, and privacy‑by‑default as architectural principles. The tax‑specific data model is not copied or repurposed for bank transactions.

### Subscription Tracker and Bank Statement Parser

- No published subscription tracker or provider‑neutral bank‑statement parser was found in the already extracted local modules, bundles, stacks, connectors, and skills.
- This gap will be encapsulated as a new reusable core under `folderhome.capabilities.finance_store`. No additional BACH extraction occurs.

## Declarative Statement Format V1

The first synthetic path reads clearly labeled lines:

```text
Kontokennung: giro-lukas
Institut: Beispielbank
Konto-Endung: 1234
Zeitraum: 2026-06-01 | 2026-06-30
Anfangssaldo: 150000 | EUR
Endsaldo: 148701 | EUR
Buchung: 2026-06-05 | -1299 | StreamFlix | abo | tx-juni-stream
```


Amounts are integer cents, never binary floating‑point numbers. V1 supports only EUR. Each transaction requires a unique reference originating from the statement. Free‑form bank formats are not guessed; unclear documents remain `review_required` and can later be supplemented via format‑specific adapters.

## Contracts and Safety Boundaries

1. A statement binds account identifier, institution, masked account suffix, period, balances, and transactions to the document ID, source hash, path, and line evidence.
2. Opening balance plus all transactions must exactly match the closing balance. Deviations are not silently compensated.
3. A plan ID binds new statements and transactions to the current financial revision. Overlapping periods are allowed, but duplicate transaction references only when the content is identical.
4. State writes require an approval file, concrete action IDs, and `--approve-state-write`. Sources and revision are re‑checked beforehand.
5. The SQLite store adds accounts, statements, transactions, and an append‑only audit in a single transaction. It has no delete or banking interface.
6. Coverage is calculated solely from stored statement periods. Missing days appear as gaps; no balance is interpolated outside documented data.
7. Recurring costs are candidates, not contractual determinations. A series requires at least two matching charges of the same profile, account, normalized counterpart, cent amount, and cost category.
8. `active` only means: the last documented charge lies, relative to the given reference date, within the recognized interval plus tolerance. Cancellation, contract status, and future debits are not proven by this.

## Use Cases

### USECASE 019-1: Import statement

- **Input:** Synthetic, mathematically consistent monthly statement and exact state approval.
- **Expectation:** One account, one statement, and all transactions are added atomically; source document and raw text remain outside the store.

### USECASE 019-2: Represent gaps

- **Input:** Statements for January and March, query January through March.
- **Expectation:** February appears fully as an undocumented period; FolderHome does not fabricate a balance or transactions.

### USECASE 019-3: Detect subscription candidate

- **Input:** Three monthly, cent‑identical charges from “StreamFlix”.
- **Expectation:** Monthly candidate with documented transaction IDs, monthly total, extrapolated annual total, and next expected window.

### USECASE 019-4: Do not claim unclear recurrence

- **Input:** Two charges of differing amounts or irregular intervals.
- **Expectation:** No active subscription; transactions remain individually queryable.

## Acceptance Threshold

Phase 19 is completed with 179 FolderHome tests and uses exclusively synthetic documents and local state. There is no bank access, no payment, no cancellation, no tax or financial advice, and no statement about periods without a documented statement.
