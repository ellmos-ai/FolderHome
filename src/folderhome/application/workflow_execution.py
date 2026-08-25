"""Typed, fail-closed handoff from master plans to existing domain executors."""

from __future__ import annotations

import json
import os
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, time
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.application.administrative_drafts import (
    AdministrativeDraftError,
    build_administrative_draft_plan,
    load_administrative_draft_request,
    write_administrative_draft,
)
from folderhome.application.artifact_studio import (
    ArtifactStudioError,
    build_design_preview,
    write_design_outputs,
)
from folderhome.application.benefit_screening import (
    BenefitScreeningError,
    load_benefit_catalog,
    load_benefit_profile_snapshot,
    screen_benefits,
    write_benefit_screening_report,
)
from folderhome.application.calendar_handoff import (
    CalendarDocumentExtractor,
    CalendarWorkflowError,
    analyze_folder_calendar,
    apply_calendar_handoff_plan,
    build_calendar_handoff_plan,
    load_calendar_configuration,
    resolve_calendar_preferences,
)
from folderhome.application.contacts import (
    ContactDocumentExtractor,
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
    render_daily_briefing,
)
from folderhome.application.directory_observation import (
    DirectoryObservationError,
    WatchedFolderConfiguration,
    run_directory_scan,
)
from folderhome.application.document_action_execution import (
    DocumentActionExecutionError,
    executable_action_prefix,
    execute_document_actions,
)
from folderhome.application.document_action_plan import (
    DocumentActionPlanError,
    build_document_action_plan,
)
from folderhome.application.document_package import (
    DocumentPackageError,
    PreparedDocumentPackage,
    prepare_folder_package,
    write_folder_package,
)
from folderhome.application.document_search import DocumentSearcher
from folderhome.application.document_transform import (
    BundleDocumentExtractor,
    DocumentTransformError,
    collect_bundle_documents,
    plan_document_bundle,
    write_document_bundle,
)
from folderhome.application.fcsa_plan import FcsaPlanProvider, run_fcsa_plan
from folderhome.application.finance_statements import (
    FinanceWorkflowError,
    StatementDocumentExtractor,
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
    CleanupDocumentExtractor,
    FolderCleanupError,
    build_folder_cleanup_plan,
    execute_folder_cleanup,
)
from folderhome.application.folder_routine import (
    FolderRoutineError,
    build_folder_routine_plan,
    execute_folder_routine,
)
from folderhome.application.health_dossier import (
    HealthDocumentExtractor,
    HealthDossierGateError,
    build_health_dossier,
)
from folderhome.application.household_inventory import (
    InventoryDocumentExtractor,
    InventoryWorkflowError,
    analyze_folder_inventory,
    apply_inventory_import_plan,
    build_inventory_import_plan,
)
from folderhome.application.legal_change_monitor import (
    LegalChangeMonitorError,
    compare_legal_source_snapshots,
    load_legal_interest_snapshot,
    load_legal_source_snapshot,
    write_legal_change_report,
)
from folderhome.application.mail_draft import (
    append_mail_draft,
    build_mail_draft_message,
    load_mail_draft_account,
)
from folderhome.application.master_agent import master_capability_catalog
from folderhome.application.medication_intake import (
    MedicationWorkflowError,
    build_medication_dose_id,
    confirm_medication_intake,
)
from folderhome.application.official_notices import (
    NoticeExtractor,
    OfficialNoticeError,
    analyze_official_notice,
    write_official_notice_report,
)
from folderhome.application.personal_notes import (
    apply_personal_note_plan,
    build_personal_note_plan,
)
from folderhome.application.profile_rules import (
    ProfileConfiguration,
    ProfileConfigurationError,
    resolve_profile_policy,
)
from folderhome.application.routine_queue import (
    FolderRoutineBindingConfiguration,
    RoutineQueueError,
    build_folder_routine_queue,
)
from folderhome.application.tax_workpaper import (
    TaxWorkflowError,
    build_tax_export_plan,
    export_tax_workpaper,
)
from folderhome.application.version_analysis import (
    DocumentVersionAnalysisError,
    analyze_document_versions,
)
from folderhome.bridges.fcsa import CONFIG_FILENAMES, FcsaBridgeError
from folderhome.bridges.law_checker import LawCheckerBridge, LawCheckerBridgeError
from folderhome.bridges.llm_note import LlmNoteBridge, LlmNoteBridgeError
from folderhome.bridges.tax_assistant import TaxAssistantBridge, TaxAssistantBridgeError
from folderhome.capabilities.calendar_store import CalendarStore, CalendarStoreError
from folderhome.capabilities.catalog import DocumentCatalogError, DocumentCatalogStore
from folderhome.capabilities.contact_registry import ContactRegisterError, ContactRegisterStore
from folderhome.capabilities.finance_store import FinanceStore, FinanceStoreError
from folderhome.capabilities.findcall import SyntheticFindCallProvider
from folderhome.capabilities.inventory_store import InventoryStore, InventoryStoreError
from folderhome.capabilities.mail_draft import (
    ImapDraftTransport,
    MailDraftError,
    MailDraftLedger,
    MailDraftTransport,
    read_mailbox_password,
)
from folderhome.capabilities.medication_store import MedicationStore, MedicationStoreError
from folderhome.capabilities.personal_note_guide import SyntheticPersonalNoteGuide
from folderhome.contracts import (
    ActionExecutionApproval,
    AdministrativeDraftApproval,
    AdministrativeDraftPlan,
    BatchItemApproval,
    BenefitScreeningReport,
    BriefingDeliveryApproval,
    BriefingRenderApproval,
    BundleFormat,
    BusinessCardContent,
    CalendarBackend,
    CalendarHandoffApproval,
    CalendarHandoffPlan,
    ContactRegisterApproval,
    ContactRegisterPlan,
    ContractCockpitReport,
    ContractCockpitRequest,
    CorrespondencePreview,
    DailyBriefingPlan,
    DailyBriefingRequest,
    DesignColors,
    DesignFonts,
    DesignPreview,
    DesignStudioRequest,
    DirectoryScanReport,
    DocumentBundlePlan,
    DocumentPolicyActionPlan,
    DocumentRecord,
    FinanceImportApproval,
    FinanceImportPlan,
    FindCallCandidate,
    FindCallFixtureOutcome,
    FindCallKind,
    FindCallPlan,
    FindCallStatus,
    FindCallWindow,
    FolderCleanupApproval,
    FolderCleanupPlan,
    FolderRoutineBinding,
    FolderRoutineMode,
    FolderRoutinePlan,
    FolderRoutineQueue,
    HealthDossierReport,
    InventoryImportApproval,
    InventoryImportPlan,
    LegalChangeMonitorReport,
    OfficialNoticeAnalysis,
    PluginDescriptor,
    RunReport,
    TaxExportApproval,
    TaxExportPlan,
    WatchedFolder,
)
from folderhome.contracts.mail_draft import (
    MAIL_DRAFT_PROVIDER_ID,
    MailDraftAccount,
    MailDraftMessage,
)
from folderhome.contracts.medication import MedicationIntakeConfirmation
from folderhome.contracts.personal_notes import (
    PersonalNoteAction,
    PersonalNoteApproval,
    PersonalNotePlan,
    PersonalNoteReference,
    PersonalNoteRequest,
)
from folderhome.contracts.resources import (
    LogicalResource,
    ResourceRegistry,
    ResourceRegistryError,
)
from folderhome.contracts.workflow_execution import (
    WorkflowAdapterDescriptor,
    WorkflowExecutionEnvelope,
    WorkflowExecutionReport,
)

_MAX_PREPARED_EXECUTIONS = 128

_LOCAL_ADAPTER_AVAILABLE_WORKFLOWS = frozenset(
    {
        "findcall",
        "medication-intake",
        "personal-notes",
    }
)
_RESOURCE_ID_REQUIRED_WORKFLOWS = frozenset(
    {
        "administrative-drafts",
        "artifact-studio",
        "benefit-screening",
        "contact-register",
        "contract-cockpit",
        "correspondence-studio",
        "daily-briefing",
        "directory-observation",
        "document-action-execution",
        "document-action-plan",
        "document-bundle",
        "document-package",
        "fcsa-dry-run",
        "finance-import",
        "folder-cleanup",
        "folder-routine",
        "health-dossier",
        "inventory-import",
        "legal-change-monitor",
        "official-notice-understanding",
        "routine-queue",
        "tax-workpaper",
    }
)
_EXTERNAL_CONNECTOR_REQUIRED_WORKFLOWS = frozenset(
    {
        "calendar-connectors",
        "calendar-handoff",
        "mail-connector",
        "scheduler-handoff",
    }
)

_PERSONAL_NOTES_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action", "notebook_id", "area", "title"],
    "properties": {
        "action": {"enum": ["create", "edit", "revert"]},
        "notebook_id": {"type": "string", "minLength": 1, "maxLength": 80},
        "area": {"type": "string", "minLength": 1, "maxLength": 80},
        "title": {"type": "string", "minLength": 1, "maxLength": 160},
        "human_content": {"type": ["string", "null"]},
        "note_id": {"type": ["string", "null"]},
        "expected_revision": {"type": ["integer", "null"], "minimum": 1},
        "revert_to_revision": {"type": ["integer", "null"], "minimum": 1},
        "references": {"type": "array"},
    },
}

_MEDICATION_INTAKE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action", "scheduled_date", "confirmed_at"],
    "properties": {
        "action": {"const": "confirm_taken"},
        "scheduled_date": {"type": "string", "format": "date"},
        "confirmed_at": {"type": "string", "format": "date-time"},
        "schedule_id": {"type": ["string", "null"]},
        "medication_name": {"type": ["string", "null"], "maxLength": 160},
        "scheduled_time": {
            "type": ["string", "null"],
            "pattern": "^[0-2][0-9]:[0-5][0-9]$",
        },
    },
}

_FINDCALL_WINDOW_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["start_at", "end_at"],
    "properties": {
        "start_at": {"type": "string", "format": "date-time"},
        "end_at": {"type": "string", "format": "date-time"},
    },
}

_FINDCALL_FIXTURE_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "service_confirmed",
        "available",
        "offered_window",
        "price_known",
        "price_eur",
        "commitment_made",
        "summary",
    ],
    "properties": {
        "status": {
            "enum": [
                "COMPLETED",
                "FAILED",
                "NO_ANSWER",
                "DECLINED",
                "CANCELED",
                "VOICEMAIL",
                "BUSY",
                "EXPIRED",
            ]
        },
        "service_confirmed": {"type": "boolean"},
        "available": {"type": "boolean"},
        "offered_window": {
            "oneOf": [_FINDCALL_WINDOW_SCHEMA, {"type": "null"}],
        },
        "price_known": {"type": "boolean"},
        "price_eur": {"type": ["number", "null"], "minimum": 0},
        "commitment_made": {"const": False},
        "summary": {"type": "string", "minLength": 1, "maxLength": 500},
    },
}

_FINDCALL_FIXTURE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "action",
        "planned_at",
        "area",
        "kind",
        "service",
        "location",
        "windows",
        "max_distance_km",
        "max_price_eur",
        "candidates",
    ],
    "properties": {
        "action": {"const": "simulate"},
        "planned_at": {"type": "string", "format": "date-time"},
        "area": {"type": "string", "minLength": 1, "maxLength": 80},
        "kind": {"enum": ["appointment", "quote"]},
        "service": {"type": "string", "minLength": 1, "maxLength": 200},
        "location": {"type": "string", "minLength": 1, "maxLength": 200},
        "windows": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": _FINDCALL_WINDOW_SCHEMA,
        },
        "max_distance_km": {"type": ["number", "null"], "minimum": 0},
        "max_price_eur": {"type": ["number", "null"], "minimum": 0},
        "candidates": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "phone_e164",
                    "services",
                    "distance_km",
                    "priority",
                    "fixture",
                ],
                "properties": {
                    "name": {"type": "string", "minLength": 1, "maxLength": 160},
                    "phone_e164": {
                        "type": "string",
                        "pattern": "^\\+[1-9][0-9]{7,14}$",
                    },
                    "services": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 20,
                        "items": {"type": "string", "minLength": 1, "maxLength": 200},
                    },
                    "distance_km": {"type": ["number", "null"], "minimum": 0},
                    "priority": {"type": "integer", "minimum": -100, "maximum": 100},
                    "fixture": _FINDCALL_FIXTURE_SCHEMA,
                },
            },
        },
    },
}

_DOCUMENT_BUNDLE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "output_resource_id",
        "output_name",
        "format",
        "recursive",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_name": {"type": "string", "minLength": 5, "maxLength": 160},
        "format": {"enum": ["pdf", "txt"]},
        "recursive": {"type": "boolean"},
    },
}

_CONTACT_REGISTER_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "state_resource_id",
        "area",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "area": {"type": "string", "minLength": 1, "maxLength": 80},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_CORRESPONDENCE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "request_resource_id",
        "designs_resource_id",
        "templates_resource_id",
        "output_resource_id",
        "output_basename",
    ],
    "properties": {
        "request_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "designs_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "templates_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
    },
}

_MAIL_DRAFT_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "account_resource_id",
        "request_resource_id",
        "designs_resource_id",
        "templates_resource_id",
        "planned_at",
    ],
    "properties": {
        "account_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "request_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "designs_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "templates_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "planned_at": {"type": "string", "minLength": 20, "maxLength": 40},
    },
}

_LOCAL_CALENDAR_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "configuration_resource_id",
        "state_resource_id",
        "area",
        "planned_at",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "configuration_resource_id": {
            "type": "string",
            "minLength": 2,
            "maxLength": 64,
        },
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "area": {"type": "string", "minLength": 1, "maxLength": 80},
        "planned_at": {"type": "string", "format": "date-time"},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_HEALTH_DOSSIER_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "output_resource_id",
        "output_basename",
        "as_of",
        "recursive",
        "gap_threshold_days",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "as_of": {"type": "string", "format": "date"},
        "recursive": {"type": "boolean"},
        "gap_threshold_days": {"type": "integer", "minimum": 1, "maximum": 3650},
    },
}

_FINANCE_IMPORT_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "state_resource_id",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_OFFICIAL_NOTICE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "output_resource_id",
        "output_basename",
        "received_on",
        "as_of",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "received_on": {"type": ["string", "null"], "format": "date"},
        "as_of": {"type": "string", "format": "date-time"},
    },
}

_ADMINISTRATIVE_DRAFT_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "request_resource_id",
        "notice_resource_id",
        "designs_resource_id",
        "templates_resource_id",
        "output_resource_id",
        "output_basename",
        "received_on",
        "as_of",
    ],
    "properties": {
        "request_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "notice_resource_id": {"type": ["string", "null"], "maxLength": 64},
        "designs_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "templates_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "received_on": {"type": ["string", "null"], "format": "date"},
        "as_of": {"type": "string", "format": "date-time"},
    },
}

_BENEFIT_SCREENING_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "profile_resource_id",
        "catalog_resource_id",
        "output_resource_id",
        "output_basename",
        "as_of",
        "max_source_age_days",
    ],
    "properties": {
        "profile_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "catalog_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "as_of": {"type": "string", "format": "date-time"},
        "max_source_age_days": {"type": "integer", "minimum": 1, "maximum": 3650},
    },
}

_LEGAL_CHANGE_MONITOR_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "before_resource_id",
        "after_resource_id",
        "interests_resource_id",
        "output_resource_id",
        "output_basename",
        "as_of",
        "max_source_age_days",
        "allow_test_fixture",
    ],
    "properties": {
        "before_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "after_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "interests_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "as_of": {"type": "string", "format": "date-time"},
        "max_source_age_days": {"type": "integer", "minimum": 1, "maximum": 3650},
        "allow_test_fixture": {"type": "boolean"},
    },
}

_INVENTORY_IMPORT_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "state_resource_id",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_DAILY_BRIEFING_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "weather_resource_id",
        "news_resource_id",
        "output_resource_id",
        "desktop_resource_id",
        "output_name",
        "desktop_name",
        "briefing_date",
        "as_of",
        "timezone",
        "title",
        "categories",
        "max_items_per_category",
        "max_weather_age_minutes",
        "max_news_age_minutes",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "weather_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "news_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "desktop_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_name": {"type": "string", "minLength": 1, "maxLength": 140},
        "desktop_name": {"type": "string", "minLength": 1, "maxLength": 140},
        "briefing_date": {"type": "string", "format": "date"},
        "as_of": {"type": "string", "format": "date-time"},
        "timezone": {"type": "string", "minLength": 1, "maxLength": 80},
        "title": {"type": "string", "minLength": 1, "maxLength": 120},
        "categories": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 2, "maxLength": 32},
        },
        "max_items_per_category": {"type": "integer", "minimum": 1, "maximum": 25},
        "max_weather_age_minutes": {"type": "integer", "minimum": 1, "maximum": 1440},
        "max_news_age_minutes": {"type": "integer", "minimum": 1, "maximum": 10080},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_TAX_WORKPAPER_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "state_resource_id",
        "output_resource_id",
        "output_name",
        "tax_year",
    ],
    "properties": {
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_name": {"type": "string", "minLength": 5, "maxLength": 140},
        "tax_year": {"type": "integer", "minimum": 2000, "maximum": 2100},
    },
}

_FOLDER_CLEANUP_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "target_resource_id",
        "state_resource_id",
        "area",
        "as_of",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "target_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "area": {"type": "string", "minLength": 2, "maxLength": 64},
        "as_of": {"type": "string", "format": "date"},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_DIRECTORY_OBSERVATION_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "state_resource_id",
        "watch_id",
        "area",
        "captured_at",
        "interval_minutes",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "watch_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "area": {"type": "string", "minLength": 2, "maxLength": 64},
        "captured_at": {"type": "string", "format": "date-time"},
        "interval_minutes": {"type": "integer", "minimum": 1},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_DOCUMENT_PACKAGE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "output_resource_id",
        "output_name",
        "recursive",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_name": {"type": "string", "minLength": 5, "maxLength": 140},
        "recursive": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_DOCUMENT_ACTION_PLAN_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "target_resource_id",
        "output_resource_id",
        "output_name",
        "area",
        "as_of",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "target_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_name": {"type": "string", "minLength": 1, "maxLength": 140},
        "area": {"type": "string", "minLength": 2, "maxLength": 64},
        "as_of": {"type": "string", "format": "date"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_DOCUMENT_ACTION_EXECUTION_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "target_resource_id",
        "state_resource_id",
        "area",
        "as_of",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "target_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "area": {"type": "string", "minLength": 2, "maxLength": 64},
        "as_of": {"type": "string", "format": "date"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_FOLDER_ROUTINE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_resource_id",
        "target_resource_id",
        "state_resource_id",
        "watch_id",
        "area",
        "as_of",
        "captured_at",
        "completed_at",
        "interval_minutes",
        "recursive",
        "mode",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "source_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "target_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "watch_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "area": {"type": "string", "minLength": 2, "maxLength": 64},
        "as_of": {"type": "string", "format": "date"},
        "captured_at": {"type": "string", "format": "date-time"},
        "completed_at": {"type": "string", "format": "date-time"},
        "interval_minutes": {"type": "integer", "minimum": 1},
        "recursive": {"type": "boolean"},
        "mode": {"type": "string", "enum": ["changes", "full"]},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_ROUTINE_QUEUE_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "state_resource_id",
        "output_resource_id",
        "output_name",
        "as_of",
        "captured_at",
        "items",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_name": {"type": "string", "minLength": 1, "maxLength": 140},
        "as_of": {"type": "string", "format": "date"},
        "captured_at": {"type": "string", "format": "date-time"},
        "items": {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "watch_id",
                    "binding_id",
                    "source_resource_id",
                    "target_resource_id",
                    "area",
                    "interval_minutes",
                    "recursive",
                    "mode",
                    "enabled",
                ],
                "properties": {
                    "watch_id": {"type": "string", "minLength": 2, "maxLength": 64},
                    "binding_id": {"type": "string", "minLength": 2, "maxLength": 64},
                    "source_resource_id": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 64,
                    },
                    "target_resource_id": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 64,
                    },
                    "area": {"type": "string", "minLength": 2, "maxLength": 64},
                    "interval_minutes": {"type": "integer", "minimum": 1},
                    "recursive": {"type": "boolean"},
                    "mode": {"type": "string", "enum": ["changes", "full"]},
                    "enabled": {"type": "boolean"},
                },
            },
        },
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_ARTIFACT_STUDIO_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "output_resource_id",
        "output_basename",
        "design_set_id",
        "display_name",
        "purpose",
        "colors",
        "fonts",
        "business_card",
    ],
    "properties": {
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "design_set_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "display_name": {"type": "string", "minLength": 1, "maxLength": 160},
        "purpose": {"type": "string", "minLength": 1, "maxLength": 300},
        "colors": {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary", "on_primary", "background", "text", "accent"],
            "properties": {
                key: {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"}
                for key in ("primary", "on_primary", "background", "text", "accent")
            },
        },
        "fonts": {
            "type": "object",
            "additionalProperties": False,
            "required": ["heading", "body"],
            "properties": {
                "heading": {"type": "string", "minLength": 1, "maxLength": 80},
                "body": {"type": "string", "minLength": 1, "maxLength": 80},
            },
        },
        "business_card": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "role", "organization", "email", "phone", "website"],
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 160},
                "role": {"type": "string", "minLength": 1, "maxLength": 160},
                "organization": {"type": "string", "minLength": 1, "maxLength": 160},
                "email": {"type": ["string", "null"], "maxLength": 160},
                "phone": {"type": ["string", "null"], "maxLength": 160},
                "website": {"type": ["string", "null"], "maxLength": 160},
            },
        },
    },
}

_CONTRACT_COCKPIT_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "state_resource_id",
        "output_resource_id",
        "output_basename",
        "area",
        "display_name",
        "document_query",
        "object_ref",
        "counterparty_terms",
        "calendar_terms",
        "account_refs",
        "coverage_start",
        "as_of",
        "archive_older_versions",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "state_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "output_basename": {"type": "string", "minLength": 1, "maxLength": 140},
        "area": {"type": "string", "minLength": 1, "maxLength": 80},
        "display_name": {"type": "string", "minLength": 1, "maxLength": 200},
        "document_query": {"type": "string", "minLength": 1, "maxLength": 500},
        "object_ref": {"type": "string", "minLength": 1, "maxLength": 200},
        "counterparty_terms": {"type": "array", "items": {"type": "string"}},
        "calendar_terms": {"type": "array", "items": {"type": "string"}},
        "account_refs": {"type": "array", "items": {"type": "string"}},
        "coverage_start": {"type": "string", "format": "date"},
        "as_of": {"type": "string", "format": "date"},
        "archive_older_versions": {"type": "boolean"},
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}

_FCSA_DRY_RUN_REQUEST_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "config_resource_id",
        "scan_resource_ids",
        "target_resource_ids",
        "allow_sensitive_local_read",
    ],
    "properties": {
        "config_resource_id": {"type": "string", "minLength": 2, "maxLength": 64},
        "scan_resource_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 2, "maxLength": 64},
        },
        "target_resource_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 2, "maxLength": 64},
        },
        "allow_sensitive_local_read": {"type": "boolean"},
    },
}


class WorkflowExecutionError(RuntimeError):
    """Raised before an untyped, stale, repeated or unsupported execution."""


class WorkflowExecutorAdapter(Protocol):
    descriptor: WorkflowAdapterDescriptor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, object]: ...

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport: ...


