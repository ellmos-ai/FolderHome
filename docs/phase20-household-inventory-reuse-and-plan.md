# Phase 20 — Household and Stock Inventory

**English** | [Deutsch](./phase20-household-inventory-reuse-and-plan.de.md)

**Status:** locally completed, 189 tests green  
**Stand:** 2026-08-22  
**Product name in competition:** FolderHome

## Goal

FolderHome explicitly takes over provided inventory records into a local, append‑only household stock. Current stock, minimum stock, expiration date and purchase requirements remain provable by profile, area, location and source document.

## Reuse

### UpToday

- local clean checkout: `C:\_Local_DEV\repos\UpToday`
- verified revision: `7582ca87e17e458bb99a7379d2c54003c15415a4`
- License: MIT
- focused contract acceptance: 4 tests green
- reused domain terms: item, category/area, location, base unit, stock, minimum stock and verifiable purchase derivation

UpToday is not loaded as a runtime provider. Its previous `InventoryEngine` uses floating‑point numbers, a global DB singleton, direct `UPDATE`-/`DELETE` operations and `date.today()`. These characteristics do not fit FolderHome's revision‑bound, deterministic append‑only contract. FolderHome does not copy any UpToday source code.

### Existing FolderHome components

- doc-services extracts the explicitly selected files read‑only.
- Profile rules provide the organizational profile ID; a profile is not a security boundary within the same operating‑system account.
- The plan/approval/revision pattern from contact, calendar, and finance services is reused.
- The new store remains a standalone capability reusable for later modules.

## Declarative V1 input format

A text file describes exactly one inventory record:

```text
Gegenstand: Reis
Bereich: Küche
Ort: Vorratsschrank
Einheit: kg
Menge: 1.5
Mindestbestand: 2
Erfasst-am: 2026-08-22
Ablaufdatum: 2027-02-28
```


`Ablaufdatum` is optional. Quantities are read as decimal and stored internally as integer thousandths of the specified unit. More than three fractional digits, negative values, duplicate fields and unknown mandatory fields result in `review_required`; FolderHome does not round silently.

## New encapsulated blueprint

```text
expliziter Bestandsordner + Profil + lokale Sensitivitätsfreigabe
  → doc-services read-only extrahieren
  → genau ein Inventarereignis je Datei mit Zeilenevidenz bilden
  → gleichzeitige widersprüchliche Beobachtungen desselben Gegenstands blockieren
  → gegen aktuelle Inventarrevision planen
  → exakte Approval-Datei + State-Gate
  → Quellhash und Revision erneut prüfen
  → Ereignisse und Audit gemeinsam append-only schreiben

Inventarstore + Profil + expliziter Stichtag
  → je Gegenstand die neueste belegte Beobachtung bestimmen
  → Unterbestand, abgelaufen und läuft-bald-ab als Kandidaten ableiten
  → Fehlmenge und Evidenz ausgeben, aber keinen Einkauf auslösen
```


New packages:

- `folderhome.contracts.inventory`
- `folderhome.application.household_inventory`
- `folderhome.capabilities.inventory_store`

## Security and product boundaries

- No silent overwriting and no SQL‑`DELETE`.
- No automatic purchasing, no ordering, and no supplier contact.
- No claim to completeness of a household inventory.
- Expiration and purchase hints are candidates requiring verification.
- Source documents remain unchanged; the store contains normalized fields and provenance, no raw document text.
- Family profiles organize data views, but do not replace operating‑system account separation.

## Acceptance

- Parser and decimal accuracy
- Data‑privacy status and line evidence
- Conflict‑free read‑only planning
- Approval, revision, source‑hash and state gates
- Atomic append‑only store
- Profile‑separated current view and complete history
- Minimum stock and expiration candidates with explicit cut‑off date
- Synthetic CLI end‑to‑end run

---
