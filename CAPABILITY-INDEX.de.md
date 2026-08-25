# CAPABILITY-INDEX.md — Ein Index aller Endpunkte

[English](./CAPABILITY-INDEX.md) | **Deutsch**

> **Zweck:** Eine Stelle, die sagt, wofuer ein Endpunkt da ist, was er
> braucht und was er bewirken kann.
> **Quelle:** `folderhome.application.capability_index` — derselbe Index, den
> der Master-Agent als kompakten Prompt-Auszug erhaelt.
> **Auto-generiert:** Der Block zwischen den Markern wird von
> `_tools/capability-index` geschrieben. Text ausserhalb bleibt unberuehrt.

`Umsetzung` sagt, ob im Code ein typisierter Adapter existiert, nicht ob
die eigene Installation ihn konfiguriert hat. Ein Endpunkt wird erst zur
Laufzeit `connected`, wenn seine Ressourcen deklariert sind.

---

## Endpunkte (auto-generiert)

<!-- @auto-generated:capability-index -->
<!-- last-updated: 2026-08-25 01:03 UTC -->
<!-- tool: _tools/capability-index -->
<!-- count: 33 endpoints -->

| Endpunkt | Fachrolle | Zweck | Eingaben | Wirkung | Umsetzung |
| --- | --- | --- | --- | --- | --- |
| `calendar-connectors` | `communication_expert` | Einen providerneutralen externen Kalender-Connector planen, ohne ihn aufzurufen. | — | `external_effect` | `no_typed_adapter` |
| `calendar-handoff` | `communication_expert` | Dokumenttermine im lokalen Kalender festhalten und auf Wunsch als ICS exportieren. | `allow_sensitive_local_read`, `area`, `configuration_resource_id`, `planned_at`, `recursive`, `source_resource_id`, `state_resource_id`, `export_basename?`, `export_resource_id?` | `local_state_and_file_write` | `typed_adapter_available` |
| `contact-register` | `communication_expert` | Gelabelte Kontaktdaten aus Dokumenten in das lokale Kontaktregister übernehmen. | `allow_sensitive_local_read`, `area`, `recursive`, `source_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `correspondence-studio` | `communication_expert` | Einen lokalen Brief aus geprüfter Vorlage und Gestaltung erzeugen. | `designs_resource_id`, `output_basename`, `output_resource_id`, `request_resource_id`, `templates_resource_id` | `local_file_write` | `typed_adapter_available` |
| `findcall` | `communication_expert` | Eine begrenzte Anbieteranfrage als strikt lokale Simulation vorbereiten. | `action`, `area`, `candidates`, `kind`, `location`, `max_distance_km`, `max_price_eur`, `planned_at`, `service`, `windows` | `local_simulation` | `typed_adapter_available` |
| `mail-connector` | `communication_expert` | Ein vorbereitetes Schreiben als Entwurf im eigenen Postfach ablegen; nie senden. | `account_resource_id`, `designs_resource_id`, `planned_at`, `request_resource_id`, `templates_resource_id` | `external_effect` | `typed_adapter_available` |
| `artifact-studio` | `creative_knowledge_expert` | Eine lokale Präsentation, Tabelle, Karte oder Mediendatei planen und erzeugen. | `business_card`, `colors`, `design_set_id`, `display_name`, `fonts`, `output_basename`, `output_resource_id`, `purpose` | `local_file_write` | `typed_adapter_available` |
| `personal-notes` | `creative_knowledge_expert` | Eine menschlich geschriebene Notiz als neue Revision im gepinnten Notizspeicher ablegen. | `action`, `area`, `notebook_id`, `title`, `expected_revision?`, `human_content?`, `note_id?`, `references?`, `revert_to_revision?` | `local_file_write` | `typed_adapter_available` |
| `directory-observation` | `document_expert` | Einen beobachteten Ordner gegen seinen Prüfpunkt vergleichen, ohne Dokumenttext zu lesen. | `allow_sensitive_local_read`, `area`, `captured_at`, `interval_minutes`, `recursive`, `source_resource_id`, `state_resource_id`, `watch_id` | `local_file_write` | `typed_adapter_available` |
| `document-action-execution` | `document_expert` | Genau eine geprüfte Umbenennung oder Verschiebung für ein Dokument reversibel ausführen. | `allow_sensitive_local_read`, `area`, `as_of`, `source_resource_id`, `state_resource_id`, `target_resource_id` | `local_file_write` | `typed_adapter_available` |
| `document-action-plan` | `document_expert` | Aus Profilregeln einen nachvollziehbaren Dateiaktionsplan ableiten, ohne etwas zu ändern. | `allow_sensitive_local_read`, `area`, `as_of`, `output_name`, `output_resource_id`, `source_resource_id`, `target_resource_id` | `local_file_write` | `typed_adapter_available` |
| `document-bundle` | `document_expert` | Einen gewählten Ordner zu einer neuen TXT- oder PDF-Datei bündeln, Originale bleiben. | `format`, `output_name`, `output_resource_id`, `recursive`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `document-library` | `document_expert` | Den lokalen Dokumentindex durchsuchen und als Themendossier zusammenfassen. | — | `none` | `direct_read_only_tool` |
| `document-package` | `document_expert` | Einen verschachtelten Ordner nach Dateityp als ZIP mit Prüfmanifest gruppieren. | `allow_sensitive_local_read`, `output_name`, `output_resource_id`, `recursive`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `fcsa-dry-run` | `document_expert` | Mit der gepinnten FCSA-Komponente einen Sortierplan erstellen, ohne etwas zu verschieben. | `allow_sensitive_local_read`, `config_resource_id`, `scan_resource_ids`, `target_resource_ids` | `local_file_write` | `typed_adapter_available` |
| `folder-cleanup` | `document_expert` | Einen ganzen Ordner planen und nur die bewusst freigegebene Teilmenge ausführen. | `allow_sensitive_local_read`, `area`, `as_of`, `recursive`, `source_resource_id`, `state_resource_id`, `target_resource_id` | `local_file_write` | `typed_adapter_available` |
| `folder-routine` | `document_expert` | Die fälligen Änderungen eines beobachteten Ordners gegen den letzten Prüfpunkt ausführen. | `allow_sensitive_local_read`, `area`, `as_of`, `captured_at`, `completed_at`, `interval_minutes`, `mode`, `recursive`, `source_resource_id`, `state_resource_id`, `target_resource_id`, `watch_id` | `local_file_write` | `typed_adapter_available` |
| `routine-queue` | `document_expert` | Alle aktivierten Beobachtungen nur lesend auswerten und übergreifende Konflikte zeigen. | `allow_sensitive_local_read`, `as_of`, `captured_at`, `items`, `output_name`, `output_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `contract-cockpit` | `finance_contract_expert` | Eine Vertrags- oder Versicherungsfrage als belegverknüpfte Übersicht beantworten. | `account_refs`, `allow_sensitive_local_read`, `archive_older_versions`, `area`, `as_of`, `calendar_terms`, `counterparty_terms`, `coverage_start`, `display_name`, `document_query`, `object_ref`, `output_basename`, `output_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `finance-import` | `finance_contract_expert` | Bereitgestellte Kontoauszüge centgenau in den lokalen Finanzspeicher übernehmen. | `allow_sensitive_local_read`, `recursive`, `source_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `tax-workpaper` | `finance_contract_expert` | Bestätigte Belege in eine private, nicht amtliche Steuerarbeitsmappe überführen. | `output_name`, `output_resource_id`, `state_resource_id`, `tax_year` | `local_file_write` | `typed_adapter_available` |
| `health-dossier` | `health_expert` | Ein extraktives, belegorientiertes Gesundheitsdossier aus lokalen Dokumenten bauen. | `as_of`, `gap_threshold_days`, `output_basename`, `output_resource_id`, `recursive`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `medication-intake` | `health_expert` | Einen bereitgestellten Medikationsplan übernehmen und eine geplante Einnahme bestätigen. | `action`, `confirmed_at`, `scheduled_date`, `medication_name?`, `schedule_id?`, `scheduled_time?` | `local_file_write` | `typed_adapter_available` |
| `daily-briefing` | `household_expert` | Einen bereitgestellten Wetter- und Nachrichtenstand als lokales HTML-Briefing bündeln. | `allow_sensitive_local_read`, `as_of`, `briefing_date`, `categories`, `desktop_name`, `desktop_resource_id`, `max_items_per_category`, `max_news_age_minutes`, `max_weather_age_minutes`, `news_resource_id`, `output_name`, `output_resource_id`, `timezone`, `title`, `weather_resource_id` | `local_file_write` | `typed_adapter_available` |
| `inventory-import` | `household_expert` | Dokumentierte Haushaltsbeobachtungen in den lokalen Append-only-Bestand aufnehmen. | `allow_sensitive_local_read`, `recursive`, `source_resource_id`, `state_resource_id` | `local_file_write` | `typed_adapter_available` |
| `administrative-drafts` | `rights_benefits_expert` | Ein ungesendetes Behördenschreiben aus einem erfassten Bescheid vorbereiten. | `as_of`, `designs_resource_id`, `notice_resource_id`, `output_basename`, `output_resource_id`, `received_on`, `request_resource_id`, `templates_resource_id` | `local_file_write` | `typed_adapter_available` |
| `benefit-screening` | `rights_benefits_expert` | Ein lokales Leistungsprofil gegen datierte Kriterien abgleichen, nur als Orientierung. | `as_of`, `catalog_resource_id`, `max_source_age_days`, `output_basename`, `output_resource_id`, `profile_resource_id` | `local_file_write` | `typed_adapter_available` |
| `legal-change-monitor` | `rights_benefits_expert` | Zwei datierte Rechtsstände vergleichen und Themen als Prüfkandidaten markieren. | `after_resource_id`, `allow_test_fixture`, `as_of`, `before_resource_id`, `interests_resource_id`, `max_source_age_days`, `output_basename`, `output_resource_id` | `local_file_write` | `typed_adapter_available` |
| `official-notice-understanding` | `rights_benefits_expert` | Einen Sozialrechtsbescheid nachprüfbar aus seinem eigenen gelabelten Inhalt erklären. | `as_of`, `output_basename`, `output_resource_id`, `received_on`, `source_resource_id` | `local_file_write` | `typed_adapter_available` |
| `local-app` | `system_expert` | Die lokale FolderHome-Anwendungsoberfläche erklären und planen. | — | `none` | `planning_only` |
| `master-agent` | `system_expert` | Den Master-Agenten, seine Fachrollen und seinen Endpunktkatalog erklären und planen. | — | `none` | `planning_only` |
| `scheduler-handoff` | `system_expert` | Ein portables Scheduler-Artefakt vorbereiten, ohne eine Systemaufgabe zu registrieren. | — | `external_effect` | `no_typed_adapter` |
| `strands-agent` | `system_expert` | Einen begrenzten Lauf der echten Strands-Agentenschleife mit synthetischen Daten planen. | — | `none` | `planning_only` |

<!-- @end:capability-index -->
---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
