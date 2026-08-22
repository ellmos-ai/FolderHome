# Synthetic Artifact Studio

**English** | [Deutsch](./README.de.md)

Both requests are completely synthetic. `artifact-request.json` shows the desired office, design, and media width. The plan does not invoke any provider and explicitly states that runtime or visual checks are missing.

`design-request.json` generates three new local files after approval:

- machine-readable JSON design tokens
- reusable CSS variables
- an SVG business card preview in 1050 × 600 format

The color combinations must achieve at least a WCAG contrast ratio of 4.5:1 for normal text. A successful SVG generation does not yet constitute visual print approval.

---
