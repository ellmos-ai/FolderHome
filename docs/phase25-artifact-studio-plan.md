# Phase 25 — Office, Media, and Design Studio

**English** | [Deutsch](./phase25-artifact-studio-plan.de.md)

**Status:** locally completed, 218 tests green  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Goal

FolderHome should not recreate presentations, spreadsheets, documents, ODT, design sets, business cards, and media with a new monolithic renderer. Instead, a provider‑neutral plan lists the existing specialists, their current status, and the required quality gates. The new local core generates only reusable design tokens and an SVG business‑card preview.

## Revision and Runtime Inventory

| Component | Finding | Phase‑25 Role |
|---|---|---|
| `pptx`-Skill | present; requires content review, rendering, and at least one visual fix/check cycle | presentation handoff, currently blocked without `soffice` |
| `academic-pptx` | present; adds argument, evidence, and citation rules | use only additionally for scientific presentations |
| `Spreadsheets` | present; requires `@oai/artifact-tool` via the workspace dependency loader | spreadsheet handoff, currently blocked without loader binding |
| `documents` | present; requires structural and visual DOCX validation | document handoff, currently blocked without `soffice` |
| report-forge | clean against `355acb5ff1abe41b384a0d1e3a00925e6ac86215`, 22 tests green; distribution `1.1.4`, runtime `1.1.0` | not invoked until identity is unified |
| ai-media-editor | clean against `4e4c79d8c16a117bf69c0f72ad946575110a6b84`, MIT, version `0.2.0`, 45 tests green | media handoff with its own read, strategy, and output approval |
| MediaBrain | local checkout with external changes | not read, modified, or claimed as provider |
| LibreOffice/`soffice` | unavailable | PPTX, DOCX, and ODT visual inspection blocked |
| Poppler/`pdftoppm` | available | alone not an office renderer |
| FFmpeg/FFprobe | available | possible ai-media-editor runtime, no automatic media invocation |

## New encapsulated core

- `folderhome.contracts.artifact_studio`
- `folderhome.application.artifact_studio`
- `folderhome-artifact-studio`-Skill

The plan contract `folderhome.artifact-studio-plan.v1` contains, for each requested artifact type, provider, revision, status, justification, and gates. `provider_invoked=false` and `side_effects=[]` are fixed invariants.

## Design set and business card

`folderhome.design-studio-request.v1` describes profile, purpose, five colors, fonts, and business‑card content. The core:

- blocks unknown schema fields
- accepts only safe font identifiers
- requires at least a 4.5:1 contrast ratio for text on background and primary color
- escapes all user‑related SVG content
- generates deterministic JSON tokens, CSS variables, and an SVG at  
  1050 × 600
- writes the three files only after a separate output gate
- never overwrites and rolls back its own hash‑identical partial outputs

The synthetic example card was additionally rasterized via Edge headless and visually inspected for umlauts, contrast, spacing, and complete contact lines. Every subsequent card still retains `visual_qa_passed=false` until it has been examined itself.

## Product boundaries

- A plan is not an executed office, media, or skill result.
- Blocked routes are not bypassed with similar system libraries.
- `review_required` permits preparation, but not a claim of completion.
- ODT remains fully blocked without a bound renderer.
- Media are not read, trimmed, or rendered.
- Shipping, upload, printing, and publishing are separate user gates.
- Profiles within an operating‑system account remain organizational and are not an access boundary.

---
