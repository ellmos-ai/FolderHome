# Workflow: Einen Los Ordner sicher aufräumen

[English](./folder-cleanup.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc, später als Teil einer beobachteten Routine
> **Duration:** abhängig von Dokumentzahl und Extraktionsformaten

## Purpose

Einen ausdrücklich gewählten Ordner vollständig planen, Zielkonflikte über
alle Dokumente erkennen und anschließend nur eine bewusst ausgewählte
Teilmenge mit automatischem Rückweg bei Teilfehlern ausführen.

## Preconditions

- Quellordner, Profil, Bereich, Zielwurzel und `as_of` sind ausdrücklich gewählt.
- Profile und gepinnter doc-services-Checkout sind geprüft.
- Die Planung darf Quellen lesen, aber weder Quellen noch Ziele verändern.
- Eine Batchausführung benötigt eine separate Approval-Datei und das
  Dateisystem-Gate.

## Steps

1. **Ordner erfassen** — relative Pfade deterministisch sortieren; Symlinks
   werden sichtbar ausgelassen.
2. **Dokumente extrahieren** — bekannte Typen read-only über doc-services
   verarbeiten; unbekannte Typen und Fehler mit Hash und Grund festhalten.
3. **Einzelpläne bilden** — für jedes Dokument dieselben Profil-, Plan- und
   Providerverträge wie bei `documents plan` verwenden.
4. **Ziele gemeinsam prüfen** — jedes Zwischen- und Endziel gegen alle
   anderen Pläne und gegen den aktuellen Dateibestand vergleichen.
5. **Batchplan prüfen** — `folders cleanup-plan` muss Batch-ID,
   Dokumentstatus, Konflikte und ausführbare Aktions-IDs ohne Rohtext zeigen.
6. **Teilmenge freigeben** — Approval-Datei mit Batch-ID und je ausgewähltem
   Dokument mit Dokument-ID, Hash, Plan-ID und Aktions-IDs erstellen.
7. **Batch ausführen** — `folders cleanup-execute` baut den Plan erneut auf,
   prüft die Approval-Datei vollständig und schreibt zuerst ein Batch-Intent.
8. **Einzelaudits prüfen** — jedes ausgewählte Dokument nutzt den
   Phase-11-Executor und erzeugt einen eigenen Abschlussbericht.
9. **Batchabschluss prüfen** — nur bei vollständigem Erfolg werden aktive
   Ablagebelege gesammelt; bei Teilfehlern laufen frühere Aktionen rückwärts.

## Exit-Criteria

- [ ] Jede Quelldatei erscheint als `planned`, `blocked`, `noop`, `skipped`
      oder `failed`.
- [ ] Keine Quelle und kein Ziel wurde während `cleanup-plan` verändert.
- [ ] Gemeinsame oder bestehende Ziele sind vor der Freigabe blockiert.
- [ ] Die Approval-Datei enthält ausschließlich bewusst gewählte Dokumente.
- [ ] Erfolgreiche Batches besitzen Intent, Abschlussbericht und je Dokument
      einen Ablagebeleg.
- [ ] Nach `rolled_back` liegen vorher ausgeführte Dokumente wieder an ihren
      Ursprüngen und es gibt keine aktiven Batch-Ablagebelege.

## Fallstricke

- Ein konfliktfreier Einzelplan kann im Gesamtordner trotzdem mit einem
  anderen Ziel oder dessen Quelle kollidieren.
- Dateiname oder Verarbeitungsreihenfolge darf keinen Konflikt still lösen.
- Eine Approval-Datei wird ungültig, sobald sich Quelle, Profilregel oder
  irgendein planrelevantes Feld ändert.
- `rolled_back` ist ein belegter Fehlerausgang, kein erfolgreicher Batch.

## Verwandte

- [`./document-action-plan.md`](document-action-plan.de.md) — Einzelplanung
- [`./document-action-execution.md`](document-action-execution.de.md) —
  Einzeltransaktion und Undo
- [`./directory-observation.md`](directory-observation.de.md) — beobachtete
  Zustände und Korrekturlernen
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-12-Datenfluss

## Historie

- **2026-08-21** — Nach Phase-12-End-to-End-Abnahme erstellt
