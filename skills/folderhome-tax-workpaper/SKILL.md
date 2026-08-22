---
name: folderhome-tax-workpaper
description: Plans and records human‑sorted tax receipts evidence‑bound in the local tax‑assistant and exports private work documents after separate approval without tax advice or portal transmission.
---

# FolderHome Tax Workpaper

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a person wants to organize provided receipts for a private tax workpaper or export such a workpaper.

## Procedure

1. Check the pinned, clean provider checkout with `folderhome tax providers --json`.  
2. Use only a document ID from the FolderHome catalog. Verify the current document hash and, if a financial posting is provided, the profile and cent amount.  
3. Treat `category_candidate` solely as a suggestion. Without `confirmed_category` the plan is not executable.  
4. Generate `tax receipt-plan` only after local sensitivity approval.  
5. Show the person the profile, amount, date, category, document binding, plan hash, and provider-store revision.  
6. Execute `tax receipt-apply` only with an exactly matching approval and `--approve-state-write`.  
7. Plan a ZIP workpaper with `tax export-plan` separately for exactly one profile and tax year.  
8. Export only with your own export approval as well as state and output gate.

## Binding Limits

- No tax deductibility verification, tax advice, or recommendation.  
- No tax calculation, official tax return, or completeness guarantee.  
- No ELSTER, ERiC, tax office, network, or transmission access.  
- No automatic adoption of a category suggestion.  
- No storage without plan, approval, document hash, and provider-store binding.  
- No mixing of different profiles in the same Provider database.  
- Profiles are organizational; the operating system account remains the security boundary.  
- Do not overwrite an existing export file.  
- Do not incorporate real receipts, account data, or secrets into repository examples.

---
