"""Reproducible synthetic accident journey over real FolderHome adapters."""

from __future__ import annotations

import json
import threading
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.workflow_execution import (
    ContactRegisterWorkflowAdapter,
    ContractCockpitWorkflowAdapter,
    CorrespondenceWorkflowAdapter,
    LocalCalendarWorkflowAdapter,
    WorkflowExecutionGateway,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    LocalAppSettings,
    LogicalResource,
    PrivacyStatus,
    ResourceRegistry,
    build_document_id,
)
from folderhome.contracts.strands_agent import StrandsAgentSettings

_PROFILE_DIR = Path(__file__).resolve().parents[1] / "demo_data" / "profiles"
_OWNERSHIP_MARKER = ".folderhome-synthetic-demo-v1"
_OWNERSHIP_MARKER_CONTENT = "folderhome synthetic accident demo v1\n"

DEFAULT_ACCIDENT_PROMPT = (
    "I had an accident with my Hyundai i10. Find my current car insurance, "
    "compare it with older policies, identify the right contact, prepare a claim "
    "letter, and save the next follow-up locally."
)

_CURRENT_POLICY = """Synthetic demo document — no real person or policy.

Organisation: Example Mutual Insurance
Ansprechpartner: Jordan Current
Zuständig für: KFZ-Versicherung und Schadenmeldung
Vertragsobjekt: Hyundai i10
E-Mail: claims-2026@example.invalid
Telefon: +49 30 20260001
Gültig ab: 2026-01-01

Policy number: SYN-I10-2026
Coverage period: 2026-01-01 through 2026-12-31
Claims route: email the current claims desk and keep the police reference attached.
"""

_OLDER_POLICY = """Synthetic demo document — expired historical fixture.

Organisation: Example Mutual Insurance
Ansprechpartner: Jordan Former
Zuständig für: KFZ-Versicherung und Schadenmeldung
Vertragsobjekt: Hyundai i10
E-Mail: claims-2025@example.invalid
Telefon: +49 30 20250001
Gültig ab: 2025-01-01

Policy number: SYN-I10-2025
Coverage period: 2025-01-01 through 2025-12-31
Historical contact. Keep for evidence; do not use for a new claim.
"""

_ACCIDENT_NOTE = """Synthetic accident note — no real incident.

Vehicle: Hyundai i10
Incident date: 2026-08-22
Location: Example Street 7, Example City
Summary: Low-speed parking collision; no injuries reported in this fixture.
Police reference: SYN-POLICE-0822
"""

_FOLLOW_UP = """Termin: Review Hyundai i10 accident claim
Datum: 2026-08-26
Beginn: 10:00
Ende: 10:30
Ort: FolderHome local calendar
"""

_CALENDAR_CONFIG = {
    "schema": "folderhome.calendar-config.v1",
    "default_backend": "folderhome_local",
    "default_timezone": "Europe/Berlin",
    "uptoday_ics_directory": "unused",
}

