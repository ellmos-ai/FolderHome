# Phase 16: Contact Reuse and Blueprint

**English** | [Deutsch](./phase16-contact-reuse-and-plan.de.md)

**As of:** 2026-08-22  
**Status:** implemented and approved with 146 FolderHome tests

## Reuse Check

- Among the already extracted local modules there is no suitable contact register. `crm-cosmology` is, despite its name, a cosmology project and professionally unrelated.
- The legacy inventory `BACH/system/hub/contact.py` manages general contacts in the BACH database. According to the project decision it will not be re‑extracted from BACH and will not be directly linked.
- The BACH handler has no document‑hash evidence, no candidate phase, no plan/action‑bound approval, and no atomic contact switch.
- Therefore the already extracted FolderHome bridges for `doc-services`, profile, document identity, hash verification, gates and audit are reused. Only the encapsulated contact core is created anew.

## User Goal

FolderHome shall be able to determine from a document who is responsible for a specific area and object, e.g., the insurance of a Hyundai i10. New contact data may only be adopted after verification. If later a different contact is assigned for the same purpose, the new contact is created and the old one is merely marked as a deletion candidate.

## Declarative Document Format V1

V1 evaluates only uniquely labeled single lines:

```text
Organisation: Beispiel Versicherung AG
Ansprechpartner: Erika Beispiel
Rolle: Kundenservice
Zuständig für: KFZ-Versicherung
Vertragsobjekt: Hyundai i10
E-Mail: erika@example.invalid
Telefon: +49 30 123456
Gültig ab: 2026-08-01
```


At minimum, organization, responsibility, and either email or phone are required. Ambiguous multi‑values and invalid channels do not produce an approval‑capable candidate. `blocked` and `not_checked` block the local adoption. `review_required` additionally requires the explicit approval `--approve-sensitive-local-read`; it does not permit external distribution.

## Data and Approval Contract

1. Each candidate binds profile, area, purpose, optional object reference, normalized channels as well as document ID, source hash, path, and line evidence.
2. A read‑only register plan compares candidates against the same key composed of profile, area, purpose, and object reference.
3. If no match is found, `create` is planned; for an identical contact, `noop` is planned.
4. A differing new contact generates an atomic `replace` action: actively create the new contact and mark the previous contact as `deletion_candidate`.
5. No workflow automatically deletes a contact.
6. An approval file binds the plan ID, register revision, and concrete action IDs.
7. Before writing, the register revision and all source document hashes are re‑checked.
8. Register changes and append‑only events occur within a SQLite transaction under an explicit state gate.
9. Multiple documents with the same responsibility key are evaluated together before the register comparison. Only the unequivocally newest contact can be planned; differing contacts with the same newest date cause a fail‑closed block.
10. Document folders and state must not overlap, so that the register is not read as a separate document source.

## Usecases

### USECASE 016-1: Plan the first responsible contact

- **Input:** Synthetic policy with a labeled point of contact.
- **Expectation:** An evidence‑bound candidate and an unapproved `create` action; no register is created.

### USECASE 016-2: Approve and find contact

- **Input:** Exact approval file for the `create` action.
- **Expectation:** Active contact is searchable by profile, area, purpose and “Hyundai i10”; document remains byte‑identical.

### USECASE 016-3: Responsibility change

- **Input:** Newer document with a different point of contact for the same key.
- **Expectation:** `replace` suggestion; after approval the new contact is active, previous contact `deletion_candidate`, no line deleted.

### USECASE 016-4: Block contradictory folder contacts

- **Input:** Two documents with the same responsibility key and date, but different contacts.
- **Expectation:** Both candidates remain visible and `blocked`; no executable register action is generated.

## Implemented Interface

- `contacts plan` extracts labeled contact candidates and compares them read‑only with the current register revision.
- `contacts apply` rebuilds the plan and requires an approval file, source‑hash readback, and `--approve-state-write`.
- `contacts list` searches for active or optionally also deletion‑candidate contacts by profile, area, and object reference.
- The reusable core resides separately under `capabilities/contact_registry`; application service and contracts remain provider‑neutral.
