"""Command-line interface for the FolderHome foundation."""

import argparse
import json
import os
import shutil
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from folderhome.application import run_synthetic
from folderhome.application.accident_demo import SyntheticAccidentDemoError
from folderhome.application.administrative_drafts import (
    AdministrativeDraftError,
    build_administrative_draft_plan,
    load_administrative_draft_request,
    write_administrative_draft,
)
from folderhome.application.archive_fcsa_plan import (
    ArchivePlanValidationError,
    validate_archive_proposals,
)
from folderhome.application.artifact_studio import (
    ArtifactStudioError,
    build_artifact_studio_plan,
    build_design_preview,
    load_artifact_request,
    load_design_request,
    write_design_outputs,
)
from folderhome.application.benefit_screening import (
    BenefitScreeningError,
    load_benefit_catalog,
    load_benefit_profile_snapshot,
    screen_benefits,
    write_benefit_screening_report,
)
from folderhome.application.calendar_connectors import (
    CalendarConnectorError,
    build_calendar_connector_plan,
    execute_calendar_connector_plan,
    load_calendar_connector_accounts,
    load_calendar_connector_request,
)
from folderhome.application.calendar_handoff import (
    CalendarWorkflowError,
    analyze_folder_calendar,
    apply_calendar_handoff_plan,
    build_calendar_handoff_plan,
    load_calendar_configuration,
    resolve_calendar_preferences,
)
from folderhome.application.competition_demo import (
    CompetitionDemoError,
    run_competition_demo,
)
from folderhome.application.contacts import (
    ContactWorkflowError,
    analyze_folder_contacts,
    apply_contact_register_plan,
    build_contact_register_plan,
)
from folderhome.application.contract_cockpit import build_contract_cockpit
from folderhome.application.correspondence import (
    CorrespondenceError,
    build_correspondence_preview,
    load_correspondence_configuration,
    load_correspondence_request,
    write_correspondence_outputs,
)
from folderhome.application.daily_briefing import (
    DailyBriefingError,
    build_daily_briefing_plan,
    deliver_daily_briefing,
    load_daily_briefing_request,
    render_daily_briefing,
)
from folderhome.application.directory_observation import (
    DirectoryObservationError,
    load_watched_folder_configuration,
    run_directory_scan,
)
from folderhome.application.directory_snapshot import (
    DirectorySnapshotError,
    build_directory_diff,
    build_learning_examples,
    read_directory_snapshot,
    snapshot_directory,
    write_directory_snapshot,
)
from folderhome.application.document_action_execution import (
    DocumentActionExecutionError,
    execute_document_actions,
    read_action_execution_report,
    undo_document_actions,
)
from folderhome.application.document_action_plan import (
    DocumentActionPlanError,
    build_document_action_plan,
)
from folderhome.application.document_ingest import (
    FolderIngestGateError,
    FolderIngestResourceError,
    ingest_folder,
)
from folderhome.application.document_package import (
    DocumentPackageError,
    prepare_folder_package,
    write_folder_package,
)
from folderhome.application.document_search import build_theme_dossier, search_documents
from folderhome.application.document_transform import (
    DocumentTransformError,
    collect_bundle_documents,
    plan_document_bundle,
    write_document_bundle,
)
from folderhome.application.fcsa_plan import run_fcsa_plan
from folderhome.application.finance_statements import (
    FinanceWorkflowError,
    analyze_folder_statements,
    apply_finance_import_plan,
    build_finance_import_plan,
    build_recurring_cost_report,
)
from folderhome.application.findcall import (
    FindCallWorkflowError,
    build_findcall_plan,
    build_findcall_request,
    run_findcall_dry_run,
)
from folderhome.application.folder_cleanup import (
    FolderCleanupError,
    build_folder_cleanup_plan,
    execute_folder_cleanup,
)
from folderhome.application.folder_report import build_folder_report
from folderhome.application.folder_routine import (
    FolderRoutineError,
    build_folder_routine_plan,
    execute_folder_routine,
)
from folderhome.application.health_dossier import (
    HealthDossierGateError,
    build_health_dossier,
)
from folderhome.application.household_inventory import (
    InventoryWorkflowError,
    analyze_folder_inventory,
    apply_inventory_import_plan,
    build_inventory_import_plan,
    build_inventory_needs_report,
)
from folderhome.application.legal_change_monitor import (
    LegalChangeMonitorError,
    compare_legal_source_snapshots,
    load_legal_interest_snapshot,
    load_legal_source_snapshot,
    write_legal_change_report,
)
from folderhome.application.local_app import (
    LocalAppError,
    LocalApplication,
    LocalAppSettings,
)
from folderhome.application.mail_connector import (
    MailConnectorError,
    build_mail_ingest_plan,
    load_mail_accounts,
    load_mail_ingest_request,
)
from folderhome.application.medication_intake import (
    MedicationWorkflowError,
    analyze_folder_medication_plans,
    apply_medication_import_plan,
    build_medication_day_report,
    build_medication_import_plan,
    confirm_medication_intake,
)
from folderhome.application.official_notices import (
    OfficialNoticeError,
    analyze_official_notice,
    write_official_notice_report,
)
from folderhome.application.personal_notes import (
    PersonalNoteWorkflowError,
    apply_personal_note_plan,
    build_personal_note_plan,
    load_personal_note_request,
)
from folderhome.application.profile_rules import (
    ProfileConfigurationError,
    load_profile_configuration,
    resolve_profile_policy,
)
from folderhome.application.recipes import (
    build_recipe_plan,
    execute_recipe_plan,
    load_bundled_recipe,
    load_bundled_recipes,
)
from folderhome.application.resource_registry import (
    ResourceRegistryError,
    default_resource_registry_path,
    load_resource_registry,
)
from folderhome.application.routine_queue import (
    RoutineQueueError,
    build_folder_routine_queue,
    load_folder_routine_bindings,
)
from folderhome.application.scheduler_handoff import (
    SchedulerHandoffError,
    build_scheduler_handoff,
    run_scheduler_queue,
)
from folderhome.application.strands_agent import (
    FolderHomeAgentError,
    StrandsAgentSettings,
    plan_folderhome_agent,
)
from folderhome.application.tax_workpaper import (
    TaxWorkflowError,
    apply_tax_receipt_plan,
    build_tax_export_plan,
    build_tax_receipt_plan,
    export_tax_workpaper,
    load_tax_receipt_request,
)
from folderhome.application.version_analysis import (
    DocumentVersionAnalysisError,
    analyze_document_versions,
)
from folderhome.application.workflow_execution import (
    AdministrativeDraftWorkflowAdapter,
    ArtifactStudioWorkflowAdapter,
    BenefitScreeningWorkflowAdapter,
    ContactRegisterWorkflowAdapter,
    ContractCockpitWorkflowAdapter,
    CorrespondenceWorkflowAdapter,
    DailyBriefingWorkflowAdapter,
    DirectoryObservationWorkflowAdapter,
    DocumentActionExecutionWorkflowAdapter,
    DocumentActionPlanWorkflowAdapter,
    DocumentBundleWorkflowAdapter,
    DocumentPackageWorkflowAdapter,
    FcsaDryRunWorkflowAdapter,
    FinanceImportWorkflowAdapter,
    FindCallWorkflowAdapter,
    FolderCleanupWorkflowAdapter,
    FolderRoutineWorkflowAdapter,
    HealthDossierWorkflowAdapter,
    InventoryImportWorkflowAdapter,
    LegalChangeMonitorWorkflowAdapter,
    LocalCalendarWorkflowAdapter,
    MailDraftWorkflowAdapter,
    MedicationIntakeWorkflowAdapter,
    OfficialNoticeWorkflowAdapter,
    PersonalNotesWorkflowAdapter,
    RoutineQueueWorkflowAdapter,
    TaxWorkpaperWorkflowAdapter,
    WorkflowExecutionError,
    WorkflowExecutionGateway,
)
from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
    verify_checkout_revision,
)
from folderhome.bridges.call_plugins import CallPluginBridge, CallPluginBridgeError
from folderhome.bridges.doc_services import DocServicesBridge, DocServicesBridgeError
from folderhome.bridges.fcsa import FcsaDryRunBridge
from folderhome.bridges.knowledge_digest import (
    KnowledgeDigestBridge,
    KnowledgeDigestBridgeError,
)
from folderhome.bridges.law_checker import LawCheckerBridge, LawCheckerBridgeError
from folderhome.bridges.llm_note import LlmNoteBridge, LlmNoteBridgeError
from folderhome.bridges.tax_assistant import TaxAssistantBridge, TaxAssistantBridgeError
from folderhome.capabilities.audit import write_report
from folderhome.capabilities.calendar_connector_gateway import (
    SyntheticCalendarConnectorGateway,
)
from folderhome.capabilities.calendar_store import CalendarStore, CalendarStoreError
from folderhome.capabilities.catalog import DocumentCatalogError, DocumentCatalogStore
from folderhome.capabilities.contact_registry import (
    ContactRegisterError,
    ContactRegisterStore,
)
from folderhome.capabilities.finance_store import FinanceStore, FinanceStoreError
from folderhome.capabilities.findcall import SyntheticFindCallProvider
from folderhome.capabilities.inventory_store import InventoryStore, InventoryStoreError
from folderhome.capabilities.medication_store import MedicationStore, MedicationStoreError
from folderhome.capabilities.personal_note_guide import SyntheticPersonalNoteGuide
from folderhome.contracts import (
    ActionExecutionApproval,
    ActionUndoApproval,
    AdministrativeDraftApproval,
    BatchItemApproval,
    BriefingDeliveryApproval,
    BriefingRenderApproval,
    BundleFormat,
    CalendarBackend,
    CalendarConnectorApproval,
    CalendarHandoffApproval,
    CalendarHandoffPlan,
    ContactRegisterApproval,
    ContactRegisterPlan,
    ContractCockpitRequest,
    FinanceImportApproval,
    FinanceImportPlan,
    FindCallCandidate,
    FindCallFixtureOutcome,
    FindCallKind,
    FindCallPlan,
    FindCallStatus,
    FindCallWindow,
    FolderCleanupApproval,
    FolderRoutineMode,
    InventoryImportApproval,
    InventoryImportPlan,
    MedicationImportApproval,
    MedicationImportPlan,
    MedicationIntakeConfirmation,
    PersonalNoteApproval,
    PlacementReceipt,
    PluginDescriptor,
    RunStatus,
    TaxExportApproval,
    TaxReceiptApproval,
)
from folderhome.contracts.recipes import CapabilityRecipeError
from folderhome.demo_site import DemoSiteApplication
from folderhome.local_server import LocalServerError, create_local_server
from folderhome.plugin_host import ManifestValidationError, load_manifests
from folderhome.setup_app import (
    LAUNCH_CONFIG_SCHEMA,
    SetupAppError,
    SetupApplication,
    default_config_dir,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
DEFAULT_MANIFEST_ROOT = REPOSITORY_ROOT / "manifests" / "components"
DEFAULT_FCSA_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "file-collect-sort-action"
DEFAULT_DOC_SERVICES_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "doc-services"
DEFAULT_KNOWLEDGE_DIGEST_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "KnowledgeDigest"
DEFAULT_HUNGRYCALL_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "hungrycall"
DEFAULT_RINGEDINGEDING_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "ringedingeding"
DEFAULT_AI_MEDIA_EDITOR_ROOT = REPOSITORY_ROOT.parent / "ai-media-editor"
DEFAULT_DOCS_GRABBER_ROOT = REPOSITORY_ROOT.parent / "UniversalDocsGrabber"
DEFAULT_UPTODAY_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "UpToday"
DEFAULT_LLM_NOTE_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "llm-note"
DEFAULT_TAX_ASSISTANT_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "steuer-assistent"
DEFAULT_LAW_CHECKER_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "law-checker"
REPORT_FORGE_REVISION = "355acb5ff1abe41b384a0d1e3a00925e6ac86215"
REPORT_FORGE_DISTRIBUTION_VERSION = "1.1.4"
REPORT_FORGE_RUNTIME_VERSION = "1.1.0"
AI_MEDIA_EDITOR_REVISION = "4e4c79d8c16a117bf69c0f72ad946575110a6b84"
AI_MEDIA_EDITOR_TESTS_PASSED = 45
SPREADSHEET_WORKSPACE_LOADER_BOUND = False
MAILPROCESSOR_REVISION = "704575901b8b526dcd1436a86d6f42818b4079cd"
UNIVERSAL_DOCS_GRABBER_REVISION = "0ccd03455b63acbca6e71cc48ba464f208a759cd"
UNIVERSAL_MAIL_CLEANER_REVISION = "85de4dd2e84c499152b09d4e5688332ff3bb2ed4"
UNIVERSAL_INVOICE_MAIL_REVISION = "c58be4cdf92d8265694037cf1dbf7f14c84b39f9"
UPTODAY_REVISION = "7582ca87e17e458bb99a7379d2c54003c15415a4"
ROUTINIKA_BUNDLE_SHA256 = "3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2"
ROUTINIKA_EXPORTFORMAT_SHA256 = "94cfdf42cc2b45e5a4260a43788f03041ebfb99aea8d8b3ef900debdc5314f8d"
ROUTINIKA_README_SHA256 = "2461b05a7c5b17dc311fea42adb2b88cead70dd765b0f53d50c7e8bbc7a8bc60"
GOOGLE_CALENDAR_SKILL_REVISION = "google-calendar-skill@1.2.5"


def main(argv: Sequence[str] | None = None) -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
        sys.stderr.reconfigure(encoding="utf-8", errors="strict")
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "plugins" and args.plugins_command == "validate":
        try:
            plugins = load_manifests(args.manifest_root)
        except ManifestValidationError as exc:
            print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
            return 2
        payload = {"valid": True, "plugins": [plugin.plugin_id for plugin in plugins]}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "run" and args.run_command == "synthetic":
        run_id = args.run_id or f"run_{uuid4().hex}"
        report = run_synthetic(args.scenario, run_id=run_id)
        write_report(report, args.report_file)
        print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "run" and args.run_command == "fcsa-plan":
        run_id = args.run_id or f"run_{uuid4().hex}"
        try:
            plugin = next(
                plugin
                for plugin in load_manifests(args.manifest_root)
                if plugin.plugin_id == "file-collect-sort-action"
            )
        except (ManifestValidationError, StopIteration) as exc:
            print(
                json.dumps(
                    {"valid": False, "error": f"FCSA-Manifest nicht verfügbar: {exc}"},
                    ensure_ascii=False,
                )
            )
            return 2
        bridge = FcsaDryRunBridge(plugin=plugin, provider_root=args.provider_root)
        report = run_fcsa_plan(
            args.config_dir,
            run_id=run_id,
            plugin=plugin,
            bridge=bridge,
        )
        write_report(report, args.report_file)
        print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
        return 1 if report.status is RunStatus.FAILED else 0
    if args.command == "documents" and args.documents_command == "ingest":
        return _run_document_ingest(args)
    if args.command == "documents" and args.documents_command == "search":
        return _run_document_search(args)
    if args.command == "documents" and args.documents_command == "dossier":
        return _run_document_dossier(args)
    if args.command == "documents" and args.documents_command == "versions":
        return _run_document_versions(args)
    if args.command == "documents" and args.documents_command == "plan":
        return _run_document_plan(args)
    if args.command == "documents" and args.documents_command == "execute":
        return _run_document_execute(args)
    if args.command == "documents" and args.documents_command == "undo":
        return _run_document_undo(args)
    if args.command == "documents" and args.documents_command == "bundle":
        return _run_document_bundle(args)
    if args.command == "documents" and args.documents_command == "package":
        return _run_document_package(args)
    if args.command == "profiles" and args.profiles_command == "validate":
        return _run_profiles_validate(args)
    if args.command == "profiles" and args.profiles_command == "resolve":
        return _run_profiles_resolve(args)
    if args.command == "resources" and args.resources_command == "validate":
        return _run_resources_validate(args)
    if args.command == "resources" and args.resources_command == "catalog":
        return _run_resources_catalog(args)
    if args.command == "contacts" and args.contacts_command == "plan":
        return _run_contacts_plan(args)
    if args.command == "contacts" and args.contacts_command == "apply":
        return _run_contacts_apply(args)
    if args.command == "contacts" and args.contacts_command == "list":
        return _run_contacts_list(args)
    if args.command == "calendar" and args.calendar_command == "plan":
        return _run_calendar_plan(args)
    if args.command == "calendar" and args.calendar_command == "apply":
        return _run_calendar_apply(args)
    if args.command == "calendar" and args.calendar_command == "list":
        return _run_calendar_list(args)
    if args.command == "calendar" and args.calendar_command == "connectors":
        return _run_calendar_connectors(args)
    if args.command == "calendar" and args.calendar_command == "connector-plan":
        return _run_calendar_connector_plan(args)
    if args.command == "calendar" and args.calendar_command == "connector-simulate":
        return _run_calendar_connector_simulate(args)
    if args.command == "findcall" and args.findcall_command == "plugins":
        return _run_findcall_plugins(args)
    if args.command == "findcall" and args.findcall_command == "plan":
        return _run_findcall_plan(args)
    if args.command == "findcall" and args.findcall_command == "simulate":
        return _run_findcall_simulate(args)
    if args.command == "finance" and args.finance_command == "plan":
        return _run_finance_plan(args)
    if args.command == "finance" and args.finance_command == "apply":
        return _run_finance_apply(args)
    if args.command == "finance" and args.finance_command == "transactions":
        return _run_finance_transactions(args)
    if args.command == "finance" and args.finance_command == "coverage":
        return _run_finance_coverage(args)
    if args.command == "finance" and args.finance_command == "period":
        return _run_finance_period(args)
    if args.command == "finance" and args.finance_command == "recurring":
        return _run_finance_recurring(args)
    if args.command == "inventory" and args.inventory_command == "plan":
        return _run_inventory_plan(args)
    if args.command == "inventory" and args.inventory_command == "apply":
        return _run_inventory_apply(args)
    if args.command == "inventory" and args.inventory_command == "current":
        return _run_inventory_current(args)
    if args.command == "inventory" and args.inventory_command == "history":
        return _run_inventory_history(args)
    if args.command == "inventory" and args.inventory_command == "needs":
        return _run_inventory_needs(args)
    if args.command == "medication" and args.medication_command == "plan":
        return _run_medication_plan(args)
    if args.command == "medication" and args.medication_command == "apply":
        return _run_medication_apply(args)
    if args.command == "medication" and args.medication_command == "day":
        return _run_medication_day(args)
    if args.command == "medication" and args.medication_command == "confirm":
        return _run_medication_confirm(args)
    if args.command == "medication" and args.medication_command == "history":
        return _run_medication_history(args)
    if args.command == "health" and args.health_command == "dossier":
        return _run_health_dossier(args)
    if args.command == "contracts" and args.contracts_command == "cockpit":
        return _run_contract_cockpit(args)
    if args.command == "correspondence" and args.correspondence_command == "preview":
        return _run_correspondence_preview(args)
    if args.command == "correspondence" and args.correspondence_command == "render":
        return _run_correspondence_render(args)
    if args.command == "artifacts" and args.artifacts_command == "plan":
        return _run_artifacts_plan(args)
    if args.command == "artifacts" and args.artifacts_command == "design-preview":
        return _run_artifacts_design_preview(args)
    if args.command == "artifacts" and args.artifacts_command == "design-render":
        return _run_artifacts_design_render(args)
    if args.command == "mail" and args.mail_command == "providers":
        return _run_mail_providers(args)
    if args.command == "mail" and args.mail_command == "ingest-plan":
        return _run_mail_ingest_plan(args)
    if args.command == "notes" and args.notes_command == "providers":
        return _run_note_providers(args)
    if args.command == "notes" and args.notes_command == "guide":
        return _run_note_guide(args)
    if args.command == "notes" and args.notes_command == "apply":
        return _run_note_apply(args)
    if args.command == "notes" and args.notes_command == "list":
        return _run_note_list(args)
    if args.command == "notes" and args.notes_command == "history":
        return _run_note_history(args)
    if args.command == "tax" and args.tax_command == "providers":
        return _run_tax_providers(args)
    if args.command == "tax" and args.tax_command == "receipt-plan":
        return _run_tax_receipt_plan(args)
    if args.command == "tax" and args.tax_command == "receipt-apply":
        return _run_tax_receipt_apply(args)
    if args.command == "tax" and args.tax_command == "export-plan":
        return _run_tax_export_plan(args)
    if args.command == "tax" and args.tax_command == "export":
        return _run_tax_export(args)
    if args.command == "briefing" and args.briefing_command == "providers":
        return _run_briefing_providers(args)
    if args.command == "briefing" and args.briefing_command == "plan":
        return _run_briefing_plan(args)
    if args.command == "briefing" and args.briefing_command == "render":
        return _run_briefing_render(args)
    if args.command == "briefing" and args.briefing_command == "deliver":
        return _run_briefing_deliver(args)
    if args.command == "notices" and args.notices_command == "providers":
        return _run_notice_providers(args)
    if args.command == "notices" and args.notices_command == "inspect":
        return _run_notice_inspect(args)
    if args.command == "notices" and args.notices_command == "render":
        return _run_notice_render(args)
    if args.command == "drafts" and args.drafts_command == "preview":
        return _run_administrative_draft_preview(args)
    if args.command == "drafts" and args.drafts_command == "render":
        return _run_administrative_draft_render(args)
    if args.command == "benefits" and args.benefits_command == "check":
        return _run_benefit_screening(args)
    if args.command == "benefits" and args.benefits_command == "render":
        return _run_benefit_screening_render(args)
    if args.command == "legal" and args.legal_command == "providers":
        return _run_legal_providers(args)
    if args.command == "legal" and args.legal_command == "compare":
        return _run_legal_compare(args)
    if args.command == "legal" and args.legal_command == "render":
        return _run_legal_render(args)
    if args.command == "agent" and args.agent_command == "plan":
        return _run_strands_agent_plan(args)
    if args.command == "agent" and args.agent_command in {"run", "chat"}:
        return _run_strands_agent(args)
    if args.command == "agent" and args.agent_command == "session":
        return _run_strands_agent_session(args)
    if args.command == "demo" and args.demo_command == "run":
        return _run_competition_demo(args)
    if args.command == "demo" and args.demo_command == "accident-serve":
        return _run_accident_demo_site(args)
    if args.command == "recipes" and args.recipes_command == "list":
        return _run_recipes_list(args)
    if args.command == "recipes" and args.recipes_command == "plan":
        return _run_recipes_plan(args)
    if args.command == "recipes" and args.recipes_command == "run":
        return _run_recipes_run(args)
    if args.command == "app" and args.app_command == "plan":
        return _run_local_app_plan(args)
    if args.command == "app" and args.app_command == "serve":
        return _run_local_app_serve(args)
    if args.command == "setup" and args.setup_command == "plan":
        return _run_setup_plan(args)
    if args.command == "setup" and args.setup_command == "serve":
        return _run_setup_serve(args)
    if args.command == "mcp" and args.mcp_command == "plan":
        return _run_mcp_plan(args)
    if args.command == "mcp" and args.mcp_command == "serve":
        return _run_mcp_serve(args)
    if args.command == "folders" and args.folders_command == "snapshot":
        return _run_folders_snapshot(args)
    if args.command == "folders" and args.folders_command == "diff":
        return _run_folders_diff(args)
    if args.command == "folders" and args.folders_command == "learning":
        return _run_folders_learning(args)
    if args.command == "folders" and args.folders_command == "scan":
        return _run_folders_scan(args)
    if args.command == "folders" and args.folders_command == "cleanup-plan":
        return _run_folders_cleanup_plan(args)
    if args.command == "folders" and args.folders_command == "cleanup-execute":
        return _run_folders_cleanup_execute(args)
    if args.command == "folders" and args.folders_command == "routine-plan":
        return _run_folders_routine_plan(args)
    if args.command == "folders" and args.folders_command == "routine-execute":
        return _run_folders_routine_execute(args)
    if args.command == "folders" and args.folders_command == "routine-queue":
        return _run_folders_routine_queue(args)
    if args.command == "scheduler" and args.scheduler_command == "plan":
        return _run_scheduler_plan(args)
    if args.command == "scheduler" and args.scheduler_command == "run":
        return _run_scheduler_run(args)
    parser.error("unsupported command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="folderhome")
    commands = parser.add_subparsers(dest="command", required=True)
    plugins = commands.add_parser("plugins")
    plugin_commands = plugins.add_subparsers(dest="plugins_command", required=True)
    validate = plugin_commands.add_parser("validate")
    validate.add_argument("--json", action="store_true", dest="as_json")
    validate.add_argument(
        "--manifest-root",
        type=Path,
        default=DEFAULT_MANIFEST_ROOT,
    )
    run = commands.add_parser("run")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    synthetic = run_commands.add_parser("synthetic")
    synthetic.add_argument(
        "--scenario",
        choices=("success", "blocked", "failure"),
        default="success",
    )
    synthetic.add_argument("--run-id")
    synthetic.add_argument("--report-file", type=Path, required=True)
    synthetic.add_argument("--json", action="store_true", dest="as_json")
    fcsa_plan = run_commands.add_parser("fcsa-plan")
    fcsa_plan.add_argument("--config-dir", type=Path, required=True)
    fcsa_plan.add_argument("--provider-root", type=Path, default=DEFAULT_FCSA_PROVIDER_ROOT)
    fcsa_plan.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    fcsa_plan.add_argument("--run-id")
    fcsa_plan.add_argument("--report-file", type=Path, required=True)
    fcsa_plan.add_argument("--json", action="store_true", dest="as_json")
    documents = commands.add_parser("documents")
    document_commands = documents.add_subparsers(
        dest="documents_command",
        required=True,
    )
    ingest = document_commands.add_parser("ingest")
    ingest.add_argument("--source-dir", type=Path, required=True)
    ingest.add_argument("--state-dir", type=Path, required=True)
    ingest.add_argument(
        "--approve-index-write",
        action="store_true",
        help="Gibt ausschließlich den lokalen KnowledgeDigest-Indexschreibzugriff frei.",
    )
    ingest.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    ingest.add_argument("--result-file", type=Path)
    ingest.add_argument("--report-file", type=Path)
    ingest.add_argument("--report-title")
    ingest.add_argument("--sentence-limit", type=int, choices=(2, 3), default=3)
    _add_document_provider_arguments(ingest, include_doc_services=True)
    ingest.add_argument("--json", action="store_true", dest="as_json")

    search = document_commands.add_parser("search")
    search.add_argument("--state-dir", type=Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=20)
    _add_document_provider_arguments(search)
    search.add_argument("--json", action="store_true", dest="as_json")

    dossier = document_commands.add_parser("dossier")
    dossier.add_argument("--state-dir", type=Path, required=True)
    dossier.add_argument("--topic", required=True)
    dossier.add_argument("--limit", type=int, default=100)
    dossier.add_argument("--output-file", type=Path)
    _add_document_provider_arguments(dossier)
    dossier.add_argument("--json", action="store_true", dest="as_json")

    versions = document_commands.add_parser("versions")
    versions.add_argument("--state-dir", type=Path, required=True)
    versions.add_argument("--query", required=True)
    versions.add_argument("--limit", type=int, default=100)
    versions.add_argument("--archive-folder", default="Archiv")
    versions.add_argument("--output-file", type=Path)
    versions.add_argument("--fcsa-root", type=Path, default=DEFAULT_FCSA_PROVIDER_ROOT)
    _add_document_provider_arguments(versions, include_doc_services=True)
    versions.add_argument("--json", action="store_true", dest="as_json")

    plan = document_commands.add_parser("plan")
    _add_action_plan_arguments(plan)
    plan.add_argument("--output-file", type=Path)
    plan.add_argument("--json", action="store_true", dest="as_json")

    execute = document_commands.add_parser("execute")
    _add_action_plan_arguments(execute)
    execute.add_argument("--state-dir", type=Path, required=True)
    execute.add_argument("--approval-id", required=True)
    execute.add_argument("--approve-plan-id", required=True)
    execute.add_argument(
        "--approve-action-id",
        action="append",
        required=True,
        dest="approved_action_ids",
    )
    execute.add_argument("--approved-at", required=True)
    execute.add_argument("--approve-file-write", action="store_true")
    execute.add_argument("--json", action="store_true", dest="as_json")

    undo = document_commands.add_parser("undo")
    undo.add_argument("--execution-file", type=Path, required=True)
    undo.add_argument("--approval-id", required=True)
    undo.add_argument("--approve-execution-id", required=True)
    undo.add_argument("--document-sha256", required=True)
    undo.add_argument("--approved-at", required=True)
    undo.add_argument("--approve-file-write", action="store_true")
    undo.add_argument("--json", action="store_true", dest="as_json")

    bundle = document_commands.add_parser("bundle")
    bundle.add_argument("--source-dir", type=Path, required=True)
    bundle.add_argument("--output-file", type=Path, required=True)
    bundle.add_argument("--format", choices=("txt", "pdf"), required=True)
    bundle.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    bundle.add_argument("--approve-output-write", action="store_true")
    bundle.add_argument("--result-file", type=Path)
    bundle.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    bundle.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    bundle.add_argument("--json", action="store_true", dest="as_json")

    package = document_commands.add_parser("package")
    package.add_argument("--source-dir", type=Path, required=True)
    package.add_argument("--output-zip", type=Path, required=True)
    package.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    package.add_argument("--approve-output-write", action="store_true")
    package.add_argument("--result-file", type=Path)
    package.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    package.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    package.add_argument("--json", action="store_true", dest="as_json")

    profiles = commands.add_parser("profiles")
    profile_commands = profiles.add_subparsers(dest="profiles_command", required=True)
    profile_validate = profile_commands.add_parser("validate")
    profile_validate.add_argument("--profiles-dir", type=Path, required=True)
    profile_validate.add_argument("--json", action="store_true", dest="as_json")
    profile_resolve = profile_commands.add_parser("resolve")
    profile_resolve.add_argument("--profiles-dir", type=Path, required=True)
    profile_resolve.add_argument("--profile", required=True)
    profile_resolve.add_argument("--area", required=True)
    profile_resolve.add_argument("--json", action="store_true", dest="as_json")

    resources = commands.add_parser("resources")
    resource_commands = resources.add_subparsers(
        dest="resources_command",
        required=True,
    )
    resource_validate = resource_commands.add_parser("validate")
    _add_resource_registry_arguments(resource_validate)
    resource_catalog = resource_commands.add_parser("catalog")
    _add_resource_registry_arguments(resource_catalog)
    resource_catalog.add_argument("--profile", required=True)

    contacts = commands.add_parser("contacts")
    contact_commands = contacts.add_subparsers(dest="contacts_command", required=True)
    contact_plan = contact_commands.add_parser("plan")
    _add_contact_plan_arguments(contact_plan)
    contact_plan.add_argument("--output-file", type=Path)
    contact_plan.add_argument("--json", action="store_true", dest="as_json")
    contact_apply = contact_commands.add_parser("apply")
    _add_contact_plan_arguments(contact_apply)
    contact_apply.add_argument("--approval-file", type=Path, required=True)
    contact_apply.add_argument("--approve-state-write", action="store_true")
    contact_apply.add_argument("--json", action="store_true", dest="as_json")
    contact_list = contact_commands.add_parser("list")
    contact_list.add_argument("--state-dir", type=Path, required=True)
    contact_list.add_argument("--profile")
    contact_list.add_argument("--area")
    contact_list.add_argument("--object", dest="object_query")
    contact_list.add_argument(
        "--include-deletion-candidates",
        action="store_true",
    )
    contact_list.add_argument("--json", action="store_true", dest="as_json")

    calendar = commands.add_parser("calendar")
    calendar_commands = calendar.add_subparsers(dest="calendar_command", required=True)
    calendar_plan = calendar_commands.add_parser("plan")
    _add_calendar_plan_arguments(calendar_plan)
    calendar_plan.add_argument("--output-file", type=Path)
    calendar_plan.add_argument("--json", action="store_true", dest="as_json")
    calendar_apply = calendar_commands.add_parser("apply")
    _add_calendar_plan_arguments(calendar_apply)
    calendar_apply.add_argument("--approval-file", type=Path, required=True)
    calendar_apply.add_argument("--approve-state-write", action="store_true")
    calendar_apply.add_argument("--approve-output-write", action="store_true")
    calendar_apply.add_argument("--json", action="store_true", dest="as_json")
    calendar_list = calendar_commands.add_parser("list")
    calendar_list.add_argument("--state-dir", type=Path, required=True)
    calendar_list.add_argument("--profile")
    calendar_list.add_argument("--area")
    calendar_list.add_argument("--date-from")
    calendar_list.add_argument("--date-to")
    calendar_list.add_argument("--json", action="store_true", dest="as_json")
    calendar_connectors = calendar_commands.add_parser("connectors")
    calendar_connectors.add_argument(
        "--uptoday-root",
        type=Path,
        default=DEFAULT_UPTODAY_PROVIDER_ROOT,
    )
    calendar_connectors.add_argument("--json", action="store_true", dest="as_json")
    calendar_connector_plan = calendar_commands.add_parser("connector-plan")
    _add_calendar_connector_arguments(calendar_connector_plan)
    calendar_connector_plan.add_argument("--output-file", type=Path)
    calendar_connector_plan.add_argument("--json", action="store_true", dest="as_json")
    calendar_connector_simulate = calendar_commands.add_parser("connector-simulate")
    _add_calendar_connector_arguments(calendar_connector_simulate)
    calendar_connector_simulate.add_argument("--approval-id", required=True)
    calendar_connector_simulate.add_argument("--approved-at", required=True)
    calendar_connector_simulate.add_argument(
        "--approve-synthetic-calendar",
        action="store_true",
    )
    calendar_connector_simulate.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
    )

    findcall = commands.add_parser("findcall")
    findcall_commands = findcall.add_subparsers(dest="findcall_command", required=True)
    findcall_plugins = findcall_commands.add_parser("plugins")
    findcall_plugins.add_argument(
        "--hungrycall-root",
        type=Path,
        default=DEFAULT_HUNGRYCALL_PROVIDER_ROOT,
    )
    findcall_plugins.add_argument(
        "--ringedingeding-root",
        type=Path,
        default=DEFAULT_RINGEDINGEDING_PROVIDER_ROOT,
    )
    findcall_plugins.add_argument(
        "--manifest-root",
        type=Path,
        default=DEFAULT_MANIFEST_ROOT,
    )
    findcall_plugins.add_argument("--json", action="store_true", dest="as_json")
    findcall_plan = findcall_commands.add_parser("plan")
    _add_findcall_plan_arguments(findcall_plan)
    findcall_plan.add_argument("--output-file", type=Path)
    findcall_plan.add_argument("--json", action="store_true", dest="as_json")
    findcall_simulate = findcall_commands.add_parser("simulate")
    _add_findcall_plan_arguments(findcall_simulate)
    findcall_simulate.add_argument("--fixture-file", type=Path, required=True)
    findcall_simulate.add_argument("--json", action="store_true", dest="as_json")

    finance = commands.add_parser("finance")
    finance_commands = finance.add_subparsers(dest="finance_command", required=True)
    finance_plan = finance_commands.add_parser("plan")
    _add_finance_plan_arguments(finance_plan)
    finance_plan.add_argument("--output-file", type=Path)
    finance_plan.add_argument("--json", action="store_true", dest="as_json")
    finance_apply = finance_commands.add_parser("apply")
    _add_finance_plan_arguments(finance_apply)
    finance_apply.add_argument("--approval-file", type=Path, required=True)
    finance_apply.add_argument("--approve-state-write", action="store_true")
    finance_apply.add_argument("--json", action="store_true", dest="as_json")
    finance_transactions = finance_commands.add_parser("transactions")
    finance_transactions.add_argument("--state-dir", type=Path, required=True)
    finance_transactions.add_argument("--profile")
    finance_transactions.add_argument("--account")
    finance_transactions.add_argument("--date-from")
    finance_transactions.add_argument("--date-to")
    finance_transactions.add_argument("--json", action="store_true", dest="as_json")
    finance_coverage = finance_commands.add_parser("coverage")
    finance_coverage.add_argument("--state-dir", type=Path, required=True)
    finance_coverage.add_argument("--account", required=True)
    finance_coverage.add_argument("--date-from", required=True)
    finance_coverage.add_argument("--date-to", required=True)
    finance_coverage.add_argument("--json", action="store_true", dest="as_json")
    finance_period = finance_commands.add_parser("period")
    finance_period.add_argument("--state-dir", type=Path, required=True)
    finance_period.add_argument("--account", required=True)
    finance_period.add_argument("--date-from", required=True)
    finance_period.add_argument("--date-to", required=True)
    finance_period.add_argument("--json", action="store_true", dest="as_json")
    finance_recurring = finance_commands.add_parser("recurring")
    finance_recurring.add_argument("--state-dir", type=Path, required=True)
    finance_recurring.add_argument("--profile", required=True)
    finance_recurring.add_argument("--as-of", required=True)
    finance_recurring.add_argument("--json", action="store_true", dest="as_json")

    inventory = commands.add_parser("inventory")
    inventory_commands = inventory.add_subparsers(dest="inventory_command", required=True)
    inventory_plan = inventory_commands.add_parser("plan")
    _add_inventory_plan_arguments(inventory_plan)
    inventory_plan.add_argument("--output-file", type=Path)
    inventory_plan.add_argument("--json", action="store_true", dest="as_json")
    inventory_apply = inventory_commands.add_parser("apply")
    _add_inventory_plan_arguments(inventory_apply)
    inventory_apply.add_argument("--approval-file", type=Path, required=True)
    inventory_apply.add_argument("--approve-state-write", action="store_true")
    inventory_apply.add_argument("--json", action="store_true", dest="as_json")
    inventory_current = inventory_commands.add_parser("current")
    inventory_current.add_argument("--state-dir", type=Path, required=True)
    inventory_current.add_argument("--profile", required=True)
    inventory_current.add_argument("--area")
    inventory_current.add_argument("--as-of")
    inventory_current.add_argument("--json", action="store_true", dest="as_json")
    inventory_history = inventory_commands.add_parser("history")
    inventory_history.add_argument("--state-dir", type=Path, required=True)
    inventory_history.add_argument("--profile", required=True)
    inventory_history.add_argument("--area")
    inventory_history.add_argument("--item-id")
    inventory_history.add_argument("--json", action="store_true", dest="as_json")
    inventory_needs = inventory_commands.add_parser("needs")
    inventory_needs.add_argument("--state-dir", type=Path, required=True)
    inventory_needs.add_argument("--profile", required=True)
    inventory_needs.add_argument("--as-of", required=True)
    inventory_needs.add_argument("--expiry-horizon-days", type=int, default=30)
    inventory_needs.add_argument("--json", action="store_true", dest="as_json")

    medication = commands.add_parser("medication")
    medication_commands = medication.add_subparsers(
        dest="medication_command",
        required=True,
    )
    medication_plan = medication_commands.add_parser("plan")
    _add_medication_plan_arguments(medication_plan)
    medication_plan.add_argument("--output-file", type=Path)
    medication_plan.add_argument("--json", action="store_true", dest="as_json")
    medication_apply = medication_commands.add_parser("apply")
    _add_medication_plan_arguments(medication_apply)
    medication_apply.add_argument("--approval-file", type=Path, required=True)
    medication_apply.add_argument("--approve-state-write", action="store_true")
    medication_apply.add_argument("--json", action="store_true", dest="as_json")
    medication_day = medication_commands.add_parser("day")
    medication_day.add_argument("--state-dir", type=Path, required=True)
    medication_day.add_argument("--inventory-state-dir", type=Path)
    medication_day.add_argument("--profile", required=True)
    medication_day.add_argument("--date", required=True)
    medication_day.add_argument("--as-of", required=True)
    medication_day.add_argument("--json", action="store_true", dest="as_json")
    medication_confirm = medication_commands.add_parser("confirm")
    medication_confirm.add_argument("--state-dir", type=Path, required=True)
    medication_confirm.add_argument("--confirmation-file", type=Path, required=True)
    medication_confirm.add_argument("--approve-state-write", action="store_true")
    medication_confirm.add_argument("--json", action="store_true", dest="as_json")
    medication_history = medication_commands.add_parser("history")
    medication_history.add_argument("--state-dir", type=Path, required=True)
    medication_history.add_argument("--profile", required=True)
    medication_history.add_argument("--json", action="store_true", dest="as_json")

    health = commands.add_parser("health")
    health_commands = health.add_subparsers(dest="health_command", required=True)
    health_dossier = health_commands.add_parser("dossier")
    health_dossier.add_argument("--source-dir", type=Path, required=True)
    health_dossier.add_argument("--profiles-dir", type=Path, required=True)
    health_dossier.add_argument("--profile", required=True)
    health_dossier.add_argument("--as-of", type=date.fromisoformat, required=True)
    health_dossier.add_argument("--gap-threshold-days", type=int, default=90)
    health_dossier.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    health_dossier.add_argument("--approve-sensitive-local-read", action="store_true")
    health_dossier.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    health_dossier.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    health_dossier.add_argument("--output-markdown", type=Path)
    health_dossier.add_argument("--output-json", type=Path)
    health_dossier.add_argument("--json", action="store_true", dest="as_json")

    contracts = commands.add_parser("contracts")
    contract_commands = contracts.add_subparsers(
        dest="contracts_command",
        required=True,
    )
    contract_cockpit = contract_commands.add_parser("cockpit")
    contract_cockpit.add_argument("--request-file", type=Path, required=True)
    contract_cockpit.add_argument("--state-dir", type=Path, required=True)
    contract_cockpit.add_argument("--profiles-dir", type=Path, required=True)
    contract_cockpit.add_argument("--approve-sensitive-local-read", action="store_true")
    contract_cockpit.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    contract_cockpit.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    contract_cockpit.add_argument(
        "--knowledge-digest-root",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DIGEST_PROVIDER_ROOT,
    )
    contract_cockpit.add_argument("--output-markdown", type=Path)
    contract_cockpit.add_argument("--output-json", type=Path)
    contract_cockpit.add_argument("--json", action="store_true", dest="as_json")

    correspondence = commands.add_parser("correspondence")
    correspondence_commands = correspondence.add_subparsers(
        dest="correspondence_command",
        required=True,
    )
    correspondence_preview = correspondence_commands.add_parser("preview")
    _add_correspondence_arguments(correspondence_preview)
    correspondence_render = correspondence_commands.add_parser("render")
    _add_correspondence_arguments(correspondence_render)
    correspondence_render.add_argument("--markdown-file", type=Path, required=True)
    correspondence_render.add_argument("--text-file", type=Path, required=True)
    correspondence_render.add_argument("--approve-output-write", action="store_true")

    artifacts = commands.add_parser("artifacts")
    artifact_commands = artifacts.add_subparsers(
        dest="artifacts_command",
        required=True,
    )
    artifact_plan = artifact_commands.add_parser("plan")
    _add_artifact_request_arguments(artifact_plan)
    design_preview = artifact_commands.add_parser("design-preview")
    _add_artifact_request_arguments(design_preview)
    design_render = artifact_commands.add_parser("design-render")
    _add_artifact_request_arguments(design_render)
    design_render.add_argument("--json-file", type=Path, required=True)
    design_render.add_argument("--css-file", type=Path, required=True)
    design_render.add_argument("--business-card-file", type=Path, required=True)
    design_render.add_argument("--approve-output-write", action="store_true")

    mail = commands.add_parser("mail")
    mail_commands = mail.add_subparsers(dest="mail_command", required=True)
    mail_providers = mail_commands.add_parser("providers")
    mail_providers.add_argument("--json", action="store_true", dest="as_json")
    mail_ingest = mail_commands.add_parser("ingest-plan")
    mail_ingest.add_argument("--accounts-file", type=Path, required=True)
    mail_ingest.add_argument("--request-file", type=Path, required=True)
    mail_ingest.add_argument("--profiles-dir", type=Path, required=True)
    mail_ingest.add_argument(
        "--provider-root",
        type=Path,
        default=DEFAULT_DOCS_GRABBER_ROOT,
    )
    mail_ingest.add_argument("--use-synthetic-provider", action="store_true")
    mail_ingest.add_argument("--approve-sensitive-local-read", action="store_true")
    mail_ingest.add_argument("--json", action="store_true", dest="as_json")

    notes = commands.add_parser("notes")
    note_commands = notes.add_subparsers(dest="notes_command", required=True)
    note_providers = note_commands.add_parser("providers")
    note_providers.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    note_providers.add_argument(
        "--provider-root",
        type=Path,
        default=DEFAULT_LLM_NOTE_PROVIDER_ROOT,
    )
    note_providers.add_argument("--json", action="store_true", dest="as_json")
    note_guide = note_commands.add_parser("guide")
    _add_note_arguments(note_guide, include_request=True)
    note_guide.add_argument("--json", action="store_true", dest="as_json")
    note_apply = note_commands.add_parser("apply")
    _add_note_arguments(note_apply, include_request=True)
    note_apply.add_argument("--approval-file", type=Path, required=True)
    note_apply.add_argument("--approve-state-write", action="store_true")
    note_apply.add_argument("--json", action="store_true", dest="as_json")
    note_list = note_commands.add_parser("list")
    _add_note_arguments(note_list)
    note_list.add_argument("--profile", required=True)
    note_list.add_argument("--area")
    note_list.add_argument("--notebook")
    note_list.add_argument("--json", action="store_true", dest="as_json")
    note_history = note_commands.add_parser("history")
    _add_note_arguments(note_history)
    note_history.add_argument("--note-id", required=True)
    note_history.add_argument("--json", action="store_true", dest="as_json")

    tax = commands.add_parser("tax")
    tax_commands = tax.add_subparsers(dest="tax_command", required=True)
    tax_providers = tax_commands.add_parser("providers")
    tax_providers.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    tax_providers.add_argument(
        "--provider-root",
        type=Path,
        default=DEFAULT_TAX_ASSISTANT_PROVIDER_ROOT,
    )
    tax_providers.add_argument("--json", action="store_true", dest="as_json")
    tax_receipt_plan = tax_commands.add_parser("receipt-plan")
    _add_tax_receipt_arguments(tax_receipt_plan)
    tax_receipt_plan.add_argument("--json", action="store_true", dest="as_json")
    tax_receipt_apply = tax_commands.add_parser("receipt-apply")
    _add_tax_receipt_arguments(tax_receipt_apply)
    tax_receipt_apply.add_argument("--approval-file", type=Path, required=True)
    tax_receipt_apply.add_argument("--approve-state-write", action="store_true")
    tax_receipt_apply.add_argument("--json", action="store_true", dest="as_json")
    tax_export_plan = tax_commands.add_parser("export-plan")
    _add_tax_export_arguments(tax_export_plan)
    tax_export_plan.add_argument("--json", action="store_true", dest="as_json")
    tax_export = tax_commands.add_parser("export")
    _add_tax_export_arguments(tax_export)
    tax_export.add_argument("--approval-file", type=Path, required=True)
    tax_export.add_argument("--approve-state-write", action="store_true")
    tax_export.add_argument("--approve-output-write", action="store_true")
    tax_export.add_argument("--json", action="store_true", dest="as_json")

    briefing = commands.add_parser("briefing")
    briefing_commands = briefing.add_subparsers(
        dest="briefing_command",
        required=True,
    )
    briefing_providers = briefing_commands.add_parser("providers")
    briefing_providers.add_argument("--json", action="store_true", dest="as_json")
    briefing_plan = briefing_commands.add_parser("plan")
    _add_briefing_arguments(briefing_plan)
    briefing_plan.add_argument("--json", action="store_true", dest="as_json")
    briefing_render = briefing_commands.add_parser("render")
    _add_briefing_arguments(briefing_render)
    briefing_render.add_argument("--approval-file", type=Path, required=True)
    briefing_render.add_argument("--approve-output-write", action="store_true")
    briefing_render.add_argument("--json", action="store_true", dest="as_json")
    briefing_deliver = briefing_commands.add_parser("deliver")
    _add_briefing_arguments(briefing_deliver)
    briefing_deliver.add_argument("--approval-file", type=Path, required=True)
    briefing_deliver.add_argument("--approve-desktop-write", action="store_true")
    briefing_deliver.add_argument("--json", action="store_true", dest="as_json")

    notices = commands.add_parser("notices")
    notice_commands = notices.add_subparsers(dest="notices_command", required=True)
    notice_providers = notice_commands.add_parser("providers")
    notice_providers.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    notice_providers.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    notice_providers.add_argument("--json", action="store_true", dest="as_json")
    notice_inspect = notice_commands.add_parser("inspect")
    _add_notice_arguments(notice_inspect)
    notice_inspect.add_argument("--json", action="store_true", dest="as_json")
    notice_render = notice_commands.add_parser("render")
    _add_notice_arguments(notice_render)
    notice_render.add_argument("--markdown-file", type=Path, required=True)
    notice_render.add_argument("--json-file", type=Path, required=True)
    notice_render.add_argument("--approve-output-write", action="store_true")
    notice_render.add_argument("--json", action="store_true", dest="as_json")

    drafts = commands.add_parser("drafts")
    draft_commands = drafts.add_subparsers(dest="drafts_command", required=True)
    draft_preview = draft_commands.add_parser("preview")
    _add_administrative_draft_arguments(draft_preview)
    draft_preview.add_argument("--json", action="store_true", dest="as_json")
    draft_render = draft_commands.add_parser("render")
    _add_administrative_draft_arguments(draft_render)
    draft_render.add_argument("--approval-file", type=Path, required=True)
    draft_render.add_argument("--markdown-file", type=Path, required=True)
    draft_render.add_argument("--text-file", type=Path, required=True)
    draft_render.add_argument("--approve-output-write", action="store_true")
    draft_render.add_argument("--json", action="store_true", dest="as_json")

    benefits = commands.add_parser("benefits")
    benefit_commands = benefits.add_subparsers(dest="benefits_command", required=True)
    benefit_check = benefit_commands.add_parser("check")
    _add_benefit_screening_arguments(benefit_check)
    benefit_check.add_argument("--json", action="store_true", dest="as_json")
    benefit_render = benefit_commands.add_parser("render")
    _add_benefit_screening_arguments(benefit_render)
    benefit_render.add_argument("--markdown-file", type=Path, required=True)
    benefit_render.add_argument("--json-file", type=Path, required=True)
    benefit_render.add_argument("--approve-output-write", action="store_true")
    benefit_render.add_argument("--json", action="store_true", dest="as_json")

    legal = commands.add_parser("legal")
    legal_commands = legal.add_subparsers(dest="legal_command", required=True)
    legal_providers = legal_commands.add_parser("providers")
    legal_providers.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    legal_providers.add_argument(
        "--law-checker-root",
        type=Path,
        default=DEFAULT_LAW_CHECKER_PROVIDER_ROOT,
    )
    legal_providers.add_argument("--json", action="store_true", dest="as_json")
    legal_compare = legal_commands.add_parser("compare")
    _add_legal_change_arguments(legal_compare)
    legal_compare.add_argument("--json", action="store_true", dest="as_json")
    legal_render = legal_commands.add_parser("render")
    _add_legal_change_arguments(legal_render)
    legal_render.add_argument("--markdown-file", type=Path, required=True)
    legal_render.add_argument("--json-file", type=Path, required=True)
    legal_render.add_argument("--approve-output-write", action="store_true")
    legal_render.add_argument("--json", action="store_true", dest="as_json")

    agent = commands.add_parser("agent")
    agent_commands = agent.add_subparsers(dest="agent_command", required=True)
    agent_plan = agent_commands.add_parser("plan")
    _add_local_app_arguments(agent_plan)
    _add_strands_agent_arguments(agent_plan)
    agent_plan.add_argument("--json", action="store_true", dest="as_json")
    agent_run = agent_commands.add_parser("run")
    _add_local_app_arguments(agent_run)
    _add_strands_agent_arguments(agent_run)
    agent_run.add_argument("--profile-id", required=True)
    agent_run.add_argument("--prompt", required=True)
    agent_run.add_argument("--json", action="store_true", dest="as_json")
    agent_chat = agent_commands.add_parser("chat")
    _add_local_app_arguments(agent_chat)
    _add_strands_agent_arguments(agent_chat)
    agent_chat.add_argument("--profile-id", required=True)
    agent_chat.add_argument("--prompt", required=True)
    agent_chat.add_argument("--json", action="store_true", dest="as_json")
    agent_session = agent_commands.add_parser("session")
    _add_local_app_arguments(agent_session)
    _add_strands_agent_arguments(agent_session)
    agent_session.add_argument("--profile-id", required=True)
    agent_session.add_argument("--json", action="store_true", dest="as_json")

    demo = commands.add_parser("demo")
    demo_commands = demo.add_subparsers(dest="demo_command", required=True)
    demo_run = demo_commands.add_parser("run")
    demo_run.add_argument("--output-dir", type=Path, required=True)
    demo_run.add_argument("--approve-output-write", action="store_true")
    demo_run.add_argument("--json", action="store_true", dest="as_json")
    accident_demo = demo_commands.add_parser("accident-serve")
    accident_demo.add_argument("--workspace-dir", type=Path, required=True)
    accident_demo.add_argument("--port", type=int, default=8767)
    accident_demo.add_argument("--approve-loopback-server", action="store_true")
    accident_demo.add_argument("--json", action="store_true", dest="as_json")

    recipes = commands.add_parser("recipes")
    recipes_commands = recipes.add_subparsers(dest="recipes_command", required=True)
    recipes_list = recipes_commands.add_parser("list")
    recipes_list.add_argument("--language", choices=("en", "de"), default="en")
    recipes_list.add_argument("--json", action="store_true", dest="as_json")
    recipes_plan = recipes_commands.add_parser("plan")
    _add_local_app_arguments(recipes_plan)
    _add_strands_agent_arguments(recipes_plan)
    recipes_plan.add_argument("--profile-id", required=True)
    recipes_plan.add_argument("--recipe-id", required=True)
    recipes_plan.add_argument("--language", choices=("en", "de"), default="en")
    recipes_plan.add_argument("--json", action="store_true", dest="as_json")
    recipes_run = recipes_commands.add_parser("run")
    _add_local_app_arguments(recipes_run)
    _add_strands_agent_arguments(recipes_run)
    recipes_run.add_argument("--profile-id", required=True)
    recipes_run.add_argument("--recipe-id", required=True)
    recipes_run.add_argument("--language", choices=("en", "de"), default="en")
    recipes_run.add_argument("--confirm", required=True)
    recipes_run.add_argument("--approved-at", required=True)
    recipes_run.add_argument("--json", action="store_true", dest="as_json")

    app = commands.add_parser("app")
    app_commands = app.add_subparsers(dest="app_command", required=True)
    app_plan = app_commands.add_parser("plan")
    _add_local_app_arguments(app_plan)
    _add_strands_agent_arguments(app_plan)
    app_plan.add_argument("--json", action="store_true", dest="as_json")
    app_serve = app_commands.add_parser("serve")
    _add_local_app_arguments(app_serve)
    _add_strands_agent_arguments(app_serve)
    app_serve.add_argument("--approve-loopback-server", action="store_true")
    app_serve.add_argument("--json", action="store_true", dest="as_json")

    setup = commands.add_parser("setup")
    setup_commands = setup.add_subparsers(dest="setup_command", required=True)
    setup_plan = setup_commands.add_parser("plan")
    setup_serve = setup_commands.add_parser("serve")
    for parser_ in (setup_plan, setup_serve):
        parser_.add_argument("--profiles-dir", type=Path, required=True)
        parser_.add_argument("--config-dir", type=Path)
        parser_.add_argument("--port", type=int, default=8766)
        parser_.add_argument("--json", action="store_true", dest="as_json")
    setup_serve.add_argument("--approve-loopback-server", action="store_true")

    mcp = commands.add_parser("mcp")
    mcp_commands = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_plan = mcp_commands.add_parser("plan")
    mcp_plan.add_argument("--access-url")
    mcp_plan.add_argument("--json", action="store_true", dest="as_json")
    mcp_serve = mcp_commands.add_parser("serve")
    mcp_serve.add_argument("--access-url")
    mcp_serve.add_argument("--approve-mcp-server", action="store_true")

    folders = commands.add_parser("folders")
    folder_commands = folders.add_subparsers(dest="folders_command", required=True)
    folder_snapshot = folder_commands.add_parser("snapshot")
    folder_snapshot.add_argument("--source-dir", type=Path, required=True)
    folder_snapshot.add_argument("--captured-at", required=True)
    folder_snapshot.add_argument("--state-dir", type=Path, required=True)
    folder_snapshot.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    folder_snapshot.add_argument("--approve-state-write", action="store_true")
    folder_snapshot.add_argument("--json", action="store_true", dest="as_json")
    folder_diff = folder_commands.add_parser("diff")
    folder_diff.add_argument("--before-file", type=Path, required=True)
    folder_diff.add_argument("--after-file", type=Path, required=True)
    folder_diff.add_argument("--json", action="store_true", dest="as_json")
    folder_learning = folder_commands.add_parser("learning")
    folder_learning.add_argument("--before-file", type=Path, required=True)
    folder_learning.add_argument("--after-file", type=Path, required=True)
    folder_learning.add_argument("--receipts-file", type=Path, required=True)
    folder_learning.add_argument("--json", action="store_true", dest="as_json")
    folder_scan = folder_commands.add_parser("scan")
    folder_scan.add_argument("--config-file", type=Path, required=True)
    folder_scan.add_argument("--watch-id", required=True)
    folder_scan.add_argument("--captured-at", required=True)
    folder_scan.add_argument("--state-dir", type=Path, required=True)
    folder_scan.add_argument("--receipts-file", type=Path)
    folder_scan.add_argument("--approve-state-write", action="store_true")
    folder_scan.add_argument("--json", action="store_true", dest="as_json")
    cleanup_plan = folder_commands.add_parser("cleanup-plan")
    _add_cleanup_plan_arguments(cleanup_plan)
    cleanup_plan.add_argument("--output-file", type=Path)
    cleanup_plan.add_argument("--json", action="store_true", dest="as_json")
    cleanup_execute = folder_commands.add_parser("cleanup-execute")
    _add_cleanup_plan_arguments(cleanup_execute)
    cleanup_execute.add_argument("--approval-file", type=Path, required=True)
    cleanup_execute.add_argument("--state-dir", type=Path, required=True)
    cleanup_execute.add_argument("--approve-file-write", action="store_true")
    cleanup_execute.add_argument("--json", action="store_true", dest="as_json")
    routine_plan = folder_commands.add_parser("routine-plan")
    _add_routine_plan_arguments(routine_plan)
    routine_plan.add_argument("--output-file", type=Path)
    routine_plan.add_argument("--json", action="store_true", dest="as_json")
    routine_execute = folder_commands.add_parser("routine-execute")
    _add_routine_plan_arguments(routine_execute)
    routine_execute.add_argument("--approval-file", type=Path, required=True)
    routine_execute.add_argument("--completed-at", required=True)
    routine_execute.add_argument("--approve-file-write", action="store_true")
    routine_execute.add_argument("--approve-state-write", action="store_true")
    routine_execute.add_argument("--json", action="store_true", dest="as_json")
    routine_queue = folder_commands.add_parser("routine-queue")
    routine_queue.add_argument("--config-file", type=Path, required=True)
    routine_queue.add_argument("--bindings-file", type=Path, required=True)
    routine_queue.add_argument("--captured-at", required=True)
    routine_queue.add_argument("--state-dir", type=Path, required=True)
    routine_queue.add_argument("--profiles-dir", type=Path, required=True)
    routine_queue.add_argument("--as-of", type=date.fromisoformat, required=True)
    routine_queue.add_argument(
        "--manifest-root",
        type=Path,
        default=DEFAULT_MANIFEST_ROOT,
    )
    routine_queue.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    routine_queue.add_argument("--json", action="store_true", dest="as_json")
    scheduler = commands.add_parser("scheduler")
    scheduler_commands = scheduler.add_subparsers(
        dest="scheduler_command",
        required=True,
    )
    scheduler_plan = scheduler_commands.add_parser("plan")
    _add_scheduler_arguments(scheduler_plan)
    scheduler_plan.add_argument("--json", action="store_true", dest="as_json")
    scheduler_run = scheduler_commands.add_parser("run")
    _add_scheduler_arguments(scheduler_run)
    scheduler_run.add_argument("--schedule-id", required=True)
    scheduler_run.add_argument("--captured-at", default="auto")
    scheduler_run.add_argument(
        "--approve-scheduler-state-write",
        action="store_true",
    )
    scheduler_run.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _add_document_provider_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_doc_services: bool = False,
) -> None:
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--knowledge-digest-root",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DIGEST_PROVIDER_ROOT,
    )
    if include_doc_services:
        parser.add_argument(
            "--doc-services-root",
            type=Path,
            default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
        )


