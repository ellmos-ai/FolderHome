# Workflow: Medikamentenplan und bestätigte Einnahme

> **Last verified:** 2026-08-22
> **Frequency:** nach ausdrücklich bereitgestelltem Plan oder einer Einnahmebestätigung
> **Duration:** wenige Sekunden

## Purpose

Einen bereitgestellten Medikamentenplan lokal und evidenzgebunden übernehmen,
die organisatorische Tagesansicht lesen und eine ausdrückliche Einnahme als
separates append-only Ereignis bestätigen.

## Preconditions

- Planordner und separater FolderHome-State sind festgelegt.
- Profil und doc-services-Pin sind gültig.
- Jede Eingabedatei entspricht dem deklarativen V1-Format.
- Die Daten sind ausdrücklich bereitgestellt; FolderHome prüft keine
  medizinische Richtigkeit.

## Steps

1. **Plan bilden** — `medication plan` mit Quelle, State, Profil und
   `--approve-sensitive-local-read` ausführen.
2. **Evidenz prüfen** — Präparat, dokumentierte Dosis/Einheit, Zeitpunkt,
   Zeitzone, Wochentage, Gültigkeit, Bestandsbezug, Dokumenthash und
   Zeilennummern kontrollieren.
3. **Konflikte prüfen** — widersprüchliche Versionen mit gleichem Beginn und
   Zeitpunkt nicht übergehen.
4. **Importfreigabe erstellen** — Plan-ID, Medikamentenrevision, konkrete
   Aktions-IDs, Approval-ID und Zeitzonenzeitpunkt festhalten.
5. **Zeitplan übernehmen** — `medication apply` mit identischen Eingaben,
   Approval-Datei und `--approve-state-write` ausführen.
6. **Tagesansicht lesen** — `medication day` mit Datum und explizitem
   Auswertungszeitpunkt ausführen. Optional kann ein FolderHome-Inventarstate
   nur auf vorhandene Bestandsbelege geprüft werden.
7. **Dosis auswählen** — ausschließlich die stabile Dosis-ID aus dieser
   Tagesansicht verwenden.
8. **Bestätigung erstellen** — Confirmation-ID, aktuelle
   Medikamentenrevision, Dosis-ID, Zeitplan-ID, geplanten Tag und tatsächlichen
   Bestätigungszeitpunkt in `folderhome.medication-intake-confirmation.v1`
   festhalten.
9. **Einnahme bestätigen** — `medication confirm` mit Bestätigungsdatei und
   `--approve-state-write` ausführen.
10. **Historie prüfen** — `medication history` muss Zeitplan und genau ein
    Einnahmeereignis zeigen; der Inventarstate bleibt unverändert.

## Exit-Criteria

- [ ] Plan, Approval, Medikamentenrevision und Quellhashes stimmen überein.
- [ ] Zeitplanversion und Audit wurden gemeinsam oder gar nicht ergänzt.
- [ ] Tagesansicht schrieb keinen State.
- [ ] Bestätigung ist an Dosis, Zeitplan, Tag und Revision gebunden.
- [ ] Eine Wiederholung erzeugt kein zweites Einnahmeereignis.
- [ ] Kein Bestand und keine Quelle wurden verändert.

## Fallstricke

- FolderHome entscheidet keine Dosis und prüft keine Wechselwirkungen.
- „Bestätigung ausstehend“ ist eine organisatorische Statusanzeige, keine
  medizinische Warnung oder Aussage über tatsächliche Einnahme.
- `bei Bedarf` wird in V1 nicht automatisch terminiert.
- Es werden keine Erinnerungen, Nachrichten, Kalenderaktionen oder
  Bestellungen ausgelöst.
- Profile sind keine Zugriffsgrenze innerhalb desselben Betriebssystemkontos.

## Verwandte

- [`../docs/phase21-medication-intake-reuse-and-plan.md`](../docs/phase21-medication-intake-reuse-and-plan.md)
- [`./inventory-import.md`](./inventory-import.md) — lokaler Haushaltsbestand
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-21-Datenfluss

## Historie

- **2026-08-22** — Nach Phase-21-End-to-End-Implementierung erstellt
