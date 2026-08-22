# Workflow: Run benefit and funding pre-screen locally

**English** | [Deutsch](./benefit-screening.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** when life situation changes or a fresh catalog  
> **Duration:** a few seconds plus official pre-check  

## Purpose

Match a local benefit profile against coarse, dated routing criteria and display appropriate official pre-checks. The result is guidance, not a claim or rejection notice.

## Preconditions

- The organizational profile exists.  
- Benefit profile facts have been provided by a person and verified locally.  
- The catalog lists only official HTTPS sources with a verification timestamp.  
- `complete=false` and unmodeled requirements are visible.  
- The desired analysis timestamp and the maximum source age are set.

## Steps

1. **Run the pre-check read‑only.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome benefits check `
     --profile-facts-file examples\benefits\Lukas-benefit-profile.json `
     --catalog-file examples\benefits\official-routing-catalog.json `
     --profiles-dir examples\profiles `
     --as-of 2026-08-22T07:00:00+02:00 `
     --max-source-age-days 30 `
     --approve-sensitive-local-read --json
   ```


2. **Check source status.** Verify publisher, URL, `checked_at`, source age, evidence summary, and catalog coverage.

3. **Classify the results.** `official_handoff_recommended` is only a route. `needs_information` requests missing facts. `routing_mismatch` is not a rejection. `blocked_source_stale` first requires a new professionally verified snapshot.

4. **Optionally write a local report.**

   ```powershell
   python -m folderhome benefits render <Argumente aus Schritt 1> `
     --markdown-file <Ausgabe\Leistungsvorcheck.md> `
     --json-file <Ausgabe\Leistungsvorcheck.json> `
     --approve-output-write --json
   ```


5. **Open the official pre-check deliberately.** Enter personal data on the official site only after your own decision. FolderHome does not open the URL automatically.

6. **Wait for a binding decision.** Only the responsible authority decides on entitlement, amount, and required evidence.

## Exit-Criteria

- [ ] Profile and catalog hash as well as explicit `as_of` are visible.  
- [ ] No source is newer than `as_of` or older than the age limit.  
- [ ] Missing facts and unmodeled requirements are visible.  
- [ ] The catalog exhibits `complete=false`.  
- [ ] No benefit entitlement or amount was claimed.  
- [ ] No application, web request, or other external step occurred.  
- [ ] Existing output files were not overwritten.

## Pitfalls

- A matching routing attribute is not a prerequisite for entitlement.  
- A mismatch proves neither exclusion nor missing entitlement.  
- An official calculator is only as up‑to‑date as the specific page.  
- A local catalog does not become current automatically based on its file date.  
- Benefit profiles contain sensitive information and remain local.

## Related

- [`../docs/phase33-benefit-screening-plan.md`](../docs/phase33-benefit-screening-plan.md)  
- [`../skills/folderhome-benefit-screening/SKILL.md`](../skills/folderhome-benefit-screening/SKILL.md)  
- [`../reused/benefit-routing/README.md`](../reused/benefit-routing/README.md)  
- [`./administrative-drafts.md`](./administrative-drafts.md)

## History

- **2026-08-22** — source‑bound pre-check with official handoffs accepted

---
