# Workflow: Read-only Queue für einen Scheduler vorbereiten

[English](./scheduler-handoff.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** einmal pro Zeitplan sowie bei Konfigurationsänderungen
> **Duration:** Plan unter einer Sekunde; Lauf abhängig von Dokumentzahl

## Purpose

Einen portablen Aufruf und ein Windows-Task-Artefakt erzeugen und einen
headless Queue-Lauf sicher koordinieren, ohne eine Betriebssystemaufgabe zu
registrieren oder Dokumentaktionen auszuführen.

## Preconditions

- Watch-, Binding-, Profil-, State- und Providerpfade sind explizit.
- Taskname, Intervall, IANA-Zeitzone und Startzeitpunkt sind festgelegt.
- Für einen echten Queue-Lauf ist das Scheduler-State-Gate erteilt.
- Eine spätere Installation benötigt eine separate Nutzerentscheidung.

## Steps

1. **Handoff planen** — `scheduler plan` mit sämtlichen Pfaden und dem
   Zeitplan aufrufen.
2. **Identität prüfen** — Schedule-ID, Taskname, Startzeit, Intervall und
   Zeitzone kontrollieren.
3. **Artefakte prüfen** — portable `argv`-Liste und Windows-XML auf lokale
   Pfade, `LeastPrivilege`, `IgnoreNew` und Laufzeitlimit prüfen.
4. **Nichtregistrierung prüfen** — `registration_performed=false`,
   `installation_supported=false` und fehlende Installationsbefehle bestätigen.
5. **Headless Lauf starten** — `scheduler run` nur mit derselben Schedule-ID
   und dem engen Scheduler-State-Gate aufrufen.
6. **Lock prüfen** — ein bestehender Lock muss Exitcode 30 liefern und
   unangetastet bleiben.
7. **Queue prüfen** — `idle`/0, `attention`/10 oder `blocked`/20 anhand des
   serialisierten Queue-Inhalts nachvollziehen.
8. **Abschluss prüfen** — append-only Bericht vorhanden, eigener Lock
   entfernt, Dokumente, Ziele und Checkpoints unverändert.

## Exit-Criteria

- [ ] Der Handoff wurde nur ausgegeben und nicht installiert.
- [ ] Die Schedule-ID stimmt beim Run mit dem neu gebildeten Plan überein.
- [ ] Der Laufbericht belegt Queue, Status und Exitcode.
- [ ] Ein vorhandener Lock wurde nicht entfernt oder überschrieben.
- [ ] Es gab keine Dokument-, Ziel- oder Checkpointänderung.

## Fallstricke

- Ein XML-Artefakt ist noch keine registrierte Windows-Aufgabe.
- Exitcode 10 bedeutet menschlichen Freigabebedarf, nicht technischen Fehler.
- Ein Restlock darf nicht aufgrund seines Alters automatisch gelöscht werden.
- Das State-Gate erteilt keine Batch- oder Dateifreigabe.
- Die Installation bleibt auch dann gesondert, wenn das XML syntaktisch passt.

## Verwandte

- [`./routine-queue.md`](routine-queue.de.md) — read-only Mehrfach-Watch-Queue
- [`./folder-routine.md`](folder-routine.de.md) — freigabepflichtige Ausführung
- [`../docs/phase15-scheduler-handoff-plan.md`](../docs/phase15-scheduler-handoff-plan.de.md)
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-15-Datenfluss

## Historie

- **2026-08-21** — Nach Phase-15-End-to-End-Abnahme erstellt
