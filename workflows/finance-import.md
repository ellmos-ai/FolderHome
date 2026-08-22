# Workflow: Import bank statements locally and cent‑accurately

**English** | [Deutsch](./finance-import.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** after provision of new bank statements  
> **Duration:** a few seconds per statement folder  

## Purpose

Explicitly provided bank statements are checked, revision‑bound imported into the local finance store, and then coverage, transactions, and recurring cost candidates are evaluated.

## Preconditions

- Statement folder and separate FolderHome state are defined.  
- Profile and doc‑services PIN are valid.  
- The statements conform to the declared cent‑accurate V1 format.  
- Local sensitive processing has been explicitly permitted.

## Steps

1. **Create plan** — execute `finance plan` with source, state, profile and `--approve-sensitive-local-read`.  
2. **Check evidence** — verify account identifier, masked suffix, period, balances, entries, references, document hash and line numbers.  
3. **Check balance** — trace internal arithmetic and continuity with adjacent statements; do not skip `blocked`.  
4. **Create approval** — record plan ID, finance revision, specific action IDs, approval ID and timezone timestamp.  
5. **Rebuild plan** — start `finance apply` with identical inputs and approval file.  
6. **Release state** — set `--approve-state-write` exclusively for this local transaction.  
7. **Check import** — read generated statement/entry IDs and new revision; sources must have remained byte‑identical.  
8. **Check coverage** — execute `finance coverage` for the desired period and leave gaps visible.  
9. **Read account period** — use `finance period` for transactions and only documented boundary balances.  
10. **Check cost candidates** — run `finance recurring` with explicit cutoff date and do not treat the result as contract status.

## Exit‑Criteria

- [ ] Plan, approval, finance revision and all source hashes match.  
- [ ] Statements, entries and audit were added together or not at all.  
- [ ] Source documents remained byte‑identical.  
- [ ] Data gaps and balance discontinuities are visible.  
- [ ] Subscription/cost status and forecasts are expressly only candidates.

## Pitfalls

- `--approve-sensitive-local-read` permits neither bank access nor distribution.  
- Free‑form PDF layouts are not guessed in V1; they require dedicated adapters.  
- Identical booking references or contradictory balances block fail‑closed.  
- A regular debit text does not prove an active contract.  
- Family profiles organize data within the same OS account.

## Related

- [`../docs/phase19-finance-reuse-and-plan.md`](../docs/phase19-finance-reuse-and-plan.md)  
- [`./document-library.md`](./document-library.md) — local document extraction  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑19 data flow  

## History

- **2026-08-22** — Created after Phase‑19 end‑to‑end acceptance
