---
name: folderhome-artifact-studio
description: Plan and create FolderHome artifacts such as presentations, tables, documents, design sets, business cards, or media using existing specialized skills and explicit quality gates.
---

# FolderHome Artifact Studio

**English** | [Deutsch](./SKILL.de.md)

Use the FolderHome plan first. It does not make creative decisions about the
content, but checks which existing specialist is responsible and is demonstrably
usable in the current runtime.

```powershell
python -m folderhome artifacts plan `
  --request-file <artifact-request.json> `
  --profiles-dir <profiles-dir> `
  --approve-sensitive-local-read `
  --json
```


## Routing

- `presentation`: Use the `pptx` skill; for scientific content
  also `academic-pptx`. Do not generate PPTX if the content, rendering, or visual
  checks specified in the plan are not fulfillable.
- `spreadsheet`: Use the `Spreadsheets` skill exclusively with its
  provided workspace dependency loader. Check formulas and every visible table before output.
- `document`: Use the `documents` skill and its structural as well as
  visual DOCX acceptance. report-forge may serve as a provider only after a uniform
  distribution/runtime identity.
- `odt`: Stop as long as the plan does not specify a revision-bound ODT renderer with
  visual acceptance.
- `design_set` and `business_card`: Use `artifacts design-preview`, check
  content and contrast, then `artifacts design-render` with a separate
  output gate. Review each SVG map again before a print approval.
- `media`: Use ai-media-editor only on the clean revision specified in the plan.
  Real media require read approval; a cut strategy must be confirmed before rendering.

A status `blocked` may not be bypassed by a similar library, a
system Python, or an unchecked conversion. A status
`review_required` permits preparation, but no claim of completion without the
specified checks.

Shipping, upload, printing, publication, and remote processing are separate
actions and are never automatically derived from an artifact plan.

---
