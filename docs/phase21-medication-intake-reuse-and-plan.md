# Phase 21 — Medication Plan and Confirmed Intake

**English** | [Deutsch](./phase21-medication-intake-reuse-and-plan.de.md)

**Status:** locally completed, 198 tests green  
**Date:** 2026-08-22  
**Product name in competition:** FolderHome

## Goal

FolderHome explicitly accepts provided medication plans as organizational, evidence‑based data. For a selected day it displays scheduled intakes and, separately, explicitly confirmed intakes. It does not decide on the medication or dose and does not automatically modify medication inventory.

## Reuse

### UpToday Health Engine

- source: separate clean UpToday checkout
- verified revision: `7582ca87e17e458bb99a7379d2c54003c15415a4`
- license: MIT
- focused medication/intake acquisition: 6 tests green
- reused separation: medication, schedule, daily dose and confirmed intake; duplicate confirmation must not have duplicate effect

Not loaded are the global DB singleton, direct `UPDATE`/`DELETE` operations, the write‑on‑read daily plan, floating‑point inventories, implicit `datetime.now()` and automatic inventory reduction.

### Gesundheit‑Skill and Health‑Assist‑Bundle

- `gesundheit` 2.0.0, repository `ellmos-ai/skills`, revision `0317f32310eed11d21f603cb6f22a689485af226`, MIT
- Health‑Assist‑Bundle 1.0.0: registered declarative draft without runtime authority

Only explicitly provided information, factual organization and the “organization only” boundary are reused. Diagnosis, therapy, prescription and dose decision remain excluded.

## Declarative V1 Input Format

A text file describes exactly one intake time point:

```text
Präparat: DemoMed
Dosis: 1
Dosiseinheit: Tablette
Zeitpunkt: 08:00
Zeitzone: Europe/Berlin
Wochentage: täglich
Gültig-von: 2026-08-22
Gültig-bis: 2026-12-31
Bestandsbereich: Gesundheit
Bestandsgegenstand: DemoMed
Bestandseinheit: Tablette
```


`Gültig-bis` is optional. Dose values are stored without rounding as integer thousandths of the documented unit. `Wochentage` accepts `täglich` or a comma‑separated selection of German weekdays. “As‑needed” plans are not automatically scheduled in V1 and remain `review_required`.

## New Encapsulated Blueprint

```text
expliziter Planordner + Profil + lokale Sensitivitätsfreigabe
  → doc-services read-only extrahieren
  → Medikamentenzeitplan mit Dokumenthash und Zeilenevidenz bilden
  → gleiche Gültigkeit/Zeit desselben Präparats auf Widerspruch prüfen
  → gegen Medikamentenrevision planen
  → exakte Approval-Datei + State-Gate
  → Quellhash und Revision erneut prüfen
  → Zeitplanversion und Audit gemeinsam append-only schreiben

Medikamentenstore + Profil + Tag + expliziter Auswertungszeitpunkt
  → gültige Zeitplanversionen für den Wochentag bestimmen
  → stabile Dosis-IDs ohne Schreibzugriff bilden
  → bestätigte Einnahmeereignisse getrennt zuordnen
  → bevorstehend / Bestätigung ausstehend / bestätigt ausgeben
  → optional belegten FolderHome-Bestand nur als Kandidat vergleichen

explizite Bestätigungsdatei + State-Gate
  → Revision, Zeitplan, Tag, Dosis-ID und Zeitzonenzeit erneut prüfen
  → genau ein append-only Einnahmeereignis ergänzen
  → keine Bestandsänderung, Erinnerung oder externe Aktion auslösen
```


New packages:

- `folderhome.contracts.medication`
- `folderhome.application.medication_intake`
- `folderhome.capabilities.medication_store`

## Security and Product Boundaries

- No diagnosis, prescription, dose calculation or interaction checking.
- No claim that a plan is medically correct or up‑to‑date.
- No automatic reminder, message, calendar action or order.
- A confirmation documents only an explicit user input; it is not a medical efficacy evidence.
- Inventories are not automatically reduced. A reconciliation is only an indication of existing or missing local evidence.
- No silent overwriting and no SQL‑`DELETE`.
- Family profiles are not an access boundary within the same OS account.

## Acceptance

- Parser, weekdays, timezone and decimal precision
- Privacy status and line evidence
- Conflict‑free read‑only planning
- approval, revision, source‑hash and state gates
- append‑only schedules, intakes and audit
- daily view without write‑on‑read
- idempotent intake confirmation
- optional inventory reconciliation without inventory change
- synthetic CLI end‑to‑end run

---
