# Phase 36 — Completion-Audit

**English** | [Deutsch](./phase36-completion-audit.de.md)

**Status:** 2026-08-22  
**Audit subject:** local competition state `phase1-foundation`  
**Phase scope:** 36 of 36  
**Publication status:** public MIT‑licensed repository approved, not submitted

## Result

The local FolderHome competition build is complete: All 36 defined phases have executable code or an explicitly Handoff‑defined provider contract, automated success and boundary checks, and up‑to‑date documentation. The reproducible competition demo runs a real Strands agent with two FolderHome tools, without network access or real personal data.

> "Complete" here refers to the agreed‑upon local competition scope. It expressly does not mean that optional live connectors, Amazon Bedrock, telephony, email sending, public URLs, or Devpost have already been approved or executed.

## Evidence Model

A phase is considered locally satisfied only if all of the following conditions are met:

1. The canonical contract and orchestration reside in the new FolderHome core or an open bridge.  
2. Success path and at least one critical fail‑closed boundary are covered by tests.  
3. A provider Handoff is not referred to as a live execution.  
4. Origin, security, and remaining external impact are documented.

## Requirement-by-Requirement-Matrix

| Phase | Requirement | Authoritative code evidence | Test evidence | Result |
|---:|---|---|---|---|
| 1 | Integrations foundation, manifests, audit, CLI | `contracts`, `run_service.py`, `capabilities/audit`, `manifests/` | `test_contracts.py`, `test_run_service.py`, `test_plugin_manifests.py` | Belegt |
| 2 | FCSA‑Dry‑Run‑Bridge | `bridges/fcsa.py`, `application/fcsa_plan.py` | `test_fcsa_bridge.py` | Belegt; no real movement |
| 3 | Ingest, search, topic dossier, folder report | `document_ingest.py`, `document_search.py`, `folder_report.py` | `test_folder_ingest.py`, `test_document_search.py`, `test_folder_report.py` | Belegt |
| 4 | Versions, comparison, archive plan | `document_versions.py`, `version_analysis.py`, `archive_fcsa_plan.py` | `test_document_versions.py`, `test_version_analysis.py`, `test_archive_fcsa_plan.py` | Belegt |
| 5 | Family profiles and rule inheritance | `contracts/profiles.py`, `profile_rules.py` | `test_profile_rules.py` | Belegt; organizational, not authorizing |
| 6 | Document action plans and provider verification | `document_action_plan.py`, `policy_fcsa_plan.py` | `test_document_action_plan.py`, `test_policy_fcsa_plan.py` | Belegt |
| 7 | TXT/PDF transformation and bundling | `document_transform.py`, `capabilities/document_transform/` | `test_document_transform.py` | Belegt; other formats blocked |
| 8 | Type packages and ZIP | `document_package.py` | `test_document_package.py` | Belegt |
| 9 | Folder state and corrective learning | `directory_observation.py` | `test_directory_observation.py` | Belegt; learning remains review candidate |
| 10 | Watch profile and scan runs | `directory_snapshot.py` | `test_directory_snapshot.py` | Belegt |
| 11 | Single action, evidence and undo | `document_action_execution.py`, `filesystem_transaction` | `test_document_action_execution.py` | Belegt |
| 12 | Extended folder cleanup plan and batch | `folder_cleanup.py` | `test_folder_cleanup.py` | Belegt |
| 13 | Observed cleanup routine | `folder_routine.py` | `test_folder_routine.py` | Belegt |
| 14 | Multi‑watch queue | `routine_queue.py` | `test_routine_queue.py` | Belegt |
| 15 | Portable scheduler Handoff | `scheduler_handoff.py` | `test_scheduler_handoff.py` | Belegt; no registration |
| 16 | Document contacts and contact register | `contacts.py`, `capabilities/contact_registry` | `test_contacts.py` | Belegt |
| 17 | appointment candidates, local calendar, ICS | `calendar_handoff.py`, `capabilities/calendar_store` | `test_calendar_handoff.py`, `test_calendar_execution.py` | Belegt |
| 18 | FindCall and call‑plugin probes | `findcall.py`, `bridges/hungrycall.py`, `bridges/ringedingeding.py` | `test_findcall.py`, `test_call_plugin_bridges.py` | Belegt; fixture/dry‑run |
| 19 | Account statements, virtual accounts, subscriptions | `finance_statements.py`, `capabilities/finance_store` | `test_finance_statements.py` | Belegt; no banking |
| 20 | Household and inventory | `household_inventory.py`, `capabilities/inventory_store` | `test_household_inventory.py` | Belegt |
| 21 | Medication plan and intake confirmation | `medication_intake.py`, `capabilities/medication_store` | `test_medication_intake.py` | Belegt; no dosage decision |
| 22 | health dossier and medical report synthesis | `health_dossier.py`, `health_report_handoff` | `test_health_dossier.py` | Belegt; extractive, no diagnosis |
| 23 | Insurance and contract cockpit | `contract_cockpit.py` | `test_contract_cockpit.py` | Belegt |
| 24 | Correspondence, templates, letter design | `correspondence.py` | `test_correspondence.py` | Belegt; output local, no sending |
| 25 | Office, media and design studio | `artifact_studio.py` | `test_artifact_studio.py` | Belegt as plan/design core; special renderer Handoff |
| 26 | Controlled mail connector | `mail_connector.py`, `capabilities/mail_gateway` | `test_mail_connector.py` | Belegt with synthetic gateway; no live mailbox |
| 27 | Calendar connectors and reminder | `calendar_connectors.py`, `calendar_connector_gateway` | `test_calendar_connectors.py` | Belegt as separate provider paths |
| 28 | Guided LLM notes | `personal_notes.py`, `bridges/llm_note.py` | `test_personal_notes.py` | Belegt |
| 29 | tax worksheet | `tax_workpaper.py`, `bridges/tax_assistant.py` | `test_tax_workpaper.py` | Belegt; no advice/transmission |
| 30 | Weather/Newspaper desktop brief | `daily_briefing.py` | `test_daily_briefing.py` | Belegt with local snapshots |
| 31 | understanding official notices | `official_notices.py` | `test_official_notices.py` | Belegt; no legal review |
| 32 | objection, response, application drafts | `administrative_drafts.py` | `test_administrative_drafts.py` | Belegt; no sending |
| 33 | benefit and funding pre-screen | `benefit_screening.py`, `trusted_authorities.py` | `test_benefit_screening.py` | Belegt; official Handoff, no claim |
| 34 | Law‑Checker and legal change monitor | `legal_change_monitor.py`, `bridges/law_checker.py` | `test_legal_change_monitor.py`, `test_law_checker_bridge.py` | Belegt; review candidates |
| 35 | Shared local API, GUI, OS boundary | `local_app.py`, `local_server.py`, `web_ui/` | `test_local_app.py`, CLI/E2E acceptance | Belegt |
| 36 | Hardening, Strands agent, demo, submission package | `resource_budget`, `trusted_authorities`, `strands_agent.py`, `competition_demo.py`, `docs/submission/` | `test_resource_budget.py`, `test_strands_agent.py`, `test_competition_demo.py` | Belegt |

