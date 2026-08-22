# Phase 21 — Medikamentenplan und bestätigte Einnahme

**Status:** lokal abgeschlossen, 198 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel

FolderHome übernimmt ausdrücklich bereitgestellte Medikamentenpläne als
organisatorische, evidenzgebundene Daten. Für einen gewählten Tag zeigt es
geplante Einnahmen und getrennt davon ausdrücklich bestätigte Einnahmen. Es
entscheidet weder Präparat noch Dosis und verändert keinen Medikamentenbestand
automatisch.

## Wiederverwendung

### UpToday Health Engine

- lokaler sauberer Checkout: `C:\_Local_DEV\repos\UpToday`
- geprüfte Revision: `7582ca87e17e458bb99a7379d2c54003c15415a4`
- Lizenz: MIT
- fokussierte Medikamenten-/Einnahmeabnahme: 6 Tests grün
- wiederverwendete Trennung: Medikament, Zeitplan, Tagesdosis und bestätigte
  Einnahme; doppelte Bestätigung darf nicht doppelt wirken

Nicht geladen werden der globale DB-Singleton, direkte `UPDATE`-/`DELETE`-
Operationen, der beim Lesen schreibende Tagesplan, Fließkomma-Bestände,
implizites `datetime.now()` und automatische Bestandsreduktion.

### Gesundheit-Skill und Health-Assist-Bundle

- `gesundheit` 2.0.0, Repository `ellmos-ai/skills`, Revision
  `0317f32310eed11d21f603cb6f22a689485af226`, MIT
- Health-Assist-Bundle 1.0.0: registrierter deklarativer Entwurf ohne
  Runtime-Autorität

Wiederverwendet werden nur ausdrücklich bereitgestellte Informationen,
sachliche Organisation und die Grenze „Organisation only“. Diagnose,
Therapie, Verordnung und Dosisentscheidung bleiben ausgeschlossen.

## Deklaratives V1-Eingabeformat

Eine Textdatei beschreibt genau einen Einnahmezeitpunkt:

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

`Gültig-bis` ist optional. Dosiswerte werden ohne Rundung als ganzzahlige
Tausendstel der dokumentierten Einheit gespeichert. `Wochentage` akzeptiert
`täglich` oder eine kommagetrennte Auswahl deutscher Wochentage. Pläne „bei
Bedarf“ werden in V1 nicht automatisch terminiert und bleiben
`review_required`.

## Neuer gekapselter Bauplan

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

Neue Pakete:

- `folderhome.contracts.medication`
- `folderhome.application.medication_intake`
- `folderhome.capabilities.medication_store`

## Sicherheits- und Produktgrenzen

- Keine Diagnose, Verordnung, Dosisberechnung oder Wechselwirkungsprüfung.
- Keine Aussage, dass ein Plan medizinisch richtig oder aktuell ist.
- Keine automatische Erinnerung, Nachricht, Kalenderaktion oder Bestellung.
- Eine Bestätigung dokumentiert nur eine ausdrückliche Nutzereingabe; sie ist
  kein medizinischer Wirksamkeitsnachweis.
- Bestände werden nicht automatisch reduziert. Ein Abgleich ist nur ein
  Hinweis auf vorhandene oder fehlende lokale Evidenz.
- Kein stilles Überschreiben und kein SQL-`DELETE`.
- Familienprofile sind keine Zugriffsgrenze innerhalb desselben OS-Kontos.

## Abnahme

- Parser, Wochentage, Zeitzone und Dezimalexaktheit
- Datenschutzstatus und Zeilenevidenz
- konfliktfreie read-only Planung
- Approval-, Revisions-, Quellhash- und State-Gates
- append-only Zeitpläne, Einnahmen und Audit
- Tagesansicht ohne Write-on-read
- idempotente Einnahmebestätigung
- optionaler Bestandsabgleich ohne Bestandsänderung
- synthetischer CLI-End-to-End-Lauf

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
