# Phase 23 — Insurance and Contract Cockpit

**English** | [Deutsch](./phase23-contract-cockpit-plan.de.md)

**Status:** locally completed, 208 tests green  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Goal

The existing FolderHome capabilities are composed for a contract subject without re‑extracting data or building new domain stores. The guiding use case is: “What is my latest auto insurance for my Hyundai i10?”

## Reuse instead of duplicate construction

| Existing component | Use in the cockpit |
|---|---|
| Document index and catalog | explicit search request and re‑source hash verification |
| Version analysis | latest/older version, date basis, comparison and archiving suggestions |
| Contact register | active and deletion‑check‑pending contacts by contract object |
| Finance store | recurring cost candidates and statement coverage |
| Calendar store | matching future, already booked events |
| Profile configuration | existence and organizational assignment of the profile |

The new code is only the encapsulated integration layer:

- `folderhome.contracts.contract_cockpit`
- `folderhome.application.contract_cockpit`

## Explicit Join Contract

A `folderhome.contract-cockpit-request.v1` file specifies profile, domain, display name, document search, contract object, counter‑party terms, calendar terms, accounts, coverage start, reference date, and archiving preference. This avoids guessing based on similar names which contact or which debit belongs to a contract.

## Output and Limits

`folderhome.contract-cockpit.v1` contains:

- current and older documented versions without raw text
- optional, uncommitted and reversible archiving suggestions
- matching active and prior contacts with source reference
- recurring cost candidates with booking IDs
- matching future calendar events with document reference
- statement coverage and gaps
- component revisions and visible missing/ambiguous evidence
- identical JSON and Markdown view

The run is read‑only. It does not archive anything, change any contact, create any appointment, send any message, access a bank account, or assert any contract status. The sensitivity approval is checked before the first state or document access.

### File export boundary — updated 2026-09-09

CLI stdout and JSON files written by the CLI or the approved workflow use
`folderhome.contract-cockpit-export.v1`. Its `source_schema` identifies the
internal `folderhome.contract-cockpit.v1` representation. The internal records
keep their filesystem paths for plan hashing and source revalidation; exports
omit document, contact and calendar `source_path` fields and the private
document `index.ref` locator.

Archive suggestions export `source_filename`, `target_filename` and
`target_role: "configured_archive"` instead of executable source/target paths.
Markdown likewise shows only the filename and archive role. Document IDs,
source hashes, dates, contact details and evidence limitations remain available.
**This is a private evidence export, not anonymization:** user-provided text can
still contain personal data or paths and requires review before sharing.

Consumers needing filesystem actions must use the internal approved plan, not
reconstruct paths from exported names. Download size and workspace-path guards
remain active. The synthetic AgentCore journey can return all four small result
files inline; this is locally tested, not evidence of a deployed cloud update.

## Acceptance

- explicit mapping instead of implicit fuzzy join
- latest version and older versions
- configurable but not executed archiving suggestions
- matching contacts, costs, appointments and financial coverage
- visible missing components and ambiguous contacts
- no document raw text in the JSON
- Never‑overwrite outputs outside the state directory
- byte‑exact unchanged shared state in the CLI end‑to‑end test
- exclusively synthetic Hyundai i10 case

---
