# PATTERNS.md — Wiederverwendbare Implementierungsmuster

## Side-Effects deklarieren und sperren

### Falsch

```python
plugin.execute(request)
```

Eine implizite Nebenwirkung ist weder prüfbar noch sicher freigebbar.

### Richtig

```python
if capability.side_effects and not gate.granted:
    return blocked_report
```

Jede Nebenwirkung steht im Capability-Vertrag und muss vor der Ausführung ein
Gate durchlaufen. Unbekannte Side-Effects machen bereits das Manifest ungültig.

## Berichte atomar veröffentlichen

### Falsch

```python
target.write_text(payload)
```

Ein Abbruch kann einen halben JSON-Bericht hinterlassen.

### Richtig

In dasselbe Verzeichnis schreiben, flushen, `fsync` ausführen und danach mit
`os.replace` atomar veröffentlichen. Temporärdateien werden im Fehlerfall
entfernt.

## Restart ohne doppelte Aktionen

Ein fortgesetzter Lauf behält seine `run_id`, übernimmt die bisherigen
Aktionsereignisse und vergibt die nächste fortlaufende Sequenznummer. Damit
bleiben sowohl Identität als auch Audit-Historie stabil.
