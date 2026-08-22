# Workflow: Generate a ZIP package with one document per file type

**English** | [Deutsch](./document-package.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad-hoc  
> **Duration:** dependent on number of documents, page count, and image size

## Purpose

Deterministically group a nested folder by file type and output it as a new ZIP containing one document per group together with a verification manifest, without modifying the source files.

## Preconditions

- The source folder and the new `.zip` output file are explicitly selected.
- The output folder exists and is not a symbolic link.
- doc-services and the optional PDF dependencies are available.
- Write permission applies only to the new ZIP file itself.

## Steps

1. **Order files** — relative paths are deterministically sorted; symlinks are not allowed.  
2. **Form type groups** — images, PDF, TXT, and Markdown have fixed groups; additional known extensions receive a text group per type.  
3. **Secure unknowns** — unbound extensions are recorded with relative path, size, hash, and reason as `unsupported`.  
4. **Plan bundles** — each group uses the Phase-7 transformation contract with privacy status, handling, and loss notice.  
5. **Gate decision** — without `--approve-output-write` the plan remains unchanged.  
6. **Rehash sources** — unknown files must also remain unchanged relative to the plan.  
7. **Render group documents** — all outputs are generated in memory; no persistent working directory is created.  
8. **Generate manifest** — internal output hashes, sources, and loss thresholds are captured as UTF-8 JSON.  
9. **Publish ZIP atomically** — fixed ZIP metadata ensure reproducibility; an existing target is never overwritten.

## Exit-Criteria

- [ ] Exactly one ZIP was newly created; without the gate nothing was written.  
- [ ] Every supported file belongs to exactly one group.  
- [ ] Unknown files are visible in the manifest and hashed.  
- [ ] Each group contains exactly one TXT or PDF document.  
- [ ] The manifest contains no raw document text.  
- [ ] Sources are byte-identical; no intermediate folder exists.  
- [ ] The same plan produces byte-identical ZIPs.

## Pitfalls

- Grouping by extension is not a content-based classification.  
- A `DOCX.txt` receives text but no Word layout.  
- Very large folders are currently packaged in memory; resource limits are a later hardening step.  
- The ZIP hash is stored outside the ZIP because an embedded self-hash would be self-referential.

## Related

- [`./document-bundle.md`](./document-bundle.md) — single TXT/PDF bundle  
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-8 package data flow

## History

- **2026-08-21** — Created after Phase-8 end-to-end acceptance
