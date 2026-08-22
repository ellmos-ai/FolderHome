# Phase 3: Wiederverwendungsinventar für Dokumente

[English](./phase3-document-reuse-inventory.md) | **Deutsch**

**Stand:** 2026-08-21  
**Zweck:** Verhindert Doppelbau bei Ingest, Suche, Zusammenfassung und Berichtserzeugung.

## Gewünschte FolderHome-Funktionen

1. Dokumente aus Ordnern lesen und mit stabiler Herkunft erfassen.
2. „Ich suche ein Dokument, in dem …“ als lokale Volltextsuche beantworten.
3. Verstreute Informationen zu einem Thema als Dossier zusammenführen.
4. Für jedes Dokument Dateiname und zwei bis drei beschreibende Sätze liefern.
5. Aus einem Ordner einen strukturierten Bericht erzeugen.
6. Später PDF, Word, ODT, Präsentationen und Tabellen aus Ergebnissen erzeugen.
7. Gesundheits-, Rechts- und Finanzdokumente administrativ unterstützen, ohne
   Diagnose oder verbindliche Beratung zu behaupten.

## Verifizierter Bestand

| Baustein | Aktueller Stand | Wiederverwendung in FolderHome | Nicht erneut bauen |
|---|---|---|---|
| `file-collect-sort-action` | `0.1.0`, Commit `8ebac273…`, 63 Tests grün | Dateibestand erkennen, kategorisieren und reversible Sortierpläne liefern | Scanner, Aktionsreihenfolge, Duplikatlogik und Verarbeitungszustand |
| `doc-services` | `0.1.0`, lokaler Commit `037a432b…`, Testsuite grün | Bevorzugte Extraktion, OCR-Auswahl und inhaltsbasierte Datenschutzampel | Formatkonverter, OCR-Routing und Privacy-Erkennung |
| `KnowledgeDigest` | `0.4.0`, Commit `7040c66a…`, 130 Tests grün | Lokale SQLite-FTS5-Ablage, Chunking, Suche und Treffer-Ranking | eigener Dokumentindex, BM25-Suche und zweites Chunking-System |
| `report-forge` | Distribution `1.1.4`, Runtime `1.1.0`, Commit `355acb5f…`, Testsuite grün | Nach Bereinigung des Versionsdrifts: schema-gebundene Berichtserzeugung und DOCX-Ausgabe | eigener Template- oder Word-Renderer |
| `llm-note` | `1.0.3`, Commit `b5fe59fc…`, 19 Tests grün | Seit Phase 28: append-only Speicher für menschlich bestätigte persönliche Notizen | zweite Notizdatenbank |
| `document-chunker` | Skill `1.0.0`, Zero Dependencies | Fallback für Textpfade ohne KnowledgeDigest | nicht zusätzlich im normalen KnowledgeDigest-Pfad chunken |
| `dokument-ingest` | Skill `1.0.0`, nutzt `doc-services` | Agentische Backendwahl und Datenschutzprüfung | keine eigenständige Runtime neben `doc-services` |
| `docs-analysis` | Skill `1.0.0` | Entwicklungsseitiger Soll-Ist-Abgleich | nicht als Endnutzer-Dokumentensuche ausgeben |

Der Skill `find-docs` ist ausdrücklich keine FolderHome-Dokumentensuche. Er
fragt aktuelle Entwicklerdokumentation über Context7 ab und bleibt außerhalb
dieses Produktpfads.

## Bestehende Bundle-Definition

Das deklarative Sovereign-Bundle `ellmos-doc-handler-bundle` enthält bereits
`report-forge`, `KnowledgeDigest`, `llm-note`, `docs-analysis` und
`document-chunker`. Es trennt Dokumentenhandwerk bewusst von der eigentlichen
Wissenssuche.

Aktuelle Lücke: `doc-services` und der Skill `dokument-ingest` fehlen noch im
Bundle und in der Komponentenbindung. FolderHome verwendet sie daher während
des Wettbewerbs über eigene gepinnte Komponentenmanifeste. Eine Änderung des
Sovereign-Bundles erfolgt erst bei der Integration nach dem Wettbewerb.

## Verbindliche Verantwortungsgrenzen

