# Workflow: Mehrere Beobachtungsroutinen read-only bewerten

> **Last verified:** 2026-08-21
> **Frequency:** bei jedem geplanten Scheduler- oder manuellen Prüflauf
> **Duration:** abhängig von Watch- und Dokumentzahl

## Purpose

Alle aktivierten Watches zu einem expliziten Zeitpunkt planen, Zustände
vergleichbar bündeln und Konflikte über Watch-Grenzen erkennen, ohne Dateien,
Checkpoints oder Betriebssystem-Scheduler zu verändern.

## Preconditions

- Watch-, Binding- und Profilkonfiguration sind lokal lesbar.
- Jeder aktive Watch besitzt höchstens ein Binding.
- Beobachtungszeit, Stichtag und State-Verzeichnis sind explizit.
- Der doc-services-Provider entspricht dem gepinnten Manifest.

## Steps

1. **Watches laden** — IDs, Roots, Profile, Bereiche und Intervalle validieren.
2. **Bindings laden** — Zielwurzeln relativ zur Binding-Datei auflösen und
   `changes`-/`full`-Modus prüfen.
3. **Zuordnung prüfen** — mehrfache und unbekannte Bindings ablehnen; fehlende
   oder deaktivierte Bindings sichtbar blockieren.
4. **Einzelroutinen planen** — je aktivem Watch den Phase-13-Plan vollständig
   read-only erzeugen.
5. **Status zuordnen** — Ergebnisse als `ready`, `not_due`, `empty` oder
   `blocked` klassifizieren.
6. **Gesamtmenge prüfen** — Eingangsüberlappungen, Ziele in anderen
   Watch-Eingängen und gemeinsame Aktionsziele blockieren.
7. **Queue ausgeben** — deterministische ID, Zusammenfassung und Planbelege
   über stdout serialisieren.
8. **Side-Effects prüfen** — `side_effects=[]` und
   `scheduler_registered=false` müssen erhalten bleiben.

## Exit-Criteria

- [ ] Jeder aktive Watch erscheint genau einmal in der Queue.
- [ ] Fehlende Bindings und Cross-Watch-Konflikte sind sichtbar blockiert.
- [ ] Die Queue enthält keinen Dokumentrohtext.
- [ ] State, Quellen und Ziele sind byte- beziehungsweise pfadgleich geblieben.
- [ ] Es wurde keine Betriebssystemaufgabe registriert.

## Fallstricke

- Ein `ready`-Eintrag ist keine Batchfreigabe.
- Zwei einzeln konfliktfreie Routinen können dasselbe Ziel verwenden.
- Ein Ziel im Eingang eines anderen Watch erzeugt eine spätere
  Wiederaufnahmeschleife.
- Shell-Umleitung oder ein externer Scheduler kann selbst Side-Effects haben;
  diese gehören nicht zum `routine-queue`-Vertrag.

## Verwandte

- [`./folder-routine.md`](./folder-routine.md) — einzelne Beobachtungsroutine
- [`./folder-cleanup.md`](./folder-cleanup.md) — ordnerweiter Batchplan
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-14-Datenfluss

## Historie

- **2026-08-21** — Nach Phase-14-End-to-End-Abnahme erstellt
