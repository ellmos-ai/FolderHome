# Phase 33: Benefit and Funding Pre-screen with Official Handoffs

**English** | [Deutsch](./phase33-benefit-screening-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Check user‑provided profile facts against a dated, incomplete routing catalog and display appropriate official guides as the next step, without claiming benefit entitlement, amount, or application.

## Inventory Reconciliation

There is no suitable extracted benefit checker:

| Inventory | Revision | Finding | Use |
|---|---|---|---|
| `ellmos-ai/skills` | `0317f32310eed11d21f603cb6f22a689485af226` | `foerderplaner` plans educational funding | no professional runtime |
| BACH | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` | general old social law wiki pages, no reliable pre‑screen API | no import, no copied code |
| extracted OneDrive modules | targeted name search 2026-08-22 | no benefit/social service provider found | new capsule required |

The new core resides in `contracts.benefit_screening` and `application.benefit_screening`. It is independent of specific benefit types and can later be used in Sovereign or other modules.

## Official Handoffs

The example catalog reviewed on 2026-08-22 contains:

- the [Social Benefit Finder of the Social Platform](https://sozialplattform.de/inhalt/sozialleistungen-finden),
- the [KiZ Guide of the Federal Employment Agency](https://www.arbeitsagentur.de/familie-und-kinder/kinderzuschlag-verstehen/kiz-lotse),
- the [Housing Benefit Plus Calculator of the BMWSB](https://www.bmwsb.bund.de/DE/wohnen/wohngeld/wohngeldrechner/wohngeldrechner-2025_artikel.html).

The Social Platform describes its finder as guidance and refers the binding decision to the responsible authority. The KiZ guide and the housing benefit calculator are also official pre‑checks or orientations. FolderHome therefore links to them instead of duplicating their complex and change‑prone individual case calculations.

## Data and Source Model

The benefit profile is technically separated from the organizational FolderHome profile. It contains only `user_provided` facts with stable keys and is bound by file SHA‑256. FolderHome does not automatically extract these data in Phase 33 from official notices, account statements, or other documents.

Each catalog source has a publisher, title, HTTPS URL, verification timestamp, a short evidence summary, and its SHA‑256. Only sources officially confirmed are accepted. Each program lists:

- official information and official pre‑check,
- the sources used,
- few coarse routing criteria,
- explicitly all non‑modeled individual case requirements.

The catalog must display `complete=false`. A later update process may only change this limit with a technically substantiated completeness agreement.

## Evaluation

```text
Sensitivitätsfreigabe + bekanntes Profil + Leistungsprofil + Katalog
  → Profil- und Kataloghash prüfen
  → amtliche Quellen und Evidenzhashes validieren
  → checked_at gegen explizites as_of und Altersgrenze prüfen
  → pro Programm ausschließlich Routingkriterien auswerten
  → fehlende Fakten, Mismatch oder veraltete Quelle sichtbar halten
  → amtlichen Vorcheck als nächsten Schritt empfehlen
  → optional neuen Markdown-/JSON-Bericht hinter Output-Gate schreiben
```


The four status values are:

- `official_handoff_recommended`: The coarse route matches; open the official pre‑check and verify complete information there.
- `needs_information`: At least one routing entry is missing.
- `routing_mismatch`: A coarse route does not match. This is not a rejection.
- `blocked_source_stale`: At least one used source is older than the configured threshold; no rule is evaluated.

All reports remain `review_required`. `eligibility_assessed`, `amount_estimated`, `application_generated` and `network_used` are always `false`.

## Acceptance

The synthetic acceptance checks the official handoff, missing facts, mismatch, outdated sources, HTTPS/officiality gate, sensitivity gate, evidence summary hash, altered catalog, output gate, and never‑overwrite. The CLI test checks all three real official handoffs without network call or application.

---
