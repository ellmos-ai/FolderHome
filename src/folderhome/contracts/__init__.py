"""Shared FolderHome contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from folderhome.contracts.documents import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)
from folderhome.contracts.profiles import (
    ProfileRule,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    RuleScope,
    UserProfile,
)
from folderhome.contracts.resources import (
    LogicalResource,
    ResourceRegistry,
    ResourceRegistryError,
)
from folderhome.contracts.versions import (
    ArchiveProposal,
    DocumentFamily,
    DocumentVersion,
    DocumentVersionComparison,
    VersionDateBasis,
    VersionDateConfidence,
)

__all__ = [
    "ARTIFACT_KINDS",
    "ActionExecutionApproval",
    "ActionExecutionReport",
    "ActionRuleProvenance",
    "ActionUndoApproval",
    "ActionUndoReport",
    "ActionEvent",
    "AdministrativeDraftApproval",
    "AdministrativeDraftFact",
    "AdministrativeDraftKind",
    "AdministrativeDraftOutputReport",
    "AdministrativeDraftPlan",
    "AdministrativeDraftRequest",
    "ArchiveProposal",
    "ArtifactRoute",
    "ArtifactStudioPlan",
    "ArtifactStudioRequest",
    "BatchItemApproval",
    "BenefitCatalog",
    "BenefitCriterionEvaluation",
    "BenefitProfileFact",
    "BenefitProfileSnapshot",
    "BenefitProgram",
    "BenefitRoutingCriterion",
    "BenefitScreeningOutputReport",
    "BenefitScreeningReport",
    "BenefitScreeningResult",
    "BenefitSource",
    "BundleFormat",
    "BundleSource",
    "BusinessCardContent",
    "BriefingDeliveryApproval",
    "BriefingDeliveryReport",
    "BriefingRenderApproval",
    "BriefingRenderReport",
    "CalendarBackend",
    "CalendarCandidate",
    "CalendarConfiguration",
    "CalendarConnectorAccount",
    "CalendarConnectorAction",
    "CalendarConnectorApproval",
    "CalendarConnectorEvent",
    "CalendarConnectorExecutionReport",
    "CalendarConnectorOperation",
    "CalendarConnectorPlan",
    "CalendarConnectorRequest",
    "CalendarConnectorRoute",
    "CalendarEventRecord",
    "CalendarEvidence",
    "CalendarExecutionItem",
    "CalendarExecutionReport",
    "CalendarHandoffAction",
    "CalendarHandoffApproval",
    "CalendarHandoffPlan",
    "CalendarProviderEventReference",
    "CalendarReminderSpec",
    "CapabilityDescriptor",
    "CleanupConflict",
    "ContactActionKind",
    "ContactCandidate",
    "ContactEvidence",
    "ContactRecord",
    "ContactRegisterAction",
    "ContactRegisterApproval",
    "ContactRegisterPlan",
    "ContactRegisterReport",
    "CoordinatorRole",
    "ContractCockpitIssue",
    "ContractCockpitReport",
    "ContractCockpitRequest",
    "CorrespondenceConfiguration",
    "CorrespondenceOutputReport",
    "CorrespondenceParty",
    "CorrespondencePreview",
    "CorrespondenceRenderHandoff",
    "CorrespondenceRequest",
    "ContentFormat",
    "DecisionCard",
    "DecisionStatus",
    "DailyBriefingPlan",
    "DailyBriefingRequest",
    "DesignColors",
    "DesignFonts",
    "DesignOutputReport",
    "DesignPreview",
    "DesignStudioRequest",
    "DirectoryChange",
    "DirectoryChangeKind",
    "DirectoryDiff",
    "DirectoryFileState",
    "DirectoryLearningExample",
    "DirectoryScanReport",
    "DirectorySnapshot",
    "DocumentRecord",
    "DocumentCalendarAnalysis",
    "DocumentContactAnalysis",
    "DocumentBundlePlan",
    "DocumentBundleResult",
    "DocumentPolicyActionPlan",
    "DocumentPackageEntryResult",
    "DocumentPackageGroup",
    "DocumentPackagePlan",
    "DocumentPackageResult",
    "DocumentFamily",
    "DocumentVersion",
    "DocumentVersionComparison",
    "EvidenceRef",
    "ExpertRole",
    "ExecutedActionStep",
    "FolderCleanupApproval",
    "FolderCleanupExecutionReport",
    "FolderCleanupItem",
    "FolderCleanupPlan",
    "FolderCalendarAnalysis",
    "FolderCalendarItem",
    "FindCallAction",
    "FindCallAttempt",
    "FindCallCandidate",
    "FindCallFixtureOutcome",
    "FindCallKind",
    "FindCallPlan",
    "FindCallReport",
    "FindCallRequest",
    "FindCallStatus",
    "FindCallWindow",
    "CallPluginProbeResult",
    "FolderContactAnalysis",
    "FolderContactItem",
    "FolderRoutineExecutionReport",
    "FolderRoutineBinding",
    "FolderRoutineMode",
    "FolderRoutinePlan",
    "FolderRoutineQueue",
    "FolderRoutineQueueItem",
    "AccountStatementCandidate",
    "DateRange",
    "FinanceCoverage",
    "FinanceEvidence",
    "FinanceImportAction",
    "FinanceImportApproval",
    "FinanceImportPlan",
    "FinanceImportReport",
    "FinancePeriodReport",
    "FinanceStatementRecord",
    "FinanceTransactionCandidate",
    "FinanceTransactionRecord",
    "FolderStatementAnalysis",
    "FolderInventoryAnalysis",
    "InventoryAnalysisItem",
    "InventoryEventRecord",
    "InventoryEvidence",
    "InventoryImportAction",
    "InventoryImportApproval",
    "InventoryImportPlan",
    "InventoryImportReport",
    "InventoryNeedCandidate",
    "InventoryNeedsReport",
    "InventoryObservationCandidate",
    "LetterDesign",
    "LetterTemplate",
    "LegalChangeMonitorReport",
    "LegalChangeOutputReport",
    "LegalInterest",
    "LegalInterestSnapshot",
    "LegalProvisionChange",
    "LegalProvisionSnapshot",
    "LegalReviewCandidate",
    "LegalSourceSnapshot",
    "LocalApiResponse",
    "LocalAppSettings",
    "OperatingSystemIdentity",
    "DesignBindings",
    "FolderMedicationPlanAnalysis",
    "HealthConflictCandidate",
    "HealthCoverage",
    "HealthDossierReport",
    "HealthEvidence",
    "HealthMissingPeriod",
    "HealthReportHandoff",
    "HealthSource",
    "HealthTimelineEntry",
    "MedicationConfirmationReport",
    "MedicationDayReport",
    "MedicationDoseView",
    "MedicationEvidence",
    "MedicationImportAction",
    "MedicationImportApproval",
    "MedicationImportPlan",
    "MedicationImportReport",
    "MedicationIntakeConfirmation",
    "MedicationIntakeEventRecord",
    "MedicationPlanAnalysisItem",
    "MedicationScheduleCandidate",
    "MedicationScheduleRecord",
    "MailAccountConfiguration",
    "MailAttachmentReference",
    "MailDraftPreview",
    "MailDraftRequest",
    "MailFolderReference",
    "MailInboundConfiguration",
    "MailIngestApproval",
    "MailIngestPlan",
    "MailIngestReport",
    "MailIngestRequest",
    "MailMessageReference",
    "MailOutboundConfiguration",
    "MailSendApproval",
    "MailSendReport",
    "MasterAgentPlan",
    "MasterCapability",
    "MasterConfirmationReceipt",
    "MasterPlanApproval",
    "MasterPlanStep",
    "NewsArticle",
    "NewsSnapshot",
    "NoticeConflict",
    "NoticeEvidence",
    "OfficialNoticeAnalysis",
    "OfficialNoticeOutputReport",
    "PersonalNoteAction",
    "PersonalNoteApproval",
    "PersonalNoteExecutionReport",
    "PersonalNoteGuidance",
    "PersonalNotePlan",
    "PersonalNoteReference",
    "PersonalNoteRequest",
    "PersonalNoteVersion",
    "RecurringCostCandidate",
    "RecurringCostReport",
    "StatementAnalysisItem",
    "TaxExportApproval",
    "TaxExportPlan",
    "TaxExportReport",
    "TaxReceiptApproval",
    "TaxReceiptPlan",
    "TaxReceiptReport",
    "TaxReceiptRequest",
    "GateDecision",
    "IndexStatus",
    "LogicalResource",
    "PluginDescriptor",
    "PlacementReceipt",
    "PolicyActionKind",
    "PolicyActionStatus",
    "PolicyActionStep",
    "PrivacyStatus",
    "ProfileRule",
    "ProviderProvenance",
    "RoutingPersona",
    "SemanticRouteReceipt",
    "RunReport",
    "RunStatus",
    "SchedulerHandoffPlan",
    "SchedulerRunReport",
    "ResolvedProfilePolicy",
    "ResolvedProfileRule",
    "ResourceRegistry",
    "ResourceRegistryError",
    "RuleKey",
    "RuleScope",
    "SideEffect",
    "TransformTreatment",
    "UnsupportedPackageSource",
    "UndoDescriptor",
    "WatchedFolder",
    "WeatherSnapshot",
    "VersionDateBasis",
    "VersionDateConfidence",
    "WorkflowAdapterDescriptor",
    "WorkflowExecutionEnvelope",
    "WorkflowExecutionReport",
    "UserProfile",
    "build_document_id",
    "build_inventory_item_id",
]


class RunStatus(StrEnum):
    """Lifecycle state shared by runs and actions."""

    PLANNED = "planned"
    EXECUTED = "executed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNDONE = "undone"


class SideEffect(StrEnum):
    """Side effects that require explicit declaration and policy checks."""

    FILESYSTEM_WRITE = "filesystem.write"
    NETWORK_REQUEST = "network.request"
    PHONE_CALL = "phone.call"
    EMAIL_SEND = "email.send"
    CALENDAR_WRITE = "calendar.write"


class DecisionStatus(StrEnum):
    """Human decision state, intentionally separate from run status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    """One capability exposed by a plugin."""

    capability_id: str
    title: str
    side_effects: tuple[SideEffect, ...] = ()
    dry_run_supported: bool = False
    gate_required: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.capability_id,
            "title": self.title,
            "side_effects": [effect.value for effect in self.side_effects],
            "dry_run_supported": self.dry_run_supported,
            "gate_required": self.gate_required,
        }


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """Validated plugin identity, provenance, and capability contract."""

    plugin_id: str
    name: str
    version: str
    source_repository: str
    source_revision: str
    license_id: str
    interface_version: str
    capabilities: tuple[CapabilityDescriptor, ...] = ()
    classification: str = "NEW_CORE"
    default_mode: str = "dry-run"
    live_enabled: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "source": {
                "repository": self.source_repository,
                "revision": self.source_revision,
            },
            "license": self.license_id,
            "interface_version": self.interface_version,
            "capabilities": [capability.to_dict() for capability in self.capabilities],
        }


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Reference to evidence without embedding potentially sensitive content."""

    kind: str
    uri: str
    sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "uri": self.uri, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Result of the permission gate for one action."""

    required: bool
    granted: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "granted": self.granted,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class UndoDescriptor:
    """Declares whether and how an action can be reversed."""

    supported: bool
    action: str | None

    def to_dict(self) -> dict[str, object]:
        return {"supported": self.supported, "action": self.action}


