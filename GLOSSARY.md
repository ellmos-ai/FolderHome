# GLOSSARY.md — FolderHome-Begriffe

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

## Side-Effect

Außenwirkung wie Dateischreiben, Netzwerkzugriff, Telefonanruf, Mailversand
oder Kalendereintrag.