## Original Feature List

The consolidated, more granular mapping of all user ideas is in [`../Feature_Analyse_FolderHome.md`](../Feature_Analyse_FolderHome.md). It covers in particular document gardener, search, topic aggregation, folder reports, versions, family rules, contacts, appointments, finances, subscriptions, insurance, household, medication, health, social law, office, design, mail, notes, taxes, briefing, FindCall, plugins and agency.

Intentionally not claimed as a local live function:

- OCR of real photo inputs and external LLM synthesis;  
- Bedrock, IMAP/SMTP, Google/Routinika, telephone, and web portal calls;  
- professionally binding medical, legal, tax, or financial decisions;  
- native Word/ODT/presentation renderers outside the verified Handoff;  
- publication and later sovereign integration.

These limits do not contradict the feature coverage: the agreed competition architecture explicitly separates the reusable local core, declared provider boundary, and external impact.

## Security and Privacy Audit

The complete baseline snapshot was scanned and sealed across all twelve relevant surfaces. After the Strands agent and its competition evidence were added, a second, time‑bounded delta audit examined all 66 files created or modified since the baseline cutoff. Together, both audits attest to the current local state.

| Evidence | Value |
|---|---|
| Baseline‑scan ID | `19d06dd4-f6e3-49cb-92f1-eb9250e05151` |
| Baseline snapshot | `codex-security-snapshot/v1:sha256:82e46a7bd206a8045f2a251f29db8276f2a86091de43e12f89f19a08125cea78` |
| Baseline scope | 357 files, 12/12 surfaces, no exclusions or deferrals |
| Delta‑scan ID | `folderhome_delta_20260822T082324Z` |
| Delta scope | 66 files, fully examined, no exclusions or deferrals |
| Finding 1 | unrestricted document work — remedied by shared resource budgets |
| Finding 2 | arbitrary official performance hosts — remedied by HTTPS/publisher binding |
| Finding 3 | unrestricted loopback threads — remedied by semaphore, timeout and overload rejection |
| Finding 4 | possible Bedrock leakage of local search results via pure network gate — remedied by separate data release |
| Baseline fix report | `artifacts/fix_report.md` in sealed baseline‑scan directory |
| Delta evidence | Red test, attack path, fix report, file receipts and canonical scan contract in delta‑scan directory |

