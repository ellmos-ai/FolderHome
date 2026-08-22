# Phase 31: Understanding Social Law Notices Safely

**English** | [Deutsch](./phase31-official-notice-understanding-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Extract explicitly labeled data with evidence from a provided official notice, surface contradictions, and produce a clear local audit report, without asserting any legal review, deadline calculation, or response.

## Inventory Reconciliation

For Phase 31, the central skills inventory and the existing `law-checker` were examined:

| Inventory | Revision | Finding | Usage |
|---|---|---|---|
| `ellmos-ai/skills` | `0317f32310eed11d21f603cb6f22a689485af226` | local checkout clean, but one commit behind upstream | method reference via the `law-checker` pointer |
| `ellmos-ai/law-checker` | `330fe47b3621c69ec824cd05ca5b283e107f9eaf` | checkout one commit behind upstream and externally modified | no runtime binding |
| `doc-services` | `037a432bbec94ac6db5dfa53941745fda7c2f38a` | pinned, clean provider | local text extraction without OCR |

The existing `law-checker` is designed for an initial legal orientation and requires precise sources, deadline verification, and human escalation. However, its local law register does not cover a complete general procedural and social court law for arbitrary notice types. Additionally, the checkout is not clean and not up to date. Therefore, FolderHome does not load it as a runtime in Phase 31 and does not copy any code.

## New Encapsulated Core

`contracts.official_notices` and `application.official_notices` are new, reusable competition code. They encapsulate:

- the profile, time, document, and source hash binding of a notice analysis,
- strictly labeled fields for notice type, authority, file reference, notice date, benefit period, decision, and justification,
- explicitly printed legal remedy, deadline, and office information,
- evidence per field with line number, document ID, and source hash,
- visible ambiguities instead of arbitrary selection,
- missing fields, warnings, and a clear audit status,
- separate Markdown/JSON output with write gate and never-overwrite.

The capsule can later also be used in Sovereign. The existing `doc-services` provider handles only the local extraction; the domain‑specific notice structure belongs to FolderHome.

## Process

```text
Bescheid + Profil + explizite Sensitivitätsfreigabe
  → gepinnten doc-services-Checkout prüfen
  → Text lokal extrahieren und Quellhash bestätigen
  → ausschließlich bekannte, ausdrücklich gelabelte Felder lesen
  → jedes Feld an Zeile, Dokument-ID und Quellhash binden
  → Konflikte und fehlende Angaben sichtbar machen
  → gedrucktes Fristdatum optional gegen explizites as_of zählen
  → read-only Analyse ausgeben
  → nach separatem Schreibgate neue Markdown-/JSON-Dateien erzeugen
```


An optional access date is always indicated as a user‑provided value. It is not guessed from metadata. An explicitly printed deadline date may be counted for orientation against `as_of`; the result is not a legal deadline calculation. Relative deadline wordings are not converted into data.

## Legal and Safety Boundary

Phase 31 performs no legal review. It does not determine whether a notice is lawful, nor when a legal deadline actually starts or ends. It does not create an objection, an application, or a message to an authority. OCR is disabled in this integration so that an uncertain recognition result does not silently appear as a reliable deadline indication.

The report makes these limitations visible. Missing or contradictory core data lead to `review_required`. Ongoing or unclear deadlines require immediate qualified social law assistance. A later legal review must first update, clean, expand the domain of `law-checker`, and bind it to current official sources.

## Acceptance

The synthetic acceptance checks field and evidence binding, relative deadline wordings, conflicts, sensitivity and output gates, changed sources, and never‑overwrite. The CLI test runs provider inventory, read‑only analysis, and report generation end‑to‑end. It explicitly confirms that no legal review, response, or external effect has taken place.

---
