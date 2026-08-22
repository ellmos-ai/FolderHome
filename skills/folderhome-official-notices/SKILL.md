---
name: folderhome-official-notices
description: Captures explicitly labeled information from a local official notice with line and hash evidence and generates, after approval, a review report, without claiming legal review, statutory deadline calculation, or a response.
---

# FolderHome Official Notices

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a person wants to initially capture a provided authority or social benefit official notice in a clear and understandable way.

## Procedure

1. Check `folderhome notices providers --json`. Use the analysis only if `document_extraction` is ready; treat the blocked legal review as an actual product boundary.
2. Confirm source, profile, analysis timestamp, and the explicit sensitivity approval. Request a date of receipt only as a user-provided value.
3. Execute `notices inspect` read-only and display official notice type, authority, file reference, decision, deadline wording, missing fields, conflicts, and all evidence lines.
4. Make clear that only explicitly labeled information has been transferred. Do not convert relative deadline wording into dates.
5. Generate Markdown and JSON only after `--approve-output-write` in two new paths. Verify source hash and never-overwrite.
6. Hand over the original and report immediately to qualified social law assistance when the deadline is ongoing, unclear, or possibly expired.

## Binding Limits

- No legal advice or assessment of legality.
- Do not calculate a statutory deadline or confirm it as binding.
- Do not derive a date of receipt from file, scan, email, or OCR metadata.
- No silent web, LLM, or law-checker calls.
- Do not generate or send any response, objection, or application.
- Do not overwrite an existing file or modify the source document.
- Leave missing and contradictory fields visible.
- Declare `ready_for_review` only as readiness for human review.
- Family profiles are organizational; the operating system account remains the security boundary.
- Do not incorporate real official notices or private profile data into repository examples.

---
