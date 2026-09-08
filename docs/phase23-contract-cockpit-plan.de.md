# Phase 23 — Versicherungs- und Vertragscockpit

[English](./phase23-contract-cockpit-plan.md) | **Deutsch**

**Status:** lokal abgeschlossen, 208 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel

Die vorhandenen FolderHome-Fähigkeiten werden für einen Vertragsgegenstand
zusammengesetzt, ohne Daten erneut zu extrahieren oder neue Fachstores zu
bauen. Der Leitfall lautet: „Was ist meine neueste KFZ-Versicherung für
meinen Hyundai i10?“

## Wiederverwendung statt Doppelbau

| Vorhandener Baustein | Verwendung im Cockpit |
|---|---|
| Dokumentindex und Katalog | explizite Suchanfrage und erneute Quellhashprüfung |
| Versionsanalyse | neueste/ältere Fassung, Datumsbasis, Vergleich und Archivierungsvorschläge |
| Kontaktregister | aktive und zur Löschprüfung vorgemerkte Kontakte nach Vertragsobjekt |
| Finanzstore | wiederkehrende Kostenkandidaten und Kontoauszugsabdeckung |
| Kalenderstore | passende zukünftige, bereits belegte Ereignisse |
| Profilkonfiguration | Existenz und organisatorische Zuordnung des Profils |

Der neue Code ist nur die gekapselte Verbindungsschicht:

- `folderhome.contracts.contract_cockpit`
- `folderhome.application.contract_cockpit`

## Expliziter Join-Vertrag

Eine `folderhome.contract-cockpit-request.v1`-Datei nennt Profil, Bereich,
Anzeigename, Dokumentensuche, Vertragsobjekt, Gegenparteibegriffe,
Kalenderbegriffe, Konten, Abdeckungsbeginn, Stichtag und
Archivierungspräferenz. Dadurch wird nicht anhand ähnlicher Namen geraten,
welcher Kontakt oder welche Abbuchung zu einem Vertrag gehört.

## Ausgabe und Grenzen

`folderhome.contract-cockpit.v1` enthält:

- aktuelle und ältere belegte Dokumentversionen ohne Rohtext
- optionale, ungefreigte und reversible Archivierungsvorschläge
- passende aktive und frühere Kontakte mit Quellbezug
- wiederkehrende Kostenkandidaten mit Buchungs-IDs
- passende zukünftige Kalenderereignisse mit Dokumentbezug
- Kontoauszugsabdeckung und Lücken
- Komponentenrevisionen und sichtbare fehlende/mehrdeutige Evidenz
- identische JSON- und Markdown-Sicht

Der Lauf ist read-only. Er archiviert nichts, wechselt keinen Kontakt, erzeugt
keinen Termin, sendet keine Nachricht, greift nicht auf ein Bankkonto zu und
behauptet keinen Vertragsstatus. Die Sensitivitätsfreigabe wird vor dem ersten
Zustands- oder Dokumentzugriff geprüft.

### Grenze des Dateiexports — aktualisiert am 09.09.2026

CLI-Standardausgabe und JSON-Dateien aus CLI oder freigegebenem Workflow verwenden
`folderhome.contract-cockpit-export.v1`. Dessen `source_schema` bezeichnet die
interne Darstellung `folderhome.contract-cockpit.v1`. Interne Datensätze behalten
ihre Dateisystempfade für Planhash und erneute Quellprüfung; Exporte lassen
`source_path` bei Dokumenten, Kontakten und Kalenderereignissen sowie den privaten
Dokumentverweis `index.ref` weg.

Archivierungsvorschläge enthalten `source_filename`, `target_filename` und
`target_role: "configured_archive"` statt ausführbarer Quell-/Zielpfade.
Auch Markdown zeigt nur Dateiname und Archivrolle. Dokument-IDs, Quellhashes,
Datumsangaben, Kontaktdaten und Evidenzgrenzen bleiben erhalten.
**Dies ist ein privater Evidenzexport, keine Anonymisierung:** Freitext kann
weiterhin personenbezogene Daten oder Pfade enthalten und muss vor einer
Weitergabe geprüft werden.

Für Dateisystemaktionen müssen Verbraucher den intern freigegebenen Plan
verwenden, statt Pfade aus exportierten Namen zu rekonstruieren. Größen- und
Workspace-Pfadschutz beim Download bleiben aktiv. Der synthetische
AgentCore-Ablauf kann alle vier kleinen Ergebnisdateien inline zurückgeben;
das ist lokal getestet und kein Nachweis einer aktualisierten Cloud-Bereitstellung.

## Abnahme

- explizite Zuordnung statt implizitem fuzzy Join
- neueste Fassung und ältere Versionen
- konfigurierbare, aber nicht ausgeführte Archivierungsvorschläge
- passende Kontakte, Kosten, Termine und Finanzabdeckung
- sichtbare fehlende Komponenten und mehrdeutige Kontakte
- kein Dokumentrohtext im JSON
- Never-overwrite-Ausgaben außerhalb des State-Verzeichnisses
- bytegenau unveränderter gemeinsamer State im CLI-End-to-End-Test
- ausschließlich synthetischer Hyundai-i10-Fall

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
