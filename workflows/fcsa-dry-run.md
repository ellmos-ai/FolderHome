# Workflow: FCSA-Sortierplan erstellen

> **Last verified:** 2026-08-21
> **Frequency:** ad-hoc
> **Duration:** abhängig von der Ordnergröße

## Purpose

Einen vorhandenen Dokumentordner mit der gepinnten FCSA-Komponente prüfen und
einen nachvollziehbaren Sortierplan erstellen, ohne den Eingangsordner, die
Zielordner oder den konfigurierten FCSA-Zustand zu verändern.

## Preconditions

- Die drei FCSA-Konfigurationsdateien sind vorhanden und verweisen nur auf
  ausdrücklich freigegebene Scanpfade.
- Die verwendete FCSA-Version entspricht dem gepinnten FolderHome-Manifest.
- Es wird ausschließlich die Fähigkeit `documents.collect_sort` im Dry-Run
  aufgerufen; eine Live-Ausführung ist nicht Teil dieses Workflows.

## Steps

1. **Provider prüfen** — FCSA-Version und bei einem lokalen Checkout auch die
   Git-Revision gegen das Komponentenmanifest prüfen.
2. **Konfiguration validieren** — FCSA lädt die drei Konfigurationsdateien mit
   seinen eigenen fail-closed Regeln.
3. **Schattenzustand erzeugen** — `state_dir` und `trash_dir` werden für diesen
   Lauf in ein temporäres Verzeichnis umgeleitet.
4. **Dry-Run ausführen** — Jeder konfigurierte Scanpfad wird über die
   öffentliche FCSA-Pipeline analysiert.
5. **Unverändertheit prüfen** — Es dürfen weder Quelldateien verschoben noch
   Ziel- oder produktive Zustandsdateien geschrieben werden.
6. **Plan übersetzen** — Kategorien und geplante Aktionen werden in den
   FolderHome-Laufvertrag mit Provenienz, Gates und Evidenz überführt.
7. **Bericht atomar schreiben** — Der vollständige JSON-Bericht wird erst nach
   erfolgreicher Erstellung veröffentlicht.

## Exit-Criteria

- [ ] Der Provider entspricht dem gepinnten Manifest.
- [ ] Der Bericht verwendet `ellmos.home-agent.run-report.v1`.
- [ ] Eingangs-, Ziel- und produktiver State-Ordner sind unverändert.
- [ ] Jede geplante Dateisystemaktion bleibt `planned` und benötigt ein Gate.
- [ ] Fehler werden als fehlgeschlagener, atomar geschriebener Bericht erfasst.

## Fallstricke

- FCSAs eigener Dry-Run schreibt normalerweise eine Bestätigung in `state_dir`.
  FolderHome muss diese Bestätigung in einen temporären Schattenzustand
  umleiten, damit der Plan keine spätere Live-Freigabe vortäuscht.
- Die FCSA-CLI bietet in der gepinnten Revision noch keine JSON-Ausgabe. Der
  Adapter verwendet daher die dokumentierte Python-Pipeline und parst niemals
  menschenlesbare Terminalausgabe.
- Ein Familienprofil innerhalb desselben OS-Kontos ist keine Sicherheitsgrenze.

## Verwandte

- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Komponenten- und Sicherheitsgrenzen
- [`../PATTERNS.md`](../PATTERNS.md) — Gates und atomare Berichte
- [`../manifests/components/file-collect-sort-action.toml`](../manifests/components/file-collect-sort-action.toml) — Provider-Pin

## Historie

- **2026-08-21** — Initialer Phase-2-Vertrag erstellt
