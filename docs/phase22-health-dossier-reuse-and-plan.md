# Phase 22 — health dossier and medical report synthesis

**English** | [Deutsch](./phase22-health-dossier-reuse-and-plan.de.md)

**Status:** locally completed, 204 tests green  
**As of:** 2026-08-22  
**Product name in competition:** FolderHome

## Goal and Requirement Gap

FolderHome explicitly aggregates selected health documents for a profile. It generates an extractive timeline, documented medications, appointments, open user questions, direct field conflicts, and visible source gaps. Each adopted statement carries a document ID, source hash, relative path, and line number.

Thus it satisfies local Markdown/JSON synthesis, evidence binding, time coverage, conflict candidates, and error transparency. Remaining open are free LLM synthesis, OCR approval for real sources, DOCX/ODT, medical interpretation, and external sharing.

## Revision‑accurate Reuse

| Component | Revision | Placement for Phase 22 |
|---|---|---|
| doc-services | `037a432bbec94ac6db5dfa53941745fda7c2f38a` | Runtime bridge for read‑only extraction, data‑protection finding, and extraction provenance |
| KnowledgeDigest | `7040c66aa9326975ad81c156acf0d49fd5dca60f` | Existing document search; not re‑described or needed for the explicit dossier folder |
| gesundheit‑Skill 2.0.0 | `0317f32310eed11d21f603cb6f22a689485af226` | Design reference for organizing provided information without diagnosis or therapy decision |
| docs-analysis 1.0.0 | local skill state 2026-03-15 | Requirement/code‑gap method; no runtime import |
| report-forge | `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | Optional report candidate, blocked: distribution `1.1.4`, runtime `1.1.0` |
| llm-note | `b5fe59fc155ded9603566aa0fb920a53181a2426` | Note storage, no dossier renderer; not loaded in Phase 22 |

All mentioned checkouts were clean during verification. No provider source code was copied. The new dossier contract and the orchestration are fully encapsulated in FolderHome.

## New Core

```text
expliziter Gesundheitsordner + Profil + Stichtag + Sensitivitätsfreigabe
  → doc-services revisionsgebunden und ohne OCR lesen
  → Datenschutzbefund auf lokalen Gesundheitszweck begrenzen
  → eindeutiges Dokumentdatum und gelabelte Aussagen extraktiv erfassen
  → jede Aussage an Dokument-ID, Hash, Pfad und Zeile binden
  → Zeitlinie deterministisch sortieren
  → direkte Feldabweichungen als Review-Kandidaten zeigen
  → Abstände zwischen datierten Quellen sichtbar machen
  → blockierte, nicht lesbare, undatierte und zukünftige Quellen ausweisen
  → Markdown und JSON als neue Dateien außerhalb des Quellordners schreiben
```


New packages:

- `folderhome.contracts.health`
- `folderhome.application.health_dossier`
- `folderhome.capabilities.health_report_handoff`

## Data Protection Decision

doc-services uses ROT for both health data and access credentials, bank identifiers, and other highly sensitive patterns. A blanket override of ROT would therefore be impermissible. FolderHome processes, after the local sensitivity gate, only a single ROT finding, whose all red finding lines are `Gesundheitsdaten`. Any additional red finding blocks the content adoption. The report remains local; network and remote providers are not invoked.

## Extraction Instead of Claim‑Upgrade

- `Befund`, `Ergebnis`, `Medikament`, `Termin` and `Offene Frage` are taken as documented statements, not validated or interpreted.
- `Diagnose` and `Maßnahme` are explicitly referred to as documented information.
- Direct conflicts arise only from equally named `Dokumentierte Angabe: Feld = Wert` lines.
- A time gap is a source gap, not an alleged treatment gap.
- Undated content is not silently sorted based on the filename or filesystem timestamp.
- The report claims neither completeness nor medical advice.

## Acceptance

- Gate before extraction
- exclusively health‑related ROT exception for local processing
- blocked, unreadable, undated, and future sources
- timeline with exact line evidence
- medications, appointments and open questions
- direct field conflicts
- source gaps over configurable threshold
- stable IDs and deterministic Markdown/JSON output
- Never-overwrite and outputs outside the source folder
- synthetic CLI end‑to‑end run

---
