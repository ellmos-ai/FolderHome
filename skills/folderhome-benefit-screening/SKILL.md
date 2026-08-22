---
name: folderhome-benefit-screening
description: Matches locally user-provided profile facts with a dated incomplete routing catalog and points to appropriate official benefit pre-screens, without claiming entitlement, amount, completeness or application.
---

# FolderHome Benefit Screening

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a person wants to know which official benefit pre‑screens, based on a few provided life‑situation data points, could be a sensible next verification step.

## Procedure

1. Request sensitivity approval, a known profile, benefit profile, catalog, analysis timestamp, and maximum source age limit.  
2. Verify that the catalog **`complete=false`** is listed and that each source is official, reachable via HTTPS, dated, and linked to an evidence summary.  
3. Execute **`benefits check`** locally. Do not open any website automatically.  
4. Explain for each program the routing status, missing facts, source, and all non‑modeled requirements.  
5. When a route matches, recommend **only** the named official pre‑screen. Designate it as the next verification step, not as an entitlement.  
6. Write Markdown/JSON only after your own output gate as new files.  
7. Leave personal input on the official site and any later application to a separate conscious user action.

## Binding Limits

- Do not determine benefit entitlement, benefit amount, or likelihood of success.  
- Never output **`routing_mismatch`** as a rejection or exclusion.  
- Do not guess missing profile information from documents, bank statements, or metadata.  
- Do not evaluate outdated or future sources.  
- Allow only official HTTPS handoffs without embedded credentials.  
- Do not claim catalog completeness.  
- No live web fetch, portal call, application, upload, or dispatch during the local run.  
- Do not overwrite an existing source or output.  
- Profiles are organizational; the operating system account remains the security boundary.  
- Do not write real sensitive profiles in repository examples.

---