def _add_note_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_request: bool = False,
) -> None:
    if include_request:
        parser.add_argument("--request-file", type=Path, required=True)
        parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--provider-root",
        type=Path,
        default=DEFAULT_LLM_NOTE_PROVIDER_ROOT,
    )


def _add_tax_receipt_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--provider-root",
        type=Path,
        default=DEFAULT_TAX_ASSISTANT_PROVIDER_ROOT,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")


def _add_tax_export_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", required=True)
    parser.add_argument("--tax-year", type=int, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--provider-root",
        type=Path,
        default=DEFAULT_TAX_ASSISTANT_PROVIDER_ROOT,
    )


def _add_briefing_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--desktop-file", type=Path, required=True)
    parser.add_argument("--approve-sensitive-local-read", action="store_true")


def _add_notice_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--received-on")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    parser.add_argument(
        "--law-checker-root",
        type=Path,
        default=DEFAULT_LAW_CHECKER_PROVIDER_ROOT,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")


def _add_administrative_draft_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--designs-file", type=Path, required=True)
    parser.add_argument("--templates-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--received-on")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")


def _add_benefit_screening_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile-facts-file", type=Path, required=True)
    parser.add_argument("--catalog-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-source-age-days", type=int, default=30)
    parser.add_argument("--approve-sensitive-local-read", action="store_true")


