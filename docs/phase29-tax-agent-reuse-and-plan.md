# Phase 29: Reusing the tax agent and safely limiting it

**English** | [Deutsch](./phase29-tax-agent-reuse-and-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Reuse existing receipt and work‑document functions of the extracted tax agent without asserting tax advice or transmission to authorities.

## Verified state

The separate clean `steuer-assistent` checkout was checked read‑only:

| Feature | Finding |
|---|---|
| Repository | `https://github.com/ellmos-ai/steuer-assistent.git` |
| Revision | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` |
| Package version | `0.2.3` |
| License | MIT |
| Checkout | clean and exactly at the pinned revision |
| Provider tests | 35/35 green |
| Runtime | local SQLite storage and ZIP output, no network |

The provider records user‑side categorized receipts from the advertising expenses area and creates a private work document. It does not check tax deductibility nor a tax case and does not transmit anything to ELSTER, ERiC, the tax office, or any other portal.

## Reuse and new integration code

Reused unchanged:

- `SteuerAssistent.add_beleg()` for an explicitly confirmed receipt,
- `SteuerAssistent.export_arbeitsunterlage()` for a private ZIP file,
- the input groups supported by the provider: work equipment, travel costs, training, home office, communication, and miscellaneous.

New and encapsulated are the FolderHome contracts, the orchestration, and the bridge under `contracts.tax`, `application.tax_workpaper` and `bridges.tax_assistant`. No provider source code is copied or modified.

## Receipt and profile binding

A receipt plan requires a catalogued document ID, the current document hash, a known family profile, and optionally an existing FolderHome financial entry of the same profile. If an entry is specified, its absolute cent amount must match the receipt. A filename or a free search hit is not sufficient as a receipt binding.

Provider stores are separated per profile in `tax-workpaper/<profile_id>/steuer.db`. This prevents mixed work documents within a household view. There is no access control: All profiles remain readable within the same operating system account.

## Proposal is not a tax classification

`category_candidate` is only a proposal that must be reviewed. As long as `confirmed_category` is missing, the plan has the status `review_required` and `provider_write_allowed=false`. FolderHome does not automatically move the proposal into a confirmed category.

Even a confirmed input group does not mean that the output is tax‑deductible. Therefore all plans and reports display `deductibility_assessed=false` and `tax_advice=false`.

## Separate gates

```text
katalogisierter Beleg + optional passende Finanzbuchung
  → Sensitivitätsfreigabe
  → read-only Plan mit Dokument- und Providerstore-Hash
  → menschlich bestätigte Eingabegruppe
  → exakte Approval-Datei + lokales State-Gate
  → Provider schreibt genau einen Beleg
  → separater read-only Exportplan pro Profil und Steuerjahr
  → Export-Approval + State-Gate + Output-Gate
  → neue private ZIP-Arbeitsunterlage
```


Receipt capture and export are separate decisions. The export does not overwrite an existing file. Portal access, network, dispatch, official format, and submission are not implemented in Phase 29 and cannot be enabled by any generic CLI switch.

## Acceptance

The tests use only a synthetic receipt. They verify the read‑only plan, the hash and state binding, idempotence, blocked modified documents, separate export approvals, and the real pinned provider. Its own test suite was also run unchanged.

---
