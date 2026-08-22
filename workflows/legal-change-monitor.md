# Workflow: Capture Legal Changes as Review Candidates

**English** | [Deutsch](./legal-change-monitor.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** after a professionally created new legal source snapshot  
> **Duration:** a few seconds without procurement or legal review  

## Purpose

Technically compare two local, dated legal source states and match changed topics against explicitly recorded profile or contract interests. The result is a checklist, not a determination of legal impact.

## Preconditions

- The clean `law-checker` checkout matches the pinned manifest.  
- Production snapshots originate from approved official HTTPS domains.  
- Text, topic tags, and the snapshot file are bound by SHA-256.  
- `complete=false` and the subject coverage are visible.  
- Legal interests have been provided by a human.  
- Sensitivity approval, `as_of`, and maximum source age are set.  

## Steps

1. **Check provider boundary.** `folderhome legal providers --json` must display the pinned checkout and `legal_review_api_available=false`.  
2. **Obtain snapshots and perform subject review.** FolderHome does not download any laws or parliamentary data itself in this workflow.  
3. **Execute comparison read‑only.** `folderhome legal compare` checks hashes, chronology, age, publication level, and normative section changes.  
4. **Classify matches.** A topic overlap generates only `review_candidate`; `affected_determined=false` remains immutable.  
5. **Separate draft from applicable law.** For `legislative_proposal` the overall status is `proposal_review_required`; the draft is never referred to as promulgated.  
6. **Optionally generate report.** `legal render` writes new Markdown/JSON files only after its own output gate and does not overwrite anything.  
7. **Commission subject review separately.** Legal effect, transitional law, case‑by‑case application, deadlines, and response remain outside the monitor.  
8. **Decide notification separately.** This run sends neither email nor desktop warning and does not register any scheduler.  

## Exit-Criteria

- [ ] Provider revision and registry coverage are visible.  
- [ ] Both the snapshot and the interest hash have been reread.  
- [ ] Non‑official, future, or outdated production sources are blocked.  
- [ ] Draft, promulgation, and consolidated state remain distinguishable.  
- [ ] Each match is only a `review_candidate`.  
- [ ] Legal effect, impact, and deadline calculation remain `false`.  
- [ ] No network access and no notification were performed.  
- [ ] Existing output files were not overwritten.  

## Related

- [`../docs/phase34-legal-change-monitor-plan.md`](../docs/phase34-legal-change-monitor-plan.md)  
- [`../skills/folderhome-legal-change-monitor/SKILL.md`](../skills/folderhome-legal-change-monitor/SKILL.md)  
- [`../reused/law-checker/README.md`](../reused/law-checker/README.md)  
- [`./official-notice-understanding.md`](./official-notice-understanding.md)  

## History

- **2026-08-22** — pinned provider and local snapshot comparison approved  

---
