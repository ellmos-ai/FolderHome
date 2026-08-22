# Personal Notes — Synthetic Example

**English** | [Deutsch](./README.de.md)

`create-request.json` describes a purely synthetic, human‑written note content. Document and calendar references are explicitly specified; FolderHome does not search for or add any link itself.

First, only a guide plan is generated:

```powershell
python -m folderhome notes guide `
  --request-file examples\notes\create-request.json `
  --profiles-dir examples\profiles `
  --state-dir "$env:TEMP\folderhome-note-demo" `
  --provider-root ..\llm-note --json
```


The user reviews `proposed_content`, questions, suggestions, references, and hashes. From this exact plan, a separate `folderhome.personal-note-approval.v1` file is then created. Only after that `notes apply --approval-file <Datei> --approve-state-write` attaches a version to the local `llm-note` database.

For `edit`, `note_id` and the current `expected_revision` are taken over and new human content is provided. For `revert`, `human_content` `null` remains; `revert_to_revision` names the older version. A rollback is also a new version and not a deletion.

---
