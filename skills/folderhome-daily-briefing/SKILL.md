---
name: folderhome-daily-briefing
description: Aggregates documented local weather and news snapshots into a source‑aware HTML brief and delivers it to a chosen desktop folder after separate approval, without claiming live network or scheduler.
---

# FolderHome Daily Briefing

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a human wants to plan, check, render, or copy a local weather and newspaper brief from already provided snapshots to the desktop.

## Process

1. Check `folderhome briefing providers --json`. Treat blocked live connectors as a real product boundary.  
2. Check briefing date, `as_of`, time zone, profile, weather location, categories, and the two snapshot paths.  
3. Generate `briefing plan` only after sensitivity approval. This step must not create any output or desktop file.  
4. Show data status, warnings, sources, omitted articles, plan hash, and HTML hash. An outdated snapshot remains explicitly outdated.  
5. Render only after your own render approval and `--approve-output-write` into a non‑desktop folder.  
6. Let the human review the local HTML file.  
7. Copy only after separate desktop approval and `--approve-desktop-write` exactly this hash to the chosen desktop.

## Binding Limits

- No silent weather, RSS, web, or LLM calls.  
- No claim of timeliness or completeness without a fresh snapshot.  
- Only HTTPS sources without embedded credentials.  
- No HTML takeover of unescaped titles, summaries, or links.  
- Do not overwrite existing output or desktop file.  
- Render and desktop target must not reside in the same target folder.  
- No scheduler registration or deriving permanent approval from a single approval.  
- Family profiles are organizational; the operating system account remains the security boundary.  
- Do not write real private location or profile data into repository examples.

---
