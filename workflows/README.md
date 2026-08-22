# workflows/ — Multi-Step-Playbooks

**English** | [Deutsch](./README.de.md)

> **Local conventions** for workflow files in this folder.  
> **Router in root:** [`../WORKFLOWS.md`](../WORKFLOWS.md) — contains the “Which workflow for what” overview.

---

## What belongs here

Playbooks for **repeatable multi-step processes** with side effects. Each workflow is its own file with a descriptive name (NOT `WORKFLOW-A.md`).

**Examples of good workflows:**
- `release.md` — Version bump, Build, Test, Tag, Push, Publish, Verify
- `hotfix.md` — Branch, Fix, Test, Merge, Cherry-Pick, Deploy
- `security-audit.md` — Dependabot scan, Update, Test, Commit, Push
- `add-module.md` — Scaffold, Tests, Wire-Up, Docs, Commit

**Examples of bad workflows (belong elsewhere):**
- ❌ “How do I install the project” → that is `README.md`
- ❌ “Why did we decide X that way” → that is `DECISIONS.md`
- ❌ “A 2-step process” → too small; use a command alias or local operator note

## File structure of a workflow

```markdown
# Workflow: [Short imperative title]

> **Last verified:** 2026-08-21
> **Frequency:** [daily / weekly / per release / ad-hoc]
> **Duration:** [~5 min / ~30 min]

## Purpose

[1-2 sentences: When do I need this workflow? What is the goal?]

## Preconditions

- [What must be true before starting]
- [Which tools and permissions the workflow requires]

## Steps

1. **[Step 1]** — [Description]
   ```bash
  
   [specific command]  
   ```

2. **[Step 2]** — [Description]
   ```bash
  
   [specific command]  
   ```

...

## Exit Criteria (check before completion)

- [ ] [Condition 1 — what must be true before the workflow is complete]
- [ ] [Condition 2]
- [ ] [Optional: changelog entry or local operator-state update]

## Pitfalls

- ⚠️ [Common failure 1 with a remedy]
- ⚠️ [Common failure 2]

## Related

- `x.md` — illustrative placeholder for the case where Y applies
- [`../SECURITY.md`](../SECURITY.md) — safety boundaries and approval gates

## History

- **2026-08-21** — Created
- **2026-08-21** — Extended step 3 with [pitfall X]
```


## Naming

- **Descriptive**, not letter suffix: `release.md`, `hotfix.md` — not `WORKFLOW-A.md`
- **Imperative** where possible: `add-module.md` instead of `module-adding.md`
- **Short**: max. 3 words, hyphenated: `security-audit.md`, `force-push.md`
- **Lowercase**: in the subfolder is the convention

## When to update a workflow

- On the **first time** the old workflow produces an error → document the root cause in “Pitfalls”
- On **tool updates** that change the flow → check version, bump last verified
- On **process changes** (e.g., new registry, new auth) → revise steps

**Staleness check:** Each workflow has a `Last verified` date. If older than 6 months and you are about to run it → verify first, then use.