```text
FCSA
  erkennt Dateien und plant Dateibewegungen

doc-services
  extrahiert Text und bewertet Datenschutzrisiken

KnowledgeDigest
  speichert normalisierte Dokumente und beantwortet lokale Suchanfragen

FolderHome
  hält Identität und Provenienz zusammen und orchestriert Nutzer-Usecases

report-forge
  erzeugt aus freigegebenen strukturierten Ergebnissen fertige Berichte

llm-note
  speichert ausdrücklich angelegte oder übernommene Nutzernotizen
```

## Notwendiger neuer FolderHome-Code

1. Ein stabiler `DocumentRecord` mit Dokument-ID, ursprünglichem Pfad,
   Inhalts-Hash, Medientyp, Extraktionsherkunft, Datenschutzstatus und
   Indexstatus.
2. Gepinnte Bridge-Manifeste für `doc-services` und `KnowledgeDigest`; seit
   Phase 28 auch für `llm-note`, für `report-forge` erst nach geklärter
   Runtime-Identität.
3. Adapter, die Provider-Ausgaben in FolderHome-Verträge übersetzen und
   unbekannte Felder oder Zustände fail-closed behandeln.
4. Eine Application-Schicht für Ingest, Suche, Themendossier und Ordnerbericht.
5. Ein späterer LLM-Port für freie Synthesen. Der aktuelle Ordnerbericht ist
   bewusst deterministisch und übernimmt höchstens zwei oder drei belegte
   Sätze; eine echte Modellwahl bleibt ein separates Gate.

## Anpassungsbedarf am Bestand

- KnowledgeDigest archiviert bei `ingest()` standardmäßig Originale. Die
  FolderHome-Bridge muss immer ausdrücklich `archive=False` setzen.
- KnowledgeDigest verwendet intern einen eigenen Extraktor. Bis ein offizieller
  Ingest-für-normalisierten-Text-Port existiert, schreibt FolderHome nicht
  direkt in dessen SQLite-Schema. Die Index-Bridge nutzt die öffentliche API
  und dokumentiert die verbleibende Extraktionsdopplung.
- KnowledgeDigest führt in seiner öffentlichen Suche `ensure_schema()` mit
  WAL-Umschaltung und `INSERT OR REPLACE` aus. FolderHome liest deshalb nur für
  die Suche das gepinnte Schema per SQLite `mode=ro&immutable=1`, prüft dessen
  Version und verändert die Indexdatei nachweislich nicht.
- `report-forge` meldet im Runtime-Paket `1.1.0`, während `pyproject.toml` und
  Changelog `1.1.4` ausweisen. Der Checkout ist sauber, aber vor einer
  versionsgeprüften Bridge muss diese Provideridentität upstream vereinheitlicht
  werden; FolderHome baut in der Zwischenzeit keinen eigenen Word-Renderer.
- `doc-services` besitzt derzeit keinen Remote und ist noch nicht in der
  Sovereign-Komponentenregistry gebunden. Vor Veröffentlichung braucht es eine
  belastbare Quellenreferenz; lokal kann der vorhandene Git-Commit gepinnt
  werden.
- Berichtserzeugung mit externem LLM, OCR und reale Nutzerordner bleiben
  gesonderte Freigaben. Der synthetische Phase-3-Pfad benötigt sie nicht.

## Reihenfolge für Phase 3

1. Provider-neutrale Dokumentverträge testgetrieben ergänzen.
2. `doc-services`- und KnowledgeDigest-Manifeste samt Pins validieren.
3. Synthetischen Ingest mit temporärer Datenbank und `archive=False` bauen.
4. Lokale Suche und Themendossier über die KnowledgeDigest-Bridge anbieten.
5. Deterministische Kurzbeschreibungen und Ordnerbericht als Application
   Service ergänzen.
6. Nach Bereinigung des Versionsdrifts `report-forge` für formatierte
   Ausgabedokumente anbinden.

## Abnahmegrenze

Phase 3 ist abgeschlossen: Ein vollständig synthetischer Ordner kann über die
CLI eingelesen, durchsucht und als Bericht zusammengefasst werden, ohne
Quelldateien zu verschieben, externe Netze aufzurufen oder personenbezogene
Daten zu verwenden. Die Gesamtsuite belegt zusätzlich, dass eine reine Suche
die Indexdatei bytegenau unverändert lässt.