@dataclass(frozen=True, slots=True)
class ProviderProvenance:
    """Pinned provider identity for an audited run."""

    plugin_id: str
    version: str
    source_repository: str
    source_revision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "version": self.version,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
        }


@dataclass(frozen=True, slots=True)
class DecisionCard:
    """A human-facing choice required before a gated action."""

    decision_id: str
    title: str
    question: str
    status: DecisionStatus
    options: tuple[str, ...]
    selected: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "question": self.question,
            "status": self.status.value,
            "options": list(self.options),
            "selected": self.selected,
        }


@dataclass(frozen=True, slots=True)
class ActionEvent:
    """Auditable record of one planned or completed action."""

    action_id: str
    sequence: int
    name: str
    status: RunStatus
    side_effects: tuple[SideEffect, ...]
    gate: GateDecision
    evidence: tuple[EvidenceRef, ...]
    undo: UndoDescriptor
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "sequence": self.sequence,
            "name": self.name,
            "status": self.status.value,
            "side_effects": [effect.value for effect in self.side_effects],
            "gate": self.gate.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "undo": self.undo.to_dict(),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class RunReport:
    """Versioned report for a single FolderHome run."""

    run_id: str
    started_at: str
    finished_at: str
    status: RunStatus
    plugin_id: str
    capability_id: str
    dry_run: bool
    provider: ProviderProvenance
    actions: tuple[ActionEvent, ...]
    decisions: tuple[DecisionCard, ...]

    SCHEMA = "ellmos.home-agent.run-report.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status.value,
            "plugin_id": self.plugin_id,
            "capability_id": self.capability_id,
            "dry_run": self.dry_run,
            "provider": self.provider.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


