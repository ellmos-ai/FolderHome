# FolderHome Video Script — Maximum 4:30

> Production draft. Every on-screen document and profile must remain visibly
> synthetic. Do not replace measured test counts or hashes with estimates.

## 0:00–0:20 — Hook

**Voiceover**

“Your home already has the answer. It is just buried in a PDF, a photo, an old
policy, a bank statement, or the wrong folder. FolderHome is a local-first
Strands agent that turns that scattered paperwork into explainable household
workflows — without giving one model unlimited authority.”

**Picture**

Fast sequence of clearly synthetic documents entering one messy folder, then
the FolderHome interface. Persistent badge: “Synthetic demo data.”

## 0:20–0:50 — Problem, audience and importance

**Voiceover**

“It is for people and families managing insurance, appointments, health
administration, bills and official letters. The repetitive burden is not only
reading. It is finding the current version, preserving evidence, connecting
contacts and dates, and knowing what is safe to do next.”

**Picture**

Show four synthetic cards: insurance version, contact, appointment and bank
statement gap. No unimplemented live-action animation.

## 0:50–1:45 — Working Strands demo

**Voiceover**

“I ask: ‘Give me everything in my documents about health insurance.’ The
request enters a real Strands Agents loop. The model can choose only two
profile-bound, read-only tools. Here it selects the evidence dossier.”

**Picture**

Run:

```powershell
folderhome demo run --output-dir .local-demo\competition --approve-output-write --json
```

Then show `02-theme-dossier.json`, the tool event and `DEMO.md`. Highlight
framework `strands-agents`, the tool name, SHA-256 evidence,
`network_used=false` and the two synthetic source names.

**Voiceover**

“The credential-free fixture makes this exact loop reproducible for judges.
The same agent supports Amazon Bedrock, but only behind separate network and
local-data-disclosure gates.”

## 1:45–2:35 — From answer to real work

**Voiceover**

“FolderHome is more than retrieval. It can plan folder cleanup, detect versions
and misplaced files, build document bundles, maintain evidence-linked contacts
and appointments, reconstruct statement coverage, and prepare household,
health and administrative views.”

**Picture**

Use actual local outputs in a controlled montage: cleanup plan, Hyundai-i10
contract cockpit, finance coverage gap and health timeline. Label every
planned or simulated action exactly as such.

## 2:35–3:20 — Safety model

**Voiceover**

“Understanding does not grant authority. FolderHome plans first. Every
consequential step has a narrow approval, a fresh hash check, a never-overwrite
rule and an audit trail. Family profiles organize preferences, but the
operating-system account remains the real security boundary.”

**Picture**

Animate the flow: request → plan → evidence → human approval → recheck → local
action → undo/audit. Show a blocked mail or phone action, not a fabricated
success.

## 3:20–3:55 — Architecture and reuse

**Voiceover**

“The Strands agent reuses one local application service. Domain capabilities
are isolated packages. Existing ellmos modules are connected through exact
revisions and manifests, with their provenance disclosed instead of relabeled
as new code.”

**Picture**

Show `ARCHITECTURE_DIAGRAM.md`, then `COMPETITION_CODE_MAP.md` and the component
manifest directory.

## 3:55–4:20 — Impact and close

**Voiceover**

“FolderHome makes household paperwork searchable, connected and actionable —
while keeping uncertainty and human control visible. Assistantify your home.”

**Picture**

Return to the local dashboard with the concise end card:

- FolderHome
- Assistantify your home.
- Local-first. Evidence-linked. Human-gated.

## Production checks

- Keep final duration below five minutes.
- Use only measured counts from the final completion audit.
- Show the working project, not mockups, during the demo section.
- Keep “Synthetic demo data” visible whenever documents or profiles appear.
- Add English captions if any spoken material is not English.
- Upload and public visibility remain separate user gates.
