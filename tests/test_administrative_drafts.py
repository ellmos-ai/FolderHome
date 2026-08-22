from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.administrative_drafts import (
    AdministrativeDraftError,
    build_administrative_draft_plan,
    load_administrative_draft_request,
    write_administrative_draft,
)
from folderhome.application.correspondence import load_correspondence_configuration
from folderhome.application.official_notices import analyze_official_notice
from folderhome.contracts import (
    AdministrativeDraftApproval,
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


class SyntheticExtractor:
    provider_revision = "synthetic-notice-v1"

    def extract(self, source_path: Path) -> DocumentRecord:
        digest = sha256(source_path.read_bytes()).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, digest),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=digest,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-08-22T06:00:00+02:00",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-notice",
            extraction_method="direct",
            privacy_status=PrivacyStatus.REVIEW_REQUIRED,
            privacy_summary="Synthetischer Bescheid.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _notice_analysis(tmp_path: Path, *, legal_remedy: str = "Widerspruch"):
    source = tmp_path / "Bescheid.txt"
    source.write_text(
        "\n".join(
            (
                "SYNTHETISCHER BESCHEID",
                "Bescheidart: Ablehnungsbescheid",
                "Behörde: Beispiel-Jobcenter",
                "Aktenzeichen: JC-SYNTH-2026-001",
                "Bescheiddatum: 2026-08-10",
                "Entscheidung: Der synthetische Antrag wird abgelehnt.",
                f"Rechtsbehelf: {legal_remedy}",
                "Fristtext: Innerhalb eines Monats nach Bekanntgabe.",
                "Explizites Fristdatum: 2026-09-15",
            )
        ),
        encoding="utf-8",
    )
    return analyze_official_notice(
        source,
        profile_id="lukas",
        received_on="2026-08-15",
        as_of="2026-08-22T06:00:00+02:00",
        extractor=SyntheticExtractor(),
        allow_sensitive_local_read=True,
    )


