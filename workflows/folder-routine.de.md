# Workflow: Beobachteten Ordner geplant aufräumen

[English](./folder-routine.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** nach einem explizit ausgelösten Scanzeitpunkt
> **Duration:** abhängig von Dateizahl und Extraktionsformaten

## Purpose

Einen deklarierten Beobachtungsordner gegen seinen letzten Checkpoint prüfen,
eine fällige Änderungsmenge oder den vollständigen Bestand planen und einen
bewusst freigegebenen Batch mit anschließendem Checkpoint ausführen.

## Preconditions

- Watch-ID, Profilregeln, Zielwurzel, Stichtag und Beobachtungszeit sind explizit.
- Die Zielwurzel liegt außerhalb des beobachteten Ordners.
- Der letzte Checkpoint ist identitätsgeprüft und eindeutig.
- Für eine Ausführung liegen Batchfreigabe, Datei-Gate und State-Gate vor.

## Steps

1. **Watch laden** — Root, Profil, Bereich, Intervall, Rekursion und Aktivstatus prüfen.
2. **Read-only scannen** — aktuellen inhaltsfreien Snapshot gegen den letzten
   Checkpoint vergleichen, ohne einen neuen Checkpoint zu schreiben.
3. **Modus anwenden** — `changes` nur bei Fälligkeit auf neue, geänderte und
   eindeutig verschobene Pfade begrenzen; `full` ausdrücklich auf alle Dateien anwenden.
4. **Cleanup planen** — nur die ausgewählten Pfade durch die ordnerweite
   Konflikt- und Dokumentaktionsplanung führen.
5. **Plan prüfen** — Routine-ID, Status, Auswahl, Batch-ID, Konflikte und
   freigabefähige Dokumente kontrollieren.
6. **Batch freigeben** — eine separate Approval-Datei für die bewusst
   ausgewählten Dokument-, Plan-, Hash- und Aktions-IDs erstellen.
7. **Ausführung preflighten** — erwarteten letzten Checkpoint und vollständige
   Scan-ID ohne Schreibzugriff erneut bestätigen.
8. **Batch ausführen** — Intent schreiben und die freigegebenen
   Einzeltransaktionen ausführen.
9. **Checkpoint abschließen** — nur nach Batcherfolg den resultierenden
   Ordnerzustand unveränderlich speichern und den Routinebericht schreiben.
10. **Fehler prüfen** — bei gescheitertem Checkpoint müssen Dateiaktionen
    rückwärts laufen und der Bericht `rolled_back` oder `failed` ausweisen.

## Exit-Criteria

- [ ] `routine-plan` hat weder Quellen, Ziele noch State verändert.
- [ ] `not_due`, `no_changes` und `planned` sind eindeutig unterscheidbar.
- [ ] Der Vollmodus wurde ausdrücklich gewählt und umgeht keine Freigabe.
- [ ] Eine Ausführung stimmt mit Routine-, Scan- und Batchzustand überein.
- [ ] Ein erfolgreicher Lauf besitzt Routine-Intent, Batchaudit und Checkpoint.
- [ ] Ein Checkpointfehler hinterlässt einen belegten Rückwegstatus.

## Fallstricke

- Ein Routinenplan ist keine Freigabe und schreibt auch keinen Checkpoint.
- Reine Zeitstempeländerungen lösen im Änderungsmodus keine Verarbeitung aus.
- Ein Ziel im beobachteten Root kann eine endlose Wiederaufnahme erzeugen und
  wird deshalb blockiert.
- Ein geänderter Ordner oder konkurrierender Checkpoint entwertet den Plan.
- Phase 13 registriert keinen Betriebssystem-Scheduler.

## Verwandte

- [`./directory-observation.md`](directory-observation.de.md) — Scan und Checkpoint
- [`./folder-cleanup.md`](folder-cleanup.de.md) — ordnerweiter Batchplan
- [`./document-action-execution.md`](document-action-execution.de.md) — Undo
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-13-Datenfluss

## Historie

- **2026-08-21** — Nach Phase-13-End-to-End-Abnahme erstellt
