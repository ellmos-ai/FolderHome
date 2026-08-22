---
name: folderhome-legal-change-monitor
description: Compares two dated local legal source snapshots, assigns technical norm changes to explicitly stored profile or contract topics as review candidates, and strictly separates drafts, promulgation, legal effect, and notification.
---

# FolderHome Legal Change Monitor

**English** | [Deutsch](./SKILL.de.md)

Use this skill when new, already acquired legal source versions need to be compared with an earlier version and possible profile or contract references should be collected for later professional review.

## Process

1. Qualify the pinned `law-checker`-Checkout via `legal providers`; do not import an unassigned legal reviewer.
2. Request two chronological snapshots, interests, `as_of`, age limit, and sensitivity approval.
3. Accept only authorized official HTTPS domains, `authoritative=true` and `complete=false`, on the production path.
4. Verify file and word hash signatures before comparison.
5. Compare norm sections technically as added, changed, or removed.
6. Match only explicit `user_provided` topics and name each hit `review_candidate`.
7. Display `legislative_proposal` visibly as a draft.
8. Write reports only behind your own output gate and as new files.
9. Hand over legal review and notification to separate, deliberately releaseable follow‑up steps.

## Binding Limits

- Do not derive any legal effect, validity, impact, or claim change.
- Do not calculate any statutory or procedural deadline.
- Do not guess topic tags from sensitive documents.
- Never output drafts as applicable or promulgated law.
- Do not evaluate outdated, future, incompletely bound, or non‑official sources.
- No automatic web research, legal review, email, warning, or scheduler registration during the comparison run.
- Test fixtures only with an explicit test gate and never use them as a legal source.
- Do not overwrite existing sources or outputs.
- The operating system account remains the security boundary.

---
