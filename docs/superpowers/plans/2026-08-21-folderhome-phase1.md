# FolderHome Phase 1 — Ausführungsplan

**Ziel:** Einen sicheren Integrationskern bereitstellen, der Komponenten
maschinenlesbar beschreibt, Läufe nachvollziehbar protokolliert und reale
Nebenwirkungen standardmäßig blockiert.

## Aufgaben

1. Projektgerüst, Provenienzkarte und Lizenzregister anlegen.
2. Gemeinsame Datenverträge für Plugins, Fähigkeiten, Aktionen, Evidenz,
   Entscheidungen, Undo und Laufberichte testgetrieben implementieren.
3. Gepinnte Manifeste für FCSA, HungryCall und Ringedingeding testgetrieben
   validieren; ungültige oder unbekannte Angaben müssen fail-closed enden.
4. Atomare JSON-Laufberichte mit dem Schema
   `ellmos.home-agent.run-report.v1` testgetrieben implementieren.
5. Einen synthetischen Run-Service für Erfolg, Blockierung, Fehler und
   Wiederaufnahme testgetrieben implementieren.
6. CLI für Manifestprüfung und synthetische Läufe ergänzen.
7. Tests, Ruff, Compileall, UTF-8/Umlaute und Git-Diff frisch verifizieren.

## Harte Phase-1-Grenzen

- keine echten Dateiänderungen außerhalb temporärer Testordner
- keine Netzwerk- oder Telefonaktionen
- keine Gesundheits-, Rechts- oder Finanzentscheidung
- keine Veröffentlichung, kein Push, keine Kosten
- keine Änderung an FCSA, HungryCall oder Ringedingeding

## Review-Checkpoint

Nach grüner Phase 1 wird der Branch unverändert lokal belassen, bis der Nutzer
über Integration, Remote und Veröffentlichung entscheidet.
