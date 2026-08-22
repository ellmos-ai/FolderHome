# Workflow: Haushaltsbestand lokal ergänzen

> **Last verified:** 2026-08-22
> **Frequency:** nach einer ausdrücklich dokumentierten Bestandsaufnahme
> **Duration:** wenige Sekunden pro Bestandsordner

## Purpose

Bereitgestellte Bestandsbeobachtungen prüfen, revisionsgebunden in den
lokalen Append-only-Inventarstore übernehmen und anschließend aktuelle
Bestände sowie Einkaufs- und Ablaufkandidaten anzeigen.

## Preconditions

- Bestandsordner und separater FolderHome-State sind festgelegt.
- Profil und doc-services-Pin sind gültig.
- Jede Eingabedatei entspricht dem deklarativen V1-Format.
- Eine lokale sensible Verarbeitung wurde bei Bedarf bewusst erlaubt.

## Steps

1. **Plan bilden** — `inventory plan` mit Quelle, State, Profil und bei Bedarf
   `--approve-sensitive-local-read` ausführen.
2. **Evidenz prüfen** — Gegenstand, Bereich, Ort, Einheit, Menge,
   Mindestbestand, Erfassungsdatum, optionales Ablaufdatum, Dokumenthash und
   Zeilennummern kontrollieren.
3. **Konflikte prüfen** — `blocked` bei widersprüchlichen Beobachtungen
   desselben Gegenstands und Tages nicht übergehen.
4. **Freigabe erstellen** — Plan-ID, Inventarrevision, konkrete Aktions-IDs,
   Approval-ID und Zeitzonenzeitpunkt festhalten.
5. **Plan erneut aufbauen** — `inventory apply` mit identischen Eingaben und
   Approval-Datei starten.
6. **State freigeben** — nur für diese lokale Transaktion
   `--approve-state-write` setzen.
7. **Ergebnis prüfen** — neue Ereignis-IDs, Revision und unveränderte Quellen
   kontrollieren.
8. **Aktuellen Bestand lesen** — `inventory current` mit Profil und optional
   Bereich/Stichtag ausführen.
9. **Historie lesen** — `inventory history` zeigt alle append-only Ereignisse
   eines Profils, Bereichs oder Gegenstands.
10. **Bedarf prüfen** — `inventory needs` mit explizitem Stichtag und
    Ablaufhorizont ausführen; keinen automatischen Einkauf ableiten.

## Exit-Criteria

- [ ] Plan, Approval, Inventarrevision und Quellhashes stimmen überein.
- [ ] Ereignisse und Audit wurden gemeinsam oder gar nicht ergänzt.
- [ ] Quelldokumente blieben bytegleich.
- [ ] Aktuelle Sicht und Historie sind nach Profil nachvollziehbar.
- [ ] Mindestbestand und Ablaufdatum erscheinen nur als prüfpflichtige Kandidaten.

## Fallstricke

- Mengen verwenden höchstens drei Nachkommastellen und werden nicht gerundet.
- Eine neue Beobachtung überschreibt keine ältere; die aktuelle Sicht wird aus
  der Ereignishistorie abgeleitet.
- `--approve-sensitive-local-read` erlaubt keine externe Weitergabe.
- Profile organisieren Ansichten innerhalb desselben Betriebssystemkontos.
- FolderHome bestellt nichts und behauptet keinen vollständigen Haushalt.

## Verwandte

- [`../docs/phase20-household-inventory-reuse-and-plan.md`](../docs/phase20-household-inventory-reuse-and-plan.md)
- [`./document-library.md`](./document-library.md) — lokale Dokumentextraktion
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-20-Datenfluss

## Historie

- **2026-08-22** — Nach Phase-20-End-to-End-Implementierung erstellt
