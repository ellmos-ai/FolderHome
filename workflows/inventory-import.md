# Workflow: Supplement Local Household Inventory

**English** | [Deutsch](./inventory-import.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** after an explicitly documented inventory  
> **Duration:** few seconds per inventory folder

## Purpose

Validate provided inventory observations, ingest them in a revision‑bound manner into the local append‑only inventory store, and then display current inventories as well as purchase and expiration candidates.

## Preconditions

- Inventory folder and separate FolderHome state are defined.  
- Profile and doc‑services PIN are valid.  
- Each input file conforms to the declarative V1 format.  
- A local sensitive processing was deliberately allowed when needed.

## Steps

1. **Create plan** — `inventory plan` with source, state, profile and, if needed, execute `--approve-sensitive-local-read`.  
2. **Check evidence** — verify item, category, location, unit, quantity, minimum stock, capture date, optional expiration date, document hash and line numbers.  
3. **Check conflicts** — do not skip `blocked` when contradictory observations of the same item and day exist.  
4. **Create approval** — record plan ID, inventory revision, concrete action IDs, approval ID and timezone timestamp.  
5. **Rebuild plan** — start `inventory apply` with identical inputs and the approval file.  
6. **Release state** — set `--approve-state-write` only for this local transaction.  
7. **Check result** — verify new event IDs, revision and unchanged sources.  
8. **Read current inventory** — execute `inventory current` with profile and optional category/reference date.  
9. **Read history** — `inventory history` shows all append‑only events of a profile, category or item.  
10. **Check demand** — run `inventory needs` with explicit reference date and expiration horizon; do not derive automatic purchase.

## Exit-Criteria

- [ ] Plan, approval, inventory revision and source hashes match.  
- [ ] Events and audit were added together or not at all.  
- [ ] Source documents remain byte‑identical.  
- [ ] Current view and history are traceable per profile.  
- [ ] Minimum stock and expiration date appear only as candidates that must be checked.

## Gotchas

- Quantities use at most three decimal places and are not rounded.  
- A new observation does not overwrite an older one; the current view is derived from the event history.  
- `--approve-sensitive-local-read` permits no external distribution.  
- Profiles organize views within the same OS account.  
- FolderHome does not order anything and does not claim a complete household.

## Related

- [`../docs/phase20-household-inventory-reuse-and-plan.md`](../docs/phase20-household-inventory-reuse-and-plan.md)  
- [`./document-library.md`](./document-library.md) — local document extraction  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑20 data flow  

## History

- **2026-08-22** — Created after Phase‑20 end‑to‑end implementation
