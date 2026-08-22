# Phase 30: Local Weather and Newspaper Desktop Brief

**English** | [Deutsch](./phase30-daily-briefing-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Bundle weather and selected news from occupied local snapshots into a daily HTML brief and, after separate approval, copy it to an explicitly chosen desktop.

## Inventory Check

Among the already extracted local modules and skills, no standalone weather or newspaper provider was found. The only suitable legacy component remains in the BACH monolith:

| Feature | Finding |
|---|---|
| Repository | `https://github.com/ellmos-ai/bach.git` |
| verified checkout | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` |
| relevant files | Wetterservice, Newspaper-Generator, Daily Agent |
| relevant path status | unchanged relative to Git |
| overall checkout | externally modified; not loaded as runtime |
| Newspaper tests | 11/11 green |
| License | MIT |

The weather service calls `wttr.in` directly. The newspaper generator reads the BACH database, renders HTML, optionally launches Edge for PDF, and copies or sends results directly. The daily agent contains a hard‑coded location. These couplings, implicit timings, and direct side‑effects do not comply with the FolderHome contract. Therefore no re‑extraction was performed; BACH remains only a designated design reference.

## New Encapsulated Core

`contracts.daily_briefing` and `application.daily_briefing` are new, reusable competition code. They define:

- a profiled briefing task with explicit `as_of` and time zone,
- integer weather values and precise observation/retrieval timestamps,
- news articles with HTTPS sources, publication and retrieval times,
- category selection and upper limits per category,
- age limits and visible warnings for outdated snapshots,
- deterministic, fully escaped UTF‑8 HTML,
- separate render and desktop approvals with hash binding and never‑overwrite.

The local input schemas are provider seams. A later weather or RSS connector must write exactly such snapshots and receives its own network gate. Phase 30 does not invent a silent live provider.

## Process and Data State

```text
Briefinganfrage + bekanntes Profil + Sensitivitätsfreigabe
  → Wetter- und Nachrichtensnapshot strikt lesen und hashen
  → Zeitstempel gegen explizites as_of prüfen
  → Datenstand fresh oder stale ausweisen
  → Kategorien deterministisch filtern und begrenzen
  → HTML und Planhash ausschließlich im Speicher erzeugen
  → Render-Approval + Output-Gate schreibt eine neue Zwischenausgabe
  → Desktop-Approval + Desktop-Gate kopiert exakt diesen Hash
```


An outdated snapshot does not block readability, but is emitted with `review_required` and a concrete age warning. Data from the future, non‑HTTPS sources, unknown profiles, modified input files, and existing targets block.

Intermediate output and the desktop target must reside in separate folders. Consequently, the render gate cannot silently replace the desktop delivery. The desktop copy uses exactly the previously approved output hash.

## Deliberately Open Connector and Automation Boundary

`briefing providers` exposes live weather and live news connectors as `blocked_not_implemented`. The current run does not invoke any network. It also does not register an operating‑system scheduler. A daily autonomous execution would require a permanent network, output, and desktop permission; such a recurring authority is not derived from a single approval.

The existing FolderHome scheduler remains unchanged, limited to document routines. A later briefing scheduler must first define snapshot generation, error handling, repetitions, and the recurring user approval as a separate contract.

## Acceptance

The synthetic acceptance checks fresh and outdated snapshots, category filters, future and URL limits, HTML and source hash binding, never‑overwrite, as well as separate render and desktop gates. The CLI test runs plan, render, and desktop copy end‑to‑end; network and scheduler remain omitted.

---
