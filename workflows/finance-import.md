# Workflow: Kontoauszüge lokal und centgenau übernehmen

> **Last verified:** 2026-08-22
> **Frequency:** nach Bereitstellung neuer Kontoauszüge
> **Duration:** wenige Sekunden pro Auszugsordner

## Purpose

Ausdrücklich bereitgestellte Kontoauszüge prüfen, revisionsgebunden in den
lokalen Finanzstore übernehmen und anschließend Abdeckung, Bewegungen und
wiederkehrende Kostenkandidaten auswerten.

## Preconditions

- Auszugsordner und separater FolderHome-State sind festgelegt.
- Profil und doc-services-Pin sind gültig.
- Die Auszüge entsprechen dem deklarierten centgenauen V1-Format.
- Lokale sensible Verarbeitung wurde bewusst erlaubt.

## Steps

1. **Plan bilden** — `finance plan` mit Quelle, State, Profil und
   `--approve-sensitive-local-read` ausführen.
2. **Evidenz prüfen** — Kontokennung, maskierte Endung, Zeitraum, Salden,
   Buchungen, Referenzen, Dokumenthash und Zeilennummern kontrollieren.
3. **Saldo prüfen** — interne Arithmetik und Kontinuität zu angrenzenden
   Auszügen nachvollziehen; `blocked` nicht übergehen.
4. **Freigabe erstellen** — Plan-ID, Finanzrevision, konkrete Aktions-IDs,
   Approval-ID und Zeitzonenzeitpunkt festhalten.
5. **Plan erneut aufbauen** — `finance apply` mit identischen Eingaben und
   Approval-Datei starten.
6. **State freigeben** — ausschließlich für diese lokale Transaktion
   `--approve-state-write` setzen.
7. **Import prüfen** — erzeugte Auszugs-/Buchungs-IDs und neue Revision lesen;
   Quellen müssen bytegleich geblieben sein.
8. **Abdeckung prüfen** — `finance coverage` für den gewünschten Zeitraum
   ausführen und Lücken sichtbar lassen.
9. **Kontoperiode lesen** — `finance period` für Bewegungen und nur belegte
   Grenzsalden verwenden.
10. **Kostenkandidaten prüfen** — `finance recurring` mit explizitem Stichtag
    ausführen und Ergebnis nicht als Vertragsstatus behandeln.

## Exit-Criteria

- [ ] Plan, Approval, Finanzrevision und alle Quellhashes stimmen überein.
- [ ] Auszüge, Buchungen und Audit wurden gemeinsam oder gar nicht ergänzt.
- [ ] Quelldokumente blieben bytegleich.
- [ ] Datenlücken und Saldo-Diskontinuitäten sind sichtbar.
- [ ] Abo-/Kostenstatus und Prognosen sind ausdrücklich nur Kandidaten.

## Fallstricke

- `--approve-sensitive-local-read` erlaubt weder Bankzugriff noch Weitergabe.
- Freie PDF-Layouts werden in V1 nicht erraten; sie brauchen eigene Adapter.
- Gleiche Buchungsreferenzen oder widersprechende Salden blockieren fail-closed.
- Ein regelmäßiger Abbuchungstext beweist keinen aktiven Vertrag.
- Familienprofile organisieren Daten innerhalb desselben OS-Kontos.

## Verwandte

- [`../docs/phase19-finance-reuse-and-plan.md`](../docs/phase19-finance-reuse-and-plan.md)
- [`./document-library.md`](./document-library.md) — lokale Dokumentextraktion
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-19-Datenfluss

## Historie

- **2026-08-22** — Nach Phase-19-End-to-End-Abnahme erstellt
