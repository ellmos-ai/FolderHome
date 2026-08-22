# Synthetischer FCSA-Dry-Run

Dieses Beispiel enthält ausschließlich erfundene Dokumente. Es zeigt einen
FolderHome-Sortierplan mit zwei Kategorien und geplanten Verschiebeaktionen,
ohne Dateien zu verschieben oder den konfigurierten FCSA-State anzulegen.

Vom Repository-Root aus:

```powershell
python -m folderhome run fcsa-plan `
  --config-dir examples\fcsa\config `
  --provider-root ..\file-collect-sort-action `
  --run-id run_fcsa_demo `
  --report-file run-reports\fcsa-demo.json `
  --json
```

Erwartung:

- beide Dateien bleiben in `inbox/`;
- `sorted/` und `runtime/` werden durch FolderHome nicht angelegt;
- der Bericht enthält ausschließlich geplante Dateisystemaktionen mit
  verweigertem Live-Gate und eine offene Entscheidungskarte.
