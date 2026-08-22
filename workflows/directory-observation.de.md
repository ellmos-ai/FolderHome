# Workflow: Beobachteten Ordner scannen und Korrektur prüfen

[English](./directory-observation.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc, später pro geplantem Scanlauf
> **Duration:** abhängig von Dateizahl und Dateigröße

## Purpose

Einen deklarierten Ordner ohne Dokumentrohtext gegen seinen letzten
verifizierten Checkpoint prüfen, Änderungen erklären und belegte manuelle
Verschiebungen als prüfpflichtige Lernkandidaten ausgeben.

## Preconditions

- `folderhome.watched-folders.v1` enthält Root, Profil, Bereich, Intervall,
  Rekursion und Aktivstatus.
- Lokaler Zustandsordner und Beobachtungszeitpunkt sind ausdrücklich gewählt.
- Der Beobachtungszeitpunkt ist ein ISO-Zeitpunkt mit Zeitzone.
- Das State-Gate gilt nur für die neuen Snapshot-Dateien.
- Für Korrekturlernen liegt eine JSON-Datei im Schema
  `folderhome.placement-receipts.v1` vor.

## Steps

1. **Beobachtung auswählen** — Konfiguration laden und genau eine aktive
   `watch_id` mit aufgelöstem Root wählen.
2. **Letzten Checkpoint prüfen** — vorhandene Snapshot-IDs validieren und den
   zeitlich neuesten eindeutigen Zustand desselben Roots bestimmen.
3. **Aktuellen Zustand erfassen** — expliziten Zeitpunkt verwenden und nur
   Pfad, Größe, Dateisystemzeit, Hash und Symlink-Auslassungen erheben.
4. **Zustände vergleichen** — der Scan unterscheidet Hinzufügen, Entfernen,
   Inhaltsänderung, Metadatenänderung und eindeutigen Move.
5. **Ablagebelege zuordnen** — optionale Belege verbinden frühere Ablagen
   mit Hash, Ausgangspfad, Profil, Bereich und Regelquellen.
6. **Scanbericht prüfen** — Intervallfälligkeit, Diff und passende
   Lernkandidaten kontrollieren; `automatic_promotion` muss `false` sein.
7. **Checkpoint entscheiden** — ohne `--approve-state-write` bleibt der Lauf
   read-only; mit Gate wird nach erneutem Historienabgleich genau ein neuer
   Snapshot ergänzt.

## Exit-Criteria

- [ ] Beobachtung und alle vorhandenen Snapshot-IDs wurden validiert.
- [ ] Vorheriger und aktueller Snapshot gehören zum selben Quellordner.
- [ ] Mehrdeutige Hash-Duplikate wurden nicht als Move behauptet.
- [ ] Jeder Lernkandidat besitzt einen passenden früheren Ablagebeleg.
- [ ] `automatic_promotion` ist global und je Kandidat `false`.
- [ ] Dokumente und Profilregeln wurden nicht verändert.

## Fallstricke

- Ein gleicher Hash beweist bei mehreren identischen Kopien keinen bestimmten
  Quell- und Zielpfad; deshalb bleibt dieser Fall absichtlich mehrdeutig.
- Ein beobachteter Move ohne Ablagebeleg kann eine Nutzerhandlung zeigen,
  belegt aber keinen Fehler einer FolderHome-Regel.
- Ein vor Intervallablauf gestarteter Scan ist zulässig, weist aber
  `interval_due=false` aus; Phase 10 installiert keinen Scheduler.
- `mtime_ns` ist Dateisystemmetadatum und kein Dokument- oder Vertragsdatum.
- Der Snapshot enthält Hashes und Pfade; er ist inhaltsfrei, aber weiterhin
  schützenswerte Haushaltsmetadaten.

## Verwandte

- [`./document-action-plan.md`](document-action-plan.de.md) — Herkunft der
  später benötigten Ablagebelege
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-9-/Phase-10-Datenfluss

## Historie

- **2026-08-21** — Nach Phase-9-End-to-End-Abnahme erstellt
- **2026-08-21** — Auf deklarative Phase-10-Scanläufe erweitert
