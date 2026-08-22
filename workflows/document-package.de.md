# Workflow: Ein Dokument pro Dateityp als ZIP-Paket erzeugen

[English](./document-package.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc
> **Duration:** abhängig von Dokumentzahl, Seitenzahl und Bildgröße

## Purpose

Einen verschachtelten Ordner deterministisch nach Dateitypen gruppieren und
als ein neues ZIP mit je einem Dokument pro Gruppe sowie einem Prüfmanifest
ausgeben, ohne Quellen zu verändern.

## Preconditions

- Quellordner und neue `.zip`-Ausgabedatei sind ausdrücklich gewählt.
- Der Ausgabeordner existiert und ist kein symbolischer Link.
- doc-services und die optionalen PDF-Abhängigkeiten sind verfügbar.
- Die Schreibfreigabe gilt nur für genau die neue ZIP-Datei.

## Steps

1. **Dateien ordnen** — relative Pfade werden deterministisch sortiert;
   Symlinks sind unzulässig.
2. **Typgruppen bilden** — Bilder, PDF, TXT und Markdown haben feste Gruppen;
   weitere bekannte Endungen erhalten je Typ eine Textgruppe.
3. **Unbekannte sichern** — nicht gebundene Endungen werden mit Relativpfad,
   Größe, Hash und Grund als `unsupported` aufgenommen.
4. **Bündel planen** — jede Gruppe nutzt den Phase-7-Transformationsvertrag
   mit Datenschutzstatus, Behandlung und Verlusthinweis.
5. **Gate entscheiden** — ohne `--approve-output-write` bleibt es beim Plan.
6. **Quellen erneut hashen** — auch unbekannte Dateien müssen unverändert zum
   Plan sein.
7. **Gruppendokumente rendern** — alle Ausgaben entstehen im Speicher; ein
   persistenter Arbeitsordner wird nicht angelegt.
8. **Manifest erzeugen** — interne Ausgabehashes, Quellen und Verlustgrenzen
   werden als UTF-8-JSON aufgenommen.
9. **ZIP atomar veröffentlichen** — feste ZIP-Metadaten sichern
   Reproduzierbarkeit; ein vorhandenes Ziel wird nie ersetzt.

## Exit-Criteria

- [ ] Genau ein ZIP wurde neu erzeugt; ohne Gate wurde nichts geschrieben.
- [ ] Jede unterstützte Datei gehört genau einer Gruppe an.
- [ ] Unbekannte Dateien sind im Manifest sichtbar und gehasht.
- [ ] Jede Gruppe enthält genau ein TXT- oder PDF-Dokument.
- [ ] Das Manifest enthält keine Dokumentrohtexte.
- [ ] Quellen sind bytegleich; es existiert kein Zwischenordner.
- [ ] Derselbe Plan erzeugt bytegleich dasselbe ZIP.

## Fallstricke

- Gruppierung nach Endung ist keine inhaltliche Klassifikation.
- Ein `DOCX.txt` erhält Text, aber kein Word-Layout.
- Sehr große Ordner werden derzeit im Speicher paketiert; Ressourcenlimits
  sind ein späterer Härtungsschritt.
- Der ZIP-Hash steht außerhalb des ZIP, da ein eingebetteter Eigenhash
  selbstreferenziell wäre.

## Verwandte

- [`./document-bundle.md`](document-bundle.de.md) — einzelnes TXT-/PDF-Bündel
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-8-Paketdatenfluss

## Historie

- **2026-08-21** — Nach Phase-8-End-to-End-Abnahme erstellt
