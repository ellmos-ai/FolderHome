---
name: folderhome-administrative-drafts
description: Prepares clearly marked objection, authority response, and benefit application drafts from notice evidence and provided user information, and writes them locally only after exact confirmation, without legal review, deadline calculation, or dispatch.
---

# FolderHome Administrative Drafts

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a person wants to draft a controlled administrative letter from a provided notice or from their own information.

## Procedure

1. Determine `objection`, `authority_response`, or `benefit_application`.
2. Confirm profile, sender, recipient, desired outcome, and the explicit sensitivity approval.
3. For notice-related drafts, re-analyze the unchanged source. Verify source hash, authority, file reference, notice date, and evidence lines.
4. Generate `drafts preview` without writing. Display document facts and `user_provided` data separately, as well as all open items and warnings.
5. Indicate that neither legal recourse, deadline, jurisdiction, benefit eligibility, nor prospect of success have been examined.
6. Allow the person to confirm the complete letter and both hashes.
7. Write only new local Markdown/TXT files with exact approval and `--approve-output-write`.
8. Terminate the skill before any external effect. Subsequent use requires its own current professional review and a separate user action.

## Binding Limits

- No objection draft without an explicitly read legal remedy `Widerspruch`, a clear authority, and appropriate recipient binding.
- Do not calculate a statutory deadline from receipt date, file date, or deadline wording.
- Do not fabricate legal opinion, prospect of success, or benefit eligibility.
- Never present user statements as document evidence.
- The visible `ENTWURF`/check note must remain in the letter.
- No LLM, web, or law-checker call within the local drafting process.
- Do not overwrite existing output or source.
- No email, no authority portal, no upload, printing, or dispatch.
- Profiles are organizational; the operating system account remains the security boundary.
- Do not write real notices or personal data in repository examples.

---