@dataclass(frozen=True, slots=True)
class _PreparedExecution:
    adapter: WorkflowExecutorAdapter
    envelope: WorkflowExecutionEnvelope
    domain_plan: object


@dataclass(frozen=True, slots=True)
class _PreparedFindCallFixture:
    plan: FindCallPlan
    outcomes: dict[str, FindCallFixtureOutcome]


@dataclass(frozen=True, slots=True)
class _PreparedDocumentBundle:
    plan: DocumentBundlePlan
    documents: tuple[DocumentRecord, ...]
    public_plan: dict[str, object]
    output_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedContactRegister:
    plan: ContactRegisterPlan
    public_plan: dict[str, object]
    store: ContactRegisterStore
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedCorrespondence:
    preview: CorrespondencePreview
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedMailDraft:
    message: MailDraftMessage
    public_plan: dict[str, object]
    account: MailDraftAccount
    account_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedLocalCalendar:
    plan: CalendarHandoffPlan
    public_plan: dict[str, object]
    store: CalendarStore
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedHealthDossier:
    report: HealthDossierReport
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedFinanceImport:
    plan: FinanceImportPlan
    public_plan: dict[str, object]
    store: FinanceStore
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedOfficialNotice:
    analysis: OfficialNoticeAnalysis
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedAdministrativeDraft:
    plan: AdministrativeDraftPlan
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedBenefitScreening:
    report: BenefitScreeningReport
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedLegalChangeMonitor:
    report: LegalChangeMonitorReport
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedInventoryImport:
    plan: InventoryImportPlan
    public_plan: dict[str, object]
    store: InventoryStore
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedDailyBriefing:
    plan: DailyBriefingPlan
    public_plan: dict[str, object]
    output_resource_id: str
    desktop_resource_id: str
    output_name: str
    desktop_name: str


@dataclass(frozen=True, slots=True)
class _PreparedTaxWorkpaper:
    plan: TaxExportPlan
    public_plan: dict[str, object]
    bridge: TaxAssistantBridge
    state_resource_id: str
    output_resource_id: str
    output_name: str


@dataclass(frozen=True, slots=True)
class _PreparedFolderCleanup:
    plan: FolderCleanupPlan
    public_plan: dict[str, object]
    state_root: Path
    source_resource_id: str
    target_resource_id: str
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedDirectoryObservation:
    scan: DirectoryScanReport
    public_plan: dict[str, object]
    state_root: Path
    source_resource_id: str
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedDocumentPackage:
    prepared: PreparedDocumentPackage
    public_plan: dict[str, object]
    source_resource_id: str
    output_resource_id: str
    output_name: str


@dataclass(frozen=True, slots=True)
class _PreparedDocumentActionPlan:
    plan: DocumentPolicyActionPlan
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_name: str


@dataclass(frozen=True, slots=True)
class _PreparedDocumentActionExecution:
    plan: DocumentPolicyActionPlan
    public_plan: dict[str, object]
    state_root: Path
    source_resource_id: str
    target_resource_id: str
    state_resource_id: str


@dataclass(frozen=True, slots=True)
class _PreparedFolderRoutine:
    plan: FolderRoutinePlan
    public_plan: dict[str, object]
    state_root: Path
    source_resource_id: str
    target_resource_id: str
    state_resource_id: str
    completed_at: str


@dataclass(frozen=True, slots=True)
class _PreparedRoutineQueue:
    queue: FolderRoutineQueue
    public_plan: dict[str, object]
    watches: WatchedFolderConfiguration
    bindings: FolderRoutineBindingConfiguration
    profiles: ProfileConfiguration
    state_root: Path
    extractor: CleanupDocumentExtractor
    as_of: date
    captured_at: str
    output_root: Path
    output_resource_id: str
    output_name: str


@dataclass(frozen=True, slots=True)
class _PreparedArtifactStudio:
    preview: DesignPreview
    public_plan: dict[str, object]
    output_root: Path
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedContractCockpit:
    report: ContractCockpitReport
    public_plan: dict[str, object]
    state_root: Path
    output_root: Path
    state_resource_id: str
    output_resource_id: str
    output_basename: str


@dataclass(frozen=True, slots=True)
class _PreparedFcsaDryRun:
    public_plan: dict[str, object]
    config_root: Path
    config_hashes: dict[str, str]
    run_id: str


