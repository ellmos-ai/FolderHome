# Synthetic FCSA Dry-Run

**English** | [Deutsch](./README.de.md)

This example contains only fictional documents. It shows a FolderHome sorting plan with two categories and scheduled move actions, without moving any files or creating the configured FCSA state.

From the repository root:

```powershell
python -m folderhome run fcsa-plan `
  --config-dir examples\fcsa\config `
  --provider-root ..\file-collect-sort-action `
  --run-id run_fcsa_demo `
  --report-file run-reports\fcsa-demo.json `
  --json
```


Expectation:

- both files remain in `inbox/`;
- `sorted/` and `runtime/` are not created by FolderHome;
- the report contains only scheduled filesystem actions with
  denied live gate and an open decision card.
