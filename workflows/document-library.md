# Workflow: Build Local Document Library

**English** | [Deutsch](./document-library.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad‑hoc  
> **Duration:** depends on number of documents and file size

## Purpose

Index an explicitly chosen folder locally, search it naturally, and generate a thematic dossier or a folder report from it without moving source documents or invoking external services.

## Preconditions

- The source folder is explicitly selected and contains only synthetic documents for acceptance.
- doc-services and KnowledgeDigest match the pinned manifests and their checkouts are clean.
- A dedicated FolderHome state folder is defined.
- The local index write approval is deliberately granted with `--approve-index-write`.

## Steps

1. **Check outputs** — Existing target reports are not overwritten; result and report paths must be different.  
2. **Check provider** — Version, Git revision, and clean checkout are verified against the manifests.  
3. **Extract documents** — doc-services reads each supported file without learning write access; OCR remains disabled.  
4. **Check identity** — FolderHome generates SHA‑256 and document ID. Before indexing, the source file is hashed again.  
5. **Index locally** — KnowledgeDigest is invoked exclusively with `archive=False` and the approved FolderHome state folder.  
6. **Check result** — Unknown formats are `skipped`, provider errors `failed`; raw texts do not appear in the JSON standard output.  
7. **Search or generate report** — Search and thematic dossier read the index read‑only; the folder report incorporates only content with data protection status `clear`.  
8. **Check versions** — A specific request maps appropriate cataloged sources via disclosed date signals and compares older versions sentence‑by‑sentence with the newest.  
9. **Validate archiving** — Older versions are passed only as unapproved proposals to the real FCSA Dry‑Run Bridge.  
10. **Prove immutability** — Verify source files and index file after pure search runs against the previous state.

## Exit‑Criteria

- [ ] No source document was moved, archived, or overwritten.  
- [ ] The index resides exclusively in the approved state folder.  
- [ ] JSON results contain no document raw text.  
- [ ] Search runs do not modify the index file.  
- [ ] Data protection status not equal to `clear` results in no content being incorporated into the folder report.  
- [ ] All errors and skips are visible per relative file.  
- [ ] Version plans show date basis and confidence.  
- [ ] FCSA confirms archiving only in Dry‑Run; the gate remains unassigned.

## Pitfalls

- KnowledgeDigest archives via its API by default. `archive=False` is mandatory and hard‑wired in the FolderHome bridge.  
- The public KnowledgeDigest search writes schema/WAL metadata. Use only the read‑only FolderHome search bridge.  
- An OS user account is the security boundary. Family profiles in the same account do not separate access rights.  
- Reaching a hit limit does not mean the dossier is complete; FolderHome marks this case.

## Related

- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Data flow and provider seams  
- [`../docs/phase3-document-reuse-inventory.md`](../docs/phase3-document-reuse-inventory.md) — Reuse decision  
- [`../manifests/components/doc-services.toml`](../manifests/components/doc-services.toml) — Extraction pin  
- [`../manifests/components/knowledge-digest.toml`](../manifests/components/knowledge-digest.toml) — Index pin  

## History

- **2026-08-21** — Created after synthetic CLI end‑to‑end acceptance
