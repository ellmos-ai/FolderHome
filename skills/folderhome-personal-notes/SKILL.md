---
name: folderhome-personal-notes
description: Guides people with separate questions and suggestions through local FolderHome notes, stores confirmed content in a revision‑secure manner in llm-note, and reads histories without remote LLM or synchronization.
---

# FolderHome Personal Notes

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a person wants to create a personal note, edit it, think it through in a structured way, or revert to an earlier version.

## Procedure

1. First, check the pinned storage provider.

   ```powershell
   python -m folderhome notes providers --json
   ```


2. Formulate the content requested by the person in the field `human_content`. Enter documents or appointments only as explicitly chosen references.

3. Generate a guide plan. Questions and suggestions are aids and must not silently modify `proposed_content`.

   ```powershell
   python -m folderhome notes guide `
     --request-file <request.json> --profiles-dir <profiles-dir> `
     --state-dir <state-dir> --provider-root <llm-note-checkout> --json
   ```


4. Show the person the content, references, questions, suggestions, and hash binding. Generate the approval file only after their explicit confirmation.

5. Store exactly the approved plan with `notes apply`, `--approval-file`, and `--approve-state-write`.

6. Verify with `notes history --note-id <id>` that a new revision has been added and no earlier version has been altered.

## Binding Limits

- The person is the author; the guide is not a co‑author.
- Suggestions remain separate from `human_content` and `proposed_content`.
- Remote LLMs, network, and external synchronization are disabled in phase 28.
- `create`, `edit`, and `revert` always add a version. There is no overwrite or delete command.
- Plan ID, plan hash, action, content hash, and store revision must match exactly; duplicates and outdated plans are blocked.
- Document and calendar references are not generated automatically nor claimed to be complete.
- Family profiles organize notes. The security boundary remains the operating system account.
- Do not store secrets in request, approval, examples, or repository.

---
