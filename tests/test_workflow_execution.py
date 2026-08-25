from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.medication_intake import (
    apply_medication_import_plan,
    build_medication_import_plan,
)
from folderhome.application.profile_rules import load_profile_configuration
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
from folderhome.bridges.fcsa import (
    FcsaDryRunResult,
    FcsaFilePlan,
    FcsaPathPlan,
    FcsaPlanStep,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.capabilities.calendar_store import CalendarStore
from folderhome.capabilities.contact_registry import ContactRegisterStore
from folderhome.capabilities.finance_store import FinanceStore
from folderhome.capabilities.inventory_store import InventoryStore
from folderhome.capabilities.mail_draft import MailDraftLedger, SyntheticDraftTransport
from folderhome.capabilities.medication_store import MedicationStore
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    FolderMedicationPlanAnalysis,
    IndexStatus,
    LogicalResource,
    MedicationEvidence,
    MedicationImportApproval,
    MedicationPlanAnalysisItem,
    MedicationScheduleCandidate,
    PrivacyStatus,
    ResourceRegistry,
    build_document_id,
)
from folderhome.plugin_host import load_manifests

REPOSITORY_ROOT = Path(__file__).parents[1]
PROVIDER_ROOT = REPOSITORY_ROOT.parent / "llm-note"
TAX_PROVIDER_ROOT = REPOSITORY_ROOT.parent / "steuer-assistent"


class StubBundleExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        source_hash = sha256(source_path.read_bytes()).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, source_hash),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=source_hash,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-08-23T08:00:00Z",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetische Testdaten.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


class StubContractSearcher:
    def __init__(self, filename: str) -> None:
        self._filename = filename

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        del query, limit
        return (
            KnowledgeDigestSearchHit(
                source="document",
                filename=self._filename,
                file_type="txt",
                snippet="Synthetischer Versicherungsvertrag",
                relevance=-1.0,
                word_count=2,
            ),
        )


class StubFcsaPlanBridge:
    def __init__(self, scan_root: Path) -> None:
        self.scan_root = scan_root
        self.calls = 0

    def plan(self, config_dir: Path) -> FcsaDryRunResult:
        assert config_dir.name == "config"
        self.calls += 1
        return FcsaDryRunResult(
            settings_fingerprint="a" * 64,
            paths=(
                FcsaPathPlan(
                    scan_path=self.scan_root,
                    unchanged_count=0,
                    skipped_locked=(),
                    was_stale=False,
                    files=(
                        FcsaFilePlan(
                            relative_path="Rechnung.txt",
                            category_id="invoices",
                            matched_category=True,
                            status="planned",
                            had_error=False,
                            steps=(FcsaPlanStep("move", "would move", True),),
                        ),
                    ),
                ),
            ),
        )


def _plugin():
    return next(
        item
        for item in load_manifests(REPOSITORY_ROOT / "manifests" / "components")
        if item.plugin_id == "llm-note"
    )


def _gateway(tmp_path: Path) -> WorkflowExecutionGateway:
    return WorkflowExecutionGateway(
        (
            FindCallWorkflowAdapter(
                profile_ids=frozenset({"lukas", "hanna"}),
            ),
            PersonalNotesWorkflowAdapter(
                plugin=_plugin(),
                provider_root=PROVIDER_ROOT,
                state_dir=tmp_path / "state",
                profile_ids=frozenset({"lukas", "hanna"}),
            ),
            MedicationIntakeWorkflowAdapter(
                state_dir=tmp_path / "state",
                profile_ids=frozenset({"lukas", "hanna"}),
            ),
        )
    )


def _seed_medication_schedule(tmp_path: Path) -> str:
    source_root = tmp_path / "medication-source"
    source_root.mkdir()
    source = source_root / "DemoMed.txt"
    source.write_text("Synthetischer Medikamentenplan.\n", encoding="utf-8")
    source_sha256 = sha256(source.read_bytes()).hexdigest()
    candidate = MedicationScheduleCandidate(
        schedule_id=f"medication_schedule_{sha256(b'schedule').hexdigest()}",
        schedule_key=f"medication_schedule_key_{sha256(b'key').hexdigest()}",
        profile_id="lukas",
        medication_name="DemoMed",
        dose_quantity_milli=1000,
        dose_unit="Tablette",
        scheduled_time="08:00",
        timezone="Europe/Berlin",
        weekdays=(5,),
        valid_from="2026-08-22",
        valid_to="2026-12-31",
        inventory_item_id=f"inventory_item_{sha256(b'inventory').hexdigest()}",
        source_document_id=f"doc_{sha256(b'document').hexdigest()}",
        source_sha256=source_sha256,
        source_path=source,
        evidence=(MedicationEvidence("medication_name", 1, "Präparat"),),
    )
    analysis = FolderMedicationPlanAnalysis(
        source_root=source_root,
        profile_id="lukas",
        items=(
            MedicationPlanAnalysisItem(
                relative_path=source.name,
                status="ready",
                schedule=candidate,
                message="Synthetischer Testzeitplan.",
            ),
        ),
    )
    store = MedicationStore(tmp_path / "state")
    plan = build_medication_import_plan(analysis, store=store)
    approval = MedicationImportApproval(
        approval_id="seed_medication",
        plan_id=plan.plan_id,
        medication_revision=plan.medication_revision,
        action_ids=(plan.actions[0].action_id,),
        approved_at="2026-08-22T07:00:00+02:00",
    )
    apply_medication_import_plan(plan, approval, store=store, allow_state_write=True)
    return candidate.schedule_id


