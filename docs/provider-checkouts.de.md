# Optionale Provider-Checkouts

[English](./provider-checkouts.md) | **Deutsch**

Die synthetischen Wettbewerbsdemos benötigen keine Provider-Repositories. Das
Komponentenmanifest-Verzeichnis enthält neun Einträge. Sieben verweisen auf
öffentliche GitHub-Quellen; ihre Capability-IDs und aktuellen Manifestrevisionen
stehen in der Tabelle. Ein für eine Komponente verwendeter Checkout muss exakt
der Revision in seiner TOML-Datei entsprechen und einen sauberen Arbeitsstand
haben.

Die optionale `doc-services`-Bridge stellt die lokale Dokumentextraktion bereit.
Ein expliziter Wert für `--doc-services-root` hat Vorrang vor dem konfigurierten
Standardpfad.

| Manifesteintrag | Deklarierte Capability-IDs | Öffentliche Quelle | Revision im Manifest |
|---|---|---|---|
| `ellmos-scheduler` | `scheduler.jobs.register`, `scheduler.jobs.consume` | [ellmos-ai/ellmos-scheduler](https://github.com/ellmos-ai/ellmos-scheduler) | `d5103b9a733701f6db80dd08cfae408bf0af8ac5` |
| `KnowledgeDigest` | `documents.index`, `documents.search` | [file-bricks/KnowledgeDigest](https://github.com/file-bricks/knowledgedigest) | `7040c66aa9326975ad81c156acf0d49fd5dca60f` |
| `llm-note` | `notes.read`, `notes.write` | [doc-bricks/llm-note](https://github.com/doc-bricks/llm-note) | `b5fe59fc155ded9603566aa0fb920a53181a2426` |
| `law-checker` | `legal.registry.read`, `legal.orientation.handoff` | [ellmos-ai/rechtsabteilung](https://github.com/ellmos-ai/rechtsabteilung) | `a5b0cd51bc3666962f2fae8017c855dea0a712a2` |
| `hungrycall` | `calls.hungry_cascade` | [ellmos-ai/hungrycall](https://github.com/ellmos-ai/hungrycall) | `9ae58c4acb31070dcf2e3fc468cff1c80c9a7e9c` |
| `ringedingeding` | `calls.ring_cascade` | [ellmos-ai/ringedingeding](https://github.com/ellmos-ai/ringedingeding) | `94ae1f1e028be5aaf100baafadc18b64ff0940a2` |
| `steuer-assistent` | `tax.receipts.write`, `tax.workpaper.export` | [ellmos-ai/steuer-assistent](https://github.com/ellmos-ai/steuer-assistent) | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` |

Die zwei übrigen Manifesteinträge `doc-services` und
`file-collect-sort-action` haben keine öffentlich zugängliche Checkout-Quelle.
Dieser öffentliche Leitfaden nennt weder Quellorte noch private Checkout-Details.
Für eine berechtigte lokale Quelle gelten die dafür bereitgestellten Zugangsregeln.
Die im `law-checker`-Manifest deklarierte Quelle leitet derzeit zum verlinkten
Repository `rechtsabteilung` weiter; verwende weiterhin die im Manifest
festgehaltene Revision.

## Öffentliche Version isolieren

Lasse vorhandene Arbeitskopien unverändert und verwende ein eigenes Ziel im
FolderHome-Repository. Das Beispiel bezieht den manifestgepinnten öffentlichen
Scheduler-Quellcode. Führe die Befehle im FolderHome-Repository in PowerShell
aus:

```powershell
$providerSource = 'https://github.com/ellmos-ai/ellmos-scheduler.git'
git clone --no-hardlinks --no-checkout $providerSource .providers/ellmos-scheduler
git -C .providers/ellmos-scheduler switch --detach d5103b9a733701f6db80dd08cfae408bf0af8ac5
git -C .providers/ellmos-scheduler status --porcelain
```

Bei einem Fehler abbrechen. Der letzte Befehl darf nichts ausgeben. Kein
bestehendes Ziel wiederverwenden und keine fremde Arbeitskopie zurücksetzen.

FolderHome bevorzugt `.providers/<provider-id>`, wenn dieser Checkout vorhanden
ist; sonst gilt der konfigurierte benachbarte Verzeichnisstandard. Die
konfigurierten Wurzeln heißen `doc-services`, `file-collect-sort-action`,
`law-checker`, `ellmos-scheduler`, `KnowledgeDigest`, `hungrycall`,
`ringedingeding`, `llm-note`, `steuer-assistent`, `ai-media-editor`,
`UniversalDocsGrabber` und `UpToday`. Die Wurzelauswahl macht nicht jeden Pfad
zu einem Komponentenmanifesteintrag.

## Providerwurzeln mit eigenem Funktionsplan

Drei weitere Wurzeln sind außerhalb von `manifests/components/` beschrieben.
Ihre Revisionsangaben stammen aus anderen Quellen als den neun Komponenten-TOML-Dateien:

| Providerwurzel | Revisionsangabe | Funktionsumfang |
|---|---|---|
| `ai-media-editor` | `AI_MEDIA_EDITOR_REVISION` in [`src/folderhome/cli.py`](../src/folderhome/cli.py), aktuell `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | [Plan Phase 25](./phase25-artifact-studio-plan.de.md) |
| `UniversalDocsGrabber` | `UNIVERSAL_DOCS_GRABBER_REVISION` in [`src/folderhome/cli.py`](../src/folderhome/cli.py), aktuell `0ccd03455b63acbca6e71cc48ba464f208a759cd` | [Plan Phase 26](./phase26-mail-connector-plan.de.md) |
| `UpToday` | `UPTODAY_REVISION` in [`src/folderhome/cli.py`](../src/folderhome/cli.py), aktuell `7582ca87e17e458bb99a7379d2c54003c15415a4` | [Plan Phase 17](./phase17-calendar-reuse-and-plan.de.md) |

FolderHome enthält einen optionalen Mail-Ingest-Providerpfad für
UniversalDocsGrabber. Das CLI-Inventar kennzeichnet ihn als Runtime-Connector
und prüft die konfigurierte Checkout-Revision. Diese Beschreibung auf
Quellcodeebene ist kein Live-Mailbox-Test. Der UpToday-Pfad beschreibt eine
ICS-Übergabe; FolderHome behauptet keinen direkten Import in UpTodays Datenbank.

## Lokaler Abhängigkeitsspeicher

`.providers/` wird von Git ignoriert. Das ist lokaler Abhängigkeitsspeicher,
**keine Erlaubnis zur Weitergabe privaten Quellcodes**. Ein `local://`-Manifest
ist keine öffentliche Downloadadresse. Private Checkout-Inhalte gehören nicht
in Releases oder Wettbewerbsuploads.

## Grenzen der Prüfung

```powershell
.venv\Scripts\python.exe -m pytest tests/test_doc_services_bridge.py -q
```

Zwei erfolgreiche Bridge-Tests üben lokale Extraktion und das Datenschutz-Gate
für den konfigurierten Checkout. Providerabhängige Tests benötigen die passenden
Quellcode-Checkouts; einige werden bei fehlendem Provider ausdrücklich
übersprungen. Vorhandene, aber falsche oder nicht saubere manifestgebundene
Provider führen bei der Checkout-Prüfung zu Fehlern. Ein übersprungener
Integrationstest belegt nicht, dass die entsprechende Funktion mit echten Daten
arbeitet.
