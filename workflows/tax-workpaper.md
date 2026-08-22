# Workflow: Private tax worksheet from confirmed receipts

**English** | [Deutsch](./tax-workpaper.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** after explicitly provided and categorized receipts  
> **Duration:** a few seconds per receipt and export  

## Purpose

Incorporate a cataloged receipt, after human category confirmation, locally into the pinned tax agents and optionally generate a private, non‑official ZIP worksheet.

## Preconditions

- The receipt is contained in the FolderHome document catalog and unchanged.  
- Profile and tax year have been explicitly selected.  
- The `steuer-assistent` checkout is clean and on the manifest revision.  
- A category has been confirmed by a human; a candidate alone is not sufficient.  
- Neither tax advice nor a government transmission is expected.

## Steps

1. **Check provider.**  

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome tax providers `
     --provider-root ..\steuer-assistent --json
   ```


2. **Prepare receipt request.** Document ID and optionally the FolderHome booking ID come from the local catalogs. Amount and date are not guessed from the file name.

3. **Generate receipt plan read‑only.**  

   ```powershell
   python -m folderhome tax receipt-plan `
     --request-file <receipt-request.json> `
     --profiles-dir examples\profiles --state-dir <state-dir> `
     --provider-root ..\steuer-assistent `
     --approve-sensitive-local-read --json
   ```


4. **Check plan.** Verify document hash, profile, cent amount, input group, provider revision and store revision. A plan with `review_required` must not be executed.

5. **Release receipt separately.** Approval binds plan ID, plan hash, action ID and store revision.

6. **Write exactly one receipt.**  

   ```powershell
   python -m folderhome tax receipt-apply `
     --request-file <receipt-request.json> `
     --approval-file <receipt-approval.json> `
     --profiles-dir examples\profiles --state-dir <state-dir> `
     --provider-root ..\steuer-assistent `
     --approve-sensitive-local-read --approve-state-write --json
   ```


7. **Generate export plan per profile and year.**  

   ```powershell
   python -m folderhome tax export-plan --profile lukas --tax-year 2026 `
     --output-file <STEUER_UNTERLAGEN_2026.zip> `
     --profiles-dir examples\profiles --state-dir <state-dir> `
     --provider-root ..\steuer-assistent --json
   ```


8. **Release export separately.** Only `tax export` with appropriate export approval, `--approve-state-write` and `--approve-output-write` creates a new ZIP file.

## Exit-Criteria

- [ ] Checkout, version and revision are confirmed.  
- [ ] The receipt is bound to a current document hash.  
- [ ] The category has been confirmed by a human.  
- [ ] No receipt was written without approval and state gate.  
- [ ] The export has its own approval and its own output gate.  
- [ ] No network, portal, shipping or official format was used.  
- [ ] The output is referred to as a private worksheet, not a tax return.

## Pitfalls

- An input group is not a statement about tax deductibility.  
- Family profiles map to separate stores, but are not a security boundary.  
- An outdated store hash or a modified receipt blocks the run.  
- An existing export file is not overwritten.  
- ELSTER, ERiC and tax authority transmission are not part of this workflow.

## Related

- [`../docs/phase29-tax-agent-reuse-and-plan.md`](../docs/phase29-tax-agent-reuse-and-plan.md)  
- [`../skills/folderhome-tax-workpaper/SKILL.md`](../skills/folderhome-tax-workpaper/SKILL.md)  
- [`../reused/steuer-assistent/README.md`](../reused/steuer-assistent/README.md)

## History

- **2026-08-22** — pinned receipt capture and private worksheet locally approved

---
