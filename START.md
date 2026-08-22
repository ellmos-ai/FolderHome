---
name: "folderhome-start"
type: session-bootstrap
version: 0.3.0
updated: 2026-08-21
last_verified: 2026-08-21
description: |
  Imperative bootstrap sequence for FolderHome sessions.
---

# START.md — Session-Bootstrap für FolderHome

1. Lies `CLAUDE.md`.
2. Prüfe `git status --short --branch` und bewahre fremde Änderungen.
3. Lies `STATE.md`, `TODO.md` und den letzten Eintrag in `CHANGELOG.md`.
4. Prüfe vor Änderungen die Herkunftsklasse in
   `COMPETITION_CODE_MAP.md` und die betroffenen Manifeste.
5. Schreibe für neues Verhalten zuerst einen Test und beobachte den erwarteten
   Fehler.
6. Führe vor einem Abschluss mindestens `pytest`, Ruff und `compileall` frisch
   aus.

## Verifikationskommandos

```powershell
python -m pytest
python -m ruff check .
python -m compileall -q src tests
python -m folderhome plugins validate --json
python _tools\doc-lint
python _tools\workflows-sync --check
```

## Sicherheitsstopp

Stoppe vor echten Datei-, Netzwerk-, Mail-, Kalender-, Telefon-, Kosten-,
Veröffentlichungs- oder Upload-Aktionen. Die lokale Phase 3 autorisiert nur
synthetische Dokumente, temporäre Testdateien und einen ausdrücklich
freigegebenen FolderHome-Indexordner. OCR bleibt deaktiviert.
