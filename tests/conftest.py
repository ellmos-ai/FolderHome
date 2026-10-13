"""Test-level selection for cases that exercise pinned provider checkouts."""

from pathlib import Path

import pytest

from folderhome.provider_locations import default_provider_root

REPOSITORY_ROOT = Path(__file__).parents[1]
TESTS_ROOT = Path(__file__).parent

# This is deliberately keyed by individual test functions, not files. The list
# records the source prerequisites observed in the isolated no-provider
# baseline; mixed test modules continue to run their provider-free cases.
_PROVIDER_CASES: dict[str, tuple[str, ...]] = {
    "test_calendar_event_editor.py::"
    "test_editor_prepares_without_network_then_us"
    "es_normal_exact_confirmation": ('KnowledgeDigest',),
    "test_calendar_event_editor.py::"
    "test_editor_rejects_invalid_or_foreign_refer"
    "ence_before_provider_io": ('KnowledgeDigest',),
    "test_calendar_event_editor.py::"
    "test_editor_does_not_read_credentials_to_pre"
    "pare_and_survives_conversation_reset": ('KnowledgeDigest',),
    "test_calendar_event_editor.py::"
    "test_editor_endpoint_keeps_session_and_origi"
    "n_gate": ('KnowledgeDigest',),
    "test_calendar_event_editor.py::"
    "test_guided_edit_cannot_bypass_rights_or_ver"
    "sion_gate": ('KnowledgeDigest',),
    "test_calendar_event_editor.py::"
    "test_guided_editor_supports_all_day_dates_lo"
    "cation_and_popups": ('KnowledgeDigest',),
    "test_scheduler_consumer.py::"
    "test_consumer_requires_separate_strict_start"
    "_gate": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_consumer_never_initializes_an_unregiste"
    "red_store": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_constructing_consumer_does_not_run_or_c"
    "laim_a_job": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_provider_loop_obeys_stop_signal_before_"
    "next_tick": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_real_provider_tick_runs_the_read_only_c"
    "hild_and_accepts_attention": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_consumer.py::"
    "test_consumer_does_not_claim_other_jobs_in_t"
    "he_same_store": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_consumer.py::"
    "test_consumer_revalidates_approved_inputs_be"
    "fore_each_claim": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_changed_payload_after_claim_cannot_laun"
    "ch_an_unapproved_child": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_child_timeout_is_not_reported_as_a_succ"
    "essful_queue_run": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_invalid_child_report_is_not_accepted_ev"
    "en_with_success_exit": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_old_valid_child_envelope_cannot_satisfy"
    "_a_later_run": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_consumer.py::"
    "test_child_uses_this_installation_even_when_"
    "working_directory_shadows_it": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_consumer.py::"
    "test_child_summary_count_types_are_not_coerc"
    "ed_into_valid_evidence": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_child_rejects_changed_configuration_bef"
    "ore_source_or_state_work": ('ellmos-scheduler',),
    "test_scheduler_consumer.py::"
    "test_existing_provider_serve_loop_runs_bound"
    "_consumer_and_stops_in_the_test": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_consumer.py::"
    "test_missing_invocation_receipt_does_not_con"
    "firm_a_child_run": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_consumer.py::"
    "test_failed_observation_persistence_is_repor"
    "ted_separately_from_completed_run": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_control.py::"
    "test_preview_and_status_do_not_start_a_worke"
    "r_or_modify_registration": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_start_requires_its_own_strict_process_g"
    "ate": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_exact_start_then_stop_owns_one_worker_a"
    "nd_never_replays_old_approval": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_changed_or_unregistered_start_is_reject"
    "ed_without_a_worker": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_stop_rejects_another_worker_and_close_p"
    "revents_future_start": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_concurrent_confirmations_create_only_on"
    "e_owned_worker": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_stop_reports_draining_until_the_real_wo"
    "rker_has_returned": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_failed_worker_is_not_reported_as_a_succ"
    "essful_stop_or_exposed_as_a_path": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_saved_configuration_is_rechecked_before"
    "_start": ('ellmos-scheduler',),
    "test_scheduler_control.py::"
    "test_preview_rejects_plan_without_active_pro"
    "file_binding": ('ellmos-scheduler',),
    "test_scheduler_control_api.py::"
    "test_api_preview_start_status_stop_and_serve"
    "r_close_own_real_worker": ('ellmos-scheduler',),
    "test_scheduler_control_api.py::"
    "test_api_scheduler_uses_existing_token_and_o"
    "rigin_gates": ('ellmos-scheduler',),
    "test_scheduler_control_api.py::"
    "test_api_scheduler_rejects_untrusted_shape_w"
    "ithout_effects": ('ellmos-scheduler',),
    "test_scheduler_control_api.py::"
    "test_api_scheduler_configuration_errors_are_"
    "path_free": ('ellmos-scheduler',),
    "test_scheduler_control_api.py::"
    "test_real_setup_launch_connects_saved_reques"
    "t_and_separate_start_gate": ('ellmos-scheduler',),
    "test_app_calendar_configuration.py::"
    "test_setup_calendar_reaches_real_application"
    "_resource_catalog": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_app_calendar_configuration.py::"
    "test_setup_to_app_executes_real_local_calend"
    "ar_only_after_approval": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_cli.py::"
    "test_documents_execute_and_undo_cli_roundtri"
    "p": ('doc-services', 'KnowledgeDigest'),
    "test_cli.py::"
    "test_folders_cleanup_plan_and_selective_exec"
    "ute_cli": ('doc-services',),
    "test_cli.py::"
    "test_folders_routine_plan_and_execute_cli_ro"
    "undtrip": ('doc-services',),
    "test_cli.py::"
    "test_folders_routine_queue_cli_is_read_only_"
    "for_multiple_watches": ('doc-services',),
    "test_cli.py::"
    "test_scheduler_plan_and_headless_run_cli_wit"
    "hout_registration": ('doc-services',),
    "test_cli.py::"
    "test_findcall_cli_probes_both_pinned_plugins"
    "_without_calls": ('hungrycall', 'ringedingeding'),
    "test_cli.py::"
    "test_app_plan_reports_the_model_id_and_locat"
    "ion_of_hosted_providers": ('KnowledgeDigest', 'llm-note'),
    "test_google_calendar_mutation_workflow.py::"
    "test_normal_factory_api_delivers_and_retains"
    "_confirmed_mutation": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_google_calendar_mutation_workflow.py::"
    "test_normal_api_revocation_preserves_unknown"
    "_and_partial_evidence": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_google_calendar_mutation_workflow.py::"
    "test_normal_cli_session_exposes_mutation_rec"
    "eipts_and_followup_versions": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_google_calendar_setup.py::"
    "test_saved_google_setup_reaches_real_app_wit"
    "h_separate_execution_gate": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_google_calendar_workflow.py::"
    "test_normal_app_factory_wires_google_resourc"
    "es_with_separate_gate": ('KnowledgeDigest', 'llm-note', 'doc-services'),
    "test_law_checker_bridge.py::"
    "test_bridge_qualifies_registry_without_claim"
    "ing_legal_api": ('law-checker',),
    "test_law_checker_bridge.py::"
    "test_bridge_rejects_wrong_revision_and_missi"
    "ng_registry_key": ('law-checker',),
    "test_local_app.py::"
    "test_executor_catalog_exposes_connected_read"
    "_only_and_missing_coverage": ('llm-note',),
    "test_personal_notes.py::"
    "test_synthetic_guide_separates_questions_fro"
    "m_human_content": ('llm-note',),
    "test_personal_notes.py::"
    "test_network_guide_is_blocked_before_invocat"
    "ion": ('llm-note',),
    "test_personal_notes.py::"
    "test_apply_uses_llm_note_append_only_and_rep"
    "lay_is_rejected": ('llm-note',),
    "test_personal_notes.py::"
    "test_edit_and_revert_create_new_versions_wit"
    "hout_overwrite": ('llm-note',),
    "test_personal_notes.py::"
    "test_stale_revision_and_wrong_approval_block"
    "_before_write": ('llm-note',),
    "test_personal_notes.py::"
    "test_list_current_is_profile_not_security_bo"
    "undary": ('llm-note',),
    "test_pinned_provider_imports.py::"
    "test_pinned_ellmos_scheduler_src_import_does"
    "_not_create_a_store": ('ellmos-scheduler',),
    "test_recipe_runs.py::"
    "test_real_note_create_then_revision_bound_ed"
    "it_uses_new_approval": ('llm-note',),
    "test_scheduler_registration_execution.py::"
    "test_registration_requires_strict_write_gate"
    "_before_creating_any_state": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_wrong_confirmation_or_changed_configura"
    "tion_cannot_open_provider": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_real_provider_registration_is_exact_and"
    "_does_not_start_a_consumer": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_repeat_confirmation_reads_existing_job_"
    "instead_of_inserting": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_changed_first_due_is_not_accepted_as_ex"
    "isting_approved_job": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_legitimate_due_progress_requires_matchi"
    "ng_provider_history": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_abandoned_paused_run_retains_its_provid"
    "er_retry_time": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_older_abandoned_slot_can_become_due_aft"
    "er_a_newer_completed_run": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_transient_attempt_path_alias_stays_unce"
    "rtain_without_opening_store": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_unknown_existing_database_is_not_initia"
    "lized_or_modified": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_foreign_job_definition_is_never_overwri"
    "tten": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_timeout_after_committed_insert_is_recon"
    "ciled_without_retry": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_failed_insert_without_job_stays_uncerta"
    "in_and_is_not_blindly_retried": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_distinct_approved_jobs_can_share_an_own"
    "ed_store": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_concurrent_confirmation_creates_at_most"
    "_one_job": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_orphaned_sqlite_files_are_not_adopted_b"
    "y_new_database": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_failed_attempt_persistence_prevents_dat"
    "abase_creation": ('ellmos-scheduler',),
    "test_scheduler_registration_execution.py::"
    "test_result_persistence_failure_does_not_hid"
    "e_possible_effects": ('ellmos-scheduler',),
    "test_scheduler_registration_plan.py::"
    "test_registration_plan_is_deterministic_and_"
    "has_no_store_or_state_effects": ('ellmos-scheduler',),
    "test_scheduler_registration_plan.py::"
    "test_registration_binds_optional_resource_au"
    "thority_file": ('ellmos-scheduler',),
    "test_scheduler_registration_plan.py::"
    "test_registration_confirmation_rejects_confi"
    "guration_drift": ('ellmos-scheduler',),
    "test_scheduler_registration_plan.py::"
    "test_changed_watched_documents_do_not_invali"
    "date_configuration_approval": ('ellmos-scheduler',),
    "test_scheduler_registration_plan.py::"
    "test_retargeted_directory_requires_new_regis"
    "tration_approval": ('ellmos-scheduler',),
    "test_scheduler_registration_plan.py::"
    "test_registration_confirmation_reconstructs_"
    "all_approval_fields": ('ellmos-scheduler',),
    "test_scheduler_setup.py::"
    "test_setup_launch_reaches_actual_scheduler_a"
    "dapter_with_separate_write_gate": (
        "ellmos-scheduler",
        "KnowledgeDigest",
        "llm-note",
        "doc-services",
    ),
    "test_scheduler_workflow.py::"
    "test_scheduler_preview_is_path_free_and_crea"
    "tes_no_scheduler_state": ('ellmos-scheduler',),
    "test_scheduler_workflow.py::"
    "test_confirmed_scheduler_adapter_registers_r"
    "eal_job_without_starting_consumer": ('ellmos-scheduler',),
    "test_scheduler_workflow.py::"
    "test_scheduler_adapter_requires_strict_start"
    "up_write_gate": ('ellmos-scheduler',),
    "test_scheduler_workflow.py::"
    "test_scheduler_adapter_revalidates_before_th"
    "e_confirmed_insert": ('ellmos-scheduler',),
    "test_scheduler_workflow.py::"
    "test_scheduler_reloads_and_binds_persisted_r"
    "esource_authority": ('ellmos-scheduler', 'doc-services'),
    "test_scheduler_workflow.py::"
    "test_normal_app_factory_connects_scheduler_r"
    "esources_with_separate_gate": (
        "ellmos-scheduler",
        "KnowledgeDigest",
        "llm-note",
        "doc-services",
    ),
    "test_scheduler_workflow.py::"
    "test_scheduler_unknown_effect_survives_the_a"
    "pplication_boundary": ('ellmos-scheduler',),
    "test_setup_app.py::"
    "test_saved_launch_config_drives_the_app_plan"
    "_command": ('KnowledgeDigest', 'llm-note'),
    "test_tax_workpaper.py::"
    "test_category_candidate_is_not_a_confirmed_t"
    "ax_classification": ('steuer-assistent',),
    "test_tax_workpaper.py::"
    "test_confirmed_receipt_is_evidence_bound_and"
    "_plan_is_read_only": ('steuer-assistent',),
    "test_tax_workpaper.py::"
    "test_receipt_apply_is_exact_idempotent_and_u"
    "ses_provider": ('steuer-assistent',),
    "test_tax_workpaper.py::"
    "test_changed_document_or_provider_state_bloc"
    "ks_before_write": ('steuer-assistent',),
    "test_tax_workpaper.py::"
    "test_private_export_has_separate_output_gate"
    "_and_no_portal": ('steuer-assistent',),
    "test_workflow_execution.py::"
    "test_executor_catalog_covers_every_workflow_"
    "and_keeps_gaps_visible": ('llm-note',),
    "test_workflow_execution.py::"
    "test_findcall_fixture_adapter_runs_only_the_"
    "existing_local_simulation": ('llm-note',),
    "test_workflow_execution.py::"
    "test_findcall_fixture_adapter_rejects_paths_"
    "and_live_authority": ('llm-note',),
    "test_workflow_execution.py::"
    "test_gateway_rejects_unconnected_workflow_be"
    "fore_any_state": ('llm-note',),
    "test_workflow_execution.py::"
    "test_medication_intake_adapter_reuses_existi"
    "ng_confirmation_workflow_once": ('llm-note',),
    "test_workflow_execution.py::"
    "test_medication_intake_adapter_rejects_cross"
    "_profile_and_unknown_fields": ('llm-note',),
}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_provider(*provider_ids): test case exercises the named pinned local source",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        relative_file = Path(str(item.path)).relative_to(TESTS_ROOT).as_posix()
        test_name = getattr(item, "originalname", None) or item.name.split("[", 1)[0]
        provider_ids = _PROVIDER_CASES.get(f"{relative_file}::{test_name}")
        if provider_ids:
            item.add_marker(pytest.mark.requires_provider(*provider_ids))


