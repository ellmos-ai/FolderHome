# Workflow — health dossier

**English** | [Deutsch](./health-dossier.de.md)

## Purpose

Create an evidence‑based health dossier as Markdown and JSON from an explicitly selected local folder. The workflow is extractive: it chronologically orders documented statements, but does not provide a diagnosis, therapy decision, or medical completeness.

## Local run

```powershell
$env:PYTHONPATH = "src"
python -m folderhome health dossier `
  --source-dir examples\health `
  --profiles-dir examples\profiles `
  --profile lukas `
  --as-of 2026-08-22 `
  --gap-threshold-days 90 `
  --approve-sensitive-local-read `
  --output-markdown .local-demo\Gesundheitsdossier.md `
  --output-json .local-demo\Gesundheitsdossier.json `
  --json
```


The two output files must be new and located outside the analyzed source folder. Existing files are not overwritten.

## Input convention

For the first version, the following labels are particularly meaningful:

- `Dokumenttyp`, `Dokumentdatum`, `Fachbereich`
- `Befund`, `Ergebnis`, `Medikament`, `Termin`, `Offene Frage`
- `Dokumentierte Angabe: Feld = Wert`

Other readable documents can provide up to three pure source extracts. Without a clear document date, a source remains visible but is not sorted into the timeline. Direct conflicts are only detected for equally labeled `Dokumentierte Angabe` fields.

## Security boundaries

- The sensitivity gate is checked before the first extraction.
- RED classified content is only taken locally if the provider finding exclusively mentions `Gesundheitsdaten`.
- Other red findings such as IBAN, API token, or credentials remain blocked.
- Unreadable, blocked, undated, and future sources remain visible in the report.
- Time gaps only indicate that there is an interval between two dated sources; they do not prove a care gap.
- There is no network access, no LLM call, and no automatic calendar, medication, or contact action.
- `report-forge` is not invoked because of its inconsistent provider identity; Markdown and JSON are the canonical outputs of this phase.

---
