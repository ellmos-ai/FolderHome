# Phase 24 — Korrespondenzstudio

[English](./phase24-correspondence-studio-plan.md) | **Deutsch**

**Status:** lokal abgeschlossen, 213 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel

FolderHome erstellt aus einer expliziten Anfrage, einer kontrollierten
Vorlage und einem vererbbaren Briefdesign eine prüfbare lokale Vorschau. Nach
einer zweiten Freigabe kann es neue Markdown- und TXT-Dateien schreiben.

## Revisionsgenauer Wiederverwendungsabgleich

| Baustein | Befund und Verwendung |
|---|---|
| report-forge | sauberer Checkout `355acb5ff1abe41b384a0d1e3a00925e6ac86215`, MIT; als geplanter Office-Renderer inventarisiert, aber wegen Distribution `1.1.4` gegenüber Runtime `1.1.0` nicht aufgerufen |
| doc-services | vorhandene Dokumentextraktion; kein Ausgaberenderer und deshalb hier nicht zweckentfremdet |
| letter-hooker | Prompt-Bootloader und Governance-Werkzeug; kein Brief- oder Vorlagenrenderer |
| python-docx | lokal vorhanden; ohne vollständige visuelle Renderabnahme keine behauptete DOCX-Ausgabe |
| pdftoppm | lokal vorhanden; allein keine Office-Konvertierung |
| LibreOffice/soffice | nicht verfügbar; ODT- und visuelle DOCX-Abnahme bleiben blockiert |

Der neue, wiederverwendbare Kern ist gekapselt in:

- `folderhome.contracts.correspondence`
- `folderhome.application.correspondence`

## Verträge

- `folderhome.letter-designs.v1`: Designs und explizite Bindungen
- `folderhome.letter-templates.v1`: kontrollierte Vorlagen
- `folderhome.correspondence-request.v1`: Profil, Anlass, Parteien,
  Variablen, Anlagen und interne Evidenzreferenzen
- `folderhome.correspondence-preview.v1`: Inhalt, Auflösungsweg, Hashes und
  nicht ausführende Formathandoffs
- `folderhome.correspondence-output-report.v1`: tatsächlich neu geschriebene
  Markdown-/TXT-Ausgaben und ihre Hashes

## Designvererbung

Die Reihenfolge ist deterministisch: Standard, Bereich, Zweck, Profil,
Profil-Zweck. Jeder Treffer ersetzt den vorherigen. Unbekannte Design-IDs
blockieren bereits das Laden der Konfiguration.

## Sicherheits- und Produktgrenzen

- Die Sensitivitätsfreigabe wird vor dem Lesen der Anfrage geprüft.
- Nur einfache Platzhalter aus Kleinbuchstaben, Ziffern und Unterstrichen
  sind zulässig; Python-Attribut- und Indexzugriffe sind ausgeschlossen.
- Fehlende oder unbenutzte Variablen blockieren den Lauf.
- Vorschauen sind read-only und rufen weder LLM noch Remote-Provider auf.
- Schreiben benötigt ein eigenes Output-Gate, prüft beide Zielpfade vorab,
  überschreibt nie und rollt ausschließlich selbst neu angelegte Dateien
  zurück.
- DOCX und ODT bleiben sichtbare, nicht ausgeführte Handoffs.
- E-Mail-Versand, Druck, Upload und Veröffentlichung bleiben außerhalb
  dieser Phase.

## Abnahme

- vier fokussierte Domänentests für Konfiguration, Rendering und Ausgabe
- ein CLI-End-to-End-Test für beide Gates, Vorschau, Ausgabe und Wiederholung
- synthetische deutsche Korrespondenz mit echten Umlauten
- vollständige Suite, Ruff und Compileall vor Phasenabschluss

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
