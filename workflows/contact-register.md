# Workflow: Dokumentkontakt prüfen und lokal registrieren

> **Last verified:** 2026-08-22
> **Frequency:** bei neuen oder geänderten Dokumenten mit Zuständigkeitsdaten
> **Duration:** wenige Sekunden pro Dokumentordner

## Purpose

Beschriftete Kontaktdaten aus ausdrücklich ausgewählten Dokumenten lokal
erkennen, gegen das zuständige Profil und ein revisionsgebundenes Register
prüfen und erst nach einer exakten Freigabe übernehmen.

## Preconditions

- Dokumentordner und separater State-Pfad sind ausdrücklich festgelegt.
- Profil und Bereich existieren in derselben OS-Konto-Konfiguration.
- Die doc-services-Revision entspricht dem gepinnten Manifest.
- Bei `review_required` wurde die rein lokale sensible Verarbeitung bewusst
  mit `--approve-sensitive-local-read` erlaubt.

## Steps

1. **Plan bilden** — `contacts plan` mit Dokumentordner, Profil, Bereich und
   State ausführen; noch entsteht keine Datenbank.
2. **Evidenz prüfen** — Organisation, Ansprechpartner, Zweck, Objekt, Kanäle,
   Wirksamkeitsdatum, Quellhash und Zeilennummern kontrollieren.
3. **Konflikte prüfen** — `blocked` bei widersprüchlichen neuesten Kontakten
   oder mehrfach aktiven Registerkontakten nicht übergehen.
4. **Aktion prüfen** — `create`, `replace` oder `noop` nachvollziehen. Bei
   `replace` bleibt der alte Kontakt erhalten und wird nur Löschkandidat.
5. **Freigabe erstellen** — Schema, Plan-ID, Registerrevision, gewünschte
   Aktions-IDs, stabile Approval-ID und Zeitzonenzeitpunkt festhalten.
6. **Plan erneut ausführen** — `contacts apply` mit derselben Eingabe und der
   Approval-Datei starten.
7. **State freigeben** — ausschließlich für die beabsichtigte lokale
   Registertransaktion `--approve-state-write` setzen.
8. **Ergebnis prüfen** — neue und markierte Kontakt-IDs sowie Revision lesen;
   `deleted_contact_ids` muss leer bleiben.
9. **Zuständigkeit suchen** — mit `contacts list --object "Hyundai i10"`
   den aktiven Ansprechpartner abfragen.

## Exit-Criteria

- [ ] Plan, Approval und Quellhash stimmen überein.
- [ ] Das Quelldokument blieb bytegleich.
- [ ] Der aktive Kontakt ist über Profil, Bereich und Objekt auffindbar.
- [ ] Ein früherer Kontakt wurde höchstens `deletion_candidate`, nie gelöscht.
- [ ] Die append-only Ereigniszahl entspricht den ausgeführten Aktionen.

## Fallstricke

- `--approve-sensitive-local-read` erlaubt keine externe Weitergabe.
- Familienprofile innerhalb desselben OS-Kontos sind keine Zugriffsgrenzen.
- Dokument- und State-Ordner dürfen sich nicht überlappen.
- Ein gleiches Wirksamkeitsdatum bei verschiedenen Kontakten erfordert
  menschliche Klärung.
- Eine Approval-Datei ist nach Register- oder Dokumentänderungen absichtlich
  nicht mehr gültig.

## Verwandte

- [`../docs/phase16-contact-reuse-and-plan.md`](../docs/phase16-contact-reuse-and-plan.md)
- [`./document-library.md`](./document-library.md) — lokale Dokumentextraktion
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-16-Datenfluss

## Historie

- **2026-08-22** — Nach Phase-16-End-to-End-Abnahme erstellt
