# GLOSSARY.md — FolderHome-Begriffe

[English](./GLOSSARY.md) | **Deutsch**

## Bridge

Neuer FolderHome-Code, der den gemeinsamen Plugin-Vertrag in die Schnittstelle
einer separat versionierten Komponente übersetzt.

## Capability

Eine einzeln deklarierte Fähigkeit eines Plugins einschließlich Side-Effects,
Dry-Run-Unterstützung und Gate-Anforderung.

## Decision Card

Maschinenlesbare, menschenverständliche Entscheidung, die vor einer
freigabepflichtigen Aktion offen bleibt.

## Gate

Explizite Erlaubnisprüfung vor einer Nebenwirkung. Fehlende oder unbekannte
Erlaubnis führt zu `blocked`, nicht zur Ausführung.

## Run Report

Versionierter JSON-Bericht eines Laufs im Schema
`ellmos.home-agent.run-report.v1` mit Provenienz, Aktionen, Evidenz und
Entscheidungen.

## Fähigkeitsrezept

Eine deklarative Geschichte über vorhandene Endpunkte. Sie verleiht keine neue
Fähigkeit: Jeder Schritt behält seinen eigenen Adapter, sein Anfrageschema und
seine Gates. Was sich ändert, ist die Einheit der Zustimmung — eine Bestätigung
für die ganze geordnete Kette.

## Übergabekante

Eine deklarierte Verbindung zwischen zwei Rezeptschritten: Ein benanntes Feld des
früheren und ein benanntes Feld des späteren Schrittes müssen dieselbe logische
Ressource bezeichnen. Sie trägt niemals einen Wert aus einem Schrittbericht.

## Abnahme

Das deterministische Prüfergebnis eines Rezeptplans, gezeichnet von jeder
Fachrolle, deren Endpunkte darin vorkommen. Es ist Teil des Planhashes; wer den
Plan bestätigt, bestätigt die Abnahme mit.

## Entwurfsablage

Das Anhängen eines vorbereiteten Schreibens an den Entwurfsordner des eigenen
Postfachs des Nutzers. Das ist keine Zustellung: Kein Empfänger wird
kontaktiert, und der Nutzer versendet die Nachricht weiterhin selbst in seinem
eigenen Mailprogramm.

## Passwort-Fundort

Der absolute Pfad einer lokalen Datei, die genau ein Zugangsgeheimnis enthält.
FolderHome konfiguriert den Fundort, nie den Wert; die Datei wird ausschließlich
zur Ausführung gelesen, und ihr Pfad bleibt aus Plänen, Berichten und Chat
heraus.

## Side-Effect

Außenwirkung wie Dateischreiben, Netzwerkzugriff, Telefonanruf, Mailversand
oder Kalendereintrag.
