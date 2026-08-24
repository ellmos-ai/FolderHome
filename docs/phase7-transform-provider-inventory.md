# Phase 7 — Document Transformation Inventory

**English** | [Deutsch](./phase7-transform-provider-inventory.de.md)

**Reviewed:** 2026-08-21 21:51 Europe/Berlin  
**Goal:** Reuse existing building blocks without mixing transformation and original handling, and without overstating provider capabilities.

## Desired Capability

FolderHome shall be able to deterministically bundle selected documents or entire folders into a single text or PDF file. The output must not be silently overwritten. Sources remain untouched; archiving, gardener storage, or recycle bin may only occur after a proven successful transformation as a separate step.

## Reviewed Existing Components

| Component | Current State | Usable for FolderHome | Limitation |
|---|---|---|---|
| `doc-services` | clean checkout `e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2`, version `0.1.0` | Yes, pinned local extraction and privacy status | Reads documents; does not produce a TXT/PDF output file |
| MarkItDown | clean checkout `fd239d5d2be43d9b68329730206b9312c7d5a388`, MIT | Only indirectly via `doc-services` | Output is analysis‑markdown, explicitly not a high‑fidelity document conversion |
| `report-forge` | clean checkout `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | Not yet | Distribution reports `1.1.4`, runtime `1.1.0`; generic PDF processor is an unimplemented stub |
| `PDFtoPDFocr` | clean checkout `c89ae00982d7597b663c99527298363b9e2fce58`, version `1.1.3` | Later via a narrow headless boundary | GUI monolith imports PySide6; `merge_ocr_outputs` moves individual files after the merge, violating FolderHome’s source boundary |
| `file-collect-sort-action` | pinned on `8ebac2739c11c6a041abdd7b30131cef648b4753` | Yes, after successful transformation | Move and recycle bin, but no format conversion |
| Skill `batch-file-ops` | List/Copy/Move/Delete with dry run | No for transformation | File selection and operations, but no document format |
| Documents‑Skill | DOCX creation, merge, render and visual inspection as an agent tool | Not as product runtime | Helps with development and acceptance artifacts, but is not a pinned FolderHome provider |
| `ai-media-editor` | clean checkout `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | No for document bundling | Video, audio and hyper‑frame pipeline, no PDF/DOCX/ODT document output |

## Reuse Decision

1. `doc-services` remains the sole extraction provider. FolderHome will not rebuild MarkItDown or Office extraction.  
2. FCSA remains solely responsible for the separate, later original handling. Transformation never moves or deletes sources.  
3. `report-forge` stays fail‑closed until a unified provider identity is established. FolderHome does not copy its pipeline.  
4. The OCR and image‑to‑PDF path from `PDFtoPDFocr` will only be integrated when a narrow headless API without implicit moving is available. The competitive core does not import the GUI monolith.  
5. The demonstrably missing gap will be implemented in the repository as a new, extractable capability `folderhome.capabilities.document_transform`. Consequently it can be taken unchanged into the Sovereign stack after the competition, or split out into its own module.

## Contract for the New Core

- Planning and writing are separate calls.  
- A plan contains ordered sources, SHA‑256, output format, quality class, loss notices, gate and target path, but no raw text.  
- Supported first outputs are UTF‑8‑TXT and PDF.  
- PDF pages remain page‑faithful for PDF inputs; images are raster‑embedded; other supported documents are re‑set from the text extracted by `doc-services` and are therefore explicitly marked as layout‑lossy.  
- OCR is not an implicit fallback.  
- The target must be new; atomic publishing and re‑checking the source hash are mandatory.  
- Original handling is modeled only as a downstream action‑plan unlock, when the output hash and acceptance are available.

## Do Not Rebuild

- File‑type detection, extraction and privacy classification  
- OCR engine and language‑pack management  
- General move/recycle‑bin logic  
- DOCX report templates and Office renderer  
- Media and presentation rendering  

## Remaining New Build

1. Provider‑agnostic bundling plan with quality and loss contract  
2. Deterministic TXT publication  
3. PDF assembly for PDF, image and extracted text  
4. Atomic, never‑overwriting output layer with explicit gate  
5. Verified success evidence as prerequisite for original handling
