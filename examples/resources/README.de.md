# Beispiele für logische Ressourcen

[English](./README.md) | **Deutsch**

[`resources.example.json`](./resources.example.json) ist ein bewusst kleines,
anonymes Startregister. Kopiere es an den privaten Speicherort des jeweiligen
Betriebssystemkontos, lege alle referenzierten Pfade lokal an und trenne
Ressourcen immer dann, wenn ein Workflow getrennte Quell-, Ziel-, State-,
Ausgabe-, Desktop- oder Konfigurationsorte verlangt. Physische Pfade und Secrets
dürfen niemals committet werden.

## Vom Masteragenten verwendete Zweckgruppen

| Gruppe | Logische Zwecke | Erforderliche Art und Operationen |
|---|---|---|
| Dokumenteingang | `documents.bundle.source`, `document_package.source`, `health.source`, `finance.source`, `inventory.source`, `contacts.source`, `calendar.source` | Verzeichnis; `list`, `read` und, falls vom Adapter verlangt, `sensitive_read` |
| Dokumentaktion | `document_action.source`, `document_action.target`, `document_action.plan_output`, `document_action.state` | Dateiquelle; getrennte Ziel-, Ausgabe- und State-Verzeichnisse; je nach Anfrage `read`, `sensitive_read`, `move`, `create`, `state_write` |
| Ordnerautomation | `folder_cleanup.source`, `folder_cleanup.target`, `folder_cleanup.state`, `directory_observation.source`, `directory_observation.state`, `folder_routine.source`, `folder_routine.target`, `folder_routine.state` | getrennte Verzeichnisse; Lesen/Auflisten an Quellen, Erstellen/Verschieben an Zielen, Lesen/State-Schreiben am State |
| Routinenqueue | `routine_queue.source`, `routine_queue.target`, `routine_queue.state`, `routine_queue.output` | getrennte Verzeichnisse; die Queue-Ausgabe registriert niemals einen Scheduler |
| FCSA | `fcsa.config`, `fcsa.scan`, `fcsa.target` | Konfiguration und Scanressourcen werden lokal gelesen; der verbundene Adapter bleibt ausschließlich Dry Run |
| Private Ausgaben | `documents.bundle.output`, `document_package.output`, `health.output`, `official_notice.output`, `administrative.output`, `benefits.output`, `legal.output`, `briefing.output`, `tax.output`, `artifact_studio.output`, `contract_cockpit.output`, `correspondence.output` | Verzeichnis; `create` |
| Privater State | `finance.state`, `inventory.state`, `contacts.state`, `calendar.state`, `tax.state`, `contract_cockpit.state` | Verzeichnis; `read` sowie je nach Anfrage `state_write` oder `sensitive_read` |
| Konfiguration und Anfragen | `calendar.configuration`, `correspondence.request`, `correspondence.designs`, `correspondence.templates`, `administrative.request`, `administrative.notice`, `administrative.designs`, `administrative.templates` | Datei; `read`, bei persönlichen Anfragen und Bescheiden zusätzlich `sensitive_read` |
| Sozialrechtsquellen | `official_notice.source`, `benefits.profile`, `benefits.catalog`, `legal.before`, `legal.after`, `legal.interests` | Datei; `read`, bei persönlichen Inhalten zusätzlich `sensitive_read` |
| Daily Briefing | `briefing.weather_snapshot`, `briefing.news_snapshot`, `briefing.desktop` | Snapshot-Dateien werden lokal gelesen; der Desktop ist ein getrenntes Verzeichnis mit `create` |

Maßgeblich ist das geschlossene Anfrageschema des jeweiligen Adapters. Die
Runtime blockiert unbekannte Ressourcen-IDs, falsche Arten, fehlende
Operationen, profilfremde Nutzung und unsichere Überlappungen, bevor eine
Fachaktion ausgeführt wird.
