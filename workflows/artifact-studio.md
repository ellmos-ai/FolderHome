# Workflow: Safely plan and design artifacts

**English** | [Deutsch](./artifact-studio.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** ad-hoc  
> **Duration:** a few seconds for plan and local design output  

## Purpose

Assign a desired presentation, table, file, business card, or media output to the existing specialist, keep missing quality gates visible, and generate a local design set in a controlled manner.

## Preconditions

- Request and profile configuration are available locally as UTF-8 files.  
- Personal data may be read for this run.  
- Three new, distinct target paths are chosen for local design outputs.

## Steps

1. **Generate artifact plan** — no providers or skills are executed.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome artifacts plan `
     --request-file examples\artifacts\artifact-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```


2. **Check routes** — stop `blocked`, at `review_required` satisfy all listed gates and only continue `ready` without additional provider dependency.

3. **Generate design preview** — verify design tokens, contrast checks, and SVG content; this step writes nothing.

   ```powershell
   python -m folderhome artifacts design-preview `
     --request-file examples\artifacts\design-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```


4. **Release local output** — only after content review write three new files as a single batch.

   ```powershell
   $artifactOutput = Join-Path $env:TEMP "folderhome-artifact-demo"
   New-Item -ItemType Directory -Force $artifactOutput | Out-Null
   python -m folderhome artifacts design-render `
     --request-file examples\artifacts\design-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json-file "$artifactOutput\design-set.json" `
     --css-file "$artifactOutput\design-set.css" `
     --business-card-file "$artifactOutput\visitenkarte.svg" `
     --approve-output-write `
     --json
   ```


5. **Visually inspect** — rasterize each concrete SVG card or view it fully in a trusted local viewer. Only after that may a separate print release be considered.

## Exit-Criteria

- [ ] Each requested artifact type has a justified route.  
- [ ] No blocked provider was invoked or replaced.  
- [ ] Design contrasts have passed and user‑related content is correct.  
- [ ] Three new files match the report hashes.  
- [ ] Shipping, upload, printing, publishing, and remote processing did not occur.

## Pitfalls

- An installed skill does not prove that its runtime or render gate is available in the current session.  
- Poppler cannot render Office files itself; without `soffice` the corresponding Office view check is not satisfied.  
- A synthetically verified sample card does not prove the visual quality of a later card with different text lengths.  
- A second output run with the same paths overwrites nothing.

## Related

- [`../docs/phase25-artifact-studio-plan.md`](../docs/phase25-artifact-studio-plan.md)  
- [`../skills/folderhome-artifact-studio/SKILL.md`](../skills/folderhome-artifact-studio/SKILL.md)

## History

- **2026-08-22** — Provider plan, design set, and SVG business card approved for the first time

---
