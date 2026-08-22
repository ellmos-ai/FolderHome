# Workflow: Dokumentenbibliothek lokal aufbauen

[English](./document-library.md) | **Deutsch**

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc
> **Duration:** abhängig von Dokumentzahl und Dateigröße

## Purpose

Einen ausdrücklich gewählten Ordner lokal indexieren, natürlich durchsuchen
und daraus ein Themendossier oder einen Ordnerbericht erzeugen, ohne
Quelldokumente zu verschieben oder externe Dienste aufzurufen.

## Preconditions

- Der Quellordner ist ausdrücklich gewählt und enthält in der Abnahme nur
  synthetische Dokumente.
- doc-services und KnowledgeDigest entsprechen den gepinnten Manifesten und
  ihre Checkouts sind sauber.
- Ein eigener FolderHome-Zustandsordner ist festgelegt.
- Die lokale Indexschreibfreigabe wird bewusst mit
  `--approve-index-write` erteilt.

## Steps

1. **Ausgaben vorprüfen** — Bereits vorhandene Zielberichte werden nicht
   überschrieben; Ergebnis- und Berichtspfad müssen verschieden sein.
2. **Provider prüfen** — Version, Git-Revision und sauberer Checkout werden
   gegen die Manifeste verifiziert.
3. **Dokumente extrahieren** — doc-services liest jede unterstützte Datei ohne
   Lernschreibzugriff; OCR bleibt deaktiviert.
4. **Identität prüfen** — FolderHome bildet SHA-256 und Dokument-ID. Vor der
   Indexierung wird die Quelldatei erneut gehasht.
5. **Lokal indexieren** — KnowledgeDigest wird ausschließlich mit
   `archive=False` und dem freigegebenen FolderHome-Zustandsordner aufgerufen.
6. **Ergebnis prüfen** — Unbekannte Formate sind `skipped`, Providerfehler
   `failed`; Rohtexte erscheinen nicht in der JSON-Standardausgabe.
7. **Suche oder Bericht erzeugen** — Suche und Themendossier lesen den Index
   schreibgeschützt; der Ordnerbericht übernimmt nur Inhalte mit
   Datenschutzstatus `clear`.
8. **Versionen prüfen** — Eine spezifische Anfrage ordnet passende
   katalogisierte Quellen über offengelegte Datumssignale und vergleicht
   ältere Fassungen satzweise mit der neuesten.
9. **Archivierung validieren** — Ältere Fassungen werden nur als ungefreigte
   Vorschläge an die echte FCSA-Dry-Run-Bridge übergeben.
10. **Unverändertheit belegen** — Quelldateien und Indexdatei nach reinen
   Suchläufen gegen den Vorzustand prüfen.

## Exit-Criteria

- [ ] Kein Quelldokument wurde verschoben, archiviert oder überschrieben.
- [ ] Der Index liegt ausschließlich im freigegebenen Zustandsordner.
- [ ] JSON-Ergebnisse enthalten keinen Dokumentrohtext.
- [ ] Suchläufe verändern die Indexdatei nicht.
- [ ] Datenschutzstatus ungleich `clear` führt zu keiner Inhaltsübernahme in
      den Ordnerbericht.
- [ ] Alle Fehler und Überspringungen sind pro relativer Datei sichtbar.
- [ ] Versionspläne weisen Datumsbasis und Konfidenz aus.
- [ ] FCSA bestätigt Archivierung nur im Dry-Run; das Gate bleibt unerteilt.

## Fallstricke

- KnowledgeDigest archiviert über seine API standardmäßig. `archive=False` ist
  zwingend und in der FolderHome-Bridge fest verdrahtet.
- Die öffentliche KnowledgeDigest-Suche schreibt Schema-/WAL-Metadaten. Nur
  die schreibgeschützte FolderHome-Suchbridge verwenden.
- Ein OS-Benutzerkonto ist die Sicherheitsgrenze. Familienprofile im selben
  Konto trennen keine Zugriffsrechte.
- Ein erreichtes Trefferlimit bedeutet nicht, dass das Dossier vollständig
  ist; FolderHome kennzeichnet diesen Fall.

## Verwandte

- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Datenfluss und Provider-Seams
- [`../docs/phase3-document-reuse-inventory.md`](../docs/phase3-document-reuse-inventory.de.md) — Wiederverwendungsentscheidung
- [`../manifests/components/doc-services.toml`](../manifests/components/doc-services.toml) — Extraktions-Pin
- [`../manifests/components/knowledge-digest.toml`](../manifests/components/knowledge-digest.toml) — Index-Pin

## Historie

- **2026-08-21** — Nach synthetischer CLI-End-to-End-Abnahme erstellt