def _configuration(tmp_path: Path):
    designs = tmp_path / "designs.json"
    designs.write_text(
        json.dumps(
            {
                "schema": "folderhome.letter-designs.v1",
                "default_design_id": "formal",
                "designs": [
                    {
                        "design_id": "formal",
                        "display_name": "Formell",
                        "page_size": "A4",
                        "margins_mm": [25, 20, 25, 20],
                        "font_family": "Liberation Serif",
                        "font_size_pt": 11,
                        "accent_color": "#333333",
                        "header_text": "Behördenkorrespondenz",
                        "footer_text": "Entwurf",
                    }
                ],
                "bindings": {
                    "areas": {"sozialrecht": "formal"},
                    "purposes": {},
                    "profiles": {},
                    "profile_purposes": {},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    templates = tmp_path / "templates.json"
    templates.write_text(
        json.dumps(
            {
                "schema": "folderhome.letter-templates.v1",
                "templates": [
                    {
                        "template_id": "official-objection-draft",
                        "display_name": "Widerspruchsentwurf",
                        "purpose": "widerspruchsentwurf",
                        "subject": (
                            "Widerspruchsentwurf zu {notice_type} vom "
                            "{notice_date}, {file_reference}"
                        ),
                        "salutation": "Sehr geehrte Damen und Herren,",
                        "paragraphs": [
                            "hiermit erhebe ich Widerspruch gegen den bezeichneten Bescheid.",
                            "Von mir bereitgestellte Angaben: {user_statements}",
                            "Mein gewünschtes Ergebnis: {requested_outcome}",
                            "{review_notice}",
                        ],
                        "closing": "Mit freundlichen Grüßen",
                    },
                    {
                        "template_id": "official-response-draft",
                        "display_name": "Antwortentwurf",
                        "purpose": "behoerdenantwortentwurf",
                        "subject": (
                            "Antwortentwurf zu {notice_type} vom "
                            "{notice_date}, {file_reference}"
                        ),
                        "salutation": "Sehr geehrte Damen und Herren,",
                        "paragraphs": [
                            "zu dem bezeichneten Bescheid teile ich Folgendes mit:",
                            "Von mir bereitgestellte Angaben: {user_statements}",
                            "Mein gewünschtes Ergebnis: {requested_outcome}",
                            "{review_notice}",
                        ],
                        "closing": "Mit freundlichen Grüßen",
                    },
                    {
                        "template_id": "benefit-application-draft",
                        "display_name": "Antragsentwurf",
                        "purpose": "leistungsantragsentwurf",
                        "subject": "Antragsentwurf: {requested_outcome}",
                        "salutation": "Sehr geehrte Damen und Herren,",
                        "paragraphs": [
                            "hiermit beantrage ich: {requested_outcome}",
                            "Von mir bereitgestellte Angaben: {user_statements}",
                            "{review_notice}",
                        ],
                        "closing": "Mit freundlichen Grüßen",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return load_correspondence_configuration(designs, templates)


def _request_file(
    tmp_path: Path,
    *,
    draft_kind: str = "objection",
    source_sha256: str | None,
) -> Path:
    request = tmp_path / f"{draft_kind}.json"
    request.write_text(
        json.dumps(
            {
                "schema": "folderhome.administrative-draft-request.v1",
                "draft_kind": draft_kind,
                "profile_id": "lukas",
                "created_on": "2026-08-22",
                "sender": {
                    "name": "Lukas Beispiel",
                    "address_lines": ["Musterweg 1", "12345 Beispielstadt"],
                    "email": "lukas@example.invalid",
                    "phone": None,
                },
                "recipient": {
                    "name": "Beispiel-Jobcenter",
                    "address_lines": ["Musterstraße 1", "12345 Beispielstadt"],
                    "email": None,
                    "phone": None,
                },
                "requested_outcome": "erneute Prüfung der eingereichten Unterlage",
                "user_statements": [
                    "Die Unterlage wurde am 2026-08-05 eingereicht."
                ],
                "attachments": ["Kopie der synthetischen Unterlage"],
                "expected_notice_source_sha256": source_sha256,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return request


def _plan(tmp_path: Path):
    analysis = _notice_analysis(tmp_path)
    request = load_administrative_draft_request(
        _request_file(tmp_path, source_sha256=analysis.source_sha256)
    )
    plan = build_administrative_draft_plan(
        request,
        notice_analysis=analysis,
        correspondence_configuration=_configuration(tmp_path),
        report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        report_forge_distribution_version="1.1.4",
        report_forge_runtime_version="1.1.0",
    )
    return analysis, plan


def test_objection_draft_reuses_notice_evidence_and_correspondence(tmp_path: Path) -> None:
    analysis, plan = _plan(tmp_path)

    assert plan.status == "review_required"
    assert plan.notice_analysis_id == analysis.analysis_id
    assert plan.correspondence_preview.template.template_id == "official-objection-draft"
    assert "Widerspruchsentwurf" in plan.correspondence_preview.subject
    assert "ENTWURF" in plan.correspondence_preview.markdown
    assert any(item.basis == "document_evidence" for item in plan.facts)
    assert any(item.basis == "user_provided" for item in plan.facts)
    assert plan.legal_review_status == "not_performed"
    assert plan.deadline_legally_calculated is False
    assert plan.human_confirmation_required is True
    assert plan.send_supported is False
    assert plan.to_dict()["external_actions"] == []


def test_objection_requires_printed_widerspruch_and_matching_authority(
    tmp_path: Path,
) -> None:
    analysis = _notice_analysis(tmp_path, legal_remedy="Klage")
    request = load_administrative_draft_request(
        _request_file(tmp_path, source_sha256=analysis.source_sha256)
    )
    with pytest.raises(AdministrativeDraftError, match="Widerspruch"):
        build_administrative_draft_plan(
            request,
            notice_analysis=analysis,
            correspondence_configuration=_configuration(tmp_path),
            report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
            report_forge_distribution_version="1.1.4",
            report_forge_runtime_version="1.1.0",
        )

    payload = json.loads(
        _request_file(tmp_path, source_sha256=analysis.source_sha256).read_text(
            encoding="utf-8"
        )
    )
    payload["recipient"]["name"] = "Andere Behörde"
    request_file = tmp_path / "wrong-authority.json"
    request_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AdministrativeDraftError, match="Empfänger"):
        build_administrative_draft_plan(
            load_administrative_draft_request(request_file),
            notice_analysis=analysis,
            correspondence_configuration=_configuration(tmp_path),
            report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
            report_forge_distribution_version="1.1.4",
            report_forge_runtime_version="1.1.0",
        )


def test_application_draft_uses_only_user_confirmed_facts(tmp_path: Path) -> None:
    request = load_administrative_draft_request(
        _request_file(tmp_path, draft_kind="benefit_application", source_sha256=None)
    )
    plan = build_administrative_draft_plan(
        request,
        notice_analysis=None,
        correspondence_configuration=_configuration(tmp_path),
        report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        report_forge_distribution_version="1.1.4",
        report_forge_runtime_version="1.1.0",
    )

    assert plan.notice_analysis_id is None
    assert {item.basis for item in plan.facts} == {"user_provided"}
    assert plan.correspondence_preview.template.template_id == "benefit-application-draft"
    assert "Antragsentwurf" in plan.correspondence_preview.subject
    assert plan.eligibility_assessed is False


def test_draft_output_requires_exact_confirmation_and_never_sends(tmp_path: Path) -> None:
    _, plan = _plan(tmp_path)
    with pytest.raises(ValueError, match="boolesche"):
        AdministrativeDraftApproval.create(
            plan_id=plan.plan_id,
            markdown_sha256=plan.correspondence_preview.markdown_sha256,
            text_sha256=plan.correspondence_preview.text_sha256,
            approved_at="2026-08-22T06:30:00+02:00",
            confirmed_content_review="yes",  # type: ignore[arg-type]
            confirmed_no_legal_review=True,
            allow_local_output_write=True,
        )
    approval = AdministrativeDraftApproval.create(
        plan_id=plan.plan_id,
        markdown_sha256=plan.correspondence_preview.markdown_sha256,
        text_sha256=plan.correspondence_preview.text_sha256,
        approved_at="2026-08-22T06:30:00+02:00",
        confirmed_content_review=True,
        confirmed_no_legal_review=True,
        allow_local_output_write=True,
    )
    markdown_file = tmp_path / "out" / "Widerspruchsentwurf.md"
    text_file = tmp_path / "out" / "Widerspruchsentwurf.txt"

    with pytest.raises(AdministrativeDraftError, match="Output-Gate"):
        write_administrative_draft(
            plan,
            approval,
            markdown_file=markdown_file,
            text_file=text_file,
            allow_output_write=False,
        )
    report = write_administrative_draft(
        plan,
        approval,
        markdown_file=markdown_file,
        text_file=text_file,
        allow_output_write=True,
    )

    assert report.status == "executed"
    assert report.sent is False
    assert report.external_actions_performed is False
    assert "nicht rechtlich geprüft" in markdown_file.read_text(encoding="utf-8")
    with pytest.raises(AdministrativeDraftError, match="existiert bereits"):
        write_administrative_draft(
            plan,
            approval,
            markdown_file=markdown_file,
            text_file=text_file,
            allow_output_write=True,
        )


def test_changed_notice_source_blocks_confirmed_draft_output(tmp_path: Path) -> None:
    analysis, plan = _plan(tmp_path)
    approval = AdministrativeDraftApproval.create(
        plan_id=plan.plan_id,
        markdown_sha256=plan.correspondence_preview.markdown_sha256,
        text_sha256=plan.correspondence_preview.text_sha256,
        approved_at="2026-08-22T06:30:00+02:00",
        confirmed_content_review=True,
        confirmed_no_legal_review=True,
        allow_local_output_write=True,
    )
    analysis.source_path.write_text("geändert", encoding="utf-8")

    with pytest.raises(AdministrativeDraftError, match="Quellhash"):
        write_administrative_draft(
            plan,
            approval,
            markdown_file=tmp_path / "draft.md",
            text_file=tmp_path / "draft.txt",
            allow_output_write=True,
        )
