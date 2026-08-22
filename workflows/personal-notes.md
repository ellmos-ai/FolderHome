# Workflow: Personal Note Managed and Stored Revision‑Safely

**English** | [Deutsch](./personal-notes.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** when a personal note is explicitly requested  
> **Duration:** planning and local storage a few seconds  

## Purpose

Review a human‑written note content with separate questions and suggestions, approve it precisely, and store it as a new version in the pinned local `llm-note` store.

## Preconditions

- Profile, notebook, area and state folder are explicitly selected.  
- The `llm-note` checkout is clean and on the manifest revision.  
- The person has authored or visibly confirmed the content to be stored.  
- A real remote LLM or synchronization approval is not part of this workflow.

## Steps

1. **Check provider** — Checkout, revision and package version must be `ready`.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome notes providers --provider-root ..\llm-note --json
   ```


2. **Create request** — `create`, `edit` or `revert` as well as declare only explicit references.

3. **Plan execution** — the read‑only run generates questions and suggestions, but no state.

   ```powershell
   $plan = python -m folderhome notes guide `
     --request-file examples\notes\create-request.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-note-demo" `
     --provider-root ..\llm-note --json | ConvertFrom-Json
   ```


4. **Human review** — check `proposed_content`, references, questions, suggestions, `plan_id`, `plan_sha256` and `content_sha256`.

5. **Create separate approval** — the file captures exactly the plan ID, plan hash, action ID and content hash, an offset timestamp, and `allow_local_note_write=true`.

6. **Append version** — only now set both write gates.

   ```powershell
   python -m folderhome notes apply `
     --request-file examples\notes\create-request.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-note-demo" `
     --provider-root ..\llm-note `
     --approval-file <approval.json> --approve-state-write --json
   ```


7. **Read history** — use the note ID from the plan.

   ```powershell
   python -m folderhome notes history --note-id $plan.note_id `
     --state-dir "$env:TEMP\folderhome-note-demo" `
     --provider-root ..\llm-note --json
   ```


## Exit‑Criteria

- [ ] Provider revision and package version are confirmed.  
- [ ] Questions and suggestions are separate from the approved content.  
- [ ] Nothing was written without approval and state gate.  
- [ ] The readback contains exactly the new append‑only revision.  
- [ ] Earlier revisions remain intact.  
- [ ] Network and external synchronization were omitted.

## Pitfalls

- `llm-note` does not generate LLM questions itself; it is the local storage.  
- A profile is not an access control mechanism against other processes in the same OS account.  
- `revert` does not delete a later version, but appends a new version with the earlier content.  
- A document hash in a reference does not prove that the document will remain unchanged later.  
- A guide plan is not a storage approval.

## Related

- [`../docs/phase28-llm-note-reuse-and-plan.md`](../docs/phase28-llm-note-reuse-and-plan.md)  
- [`../skills/folderhome-personal-notes/SKILL.md`](../skills/folderhome-personal-notes/SKILL.md)  
- [`../reused/llm-note/README.md`](../reused/llm-note/README.md)

## History

- **2026-08-22** — pinned llm‑note storage, separate execution and local append‑only version archive approved  

---