The current security policy is in [`../SECURITY.md`](../SECURITY.md). The agent adds hard limits for Prompt, Response, Tool result, Turns, Tool calls and Output tokens. The demo contains exclusively synthetic data; `network_used=false` and `side_effects=[]` are emitted machine‑readable. For Bedrock, network access and sharing of sensitive local data are denied independently as long as the respective approval is missing.

## Reproducible Strands Evidence

Executed:

```powershell
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir examples\competition\evidence `
  --approve-output-write --json
```


Result: `status=passed`, `strands-agents 1.53.0`, two sequential tool events, no network, no side‑effects and no approval to share sensitive local data. The subsequent run against the same folder was stopped at the Never‑overwrite gate with exit code 2; all hashes remained unchanged.

| Artifact | SHA‑256 |
|---|---|
| `01-document-search.json` | `7fdd64a9153b36a97db291162686b1217902e3ef914670f83be6a5e1b597921e` |
| `02-theme-dossier.json` | `018b4fa9278e0546cd7930e76bb39aeb080b19b52dfbf9ed3e88ae7dbad1426f` |
| `DEMO.md` | `17aeb3fca698adffae895f4488713c2b8dd7fa13428924a49b5013ee42344b9e` |
| `EVIDENCE.json` | `78d26c5e39e4ea97debbf12a0ce213cb3dadb4143eeac50776bd16e9385af213` |

## Quality Evidence

| Check | Result |
|---|---|
| Full test suite | 333/333 passed in 464.27 seconds |
| Ruff | `All checks passed!` |
| Compileall | Exitcode 0 |
| Plugin manifests | 8/8 valid |
| FolderHome skills | 12/12 valid with `quick_validate.py` |
| Workflow router | 31 workflows, `--check` current |
| Document metadata | `CLAUDE.md`, `START.md`, `STATE.md` valid |
| Python dependencies | `pip check`: no broken requirements |
| Vulnerability alignment | `pip-audit --skip-editable`: no known vulnerabilities after tool update |
| Wheel | `folderhome-0.1.0-py3-none-any.whl`, 359.969 Bytes, SHA‑256 `4a6099b4744738eeb3d85c3c214633bead4ec98573f8e58b24e0a1fce82983ee` |
| Isolated wheel acceptance | Reinstalled in a clean environment; demo passed and all four reference hashes identical |

## GUI and Accessibility

The Phase‑35 acceptance remains valid for the unchanged local UI:

- Desktop `1440 × 1100` and mobile `390 × 844` without horizontal overflow;  
- Search with a synthetic hit, profile display and focus return;  
- `aria-busy=false`, no console or HTTP errors, no external requests;  
- no external assets and no document‑modifying GUI function;  
- Design set contrast ratio 4.5:1 automatically tested.

The Strands agent was deliberately not exposed as an additional GUI action. Its CLI/Application interface is therefore not an untested new browser path.

## Competition Package and External Gates

Locally prepared are an English description, test guide, architecture diagram, a video script planned to be under five minutes, and a submission checklist at [`submission/`](./submission/).

Executable only by a human and only after explicit approval:

1. Confirm eligibility and AWS Builder ID;  
2. Record a real video, review it, and upload publicly;  
3. Decide on the optional live demo/Bedrock path;  
4. Re‑check the official rules shortly before the deadline;  
5. Verify Devpost fields and submit finally.

The public repository is located at <https://github.com/ellmos-ai/FolderHome>. A script is not a video and a draft is not a submission.

## Final Judgment

The agreed local competition scope is technically complete and reproducibly demonstrated. All 36 phases, 333 tests, the real Strands demo, the installable wheel, both security audits, and the local submission materials are finished. Only the aforementioned human external‑impact and publication gates remain open.

---