def test_executor_catalog_covers_every_workflow_and_keeps_gaps_visible(
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    catalog = {item.workflow_id: item for item in gateway.catalog()}

    assert len(catalog) == 33
    assert catalog["findcall"].status == "connected"
    assert catalog["findcall"].adapter_id == "findcall_fixture.v1"
    assert catalog["findcall"].side_effects == ("simulation.findcall.fixture",)
    assert catalog["findcall"].request_schema["additionalProperties"] is False
    assert catalog["personal-notes"].status == "connected"
    assert catalog["personal-notes"].adapter_id == "personal_notes.v1"
    assert catalog["personal-notes"].request_schema["additionalProperties"] is False
    assert catalog["medication-intake"].status == "connected"
    assert catalog["medication-intake"].adapter_id == "medication_intake.v1"
    assert catalog["medication-intake"].request_schema["required"] == [
        "action",
        "scheduled_date",
        "confirmed_at",
    ]
    assert catalog["document-library"].status == "direct_read_only"
    assert catalog["master-agent"].status == "planning_only"
    assert catalog["folder-cleanup"].status == "not_connected"
    assert "canonical configured logical resource IDs" in (
        catalog["folder-cleanup"].reason
    )
    assert "explicitly configured external connector" in (
        catalog["mail-connector"].reason
    )
    assert sum(item.status == "connected" for item in catalog.values()) == 3
    assert sum(item.status == "not_connected" for item in catalog.values()) == 26
    assert sum(
        "canonical configured logical resource IDs" in item.reason
        for item in catalog.values()
    ) == 22
    assert sum(
        "explicitly configured external connector" in item.reason
        for item in catalog.values()
    ) == 4


def test_findcall_fixture_adapter_runs_only_the_existing_local_simulation(
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    raw_phone = "+4915111111111"
    request = {
        "action": "simulate",
        "planned_at": "2026-08-23T00:20:00+02:00",
        "area": "mobilität",
        "kind": "quote",
        "service": "Bremsenprüfung Hyundai i10",
        "location": "Beispielstadt",
        "windows": [
            {
                "start_at": "2026-09-16T09:00:00+02:00",
                "end_at": "2026-09-16T12:00:00+02:00",
            }
        ],
        "max_distance_km": 20.0,
        "max_price_eur": 180.0,
        "candidates": [
            {
                "name": "Synthetische Werkstatt",
                "phone_e164": raw_phone,
                "services": ["Bremsenprüfung Hyundai i10"],
                "distance_km": 4.0,
                "priority": 1,
                "fixture": {
                    "status": "COMPLETED",
                    "service_confirmed": True,
                    "available": True,
                    "offered_window": {
                        "start_at": "2026-09-16T10:00:00+02:00",
                        "end_at": "2026-09-16T11:00:00+02:00",
                    },
                    "price_known": True,
                    "price_eur": 175.0,
                    "commitment_made": False,
                    "summary": "Synthetisches Angebot innerhalb der Grenze.",
                },
            }
        ],
    }

    envelope = gateway.prepare(
        workflow_id="findcall",
        profile_id="lukas",
        request=request,
    )

    assert envelope.domain_plan_schema == "folderhome.findcall-plan.v1"
    assert envelope.approval_kind == "explicit_local_fixture_execution"
    assert envelope.side_effects == ("simulation.findcall.fixture",)
    assert raw_phone not in str(envelope.domain_plan)
    assert envelope.domain_plan["network_used"] is False
    assert envelope.domain_plan["phone_calls_placed"] is False

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T00:21:00+02:00",
    )

    assert report.domain_report_schema == "folderhome.findcall-report.v1"
    assert report.domain_report["success"] is True
    assert report.domain_report["simulated"] is True
    assert report.domain_report["network_used"] is False
    assert report.domain_report["phone_calls_placed"] is False
    assert report.domain_report["commitment_made"] is False
    assert report.side_effects == ("simulation.findcall.fixture",)
    with pytest.raises(WorkflowExecutionError, match="bereits ausgeführt"):
        gateway.execute(
            envelope_id=envelope.envelope_id,
            approved_at="2026-08-23T00:22:00+02:00",
        )


def test_findcall_fixture_adapter_rejects_paths_and_live_authority(
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    request = {
        "action": "call",
        "planned_at": "2026-08-23T00:20:00+02:00",
        "area": "mobilität",
        "kind": "quote",
        "service": "Bremsenprüfung Hyundai i10",
        "location": "Beispielstadt",
        "windows": [],
        "max_distance_km": None,
        "max_price_eur": None,
        "candidates": [],
        "path": "C:/private",
    }

    with pytest.raises(WorkflowExecutionError, match="Unbekannte Felder"):
        gateway.prepare(
            workflow_id="findcall",
            profile_id="lukas",
            request=request,
        )


@pytest.mark.skipif(not PROVIDER_ROOT.is_dir(), reason="llm-note checkout unavailable")
def test_personal_note_adapter_prepares_then_executes_only_once(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    database = tmp_path / "state" / "personal-notes" / "llm-note.db"
    request = {
        "action": "create",
        "notebook_id": "gesundheit",
        "area": "gesundheit",
        "title": "Fragen für den Hausarzt",
        "human_content": "Ich möchte drei Fragen für den Termin festhalten.",
        "note_id": None,
        "expected_revision": None,
        "revert_to_revision": None,
        "references": [],
    }

    envelope = gateway.prepare(
        workflow_id="personal-notes",
        profile_id="lukas",
        request=request,
    )

    assert envelope.workflow_id == "personal-notes"
    assert envelope.domain_plan["proposed_content"] == request["human_content"]
    assert envelope.side_effects == ("state.personal_notes.append",)
    assert not database.exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-22T19:00:00+02:00",
    )

    assert report.status == "executed"
    assert report.execution_performed is True
    assert report.domain_report["status"] == "executed"
    assert database.is_file()
    with pytest.raises(WorkflowExecutionError, match="bereits ausgeführt"):
        gateway.execute(
            envelope_id=envelope.envelope_id,
            approved_at="2026-08-22T19:01:00+02:00",
        )


@pytest.mark.skipif(not PROVIDER_ROOT.is_dir(), reason="llm-note checkout unavailable")
def test_gateway_discards_unexecuted_envelope_without_domain_side_effect(
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    database = tmp_path / "state" / "personal-notes" / "llm-note.db"
    envelope = gateway.prepare(
        workflow_id="personal-notes",
        profile_id="lukas",
        request={
            "action": "create",
            "notebook_id": "gesundheit",
            "area": "gesundheit",
            "title": "Noch nicht freigegebene Notiz",
            "human_content": "Diese Ausführungshülle soll verworfen werden.",
            "note_id": None,
            "expected_revision": None,
            "revert_to_revision": None,
            "references": [],
        },
    )

    discarded = gateway.discard_unexecuted((envelope.envelope_id, "unknown"))

    assert discarded == (envelope.envelope_id,)
    assert not database.exists()
    with pytest.raises(WorkflowExecutionError, match="nicht vorbereitet"):
        gateway.execute(
            envelope_id=envelope.envelope_id,
            approved_at="2026-08-22T19:02:00+02:00",
        )


def test_gateway_rejects_unconnected_workflow_before_any_state(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)

    with pytest.raises(WorkflowExecutionError, match="keinen typisierten"):
        gateway.prepare(
            workflow_id="folder-cleanup",
            profile_id="lukas",
            request={"source": "inbox"},
        )
    assert not (tmp_path / "state").exists()


def test_document_bundle_adapter_resolves_ids_and_never_exposes_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-source"
    output = tmp_path / "private-output"
    source.mkdir()
    output.mkdir()
    (source / "Unfall.txt").write_text(
        "Synthetischer Unfallbericht mit Ölspur.",
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="accident_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"documents.bundle.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="document_outputs",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"documents.bundle.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            DocumentBundleWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="document-bundle",
        profile_id="lukas",
        request={
            "source_resource_id": "accident_documents",
            "output_resource_id": "document_outputs",
            "output_name": "Unfallakte.txt",
            "format": "txt",
            "recursive": True,
        },
    )

    serialized_plan = str(envelope.to_dict())
    assert str(source) not in serialized_plan
    assert str(output) not in serialized_plan
    assert envelope.domain_plan["source_resource_id"] == "accident_documents"
    assert envelope.domain_plan["output_resource_id"] == "document_outputs"
    assert not (output / "Unfallakte.txt").exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:01:00+02:00",
    )

    assert (output / "Unfallakte.txt").is_file()
    assert report.domain_report["output_resource_id"] == "document_outputs"
    assert str(output) not in str(report.to_dict())
    assert report.side_effects == ("file.create",)
    with pytest.raises(WorkflowExecutionError, match="Unbekannte Felder"):
        gateway.prepare(
            workflow_id="document-bundle",
            profile_id="lukas",
            request={
                "source_resource_id": "accident_documents",
                "output_resource_id": "document_outputs",
                "output_name": "Zweite.txt",
                "format": "txt",
                "recursive": True,
                "source_path": "C:/private",
            },
        )


def test_contact_register_adapter_extracts_insurance_contact_after_approval(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-insurance"
    state = tmp_path / "private-contact-state"
    source.mkdir()
    state.mkdir()
    (source / "Police.txt").write_text(
        "\n".join(
            (
                "Organisation: Beispiel Versicherung AG",
                "Ansprechpartner: Erika Beispiel",
                "Zuständig für: KFZ-Versicherung",
                "Vertragsobjekt: Hyundai i10",
                "E-Mail: erika@example.invalid",
                "Telefon: +49 30 123456",
                "Gültig ab: 2026-08-01",
            )
        ),
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="insurance_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"contacts.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="contact_store",
                kind="directory",
                local_path=state,
                operations=frozenset({"state_write", "read"}),
                purposes=frozenset({"contacts.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            ContactRegisterWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="contact-register",
        profile_id="lukas",
        request={
            "source_resource_id": "insurance_documents",
            "state_resource_id": "contact_store",
            "area": "versicherungen",
            "recursive": True,
            "allow_sensitive_local_read": False,
        },
    )

    assert not (state / "contacts.sqlite3").exists()
    assert str(source) not in str(envelope.to_dict())
    assert str(state) not in str(envelope.to_dict())
    assert envelope.domain_plan["planned_action_count"] == 1

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:10:00+02:00",
    )

    contacts = ContactRegisterStore(state).list_contacts(
        profile_id="lukas",
        object_query="Hyundai i10",
    )
    assert len(contacts) == 1
    assert contacts[0].phone == "+4930123456"
    assert report.domain_report["created_contact_count"] == 1
    assert str(state) not in str(report.to_dict())


def test_correspondence_adapter_writes_local_letter_without_model_content_leak(
    tmp_path: Path,
) -> None:
    example_root = REPOSITORY_ROOT / "examples" / "correspondence"
    output = tmp_path / "private-correspondence-output"
    output.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="letter_request",
                kind="file",
                local_path=example_root / "insurance-cancellation.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"correspondence.request"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="letter_designs",
                kind="file",
                local_path=example_root / "designs.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"correspondence.designs"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="letter_templates",
                kind="file",
                local_path=example_root / "templates.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"correspondence.templates"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="letter_output",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"correspondence.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            CorrespondenceWorkflowAdapter(
                registry=registry,
                report_forge_revision="0123456789abcdef0123456789abcdef01234567",
                report_forge_distribution_version="1.1.4",
                report_forge_runtime_version="1.1.0",
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="correspondence-studio",
        profile_id="lukas",
        request={
            "request_resource_id": "letter_request",
            "designs_resource_id": "letter_designs",
            "templates_resource_id": "letter_templates",
            "output_resource_id": "letter_output",
            "output_basename": "Versicherungsschreiben",
        },
    )

    assert "Kündigung" in envelope.domain_plan["subject"]
    assert "SYN-4711" in envelope.domain_plan["subject"]
    assert "markdown" not in envelope.domain_plan
    assert "text" not in envelope.domain_plan
    assert "Musterweg" not in str(envelope.to_dict())
    assert str(output) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:20:00+02:00",
    )

    markdown_file = output / "Versicherungsschreiben.md"
    text_file = output / "Versicherungsschreiben.txt"
    assert markdown_file.is_file() and text_file.is_file()
    assert "SYN-4711" in markdown_file.read_text(encoding="utf-8")
    assert report.domain_report["output_resource_id"] == "letter_output"
    assert str(output) not in str(report.to_dict())


def _mail_draft_registry(tmp_path: Path) -> tuple[ResourceRegistry, Path]:
    example_root = REPOSITORY_ROOT / "examples" / "correspondence"
    private = tmp_path / "private-mail-configuration"
    private.mkdir()
    password_file = private / "mailbox-password.txt"
    password_file.write_text("synthetisches-postfach-geheimnis", encoding="utf-8")
    account_file = private / "mail-draft-account.json"
    account_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.mail-draft-account.v1",
                "account_id": "family-mailbox",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "from_address": "lukas@example.invalid",
                "host": "imap.example.invalid",
                "port": 993,
                "use_ssl": True,
                "username": "lukas@example.invalid",
                "drafts_folder": "INBOX.Drafts",
                "password_file": str(password_file),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    request_file = private / "letter-with-mail-recipient.json"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.correspondence-request.v1",
                "profile_id": "lukas",
                "area": "versicherungen",
                "purpose": "kuendigung",
                "template_id": "insurance-cancellation",
                "created_on": "2026-08-22",
                "sender": {
                    "name": "Lukas Beispiel",
                    "address_lines": ["Musterweg 1", "12345 Beispielstadt"],
                    "email": "lukas@example.invalid",
                    "phone": None,
                },
                "recipient": {
                    "name": "Beispiel Versicherung AG",
                    "address_lines": ["Versicherungsplatz 2", "54321 Beispielstadt"],
                    "email": "service@example.invalid",
                    "phone": None,
                },
                "variables": {
                    "policy_number": "SYN-4711",
                    "vehicle": "Hyundai i10",
                    "termination_date": "31.12.2026",
                },
                "attachments": [],
                "evidence_refs": ["doc_" + "a" * 64],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="mail_draft_account",
                kind="file",
                local_path=account_file,
                operations=frozenset({"read"}),
                purposes=frozenset({"mail.draft_account"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="letter_request",
                kind="file",
                local_path=request_file,
                operations=frozenset({"read"}),
                purposes=frozenset({"correspondence.request"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="letter_designs",
                kind="file",
                local_path=example_root / "designs.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"correspondence.designs"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="letter_templates",
                kind="file",
                local_path=example_root / "templates.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"correspondence.templates"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    return registry, password_file


def _mail_draft_request() -> dict[str, object]:
    return {
        "account_resource_id": "mail_draft_account",
        "request_resource_id": "letter_request",
        "designs_resource_id": "letter_designs",
        "templates_resource_id": "letter_templates",
        "planned_at": "2026-08-25T09:00:00+02:00",
    }


def test_mail_draft_adapter_appends_one_draft_without_sending_or_leaking(
    tmp_path: Path,
) -> None:
    registry, password_file = _mail_draft_registry(tmp_path)
    transport = SyntheticDraftTransport()
    gateway = WorkflowExecutionGateway(
        (
            MailDraftWorkflowAdapter(
                registry=registry,
                state_dir=tmp_path / "state",
                report_forge_revision="0123456789abcdef0123456789abcdef01234567",
                report_forge_distribution_version="1.1.4",
                report_forge_runtime_version="1.1.0",
                allow_mail_draft=True,
                transport_factory=lambda account: transport,
            ),
        )
    )
    descriptor = gateway.descriptor("mail-connector")
    assert descriptor.status == "connected"
    assert descriptor.side_effects == ("external.mailbox.draft_write",)

    envelope = gateway.prepare(
        workflow_id="mail-connector",
        profile_id="lukas",
        request=_mail_draft_request(),
    )

    serialized = str(envelope.to_dict())
    assert envelope.domain_plan["delivery_attempted"] is False
    assert envelope.domain_plan["recipient_disclosed"] is False
    assert envelope.domain_plan["body_disclosed"] is False
    assert envelope.domain_plan["live_effect_approved"] is True
    assert envelope.domain_plan["drafts_folder"] == "INBOX.Drafts"
    assert "service@example.invalid" not in serialized
    assert "synthetisches-postfach-geheimnis" not in serialized
    assert str(password_file) not in serialized
    assert "imap.example.invalid" not in serialized
    assert transport.appended == []

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-25T09:05:00+02:00",
    )

    assert report.domain_report["status"] == "drafted"
    assert report.domain_report["email_sent"] is False
    assert report.domain_report["account_resource_id"] == "mail_draft_account"
    assert len(transport.appended) == 1
    folder, raw = transport.appended[0]
    assert folder == "INBOX.Drafts"
    assert b"service@example.invalid" in raw
    assert MailDraftLedger(tmp_path / "state").status(
        str(envelope.domain_plan["idempotency_key"])
    ) == "drafted"
    assert "synthetisches-postfach-geheimnis" not in str(report.to_dict())


def test_mail_draft_adapter_plans_but_refuses_execution_without_live_gate(
    tmp_path: Path,
) -> None:
    registry, _ = _mail_draft_registry(tmp_path)
    transport = SyntheticDraftTransport()
    gateway = WorkflowExecutionGateway(
        (
            MailDraftWorkflowAdapter(
                registry=registry,
                state_dir=tmp_path / "state",
                report_forge_revision="0123456789abcdef0123456789abcdef01234567",
                report_forge_distribution_version="1.1.4",
                report_forge_runtime_version="1.1.0",
                allow_mail_draft=False,
                transport_factory=lambda account: transport,
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="mail-connector",
        profile_id="lukas",
        request=_mail_draft_request(),
    )
    assert envelope.domain_plan["live_effect_approved"] is False

    with pytest.raises(WorkflowExecutionError, match="--approve-mail-draft"):
        gateway.execute(
            envelope_id=envelope.envelope_id,
            approved_at="2026-08-25T09:05:00+02:00",
        )

    assert transport.appended == []


def test_local_calendar_adapter_records_evidenced_appointment_without_connector(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-appointment-documents"
    state = tmp_path / "private-calendar-state"
    source.mkdir()
    state.mkdir()
    (source / "Werkstatttermin.txt").write_text(
        "\n".join(
            (
                "Termin: Werkstattprüfung Hyundai i10",
                "Datum: 2026-09-02",
                "Beginn: 10:30",
                "Ende: 11:30",
                "Ort: Beispielwerkstatt",
            )
        ),
        encoding="utf-8",
    )
    calendar_config = tmp_path / "calendar.json"
    calendar_config.write_text(
        '{"schema":"folderhome.calendar-config.v1",'
        '"default_backend":"folderhome_local",'
        '"default_timezone":"Europe/Berlin",'
        '"uptoday_ics_directory":"unused"}',
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="appointment_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"calendar.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="calendar_configuration",
                kind="file",
                local_path=calendar_config,
                operations=frozenset({"read"}),
                purposes=frozenset({"calendar.configuration"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="local_calendar",
                kind="local_calendar",
                local_path=state,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"calendar.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas", "hanna", "simon"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            LocalCalendarWorkflowAdapter(
                registry=registry,
                profiles=load_profile_configuration(
                    REPOSITORY_ROOT / "examples" / "profiles"
                ),
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="calendar-handoff",
        profile_id="lukas",
        request={
            "source_resource_id": "appointment_documents",
            "configuration_resource_id": "calendar_configuration",
            "state_resource_id": "local_calendar",
            "area": "termine",
            "planned_at": "2026-08-23T08:30:00+02:00",
            "recursive": True,
            "allow_sensitive_local_read": False,
        },
    )

    assert envelope.domain_plan["backend"] == "folderhome_local"
    assert envelope.domain_plan["planned_action_count"] == 1
    assert str(source) not in str(envelope.to_dict())
    assert str(state) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:31:00+02:00",
    )

    events = CalendarStore(state).list_events(profile_id="lukas")
    assert len(events) == 1
    assert events[0].title == "Werkstattprüfung Hyundai i10"
    assert report.domain_report["connector_invoked"] is False
    assert report.domain_report["export_written"] is False
    assert report.side_effects == ("state.calendar.write",)
    assert str(state) not in str(report.to_dict())


def _local_calendar_export_gateway(
    tmp_path: Path,
) -> tuple[WorkflowExecutionGateway, Path, Path]:
    source = tmp_path / "private-appointment-documents"
    state = tmp_path / "private-calendar-state"
    export = tmp_path / "private-calendar-export"
    for directory in (source, state, export):
        directory.mkdir()
    (source / "Werkstatttermin.txt").write_text(
        "\n".join(
            (
                "Termin: Werkstattprüfung Hyundai i10",
                "Datum: 2026-09-02",
                "Beginn: 10:30",
                "Ende: 11:30",
                "Ort: Beispielwerkstatt",
            )
        ),
        encoding="utf-8",
    )
    calendar_config = tmp_path / "calendar.json"
    calendar_config.write_text(
        '{"schema":"folderhome.calendar-config.v1",'
        '"default_backend":"folderhome_local",'
        '"default_timezone":"Europe/Berlin",'
        '"uptoday_ics_directory":"unused"}',
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="appointment_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"calendar.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="calendar_configuration",
                kind="file",
                local_path=calendar_config,
                operations=frozenset({"read"}),
                purposes=frozenset({"calendar.configuration"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="local_calendar",
                kind="local_calendar",
                local_path=state,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"calendar.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="calendar_export",
                kind="directory",
                local_path=export,
                operations=frozenset({"create"}),
                purposes=frozenset({"calendar.export_output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas", "hanna", "simon"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            LocalCalendarWorkflowAdapter(
                registry=registry,
                profiles=load_profile_configuration(
                    REPOSITORY_ROOT / "examples" / "profiles"
                ),
                extractor=StubBundleExtractor(),
            ),
        )
    )
    return gateway, state, export


def _local_calendar_export_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "source_resource_id": "appointment_documents",
        "configuration_resource_id": "calendar_configuration",
        "state_resource_id": "local_calendar",
        "area": "termine",
        "planned_at": "2026-08-23T08:30:00+02:00",
        "recursive": True,
        "allow_sensitive_local_read": False,
        "export_resource_id": "calendar_export",
        "export_basename": "Hyundai-i10-Termine",
    }
    request.update(overrides)
    return request


def test_local_calendar_adapter_exports_recorded_appointments_as_one_ics(
    tmp_path: Path,
) -> None:
    gateway, state, export = _local_calendar_export_gateway(tmp_path)

    envelope = gateway.prepare(
        workflow_id="calendar-handoff",
        profile_id="lukas",
        request=_local_calendar_export_request(),
    )

    assert envelope.domain_plan["export_planned"] is True
    assert envelope.domain_plan["export_resource_id"] == "calendar_export"
    assert envelope.domain_plan["export_name"] == "Hyundai-i10-Termine"
    assert len(str(envelope.domain_plan["export_sha256"])) == 64
    assert envelope.side_effects == ("state.calendar.write", "file.create")
    assert str(export) not in str(envelope.to_dict())
    assert not any(export.iterdir())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:31:00+02:00",
    )

    exported = export / "Hyundai-i10-Termine.ics"
    assert exported.is_file()
    raw = exported.read_bytes()
    payload = raw.decode("utf-8")
    assert payload.startswith("BEGIN:VCALENDAR\r\n")
    assert payload.rstrip("\r\n").endswith("END:VCALENDAR")
    assert payload.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:Werkstattprüfung Hyundai i10" in payload
    assert "DTSTART;TZID=Europe/Berlin:20260902T103000" in payload
    assert sha256(raw).hexdigest() == envelope.domain_plan["export_sha256"]
    assert report.domain_report["export_written"] is True
    assert report.domain_report["export_name"] == "Hyundai-i10-Termine.ics"
    assert report.domain_report["export_event_count"] == 1
    assert report.side_effects == ("state.calendar.write", "file.create")
    assert len(CalendarStore(state).list_events(profile_id="lukas")) == 1
    assert str(export) not in str(report.to_dict())


def test_local_calendar_export_never_overwrites_and_rolls_back(
    tmp_path: Path,
) -> None:
    gateway, state, export = _local_calendar_export_gateway(tmp_path)
    occupied = export / "Hyundai-i10-Termine.ics"
    occupied.write_text("BESTEHENDE DATEI", encoding="utf-8")

    envelope = gateway.prepare(
        workflow_id="calendar-handoff",
        profile_id="lukas",
        request=_local_calendar_export_request(),
    )
    with pytest.raises(WorkflowExecutionError, match="existiert bereits"):
        gateway.execute(
            envelope_id=envelope.envelope_id,
            approved_at="2026-08-23T08:31:00+02:00",
        )

    assert occupied.read_text(encoding="utf-8") == "BESTEHENDE DATEI"
    assert CalendarStore(state).list_events(profile_id="lukas") == ()


def test_local_calendar_export_requires_both_resource_and_name(
    tmp_path: Path,
) -> None:
    gateway, _, _ = _local_calendar_export_gateway(tmp_path)

    with pytest.raises(WorkflowExecutionError, match="gemeinsam"):
        gateway.prepare(
            workflow_id="calendar-handoff",
            profile_id="lukas",
            request=_local_calendar_export_request(export_basename=None),
        )


def test_local_calendar_export_rejects_a_resource_without_the_export_purpose(
    tmp_path: Path,
) -> None:
    gateway, _, _ = _local_calendar_export_gateway(tmp_path)

    with pytest.raises(WorkflowExecutionError, match="Zweckbindung"):
        gateway.prepare(
            workflow_id="calendar-handoff",
            profile_id="lukas",
            request=_local_calendar_export_request(
                export_resource_id="appointment_documents"
            ),
        )


def test_health_dossier_adapter_keeps_medical_content_in_local_outputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-health-documents"
    output = tmp_path / "private-health-output"
    source.mkdir()
    output.mkdir()
    (source / "Arztbericht.txt").write_text(
        "\n".join(
            (
                "Dokumenttyp: Arztbericht",
                "Dokumentdatum: 2026-08-01",
                "Fachbereich: Hausarzt",
                "Befund: Blutdruck wurde mit 120/80 dokumentiert.",
                "Medikament: DemoMed morgens.",
            )
        ),
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="health_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read", "sensitive_read"}),
                purposes=frozenset({"health.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="health_output",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"health.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            HealthDossierWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="health-dossier",
        profile_id="lukas",
        request={
            "source_resource_id": "health_documents",
            "output_resource_id": "health_output",
            "output_basename": "Gesundheitsdossier",
            "as_of": "2026-08-23",
            "recursive": True,
            "gap_threshold_days": 90,
        },
    )

    assert envelope.domain_plan["timeline_entry_count"] == 2
    assert envelope.domain_plan["content_disclosed"] is False
    assert "Blutdruck" not in str(envelope.to_dict())
    assert str(source) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:41:00+02:00",
    )

    markdown_file = output / "Gesundheitsdossier.md"
    json_file = output / "Gesundheitsdossier.json"
    assert markdown_file.is_file() and json_file.is_file()
    assert "Blutdruck" in markdown_file.read_text(encoding="utf-8")
    assert report.domain_report["medical_advice"] is False
    assert report.domain_report["output_resource_id"] == "health_output"
    assert "Blutdruck" not in str(report.to_dict())


def test_finance_import_adapter_rebuilds_local_account_after_approval(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-finance-documents"
    state = tmp_path / "private-finance-state"
    source.mkdir()
    state.mkdir()
    (source / "Kontoauszug.txt").write_text(
        "".join(
            (
                "Kontokennung: giro-lukas\n",
                "Institut: Beispielbank\n",
                "Konto-Endung: 1234\n",
                "Zeitraum: 2026-07-01 | 2026-07-31\n",
                "Anfangssaldo: 100000 | EUR\n",
                "Endsaldo: 98701 | EUR\n",
                "Buchung: 2026-07-05 | -1299 | StreamFlix | subscription | tx-juli-stream\n",
            )
        ),
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="finance_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read", "sensitive_read"}),
                purposes=frozenset({"finance.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="finance_state",
                kind="directory",
                local_path=state,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"finance.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            FinanceImportWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="finance-import",
        profile_id="lukas",
        request={
            "source_resource_id": "finance_documents",
            "state_resource_id": "finance_state",
            "recursive": True,
            "allow_sensitive_local_read": True,
        },
    )

    store = FinanceStore(state)
    assert store.list_statements() == ()
    assert envelope.domain_plan["planned_action_count"] == 1
    assert envelope.domain_plan["content_disclosed"] is False
    assert "StreamFlix" not in str(envelope.to_dict())
    assert str(source) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T08:51:00+02:00",
    )

    assert len(store.list_statements(profile_id="lukas")) == 1
    assert len(store.list_transactions(profile_id="lukas")) == 1
    assert report.domain_report["created_statement_count"] == 1
    assert report.domain_report["bank_access_performed"] is False
    assert report.domain_report["state_resource_id"] == "finance_state"
    assert "StreamFlix" not in str(report.to_dict())
    assert str(state) not in str(report.to_dict())


def test_official_notice_adapter_writes_private_extractive_report_after_approval(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-notice.txt"
    output = tmp_path / "private-notice-output"
    output.mkdir()
    source.write_text(
        "\n".join(
            (
                "Bescheidart: Bewilligungsbescheid",
                "Behörde: Beispiel-Jobcenter",
                "Aktenzeichen: SYN-2026-17",
                "Bescheiddatum: 2026-08-20",
                "Leistungszeitraum: September 2026",
                "Entscheidung: Leistungen werden synthetisch bewilligt.",
                "Begründung: Synthetische Voraussetzungen liegen vor.",
                "Rechtsbehelf: Widerspruch möglich.",
                "Fristtext: Beachten Sie das ausdrücklich gedruckte Fristdatum.",
                "Explizites Fristdatum: 2026-09-20",
                "Rechtsbehelfsstelle: Beispiel-Jobcenter",
            )
        ),
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="official_notice",
                kind="file",
                local_path=source,
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"official_notice.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="official_notice_output",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"official_notice.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            OfficialNoticeWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="official-notice-understanding",
        profile_id="lukas",
        request={
            "source_resource_id": "official_notice",
            "output_resource_id": "official_notice_output",
            "output_basename": "Bescheidbericht",
            "received_on": "2026-08-21",
            "as_of": "2026-08-23T09:00:00+02:00",
        },
    )

    assert envelope.domain_plan["status"] == "ready_for_review"
    assert envelope.domain_plan["deadline_urgency"] == "later"
    assert envelope.domain_plan["content_disclosed"] is False
    assert "Beispiel-Jobcenter" not in str(envelope.to_dict())
    assert not (output / "Bescheidbericht.md").exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T09:01:00+02:00",
    )

    markdown_file = output / "Bescheidbericht.md"
    json_file = output / "Bescheidbericht.json"
    assert markdown_file.is_file() and json_file.is_file()
    assert "Beispiel-Jobcenter" in markdown_file.read_text(encoding="utf-8")
    assert report.domain_report["legal_review_status"] == "not_performed"
    assert report.domain_report["external_actions_performed"] is False
    assert report.domain_report["output_resource_id"] == "official_notice_output"
    assert "Beispiel-Jobcenter" not in str(report.to_dict())
    assert str(output) not in str(report.to_dict())


def test_administrative_draft_adapter_writes_review_only_objection_after_approval(
    tmp_path: Path,
) -> None:
    notice_root = REPOSITORY_ROOT / "examples" / "notices"
    correspondence_root = REPOSITORY_ROOT / "examples" / "correspondence"
    output = tmp_path / "private-administrative-output"
    output.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="administrative_request",
                kind="file",
                local_path=notice_root / "objection-draft-request.json",
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"administrative.request"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="administrative_notice",
                kind="file",
                local_path=notice_root / "Bescheid.txt",
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"administrative.notice"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="administrative_designs",
                kind="file",
                local_path=correspondence_root / "designs.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"administrative.designs"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="administrative_templates",
                kind="file",
                local_path=notice_root / "administrative-templates.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"administrative.templates"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="administrative_output",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"administrative.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            AdministrativeDraftWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
                report_forge_revision="0123456789abcdef0123456789abcdef01234567",
                report_forge_distribution_version="1.1.4",
                report_forge_runtime_version="1.1.0",
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="administrative-drafts",
        profile_id="lukas",
        request={
            "request_resource_id": "administrative_request",
            "notice_resource_id": "administrative_notice",
            "designs_resource_id": "administrative_designs",
            "templates_resource_id": "administrative_templates",
            "output_resource_id": "administrative_output",
            "output_basename": "Widerspruchsentwurf",
            "received_on": "2026-08-15",
            "as_of": "2026-08-23T09:10:00+02:00",
        },
    )

    assert envelope.domain_plan["draft_kind"] == "objection"
    assert envelope.domain_plan["human_confirmation_required"] is True
    assert envelope.domain_plan["send_supported"] is False
    assert envelope.domain_plan["content_disclosed"] is False
    assert "Beispiel-Jobcenter" not in str(envelope.to_dict())
    assert not (output / "Widerspruchsentwurf.md").exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T09:11:00+02:00",
    )

    markdown_file = output / "Widerspruchsentwurf.md"
    text_file = output / "Widerspruchsentwurf.txt"
    assert markdown_file.is_file() and text_file.is_file()
    assert "Widerspruchsentwurf" in markdown_file.read_text(encoding="utf-8")
    assert report.domain_report["sent"] is False
    assert report.domain_report["legal_review_status"] == "not_performed"
    assert report.domain_report["external_actions_performed"] is False
    assert "Beispiel-Jobcenter" not in str(report.to_dict())
    assert str(output) not in str(report.to_dict())


def test_benefit_screening_adapter_writes_private_orientation_after_approval(
    tmp_path: Path,
) -> None:
    benefit_root = REPOSITORY_ROOT / "examples" / "benefits"
    output = tmp_path / "private-benefit-output"
    output.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="benefit_profile",
                kind="file",
                local_path=benefit_root / "Lukas-benefit-profile.json",
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"benefits.profile"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="benefit_catalog",
                kind="file",
                local_path=benefit_root / "official-routing-catalog.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"benefits.catalog"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="benefit_output",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"benefits.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (BenefitScreeningWorkflowAdapter(registry=registry),)
    )

    envelope = gateway.prepare(
        workflow_id="benefit-screening",
        profile_id="lukas",
        request={
            "profile_resource_id": "benefit_profile",
            "catalog_resource_id": "benefit_catalog",
            "output_resource_id": "benefit_output",
            "output_basename": "Leistungsvorcheck",
            "as_of": "2026-08-23T09:20:00+02:00",
            "max_source_age_days": 7,
        },
    )

    assert envelope.domain_plan["status"] == "review_required"
    assert envelope.domain_plan["result_count"] == 3
    assert envelope.domain_plan["eligibility_assessed"] is False
    assert envelope.domain_plan["network_used"] is False
    assert envelope.domain_plan["content_disclosed"] is False
    assert any(
        item["name"] == "Kinderzuschlag-Lotse"
        for item in envelope.domain_plan["routing_results"]
    )
    assert "has_child_in_household" not in str(envelope.to_dict())
    assert not (output / "Leistungsvorcheck.md").exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T09:21:00+02:00",
    )

    markdown_file = output / "Leistungsvorcheck.md"
    json_file = output / "Leistungsvorcheck.json"
    assert markdown_file.is_file() and json_file.is_file()
    assert "Kinderzuschlag" in markdown_file.read_text(encoding="utf-8")
    assert report.domain_report["eligibility_assessed"] is False
    assert report.domain_report["application_generated"] is False
    assert report.domain_report["external_actions_performed"] is False
    assert "has_child_in_household" not in str(report.to_dict())
    assert str(output) not in str(report.to_dict())


def test_legal_change_monitor_adapter_writes_private_review_candidates_after_approval(
    tmp_path: Path,
) -> None:
    legal_root = REPOSITORY_ROOT / "examples" / "legal"
    output = tmp_path / "private-legal-output"
    output.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="legal_before",
                kind="file",
                local_path=legal_root / "before.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"legal.before"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="legal_after",
                kind="file",
                local_path=legal_root / "after.json",
                operations=frozenset({"read"}),
                purposes=frozenset({"legal.after"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="legal_interests",
                kind="file",
                local_path=legal_root / "Lukas-interests.json",
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"legal.interests"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="legal_output",
                kind="directory",
                local_path=output,
                operations=frozenset({"create"}),
                purposes=frozenset({"legal.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (LegalChangeMonitorWorkflowAdapter(registry=registry),)
    )

    envelope = gateway.prepare(
        workflow_id="legal-change-monitor",
        profile_id="lukas",
        request={
            "before_resource_id": "legal_before",
            "after_resource_id": "legal_after",
            "interests_resource_id": "legal_interests",
            "output_resource_id": "legal_output",
            "output_basename": "Rechtsaenderungen",
            "as_of": "2026-08-23T09:30:00+02:00",
            "max_source_age_days": 7,
            "allow_test_fixture": True,
        },
    )

    assert envelope.domain_plan["status"] == "review_required"
    assert envelope.domain_plan["change_count"] == 1
    assert envelope.domain_plan["review_candidate_count"] == 1
    assert envelope.domain_plan["legal_effect_assessed"] is False
    assert envelope.domain_plan["notification_sent"] is False
    assert envelope.domain_plan["network_used"] is False
    assert "krankenversicherung" not in str(envelope.to_dict())
    assert not (output / "Rechtsaenderungen.md").exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T09:31:00+02:00",
    )

    markdown_file = output / "Rechtsaenderungen.md"
    json_file = output / "Rechtsaenderungen.json"
    assert markdown_file.is_file() and json_file.is_file()
    assert "Krankenversicherung" in markdown_file.read_text(encoding="utf-8")
    assert report.domain_report["legal_effect_assessed"] is False
    assert report.domain_report["notification_sent"] is False
    assert report.domain_report["external_actions_performed"] is False
    assert "krankenversicherung" not in str(report.to_dict())
    assert str(output) not in str(report.to_dict())


def test_inventory_import_adapter_appends_private_observation_after_approval(
    tmp_path: Path,
) -> None:
    source = REPOSITORY_ROOT / "examples" / "inventory" / "bestand"
    state = tmp_path / "private-inventory-state"
    state.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="inventory_documents",
                kind="directory",
                local_path=source,
                operations=frozenset({"list", "read"}),
                purposes=frozenset({"inventory.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="inventory_state",
                kind="directory",
                local_path=state,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"inventory.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            InventoryImportWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="inventory-import",
        profile_id="lukas",
        request={
            "source_resource_id": "inventory_documents",
            "state_resource_id": "inventory_state",
            "recursive": True,
            "allow_sensitive_local_read": False,
        },
    )

    store = InventoryStore(state)
    assert store.list_events() == ()
    assert envelope.domain_plan["planned_action_count"] == 1
    assert envelope.domain_plan["automatic_purchase"] is False
    assert envelope.domain_plan["content_disclosed"] is False
    assert "Vorratsschrank" not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T09:41:00+02:00",
    )

    events = store.list_events(profile_id="lukas")
    assert len(events) == 1
    assert events[0].name == "Reis"
    assert report.domain_report["created_event_count"] == 1
    assert report.domain_report["automatic_purchase"] is False
    assert report.domain_report["state_resource_id"] == "inventory_state"
    assert "Vorratsschrank" not in str(report.to_dict())
    assert str(state) not in str(report.to_dict())


def test_daily_briefing_adapter_renders_and_delivers_only_after_approval(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    desktop_root = tmp_path / "desktop"
    output_root.mkdir()
    desktop_root.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="weather_snapshot",
                kind="file",
                local_path=REPOSITORY_ROOT / "examples" / "briefing" / "weather-snapshot.json",
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"briefing.weather_snapshot"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="news_snapshot",
                kind="file",
                local_path=REPOSITORY_ROOT / "examples" / "briefing" / "news-snapshot.json",
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"briefing.news_snapshot"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="briefing_output",
                kind="directory",
                local_path=output_root,
                operations=frozenset({"create"}),
                purposes=frozenset({"briefing.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="briefing_desktop",
                kind="directory",
                local_path=desktop_root,
                operations=frozenset({"create"}),
                purposes=frozenset({"briefing.desktop"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            DailyBriefingWorkflowAdapter(
                registry=registry,
            ),
        )
    )
    request = {
        "weather_resource_id": "weather_snapshot",
        "news_resource_id": "news_snapshot",
        "output_resource_id": "briefing_output",
        "desktop_resource_id": "briefing_desktop",
        "output_name": "Morgenbrief.html",
        "desktop_name": "Morgenbrief.html",
        "briefing_date": "2026-08-22",
        "as_of": "2026-08-22T06:00:00+02:00",
        "timezone": "Europe/Berlin",
        "title": "FolderHome Morgenbrief",
        "categories": ["lokales", "wissenschaft"],
        "max_items_per_category": 2,
        "max_weather_age_minutes": 180,
        "max_news_age_minutes": 180,
        "allow_sensitive_local_read": True,
    }

    envelope = gateway.prepare(
        workflow_id="daily-briefing",
        profile_id="lukas",
        request=request,
    )

    assert not (output_root / "Morgenbrief.html").exists()
    assert not (desktop_root / "Morgenbrief.html").exists()
    assert envelope.domain_plan["article_count"] == 2
    assert envelope.domain_plan["content_disclosed"] is False
    assert str(REPOSITORY_ROOT) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-22T06:01:00+02:00",
    )

    assert (output_root / "Morgenbrief.html").is_file()
    assert (desktop_root / "Morgenbrief.html").read_bytes() == (
        output_root / "Morgenbrief.html"
    ).read_bytes()
    assert report.domain_report["desktop_written"] is True
    assert report.domain_report["network_invoked"] is False
    assert report.domain_report["paths_disclosed"] is False


@pytest.mark.skipif(
    not TAX_PROVIDER_ROOT.is_dir(),
    reason="pinned steuer-assistent checkout unavailable",
)
def test_tax_workpaper_adapter_exports_private_zip_only_after_approval(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "tax-state"
    output_root = tmp_path / "tax-output"
    (state_root / "lukas").mkdir(parents=True)
    output_root.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="tax_state",
                kind="directory",
                local_path=state_root,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"tax.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="tax_output",
                kind="directory",
                local_path=output_root,
                operations=frozenset({"create"}),
                purposes=frozenset({"tax.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    tax_plugin = next(
        item
        for item in load_manifests(REPOSITORY_ROOT / "manifests" / "components")
        if item.plugin_id == "steuer-assistent"
    )
    gateway = WorkflowExecutionGateway(
        (
            TaxWorkpaperWorkflowAdapter(
                registry=registry,
                plugin=tax_plugin,
                provider_root=TAX_PROVIDER_ROOT,
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="tax-workpaper",
        profile_id="lukas",
        request={
            "state_resource_id": "tax_state",
            "output_resource_id": "tax_output",
            "output_name": "STEUER_UNTERLAGEN_2026.zip",
            "tax_year": 2026,
        },
    )

    assert envelope.domain_plan["receipt_count"] == 0
    assert envelope.domain_plan["official_format"] is False
    assert envelope.domain_plan["portal_submission_supported"] is False
    assert not (output_root / "STEUER_UNTERLAGEN_2026.zip").exists()
    assert str(state_root) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T10:15:00+02:00",
    )

    assert (output_root / "STEUER_UNTERLAGEN_2026.zip").is_file()
    assert report.domain_report["official_format"] is False
    assert report.domain_report["portal_submitted"] is False
    assert report.domain_report["network_invoked"] is False
    assert report.domain_report["paths_disclosed"] is False


def test_folder_cleanup_adapter_moves_only_planned_files_after_approval(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "inbox"
    target_root = tmp_path / "organized"
    state_root = tmp_path / "state"
    source_root.mkdir()
    target_root.mkdir()
    state_root.mkdir()
    source_file = source_root / "A.txt"
    source_file.write_text("Synthetischer Inhalt", encoding="utf-8")
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="cleanup_source",
                kind="directory",
                local_path=source_root,
                operations=frozenset({"list", "read", "sensitive_read", "move"}),
                purposes=frozenset({"folder_cleanup.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="cleanup_target",
                kind="directory",
                local_path=target_root,
                operations=frozenset({"create", "move"}),
                purposes=frozenset({"folder_cleanup.target"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="cleanup_state",
                kind="directory",
                local_path=state_root,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"folder_cleanup.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    profiles = load_profile_configuration(REPOSITORY_ROOT / "examples" / "profiles")
    gateway = WorkflowExecutionGateway(
        (
            FolderCleanupWorkflowAdapter(
                registry=registry,
                profiles=profiles,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="folder-cleanup",
        profile_id="lukas",
        request={
            "source_resource_id": "cleanup_source",
            "target_resource_id": "cleanup_target",
            "state_resource_id": "cleanup_state",
            "area": "dokumente",
            "as_of": "2026-08-23",
            "recursive": True,
            "allow_sensitive_local_read": True,
        },
    )

    assert source_file.is_file()
    assert envelope.domain_plan["selected_item_count"] == 1
    assert envelope.domain_plan["content_disclosed"] is False
    assert str(source_root) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T10:30:00+02:00",
    )

    renamed = source_root / "Lukas_2026-08-23_A.txt"
    assert not source_file.exists()
    assert renamed.read_text(encoding="utf-8") == "Synthetischer Inhalt"
    assert report.domain_report["execution_count"] == 1
    assert report.domain_report["placement_receipt_count"] == 1
    assert report.domain_report["paths_disclosed"] is False


def test_directory_observation_adapter_writes_bound_checkpoint_after_approval(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "observed"
    state_root = tmp_path / "observation-state"
    source_root.mkdir()
    state_root.mkdir()
    (source_root / "A.txt").write_text("A", encoding="utf-8")
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="observed_folder",
                kind="directory",
                local_path=source_root,
                operations=frozenset({"list", "read", "sensitive_read"}),
                purposes=frozenset({"directory_observation.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="observation_state",
                kind="directory",
                local_path=state_root,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"directory_observation.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (DirectoryObservationWorkflowAdapter(registry=registry),)
    )

    envelope = gateway.prepare(
        workflow_id="directory-observation",
        profile_id="lukas",
        request={
            "source_resource_id": "observed_folder",
            "state_resource_id": "observation_state",
            "watch_id": "inbox_watch",
            "area": "dokumente",
            "captured_at": "2026-08-23T10:45:00+02:00",
            "interval_minutes": 60,
            "recursive": True,
            "allow_sensitive_local_read": True,
        },
    )

    assert envelope.domain_plan["file_count"] == 1
    assert envelope.domain_plan["checkpoint_write_planned"] is True
    assert not (state_root / "directory-snapshots").exists()
    assert str(source_root) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T10:46:00+02:00",
    )

    assert len(tuple((state_root / "directory-snapshots").glob("*.json"))) == 1
    assert report.domain_report["checkpoint_written"] is True
    assert report.domain_report["file_count"] == 1
    assert report.domain_report["paths_disclosed"] is False


def test_document_package_adapter_publishes_grouped_zip_after_approval(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "package-source"
    output_root = tmp_path / "package-output"
    source_root.mkdir()
    output_root.mkdir()
    (source_root / "A.txt").write_text("Äpfel", encoding="utf-8")
    (source_root / "B.md").write_text("Öl", encoding="utf-8")
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="package_source",
                kind="directory",
                local_path=source_root,
                operations=frozenset({"list", "read", "sensitive_read"}),
                purposes=frozenset({"document_package.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="package_output",
                kind="directory",
                local_path=output_root,
                operations=frozenset({"create"}),
                purposes=frozenset({"document_package.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            DocumentPackageWorkflowAdapter(
                registry=registry,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="document-package",
        profile_id="lukas",
        request={
            "source_resource_id": "package_source",
            "output_resource_id": "package_output",
            "output_name": "Dokumente.zip",
            "recursive": True,
            "allow_sensitive_local_read": True,
        },
    )

    assert envelope.domain_plan["group_count"] == 2
    assert envelope.domain_plan["source_count"] == 2
    assert envelope.domain_plan["content_disclosed"] is False
    assert not (output_root / "Dokumente.zip").exists()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T11:00:00+02:00",
    )

    assert (output_root / "Dokumente.zip").is_file()
    assert report.domain_report["entry_count"] == 2
    assert report.domain_report["paths_disclosed"] is False


def test_artifact_studio_adapter_writes_design_set_and_business_card_after_approval(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "design-output"
    output_root.mkdir()
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="design_output",
                kind="directory",
                local_path=output_root,
                operations=frozenset({"create"}),
                purposes=frozenset({"artifact_studio.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (ArtifactStudioWorkflowAdapter(registry=registry),)
    )
    request = {
        "output_resource_id": "design_output",
        "output_basename": "folderhome-family",
        "design_set_id": "folderhome-family",
        "display_name": "FolderHome Familie",
        "purpose": "Private Haushaltsorganisation",
        "colors": {
            "primary": "#17324D",
            "on_primary": "#FFFFFF",
            "background": "#F7F3EB",
            "text": "#1B1D20",
            "accent": "#D2693E",
        },
        "fonts": {"heading": "Arial", "body": "Arial"},
        "business_card": {
            "name": "Lukas Grüner",
            "role": "Familienorganisation",
            "organization": "FolderHome",
            "email": "lukas@example.invalid",
            "phone": "+49 000 000000",
            "website": "https://example.invalid",
        },
    }

    envelope = gateway.prepare(
        workflow_id="artifact-studio",
        profile_id="lukas",
        request=request,
    )

    assert envelope.domain_plan["contrast_checks_passed"] is True
    assert envelope.domain_plan["content_disclosed"] is False
    assert tuple(output_root.iterdir()) == ()
    assert "Lukas Grüner" not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T11:15:00+02:00",
    )

    assert (output_root / "folderhome-family.json").is_file()
    assert (output_root / "folderhome-family.css").is_file()
    assert (output_root / "folderhome-family.svg").is_file()
    assert report.domain_report["output_count"] == 3
    assert report.domain_report["visual_qa_passed"] is False
    assert report.domain_report["paths_disclosed"] is False


def test_contract_cockpit_adapter_writes_private_synthesis_after_approval(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "cockpit-state"
    output_root = tmp_path / "cockpit-output"
    source_root = tmp_path / "contracts"
    state_root.mkdir()
    output_root.mkdir()
    source_root.mkdir()
    source = source_root / "Hyundai-Versicherung.txt"
    source.write_text("Synthetischer Vertrag", encoding="utf-8")
    document = StubBundleExtractor().extract(source)
    catalog_entry = document.to_dict()
    catalog_entry.pop("text", None)
    (state_root / "folderhome-catalog.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.document-catalog.v1",
                "documents": [catalog_entry],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="cockpit_state",
                kind="directory",
                local_path=state_root,
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"contract_cockpit.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="cockpit_output",
                kind="directory",
                local_path=output_root,
                operations=frozenset({"create"}),
                purposes=frozenset({"contract_cockpit.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    gateway = WorkflowExecutionGateway(
        (
            ContractCockpitWorkflowAdapter(
                registry=registry,
                searcher=StubContractSearcher(source.name),
                extractor=StubBundleExtractor(),
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="contract-cockpit",
        profile_id="lukas",
        request={
            "state_resource_id": "cockpit_state",
            "output_resource_id": "cockpit_output",
            "output_basename": "Hyundai-Cockpit",
            "area": "versicherungen",
            "display_name": "Hyundai i10 Versicherung",
            "document_query": "Hyundai Versicherung",
            "object_ref": "Hyundai i10",
            "counterparty_terms": [],
            "calendar_terms": [],
            "account_refs": [],
            "coverage_start": "2026-01-01",
            "as_of": "2026-08-23",
            "archive_older_versions": True,
            "allow_sensitive_local_read": True,
        },
    )

    assert envelope.domain_plan["latest_document_found"] is True
    assert envelope.domain_plan["contract_status_proven"] is False
    assert envelope.domain_plan["content_disclosed"] is False
    assert "Hyundai i10" not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T11:30:00+02:00",
    )

    assert (output_root / "Hyundai-Cockpit.md").is_file()
    assert (output_root / "Hyundai-Cockpit.json").is_file()
    assert report.domain_report["contract_status_proven"] is False
    assert report.domain_report["automatic_archive_executed"] is False
    assert report.domain_report["paths_disclosed"] is False


def test_fcsa_adapter_runs_only_a_resource_bound_provider_dry_run_after_approval(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    scan_root = tmp_path / "inbox"
    target_root = tmp_path / "sorted"
    config_root.mkdir()
    scan_root.mkdir()
    target_root.mkdir()
    (scan_root / "Rechnung.txt").write_text("Rechnung", encoding="utf-8")
    (config_root / "config.json").write_text(
        json.dumps({"scan_paths": [str(scan_root)]}),
        encoding="utf-8",
    )
    (config_root / "categories-definitions.json").write_text(
        json.dumps(
            {
                "categories": [
                    {"id": "invoices", "default_target": str(target_root)}
                ]
            }
        ),
        encoding="utf-8",
    )
    (config_root / "action-rules.json").write_text("{}", encoding="utf-8")
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="fcsa_config",
                kind="directory",
                local_path=config_root,
                operations=frozenset({"read", "sensitive_read"}),
                purposes=frozenset({"fcsa.config"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="fcsa_scan",
                kind="directory",
                local_path=scan_root,
                operations=frozenset({"list", "read", "sensitive_read"}),
                purposes=frozenset({"fcsa.scan"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="fcsa_target",
                kind="directory",
                local_path=target_root,
                operations=frozenset({"create", "move"}),
                purposes=frozenset({"fcsa.target"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    plugin = next(
        item
        for item in load_manifests(REPOSITORY_ROOT / "manifests" / "components")
        if item.plugin_id == "file-collect-sort-action"
    )
    bridge = StubFcsaPlanBridge(scan_root)
    gateway = WorkflowExecutionGateway(
        (
            FcsaDryRunWorkflowAdapter(
                registry=registry,
                plugin=plugin,
                bridge=bridge,
            ),
        )
    )

    envelope = gateway.prepare(
        workflow_id="fcsa-dry-run",
        profile_id="lukas",
        request={
            "config_resource_id": "fcsa_config",
            "scan_resource_ids": ["fcsa_scan"],
            "target_resource_ids": ["fcsa_target"],
            "allow_sensitive_local_read": True,
        },
    )

    assert bridge.calls == 0
    assert envelope.domain_plan["dry_run"] is True
    assert envelope.domain_plan["live_execution_supported"] is False
    assert str(scan_root) not in str(envelope.to_dict())

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-23T11:45:00+02:00",
    )

    assert bridge.calls == 1
    assert (scan_root / "Rechnung.txt").is_file()
    assert tuple(target_root.iterdir()) == ()
    assert report.domain_report["planned_mutation_count"] == 1
    assert report.domain_report["filesystem_mutated"] is False
    assert report.domain_report["paths_disclosed"] is False


def test_document_action_plan_and_execution_adapters_share_profile_rules(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "single-source"
    target_root = tmp_path / "single-target"
    plan_output = tmp_path / "plan-output"
    state_root = tmp_path / "action-state"
    for root in (source_root, target_root, plan_output, state_root):
        root.mkdir()
    source_file = source_root / "A.txt"
    source_file.write_text("Einzeldokument", encoding="utf-8")
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="action_source",
                kind="file",
                local_path=source_file,
                operations=frozenset({"read", "sensitive_read", "move"}),
                purposes=frozenset({"document_action.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="minimized_with_approval",
            ),
            LogicalResource(
                resource_id="action_target",
                kind="directory",
                local_path=target_root,
                operations=frozenset({"create", "move"}),
                purposes=frozenset({"document_action.target"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="action_plan_output",
                kind="directory",
                local_path=plan_output,
                operations=frozenset({"create"}),
                purposes=frozenset({"document_action.plan_output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="action_state",
                kind="directory",
                local_path=state_root,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"document_action.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    profiles = load_profile_configuration(REPOSITORY_ROOT / "examples" / "profiles")
    gateway = WorkflowExecutionGateway(
        (
            DocumentActionPlanWorkflowAdapter(
                registry=registry,
                profiles=profiles,
                extractor=StubBundleExtractor(),
            ),
            DocumentActionExecutionWorkflowAdapter(
                registry=registry,
                profiles=profiles,
                extractor=StubBundleExtractor(),
            ),
        )
    )
    common = {
        "source_resource_id": "action_source",
        "target_resource_id": "action_target",
        "area": "dokumente",
        "as_of": "2026-08-23",
        "allow_sensitive_local_read": True,
    }

    plan_envelope = gateway.prepare(
        workflow_id="document-action-plan",
        profile_id="lukas",
        request={
            **common,
            "output_resource_id": "action_plan_output",
            "output_name": "A-plan.json",
        },
    )
    assert plan_envelope.domain_plan["executable_action_count"] == 1
    assert source_file.is_file()
    gateway.execute(
        envelope_id=plan_envelope.envelope_id,
        approved_at="2026-08-23T12:00:00+02:00",
    )
    assert (plan_output / "A-plan.json").is_file()
    assert source_file.is_file()

    execution_envelope = gateway.prepare(
        workflow_id="document-action-execution",
        profile_id="lukas",
        request={**common, "state_resource_id": "action_state"},
    )
    assert execution_envelope.domain_plan["executable_action_count"] == 1
    execution_report = gateway.execute(
        envelope_id=execution_envelope.envelope_id,
        approved_at="2026-08-23T12:01:00+02:00",
    )

    renamed = source_root / "Lukas_2026-08-23_A.txt"
    assert renamed.read_text(encoding="utf-8") == "Einzeldokument"
    assert not source_file.exists()
    assert execution_report.domain_report["executed_action_count"] == 1
    assert execution_report.domain_report["paths_disclosed"] is False


def test_folder_routine_and_queue_adapters_reuse_local_routine_core(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "routine-source"
    target_root = tmp_path / "routine-target"
    state_root = tmp_path / "routine-state"
    queue_source = tmp_path / "queue-source"
    queue_target = tmp_path / "queue-target"
    queue_state = tmp_path / "queue-state"
    queue_output = tmp_path / "queue-output"
    for path in (
        source_root,
        target_root,
        state_root,
        queue_source,
        queue_target,
        queue_state,
        queue_output,
    ):
        path.mkdir()
    source_file = source_root / "A.txt"
    source_file.write_text("Routine", encoding="utf-8")
    queue_file = queue_source / "B.txt"
    queue_file.write_text("Queue", encoding="utf-8")
    registry = ResourceRegistry(
        os_account="synthetic-family-account",
        resources=(
            LogicalResource(
                resource_id="routine_source",
                kind="directory",
                local_path=source_root,
                operations=frozenset({"list", "read", "sensitive_read", "move"}),
                purposes=frozenset({"folder_routine.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="routine_target",
                kind="directory",
                local_path=target_root,
                operations=frozenset({"create", "move"}),
                purposes=frozenset({"folder_routine.target"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="routine_state",
                kind="directory",
                local_path=state_root,
                operations=frozenset({"read", "state_write"}),
                purposes=frozenset({"folder_routine.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="queue_source",
                kind="directory",
                local_path=queue_source,
                operations=frozenset({"list", "read", "sensitive_read"}),
                purposes=frozenset({"routine_queue.source"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="queue_target",
                kind="directory",
                local_path=queue_target,
                operations=frozenset({"create", "move"}),
                purposes=frozenset({"routine_queue.target"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="queue_state",
                kind="directory",
                local_path=queue_state,
                operations=frozenset({"read"}),
                purposes=frozenset({"routine_queue.state"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
            LogicalResource(
                resource_id="queue_output",
                kind="directory",
                local_path=queue_output,
                operations=frozenset({"create"}),
                purposes=frozenset({"routine_queue.output"}),
                profile_ids=frozenset({"lukas"}),
                cloud_context="deny",
            ),
        ),
        profile_defaults={},
        known_profile_ids=frozenset({"lukas"}),
    )
    profiles = load_profile_configuration(REPOSITORY_ROOT / "examples" / "profiles")
    gateway = WorkflowExecutionGateway(
        (
            FolderRoutineWorkflowAdapter(
                registry=registry,
                profiles=profiles,
                extractor=StubBundleExtractor(),
            ),
            RoutineQueueWorkflowAdapter(
                registry=registry,
                profiles=profiles,
                extractor=StubBundleExtractor(),
            ),
        )
    )

    routine = gateway.prepare(
        workflow_id="folder-routine",
        profile_id="lukas",
        request={
            "source_resource_id": "routine_source",
            "target_resource_id": "routine_target",
            "state_resource_id": "routine_state",
            "watch_id": "routine_watch",
            "area": "dokumente",
            "as_of": "2026-08-23",
            "captured_at": "2026-08-23T08:00:00+02:00",
            "completed_at": "2026-08-23T08:01:00+02:00",
            "interval_minutes": 60,
            "recursive": True,
            "mode": "full",
            "allow_sensitive_local_read": True,
        },
    )
    assert routine.domain_plan["executable_document_count"] == 1
    assert source_file.is_file()
    assert tuple(state_root.iterdir()) == ()
    routine_report = gateway.execute(
        envelope_id=routine.envelope_id,
        approved_at="2026-08-23T08:00:30+02:00",
    )
    assert routine_report.domain_report["status"] == "executed"
    assert (source_root / "Lukas_2026-08-23_A.txt").is_file()

    queue = gateway.prepare(
        workflow_id="routine-queue",
        profile_id="lukas",
        request={
            "state_resource_id": "queue_state",
            "output_resource_id": "queue_output",
            "output_name": "queue.json",
            "as_of": "2026-08-23",
            "captured_at": "2026-08-23T09:00:00+02:00",
            "items": [
                {
                    "watch_id": "queue_watch",
                    "binding_id": "queue_binding",
                    "source_resource_id": "queue_source",
                    "target_resource_id": "queue_target",
                    "area": "dokumente",
                    "interval_minutes": 60,
                    "recursive": True,
                    "mode": "full",
                    "enabled": True,
                }
            ],
            "allow_sensitive_local_read": True,
        },
    )
    assert queue.domain_plan["ready_count"] == 1
    assert queue_file.is_file()
    assert tuple(queue_state.iterdir()) == ()
    queue_report = gateway.execute(
        envelope_id=queue.envelope_id,
        approved_at="2026-08-23T09:01:00+02:00",
    )
    assert queue_report.domain_report["scheduler_registered"] is False
    assert (queue_output / "queue.json").is_file()
    assert queue_file.is_file()


def test_medication_intake_adapter_reuses_existing_confirmation_workflow_once(
    tmp_path: Path,
) -> None:
    schedule_id = _seed_medication_schedule(tmp_path)
    gateway = _gateway(tmp_path)
    store = MedicationStore(tmp_path / "state")

    envelope = gateway.prepare(
        workflow_id="medication-intake",
        profile_id="lukas",
        request={
            "action": "confirm_taken",
            "schedule_id": schedule_id,
            "scheduled_date": "2026-08-22",
            "confirmed_at": "2026-08-22T08:05:00+02:00",
        },
    )

    assert envelope.domain_plan_schema == "folderhome.medication-intake-confirmation.v1"
    assert envelope.side_effects == ("state.medication_intake.append",)
    assert store.list_intake_events(profile_id="lukas") == ()

    report = gateway.execute(
        envelope_id=envelope.envelope_id,
        approved_at="2026-08-22T08:06:00+02:00",
    )

    assert report.domain_report_schema == "folderhome.medication-confirmation-report.v1"
    assert report.domain_report["status"] == "executed"
    assert "state_path" not in report.domain_report
    assert len(store.list_intake_events(profile_id="lukas")) == 1
    with pytest.raises(WorkflowExecutionError, match="bereits ausgeführt"):
        gateway.execute(
            envelope_id=envelope.envelope_id,
            approved_at="2026-08-22T08:07:00+02:00",
        )


def test_medication_intake_adapter_rejects_cross_profile_and_unknown_fields(
    tmp_path: Path,
) -> None:
    schedule_id = _seed_medication_schedule(tmp_path)
    gateway = _gateway(tmp_path)
    request = {
        "action": "confirm_taken",
        "schedule_id": schedule_id,
        "scheduled_date": "2026-08-22",
        "confirmed_at": "2026-08-22T08:05:00+02:00",
    }

    with pytest.raises(WorkflowExecutionError, match="anderen Profil"):
        gateway.prepare(
            workflow_id="medication-intake",
            profile_id="hanna",
            request=request,
        )
    with pytest.raises(WorkflowExecutionError, match="Unbekannte Felder"):
        gateway.prepare(
            workflow_id="medication-intake",
            profile_id="lukas",
            request={**request, "path": "C:/private"},
        )


def test_personal_note_adapter_is_not_connected_without_pinned_provider(
    tmp_path: Path,
) -> None:
    with pytest.raises(WorkflowExecutionError, match="llm-note"):
        PersonalNotesWorkflowAdapter(
            plugin=_plugin(),
            provider_root=tmp_path / "missing-llm-note",
            state_dir=tmp_path / "state",
            profile_ids=frozenset({"lukas"}),
        )
    assert not (tmp_path / "state").exists()