# Imported after the shared gate/undo contracts to avoid a package-init cycle.
from folderhome.contracts.action_execution import (  # noqa: E402
    ActionExecutionApproval,
    ActionExecutionReport,
    ActionUndoApproval,
    ActionUndoReport,
    ExecutedActionStep,
)
from folderhome.contracts.action_plans import (  # noqa: E402
    ActionRuleProvenance,
    DocumentPolicyActionPlan,
    PolicyActionKind,
    PolicyActionStatus,
    PolicyActionStep,
)
from folderhome.contracts.administrative_drafts import (  # noqa: E402
    AdministrativeDraftApproval,
    AdministrativeDraftFact,
    AdministrativeDraftKind,
    AdministrativeDraftOutputReport,
    AdministrativeDraftPlan,
    AdministrativeDraftRequest,
)
from folderhome.contracts.artifact_studio import (  # noqa: E402
    ARTIFACT_KINDS,
    ArtifactRoute,
    ArtifactStudioPlan,
    ArtifactStudioRequest,
    BusinessCardContent,
    DesignColors,
    DesignFonts,
    DesignOutputReport,
    DesignPreview,
    DesignStudioRequest,
)
from folderhome.contracts.benefit_screening import (  # noqa: E402
    BenefitCatalog,
    BenefitCriterionEvaluation,
    BenefitProfileFact,
    BenefitProfileSnapshot,
    BenefitProgram,
    BenefitRoutingCriterion,
    BenefitScreeningOutputReport,
    BenefitScreeningReport,
    BenefitScreeningResult,
    BenefitSource,
)
from folderhome.contracts.calendar import (  # noqa: E402
    CalendarBackend,
    CalendarCandidate,
    CalendarConfiguration,
    CalendarEventRecord,
    CalendarEvidence,
    CalendarExecutionItem,
    CalendarExecutionReport,
    CalendarHandoffAction,
    CalendarHandoffApproval,
    CalendarHandoffPlan,
    DocumentCalendarAnalysis,
    FolderCalendarAnalysis,
    FolderCalendarItem,
)
from folderhome.contracts.calendar_connectors import (  # noqa: E402
    CalendarConnectorAccount,
    CalendarConnectorAction,
    CalendarConnectorApproval,
    CalendarConnectorEvent,
    CalendarConnectorExecutionReport,
    CalendarConnectorOperation,
    CalendarConnectorPlan,
    CalendarConnectorRequest,
    CalendarConnectorRoute,
    CalendarProviderEventReference,
    CalendarReminderSpec,
)
from folderhome.contracts.cleanup import (  # noqa: E402
    BatchItemApproval,
    CleanupConflict,
    FolderCleanupApproval,
    FolderCleanupExecutionReport,
    FolderCleanupItem,
    FolderCleanupPlan,
)
from folderhome.contracts.contacts import (  # noqa: E402
    ContactActionKind,
    ContactCandidate,
    ContactEvidence,
    ContactRecord,
    ContactRegisterAction,
    ContactRegisterApproval,
    ContactRegisterPlan,
    ContactRegisterReport,
    DocumentContactAnalysis,
    FolderContactAnalysis,
    FolderContactItem,
)
from folderhome.contracts.contract_cockpit import (  # noqa: E402
    ContractCockpitIssue,
    ContractCockpitReport,
    ContractCockpitRequest,
)
from folderhome.contracts.correspondence import (  # noqa: E402
    CorrespondenceConfiguration,
    CorrespondenceOutputReport,
    CorrespondenceParty,
    CorrespondencePreview,
    CorrespondenceRenderHandoff,
    CorrespondenceRequest,
    DesignBindings,
    LetterDesign,
    LetterTemplate,
)
from folderhome.contracts.daily_briefing import (  # noqa: E402
    BriefingDeliveryApproval,
    BriefingDeliveryReport,
    BriefingRenderApproval,
    BriefingRenderReport,
    DailyBriefingPlan,
    DailyBriefingRequest,
    NewsArticle,
    NewsSnapshot,
    WeatherSnapshot,
)
from folderhome.contracts.finance import (  # noqa: E402
    AccountStatementCandidate,
    DateRange,
    FinanceCoverage,
    FinanceEvidence,
    FinanceImportAction,
    FinanceImportApproval,
    FinanceImportPlan,
    FinanceImportReport,
    FinancePeriodReport,
    FinanceStatementRecord,
    FinanceTransactionCandidate,
    FinanceTransactionRecord,
    FolderStatementAnalysis,
    RecurringCostCandidate,
    RecurringCostReport,
    StatementAnalysisItem,
)
from folderhome.contracts.findcall import (  # noqa: E402
    CallPluginProbeResult,
    FindCallAction,
    FindCallAttempt,
    FindCallCandidate,
    FindCallFixtureOutcome,
    FindCallKind,
    FindCallPlan,
    FindCallReport,
    FindCallRequest,
    FindCallStatus,
    FindCallWindow,
)
from folderhome.contracts.health import (  # noqa: E402
    HealthConflictCandidate,
    HealthCoverage,
    HealthDossierReport,
    HealthEvidence,
    HealthMissingPeriod,
    HealthReportHandoff,
    HealthSource,
    HealthTimelineEntry,
)
from folderhome.contracts.inventory import (  # noqa: E402
    FolderInventoryAnalysis,
    InventoryAnalysisItem,
    InventoryEventRecord,
    InventoryEvidence,
    InventoryImportAction,
    InventoryImportApproval,
    InventoryImportPlan,
    InventoryImportReport,
    InventoryNeedCandidate,
    InventoryNeedsReport,
    InventoryObservationCandidate,
    build_inventory_item_id,
)
from folderhome.contracts.legal_change_monitor import (  # noqa: E402
    LegalChangeMonitorReport,
    LegalChangeOutputReport,
    LegalInterest,
    LegalInterestSnapshot,
    LegalProvisionChange,
    LegalProvisionSnapshot,
    LegalReviewCandidate,
    LegalSourceSnapshot,
)
from folderhome.contracts.local_app import (  # noqa: E402
    LocalApiResponse,
    LocalAppSettings,
    OperatingSystemIdentity,
)
from folderhome.contracts.mail import (  # noqa: E402
    MailAccountConfiguration,
    MailAttachmentReference,
    MailDraftPreview,
    MailDraftRequest,
    MailFolderReference,
    MailInboundConfiguration,
    MailIngestApproval,
    MailIngestPlan,
    MailIngestReport,
    MailIngestRequest,
    MailMessageReference,
    MailOutboundConfiguration,
    MailSendApproval,
    MailSendReport,
)
from folderhome.contracts.master_agent import (  # noqa: E402
    CoordinatorRole,
    ExpertRole,
    MasterAgentPlan,
    MasterCapability,
    MasterConfirmationReceipt,
    MasterPlanApproval,
    MasterPlanStep,
    RoutingPersona,
    SemanticRouteReceipt,
)
from folderhome.contracts.medication import (  # noqa: E402
    FolderMedicationPlanAnalysis,
    MedicationConfirmationReport,
    MedicationDayReport,
    MedicationDoseView,
    MedicationEvidence,
    MedicationImportAction,
    MedicationImportApproval,
    MedicationImportPlan,
    MedicationImportReport,
    MedicationIntakeConfirmation,
    MedicationIntakeEventRecord,
    MedicationPlanAnalysisItem,
    MedicationScheduleCandidate,
    MedicationScheduleRecord,
)
from folderhome.contracts.observations import (  # noqa: E402
    DirectoryScanReport,
    WatchedFolder,
)
from folderhome.contracts.official_notices import (  # noqa: E402
    NoticeConflict,
    NoticeEvidence,
    OfficialNoticeAnalysis,
    OfficialNoticeOutputReport,
)
from folderhome.contracts.packages import (  # noqa: E402
    DocumentPackageEntryResult,
    DocumentPackageGroup,
    DocumentPackagePlan,
    DocumentPackageResult,
    UnsupportedPackageSource,
)
from folderhome.contracts.personal_notes import (  # noqa: E402
    PersonalNoteAction,
    PersonalNoteApproval,
    PersonalNoteExecutionReport,
    PersonalNoteGuidance,
    PersonalNotePlan,
    PersonalNoteReference,
    PersonalNoteRequest,
    PersonalNoteVersion,
)
from folderhome.contracts.routine_queue import (  # noqa: E402
    FolderRoutineBinding,
    FolderRoutineQueue,
    FolderRoutineQueueItem,
)
from folderhome.contracts.routines import (  # noqa: E402
    FolderRoutineExecutionReport,
    FolderRoutineMode,
    FolderRoutinePlan,
)
from folderhome.contracts.scheduler import (  # noqa: E402
    SchedulerHandoffPlan,
    SchedulerRunReport,
)
from folderhome.contracts.snapshots import (  # noqa: E402
    DirectoryChange,
    DirectoryChangeKind,
    DirectoryDiff,
    DirectoryFileState,
    DirectoryLearningExample,
    DirectorySnapshot,
    PlacementReceipt,
)
from folderhome.contracts.tax import (  # noqa: E402
    TaxExportApproval,
    TaxExportPlan,
    TaxExportReport,
    TaxReceiptApproval,
    TaxReceiptPlan,
    TaxReceiptReport,
    TaxReceiptRequest,
)
from folderhome.contracts.transforms import (  # noqa: E402
    BundleFormat,
    BundleSource,
    DocumentBundlePlan,
    DocumentBundleResult,
    TransformTreatment,
)
from folderhome.contracts.workflow_execution import (  # noqa: E402
    WorkflowAdapterDescriptor,
    WorkflowExecutionEnvelope,
    WorkflowExecutionReport,
)
