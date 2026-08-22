# Phase 25 — Office-, Medien- und Designstudio

**Status:** lokal abgeschlossen, 218 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel

FolderHome soll Präsentationen, Tabellen, Dokumente, ODT, Designsets,
Visitenkarten und Medien nicht mit einem neuen monolithischen Renderer
nachbauen. Ein providerneutraler Plan weist stattdessen den vorhandenen
Spezialisten, seinen aktuellen Status und die erforderlichen Qualitätsgates
aus. Der neue lokale Kern erzeugt ausschließlich wiederverwendbare
Designtokens und eine SVG-Visitenkartenvorschau.

## Revisions- und Laufzeitinventur

| Baustein | Befund | Phase-25-Rolle |
|---|---|---|
| `pptx`-Skill | vorhanden; verlangt Inhaltsprüfung, Rendering und mindestens einen visuellen Fix-/Prüfzyklus | Präsentations-Handoff, aktuell ohne `soffice` blockiert |
| `academic-pptx` | vorhanden; ergänzt Argument-, Evidenz- und Zitationsregeln | nur bei wissenschaftlichen Präsentationen zusätzlich verwenden |
| `Spreadsheets` | vorhanden; verlangt `@oai/artifact-tool` über den Workspace-Dependency-Loader | Tabellen-Handoff, aktuell ohne Loaderbindung blockiert |
| `documents` | vorhanden; verlangt strukturelle und visuelle DOCX-Prüfung | Dokument-Handoff, aktuell ohne `soffice` blockiert |
| report-forge | sauber an `355acb5ff1abe41b384a0d1e3a00925e6ac86215`, 22 Tests grün; Distribution `1.1.4`, Runtime `1.1.0` | nicht aufgerufen, bis die Identität vereinheitlicht ist |
| ai-media-editor | sauber an `4e4c79d8c16a117bf69c0f72ad946575110a6b84`, MIT, Version `0.2.0`, 45 Tests grün | Medien-Handoff mit eigener Lese-, Strategie- und Ausgabefreigabe |
| MediaBrain | lokaler Checkout mit fremden Änderungen | nicht gelesen, geändert oder als Provider behauptet |
| LibreOffice/`soffice` | nicht verfügbar | PPTX-, DOCX- und ODT-Sichtprüfung blockiert |
| Poppler/`pdftoppm` | verfügbar | allein kein Office-Renderer |
| FFmpeg/FFprobe | verfügbar | mögliche ai-media-editor-Laufzeit, kein automatischer Medienaufruf |

## Neuer gekapselter Kern

- `folderhome.contracts.artifact_studio`
- `folderhome.application.artifact_studio`
- `folderhome-artifact-studio`-Skill

Der Planvertrag `folderhome.artifact-studio-plan.v1` enthält für jede
angeforderte Artefaktart Provider, Revision, Status, Begründung und Gates.
`provider_invoked=false` und `side_effects=[]` sind feste Invarianten.

## Designset und Visitenkarte

`folderhome.design-studio-request.v1` beschreibt Profil, Zweck, fünf Farben,
Schriften und Visitenkarteninhalt. Der Kern:

- blockiert unbekannte Schemafelder
- akzeptiert nur sichere Schriftbezeichnungen
- verlangt mindestens 4,5:1 Kontrast für Text auf Hintergrund und Primärfarbe
- escaped alle nutzerbezogenen SVG-Inhalte
- erzeugt deterministische JSON-Tokens, CSS-Variablen und ein SVG in
  1050 × 600
- schreibt die drei Dateien erst nach einem getrennten Output-Gate
- überschreibt nie und rollt eigene, hashgleiche Teilausgaben zurück

Die synthetische Beispielkarte wurde zusätzlich über Edge headless gerastert
und visuell auf Umlaute, Kontrast, Abstände und vollständige Kontaktzeilen
geprüft. Jede spätere Karte behält trotzdem `visual_qa_passed=false`, bis sie
selbst betrachtet wurde.

## Produktgrenzen

- Ein Plan ist kein ausgeführtes Office-, Medien- oder Skill-Ergebnis.
- Blockierte Routen werden nicht mit ähnlichen Systembibliotheken umgangen.
- `review_required` erlaubt Vorbereitung, aber keine Fertigbehauptung.
- ODT bleibt ohne gebundenen Renderer vollständig blockiert.
- Medien werden nicht gelesen, geschnitten oder gerendert.
- Versand, Upload, Druck und Veröffentlichung sind eigene Nutzer-Gates.
- Profile innerhalb eines Betriebssystemkontos bleiben organisatorisch und
  sind keine Zugriffsgrenze.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
