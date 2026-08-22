# Workflow: Dokumentaktion freigeben und rückgängig machen

[English](./document-action-execution.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc nach menschlicher Planprüfung
> **Duration:** wenige Sekunden pro Dokument auf demselben Datenträger

## Purpose

Einen vorher geprüften Rename-/Move-Präfix für genau ein Dokument
plan-, hash- und aktionsgebunden ausführen, lückenlos protokollieren und bei
Bedarf über eine getrennte Freigabe zurückführen.

## Preconditions

- Quelle, Profilregeln, Zielwurzel und `as_of` entsprechen dem geprüften Plan.
- Die Plan-ID und jede freizugebende Aktions-ID wurden aus `documents plan`
  abgelesen und bewusst ausgewählt.
- Quelle und Ziel liegen auf demselben Datenträger; Cross-Volume-Fallback ist
  nicht erlaubt.
- Lokaler State-Ordner und Datei-Schreibgate sind ausdrücklich gewählt.
- Die Freigabe gilt nicht für Konvertierung, Papierkorb, Review oder
  blockierte Aktionen.

## Steps

1. **Plan erneut bilden** — `documents execute` extrahiert die Quelle erneut,
   löst dieselben Profilregeln auf und berechnet die vollständige `plan_id`.
2. **Freigabe binden** — `--approve-plan-id` und alle wiederholten
   `--approve-action-id` müssen einen lückenlosen ausführbaren Planpräfix
   bilden; `--approved-at` braucht eine Zeitzone.
3. **Quelle verifizieren** — Dokument-ID und SHA-256 müssen weiterhin zum
   ursprünglichen Pfad passen.
4. **Gesamte Zielkette prüfen** — jedes Ziel muss unbesetzt, symlinkfrei und
   entsprechend der Aktionsart innerhalb des erlaubten Bereichs sein.
5. **Intent schreiben** — vor der ersten Dateiaktion wird im State-Ordner ein
   neues `000-intent.json` ohne Rohtext veröffentlicht.
6. **Schritte ausführen** — der Transaktionskern legt das Ziel ohne
   Überschreiben an, prüft dessen Hash und entfernt erst danach die Quelle.
7. **Abschluss prüfen** — `100-completed.json` weist Planprovider, Executor,
   Pfade, Hashes, Regeln und Ablagebeleg aus.
8. **Optional Undo freigeben** — `documents undo` benötigt Abschlussdatei,
   Ausführungs-ID, Hash, neue Freigabe-ID, Zeitpunkt und Schreibgate.
9. **Undo verifizieren** — Zielhash und Intent müssen passen; der Ursprung
   darf nicht existieren. Erst dann wird der inverse Move ausgeführt.

## Exit-Criteria

- [ ] Plan-ID, Quellhash und freigegebene Aktions-IDs stimmen exakt überein.
- [ ] Kein bestehendes Ziel wurde überschrieben oder umbenannt.
- [ ] Intent und Abschlussbericht liegen append-only im Ausführungsordner.
- [ ] Der Ablagebeleg enthält Root, Relativpfad, Profil, Bereich und Regeln.
- [ ] Planprovider und tatsächlicher Executor sind getrennt ausgewiesen.
- [ ] Ohne Datei-Schreibgate wurde keine Quelle verändert.
- [ ] Nach erfolgreichem Undo liegt der ursprüngliche Inhalt am Ursprung und
      nicht mehr am Endziel.

## Fallstricke

- Eine Plan-ID ist nicht selbst die Freigabe; konkrete Aktions-IDs und das
  Dateisystem-Gate sind zusätzlich erforderlich.
- Ein nach der Planung geänderter Dateiinhalt entwertet die Freigabe.
- FCSA bestätigt Sortiersemantik im Dry-Run, führt diesen exakten
  Einzeldokument-Move aber nicht live aus. Der Bericht nennt deshalb den
  FolderHome-Transaktionskern als Executor.
- Cross-Volume-Moves werden nicht durch Kopieren-und-Löschen ersetzt.
- Undo ist kein Überschreiben: Existiert der Ursprung erneut, wird blockiert.

## Verwandte

- [`./document-action-plan.md`](document-action-plan.de.md) — Plan und
  Regelprovenienz erzeugen
- [`./directory-observation.md`](directory-observation.de.md) — spätere
  Nutzerkorrekturen anhand des Ablagebelegs erkennen
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-11-Datenfluss

## Historie

- **2026-08-21** — Nach Phase-11-End-to-End-Roundtrip erstellt
