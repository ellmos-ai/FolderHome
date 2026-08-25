# WORKFLOWS.md — Router to Multi-Step Playbooks

**English** | [Deutsch](./WORKFLOWS.de.md)

> **Purpose:** Navigation. “Which workflow for which problem?”  
> **Content:** See `workflows/*.md` — there is **no** procedure detail here.  
> **Distinction from PATTERNS.md:** Patterns = individual code snippets.  
> **Workflows:** Multi-step procedures with side effects.  
> **Auto-generated:** The table in the AUTOGEN block below is maintained by `_tools/workflows-sync`. Handwritten content above and below the markers remains untouched.

---

## Available Workflows (auto-generated)

<!-- @auto-generated:workflow-index -->
<!-- last-updated: 2026-08-25 02:42 -->
<!-- tool: _tools/workflows-sync -->
<!-- count: 33 workflows in 1 categories -->

## General (33)

| Workflow | Purpose | Frequency | Duration |
|---|---|---|---|
| **Approve and Undo Document Action** [`document-action-execution.md`](./workflows/document-action-execution.md) | Execute a previously verified rename/move prefix for exactly one document, bound to plan, hash, and action, log it without gaps, and, if needed, re... | ad-hoc after human plan review | a few seconds per document on the same storage medium |
| **Build Local Document Library** [`document-library.md`](./workflows/document-library.md) | Index an explicitly chosen folder locally, search it naturally, and generate a thematic dossier or a folder report from it without moving source do... | ad‑hoc | depends on number of documents and file size |
| **Bundle Documents as TXT or PDF** [`document-bundle.md`](./workflows/document-bundle.md) | Merge a deliberately selected folder into a new TXT or PDF file without altering, archiving, or deleting the originals. | ad-hoc | dependent on number of documents, page count, and image size |
| **Capture Legal Changes as Review Candidates** [`legal-change-monitor.md`](./workflows/legal-change-monitor.md) | Technically compare two local, dated legal source states and match changed topics against explicitly recorded profile or contract interests. The re... | after a professionally created new legal source snapshot | a few seconds without procurement or legal review |
| **Check Document Contact and Register Locally** [`contact-register.md`](./workflows/contact-register.md) | Detect labeled contact data from explicitly selected documents locally, verify it against the responsible profile and a revision‑bound register, an... | for new or changed documents with responsibility data | a few seconds per document folder |
| **Create Document Action Plan from Profile Rules** [`document-action-plan.md`](./workflows/document-action-plan.md) | Check a synthetic or explicitly selected document against the rules of an organization profile and generate a traceable plan without altering the s... | ad-hoc or before each subsequent file execution | a few seconds per document |
| **Create FCSA Sorting Plan** [`fcsa-dry-run.md`](./workflows/fcsa-dry-run.md) | Inspect an existing document folder with the pinned FCSA component and create a traceable sorting plan without modifying the inbox folder, the targ... | ad-hoc | dependent on folder size |
| **Evaluate Multiple Observation Routines Read-Only** [`routine-queue.md`](./workflows/routine-queue.md) | Schedule all activated watches at a specific point in time, bundle comparable states, and detect conflicts across watch boundaries, without modifyi... | on every scheduled or manual check run | depends on the number of watches and documents |
| **Generate a ZIP package with one document per file type** [`document-package.md`](./workflows/document-package.md) | Deterministically group a nested folder by file type and output it as a new ZIP containing one document per group together with a verification mani... | ad-hoc | dependent on number of documents, page count, and image size |
| **Import bank statements locally and cent‑accurately** [`finance-import.md`](./workflows/finance-import.md) | Explicitly provided bank statements are checked, revision‑bound imported into the local finance store, and then coverage, transactions, and recurri... | after provision of new bank statements | a few seconds per statement folder |
| **Local Delivery of Weather and Newspaper Brief** [`daily-briefing.md`](./workflows/daily-briefing.md) | Bundle a weather and news snapshot into a traceable HTML brief and copy exactly this output after a second approval into a chosen Desktop folder. | after provisioning a new dated snapshot pair | a few seconds |
| **Medication Plan and Confirmed Intake** [`medication-intake.md`](./workflows/medication-intake.md) | Adopt a provided medication plan locally and evidence‑based, read the organizational daily view, and confirm an explicit intake as a separate appen... | according to an explicitly provided plan or an intake confirmation | a few seconds |
| **Personal Note Managed and Stored Revision‑Safely** [`personal-notes.md`](./workflows/personal-notes.md) | Review a human‑written note content with separate questions and suggestions, approve it precisely, and store it as a new version in the pinned loca... | when a personal note is explicitly requested | planning and local storage a few seconds |
| **Planned cleanup of observed folder** [`folder-routine.md`](./workflows/folder-routine.md) | Check a declared observed folder against its last checkpoint, plan a due set of changes or the full inventory, and execute a deliberately approved ... | after an explicitly triggered scan point | depending on file count and extraction formats |
| **Prepare a bounded provider inquiry with FindCall** [`findcall.md`](./workflows/findcall.md) | Prepare a serial inquiry for an appointment or quote from explicitly configured candidates. FindCall applies the user's time, location and price li... | ad hoc for appointment or quote searches | seconds for local planning and fixture simulation |
| **Prepare a read‑only queue for a scheduler** [`scheduler-handoff.md`](./workflows/scheduler-handoff.md) | Create a portable invocation and a Windows‑task artifact and safely coordinate a headless queue run without registering an operating‑system task or... | once per schedule and when configuration changes | plan under one second; runtime depends on document count |
| **Private tax worksheet from confirmed receipts** [`tax-workpaper.md`](./workflows/tax-workpaper.md) | Incorporate a cataloged receipt, after human category confirmation, locally into the pinned tax agents and optionally generate a private, non‑offic... | after explicitly provided and categorized receipts | a few seconds per receipt and export |
| **Run Strands Agent and Competition Demo** [`strands-agent.md`](./workflows/strands-agent.md) | Plan a limited execution of the real Strands‑Agents loop from FolderHome, run it reproducibly with synthetic data, and generate a hash‑bound compet... | per demo or agent acceptance | a few seconds without Bedrock; provider‑dependent with Bedrock |
| **Run benefit and funding pre-screen locally** [`benefit-screening.md`](./workflows/benefit-screening.md) | Match a local benefit profile against coarse, dated routing criteria and display appropriate official pre-checks. The result is guidance, not a cla... | when life situation changes or a fresh catalog | a few seconds plus official pre-check |
| **Safely clean up a batch folder** [`folder-cleanup.md`](./workflows/folder-cleanup.md) | Fully plan an explicitly selected folder, identify target conflicts across all documents, and then execute only a deliberately chosen subset with a... | ad-hoc, later as part of an observed routine | dependent on document count and extraction formats |
| **Safely hand over document appointment to calendar** [`calendar-handoff.md`](./workflows/calendar-handoff.md) | Check labeled appointment data from an explicitly selected document folder and, after exact approval, transfer it to the local FolderHome calendar ... | for new or changed documents with appointment information | a few seconds per document folder |
| **Safely plan and design artifacts** [`artifact-studio.md`](./workflows/artifact-studio.md) | Assign a desired presentation, table, file, business card, or media output to the existing specialist, keep missing quality gates visible, and gene... | ad-hoc | a few seconds for plan and local design output |
| **Safely plan and simulate calendar connector** [`calendar-connectors.md`](./workflows/calendar-connectors.md) | Generate a provider‑neutral connector plan for UpToday, Routinika, or Google from documented Phase‑17 appointment candidates and optionally test th... | upon explicitly requested calendar handoff | planning takes a few seconds; a real connector run is not part of the acceptance |
| **Scan Observed Folder and Verify Corrections** [`directory-observation.md`](./workflows/directory-observation.md) | Check a declared folder (without raw document text) against its last verified checkpoint, explain changes, and emit documented manual moves as lear... | ad‑hoc, later per scheduled scan run | dependent on file count and file size |
| **Securely Create Correspondence** [`correspondence-studio.md`](./workflows/correspondence-studio.md) | View a letter generated from a controlled template and a custom, inheritable design entirely locally first, and then output it as new Markdown and ... | ad-hoc | a few seconds per letter |
| **Securely create administrative draft** [`administrative-drafts.md`](./workflows/administrative-drafts.md) | Prepare a visibly unchecked and unsent administrative letter from a documented notice structure and provided information. The workflow generates on... | per objection, response, or application draft | a few seconds plus full human review |
| **Securely read, assign, and approve Mail** [`mail-connector.md`](./workflows/mail-connector.md) | Plan a mailbox fetch without changing the mailbox, adopt incoming message references in a provider‑neutral way, and place one prepared letter as a ... | when mail fetch or draft placement is explicitly triggered | plan under one second; provider runtime depends on mailbox |
| **Start Local FolderHome App** [`local-app.md`](./workflows/local-app.md) | Start the shared FolderHome chat interface on the current operating-system account. The GUI calls the same master-agent service as the CLI, shows r... | per local work session | a few seconds plus interactive usage |
| **Supplement Local Household Inventory** [`inventory-import.md`](./workflows/inventory-import.md) | Validate provided inventory observations, ingest them in a revision‑bound manner into the local append‑only inventory store, and then display curre... | after an explicitly documented inventory | few seconds per inventory folder |
| **Understanding a Social Law Official Notice** [`official-notice-understanding.md`](./workflows/official-notice-understanding.md) | Capture explicitly labeled information from a local official notice in a traceable way and output it as a verifiable Markdown/JSON report. This wor... | per provided official notice | a few seconds plus human review |
| **Use the FolderHome Master Agent** [`master-agent.md`](./workflows/master-agent.md) | Use one model-driven agent from GUI or CLI for FolderHome discovery, local read-only tools, and bounded domain planning. Keep semantic selection, d... | per conversational request | model-dependent; domain execution remains a separate workflow |
| **Workflow — Insurance and Contract Cockpit** [`contract-cockpit.md`](./workflows/contract-cockpit.md) | Answer a request such as “What is my latest car insurance for my Hyundai i10?” as a read‑only overview. The cockpit combines existing document vers... | — | — |
| **Workflow — health dossier** [`health-dossier.md`](./workflows/health-dossier.md) | Create an evidence‑based health dossier as Markdown and JSON from an explicitly selected local folder. The workflow is extractive: it chronological... | — | — |

