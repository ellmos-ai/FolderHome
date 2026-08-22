# Workflow: Check Document Contact and Register Locally

**English** | [Deutsch](./contact-register.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** for new or changed documents with responsibility data  
> **Duration:** a few seconds per document folder  

## Purpose

Detect labeled contact data from explicitly selected documents locally, verify it against the responsible profile and a revision‑bound register, and adopt it only after an exact approval.

## Preconditions

- Document folder and separate state path are explicitly defined.  
- Profile and area exist in the same OS‑account configuration.  
- The doc‑services revision matches the pinned manifest.  
- For `review_required`, purely local sensitive processing was deliberately allowed with `--approve-sensitive-local-read`.

## Steps

1. **Create plan** — execute `contacts plan` with document folder, profile, area, and state; no database is created yet.  
2. **Check evidence** — verify organization, contact person, purpose, object, channels, effective date, source hash, and line numbers.  
3. **Check conflicts** — `blocked` must not be bypassed for contradictory latest contacts or multiple active register contacts.  
4. **Check action** — trace `create`, `replace` or `noop`. With `replace` the old contact remains and becomes only a deletion candidate.  
5. **Create approval** — record schema, plan ID, register revision, desired action IDs, stable approval ID, and timezone timestamp.  
6. **Run plan again** — start `contacts apply` with the same input and the approval file.  
7. **Grant state** — set `--approve-state-write` exclusively for the intended local register transaction.  
8. **Check result** — read new and marked contact IDs as well as revision; `deleted_contact_ids` must remain empty.  
9. **Search responsibility** — query the active contact with `contacts list --object "Hyundai i10"`.

## Exit‑Criteria

- [ ] Plan, approval, and source hash match.  
- [ ] The source document remained byte‑identical.  
- [ ] The active contact is discoverable via profile, area, and object.  
- [ ] An earlier contact was at most `deletion_candidate`, never deleted.  
- [ ] The append‑only event number corresponds to the executed actions.

## Pitfalls

- `--approve-sensitive-local-read` does not allow external distribution.  
- Family profiles within the same OS account are not access boundaries.  
- Document and state folders must not overlap.  
- Identical effective dates across different contacts require human clarification.  
- An approval file is intentionally no longer valid after register or document changes.

## Related

- [`../docs/phase16-contact-reuse-and-plan.md`](../docs/phase16-contact-reuse-and-plan.md)  
- [`./document-library.md`](./document-library.md) — local document extraction  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase‑16 data flow  

## History

- **2026-08-22** — created after Phase‑16 end‑to‑end acceptance
