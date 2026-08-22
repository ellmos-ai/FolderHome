---
name: "folderhome"
type: project-docs
profile: "FULL"
version: 0.1.0
created: "2026-08-21"
updated: 2026-08-22
reason_last_change: "Öffentliches Wettbewerbsrepository freigegeben"
last_verified: 2026-08-21
author: "Lukas Geiger"
anthropic_compatible: true
description: |
  Project-specific instructions for AI coding agents in FolderHome.
---

# CLAUDE.md — Arbeitsregeln für FolderHome

## Projekt

**FolderHome** ist ein lokaler Dokument- und Assistenzservice-Agent für
Alltagsabläufe.

- Pfad: `C:\_Local_DEV\repos\folderhome`
- Repository: `https://github.com/ellmos-ai/FolderHome`
- Stack: Python 3.11+, Standardbibliothek zuerst
- Sprache: Deutsch in Endnutzertexten, Englisch für Code und Identifier

## Session-Einstieg

1. `git status --short --branch`
2. `STATE.md`, `TODO.md` und den letzten Changelog-Eintrag lesen
3. Passende Tests zuerst rot ausführen
4. Minimal implementieren und anschließend vollständig verifizieren

## Befehle

```powershell
python -m pytest
python -m ruff check .
python -m compileall -q src tests
python -m folderhome plugins validate --json
```

## Harte Regeln

- Keine Credentials oder personenbezogenen Echtdaten committen.
- Keine realen Datei-, Netzwerk-, Mail-, Kalender- oder Telefonaktionen ohne
  explizites Gate und gesonderte Nutzerfreigabe.
- Unbekannte Plugins, Fähigkeiten, Side-Effects oder Manifestfelder werden
  fail-closed behandelt.
- Jede Aktion erhält `run_id`, Status, Provenienz, Gate-Status, Evidenz und
  gegebenenfalls einen Undo-Vertrag.
- FCSA, HungryCall und Ringedingeding bleiben eigenständige Komponenten;
  deren Quellcode wird hier nicht still kopiert oder verändert.
- Neue Funktionen leben gekapselt in `src/folderhome`, `bridges` oder `skills`.
- Endnutzertexte auf Deutsch verwenden echte Umlaute: ä, ö, ü, Ä, Ö, Ü.
- Neue Verhaltensfunktionen entstehen testgetrieben: Rot, Grün, Refaktor.
- Kein Push, Remote, Release oder öffentlicher Upload ohne Nutzerentscheidung.

## Dokumentationsgrenzen

- `COMPETITION_CODE_MAP.md` ist die Herkunftsübersicht.
- `THIRD_PARTY_LICENSES.md` und `manifests/components/` belegen Bestand.
- `STATE.md` hält den knappen Ist-Stand; `TODO.md` nur offene Aufgaben.
- Bei zu langen Steuerdateien gilt `CUT-AND-CLUE.md`.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
