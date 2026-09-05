import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

import pytest

from folderhome.application.medication_intake import (
    apply_medication_import_plan,
    build_medication_import_plan,
)
from folderhome.capabilities.calendar_store import CalendarStore
from folderhome.capabilities.medication_store import MedicationStore
from folderhome.contracts import (
    AdministrativeDraftApproval,
    FolderMedicationPlanAnalysis,
    MedicationEvidence,
    MedicationImportApproval,
    MedicationPlanAnalysisItem,
    MedicationScheduleCandidate,
)

REPO_ROOT = Path(__file__).parents[1]
FCSA_ROOT = REPO_ROOT.parent / "file-collect-sort-action"
DOC_SERVICES_ROOT = REPO_ROOT.parent / "doc-services"
KNOWLEDGE_DIGEST_ROOT = REPO_ROOT.parent / "KnowledgeDigest"
LLM_NOTE_ROOT = REPO_ROOT.parent / "llm-note"
TAX_ASSISTANT_ROOT = REPO_ROOT.parent / "steuer-assistent"
LAW_CHECKER_ROOT = REPO_ROOT.parent / "law-checker"


def run_cli(
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "folderhome", *args],
        cwd=REPO_ROOT,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _seed_cli_medication_schedule(tmp_path: Path, state_dir: Path) -> str:
    source_root = tmp_path / "medication-source"
    source_root.mkdir()
    source = source_root / "DemoMed.txt"
    source.write_text("Synthetischer Medikamentenplan.\n", encoding="utf-8")
    candidate = MedicationScheduleCandidate(
        schedule_id=f"medication_schedule_{sha256(b'cli-schedule').hexdigest()}",
        schedule_key=f"medication_schedule_key_{sha256(b'cli-key').hexdigest()}",
        profile_id="lukas",
        medication_name="DemoMed",
        dose_quantity_milli=1000,
        dose_unit="Tablette",
        scheduled_time="08:00",
        timezone="Europe/Berlin",
        weekdays=(5,),
        valid_from="2026-08-22",
        valid_to="2026-12-31",
        inventory_item_id=f"inventory_item_{sha256(b'cli-inventory').hexdigest()}",
        source_document_id=f"doc_{sha256(b'cli-document').hexdigest()}",
        source_sha256=sha256(source.read_bytes()).hexdigest(),
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
    store = MedicationStore(state_dir)
    plan = build_medication_import_plan(analysis, store=store)
    approval = MedicationImportApproval(
        approval_id="seed_cli_medication",
        plan_id=plan.plan_id,
        medication_revision=plan.medication_revision,
        action_ids=(plan.actions[0].action_id,),
        approved_at="2026-08-22T07:00:00+02:00",
    )
    apply_medication_import_plan(plan, approval, store=store, allow_state_write=True)
    return candidate.schedule_id


def test_plugins_validate_reports_all_pinned_manifests_as_json() -> None:
    result = run_cli("plugins", "validate", "--json")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "valid": True,
        "plugins": [
            "doc-services",
            "file-collect-sort-action",
            "hungrycall",
            "KnowledgeDigest",
            "law-checker",
            "llm-note",
            "ringedingeding",
            "steuer-assistent",
        ],
    }