def pytest_collection_finish(session: pytest.Session) -> None:
    """Catch stale provider registry keys on complete collections only."""

    config = session.config
    selection_options = (
        "keyword",
        "markexpr",
        "ignore",
        "ignore_glob",
        "deselect",
        "lf",
        "ff",
        "failedfirst",
        "newfirst",
        "stepwise",
    )
    if any(config.getoption(option, default=None) for option in selection_options):
        return

    requested_paths = [Path(value).resolve() for value in config.args]
    if any(path not in {REPOSITORY_ROOT, TESTS_ROOT} for path in requested_paths):
        return

    collected_cases = {
        f"{Path(str(item.path)).relative_to(TESTS_ROOT).as_posix()}::"
        f"{getattr(item, 'originalname', None) or item.name.split('[', 1)[0]}"
        for item in session.items
    }
    stale = sorted(set(_PROVIDER_CASES) - collected_cases)
    if stale:
        examples = ", ".join(stale[:5])
        raise pytest.UsageError(
            f"{len(stale)} requires_provider registry keys did not match the complete "
            f"pytest collection: {examples}"
        )


def pytest_runtest_setup(item: pytest.Item) -> None:
    marker = item.get_closest_marker("requires_provider")
    if marker is None:
        return

    provider_ids = tuple(dict.fromkeys(str(provider_id) for provider_id in marker.args))
    missing = [
        provider_id
        for provider_id in provider_ids
        if not default_provider_root(REPOSITORY_ROOT, provider_id).is_dir()
    ]
    if missing:
        pytest.skip("Pinned provider checkout unavailable: " + ", ".join(sorted(missing)))
