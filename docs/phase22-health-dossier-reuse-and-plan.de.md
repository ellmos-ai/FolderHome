# Phase 22 — Gesundheitsdossier und Arztbericht-Synthese

[English](./phase22-health-dossier-reuse-and-plan.md) | **Deutsch**

**Status:** lokal abgeschlossen, 204 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel und Anforderungsdifferenz

FolderHome bündelt ausdrücklich ausgewählte Gesundheitsdokumente für ein
Profil. Es erzeugt eine extraktive Zeitlinie, dokumentierte Medikamente,
Termine, offene Nutzerfragen, direkte Feldkonflikte und sichtbare
Quellenlücken. Jede übernommene Aussage trägt Dokument-ID, Quellhash,
Relativpfad und Zeilennummer.

Erfüllt sind damit die lokale Markdown-/JSON-Synthese, Evidenzbindung,
Zeitabdeckung, Konfliktkandidaten und Fehlertransparenz. Weiter offen bleiben
freie LLM-Synthese, OCR-Freigabe für reale Quellen, DOCX/ODT, medizinische
Interpretation und externe Weitergabe.

## Revisionsgenaue Wiederverwendung

| Komponente | Revision | Einordnung für Phase 22 |
|---|---|---|
| doc-services | `e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2` | Runtime-Bridge für read-only Extraktion, Datenschutzbefund und Extraktionsprovenienz |
| KnowledgeDigest | `7040c66aa9326975ad81c156acf0d49fd5dca60f` | Bereits vorhandene Dokumentensuche; für den expliziten Dossierordner nicht erneut beschrieben oder benötigt |
| gesundheit-Skill 2.0.0 | `0317f32310eed11d21f603cb6f22a689485af226` | Designreferenz für Organisation bereitgestellter Angaben ohne Diagnose oder Therapieentscheidung |
| docs-analysis 1.0.0 | lokaler Skillstand 2026-03-15 | Anforderungs-/Code-Differenzmethode; kein Runtime-Import |
| report-forge | `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | Optionaler Berichtskandidat, blockiert: Distribution `1.1.4`, Runtime `1.1.0` |
| llm-note | `b5fe59fc155ded9603566aa0fb920a53181a2426` | Notizspeicher, kein Dossier-Renderer; in Phase 22 nicht geladen |

Alle genannten Checkouts waren bei der Prüfung sauber. Es wurde kein
Providerquellcode kopiert. Der neue Dossiervertrag und die Orchestrierung
liegen vollständig gekapselt in FolderHome.

## Neuer Kern

```text
expliziter Gesundheitsordner + Profil + Stichtag + Sensitivitätsfreigabe
  → doc-services revisionsgebunden und ohne OCR lesen
  → Datenschutzbefund auf lokalen Gesundheitszweck begrenzen
  → eindeutiges Dokumentdatum und gelabelte Aussagen extraktiv erfassen
  → jede Aussage an Dokument-ID, Hash, Pfad und Zeile binden
  → Zeitlinie deterministisch sortieren
  → direkte Feldabweichungen als Review-Kandidaten zeigen
  → Abstände zwischen datierten Quellen sichtbar machen
  → blockierte, nicht lesbare, undatierte und zukünftige Quellen ausweisen
  → Markdown und JSON als neue Dateien außerhalb des Quellordners schreiben
```

Neue Pakete:

- `folderhome.contracts.health`
- `folderhome.application.health_dossier`
- `folderhome.capabilities.health_report_handoff`

## Datenschutzentscheidung

doc-services verwendet ROT sowohl für Gesundheitsdaten als auch für
Zugangsdaten, Bankkennungen und andere hochsensible Muster. Ein pauschales
Überstimmen von ROT wäre deshalb unzulässig. FolderHome verarbeitet nach dem
lokalen Sensitivitäts-Gate nur einen ROT-Befund, dessen sämtliche roten
Fundzeilen `Gesundheitsdaten` sind. Jeder zusätzliche rote Befund blockiert die
inhaltliche Übernahme. Der Bericht bleibt lokal; Netzwerk und Remote-Provider
werden nicht aufgerufen.

## Extraktion statt Claim-Upgrade

- `Befund`, `Ergebnis`, `Medikament`, `Termin` und `Offene Frage` werden als
  dokumentierte Aussagen übernommen, nicht validiert oder interpretiert.
- `Diagnose` und `Maßnahme` werden ausdrücklich als dokumentierte Angaben
  bezeichnet.
- Direkte Konflikte entstehen nur aus gleich benannten
  `Dokumentierte Angabe: Feld = Wert`-Zeilen.
- Ein Zeitabstand ist eine Quellenlücke, keine behauptete Behandlungslücke.
- Undatierte Inhalte werden nicht still anhand des Dateinamens oder der
  Dateisystemzeit einsortiert.
- Der Bericht behauptet weder Vollständigkeit noch medizinischen Rat.

## Abnahme

- Gate vor Extraktion
- ausschließlich gesundheitsbezogene ROT-Ausnahme für lokale Verarbeitung
- blockierte, nicht lesbare, undatierte und zukünftige Quellen
- Zeitlinie mit exakter Zeilenevidenz
- Medikamente, Termine und offene Fragen
- direkte Feldkonflikte
- Quellenabstände über konfigurierbarer Schwelle
- stabile IDs und deterministische Markdown-/JSON-Ausgabe
- Never-overwrite und Ausgaben außerhalb des Quellordners
- synthetischer CLI-End-to-End-Lauf

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