@pytest.mark.skipif(
    not TAX_ASSISTANT_ROOT.is_dir(),
    reason="pinned steuer-assistent checkout unavailable",
)
def test_tax_provider_cli_reports_private_local_boundary() -> None:
    result = run_cli(
        "tax",
        "providers",
        "--provider-root",
        str(TAX_ASSISTANT_ROOT),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["provider"]["status"] == "ready"
    assert payload["provider"]["network_required"] is False
    assert payload["tax_advice"] is False
    assert payload["official_format"] is False
    assert payload["portal_submission_supported"] is False


@pytest.mark.skipif(
    not TAX_ASSISTANT_ROOT.is_dir(),
    reason="pinned steuer-assistent checkout unavailable",
)
def test_tax_receipt_cli_plan_binds_catalog_evidence_without_tax_write(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Arbeitsmittel.txt"
    source.write_text("Synthetischer Beleg über 49,90 EUR.", encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    document_id = "doc_" + "a" * 64
    (state_dir / "folderhome-catalog.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.document-catalog.v1",
                "documents": [
                    {
                        "document_id": document_id,
                        "source_path": str(source),
                        "relative_path": source.name,
                        "filename": source.name,
                        "media_type": "text/plain",
                        "source_sha256": sha256(source.read_bytes()).hexdigest(),
                        "source_size": source.stat().st_size,
                        "modified_at": "2026-08-22T06:00:00+02:00",
                        "extractor": "synthetic-test",
                        "extractor_version": "1",
                        "index_status": "indexed",
                        "privacy_status": "review_required",
                        "warnings": [],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    request_file = tmp_path / "tax-request.json"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.tax-receipt-request.v1",
                "request_id": "tax-receipt-cli",
                "profile_id": "lukas",
                "tax_year": 2026,
                "receipt_date": "2026-03-15",
                "amount_cents": 4990,
                "document_id": document_id,
                "finance_transaction_id": None,
                "category_candidate": "Arbeitsmittel",
                "confirmed_category": "Arbeitsmittel",
                "note": "Synthetischer CLI-Fall",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "tax",
        "receipt-plan",
        "--request-file",
        str(request_file),
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--provider-root",
        str(TAX_ASSISTANT_ROOT),
        "--approve-sensitive-local-read",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready_for_approval"
    assert payload["document_sha256"] == sha256(source.read_bytes()).hexdigest()
    assert payload["tax_advice"] is False
    assert payload["portal_submission_supported"] is False
    assert not (state_dir / "tax-workpaper").exists()


def test_briefing_cli_plans_renders_and_delivers_with_separate_gates(
    tmp_path: Path,
) -> None:
    output_file = tmp_path / "Ausgabe" / "Morgenbrief.html"
    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    desktop_file = desktop_dir / "Morgenbrief.html"
    common = (
        "--request-file",
        str(REPO_ROOT / "examples" / "briefing" / "briefing-request.json"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--output-file",
        str(output_file),
        "--desktop-file",
        str(desktop_file),
        "--approve-sensitive-local-read",
        "--json",
    )

    providers = run_cli("briefing", "providers", "--json")
    assert providers.returncode == 0, providers.stderr
    provider_payload = json.loads(providers.stdout)
    assert provider_payload["snapshot_inputs"]["status"] == "ready"
    assert provider_payload["live_weather_connector"]["status"] == (
        "blocked_not_implemented"
    )
    assert provider_payload["network_invoked"] is False

    planned = run_cli("briefing", "plan", *common)
    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    assert plan["status"] == "ready_for_approval"
    assert not output_file.exists()
    assert not desktop_file.exists()

    render_approval = tmp_path / "render-approval.json"
    render_approval.write_text(
        json.dumps(
            {
                "schema": "folderhome.briefing-render-approval.v1",
                "approval_id": "briefing-render-approval",
                "plan_id": plan["plan_id"],
                "plan_sha256": plan["plan_sha256"],
                "html_sha256": plan["html_sha256"],
                "output_path": str(output_file),
                "approved_at": "2026-08-22T06:01:00+02:00",
                "allow_output_write": True,
            }
        ),
        encoding="utf-8",
    )
    rendered = run_cli(
        "briefing",
        "render",
        *common,
        "--approval-file",
        str(render_approval),
        "--approve-output-write",
    )
    assert rendered.returncode == 0, rendered.stderr
    assert output_file.is_file()
    assert not desktop_file.exists()

    delivery_approval = tmp_path / "delivery-approval.json"
    delivery_approval.write_text(
        json.dumps(
            {
                "schema": "folderhome.briefing-delivery-approval.v1",
                "approval_id": "briefing-delivery-approval",
                "plan_id": plan["plan_id"],
                "plan_sha256": plan["plan_sha256"],
                "html_sha256": plan["html_sha256"],
                "desktop_path": str(desktop_file),
                "approved_at": "2026-08-22T06:02:00+02:00",
                "allow_desktop_write": True,
            }
        ),
        encoding="utf-8",
    )
    delivered = run_cli(
        "briefing",
        "deliver",
        *common,
        "--approval-file",
        str(delivery_approval),
        "--approve-desktop-write",
    )

    assert delivered.returncode == 0, delivered.stderr
    delivery = json.loads(delivered.stdout)
    assert delivery["desktop_written"] is True
    assert delivery["scheduler_registered"] is False
    assert desktop_file.read_bytes() == output_file.read_bytes()


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_notice_cli_inspects_and_renders_without_legal_review(
    tmp_path: Path,
) -> None:
    common = (
        "--source-file",
        str(REPO_ROOT / "examples" / "notices" / "Bescheid.txt"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--received-on",
        "2026-08-15",
        "--as-of",
        "2026-08-22T06:00:00+02:00",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--approve-sensitive-local-read",
        "--json",
    )

    providers = run_cli(
        "notices",
        "providers",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--json",
    )
    assert providers.returncode == 0, providers.stderr
    provider_payload = json.loads(providers.stdout)
    assert provider_payload["document_extraction"]["status"] == "ready"
    assert provider_payload["legal_review"]["status"] == "blocked_not_integrated"

    inspected = run_cli("notices", "inspect", *common)
    assert inspected.returncode == 0, inspected.stderr
    analysis = json.loads(inspected.stdout)
    assert analysis["notice_type"] == "Ablehnungsbescheid"
    assert analysis["explicit_deadline_date"] == "2026-09-15"
    assert analysis["deadline_legally_calculated"] is False
    assert analysis["legal_review_status"] == "not_performed"
    assert analysis["external_actions"] == []

    markdown_file = tmp_path / "Bescheidbericht.md"
    json_file = tmp_path / "Bescheidbericht.json"
    rendered = run_cli(
        "notices",
        "render",
        *common,
        "--markdown-file",
        str(markdown_file),
        "--json-file",
        str(json_file),
        "--approve-output-write",
    )

    assert rendered.returncode == 0, rendered.stderr
    assert markdown_file.is_file()
    assert json_file.is_file()
    assert "Keine Rechtsprüfung durchgeführt" in markdown_file.read_text(encoding="utf-8")


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_administrative_draft_cli_previews_and_writes_without_sending(
    tmp_path: Path,
) -> None:
    common = (
        "--request-file",
        str(REPO_ROOT / "examples" / "notices" / "objection-draft-request.json"),
        "--source-file",
        str(REPO_ROOT / "examples" / "notices" / "Bescheid.txt"),
        "--designs-file",
        str(REPO_ROOT / "examples" / "correspondence" / "designs.json"),
        "--templates-file",
        str(REPO_ROOT / "examples" / "notices" / "administrative-templates.json"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--received-on",
        "2026-08-15",
        "--as-of",
        "2026-08-22T06:00:00+02:00",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--approve-sensitive-local-read",
        "--json",
    )
    previewed = run_cli("drafts", "preview", *common)
    assert previewed.returncode == 0, previewed.stderr
    plan = json.loads(previewed.stdout)
    assert plan["status"] == "review_required"
    assert plan["legal_review_status"] == "not_performed"
    assert plan["send_supported"] is False
    assert "ENTWURF" in plan["correspondence_preview"]["markdown"]

    correspondence = plan["correspondence_preview"]
    approval = AdministrativeDraftApproval.create(
        plan_id=plan["plan_id"],
        markdown_sha256=correspondence["markdown_sha256"],
        text_sha256=correspondence["text_sha256"],
        approved_at="2026-08-22T06:30:00+02:00",
        confirmed_content_review=True,
        confirmed_no_legal_review=True,
        allow_local_output_write=True,
    )
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(
        json.dumps(approval.to_dict(), ensure_ascii=False),
        encoding="utf-8",
    )
    markdown_file = tmp_path / "Widerspruchsentwurf.md"
    text_file = tmp_path / "Widerspruchsentwurf.txt"
    rendered = run_cli(
        "drafts",
        "render",
        *common,
        "--approval-file",
        str(approval_file),
        "--markdown-file",
        str(markdown_file),
        "--text-file",
        str(text_file),
        "--approve-output-write",
    )

    assert rendered.returncode == 0, rendered.stderr
    report = json.loads(rendered.stdout)
    assert report["sent"] is False
    assert report["external_actions_performed"] is False
    assert "nicht rechtlich geprüft" in markdown_file.read_text(encoding="utf-8")


def test_benefit_screening_cli_routes_only_to_official_prechecks(tmp_path: Path) -> None:
    common = (
        "--profile-facts-file",
        str(REPO_ROOT / "examples" / "benefits" / "Lukas-benefit-profile.json"),
        "--catalog-file",
        str(REPO_ROOT / "examples" / "benefits" / "official-routing-catalog.json"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--as-of",
        "2026-08-22T07:00:00+02:00",
        "--max-source-age-days",
        "30",
        "--approve-sensitive-local-read",
        "--json",
    )
    checked = run_cli("benefits", "check", *common)
    assert checked.returncode == 0, checked.stderr
    report = json.loads(checked.stdout)
    assert report["catalog_complete"] is False
    assert report["eligibility_assessed"] is False
    assert report["amount_estimated"] is False
    assert report["network_used"] is False
    assert {item["status"] for item in report["results"]} == {
        "official_handoff_recommended"
    }
    assert all(
        item["official_precheck_url"].startswith("https://")
        for item in report["results"]
    )

    markdown_file = tmp_path / "Leistungsvorcheck.md"
    json_file = tmp_path / "Leistungsvorcheck.json"
    rendered = run_cli(
        "benefits",
        "render",
        *common,
        "--markdown-file",
        str(markdown_file),
        "--json-file",
        str(json_file),
        "--approve-output-write",
    )
    assert rendered.returncode == 0, rendered.stderr
    assert "Keine Leistungsberechtigung geprüft" in markdown_file.read_text(
        encoding="utf-8"
    )
    output = json.loads(rendered.stdout)
    assert output["external_actions_performed"] is False


@pytest.mark.skipif(
    not LAW_CHECKER_ROOT.is_dir(),
    reason="pinned law-checker checkout unavailable",
)
def test_legal_monitor_cli_qualifies_provider_compares_and_renders(tmp_path: Path) -> None:
    def write_snapshot(name: str, text: str, checked_at: str, source_date: str) -> Path:
        path = tmp_path / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "folderhome.legal-source-snapshot.v1",
                    "law_id": "synthetic-social-law",
                    "law_title": "Synthetisches Sozialgesetz",
                    "law_checker_registry_key": None,
                    "publication_stage": "consolidated_current",
                    "publisher": "Teststelle",
                    "official_url": "https://example.invalid/synthetic-law",
                    "checked_at": checked_at,
                    "source_date": source_date,
                    "authoritative": False,
                    "fixture_only": True,
                    "complete": False,
                    "coverage_statement": "Nur der Testabschnitt ist erfasst.",
                    "provisions": [
                        {
                            "provision_id": "section-demo",
                            "heading": "Synthetischer Testabschnitt",
                            "text": text,
                            "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
                            "topics": ["krankenversicherung"],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    before = write_snapshot(
        "before",
        "Alter Testwortlaut.",
        "2026-08-21T07:30:00+02:00",
        "2026-08-21",
    )
    after = write_snapshot(
        "after",
        "Neuer Testwortlaut.",
        "2026-08-22T07:30:00+02:00",
        "2026-08-22",
    )
    interests = tmp_path / "interests.json"
    interests.write_text(
        json.dumps(
            {
                "schema": "folderhome.legal-interest-snapshot.v1",
                "profile_id": "lukas",
                "provided_on": "2026-08-22",
                "interests": [
                    {
                        "interest_id": "health-profile",
                        "subject_kind": "profile",
                        "subject_ref": "lukas",
                        "topics": ["krankenversicherung"],
                        "basis": "user_provided",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    providers = run_cli(
        "legal",
        "providers",
        "--law-checker-root",
        str(LAW_CHECKER_ROOT),
        "--json",
    )
    assert providers.returncode == 0, providers.stderr
    qualification = json.loads(providers.stdout)
    assert qualification["legal_review_api_available"] is False
    assert qualification["network_invoked"] is False

    common = (
        "--before-file",
        str(before),
        "--after-file",
        str(after),
        "--interests-file",
        str(interests),
        "--as-of",
        "2026-08-22T08:00:00+02:00",
        "--max-source-age-days",
        "7",
        "--law-checker-root",
        str(LAW_CHECKER_ROOT),
        "--approve-sensitive-local-read",
        "--allow-test-fixture",
        "--json",
    )
    compared = run_cli("legal", "compare", *common)
    assert compared.returncode == 0, compared.stderr
    report = json.loads(compared.stdout)
    assert report["status"] == "review_required"
    assert report["law_checker"]["provider_revision"] == (
        "a5b0cd51bc3666962f2fae8017c855dea0a712a2"
    )
    assert report["candidates"][0]["affected_determined"] is False
    assert report["network_used"] is False

    markdown_file = tmp_path / "Rechtsaenderungen.md"
    json_file = tmp_path / "Rechtsaenderungen.json"
    rendered = run_cli(
        "legal",
        "render",
        *common,
        "--markdown-file",
        str(markdown_file),
        "--json-file",
        str(json_file),
        "--approve-output-write",
    )
    assert rendered.returncode == 0, rendered.stderr
    assert "Keine Rechtswirkung geprüft" in markdown_file.read_text(encoding="utf-8")
    assert json.loads(rendered.stdout)["external_actions_performed"] is False


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_local_app_cli_plans_loopback_surface_without_starting_server(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    documents = tmp_path / "documents"
    documents.mkdir()
    password_file = tmp_path / "mailbox-password.txt"
    password_file.write_text("synthetisches-postfach-geheimnis", encoding="utf-8")
    mail_account_file = tmp_path / "mail-draft-account.json"
    mail_account_file.write_text(
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
                "keyring_service": None,
                "keyring_user": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    resources_file = tmp_path / "resources.json"
    resources_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.resource-registry.v1",
                "os_account": "synthetic-family-account",
                "resources": [
                    {
                        "resource_id": "documents_source",
                        "kind": "directory",
                        "locator": {"type": "local_path", "path": str(documents)},
                        "operations": ["list", "read"],
                        "purposes": ["documents.source"],
                        "profile_ids": ["lukas"],
                        "cloud_context": "minimized_with_approval",
                    },
                    {
                        "resource_id": "mail_draft_account",
                        "kind": "file",
                        "locator": {
                            "type": "local_path",
                            "path": str(mail_account_file),
                        },
                        "operations": ["read"],
                        "purposes": ["mail.draft_account"],
                        "profile_ids": ["lukas"],
                        "cloud_context": "deny",
                    },
                ],
                "profile_defaults": {
                    "lukas": {
                        "documents.source": "documents_source",
                        "mail.draft_account": "mail_draft_account",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    planned = run_cli(
        "app",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--resources-file",
        str(resources_file),
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["security_boundary"] == "operating_system_account"
    assert payload["profiles_are_authorization_boundaries"] is False
    assert payload["settings"]["network_scope"] == "loopback_only"
    assert payload["session_token_generated"] is True
    assert payload["session_token_disclosed_in_plan"] is False
    assert payload["server_started"] is False
    assert payload["shell_execution_available"] is False
    assert payload["logical_resources_configured"] is True
    assert payload["agent"]["executor_coverage"]["connected"] == 27
    assert payload["agent"]["executor_coverage"]["not_connected"] == 2
    assert str(documents) not in planned.stdout
    assert str(password_file) not in planned.stdout
    assert "synthetisches-postfach-geheimnis" not in planned.stdout
    assert "imap.example.invalid" not in planned.stdout

    blocked = run_cli(
        "app",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--resources-file",
        str(resources_file),
        "--host",
        "0.0.0.0",
        "--json",
    )
    assert blocked.returncode == 2
    assert "127.0.0.1" in json.loads(blocked.stdout)["error"]


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_mail_connector_stays_not_connected_without_a_configured_mailbox(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    documents = tmp_path / "documents"
    documents.mkdir()
    resources_file = tmp_path / "resources.json"
    resources_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.resource-registry.v1",
                "os_account": "synthetic-family-account",
                "resources": [
                    {
                        "resource_id": "documents_source",
                        "kind": "directory",
                        "locator": {"type": "local_path", "path": str(documents)},
                        "operations": ["list", "read"],
                        "purposes": ["documents.source"],
                        "profile_ids": ["lukas"],
                        "cloud_context": "minimized_with_approval",
                    }
                ],
                "profile_defaults": {
                    "lukas": {"documents.source": "documents_source"}
                },
            }
        ),
        encoding="utf-8",
    )

    planned = run_cli(
        "app",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--resources-file",
        str(resources_file),
        "--approve-mail-draft",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["agent"]["executor_coverage"]["connected"] == 26
    assert payload["agent"]["executor_coverage"]["not_connected"] == 3


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_strands_agent_cli_plans_bounded_fixture_without_model_call(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    planned = run_cli(
        "agent",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "fixture",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["framework"] == "strands-agents"
    assert payload["framework_version"] == "1.53.0"
    assert payload["model_call_performed"] is False
    assert payload["settings"]["max_turns"] == 4
    assert payload["settings"]["max_conversation_messages"] == 24
    assert payload["tools"] == [
        "build_home_theme_dossier",
        "consult_home_specialist",
        "list_home_capabilities",
        "list_home_resources",
        "search_home_documents",
    ]
    assert payload["agent_role"] == "folderhome_master"
    assert payload["routing_policy"] == "semantic_model_selection"
    assert payload["executor_coverage"] == {
        "connected": 3,
        "direct_read_only": 1,
        "planning_only": 3,
        "not_connected": 26,
        "total": 33,
    }
    assert payload["external_network_used"] is False

    missing_note_provider = run_cli(
        "agent",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--llm-note-root",
        str(tmp_path / "missing-llm-note"),
        "--model-provider",
        "fixture",
        "--json",
    )
    assert missing_note_provider.returncode == 2
    assert "llm-note" in json.loads(missing_note_provider.stdout)["error"]

    chatted = run_cli(
        "agent",
        "chat",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "fixture",
        "--profile-id",
        "lukas",
        "--prompt",
        "What can you do?",
        "--json",
    )
    assert chatted.returncode == 0, chatted.stderr
    chat_payload = json.loads(chatted.stdout)
    assert chat_payload["organizational_profile_id"] == "lukas"
    assert chat_payload["tool_events"][0]["tool_name"] == "list_home_capabilities"
    assert chat_payload["side_effects"] == []

    bedrock_common = (
        "agent",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "bedrock",
        "--bedrock-model-id",
        "eu.anthropic.claude-sonnet-4-20250514-v1:0",
        "--aws-region",
        "eu-central-1",
        "--allow-network",
    )
    blocked = run_cli(*bedrock_common, "--json")
    assert blocked.returncode == 2
    assert "Datenweitergabefreigabe" in json.loads(blocked.stdout)["error"]

    approved = run_cli(
        *bedrock_common,
        "--approve-sensitive-cloud-data",
        "--json",
    )
    assert approved.returncode == 0, approved.stderr
    approved_payload = json.loads(approved.stdout)
    assert approved_payload["model_call_performed"] is False
    assert approved_payload["settings"]["allow_sensitive_cloud_data"] is True


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_agent_session_exposes_executor_catalog_as_read_only_ndjson(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    result = run_cli(
        "agent",
        "session",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "fixture",
        "--profile-id",
        "lukas",
        "--json",
        input_text="/catalog\n/reset\n/quit\n",
    )

    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [item["event"] for item in events] == [
        "ready",
        "catalog",
        "conversation_reset",
        "closed",
    ]
    assert all(item["schema"] == "folderhome.agent-session-event.v1" for item in events)
    assert events[0]["profile_id"] == "lukas"
    assert events[0]["chat_is_approval"] is False
    assert events[0]["confirmation_command"] == "/confirm <plan_id>"
    assert events[1]["catalog"]["coverage"] == {
        "connected": 3,
        "direct_read_only": 1,
        "planning_only": 3,
        "not_connected": 26,
        "total": 33,
    }
    assert events[2]["conversation"]["turn"] == 0
    assert events[2]["side_effects"] == ["memory.agent_conversation.clear"]
    assert events[3]["side_effects"] == []


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_agent_session_retains_conversation_between_cli_turns(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    remember = json.dumps(
        {
            "schema": "folderhome.fixture-conversation-turn.v1",
            "remember": "Hyundai i10",
            "recall": False,
        }
    )
    recall = json.dumps(
        {
            "schema": "folderhome.fixture-conversation-turn.v1",
            "remember": None,
            "recall": True,
        }
    )

    result = run_cli(
        "agent",
        "session",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "fixture",
        "--profile-id",
        "lukas",
        "--json",
        input_text=f"{remember}\n{recall}\n/quit\n",
    )

    assert result.returncode == 0, result.stderr
    chats = [
        json.loads(line)
        for line in result.stdout.splitlines()
        if json.loads(line)["event"] == "chat"
    ]
    assert [item["conversation"]["turn"] for item in chats] == [1, 2]
    assert "Hyundai i10" in chats[1]["agent"]["response_text"]
    assert all(item["side_effects"] == [] for item in chats)


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir() or not LLM_NOTE_ROOT.is_dir(),
    reason="pinned KnowledgeDigest or llm-note checkout unavailable",
)
def test_agent_session_requires_explicit_plan_id_then_executes_note_once(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    specialist_request = {
        "schema": "folderhome.fixture-specialist-request.v1",
        "expert_id": "creative_knowledge_expert",
        "workflow_id": "personal-notes",
        "persona_id": "creative_guide",
        "language": "de",
        "request": {
            "action": "create",
            "notebook_id": "gesundheit",
            "area": "gesundheit",
            "title": "Fragen für den Hausarzt",
            "human_content": "Ich möchte drei Fragen für den Termin festhalten.",
            "note_id": None,
            "expected_revision": None,
            "revert_to_revision": None,
            "references": [],
        },
    }
    prompt = json.dumps(specialist_request, ensure_ascii=False)
    session_args = (
        "agent",
        "session",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--llm-note-root",
        str(LLM_NOTE_ROOT),
        "--model-provider",
        "fixture",
        "--profile-id",
        "lukas",
        "--json",
    )
    database = state_dir / "personal-notes" / "llm-note.db"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    process = subprocess.Popen(
        [sys.executable, "-m", "folderhome", *session_args],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        ready = json.loads(process.stdout.readline())
        process.stdin.write(prompt + "\n")
        process.stdin.flush()
        chat = json.loads(process.stdout.readline())
        plan = chat["agent"]["proposed_plans"][0]
        assert not database.exists()

        process.stdin.write(f"/confirm {plan['plan_id']}\n")
        process.stdin.flush()
        confirmation = json.loads(process.stdout.readline())
        process.stdin.write("/quit\n")
        process.stdin.flush()
        closed = json.loads(process.stdout.readline())
        process.stdin.close()
        returncode = process.wait(timeout=30)
        stderr = process.stderr.read()
    finally:
        if process.poll() is None:
            process.kill()

    assert returncode == 0, stderr
    assert ready["event"] == "ready"
    assert chat["event"] == "chat"
    assert chat["side_effects"] == []
    assert confirmation["event"] == "confirmation"
    assert confirmation["plan_id"] == plan["plan_id"]
    assert confirmation["plan_sha256"] == plan["plan_sha256"]
    assert confirmation["result"]["execution_performed"] is True
    assert confirmation["result"]["side_effects"] == ["state.personal_notes.append"]
    assert closed["event"] == "closed"
    assert database.is_file()


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir() or not LLM_NOTE_ROOT.is_dir(),
    reason="pinned KnowledgeDigest or llm-note checkout unavailable",
)
def test_agent_session_confirms_findcall_fixture_without_live_call(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    raw_phone = "+4915111111111"
    prompt = json.dumps(
        {
            "schema": "folderhome.fixture-specialist-request.v1",
            "expert_id": "communication_expert",
            "workflow_id": "findcall",
            "persona_id": "methodical_operator",
            "language": "de",
            "request": {
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
            },
        },
        ensure_ascii=False,
    )
    session_args = (
        "agent",
        "session",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--llm-note-root",
        str(LLM_NOTE_ROOT),
        "--model-provider",
        "fixture",
        "--profile-id",
        "lukas",
        "--json",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    process = subprocess.Popen(
        [sys.executable, "-m", "folderhome", *session_args],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        ready = json.loads(process.stdout.readline())
        process.stdin.write(prompt + "\n")
        process.stdin.flush()
        chat = json.loads(process.stdout.readline())
        plan = chat["agent"]["proposed_plans"][0]
        process.stdin.write(f"/confirm {plan['plan_id']}\n")
        process.stdin.flush()
        confirmation = json.loads(process.stdout.readline())
        process.stdin.write("/quit\n")
        process.stdin.flush()
        closed = json.loads(process.stdout.readline())
        process.stdin.close()
        returncode = process.wait(timeout=30)
        stderr = process.stderr.read()
    finally:
        if process.poll() is None:
            process.kill()

    assert returncode == 0, stderr
    assert ready["event"] == "ready"
    assert chat["event"] == "chat"
    assert raw_phone not in json.dumps(chat, ensure_ascii=False)
    assert confirmation["event"] == "confirmation"
    assert confirmation["result"]["execution_performed"] is True
    assert confirmation["result"]["side_effects"] == [
        "simulation.findcall.fixture"
    ]
    report = confirmation["result"]["execution_reports"][0]["domain_report"]
    assert report["simulated"] is True
    assert report["network_used"] is False
    assert report["phone_calls_placed"] is False
    assert report["commitment_made"] is False
    assert closed["event"] == "closed"


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir() or not LLM_NOTE_ROOT.is_dir(),
    reason="pinned KnowledgeDigest or llm-note checkout unavailable",
)
def test_agent_session_confirms_existing_medication_intake_once(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    schedule_id = _seed_cli_medication_schedule(tmp_path, state_dir)
    prompt = json.dumps(
        {
            "schema": "folderhome.fixture-specialist-request.v1",
            "expert_id": "health_expert",
            "workflow_id": "medication-intake",
            "persona_id": "careful_reviewer",
            "language": "de",
            "request": {
                "action": "confirm_taken",
                "schedule_id": schedule_id,
                "scheduled_date": "2026-08-22",
                "confirmed_at": "2026-08-22T08:05:00+02:00",
            },
        },
        ensure_ascii=False,
    )
    session_args = (
        "agent",
        "session",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--llm-note-root",
        str(LLM_NOTE_ROOT),
        "--model-provider",
        "fixture",
        "--profile-id",
        "lukas",
        "--json",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    process = subprocess.Popen(
        [sys.executable, "-m", "folderhome", *session_args],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        ready = json.loads(process.stdout.readline())
        process.stdin.write(prompt + "\n")
        process.stdin.flush()
        chat = json.loads(process.stdout.readline())
        plan = chat["agent"]["proposed_plans"][0]
        assert MedicationStore(state_dir).list_intake_events(profile_id="lukas") == ()

        process.stdin.write(f"/confirm {plan['plan_id']}\n")
        process.stdin.flush()
        confirmation = json.loads(process.stdout.readline())
        process.stdin.write("/quit\n")
        process.stdin.flush()
        closed = json.loads(process.stdout.readline())
        process.stdin.close()
        returncode = process.wait(timeout=30)
        stderr = process.stderr.read()
    finally:
        if process.poll() is None:
            process.kill()

    assert returncode == 0, stderr
    assert ready["event"] == "ready"
    assert chat["event"] == "chat"
    assert chat["side_effects"] == []
    assert confirmation["event"] == "confirmation"
    assert confirmation["result"]["execution_performed"] is True
    assert confirmation["result"]["side_effects"] == [
        "state.medication_intake.append"
    ]
    report = confirmation["result"]["execution_reports"][0]["domain_report"]
    assert report["medical_advice"] is False
    assert "state_path" not in report
    assert len(MedicationStore(state_dir).list_intake_events(profile_id="lukas")) == 1
    assert closed["event"] == "closed"


def test_competition_demo_cli_publishes_only_after_explicit_gate(tmp_path: Path) -> None:
    output_dir = tmp_path / "competition-demo"

    blocked = run_cli("demo", "run", "--output-dir", str(output_dir), "--json")
    assert blocked.returncode == 2
    assert "Ausgabefreigabe" in json.loads(blocked.stdout)["error"]
    assert not output_dir.exists()

    executed = run_cli(
        "demo",
        "run",
        "--output-dir",
        str(output_dir),
        "--approve-output-write",
        "--json",
    )
    assert executed.returncode == 0, executed.stderr
    payload = json.loads(executed.stdout)
    assert payload["status"] == "passed"
    assert payload["framework"] == "strands-agents"
    assert payload["network_used"] is False
    assert (output_dir / "EVIDENCE.json").is_file()


def test_accident_demo_site_cli_starts_only_after_explicit_gate(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "accident-demo"
    blocked = run_cli(
        "demo",
        "accident-serve",
        "--workspace-dir",
        str(workspace_dir),
        "--port",
        "0",
        "--json",
    )
    assert blocked.returncode == 2
    assert "Serverfreigabe" in json.loads(blocked.stdout)["error"]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "folderhome",
            "demo",
            "accident-serve",
            "--workspace-dir",
            str(workspace_dir),
            "--port",
            "0",
            "--approve-loopback-server",
            "--json",
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        ready = json.loads(process.stdout.readline())
        access_url = str(ready["access_url"])
        split = urlsplit(access_url)
        token = parse_qs(split.query)["token"][0]
        status_url = f"{ready['base_url']}/demo/api/status?token={token}"
        with urlopen(status_url, timeout=5) as response:  # noqa: S310 - loopback only
            status = json.loads(response.read().decode("utf-8"))
    finally:
        process.terminate()
        process.wait(timeout=10)

    assert ready["status"] == "ready"
    assert ready["demo"] == "synthetic_accident"
    assert ready["external_network_used"] is False
    assert status["synthetic_data_only"] is True


@pytest.mark.skipif(not LLM_NOTE_ROOT.is_dir(), reason="pinned llm-note checkout unavailable")
def test_personal_note_cli_guides_applies_and_reads_history_without_network(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "note-request.json"
    state_dir = tmp_path / "state"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.personal-note-request.v1",
                "request_id": "request-cli-create",
                "action": "create",
                "profile_id": "lukas",
                "notebook_id": "gesundheit",
                "area": "gesundheit",
                "title": "Fragen für den Hausarzt",
                "human_content": "Ich möchte drei Fragen für den Termin sammeln.",
                "note_id": None,
                "expected_revision": None,
                "revert_to_revision": None,
                "references": [
                    {
                        "schema": "folderhome.personal-note-reference.v1",
                        "kind": "document",
                        "target_id": "doc_hausarztbericht",
                        "label": "Hausarztbericht",
                        "sha256": "a" * 64,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    common = (
        "--request-file",
        str(request_file),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--provider-root",
        str(LLM_NOTE_ROOT),
        "--json",
    )

    providers = run_cli(
        "notes",
        "providers",
        "--provider-root",
        str(LLM_NOTE_ROOT),
        "--json",
    )
    assert providers.returncode == 0, providers.stderr
    provider_payload = json.loads(providers.stdout)
    assert provider_payload["storage_provider"]["status"] == "ready"
    assert provider_payload["remote_llm_invoked"] is False

    guide = run_cli("notes", "guide", *common)
    assert guide.returncode == 0, guide.stderr
    plan = json.loads(guide.stdout)
    assert plan["status"] == "review_required"
    assert plan["guidance"]["confirmed_content_changed"] is False
    assert plan["guidance"]["network_invoked"] is False
    assert not state_dir.exists()

    approval_file = tmp_path / "note-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.personal-note-approval.v1",
                "approval_id": "approval-cli-create",
                "plan_id": plan["plan_id"],
                "plan_sha256": plan["plan_sha256"],
                "action_id": plan["action_id"],
                "content_sha256": plan["content_sha256"],
                "approved_at": "2026-08-22T05:30:00+02:00",
                "allow_local_note_write": True,
            }
        ),
        encoding="utf-8",
    )
    applied = run_cli(
        "notes",
        "apply",
        *common[:-1],
        "--approval-file",
        str(approval_file),
        "--approve-state-write",
        "--json",
    )
    assert applied.returncode == 0, applied.stderr
    report = json.loads(applied.stdout)
    assert report["status"] == "executed"
    assert report["network_invoked"] is False
    assert report["external_sync_invoked"] is False

    history = run_cli(
        "notes",
        "history",
        "--note-id",
        plan["note_id"],
        "--state-dir",
        str(state_dir),
        "--provider-root",
        str(LLM_NOTE_ROOT),
        "--json",
    )
    assert history.returncode == 0, history.stderr
    history_payload = json.loads(history.stdout)
    assert history_payload["never_overwrite"] is True
    assert [item["revision"] for item in history_payload["versions"]] == [1]
    assert history_payload["versions"][0]["human_content"].startswith("Ich möchte")


def test_synthetic_run_writes_the_same_report_returned_on_stdout(tmp_path: Path) -> None:
    report_file = tmp_path / "run.json"
    result = run_cli(
        "run",
        "synthetic",
        "--scenario",
        "success",
        "--run-id",
        "run_cli",
        "--report-file",
        str(report_file),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    stdout_report = json.loads(result.stdout)
    assert stdout_report["run_id"] == "run_cli"
    assert stdout_report["status"] == "executed"
    assert stdout_report["dry_run"] is True
    assert json.loads(report_file.read_text(encoding="utf-8")) == stdout_report


def test_synthetic_run_generates_a_stable_run_id_when_omitted(tmp_path: Path) -> None:
    report_file = tmp_path / "generated.json"

    result = run_cli("run", "synthetic", "--report-file", str(report_file), "--json")

    assert result.returncode == 0, result.stderr
    run_id = json.loads(result.stdout)["run_id"]
    assert re.fullmatch(r"run_[0-9a-f]{32}", run_id)
    assert json.loads(report_file.read_text(encoding="utf-8"))["run_id"] == run_id


@pytest.mark.skipif(not FCSA_ROOT.is_dir(), reason="pinned sibling FCSA checkout unavailable")
def test_fcsa_plan_cli_runs_the_pinned_provider_without_moving_files(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    scan_dir = tmp_path / "inbox"
    target_dir = tmp_path / "sorted"
    state_dir = tmp_path / "state"
    config_dir.mkdir()
    scan_dir.mkdir()
    target_dir.mkdir()
    source_file = scan_dir / "Rechnung.txt"
    source_file.write_text("Rechnungsnummer 42", encoding="utf-8")
    payloads = {
        "config.json": {
            "scan_paths": [str(scan_dir)],
            "include_formats": None,
            "exclude_formats": [],
            "duplication_detection_rules": {
                "on_duplicate": "rename",
                "hash_algorithm": "sha256",
            },
            "state_dir": str(state_dir),
            "trash_dir": str(state_dir / "trash"),
            "allow_hard_delete": False,
            "require_dry_run_before_live": True,
            "ocr_backend": {"type": "none"},
        },
        "categories-definitions.json": {
            "categories": [
                {
                    "id": "invoices",
                    "display_name": "Rechnungen",
                    "detection": {"extensions": [".txt"]},
                    "checks": [],
                    "gates": [],
                    "default_target": str(target_dir),
                    "default_actions": ["move"],
                    "default_stepping": True,
                }
            ],
            "fallback_category": "unsorted",
        },
        "action-rules.json": {
            "rules": {"invoices": {"move": {"target": "default"}}},
            "default_rule": {"move": {"target": "default"}},
        },
    }
    for filename, payload in payloads.items():
        (config_dir / filename).write_text(json.dumps(payload), encoding="utf-8")
    report_file = tmp_path / "fcsa-plan.json"

    result = run_cli(
        "run",
        "fcsa-plan",
        "--config-dir",
        str(config_dir),
        "--provider-root",
        str(FCSA_ROOT),
        "--run-id",
        "run_cli_fcsa",
        "--report-file",
        str(report_file),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["run_id"] == "run_cli_fcsa"
    assert report["plugin_id"] == "file-collect-sort-action"
    assert report["actions"][0]["name"] == "fcsa.move"
    assert report["actions"][0]["status"] == "planned"
    assert report["actions"][0]["gate"]["granted"] is False
    assert "würde" in report["actions"][0]["message"]
    assert "wuerde" not in report["actions"][0]["message"]
    assert json.loads(report_file.read_text(encoding="utf-8")) == report
    assert source_file.is_file()
    assert list(target_dir.iterdir()) == []
    assert not state_dir.exists()


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_document_cli_ingest_search_dossier_and_report_end_to_end(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    state = tmp_path / "state"
    inbox.mkdir()
    policy = inbox / "Krankenversicherung.txt"
    note = inbox / "Notiz.md"
    policy.write_text(
        "Die Krankenversicherung ist rein synthetisch. Der Tarif heißt TestPlus. "
        "Der Beitrag beträgt 210 Euro.",
        encoding="utf-8",
    )
    note.write_text(
        "# Haushaltsnotiz\n\nDer Vorrat ist rein synthetisch. Zwei Packungen sind vorhanden.",
        encoding="utf-8",
    )
    source_before = {path: path.read_bytes() for path in (policy, note)}
    ingest_file = tmp_path / "ingest.json"
    report_file = tmp_path / "ordnerbericht.md"

    ingest = run_cli(
        "documents",
        "ingest",
        "--source-dir",
        str(inbox),
        "--state-dir",
        str(state),
        "--approve-index-write",
        "--result-file",
        str(ingest_file),
        "--report-file",
        str(report_file),
        "--json",
    )

    assert ingest.returncode == 0, ingest.stderr
    ingest_payload = json.loads(ingest.stdout)
    assert ingest_payload["indexed"] == 2
    assert json.loads(ingest_file.read_text(encoding="utf-8")) == ingest_payload
    catalog_payload = json.loads(
        (state / "folderhome-catalog.json").read_text(encoding="utf-8")
    )
    assert len(catalog_payload["documents"]) == 2
    assert all("text" not in document for document in catalog_payload["documents"])
    report_text = report_file.read_text(encoding="utf-8")
    assert "### Krankenversicherung.txt" in report_text
    assert "Tarif heißt TestPlus" in report_text
    assert {path: path.read_bytes() for path in source_before} == source_before
    assert not (state / "archive").exists()

    search = run_cli(
        "documents",
        "search",
        "--state-dir",
        str(state),
        "--query",
        "Ich suche nach einem Dokument über meine Krankenversicherung.",
        "--json",
    )

    assert search.returncode == 0, search.stderr
    search_payload = json.loads(search.stdout)
    assert search_payload["search_query"] == "Krankenversicherung"
    assert [hit["filename"] for hit in search_payload["hits"]] == [
        "Krankenversicherung.txt"
    ]

    dossier_file = tmp_path / "dossier.md"
    dossier = run_cli(
        "documents",
        "dossier",
        "--state-dir",
        str(state),
        "--topic",
        "Krankenversicherung",
        "--output-file",
        str(dossier_file),
        "--json",
    )

    assert dossier.returncode == 0, dossier.stderr
    dossier_payload = json.loads(dossier.stdout)
    assert dossier_payload["total_hits"] == 1
    assert dossier_file.read_text(encoding="utf-8") == dossier_payload["markdown"]


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_document_cli_denies_ingest_without_explicit_write_approval(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "Notiz.txt").write_text("Synthetisch.", encoding="utf-8")

    result = run_cli(
        "documents",
        "ingest",
        "--source-dir",
        str(inbox),
        "--state-dir",
        str(tmp_path / "state"),
        "--json",
    )

    assert result.returncode == 2
    assert "Schreibfreigabe" in json.loads(result.stdout)["error"]
    assert not (tmp_path / "state").exists()


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_document_versions_cli_finds_latest_and_only_proposes_archive(
    tmp_path: Path,
) -> None:
    inbox = tmp_path / "inbox"
    state = tmp_path / "state"
    inbox.mkdir()
    old = inbox / "KFZ_Hyundai_i10_2025.txt"
    new = inbox / "KFZ_Hyundai_i10_2026.txt"
    old.write_text(
        "KFZ Versicherung für Hyundai i10. Gültig ab 01.01.2025. "
        "Der synthetische Beitrag beträgt 400 Euro.",
        encoding="utf-8",
    )
    new.write_text(
        "KFZ Versicherung für Hyundai i10. Gültig ab 01.01.2026. "
        "Der synthetische Beitrag beträgt 420 Euro.",
        encoding="utf-8",
    )
    ingest = run_cli(
        "documents",
        "ingest",
        "--source-dir",
        str(inbox),
        "--state-dir",
        str(state),
        "--approve-index-write",
        "--json",
    )
    assert ingest.returncode == 0, ingest.stderr
    database_before = (state / "knowledge.db").read_bytes()
    output_file = tmp_path / "versionen.json"

    result = run_cli(
        "documents",
        "versions",
        "--state-dir",
        str(state),
        "--query",
        "Was ist meine neueste KFZ-Versicherung für meinen Hyundai i10?",
        "--output-file",
        str(output_file),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["family"]["versions"][0]["document"]["filename"] == new.name
    assert len(payload["comparisons"]) == 1
    assert len(payload["archive_proposals"]) == 1
    assert payload["fcsa_archive_plans"][0]["planned_actions"] == [
        "duplicate_check",
        "move",
    ]
    assert payload["fcsa_archive_plans"][0]["gate"]["granted"] is False
    assert payload["archive_proposals"][0]["status"] == "planned"
    assert payload["archive_proposals"][0]["gate"]["granted"] is False
    assert json.loads(output_file.read_text(encoding="utf-8")) == payload
    assert old.exists() and new.exists()
    assert not (inbox / "Archiv").exists()
    assert (state / "knowledge.db").read_bytes() == database_before


def test_profiles_cli_validates_and_resolves_inheritance(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "household.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.household-rules.v1",
                "os_account": "synthetic-family-account",
                "rules": [
                    {
                        "rule_id": "rule_global_delete",
                        "key": "delete.mode",
                        "value": "review_only",
                        "scope": "global",
                    },
                    {
                        "rule_id": "rule_area_archive",
                        "key": "archive.after_days",
                        "value": 3650,
                        "scope": "area",
                        "area": "versicherungen",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (profiles / "Lukas.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.user-profile.v1",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "os_account": "synthetic-family-account",
                "organizational_only": True,
                "rules": [
                    {
                        "rule_id": "rule_lukas_archive",
                        "key": "archive.after_days",
                        "value": 1825,
                        "scope": "profile_area",
                        "area": "versicherungen",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    validate = run_cli(
        "profiles",
        "validate",
        "--profiles-dir",
        str(profiles),
        "--json",
    )
    resolve = run_cli(
        "profiles",
        "resolve",
        "--profiles-dir",
        str(profiles),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--json",
    )

    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["profiles"] == ["lukas"]
    assert resolve.returncode == 0, resolve.stderr
    payload = json.loads(resolve.stdout)
    assert payload["organizational_only"] is True
    assert "keine Zugriffsgrenze" in payload["security_boundary"]
    rules = {item["key"]: item for item in payload["rules"]}
    assert rules["archive.after_days"]["value"] == 1825
    assert rules["archive.after_days"]["scope"] == "profile_area"
    assert rules["delete.mode"]["value"] == "review_only"


def test_resources_cli_validates_and_lists_only_logical_profile_catalog(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-source"
    source.mkdir()
    registry_file = tmp_path / "resources.json"
    registry_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.resource-registry.v1",
                "os_account": "synthetic-family-account",
                "resources": [
                    {
                        "resource_id": "insurance_documents",
                        "kind": "directory",
                        "locator": {"type": "local_path", "path": str(source)},
                        "operations": ["list", "read"],
                        "purposes": ["insurance.source"],
                        "profile_ids": ["lukas"],
                        "cloud_context": "minimized_with_approval",
                    }
                ],
                "profile_defaults": {
                    "lukas": {"insurance.source": "insurance_documents"}
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    validated = run_cli(
        "resources",
        "validate",
        "--resources-file",
        str(registry_file),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--json",
    )
    catalog = run_cli(
        "resources",
        "catalog",
        "--resources-file",
        str(registry_file),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--json",
    )

    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)["resource_count"] == 1
    assert catalog.returncode == 0, catalog.stderr
    payload = json.loads(catalog.stdout)
    assert payload["paths_disclosed"] is False
    assert payload["resources"][0]["resource_id"] == "insurance_documents"
    assert str(source) not in catalog.stdout


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_document_policy_plan_cli_is_end_to_end_and_never_changes_files(
    tmp_path: Path,
) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "household.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.household-rules.v1",
                "os_account": "synthetic-family-account",
                "rules": [
                    {
                        "rule_id": "global_format",
                        "key": "format.required",
                        "value": "pdf",
                        "scope": "global",
                    },
                    {
                        "rule_id": "global_original",
                        "key": "conversion.original",
                        "value": "gardener_storage",
                        "scope": "global",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (profiles / "Lukas.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.user-profile.v1",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "os_account": "synthetic-family-account",
                "organizational_only": True,
                "rules": [
                    {
                        "rule_id": "lukas_name",
                        "key": "naming.template",
                        "value": "{name}_{profile}.{ext}",
                        "scope": "profile_area",
                        "area": "versicherungen",
                    },
                    {
                        "rule_id": "lukas_sort",
                        "key": "sort.target",
                        "value": "Versicherungen/KFZ",
                        "scope": "profile_area",
                        "area": "versicherungen",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    source = inbox / "Hyundai i10.txt"
    source.write_text("Rein synthetische KFZ-Versicherung.", encoding="utf-8")
    source_before = source.read_bytes()
    target_root = tmp_path / "Ablage"
    output_file = tmp_path / "aktionsplan.json"

    result = run_cli(
        "documents",
        "plan",
        "--profiles-dir",
        str(profiles),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--source-file",
        str(source),
        "--target-root",
        str(target_root),
        "--as-of",
        "2026-08-21",
        "--output-file",
        str(output_file),
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert json.loads(output_file.read_text(encoding="utf-8")) == payload
    assert [step["kind"] for step in payload["steps"]] == [
        "rename",
        "sort",
        "convert",
        "handle_original",
    ]
    assert payload["steps"][0]["rules"][0]["source_rule_ids"] == ["lukas_name"]
    assert payload["steps"][2]["status"] == "planned"
    assert payload["steps"][2]["provider_id"] == "folderhome.document-transform"
    assert payload["steps"][3]["status"] == "blocked"
    assert all(step["gate"]["granted"] is False for step in payload["steps"])
    assert "text" not in payload["document"]
    assert source.read_bytes() == source_before
    assert not target_root.exists()


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_document_bundle_cli_plans_then_writes_only_with_explicit_gate(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    first = source_dir / "A.txt"
    second = source_dir / "B.md"
    first.write_text("Äpfel und Öl.", encoding="utf-8")
    second.write_text("Zweiter synthetischer Inhalt.", encoding="utf-8")
    before = {path: path.read_bytes() for path in (first, second)}
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    dry_output = output_dir / "Nur-Plan.txt"

    dry_run = run_cli(
        "documents",
        "bundle",
        "--source-dir",
        str(source_dir),
        "--output-file",
        str(dry_output),
        "--format",
        "txt",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--json",
    )

    assert dry_run.returncode == 0, dry_run.stderr
    dry_payload = json.loads(dry_run.stdout)
    assert dry_payload["result"] is None
    assert dry_payload["plan"]["gate"]["granted"] is False
    assert not dry_output.exists()

    output = output_dir / "Sammlung.txt"
    result_file = output_dir / "Sammlung.json"
    live = run_cli(
        "documents",
        "bundle",
        "--source-dir",
        str(source_dir),
        "--output-file",
        str(output),
        "--format",
        "txt",
        "--approve-output-write",
        "--result-file",
        str(result_file),
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--json",
    )

    assert live.returncode == 0, live.stderr
    payload = json.loads(live.stdout)
    assert payload["result"]["status"] == "executed"
    assert payload["result"]["output_path"] == str(output.resolve())
    assert json.loads(result_file.read_text(encoding="utf-8")) == payload
    assert "## A.txt" in output.read_text(encoding="utf-8")
    assert "Äpfel und Öl." in output.read_text(encoding="utf-8")
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_document_package_cli_groups_types_and_emits_zip_manifest(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Dokumente"
    nested = source_dir / "Unterordner"
    nested.mkdir(parents=True)
    first = source_dir / "A.txt"
    second = nested / "B.txt"
    note = source_dir / "Notiz.md"
    unknown = source_dir / "Rohdaten.bin"
    first.write_text("Äpfel und Öl.", encoding="utf-8")
    second.write_text("Zweiter Text.", encoding="utf-8")
    note.write_text("# Synthetische Notiz", encoding="utf-8")
    unknown.write_bytes(b"synthetic-binary")
    sources = (first, second, note, unknown)
    before = {path: path.read_bytes() for path in sources}
    output_dir = tmp_path / "Ausgabe"
    output_dir.mkdir()
    output_zip = output_dir / "Dokumentpaket.zip"
    result_file = output_dir / "Dokumentpaket.json"

    result = run_cli(
        "documents",
        "package",
        "--source-dir",
        str(source_dir),
        "--output-zip",
        str(output_zip),
        "--approve-output-write",
        "--result-file",
        str(result_file),
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["plan"]["unsupported"][0]["relative_path"] == "Rohdaten.bin"
    assert payload["result"]["status"] == "executed"
    assert json.loads(result_file.read_text(encoding="utf-8")) == payload
    with zipfile.ZipFile(output_zip) as package:
        assert package.namelist() == ["Markdown.txt", "TXT.txt", "manifest.json"]
        manifest = json.loads(package.read("manifest.json").decode("utf-8"))
        assert manifest["unsupported"][0]["relative_path"] == "Rohdaten.bin"
        assert "Äpfel und Öl." in package.read("TXT.txt").decode("utf-8")
    assert {path: path.read_bytes() for path in before} == before


def test_folders_cli_persists_history_and_detects_hash_move(tmp_path: Path) -> None:
    source_dir = tmp_path / "Dokumente"
    inbox = source_dir / "Eingang"
    inbox.mkdir(parents=True)
    source = inbox / "Police.txt"
    source.write_text("Unveränderter synthetischer Inhalt.", encoding="utf-8")
    before_bytes = source.read_bytes()
    state_dir = tmp_path / "state"

    first = run_cli(
        "folders",
        "snapshot",
        "--source-dir",
        str(source_dir),
        "--captured-at",
        "2026-08-21T20:30:00Z",
        "--state-dir",
        str(state_dir),
        "--approve-state-write",
        "--json",
    )
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    first_file = Path(first_payload["snapshot_file"])
    assert first_file.is_file()

    target = source_dir / "Versicherungen" / "Police.txt"
    target.parent.mkdir()
    source.rename(target)
    second = run_cli(
        "folders",
        "snapshot",
        "--source-dir",
        str(source_dir),
        "--captured-at",
        "2026-08-21T20:31:00Z",
        "--state-dir",
        str(state_dir),
        "--approve-state-write",
        "--json",
    )
    assert second.returncode == 0, second.stderr
    second_file = Path(json.loads(second.stdout)["snapshot_file"])

    diff = run_cli(
        "folders",
        "diff",
        "--before-file",
        str(first_file),
        "--after-file",
        str(second_file),
        "--json",
    )

    assert diff.returncode == 0, diff.stderr
    payload = json.loads(diff.stdout)
    assert payload["changes"] == [
        {
            "after_path": "Versicherungen/Police.txt",
            "after_sha256": payload["changes"][0]["after_sha256"],
            "before_path": "Eingang/Police.txt",
            "before_sha256": payload["changes"][0]["after_sha256"],
            "confidence": "high",
            "evidence": "Eindeutiger, unveränderter SHA-256 an genau einem neuen Pfad.",
            "kind": "moved",
        }
    ]
    assert target.read_bytes() == before_bytes
    assert len(list((state_dir / "directory-snapshots").glob("*.json"))) == 2
    receipts_file = tmp_path / "receipts.json"
    receipts_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.placement-receipts.v1",
                "receipts": [
                    {
                        "receipt_id": "receipt_policy",
                        "document_sha256": payload["changes"][0]["after_sha256"],
                        "placed_path": "Eingang/Police.txt",
                        "profile_id": "lukas",
                        "area": "versicherungen",
                        "source_rule_ids": ["rule_sort_inbox"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    learning = run_cli(
        "folders",
        "learning",
        "--before-file",
        str(first_file),
        "--after-file",
        str(second_file),
        "--receipts-file",
        str(receipts_file),
        "--json",
    )

    assert learning.returncode == 0, learning.stderr
    example = json.loads(learning.stdout)["examples"][0]
    assert example["corrected_path"] == "Versicherungen/Police.txt"
    assert example["status"] == "candidate"
    assert example["automatic_promotion"] is False


def test_folders_scan_cli_uses_watch_config_and_latest_checkpoint(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    source = source_dir / "Police.txt"
    source.write_text("Unveränderter synthetischer Inhalt.", encoding="utf-8")
    config_file = tmp_path / "watched-folders.json"
    config_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.watched-folders.v1",
                "watches": [
                    {
                        "watch_id": "family_inbox",
                        "source_dir": str(source_dir),
                        "profile_id": "lukas",
                        "area": "versicherungen",
                        "interval_minutes": 1,
                        "recursive": True,
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"

    first = run_cli(
        "folders",
        "scan",
        "--config-file",
        str(config_file),
        "--watch-id",
        "family_inbox",
        "--captured-at",
        "2026-08-21T20:40:00Z",
        "--state-dir",
        str(state_dir),
        "--approve-state-write",
        "--json",
    )

    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    assert first_payload["previous_snapshot_id"] is None
    assert first_payload["checkpoint_file"] is not None
    target = source_dir / "Versicherungen" / "Police.txt"
    target.parent.mkdir()
    source.rename(target)
    receipts_file = tmp_path / "receipts.json"
    receipts_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.placement-receipts.v1",
                "receipts": [
                    {
                        "receipt_id": "receipt_policy",
                        "document_sha256": first_payload["snapshot"]["files"][0][
                            "source_sha256"
                        ],
                        "placed_path": "Police.txt",
                        "profile_id": "lukas",
                        "area": "versicherungen",
                        "source_rule_ids": ["rule_sort_inbox"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    second = run_cli(
        "folders",
        "scan",
        "--config-file",
        str(config_file),
        "--watch-id",
        "family_inbox",
        "--captured-at",
        "2026-08-21T20:41:00Z",
        "--state-dir",
        str(state_dir),
        "--receipts-file",
        str(receipts_file),
        "--approve-state-write",
        "--json",
    )

    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)
    assert second_payload["diff"]["changes"][0]["kind"] == "moved"
    assert second_payload["learning_examples"][0]["corrected_path"] == (
        "Versicherungen/Police.txt"
    )
    assert second_payload["automatic_promotion"] is False


def test_documents_execute_and_undo_cli_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "Eingang" / "Police.txt"
    source.parent.mkdir(parents=True)
    source.write_text("Synthetischer Versicherungsinhalt.", encoding="utf-8")
    before = source.read_bytes()
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "household.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.household-rules.v1",
                "os_account": "synthetic",
                "rules": [
                    {
                        "rule_id": "rule_name",
                        "key": "naming.template",
                        "value": "{date}_{name}",
                        "scope": "global",
                    },
                    {
                        "rule_id": "rule_sort",
                        "key": "sort.target",
                        "value": "Versicherungen/KFZ",
                        "scope": "global",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (profiles / "Lukas.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.user-profile.v1",
                "profile_id": "lukas",
                "display_name": "Lukas",
                "os_account": "synthetic",
                "organizational_only": True,
                "rules": [],
            }
        ),
        encoding="utf-8",
    )
    target_root = tmp_path / "Ablage"
    common = (
        "--profiles-dir",
        str(profiles),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--source-file",
        str(source),
        "--target-root",
        str(target_root),
        "--as-of",
        "2026-08-21",
    )
    planned = run_cli("documents", "plan", *common, "--json")
    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)

    executed = run_cli(
        "documents",
        "execute",
        *common,
        "--state-dir",
        str(tmp_path / "state"),
        "--approval-id",
        "approval_cli",
        "--approve-plan-id",
        plan["plan_id"],
        "--approve-action-id",
        plan["steps"][0]["action_id"],
        "--approve-action-id",
        plan["steps"][1]["action_id"],
        "--approved-at",
        "2026-08-21T21:00:00Z",
        "--approve-file-write",
        "--json",
    )

    assert executed.returncode == 0, executed.stderr
    execution = json.loads(executed.stdout)
    final_target = Path(execution["final_target"])
    assert final_target.read_bytes() == before
    assert not source.exists()
    completed_file = Path(execution["completed_file"])
    assert completed_file.is_file()

    undone = run_cli(
        "documents",
        "undo",
        "--execution-file",
        str(completed_file),
        "--approval-id",
        "undo_cli",
        "--approve-execution-id",
        execution["execution_id"],
        "--document-sha256",
        execution["document_sha256"],
        "--approved-at",
        "2026-08-21T21:01:00Z",
        "--approve-file-write",
        "--json",
    )

    assert undone.returncode == 0, undone.stderr
    assert json.loads(undone.stdout)["status"] == "undone"
    assert source.read_bytes() == before
    assert not final_target.exists()


def test_folders_cleanup_plan_and_selective_execute_cli(tmp_path: Path) -> None:
    source_dir = tmp_path / "Los"
    source_dir.mkdir()
    (source_dir / "A.txt").write_text("A", encoding="utf-8")
    (source_dir / "B.txt").write_text("B", encoding="utf-8")
    common = (
        "--source-dir",
        str(source_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--target-root",
        str(tmp_path / "Ablage"),
        "--as-of",
        "2026-08-21",
    )

    planned = run_cli("folders", "cleanup-plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    selectable = [item for item in plan["items"] if item["status"] == "planned"]
    assert len(selectable) == 2
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.folder-cleanup-approval.v1",
                "approval_id": "cleanup_cli",
                "batch_id": plan["batch_id"],
                "approved_at": "2026-08-21T21:10:00Z",
                "items": [
                    {
                        "document_id": item["document_id"],
                        "plan_id": item["action_plan"]["plan_id"],
                        "document_sha256": item["source_sha256"],
                        "action_ids": item["executable_action_ids"],
                    }
                    for item in selectable
                ],
            }
        ),
        encoding="utf-8",
    )

    executed = run_cli(
        "folders",
        "cleanup-execute",
        *common,
        "--approval-file",
        str(approval_file),
        "--state-dir",
        str(tmp_path / "state"),
        "--approve-file-write",
        "--json",
    )

    assert executed.returncode == 0, executed.stderr
    report = json.loads(executed.stdout)
    assert report["status"] == "executed"
    assert len(report["executions"]) == 2
    assert len(report["placement_receipts"]) == 2
    assert all(Path(item["final_target"]).is_file() for item in report["executions"])
    assert not (source_dir / "A.txt").exists()
    assert not (source_dir / "B.txt").exists()


def test_folders_routine_plan_and_execute_cli_roundtrip(tmp_path: Path) -> None:
    source_dir = tmp_path / "Eingang"
    source_dir.mkdir()
    config_file = tmp_path / "watched-folders.json"
    config_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.watched-folders.v1",
                "watches": [
                    {
                        "watch_id": "family_inbox",
                        "source_dir": str(source_dir),
                        "profile_id": "hanna",
                        "area": "haushalt",
                        "interval_minutes": 60,
                        "recursive": True,
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    baseline = run_cli(
        "folders",
        "scan",
        "--config-file",
        str(config_file),
        "--watch-id",
        "family_inbox",
        "--captured-at",
        "2026-08-21T20:00:00Z",
        "--state-dir",
        str(state_dir),
        "--approve-state-write",
        "--json",
    )
    assert baseline.returncode == 0, baseline.stderr
    source = source_dir / "Police.txt"
    source.write_text("Synthetische Police", encoding="utf-8")
    stable_mtime = datetime(2026, 8, 21, 12, 0, tzinfo=UTC).timestamp()
    os.utime(source, (stable_mtime, stable_mtime))
    common = (
        "--config-file",
        str(config_file),
        "--watch-id",
        "family_inbox",
        "--captured-at",
        "2026-08-21T21:01:00Z",
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--target-root",
        str(tmp_path / "Ablage"),
        "--as-of",
        "2026-08-21",
        "--mode",
        "changes",
    )

    planned = run_cli("folders", "routine-plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    assert plan["status"] == "planned"
    assert plan["eligible_relative_paths"] == ["Police.txt"]
    assert plan["scan_report"]["checkpoint_file"] is None
    item = plan["cleanup_plan"]["items"][0]
    approval_file = tmp_path / "routine-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.folder-cleanup-approval.v1",
                "approval_id": "routine_cli",
                "batch_id": plan["cleanup_plan"]["batch_id"],
                "approved_at": "2026-08-21T21:02:00Z",
                "items": [
                    {
                        "document_id": item["document_id"],
                        "plan_id": item["action_plan"]["plan_id"],
                        "document_sha256": item["source_sha256"],
                        "action_ids": item["executable_action_ids"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    executed = run_cli(
        "folders",
        "routine-execute",
        *common,
        "--approval-file",
        str(approval_file),
        "--completed-at",
        "2026-08-21T21:03:00Z",
        "--approve-file-write",
        "--approve-state-write",
        "--json",
    )

    assert executed.returncode == 0, executed.stderr
    report = json.loads(executed.stdout)
    assert report["status"] == "executed"
    assert report["checkpoint_report"]["snapshot"]["files"] == []
    assert Path(report["completed_file"]).is_file()
    assert not source.exists()
    assert (
        tmp_path
        / "Ablage"
        / "Haushalt"
        / "Hanna"
        / "Hanna_Haushalt_2026-08-21_Police.txt"
    ).is_file()


def test_folders_routine_queue_cli_is_read_only_for_multiple_watches(
    tmp_path: Path,
) -> None:
    ready_dir = tmp_path / "Ready"
    not_due_dir = tmp_path / "NotDue"
    ready_dir.mkdir()
    not_due_dir.mkdir()
    (ready_dir / "Neu.txt").write_text("Neu", encoding="utf-8")
    (not_due_dir / "Alt.txt").write_text("Alt", encoding="utf-8")
    config_file = tmp_path / "watched-folders.json"
    config_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.watched-folders.v1",
                "watches": [
                    {
                        "watch_id": "ready_watch",
                        "source_dir": str(ready_dir),
                        "profile_id": "hanna",
                        "area": "haushalt",
                        "interval_minutes": 60,
                        "recursive": True,
                        "enabled": True,
                    },
                    {
                        "watch_id": "not_due_watch",
                        "source_dir": str(not_due_dir),
                        "profile_id": "hanna",
                        "area": "haushalt",
                        "interval_minutes": 60,
                        "recursive": True,
                        "enabled": True,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    bindings_file = tmp_path / "routine-bindings.json"
    bindings_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.routine-bindings.v1",
                "bindings": [
                    {
                        "binding_id": "ready_binding",
                        "watch_id": "ready_watch",
                        "target_dir": "Targets/Ready",
                        "mode": "changes",
                        "enabled": True,
                    },
                    {
                        "binding_id": "not_due_binding",
                        "watch_id": "not_due_watch",
                        "target_dir": "Targets/NotDue",
                        "mode": "changes",
                        "enabled": True,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    baseline = run_cli(
        "folders",
        "scan",
        "--config-file",
        str(config_file),
        "--watch-id",
        "not_due_watch",
        "--captured-at",
        "2026-08-21T20:30:00Z",
        "--state-dir",
        str(state_dir),
        "--approve-state-write",
        "--json",
    )
    assert baseline.returncode == 0, baseline.stderr
    before_state = {
        path: path.read_bytes() for path in state_dir.rglob("*.json")
    }

    queued = run_cli(
        "folders",
        "routine-queue",
        "--config-file",
        str(config_file),
        "--bindings-file",
        str(bindings_file),
        "--captured-at",
        "2026-08-21T21:01:00Z",
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--as-of",
        "2026-08-21",
        "--json",
    )

    assert queued.returncode == 0, queued.stderr
    payload = json.loads(queued.stdout)
    assert payload["summary"] == {"not_due": 1, "ready": 1}
    assert payload["side_effects"] == []
    assert payload["scheduler_registered"] is False
    assert {path: path.read_bytes() for path in state_dir.rglob("*.json")} == (
        before_state
    )
    assert not (tmp_path / "Targets").exists()


def test_scheduler_plan_and_headless_run_cli_without_registration(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Eingang"
    source_dir.mkdir()
    source = source_dir / "Neu.txt"
    source.write_text("Neu", encoding="utf-8")
    config_file = tmp_path / "watched-folders.json"
    config_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.watched-folders.v1",
                "watches": [
                    {
                        "watch_id": "family_inbox",
                        "source_dir": str(source_dir),
                        "profile_id": "hanna",
                        "area": "haushalt",
                        "interval_minutes": 60,
                        "recursive": True,
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    bindings_file = tmp_path / "routine-bindings.json"
    bindings_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.routine-bindings.v1",
                "bindings": [
                    {
                        "binding_id": "family_cleanup",
                        "watch_id": "family_inbox",
                        "target_dir": "Ablage",
                        "mode": "changes",
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    common = (
        "--task-name",
        "folderhome_routine_queue",
        "--interval-minutes",
        "30",
        "--start-at",
        "2026-08-22T08:00:00+02:00",
        "--timezone",
        "Europe/Berlin",
        "--config-file",
        str(config_file),
        "--bindings-file",
        str(bindings_file),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--python-executable",
        sys.executable,
        "--working-directory",
        str(REPO_ROOT),
    )

    planned = run_cli("scheduler", "plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    assert plan["registration_performed"] is False
    assert plan["installation_supported"] is False
    assert plan["side_effects"] == []
    assert not state_dir.exists()
    assert "schtasks" not in planned.stdout.lower()

    executed = run_cli(
        "scheduler",
        "run",
        *common,
        "--schedule-id",
        plan["schedule_id"],
        "--captured-at",
        "2026-08-22T06:01:00Z",
        "--approve-scheduler-state-write",
        "--json",
    )

    assert executed.returncode == 10, executed.stderr
    report = json.loads(executed.stdout)
    assert report["status"] == "attention"
    assert report["exit_code"] == 10
    assert report["queue"]["summary"] == {"ready": 1}
    assert report["scheduler_registered"] is False
    assert Path(report["completed_file"]).is_file()
    assert source.read_text(encoding="utf-8") == "Neu"
    assert not (tmp_path / "Ablage").exists()


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_contacts_cli_plans_applies_and_queries_local_register(tmp_path: Path) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    contact_file = source_dir / "Hyundai-i10-Versicherung.txt"
    contact_text = (
        "Organisation: Beispiel Versicherung AG\n"
        "Ansprechpartner: Erika Beispiel\n"
        "Rolle: Kundenservice\n"
        "Zuständig für: KFZ-Versicherung\n"
        "Vertragsobjekt: Hyundai i10\n"
        "E-Mail: erika.beispiel@example.invalid\n"
        "Telefon: +49 30 123456\n"
        "Gültig ab: 2026-08-01\n"
        "Interne Notiz: darf nicht im Register landen.\n"
    )
    contact_file.write_text(contact_text, encoding="utf-8")
    state_dir = tmp_path / "state"
    common = (
        "--source-dir",
        str(source_dir),
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
    )

    planned = run_cli("contacts", "plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    selected = [action for action in plan["actions"] if action["status"] == "planned"]
    assert len(selected) == 1
    assert selected[0]["kind"] == "create"
    assert plan["automatic_deletion"] is False
    assert "Interne Notiz" not in planned.stdout
    assert not state_dir.exists()

    approval_file = tmp_path / "contact-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.contact-register-approval.v1",
                "approval_id": "contact_cli_create",
                "plan_id": plan["plan_id"],
                "register_revision": plan["register_revision"],
                "action_ids": [selected[0]["action_id"]],
                "approved_at": "2026-08-22T08:00:00+02:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    denied = run_cli(
        "contacts",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--json",
    )

    assert denied.returncode == 2
    assert "State-Freigabe" in json.loads(denied.stdout)["error"]
    assert not state_dir.exists()

    applied = run_cli(
        "contacts",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--approve-state-write",
        "--json",
    )

    assert applied.returncode == 0, applied.stderr
    report = json.loads(applied.stdout)
    assert report["status"] == "applied"
    assert len(report["created_contact_ids"]) == 1
    assert report["deleted_contact_ids"] == []
    assert contact_file.read_text(encoding="utf-8") == contact_text

    queried = run_cli(
        "contacts",
        "list",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--object",
        "Hyundai i10",
        "--json",
    )

    assert queried.returncode == 0, queried.stderr
    contacts = json.loads(queried.stdout)
    assert contacts["count"] == 1
    assert contacts["contacts"][0]["organization"] == "Beispiel Versicherung AG"
    assert contacts["contacts"][0]["status"] == "active"
    assert "Interne Notiz" not in queried.stdout


def test_contacts_cli_rejects_state_inside_source_tree(tmp_path: Path) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()

    result = run_cli(
        "contacts",
        "plan",
        "--source-dir",
        str(source_dir),
        "--state-dir",
        str(source_dir / ".folderhome-state"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--area",
        "versicherungen",
        "--json",
    )

    assert result.returncode == 2
    assert "nicht überlappen" in json.loads(result.stdout)["error"]
    assert not (source_dir / ".folderhome-state").exists()


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_calendar_plan_cli_builds_read_only_uptoday_ics_handoff(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Dokumente"
    source_dir.mkdir()
    source = source_dir / "Kontrolltermin.txt"
    text = (
        "Termin: Kontrolltermin\n"
        "Datum: 2026-09-14\n"
        "Uhrzeit: 10:30\n"
        "Ende: 11:00\n"
        "Ort: Praxis Beispiel\n"
        "Zeitzone: Europe/Berlin\n"
    )
    source.write_text(text, encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "calendar-config.json"
    config_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.calendar-config.v1",
                "default_backend": "uptoday_ics",
                "default_timezone": "Europe/Berlin",
                "uptoday_ics_directory": "handoff/uptoday",
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"

    common = (
        "--source-dir",
        str(source_dir),
        "--calendar-config",
        str(config_file),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--area",
        "gesundheit",
        "--planned-at",
        "2026-08-22T00:30:00+02:00",
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
    )
    result = run_cli(
        "calendar",
        "plan",
        *common,
        "--json",
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["backend"] == "uptoday_ics"
    assert plan["backend_source"] == "config_default"
    assert plan["connector_invoked"] is False
    assert plan["automatic_calendar_write"] is False
    assert plan["completeness_guaranteed"] is False
    assert len(plan["actions"]) == 1
    assert plan["actions"][0]["status"] == "planned"
    assert plan["actions"][0]["side_effect"] == "new_ics_file"
    assert not Path(plan["actions"][0]["target_path"]).exists()
    assert not state_dir.exists()
    assert source.read_text(encoding="utf-8") == text

    approval_file = tmp_path / "calendar-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.calendar-handoff-approval.v1",
                "approval_id": "calendar_cli",
                "plan_id": plan["plan_id"],
                "calendar_revision": plan["calendar_revision"],
                "action_ids": [plan["actions"][0]["action_id"]],
                "approved_at": "2026-08-22T00:35:00+02:00",
            }
        ),
        encoding="utf-8",
    )
    denied = run_cli(
        "calendar",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--json",
    )

    assert denied.returncode == 2
    assert "State-Freigabe" in json.loads(denied.stdout)["error"]
    assert not state_dir.exists()
    assert not Path(plan["actions"][0]["target_path"]).exists()

    applied = run_cli(
        "calendar",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--approve-state-write",
        "--approve-output-write",
        "--json",
    )

    assert applied.returncode == 0, applied.stderr
    report = json.loads(applied.stdout)
    assert report["status"] == "executed"
    assert report["connector_invoked"] is False
    assert Path(report["items"][0]["output_path"]).is_file()
    assert CalendarStore(state_dir).count_actions() == 1
    assert source.read_text(encoding="utf-8") == text

    listed = run_cli(
        "calendar",
        "list",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--area",
        "gesundheit",
        "--json",
    )

    assert listed.returncode == 0, listed.stderr
    assert json.loads(listed.stdout)["count"] == 0


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_calendar_connector_cli_inventories_plans_and_simulates_without_live_write(
    tmp_path: Path,
) -> None:
    inventory = run_cli("calendar", "connectors", "--json")
    assert inventory.returncode == 0, inventory.stderr
    inventory_payload = json.loads(inventory.stdout)
    assert inventory_payload["schema"] == "folderhome.calendar-connector-inventory.v1"
    assert inventory_payload["connector_invoked"] is False
    assert inventory_payload["live_calendar_written"] is False
    assert {
        item["provider_id"] for item in inventory_payload["providers"]
    } >= {
        "module:uptoday-ics",
        "bundle:routinika",
        "skill:google-calendar",
        "folderhome.synthetic-calendar",
    }

    source_dir = REPO_ROOT / "examples" / "documents" / "calendar"
    source = source_dir / "Kontrolltermin.txt"
    source_before = source.read_bytes()
    state_dir = tmp_path / "calendar-state"
    common = (
        "--source-dir",
        str(source_dir),
        "--calendar-config",
        str(REPO_ROOT / "examples" / "calendar" / "calendar-config-google.json"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--area",
        "gesundheit",
        "--planned-at",
        "2026-08-22T04:20:00+02:00",
        "--approve-sensitive-local-read",
        "--connector-accounts",
        str(REPO_ROOT / "examples" / "calendar" / "connector-accounts.json"),
        "--connector-request",
        str(REPO_ROOT / "examples" / "calendar" / "connector-request-google.json"),
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--use-synthetic-provider",
    )

    planned = run_cli("calendar", "connector-plan", *common, "--json")
    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    assert plan["status"] == "ready"
    assert plan["route"]["provider_id"] == "folderhome.synthetic-calendar"
    assert plan["connector_invoked"] is False
    assert plan["live_calendar_written"] is False
    assert not state_dir.exists()

    denied = run_cli(
        "calendar",
        "connector-simulate",
        *common,
        "--approval-id",
        "calendar-connector-cli",
        "--approved-at",
        "2026-08-22T04:21:00+02:00",
        "--json",
    )
    assert denied.returncode == 2
    assert "Synthetische Kalenderfreigabe fehlt" in json.loads(denied.stdout)["error"]

    simulated = run_cli(
        "calendar",
        "connector-simulate",
        *common,
        "--approval-id",
        "calendar-connector-cli",
        "--approved-at",
        "2026-08-22T04:21:00+02:00",
        "--approve-synthetic-calendar",
        "--json",
    )
    assert simulated.returncode == 0, simulated.stderr
    report = json.loads(simulated.stdout)
    assert report["status"] == "simulated"
    assert report["provider_id"] == "folderhome.synthetic-calendar"
    assert report["network_invoked"] is False
    assert report["live_calendar_written"] is False
    assert len(report["event_references"]) == 1
    assert source.read_bytes() == source_before
    assert not state_dir.exists()


def test_findcall_cli_plans_and_runs_strictly_local_fixture_cascade(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "request.json"
    candidates_file = tmp_path / "candidates.json"
    fixture_file = tmp_path / "fixtures.json"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.findcall-request-input.v1",
                "profile_id": "lukas",
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
                "max_price_eur": 180.0,
            }
        ),
        encoding="utf-8",
    )
    candidates = [
        {
            "candidate_id": f"findcall_candidate_{'a' * 64}",
            "name": "Werkstatt A",
            "phone_e164": "+4915111111111",
            "services": ["Bremsenprüfung Hyundai i10"],
            "distance_km": 4.0,
            "priority": 2,
        },
        {
            "candidate_id": f"findcall_candidate_{'b' * 64}",
            "name": "Werkstatt B",
            "phone_e164": "+4915222222222",
            "services": ["Bremsenprüfung Hyundai i10"],
            "distance_km": 6.0,
            "priority": 1,
        },
    ]
    candidates_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.findcall-candidates.v1",
                "candidates": candidates,
            }
        ),
        encoding="utf-8",
    )
    fixture_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.findcall-fixtures.v1",
                "outcomes": {
                    candidates[0]["candidate_id"]: {
                        "status": "BUSY",
                        "service_confirmed": False,
                        "available": False,
                        "offered_window": None,
                        "price_known": False,
                        "price_eur": None,
                        "commitment_made": False,
                        "summary": "Synthetisch besetzt.",
                    },
                    candidates[1]["candidate_id"]: {
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
                        "summary": "Synthetisches Angebot unter +4915222222222.",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    common = (
        "--request-file",
        str(request_file),
        "--candidates-file",
        str(candidates_file),
        "--planned-at",
        "2026-08-22T01:00:00+02:00",
    )

    planned = run_cli("findcall", "plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    assert "+4915111111111" not in planned.stdout
    assert "+49••••1111" in planned.stdout
    assert json.loads(planned.stdout)["phone_calls_placed"] is False

    simulated = run_cli(
        "findcall",
        "simulate",
        *common,
        "--fixture-file",
        str(fixture_file),
        "--json",
    )

    assert simulated.returncode == 0, simulated.stderr
    report = json.loads(simulated.stdout)
    assert report["success"] is True
    assert report["simulated"] is True
    assert report["network_used"] is False
    assert report["phone_calls_placed"] is False
    assert len(report["attempts"]) == 2
    assert report["attempts"][0]["status"] == "BUSY"
    assert "+4915222222222" not in simulated.stdout
    assert "+49••••2222" in simulated.stdout


def test_findcall_cli_probes_both_pinned_plugins_without_calls() -> None:
    result = run_cli(
        "findcall",
        "plugins",
        "--hungrycall-root",
        str(REPO_ROOT.parent / "hungrycall"),
        "--ringedingeding-root",
        str(REPO_ROOT.parent / "ringedingeding"),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [plugin["plugin_id"] for plugin in payload["plugins"]] == [
        "hungrycall",
        "ringedingeding",
    ]
    assert all(plugin["dry_run_available"] for plugin in payload["plugins"])
    assert all(not plugin["phone_calls_placed"] for plugin in payload["plugins"])


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_finance_cli_imports_statements_and_reports_recurring_costs(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Auszüge"
    source_dir.mkdir()
    for name, start, end, booking, reference in (
        ("Januar", "2026-01-01", "2026-01-31", "2026-01-05", "tx-jan"),
        ("Februar", "2026-02-01", "2026-02-28", "2026-02-05", "tx-feb"),
        ("März", "2026-03-01", "2026-03-31", "2026-03-05", "tx-mar"),
    ):
        opening = {"Januar": 100000, "Februar": 98701, "März": 97402}[name]
        closing = opening - 1299
        (source_dir / f"{name}.txt").write_text(
            (
                "Kontokennung: giro-lukas\n"
                "Institut: Beispielbank\n"
                "Konto-Endung: 1234\n"
                f"Zeitraum: {start} | {end}\n"
                f"Anfangssaldo: {opening} | EUR\n"
                f"Endsaldo: {closing} | EUR\n"
                f"Buchung: {booking} | -1299 | StreamFlix | subscription | "
                f"{reference}\n"
            ),
            encoding="utf-8",
        )
    state_dir = tmp_path / "state"
    common = (
        "--source-dir",
        str(source_dir),
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
    )

    planned = run_cli("finance", "plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    assert len(plan["actions"]) == 3
    assert all(action["status"] == "planned" for action in plan["actions"])
    assert plan["automatic_bank_access"] is False
    assert not state_dir.exists()
    approval_file = tmp_path / "finance-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.finance-import-approval.v1",
                "approval_id": "finance_cli",
                "plan_id": plan["plan_id"],
                "finance_revision": plan["finance_revision"],
                "action_ids": [action["action_id"] for action in plan["actions"]],
                "approved_at": "2026-08-22T01:15:00+02:00",
            }
        ),
        encoding="utf-8",
    )
    denied = run_cli(
        "finance",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--json",
    )
    assert denied.returncode == 2
    assert "State-Freigabe" in json.loads(denied.stdout)["error"]
    assert not state_dir.exists()

    applied = run_cli(
        "finance",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--approve-state-write",
        "--json",
    )

    assert applied.returncode == 0, applied.stderr
    report = json.loads(applied.stdout)
    assert len(report["created_statement_ids"]) == 3
    assert len(report["created_transaction_ids"]) == 3
    assert report["bank_access_performed"] is False

    transactions = run_cli(
        "finance",
        "transactions",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--account",
        "giro-lukas",
        "--json",
    )
    assert transactions.returncode == 0, transactions.stderr
    assert json.loads(transactions.stdout)["count"] == 3

    coverage = run_cli(
        "finance",
        "coverage",
        "--state-dir",
        str(state_dir),
        "--account",
        "giro-lukas",
        "--date-from",
        "2026-01-01",
        "--date-to",
        "2026-03-31",
        "--json",
    )
    assert coverage.returncode == 0, coverage.stderr
    assert json.loads(coverage.stdout)["complete"] is True

    period = run_cli(
        "finance",
        "period",
        "--state-dir",
        str(state_dir),
        "--account",
        "giro-lukas",
        "--date-from",
        "2026-01-01",
        "--date-to",
        "2026-03-31",
        "--json",
    )
    assert period.returncode == 0, period.stderr
    period_payload = json.loads(period.stdout)
    assert period_payload["balance_continuity_verified"] is True
    assert period_payload["opening_balance_cents"] == 100000
    assert period_payload["closing_balance_cents"] == 96103

    recurring = run_cli(
        "finance",
        "recurring",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--as-of",
        "2026-04-10",
        "--json",
    )
    assert recurring.returncode == 0, recurring.stderr
    recurring_payload = json.loads(recurring.stdout)
    assert recurring_payload["contract_status_proven"] is False
    assert recurring_payload["candidates"][0]["monthly_cost_cents"] == 1299
    assert recurring_payload["total_monthly_cost_cents"] == 1299


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_inventory_cli_imports_append_only_stock_and_reports_needs(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Bestand"
    source_dir.mkdir()
    source = source_dir / "Reis.txt"
    source_text = (
        "Gegenstand: Reis\n"
        "Bereich: Küche\n"
        "Ort: Vorratsschrank\n"
        "Einheit: kg\n"
        "Menge: 1.5\n"
        "Mindestbestand: 2\n"
        "Erfasst-am: 2026-08-22\n"
        "Ablaufdatum: 2026-09-05\n"
    )
    source.write_text(source_text, encoding="utf-8")
    state_dir = tmp_path / "state"
    common = (
        "--source-dir",
        str(source_dir),
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
    )

    planned = run_cli("inventory", "plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    selected = [action for action in plan["actions"] if action["status"] == "planned"]
    assert len(selected) == 1
    assert selected[0]["observation"]["quantity"] == "1.5"
    assert plan["automatic_purchase"] is False
    assert not state_dir.exists()

    approval_file = tmp_path / "inventory-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.inventory-import-approval.v1",
                "approval_id": "inventory_cli",
                "plan_id": plan["plan_id"],
                "inventory_revision": plan["inventory_revision"],
                "action_ids": [selected[0]["action_id"]],
                "approved_at": "2026-08-22T02:30:00+02:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    denied = run_cli(
        "inventory",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--json",
    )

    assert denied.returncode == 2
    assert "State-Freigabe" in json.loads(denied.stdout)["error"]
    assert not state_dir.exists()

    applied = run_cli(
        "inventory",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--approve-state-write",
        "--json",
    )

    assert applied.returncode == 0, applied.stderr
    report = json.loads(applied.stdout)
    assert report["status"] == "executed"
    assert len(report["created_event_ids"]) == 1
    assert source.read_text(encoding="utf-8") == source_text

    current = run_cli(
        "inventory",
        "current",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--as-of",
        "2026-08-22",
        "--json",
    )
    assert current.returncode == 0, current.stderr
    current_payload = json.loads(current.stdout)
    assert current_payload["count"] == 1
    assert current_payload["items"][0]["quantity_milli"] == 1500
    assert current_payload["complete_inventory_claimed"] is False

    needs = run_cli(
        "inventory",
        "needs",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--as-of",
        "2026-08-22",
        "--expiry-horizon-days",
        "30",
        "--json",
    )
    assert needs.returncode == 0, needs.stderr
    needs_payload = json.loads(needs.stdout)
    assert needs_payload["automatic_purchase"] is False
    assert needs_payload["candidates"][0]["reasons"] == [
        "below_minimum",
        "expires_soon",
    ]


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_medication_cli_separates_schedule_and_confirmed_intake(tmp_path: Path) -> None:
    source_dir = tmp_path / "Medikamentenpläne"
    source_dir.mkdir()
    source = source_dir / "DemoMed.txt"
    source_text = (
        "Präparat: DemoMed\n"
        "Dosis: 1\n"
        "Dosiseinheit: Tablette\n"
        "Zeitpunkt: 08:00\n"
        "Zeitzone: Europe/Berlin\n"
        "Wochentage: täglich\n"
        "Gültig-von: 2026-08-22\n"
        "Gültig-bis: 2026-12-31\n"
        "Bestandsbereich: Gesundheit\n"
        "Bestandsgegenstand: DemoMed\n"
        "Bestandseinheit: Tablette\n"
    )
    source.write_text(source_text, encoding="utf-8")
    state_dir = tmp_path / "state"
    common = (
        "--source-dir",
        str(source_dir),
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
    )

    planned = run_cli("medication", "plan", *common, "--json")

    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    selected = [item for item in plan["actions"] if item["status"] == "planned"]
    assert len(selected) == 1
    assert plan["medical_advice"] is False
    assert not state_dir.exists()

    approval_file = tmp_path / "medication-approval.json"
    approval_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.medication-import-approval.v1",
                "approval_id": "medication_cli",
                "plan_id": plan["plan_id"],
                "medication_revision": plan["medication_revision"],
                "action_ids": [selected[0]["action_id"]],
                "approved_at": "2026-08-22T03:10:00+02:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    applied = run_cli(
        "medication",
        "apply",
        *common,
        "--approval-file",
        str(approval_file),
        "--approve-state-write",
        "--json",
    )

    assert applied.returncode == 0, applied.stderr
    assert len(json.loads(applied.stdout)["created_schedule_ids"]) == 1
    assert source.read_text(encoding="utf-8") == source_text

    day = run_cli(
        "medication",
        "day",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--date",
        "2026-08-22",
        "--as-of",
        "2026-08-22T09:00:00+02:00",
        "--json",
    )
    assert day.returncode == 0, day.stderr
    day_payload = json.loads(day.stdout)
    dose = day_payload["doses"][0]
    assert dose["status"] == "confirmation_pending"
    assert day_payload["automatic_reminder_sent"] is False

    confirmation_file = tmp_path / "medication-confirmation.json"
    confirmation_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.medication-intake-confirmation.v1",
                "confirmation_id": "medication_cli_taken",
                "medication_revision": day_payload["medication_revision"],
                "dose_id": dose["dose_id"],
                "schedule_id": dose["schedule_id"],
                "scheduled_date": dose["scheduled_date"],
                "confirmed_at": "2026-08-22T08:05:00+02:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    denied = run_cli(
        "medication",
        "confirm",
        "--state-dir",
        str(state_dir),
        "--confirmation-file",
        str(confirmation_file),
        "--json",
    )
    assert denied.returncode == 2
    assert "State-Freigabe" in json.loads(denied.stdout)["error"]

    confirmed = run_cli(
        "medication",
        "confirm",
        "--state-dir",
        str(state_dir),
        "--confirmation-file",
        str(confirmation_file),
        "--approve-state-write",
        "--json",
    )
    assert confirmed.returncode == 0, confirmed.stderr
    assert json.loads(confirmed.stdout)["status"] == "executed"

    history = run_cli(
        "medication",
        "history",
        "--state-dir",
        str(state_dir),
        "--profile",
        "lukas",
        "--json",
    )
    assert history.returncode == 0, history.stderr
    history_payload = json.loads(history.stdout)
    assert len(history_payload["schedules"]) == 1
    assert len(history_payload["intake_events"]) == 1
    assert history_payload["medical_advice"] is False


@pytest.mark.skipif(
    not DOC_SERVICES_ROOT.is_dir(),
    reason="pinned doc-services checkout unavailable",
)
def test_health_dossier_cli_writes_extractive_markdown_and_json(tmp_path: Path) -> None:
    source_dir = tmp_path / "Gesundheitsdokumente"
    source_dir.mkdir()
    first = source_dir / "Hausarzt.txt"
    first.write_text(
        "Dokumenttyp: Arztbericht\n"
        "Dokumentdatum: 2026-01-10\n"
        "Fachbereich: Hausarzt\n"
        "Befund: Blutdruck wurde mit 120/80 dokumentiert.\n"
        "Medikament: DemoMed 1 Tablette morgens.\n"
        "Dokumentierte Angabe: Allergie = keine\n"
        "Offene Frage: Wann ist die nächste Kontrolle?\n",
        encoding="utf-8",
    )
    second = source_dir / "Kardiologie.txt"
    second.write_text(
        "Dokumenttyp: Arztbericht\n"
        "Dokumentdatum: 2026-06-20\n"
        "Fachbereich: Kardiologie\n"
        "Befund: Ein Ruhe-EKG wurde durchgeführt.\n"
        "Termin: 2026-09-03 10:30 Europe/Berlin | Kontrolltermin\n"
        "Dokumentierte Angabe: Allergie = Penicillin\n",
        encoding="utf-8",
    )
    output_markdown = tmp_path / "Gesundheitsdossier.md"
    output_json = tmp_path / "Gesundheitsdossier.json"
    arguments = (
        "health",
        "dossier",
        "--source-dir",
        str(source_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--profile",
        "lukas",
        "--as-of",
        "2026-08-22",
        "--gap-threshold-days",
        "90",
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--output-markdown",
        str(output_markdown),
        "--output-json",
        str(output_json),
        "--json",
    )

    denied = run_cli(*(item for item in arguments if item != "--approve-sensitive-local-read"))
    assert denied.returncode == 2
    assert "Sensitivitätsfreigabe" in json.loads(denied.stdout)["error"]
    assert not output_markdown.exists()
    assert not output_json.exists()

    result = run_cli(*arguments)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "folderhome.health-dossier.v1"
    assert payload["profile_id"] == "lukas"
    assert len(payload["timeline"]) == 7
    assert payload["conflicts"][0]["field"] == "Allergie"
    assert payload["coverage"]["missing_periods"][0]["days_without_document"] == 161
    assert payload["medical_advice"] is False
    assert payload["completeness_claimed"] is False
    assert payload["remote_provider_invoked"] is False
    assert output_markdown.read_text(encoding="utf-8") == payload["markdown"]
    assert json.loads(output_json.read_text(encoding="utf-8")) == payload
    assert first.read_text(encoding="utf-8").startswith("Dokumenttyp: Arztbericht")

    repeated = run_cli(*arguments)
    assert repeated.returncode == 2
    assert "existiert bereits" in json.loads(repeated.stdout)["error"]


@pytest.mark.skipif(
    not (DOC_SERVICES_ROOT.is_dir() and KNOWLEDGE_DIGEST_ROOT.is_dir()),
    reason="pinned document provider checkouts unavailable",
)
def test_contract_cockpit_cli_combines_versions_and_keeps_state_read_only(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "Versicherungen"
    source_dir.mkdir()
    old = source_dir / "KFZ_Hyundai_i10_2025.txt"
    old.write_text(
        "KFZ Versicherung für Hyundai i10. Gültig ab 01.01.2025. "
        "Der synthetische Beitrag beträgt 400 Euro.",
        encoding="utf-8",
    )
    new = source_dir / "KFZ_Hyundai_i10_2026.txt"
    new.write_text(
        "KFZ Versicherung für Hyundai i10. Gültig ab 01.01.2026. "
        "Der synthetische Beitrag beträgt 420 Euro.",
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    ingested = run_cli(
        "documents",
        "ingest",
        "--source-dir",
        str(source_dir),
        "--state-dir",
        str(state_dir),
        "--approve-index-write",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--json",
    )
    assert ingested.returncode == 0, ingested.stderr
    request_file = tmp_path / "cockpit-request.json"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.contract-cockpit-request.v1",
                "profile_id": "lukas",
                "area": "versicherungen",
                "display_name": "KFZ-Versicherung Hyundai i10",
                "document_query": "KFZ Versicherung Hyundai i10",
                "object_ref": "Hyundai i10",
                "counterparty_terms": ["Beispiel Versicherung"],
                "calendar_terms": ["Hyundai i10", "KFZ-Versicherung"],
                "account_refs": ["giro-lukas"],
                "coverage_start": "2026-01-01",
                "as_of": "2026-08-22",
                "archive_older_versions": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_markdown = tmp_path / "Vertragscockpit.md"
    output_json = tmp_path / "Vertragscockpit.json"
    state_before = {
        path.relative_to(state_dir).as_posix(): path.read_bytes()
        for path in state_dir.rglob("*")
        if path.is_file()
    }
    arguments = (
        "contracts",
        "cockpit",
        "--request-file",
        str(request_file),
        "--state-dir",
        str(state_dir),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--approve-sensitive-local-read",
        "--doc-services-root",
        str(DOC_SERVICES_ROOT),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--output-markdown",
        str(output_markdown),
        "--output-json",
        str(output_json),
        "--json",
    )

    denied = run_cli(*(item for item in arguments if item != "--approve-sensitive-local-read"))
    assert denied.returncode == 2
    assert "Sensitivitätsfreigabe" in json.loads(denied.stdout)["error"]
    assert not output_markdown.exists()
    assert not output_json.exists()

    result = run_cli(*arguments)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "folderhome.contract-cockpit.v1"
    assert payload["latest_version"]["document"]["filename"] == new.name
    assert [item["document"]["filename"] for item in payload["older_versions"]] == [
        old.name
    ]
    assert len(payload["archive_proposals"]) == 1
    assert payload["archive_proposals"][0]["gate"]["granted"] is False
    assert payload["automatic_archive_executed"] is False
    assert payload["read_only"] is True
    assert payload["contract_status_proven"] is False
    assert {item["component"] for item in payload["component_issues"]} == {
        "contacts",
        "costs",
        "calendar",
    }
    assert payload["finance_coverages"][0]["complete"] is False
    assert payload["finance_coverages"][0]["gaps"] == [
        {"start_date": "2026-01-01", "end_date": "2026-08-22"}
    ]
    assert "text" not in payload["latest_version"]["document"]
    assert output_markdown.read_text(encoding="utf-8") == payload["markdown"]
    assert json.loads(output_json.read_text(encoding="utf-8")) == payload
    state_after = {
        path.relative_to(state_dir).as_posix(): path.read_bytes()
        for path in state_dir.rglob("*")
        if path.is_file()
    }
    assert state_after == state_before
    assert not (source_dir / "Archiv").exists()

    repeated = run_cli(*arguments)
    assert repeated.returncode == 2
    assert "existiert bereits" in json.loads(repeated.stdout)["error"]


def test_correspondence_cli_previews_then_writes_only_with_both_gates(
    tmp_path: Path,
) -> None:
    designs_file = tmp_path / "designs.json"
    designs_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.letter-designs.v1",
                "default_design_id": "classic",
                "designs": [
                    {
                        "design_id": "classic",
                        "display_name": "Klassisch",
                        "page_size": "A4",
                        "margins_mm": [20, 20, 20, 20],
                        "font_family": "Arial",
                        "font_size_pt": 11,
                        "accent_color": "#234567",
                        "header_text": "Privatkorrespondenz",
                        "footer_text": "Vertraulich",
                    }
                ],
                "bindings": {
                    "areas": {},
                    "purposes": {},
                    "profiles": {},
                    "profile_purposes": {},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    templates_file = tmp_path / "templates.json"
    templates_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.letter-templates.v1",
                "templates": [
                    {
                        "template_id": "insurance-cancellation",
                        "display_name": "Versicherung kündigen",
                        "purpose": "kuendigung",
                        "subject": "Kündigung {policy_number}",
                        "salutation": "Sehr geehrte Damen und Herren,",
                        "paragraphs": [
                            "hiermit kündige ich den Vertrag für {vehicle} zum "
                            "{termination_date}."
                        ],
                        "closing": "Mit freundlichen Grüßen",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    request_file = tmp_path / "request.json"
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
                    "email": None,
                    "phone": None,
                },
                "recipient": {
                    "name": "Beispiel Versicherung AG",
                    "address_lines": ["Versicherungsplatz 2", "54321 Beispielstadt"],
                    "email": None,
                    "phone": None,
                },
                "variables": {
                    "policy_number": "SYN-4711",
                    "vehicle": "Hyundai i10",
                    "termination_date": "31.12.2026",
                },
                "attachments": [],
                "evidence_refs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    common = (
        "--request-file",
        str(request_file),
        "--designs-file",
        str(designs_file),
        "--templates-file",
        str(templates_file),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--json",
    )

    denied = run_cli("correspondence", "preview", *common)
    assert denied.returncode == 2
    assert "Sensitivitätsfreigabe" in json.loads(denied.stdout)["error"]

    preview = run_cli(
        "correspondence",
        "preview",
        *common,
        "--approve-sensitive-local-read",
    )
    assert preview.returncode == 0, preview.stderr
    preview_payload = json.loads(preview.stdout)
    assert preview_payload["read_only"] is True
    assert preview_payload["design"]["design_id"] == "classic"
    assert "Kündigung SYN-4711" in preview_payload["markdown"]
    assert {item["status"] for item in preview_payload["render_handoffs"]} == {
        "blocked"
    }
    assert all(
        item["provider_invoked"] is False
        for item in preview_payload["render_handoffs"]
    )

    markdown_file = tmp_path / "Brief.md"
    text_file = tmp_path / "Brief.txt"
    render_arguments = (
        "correspondence",
        "render",
        *common,
        "--approve-sensitive-local-read",
        "--markdown-file",
        str(markdown_file),
        "--text-file",
        str(text_file),
    )
    write_denied = run_cli(*render_arguments)
    assert write_denied.returncode == 2
    assert "Output-Freigabe" in json.loads(write_denied.stdout)["error"]
    assert not markdown_file.exists()
    assert not text_file.exists()

    rendered = run_cli(*render_arguments, "--approve-output-write")
    assert rendered.returncode == 0, rendered.stderr
    rendered_payload = json.loads(rendered.stdout)
    assert rendered_payload["status"] == "executed"
    assert rendered_payload["provider_invoked"] is False
    assert markdown_file.read_text(encoding="utf-8") == preview_payload["markdown"]
    assert text_file.read_text(encoding="utf-8") == preview_payload["text"]

    repeated = run_cli(*render_arguments, "--approve-output-write")
    assert repeated.returncode == 2
    assert "existiert bereits" in json.loads(repeated.stdout)["error"]


def test_artifact_studio_cli_plans_and_writes_only_local_design_outputs(
    tmp_path: Path,
) -> None:
    common_plan = (
        "artifacts",
        "plan",
        "--request-file",
        str(REPO_ROOT / "examples" / "artifacts" / "artifact-request.json"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--json",
    )
    denied_plan = run_cli(*common_plan)
    assert denied_plan.returncode == 2
    assert "Sensitivitätsfreigabe" in json.loads(denied_plan.stdout)["error"]

    planned = run_cli(*common_plan, "--approve-sensitive-local-read")
    assert planned.returncode == 0, planned.stderr
    plan_payload = json.loads(planned.stdout)
    routes = {
        item["artifact_kind"]: item for item in plan_payload["routes"]
    }
    assert routes["presentation"]["provider_id"] == "skill:pptx"
    assert routes["presentation"]["status"] == "blocked"
    assert routes["spreadsheet"]["status"] == "blocked"
    assert routes["document"]["status"] == "blocked"
    assert routes["design_set"]["status"] == "ready"
    assert routes["business_card"]["status"] == "review_required"
    assert routes["media"]["provider_id"] == "module:ai-media-editor"
    assert plan_payload["provider_invoked"] is False

    design_request = REPO_ROOT / "examples" / "artifacts" / "design-request.json"
    common_design = (
        "--request-file",
        str(design_request),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--approve-sensitive-local-read",
        "--json",
    )
    preview = run_cli("artifacts", "design-preview", *common_design)
    assert preview.returncode == 0, preview.stderr
    preview_payload = json.loads(preview.stdout)
    assert preview_payload["read_only"] is True
    assert preview_payload["visual_qa_passed"] is False
    assert "Lukas Grüner" in preview_payload["business_card_svg"]

    json_file = tmp_path / "design" / "design-set.json"
    css_file = tmp_path / "design" / "design-set.css"
    svg_file = tmp_path / "design" / "visitenkarte.svg"
    render = (
        "artifacts",
        "design-render",
        *common_design,
        "--json-file",
        str(json_file),
        "--css-file",
        str(css_file),
        "--business-card-file",
        str(svg_file),
    )
    denied_render = run_cli(*render)
    assert denied_render.returncode == 2
    assert "Output-Freigabe" in json.loads(denied_render.stdout)["error"]
    assert not json_file.exists()

    rendered = run_cli(*render, "--approve-output-write")
    assert rendered.returncode == 0, rendered.stderr
    output_payload = json.loads(rendered.stdout)
    assert output_payload["status"] == "executed"
    assert output_payload["visual_qa_passed"] is False
    assert output_payload["remote_provider_invoked"] is False
    assert json_file.is_file() and css_file.is_file() and svg_file.is_file()

    repeated = run_cli(*render, "--approve-output-write")
    assert repeated.returncode == 2
    assert "existiert bereits" in json.loads(repeated.stdout)["error"]


def test_mail_cli_inventories_providers_and_plans_without_provider_call() -> None:
    providers = run_cli("mail", "providers", "--json")
    assert providers.returncode == 0, providers.stderr
    inventory = json.loads(providers.stdout)
    assert inventory["schema"] == "folderhome.mail-provider-inventory.v1"
    assert inventory["smtp_live_transport"] == "not_implemented"
    assert inventory["mailbox_mutations_in_ingest"] is False
    assert {
        item["provider_id"] for item in inventory["providers"]
    } >= {
        "mailprocessor",
        "universal-docs-grabber",
        "universal-mail-cleaner",
        "universal-invoice-mail",
        "folderhome.synthetic-mail",
    }

    common = (
        "mail",
        "ingest-plan",
        "--accounts-file",
        str(REPO_ROOT / "examples" / "mail" / "accounts.json"),
        "--request-file",
        str(REPO_ROOT / "examples" / "mail" / "ingest-request.json"),
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--json",
    )
    denied = run_cli(*common)
    assert denied.returncode == 2
    assert "Sensitivitätsfreigabe" in json.loads(denied.stdout)["error"]

    planned = run_cli(
        *common,
        "--approve-sensitive-local-read",
        "--use-synthetic-provider",
    )
    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["status"] == "ready"
    assert payload["provider_id"] == "folderhome.synthetic-mail"
    assert payload["mailbox_mutations"] == []
    assert payload["provider_invoked"] is False


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_ollama_cli_plans_loopback_provider_without_gates_or_model_call(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    planned = run_cli(
        "agent",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "ollama",
        "--ollama-model-id",
        "qwen3.8:27b-mlx",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["model_call_performed"] is False
    assert payload["settings"]["model_provider"] == "ollama"
    assert payload["settings"]["ollama_host"] == "http://127.0.0.1:11434"
    assert payload["settings"]["ollama_model_id"] == "qwen3.8:27b-mlx"
    assert payload["settings"]["network_used"] is False
    assert payload["settings"]["allow_network"] is False


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_ollama_cli_refuses_remote_host_without_both_gates(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    arguments = (
        "agent",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--state-dir",
        str(state_dir),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "ollama",
        "--ollama-host",
        "http://192.0.2.10:11434",
        "--ollama-model-id",
        "qwen3.8:27b-mlx",
    )

    blocked = run_cli(*arguments, "--json")
    approved = run_cli(
        *arguments,
        "--allow-network",
        "--approve-sensitive-cloud-data",
        "--json",
    )

    assert blocked.returncode == 2
    assert "Netzwerkfreigabe" in json.loads(blocked.stdout)["error"]
    assert approved.returncode == 0, approved.stderr
    settings = json.loads(approved.stdout)["settings"]
    assert settings["network_used"] is True
    assert settings["ollama_host"] == "http://192.0.2.10:11434"


def test_mcp_plan_cli_describes_both_editor_integrations_read_only() -> None:
    planned = run_cli(
        "mcp",
        "plan",
        "--access-url",
        "http://127.0.0.1:8765/?token=cli-plan-token",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["schema"] == "folderhome.mcp-integration-plan.v1"
    assert payload["transport"] == "stdio"
    assert payload["network_scope"] == "loopback_only"
    assert payload["own_application_instance"] is False
    assert payload["server_started"] is False
    assert payload["requires_running_app_serve"] is True
    assert "claude mcp add folderhome" in payload["claude_code_command"]
    assert "[mcp_servers.folderhome]" in payload["codex_config_toml"]
    assert "folderhome_confirm_plan" in payload["tools"]


def test_mcp_serve_cli_fails_closed_and_keeps_stdout_free_for_the_transport() -> None:
    ungated = run_cli(
        "mcp",
        "serve",
        "--access-url",
        "http://127.0.0.1:8765/?token=cli-serve-token",
    )
    remote = run_cli(
        "mcp",
        "serve",
        "--access-url",
        "http://192.0.2.10:8765/?token=cli-serve-token",
        "--approve-mcp-server",
    )

    assert ungated.returncode == 2
    assert ungated.stdout == ""
    assert "--approve-mcp-server" in json.loads(ungated.stderr)["error"]
    assert remote.returncode == 2
    assert remote.stdout == ""
    assert "127.0.0.1" in json.loads(remote.stderr)["error"]


@pytest.mark.skipif(
    not KNOWLEDGE_DIGEST_ROOT.is_dir(),
    reason="pinned KnowledgeDigest checkout unavailable",
)
def test_launch_config_supplies_defaults_but_never_a_gate(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    launch = tmp_path / "launch.json"
    launch.write_text(
        json.dumps(
            {
                "schema": "folderhome.launch-config.v1",
                "profiles_dir": str(REPO_ROOT / "examples" / "profiles"),
                "state_dir": str(state_dir),
                "port": 8791,
                "model_provider": "ollama",
                "ollama_host": "http://127.0.0.1:11434",
                "ollama_model_id": "qwen3.8:27b-mlx",
                "allow_network": True,
                "approve_sensitive_cloud_data": True,
                "approve_loopback_server": True,
            }
        ),
        encoding="utf-8",
    )

    planned = run_cli(
        "app",
        "plan",
        "--launch-config",
        str(launch),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--json",
    )
    overridden = run_cli(
        "app",
        "plan",
        "--launch-config",
        str(launch),
        "--knowledge-digest-root",
        str(KNOWLEDGE_DIGEST_ROOT),
        "--model-provider",
        "fixture",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["settings"]["port"] == 8791
    assert payload["agent"]["model_provider"] == "ollama"
    assert payload["agent"]["model_connection"]["model_id"] == "qwen3.8:27b-mlx"
    # Gates are start-up flags and are never read from the file.
    assert payload["agent"]["model_connection"]["network_authorized"] is False
    assert payload["agent"]["model_connection"][
        "sensitive_cloud_data_authorized"
    ] is False

    assert overridden.returncode == 0, overridden.stderr
    assert json.loads(overridden.stdout)["agent"]["model_provider"] == "fixture"


def test_app_plan_without_profiles_dir_or_launch_config_fails_closed() -> None:
    missing = run_cli("app", "plan", "--json")

    assert missing.returncode == 2
    assert "--profiles-dir" in json.loads(missing.stdout)["error"]


def test_setup_cli_plans_read_only_and_refuses_a_listener_without_the_gate(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"

    planned = run_cli(
        "setup",
        "plan",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--config-dir",
        str(config_dir),
        "--json",
    )
    ungated = run_cli(
        "setup",
        "serve",
        "--profiles-dir",
        str(REPO_ROOT / "examples" / "profiles"),
        "--config-dir",
        str(config_dir),
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["schema"] == "folderhome.setup-state.v1"
    assert payload["configured"] is False
    assert payload["writes_credentials"] is False
    # Planning stays read-only: it does not even create the configuration folder.
    assert not config_dir.exists()
    assert ungated.returncode == 2
    assert "Serverfreigabe" in json.loads(ungated.stdout)["error"]