def _add_legal_change_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--before-file", type=Path, required=True)
    parser.add_argument("--after-file", type=Path, required=True)
    parser.add_argument("--interests-file", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-source-age-days", type=int, default=30)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--law-checker-root",
        type=Path,
        default=DEFAULT_LAW_CHECKER_PROVIDER_ROOT,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--allow-test-fixture", action="store_true")


def _add_local_app_arguments(parser: argparse.ArgumentParser) -> None:
    # Values a launch config may supply use SUPPRESS, so an explicit flag always
    # wins: the attribute simply does not exist unless the caller passed it.
    parser.add_argument("--launch-config", type=Path)
    parser.add_argument("--profiles-dir", type=Path, default=argparse.SUPPRESS)
    parser.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    parser.add_argument("--resources-file", type=Path, default=argparse.SUPPRESS)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--knowledge-digest-root",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DIGEST_PROVIDER_ROOT,
    )
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    parser.add_argument(
        "--law-checker-root",
        type=Path,
        default=DEFAULT_LAW_CHECKER_PROVIDER_ROOT,
    )
    parser.add_argument(
        "--tax-assistant-root",
        type=Path,
        default=DEFAULT_TAX_ASSISTANT_PROVIDER_ROOT,
    )
    parser.add_argument(
        "--fcsa-root",
        type=Path,
        default=DEFAULT_FCSA_PROVIDER_ROOT,
    )
    parser.add_argument("--approve-mail-draft", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--max-body-bytes", type=int, default=65_536)
    parser.add_argument("--max-query-limit", type=int, default=50)
    parser.add_argument("--max-concurrent-requests", type=int, default=32)
    parser.add_argument("--request-timeout-seconds", type=float, default=5.0)


def _add_strands_agent_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model-provider",
        choices=("fixture", "bedrock", "ollama"),
        default=argparse.SUPPRESS,
    )
    parser.add_argument("--bedrock-model-id", default=argparse.SUPPRESS)
    parser.add_argument("--aws-region", default=argparse.SUPPRESS)
    parser.add_argument("--ollama-host", default=argparse.SUPPRESS)
    parser.add_argument("--ollama-model-id", default=argparse.SUPPRESS)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--approve-sensitive-cloud-data", action="store_true")
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--max-tool-calls", type=int, default=4)
    parser.add_argument("--max-prompt-chars", type=int, default=1_000)
    parser.add_argument("--max-response-chars", type=int, default=20_000)
    parser.add_argument("--max-tool-result-bytes", type=int, default=1_048_576)
    parser.add_argument("--max-output-tokens", type=int, default=4_096)
    parser.add_argument("--max-conversation-messages", type=int, default=24)
    parser.add_argument("--bedrock-connect-timeout-seconds", type=int, default=5)
    parser.add_argument("--bedrock-read-timeout-seconds", type=int, default=30)
    parser.add_argument(
        "--llm-note-root",
        type=Path,
        default=DEFAULT_LLM_NOTE_PROVIDER_ROOT,
    )


def _add_correspondence_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--designs-file", type=Path, required=True)
    parser.add_argument("--templates-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")


def _add_artifact_request_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")


def _add_action_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_cleanup_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_contact_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--approve-sensitive-local-read",
        action="store_true",
        help=(
            "Erlaubt ausschließlich lokale Kontaktextraktion aus Dokumenten mit "
            "Datenschutzstatus review_required."
        ),
    )
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_calendar_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--calendar-config", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--planned-at", required=True)
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_calendar_connector_arguments(parser: argparse.ArgumentParser) -> None:
    _add_calendar_plan_arguments(parser)
    parser.add_argument("--connector-accounts", type=Path, required=True)
    parser.add_argument("--connector-request", type=Path, required=True)
    parser.add_argument(
        "--uptoday-root",
        type=Path,
        default=DEFAULT_UPTODAY_PROVIDER_ROOT,
    )
    parser.add_argument("--use-synthetic-provider", action="store_true")


def _add_findcall_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--candidates-file", type=Path, required=True)
    parser.add_argument("--planned-at", required=True)


def _add_finance_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_inventory_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_medication_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--approve-sensitive-local-read", action="store_true")
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_routine_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--watch-id", required=True)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in FolderRoutineMode),
        default=FolderRoutineMode.CHANGES.value,
    )
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )


def _add_scheduler_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--interval-minutes", type=int, required=True)
    parser.add_argument("--start-at", required=True)
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--bindings-file", type=Path, required=True)
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument(
        "--doc-services-root",
        type=Path,
        default=DEFAULT_DOC_SERVICES_PROVIDER_ROOT,
    )
    parser.add_argument(
        "--python-executable",
        type=Path,
        default=Path(sys.executable),
    )
    parser.add_argument(
        "--working-directory",
        type=Path,
        default=REPOSITORY_ROOT,
    )


