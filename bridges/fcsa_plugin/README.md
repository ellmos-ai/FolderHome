# FCSA Bridge

Implementierter Adapter zwischen `folderhome.plugin.v1` und dem separat
gepinnten Repository `file-collect-sort-action`.

Der Code liegt installierbar unter `src/folderhome/bridges/fcsa.py`. Er prüft
Version, Git-Revision und einen sauberen Provider-Checkout, lädt die
dokumentierte FCSA-Python-Pipeline und führt ausschließlich einen Dry-Run mit
temporärem Schattenzustand aus. Anschließend übersetzt der Application Service
den Plan in `ellmos.home-agent.run-report.v1`.

Nicht implementiert und weiterhin gesperrt:

- Live-Ausführung von FCSA-Aktionen
- produktive Dry-Run-Bestätigung im FCSA-State
- implizite Auswahl eines echten Nutzerordners
- kopierter oder veränderter FCSA-Quellcode
