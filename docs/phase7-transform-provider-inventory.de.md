# Phase 7 — Inventar der Dokumenttransformation

[English](./phase7-transform-provider-inventory.md) | **Deutsch**

**Geprüft:** 2026-08-21 21:51 Europe/Berlin  
**Ziel:** Vorhandene Bausteine wiederverwenden, ohne Transformation und
Originalbehandlung zu vermischen oder Providerfähigkeiten zu überzeichnen.

## Gewünschte Fähigkeit

FolderHome soll ausgewählte Dokumente oder ganze Ordner deterministisch zu
einer Text- oder PDF-Datei bündeln können. Die Ausgabe darf nicht still
überschrieben werden. Quellen bleiben unangetastet; Archivierung,
Gardener-Ablage oder Papierkorb dürfen erst nach einer nachgewiesenen
erfolgreichen Transformation als eigener Schritt folgen.

## Geprüfte vorhandene Bausteine

| Baustein | Belegter Stand | Nutzbar für FolderHome | Grenze |
|---|---|---|---|
| `doc-services` | sauberer Checkout `037a432bbec94ac6db5dfa53941745fda7c2f38a`, Version `0.1.0` | Ja, gepinnte lokale Extraktion und Datenschutzstatus | Liest Dokumente; erzeugt keine TXT-/PDF-Ausgabedatei |
| MarkItDown | sauberer Checkout `fd239d5d2be43d9b68329730206b9312c7d5a388`, MIT | Nur indirekt über `doc-services` | Ausgabe ist Analyse-Markdown, ausdrücklich keine hochfidele Dokumentkonvertierung |
| `report-forge` | sauberer Checkout `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | Noch nicht | Distribution meldet `1.1.4`, Runtime `1.1.0`; generischer PDF-Prozessor ist ein nicht implementierter Stub |
| `PDFtoPDFocr` | sauberer Checkout `c89ae00982d7597b663c99527298363b9e2fce58`, Version `1.1.3` | Später über eine schmale Headless-Grenze | GUI-Monolith importiert PySide6; `merge_ocr_outputs` verschiebt nach dem Merge die Einzeldateien und verletzt damit die FolderHome-Quellgrenze |
| `file-collect-sort-action` | gepinnt auf `8ebac2739c11c6a041abdd7b30131cef648b4753` | Ja, nach erfolgreicher Transformation | Verschieben und Papierkorb, aber keine Formatkonvertierung |
| Skill `batch-file-ops` | List/Copy/Move/Delete mit Dry Run | Nein für Transformation | Dateiauswahl und Operationen, aber kein Dokumentformat |
| Documents-Skill | DOCX-Erstellung, Merge, Render und visuelle Prüfung als Agentenwerkzeug | Nicht als Produkt-Runtime | Hilft bei Entwicklungs- und Abnahmeartefakten, ist aber kein gepinnter FolderHome-Provider |
| `ai-media-editor` | sauberer Checkout `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | Nein für Dokumentbündel | Video-, Audio- und Hyperframes-Pipeline, keine PDF-/DOCX-/ODT-Dokumentausgabe |

## Wiederverwendungsentscheidung

1. `doc-services` bleibt der einzige Extraktionsprovider. FolderHome baut
   weder MarkItDown- noch Office-Extraktion erneut.
2. FCSA bleibt allein für die getrennte, spätere Originalbehandlung
   verantwortlich. Transformation verschiebt oder löscht niemals Quellen.
3. `report-forge` bleibt bis zu einer einheitlichen Provideridentität
   fail-closed. FolderHome kopiert dessen Pipeline nicht.
4. Der OCR- und Bild-zu-PDF-Pfad von `PDFtoPDFocr` wird erst angebunden, wenn
   eine schmale Headless-API ohne implizites Verschieben vorliegt. Der
   Wettbewerbskern importiert den GUI-Monolith nicht.
5. Die nachweislich fehlende Lücke wird im Repository als neue,
   extrahierbare Capability `folderhome.capabilities.document_transform`
   implementiert. Dadurch kann sie nach dem Wettbewerb unverändert in den
   Sovereign-Stack übernommen oder in ein eigenes Modul ausgegliedert werden.

## Vertrag für den neuen Kern

- Planung und Schreiben sind getrennte Aufrufe.
- Ein Plan enthält geordnete Quellen, SHA-256, Ausgabeformat,
  Qualitätsklasse, Verlusthinweise, Gate und Zielpfad, aber keinen Rohtext.
- Unterstützte erste Ausgaben sind UTF-8-TXT und PDF.
- PDF-Seiten bleiben bei PDF-Eingaben seitengetreu; Bilder werden gerastert
  eingebettet; andere unterstützte Dokumente werden aus dem von
  `doc-services` extrahierten Text neu gesetzt und daher ausdrücklich als
  layoutverlustbehaftet markiert.
- OCR ist kein impliziter Fallback.
- Das Ziel muss neu sein; atomare Veröffentlichung und erneute Quellhashprüfung
  sind Pflicht.
- Originalbehandlung wird nur als nachgelagerte Aktionsplan-Freischaltung
  modelliert, wenn Ausgabehash und Abnahme vorliegen.

## Nicht erneut bauen

- Dateityperkennung, Extraktion und Datenschutzklassifikation
- OCR-Engine und Sprachpaketverwaltung
- Allgemeine Move-/Papierkorblogik
- DOCX-Berichtsvorlagen und Office-Renderer
- Medien- und Präsentationsrendering

## Verbleibender Neubau

1. Providerneutraler Bündelplan mit Qualitäts- und Verlustvertrag
2. Deterministische TXT-Publikation
3. PDF-Montage für PDF, Bild und extrahierten Text
4. Atomare, nie überschreibende Ausgabeschicht mit explizitem Gate
5. Verifizierter Erfolgsbeleg als Voraussetzung für Originalbehandlung
