# Workflow: Dokumenttermin sicher an Kalender übergeben

> **Last verified:** 2026-08-22
> **Frequency:** bei neuen oder geänderten Dokumenten mit Terminangaben
> **Duration:** wenige Sekunden pro Dokumentordner

## Purpose

Gelabelte Termindaten aus einem ausdrücklich gewählten Dokumentordner prüfen
und nach exakter Freigabe in den lokalen FolderHome-Kalender oder als neue
ICS-Dateien für UpToday übernehmen.

## Preconditions

- Dokumentordner, Kalenderkonfiguration, Profile und separater State sind festgelegt.
- Die doc-services-Revision entspricht dem gepinnten Manifest.
- Bei `review_required` ist die lokale sensible Verarbeitung bewusst erlaubt.
- Für ICS liegt ein eigener, nicht überlappender Ausgabepfad vor.

## Steps

1. **Plan bilden** — `calendar plan` mit Quelle, Profil, Bereich, State,
   Konfiguration und Zeitzonenzeitpunkt ausführen.
2. **Evidenz prüfen** — Titel, Datum, Zeit, Ort, Zeitzone, Dokumenthash und
   Zeilennummern kontrollieren.
3. **Konflikte prüfen** — `blocked` und unklare Dokumente nicht übergehen;
   vorhandene identische lokale UIDs müssen `noop` sein.
4. **Freigabe erstellen** — Schema, Plan-ID, Kalenderrevision, gewünschte
   Aktions-IDs, stabile Approval-ID und Zeitzonenzeitpunkt festhalten.
5. **Plan erneut aufbauen** — `calendar apply` mit identischen Planungseingaben
   und der Approval-Datei starten.
6. **State freigeben** — `--approve-state-write` nur für Ereignis und Audit setzen.
7. **ICS gesondert freigeben** — ausschließlich beim Backend `uptoday_ics`
   zusätzlich `--approve-output-write` setzen.
8. **Ergebnis prüfen** — Event-ID oder ICS-Pfad und -Hash gegen den Bericht lesen.
9. **Lokalen Kalender abfragen** — `calendar list` nach Profil, Bereich und
   optionalem Datumsbereich verwenden.

## Exit-Criteria

- [ ] Plan, Approval, Kalenderrevision und Quellhash stimmen überein.
- [ ] Quelldokumente blieben bytegleich.
- [ ] Lokale Ereignisse und Audit wurden gemeinsam geschrieben oder gar nicht.
- [ ] Alle ICS-Dateien besitzen den geplanten Hash; es wurde nichts überschrieben.
- [ ] `connector_invoked` ist `false`; ein UpToday-Import wurde nicht behauptet.

## Fallstricke

- `--approve-sensitive-local-read` ist keine Kalender- oder Netzwerkfreigabe.
- Eine geänderte Quelle, Revision oder vorhandene Zieldatei entwertet den Plan.
- State, Quelle und ICS-Ausgabe dürfen sich nicht überlappen.
- Routinika und Google bleiben bis zu eigenen geprüften Connectoren blockiert.
- Terminerkennung ist best effort und garantiert keine Vollständigkeit.

## Verwandte

- [`../docs/phase17-calendar-reuse-and-plan.md`](../docs/phase17-calendar-reuse-and-plan.md)
- [`./document-library.md`](./document-library.md) — lokale Dokumentextraktion
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-17-Datenfluss

## Historie

- **2026-08-22** — Nach Phase-17-End-to-End-Abnahme erstellt
