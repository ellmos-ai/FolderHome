# Workflow: Dokumente als TXT oder PDF bündeln

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc
> **Duration:** abhängig von Dokumentzahl, Seitenzahl und Bildgröße

## Purpose

Einen ausdrücklich gewählten Ordner als eine neue TXT- oder PDF-Datei
zusammenführen, ohne Originale zu verändern, zu archivieren oder zu löschen.

## Preconditions

- Quellordner, neue Ausgabedatei und Ausgabeformat sind ausdrücklich gewählt.
- Für PDF-Rendering sind die optionalen Transformationsabhängigkeiten
  installiert.
- doc-services entspricht dem gepinnten sauberen Checkout.
- Der Ausgabeordner existiert und ist kein symbolischer Link.

## Steps

1. **Quellen sammeln** — Dateien werden nach relativem Pfad deterministisch
   geordnet; Symlinks und doppelte Quellen sind unzulässig.
2. **Inhalt gewinnen** — Textquellen gehen durch doc-services. PDF-Seiten und
   Bilder können für PDF ohne OCR direkt übernommen werden.
3. **Plan prüfen** — Jede Quelle nennt Hash, Datenschutzstatus, Behandlung,
   Qualitätsgrenze und möglichen Verlust; Rohtext erscheint nicht im Plan.
4. **Gate entscheiden** — Ohne `--approve-output-write` endet der Ablauf nach
   dem Plan und schreibt keine Bündeldatei.
5. **Quellen erneut prüfen** — Unmittelbar vor dem Rendern müssen Pfad und
   SHA-256 noch zum Plan passen.
6. **Im Speicher rendern** — TXT bleibt UTF-8; PDF montiert Seiten, rastert
   Bilder oder setzt extrahierten Text mit sichtbarem Layoutverlust neu.
7. **Atomar veröffentlichen** — Das Ziel wird nur neu angelegt und niemals
   ersetzt.
8. **Ergebnis belegen** — Ausgabehash, Größe, optionale Seitenzahl und alle
   Quelldokument-IDs werden im Resultat festgehalten.

## Exit-Criteria

- [ ] Ohne Gate existiert keine Ausgabedatei.
- [ ] Das Ziel war vorher nicht vorhanden und wurde nicht überschrieben.
- [ ] Alle Quellen sind bytegleich zum Planungsstand.
- [ ] TXT ist UTF-8 mit echten Umlauten.
- [ ] PDF ist lesbar, hat mindestens eine Seite und weist Layoutverluste aus.
- [ ] Der JSON-Plan enthält keinen Rohtext.
- [ ] Originalbehandlung bleibt ein getrennter, weiterhin ungefreigter Schritt.

## Fallstricke

- Textneusetzung ist keine layoutgetreue Office-Konvertierung.
- PDF-Passthrough prüft keinen Dokumentinhalt und aktiviert keine OCR.
- Ein Ausgabehash beweist die erzeugte Datei, nicht ihre fachliche Richtigkeit.
- DOCX, ODT, CSV und XLSX sind noch keine Ausgabeformate dieses Providers.

## Verwandte

- [`../docs/phase7-transform-provider-inventory.md`](../docs/phase7-transform-provider-inventory.md)
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-7-Grenze
- [`./document-action-plan.md`](./document-action-plan.md) — Originalbehandlung

## Historie

- **2026-08-21** — Nach Phase-7-End-to-End-Abnahme erstellt