<!-- @end:workflow-index -->

## Example (handwritten, for orientation)

If you prefer to work without the auto‑generator, the table could look like this:

| You want... | Open |
|---|---|
| [Start from the example to a real workflow] | [`workflows/_example-workflow.md`](./workflows/_example-workflow.md) |
| [Document a release process] | `workflows/release.md` (if created) |
| [Document a security playbook] | `workflows/security-audit.md` (if created) |
| [Document a hotfix process] | `workflows/hotfix.md` (if created) |
| [Maintain an admin playbook for force‑push] | `workflows/force-push.md` (if created) |

(You can delete this example block once `workflows-sync` is set up.)

## When which workflow?

- **After Dependabot alert** → use existing security playbook or create a new one  
- **After feature‑branch merge** → use or create release workflow  
- **When a crash in production** → use or create hotfix workflow  
- **When a new team member joins** → create orientation or onboarding workflow  
- **When cleaning up history** → own admin‑force‑push playbook of the project  

## When to create a new workflow

A new workflow is justified when:
- At least **5 steps** with **side effects** (not just “read docs”)  
- The procedure recurs at least **every 3 months**  
- There are **pitfalls** that an LLM agent cannot spontaneously reconstruct  
- A **clear exit criterion** exists (when is the workflow finished?)

If any of these points is missing: **no separate workflow**, but a section in an existing one or a pattern in `PATTERNS.md`.

## Conventions

See [`workflows/README.md`](./workflows/README.md) for:
- File structure of an individual workflow  
- Naming convention (no `WORKFLOW-A.md` — descriptive names!)  
- Required sections (Purpose, Steps, Exit Criteria, Pitfalls)