def _run_document_ingest(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.result_file, args.report_file)
        plugins = _document_plugins(args.manifest_root)
        extractor = DocServicesBridge(
            plugin=plugins["doc-services"],
            provider_root=args.doc_services_root,
        )
        indexer = KnowledgeDigestBridge(
            plugin=plugins["KnowledgeDigest"],
            provider_root=args.knowledge_digest_root,
            state_dir=args.state_dir,
        )
        result = ingest_folder(
            args.source_dir,
            extractor=extractor,
            indexer=indexer,
            allow_index_write=args.approve_index_write,
            recursive=args.recursive,
        )
        indexed_documents = tuple(
            item.document
            for item in result.items
            if item.document is not None and item.status.value == "indexed"
        )
        DocumentCatalogStore(args.state_dir).merge(indexed_documents)
        payload = result.to_dict()
        if args.result_file:
            _write_new_text(args.result_file, _json_text(payload))
        if args.report_file:
            report = build_folder_report(
                result,
                title=args.report_title,
                sentence_limit=args.sentence_limit,
            )
            _write_new_text(args.report_file, report.markdown)
    except (
        DocServicesBridgeError,
        DocumentCatalogError,
        FolderIngestGateError,
        FolderIngestResourceError,
        KnowledgeDigestBridgeError,
        ManifestValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 1 if result.failed else 0


def _run_document_search(args: argparse.Namespace) -> int:
    try:
        plugin = _document_plugins(args.manifest_root)["KnowledgeDigest"]
        bridge = KnowledgeDigestBridge(
            plugin=plugin,
            provider_root=args.knowledge_digest_root,
            state_dir=args.state_dir,
        )
        response = search_documents(args.query, searcher=bridge, limit=args.limit)
    except (KnowledgeDigestBridgeError, ManifestValidationError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(response.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_document_dossier(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plugin = _document_plugins(args.manifest_root)["KnowledgeDigest"]
        bridge = KnowledgeDigestBridge(
            plugin=plugin,
            provider_root=args.knowledge_digest_root,
            state_dir=args.state_dir,
        )
        dossier = build_theme_dossier(args.topic, searcher=bridge, limit=args.limit)
        payload = dossier.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, dossier.markdown)
    except (KnowledgeDigestBridgeError, ManifestValidationError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_document_versions(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plugins = _document_plugins(args.manifest_root)
        extractor = DocServicesBridge(
            plugin=plugins["doc-services"],
            provider_root=args.doc_services_root,
        )
        searcher = KnowledgeDigestBridge(
            plugin=plugins["KnowledgeDigest"],
            provider_root=args.knowledge_digest_root,
            state_dir=args.state_dir,
        )
        result = analyze_document_versions(
            args.query,
            catalog=DocumentCatalogStore(args.state_dir),
            searcher=searcher,
            extractor=extractor,
            limit=args.limit,
            archive_folder=args.archive_folder,
        )
        payload = result.to_dict()
        fcsa_bridge = FcsaDryRunBridge(
            plugin=plugins["file-collect-sort-action"],
            provider_root=args.fcsa_root,
        )
        fcsa_plans = validate_archive_proposals(
            result.archive_proposals,
            bridge=fcsa_bridge,
        )
        payload["schema"] = "folderhome.document-version-workflow.v1"
        payload["fcsa_archive_plans"] = [plan.to_dict() for plan in fcsa_plans]
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        ArchivePlanValidationError,
        DocumentCatalogError,
        DocumentVersionAnalysisError,
        KnowledgeDigestBridgeError,
        ManifestValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_document_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        action_plan = _prepare_document_action_plan(args)
        payload = action_plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        DocumentActionPlanError,
        ManifestValidationError,
        ProfileConfigurationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_document_execute(args: argparse.Namespace) -> int:
    try:
        action_plan = _prepare_document_action_plan(args)
        approval = ActionExecutionApproval(
            approval_id=args.approval_id,
            plan_id=args.approve_plan_id,
            action_ids=tuple(args.approved_action_ids),
            document_sha256=action_plan.document.source_sha256,
            approved_at=args.approved_at,
        )
        report = execute_document_actions(
            action_plan,
            approval,
            state_dir=args.state_dir,
            allow_file_write=args.approve_file_write,
        )
    except (
        DocServicesBridgeError,
        DocumentActionExecutionError,
        DocumentActionPlanError,
        ManifestValidationError,
        ProfileConfigurationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_document_undo(args: argparse.Namespace) -> int:
    try:
        report = read_action_execution_report(args.execution_file)
        approval = ActionUndoApproval(
            approval_id=args.approval_id,
            execution_id=args.approve_execution_id,
            document_sha256=args.document_sha256,
            approved_at=args.approved_at,
        )
        undo_report = undo_document_actions(
            report,
            approval,
            allow_file_write=args.approve_file_write,
        )
    except (DocumentActionExecutionError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(undo_report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_document_action_plan(args: argparse.Namespace):
    configuration = load_profile_configuration(args.profiles_dir)
    policy = resolve_profile_policy(
        configuration,
        profile_id=args.profile,
        area=args.area,
    )
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    document = extractor.extract(args.source_file)
    return build_document_action_plan(
        document,
        policy,
        target_root=args.target_root,
        as_of=args.as_of,
    )


def _run_document_bundle(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file, args.result_file)
        output_format = BundleFormat(args.format)
        extractor = DocServicesBridge(
            plugin=_plugin_by_id(args.manifest_root, "doc-services"),
            provider_root=args.doc_services_root,
        )
        documents = collect_bundle_documents(
            args.source_dir,
            output_path=args.output_file,
            output_format=output_format,
            extractor=extractor,
            recursive=args.recursive,
        )
        plan = plan_document_bundle(
            documents,
            source_root=args.source_dir,
            output_path=args.output_file,
            output_format=output_format,
        )
        result = (
            write_document_bundle(
                plan,
                documents,
                allow_output_write=True,
            )
            if args.approve_output_write
            else None
        )
        payload = {
            "schema": "folderhome.document-bundle-workflow.v1",
            "plan": plan.to_dict(),
            "result": result.to_dict() if result else None,
        }
        if args.result_file:
            _write_new_text(args.result_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        DocumentTransformError,
        ManifestValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_document_package(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_zip, args.result_file)
        extractor = DocServicesBridge(
            plugin=_plugin_by_id(args.manifest_root, "doc-services"),
            provider_root=args.doc_services_root,
        )
        prepared = prepare_folder_package(
            args.source_dir,
            output_zip=args.output_zip,
            extractor=extractor,
            recursive=args.recursive,
        )
        result = (
            write_folder_package(prepared, allow_output_write=True)
            if args.approve_output_write
            else None
        )
        payload = {
            "schema": "folderhome.document-package-workflow.v1",
            "plan": prepared.plan.to_dict(),
            "result": result.to_dict() if result else None,
        }
        if args.result_file:
            _write_new_text(args.result_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        DocumentPackageError,
        ManifestValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_profiles_validate(args: argparse.Namespace) -> int:
    try:
        configuration = load_profile_configuration(args.profiles_dir)
    except ProfileConfigurationError as exc:
        return _print_error(str(exc))
    payload = {
        "schema": "folderhome.profile-configuration.v1",
        "valid": True,
        "os_account": configuration.os_account,
        "organizational_only": True,
        "profiles": [profile.profile_id for profile in configuration.profiles],
        "common_rule_count": len(configuration.common_rules),
        "profile_rule_count": sum(
            len(profile.rules) for profile in configuration.profiles
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_profiles_resolve(args: argparse.Namespace) -> int:
    try:
        configuration = load_profile_configuration(args.profiles_dir)
        policy = resolve_profile_policy(
            configuration,
            profile_id=args.profile,
            area=args.area,
        )
    except ProfileConfigurationError as exc:
        return _print_error(str(exc))
    print(json.dumps(policy.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _add_resource_registry_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--resources-file",
        type=Path,
        default=default_resource_registry_path(),
    )
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")


def _load_configured_resources(args: argparse.Namespace):
    configuration = load_profile_configuration(args.profiles_dir)
    profile_ids = frozenset(profile.profile_id for profile in configuration.profiles)
    registry = load_resource_registry(
        args.resources_file,
        expected_os_account=configuration.os_account,
        known_profile_ids=profile_ids,
    )
    return configuration, registry


def _run_resources_validate(args: argparse.Namespace) -> int:
    try:
        configuration, registry = _load_configured_resources(args)
    except (OSError, ProfileConfigurationError, ResourceRegistryError) as exc:
        return _print_error(str(exc))
    payload = {
        "schema": "folderhome.resource-registry-validation.v1",
        "valid": True,
        "os_account": configuration.os_account,
        "profile_count": len(configuration.profiles),
        "resource_count": len(registry.resources),
        "paths_disclosed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_resources_catalog(args: argparse.Namespace) -> int:
    try:
        _, registry = _load_configured_resources(args)
        payload = registry.to_public_dict(profile_id=args.profile)
    except (OSError, ProfileConfigurationError, ResourceRegistryError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_contacts_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan, _ = _prepare_contact_register_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        ContactRegisterError,
        ContactWorkflowError,
        DocServicesBridgeError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_calendar_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan, _ = _prepare_calendar_handoff(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        CalendarStoreError,
        CalendarWorkflowError,
        DocServicesBridgeError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_calendar_apply(args: argparse.Namespace) -> int:
    try:
        plan, store = _prepare_calendar_handoff(args)
        approval = _read_calendar_approval(args.approval_file)
        report = apply_calendar_handoff_plan(
            plan,
            approval,
            store=store,
            allow_state_write=args.approve_state_write,
            allow_output_write=args.approve_output_write,
        )
    except (
        CalendarStoreError,
        CalendarWorkflowError,
        DocServicesBridgeError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_calendar_list(args: argparse.Namespace) -> int:
    try:
        store = CalendarStore(args.state_dir)
        events = store.list_events(
            profile_id=args.profile,
            area=args.area,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        payload = {
            "schema": "folderhome.calendar-list.v1",
            "calendar_revision": store.revision(),
            "count": len(events),
            "events": [event.to_dict() for event in events],
            "security_boundary": "operating_system_account",
        }
    except (CalendarStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_calendar_connectors(args: argparse.Namespace) -> int:
    payload = {
        "schema": "folderhome.calendar-connector-inventory.v1",
        "providers": [
            {
                "provider_id": "folderhome.local-calendar",
                "revision": "phase17",
                "role": "local_calendar_store",
                "status": "ready",
                "live_sync": False,
            },
            {
                "provider_id": "module:uptoday-ics",
                "revision": UPTODAY_REVISION,
                "role": "rfc5545_ics_file_handoff",
                "status": _calendar_provider_status(
                    args.uptoday_root,
                    UPTODAY_REVISION,
                ),
                "live_sync": False,
            },
            {
                "provider_id": "bundle:routinika",
                "revision": ROUTINIKA_BUNDLE_SHA256,
                "supporting_hashes": {
                    "exportformat_sha256": ROUTINIKA_EXPORTFORMAT_SHA256,
                    "readme_sha256": ROUTINIKA_README_SHA256,
                },
                "role": "hash_bound_bundle_reference",
                "status": "blocked_no_live_connector_contract",
                "live_sync": False,
            },
            {
                "provider_id": "skill:google-calendar",
                "revision": GOOGLE_CALENDAR_SKILL_REVISION,
                "role": "agentic_connector_handoff",
                "status": "review_required",
                "live_sync": True,
            },
            {
                "provider_id": "folderhome.synthetic-calendar",
                "revision": None,
                "role": "no_network_acceptance_gateway",
                "status": "ready",
                "live_sync": False,
            },
        ],
        "connector_invoked": False,
        "network_invoked": False,
        "live_calendar_written": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_calendar_connector_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan = _prepare_calendar_connector_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        CalendarConnectorError,
        CalendarStoreError,
        CalendarWorkflowError,
        DocServicesBridgeError,
        ManifestValidationError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_calendar_connector_simulate(args: argparse.Namespace) -> int:
    try:
        if not args.use_synthetic_provider or not args.approve_synthetic_calendar:
            raise CalendarConnectorError(
                "Synthetische Kalenderfreigabe fehlt; es wurde kein Connector ausgeführt."
            )
        plan = _prepare_calendar_connector_plan(args)
        planned_actions = tuple(item for item in plan.actions if item.status == "planned")
        approval = CalendarConnectorApproval(
            approval_id=args.approval_id,
            plan_id=plan.plan_id,
            plan_sha256=plan.plan_sha256,
            action_ids=tuple(item.action_id for item in planned_actions),
            allowed_operations=tuple(
                dict.fromkeys(item.operation for item in planned_actions)
            ),
            approved_at=args.approved_at,
            allow_network_write=False,
        )
        report = execute_calendar_connector_plan(
            plan,
            approval=approval,
            gateway=SyntheticCalendarConnectorGateway(),
        )
    except (
        CalendarConnectorError,
        CalendarStoreError,
        CalendarWorkflowError,
        DocServicesBridgeError,
        ManifestValidationError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_calendar_connector_plan(args: argparse.Namespace):
    if not args.approve_sensitive_local_read:
        raise PermissionError(
            "Sensitivitätsfreigabe fehlt; Kalenderconnectorkonfiguration wurde nicht gelesen."
        )
    handoff, _ = _prepare_calendar_handoff(args)
    request = load_calendar_connector_request(args.connector_request)
    accounts = load_calendar_connector_accounts(args.connector_accounts)
    account = next(
        (item for item in accounts if item.account_id == request.account_id),
        None,
    )
    if account is None:
        raise CalendarConnectorError(f"Unbekanntes Kalenderkonto: {request.account_id}")
    provider_ready = _calendar_account_provider_ready(account, args.uptoday_root)
    return build_calendar_connector_plan(
        handoff,
        request=request,
        account=account,
        provider_ready=provider_ready,
        synthetic_override=args.use_synthetic_provider,
    )


def _calendar_account_provider_ready(account, uptoday_root: Path) -> bool:
    if account.backend is CalendarBackend.FOLDERHOME_LOCAL:
        return True
    if account.backend is CalendarBackend.UPTODAY_ICS:
        return (
            account.provider_id == "module:uptoday-ics"
            and account.provider_revision == UPTODAY_REVISION
            and _calendar_provider_status(uptoday_root, UPTODAY_REVISION) == "ready"
        )
    if account.backend is CalendarBackend.GOOGLE:
        return (
            account.provider_id == "skill:google-calendar"
            and account.provider_revision == GOOGLE_CALENDAR_SKILL_REVISION
        )
    return False


def _calendar_provider_status(provider_root: Path, revision: str) -> str:
    try:
        verify_checkout_revision(provider_root, revision)
    except ProviderCheckoutError:
        return "blocked_checkout_unavailable_or_dirty"
    return "ready"


def _prepare_calendar_handoff(
    args: argparse.Namespace,
) -> tuple[CalendarHandoffPlan, CalendarStore]:
    _ensure_calendar_paths_separate(args.source_dir, args.state_dir)
    configuration = load_calendar_configuration(args.calendar_config)
    policy = resolve_profile_policy(
        load_profile_configuration(args.profiles_dir),
        profile_id=args.profile,
        area=args.area,
    )
    _, _, timezone, _ = resolve_calendar_preferences(configuration, policy)
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    analysis = analyze_folder_calendar(
        args.source_dir,
        profile_id=args.profile,
        area=args.area,
        default_timezone=timezone,
        extractor=extractor,
        recursive=args.recursive,
        allow_sensitive_local_read=args.approve_sensitive_local_read,
    )
    store = CalendarStore(args.state_dir)
    return (
        build_calendar_handoff_plan(
            analysis,
            configuration=configuration,
            policy=policy,
            planned_at=args.planned_at,
            calendar_revision=store.revision(),
            existing_events=store.list_events(),
        ),
        store,
    )


def _ensure_calendar_paths_separate(source_dir: Path, state_dir: Path) -> None:
    source = source_dir.resolve()
    state = state_dir.resolve()
    if source == state or source.is_relative_to(state) or state.is_relative_to(source):
        raise CalendarWorkflowError(
            "Dokumentenordner und Kalender-State dürfen sich nicht überlappen."
        )


def _run_findcall_plugins(args: argparse.Namespace) -> int:
    try:
        plugins = {plugin.plugin_id: plugin for plugin in load_manifests(args.manifest_root)}
        results = tuple(
            CallPluginBridge(plugin=plugins[plugin_id], provider_root=provider_root).probe()
            for plugin_id, provider_root in (
                ("hungrycall", args.hungrycall_root),
                ("ringedingeding", args.ringedingeding_root),
            )
        )
        payload = {
            "schema": "folderhome.call-plugin-inventory.v1",
            "plugins": [result.to_dict() for result in results],
            "live_invoked": False,
            "network_used": False,
            "phone_calls_placed": False,
        }
    except (CallPluginBridgeError, KeyError, ManifestValidationError, OSError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_findcall_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan = _prepare_findcall_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (FindCallWorkflowError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_findcall_simulate(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_findcall_plan(args)
        provider = SyntheticFindCallProvider(_read_findcall_fixtures(args.fixture_file))
        report = run_findcall_dry_run(plan, provider=provider)
    except (FindCallWorkflowError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_findcall_plan(args: argparse.Namespace) -> FindCallPlan:
    request = _read_findcall_request(args.request_file)
    candidates = _read_findcall_candidates(args.candidates_file)
    return build_findcall_plan(request, candidates, planned_at=args.planned_at)


def _read_findcall_request(path: Path):
    payload = _read_findcall_payload(
        path,
        schema="folderhome.findcall-request-input.v1",
        label="FindCall-Auftrag",
    )
    raw_windows = payload.get("windows")
    if not isinstance(raw_windows, list):
        raise FindCallWorkflowError("FindCall-Auftrag benötigt eine windows-Liste.")
    try:
        windows = tuple(
            FindCallWindow(
                start_at=_findcall_text(item, "start_at"),
                end_at=_findcall_text(item, "end_at"),
            )
            for item in raw_windows
            if isinstance(item, dict)
        )
        if len(windows) != len(raw_windows):
            raise ValueError("windows enthält einen ungültigen Eintrag.")
        return build_findcall_request(
            profile_id=_findcall_text(payload, "profile_id"),
            area=_findcall_text(payload, "area"),
            kind=FindCallKind(_findcall_text(payload, "kind")),
            service=_findcall_text(payload, "service"),
            location=_findcall_text(payload, "location"),
            windows=windows,
            max_distance_km=_optional_number(payload, "max_distance_km"),
            max_price_eur=_optional_number(payload, "max_price_eur"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FindCallWorkflowError(f"FindCall-Auftrag ist ungültig: {exc}") from exc


def _read_findcall_candidates(path: Path) -> tuple[FindCallCandidate, ...]:
    payload = _read_findcall_payload(
        path,
        schema="folderhome.findcall-candidates.v1",
        label="FindCall-Kandidaten",
    )
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list):
        raise FindCallWorkflowError("FindCall-Kandidaten benötigen eine candidates-Liste.")
    candidates = []
    try:
        for item in raw_candidates:
            if not isinstance(item, dict):
                raise ValueError("Kandidat muss ein JSON-Objekt sein.")
            services = item.get("services")
            if not isinstance(services, list) or not all(
                isinstance(service, str) for service in services
            ):
                raise ValueError("Kandidat benötigt eine services-Textliste.")
            priority = item.get("priority", 0)
            if not isinstance(priority, int) or isinstance(priority, bool):
                raise ValueError("priority muss eine Ganzzahl sein.")
            candidates.append(
                FindCallCandidate(
                    candidate_id=_findcall_text(item, "candidate_id"),
                    name=_findcall_text(item, "name"),
                    phone_e164=_findcall_text(item, "phone_e164"),
                    services=tuple(services),
                    distance_km=_optional_number(item, "distance_km"),
                    priority=priority,
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise FindCallWorkflowError(f"FindCall-Kandidaten sind ungültig: {exc}") from exc
    return tuple(candidates)


def _read_findcall_fixtures(path: Path) -> dict[str, FindCallFixtureOutcome]:
    payload = _read_findcall_payload(
        path,
        schema="folderhome.findcall-fixtures.v1",
        label="FindCall-Fixtures",
    )
    raw_outcomes = payload.get("outcomes")
    if not isinstance(raw_outcomes, dict):
        raise FindCallWorkflowError("FindCall-Fixtures benötigen ein outcomes-Objekt.")
    outcomes = {}
    try:
        for candidate_id, item in raw_outcomes.items():
            if not isinstance(candidate_id, str) or not isinstance(item, dict):
                raise ValueError("Fixture-Eintrag ist ungültig.")
            raw_window = item.get("offered_window")
            if raw_window is not None and not isinstance(raw_window, dict):
                raise ValueError("offered_window muss ein Objekt oder null sein.")
            offered_window = (
                FindCallWindow(
                    start_at=_findcall_text(raw_window, "start_at"),
                    end_at=_findcall_text(raw_window, "end_at"),
                )
                if raw_window is not None
                else None
            )
            outcomes[candidate_id] = FindCallFixtureOutcome(
                status=FindCallStatus(_findcall_text(item, "status")),
                service_confirmed=_findcall_bool(item, "service_confirmed"),
                available=_findcall_bool(item, "available"),
                offered_window=offered_window,
                price_known=_findcall_bool(item, "price_known"),
                price_eur=_optional_number(item, "price_eur"),
                commitment_made=_findcall_bool(item, "commitment_made"),
                summary=_findcall_text(item, "summary"),
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise FindCallWorkflowError(f"FindCall-Fixtures sind ungültig: {exc}") from exc
    return outcomes


def _read_findcall_payload(path: Path, *, schema: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FindCallWorkflowError(f"{label} sind nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise FindCallWorkflowError(f"{label} verwenden ein unbekanntes Schema.")
    return payload


def _findcall_text(payload: dict[str, object], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} muss ein nichtleerer Text sein.")
    return value.strip()


def _findcall_bool(payload: dict[str, object], field: str) -> bool:
    value = payload[field]
    if not isinstance(value, bool):
        raise ValueError(f"{field} muss boolesch sein.")
    return value


def _optional_number(payload: dict[str, object], field: str) -> float | None:
    value = payload.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} muss eine Zahl oder null sein.")
    return float(value)


def _run_finance_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan, _ = _prepare_finance_import_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        FinanceStoreError,
        FinanceWorkflowError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_finance_apply(args: argparse.Namespace) -> int:
    try:
        plan, store = _prepare_finance_import_plan(args)
        approval = _read_finance_approval(args.approval_file)
        report = apply_finance_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=args.approve_state_write,
        )
    except (
        DocServicesBridgeError,
        FinanceStoreError,
        FinanceWorkflowError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_finance_transactions(args: argparse.Namespace) -> int:
    try:
        store = FinanceStore(args.state_dir)
        transactions = store.list_transactions(
            profile_id=args.profile,
            account_ref=args.account,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        payload = {
            "schema": "folderhome.finance-transaction-list.v1",
            "finance_revision": store.revision(),
            "count": len(transactions),
            "transactions": [item.to_dict() for item in transactions],
            "bank_access_performed": False,
        }
    except (FinanceStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_finance_coverage(args: argparse.Namespace) -> int:
    try:
        coverage = FinanceStore(args.state_dir).coverage(
            account_ref=args.account,
            date_from=args.date_from,
            date_to=args.date_to,
        )
    except (FinanceStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(coverage.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_finance_period(args: argparse.Namespace) -> int:
    try:
        report = FinanceStore(args.state_dir).period_report(
            account_ref=args.account,
            date_from=args.date_from,
            date_to=args.date_to,
        )
    except (FinanceStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_finance_recurring(args: argparse.Namespace) -> int:
    try:
        report = build_recurring_cost_report(
            store=FinanceStore(args.state_dir),
            profile_id=args.profile,
            as_of=args.as_of,
        )
    except (FinanceStoreError, FinanceWorkflowError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_finance_import_plan(
    args: argparse.Namespace,
) -> tuple[FinanceImportPlan, FinanceStore]:
    _ensure_finance_paths_separate(args.source_dir, args.state_dir)
    configuration = load_profile_configuration(args.profiles_dir)
    if args.profile not in {profile.profile_id for profile in configuration.profiles}:
        raise FinanceWorkflowError(f"Unbekanntes Profil: {args.profile}")
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    analysis = analyze_folder_statements(
        args.source_dir,
        profile_id=args.profile,
        extractor=extractor,
        recursive=args.recursive,
        allow_sensitive_local_read=args.approve_sensitive_local_read,
    )
    store = FinanceStore(args.state_dir)
    return build_finance_import_plan(analysis, store=store), store


def _ensure_finance_paths_separate(source_dir: Path, state_dir: Path) -> None:
    source = source_dir.resolve()
    state = state_dir.resolve()
    if source == state or source.is_relative_to(state) or state.is_relative_to(source):
        raise FinanceWorkflowError(
            "Auszugsordner und Finanz-State dürfen sich nicht überlappen."
        )


def _read_finance_approval(path: Path) -> FinanceImportApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinanceWorkflowError(f"Finanzfreigabe ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        FinanceImportApproval.SCHEMA
    ):
        raise FinanceWorkflowError("Finanzfreigabe verwendet ein unbekanntes Schema.")
    raw_action_ids = payload.get("action_ids")
    if not isinstance(raw_action_ids, list) or not all(
        isinstance(action_id, str) for action_id in raw_action_ids
    ):
        raise FinanceWorkflowError("Finanzfreigabe benötigt gültige action_ids.")
    try:
        return FinanceImportApproval(
            approval_id=_findcall_text(payload, "approval_id"),
            plan_id=_findcall_text(payload, "plan_id"),
            finance_revision=_findcall_text(payload, "finance_revision"),
            action_ids=tuple(raw_action_ids),
            approved_at=_findcall_text(payload, "approved_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FinanceWorkflowError(f"Finanzfreigabe ist ungültig: {exc}") from exc


def _run_inventory_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan, _ = _prepare_inventory_import_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        InventoryStoreError,
        InventoryWorkflowError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_inventory_apply(args: argparse.Namespace) -> int:
    try:
        plan, store = _prepare_inventory_import_plan(args)
        approval = _read_inventory_approval(args.approval_file)
        report = apply_inventory_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=args.approve_state_write,
        )
    except (
        DocServicesBridgeError,
        InventoryStoreError,
        InventoryWorkflowError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_inventory_current(args: argparse.Namespace) -> int:
    try:
        if args.as_of is not None:
            date.fromisoformat(args.as_of)
        store = InventoryStore(args.state_dir)
        items = store.current_items(
            profile_id=args.profile,
            area=args.area,
            as_of=args.as_of,
        )
        payload = {
            "schema": "folderhome.inventory-current-list.v1",
            "inventory_revision": store.revision(),
            "profile_id": args.profile,
            "area": args.area,
            "as_of": args.as_of,
            "count": len(items),
            "items": [item.to_dict() for item in items],
            "complete_inventory_claimed": False,
        }
    except (InventoryStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_inventory_history(args: argparse.Namespace) -> int:
    try:
        store = InventoryStore(args.state_dir)
        events = store.list_events(
            profile_id=args.profile,
            area=args.area,
            item_id=args.item_id,
        )
        payload = {
            "schema": "folderhome.inventory-history.v1",
            "inventory_revision": store.revision(),
            "profile_id": args.profile,
            "area": args.area,
            "item_id": args.item_id,
            "count": len(events),
            "events": [item.to_dict() for item in events],
            "append_only": True,
        }
    except (InventoryStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_inventory_needs(args: argparse.Namespace) -> int:
    try:
        report = build_inventory_needs_report(
            store=InventoryStore(args.state_dir),
            profile_id=args.profile,
            as_of=args.as_of,
            expiry_horizon_days=args.expiry_horizon_days,
        )
    except (InventoryStoreError, InventoryWorkflowError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_inventory_import_plan(
    args: argparse.Namespace,
) -> tuple[InventoryImportPlan, InventoryStore]:
    _ensure_inventory_paths_separate(args.source_dir, args.state_dir)
    configuration = load_profile_configuration(args.profiles_dir)
    if args.profile not in {profile.profile_id for profile in configuration.profiles}:
        raise InventoryWorkflowError(f"Unbekanntes Profil: {args.profile}")
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    analysis = analyze_folder_inventory(
        args.source_dir,
        profile_id=args.profile,
        extractor=extractor,
        recursive=args.recursive,
        allow_sensitive_local_read=args.approve_sensitive_local_read,
    )
    store = InventoryStore(args.state_dir)
    return build_inventory_import_plan(analysis, store=store), store


def _ensure_inventory_paths_separate(source_dir: Path, state_dir: Path) -> None:
    source = source_dir.resolve()
    state = state_dir.resolve()
    if source == state or source.is_relative_to(state) or state.is_relative_to(source):
        raise InventoryWorkflowError(
            "Bestandsordner und Inventar-State dürfen sich nicht überlappen."
        )


def _read_inventory_approval(path: Path) -> InventoryImportApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryWorkflowError(f"Inventarfreigabe ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        InventoryImportApproval.SCHEMA
    ):
        raise InventoryWorkflowError("Inventarfreigabe verwendet ein unbekanntes Schema.")
    raw_action_ids = payload.get("action_ids")
    if not isinstance(raw_action_ids, list) or not all(
        isinstance(action_id, str) for action_id in raw_action_ids
    ):
        raise InventoryWorkflowError("Inventarfreigabe benötigt gültige action_ids.")
    try:
        return InventoryImportApproval(
            approval_id=_findcall_text(payload, "approval_id"),
            plan_id=_findcall_text(payload, "plan_id"),
            inventory_revision=_findcall_text(payload, "inventory_revision"),
            action_ids=tuple(raw_action_ids),
            approved_at=_findcall_text(payload, "approved_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InventoryWorkflowError(f"Inventarfreigabe ist ungültig: {exc}") from exc


def _run_medication_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan, _ = _prepare_medication_import_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        ManifestValidationError,
        MedicationStoreError,
        MedicationWorkflowError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_medication_apply(args: argparse.Namespace) -> int:
    try:
        plan, store = _prepare_medication_import_plan(args)
        approval = _read_medication_approval(args.approval_file)
        report = apply_medication_import_plan(
            plan,
            approval,
            store=store,
            allow_state_write=args.approve_state_write,
        )
    except (
        DocServicesBridgeError,
        ManifestValidationError,
        MedicationStoreError,
        MedicationWorkflowError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_medication_day(args: argparse.Namespace) -> int:
    try:
        inventory_store = (
            InventoryStore(args.inventory_state_dir)
            if args.inventory_state_dir is not None
            else None
        )
        report = build_medication_day_report(
            store=MedicationStore(args.state_dir),
            inventory_store=inventory_store,
            profile_id=args.profile,
            on_date=args.date,
            as_of=args.as_of,
        )
    except (
        InventoryStoreError,
        MedicationStoreError,
        MedicationWorkflowError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_medication_confirm(args: argparse.Namespace) -> int:
    try:
        confirmation = _read_medication_confirmation(args.confirmation_file)
        report = confirm_medication_intake(
            confirmation,
            store=MedicationStore(args.state_dir),
            allow_state_write=args.approve_state_write,
        )
    except (MedicationStoreError, MedicationWorkflowError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_medication_history(args: argparse.Namespace) -> int:
    try:
        store = MedicationStore(args.state_dir)
        schedules = store.list_schedules(profile_id=args.profile)
        intake_events = store.list_intake_events(profile_id=args.profile)
        payload = {
            "schema": "folderhome.medication-history.v1",
            "medication_revision": store.revision(),
            "profile_id": args.profile,
            "schedules": [item.to_dict() for item in schedules],
            "intake_events": [item.to_dict() for item in intake_events],
            "append_only": True,
            "medical_advice": False,
        }
    except (MedicationStoreError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_health_dossier(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_markdown, args.output_json)
        _ensure_health_outputs_outside_source(
            args.source_dir,
            args.output_markdown,
            args.output_json,
        )
        configuration = load_profile_configuration(args.profiles_dir)
        if args.profile not in {
            profile.profile_id for profile in configuration.profiles
        }:
            raise ValueError(f"Unbekanntes Profil: {args.profile}")
        extractor = DocServicesBridge(
            plugin=_plugin_by_id(args.manifest_root, "doc-services"),
            provider_root=args.doc_services_root,
        )
        report = build_health_dossier(
            args.source_dir,
            profile_id=args.profile,
            as_of=args.as_of,
            extractor=extractor,
            allow_sensitive_local_read=args.approve_sensitive_local_read,
            recursive=args.recursive,
            gap_threshold_days=args.gap_threshold_days,
        )
        payload = report.to_dict()
        if args.output_markdown:
            _write_new_text(args.output_markdown, report.markdown)
        if args.output_json:
            _write_new_text(args.output_json, _json_text(payload))
    except (
        DocServicesBridgeError,
        HealthDossierGateError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _ensure_health_outputs_outside_source(
    source_dir: Path,
    *outputs: Path | None,
) -> None:
    source = source_dir.resolve()
    for output in outputs:
        if output is not None and output.resolve().is_relative_to(source):
            raise ValueError(
                "Dossier-Ausgaben müssen außerhalb des analysierten Quellordners liegen."
            )


def _run_contract_cockpit(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_markdown, args.output_json)
        _ensure_outputs_outside_root(
            args.state_dir,
            args.output_markdown,
            args.output_json,
            label="Cockpit-Ausgaben müssen außerhalb des State-Verzeichnisses liegen.",
        )
        request = _read_contract_cockpit_request(args.request_file)
        configuration = load_profile_configuration(args.profiles_dir)
        if request.profile_id not in {
            profile.profile_id for profile in configuration.profiles
        }:
            raise ValueError(f"Unbekanntes Profil: {request.profile_id}")
        if not args.approve_sensitive_local_read:
            raise PermissionError(
                "Sensitivitätsfreigabe fehlt; Vertragszustände wurden nicht gelesen."
            )
        plugins = _document_plugins(args.manifest_root)
        extractor = DocServicesBridge(
            plugin=plugins["doc-services"],
            provider_root=args.doc_services_root,
        )
        searcher = KnowledgeDigestBridge(
            plugin=plugins["KnowledgeDigest"],
            provider_root=args.knowledge_digest_root,
            state_dir=args.state_dir,
        )
        version_analysis = analyze_document_versions(
            request.document_query,
            catalog=DocumentCatalogStore(args.state_dir),
            searcher=searcher,
            extractor=extractor,
        )
        contact_store = ContactRegisterStore(args.state_dir)
        contacts = contact_store.list_contacts(
            profile_id=request.profile_id,
            area=request.area,
            object_query=request.object_ref,
            include_deletion_candidates=True,
        )
        finance_store = FinanceStore(args.state_dir)
        recurring_report = build_recurring_cost_report(
            store=finance_store,
            profile_id=request.profile_id,
            as_of=request.as_of,
        )
        coverages = tuple(
            finance_store.coverage(
                account_ref=account_ref,
                date_from=request.coverage_start,
                date_to=request.as_of,
            )
            for account_ref in request.account_refs
        )
        calendar_store = CalendarStore(args.state_dir)
        events = calendar_store.list_events(
            profile_id=request.profile_id,
            area=request.area,
            date_from=request.as_of,
        )
        report = build_contract_cockpit(
            request,
            version_analysis=version_analysis,
            contacts=contacts,
            recurring_report=recurring_report,
            calendar_events=events,
            finance_coverages=coverages,
            component_revisions={
                "contacts": contact_store.revision(),
                "finance": finance_store.revision(),
                "calendar": calendar_store.revision(),
                "document_family": version_analysis.family.family_id,
            },
        )
        payload = report.to_dict()
        if args.output_markdown:
            _write_new_text(args.output_markdown, report.markdown)
        if args.output_json:
            _write_new_text(args.output_json, _json_text(payload))
    except (
        CalendarStoreError,
        ContactRegisterError,
        DocServicesBridgeError,
        DocumentCatalogError,
        DocumentVersionAnalysisError,
        FinanceStoreError,
        FinanceWorkflowError,
        KnowledgeDigestBridgeError,
        ManifestValidationError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_correspondence_preview(args: argparse.Namespace) -> int:
    try:
        preview = _prepare_correspondence_preview(args)
    except (
        CorrespondenceError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(preview.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_correspondence_render(args: argparse.Namespace) -> int:
    try:
        if not args.approve_output_write:
            raise CorrespondenceError(
                "Output-Freigabe fehlt; es wurde kein Brief geschrieben."
            )
        _preflight_new_outputs(args.markdown_file, args.text_file)
        preview = _prepare_correspondence_preview(args)
        report = write_correspondence_outputs(
            preview,
            markdown_file=args.markdown_file,
            text_file=args.text_file,
            allow_output_write=True,
        )
    except (
        CorrespondenceError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_correspondence_preview(args: argparse.Namespace):
    if not args.approve_sensitive_local_read:
        raise PermissionError(
            "Sensitivitätsfreigabe fehlt; Korrespondenzanfrage wurde nicht gelesen."
        )
    configuration = load_correspondence_configuration(
        args.designs_file,
        args.templates_file,
    )
    request = load_correspondence_request(args.request_file)
    profiles = load_profile_configuration(args.profiles_dir)
    if request.profile_id not in {profile.profile_id for profile in profiles.profiles}:
        raise CorrespondenceError(f"Unbekanntes Profil: {request.profile_id}")
    return build_correspondence_preview(
        request,
        configuration=configuration,
        report_forge_revision=REPORT_FORGE_REVISION,
        report_forge_distribution_version=REPORT_FORGE_DISTRIBUTION_VERSION,
        report_forge_runtime_version=REPORT_FORGE_RUNTIME_VERSION,
    )


def _run_artifacts_plan(args: argparse.Namespace) -> int:
    try:
        request = _prepare_artifact_request(args)
        media_clean = True
        try:
            verify_checkout_revision(
                DEFAULT_AI_MEDIA_EDITOR_ROOT,
                AI_MEDIA_EDITOR_REVISION,
            )
        except ProviderCheckoutError:
            media_clean = False
        plan = build_artifact_studio_plan(
            request,
            office_visual_renderer_available=bool(
                shutil.which("soffice") or shutil.which("libreoffice")
            ),
            spreadsheet_workspace_loader_available=(
                SPREADSHEET_WORKSPACE_LOADER_BOUND
            ),
            ai_media_editor_revision=AI_MEDIA_EDITOR_REVISION,
            ai_media_editor_clean=media_clean,
            ai_media_editor_tests_passed=AI_MEDIA_EDITOR_TESTS_PASSED,
        )
    except (
        ArtifactStudioError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_artifacts_design_preview(args: argparse.Namespace) -> int:
    try:
        preview = _prepare_design_preview(args)
    except (
        ArtifactStudioError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(preview.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_artifacts_design_render(args: argparse.Namespace) -> int:
    try:
        if not args.approve_output_write:
            raise ArtifactStudioError(
                "Output-Freigabe fehlt; Designset wurde nicht geschrieben."
            )
        _preflight_new_outputs(
            args.json_file,
            args.css_file,
            args.business_card_file,
        )
        preview = _prepare_design_preview(args)
        report = write_design_outputs(
            preview,
            json_file=args.json_file,
            css_file=args.css_file,
            business_card_file=args.business_card_file,
            allow_output_write=True,
        )
    except (
        ArtifactStudioError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_artifact_request(args: argparse.Namespace):
    _require_artifact_sensitive_gate(args)
    request = load_artifact_request(args.request_file)
    _require_known_profile(request.profile_id, args.profiles_dir)
    return request


def _prepare_design_preview(args: argparse.Namespace):
    _require_artifact_sensitive_gate(args)
    request = load_design_request(args.request_file)
    _require_known_profile(request.profile_id, args.profiles_dir)
    return build_design_preview(request)


def _require_artifact_sensitive_gate(args: argparse.Namespace) -> None:
    if not args.approve_sensitive_local_read:
        raise PermissionError(
            "Sensitivitätsfreigabe fehlt; Artefaktanfrage wurde nicht gelesen."
        )


def _require_known_profile(profile_id: str, profiles_dir: Path) -> None:
    configuration = load_profile_configuration(profiles_dir)
    if profile_id not in {profile.profile_id for profile in configuration.profiles}:
        raise ArtifactStudioError(f"Unbekanntes Profil: {profile_id}")


def _run_mail_providers(args: argparse.Namespace) -> int:
    providers = [
        {
            "provider_id": "mailprocessor",
            "repository": "https://github.com/doc-bricks/MailProcessor",
            "revision": MAILPROCESSOR_REVISION,
            "version": "0.1.0",
            "role": "suite_launcher",
            "runtime_connector": False,
            "status": "reference_only",
        },
        {
            "provider_id": "universal-docs-grabber",
            "repository": "https://github.com/doc-bricks/UniversalDocsGrabber",
            "revision": UNIVERSAL_DOCS_GRABBER_REVISION,
            "version": "1.1.4",
            "role": "read_only_imap_document_ingest",
            "runtime_connector": True,
            "status": _mail_provider_status(
                DEFAULT_DOCS_GRABBER_ROOT,
                UNIVERSAL_DOCS_GRABBER_REVISION,
            ),
        },
        {
            "provider_id": "universal-mail-cleaner",
            "repository": "https://github.com/doc-bricks/UniversalMailCleaner",
            "revision": UNIVERSAL_MAIL_CLEANER_REVISION,
            "version": "1.2.0",
            "role": "mailbox_mutation_excluded_from_ingest",
            "runtime_connector": False,
            "status": "separate_gated_component",
        },
        {
            "provider_id": "universal-invoice-mail",
            "repository": "https://github.com/doc-bricks/UniversalInvoiceMail",
            "revision": UNIVERSAL_INVOICE_MAIL_REVISION,
            "version": "2.3.0",
            "role": "specialized_invoice_ingest_reference",
            "runtime_connector": False,
            "status": "reference_only",
        },
        {
            "provider_id": "folderhome.synthetic-mail",
            "repository": "local://folderhome",
            "revision": "working-tree",
            "version": "0.26.0",
            "role": "no_network_acceptance_gateway",
            "runtime_connector": True,
            "status": "ready",
        },
    ]
    payload = {
        "schema": "folderhome.mail-provider-inventory.v1",
        "providers": providers,
        "smtp_live_transport": "not_implemented",
        "mailbox_mutations_in_ingest": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_mail_ingest_plan(args: argparse.Namespace) -> int:
    try:
        if not args.approve_sensitive_local_read:
            raise PermissionError(
                "Sensitivitätsfreigabe fehlt; Mailkonfiguration wurde nicht gelesen."
            )
        request = load_mail_ingest_request(args.request_file)
        accounts = load_mail_accounts(args.accounts_file)
        _require_known_profile(request.profile_id, args.profiles_dir)
        account = next(
            (item for item in accounts if item.account_id == request.account_id),
            None,
        )
        if account is None:
            raise MailConnectorError(f"Unbekanntes Mailkonto: {request.account_id}")
        if args.use_synthetic_provider:
            plan = build_mail_ingest_plan(
                request,
                account=account,
                provider_ready=True,
                provider_id="folderhome.synthetic-mail",
                provider_revision=None,
            )
        else:
            provider_ready = False
            if (
                account.inbound.provider_id == "universal-docs-grabber"
                and account.inbound.provider_revision
                == UNIVERSAL_DOCS_GRABBER_REVISION
            ):
                provider_ready = (
                    _mail_provider_status(
                        args.provider_root,
                        UNIVERSAL_DOCS_GRABBER_REVISION,
                    )
                    == "ready"
                )
            plan = build_mail_ingest_plan(
                request,
                account=account,
                provider_ready=provider_ready,
            )
    except (
        MailConnectorError,
        OSError,
        PermissionError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _mail_provider_status(provider_root: Path, revision: str) -> str:
    try:
        verify_checkout_revision(provider_root, revision)
    except ProviderCheckoutError:
        return "blocked_checkout_unavailable_or_dirty"
    return "ready"


def _run_note_providers(args: argparse.Namespace) -> int:
    try:
        plugin = _plugin_by_id(args.manifest_root, "llm-note")
        load_pinned_python_modules(
            plugin=plugin,
            provider_root=args.provider_root,
            package_name="llm_note",
        )
        status = "ready"
        reason = "Gepinnter sauberer Checkout und Paketversion wurden bestätigt."
    except (
        LlmNoteBridgeError,
        ManifestValidationError,
        ProviderCheckoutError,
        ValueError,
    ) as exc:
        status = "blocked"
        reason = str(exc)
        plugin = None
    payload = {
        "schema": "folderhome.personal-note-provider-inventory.v1",
        "storage_provider": {
            "provider_id": "llm-note",
            "version": plugin.version if plugin else "unknown",
            "revision": plugin.source_revision if plugin else None,
            "repository": plugin.source_repository if plugin else None,
            "status": status,
            "reason": reason,
            "network_required": False,
            "source_code_copied": False,
        },
        "guidance_provider": {
            "provider_id": SyntheticPersonalNoteGuide.provider_id,
            "revision": SyntheticPersonalNoteGuide.provider_revision,
            "status": "ready",
            "network_required": False,
        },
        "remote_llm_invoked": False,
        "external_sync_invoked": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if status == "ready" else 2


def _run_note_guide(args: argparse.Namespace) -> int:
    try:
        plan, _ = _prepare_note_plan(args)
    except (
        LlmNoteBridgeError,
        ManifestValidationError,
        PersonalNoteWorkflowError,
        ProfileConfigurationError,
        ProviderCheckoutError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_note_apply(args: argparse.Namespace) -> int:
    try:
        plan, store = _prepare_note_plan(args)
        approval = _read_note_approval(args.approval_file)
        report = apply_personal_note_plan(
            plan,
            approval,
            store=store,
            allow_state_write=args.approve_state_write,
        )
    except (
        LlmNoteBridgeError,
        ManifestValidationError,
        PersonalNoteWorkflowError,
        ProfileConfigurationError,
        ProviderCheckoutError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_note_list(args: argparse.Namespace) -> int:
    try:
        store = _note_store(args)
        notes = store.list_current(
            profile_id=args.profile,
            area=args.area,
            notebook_id=args.notebook,
        )
    except (LlmNoteBridgeError, ManifestValidationError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    payload = {
        "schema": "folderhome.personal-note-list.v1",
        "profile_id": args.profile,
        "area": args.area,
        "notebook_id": args.notebook,
        "notes": [item.to_dict() for item in notes],
        "os_account_is_security_boundary": True,
        "profile_is_security_boundary": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_note_history(args: argparse.Namespace) -> int:
    try:
        store = _note_store(args)
        history = store.history(args.note_id)
    except (LlmNoteBridgeError, ManifestValidationError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    payload = {
        "schema": "folderhome.personal-note-history.v1",
        "note_id": args.note_id,
        "versions": [item.to_dict() for item in history],
        "never_overwrite": True,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_note_plan(
    args: argparse.Namespace,
):
    _ensure_note_paths_separate(
        state_dir=args.state_dir,
        provider_root=args.provider_root,
        profiles_dir=args.profiles_dir,
    )
    request = load_personal_note_request(args.request_file)
    configuration = load_profile_configuration(args.profiles_dir)
    if request.profile_id not in {
        profile.profile_id for profile in configuration.profiles
    }:
        raise PersonalNoteWorkflowError(f"Unbekanntes Profil: {request.profile_id}")
    store = _note_store(args)
    plan = build_personal_note_plan(
        request,
        store=store,
        guide=SyntheticPersonalNoteGuide(),
    )
    return plan, store


def _note_store(args: argparse.Namespace) -> LlmNoteBridge:
    plugin = _plugin_by_id(args.manifest_root, "llm-note")
    return LlmNoteBridge(
        plugin=plugin,
        provider_root=args.provider_root,
        db_path=args.state_dir / "personal-notes" / "llm-note.db",
    )


def _ensure_note_paths_separate(
    *,
    state_dir: Path,
    provider_root: Path,
    profiles_dir: Path,
) -> None:
    state = state_dir.resolve()
    for label, path in (
        ("llm-note-Checkout", provider_root.resolve()),
        ("Profilordner", profiles_dir.resolve()),
    ):
        if state == path or state.is_relative_to(path) or path.is_relative_to(state):
            raise PersonalNoteWorkflowError(
                f"Notiz-State und {label} dürfen sich nicht überlappen."
            )


def _read_note_approval(path: Path) -> PersonalNoteApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PersonalNoteWorkflowError(f"Notizfreigabe ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != PersonalNoteApproval.SCHEMA:
        raise PersonalNoteWorkflowError("Notizfreigabe besitzt ein unbekanntes Schema.")
    expected = {
        "schema",
        "approval_id",
        "plan_id",
        "plan_sha256",
        "action_id",
        "content_sha256",
        "approved_at",
        "allow_local_note_write",
    }
    if set(payload) != expected:
        raise PersonalNoteWorkflowError("Notizfreigabe besitzt unbekannte oder fehlende Felder.")
    if not isinstance(payload["allow_local_note_write"], bool):
        raise PersonalNoteWorkflowError("Notizfreigabe benötigt einen booleschen Schreibschalter.")
    try:
        return PersonalNoteApproval(
            approval_id=payload["approval_id"],
            plan_id=payload["plan_id"],
            plan_sha256=payload["plan_sha256"],
            action_id=payload["action_id"],
            content_sha256=payload["content_sha256"],
            approved_at=payload["approved_at"],
            allow_local_note_write=payload["allow_local_note_write"],
        )
    except (TypeError, ValueError) as exc:
        raise PersonalNoteWorkflowError(f"Notizfreigabe ist ungültig: {exc}") from exc


def _run_tax_providers(args: argparse.Namespace) -> int:
    try:
        plugin = _plugin_by_id(args.manifest_root, "steuer-assistent")
        load_pinned_python_modules(
            plugin=plugin,
            provider_root=args.provider_root,
            package_name="steuer_assistent",
        )
        status = "ready"
        reason = "Gepinnter sauberer Checkout und Paketversion wurden bestätigt."
    except (
        ManifestValidationError,
        ProviderCheckoutError,
        TaxAssistantBridgeError,
        ValueError,
    ) as exc:
        status = "blocked"
        reason = str(exc)
        plugin = None
    payload = {
        "schema": "folderhome.tax-provider-inventory.v1",
        "provider": {
            "provider_id": "steuer-assistent",
            "version": plugin.version if plugin else "unknown",
            "revision": plugin.source_revision if plugin else None,
            "repository": plugin.source_repository if plugin else None,
            "status": status,
            "reason": reason,
            "network_required": False,
            "source_code_copied": False,
        },
        "scope": "private_employee_expense_workpaper",
        "tax_advice": False,
        "deductibility_assessed": False,
        "official_format": False,
        "portal_submission_supported": False,
        "os_account_is_security_boundary": True,
        "profile_is_security_boundary": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if status == "ready" else 2


def _run_tax_receipt_plan(args: argparse.Namespace) -> int:
    try:
        plan, _ = _prepare_tax_receipt_plan(args)
    except _TAX_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_tax_receipt_apply(args: argparse.Namespace) -> int:
    try:
        plan, bridge = _prepare_tax_receipt_plan(args)
        approval = _read_tax_receipt_approval(args.approval_file)
        report = apply_tax_receipt_plan(
            plan,
            approval,
            bridge=bridge,
            allow_state_write=args.approve_state_write,
        )
    except _TAX_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_tax_export_plan(args: argparse.Namespace) -> int:
    try:
        plan, _ = _prepare_tax_export_plan(args)
    except _TAX_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_tax_export(args: argparse.Namespace) -> int:
    try:
        plan, bridge = _prepare_tax_export_plan(args)
        approval = _read_tax_export_approval(args.approval_file)
        report = export_tax_workpaper(
            plan,
            approval,
            bridge=bridge,
            allow_state_write=args.approve_state_write,
            allow_output_write=args.approve_output_write,
        )
    except _TAX_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


_TAX_ERRORS = (
    DocumentCatalogError,
    FinanceStoreError,
    ManifestValidationError,
    ProfileConfigurationError,
    ProviderCheckoutError,
    TaxAssistantBridgeError,
    TaxWorkflowError,
    OSError,
    ValueError,
)


def _prepare_tax_receipt_plan(
    args: argparse.Namespace,
):
    _ensure_tax_paths_separate(
        state_dir=args.state_dir,
        provider_root=args.provider_root,
        profiles_dir=args.profiles_dir,
    )
    request = load_tax_receipt_request(args.request_file)
    configuration = load_profile_configuration(args.profiles_dir)
    if request.profile_id not in {
        profile.profile_id for profile in configuration.profiles
    }:
        raise TaxWorkflowError(f"Unbekanntes Profil: {request.profile_id}")
    bridge = _tax_bridge(args, request.profile_id)
    plan = build_tax_receipt_plan(
        request,
        documents=DocumentCatalogStore(args.state_dir).load(),
        transactions=FinanceStore(args.state_dir).list_transactions(
            profile_id=request.profile_id
        ),
        bridge=bridge,
        allow_sensitive_local_read=args.approve_sensitive_local_read,
    )
    return plan, bridge


def _prepare_tax_export_plan(
    args: argparse.Namespace,
):
    _ensure_tax_paths_separate(
        state_dir=args.state_dir,
        provider_root=args.provider_root,
        profiles_dir=args.profiles_dir,
    )
    configuration = load_profile_configuration(args.profiles_dir)
    if args.profile not in {profile.profile_id for profile in configuration.profiles}:
        raise TaxWorkflowError(f"Unbekanntes Profil: {args.profile}")
    bridge = _tax_bridge(args, args.profile)
    plan = build_tax_export_plan(
        args.tax_year,
        profile_id=args.profile,
        output_path=args.output_file,
        bridge=bridge,
    )
    return plan, bridge


def _tax_bridge(args: argparse.Namespace, profile_id: str) -> TaxAssistantBridge:
    plugin = _plugin_by_id(args.manifest_root, "steuer-assistent")
    return TaxAssistantBridge(
        plugin=plugin,
        provider_root=args.provider_root,
        db_path=args.state_dir / "tax-workpaper" / profile_id / "steuer.db",
    )


def _ensure_tax_paths_separate(
    *,
    state_dir: Path,
    provider_root: Path,
    profiles_dir: Path,
) -> None:
    state = state_dir.resolve()
    for label, path in (
        ("steuer-assistent-Checkout", provider_root.resolve()),
        ("Profilordner", profiles_dir.resolve()),
    ):
        if state == path or state.is_relative_to(path) or path.is_relative_to(state):
            raise TaxWorkflowError(
                f"Steuer-State und {label} dürfen sich nicht überlappen."
            )


def _read_tax_receipt_approval(path: Path) -> TaxReceiptApproval:
    payload = _read_tax_json(path, TaxReceiptApproval.SCHEMA, "Steuerbelegfreigabe")
    expected = {
        "schema",
        "approval_id",
        "plan_id",
        "plan_sha256",
        "action_id",
        "provider_store_revision",
        "approved_at",
        "allow_local_tax_write",
    }
    if set(payload) != expected or not isinstance(payload["allow_local_tax_write"], bool):
        raise TaxWorkflowError("Steuerbelegfreigabe besitzt ungültige Felder.")
    try:
        return TaxReceiptApproval(
            approval_id=_required_text(payload, "approval_id", "Steuerbelegfreigabe"),
            plan_id=_required_text(payload, "plan_id", "Steuerbelegfreigabe"),
            plan_sha256=_required_text(payload, "plan_sha256", "Steuerbelegfreigabe"),
            action_id=_required_text(payload, "action_id", "Steuerbelegfreigabe"),
            provider_store_revision=_required_text(
                payload,
                "provider_store_revision",
                "Steuerbelegfreigabe",
            ),
            approved_at=_required_text(payload, "approved_at", "Steuerbelegfreigabe"),
            allow_local_tax_write=payload["allow_local_tax_write"],
        )
    except (TypeError, ValueError) as exc:
        raise TaxWorkflowError(f"Steuerbelegfreigabe ist ungültig: {exc}") from exc


def _read_tax_export_approval(path: Path) -> TaxExportApproval:
    payload = _read_tax_json(path, TaxExportApproval.SCHEMA, "Steuerexportfreigabe")
    expected = {
        "schema",
        "approval_id",
        "plan_id",
        "plan_sha256",
        "provider_store_revision",
        "approved_at",
        "allow_local_tax_state_write",
        "allow_output_write",
    }
    if set(payload) != expected or not all(
        isinstance(payload[field], bool)
        for field in ("allow_local_tax_state_write", "allow_output_write")
    ):
        raise TaxWorkflowError("Steuerexportfreigabe besitzt ungültige Felder.")
    try:
        return TaxExportApproval(
            approval_id=_required_text(payload, "approval_id", "Steuerexportfreigabe"),
            plan_id=_required_text(payload, "plan_id", "Steuerexportfreigabe"),
            plan_sha256=_required_text(payload, "plan_sha256", "Steuerexportfreigabe"),
            provider_store_revision=_required_text(
                payload,
                "provider_store_revision",
                "Steuerexportfreigabe",
            ),
            approved_at=_required_text(payload, "approved_at", "Steuerexportfreigabe"),
            allow_local_tax_state_write=payload["allow_local_tax_state_write"],
            allow_output_write=payload["allow_output_write"],
        )
    except (TypeError, ValueError) as exc:
        raise TaxWorkflowError(f"Steuerexportfreigabe ist ungültig: {exc}") from exc


def _read_tax_json(path: Path, schema: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaxWorkflowError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise TaxWorkflowError(f"{label} besitzt ein unbekanntes Schema.")
    return payload


def _run_briefing_providers(args: argparse.Namespace) -> int:
    payload = {
        "schema": "folderhome.daily-briefing-provider-inventory.v1",
        "snapshot_inputs": {
            "weather_schema": "folderhome.weather-snapshot.v1",
            "news_schema": "folderhome.news-snapshot.v1",
            "status": "ready",
            "network_required": False,
        },
        "live_weather_connector": {
            "status": "blocked_not_implemented",
            "network_required": True,
        },
        "live_news_connector": {
            "status": "blocked_not_implemented",
            "network_required": True,
        },
        "html_renderer": {"status": "ready", "network_required": False},
        "desktop_delivery": {
            "status": "ready_with_explicit_gate",
            "automatic": False,
        },
        "scheduler_registration_supported": False,
        "network_invoked": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_briefing_plan(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_briefing_plan(args)
    except _BRIEFING_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_briefing_render(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_briefing_plan(args)
        approval = _read_briefing_render_approval(args.approval_file)
        report = render_daily_briefing(
            plan,
            approval,
            allow_output_write=args.approve_output_write,
        )
    except _BRIEFING_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_briefing_deliver(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_briefing_plan(args, allow_existing_output=True)
        approval = _read_briefing_delivery_approval(args.approval_file)
        report = deliver_daily_briefing(
            plan,
            approval,
            allow_desktop_write=args.approve_desktop_write,
        )
    except _BRIEFING_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


_BRIEFING_ERRORS = (
    DailyBriefingError,
    ProfileConfigurationError,
    OSError,
    ValueError,
)


def _prepare_briefing_plan(
    args: argparse.Namespace,
    *,
    allow_existing_output: bool = False,
):
    if not args.approve_sensitive_local_read:
        raise DailyBriefingError(
            "Sensitivitätsfreigabe für lokale Briefingdaten fehlt."
        )
    request = load_daily_briefing_request(args.request_file)
    configuration = load_profile_configuration(args.profiles_dir)
    return build_daily_briefing_plan(
        request,
        known_profile_ids={profile.profile_id for profile in configuration.profiles},
        output_path=args.output_file,
        desktop_path=args.desktop_file,
        allow_sensitive_local_read=True,
        allow_existing_output=allow_existing_output,
    )


def _read_briefing_render_approval(path: Path) -> BriefingRenderApproval:
    payload = _read_briefing_json(
        path,
        BriefingRenderApproval.SCHEMA,
        "Briefing-Renderfreigabe",
    )
    expected = {
        "schema",
        "approval_id",
        "plan_id",
        "plan_sha256",
        "html_sha256",
        "output_path",
        "approved_at",
        "allow_output_write",
    }
    if set(payload) != expected or not isinstance(payload["allow_output_write"], bool):
        raise DailyBriefingError("Briefing-Renderfreigabe besitzt ungültige Felder.")
    try:
        return BriefingRenderApproval(
            approval_id=_required_text(payload, "approval_id", "Renderfreigabe"),
            plan_id=_required_text(payload, "plan_id", "Renderfreigabe"),
            plan_sha256=_required_text(payload, "plan_sha256", "Renderfreigabe"),
            html_sha256=_required_text(payload, "html_sha256", "Renderfreigabe"),
            output_path=Path(_required_text(payload, "output_path", "Renderfreigabe")),
            approved_at=_required_text(payload, "approved_at", "Renderfreigabe"),
            allow_output_write=payload["allow_output_write"],
        )
    except (TypeError, ValueError) as exc:
        raise DailyBriefingError(f"Briefing-Renderfreigabe ist ungültig: {exc}") from exc


def _read_briefing_delivery_approval(path: Path) -> BriefingDeliveryApproval:
    payload = _read_briefing_json(
        path,
        BriefingDeliveryApproval.SCHEMA,
        "Briefing-Desktopfreigabe",
    )
    expected = {
        "schema",
        "approval_id",
        "plan_id",
        "plan_sha256",
        "html_sha256",
        "desktop_path",
        "approved_at",
        "allow_desktop_write",
    }
    if set(payload) != expected or not isinstance(payload["allow_desktop_write"], bool):
        raise DailyBriefingError("Briefing-Desktopfreigabe besitzt ungültige Felder.")
    try:
        return BriefingDeliveryApproval(
            approval_id=_required_text(payload, "approval_id", "Desktopfreigabe"),
            plan_id=_required_text(payload, "plan_id", "Desktopfreigabe"),
            plan_sha256=_required_text(payload, "plan_sha256", "Desktopfreigabe"),
            html_sha256=_required_text(payload, "html_sha256", "Desktopfreigabe"),
            desktop_path=Path(
                _required_text(payload, "desktop_path", "Desktopfreigabe")
            ),
            approved_at=_required_text(payload, "approved_at", "Desktopfreigabe"),
            allow_desktop_write=payload["allow_desktop_write"],
        )
    except (TypeError, ValueError) as exc:
        raise DailyBriefingError(f"Briefing-Desktopfreigabe ist ungültig: {exc}") from exc


def _read_briefing_json(path: Path, schema: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DailyBriefingError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise DailyBriefingError(f"{label} besitzt ein unbekanntes Schema.")
    return payload


def _run_notice_providers(args: argparse.Namespace) -> int:
    try:
        plugin = _plugin_by_id(args.manifest_root, "doc-services")
        load_pinned_python_modules(
            plugin=plugin,
            provider_root=args.doc_services_root,
            package_name="doc_services",
        )
        document_status = "ready"
        document_reason = "Gepinnter doc-services-Checkout wurde bestätigt."
    except (ManifestValidationError, ProviderCheckoutError, ValueError) as exc:
        plugin = None
        document_status = "blocked"
        document_reason = str(exc)
    payload = {
        "schema": "folderhome.official-notice-provider-inventory.v1",
        "document_extraction": {
            "provider_id": "doc-services",
            "revision": plugin.source_revision if plugin else None,
            "status": document_status,
            "reason": document_reason,
            "ocr_enabled": False,
            "network_required": False,
        },
        "legal_review": {
            "provider_id": "law-checker",
            "status": "blocked_not_integrated",
            "reason": (
                "Phase 31 erklärt Dokumentangaben; law-checker ist nicht als "
                "saubere vollständige Sozialrechts-Runtime angebunden."
            ),
            "review_performed": False,
        },
        "deadline_legally_calculated": False,
        "response_generation_supported": False,
        "external_actions": [],
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if document_status == "ready" else 2


def _run_notice_inspect(args: argparse.Namespace) -> int:
    try:
        analysis = _prepare_notice_analysis(args)
    except _NOTICE_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(analysis.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_notice_render(args: argparse.Namespace) -> int:
    try:
        analysis = _prepare_notice_analysis(args)
        report = write_official_notice_report(
            analysis,
            markdown_path=args.markdown_file,
            json_path=args.json_file,
            allow_output_write=args.approve_output_write,
        )
    except _NOTICE_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


_NOTICE_ERRORS = (
    DocServicesBridgeError,
    ManifestValidationError,
    OfficialNoticeError,
    ProfileConfigurationError,
    ProviderCheckoutError,
    OSError,
    ValueError,
)


def _prepare_notice_analysis(args: argparse.Namespace):
    if not args.approve_sensitive_local_read:
        raise OfficialNoticeError("Sensitivitätsfreigabe für den Bescheid fehlt.")
    configuration = load_profile_configuration(args.profiles_dir)
    if args.profile not in {profile.profile_id for profile in configuration.profiles}:
        raise OfficialNoticeError(f"Unbekanntes Profil: {args.profile}")
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
        allow_ocr=False,
    )
    return analyze_official_notice(
        args.source_file,
        profile_id=args.profile,
        received_on=args.received_on,
        as_of=args.as_of,
        extractor=extractor,
        allow_sensitive_local_read=True,
    )


def _run_administrative_draft_preview(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_administrative_draft_plan(args)
    except _ADMINISTRATIVE_DRAFT_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_administrative_draft_render(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_administrative_draft_plan(args)
        approval = _read_administrative_draft_approval(args.approval_file)
        report = write_administrative_draft(
            plan,
            approval,
            markdown_file=args.markdown_file,
            text_file=args.text_file,
            allow_output_write=args.approve_output_write,
        )
    except _ADMINISTRATIVE_DRAFT_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


_ADMINISTRATIVE_DRAFT_ERRORS = (
    AdministrativeDraftError,
    CorrespondenceError,
    DocServicesBridgeError,
    ManifestValidationError,
    OfficialNoticeError,
    ProfileConfigurationError,
    ProviderCheckoutError,
    OSError,
    ValueError,
)


def _prepare_administrative_draft_plan(args: argparse.Namespace):
    if not args.approve_sensitive_local_read:
        raise AdministrativeDraftError(
            "Sensitivitätsfreigabe für den Verwaltungsentwurf fehlt."
        )
    request = load_administrative_draft_request(args.request_file)
    configuration = load_profile_configuration(args.profiles_dir)
    if request.profile_id not in {
        profile.profile_id for profile in configuration.profiles
    }:
        raise AdministrativeDraftError(f"Unbekanntes Profil: {request.profile_id}")
    correspondence_configuration = load_correspondence_configuration(
        args.designs_file,
        args.templates_file,
    )
    if request.draft_kind.value == "benefit_application":
        if args.source_file is not None or args.received_on is not None:
            raise AdministrativeDraftError(
                "Antragsentwurf darf keine Bescheidquelle oder Zugangsdaten vortäuschen."
            )
        notice_analysis = None
    else:
        if args.source_file is None:
            raise AdministrativeDraftError("Bescheidentwurf benötigt --source-file.")
        extractor = DocServicesBridge(
            plugin=_plugin_by_id(args.manifest_root, "doc-services"),
            provider_root=args.doc_services_root,
            allow_ocr=False,
        )
        notice_analysis = analyze_official_notice(
            args.source_file,
            profile_id=request.profile_id,
            received_on=args.received_on,
            as_of=args.as_of,
            extractor=extractor,
            allow_sensitive_local_read=True,
        )
    return build_administrative_draft_plan(
        request,
        notice_analysis=notice_analysis,
        correspondence_configuration=correspondence_configuration,
        report_forge_revision=REPORT_FORGE_REVISION,
        report_forge_distribution_version=REPORT_FORGE_DISTRIBUTION_VERSION,
        report_forge_runtime_version=REPORT_FORGE_RUNTIME_VERSION,
    )


def _read_administrative_draft_approval(path: Path) -> AdministrativeDraftApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdministrativeDraftError(f"Entwurfsfreigabe ist nicht lesbar: {exc}") from exc
    expected = {
        "schema",
        "approval_id",
        "plan_id",
        "markdown_sha256",
        "text_sha256",
        "approved_at",
        "confirmed_content_review",
        "confirmed_no_legal_review",
        "allow_local_output_write",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise AdministrativeDraftError(
            "Entwurfsfreigabe besitzt unbekannte oder fehlende Felder."
        )
    if payload.get("schema") != AdministrativeDraftApproval.SCHEMA:
        raise AdministrativeDraftError("Entwurfsfreigabe verwendet ein unbekanntes Schema.")
    try:
        approval = AdministrativeDraftApproval.create(
            plan_id=payload["plan_id"],
            markdown_sha256=payload["markdown_sha256"],
            text_sha256=payload["text_sha256"],
            approved_at=payload["approved_at"],
            confirmed_content_review=payload["confirmed_content_review"],
            confirmed_no_legal_review=payload["confirmed_no_legal_review"],
            allow_local_output_write=payload["allow_local_output_write"],
        )
    except (TypeError, ValueError) as exc:
        raise AdministrativeDraftError(f"Entwurfsfreigabe ist ungültig: {exc}") from exc
    if approval.approval_id != payload["approval_id"]:
        raise AdministrativeDraftError("Entwurfsfreigabe-ID stimmt nicht mit dem Inhalt überein.")
    return approval


def _run_benefit_screening(args: argparse.Namespace) -> int:
    try:
        report = _prepare_benefit_screening(args)
    except _BENEFIT_SCREENING_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_benefit_screening_render(args: argparse.Namespace) -> int:
    try:
        report = _prepare_benefit_screening(args)
        output = write_benefit_screening_report(
            report,
            markdown_file=args.markdown_file,
            json_file=args.json_file,
            allow_output_write=args.approve_output_write,
        )
    except _BENEFIT_SCREENING_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(output.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


_BENEFIT_SCREENING_ERRORS = (
    BenefitScreeningError,
    ProfileConfigurationError,
    OSError,
    ValueError,
)


def _prepare_benefit_screening(args: argparse.Namespace):
    if not args.approve_sensitive_local_read:
        raise BenefitScreeningError("Sensitivitätsfreigabe für Leistungsvorcheck fehlt.")
    profile = load_benefit_profile_snapshot(
        args.profile_facts_file,
        allow_sensitive_local_read=True,
    )
    configuration = load_profile_configuration(args.profiles_dir)
    if profile.profile_id not in {
        item.profile_id for item in configuration.profiles
    }:
        raise BenefitScreeningError(f"Unbekanntes Profil: {profile.profile_id}")
    catalog = load_benefit_catalog(args.catalog_file)
    return screen_benefits(
        profile,
        catalog,
        as_of=args.as_of,
        max_source_age_days=args.max_source_age_days,
        allow_sensitive_local_read=True,
    )


def _run_legal_providers(args: argparse.Namespace) -> int:
    try:
        bridge = LawCheckerBridge(
            plugin=_plugin_by_id(args.manifest_root, "law-checker"),
            provider_root=args.law_checker_root,
        )
        payload = bridge.qualification()
    except _LEGAL_CHANGE_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_legal_compare(args: argparse.Namespace) -> int:
    try:
        report = _prepare_legal_change(args)
    except _LEGAL_CHANGE_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_legal_render(args: argparse.Namespace) -> int:
    try:
        report = _prepare_legal_change(args)
        output = write_legal_change_report(
            report,
            markdown_file=args.markdown_file,
            json_file=args.json_file,
            allow_output_write=args.approve_output_write,
        )
    except _LEGAL_CHANGE_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(output.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


_LEGAL_CHANGE_ERRORS = (
    LawCheckerBridgeError,
    LegalChangeMonitorError,
    ManifestValidationError,
    OSError,
    ValueError,
)


def _prepare_legal_change(args: argparse.Namespace):
    if not args.approve_sensitive_local_read:
        raise LegalChangeMonitorError(
            "Sensitivitätsfreigabe für Rechtsänderungsmonitor fehlt."
        )
    bridge = LawCheckerBridge(
        plugin=_plugin_by_id(args.manifest_root, "law-checker"),
        provider_root=args.law_checker_root,
    )
    before = load_legal_source_snapshot(
        args.before_file,
        allow_test_fixture=args.allow_test_fixture,
    )
    after = load_legal_source_snapshot(
        args.after_file,
        allow_test_fixture=args.allow_test_fixture,
    )
    interests = load_legal_interest_snapshot(
        args.interests_file,
        allow_sensitive_local_read=True,
    )
    return compare_legal_source_snapshots(
        before,
        after,
        interests,
        as_of=args.as_of,
        max_source_age_days=args.max_source_age_days,
        allow_sensitive_local_read=True,
        allow_test_fixture=args.allow_test_fixture,
        law_checker=bridge,
    )


def _run_strands_agent_plan(args: argparse.Namespace) -> int:
    try:
        application = _prepare_local_app(args)
        payload = plan_folderhome_agent(
            application=application,
            settings=_strands_agent_settings(args),
        )
    except (*_LOCAL_APP_ERRORS, FolderHomeAgentError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_strands_agent(args: argparse.Namespace) -> int:
    try:
        application = _prepare_local_app(args)
        report = application.run_agent_chat(
            profile_id=args.profile_id,
            message=args.prompt,
        )
    except (*_LOCAL_APP_ERRORS, FolderHomeAgentError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_strands_agent_session(args: argparse.Namespace) -> int:
    try:
        application = _prepare_local_app(args)
    except (*_LOCAL_APP_ERRORS, FolderHomeAgentError) as exc:
        return _print_error(str(exc))

    ready = _agent_session_event(
        "ready",
        profile_id=args.profile_id,
        model_provider=application.agent_settings.model_provider,
        conversation=application.agent_conversation_payload(args.profile_id),
        chat_is_approval=False,
        confirmation_command="/confirm <plan_id>",
        commands=[
            "/help",
            "/catalog",
            "/reset",
            "/confirm <plan_id>",
            "/quit",
        ],
        side_effects=[],
    )
    _print_agent_session_event(ready, as_json=args.as_json)
    encountered_error = False
    interactive = sys.stdin.isatty()
    while True:
        try:
            if interactive:
                line = input("folderhome> ")
            else:
                raw_line = sys.stdin.readline()
                if raw_line == "":
                    break
                line = raw_line.rstrip("\r\n")
        except (EOFError, KeyboardInterrupt):
            break
        message = line.strip()
        if not message:
            continue
        if message == "/quit":
            break
        if message == "/help":
            _print_agent_session_event(
                _agent_session_event(
                    "help",
                    commands={
                        "/help": "Show these bounded session commands.",
                        "/catalog": "Show exact workflow executor coverage without changes.",
                        "/reset": "Clear this profile's process-local context and plans.",
                        "/confirm <plan_id>": (
                            "Confirm every approval-required step of one displayed plan."
                        ),
                        "/quit": "Close the in-process agent session.",
                    },
                    chat_is_approval=False,
                    side_effects=[],
                ),
                as_json=args.as_json,
            )
            continue
        if message == "/catalog":
            _print_agent_session_event(
                _agent_session_event(
                    "catalog",
                    catalog=application.executor_catalog_payload(),
                    side_effects=[],
                ),
                as_json=args.as_json,
            )
            continue
        if message == "/reset":
            result = application.reset_agent_conversation(args.profile_id)
            _print_agent_session_event(
                _agent_session_event(
                    "conversation_reset",
                    conversation=result["conversation"],
                    discarded_plan_ids=result["discarded_plan_ids"],
                    side_effects=result["side_effects"],
                ),
                as_json=args.as_json,
            )
            continue
        if message.startswith("/confirm"):
            parts = message.split()
            if len(parts) != 2 or parts[0] != "/confirm":
                encountered_error = True
                _print_agent_session_error(
                    "Use exactly: /confirm <plan_id>",
                    as_json=args.as_json,
                )
                continue
            plan = application.proposed_agent_plan(parts[1])
            if plan is None:
                encountered_error = True
                _print_agent_session_error(
                    "The plan is not known in this local process session.",
                    as_json=args.as_json,
                )
                continue
            step_ids = tuple(
                step.step_id for step in plan.steps if step.confirmation_required
            )
            if not step_ids:
                encountered_error = True
                _print_agent_session_error(
                    "This plan has no approval-required steps.",
                    as_json=args.as_json,
                )
                continue
            try:
                result = application.confirm_agent_plan(
                    plan_id=plan.plan_id,
                    plan_sha256=plan.plan_sha256,
                    step_ids=step_ids,
                )
            except (*_LOCAL_APP_ERRORS, FolderHomeAgentError) as exc:
                encountered_error = True
                _print_agent_session_error(str(exc), as_json=args.as_json)
                continue
            _print_agent_session_event(
                _agent_session_event(
                    "confirmation",
                    plan_id=plan.plan_id,
                    plan_sha256=plan.plan_sha256,
                    confirmed_step_ids=list(step_ids),
                    result=result,
                    side_effects=result["side_effects"],
                ),
                as_json=args.as_json,
            )
            continue
        if message.startswith("/"):
            encountered_error = True
            _print_agent_session_error(
                "Unknown session command. Use /help.",
                as_json=args.as_json,
            )
            continue
        try:
            report = application.run_agent_chat(
                profile_id=args.profile_id,
                message=message,
            )
        except (*_LOCAL_APP_ERRORS, FolderHomeAgentError) as exc:
            encountered_error = True
            _print_agent_session_error(str(exc), as_json=args.as_json)
            continue
        _print_agent_session_event(
            _agent_session_event(
                "chat",
                agent=report.to_dict(),
                conversation=application.agent_conversation_payload(args.profile_id),
                side_effects=list(report.side_effects),
            ),
            as_json=args.as_json,
        )

    _print_agent_session_event(
        _agent_session_event("closed", side_effects=[]),
        as_json=args.as_json,
    )
    return 2 if encountered_error else 0


def _agent_session_event(event: str, **payload: object) -> dict[str, object]:
    return {
        "schema": "folderhome.agent-session-event.v1",
        "event": event,
        **payload,
    }


def _print_agent_session_error(message: str, *, as_json: bool) -> None:
    _print_agent_session_event(
        _agent_session_event("error", message=message, side_effects=[]),
        as_json=as_json,
    )


def _print_agent_session_event(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
        return
    event = payload["event"]
    if event == "ready":
        print(
            "FolderHome master agent ready for profile "
            f"{payload['profile_id']}. Chat never counts as approval."
        )
        print(
            "Commands: /help, /catalog, /reset, /confirm <plan_id>, /quit",
            flush=True,
        )
        return
    if event == "help":
        for command, description in payload["commands"].items():
            print(f"{command}: {description}")
        sys.stdout.flush()
        return
    if event == "catalog":
        catalog = payload["catalog"]
        coverage = catalog["coverage"]
        print(
            "Executor coverage: "
            f"{coverage['connected']} connected, "
            f"{coverage['direct_read_only']} read-only, "
            f"{coverage['planning_only']} planning-only, "
            f"{coverage['not_connected']} not connected."
        )
        for workflow in catalog["workflows"]:
            print(f"- {workflow['workflow_id']}: {workflow['status']}")
        sys.stdout.flush()
        return
    if event == "chat":
        report = payload["agent"]
        conversation = payload["conversation"]
        print(f"Conversation turn {conversation['turn']}:")
        print(report["response_text"])
        for plan in report["proposed_plans"]:
            print(f"Plan {plan['plan_id']}  SHA-256 {plan['plan_sha256']}")
            for step in plan["steps"]:
                approval = "approval required" if step["confirmation_required"] else "read-only"
                print(f"  {step['step_id']}: {step['goal']} ({approval})")
            if plan["confirmation_required"]:
                print(f"Confirm the complete displayed plan with: /confirm {plan['plan_id']}")
        sys.stdout.flush()
        return
    if event == "conversation_reset":
        print("Process-local conversation and unconfirmed plans cleared.", flush=True)
        return
    if event == "confirmation":
        result = payload["result"]
        print(
            f"Confirmed plan {payload['plan_id']}; "
            f"execution_performed={str(result['execution_performed']).lower()}."
        )
        if result["side_effects"]:
            print("Side effects: " + ", ".join(result["side_effects"]))
        sys.stdout.flush()
        return
    if event == "error":
        print(f"Error: {payload['message']}", flush=True)
        return
    if event == "closed":
        print("FolderHome agent session closed.", flush=True)


def _run_competition_demo(args: argparse.Namespace) -> int:
    try:
        report = run_competition_demo(
            args.output_dir,
            allow_output_write=args.approve_output_write,
        )
    except (CompetitionDemoError, FolderHomeAgentError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_accident_demo_site(args: argparse.Namespace) -> int:
    server = None
    try:
        if not args.approve_loopback_server:
            raise LocalServerError("Explizite lokale Serverfreigabe fehlt.")
        application = DemoSiteApplication(
            args.workspace_dir,
            port=args.port,
        )
        server = create_local_server(application, allow_loopback_server=True)
        payload = server.to_public_dict()
        payload["demo"] = "synthetic_accident"
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        sys.stdout.flush()
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (SyntheticAccidentDemoError, LocalServerError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    finally:
        if server is not None:
            server.server_close()
    return 0


DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


def _strands_agent_settings(args: argparse.Namespace) -> StrandsAgentSettings:
    ollama_host = args.ollama_host
    if args.model_provider == "ollama" and ollama_host is None:
        ollama_host = DEFAULT_OLLAMA_HOST
    return StrandsAgentSettings(
        model_provider=args.model_provider,
        bedrock_model_id=args.bedrock_model_id,
        aws_region=args.aws_region,
        ollama_host=ollama_host,
        ollama_model_id=args.ollama_model_id,
        allow_network=args.allow_network,
        allow_sensitive_cloud_data=args.approve_sensitive_cloud_data,
        max_turns=args.max_turns,
        max_tool_calls=args.max_tool_calls,
        max_prompt_chars=args.max_prompt_chars,
        max_response_chars=args.max_response_chars,
        max_tool_result_bytes=args.max_tool_result_bytes,
        max_output_tokens=args.max_output_tokens,
        max_conversation_messages=args.max_conversation_messages,
        bedrock_connect_timeout_seconds=args.bedrock_connect_timeout_seconds,
        bedrock_read_timeout_seconds=args.bedrock_read_timeout_seconds,
    )


def _run_recipes_list(args: argparse.Namespace) -> int:
    try:
        payload = {
            "schema": "folderhome.capability-recipe-catalog.v1",
            "recipes": [
                {
                    "recipe_id": item.recipe_id,
                    "title": item.title(language=args.language),
                    "summary": item.summary(language=args.language),
                    "lead_expert_id": item.lead_expert_id,
                    "workflow_ids": list(item.workflow_ids),
                    "step_count": len(item.steps),
                    "grants_new_capability": False,
                }
                for item in load_bundled_recipes()
            ],
        }
    except CapabilityRecipeError as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_recipe_plan(args: argparse.Namespace):
    application = _prepare_local_app(args)
    gateway = application.workflow_executor
    registry = application.resource_registry
    if registry is None:
        raise CapabilityRecipeError(
            "Rezepte benötigen ein konfiguriertes privates Ressourcenregister."
        )
    known_resource_ids = frozenset(
        item.resource_id
        for item in registry.resources
        if args.profile_id in item.profile_ids
    )
    statuses = {item.workflow_id: item.status for item in gateway.catalog()}
    recipe = load_bundled_recipe(args.recipe_id)
    recipe_plan = build_recipe_plan(
        recipe,
        profile_id=args.profile_id,
        language=args.language,
        prepare=lambda workflow_id, request: gateway.prepare(
            workflow_id=workflow_id,
            profile_id=args.profile_id,
            request=request,
        ),
        endpoint_statuses=statuses,
        known_resource_ids=known_resource_ids,
    )
    return gateway, recipe_plan


def _run_recipes_plan(args: argparse.Namespace) -> int:
    try:
        _, recipe_plan = _prepare_recipe_plan(args)
    except (CapabilityRecipeError, *_LOCAL_APP_ERRORS) as exc:
        return _print_error(str(exc))
    print(json.dumps(recipe_plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_recipes_run(args: argparse.Namespace) -> int:
    try:
        gateway, recipe_plan = _prepare_recipe_plan(args)
        if args.confirm != recipe_plan.plan.plan_id:
            raise CapabilityRecipeError(
                "Die Bestätigung gehört nicht zu diesem Rezeptplan. Erwartet: "
                f"/confirm {recipe_plan.plan.plan_id}"
            )
        report = execute_recipe_plan(
            recipe_plan,
            execute=lambda envelope_id, approved_at: gateway.execute(
                envelope_id=envelope_id,
                approved_at=approved_at,
            ),
            approved_at=args.approved_at,
        )
    except (CapabilityRecipeError, *_LOCAL_APP_ERRORS) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.status == "executed" else 3


def _run_local_app_plan(args: argparse.Namespace) -> int:
    try:
        application = _prepare_local_app(args)
        payload = application.plan()
    except _LOCAL_APP_ERRORS as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_local_app_serve(args: argparse.Namespace) -> int:
    server = None
    try:
        application = _prepare_local_app(args)
        server = create_local_server(
            application,
            allow_loopback_server=args.approve_loopback_server,
        )
        print(json.dumps(server.to_public_dict(), ensure_ascii=False, sort_keys=True))
        sys.stdout.flush()
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except _LOCAL_APP_ERRORS as exc:
        return _print_error(str(exc))
    finally:
        if server is not None:
            server.server_close()
    return 0


def _build_setup_app(args: argparse.Namespace) -> SetupApplication:
    config_dir = Path(args.config_dir or default_config_dir())
    return SetupApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=args.port,
            profiles_dir=args.profiles_dir,
            state_dir=config_dir,
        ),
        profiles=load_profile_configuration(args.profiles_dir),
        config_dir=config_dir,
    )


def _run_setup_plan(args: argparse.Namespace) -> int:
    """Show what the installer would configure without starting a listener."""

    try:
        payload = _build_setup_app(args).state_payload()
    except (*_LOCAL_APP_ERRORS, SetupAppError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_setup_serve(args: argparse.Namespace) -> int:
    """Serve the installer on its own loopback port with its own token."""

    server = None
    try:
        application = _build_setup_app(args)
        # The installer writes here, and the server insists on an existing state
        # dir. Only after the gate, so a refused start leaves nothing behind.
        if args.approve_loopback_server:
            application.config_dir.mkdir(parents=True, exist_ok=True)
        server = create_local_server(
            application,
            allow_loopback_server=args.approve_loopback_server,
        )
        print(json.dumps(server.to_public_dict(), ensure_ascii=False, sort_keys=True))
        sys.stdout.flush()
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (*_LOCAL_APP_ERRORS, SetupAppError) as exc:
        return _print_error(str(exc))
    finally:
        if server is not None:
            server.server_close()
    return 0


def _run_mcp_plan(args: argparse.Namespace) -> int:
    from folderhome.mcp_server import ACCESS_URL_ENV, integration_plan

    payload = integration_plan(args.access_url or os.environ.get(ACCESS_URL_ENV))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_mcp_serve(args: argparse.Namespace) -> int:
    """Run the stdio MCP proxy; stdout is the transport, so errors go to stderr."""

    from folderhome.mcp_server import ACCESS_URL_ENV, McpServerError, serve_mcp_stdio

    try:
        serve_mcp_stdio(
            access_url=args.access_url or os.environ.get(ACCESS_URL_ENV),
            approve_mcp_server=args.approve_mcp_server,
        )
    except KeyboardInterrupt:
        return 0
    except McpServerError as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    return 0


_LOCAL_APP_ERRORS = (
    LocalAppError,
    LocalServerError,
    KnowledgeDigestBridgeError,
    ManifestValidationError,
    ProfileConfigurationError,
    ProviderCheckoutError,
    WorkflowExecutionError,
    OSError,
    ValueError,
)


_LAUNCH_CONFIG_FIELDS = {
    "profiles_dir": Path,
    "state_dir": Path,
    "resources_file": Path,
    "port": int,
    "model_provider": str,
    "ollama_host": str,
    "ollama_model_id": str,
    "bedrock_model_id": str,
    "aws_region": str,
}
_LAUNCH_CONFIG_DEFAULTS: dict[str, object] = {
    "resources_file": None,
    "port": 8765,
    "model_provider": "fixture",
    "ollama_host": None,
    "ollama_model_id": None,
    "bedrock_model_id": None,
    "aws_region": None,
}


def _apply_launch_config(args: argparse.Namespace) -> None:
    """Fill start-up values from a launch config; explicit flags always win.

    Gates stay start-up flags on purpose: they are not on the allowlist, so no
    file can grant network access or a cloud data approval.
    """

    supplied: dict[str, object] = {}
    launch_config = getattr(args, "launch_config", None)
    if launch_config is not None:
        try:
            payload = json.loads(Path(launch_config).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Startkonfiguration ist nicht lesbar: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema") != (
            LAUNCH_CONFIG_SCHEMA
        ):
            raise ValueError("Startkonfiguration verwendet ein unbekanntes Schema.")
        for name, kind in _LAUNCH_CONFIG_FIELDS.items():
            value = payload.get(name)
            if value is None:
                continue
            if kind is int and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValueError(f"Startkonfiguration braucht für {name} eine Zahl.")
            if kind is not int and not isinstance(value, str):
                raise ValueError(f"Startkonfiguration braucht für {name} einen Text.")
            supplied[name] = kind(value) if kind is not str else value
    # A launch config describes one intended provider. If the caller picks a
    # different one on the command line, the other provider's fields do not apply.
    effective = getattr(args, "model_provider", supplied.get("model_provider", "fixture"))
    if effective != "ollama":
        supplied.pop("ollama_host", None)
        supplied.pop("ollama_model_id", None)
    if effective != "bedrock":
        supplied.pop("bedrock_model_id", None)
        supplied.pop("aws_region", None)
    for name in _LAUNCH_CONFIG_FIELDS:
        if hasattr(args, name):
            continue
        if name in supplied:
            setattr(args, name, supplied[name])
        elif name in _LAUNCH_CONFIG_DEFAULTS:
            setattr(args, name, _LAUNCH_CONFIG_DEFAULTS[name])
    for name in ("profiles_dir", "state_dir"):
        if getattr(args, name, None) is None:
            flag = f"--{name.replace('_', '-')}"
            raise ValueError(
                f"{flag} fehlt; gib es an oder nenne es in --launch-config."
            )


def _prepare_local_app(args: argparse.Namespace) -> LocalApplication:
    _apply_launch_config(args)
    settings = LocalAppSettings(
        host=args.host,
        port=args.port,
        profiles_dir=args.profiles_dir,
        state_dir=args.state_dir,
        max_body_bytes=args.max_body_bytes,
        max_query_limit=args.max_query_limit,
        max_concurrent_requests=args.max_concurrent_requests,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    if not settings.state_dir.is_dir():
        raise LocalAppError(f"App-State-Verzeichnis fehlt: {settings.state_dir}")
    profiles = load_profile_configuration(settings.profiles_dir)
    configured_resources_file = (
        args.resources_file
        if args.resources_file is not None
        else default_resource_registry_path()
    )
    resource_registry = None
    if args.resources_file is not None or configured_resources_file.is_file():
        resource_registry = load_resource_registry(
            configured_resources_file,
            expected_os_account=profiles.os_account,
            known_profile_ids=frozenset(
                profile.profile_id for profile in profiles.profiles
            ),
        )
    document_plugins = _document_plugins(args.manifest_root)
    plugin = document_plugins["KnowledgeDigest"]
    verify_checkout_revision(args.knowledge_digest_root, plugin.source_revision)
    searcher = KnowledgeDigestBridge(
        plugin=plugin,
        provider_root=args.knowledge_digest_root,
        state_dir=settings.state_dir,
    )
    profile_ids = frozenset(profile.profile_id for profile in profiles.profiles)
    workflow_adapters = [
        FindCallWorkflowAdapter(
            profile_ids=profile_ids,
        ),
        PersonalNotesWorkflowAdapter(
            plugin=_plugin_by_id(args.manifest_root, "llm-note"),
            provider_root=args.llm_note_root,
            state_dir=settings.state_dir,
            profile_ids=profile_ids,
        ),
        MedicationIntakeWorkflowAdapter(
            state_dir=settings.state_dir,
            profile_ids=profile_ids,
        ),
    ]
    if resource_registry is not None:
        resource_extractor = DocServicesBridge(
            plugin=document_plugins["doc-services"],
            provider_root=args.doc_services_root,
        )
        workflow_adapters.extend(
            (
                DocumentBundleWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                ContactRegisterWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                CorrespondenceWorkflowAdapter(
                    registry=resource_registry,
                    report_forge_revision=REPORT_FORGE_REVISION,
                    report_forge_distribution_version=(
                        REPORT_FORGE_DISTRIBUTION_VERSION
                    ),
                    report_forge_runtime_version=REPORT_FORGE_RUNTIME_VERSION,
                ),
                LocalCalendarWorkflowAdapter(
                    registry=resource_registry,
                    profiles=profiles,
                    extractor=resource_extractor,
                ),
                HealthDossierWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                FinanceImportWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                OfficialNoticeWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                AdministrativeDraftWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                    report_forge_revision=REPORT_FORGE_REVISION,
                    report_forge_distribution_version=(
                        REPORT_FORGE_DISTRIBUTION_VERSION
                    ),
                    report_forge_runtime_version=REPORT_FORGE_RUNTIME_VERSION,
                ),
                BenefitScreeningWorkflowAdapter(
                    registry=resource_registry,
                ),
                LegalChangeMonitorWorkflowAdapter(
                    registry=resource_registry,
                    law_checker_plugin=_plugin_by_id(
                        args.manifest_root,
                        "law-checker",
                    ),
                    law_checker_root=args.law_checker_root,
                ),
                InventoryImportWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                DailyBriefingWorkflowAdapter(
                    registry=resource_registry,
                ),
                TaxWorkpaperWorkflowAdapter(
                    registry=resource_registry,
                    plugin=_plugin_by_id(
                        args.manifest_root,
                        "steuer-assistent",
                    ),
                    provider_root=args.tax_assistant_root,
                ),
                FolderCleanupWorkflowAdapter(
                    registry=resource_registry,
                    profiles=profiles,
                    extractor=resource_extractor,
                ),
                FolderRoutineWorkflowAdapter(
                    registry=resource_registry,
                    profiles=profiles,
                    extractor=resource_extractor,
                ),
                DirectoryObservationWorkflowAdapter(
                    registry=resource_registry,
                ),
                DocumentActionPlanWorkflowAdapter(
                    registry=resource_registry,
                    profiles=profiles,
                    extractor=resource_extractor,
                ),
                DocumentActionExecutionWorkflowAdapter(
                    registry=resource_registry,
                    profiles=profiles,
                    extractor=resource_extractor,
                ),
                DocumentPackageWorkflowAdapter(
                    registry=resource_registry,
                    extractor=resource_extractor,
                ),
                ArtifactStudioWorkflowAdapter(
                    registry=resource_registry,
                ),
                ContractCockpitWorkflowAdapter(
                    registry=resource_registry,
                    searcher=searcher,
                    extractor=resource_extractor,
                    expected_state_root=settings.state_dir,
                ),
                FcsaDryRunWorkflowAdapter(
                    registry=resource_registry,
                    plugin=_plugin_by_id(
                        args.manifest_root,
                        "file-collect-sort-action",
                    ),
                    bridge=FcsaDryRunBridge(
                        plugin=_plugin_by_id(
                            args.manifest_root,
                            "file-collect-sort-action",
                        ),
                        provider_root=args.fcsa_root,
                    ),
                ),
                RoutineQueueWorkflowAdapter(
                    registry=resource_registry,
                    profiles=profiles,
                    extractor=resource_extractor,
                ),
            )
        )
        if any(
            "mail.draft_account" in resource.purposes
            for resource in resource_registry.resources
        ):
            workflow_adapters.append(
                MailDraftWorkflowAdapter(
                    registry=resource_registry,
                    state_dir=settings.state_dir,
                    report_forge_revision=REPORT_FORGE_REVISION,
                    report_forge_distribution_version=(
                        REPORT_FORGE_DISTRIBUTION_VERSION
                    ),
                    report_forge_runtime_version=REPORT_FORGE_RUNTIME_VERSION,
                    allow_mail_draft=args.approve_mail_draft,
                )
            )
    workflow_executor = WorkflowExecutionGateway(tuple(workflow_adapters))
    return LocalApplication(
        settings=settings,
        profiles=profiles,
        searcher=searcher,
        agent_settings=_strands_agent_settings(args),
        workflow_executor=workflow_executor,
        resource_registry=resource_registry,
    )


def _read_contract_cockpit_request(path: Path) -> ContractCockpitRequest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cockpit-Anfrage ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != ContractCockpitRequest.SCHEMA:
        raise ValueError("Cockpit-Anfrage verwendet ein unbekanntes Schema.")
    list_fields = {}
    for field in ("counterparty_terms", "calendar_terms", "account_refs"):
        values = payload.get(field)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"Cockpit-Anfrage benötigt eine gültige Liste {field}.")
        list_fields[field] = tuple(values)
    archive = payload.get("archive_older_versions")
    if not isinstance(archive, bool):
        raise ValueError("archive_older_versions muss true oder false sein.")
    try:
        return ContractCockpitRequest(
            profile_id=_required_text(payload, "profile_id", "Cockpit-Anfrage"),
            area=_required_text(payload, "area", "Cockpit-Anfrage"),
            display_name=_required_text(payload, "display_name", "Cockpit-Anfrage"),
            document_query=_required_text(payload, "document_query", "Cockpit-Anfrage"),
            object_ref=_required_text(payload, "object_ref", "Cockpit-Anfrage"),
            counterparty_terms=list_fields["counterparty_terms"],
            calendar_terms=list_fields["calendar_terms"],
            account_refs=list_fields["account_refs"],
            coverage_start=_required_text(payload, "coverage_start", "Cockpit-Anfrage"),
            as_of=_required_text(payload, "as_of", "Cockpit-Anfrage"),
            archive_older_versions=archive,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Cockpit-Anfrage ist ungültig: {exc}") from exc


def _required_text(payload: dict[str, object], field: str, label: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} benötigt das Textfeld {field}.")
    return value.strip()


def _ensure_outputs_outside_root(
    root: Path,
    *outputs: Path | None,
    label: str,
) -> None:
    resolved_root = root.resolve()
    for output in outputs:
        if output is not None and output.resolve().is_relative_to(resolved_root):
            raise ValueError(label)


def _prepare_medication_import_plan(
    args: argparse.Namespace,
) -> tuple[MedicationImportPlan, MedicationStore]:
    _ensure_medication_paths_separate(args.source_dir, args.state_dir)
    configuration = load_profile_configuration(args.profiles_dir)
    if args.profile not in {profile.profile_id for profile in configuration.profiles}:
        raise MedicationWorkflowError(f"Unbekanntes Profil: {args.profile}")
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    analysis = analyze_folder_medication_plans(
        args.source_dir,
        profile_id=args.profile,
        extractor=extractor,
        recursive=args.recursive,
        allow_sensitive_local_read=args.approve_sensitive_local_read,
    )
    store = MedicationStore(args.state_dir)
    return build_medication_import_plan(analysis, store=store), store


def _ensure_medication_paths_separate(source_dir: Path, state_dir: Path) -> None:
    source = source_dir.resolve()
    state = state_dir.resolve()
    if source == state or source.is_relative_to(state) or state.is_relative_to(source):
        raise MedicationWorkflowError(
            "Medikamentenordner und Medikamenten-State dürfen sich nicht überlappen."
        )


def _read_medication_approval(path: Path) -> MedicationImportApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MedicationWorkflowError(f"Medikamentenfreigabe ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        MedicationImportApproval.SCHEMA
    ):
        raise MedicationWorkflowError("Medikamentenfreigabe verwendet ein unbekanntes Schema.")
    raw_action_ids = payload.get("action_ids")
    if not isinstance(raw_action_ids, list) or not all(
        isinstance(action_id, str) for action_id in raw_action_ids
    ):
        raise MedicationWorkflowError("Medikamentenfreigabe benötigt gültige action_ids.")
    try:
        return MedicationImportApproval(
            approval_id=_findcall_text(payload, "approval_id"),
            plan_id=_findcall_text(payload, "plan_id"),
            medication_revision=_findcall_text(payload, "medication_revision"),
            action_ids=tuple(raw_action_ids),
            approved_at=_findcall_text(payload, "approved_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MedicationWorkflowError(f"Medikamentenfreigabe ist ungültig: {exc}") from exc


def _read_medication_confirmation(path: Path) -> MedicationIntakeConfirmation:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MedicationWorkflowError(f"Einnahmebestätigung ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        MedicationIntakeConfirmation.SCHEMA
    ):
        raise MedicationWorkflowError("Einnahmebestätigung verwendet ein unbekanntes Schema.")
    try:
        return MedicationIntakeConfirmation(
            confirmation_id=_findcall_text(payload, "confirmation_id"),
            medication_revision=_findcall_text(payload, "medication_revision"),
            dose_id=_findcall_text(payload, "dose_id"),
            schedule_id=_findcall_text(payload, "schedule_id"),
            scheduled_date=_findcall_text(payload, "scheduled_date"),
            confirmed_at=_findcall_text(payload, "confirmed_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MedicationWorkflowError(f"Einnahmebestätigung ist ungültig: {exc}") from exc


def _run_contacts_apply(args: argparse.Namespace) -> int:
    try:
        plan, store = _prepare_contact_register_plan(args)
        approval = _read_contact_approval(args.approval_file)
        report = apply_contact_register_plan(
            plan,
            approval,
            store=store,
            allow_state_write=args.approve_state_write,
        )
    except (
        ContactRegisterError,
        ContactWorkflowError,
        DocServicesBridgeError,
        ManifestValidationError,
        OSError,
        ProfileConfigurationError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_contacts_list(args: argparse.Namespace) -> int:
    try:
        store = ContactRegisterStore(args.state_dir)
        contacts = store.list_contacts(
            profile_id=args.profile,
            area=args.area,
            object_query=args.object_query,
            include_deletion_candidates=args.include_deletion_candidates,
        )
        payload = {
            "schema": "folderhome.contact-list.v1",
            "register_revision": store.revision(),
            "count": len(contacts),
            "contacts": [contact.to_dict() for contact in contacts],
            "organizational_profiles_only": True,
            "security_boundary": "operating_system_account",
        }
    except (ContactRegisterError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _prepare_contact_register_plan(
    args: argparse.Namespace,
) -> tuple[ContactRegisterPlan, ContactRegisterStore]:
    _ensure_contact_paths_separate(args.source_dir, args.state_dir)
    configuration = load_profile_configuration(args.profiles_dir)
    resolve_profile_policy(
        configuration,
        profile_id=args.profile,
        area=args.area,
    )
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    analysis = analyze_folder_contacts(
        args.source_dir,
        profile_id=args.profile,
        area=args.area,
        extractor=extractor,
        recursive=args.recursive,
        allow_sensitive_local_read=args.approve_sensitive_local_read,
    )
    store = ContactRegisterStore(args.state_dir)
    return build_contact_register_plan(analysis, store=store), store


def _ensure_contact_paths_separate(source_dir: Path, state_dir: Path) -> None:
    source = source_dir.resolve()
    state = state_dir.resolve()
    if source == state or source.is_relative_to(state) or state.is_relative_to(source):
        raise ContactWorkflowError(
            "Dokumentenordner und Kontakt-State dürfen sich nicht überlappen."
        )


def _run_folders_cleanup_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan = _prepare_folder_cleanup_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        FolderCleanupError,
        ManifestValidationError,
        ProfileConfigurationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_folders_cleanup_execute(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_folder_cleanup_plan(args)
        approval = _read_cleanup_approval(args.approval_file)
        report = execute_folder_cleanup(
            plan,
            approval,
            state_dir=args.state_dir,
            allow_file_write=args.approve_file_write,
        )
    except (
        DocServicesBridgeError,
        FolderCleanupError,
        ManifestValidationError,
        ProfileConfigurationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.status == "executed" else 1


def _prepare_folder_cleanup_plan(args: argparse.Namespace):
    configuration = load_profile_configuration(args.profiles_dir)
    policy = resolve_profile_policy(
        configuration,
        profile_id=args.profile,
        area=args.area,
    )
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    return build_folder_cleanup_plan(
        args.source_dir,
        policy=policy,
        target_root=args.target_root,
        as_of=args.as_of,
        extractor=extractor,
        recursive=args.recursive,
    )


def _run_folders_routine_plan(args: argparse.Namespace) -> int:
    try:
        _preflight_new_outputs(args.output_file)
        plan = _prepare_folder_routine_plan(args)
        payload = plan.to_dict()
        if args.output_file:
            _write_new_text(args.output_file, _json_text(payload))
    except (
        DocServicesBridgeError,
        FolderRoutineError,
        ManifestValidationError,
        ProfileConfigurationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_folders_routine_execute(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_folder_routine_plan(args)
        approval = _read_cleanup_approval(args.approval_file)
        report = execute_folder_routine(
            plan,
            approval,
            completed_at=args.completed_at,
            state_dir=args.state_dir,
            allow_file_write=args.approve_file_write,
            allow_state_write=args.approve_state_write,
        )
    except (
        DocServicesBridgeError,
        FolderRoutineError,
        ManifestValidationError,
        ProfileConfigurationError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.status == "executed" else 1


def _prepare_folder_routine_plan(args: argparse.Namespace):
    watch_configuration = load_watched_folder_configuration(args.config_file)
    watch = next(
        (
            item
            for item in watch_configuration.watches
            if item.watch_id == args.watch_id
        ),
        None,
    )
    if watch is None:
        raise FolderRoutineError(f"Unbekannter Beobachtungsordner: {args.watch_id}")
    profile_configuration = load_profile_configuration(args.profiles_dir)
    policy = resolve_profile_policy(
        profile_configuration,
        profile_id=watch.profile_id,
        area=watch.area,
    )
    extractor = DocServicesBridge(
        plugin=_plugin_by_id(args.manifest_root, "doc-services"),
        provider_root=args.doc_services_root,
    )
    return build_folder_routine_plan(
        watch,
        policy=policy,
        target_root=args.target_root,
        as_of=args.as_of,
        captured_at=args.captured_at,
        state_dir=args.state_dir,
        extractor=extractor,
        mode=FolderRoutineMode(args.mode),
    )


def _run_folders_routine_queue(args: argparse.Namespace) -> int:
    try:
        watches = load_watched_folder_configuration(args.config_file)
        bindings = load_folder_routine_bindings(args.bindings_file)
        profiles = load_profile_configuration(args.profiles_dir)
        extractor = DocServicesBridge(
            plugin=_plugin_by_id(args.manifest_root, "doc-services"),
            provider_root=args.doc_services_root,
        )
        queue = build_folder_routine_queue(
            watches,
            bindings,
            profiles=profiles,
            as_of=args.as_of,
            captured_at=args.captured_at,
            state_dir=args.state_dir,
            extractor=extractor,
        )
    except (
        DirectoryObservationError,
        DocServicesBridgeError,
        ManifestValidationError,
        ProfileConfigurationError,
        RoutineQueueError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(queue.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_scheduler_plan(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_scheduler_handoff(args)
    except (SchedulerHandoffError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_scheduler_run(args: argparse.Namespace) -> int:
    try:
        plan = _prepare_scheduler_handoff(args)
        if args.schedule_id != plan.schedule_id:
            raise SchedulerHandoffError(
                "schedule_id stimmt nicht mit dem aktuellen Handoff-Plan überein."
            )
        captured_at = (
            datetime.now(UTC).isoformat().replace("+00:00", "Z")
            if args.captured_at == "auto"
            else args.captured_at
        )
        watches = load_watched_folder_configuration(plan.config_file)
        bindings = load_folder_routine_bindings(plan.bindings_file)
        profiles = load_profile_configuration(plan.profiles_dir)
        extractor = DocServicesBridge(
            plugin=_plugin_by_id(plan.manifest_root, "doc-services"),
            provider_root=plan.doc_services_root,
        )
        report = run_scheduler_queue(
            plan,
            captured_at=captured_at,
            watches=watches,
            bindings=bindings,
            profiles=profiles,
            extractor=extractor,
            allow_scheduler_state_write=args.approve_scheduler_state_write,
        )
    except (
        DirectoryObservationError,
        DocServicesBridgeError,
        ManifestValidationError,
        ProfileConfigurationError,
        RoutineQueueError,
        SchedulerHandoffError,
        OSError,
        ValueError,
    ) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return report.exit_code


def _prepare_scheduler_handoff(args: argparse.Namespace):
    return build_scheduler_handoff(
        task_name=args.task_name,
        interval_minutes=args.interval_minutes,
        start_at=args.start_at,
        timezone=args.timezone,
        config_file=args.config_file,
        bindings_file=args.bindings_file,
        profiles_dir=args.profiles_dir,
        state_dir=args.state_dir,
        manifest_root=args.manifest_root,
        doc_services_root=args.doc_services_root,
        python_executable=args.python_executable,
        working_directory=args.working_directory,
    )


def _read_contact_approval(path: Path) -> ContactRegisterApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContactWorkflowError(
            f"Kontaktfreigabe ist nicht lesbar: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        ContactRegisterApproval.SCHEMA
    ):
        raise ContactWorkflowError("Kontaktfreigabe verwendet ein unbekanntes Schema.")
    raw_action_ids = payload.get("action_ids")
    if not isinstance(raw_action_ids, list) or not all(
        isinstance(action_id, str) for action_id in raw_action_ids
    ):
        raise ContactWorkflowError("Kontaktfreigabe benötigt gültige action_ids.")
    try:
        return ContactRegisterApproval(
            approval_id=_contact_text(payload, "approval_id"),
            plan_id=_contact_text(payload, "plan_id"),
            register_revision=_contact_text(payload, "register_revision"),
            action_ids=tuple(raw_action_ids),
            approved_at=_contact_text(payload, "approved_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContactWorkflowError(f"Kontaktfreigabe ist ungültig: {exc}") from exc


def _read_calendar_approval(path: Path) -> CalendarHandoffApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalendarWorkflowError(
            f"Kalenderfreigabe ist nicht lesbar: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        CalendarHandoffApproval.SCHEMA
    ):
        raise CalendarWorkflowError("Kalenderfreigabe verwendet ein unbekanntes Schema.")
    raw_action_ids = payload.get("action_ids")
    if not isinstance(raw_action_ids, list) or not all(
        isinstance(action_id, str) for action_id in raw_action_ids
    ):
        raise CalendarWorkflowError("Kalenderfreigabe benötigt gültige action_ids.")
    try:
        return CalendarHandoffApproval(
            approval_id=_contact_text(payload, "approval_id"),
            plan_id=_contact_text(payload, "plan_id"),
            calendar_revision=_contact_text(payload, "calendar_revision"),
            action_ids=tuple(raw_action_ids),
            approved_at=_contact_text(payload, "approved_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CalendarWorkflowError(f"Kalenderfreigabe ist ungültig: {exc}") from exc


def _contact_text(payload: dict[str, object], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} muss ein nichtleerer Text sein.")
    return value


def _read_cleanup_approval(path: Path) -> FolderCleanupApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FolderCleanupError(f"Batchfreigabe ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        "folderhome.folder-cleanup-approval.v1"
    ):
        raise FolderCleanupError("Batchfreigabe verwendet ein unbekanntes Schema.")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise FolderCleanupError("Batchfreigabe benötigt eine items-Liste.")
    items = []
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise FolderCleanupError(
                f"Batchfreigabe-Element {index} muss ein JSON-Objekt sein."
            )
        action_ids = raw_item.get("action_ids")
        if not isinstance(action_ids, list) or not all(
            isinstance(action_id, str) for action_id in action_ids
        ):
            raise FolderCleanupError(
                f"Batchfreigabe-Element {index} benötigt gültige action_ids."
            )
        try:
            items.append(
                BatchItemApproval(
                    document_id=_cleanup_text(raw_item, "document_id", index),
                    plan_id=_cleanup_text(raw_item, "plan_id", index),
                    document_sha256=_cleanup_text(
                        raw_item,
                        "document_sha256",
                        index,
                    ),
                    action_ids=tuple(action_ids),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FolderCleanupError(
                f"Batchfreigabe-Element {index} ist ungültig: {exc}"
            ) from exc
    try:
        return FolderCleanupApproval(
            approval_id=_cleanup_text(payload, "approval_id", -1),
            batch_id=_cleanup_text(payload, "batch_id", -1),
            items=tuple(items),
            approved_at=_cleanup_text(payload, "approved_at", -1),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FolderCleanupError(f"Batchfreigabe ist ungültig: {exc}") from exc


def _cleanup_text(item: dict[str, object], field: str, index: int) -> str:
    value = item[field]
    if not isinstance(value, str) or not value:
        location = f"Element {index}" if index >= 0 else "Kopf"
        raise ValueError(f"{location}: {field} muss ein nichtleerer Text sein.")
    return value


def _run_folders_snapshot(args: argparse.Namespace) -> int:
    try:
        snapshot = snapshot_directory(
            args.source_dir,
            captured_at=args.captured_at,
            recursive=args.recursive,
        )
        snapshot_file = (
            write_directory_snapshot(
                snapshot,
                args.state_dir,
                allow_state_write=True,
            )
            if args.approve_state_write
            else None
        )
        payload = {
            "schema": "folderhome.directory-snapshot-workflow.v1",
            "snapshot": snapshot.to_dict(),
            "snapshot_file": str(snapshot_file) if snapshot_file else None,
        }
    except (DirectorySnapshotError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_folders_diff(args: argparse.Namespace) -> int:
    try:
        before = read_directory_snapshot(args.before_file)
        after = read_directory_snapshot(args.after_file)
        diff = build_directory_diff(before, after)
    except (DirectorySnapshotError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(diff.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _run_folders_learning(args: argparse.Namespace) -> int:
    try:
        before = read_directory_snapshot(args.before_file)
        after = read_directory_snapshot(args.after_file)
        diff = build_directory_diff(before, after)
        receipts = _read_placement_receipts(args.receipts_file)
        examples = build_learning_examples(diff, receipts)
    except (DirectorySnapshotError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    payload = {
        "schema": "folderhome.directory-learning.v1",
        "diff": diff.to_dict(),
        "examples": [example.to_dict() for example in examples],
        "automatic_promotion": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_folders_scan(args: argparse.Namespace) -> int:
    try:
        configuration = load_watched_folder_configuration(args.config_file)
        watch = next(
            (item for item in configuration.watches if item.watch_id == args.watch_id),
            None,
        )
        if watch is None:
            raise DirectoryObservationError(
                f"Unbekannter Beobachtungsordner: {args.watch_id}"
            )
        receipts = (
            _read_placement_receipts(args.receipts_file)
            if args.receipts_file is not None
            else ()
        )
        report = run_directory_scan(
            watch,
            captured_at=args.captured_at,
            state_dir=args.state_dir,
            receipts=receipts,
            allow_state_write=args.approve_state_write,
        )
    except (DirectoryObservationError, DirectorySnapshotError, OSError, ValueError) as exc:
        return _print_error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


def _read_placement_receipts(path: Path) -> tuple[PlacementReceipt, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DirectorySnapshotError(
            f"Ablagebelege sind nicht lesbar: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        "folderhome.placement-receipts.v1"
    ):
        raise DirectorySnapshotError("Ablagebelege verwenden ein unbekanntes Schema.")
    items = payload.get("receipts")
    if not isinstance(items, list):
        raise DirectorySnapshotError("Ablagebelege benötigen eine receipts-Liste.")
    receipts = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise DirectorySnapshotError(
                f"Ablagebeleg {index} muss ein JSON-Objekt sein."
            )
        source_rule_ids = item.get("source_rule_ids")
        if not isinstance(source_rule_ids, list) or not all(
            isinstance(rule_id, str) and rule_id.strip()
            for rule_id in source_rule_ids
        ):
            raise DirectorySnapshotError(
                f"Ablagebeleg {index} benötigt gültige source_rule_ids."
            )
        try:
            receipt = PlacementReceipt(
                receipt_id=_receipt_text(item, "receipt_id", index),
                document_sha256=_receipt_text(item, "document_sha256", index),
                placed_path=_receipt_text(item, "placed_path", index),
                profile_id=_receipt_text(item, "profile_id", index),
                area=_receipt_text(item, "area", index),
                source_rule_ids=tuple(source_rule_ids),
                root_path=(
                    Path(root_value)
                    if isinstance((root_value := item.get("root_path")), str)
                    and root_value.strip()
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DirectorySnapshotError(
                f"Ablagebeleg {index} ist ungültig: {exc}"
            ) from exc
        receipts.append(receipt)
    return tuple(receipts)


def _receipt_text(item: dict[str, object], field: str, index: int) -> str:
    value = item[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Feld {field} in Ablagebeleg {index} ist leer.")
    return value


def _document_plugins(manifest_root: Path) -> dict[str, PluginDescriptor]:
    plugins = {plugin.plugin_id: plugin for plugin in load_manifests(manifest_root)}
    missing = sorted({"doc-services", "KnowledgeDigest"}.difference(plugins))
    if missing:
        raise ManifestValidationError(
            f"Dokument-Provider-Manifest fehlt: {', '.join(missing)}"
        )
    return plugins


def _plugin_by_id(manifest_root: Path, plugin_id: str) -> PluginDescriptor:
    plugin = next(
        (item for item in load_manifests(manifest_root) if item.plugin_id == plugin_id),
        None,
    )
    if plugin is None:
        raise ManifestValidationError(f"Provider-Manifest fehlt: {plugin_id}")
    return plugin


def _preflight_new_outputs(*paths: Path | None) -> None:
    selected = [path.resolve() for path in paths if path is not None]
    if len(set(selected)) != len(selected):
        raise ValueError("Ausgabedateien müssen unterschiedliche Pfade verwenden.")
    existing = next((path for path in selected if path.exists()), None)
    if existing is not None:
        raise FileExistsError(f"Ausgabedatei existiert bereits: {existing}")


def _write_new_text(path: Path, content: str) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _json_text(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _print_error(message: str) -> int:
    print(json.dumps({"valid": False, "error": message}, ensure_ascii=False))
    return 2