class WorkflowExecutionGateway:
    """Registry and in-memory binding for typed plans prepared in one app session."""

    def __init__(self, adapters: tuple[WorkflowExecutorAdapter, ...] = ()) -> None:
        by_workflow = {item.descriptor.workflow_id: item for item in adapters}
        if len(by_workflow) != len(adapters):
            raise WorkflowExecutionError("Workflow-Adapter müssen eindeutig sein.")
        self._adapters = by_workflow
        self._prepared: dict[str, _PreparedExecution] = {}
        self._executed: set[str] = set()
        self._lock = threading.RLock()

    def catalog(self) -> tuple[WorkflowAdapterDescriptor, ...]:
        """Expose exact coverage for every declared FolderHome workflow."""

        descriptors = []
        for capability in master_capability_catalog():
            adapter = self._adapters.get(capability.workflow_id)
            if adapter is not None:
                descriptors.append(adapter.descriptor)
            elif capability.execution_mode == "direct_read_only":
                descriptors.append(
                    WorkflowAdapterDescriptor(
                        workflow_id=capability.workflow_id,
                        adapter_id=None,
                        status="direct_read_only",
                        plan_schema=None,
                        report_schema=None,
                        side_effects=(),
                        reason="The master agent already exposes a bounded read-only tool.",
                    )
                )
            elif capability.execution_mode == "planning_only":
                descriptors.append(
                    WorkflowAdapterDescriptor(
                        workflow_id=capability.workflow_id,
                        adapter_id=None,
                        status="planning_only",
                        plan_schema=None,
                        report_schema=None,
                        side_effects=(),
                        reason="This system endpoint is intentionally planning-only.",
                    )
                )
            else:
                descriptors.append(
                    WorkflowAdapterDescriptor(
                        workflow_id=capability.workflow_id,
                        adapter_id=None,
                        status="not_connected",
                        plan_schema=None,
                        report_schema=None,
                        side_effects=capability.side_effects,
                        reason=_unconnected_reason(capability.workflow_id),
                    )
                )
        return tuple(descriptors)

    def coverage(self) -> dict[str, int]:
        """Return non-overlapping runtime counts for the complete catalog."""

        counts = {
            "connected": 0,
            "direct_read_only": 0,
            "planning_only": 0,
            "not_connected": 0,
        }
        for descriptor in self.catalog():
            counts[descriptor.status] += 1
        counts["total"] = sum(counts.values())
        return counts

    def descriptor(self, workflow_id: str) -> WorkflowAdapterDescriptor:
        matches = {item.workflow_id: item for item in self.catalog()}
        try:
            return matches[workflow_id]
        except KeyError as exc:
            raise WorkflowExecutionError(f"Unbekannter Workflow: {workflow_id}") from exc

    def prepare(
        self,
        *,
        workflow_id: str,
        profile_id: str,
        request: dict[str, object],
    ) -> WorkflowExecutionEnvelope:
        adapter = self._adapters.get(workflow_id)
        if adapter is None:
            raise WorkflowExecutionError(
                f"Workflow besitzt noch keinen typisierten Executor-Adapter: {workflow_id}"
            )
        envelope, domain_plan = adapter.prepare(
            profile_id=profile_id,
            request=dict(request),
        )
        with self._lock:
            if (
                envelope.envelope_id not in self._prepared
                and len(self._prepared) >= _MAX_PREPARED_EXECUTIONS
            ):
                oldest_id = next(iter(self._prepared))
                if oldest_id not in self._executed:
                    del self._prepared[oldest_id]
                else:
                    raise WorkflowExecutionError(
                        "Vorbereitungsbudget ist belegt; App-Sitzung muss neu gestartet werden."
                    )
            self._prepared[envelope.envelope_id] = _PreparedExecution(
                adapter=adapter,
                envelope=envelope,
                domain_plan=domain_plan,
            )
        return envelope

    def execute(
        self,
        *,
        envelope_id: str,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        with self._lock:
            prepared = self._prepared.get(envelope_id)
            if prepared is None:
                raise WorkflowExecutionError(
                    "Ausführungshülle ist in dieser App-Sitzung nicht vorbereitet."
                )
            if envelope_id in self._executed:
                raise WorkflowExecutionError("Ausführungshülle wurde bereits ausgeführt.")
            report = prepared.adapter.execute(
                envelope=prepared.envelope,
                domain_plan=prepared.domain_plan,
                approved_at=approved_at,
            )
            self._executed.add(envelope_id)
            return report

    def discard_unexecuted(self, envelope_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Forget named in-memory preparations that have never been executed."""

        discarded = []
        with self._lock:
            for envelope_id in dict.fromkeys(envelope_ids):
                if envelope_id in self._executed:
                    continue
                if self._prepared.pop(envelope_id, None) is not None:
                    discarded.append(envelope_id)
        return tuple(discarded)


class HealthDossierWorkflowAdapter:
    """Build a sensitive local health dossier and disclose only metadata to the agent."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="health-dossier",
        adapter_id="health_dossier_resource.v1",
        status="connected",
        plan_schema="folderhome.health-dossier-resource-plan.v1",
        report_schema="folderhome.health-dossier-resource-output.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the existing extractive, evidence-bound health dossier. The source "
            "resource must explicitly allow sensitive_read and report content stays local."
        ),
        request_schema=_HEALTH_DOSSIER_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: HealthDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedHealthDossier]:
        expected = {
            "source_resource_id",
            "output_resource_id",
            "output_basename",
            "as_of",
            "recursive",
            "gap_threshold_days",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Gesundheitsdossieranfrage: "
                + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Gesundheitsdossieranfrage fehlt Feld: " + missing[0]
            )
        source_id = _text(request["source_resource_id"], "source_resource_id")
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_basename = _safe_output_basename(request["output_basename"])
        recursive = _required_bool(request["recursive"], "recursive")
        gap_threshold = _required_int(
            request["gap_threshold_days"],
            "gap_threshold_days",
        )
        if not 1 <= gap_threshold <= 3650:
            raise WorkflowExecutionError(
                "gap_threshold_days muss zwischen 1 und 3650 liegen."
            )
        try:
            as_of = date.fromisoformat(_text(request["as_of"], "as_of"))
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="health.source",
                required_kind="directory",
                required_operations=frozenset(
                    {"list", "read", "sensitive_read"}
                ),
            )
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="health.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_separate_resources(source.local_path, output.local_path)
            report = build_health_dossier(
                source.local_path,
                profile_id=profile_id,
                as_of=as_of,
                extractor=self._extractor,
                allow_sensitive_local_read=True,
                recursive=recursive,
                gap_threshold_days=gap_threshold,
            )
        except (
            HealthDossierGateError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        report_digest = sha256(
            _canonical_json(_redact_physical_paths(report.to_dict()))
        ).hexdigest()
        public_plan = {
            "schema": "folderhome.health-dossier-resource-plan.v1",
            "report_id": report.report_id,
            "profile_id": profile_id,
            "source_resource_id": source.resource_id,
            "output_resource_id": output.resource_id,
            "output_basename": output_basename,
            "as_of": report.as_of,
            "source_count": len(report.sources),
            "included_source_count": sum(
                item.status == "included" for item in report.sources
            ),
            "timeline_entry_count": len(report.timeline),
            "conflict_count": len(report.conflicts),
            "report_sha256": report_digest,
            "medical_advice": False,
            "completeness_claimed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "health_dossier_resource.v1",
            domain_plan_id=report.report_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_sensitive_local_report_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedHealthDossier(
            report=report,
            public_plan=public_plan,
            output_root=output.local_path,
            output_resource_id=output.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedHealthDossier):
            raise WorkflowExecutionError(
                "Vorbereitetes Gesundheitsdossier besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.report.report_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Gesundheitsdossier überein."
            )
        json_payload = _redact_physical_paths(domain_plan.report.to_dict())
        outputs = {
            f"{domain_plan.output_basename}.md": domain_plan.report.markdown,
            f"{domain_plan.output_basename}.json": json.dumps(
                json_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
        }
        try:
            output_hashes = _publish_private_text_outputs(
                domain_plan.output_root,
                outputs,
            )
        except (OSError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.health-dossier-resource-output.v1",
            "report_id": domain_plan.report.report_id,
            "output_resource_id": domain_plan.output_resource_id,
            "outputs": [
                {"name": name, "sha256": digest}
                for name, digest in sorted(output_hashes.items())
            ],
            "medical_advice": False,
            "completeness_claimed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
            "status": "executed",
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "health_dossier_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class FinanceImportWorkflowAdapter:
    """Import evidenced statements into the private local finance store."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="finance-import",
        adapter_id="finance_import_resource.v1",
        status="connected",
        plan_schema="folderhome.finance-import-resource-plan.v1",
        report_schema="folderhome.finance-import-resource-report.v1",
        side_effects=("state.finance.write",),
        reason=(
            "Reuses the existing cent-exact, revision-bound finance import through "
            "profile-scoped resource IDs. Statement content remains local and no bank "
            "connection is opened."
        ),
        request_schema=_FINANCE_IMPORT_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: StatementDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedFinanceImport]:
        expected = {
            "source_resource_id",
            "state_resource_id",
            "recursive",
            "allow_sensitive_local_read",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Finanzimportanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError("Finanzimportanfrage fehlt Feld: " + missing[0])
        source_id = _text(request["source_resource_id"], "source_resource_id")
        state_id = _text(request["state_resource_id"], "state_resource_id")
        recursive = _required_bool(request["recursive"], "recursive")
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        source_operations = {"list", "read"}
        if sensitive_read:
            source_operations.add("sensitive_read")
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="finance.source",
                required_kind="directory",
                required_operations=frozenset(source_operations),
            )
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="finance.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_separate_resources(source.local_path, state.local_path)
            analysis = analyze_folder_statements(
                source.local_path,
                profile_id=profile_id,
                extractor=self._extractor,
                recursive=recursive,
                allow_sensitive_local_read=sensitive_read,
            )
            store = FinanceStore(state.local_path)
            plan = build_finance_import_plan(analysis, store=store)
        except (
            FinanceStoreError,
            FinanceWorkflowError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_finance_import_plan(
            plan,
            source_resource_id=source.resource_id,
            state_resource_id=state.resource_id,
        )
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "finance_import_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_sensitive_local_finance_state_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedFinanceImport(
            plan=plan,
            public_plan=public_plan,
            store=store,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedFinanceImport):
            raise WorkflowExecutionError("Vorbereiteter Finanzimport besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Finanzimportplan überein."
            )
        action_ids = tuple(
            item.action_id
            for item in domain_plan.plan.actions
            if item.status == "planned"
        )
        if not action_ids:
            raise WorkflowExecutionError(
                "Finanzimportplan enthält keinen ausführbaren neuen Auszug."
            )
        approval = FinanceImportApproval(
            approval_id=f"agent_finance_{secrets.token_hex(10)}",
            plan_id=domain_plan.plan.plan_id,
            finance_revision=domain_plan.plan.finance_revision,
            action_ids=action_ids,
            approved_at=approved_at,
        )
        try:
            report = apply_finance_import_plan(
                domain_plan.plan,
                approval,
                store=domain_plan.store,
                allow_state_write=True,
            )
        except (FinanceStoreError, FinanceWorkflowError, OSError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.finance-import-resource-report.v1",
            "report_id": report.report_id,
            "status": report.status,
            "state_resource_id": domain_plan.state_resource_id,
            "revision_before": report.revision_before,
            "revision_after": report.revision_after,
            "created_statement_count": len(report.created_statement_ids),
            "created_transaction_count": len(report.created_transaction_ids),
            "bank_access_performed": False,
            "financial_advice": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "finance_import_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class OfficialNoticeWorkflowAdapter:
    """Explain one official notice locally and publish a private evidence report."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="official-notice-understanding",
        adapter_id="official_notice_resource.v1",
        status="connected",
        plan_schema="folderhome.official-notice-resource-plan.v1",
        report_schema="folderhome.official-notice-resource-report.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the existing extractive notice analysis through private resources. "
            "It never calculates a legal deadline, performs legal review, or sends a reply."
        ),
        request_schema=_OFFICIAL_NOTICE_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: NoticeExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedOfficialNotice]:
        expected = {
            "source_resource_id",
            "output_resource_id",
            "output_basename",
            "received_on",
            "as_of",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Bescheidanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError("Bescheidanfrage fehlt Feld: " + missing[0])
        source_id = _text(request["source_resource_id"], "source_resource_id")
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_basename = _safe_output_basename(request["output_basename"])
        received_on = _optional_text(request["received_on"], "received_on")
        as_of = _text(request["as_of"], "as_of")
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="official_notice.source",
                required_kind="file",
                required_operations=frozenset({"read", "sensitive_read"}),
            )
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="official_notice.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_separate_resources(source.local_path, output.local_path)
            analysis = analyze_official_notice(
                source.local_path,
                profile_id=profile_id,
                received_on=received_on,
                as_of=as_of,
                extractor=self._extractor,
                allow_sensitive_local_read=True,
            )
        except (
            OfficialNoticeError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.official-notice-resource-plan.v1",
            "analysis_id": analysis.analysis_id,
            "profile_id": profile_id,
            "source_resource_id": source.resource_id,
            "output_resource_id": output.resource_id,
            "output_basename": output_basename,
            "status": analysis.status,
            "deadline_urgency": analysis.deadline_urgency,
            "evidence_count": len(analysis.evidence),
            "missing_field_count": len(analysis.missing_fields),
            "conflict_count": len(analysis.conflicts),
            "warning_count": len(analysis.warnings),
            "received_on_basis": analysis.received_on_basis,
            "legal_review_status": "not_performed",
            "deadline_legally_calculated": False,
            "response_generated": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "official_notice_resource.v1",
            domain_plan_id=analysis.analysis_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_sensitive_local_notice_report_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedOfficialNotice(
            analysis=analysis,
            public_plan=public_plan,
            output_root=output.local_path,
            output_resource_id=output.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedOfficialNotice):
            raise WorkflowExecutionError("Vorbereitete Bescheidanalyse besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.analysis.analysis_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Bescheidanalyse überein."
            )
        try:
            report = write_official_notice_report(
                domain_plan.analysis,
                markdown_path=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.md"
                ),
                json_path=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.json"
                ),
                allow_output_write=True,
            )
        except (OfficialNoticeError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.official-notice-resource-report.v1",
            "report_id": report.report_id,
            "analysis_id": report.analysis_id,
            "status": report.status,
            "output_resource_id": domain_plan.output_resource_id,
            "outputs": [
                {
                    "name": report.markdown_path.name,
                    "sha256": report.markdown_sha256,
                },
                {"name": report.json_path.name, "sha256": report.json_sha256},
            ],
            "legal_review_status": "not_performed",
            "deadline_legally_calculated": False,
            "response_generated": False,
            "source_document_modified": False,
            "external_actions_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "official_notice_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class AdministrativeDraftWorkflowAdapter:
    """Create a private, review-only administrative draft without sending it."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="administrative-drafts",
        adapter_id="administrative_draft_resource.v1",
        status="connected",
        plan_schema="folderhome.administrative-draft-resource-plan.v1",
        report_schema="folderhome.administrative-draft-resource-report.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the evidence-bound administrative draft and correspondence core. "
            "Content stays local, remains legally unreviewed, and sending is unsupported."
        ),
        request_schema=_ADMINISTRATIVE_DRAFT_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: NoticeExtractor,
        report_forge_revision: str,
        report_forge_distribution_version: str,
        report_forge_runtime_version: str,
    ) -> None:
        self._registry = registry
        self._extractor = extractor
        self._report_forge_revision = report_forge_revision
        self._report_forge_distribution_version = report_forge_distribution_version
        self._report_forge_runtime_version = report_forge_runtime_version

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedAdministrativeDraft]:
        expected = {
            "request_resource_id",
            "notice_resource_id",
            "designs_resource_id",
            "templates_resource_id",
            "output_resource_id",
            "output_basename",
            "received_on",
            "as_of",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Verwaltungsentwurfsanfrage: "
                + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Verwaltungsentwurfsanfrage fehlt Feld: " + missing[0]
            )
        resource_ids = {
            key: _text(request[key], key)
            for key in (
                "request_resource_id",
                "designs_resource_id",
                "templates_resource_id",
                "output_resource_id",
            )
        }
        notice_id = _optional_text(request["notice_resource_id"], "notice_resource_id")
        output_basename = _safe_output_basename(request["output_basename"])
        received_on = _optional_text(request["received_on"], "received_on")
        as_of = _text(request["as_of"], "as_of")
        try:
            request_resource = self._registry.resolve(
                resource_id=resource_ids["request_resource_id"],
                profile_id=profile_id,
                purpose="administrative.request",
                required_kind="file",
                required_operations=frozenset({"read", "sensitive_read"}),
            )
            designs_resource = self._registry.resolve(
                resource_id=resource_ids["designs_resource_id"],
                profile_id=profile_id,
                purpose="administrative.designs",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            templates_resource = self._registry.resolve(
                resource_id=resource_ids["templates_resource_id"],
                profile_id=profile_id,
                purpose="administrative.templates",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            output_resource = self._registry.resolve(
                resource_id=resource_ids["output_resource_id"],
                profile_id=profile_id,
                purpose="administrative.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            for private_input in (
                request_resource,
                designs_resource,
                templates_resource,
            ):
                _require_separate_resources(
                    private_input.local_path,
                    output_resource.local_path,
                )
            draft_request = load_administrative_draft_request(
                request_resource.local_path
            )
            if draft_request.profile_id != profile_id:
                raise AdministrativeDraftError(
                    "Entwurfsanfrage gehört zu einem anderen Profil."
                )
            notice_analysis = None
            if notice_id is not None:
                notice_resource = self._registry.resolve(
                    resource_id=notice_id,
                    profile_id=profile_id,
                    purpose="administrative.notice",
                    required_kind="file",
                    required_operations=frozenset({"read", "sensitive_read"}),
                )
                _require_separate_resources(
                    notice_resource.local_path,
                    output_resource.local_path,
                )
                notice_analysis = analyze_official_notice(
                    notice_resource.local_path,
                    profile_id=profile_id,
                    received_on=received_on,
                    as_of=as_of,
                    extractor=self._extractor,
                    allow_sensitive_local_read=True,
                )
            configuration = load_correspondence_configuration(
                designs_resource.local_path,
                templates_resource.local_path,
            )
            plan = build_administrative_draft_plan(
                draft_request,
                notice_analysis=notice_analysis,
                correspondence_configuration=configuration,
                report_forge_revision=self._report_forge_revision,
                report_forge_distribution_version=(
                    self._report_forge_distribution_version
                ),
                report_forge_runtime_version=self._report_forge_runtime_version,
            )
        except (
            AdministrativeDraftError,
            CorrespondenceError,
            OfficialNoticeError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.administrative-draft-resource-plan.v1",
            "plan_id": plan.plan_id,
            "profile_id": profile_id,
            "draft_kind": plan.request.draft_kind.value,
            "request_resource_id": request_resource.resource_id,
            "notice_resource_id": notice_id,
            "designs_resource_id": designs_resource.resource_id,
            "templates_resource_id": templates_resource.resource_id,
            "output_resource_id": output_resource.resource_id,
            "output_basename": output_basename,
            "status": plan.status,
            "fact_count": len(plan.facts),
            "unresolved_item_count": len(plan.unresolved_items),
            "warning_count": len(plan.warnings),
            "legal_review_status": "not_performed",
            "deadline_legally_calculated": False,
            "eligibility_assessed": False,
            "human_confirmation_required": True,
            "send_supported": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "administrative_draft_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_sensitive_local_administrative_draft_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedAdministrativeDraft(
            plan=plan,
            public_plan=public_plan,
            output_root=output_resource.local_path,
            output_resource_id=output_resource.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedAdministrativeDraft):
            raise WorkflowExecutionError(
                "Vorbereiteter Verwaltungsentwurf besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Verwaltungsentwurf überein."
            )
        approval = AdministrativeDraftApproval.create(
            plan_id=domain_plan.plan.plan_id,
            markdown_sha256=domain_plan.plan.correspondence_preview.markdown_sha256,
            text_sha256=domain_plan.plan.correspondence_preview.text_sha256,
            approved_at=approved_at,
            confirmed_content_review=True,
            confirmed_no_legal_review=True,
            allow_local_output_write=True,
        )
        try:
            report = write_administrative_draft(
                domain_plan.plan,
                approval,
                markdown_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.md"
                ),
                text_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.txt"
                ),
                allow_output_write=True,
            )
        except (AdministrativeDraftError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        output = report.correspondence_output
        public_report = {
            "schema": "folderhome.administrative-draft-resource-report.v1",
            "report_id": report.report_id,
            "plan_id": report.plan_id,
            "status": report.status,
            "output_resource_id": domain_plan.output_resource_id,
            "outputs": [
                {"name": output.markdown_file.name, "sha256": output.markdown_sha256},
                {"name": output.text_file.name, "sha256": output.text_sha256},
            ],
            "legal_review_status": "not_performed",
            "sent": False,
            "external_actions_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "administrative_draft_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class BenefitScreeningWorkflowAdapter:
    """Route a private profile to dated official prechecks without eligibility claims."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="benefit-screening",
        adapter_id="benefit_screening_resource.v1",
        status="connected",
        plan_schema="folderhome.benefit-screening-resource-plan.v1",
        report_schema="folderhome.benefit-screening-resource-report.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the dated official-routing catalog and private profile snapshot. "
            "It recommends official prechecks but never determines eligibility or amount."
        ),
        request_schema=_BENEFIT_SCREENING_REQUEST_SCHEMA,
    )

    def __init__(self, *, registry: ResourceRegistry) -> None:
        self._registry = registry

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedBenefitScreening]:
        expected = {
            "profile_resource_id",
            "catalog_resource_id",
            "output_resource_id",
            "output_basename",
            "as_of",
            "max_source_age_days",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Leistungsvorcheckanfrage: "
                + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Leistungsvorcheckanfrage fehlt Feld: " + missing[0]
            )
        profile_resource_id = _text(
            request["profile_resource_id"],
            "profile_resource_id",
        )
        catalog_resource_id = _text(
            request["catalog_resource_id"],
            "catalog_resource_id",
        )
        output_resource_id = _text(
            request["output_resource_id"],
            "output_resource_id",
        )
        output_basename = _safe_output_basename(request["output_basename"])
        as_of = _text(request["as_of"], "as_of")
        max_source_age_days = _required_int(
            request["max_source_age_days"],
            "max_source_age_days",
        )
        if not 1 <= max_source_age_days <= 3650:
            raise WorkflowExecutionError(
                "max_source_age_days muss zwischen 1 und 3650 liegen."
            )
        try:
            profile_resource = self._registry.resolve(
                resource_id=profile_resource_id,
                profile_id=profile_id,
                purpose="benefits.profile",
                required_kind="file",
                required_operations=frozenset({"read", "sensitive_read"}),
            )
            catalog_resource = self._registry.resolve(
                resource_id=catalog_resource_id,
                profile_id=profile_id,
                purpose="benefits.catalog",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            output_resource = self._registry.resolve(
                resource_id=output_resource_id,
                profile_id=profile_id,
                purpose="benefits.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_separate_resources(
                profile_resource.local_path,
                output_resource.local_path,
            )
            _require_separate_resources(
                catalog_resource.local_path,
                output_resource.local_path,
            )
            profile = load_benefit_profile_snapshot(
                profile_resource.local_path,
                allow_sensitive_local_read=True,
            )
            if profile.profile_id != profile_id:
                raise BenefitScreeningError(
                    "Leistungsprofil gehört zu einem anderen Profil."
                )
            catalog = load_benefit_catalog(catalog_resource.local_path)
            report = screen_benefits(
                profile,
                catalog,
                as_of=as_of,
                max_source_age_days=max_source_age_days,
                allow_sensitive_local_read=True,
            )
        except (
            BenefitScreeningError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        routing_results = _public_benefit_routing_results(report)
        public_plan = {
            "schema": "folderhome.benefit-screening-resource-plan.v1",
            "report_id": report.report_id,
            "profile_id": profile_id,
            "profile_resource_id": profile_resource.resource_id,
            "catalog_resource_id": catalog_resource.resource_id,
            "output_resource_id": output_resource.resource_id,
            "output_basename": output_basename,
            "status": report.status,
            "result_count": len(report.results),
            "routing_results": routing_results,
            "catalog_complete": False,
            "eligibility_assessed": False,
            "amount_estimated": False,
            "application_generated": False,
            "network_used": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "benefit_screening_resource.v1",
            domain_plan_id=report.report_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_sensitive_local_benefit_report_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedBenefitScreening(
            report=report,
            public_plan=public_plan,
            output_root=output_resource.local_path,
            output_resource_id=output_resource.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedBenefitScreening):
            raise WorkflowExecutionError(
                "Vorbereiteter Leistungsvorcheck besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.report.report_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Leistungsvorcheck überein."
            )
        try:
            output = write_benefit_screening_report(
                domain_plan.report,
                markdown_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.md"
                ),
                json_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.json"
                ),
                allow_output_write=True,
            )
        except (BenefitScreeningError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.benefit-screening-resource-report.v1",
            "output_id": output.output_id,
            "report_id": output.report_id,
            "status": output.status,
            "output_resource_id": domain_plan.output_resource_id,
            "outputs": [
                {"name": output.markdown_path.name, "sha256": output.markdown_sha256},
                {"name": output.json_path.name, "sha256": output.json_sha256},
            ],
            "routing_results": _public_benefit_routing_results(domain_plan.report),
            "catalog_complete": False,
            "eligibility_assessed": False,
            "amount_estimated": False,
            "application_generated": False,
            "network_used": False,
            "external_actions_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "benefit_screening_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class LegalChangeMonitorWorkflowAdapter:
    """Compare supplied legal snapshots locally and emit review candidates only."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="legal-change-monitor",
        adapter_id="legal_change_monitor_resource.v1",
        status="connected",
        plan_schema="folderhome.legal-change-monitor-resource-plan.v1",
        report_schema="folderhome.legal-change-monitor-resource-report.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the bounded local snapshot comparison and optional pinned "
            "law-checker registry qualification. It performs no web research, legal "
            "effect assessment, deadline calculation, or notification."
        ),
        request_schema=_LEGAL_CHANGE_MONITOR_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        law_checker_plugin: PluginDescriptor | None = None,
        law_checker_root: Path | None = None,
    ) -> None:
        if (law_checker_plugin is None) != (law_checker_root is None):
            raise WorkflowExecutionError(
                "law-checker-Manifest und Checkout müssen gemeinsam konfiguriert sein."
            )
        self._registry = registry
        self._law_checker_plugin = law_checker_plugin
        self._law_checker_root = law_checker_root

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedLegalChangeMonitor]:
        expected = {
            "before_resource_id",
            "after_resource_id",
            "interests_resource_id",
            "output_resource_id",
            "output_basename",
            "as_of",
            "max_source_age_days",
            "allow_test_fixture",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Rechtsänderungsanfrage: "
                + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Rechtsänderungsanfrage fehlt Feld: " + missing[0]
            )
        resource_ids = {
            key: _text(request[key], key)
            for key in (
                "before_resource_id",
                "after_resource_id",
                "interests_resource_id",
                "output_resource_id",
            )
        }
        output_basename = _safe_output_basename(request["output_basename"])
        as_of = _text(request["as_of"], "as_of")
        max_source_age_days = _required_int(
            request["max_source_age_days"],
            "max_source_age_days",
        )
        if not 1 <= max_source_age_days <= 3650:
            raise WorkflowExecutionError(
                "max_source_age_days muss zwischen 1 und 3650 liegen."
            )
        allow_test_fixture = _required_bool(
            request["allow_test_fixture"],
            "allow_test_fixture",
        )
        try:
            before_resource = self._registry.resolve(
                resource_id=resource_ids["before_resource_id"],
                profile_id=profile_id,
                purpose="legal.before",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            after_resource = self._registry.resolve(
                resource_id=resource_ids["after_resource_id"],
                profile_id=profile_id,
                purpose="legal.after",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            interests_resource = self._registry.resolve(
                resource_id=resource_ids["interests_resource_id"],
                profile_id=profile_id,
                purpose="legal.interests",
                required_kind="file",
                required_operations=frozenset({"read", "sensitive_read"}),
            )
            output_resource = self._registry.resolve(
                resource_id=resource_ids["output_resource_id"],
                profile_id=profile_id,
                purpose="legal.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            for private_input in (
                before_resource,
                after_resource,
                interests_resource,
            ):
                _require_separate_resources(
                    private_input.local_path,
                    output_resource.local_path,
                )
            before = load_legal_source_snapshot(
                before_resource.local_path,
                allow_test_fixture=allow_test_fixture,
            )
            after = load_legal_source_snapshot(
                after_resource.local_path,
                allow_test_fixture=allow_test_fixture,
            )
            interests = load_legal_interest_snapshot(
                interests_resource.local_path,
                allow_sensitive_local_read=True,
            )
            if interests.profile_id != profile_id:
                raise LegalChangeMonitorError(
                    "Rechtsinteressen gehören zu einem anderen Profil."
                )
            law_checker = None
            if before.law_checker_registry_key or after.law_checker_registry_key:
                if self._law_checker_plugin is None or self._law_checker_root is None:
                    raise LegalChangeMonitorError(
                        "Konfigurierter Rechtsquellenstand benötigt den gepinnten "
                        "law-checker-Provider."
                    )
                law_checker = LawCheckerBridge(
                    plugin=self._law_checker_plugin,
                    provider_root=self._law_checker_root,
                )
            report = compare_legal_source_snapshots(
                before,
                after,
                interests,
                as_of=as_of,
                max_source_age_days=max_source_age_days,
                allow_sensitive_local_read=True,
                allow_test_fixture=allow_test_fixture,
                law_checker=law_checker,
            )
        except (
            LawCheckerBridgeError,
            LegalChangeMonitorError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.legal-change-monitor-resource-plan.v1",
            "report_id": report.report_id,
            "profile_id": profile_id,
            "before_resource_id": before_resource.resource_id,
            "after_resource_id": after_resource.resource_id,
            "interests_resource_id": interests_resource.resource_id,
            "output_resource_id": output_resource.resource_id,
            "output_basename": output_basename,
            "status": report.status,
            "law_id": report.law_id,
            "publication_stage": report.publication_stage,
            "registry_coverage_status": report.registry_coverage_status,
            "change_count": len(report.changes),
            "review_candidate_count": len(report.candidates),
            "legal_effect_assessed": False,
            "deadline_legally_calculated": False,
            "notification_sent": False,
            "network_used": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "legal_change_monitor_resource.v1",
            domain_plan_id=report.report_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_sensitive_local_legal_report_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedLegalChangeMonitor(
            report=report,
            public_plan=public_plan,
            output_root=output_resource.local_path,
            output_resource_id=output_resource.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedLegalChangeMonitor):
            raise WorkflowExecutionError(
                "Vorbereiteter Rechtsänderungsbericht besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.report.report_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Rechtsänderungsbericht überein."
            )
        try:
            output = write_legal_change_report(
                domain_plan.report,
                markdown_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.md"
                ),
                json_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.json"
                ),
                allow_output_write=True,
            )
        except (LegalChangeMonitorError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.legal-change-monitor-resource-report.v1",
            "output_id": output.output_id,
            "report_id": output.report_id,
            "status": output.status,
            "output_resource_id": domain_plan.output_resource_id,
            "outputs": [
                {"name": output.markdown_file.name, "sha256": output.markdown_sha256},
                {"name": output.json_file.name, "sha256": output.json_sha256},
            ],
            "legal_effect_assessed": False,
            "deadline_legally_calculated": False,
            "notification_sent": False,
            "network_used": False,
            "external_actions_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "legal_change_monitor_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class InventoryImportWorkflowAdapter:
    """Append evidenced household observations to the private inventory store."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="inventory-import",
        adapter_id="inventory_import_resource.v1",
        status="connected",
        plan_schema="folderhome.inventory-import-resource-plan.v1",
        report_schema="folderhome.inventory-import-resource-report.v1",
        side_effects=("state.inventory.write",),
        reason=(
            "Reuses the existing revision-bound, evidence-backed inventory import "
            "through private resource IDs. It never orders or purchases anything."
        ),
        request_schema=_INVENTORY_IMPORT_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: InventoryDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedInventoryImport]:
        expected = {
            "source_resource_id",
            "state_resource_id",
            "recursive",
            "allow_sensitive_local_read",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Inventarimportanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Inventarimportanfrage fehlt Feld: " + missing[0]
            )
        source_id = _text(request["source_resource_id"], "source_resource_id")
        state_id = _text(request["state_resource_id"], "state_resource_id")
        recursive = _required_bool(request["recursive"], "recursive")
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        source_operations = {"list", "read"}
        if sensitive_read:
            source_operations.add("sensitive_read")
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="inventory.source",
                required_kind="directory",
                required_operations=frozenset(source_operations),
            )
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="inventory.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_separate_resources(source.local_path, state.local_path)
            analysis = analyze_folder_inventory(
                source.local_path,
                profile_id=profile_id,
                extractor=self._extractor,
                recursive=recursive,
                allow_sensitive_local_read=sensitive_read,
            )
            store = InventoryStore(state.local_path)
            plan = build_inventory_import_plan(analysis, store=store)
        except (
            InventoryStoreError,
            InventoryWorkflowError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_inventory_import_plan(
            plan,
            source_resource_id=source.resource_id,
            state_resource_id=state.resource_id,
        )
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "inventory_import_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_local_inventory_state_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedInventoryImport(
            plan=plan,
            public_plan=public_plan,
            store=store,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedInventoryImport):
            raise WorkflowExecutionError("Vorbereiteter Inventarimport besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Inventarimportplan überein."
            )
        action_ids = tuple(
            item.action_id
            for item in domain_plan.plan.actions
            if item.status == "planned"
        )
        if not action_ids:
            raise WorkflowExecutionError(
                "Inventarimportplan enthält keine ausführbare neue Beobachtung."
            )
        approval = InventoryImportApproval(
            approval_id=f"agent_inventory_{secrets.token_hex(10)}",
            plan_id=domain_plan.plan.plan_id,
            inventory_revision=domain_plan.plan.inventory_revision,
            action_ids=action_ids,
            approved_at=approved_at,
        )
        try:
            report = apply_inventory_import_plan(
                domain_plan.plan,
                approval,
                store=domain_plan.store,
                allow_state_write=True,
            )
        except (InventoryStoreError, InventoryWorkflowError, OSError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.inventory-import-resource-report.v1",
            "report_id": report.report_id,
            "status": report.status,
            "state_resource_id": domain_plan.state_resource_id,
            "revision_before": report.revision_before,
            "revision_after": report.revision_after,
            "created_event_count": len(report.created_event_ids),
            "automatic_purchase": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "inventory_import_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class DailyBriefingWorkflowAdapter:
    """Render and deliver a briefing from already supplied local snapshots."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="daily-briefing",
        adapter_id="daily_briefing_resource.v1",
        status="connected",
        plan_schema="folderhome.daily-briefing-resource-plan.v1",
        report_schema="folderhome.daily-briefing-resource-report.v1",
        side_effects=("filesystem.briefing.write", "filesystem.desktop.write"),
        reason=(
            "Reuses the deterministic local snapshot briefing with one exact approval "
            "for the declared render and desktop targets. It performs no live fetch."
        ),
        request_schema=_DAILY_BRIEFING_REQUEST_SCHEMA,
    )

    def __init__(self, *, registry: ResourceRegistry) -> None:
        self._registry = registry

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedDailyBriefing]:
        expected = set(_DAILY_BRIEFING_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Briefinganfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError("Briefinganfrage fehlt Feld: " + missing[0])
        weather_id = _text(request["weather_resource_id"], "weather_resource_id")
        news_id = _text(request["news_resource_id"], "news_resource_id")
        output_id = _text(request["output_resource_id"], "output_resource_id")
        desktop_id = _text(request["desktop_resource_id"], "desktop_resource_id")
        output_name = _safe_output_name(request["output_name"])
        desktop_name = _safe_output_name(request["desktop_name"])
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        categories_value = request["categories"]
        if (
            not isinstance(categories_value, list)
            or not categories_value
            or not all(isinstance(item, str) for item in categories_value)
        ):
            raise WorkflowExecutionError("categories benötigt eine nicht leere Textliste.")
        categories = tuple(categories_value)
        input_operations = {"read"}
        if sensitive_read:
            input_operations.add("sensitive_read")
        try:
            weather = self._registry.resolve(
                resource_id=weather_id,
                profile_id=profile_id,
                purpose="briefing.weather_snapshot",
                required_kind="file",
                required_operations=frozenset(input_operations),
            )
            news = self._registry.resolve(
                resource_id=news_id,
                profile_id=profile_id,
                purpose="briefing.news_snapshot",
                required_kind="file",
                required_operations=frozenset(input_operations),
            )
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="briefing.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            desktop = self._registry.resolve(
                resource_id=desktop_id,
                profile_id=profile_id,
                purpose="briefing.desktop",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            for first, second in (
                (weather.local_path, news.local_path),
                (weather.local_path, output.local_path),
                (weather.local_path, desktop.local_path),
                (news.local_path, output.local_path),
                (news.local_path, desktop.local_path),
                (output.local_path, desktop.local_path),
            ):
                _require_separate_resources(first, second)
            request_material = {
                "profile_id": profile_id,
                "briefing_date": _text(request["briefing_date"], "briefing_date"),
                "as_of": _text(request["as_of"], "as_of"),
                "timezone": _text(request["timezone"], "timezone"),
                "title": _text(request["title"], "title"),
                "categories": categories,
                "weather_resource_id": weather.resource_id,
                "news_resource_id": news.resource_id,
            }
            briefing_request = DailyBriefingRequest(
                request_id=(
                    "briefing_"
                    + sha256(_canonical_json(request_material)).hexdigest()[:24]
                ),
                profile_id=profile_id,
                briefing_date=str(request_material["briefing_date"]),
                as_of=str(request_material["as_of"]),
                timezone=str(request_material["timezone"]),
                title=str(request_material["title"]),
                categories=categories,
                max_items_per_category=_required_int(
                    request["max_items_per_category"],
                    "max_items_per_category",
                ),
                max_weather_age_minutes=_required_int(
                    request["max_weather_age_minutes"],
                    "max_weather_age_minutes",
                ),
                max_news_age_minutes=_required_int(
                    request["max_news_age_minutes"],
                    "max_news_age_minutes",
                ),
                weather_snapshot_path=weather.local_path,
                news_snapshot_path=news.local_path,
            )
            plan = build_daily_briefing_plan(
                briefing_request,
                known_profile_ids=set(self._registry.known_profile_ids),
                output_path=output.local_path / output_name,
                desktop_path=desktop.local_path / desktop_name,
                allow_sensitive_local_read=sensitive_read,
            )
        except (
            DailyBriefingError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_daily_briefing_plan(
            plan,
            weather_resource_id=weather.resource_id,
            news_resource_id=news.resource_id,
            output_resource_id=output.resource_id,
            desktop_resource_id=desktop.resource_id,
            output_name=output_name,
            desktop_name=desktop_name,
        )
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "daily_briefing_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_local_briefing_render_and_desktop_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedDailyBriefing(
            plan=plan,
            public_plan=public_plan,
            output_resource_id=output.resource_id,
            desktop_resource_id=desktop.resource_id,
            output_name=output_name,
            desktop_name=desktop_name,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedDailyBriefing):
            raise WorkflowExecutionError("Vorbereitetes Briefing besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Briefingplan überein."
            )
        render_approval = BriefingRenderApproval(
            approval_id=f"agent_briefing_render_{secrets.token_hex(8)}",
            plan_id=domain_plan.plan.plan_id,
            plan_sha256=domain_plan.plan.plan_sha256,
            html_sha256=domain_plan.plan.html_sha256,
            output_path=domain_plan.plan.output_path,
            approved_at=approved_at,
            allow_output_write=True,
        )
        delivery_approval = BriefingDeliveryApproval(
            approval_id=f"agent_briefing_delivery_{secrets.token_hex(8)}",
            plan_id=domain_plan.plan.plan_id,
            plan_sha256=domain_plan.plan.plan_sha256,
            html_sha256=domain_plan.plan.html_sha256,
            desktop_path=domain_plan.plan.desktop_path,
            approved_at=approved_at,
            allow_desktop_write=True,
        )
        rendered = None
        try:
            rendered = render_daily_briefing(
                domain_plan.plan,
                render_approval,
                allow_output_write=True,
            )
            delivered = deliver_daily_briefing(
                domain_plan.plan,
                delivery_approval,
                allow_desktop_write=True,
            )
        except (DailyBriefingError, OSError, TypeError, ValueError) as exc:
            target = domain_plan.plan.output_path
            if (
                rendered is not None
                and target.is_file()
                and not target.is_symlink()
                and sha256(target.read_bytes()).hexdigest()
                == domain_plan.plan.html_sha256
            ):
                target.unlink()
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.daily-briefing-resource-report.v1",
            "status": "executed",
            "render_report_id": rendered.report_id,
            "delivery_report_id": delivered.report_id,
            "output_resource_id": domain_plan.output_resource_id,
            "desktop_resource_id": domain_plan.desktop_resource_id,
            "output_name": domain_plan.output_name,
            "desktop_name": domain_plan.desktop_name,
            "output_sha256": delivered.output_sha256,
            "desktop_written": delivered.desktop_written,
            "network_invoked": False,
            "scheduler_registered": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "daily_briefing_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class TaxWorkpaperWorkflowAdapter:
    """Export the pinned tax provider state as a private review workpaper."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="tax-workpaper",
        adapter_id="tax_workpaper_resource.v1",
        status="connected",
        plan_schema="folderhome.tax-workpaper-resource-plan.v1",
        report_schema="folderhome.tax-workpaper-resource-report.v1",
        side_effects=("state.tax.local_write", "filesystem.tax_workpaper.write"),
        reason=(
            "Reuses the pinned steuer-assistent export as a private workpaper. "
            "It gives no tax advice, creates no official format and submits nothing."
        ),
        request_schema=_TAX_WORKPAPER_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        plugin: PluginDescriptor,
        provider_root: Path,
    ) -> None:
        self._registry = registry
        self._plugin = plugin
        self._provider_root = provider_root.resolve()

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedTaxWorkpaper]:
        expected = set(_TAX_WORKPAPER_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Steuerarbeitsmappenanfrage: "
                + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Steuerarbeitsmappenanfrage fehlt Feld: " + missing[0]
            )
        state_id = _text(request["state_resource_id"], "state_resource_id")
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_name = _safe_output_name(request["output_name"])
        tax_year = _required_int(request["tax_year"], "tax_year")
        try:
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="tax.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="tax.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_separate_resources(state.local_path, output.local_path)
            if (
                state.local_path == self._provider_root
                or state.local_path.is_relative_to(self._provider_root)
                or self._provider_root.is_relative_to(state.local_path)
            ):
                raise WorkflowExecutionError(
                    "Steuer-State und Provider-Checkout dürfen sich nicht überlappen."
                )
            bridge = TaxAssistantBridge(
                plugin=self._plugin,
                provider_root=self._provider_root,
                db_path=state.local_path / profile_id / "steuer.db",
            )
            plan = build_tax_export_plan(
                tax_year,
                profile_id=profile_id,
                output_path=output.local_path / output_name,
                bridge=bridge,
            )
        except (
            ResourceRegistryError,
            TaxAssistantBridgeError,
            TaxWorkflowError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.tax-workpaper-resource-plan.v1",
            "plan_id": plan.plan_id,
            "plan_sha256": plan.plan_sha256,
            "profile_id": profile_id,
            "tax_year": plan.tax_year,
            "state_resource_id": state.resource_id,
            "output_resource_id": output.resource_id,
            "output_name": output_name,
            "provider_id": self._plugin.plugin_id,
            "provider_version": self._plugin.version,
            "provider_revision": self._plugin.source_revision,
            "provider_store_revision": plan.provider_store_revision,
            "receipt_count": plan.receipt_count,
            "status": plan.status,
            "official_format": False,
            "tax_advice": False,
            "portal_submission_supported": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "tax_workpaper_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_private_tax_workpaper_export",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedTaxWorkpaper(
            plan=plan,
            public_plan=public_plan,
            bridge=bridge,
            state_resource_id=state.resource_id,
            output_resource_id=output.resource_id,
            output_name=output_name,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedTaxWorkpaper):
            raise WorkflowExecutionError(
                "Vorbereitete Steuerarbeitsmappe besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Steuerexportplan überein."
            )
        approval = TaxExportApproval(
            approval_id=f"agent_tax_export_{secrets.token_hex(8)}",
            plan_id=domain_plan.plan.plan_id,
            plan_sha256=domain_plan.plan.plan_sha256,
            provider_store_revision=domain_plan.plan.provider_store_revision,
            approved_at=approved_at,
            allow_local_tax_state_write=True,
            allow_output_write=True,
        )
        try:
            domain_plan.bridge.db_path.parent.mkdir(parents=True, exist_ok=True)
            report = export_tax_workpaper(
                domain_plan.plan,
                approval,
                bridge=domain_plan.bridge,
                allow_state_write=True,
                allow_output_write=True,
            )
        except (
            TaxAssistantBridgeError,
            TaxWorkflowError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.tax-workpaper-resource-report.v1",
            "report_id": report.report_id,
            "status": report.status,
            "state_resource_id": domain_plan.state_resource_id,
            "output_resource_id": domain_plan.output_resource_id,
            "output_name": domain_plan.output_name,
            "output_sha256": report.output_sha256,
            "official_format": False,
            "tax_advice": False,
            "portal_submitted": False,
            "network_invoked": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "tax_workpaper_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class FolderCleanupWorkflowAdapter:
    """Plan and execute the existing safe whole-folder cleanup workflow."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="folder-cleanup",
        adapter_id="folder_cleanup_resource.v1",
        status="connected",
        plan_schema="folderhome.folder-cleanup-resource-plan.v1",
        report_schema="folderhome.folder-cleanup-resource-report.v1",
        side_effects=("filesystem.files.move", "state.cleanup.audit_write"),
        reason=(
            "Reuses deterministic profile rules, conflict detection, hash-bound moves "
            "and rollback-capable audit records for one configured source and target."
        ),
        request_schema=_FOLDER_CLEANUP_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles: ProfileConfiguration,
        extractor: CleanupDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._profiles = profiles
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedFolderCleanup]:
        expected = set(_FOLDER_CLEANUP_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Ordneraufräumanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Ordneraufräumanfrage fehlt Feld: " + missing[0]
            )
        source_id = _text(request["source_resource_id"], "source_resource_id")
        target_id = _text(request["target_resource_id"], "target_resource_id")
        state_id = _text(request["state_resource_id"], "state_resource_id")
        area = _text(request["area"], "area")
        recursive = _required_bool(request["recursive"], "recursive")
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        if not sensitive_read:
            raise WorkflowExecutionError(
                "Ordneraufräumen benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="folder_cleanup.source",
                required_kind="directory",
                required_operations=frozenset(
                    {"list", "read", "sensitive_read", "move"}
                ),
            )
            target = self._registry.resolve(
                resource_id=target_id,
                profile_id=profile_id,
                purpose="folder_cleanup.target",
                required_kind="directory",
                required_operations=frozenset({"create", "move"}),
            )
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="folder_cleanup.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_separate_resources(source.local_path, target.local_path)
            _require_separate_resources(source.local_path, state.local_path)
            _require_separate_resources(target.local_path, state.local_path)
            policy = resolve_profile_policy(
                self._profiles,
                profile_id=profile_id,
                area=area,
            )
            plan = build_folder_cleanup_plan(
                source.local_path,
                policy=policy,
                target_root=target.local_path,
                as_of=date.fromisoformat(_text(request["as_of"], "as_of")),
                extractor=self._extractor,
                recursive=recursive,
            )
        except (
            FolderCleanupError,
            ProfileConfigurationError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        selected = tuple(
            item
            for item in plan.items
            if item.status == "planned"
            and item.action_plan is not None
            and item.executable_action_ids
        )
        public_plan = {
            "schema": "folderhome.folder-cleanup-resource-plan.v1",
            "batch_id": plan.batch_id,
            "profile_id": plan.profile_id,
            "area": plan.area,
            "as_of": plan.as_of,
            "recursive": plan.recursive,
            "source_resource_id": source.resource_id,
            "target_resource_id": target.resource_id,
            "state_resource_id": state.resource_id,
            "item_count": len(plan.items),
            "selected_item_count": len(selected),
            "planned_action_count": sum(
                len(item.executable_action_ids) for item in selected
            ),
            "blocked_item_count": sum(item.status == "blocked" for item in plan.items),
            "skipped_item_count": sum(item.status == "skipped" for item in plan.items),
            "conflict_count": len(plan.conflicts),
            "selection_policy": "all_conflict_free_planned_items",
            "hard_delete_supported": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "folder_cleanup_resource.v1",
            domain_plan_id=plan.batch_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_hash_bound_folder_cleanup",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedFolderCleanup(
            plan=plan,
            public_plan=public_plan,
            state_root=state.local_path,
            source_resource_id=source.resource_id,
            target_resource_id=target.resource_id,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedFolderCleanup):
            raise WorkflowExecutionError("Vorbereiteter Ordnerplan besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.batch_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Ordneraufräumplan überein."
            )
        approvals = tuple(
            BatchItemApproval(
                document_id=item.document_id or "",
                plan_id=item.action_plan.plan_id if item.action_plan is not None else "",
                document_sha256=item.source_sha256,
                action_ids=item.executable_action_ids,
            )
            for item in domain_plan.plan.items
            if item.status == "planned"
            and item.action_plan is not None
            and item.executable_action_ids
        )
        if not approvals:
            raise WorkflowExecutionError(
                "Ordneraufräumplan enthält keine konfliktfrei ausführbare Aktion."
            )
        approval = FolderCleanupApproval(
            approval_id=f"agent_cleanup_{secrets.token_hex(8)}",
            batch_id=domain_plan.plan.batch_id,
            items=approvals,
            approved_at=approved_at,
        )
        try:
            report = execute_folder_cleanup(
                domain_plan.plan,
                approval,
                state_dir=domain_plan.state_root,
                allow_file_write=True,
            )
        except (FolderCleanupError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.folder-cleanup-resource-report.v1",
            "batch_execution_id": report.batch_execution_id,
            "status": report.status,
            "source_resource_id": domain_plan.source_resource_id,
            "target_resource_id": domain_plan.target_resource_id,
            "state_resource_id": domain_plan.state_resource_id,
            "execution_count": len(report.executions),
            "placement_receipt_count": len(report.placement_receipts),
            "hard_delete_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "folder_cleanup_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class DirectoryObservationWorkflowAdapter:
    """Write one immutable watched-directory checkpoint after exact approval."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="directory-observation",
        adapter_id="directory_observation_resource.v1",
        status="connected",
        plan_schema="folderhome.directory-observation-resource-plan.v1",
        report_schema="folderhome.directory-observation-resource-report.v1",
        side_effects=("state.directory_snapshot.write",),
        reason=(
            "Reuses immutable directory snapshots and diff learning without moving "
            "files. The checkpoint is bound to the exact planned source snapshot."
        ),
        request_schema=_DIRECTORY_OBSERVATION_REQUEST_SCHEMA,
    )

    def __init__(self, *, registry: ResourceRegistry) -> None:
        self._registry = registry

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedDirectoryObservation]:
        expected = set(_DIRECTORY_OBSERVATION_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Verzeichnisscananfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Verzeichnisscananfrage fehlt Feld: " + missing[0]
            )
        source_id = _text(request["source_resource_id"], "source_resource_id")
        state_id = _text(request["state_resource_id"], "state_resource_id")
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        if not sensitive_read:
            raise WorkflowExecutionError(
                "Verzeichnisscan benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="directory_observation.source",
                required_kind="directory",
                required_operations=frozenset({"list", "read", "sensitive_read"}),
            )
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="directory_observation.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_separate_resources(source.local_path, state.local_path)
            watch = WatchedFolder(
                watch_id=_text(request["watch_id"], "watch_id"),
                source_root=source.local_path,
                profile_id=profile_id,
                area=_text(request["area"], "area"),
                interval_minutes=_required_int(
                    request["interval_minutes"],
                    "interval_minutes",
                ),
                recursive=_required_bool(request["recursive"], "recursive"),
                enabled=True,
            )
            scan = run_directory_scan(
                watch,
                captured_at=_text(request["captured_at"], "captured_at"),
                state_dir=state.local_path,
                allow_state_write=False,
            )
        except (
            DirectoryObservationError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.directory-observation-resource-plan.v1",
            "scan_id": scan.scan_id,
            "snapshot_id": scan.snapshot.snapshot_id,
            "previous_snapshot_id": scan.previous_snapshot_id,
            "profile_id": profile_id,
            "watch_id": watch.watch_id,
            "area": watch.area,
            "source_resource_id": source.resource_id,
            "state_resource_id": state.resource_id,
            "file_count": len(scan.snapshot.files),
            "change_count": len(scan.diff.changes) if scan.diff is not None else 0,
            "learning_example_count": len(scan.learning_examples),
            "interval_due": scan.interval_due,
            "checkpoint_write_planned": True,
            "files_moved": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "directory_observation_resource.v1",
            domain_plan_id=scan.scan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_directory_checkpoint_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedDirectoryObservation(
            scan=scan,
            public_plan=public_plan,
            state_root=state.local_path,
            source_resource_id=source.resource_id,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedDirectoryObservation):
            raise WorkflowExecutionError(
                "Vorbereiteter Verzeichnisscan besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.scan.scan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Verzeichnisscan überein."
            )
        try:
            report = run_directory_scan(
                domain_plan.scan.watch,
                captured_at=domain_plan.scan.snapshot.captured_at,
                state_dir=domain_plan.state_root,
                allow_state_write=True,
                expected_previous_snapshot_id=domain_plan.scan.previous_snapshot_id,
                expected_current_snapshot_id=domain_plan.scan.snapshot.snapshot_id,
            )
        except (DirectoryObservationError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.directory-observation-resource-report.v1",
            "scan_id": report.scan_id,
            "snapshot_id": report.snapshot.snapshot_id,
            "source_resource_id": domain_plan.source_resource_id,
            "state_resource_id": domain_plan.state_resource_id,
            "file_count": len(report.snapshot.files),
            "change_count": len(report.diff.changes) if report.diff is not None else 0,
            "learning_example_count": len(report.learning_examples),
            "checkpoint_written": report.checkpoint_file is not None,
            "files_moved": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "directory_observation_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class DocumentActionPlanWorkflowAdapter:
    """Write one private, deterministic policy plan without changing the document."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="document-action-plan",
        adapter_id="document_action_plan_resource.v1",
        status="connected",
        plan_schema="folderhome.document-action-plan-resource-plan.v1",
        report_schema="folderhome.document-action-plan-resource-report.v1",
        side_effects=("filesystem.private_action_plan.write",),
        reason=(
            "Reuses resolved household/profile rules and the deterministic document "
            "policy planner. It writes only a private plan and never changes the source."
        ),
        request_schema=_DOCUMENT_ACTION_PLAN_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles: ProfileConfiguration,
        extractor: BundleDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._profiles = profiles
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedDocumentActionPlan]:
        _validate_exact_request(
            request,
            _DOCUMENT_ACTION_PLAN_REQUEST_SCHEMA,
            "Dokumentaktionsplan",
        )
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_name = _safe_output_name(request["output_name"])
        plan, source, target = _prepare_single_document_action(
            registry=self._registry,
            profiles=self._profiles,
            extractor=self._extractor,
            profile_id=profile_id,
            request=request,
            require_source_move=False,
        )
        try:
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="document_action.plan_output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_distinct_resources((source, target, output))
            if (output.local_path / output_name).exists():
                raise WorkflowExecutionError(
                    f"Dokumentaktionsplanausgabe existiert bereits: {output_name}"
                )
        except (ResourceRegistryError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_document_action_plan(
            plan,
            schema="folderhome.document-action-plan-resource-plan.v1",
            source_resource_id=source.resource_id,
            target_resource_id=target.resource_id,
            output_resource_id=output.resource_id,
            output_name=output_name,
        )
        envelope = _resource_execution_envelope(
            descriptor=self.descriptor,
            domain_plan_id=plan.plan_id,
            public_plan=public_plan,
            approval_kind="explicit_private_document_action_plan_write",
        )
        return envelope, _PreparedDocumentActionPlan(
            plan=plan,
            public_plan=public_plan,
            output_root=output.local_path,
            output_resource_id=output.resource_id,
            output_name=output_name,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedDocumentActionPlan):
            raise WorkflowExecutionError(
                "Vorbereiteter Dokumentaktionsplan besitzt falschen Typ."
            )
        _verify_resource_envelope(envelope, domain_plan.plan.plan_id, domain_plan.public_plan)
        _verify_planned_document_unchanged(domain_plan.plan)
        try:
            output_hashes = _publish_private_text_outputs(
                domain_plan.output_root,
                {
                    domain_plan.output_name: json.dumps(
                        domain_plan.plan.to_dict(),
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                },
            )
        except (OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.document-action-plan-resource-report.v1",
            "plan_id": domain_plan.plan.plan_id,
            "status": "written",
            "output_resource_id": domain_plan.output_resource_id,
            "output_name": domain_plan.output_name,
            "output_sha256": output_hashes[domain_plan.output_name],
            "source_changed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        return _resource_execution_report(
            envelope=envelope,
            descriptor=self.descriptor,
            approved_at=approved_at,
            public_report=public_report,
        )


class DocumentActionExecutionWorkflowAdapter:
    """Execute one approved, contiguous and reversible document move prefix."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="document-action-execution",
        adapter_id="document_action_execution_resource.v1",
        status="connected",
        plan_schema="folderhome.document-action-execution-resource-plan.v1",
        report_schema="folderhome.document-action-execution-resource-report.v1",
        side_effects=("filesystem.document.move", "state.action_execution.audit_write"),
        reason=(
            "Reuses hash-bound profile action planning plus the existing transactional "
            "move executor and immutable rollback-capable audit trail."
        ),
        request_schema=_DOCUMENT_ACTION_EXECUTION_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles: ProfileConfiguration,
        extractor: BundleDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._profiles = profiles
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedDocumentActionExecution]:
        _validate_exact_request(
            request,
            _DOCUMENT_ACTION_EXECUTION_REQUEST_SCHEMA,
            "Dokumentaktionsausführung",
        )
        state_id = _text(request["state_resource_id"], "state_resource_id")
        plan, source, target = _prepare_single_document_action(
            registry=self._registry,
            profiles=self._profiles,
            extractor=self._extractor,
            profile_id=profile_id,
            request=request,
            require_source_move=True,
        )
        steps = executable_action_prefix(plan)
        if not steps:
            raise WorkflowExecutionError(
                "Dokumentaktionsplan enthält keinen sicher ausführbaren Aktionspräfix."
            )
        try:
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="document_action.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_distinct_resources((source, target, state))
        except (ResourceRegistryError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_document_action_plan(
            plan,
            schema="folderhome.document-action-execution-resource-plan.v1",
            source_resource_id=source.resource_id,
            target_resource_id=target.resource_id,
            state_resource_id=state.resource_id,
        )
        envelope = _resource_execution_envelope(
            descriptor=self.descriptor,
            domain_plan_id=plan.plan_id,
            public_plan=public_plan,
            approval_kind="explicit_hash_bound_document_move",
        )
        return envelope, _PreparedDocumentActionExecution(
            plan=plan,
            public_plan=public_plan,
            state_root=state.local_path,
            source_resource_id=source.resource_id,
            target_resource_id=target.resource_id,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedDocumentActionExecution):
            raise WorkflowExecutionError(
                "Vorbereitete Dokumentaktionsausführung besitzt falschen Typ."
            )
        _verify_resource_envelope(envelope, domain_plan.plan.plan_id, domain_plan.public_plan)
        steps = executable_action_prefix(domain_plan.plan)
        if not steps:
            raise WorkflowExecutionError(
                "Dokumentaktionsplan enthält keinen ausführbaren Aktionspräfix."
            )
        approval = ActionExecutionApproval(
            approval_id=f"agent_action_{secrets.token_hex(8)}",
            plan_id=domain_plan.plan.plan_id,
            action_ids=tuple(step.action_id for step in steps),
            document_sha256=domain_plan.plan.document.source_sha256,
            approved_at=approved_at,
        )
        try:
            report = execute_document_actions(
                domain_plan.plan,
                approval,
                state_dir=domain_plan.state_root,
                allow_file_write=True,
            )
        except (DocumentActionExecutionError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.document-action-execution-resource-report.v1",
            "execution_id": report.execution_id,
            "plan_id": report.plan_id,
            "status": report.status,
            "source_resource_id": domain_plan.source_resource_id,
            "target_resource_id": domain_plan.target_resource_id,
            "state_resource_id": domain_plan.state_resource_id,
            "executed_action_count": len(report.steps),
            "placement_receipt_id": report.placement_receipt.receipt_id,
            "undo_supported": True,
            "hard_delete_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        return _resource_execution_report(
            envelope=envelope,
            descriptor=self.descriptor,
            approved_at=approved_at,
            public_report=public_report,
        )


class FolderRoutineWorkflowAdapter:
    """Execute one observed-folder cleanup and checkpoint it after approval."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="folder-routine",
        adapter_id="folder_routine_resource.v1",
        status="connected",
        plan_schema="folderhome.folder-routine-resource-plan.v1",
        report_schema="folderhome.folder-routine-resource-report.v1",
        side_effects=(
            "filesystem.folder_routine.move",
            "state.folder_routine.audit_write",
            "state.directory_snapshot.write",
        ),
        reason=(
            "Reuses watched-folder scans, profile cleanup rules, transactional moves, "
            "rollback and the post-run immutable checkpoint."
        ),
        request_schema=_FOLDER_ROUTINE_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles: ProfileConfiguration,
        extractor: CleanupDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._profiles = profiles
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedFolderRoutine]:
        _validate_exact_request(
            request,
            _FOLDER_ROUTINE_REQUEST_SCHEMA,
            "Ordnerroutine",
        )
        if not _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        ):
            raise WorkflowExecutionError(
                "Ordnerroutine benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        try:
            source = self._registry.resolve(
                resource_id=_text(request["source_resource_id"], "source_resource_id"),
                profile_id=profile_id,
                purpose="folder_routine.source",
                required_kind="directory",
                required_operations=frozenset(
                    {"list", "read", "sensitive_read", "move"}
                ),
            )
            target = self._registry.resolve(
                resource_id=_text(request["target_resource_id"], "target_resource_id"),
                profile_id=profile_id,
                purpose="folder_routine.target",
                required_kind="directory",
                required_operations=frozenset({"create", "move"}),
            )
            state = self._registry.resolve(
                resource_id=_text(request["state_resource_id"], "state_resource_id"),
                profile_id=profile_id,
                purpose="folder_routine.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_distinct_resources((source, target, state))
            area = _text(request["area"], "area")
            watch = WatchedFolder(
                watch_id=_text(request["watch_id"], "watch_id"),
                source_root=source.local_path,
                profile_id=profile_id,
                area=area,
                interval_minutes=_required_int(
                    request["interval_minutes"],
                    "interval_minutes",
                ),
                recursive=_required_bool(request["recursive"], "recursive"),
                enabled=True,
            )
            plan = build_folder_routine_plan(
                watch,
                policy=resolve_profile_policy(
                    self._profiles,
                    profile_id=profile_id,
                    area=area,
                ),
                target_root=target.local_path,
                as_of=date.fromisoformat(_text(request["as_of"], "as_of")),
                captured_at=_text(request["captured_at"], "captured_at"),
                state_dir=state.local_path,
                extractor=self._extractor,
                mode=FolderRoutineMode(_text(request["mode"], "mode")),
            )
        except (
            FolderRoutineError,
            ProfileConfigurationError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        executable_count = sum(
            item.status == "planned" and bool(item.executable_action_ids)
            for item in plan.cleanup_plan.items
        )
        if not plan.approval_required or executable_count == 0:
            raise WorkflowExecutionError(
                "Ordnerroutine enthält keine konfliktfrei ausführbare Dokumentaktion."
            )
        public_plan = {
            "schema": "folderhome.folder-routine-resource-plan.v1",
            "routine_id": plan.routine_id,
            "profile_id": profile_id,
            "watch_id": watch.watch_id,
            "area": watch.area,
            "mode": plan.mode.value,
            "status": plan.status,
            "reason": plan.reason,
            "source_resource_id": source.resource_id,
            "target_resource_id": target.resource_id,
            "state_resource_id": state.resource_id,
            "eligible_document_count": len(plan.eligible_relative_paths),
            "executable_document_count": executable_count,
            "checkpoint_write_planned": True,
            "hard_delete_planned": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        envelope = _resource_execution_envelope(
            descriptor=self.descriptor,
            domain_plan_id=plan.routine_id,
            public_plan=public_plan,
            approval_kind="explicit_hash_bound_folder_routine",
        )
        return envelope, _PreparedFolderRoutine(
            plan=plan,
            public_plan=public_plan,
            state_root=state.local_path,
            source_resource_id=source.resource_id,
            target_resource_id=target.resource_id,
            state_resource_id=state.resource_id,
            completed_at=_text(request["completed_at"], "completed_at"),
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedFolderRoutine):
            raise WorkflowExecutionError("Vorbereitete Ordnerroutine besitzt falschen Typ.")
        _verify_resource_envelope(
            envelope,
            domain_plan.plan.routine_id,
            domain_plan.public_plan,
        )
        approvals = _folder_cleanup_item_approvals(domain_plan.plan.cleanup_plan)
        if not approvals:
            raise WorkflowExecutionError(
                "Ordnerroutine enthält keine ausführbare Dokumentaktion."
            )
        approval = FolderCleanupApproval(
            approval_id=f"agent_routine_{secrets.token_hex(8)}",
            batch_id=domain_plan.plan.cleanup_plan.batch_id,
            items=approvals,
            approved_at=approved_at,
        )
        try:
            report = execute_folder_routine(
                domain_plan.plan,
                approval,
                completed_at=domain_plan.completed_at,
                state_dir=domain_plan.state_root,
                allow_file_write=True,
                allow_state_write=True,
            )
        except (FolderRoutineError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.folder-routine-resource-report.v1",
            "routine_execution_id": report.routine_execution_id,
            "routine_id": report.routine_id,
            "status": report.status,
            "source_resource_id": domain_plan.source_resource_id,
            "target_resource_id": domain_plan.target_resource_id,
            "state_resource_id": domain_plan.state_resource_id,
            "executed_document_count": len(report.cleanup_report.executions),
            "checkpoint_written": report.checkpoint_report is not None,
            "undo_supported": True,
            "hard_delete_performed": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        return _resource_execution_report(
            envelope=envelope,
            descriptor=self.descriptor,
            approved_at=approved_at,
            public_report=public_report,
        )


class RoutineQueueWorkflowAdapter:
    """Build and privately publish a scheduler-neutral multi-folder queue."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="routine-queue",
        adapter_id="routine_queue_resource.v1",
        status="connected",
        plan_schema="folderhome.routine-queue-resource-plan.v1",
        report_schema="folderhome.routine-queue-resource-report.v1",
        side_effects=("filesystem.private_routine_queue.write",),
        reason=(
            "Reuses the deterministic multi-watch queue through logical resources. "
            "Publishing the private JSON never moves files or registers a scheduler."
        ),
        request_schema=_ROUTINE_QUEUE_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles: ProfileConfiguration,
        extractor: CleanupDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._profiles = profiles
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedRoutineQueue]:
        _validate_exact_request(request, _ROUTINE_QUEUE_REQUEST_SCHEMA, "Routinenqueue")
        if not _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        ):
            raise WorkflowExecutionError(
                "Routinenqueue benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        output_name = _safe_output_name(request["output_name"])
        try:
            state = self._registry.resolve(
                resource_id=_text(request["state_resource_id"], "state_resource_id"),
                profile_id=profile_id,
                purpose="routine_queue.state",
                required_kind="directory",
                required_operations=frozenset({"read"}),
            )
            output = self._registry.resolve(
                resource_id=_text(request["output_resource_id"], "output_resource_id"),
                profile_id=profile_id,
                purpose="routine_queue.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            watches, bindings, item_resources = _routine_queue_configuration(
                registry=self._registry,
                profile_id=profile_id,
                value=request["items"],
            )
            _require_distinct_resources((state, output, *item_resources))
            if (output.local_path / output_name).exists():
                raise WorkflowExecutionError(
                    f"Routinenqueue-Ausgabe existiert bereits: {output_name}"
                )
            as_of = date.fromisoformat(_text(request["as_of"], "as_of"))
            captured_at = _text(request["captured_at"], "captured_at")
            queue = build_folder_routine_queue(
                watches,
                bindings,
                profiles=self._profiles,
                as_of=as_of,
                captured_at=captured_at,
                state_dir=state.local_path,
                extractor=self._extractor,
            )
        except (
            DirectoryObservationError,
            ProfileConfigurationError,
            ResourceRegistryError,
            RoutineQueueError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.routine-queue-resource-plan.v1",
            "queue_id": queue.queue_id,
            "profile_id": profile_id,
            "state_resource_id": state.resource_id,
            "output_resource_id": output.resource_id,
            "output_name": output_name,
            "item_count": len(queue.items),
            "ready_count": queue.summary.get("ready", 0),
            "blocked_count": queue.summary.get("blocked", 0),
            "not_due_count": queue.summary.get("not_due", 0),
            "empty_count": queue.summary.get("empty", 0),
            "scheduler_registered": False,
            "files_moved": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        envelope = _resource_execution_envelope(
            descriptor=self.descriptor,
            domain_plan_id=queue.queue_id,
            public_plan=public_plan,
            approval_kind="explicit_private_routine_queue_write",
        )
        return envelope, _PreparedRoutineQueue(
            queue=queue,
            public_plan=public_plan,
            watches=watches,
            bindings=bindings,
            profiles=self._profiles,
            state_root=state.local_path,
            extractor=self._extractor,
            as_of=as_of,
            captured_at=captured_at,
            output_root=output.local_path,
            output_resource_id=output.resource_id,
            output_name=output_name,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedRoutineQueue):
            raise WorkflowExecutionError("Vorbereitete Routinenqueue besitzt falschen Typ.")
        _verify_resource_envelope(
            envelope,
            domain_plan.queue.queue_id,
            domain_plan.public_plan,
        )
        try:
            current = build_folder_routine_queue(
                domain_plan.watches,
                domain_plan.bindings,
                profiles=domain_plan.profiles,
                as_of=domain_plan.as_of,
                captured_at=domain_plan.captured_at,
                state_dir=domain_plan.state_root,
                extractor=domain_plan.extractor,
            )
            if current.queue_id != domain_plan.queue.queue_id:
                raise WorkflowExecutionError(
                    "Routinenqueue ist seit der Planung veraltet."
                )
            hashes = _publish_private_text_outputs(
                domain_plan.output_root,
                {
                    domain_plan.output_name: json.dumps(
                        current.to_dict(),
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                },
            )
        except (RoutineQueueError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.routine-queue-resource-report.v1",
            "queue_id": current.queue_id,
            "status": "written",
            "output_resource_id": domain_plan.output_resource_id,
            "output_name": domain_plan.output_name,
            "output_sha256": hashes[domain_plan.output_name],
            "item_count": len(current.items),
            "scheduler_registered": False,
            "files_moved": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        return _resource_execution_report(
            envelope=envelope,
            descriptor=self.descriptor,
            approved_at=approved_at,
            public_report=public_report,
        )


class DocumentPackageWorkflowAdapter:
    """Create one deterministic ZIP with one bundled document per source type."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="document-package",
        adapter_id="document_package_resource.v1",
        status="connected",
        plan_schema="folderhome.document-package-resource-plan.v1",
        report_schema="folderhome.document-package-resource-report.v1",
        side_effects=("filesystem.document_package.write",),
        reason=(
            "Reuses the deterministic per-type grouping and atomic ZIP publisher "
            "through configured source and output resource IDs."
        ),
        request_schema=_DOCUMENT_PACKAGE_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: BundleDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedDocumentPackage]:
        expected = set(_DOCUMENT_PACKAGE_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Dokumentpaketanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Dokumentpaketanfrage fehlt Feld: " + missing[0]
            )
        source_id = _text(request["source_resource_id"], "source_resource_id")
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_name = _safe_output_name(request["output_name"])
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        if not sensitive_read:
            raise WorkflowExecutionError(
                "Dokumentpaket benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="document_package.source",
                required_kind="directory",
                required_operations=frozenset({"list", "read", "sensitive_read"}),
            )
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="document_package.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_separate_resources(source.local_path, output.local_path)
            prepared = prepare_folder_package(
                source.local_path,
                output_zip=output.local_path / output_name,
                extractor=self._extractor,
                recursive=_required_bool(request["recursive"], "recursive"),
            )
        except (
            DocumentPackageError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        plan = prepared.plan
        public_plan = {
            "schema": "folderhome.document-package-resource-plan.v1",
            "package_id": plan.package_id,
            "provider_id": plan.provider_id,
            "profile_id": profile_id,
            "source_resource_id": source.resource_id,
            "output_resource_id": output.resource_id,
            "output_name": output_name,
            "group_count": len(plan.groups),
            "group_ids": [item.group_id for item in plan.groups],
            "source_count": sum(len(item.sources) for item in plan.groups),
            "unsupported_source_count": len(plan.unsupported),
            "atomic_zip_write": True,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "document_package_resource.v1",
            domain_plan_id=plan.package_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_atomic_document_package_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedDocumentPackage(
            prepared=prepared,
            public_plan=public_plan,
            source_resource_id=source.resource_id,
            output_resource_id=output.resource_id,
            output_name=output_name,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedDocumentPackage):
            raise WorkflowExecutionError("Vorbereitetes Dokumentpaket besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.prepared.plan.package_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Dokumentpaketplan überein."
            )
        try:
            result = write_folder_package(
                domain_plan.prepared,
                allow_output_write=True,
            )
        except (DocumentPackageError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.document-package-resource-report.v1",
            "package_id": result.package_id,
            "status": "executed",
            "source_resource_id": domain_plan.source_resource_id,
            "output_resource_id": domain_plan.output_resource_id,
            "output_name": domain_plan.output_name,
            "output_sha256": result.output_sha256,
            "output_size_bytes": result.output_size_bytes,
            "entry_count": len(result.entries),
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "document_package_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class ArtifactStudioWorkflowAdapter:
    """Create a reusable local design set and SVG business-card preview."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="artifact-studio",
        adapter_id="artifact_studio_resource.v1",
        status="connected",
        plan_schema="folderhome.artifact-studio-resource-plan.v1",
        report_schema="folderhome.artifact-studio-resource-report.v1",
        side_effects=("filesystem.design_assets.write",),
        reason=(
            "Reuses the local accessible design-set and business-card renderer. "
            "The SVG remains a preview and still requires human visual review."
        ),
        request_schema=_ARTIFACT_STUDIO_REQUEST_SCHEMA,
    )

    def __init__(self, *, registry: ResourceRegistry) -> None:
        self._registry = registry

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedArtifactStudio]:
        expected = set(_ARTIFACT_STUDIO_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Designanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError("Designanfrage fehlt Feld: " + missing[0])
        colors = _strict_request_object(
            request["colors"],
            "colors",
            {"primary", "on_primary", "background", "text", "accent"},
        )
        fonts = _strict_request_object(
            request["fonts"],
            "fonts",
            {"heading", "body"},
        )
        card = _strict_request_object(
            request["business_card"],
            "business_card",
            {"name", "role", "organization", "email", "phone", "website"},
        )
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_basename = _safe_output_basename(request["output_basename"])
        try:
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="artifact_studio.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            design_request = DesignStudioRequest(
                profile_id=profile_id,
                design_set_id=_text(request["design_set_id"], "design_set_id"),
                display_name=_text(request["display_name"], "display_name"),
                purpose=_text(request["purpose"], "purpose"),
                colors=DesignColors(
                    primary=_text(colors["primary"], "colors.primary"),
                    on_primary=_text(colors["on_primary"], "colors.on_primary"),
                    background=_text(colors["background"], "colors.background"),
                    text=_text(colors["text"], "colors.text"),
                    accent=_text(colors["accent"], "colors.accent"),
                ),
                fonts=DesignFonts(
                    heading=_text(fonts["heading"], "fonts.heading"),
                    body=_text(fonts["body"], "fonts.body"),
                ),
                business_card=BusinessCardContent(
                    name=_text(card["name"], "business_card.name"),
                    role=_text(card["role"], "business_card.role"),
                    organization=_text(
                        card["organization"],
                        "business_card.organization",
                    ),
                    email=_optional_text(card["email"], "business_card.email"),
                    phone=_optional_text(card["phone"], "business_card.phone"),
                    website=_optional_text(card["website"], "business_card.website"),
                ),
            )
            preview = build_design_preview(design_request)
            for suffix in (".json", ".css", ".svg"):
                if (output.local_path / f"{output_basename}{suffix}").exists():
                    raise WorkflowExecutionError(
                        f"Designausgabe existiert bereits: {output_basename}{suffix}"
                    )
        except (
            ArtifactStudioError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.artifact-studio-resource-plan.v1",
            "preview_id": preview.preview_id,
            "profile_id": profile_id,
            "design_set_id": design_request.design_set_id,
            "output_resource_id": output.resource_id,
            "output_basename": output_basename,
            "output_count": 3,
            "json_sha256": preview.json_sha256,
            "css_sha256": preview.css_sha256,
            "svg_sha256": preview.svg_sha256,
            "contrast_checks_passed": all(
                passed for _name, passed in preview.contrast_checks
            ),
            "visual_qa_passed": False,
            "remote_provider_invoked": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "artifact_studio_resource.v1",
            domain_plan_id=preview.preview_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_local_design_asset_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedArtifactStudio(
            preview=preview,
            public_plan=public_plan,
            output_root=output.local_path,
            output_resource_id=output.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedArtifactStudio):
            raise WorkflowExecutionError("Vorbereitete Designausgabe besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.preview.preview_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Designvorschau überein."
            )
        try:
            report = write_design_outputs(
                domain_plan.preview,
                json_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.json"
                ),
                css_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.css"
                ),
                business_card_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.svg"
                ),
                allow_output_write=True,
            )
        except (ArtifactStudioError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.artifact-studio-resource-report.v1",
            "report_id": report.report_id,
            "preview_id": report.preview_id,
            "status": report.status,
            "output_resource_id": domain_plan.output_resource_id,
            "output_basename": domain_plan.output_basename,
            "output_count": 3,
            "json_sha256": report.json_sha256,
            "css_sha256": report.css_sha256,
            "svg_sha256": report.svg_sha256,
            "visual_qa_passed": False,
            "remote_provider_invoked": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "artifact_studio_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class ContractCockpitWorkflowAdapter:
    """Synthesize contract evidence from the existing private local stores."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="contract-cockpit",
        adapter_id="contract_cockpit_resource.v1",
        status="connected",
        plan_schema="folderhome.contract-cockpit-resource-plan.v1",
        report_schema="folderhome.contract-cockpit-resource-report.v1",
        side_effects=("filesystem.contract_cockpit.write",),
        reason=(
            "Reuses document version analysis plus contact, finance and calendar "
            "stores. It writes a private evidence synthesis but proves no contract status."
        ),
        request_schema=_CONTRACT_COCKPIT_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        searcher: DocumentSearcher,
        extractor: BundleDocumentExtractor,
        expected_state_root: Path | None = None,
    ) -> None:
        self._registry = registry
        self._searcher = searcher
        self._extractor = extractor
        self._expected_state_root = (
            expected_state_root.resolve() if expected_state_root is not None else None
        )

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedContractCockpit]:
        expected = set(_CONTRACT_COCKPIT_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Vertragscockpitanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Vertragscockpitanfrage fehlt Feld: " + missing[0]
            )
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        if not sensitive_read:
            raise WorkflowExecutionError(
                "Vertragscockpit benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        state_id = _text(request["state_resource_id"], "state_resource_id")
        output_id = _text(request["output_resource_id"], "output_resource_id")
        output_basename = _safe_output_basename(request["output_basename"])
        try:
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="contract_cockpit.state",
                required_kind="directory",
                required_operations=frozenset({"read", "sensitive_read"}),
            )
            output = self._registry.resolve(
                resource_id=output_id,
                profile_id=profile_id,
                purpose="contract_cockpit.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            _require_separate_resources(state.local_path, output.local_path)
            if (
                self._expected_state_root is not None
                and state.local_path != self._expected_state_root
            ):
                raise WorkflowExecutionError(
                    "Cockpit-State stimmt nicht mit dem lokalen Suchindex-State überein."
                )
            cockpit_request = ContractCockpitRequest(
                profile_id=profile_id,
                area=_text(request["area"], "area"),
                display_name=_text(request["display_name"], "display_name"),
                document_query=_text(request["document_query"], "document_query"),
                object_ref=_text(request["object_ref"], "object_ref"),
                counterparty_terms=_strict_text_list(
                    request["counterparty_terms"],
                    "counterparty_terms",
                    allow_empty=True,
                ),
                calendar_terms=_strict_text_list(
                    request["calendar_terms"],
                    "calendar_terms",
                    allow_empty=True,
                ),
                account_refs=_strict_text_list(
                    request["account_refs"],
                    "account_refs",
                    allow_empty=True,
                ),
                coverage_start=_text(request["coverage_start"], "coverage_start"),
                as_of=_text(request["as_of"], "as_of"),
                archive_older_versions=_required_bool(
                    request["archive_older_versions"],
                    "archive_older_versions",
                ),
            )
            version_analysis = analyze_document_versions(
                cockpit_request.document_query,
                catalog=DocumentCatalogStore(state.local_path),
                searcher=self._searcher,
                extractor=self._extractor,
            )
            contacts_store = ContactRegisterStore(state.local_path)
            finance_store = FinanceStore(state.local_path)
            calendar_store = CalendarStore(state.local_path)
            recurring_report = build_recurring_cost_report(
                store=finance_store,
                profile_id=profile_id,
                as_of=cockpit_request.as_of,
            )
            report = build_contract_cockpit(
                cockpit_request,
                version_analysis=version_analysis,
                contacts=contacts_store.list_contacts(
                    profile_id=profile_id,
                    area=cockpit_request.area,
                    object_query=cockpit_request.object_ref,
                    include_deletion_candidates=True,
                ),
                recurring_report=recurring_report,
                calendar_events=calendar_store.list_events(
                    profile_id=profile_id,
                    area=cockpit_request.area,
                    date_from=cockpit_request.as_of,
                ),
                finance_coverages=tuple(
                    finance_store.coverage(
                        account_ref=account_ref,
                        date_from=cockpit_request.coverage_start,
                        date_to=cockpit_request.as_of,
                    )
                    for account_ref in cockpit_request.account_refs
                ),
                component_revisions={
                    "contacts": contacts_store.revision(),
                    "finance": finance_store.revision(),
                    "calendar": calendar_store.revision(),
                    "document_family": version_analysis.family.family_id,
                },
            )
        except (
            CalendarStoreError,
            ContactRegisterError,
            DocumentCatalogError,
            DocumentVersionAnalysisError,
            FinanceStoreError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.contract-cockpit-resource-plan.v1",
            "report_id": report.report_id,
            "profile_id": profile_id,
            "state_resource_id": state.resource_id,
            "output_resource_id": output.resource_id,
            "output_basename": output_basename,
            "latest_document_found": True,
            "older_version_count": len(report.older_versions),
            "archive_proposal_count": len(report.archive_proposals),
            "current_contact_count": len(report.current_contacts),
            "recurring_cost_count": len(report.recurring_costs),
            "calendar_event_count": len(report.calendar_events),
            "finance_coverage_count": len(report.finance_coverages),
            "component_issue_count": len(report.component_issues),
            "contract_status_proven": False,
            "automatic_archive_executed": False,
            "automatic_contact_change": False,
            "automatic_calendar_action": False,
            "payment_or_bank_access": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "contract_cockpit_resource.v1",
            domain_plan_id=report.report_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_private_contract_cockpit_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedContractCockpit(
            report=report,
            public_plan=public_plan,
            state_root=state.local_path,
            output_root=output.local_path,
            state_resource_id=state.resource_id,
            output_resource_id=output.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedContractCockpit):
            raise WorkflowExecutionError("Vorbereitetes Vertragscockpit besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.report.report_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Vertragscockpit überein."
            )
        try:
            current_revisions = {
                "contacts": ContactRegisterStore(domain_plan.state_root).revision(),
                "finance": FinanceStore(domain_plan.state_root).revision(),
                "calendar": CalendarStore(domain_plan.state_root).revision(),
            }
            for key, value in current_revisions.items():
                if domain_plan.report.component_revisions[key] != value:
                    raise WorkflowExecutionError(
                        f"Cockpit-Komponente wurde seit der Planung verändert: {key}"
                    )
            versions = (
                domain_plan.report.latest_version,
                *domain_plan.report.older_versions,
            )
            for version in versions:
                source = version.document.source_path
                if (
                    not source.is_file()
                    or source.is_symlink()
                    or sha256(source.read_bytes()).hexdigest()
                    != version.document.source_sha256
                ):
                    raise WorkflowExecutionError(
                        "Cockpit-Dokument wurde seit der Planung verändert."
                    )
            hashes = _publish_private_text_outputs(
                domain_plan.output_root,
                {
                    f"{domain_plan.output_basename}.md": domain_plan.report.markdown,
                    f"{domain_plan.output_basename}.json": json.dumps(
                        domain_plan.report.to_dict(),
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                },
            )
        except (
            CalendarStoreError,
            ContactRegisterError,
            FinanceStoreError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.contract-cockpit-resource-report.v1",
            "report_id": domain_plan.report.report_id,
            "status": "executed",
            "state_resource_id": domain_plan.state_resource_id,
            "output_resource_id": domain_plan.output_resource_id,
            "output_basename": domain_plan.output_basename,
            "output_hashes": hashes,
            "contract_status_proven": False,
            "automatic_archive_executed": False,
            "automatic_contact_change": False,
            "automatic_calendar_action": False,
            "payment_or_bank_access": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "contract_cockpit_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class FcsaDryRunWorkflowAdapter:
    """Invoke only the pinned FCSA dry-run over explicitly bound resources."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="fcsa-dry-run",
        adapter_id="fcsa_dry_run_resource.v1",
        status="connected",
        plan_schema="folderhome.fcsa-dry-run-resource-plan.v1",
        report_schema="folderhome.fcsa-dry-run-resource-report.v1",
        side_effects=("provider.fcsa.local_dry_run.invoke",),
        reason=(
            "Runs the pinned FCSA provider only in shadow-state dry-run mode after "
            "validating every configured scan and target against logical resources."
        ),
        request_schema=_FCSA_DRY_RUN_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        plugin: PluginDescriptor,
        bridge: FcsaPlanProvider,
    ) -> None:
        self._registry = registry
        self._plugin = plugin
        self._bridge = bridge

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedFcsaDryRun]:
        expected = set(_FCSA_DRY_RUN_REQUEST_SCHEMA["required"])
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in FCSA-Dry-Run-Anfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "FCSA-Dry-Run-Anfrage fehlt Feld: " + missing[0]
            )
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        if not sensitive_read:
            raise WorkflowExecutionError(
                "FCSA-Dry-Run benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
            )
        config_id = _text(request["config_resource_id"], "config_resource_id")
        scan_ids = _strict_text_list(
            request["scan_resource_ids"],
            "scan_resource_ids",
            allow_empty=False,
        )
        target_ids = _strict_text_list(
            request["target_resource_ids"],
            "target_resource_ids",
            allow_empty=False,
        )
        try:
            config = self._registry.resolve(
                resource_id=config_id,
                profile_id=profile_id,
                purpose="fcsa.config",
                required_kind="directory",
                required_operations=frozenset({"read", "sensitive_read"}),
            )
            scans = tuple(
                self._registry.resolve(
                    resource_id=resource_id,
                    profile_id=profile_id,
                    purpose="fcsa.scan",
                    required_kind="directory",
                    required_operations=frozenset(
                        {"list", "read", "sensitive_read"}
                    ),
                )
                for resource_id in scan_ids
            )
            targets = tuple(
                self._registry.resolve(
                    resource_id=resource_id,
                    profile_id=profile_id,
                    purpose="fcsa.target",
                    required_kind="directory",
                    required_operations=frozenset({"create", "move"}),
                )
                for resource_id in target_ids
            )
            for item in (*scans, *targets):
                _require_separate_resources(config.local_path, item.local_path)
            for scan in scans:
                for target in targets:
                    _require_separate_resources(scan.local_path, target.local_path)
            config_payload = _load_strict_json_file(
                config.local_path / "config.json",
                "FCSA config.json",
            )
            raw_scan_paths = config_payload.get("scan_paths")
            if not isinstance(raw_scan_paths, list) or not all(
                isinstance(item, str) for item in raw_scan_paths
            ):
                raise WorkflowExecutionError(
                    "FCSA config.json besitzt keine gültigen scan_paths."
                )
            configured_scans = {
                _resolve_config_path(item, config.local_path) for item in raw_scan_paths
            }
            allowed_scans = {item.local_path for item in scans}
            if configured_scans != allowed_scans:
                raise WorkflowExecutionError(
                    "FCSA scan_paths stimmen nicht exakt mit scan_resource_ids überein."
                )
            categories_payload = _load_strict_json_file(
                config.local_path / "categories-definitions.json",
                "FCSA categories-definitions.json",
            )
            raw_categories = categories_payload.get("categories")
            if not isinstance(raw_categories, list):
                raise WorkflowExecutionError(
                    "FCSA-Kategorien besitzen keine gültige categories-Liste."
                )
            configured_targets = {
                _resolve_config_path(item["default_target"], config.local_path)
                for item in raw_categories
                if isinstance(item, dict)
                and isinstance(item.get("default_target"), str)
            }
            allowed_targets = {item.local_path for item in targets}
            if configured_targets != allowed_targets:
                raise WorkflowExecutionError(
                    "FCSA-Ziele stimmen nicht exakt mit target_resource_ids überein."
                )
            config_hashes = {
                name: sha256((config.local_path / name).read_bytes()).hexdigest()
                for name in CONFIG_FILENAMES
            }
        except (
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        run_material = {
            "profile_id": profile_id,
            "config_resource_id": config.resource_id,
            "scan_resource_ids": scan_ids,
            "target_resource_ids": target_ids,
            "config_hashes": config_hashes,
            "provider_revision": self._plugin.source_revision,
        }
        run_id = "run_fcsa_agent_" + sha256(_canonical_json(run_material)).hexdigest()[:24]
        public_plan = {
            "schema": "folderhome.fcsa-dry-run-resource-plan.v1",
            "run_id": run_id,
            "profile_id": profile_id,
            "config_resource_id": config.resource_id,
            "scan_resource_ids": list(scan_ids),
            "target_resource_ids": list(target_ids),
            "provider_id": self._plugin.plugin_id,
            "provider_version": self._plugin.version,
            "provider_revision": self._plugin.source_revision,
            "config_hashes": config_hashes,
            "dry_run": True,
            "shadow_state": True,
            "live_execution_supported": False,
            "filesystem_mutated": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "fcsa_dry_run_resource.v1",
            domain_plan_id=run_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_local_fcsa_provider_dry_run",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedFcsaDryRun(
            public_plan=public_plan,
            config_root=config.local_path,
            config_hashes=config_hashes,
            run_id=run_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedFcsaDryRun):
            raise WorkflowExecutionError("Vorbereiteter FCSA-Dry-Run besitzt falschen Typ.")
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.run_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit FCSA-Dry-Run-Plan überein."
            )
        try:
            current_hashes = {
                name: sha256((domain_plan.config_root / name).read_bytes()).hexdigest()
                for name in CONFIG_FILENAMES
            }
            if current_hashes != domain_plan.config_hashes:
                raise WorkflowExecutionError(
                    "FCSA-Konfiguration wurde seit der Planung verändert."
                )
            report: RunReport = run_fcsa_plan(
                domain_plan.config_root,
                run_id=domain_plan.run_id,
                plugin=self._plugin,
                bridge=self._bridge,
            )
        except (FcsaBridgeError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.fcsa-dry-run-resource-report.v1",
            "run_id": report.run_id,
            "status": report.status.value,
            "provider_id": report.plugin_id,
            "capability_id": report.capability_id,
            "action_count": len(report.actions),
            "planned_mutation_count": sum(
                action.gate.required for action in report.actions
            ),
            "failed_action_count": sum(
                action.status.value == "failed" for action in report.actions
            ),
            "decision_count": len(report.decisions),
            "dry_run": report.dry_run,
            "shadow_state": True,
            "live_execution_supported": False,
            "filesystem_mutated": False,
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "fcsa_dry_run_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class LocalCalendarWorkflowAdapter:
    """Write evidence-bound appointments to FolderHome's own local calendar only."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="calendar-handoff",
        adapter_id="local_calendar_resource.v1",
        status="connected",
        plan_schema="folderhome.local-calendar-resource-plan.v1",
        report_schema="folderhome.local-calendar-resource-report.v1",
        side_effects=("state.calendar.write",),
        reason=(
            "Reuses the existing calendar evidence and revision workflow but permits only "
            "the FolderHome local backend; no external connector is invoked."
        ),
        request_schema=_LOCAL_CALENDAR_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        profiles: ProfileConfiguration,
        extractor: CalendarDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._profiles = profiles
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedLocalCalendar]:
        expected = {
            "source_resource_id",
            "configuration_resource_id",
            "state_resource_id",
            "area",
            "planned_at",
            "recursive",
            "allow_sensitive_local_read",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in lokaler Kalenderanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Lokale Kalenderanfrage fehlt Feld: " + missing[0]
            )
        source_id = _text(request["source_resource_id"], "source_resource_id")
        config_id = _text(
            request["configuration_resource_id"],
            "configuration_resource_id",
        )
        state_id = _text(request["state_resource_id"], "state_resource_id")
        area = _text(request["area"], "area")
        planned_at = _text(request["planned_at"], "planned_at")
        recursive = _required_bool(request["recursive"], "recursive")
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        source_operations = {"list", "read"}
        if sensitive_read:
            source_operations.add("sensitive_read")
        try:
            source = self._registry.resolve(
                resource_id=source_id,
                profile_id=profile_id,
                purpose="calendar.source",
                required_kind="directory",
                required_operations=frozenset(source_operations),
            )
            configuration_resource = self._registry.resolve(
                resource_id=config_id,
                profile_id=profile_id,
                purpose="calendar.configuration",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            state = self._registry.resolve(
                resource_id=state_id,
                profile_id=profile_id,
                purpose="calendar.state",
                required_kind="local_calendar",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_separate_resources(source.local_path, state.local_path)
            configuration = load_calendar_configuration(
                configuration_resource.local_path
            )
            policy = resolve_profile_policy(
                self._profiles,
                profile_id=profile_id,
                area=area,
            )
            backend, _, timezone, _ = resolve_calendar_preferences(
                configuration,
                policy,
            )
            if backend is not CalendarBackend.FOLDERHOME_LOCAL:
                raise WorkflowExecutionError(
                    "Dieser Adapter erlaubt ausschließlich folderhome_local; "
                    "externe Kalender bleiben getrennt gegatet."
                )
            analysis = analyze_folder_calendar(
                source.local_path,
                profile_id=profile_id,
                area=area,
                default_timezone=timezone,
                extractor=self._extractor,
                recursive=recursive,
                allow_sensitive_local_read=sensitive_read,
            )
            store = CalendarStore(state.local_path)
            plan = build_calendar_handoff_plan(
                analysis,
                configuration=configuration,
                policy=policy,
                planned_at=planned_at,
                calendar_revision=store.revision(),
                existing_events=store.list_events(),
            )
        except (
            CalendarStoreError,
            CalendarWorkflowError,
            ProfileConfigurationError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _redact_physical_paths(plan.to_dict())
        public_plan.update(
            {
                "schema": "folderhome.local-calendar-resource-plan.v1",
                "source_resource_id": source.resource_id,
                "configuration_resource_id": configuration_resource.resource_id,
                "state_resource_id": state.resource_id,
                "planned_action_count": sum(
                    item.status == "planned" for item in plan.actions
                ),
                "paths_disclosed": False,
                "connector_invoked": False,
            }
        )
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "local_calendar_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_local_calendar_state_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedLocalCalendar(
            plan=plan,
            public_plan=public_plan,
            store=store,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedLocalCalendar):
            raise WorkflowExecutionError(
                "Vorbereiteter lokaler Kalenderplan besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit lokalem Kalenderplan überein."
            )
        action_ids = tuple(
            item.action_id
            for item in domain_plan.plan.actions
            if item.status == "planned"
        )
        if not action_ids:
            raise WorkflowExecutionError(
                "Lokaler Kalenderplan enthält keine ausführbare Änderung."
            )
        approval = CalendarHandoffApproval(
            approval_id=f"agent_calendar_{secrets.token_hex(10)}",
            plan_id=domain_plan.plan.plan_id,
            calendar_revision=domain_plan.plan.calendar_revision,
            action_ids=action_ids,
            approved_at=approved_at,
        )
        try:
            report = apply_calendar_handoff_plan(
                domain_plan.plan,
                approval,
                store=domain_plan.store,
                allow_state_write=True,
                allow_output_write=False,
            )
        except (
            CalendarStoreError,
            CalendarWorkflowError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = _redact_physical_paths(report.to_dict())
        public_report.update(
            {
                "schema": "folderhome.local-calendar-resource-report.v1",
                "state_resource_id": domain_plan.state_resource_id,
                "connector_invoked": False,
                "paths_disclosed": False,
            }
        )
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "local_calendar_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class CorrespondenceWorkflowAdapter:
    """Render one existing local letter request through logical resources."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="correspondence-studio",
        adapter_id="correspondence_resource.v1",
        status="connected",
        plan_schema="folderhome.correspondence-resource-plan.v1",
        report_schema="folderhome.correspondence-resource-report.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the deterministic correspondence templates and designs. Full letter "
            "content remains local; the agent receives only IDs, subject and hashes."
        ),
        request_schema=_CORRESPONDENCE_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        report_forge_revision: str,
        report_forge_distribution_version: str,
        report_forge_runtime_version: str,
    ) -> None:
        self._registry = registry
        self._report_forge_revision = report_forge_revision
        self._report_forge_distribution_version = report_forge_distribution_version
        self._report_forge_runtime_version = report_forge_runtime_version

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedCorrespondence]:
        expected = {
            "request_resource_id",
            "designs_resource_id",
            "templates_resource_id",
            "output_resource_id",
            "output_basename",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Korrespondenzanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Korrespondenzanfrage fehlt Feld: " + missing[0]
            )
        resource_ids = {
            name: _text(request[name], name)
            for name in (
                "request_resource_id",
                "designs_resource_id",
                "templates_resource_id",
                "output_resource_id",
            )
        }
        output_basename = _safe_output_basename(request["output_basename"])
        try:
            request_resource = self._registry.resolve(
                resource_id=resource_ids["request_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.request",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            designs_resource = self._registry.resolve(
                resource_id=resource_ids["designs_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.designs",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            templates_resource = self._registry.resolve(
                resource_id=resource_ids["templates_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.templates",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            output_resource = self._registry.resolve(
                resource_id=resource_ids["output_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            correspondence_request = load_correspondence_request(
                request_resource.local_path
            )
            if correspondence_request.profile_id != profile_id:
                raise WorkflowExecutionError(
                    "Korrespondenzanfrage gehört zu einem anderen Profil."
                )
            configuration = load_correspondence_configuration(
                designs_resource.local_path,
                templates_resource.local_path,
            )
            preview = build_correspondence_preview(
                correspondence_request,
                configuration=configuration,
                report_forge_revision=self._report_forge_revision,
                report_forge_distribution_version=(
                    self._report_forge_distribution_version
                ),
                report_forge_runtime_version=self._report_forge_runtime_version,
            )
        except (
            CorrespondenceError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.correspondence-resource-plan.v1",
            "preview_id": preview.preview_id,
            **resource_ids,
            "output_basename": output_basename,
            "profile_id": profile_id,
            "area": preview.request.area,
            "purpose": preview.request.purpose,
            "template_id": preview.template.template_id,
            "design_id": preview.design.design_id,
            "subject": preview.subject,
            "markdown_sha256": preview.markdown_sha256,
            "text_sha256": preview.text_sha256,
            "render_handoffs": [item.to_dict() for item in preview.render_handoffs],
            "content_disclosed": False,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "correspondence_resource.v1",
            domain_plan_id=preview.preview_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_resource_bound_output_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedCorrespondence(
            preview=preview,
            public_plan=public_plan,
            output_root=output_resource.local_path,
            output_resource_id=output_resource.resource_id,
            output_basename=output_basename,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedCorrespondence):
            raise WorkflowExecutionError(
                "Vorbereiteter Korrespondenzplan besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.preview.preview_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Korrespondenzplan überein."
            )
        try:
            report = write_correspondence_outputs(
                domain_plan.preview,
                markdown_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.md"
                ),
                text_file=(
                    domain_plan.output_root / f"{domain_plan.output_basename}.txt"
                ),
                allow_output_write=True,
            )
        except (CorrespondenceError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.correspondence-resource-report.v1",
            "report_id": report.report_id,
            "preview_id": report.preview_id,
            "status": report.status,
            "output_resource_id": domain_plan.output_resource_id,
            "markdown_name": report.markdown_file.name,
            "text_name": report.text_file.name,
            "markdown_sha256": report.markdown_sha256,
            "text_sha256": report.text_sha256,
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "correspondence_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class MailDraftWorkflowAdapter:
    """Place one prepared letter into the drafts folder of the user's own mailbox."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="mail-connector",
        adapter_id="mail_draft_resource.v1",
        status="connected",
        plan_schema="folderhome.mail-draft-resource-plan.v1",
        report_schema="folderhome.mail-draft-resource-report.v1",
        side_effects=("external.mailbox.draft_write",),
        reason=(
            "Appends one prepared letter to the configured drafts folder of the "
            "user's own mailbox. There is no send path at all: no recipient is "
            "contacted, the mailbox password is read only from its configured local "
            "file, and the separate live-effect approval stays required."
        ),
        request_schema=_MAIL_DRAFT_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        state_dir: Path,
        report_forge_revision: str,
        report_forge_distribution_version: str,
        report_forge_runtime_version: str,
        allow_mail_draft: bool,
        transport_factory: Callable[[MailDraftAccount], MailDraftTransport] | None = None,
    ) -> None:
        self._registry = registry
        self._state_dir = state_dir
        self._report_forge_revision = report_forge_revision
        self._report_forge_distribution_version = report_forge_distribution_version
        self._report_forge_runtime_version = report_forge_runtime_version
        self._allow_mail_draft = allow_mail_draft
        self._transport_factory = transport_factory or _imap_draft_transport

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedMailDraft]:
        expected = {
            "account_resource_id",
            "request_resource_id",
            "designs_resource_id",
            "templates_resource_id",
            "planned_at",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Mailentwurfsanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Mailentwurfsanfrage fehlt Feld: " + missing[0]
            )
        resource_ids = {
            name: _text(request[name], name)
            for name in (
                "account_resource_id",
                "request_resource_id",
                "designs_resource_id",
                "templates_resource_id",
            )
        }
        planned_at = _text(request["planned_at"], "planned_at")
        try:
            account_resource = self._registry.resolve(
                resource_id=resource_ids["account_resource_id"],
                profile_id=profile_id,
                purpose="mail.draft_account",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            request_resource = self._registry.resolve(
                resource_id=resource_ids["request_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.request",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            designs_resource = self._registry.resolve(
                resource_id=resource_ids["designs_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.designs",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            templates_resource = self._registry.resolve(
                resource_id=resource_ids["templates_resource_id"],
                profile_id=profile_id,
                purpose="correspondence.templates",
                required_kind="file",
                required_operations=frozenset({"read"}),
            )
            account = load_mail_draft_account(account_resource.local_path)
            if account.profile_id != profile_id:
                raise WorkflowExecutionError(
                    "Entwurfskonto gehört zu einem anderen Profil."
                )
            correspondence_request = load_correspondence_request(
                request_resource.local_path
            )
            if correspondence_request.profile_id != profile_id:
                raise WorkflowExecutionError(
                    "Korrespondenzanfrage gehört zu einem anderen Profil."
                )
            configuration = load_correspondence_configuration(
                designs_resource.local_path,
                templates_resource.local_path,
            )
            preview = build_correspondence_preview(
                correspondence_request,
                configuration=configuration,
                report_forge_revision=self._report_forge_revision,
                report_forge_distribution_version=(
                    self._report_forge_distribution_version
                ),
                report_forge_runtime_version=self._report_forge_runtime_version,
            )
            message = build_mail_draft_message(
                preview,
                account=account,
                planned_at=planned_at,
            )
        except (
            CorrespondenceError,
            MailDraftError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = {
            "schema": "folderhome.mail-draft-resource-plan.v1",
            **resource_ids,
            **message.to_public_dict(),
            **account.to_public_dict(),
            "live_effect_approved": self._allow_mail_draft,
            "paths_disclosed": False,
        }
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "mail_draft_resource.v1",
            domain_plan_id=message.draft_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_mailbox_draft_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedMailDraft(
            message=message,
            public_plan=public_plan,
            account=account,
            account_resource_id=account_resource.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedMailDraft):
            raise WorkflowExecutionError(
                "Vorbereiteter Mailentwurf besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.message.draft_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit dem Mailentwurf überein."
            )
        if not self._allow_mail_draft:
            raise WorkflowExecutionError(
                "Die Entwurfsablage in ein echtes Postfach benötigt die getrennte "
                "Freigabe --approve-mail-draft."
            )
        try:
            transport = self._transport_factory(domain_plan.account)
            report = append_mail_draft(
                domain_plan.message,
                account=domain_plan.account,
                transport=transport,
                ledger=MailDraftLedger(self._state_dir),
                allow_mailbox_write=True,
                appended_at=approved_at,
            )
        except (MailDraftError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = dict(report.to_dict())
        public_report.update(
            {
                "schema": "folderhome.mail-draft-resource-report.v1",
                "account_resource_id": domain_plan.account_resource_id,
                "provider_id": MAIL_DRAFT_PROVIDER_ID,
                "paths_disclosed": False,
            }
        )
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "mail_draft_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


def _imap_draft_transport(account: MailDraftAccount) -> MailDraftTransport:
    """Build the real IMAP transport and read the password exactly once."""

    return ImapDraftTransport(
        host=account.host,
        port=account.port,
        username=account.username,
        password=read_mailbox_password(account),
    )


class ContactRegisterWorkflowAdapter:
    """Maintain the existing local contact register through logical resources."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="contact-register",
        adapter_id="contact_register_resource.v1",
        status="connected",
        plan_schema="folderhome.contact-register-resource-plan.v1",
        report_schema="folderhome.contact-register-resource-report.v1",
        side_effects=("state.contacts.write",),
        reason=(
            "Reuses the existing evidence-bound contact extraction and revision-bound "
            "register update through profile-scoped source and state resource IDs."
        ),
        request_schema=_CONTACT_REGISTER_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: ContactDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedContactRegister]:
        expected = {
            "source_resource_id",
            "state_resource_id",
            "area",
            "recursive",
            "allow_sensitive_local_read",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Kontaktregisteranfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Kontaktregisteranfrage fehlt Feld: " + missing[0]
            )
        source_resource_id = _text(
            request["source_resource_id"],
            "source_resource_id",
        )
        state_resource_id = _text(request["state_resource_id"], "state_resource_id")
        area = _text(request["area"], "area")
        recursive = _required_bool(request["recursive"], "recursive")
        sensitive_read = _required_bool(
            request["allow_sensitive_local_read"],
            "allow_sensitive_local_read",
        )
        source_operations = {"list", "read"}
        if sensitive_read:
            source_operations.add("sensitive_read")
        try:
            source = self._registry.resolve(
                resource_id=source_resource_id,
                profile_id=profile_id,
                purpose="contacts.source",
                required_kind="directory",
                required_operations=frozenset(source_operations),
            )
            state = self._registry.resolve(
                resource_id=state_resource_id,
                profile_id=profile_id,
                purpose="contacts.state",
                required_kind="directory",
                required_operations=frozenset({"read", "state_write"}),
            )
            _require_separate_resources(source.local_path, state.local_path)
            analysis = analyze_folder_contacts(
                source.local_path,
                profile_id=profile_id,
                area=area,
                extractor=self._extractor,
                recursive=recursive,
                allow_sensitive_local_read=sensitive_read,
            )
            store = ContactRegisterStore(state.local_path)
            plan = build_contact_register_plan(analysis, store=store)
        except (
            ContactRegisterError,
            ContactWorkflowError,
            ResourceRegistryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_contact_register_plan(
            plan,
            source_resource_id=source.resource_id,
            state_resource_id=state.resource_id,
        )
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "contact_register_resource.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_resource_bound_state_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedContactRegister(
            plan=plan,
            public_plan=public_plan,
            store=store,
            state_resource_id=state.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedContactRegister):
            raise WorkflowExecutionError(
                "Vorbereiteter Kontaktregisterplan besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Kontaktregisterplan überein."
            )
        action_ids = tuple(
            item.action_id
            for item in domain_plan.plan.actions
            if item.status == "planned"
        )
        if not action_ids:
            raise WorkflowExecutionError(
                "Kontaktregisterplan enthält keine ausführbare Änderung."
            )
        approval = ContactRegisterApproval(
            approval_id=f"agent_contact_{secrets.token_hex(10)}",
            plan_id=domain_plan.plan.plan_id,
            register_revision=domain_plan.plan.register_revision,
            action_ids=action_ids,
            approved_at=approved_at,
        )
        try:
            report = apply_contact_register_plan(
                domain_plan.plan,
                approval,
                store=domain_plan.store,
                allow_state_write=True,
            )
        except (
            ContactRegisterError,
            ContactWorkflowError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = _redact_physical_paths(report.to_dict())
        public_report.update(
            {
                "schema": "folderhome.contact-register-resource-report.v1",
                "state_resource_id": domain_plan.state_resource_id,
                "created_contact_count": len(report.created_contact_ids),
                "marked_contact_count": len(report.marked_contact_ids),
                "paths_disclosed": False,
            }
        )
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "contact_register_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class DocumentBundleWorkflowAdapter:
    """Create one local document bundle from profile-bound logical resources."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="document-bundle",
        adapter_id="document_bundle_resource.v1",
        status="connected",
        plan_schema="folderhome.document-bundle-resource-plan.v1",
        report_schema="folderhome.document-bundle-resource-result.v1",
        side_effects=("file.create",),
        reason=(
            "Reuses the existing deterministic document bundle service while resolving "
            "source and output exclusively through profile-bound logical resource IDs."
        ),
        request_schema=_DOCUMENT_BUNDLE_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        registry: ResourceRegistry,
        extractor: BundleDocumentExtractor,
    ) -> None:
        self._registry = registry
        self._extractor = extractor

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedDocumentBundle]:
        expected = {
            "source_resource_id",
            "output_resource_id",
            "output_name",
            "format",
            "recursive",
        }
        unknown = sorted(set(request).difference(expected))
        missing = sorted(expected.difference(request))
        if unknown:
            raise WorkflowExecutionError(
                "Unbekannte Felder in Dokumentbündelanfrage: " + ", ".join(unknown)
            )
        if missing:
            raise WorkflowExecutionError(
                "Dokumentbündelanfrage fehlt Feld: " + missing[0]
            )
        source_resource_id = _text(
            request["source_resource_id"],
            "source_resource_id",
        )
        output_resource_id = _text(
            request["output_resource_id"],
            "output_resource_id",
        )
        output_name = _safe_output_name(request["output_name"])
        recursive = _required_bool(request["recursive"], "recursive")
        try:
            output_format = BundleFormat(_text(request["format"], "format"))
            source = self._registry.resolve(
                resource_id=source_resource_id,
                profile_id=profile_id,
                purpose="documents.bundle.source",
                required_kind="directory",
                required_operations=frozenset({"list", "read"}),
            )
            output = self._registry.resolve(
                resource_id=output_resource_id,
                profile_id=profile_id,
                purpose="documents.bundle.output",
                required_kind="directory",
                required_operations=frozenset({"create"}),
            )
            output_path = output.local_path / output_name
            documents = collect_bundle_documents(
                source.local_path,
                output_path=output_path,
                output_format=output_format,
                extractor=self._extractor,
                recursive=recursive,
            )
            plan = plan_document_bundle(
                documents,
                source_root=source.local_path,
                output_path=output_path,
                output_format=output_format,
            )
        except (
            DocumentTransformError,
            ResourceRegistryError,
            TypeError,
            ValueError,
        ) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_plan = _public_document_bundle_plan(
            plan,
            source_resource_id=source.resource_id,
            output_resource_id=output.resource_id,
            output_name=output_name,
        )
        plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "document_bundle_resource.v1",
            domain_plan_id=plan.bundle_id,
            domain_plan_schema=str(public_plan["schema"]),
            domain_plan_sha256=plan_sha256,
            domain_plan=public_plan,
            approval_kind="explicit_resource_bound_output_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, _PreparedDocumentBundle(
            plan=plan,
            documents=documents,
            public_plan=public_plan,
            output_resource_id=output.resource_id,
        )

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedDocumentBundle):
            raise WorkflowExecutionError(
                "Vorbereiteter Dokumentbündelplan besitzt falschen Typ."
            )
        public_sha256 = sha256(_canonical_json(domain_plan.public_plan)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.bundle_id
            or envelope.domain_plan_sha256 != public_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Dokumentbündelplan überein."
            )
        try:
            result = write_document_bundle(
                domain_plan.plan,
                domain_plan.documents,
                allow_output_write=True,
            )
        except (DocumentTransformError, OSError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        public_report = {
            "schema": "folderhome.document-bundle-resource-result.v1",
            "bundle_id": result.bundle_id,
            "provider_id": result.provider_id,
            "output_resource_id": domain_plan.output_resource_id,
            "output_name": domain_plan.plan.output_path.name,
            "output_sha256": result.output_sha256,
            "output_size_bytes": result.output_size_bytes,
            "page_count": result.page_count,
            "source_document_ids": list(result.source_document_ids),
            "status": "executed",
            "paths_disclosed": False,
        }
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": public_report,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "document_bundle_resource.v1",
            domain_report_schema=str(public_report["schema"]),
            domain_report=public_report,
            side_effects=self.descriptor.side_effects,
        )


class FindCallWorkflowAdapter:
    """Run the existing provider-neutral FindCall fixture after exact approval."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="findcall",
        adapter_id="findcall_fixture.v1",
        status="connected",
        plan_schema=FindCallPlan.SCHEMA,
        report_schema="folderhome.findcall-report.v1",
        side_effects=("simulation.findcall.fixture",),
        reason=(
            "Uses the existing strictly local FindCall fixture cascade. It cannot "
            "access a network, place a call, book, order, or make a commitment."
        ),
        request_schema=_FINDCALL_FIXTURE_REQUEST_SCHEMA,
    )

    def __init__(self, *, profile_ids: frozenset[str]) -> None:
        if not profile_ids:
            raise WorkflowExecutionError("FindCall-Adapter benötigt Profile.")
        self._profile_ids = profile_ids

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, _PreparedFindCallFixture]:
        if profile_id not in self._profile_ids:
            raise WorkflowExecutionError("Unbekanntes organisatorisches Profil.")
        prepared = _findcall_fixture_plan(profile_id, request)
        plan_payload = prepared.plan.to_dict()
        plan_sha256 = sha256(_canonical_json(plan_payload)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "findcall_fixture.v1",
            domain_plan_id=prepared.plan.plan_id,
            domain_plan_schema=prepared.plan.SCHEMA,
            domain_plan_sha256=plan_sha256,
            domain_plan=plan_payload,
            approval_kind="explicit_local_fixture_execution",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, prepared

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, _PreparedFindCallFixture):
            raise WorkflowExecutionError("Vorbereiteter FindCall-Plan besitzt falschen Typ.")
        plan_payload = domain_plan.plan.to_dict()
        plan_sha256 = sha256(_canonical_json(plan_payload)).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.plan.plan_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit FindCall-Plan überein."
            )
        provider = SyntheticFindCallProvider(dict(domain_plan.outcomes))
        try:
            domain_report = run_findcall_dry_run(domain_plan.plan, provider=provider)
        except (FindCallWorkflowError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        if provider.network_used or provider.phone_calls_placed or not provider.simulated:
            raise WorkflowExecutionError(
                "FindCall-Fixture hat seine lokale Simulationsgrenze verletzt."
            )
        report_payload = domain_report.to_dict()
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": report_payload,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "findcall_fixture.v1",
            domain_report_schema=domain_report.SCHEMA,
            domain_report=report_payload,
            side_effects=self.descriptor.side_effects,
        )


class PersonalNotesWorkflowAdapter:
    """Connect the master agent to the existing append-only llm-note workflow."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="personal-notes",
        adapter_id="personal_notes.v1",
        status="connected",
        plan_schema="folderhome.personal-note-plan.v1",
        report_schema="folderhome.personal-note-report.v1",
        side_effects=("state.personal_notes.append",),
        reason="Uses the existing hash-bound append-only personal-notes executor.",
        request_schema=_PERSONAL_NOTES_REQUEST_SCHEMA,
    )

    def __init__(
        self,
        *,
        plugin: PluginDescriptor,
        provider_root: Path,
        state_dir: Path,
        profile_ids: frozenset[str],
    ) -> None:
        self._plugin = plugin
        self._provider_root = provider_root.resolve()
        self._state_dir = state_dir.resolve()
        self._profile_ids = profile_ids
        if self._state_dir == self._provider_root or self._state_dir.is_relative_to(
            self._provider_root
        ):
            raise WorkflowExecutionError(
                "Notiz-State darf nicht innerhalb des Provider-Checkouts liegen."
            )
        try:
            self._store()
        except LlmNoteBridgeError as exc:
            raise WorkflowExecutionError(str(exc)) from exc

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, PersonalNotePlan]:
        if profile_id not in self._profile_ids:
            raise WorkflowExecutionError("Unbekanntes organisatorisches Profil.")
        note_request = _personal_note_request(profile_id, request)
        plan = build_personal_note_plan(
            note_request,
            store=self._store(),
            guide=SyntheticPersonalNoteGuide(),
        )
        plan_payload = plan.to_dict()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan": plan_payload,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id="personal-notes",
            adapter_id="personal_notes.v1",
            domain_plan_id=plan.plan_id,
            domain_plan_schema=plan.SCHEMA,
            domain_plan_sha256=plan.plan_sha256,
            domain_plan=plan_payload,
            approval_kind="explicit_local_note_write",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, plan

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, PersonalNotePlan):
            raise WorkflowExecutionError("Vorbereiteter Notizplan besitzt falschen Typ.")
        if (
            envelope.domain_plan_id != domain_plan.plan_id
            or envelope.domain_plan_sha256 != domain_plan.plan_sha256
        ):
            raise WorkflowExecutionError("Ausführungshülle stimmt nicht mit Notizplan überein.")
        approval = PersonalNoteApproval(
            approval_id=f"agent-approval-{secrets.token_hex(12)}",
            plan_id=domain_plan.plan_id,
            plan_sha256=domain_plan.plan_sha256,
            action_id=domain_plan.action_id,
            content_sha256=domain_plan.content_sha256,
            approved_at=approved_at,
            allow_local_note_write=True,
        )
        domain_report = apply_personal_note_plan(
            domain_plan,
            approval,
            store=self._store(),
            allow_state_write=True,
        )
        report_payload = domain_report.to_dict()
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "domain_report": report_payload,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id="personal-notes",
            adapter_id="personal_notes.v1",
            domain_report_schema=domain_report.SCHEMA,
            domain_report=report_payload,
            side_effects=self.descriptor.side_effects,
        )

    def _store(self) -> LlmNoteBridge:
        return LlmNoteBridge(
            plugin=self._plugin,
            provider_root=self._provider_root,
            db_path=self._state_dir / "personal-notes" / "llm-note.db",
        )


class MedicationIntakeWorkflowAdapter:
    """Confirm one existing scheduled dose through the medication state workflow."""

    descriptor = WorkflowAdapterDescriptor(
        workflow_id="medication-intake",
        adapter_id="medication_intake.v1",
        status="connected",
        plan_schema=MedicationIntakeConfirmation.SCHEMA,
        report_schema="folderhome.medication-confirmation-report.v1",
        side_effects=("state.medication_intake.append",),
        reason=(
            "Uses the existing revision-bound medication intake confirmation workflow "
            "against the configured local state."
        ),
        request_schema=_MEDICATION_INTAKE_REQUEST_SCHEMA,
    )

    def __init__(self, *, state_dir: Path, profile_ids: frozenset[str]) -> None:
        self._state_dir = state_dir.resolve()
        self._profile_ids = profile_ids
        if not self._profile_ids:
            raise WorkflowExecutionError(
                "Medikamentenadapter benötigt organisatorische Profile."
            )
        self._store()

    def prepare(
        self,
        *,
        profile_id: str,
        request: dict[str, object],
    ) -> tuple[WorkflowExecutionEnvelope, MedicationIntakeConfirmation]:
        if profile_id not in self._profile_ids:
            raise WorkflowExecutionError("Unbekanntes organisatorisches Profil.")
        try:
            confirmation = _medication_intake_confirmation(
                profile_id,
                request,
                store=self._store(),
            )
        except (MedicationStoreError, MedicationWorkflowError, TypeError, ValueError) as exc:
            raise WorkflowExecutionError(f"Ungültige Einnahmeanfrage: {exc}") from exc
        plan_payload = confirmation.to_dict()
        plan_sha256 = sha256(_canonical_json(plan_payload)).hexdigest()
        material = _canonical_json(
            {
                "adapter_id": self.descriptor.adapter_id,
                "workflow_id": self.descriptor.workflow_id,
                "domain_plan_sha256": plan_sha256,
            }
        )
        envelope = WorkflowExecutionEnvelope(
            envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "medication_intake.v1",
            domain_plan_id=confirmation.confirmation_id,
            domain_plan_schema=confirmation.SCHEMA,
            domain_plan_sha256=plan_sha256,
            domain_plan=plan_payload,
            approval_kind="explicit_medication_intake_confirmation",
            side_effects=self.descriptor.side_effects,
        )
        return envelope, confirmation

    def execute(
        self,
        *,
        envelope: WorkflowExecutionEnvelope,
        domain_plan: object,
        approved_at: str,
    ) -> WorkflowExecutionReport:
        if not isinstance(domain_plan, MedicationIntakeConfirmation):
            raise WorkflowExecutionError(
                "Vorbereitete Einnahmebestätigung besitzt falschen Typ."
            )
        plan_sha256 = sha256(_canonical_json(domain_plan.to_dict())).hexdigest()
        if (
            envelope.domain_plan_id != domain_plan.confirmation_id
            or envelope.domain_plan_sha256 != plan_sha256
        ):
            raise WorkflowExecutionError(
                "Ausführungshülle stimmt nicht mit Einnahmebestätigung überein."
            )
        try:
            domain_report = confirm_medication_intake(
                domain_plan,
                store=self._store(),
                allow_state_write=True,
            )
        except (MedicationStoreError, MedicationWorkflowError, ValueError) as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        if domain_report.status != "executed":
            raise WorkflowExecutionError(
                "Einnahme war bereits bestätigt; es wurde nichts ausgeführt."
            )
        report_payload = domain_report.to_dict()
        report_payload.pop("state_path", None)
        report_payload.update(
            {
                "state_path_disclosed": False,
                "medical_advice": False,
                "automatic_medication_change": False,
            }
        )
        digest = sha256(
            _canonical_json(
                {
                    "envelope_id": envelope.envelope_id,
                    "approved_at": approved_at,
                    "domain_report": report_payload,
                }
            )
        ).hexdigest()
        return WorkflowExecutionReport(
            execution_id=f"workflow_execution_{digest}",
            envelope_id=envelope.envelope_id,
            workflow_id=self.descriptor.workflow_id,
            adapter_id=self.descriptor.adapter_id or "medication_intake.v1",
            domain_report_schema=domain_report.SCHEMA,
            domain_report=report_payload,
            side_effects=self.descriptor.side_effects,
        )

    def _store(self) -> MedicationStore:
        return MedicationStore(self._state_dir)


def _medication_intake_confirmation(
    profile_id: str,
    payload: dict[str, object],
    *,
    store: MedicationStore,
) -> MedicationIntakeConfirmation:
    allowed = {
        "action",
        "scheduled_date",
        "confirmed_at",
        "schedule_id",
        "medication_name",
        "scheduled_time",
    }
    unknown = sorted(set(payload).difference(allowed))
    if unknown:
        raise WorkflowExecutionError(
            "Unbekannte Felder in Einnahmeanfrage: " + ", ".join(unknown)
        )
    required = {"action", "scheduled_date", "confirmed_at"}
    missing = sorted(required.difference(payload))
    if missing:
        raise WorkflowExecutionError("Einnahmeanfrage fehlt Feld: " + missing[0])
    if payload["action"] != "confirm_taken":
        raise WorkflowExecutionError("Einnahmeanfrage unterstützt nur confirm_taken.")
    scheduled_date = _text(payload["scheduled_date"], "scheduled_date")
    target_date = date.fromisoformat(scheduled_date)
    confirmed_at = _text(payload["confirmed_at"], "confirmed_at")
    schedule_id = _optional_text(payload.get("schedule_id"), "schedule_id")
    medication_name = _optional_text(
        payload.get("medication_name"), "medication_name"
    )
    scheduled_time = _optional_text(payload.get("scheduled_time"), "scheduled_time")
    if scheduled_time is not None:
        time.fromisoformat(scheduled_time)

    if schedule_id is not None:
        explicit_schedule = store.get_schedule(schedule_id)
        if explicit_schedule is None:
            raise WorkflowExecutionError("Einnahmeanfrage nennt keinen bekannten Zeitplan.")
        if explicit_schedule.profile_id != profile_id:
            raise WorkflowExecutionError(
                "Einnahmeanfrage verweist auf einen Zeitplan eines anderen Profils."
            )

    candidates = [
        item
        for item in store.current_schedules(
            profile_id=profile_id,
            on_date=scheduled_date,
        )
        if target_date.weekday() in item.weekdays
    ]
    if schedule_id is not None:
        candidates = [item for item in candidates if item.schedule_id == schedule_id]
    if medication_name is not None:
        expected_name = " ".join(medication_name.casefold().split())
        candidates = [
            item
            for item in candidates
            if " ".join(item.medication_name.casefold().split()) == expected_name
        ]
    if scheduled_time is not None:
        candidates = [
            item for item in candidates if item.scheduled_time == scheduled_time
        ]

    pending = []
    for candidate in candidates:
        dose_id = build_medication_dose_id(candidate.schedule_id, scheduled_date)
        if store.find_intake_event(dose_id) is None:
            pending.append((candidate, dose_id))
    if not pending:
        raise WorkflowExecutionError(
            "Keine passende unbestätigte Einnahme ist im konfigurierten State vorhanden."
        )
    if len(pending) > 1:
        choices = ", ".join(
            f"{item.medication_name} {item.scheduled_time} ({item.schedule_id})"
            for item, _dose_id in pending
        )
        raise WorkflowExecutionError(
            "Einnahmeanfrage ist mehrdeutig; ergänze Medikament, Uhrzeit oder "
            f"Zeitplan-ID. Kandidaten: {choices}"
        )
    schedule, dose_id = pending[0]
    revision = store.revision()
    material = _canonical_json(
        {
            "profile_id": profile_id,
            "medication_revision": revision,
            "dose_id": dose_id,
            "schedule_id": schedule.schedule_id,
            "scheduled_date": scheduled_date,
            "confirmed_at": confirmed_at,
        }
    )
    return MedicationIntakeConfirmation(
        confirmation_id=f"agent_medication_{sha256(material).hexdigest()[:32]}",
        medication_revision=revision,
        dose_id=dose_id,
        schedule_id=schedule.schedule_id,
        scheduled_date=scheduled_date,
        confirmed_at=confirmed_at,
    )


def _findcall_fixture_plan(
    profile_id: str,
    payload: dict[str, object],
) -> _PreparedFindCallFixture:
    allowed = {
        "action",
        "planned_at",
        "area",
        "kind",
        "service",
        "location",
        "windows",
        "max_distance_km",
        "max_price_eur",
        "candidates",
    }
    unknown = sorted(set(payload).difference(allowed))
    if unknown:
        raise WorkflowExecutionError(
            "Unbekannte Felder in FindCall-Anfrage: " + ", ".join(unknown)
        )
    missing = sorted(allowed.difference(payload))
    if missing:
        raise WorkflowExecutionError("FindCall-Anfrage fehlt Feld: " + missing[0])
    if payload["action"] != "simulate":
        raise WorkflowExecutionError(
            "FindCall-Chatadapter unterstützt ausschließlich simulate."
        )
    windows = _findcall_windows(payload["windows"], "windows")
    candidates, outcomes = _findcall_candidates(payload["candidates"])
    try:
        request = build_findcall_request(
            profile_id=profile_id,
            area=_text(payload["area"], "area"),
            kind=FindCallKind(_text(payload["kind"], "kind")),
            service=_text(payload["service"], "service"),
            location=_text(payload["location"], "location"),
            windows=windows,
            max_distance_km=_optional_number(
                payload["max_distance_km"], "max_distance_km"
            ),
            max_price_eur=_optional_number(payload["max_price_eur"], "max_price_eur"),
        )
        plan = build_findcall_plan(
            request,
            candidates,
            planned_at=_text(payload["planned_at"], "planned_at"),
        )
    except (FindCallWorkflowError, TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"Ungültige FindCall-Anfrage: {exc}") from exc
    return _PreparedFindCallFixture(plan=plan, outcomes=outcomes)


def _findcall_windows(value: object, label: str) -> tuple[FindCallWindow, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise WorkflowExecutionError(f"{label} benötigt eine Liste mit 1 bis 8 Einträgen.")
    return tuple(
        _findcall_window(item, f"{label}[{index}]") for index, item in enumerate(value)
    )


def _findcall_window(value: object, label: str) -> FindCallWindow:
    if not isinstance(value, dict) or set(value) != {"start_at", "end_at"}:
        raise WorkflowExecutionError(f"{label} besitzt unbekannte oder fehlende Felder.")
    try:
        return FindCallWindow(
            start_at=_text(value["start_at"], f"{label}.start_at"),
            end_at=_text(value["end_at"], f"{label}.end_at"),
        )
    except ValueError as exc:
        raise WorkflowExecutionError(f"Ungültiges FindCall-Zeitfenster: {exc}") from exc


def _findcall_candidates(
    value: object,
) -> tuple[tuple[FindCallCandidate, ...], dict[str, FindCallFixtureOutcome]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 20:
        raise WorkflowExecutionError("candidates benötigt eine Liste mit 1 bis 20 Einträgen.")
    candidates = []
    outcomes: dict[str, FindCallFixtureOutcome] = {}
    expected = {
        "name",
        "phone_e164",
        "services",
        "distance_km",
        "priority",
        "fixture",
    }
    for index, item in enumerate(value):
        label = f"candidates[{index}]"
        if not isinstance(item, dict) or set(item) != expected:
            raise WorkflowExecutionError(
                f"{label} besitzt unbekannte oder fehlende Felder."
            )
        services = _findcall_services(item["services"], f"{label}.services")
        priority = _required_int(item["priority"], f"{label}.priority")
        if not -100 <= priority <= 100:
            raise WorkflowExecutionError(f"{label}.priority liegt außerhalb der Grenze.")
        candidate_material = {
            "name": _text(item["name"], f"{label}.name"),
            "phone_e164": _text(item["phone_e164"], f"{label}.phone_e164"),
            "services": list(services),
            "distance_km": _optional_number(
                item["distance_km"], f"{label}.distance_km"
            ),
            "priority": priority,
        }
        candidate_digest = sha256(_canonical_json(candidate_material)).hexdigest()
        candidate_id = f"findcall_candidate_{candidate_digest}"
        try:
            candidate = FindCallCandidate(
                candidate_id=candidate_id,
                name=str(candidate_material["name"]),
                phone_e164=str(candidate_material["phone_e164"]),
                services=services,
                distance_km=candidate_material["distance_km"],
                priority=priority,
            )
        except (TypeError, ValueError) as exc:
            raise WorkflowExecutionError(f"Ungültiger FindCall-Kandidat: {exc}") from exc
        outcome = _findcall_fixture(item["fixture"], f"{label}.fixture")
        candidates.append(candidate)
        outcomes[candidate_id] = outcome
    return tuple(candidates), outcomes


def _findcall_services(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 20:
        raise WorkflowExecutionError(f"{label} benötigt eine Liste mit 1 bis 20 Einträgen.")
    return tuple(_text(item, f"{label}[{index}]") for index, item in enumerate(value))


def _findcall_fixture(value: object, label: str) -> FindCallFixtureOutcome:
    expected = {
        "status",
        "service_confirmed",
        "available",
        "offered_window",
        "price_known",
        "price_eur",
        "commitment_made",
        "summary",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise WorkflowExecutionError(f"{label} besitzt unbekannte oder fehlende Felder.")
    if value["commitment_made"] is not False:
        raise WorkflowExecutionError(
            f"{label}.commitment_made muss für lokale Simulation false sein."
        )
    offered = value["offered_window"]
    offered_window = None if offered is None else _findcall_window(
        offered, f"{label}.offered_window"
    )
    try:
        return FindCallFixtureOutcome(
            status=FindCallStatus(_text(value["status"], f"{label}.status")),
            service_confirmed=_required_bool(
                value["service_confirmed"], f"{label}.service_confirmed"
            ),
            available=_required_bool(value["available"], f"{label}.available"),
            offered_window=offered_window,
            price_known=_required_bool(
                value["price_known"], f"{label}.price_known"
            ),
            price_eur=_optional_number(value["price_eur"], f"{label}.price_eur"),
            commitment_made=False,
            summary=_text(value["summary"], f"{label}.summary"),
        )
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"Ungültiges FindCall-Fixture: {exc}") from exc


def _unconnected_reason(workflow_id: str) -> str:
    if workflow_id in _LOCAL_ADAPTER_AVAILABLE_WORKFLOWS:
        return (
            "A typed local chat executor adapter exists, but it is not "
            "configured in this application instance."
        )
    if workflow_id in _RESOURCE_ID_REQUIRED_WORKFLOWS:
        return (
            "No typed chat executor adapter is connected yet. This workflow requires "
            "canonical configured logical resource IDs for every input, store, and "
            "output before arbitrary paths can remain unavailable to the model."
        )
    if workflow_id in _EXTERNAL_CONNECTOR_REQUIRED_WORKFLOWS:
        return (
            "No typed chat executor adapter is connected yet. This workflow requires "
            "an explicitly configured external connector plus its workflow-specific "
            "approval and live-effect gate."
        )
    raise WorkflowExecutionError(
        f"Nicht verbundener Workflow besitzt keine geprüfte Lückenklasse: {workflow_id}"
    )


def _personal_note_request(
    profile_id: str,
    payload: dict[str, object],
) -> PersonalNoteRequest:
    allowed = {
        "action",
        "notebook_id",
        "area",
        "title",
        "human_content",
        "note_id",
        "expected_revision",
        "revert_to_revision",
        "references",
    }
    unknown = sorted(set(payload).difference(allowed))
    if unknown:
        raise WorkflowExecutionError(
            "Unbekannte Felder in Notizanfrage: " + ", ".join(unknown)
        )
    required = {"action", "notebook_id", "area", "title"}
    missing = sorted(required.difference(payload))
    if missing:
        raise WorkflowExecutionError("Notizanfrage fehlt Feld: " + missing[0])
    references = _personal_note_references(payload.get("references", []))
    request_material = _canonical_json({"profile_id": profile_id, **payload})
    try:
        return PersonalNoteRequest(
            request_id=f"agent-note-{sha256(request_material).hexdigest()[:32]}",
            action=PersonalNoteAction(str(payload["action"])),
            profile_id=profile_id,
            notebook_id=_text(payload["notebook_id"], "notebook_id"),
            area=_text(payload["area"], "area"),
            title=_text(payload["title"], "title"),
            human_content=_optional_text(payload.get("human_content"), "human_content"),
            note_id=_optional_text(payload.get("note_id"), "note_id"),
            expected_revision=_optional_int(
                payload.get("expected_revision"), "expected_revision"
            ),
            revert_to_revision=_optional_int(
                payload.get("revert_to_revision"), "revert_to_revision"
            ),
            references=references,
        )
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"Ungültige Notizanfrage: {exc}") from exc


def _personal_note_references(value: object) -> tuple[PersonalNoteReference, ...]:
    if not isinstance(value, list):
        raise WorkflowExecutionError("Notizreferenzen müssen eine Liste sein.")
    references = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkflowExecutionError(f"Notizreferenz {index} ist kein Objekt.")
        if set(item) != {"kind", "target_id", "label", "sha256"}:
            raise WorkflowExecutionError(f"Notizreferenz {index} besitzt falsche Felder.")
        try:
            references.append(
                PersonalNoteReference(
                    kind=_text(item["kind"], "kind"),
                    target_id=_text(item["target_id"], "target_id"),
                    label=_text(item["label"], "label"),
                    sha256=_optional_text(item["sha256"], "sha256"),
                )
            )
        except (TypeError, ValueError) as exc:
            raise WorkflowExecutionError(
                f"Ungültige Notizreferenz {index}: {exc}"
            ) from exc
    return tuple(references)


def _publish_private_text_outputs(
    output_root: Path,
    outputs: dict[str, str],
) -> dict[str, str]:
    """Publish an owned text batch with never-overwrite and exact rollback."""

    root = output_root.resolve()
    if output_root.is_symlink() or not root.is_dir():
        raise ValueError("Private Ausgabe benötigt einen bestehenden echten Ordner.")
    if not outputs:
        raise ValueError("Private Ausgabe benötigt mindestens eine Datei.")
    targets: list[tuple[str, Path, str, str]] = []
    for name, content in outputs.items():
        safe_name = _safe_output_name(name)
        if not isinstance(content, str):
            raise ValueError("Private Textausgabe benötigt ausschließlich Textinhalte.")
        target = root / safe_name
        if target.exists() or target.is_symlink():
            raise ValueError(f"Ausgabedatei existiert bereits: {safe_name}")
        digest = sha256(content.encode("utf-8")).hexdigest()
        targets.append((safe_name, target, content, digest))
    created: list[tuple[Path, str]] = []
    try:
        for _name, target, content, digest in targets:
            with target.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            created.append((target, digest))
            if sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Ausgabehash stimmt nicht: {target.name}")
    except BaseException:
        for target, digest in reversed(created):
            if (
                target.is_file()
                and not target.is_symlink()
                and sha256(target.read_bytes()).hexdigest() == digest
            ):
                target.unlink()
        raise
    return {name: digest for name, _target, _content, digest in targets}


def _validate_exact_request(
    request: dict[str, object],
    schema: dict[str, object],
    label: str,
) -> None:
    required_value = schema.get("required")
    if not isinstance(required_value, list):
        raise WorkflowExecutionError(f"{label}: internes Anfrageschema ist ungültig.")
    required = {str(item) for item in required_value}
    unknown = sorted(set(request).difference(required))
    missing = sorted(required.difference(request))
    if unknown:
        raise WorkflowExecutionError(
            f"Unbekannte Felder in {label}: " + ", ".join(unknown)
        )
    if missing:
        raise WorkflowExecutionError(f"{label} fehlt Feld: {missing[0]}")


def _prepare_single_document_action(
    *,
    registry: ResourceRegistry,
    profiles: ProfileConfiguration,
    extractor: BundleDocumentExtractor,
    profile_id: str,
    request: dict[str, object],
    require_source_move: bool,
) -> tuple[DocumentPolicyActionPlan, LogicalResource, LogicalResource]:
    sensitive_read = _required_bool(
        request["allow_sensitive_local_read"],
        "allow_sensitive_local_read",
    )
    if not sensitive_read:
        raise WorkflowExecutionError(
            "Dokumentaktion benötigt die Sensitivitätsfreigabe zum lokalen Lesen."
        )
    source_operations = {"read", "sensitive_read"}
    if require_source_move:
        source_operations.add("move")
    try:
        source = registry.resolve(
            resource_id=_text(request["source_resource_id"], "source_resource_id"),
            profile_id=profile_id,
            purpose="document_action.source",
            required_kind="file",
            required_operations=frozenset(source_operations),
        )
        target = registry.resolve(
            resource_id=_text(request["target_resource_id"], "target_resource_id"),
            profile_id=profile_id,
            purpose="document_action.target",
            required_kind="directory",
            required_operations=frozenset({"create", "move"}),
        )
        _require_distinct_resources((source, target))
        document = extractor.extract(source.local_path)
        policy = resolve_profile_policy(
            profiles,
            profile_id=profile_id,
            area=_text(request["area"], "area"),
        )
        plan = build_document_action_plan(
            document,
            policy,
            target_root=target.local_path,
            as_of=date.fromisoformat(_text(request["as_of"], "as_of")),
        )
    except (
        DocumentActionPlanError,
        DocumentTransformError,
        ProfileConfigurationError,
        ResourceRegistryError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise WorkflowExecutionError(str(exc)) from exc
    return plan, source, target


def _public_document_action_plan(
    plan: DocumentPolicyActionPlan,
    *,
    schema: str,
    source_resource_id: str,
    target_resource_id: str,
    output_resource_id: str | None = None,
    output_name: str | None = None,
    state_resource_id: str | None = None,
) -> dict[str, object]:
    steps = [
        {
            "action_id": step.action_id,
            "sequence": step.sequence,
            "kind": step.kind.value,
            "status": step.status.value,
            "provider_id": step.provider_id,
            "undo_supported": step.undo.supported,
        }
        for step in plan.steps
    ]
    public: dict[str, object] = {
        "schema": schema,
        "plan_id": plan.plan_id,
        "profile_id": plan.profile_id,
        "area": plan.area,
        "as_of": plan.as_of,
        "source_resource_id": source_resource_id,
        "target_resource_id": target_resource_id,
        "step_count": len(plan.steps),
        "executable_action_count": len(executable_action_prefix(plan)),
        "steps": steps,
        "hard_delete_planned": False,
        "content_disclosed": False,
        "paths_disclosed": False,
    }
    if output_resource_id is not None:
        public["output_resource_id"] = output_resource_id
    if output_name is not None:
        public["output_name"] = output_name
    if state_resource_id is not None:
        public["state_resource_id"] = state_resource_id
    return public


def _resource_execution_envelope(
    *,
    descriptor: WorkflowAdapterDescriptor,
    domain_plan_id: str,
    public_plan: dict[str, object],
    approval_kind: str,
) -> WorkflowExecutionEnvelope:
    plan_sha256 = sha256(_canonical_json(public_plan)).hexdigest()
    material = _canonical_json(
        {
            "adapter_id": descriptor.adapter_id,
            "workflow_id": descriptor.workflow_id,
            "domain_plan_sha256": plan_sha256,
        }
    )
    return WorkflowExecutionEnvelope(
        envelope_id=f"workflow_envelope_{sha256(material).hexdigest()}",
        workflow_id=descriptor.workflow_id,
        adapter_id=descriptor.adapter_id or descriptor.workflow_id,
        domain_plan_id=domain_plan_id,
        domain_plan_schema=str(public_plan["schema"]),
        domain_plan_sha256=plan_sha256,
        domain_plan=public_plan,
        approval_kind=approval_kind,
        side_effects=descriptor.side_effects,
    )


def _verify_resource_envelope(
    envelope: WorkflowExecutionEnvelope,
    domain_plan_id: str,
    public_plan: dict[str, object],
) -> None:
    if (
        envelope.domain_plan_id != domain_plan_id
        or envelope.domain_plan_sha256
        != sha256(_canonical_json(public_plan)).hexdigest()
    ):
        raise WorkflowExecutionError(
            "Ausführungshülle stimmt nicht mit dem Ressourcenplan überein."
        )


def _resource_execution_report(
    *,
    envelope: WorkflowExecutionEnvelope,
    descriptor: WorkflowAdapterDescriptor,
    approved_at: str,
    public_report: dict[str, object],
) -> WorkflowExecutionReport:
    digest = sha256(
        _canonical_json(
            {
                "envelope_id": envelope.envelope_id,
                "approved_at": approved_at,
                "domain_report": public_report,
            }
        )
    ).hexdigest()
    return WorkflowExecutionReport(
        execution_id=f"workflow_execution_{digest}",
        envelope_id=envelope.envelope_id,
        workflow_id=descriptor.workflow_id,
        adapter_id=descriptor.adapter_id or descriptor.workflow_id,
        domain_report_schema=str(public_report["schema"]),
        domain_report=public_report,
        side_effects=descriptor.side_effects,
    )


def _verify_planned_document_unchanged(plan: DocumentPolicyActionPlan) -> None:
    source = plan.document.source_path.resolve()
    if source.is_symlink() or not source.is_file():
        raise WorkflowExecutionError(
            "Plandokument fehlt, ist kein reguläres Dokument oder ist ein Link."
        )
    if sha256(source.read_bytes()).hexdigest() != plan.document.source_sha256:
        raise WorkflowExecutionError(
            "Quellhash hat sich seit der Dokumentaktionsplanung geändert."
        )


def _folder_cleanup_item_approvals(
    plan: FolderCleanupPlan,
) -> tuple[BatchItemApproval, ...]:
    return tuple(
        BatchItemApproval(
            document_id=item.document_id or "",
            plan_id=item.action_plan.plan_id if item.action_plan is not None else "",
            document_sha256=item.source_sha256,
            action_ids=item.executable_action_ids,
        )
        for item in plan.items
        if item.status == "planned"
        and item.action_plan is not None
        and item.executable_action_ids
    )


def _routine_queue_configuration(
    *,
    registry: ResourceRegistry,
    profile_id: str,
    value: object,
) -> tuple[
    WatchedFolderConfiguration,
    FolderRoutineBindingConfiguration,
    tuple[LogicalResource, ...],
]:
    if not isinstance(value, list) or not value or len(value) > 32:
        raise WorkflowExecutionError(
            "Routinenqueue benötigt eine Liste mit 1 bis 32 Einträgen."
        )
    expected = {
        "watch_id",
        "binding_id",
        "source_resource_id",
        "target_resource_id",
        "area",
        "interval_minutes",
        "recursive",
        "mode",
        "enabled",
    }
    watches = []
    bindings = []
    resources = []
    watch_ids = set()
    binding_ids = set()
    for index, raw in enumerate(value):
        item = _strict_request_object(raw, f"items[{index}]", expected)
        watch_id = _text(item["watch_id"], f"items[{index}].watch_id")
        binding_id = _text(item["binding_id"], f"items[{index}].binding_id")
        if watch_id in watch_ids or binding_id in binding_ids:
            raise WorkflowExecutionError(
                "watch_id und binding_id müssen in der Routinenqueue eindeutig sein."
            )
        watch_ids.add(watch_id)
        binding_ids.add(binding_id)
        source = registry.resolve(
            resource_id=_text(
                item["source_resource_id"],
                f"items[{index}].source_resource_id",
            ),
            profile_id=profile_id,
            purpose="routine_queue.source",
            required_kind="directory",
            required_operations=frozenset({"list", "read", "sensitive_read"}),
        )
        target = registry.resolve(
            resource_id=_text(
                item["target_resource_id"],
                f"items[{index}].target_resource_id",
            ),
            profile_id=profile_id,
            purpose="routine_queue.target",
            required_kind="directory",
            required_operations=frozenset({"create", "move"}),
        )
        enabled = _required_bool(item["enabled"], f"items[{index}].enabled")
        mode = FolderRoutineMode(_text(item["mode"], f"items[{index}].mode"))
        watches.append(
            WatchedFolder(
                watch_id=watch_id,
                source_root=source.local_path,
                profile_id=profile_id,
                area=_text(item["area"], f"items[{index}].area"),
                interval_minutes=_required_int(
                    item["interval_minutes"],
                    f"items[{index}].interval_minutes",
                ),
                recursive=_required_bool(
                    item["recursive"],
                    f"items[{index}].recursive",
                ),
                enabled=enabled,
            )
        )
        bindings.append(
            FolderRoutineBinding(
                binding_id=binding_id,
                watch_id=watch_id,
                target_root=target.local_path,
                mode=mode,
                enabled=enabled,
            )
        )
        resources.extend((source, target))
    return (
        WatchedFolderConfiguration(watches=tuple(watches)),
        FolderRoutineBindingConfiguration(bindings=tuple(bindings)),
        tuple(resources),
    )


def _require_distinct_resources(resources: tuple[LogicalResource, ...]) -> None:
    paths = tuple(resource.local_path.resolve() for resource in resources)
    for index, first in enumerate(paths):
        for second in paths[index + 1 :]:
            if (
                first == second
                or first.is_relative_to(second)
                or second.is_relative_to(first)
            ):
                raise WorkflowExecutionError(
                    "Dokumentaktionsressourcen dürfen sich nicht überlappen."
                )


def _safe_output_name(value: object) -> str:
    name = _text(value, "output_name")
    candidate = Path(name)
    if (
        candidate.is_absolute()
        or candidate.name != name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
    ):
        raise WorkflowExecutionError(
            "output_name muss ein einzelner Dateiname ohne Pfadanteile sein."
        )
    return name


def _safe_output_basename(value: object) -> str:
    name = _safe_output_name(value)
    if Path(name).suffix:
        raise WorkflowExecutionError(
            "output_basename darf keine Dateiendung enthalten."
        )
    return name


def _public_document_bundle_plan(
    plan: DocumentBundlePlan,
    *,
    source_resource_id: str,
    output_resource_id: str,
    output_name: str,
) -> dict[str, object]:
    sources = []
    for source in plan.sources:
        payload = source.to_dict()
        payload.pop("source_path", None)
        payload["source_path_disclosed"] = False
        sources.append(payload)
    return {
        "schema": "folderhome.document-bundle-resource-plan.v1",
        "bundle_id": plan.bundle_id,
        "provider_id": plan.provider_id,
        "source_resource_id": source_resource_id,
        "output_resource_id": output_resource_id,
        "output_name": output_name,
        "output_format": plan.output_format.value,
        "sources": sources,
        "gate": plan.gate.to_dict(),
        "undo": plan.undo.to_dict(),
        "paths_disclosed": False,
    }


def _public_contact_register_plan(
    plan: ContactRegisterPlan,
    *,
    source_resource_id: str,
    state_resource_id: str,
) -> dict[str, object]:
    payload = _redact_physical_paths(plan.to_dict())
    payload.update(
        {
            "schema": "folderhome.contact-register-resource-plan.v1",
            "source_resource_id": source_resource_id,
            "state_resource_id": state_resource_id,
            "planned_action_count": sum(
                item.status == "planned" for item in plan.actions
            ),
            "paths_disclosed": False,
        }
    )
    return payload


def _public_finance_import_plan(
    plan: FinanceImportPlan,
    *,
    source_resource_id: str,
    state_resource_id: str,
) -> dict[str, object]:
    status_counts = {"planned": 0, "noop": 0, "blocked": 0}
    transaction_count = 0
    for action in plan.actions:
        status_counts[action.status] += 1
        transaction_count += len(action.statement.transactions)
    return {
        "schema": "folderhome.finance-import-resource-plan.v1",
        "plan_id": plan.plan_id,
        "finance_revision": plan.finance_revision,
        "profile_id": plan.analysis.profile_id,
        "source_resource_id": source_resource_id,
        "state_resource_id": state_resource_id,
        "source_count": len(plan.analysis.items),
        "statement_candidate_count": len(plan.analysis.statements),
        "transaction_candidate_count": transaction_count,
        "planned_action_count": status_counts["planned"],
        "noop_action_count": status_counts["noop"],
        "blocked_action_count": status_counts["blocked"],
        "automatic_bank_access": False,
        "financial_advice": False,
        "content_disclosed": False,
        "paths_disclosed": False,
    }


def _public_inventory_import_plan(
    plan: InventoryImportPlan,
    *,
    source_resource_id: str,
    state_resource_id: str,
) -> dict[str, object]:
    status_counts = {"planned": 0, "noop": 0, "blocked": 0}
    for action in plan.actions:
        status_counts[action.status] += 1
    return {
        "schema": "folderhome.inventory-import-resource-plan.v1",
        "plan_id": plan.plan_id,
        "inventory_revision": plan.inventory_revision,
        "profile_id": plan.analysis.profile_id,
        "source_resource_id": source_resource_id,
        "state_resource_id": state_resource_id,
        "source_count": len(plan.analysis.items),
        "observation_candidate_count": len(plan.analysis.observations),
        "planned_action_count": status_counts["planned"],
        "noop_action_count": status_counts["noop"],
        "blocked_action_count": status_counts["blocked"],
        "automatic_purchase": False,
        "content_disclosed": False,
        "paths_disclosed": False,
    }


def _public_daily_briefing_plan(
    plan: DailyBriefingPlan,
    *,
    weather_resource_id: str,
    news_resource_id: str,
    output_resource_id: str,
    desktop_resource_id: str,
    output_name: str,
    desktop_name: str,
) -> dict[str, object]:
    return {
        "schema": "folderhome.daily-briefing-resource-plan.v1",
        "plan_id": plan.plan_id,
        "plan_sha256": plan.plan_sha256,
        "profile_id": plan.request.profile_id,
        "briefing_date": plan.request.briefing_date,
        "weather_resource_id": weather_resource_id,
        "news_resource_id": news_resource_id,
        "output_resource_id": output_resource_id,
        "desktop_resource_id": desktop_resource_id,
        "output_name": output_name,
        "desktop_name": desktop_name,
        "status": plan.status,
        "article_count": len(plan.articles),
        "omitted_article_count": plan.omitted_article_count,
        "weather_freshness": plan.weather_freshness,
        "news_freshness": plan.news_freshness,
        "warning_count": len(plan.warnings),
        "html_sha256": plan.html_sha256,
        "network_invoked": False,
        "scheduler_registered": False,
        "content_disclosed": False,
        "paths_disclosed": False,
    }


def _public_benefit_routing_results(
    report: BenefitScreeningReport,
) -> list[dict[str, object]]:
    return [
        {
            "program_id": item.program_id,
            "name": item.name,
            "provider": item.provider,
            "status": item.status,
            "official_info_url": item.official_info_url,
            "official_precheck_url": item.official_precheck_url,
            "missing_fact_count": len(item.missing_fact_keys),
            "eligibility_assessed": False,
        }
        for item in report.results
    ]


def _redact_physical_paths(value: object) -> object:
    blocked_keys = {
        "config_path",
        "output_path",
        "register_path",
        "source_path",
        "source_root",
        "state_path",
        "target_path",
        "uptoday_ics_directory",
    }
    if isinstance(value, dict):
        return {
            key: _redact_physical_paths(item)
            for key, item in value.items()
            if key not in blocked_keys
        }
    if isinstance(value, list):
        return [_redact_physical_paths(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_physical_paths(item) for item in value]
    return value


def _require_separate_resources(first: Path, second: Path) -> None:
    first = first.resolve()
    second = second.resolve()
    if (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    ):
        raise WorkflowExecutionError(
            "Quell- und State-Ressource dürfen sich nicht überlappen."
        )


def _strict_request_object(
    value: object,
    label: str,
    expected_fields: set[str],
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise WorkflowExecutionError(
            f"{label} besitzt unbekannte oder fehlende Felder."
        )
    return value


def _strict_text_list(
    value: object,
    label: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise WorkflowExecutionError(f"{label} benötigt eine gültige Textliste.")
    result = tuple(item.strip() for item in value)
    if len(result) != len(set(result)):
        raise WorkflowExecutionError(f"{label} muss eindeutige Werte enthalten.")
    return result


def _load_strict_json_file(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowExecutionError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkflowExecutionError(f"{label} muss ein JSON-Objekt sein.")
    return payload


def _resolve_config_path(value: str, config_root: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (config_root / candidate).resolve()


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowExecutionError(f"{label} benötigt Text.")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkflowExecutionError(f"{label} benötigt eine Ganzzahl.")
    return value


def _required_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkflowExecutionError(f"{label} benötigt eine Ganzzahl.")
    return value


def _required_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkflowExecutionError(f"{label} benötigt einen Wahrheitswert.")
    return value


def _optional_number(value: object, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkflowExecutionError(f"{label} benötigt eine Zahl oder null.")
    number = float(value)
    if number < 0:
        raise WorkflowExecutionError(f"{label} darf nicht negativ sein.")
    return number


def _canonical_json(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"Workflowdaten sind nicht JSON-kompatibel: {exc}") from exc


__all__ = [
    "AdministrativeDraftWorkflowAdapter",
    "ArtifactStudioWorkflowAdapter",
    "BenefitScreeningWorkflowAdapter",
    "ContactRegisterWorkflowAdapter",
    "CorrespondenceWorkflowAdapter",
    "ContractCockpitWorkflowAdapter",
    "DailyBriefingWorkflowAdapter",
    "DirectoryObservationWorkflowAdapter",
    "DocumentActionExecutionWorkflowAdapter",
    "DocumentActionPlanWorkflowAdapter",
    "DocumentBundleWorkflowAdapter",
    "DocumentPackageWorkflowAdapter",
    "FindCallWorkflowAdapter",
    "FinanceImportWorkflowAdapter",
    "FcsaDryRunWorkflowAdapter",
    "HealthDossierWorkflowAdapter",
    "FolderCleanupWorkflowAdapter",
    "FolderRoutineWorkflowAdapter",
    "InventoryImportWorkflowAdapter",
    "LegalChangeMonitorWorkflowAdapter",
    "LocalCalendarWorkflowAdapter",
    "MailDraftWorkflowAdapter",
    "MedicationIntakeWorkflowAdapter",
    "OfficialNoticeWorkflowAdapter",
    "PersonalNotesWorkflowAdapter",
    "RoutineQueueWorkflowAdapter",
    "TaxWorkpaperWorkflowAdapter",
    "WorkflowExecutionError",
    "WorkflowExecutionGateway",
]
