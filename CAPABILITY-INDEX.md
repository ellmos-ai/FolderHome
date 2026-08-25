# CAPABILITY-INDEX.md — One Index of Every Endpoint

**English** | [Deutsch](./CAPABILITY-INDEX.de.md)

> **Purpose:** One place that says what each endpoint is for, what it needs,
> and what it can affect.
> **Source:** `folderhome.application.capability_index` — the same index the
> master agent receives as a compact prompt excerpt.
> **Auto-generated:** The block between the markers is written by
> `_tools/capability-index`. Text outside the markers stays untouched.

`Implementation` says whether a typed adapter exists in the code, not
whether your installation has it configured. An endpoint only becomes
`connected` at runtime once its resources are declared.

---

## Endpoints (auto-generated)

<!-- @auto-generated:capability-index -->
<!-- last-updated: 2026-08-25 01:03 UTC -->
<!-- tool: _tools/capability-index -->
<!-- count: 33 endpoints -->

| Endpoint | Expert | Purpose | Inputs | Effect | Implementation |
| --- | --- | --- | --- | --- | --- |
| `calendar-connectors` | `communication_expert` | Plan a provider-neutral external calendar connector without invoking one. | — | `external_effect` | `no_typed_adapter` |
| `calendar-handoff` | `communication_expert` | Record document appointments in the local calendar and optionally export them as ICS. | `allow_sensitive_local_read`, `area`, `configuration_resource_id`, `planned_at`, `recursive`, `source_resource_id`, `state_resource_id`, `export_basename?`, `export_resource_id?` | `local_state_and_file_write` | `typed_adapter_available` |
| `contact-register` | `communication_expert` | Extract labeled contact data from documents into the local contact register. | `allow_sensitive_local_read`, `area`, `recursive`, `source_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `correspondence-studio` | `communication_expert` | Render one local letter from a controlled template and design. | `designs_resource_id`, `output_basename`, `output_resource_id`, `request_resource_id`, `templates_resource_id` | `local_file_write` | `typed_adapter_available` |
| `findcall` | `communication_expert` | Prepare a bounded provider inquiry as a strictly local simulation. | `action`, `area`, `candidates`, `kind`, `location`, `max_distance_km`, `max_price_eur`, `planned_at`, `service`, `windows` | `local_simulation` | `typed_adapter_available` |
| `mail-connector` | `communication_expert` | Place one prepared letter as a draft in the user's own mailbox; never send. | `account_resource_id`, `designs_resource_id`, `planned_at`, `request_resource_id`, `templates_resource_id` | `external_effect` | `typed_adapter_available` |
| `artifact-studio` | `creative_knowledge_expert` | Plan and render a local presentation, table, card or media artifact. | `business_card`, `colors`, `design_set_id`, `display_name`, `fonts`, `output_basename`, `output_resource_id`, `purpose` | `local_file_write` | `typed_adapter_available` |
| `personal-notes` | `creative_knowledge_expert` | Store a human-written note as a new revision in the pinned local note store. | `action`, `area`, `notebook_id`, `title`, `expected_revision?`, `human_content?`, `note_id?`, `references?`, `revert_to_revision?` | `local_file_write` | `typed_adapter_available` |
| `directory-observation` | `document_expert` | Compare an observed folder against its checkpoint without reading document text. | `allow_sensitive_local_read`, `area`, `captured_at`, `interval_minutes`, `recursive`, `source_resource_id`, `state_resource_id`, `watch_id` | `local_file_write` | `typed_adapter_available` |
| `document-action-execution` | `document_expert` | Execute one verified rename or move for exactly one document, reversibly. | `allow_sensitive_local_read`, `area`, `as_of`, `source_resource_id`, `state_resource_id`, `target_resource_id` | `local_file_write` | `typed_adapter_available` |
| `document-action-plan` | `document_expert` | Derive a traceable file action plan from profile rules without changing anything. | `allow_sensitive_local_read`, `area`, `as_of`, `output_name`, `output_resource_id`, `source_resource_id`, `target_resource_id` | `local_file_write` | `typed_adapter_available` |
| `document-bundle` | `document_expert` | Merge a selected folder into one new TXT or PDF, leaving the originals untouched. | `format`, `output_name`, `output_resource_id`, `recursive`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `document-library` | `document_expert` | Search the local document index and summarize it as a topic dossier. | — | `none` | `direct_read_only_tool` |
| `document-package` | `document_expert` | Group a nested folder by file type into one ZIP with a verification manifest. | `allow_sensitive_local_read`, `output_name`, `output_resource_id`, `recursive`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `fcsa-dry-run` | `document_expert` | Create a sorting plan with the pinned FCSA component without moving anything. | `allow_sensitive_local_read`, `config_resource_id`, `scan_resource_ids`, `target_resource_ids` | `local_file_write` | `typed_adapter_available` |
| `folder-cleanup` | `document_expert` | Plan a whole folder and execute only the deliberately approved subset. | `allow_sensitive_local_read`, `area`, `as_of`, `recursive`, `source_resource_id`, `state_resource_id`, `target_resource_id` | `local_file_write` | `typed_adapter_available` |
| `folder-routine` | `document_expert` | Run the due changes of one observed folder against its last checkpoint. | `allow_sensitive_local_read`, `area`, `as_of`, `captured_at`, `completed_at`, `interval_minutes`, `mode`, `recursive`, `source_resource_id`, `state_resource_id`, `target_resource_id`, `watch_id` | `local_file_write` | `typed_adapter_available` |
| `routine-queue` | `document_expert` | Evaluate all activated watches read-only and surface cross-watch conflicts. | `allow_sensitive_local_read`, `as_of`, `captured_at`, `items`, `output_name`, `output_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `contract-cockpit` | `finance_contract_expert` | Answer a contract or insurance question as an evidence-linked read-only overview. | `account_refs`, `allow_sensitive_local_read`, `archive_older_versions`, `area`, `as_of`, `calendar_terms`, `counterparty_terms`, `coverage_start`, `display_name`, `document_query`, `object_ref`, `output_basename`, `output_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `finance-import` | `finance_contract_expert` | Import provided bank statements cent-accurately into the local finance store. | `allow_sensitive_local_read`, `recursive`, `source_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `tax-workpaper` | `finance_contract_expert` | Turn confirmed receipts into a private, non-official tax workpaper. | `output_name`, `output_resource_id`, `state_resource_id`, `tax_year` | `local_file_write` | `typed_adapter_available` |
| `health-dossier` | `health_expert` | Build an extractive, evidence-bound health dossier from selected local documents. | `as_of`, `gap_threshold_days`, `output_basename`, `output_resource_id`, `recursive`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `medication-intake` | `health_expert` | Adopt a provided medication plan and confirm one scheduled dose. | `action`, `confirmed_at`, `scheduled_date`, `medication_name?`, `schedule_id?`, `scheduled_time?` | `local_file_write` | `typed_adapter_available` |
| `daily-briefing` | `household_expert` | Bundle a provided weather and news snapshot into one local HTML brief. | `allow_sensitive_local_read`, `as_of`, `briefing_date`, `categories`, `desktop_name`, `desktop_resource_id`, `max_items_per_category`, `max_news_age_minutes`, `max_weather_age_minutes`, `news_resource_id`, `output_name`, `output_resource_id`, `timezone`, `title`, `weather_resource_id` | `local_file_write` | `typed_adapter_available` |
| `inventory-import` | `household_expert` | Add documented household observations to the local append-only inventory. | `allow_sensitive_local_read`, `recursive`, `source_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `administrative-drafts` | `rights_benefits_expert` | Prepare an unsent administrative letter from a recorded notice. | `as_of`, `designs_resource_id`, `notice_resource_id`, `output_basename`, `output_resource_id`, `received_on`, `request_resource_id`, `templates_resource_id` | `local_file_write` | `typed_adapter_available` |
| `benefit-screening` | `rights_benefits_expert` | Match a local benefit profile against dated criteria as guidance only. | `as_of`, `catalog_resource_id`, `max_source_age_days`, `output_basename`, `output_resource_id`, `profile_resource_id` | `local_file_write` | `typed_adapter_available` |
| `legal-change-monitor` | `rights_benefits_expert` | Compare two dated legal snapshots and flag topics as review candidates. | `after_resource_id`, `allow_test_fixture`, `as_of`, `before_resource_id`, `interests_resource_id`, `max_source_age_days`, `output_basename`, `output_resource_id` | `local_file_write` | `typed_adapter_available` |
| `official-notice-understanding` | `rights_benefits_expert` | Explain a social-law notice from its own labeled content, verifiably. | `as_of`, `output_basename`, `output_resource_id`, `received_on`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `local-app` | `system_expert` | Explain and plan the local FolderHome application surface. | — | `none` | `planning_only` |
| `master-agent` | `system_expert` | Explain and plan the master agent, its experts and its endpoint catalog. | — | `none` | `planning_only` |
| `scheduler-handoff` | `system_expert` | Prepare a portable scheduler artifact without registering any system task. | — | `external_effect` | `no_typed_adapter` |
| `strands-agent` | `system_expert` | Plan a bounded run of the real Strands agent loop with synthetic data. | — | `none` | `planning_only` |

<!-- @end:capability-index -->
---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
