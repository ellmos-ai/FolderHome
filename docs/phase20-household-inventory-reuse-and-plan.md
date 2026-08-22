# Phase 20 — Haushalts- und Lagerbestand

**Status:** lokal abgeschlossen, 189 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel

FolderHome übernimmt ausdrücklich bereitgestellte Bestandsaufnahmen in einen
lokalen, append-only geführten Haushaltsbestand. Aktueller Bestand,
Mindestbestand, Ablaufdatum und Einkaufsbedarf bleiben nach Profil, Bereich,
Ort und Quelldokument belegbar.

## Wiederverwendung

### UpToday

- lokaler sauberer Checkout: `C:\_Local_DEV\repos\UpToday`
- geprüfte Revision: `7582ca87e17e458bb99a7379d2c54003c15415a4`
- Lizenz: MIT
- fokussierte Vertragsabnahme: 4 Tests grün
- wiederverwendete Fachbegriffe: Artikel, Kategorie/Bereich, Ort, Basiseinheit,
  Bestand, Mindestbestand und prüfbare Einkaufsableitung

UpToday wird nicht als Runtime-Provider geladen. Sein bisheriger
`InventoryEngine` verwendet Fließkommazahlen, einen globalen DB-Singleton,
direkte `UPDATE`-/`DELETE`-Operationen und `date.today()`. Diese Eigenschaften
passen nicht zu FolderHomes revisionsgebundenem, deterministischem
Append-only-Vertrag. FolderHome kopiert keinen UpToday-Quellcode.

### Bestehende FolderHome-Bausteine

- doc-services extrahiert die ausdrücklich gewählten Dateien read-only.
- Profilregeln liefern die organisatorische Profil-ID; ein Profil ist keine
  Sicherheitsgrenze innerhalb desselben Betriebssystemkontos.
- Das Plan-/Approval-/Revision-Muster aus Kontakt-, Kalender- und
  Finanzdiensten wird wiederverwendet.
- Der neue Store bleibt als eigenständige Capability für spätere Module
  wiederverwendbar.

## Deklaratives V1-Eingabeformat

Eine Textdatei beschreibt genau eine Bestandsaufnahme:

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

`Ablaufdatum` ist optional. Mengen werden dezimal gelesen und intern als
ganzzahlige Tausendstel der angegebenen Einheit gespeichert. Mehr als drei
Nachkommastellen, negative Werte, doppelte Felder und unbeklare Pflichtfelder
führen zu `review_required`; FolderHome rundet nicht still.

## Neuer gekapselter Bauplan

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

Neue Pakete:

- `folderhome.contracts.inventory`
- `folderhome.application.household_inventory`
- `folderhome.capabilities.inventory_store`

## Sicherheits- und Produktgrenzen

- Kein stilles Überschreiben und kein SQL-`DELETE`.
- Kein automatischer Einkauf, keine Bestellung und kein Lieferantenkontakt.
- Kein Anspruch auf Vollständigkeit eines Haushaltsbestands.
- Ablauf- und Einkaufshinweise sind prüfpflichtige Kandidaten.
- Quelldokumente bleiben unverändert; der Store enthält normalisierte Felder
  und Provenienz, keinen Dokumentrohtext.
- Familienprofile organisieren Datensichten, ersetzen aber keine
  Betriebssystemkontentrennung.

## Abnahme

- Parser und Dezimalexaktheit
- Datenschutzstatus und Zeilenevidenz
- konfliktfreie read-only Planung
- Approval-, Revisions-, Quellhash- und State-Gates
- atomarer Append-only-Store
- profilgetrennte aktuelle Sicht und vollständige Historie
- Mindestbestand und Ablaufkandidaten mit explizitem Stichtag
- synthetischer CLI-End-to-End-Lauf

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
