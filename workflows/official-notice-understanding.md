# Workflow: Understanding a Social Law Official Notice

**English** | [Deutsch](./official-notice-understanding.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** per provided official notice  
> **Duration:** a few seconds plus human review  

## Purpose

Capture explicitly labeled information from a local official notice in a traceable way and output it as a verifiable Markdown/JSON report. This workflow is for document understanding, not legal review.

## Preconditions

- The official notice is stored locally in a format supported by `doc-services`.  
- The relevant profile exists in the selected profile configuration.  
- An optional receipt date comes from a human and is known as such.  
- The pinned `doc-services` checkout is clean and revision‑accurate.  
- Qualified assistance is reachable for ongoing or unclear deadlines.

## Steps

1. **Check provider boundaries.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome notices providers --json
   ```
  

   `document_extraction` must be `ready`. `legal_review` remains in Phase 31 as expected `blocked_not_integrated`.

2. **Analyze official notice read‑only.** Provide the receipt date only if the human actually confirmed it.

   ```powershell
   python -m folderhome notices inspect `
     --source-file examples\notices\Bescheid.txt `
     --profiles-dir examples\profiles `
     --profile lukas `
     --received-on 2026-08-21 `
     --as-of 2026-08-22T12:00:00+02:00 `
     --approve-sensitive-local-read --json
   ```


3. **Check evidence and limits.** Verify source hash, lines, missing fields, conflicts, printed deadline wording and any explicitly printed deadline date. Remaining days are only calendar arithmetic relative to that printed date.

4. **Approve report separately.** Choose two new, not‑yet‑existing targets and leave the source unchanged.

5. **Render Markdown and JSON.**

   ```powershell
   python -m folderhome notices render `
     --source-file examples\notices\Bescheid.txt `
     --profiles-dir examples\profiles `
     --profile lukas `
     --received-on 2026-08-21 `
     --as-of 2026-08-22T12:00:00+02:00 `
     --markdown-file <Ausgabe\Bescheidbericht.md> `
     --json-file <Ausgabe\Bescheidbericht.json> `
     --approve-sensitive-local-read --approve-output-write --json
   ```


6. **Make a human decision.** In case of `review_required`, unclear deadline, or desired legal assessment, give the report together with the original to a qualified entity. Do not send any response from Phase 31.

## Exit‑Criteria

- [ ] Profile, analysis time, document ID and source hash are visible.  
- [ ] Each adopted field cites its exact source line.  
- [ ] Conflicts and missing information were not hidden.  
- [ ] Relative deadline wordings were not converted to statutory dates.  
- [ ] Report and JSON are newly created; the original remained unchanged.  
- [ ] `legal_review_status` reads `not_performed`.  
- [ ] No response, email, authority action, or other external effect occurred.

## Pitfalls

- A printed date may be incorrect, incomplete, or legally not the actual deadline end.  
- File and scan timestamps are not receipt dates.  
- OCR is intentionally disabled in this phase.  
- `ready_for_review` means ready for human review, not legally correct or complete.  
- A relative deadline wording such as “within one month” requires a current legal review and must not be automatically reinterpreted.

## Related

- [`../docs/phase31-official-notice-understanding-plan.md`](../docs/phase31-official-notice-understanding-plan.md)  
- [`../skills/folderhome-official-notices/SKILL.md`](../skills/folderhome-official-notices/SKILL.md)  
- [`../reused/law-checker/README.md`](../reused/law-checker/README.md)

## History

- **2026-08-22** — evidence‑based official notice understanding locally approved  

---
