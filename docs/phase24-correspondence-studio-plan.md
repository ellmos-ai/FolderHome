# Phase 24 — Correspondence Studio

**English** | [Deutsch](./phase24-correspondence-studio-plan.de.md)

**Status:** locally completed, 213 tests green  
**As of:** 2026-08-22  
**Product name in competition:** FolderHome

## Goal

FolderHome creates a verifiable local preview from an explicit request, a controlled template, and an inheritable letter design. After a second approval it can write new Markdown and TXT files.

## Revision‑accurate reuse match

| Component | Finding and usage |
|---|---|
| report-forge | clean checkout `355acb5ff1abe41b384a0d1e3a00925e6ac86215`, MIT; inventoried as a planned Office renderer but not invoked against Runtime `1.1.0` due to distribution `1.1.4` |
| doc-services | available document extraction; no output renderer and therefore not repurposed here |
| letter-hooker | prompt bootloader and governance tool; no letter or template renderer |
| python-docx | locally available; without complete visual render acceptance no claimed DOCX output |
| pdftoppm | locally available; alone no Office conversion |
| LibreOffice/soffice | not available; ODT and visual DOCX acceptance remain blocked |

The new, reusable core is encapsulated in:

- `folderhome.contracts.correspondence`
- `folderhome.application.correspondence`

## Contracts

- `folderhome.letter-designs.v1`: designs and explicit bindings
- `folderhome.letter-templates.v1`: controlled templates
- `folderhome.correspondence-request.v1`: profile, occasion, parties, variables, attachments and internal evidence references
- `folderhome.correspondence-preview.v1`: content, resolution path, hashes and non‑executing format handoffs
- `folderhome.correspondence-output-report.v1`: actually newly written Markdown/TXT outputs and their hashes

## Design inheritance

The order is deterministic: default, scope, purpose, profile, profile‑purpose. Each match replaces the previous. Unknown design IDs already block loading the configuration.

## Security and product boundaries

- The sensitivity approval is checked before reading the request.  
- Only simple placeholders consisting of lowercase letters, digits and underscores are allowed; Python attribute and index accesses are excluded.  
- Missing or unused variables block execution.  
- Previews are read‑only and do not invoke either LLM nor remote providers.  
- Writing requires its own output gate, checks both target paths in advance, never overwrites, and only rolls back newly created files.  
- DOCX and ODT remain visible, non‑executed handoffs.  
- Email sending, printing, upload and publishing remain outside this phase.

## Acceptance

- four focused domain tests for configuration, rendering and output  
- one CLI end‑to‑end test for both gates, preview, output and repeat  
- synthetic German correspondence with real umlauts  
- full suite, Ruff and Compileall before phase completion  

---
