# Workflow: Dokumentaktionsplan aus Profilregeln erstellen

[English](./document-action-plan.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc oder vor jeder späteren Dateiausführung
> **Duration:** wenige Sekunden pro Dokument

## Purpose

Ein synthetisches oder ausdrücklich gewähltes Dokument gegen die Regeln eines
Organisationsprofils prüfen und einen nachvollziehbaren Plan erzeugen, ohne
die Quelle, Zielordner oder den produktiven FCSA-Zustand zu verändern.

## Preconditions

- `household.json` und Profildateien sind mit `profiles validate` geprüft.
- Das Profil liegt innerhalb desselben deklarierten OS-Kontos; es ist keine
  Zugriffsgrenze.
- Quellpfad, Zielwurzel und Stichtag sind ausdrücklich angegeben.
- doc-services und FCSA entsprechen ihren gepinnten, sauberen Checkouts.

## Steps

1. **Regeln auflösen** — global → Bereich → Profil → Profilbereich; Konflikte
   auf derselben Stufe blockieren.
2. **Quelle read-only extrahieren** — doc-services arbeitet ohne OCR und ohne
   Lernschreibzugriff; der Aktionsplan übernimmt keinen Rohtext.
3. **Benennung prüfen** — nur feste Platzhalter sind erlaubt; Pfadtrenner,
   reservierte Namen und Ausbruch aus der Zielwurzel blockieren.
4. **Aktionen projizieren** — Benennung, Sortierung, Konvertierung,
   Originalbehandlung und Aufbewahrung bleiben getrennte Schritte.
5. **Fristen prüfen** — nur der explizite `as_of`-Stichtag entscheidet, nicht
   eine versteckte Systemzeit.
6. **Konflikte stoppen** — gleichzeitig fällige Sortier-, Archivierungs- oder
   Papierkorbziele werden blockiert und an Review übergeben.
7. **FCSA bestätigen** — ausführbare Move-/Papierkorbschritte laufen nur durch
   den temporären FCSA-Dry-Run; Hard Delete bleibt deaktiviert.
8. **Unverändertheit prüfen** — Quelle ist bytegleich, Zielwurzel und
   produktiver Provider-State wurden nicht angelegt oder verändert.

## Exit-Criteria

- [ ] Jede Aktion nennt Quellregeln, Provider, Capability, Gate und Undo.
- [ ] Alle Dateisystem-Gates stehen auf `granted=false`.
- [ ] Kein Rohtext erscheint im JSON-Plan.
- [ ] Fehlende Provider und konkurrierende Ziele stehen sichtbar auf
      `blocked` oder `review_required`.
- [ ] FCSA bestätigt nur `move`, `duplicate_check` oder `delete-to-trash` im
      Dry Run; `allow_hard_delete` ist false.
- [ ] Quelle und Zielzustand sind unverändert.

## Fallstricke

- Ein Plan ist keine Ausführungsfreigabe.
- Eine profilbezogene Regel ist keine Dateiberechtigung.
- `modified_at` ist nur ein organisatorisches Fristsignal, keine rechtliche
  Aussage zur Aufbewahrungspflicht.
- Ein Konvertierungswunsch bleibt bis zu einem geprüften Provider blockiert.

## Verwandte

- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-6-Datenfluss
- [`../examples/profiles/README.md`](../examples/profiles/README.de.md) — synthetische Profile
- [`./fcsa-dry-run.md`](fcsa-dry-run.de.md) — Provider-Dry-Run
- [`./document-action-execution.md`](document-action-execution.de.md) —
  getrennte plan- und hashgebundene Ausführung mit Undo

## Historie

- **2026-08-21** — Nach Phase-6-End-to-End-Abnahme erstellt
- **2026-08-21** — Phase-11-Ausführungsworkflow verknüpft
