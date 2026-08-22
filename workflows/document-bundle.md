# Workflow: Bundle Documents as TXT or PDF

**English** | [Deutsch](./document-bundle.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad-hoc  
> **Duration:** dependent on number of documents, page count, and image size  

## Purpose

Merge a deliberately selected folder into a new TXT or PDF file without altering, archiving, or deleting the originals.

## Preconditions

- Source folder, new output file, and output format are deliberately selected.  
- Optional transformation dependencies for PDF rendering are installed.  
- doc-services corresponds to the pinned clean checkout.  
- The output folder exists and is not a symbolic link.

## Steps

1. **Collect sources** — Files are deterministically ordered by relative path; symlinks and duplicate sources are not allowed.  
2. **Extract content** — Text sources go through doc-services. PDF pages and images can be taken directly for PDF without OCR.  
3. **Validate plan** — Each source lists hash, privacy status, handling, quality threshold, and possible loss; raw text does not appear in the plan.  
4. **Gate decision** — Without `--approve-output-write` the process ends after the plan and does not write a bundle file.  
5. **Re-validate sources** — Immediately before rendering, the path and SHA-256 must still match the plan.  
6. **Render in memory** — TXT remains UTF-8; PDF assembles pages, rasterizes images, or reconstitutes extracted text with visible layout loss.  
7. **Publish atomically** — The target is only created anew and never replaced.  
8. **Document result** — Output hash, size, optional page count, and all source document IDs are recorded in the result.

## Exit-Criteria

- [ ] Without the gate, no output file exists.  
- [ ] The target did not exist beforehand and was not overwritten.  
- [ ] All sources are byte-identical to the planning state.  
- [ ] TXT is UTF-8 with real umlauts.  
- [ ] PDF is readable, has at least one page, and exhibits layout loss.  
- [ ] The JSON plan contains no raw text.  
- [ ] Original handling remains a separate, still unapproved step.

## Pitfalls

- Text replacement is not a layout-accurate Office conversion.  
- PDF passthrough does not inspect document content and does not enable OCR.  
- An output hash proves the generated file, not its domain correctness.  
- DOCX, ODT, CSV, and XLSX are not yet output formats of this provider.

## Related

- [`../docs/phase7-transform-provider-inventory.md`](../docs/phase7-transform-provider-inventory.md)  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-7 boundary  
- [`./document-action-plan.md`](./document-action-plan.md) — Original handling  

## History

- **2026-08-21** — Created after Phase-7 end-to-end acceptance