_LETTER_REQUEST = {
    "schema": "folderhome.correspondence-request.v1",
    "profile_id": "lukas",
    "area": "versicherungen",
    "purpose": "schadensmeldung",
    "template_id": "insurance-claim",
    "created_on": "2026-08-23",
    "sender": {
        "name": "Lukas Example",
        "address_lines": ["Example Lane 1", "12345 Example City"],
        "email": "lukas@example.invalid",
        "phone": None,
    },
    "recipient": {
        "name": "Example Mutual Insurance",
        "address_lines": ["Insurance Square 2", "54321 Example City"],
        "email": "claims-2026@example.invalid",
        "phone": "+49 30 20260001",
    },
    "variables": {
        "policy_number": "SYN-I10-2026",
        "vehicle": "Hyundai i10",
        "incident_date": "2026-08-22",
        "police_reference": "SYN-POLICE-0822",
    },
    "attachments": ["Synthetic accident note", "Synthetic police reference"],
    "evidence_refs": [
        "doc_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ],
}

_LETTER_DESIGNS = {
    "schema": "folderhome.letter-designs.v1",
    "default_design_id": "folderhome-demo",
    "designs": [
        {
            "design_id": "folderhome-demo",
            "display_name": "FolderHome demo",
            "page_size": "A4",
            "margins_mm": [22, 18, 22, 18],
            "font_family": "Arial",
            "font_size_pt": 10.5,
            "accent_color": "#0284C7",
            "header_text": "FolderHome | Synthetic insurance demo",
            "footer_text": "Synthetic demo data — not sent",
        }
    ],
    "bindings": {
        "areas": {"versicherungen": "folderhome-demo"},
        "purposes": {"schadensmeldung": "folderhome-demo"},
        "profiles": {"lukas": "folderhome-demo"},
        "profile_purposes": {"lukas|schadensmeldung": "folderhome-demo"},
    },
}

_LETTER_TEMPLATES = {
    "schema": "folderhome.letter-templates.v1",
    "templates": [
        {
            "template_id": "insurance-claim",
            "display_name": "Report a vehicle claim",
            "purpose": "schadensmeldung",
            "subject": "Accident report for policy {policy_number}",
            "salutation": "Dear claims team,",
            "paragraphs": [
                "I am reporting the synthetic incident involving my {vehicle} on {incident_date}.",
                "The police reference for this demo is {police_reference}. Please "
                "confirm the next review step in writing.",
            ],
            "closing": "Kind regards",
        }
    ],
}

_RESULT_FILES = (
    "Hyundai-i10-claim-letter.md",
    "Hyundai-i10-claim-letter.txt",
    "Hyundai-i10-insurance-overview.json",
    "Hyundai-i10-insurance-overview.md",
)

_REQUESTS: tuple[tuple[str, str, str, dict[str, object]], ...] = (
    (
        "contact-register",
        "communication_expert",
        "methodical_operator",
        {
            "source_resource_id": "insurance_documents",
            "state_resource_id": "contact_state",
            "area": "versicherungen",
            "recursive": True,
            "allow_sensitive_local_read": False,
        },
    ),
    (
        "calendar-handoff",
        "communication_expert",
        "methodical_operator",
        {
            "source_resource_id": "follow_up_documents",
            "configuration_resource_id": "calendar_configuration",
            "state_resource_id": "local_calendar",
            "area": "versicherungen",
            "planned_at": "2026-08-23T12:00:00+02:00",
            "recursive": True,
            "allow_sensitive_local_read": False,
        },
    ),
    (
        "contract-cockpit",
        "finance_contract_expert",
        "careful_reviewer",
        {
            "state_resource_id": "cockpit_state",
            "output_resource_id": "demo_outputs",
            "output_basename": "Hyundai-i10-insurance-overview",
            "area": "versicherungen",
            "display_name": "Hyundai i10 insurance",
            "document_query": "Hyundai i10 insurance",
            "object_ref": "Hyundai i10",
            "counterparty_terms": [],
            "calendar_terms": ["Hyundai", "accident"],
            "account_refs": [],
            "coverage_start": "2026-01-01",
            "as_of": "2026-08-23",
            "archive_older_versions": True,
            "allow_sensitive_local_read": True,
        },
    ),
    (
        "correspondence-studio",
        "communication_expert",
        "clear_companion",
        {
            "request_resource_id": "letter_request",
            "designs_resource_id": "letter_designs",
            "templates_resource_id": "letter_templates",
            "output_resource_id": "demo_outputs",
            "output_basename": "Hyundai-i10-claim-letter",
        },
    ),
)


class SyntheticAccidentDemoError(RuntimeError):
    """Raised when the synthetic journey is stale, unsafe, or not confirmed."""


class _PlainTextExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        path = source_path.resolve()
        payload = path.read_bytes()
        source_hash = sha256(payload).hexdigest()
        year = "2025" if "2025" in path.name else "2026"
        return DocumentRecord(
            document_id=build_document_id(path, source_hash),
            source_path=path,
            filename=path.name,
            media_type="text/plain",
            source_sha256=source_hash,
            size_bytes=len(payload),
            modified_at=f"{year}-08-01T10:00:00+00:00",
            text=payload.decode("utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="folderhome-synthetic-demo",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetic demo data only.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


class _SyntheticInsuranceSearcher:
    def __init__(self, document_root: Path) -> None:
        self._document_root = document_root

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        folded = query.casefold()
        if not any(term in folded for term in ("hyundai", "insurance", "policy")):
            return ()
        hits = (
            KnowledgeDigestSearchHit(
                source="document",
                filename="KFZ_Hyundai_i10_2026.txt",
                file_type="txt",
                snippet=(
                    "Current synthetic Hyundai i10 policy, valid from 2026, with the "
                    "current claims contact."
                ),
                relevance=-2.0,
                word_count=64,
            ),
            KnowledgeDigestSearchHit(
                source="document",
                filename="KFZ_Hyundai_i10_2025.txt",
                file_type="txt",
                snippet=(
                    "Older synthetic Hyundai i10 policy, valid in 2025, retained for "
                    "evidence and archive planning."
                ),
                relevance=-1.0,
                word_count=61,
            ),
        )
        existing = tuple(
            hit for hit in hits if (self._document_root / hit.filename).is_file()
        )
        return existing[:limit]


class SyntheticAccidentDemo:
    """Own a bounded fixture workspace and one exact confirmation journey."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        agent_settings: StrandsAgentSettings | None = None,
        specialist_agent_settings: StrandsAgentSettings | None = None,
    ) -> None:
        root = workspace_root.resolve()
        if root == Path(root.anchor):
            raise SyntheticAccidentDemoError("Demo workspace may not be a filesystem root.")
        self.runtime_root = root / "synthetic-accident-demo"
        self._claim_runtime_root()
        self._lock = threading.RLock()
        self._prepared: dict[str, object] | None = None
        self._executed_plan_ids: set[str] = set()
        self._application: LocalApplication | None = None
        self._specialist_application: LocalApplication | None = None
        self.agent_settings = agent_settings or StrandsAgentSettings(
            model_provider="fixture",
            max_conversation_messages=64,
        )
        self.specialist_agent_settings = (
            specialist_agent_settings or self.agent_settings
        )
        self._seed_workspace()

    def _claim_runtime_root(self) -> None:
        if self.runtime_root.is_symlink():
            raise SyntheticAccidentDemoError("Demo runtime root may not be a symbolic link.")
        marker = self.runtime_root / _OWNERSHIP_MARKER
        if self.runtime_root.exists():
            if not self.runtime_root.is_dir():
                raise SyntheticAccidentDemoError("Demo runtime root is not a directory.")
            entries = tuple(self.runtime_root.iterdir())
            if entries and not marker.is_file():
                raise SyntheticAccidentDemoError(
                    "Existing demo runtime has no FolderHome ownership marker."
                )
        else:
            self.runtime_root.mkdir(parents=True)
        if marker.is_symlink():
            raise SyntheticAccidentDemoError("Demo ownership marker may not be a link.")
        if marker.exists():
            if marker.read_text(encoding="utf-8") != _OWNERSHIP_MARKER_CONTENT:
                raise SyntheticAccidentDemoError("Demo ownership marker is invalid.")
        else:
            marker.write_text(_OWNERSHIP_MARKER_CONTENT, encoding="utf-8")

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "schema": "folderhome.synthetic-accident-demo-status.v1",
                "runtime_status": "ready",
                "mode": f"synthetic_{self.agent_settings.model_provider}",
                "synthetic_demo_data": True,
                "network_used": False,
                "external_actions_enabled": False,
                "active_plan_id": (
                    self._prepared["plan_id"] if self._prepared is not None else None
                ),
                "generated_results": self._generated_results(),
            }

    def prepare(self, prompt: str = DEFAULT_ACCIDENT_PROMPT) -> dict[str, object]:
        normalized = " ".join(prompt.split())
        if not normalized or len(normalized) > 1_000:
            raise SyntheticAccidentDemoError("Demo prompt must contain 1 to 1000 characters.")
        with self._lock:
            if self._generated_results():
                raise SyntheticAccidentDemoError(
                    "Demo already has results; reset it before preparing another journey."
                )
            self._application = self._build_application(self.agent_settings)
            search = self._application.run_agent_chat(
                profile_id="lukas",
                message=normalized,
            )
            if [item.tool_name for item in search.tool_events] != [
                "search_home_documents"
            ]:
                raise SyntheticAccidentDemoError(
                    "The master agent did not perform the expected local document search."
                )
            steps = [
                {
                    "sequence": index,
                    "workflow_id": workflow_id,
                    "expert_id": expert_id,
                    "persona_id": persona_id,
                    "request_sha256": sha256(_canonical_json(request)).hexdigest(),
                    "confirmation_required": True,
                    "status": "planned",
                }
                for index, (workflow_id, expert_id, persona_id, request) in enumerate(
                    _REQUESTS,
                    start=1,
                )
            ]
            plan_material = {
                "schema": "folderhome.synthetic-accident-demo-plan.v1",
                "scenario_id": "hyundai-i10-accident",
                "prompt_sha256": sha256(normalized.encode("utf-8")).hexdigest(),
                "detected_documents": [
                    {
                        "filename": "KFZ_Hyundai_i10_2026.txt",
                        "classification": "current",
                    },
                    {
                        "filename": "KFZ_Hyundai_i10_2025.txt",
                        "classification": "older",
                    },
                ],
                "steps": steps,
                "network_used": search.network_used,
                "external_actions_performed": [],
            }
            plan_sha256 = sha256(_canonical_json(plan_material)).hexdigest()
            plan_id = f"accident_demo_{plan_sha256[:32]}"
            prepared = {
                **plan_material,
                "plan_id": plan_id,
                "plan_sha256": plan_sha256,
                "status": "confirmation_required",
                "prompt": normalized,
                "confirmation_command": f"/confirm {plan_id}",
                "agent_search": search.to_dict(),
            }
            self._prepared = prepared
            return _copy_json(prepared)

    def confirm(self, command: str) -> dict[str, object]:
        with self._lock:
            parts = command.split()
            if len(parts) != 2 or parts[0] != "/confirm":
                raise SyntheticAccidentDemoError(
                    "Use exactly /confirm <plan_id>; conversation text is not approval."
                )
            plan_id = parts[1]
            if self._prepared is None or self._prepared["plan_id"] != plan_id:
                raise SyntheticAccidentDemoError("The confirmed plan is unknown or stale.")
            if plan_id in self._executed_plan_ids:
                raise SyntheticAccidentDemoError("This plan was already executed.")
            application = self._application
            if application is None:
                raise SyntheticAccidentDemoError("The prepared demo runtime is unavailable.")
            if self.specialist_agent_settings is self.agent_settings:
                specialist_application = application
            else:
                if self._specialist_application is None:
                    self._specialist_application = self._build_application(
                        self.specialist_agent_settings
                    )
                specialist_application = self._specialist_application
            executions = []
            local_actions = []
            for workflow_id, expert_id, persona_id, request in _REQUESTS:
                specialist_request = {
                    "schema": "folderhome.fixture-specialist-request.v1",
                    "expert_id": expert_id,
                    "workflow_id": workflow_id,
                    "persona_id": persona_id,
                    "language": "en",
                    "request": request,
                }
                report = specialist_application.run_agent_chat(
                    profile_id="lukas",
                    message=json.dumps(
                        specialist_request,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                )
                if len(report.proposed_plans) != 1:
                    raise SyntheticAccidentDemoError(
                        f"The specialist did not return one plan for {workflow_id}."
                    )
                plan = report.proposed_plans[0]
                confirmation = specialist_application.confirm_agent_plan(
                    plan_id=plan.plan_id,
                    plan_sha256=plan.plan_sha256,
                    step_ids=tuple(
                        step.step_id
                        for step in plan.steps
                        if step.confirmation_required
                    ),
                )
                if not confirmation["execution_performed"]:
                    raise SyntheticAccidentDemoError(
                        f"The confirmed workflow did not execute: {workflow_id}."
                    )
                local_actions.extend(confirmation["side_effects"])
                executions.append(
                    {
                        "workflow_id": workflow_id,
                        "agent": report.to_dict(),
                        "confirmation": confirmation,
                    }
                )
            self._executed_plan_ids.add(plan_id)
            result = {
                "schema": "folderhome.synthetic-accident-demo-result.v1",
                "status": "executed",
                "scenario_id": "hyundai-i10-accident",
                "plan_id": plan_id,
                "plan_sha256": self._prepared["plan_sha256"],
                "synthetic_demo_data": True,
                "network_used": bool(self._prepared["network_used"])
                or any(item["agent"]["network_used"] for item in executions),
                "external_actions_performed": [],
                "local_actions_performed": list(dict.fromkeys(local_actions)),
                "archive_action_performed": False,
                "mail_sent": False,
                "external_calendar_used": False,
                "phone_call_made": False,
                "executions": executions,
                "generated_results": self._generated_results(),
            }
            return _copy_json(result)

    def reset(self) -> dict[str, object]:
        """Remove only demo-owned outputs and state files, then restore fixtures."""

        with self._lock:
            owned_files = [self.runtime_root / "outputs" / name for name in _RESULT_FILES]
            for relative in (
                Path("state/contacts/contacts.sqlite3"),
                Path("state/contacts/contacts.sqlite3-wal"),
                Path("state/contacts/contacts.sqlite3-shm"),
                Path("state/calendar/calendar.sqlite3"),
                Path("state/calendar/calendar.sqlite3-wal"),
                Path("state/calendar/calendar.sqlite3-shm"),
            ):
                owned_files.append(self.runtime_root / relative)
            for path in owned_files:
                if path.is_symlink():
                    raise SyntheticAccidentDemoError(
                        "Demo reset blocked a symbolic link in an owned output slot."
                    )
                if path.is_file():
                    path.unlink()
            self._prepared = None
            self._executed_plan_ids.clear()
            self._application = None
            self._specialist_application = None
            self._seed_workspace()
            return {
                "schema": "folderhome.synthetic-accident-demo-reset.v1",
                "status": "reset",
                "synthetic_demo_data": True,
                "generated_results": [],
            }

    def result_file(self, filename: str) -> Path:
        if filename not in _RESULT_FILES:
            raise SyntheticAccidentDemoError("Unknown demo result file.")
        path = self.runtime_root / "outputs" / filename
        if path.is_symlink() or not path.is_file():
            raise SyntheticAccidentDemoError("Demo result is not available.")
        return path

    def _seed_workspace(self) -> None:
        documents = self.runtime_root / "documents"
        follow_up = self.runtime_root / "follow-up"
        correspondence = self.runtime_root / "correspondence"
        state = self.runtime_root / "state"
        outputs = self.runtime_root / "outputs"
        for path in (documents, follow_up, correspondence, state, outputs):
            path.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                raise SyntheticAccidentDemoError("Demo workspace contains a symbolic link.")
        fixtures: dict[Path, str] = {
            documents / "KFZ_Hyundai_i10_2026.txt": _CURRENT_POLICY,
            documents / "KFZ_Hyundai_i10_2025.txt": _OLDER_POLICY,
            documents / "Accident-note-2026-08-22.txt": _ACCIDENT_NOTE,
            follow_up / "Claim-follow-up.txt": _FOLLOW_UP,
            self.runtime_root / "calendar.json": _pretty_json(_CALENDAR_CONFIG),
            correspondence / "claim-request.json": _pretty_json(_LETTER_REQUEST),
            correspondence / "designs.json": _pretty_json(_LETTER_DESIGNS),
            correspondence / "templates.json": _pretty_json(_LETTER_TEMPLATES),
        }
        for path, content in fixtures.items():
            if path.is_symlink():
                raise SyntheticAccidentDemoError("Demo fixture slot is a symbolic link.")
            path.write_text(content, encoding="utf-8")
        extractor = _PlainTextExtractor()
        catalog_entries = []
        for name in ("KFZ_Hyundai_i10_2026.txt", "KFZ_Hyundai_i10_2025.txt"):
            entry = extractor.extract(documents / name).to_dict()
            entry.pop("text", None)
            catalog_entries.append(entry)
        (state / "folderhome-catalog.json").write_text(
            _pretty_json(
                {
                    "schema": "folderhome.document-catalog.v1",
                    "documents": catalog_entries,
                }
            ),
            encoding="utf-8",
        )

    def _build_application(
        self,
        agent_settings: StrandsAgentSettings,
    ) -> LocalApplication:
        profiles = load_profile_configuration(_PROFILE_DIR)
        profile_ids = frozenset(item.profile_id for item in profiles.profiles)
        documents = self.runtime_root / "documents"
        follow_up = self.runtime_root / "follow-up"
        correspondence = self.runtime_root / "correspondence"
        state = self.runtime_root / "state"
        outputs = self.runtime_root / "outputs"
        registry = ResourceRegistry(
            os_account=profiles.os_account,
            resources=(
                LogicalResource(
                    "insurance_documents",
                    "directory",
                    documents,
                    frozenset({"list", "read"}),
                    frozenset({"contacts.source"}),
                    frozenset({"lukas"}),
                    "synthetic_only",
                ),
                LogicalResource(
                    "follow_up_documents",
                    "directory",
                    follow_up,
                    frozenset({"list", "read"}),
                    frozenset({"calendar.source"}),
                    frozenset({"lukas"}),
                    "synthetic_only",
                ),
                LogicalResource(
                    "contact_state",
                    "directory",
                    state,
                    frozenset({"read", "state_write"}),
                    frozenset({"contacts.state"}),
                    frozenset({"lukas"}),
                    "deny",
                ),
                LogicalResource(
                    "local_calendar",
                    "local_calendar",
                    state,
                    frozenset({"read", "state_write"}),
                    frozenset({"calendar.state"}),
                    frozenset({"lukas"}),
                    "deny",
                ),
                LogicalResource(
                    "calendar_configuration",
                    "file",
                    self.runtime_root / "calendar.json",
                    frozenset({"read"}),
                    frozenset({"calendar.configuration"}),
                    frozenset({"lukas"}),
                    "deny",
                ),
                LogicalResource(
                    "cockpit_state",
                    "directory",
                    state,
                    frozenset({"read", "sensitive_read"}),
                    frozenset({"contract_cockpit.state"}),
                    frozenset({"lukas"}),
                    "synthetic_only",
                ),
                LogicalResource(
                    "demo_outputs",
                    "directory",
                    outputs,
                    frozenset({"create"}),
                    frozenset(
                        {"contract_cockpit.output", "correspondence.output"}
                    ),
                    frozenset({"lukas"}),
                    "deny",
                ),
                LogicalResource(
                    "letter_request",
                    "file",
                    correspondence / "claim-request.json",
                    frozenset({"read"}),
                    frozenset({"correspondence.request"}),
                    frozenset({"lukas"}),
                    "deny",
                ),
                LogicalResource(
                    "letter_designs",
                    "file",
                    correspondence / "designs.json",
                    frozenset({"read"}),
                    frozenset({"correspondence.designs"}),
                    frozenset({"lukas"}),
                    "deny",
                ),
                LogicalResource(
                    "letter_templates",
                    "file",
                    correspondence / "templates.json",
                    frozenset({"read"}),
                    frozenset({"correspondence.templates"}),
                    frozenset({"lukas"}),
                    "deny",
                ),
            ),
            profile_defaults={},
            known_profile_ids=profile_ids,
        )
        extractor = _PlainTextExtractor()
        searcher = _SyntheticInsuranceSearcher(documents)
        gateway = WorkflowExecutionGateway(
            (
                ContactRegisterWorkflowAdapter(registry=registry, extractor=extractor),
                LocalCalendarWorkflowAdapter(
                    registry=registry,
                    profiles=profiles,
                    extractor=extractor,
                ),
                ContractCockpitWorkflowAdapter(
                    registry=registry,
                    searcher=searcher,
                    extractor=extractor,
                    expected_state_root=state,
                ),
                CorrespondenceWorkflowAdapter(
                    registry=registry,
                    report_forge_revision="0123456789abcdef0123456789abcdef01234567",
                    report_forge_distribution_version="1.1.4",
                    report_forge_runtime_version="1.1.0",
                ),
            )
        )
        return LocalApplication(
            settings=LocalAppSettings(
                host="127.0.0.1",
                port=8767,
                profiles_dir=_PROFILE_DIR,
                state_dir=state,
                max_query_limit=10,
            ),
            profiles=profiles,
            searcher=searcher,
            session_token="folderhome-synthetic-accident-demo-session-token",
            agent_settings=agent_settings,
            workflow_executor=gateway,
            resource_registry=registry,
        )

    def _generated_results(self) -> list[dict[str, object]]:
        results = []
        for filename in _RESULT_FILES:
            path = self.runtime_root / "outputs" / filename
            if path.is_file() and not path.is_symlink():
                payload = path.read_bytes()
                result_url = f"/demo/results/{quote(filename, safe='')}"
                results.append(
                    {
                        "filename": filename,
                        "sha256": sha256(payload).hexdigest(),
                        "size_bytes": len(payload),
                        "view_url": result_url,
                        "download_url": f"{result_url}?download=1",
                    }
                )
        return results


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _pretty_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _copy_json(payload: dict[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(payload, ensure_ascii=False))


__all__ = [
    "DEFAULT_ACCIDENT_PROMPT",
    "SyntheticAccidentDemo",
    "SyntheticAccidentDemoError",
]
