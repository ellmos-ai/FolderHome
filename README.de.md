<img src="assets/banner.png" width="100%" alt="FolderHome-Banner">

# FolderHome

[English](./README.md) | **Deutsch**

> Assistantify your home.

Dies ist der kompakte Projekteinstieg. Er ersetzt die ausführliche README im [`korrigierten Archiv`](./docs/archive/README.de-through-2026-10-13.md), das aus dem Quellcommit [`dac6541`](https://github.com/ellmos-ai/FolderHome/blob/dac6541ba0f6429d38d4ee3bffec08a94316213c/README.de.md) abgeleitet wurde. Der unveränderte Ausgangstext ist über diesen Commit erreichbar. Versionsbezogene Test- und Demoangaben im Archiv sind historische Einträge, keine aktuelle Abnahme.

FolderHome ist eine Python-Anwendung zur Suche in ausgewählten Haushaltsdokumenten und zur Vorbereitung prüfbarer Abläufe. Die Paketversion ist **0.6.1**, erforderlich ist Python **3.11 oder neuer**. Die Anwendung kann konfigurierte Modell- und Dienstprovider verwenden; Netzwerkzugriffe und externe Wirkungen hängen vom gewählten Provider und seinen Freigaben ab. Die Grenze des lokalen Speicherschutzes ist das Betriebssystemkonto; Profile organisieren Ansichten, sie isolieren keine Personen.

- [Datenschutz und Datenflüsse](./PRIVACY.de.md)
- [Sicherheitsgrenzen und Meldungen](./SECURITY.de.md)
- [Architektur](./ARCHITECTURE.de.md) · [englische Architektur](./ARCHITECTURE.md)
- [Änderungsprotokoll](./CHANGELOG.de.md)
- [Lizenz](./LICENSE)

## Status

Die Quellversion ist 0.6.1. Historische Testzahlen, Live-Provider-Prüfungen, gehostete Demo-Versionen und Wettbewerbsabnahmen stehen im korrigierten Archiv; sie belegen keine aktuelle Verifikation. Der statische Showcase in [`site/`](./site/) ist von der ausführbaren Anwendung getrennt.

[Archivierte Statusdetails](./docs/archive/README.de-through-2026-10-13.md#status).

## Schnelltest für Jurorinnen und Juroren

Diese synthetische Demo verwendet das Fixture und schreibt nur in das ausgewählte lokale Ausgabeverzeichnis. Die Installation lädt Build- und Abhängigkeitspakete vom konfigurierten Paketindex.

Windows PowerShell:

```powershell
git clone https://github.com/ellmos-ai/FolderHome.git
cd FolderHome
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,transform]"
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir .local-demo\competition `
  --approve-output-write --json
```

macOS/Linux:

```sh
git clone https://github.com/ellmos-ai/FolderHome.git
cd FolderHome
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,transform]"
.venv/bin/python -m folderhome demo run \
  --output-dir .local-demo/competition \
  --approve-output-write --json
```

Die Demo verwendet synthetische Eingaben und ruft keinen Modellprovider auf. `--approve-output-write` erlaubt das Anlegen der Demoausgaben in diesem Verzeichnis.

[Archivierte Demo- und Ablaufdetails](./docs/archive/README.de-through-2026-10-13.md#schnelltest-für-jurorinnen-und-juroren).

## Interaktive Unfallgeschichte

Das Repository enthält einen synthetischen Unfallrundgang. Lokaler Befehl, Oberfläche und Fixture sind im Archiv dokumentiert; Live-Provider unterliegen den getrennten Netzwerk-, Datenfreigabe- und Wirkungsfreigaben aus [Sicherheit](./SECURITY.de.md).

[Archivierte Ablaufdetails](./docs/archive/README.de-through-2026-10-13.md#interaktive-unfallgeschichte).

## Agentenarchitektur

FolderHome führt seine Python-Anwendung lokal aus. Bei Aktivierung kann sie konfigurierte Modell- oder Fachprovider aufrufen; ein lokaler Prozess ist keine Netzwerksandbox. Der Architekturleitfaden beschreibt Komponenten und Grenzen.

[Architekturleitfaden](./ARCHITECTURE.de.md) · [Archiviertes Diagramm und Details](./docs/archive/README.de-through-2026-10-13.md#agentenarchitektur).

## Was FolderHome lokal kann

Die Anwendung unterstützt Dokumentensuche, lokale Ausgabevorbereitung, Statusansichten und freigabegesteuerte Fachabläufe. Die konkrete Verfügbarkeit hängt von konfigurierten Ressourcen und optionalen Abhängigkeiten ab; Details stehen in Architektur- und Konfigurationsleitfäden.

[Archivierte Funktionsdetails](./docs/archive/README.de-through-2026-10-13.md#was-folderhome-lokal-kann).

## Sicherheitsmodell

Das Betriebssystemkonto und seine Dateirechte bilden die lokale Sicherheitsgrenze. Profile isolieren keine Nutzer. Die App nutzt für unterstützte Netzwerkzugriffe und externe Wirkungen ausdrückliche Freigaben; Kindprozesse erben die Berechtigungen des startenden Prozesses. FolderHome stellt keine Betriebssystemsandbox bereit und sperrt anderen Prozessen nicht den Netzzugriff.

Siehe [Sicherheit](./SECURITY.de.md) und [Datenschutz](./PRIVACY.de.md) zu Implementierung und Datenflüssen.

[Archivierte Details zum Sicherheitsmodell](./docs/archive/README.de-through-2026-10-13.md#sicherheitsmodell).

## Private logische Ressourcen

FolderHome kann konfigurierte Ressourcennamen in Agentenabläufen verfügbar machen, ohne physische Speicherorte in diese modellseitigen Kataloge aufzunehmen. Vor der Nutzung mit echten Haushaltsdaten das Ressourcenregister und den Datenschutzleitfaden prüfen.

[Archivierte Ressourcendetails](./docs/archive/README.de-through-2026-10-13.md#private-logische-ressourcen).

## Lokales Modell über Ollama

Ollama ist ein optionaler Modellprovider. Ein Loopback-Endpunkt bleibt auf diesem Computer; ein Modell auf einem anderen Rechner nutzt das Netzwerk und benötigt die entsprechenden Freigaben.

[Archivierte Ollama-Anleitung](./docs/archive/README.de-through-2026-10-13.md#lokales-modell-über-ollama).

## Modell-Provider

Das Projekt enthält ein deterministisches Fixture und optionale Integrationen für konfigurierte Modellprovider. Vor der Aktivierung die aktuellen Abhängigkeitsextras und Provider-Anleitungen prüfen.

[Archivierte Provider-Einrichtung und Hinweise](./docs/archive/README.de-through-2026-10-13.md#modell-provider).

## FolderHome aus Claude Code oder Codex nutzen (MCP)

FolderHome enthält einen lokalen MCP-Einstieg. Transport und Einrichtung stehen im Archiv; ein gestarteter lokaler Prozess gibt dem verbundenen Editor keine zusätzlichen Betriebssystembeschränkungen.

[Archivierte MCP-Anleitung](./docs/archive/README.de-through-2026-10-13.md#folderhome-aus-claude-code-oder-codex-nutzen-mcp).

## Ergebnisse zum Abholen

Erzeugte Dateien und Berichte liegen an den konfigurierten lokalen Ausgabepfaden. Sie können nutzerseitige Inhalte enthalten und sollten vor einer Weitergabe geprüft werden.

[Archivierte Ergebnisdetails](./docs/archive/README.de-through-2026-10-13.md#ergebnisse-zum-abholen).

## FolderHome einrichten (lokales Einrichtungsprogramm)

Das Repository enthält einen getrennten Einrichtungsbefehl. Vor dem Start angefragte Pfade und Aktionen prüfen; das Programm läuft mit den Berechtigungen des aktuellen Nutzers.

[Archivierte Einrichtungshinweise](./docs/archive/README.de-through-2026-10-13.md#folderhome-einrichten-lokales-einrichtungsprogramm).

## Direkte HTTP-API

Die lokale HTTP-Schnittstelle ist optional und hat eigene Loopback- und Sitzungstokenkontrollen. Sie ist kein fern gehosteter API-Dienst.

[Archivierte API-Anleitung](./docs/archive/README.de-through-2026-10-13.md#direkte-http-api).

## Wichtige Befehle

Die eingebaute Hilfe zeigt die Befehle der installierten Version:

```powershell
.venv\Scripts\python.exe -m folderhome --help
```

[Archivierte Befehlsreferenz](./docs/archive/README.de-through-2026-10-13.md#wichtige-befehle).

## Entwicklungsprüfung

Die Prüfungen aus einer installierten Entwicklungsumgebung starten:

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q src tests
```

macOS/Linux:

```sh
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m compileall -q src tests
```

Diese Befehle führen keine Live-Provider-, Browser- oder gehostete Runtime-Abnahme aus. Optionale Integrationstests benötigen möglicherweise die exakten Provider-Checkouts aus [Provider-Checkouts](./docs/provider-checkouts.de.md).

[Archivierte Details zu Entwicklungsprüfungen](./docs/archive/README.de-through-2026-10-13.md#entwicklungsprüfung).

## Repositorystruktur und Herkunft

Das Repository enthält die Python-Anwendung, Komponentenmanifeste, Tests, Dokumentation und einen statischen synthetischen Showcase. Die Leitfäden beschreiben Verzeichnisstruktur und Herkunft der Komponenten.

[Archivierte Strukturdetails](./docs/archive/README.de-through-2026-10-13.md#repositorystruktur-und-herkunft).

## Datenschutzfreundlicher Chatfokus und Ausblick

Chat- und Aufbewahrungsverhalten hängen vom konfigurierten Anwendungspfad ab. Der Datenschutzleitfaden beschreibt die Grenzen von Reset und Schließen; FolderHome verspricht keine Löschung von Dateien oder Daten bei externen Providern.

[Archivierte Ausblicknotizen](./docs/archive/README.de-through-2026-10-13.md#datenschutzfreundlicher-chatfokus-und-ausblick).

## Submission-Grenze

Wettbewerbsmaterialien und historische Einreichungsgrenzen stehen im Archiv. Sie sind keine aktuelle Zertifizierung oder Releasefreigabe.

[Archivierte Einreichungsnotizen](./docs/archive/README.de-through-2026-10-13.md#submission-grenze).

## Lizenz

FolderHome steht unter der MIT-Lizenz. Siehe [`LICENSE`](./LICENSE) und das komponentenbezogene Inventar in [`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md).

[Archivierte Lizenznotizen](./docs/archive/README.de-through-2026-10-13.md#lizenz).
