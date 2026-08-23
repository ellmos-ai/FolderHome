# Phase 28: llm-note Reuse and Personal Note Service

**English** | [Deutsch](./phase28-llm-note-reuse-and-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Reuse the existing note storage and encapsulatedly supplement the missing human‑controlled management.

## Verified Inventory

The separate clean `llm-note` checkout was verified read‑only:

| Feature | Finding |
|---|---|
| Repository | `https://github.com/doc-bricks/llm-note.git` |
| Revision | `b5fe59fc155ded9603566aa0fb920a53181a2426` |
| Package version | `1.0.3` |
| License | MIT |
| Checkout | clean, exactly on the pinned revision |
| Provider tests | 19/19 green |
| Runtime | Python standard library, local SQLite/text storage, no network |

The earlier FolderHome table still referenced `ellmos-ai/llm-note`. The actual checkout, its manifest, and its README now indicate `doc-bricks` as the repository. Phase 28 therefore corrects the provenance without changing the provider state.

## What Is Reused

FolderHome uses `llm_note.NoteStore.write()` as the sole writable note store. Every approved FolderHome version is stored as a new `folderhome_note_version` entry. The provider source code is neither copied nor modified.

The public provider read path initializes a database and runs schema DDL when a store is missing. However, a FolderHome plan must remain read‑only. Therefore the bridge reads existing FolderHome versions via a tightly scoped SQLite adapter with `mode=ro&immutable=1`, validates the expected `note_entries` schema, and uses the public provider API only for approved attachments. This matches the already proven KnowledgeDigest seam: write‑on‑read is avoided without building a second note store.

## Missing Features of the Inventory

`llm-note` is a small agent and human note store. It does not yet model:

- Profile, area and logical notebook as FolderHome context,
- Questions and suggestions separated from the approved content,
- Plan, content, state, and approval binding,
- an explicit document or calendar reference,
- Editing and return as a traceable version sequence,
- the operating‑system‑account boundary of the family profile.

This gap is closed by new, reusable code in `contracts.personal_notes`, `application.personal_notes`, `bridges.llm_note` and `capabilities.personal_note_guide`.

## Binding Procedure

```text
menschliche Anfrage
  → strikte Schema- und Profilprüfung
  → gepinnter read-only llm-note-Readback
  → synthetische Fragen und Vorschläge, kein Inhaltsumbau
  → review_required-Plan mit Store- und Inhaltshash
  → menschliche Freigabe exakt dieses Inhalts
  → llm-note.NoteStore.write() ergänzt genau eine Version
  → read-only Readback und Ausführungsbericht
```


`create` starts at revision 1. `edit` appends a new revision. `revert` copies the content of an earlier revision into a new revision; it does not delete or overwrite any version. A repeated plan, an outdated store hash, or a mismatching content hash blocks the write.

## Authorship and LLM Boundary

The plan stores `author_kind=human`. The guide provides exclusively `questions` and `suggestions`; `confirmed_content_changed` must be `false`. The Phase‑28 acceptance uses a deterministic no‑network guide. A later real LLM provider requires its own disclosure of the data to be transferred, a separate user approval, and a proven provider contract. Remote calls are not executable in Phase 28 even with a global switch.

## References and Security Boundary

Documents and appointments are never searched for or linked automatically. A reference must be included in the request with type, target ID, label, and for documents an optional SHA‑256. FolderHome only validates the format; the reference is not a claim that the target still exists or is technically complete.

Profiles such as Lukas, Hanna, or Simon are view and organization attributes within the same operating‑system account. They are not access barriers. Phase 28 introduces neither network synchronization nor account sharing.

## Acceptance

The synthetic end‑to‑end case executes provider inventory, guide plan, content‑hash‑bound approval, local storage, and history read‑back. Before the approval there is no state folder. After the approval exactly one new provider revision exists; `network_invoked` and `external_sync_invoked` remain `false`.

---
