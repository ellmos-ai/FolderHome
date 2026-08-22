# Workflow: Securely create administrative draft

**English** | [Deutsch](./administrative-drafts.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** per objection, response, or application draft  
> **Duration:** a few seconds plus full human review

## Purpose

Prepare a visibly unchecked and unsent administrative letter from a documented notice structure and provided information. The workflow generates only local Markdown/TXT files.

## Preconditions

- Profile, sender, recipient, desired outcome, and user statements have been explicitly provided.  
- For an objection or authority response, a current Phase‑31 analysis of the same unchanged source is available.  
- The request contains the SHA‑256 of the expected notice source.  
- Letter design and special administrative letter templates have been reviewed.  
- Deadline, legal route, jurisdiction, and content are examined separately by subject‑matter experts.

## Steps

1. **Generate read‑only preview.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome drafts preview `
     --request-file examples\notices\objection-draft-request.json `
     --source-file examples\notices\Bescheid.txt `
     --designs-file examples\correspondence\designs.json `
     --templates-file examples\notices\administrative-templates.json `
     --profiles-dir examples\profiles `
     --received-on 2026-08-15 `
     --as-of 2026-08-22T06:00:00+02:00 `
     --approve-sensitive-local-read --json
   ```


2. **Check provenance.** Document facts must specify line, document ID, and source hash. User statements must remain `user_provided`.

3. **Check open items.** In particular, verify deadline, jurisdiction, type of legal remedy, file reference, recipient, and attachments against the original. `review_required` is not considered “legally reviewed.”

4. **Read the letter in full.** The visible `ENTWURF` notice must be included in both Markdown and TXT.

5. **Generate approval.** Adopt the plan ID, Markdown hash, and TXT hash from exactly this preview. Content reviewed, missing legal review understood, and confirm local output only with a boolean each.

6. **Write local output behind its own gate.**

   ```powershell
   python -m folderhome drafts render <Argumente aus Schritt 1> `
     --approval-file <draft-approval.json> `
     --markdown-file <Ausgabe\Verwaltungsentwurf.md> `
     --text-file <Ausgabe\Verwaltungsentwurf.txt> `
     --approve-output-write --json
   ```


7. **Decide external impact separately.** FolderHome Phase 32 has no dispatch. Before any real use, the current subject‑matter review, including deadline, form, authority, and attachments, is required.

## Exit‑Criteria

- [ ] Notice source, profile, recipient, and source hash match.  
- [ ] Document evidence and provided information are separate.  
- [ ] The specific letter content and both output hashes have been confirmed.  
- [ ] Markdown and TXT visibly carry the draft/review notice.  
- [ ] Existing files were not overwritten.  
- [ ] Legal review, benefit review, and deadline calculation were omitted.  
- [ ] No email, portal, printing, or dispatch was triggered.

## Pitfalls

- A legal remedy printed in the notice does not prove its correctness or applicability in the individual case.  
- A calculated remaining‑days value from Phase 31 is not a legal deadline.  
- `user_provided` does not already mean confirmed or evidenced.  
- A local output approval is not a dispatch approval.  
- A benefit application draft is not a benefit and funding pre‑screen.

## Related

- [`../docs/phase32-administrative-drafts-plan.md`](../docs/phase32-administrative-drafts-plan.md)  
- [`./official-notice-understanding.md`](./official-notice-understanding.md)  
- [`./correspondence-studio.md`](./correspondence-studio.md)  
- [`../skills/folderhome-administrative-drafts/SKILL.md`](../skills/folderhome-administrative-drafts/SKILL.md)

## History

- **2026-08-22** — evidence‑based local administrative drafts approved

---
