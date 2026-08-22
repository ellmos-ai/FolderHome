# Workflow: Securely Create Correspondence

**English** | [Deutsch](./correspondence-studio.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** ad-hoc  
> **Duration:** a few seconds per letter

## Purpose

View a letter generated from a controlled template and a custom, inheritable design entirely locally first, and then output it as new Markdown and TXT files. Existing files are not overwritten.

## Preconditions

- Requests, designs, and templates are local UTF-8 JSON files.  
- The specified profile exists in the profile configuration.  
- Personal data may be read for this local run.  
- Both planned output paths are new and distinct.

## Steps

1. **Generate preview** — check design resolution, content, hashes, and blocked Office‑handoffs.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome correspondence preview `
     --request-file examples\correspondence\insurance-cancellation.json `
     --designs-file examples\correspondence\designs.json `
     --templates-file examples\correspondence\templates.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```


2. **Validate content** — compare sender, recipient, date, subject, contract identifier, deadline, attachments, and selected design with the sources. The preview run does not write any file.

3. **Choose new target paths** — specify a dedicated output folder and two filenames that do not yet exist.

   ```powershell
   $demoOutput = Join-Path $env:TEMP "folderhome-correspondence-demo"
   New-Item -ItemType Directory -Force $demoOutput | Out-Null
   ```


4. **Release output** — write Markdown and TXT as a single batch only after visual inspection.

   ```powershell
   python -m folderhome correspondence render `
     --request-file examples\correspondence\insurance-cancellation.json `
     --designs-file examples\correspondence\designs.json `
     --templates-file examples\correspondence\templates.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --markdown-file "$demoOutput\Versicherungskuendigung.md" `
     --text-file "$demoOutput\Versicherungskuendigung.txt" `
     --approve-output-write `
     --json
   ```


5. **Check hashes and boundaries** — compare report hashes with the two files and verify that no Office, LLM, or remote provider was executed.

## Exit-Criteria

- [ ] Preview mentions the expected design and `read_only=true`.  
- [ ] Sender, recipient, content, attachments, and evidence references are verified.  
- [ ] Both new files have the hashes listed in the output report.  
- [ ] `provider_invoked=false`; shipping, printing, and publishing were omitted.

## Pitfalls

- Unsafe placeholders with attribute, index, conversion, or format syntax are intentionally blocked.  
- Missing and extra variables are configuration errors.  
- All design bindings are explicit; there is no fuzzy mapping.  
- The dual output is pre‑checked and rolled back on any individual sub‑error.  
- DOCX/ODT are released only when provider identity and visual rendering checks are demonstrably correct.  
- A second run with the same target paths overwrites nothing.

## Related

- [`../docs/phase24-correspondence-studio-plan.md`](../docs/phase24-correspondence-studio-plan.md)  
- [`../examples/correspondence/README.md`](../examples/correspondence/README.md)

## History

- **2026-08-22** — Synthetic preview/render workflow created and verified

---
