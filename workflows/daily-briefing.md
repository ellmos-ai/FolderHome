# Workflow: Local Delivery of Weather and Newspaper Brief

**English** | [Deutsch](./daily-briefing.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** after provisioning a new dated snapshot pair  
> **Duration:** a few seconds  

## Purpose

Bundle a weather and news snapshot into a traceable HTML brief and copy exactly this output after a second approval into a chosen Desktop folder.

## Preconditions

- Weather and news snapshots follow the FolderHome‑V1 schemas.  
- Profile, briefing date, `as_of`, time zone and categories are explicitly set.  
- Snapshot sources use HTTPS and have fetch timestamps.  
- The Desktop folder already exists and is explicitly chosen.  
- A live fetch or an automatic scheduler registration is not expected.

## Steps

1. **Check provider boundaries.**  

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome briefing providers --json
   ```
  

2. **Create read‑only plan.** Clipboard and Desktop target must be different folders.  

   ```powershell
   python -m folderhome briefing plan `
     --request-file examples\briefing\briefing-request.json `
     --profiles-dir examples\profiles `
     --output-file <ausgabe\Morgenbrief.html> `
     --desktop-file <Desktop\Morgenbrief.html> `
     --approve-sensitive-local-read --json
   ```
  

3. **Check data status.** Verify weather location, observation time, news sources, categories, omitted articles and any `stale` warning.  
4. **Release render separately.** Approval binds plan ID, plan hash, HTML hash and intermediate output.  
5. **Render new HTML file.**  

   ```powershell
   python -m folderhome briefing render <Argumente aus Schritt 2> `
     --approval-file <render-approval.json> --approve-output-write --json
   ```
  

6. **Open rendered file locally and verify.** Check links, umlauts, weather values, warnings and source status.  
7. **Release Desktop copy separately.** Approval binds the same plan and HTML hash as well as exactly the Desktop target.  
8. **Deliver exact hash.**  

   ```powershell
   python -m folderhome briefing deliver <Argumente aus Schritt 2> `
     --approval-file <desktop-approval.json> --approve-desktop-write --json
   ```
  

## Exit criteria

- [ ] Profile, date, time zone and both snapshot hashes are visible.  
- [ ] Outdated data is marked as `stale` and `review_required`.  
- [ ] Rendering did not produce a Desktop file.  
- [ ] Desktop delivery copied exactly the approved HTML hash.  
- [ ] No existing file was overwritten.  
- [ ] No network or scheduler was used or registered.

## Pitfalls

- A local snapshot is not evidence of a currently successful live fetch.  
- `review_required` must not be presented as a current or complete newspaper.  
- The render gate does not replace the Desktop gate.  
- A single approval is not a permanent scheduler or network authorization.  
- Profiles organize briefings; the operating system account remains the security boundary.

## Related

- [`../docs/phase30-daily-briefing-plan.md`](../docs/phase30-daily-briefing-plan.md)  
- [`../skills/folderhome-daily-briefing/SKILL.md`](../skills/folderhome-daily-briefing/SKILL.md)  
- [`../reused/bach-daily-briefing/README.md`](../reused/bach-daily-briefing/README.md)

## History

- **2026-08-22** — local snapshot briefing and separate Desktop delivery approved  

---
