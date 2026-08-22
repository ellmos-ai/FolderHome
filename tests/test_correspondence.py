from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.application.correspondence import (
    CorrespondenceError,
    build_correspondence_preview,
    load_correspondence_configuration,
    load_correspondence_request,
    write_correspondence_outputs,
)


def _write_configuration(tmp_path: Path) -> tuple[Path, Path]:
    designs_file = tmp_path / "designs.json"
    designs_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.letter-designs.v1",
                "default_design_id": "classic",
                "designs": [
                    {
                        "design_id": "classic",
                        "display_name": "FolderHome Klassisch",
                        "page_size": "A4",
                        "margins_mm": [20, 20, 20, 20],
                        "font_family": "Aptos",
                        "font_size_pt": 11,
                        "accent_color": "#24415A",
                        "header_text": "",
                        "footer_text": "Privater Brief",
                    },
                    {
                        "design_id": "formal",
                        "display_name": "Formell",
                        "page_size": "A4",
                        "margins_mm": [25, 20, 25, 20],
                        "font_family": "Liberation Serif",
                        "font_size_pt": 11,
                        "accent_color": "#111111",
                        "header_text": "Korrespondenz",
                        "footer_text": "",
                    },
                    {
                        "design_id": "lukas-insurance",
                        "display_name": "Lukas Versicherung",
                        "page_size": "A4",
                        "margins_mm": [22, 20, 22, 20],
                        "font_family": "Aptos",
                        "font_size_pt": 11,
                        "accent_color": "#005A78",
                        "header_text": "Versicherungsangelegenheiten",
                        "footer_text": "Bitte um schriftliche Bestätigung",
                    },
                ],
                "bindings": {
                    "areas": {"versicherungen": "formal"},
                    "purposes": {"kuendigung": "formal"},
                    "profiles": {"lukas": "classic"},
                    "profile_purposes": {
                        "lukas|kuendigung": "lukas-insurance"
                    },
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
                        "subject": "Kündigung der KFZ-Versicherung {policy_number}",
                        "salutation": "Sehr geehrte Damen und Herren,",
                        "paragraphs": [
                            "hiermit kündige ich die Versicherung für {vehicle} "
                            "fristgerecht zum {termination_date}.",
                            "Bitte bestätigen Sie mir die Kündigung und das "
                            "Vertragsende schriftlich.",
                        ],
                        "closing": "Mit freundlichen Grüßen",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return designs_file, templates_file


def _write_request(tmp_path: Path) -> Path:
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
                    "email": "lukas@example.invalid",
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
                    "termination_date": "31.12.2026"
                },
                "attachments": ["Versicherungsschein in Kopie"],
                "evidence_refs": ["doc_" + "a" * 64],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return request_file


def test_correspondence_resolves_profile_purpose_design_and_renders_umlauts(
    tmp_path: Path,
) -> None:
    designs_file, templates_file = _write_configuration(tmp_path)
    request_file = _write_request(tmp_path)
    configuration = load_correspondence_configuration(designs_file, templates_file)
    request = load_correspondence_request(request_file)

    preview = build_correspondence_preview(
        request,
        configuration=configuration,
        report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        report_forge_distribution_version="1.1.4",
        report_forge_runtime_version="1.1.0",
    )

    assert preview.design.design_id == "lukas-insurance"
    assert preview.design_resolution == (
        "default:classic",
        "area:versicherungen=formal",
        "purpose:kuendigung=formal",
        "profile:lukas=classic",
        "profile_purpose:lukas|kuendigung=lukas-insurance",
    )
    assert preview.subject == "Kündigung der KFZ-Versicherung SYN-4711"
    assert preview.paragraphs[0] == (
        "hiermit kündige ich die Versicherung für Hyundai i10 fristgerecht "
        "zum 31.12.2026."
    )
    assert "Sehr geehrte Damen und Herren," in preview.markdown
    assert "Mit freundlichen Grüßen" in preview.text
    assert "Bitte um schriftliche Bestätigung" in preview.markdown
    assert preview.read_only is True
    handoffs = {item.format: item for item in preview.render_handoffs}
    assert handoffs["docx"].status == "blocked"
    assert "1.1.4" in handoffs["docx"].reason
    assert "1.1.0" in handoffs["docx"].reason
    assert handoffs["odt"].status == "blocked"
    assert all(item.provider_invoked is False for item in handoffs.values())
    assert preview.to_dict()["contains_sensitive_data"] is True


def test_correspondence_rejects_missing_extra_and_unsafe_placeholders(
    tmp_path: Path,
) -> None:
    designs_file, templates_file = _write_configuration(tmp_path)
    request_file = _write_request(tmp_path)
    configuration = load_correspondence_configuration(designs_file, templates_file)
    payload = json.loads(request_file.read_text(encoding="utf-8"))
    del payload["variables"]["vehicle"]
    request_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CorrespondenceError, match="vehicle"):
        build_correspondence_preview(
            load_correspondence_request(request_file),
            configuration=configuration,
            report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
            report_forge_distribution_version="1.1.4",
            report_forge_runtime_version="1.1.0",
        )

    payload["variables"]["vehicle"] = "Hyundai i10"
    payload["variables"]["nicht_verwendet"] = "darf nicht still verschwinden"
    request_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CorrespondenceError, match="nicht_verwendet"):
        build_correspondence_preview(
            load_correspondence_request(request_file),
            configuration=configuration,
            report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
            report_forge_distribution_version="1.1.4",
            report_forge_runtime_version="1.1.0",
        )

    templates = json.loads(templates_file.read_text(encoding="utf-8"))
    templates["templates"][0]["subject"] = "Kündigung {policy_number.__class__}"
    templates_file.write_text(json.dumps(templates), encoding="utf-8")
    with pytest.raises(CorrespondenceError, match="Platzhalter"):
        load_correspondence_configuration(designs_file, templates_file)


def test_correspondence_output_gate_never_overwrites_and_rolls_back_batch(
    tmp_path: Path,
) -> None:
    designs_file, templates_file = _write_configuration(tmp_path)
    configuration = load_correspondence_configuration(designs_file, templates_file)
    preview = build_correspondence_preview(
        load_correspondence_request(_write_request(tmp_path)),
        configuration=configuration,
        report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        report_forge_distribution_version="1.1.4",
        report_forge_runtime_version="1.1.0",
    )
    markdown_file = tmp_path / "output" / "Kündigung.md"
    text_file = tmp_path / "output" / "Kündigung.txt"

    with pytest.raises(CorrespondenceError, match="Output-Freigabe"):
        write_correspondence_outputs(
            preview,
            markdown_file=markdown_file,
            text_file=text_file,
            allow_output_write=False,
        )
    assert not markdown_file.exists()
    assert not text_file.exists()

    report = write_correspondence_outputs(
        preview,
        markdown_file=markdown_file,
        text_file=text_file,
        allow_output_write=True,
    )
    assert report.status == "executed"
    assert markdown_file.read_text(encoding="utf-8") == preview.markdown
    assert text_file.read_text(encoding="utf-8") == preview.text
    assert report.markdown_sha256
    assert report.text_sha256
    assert report.provider_invoked is False

    before = {markdown_file: markdown_file.read_bytes(), text_file: text_file.read_bytes()}
    with pytest.raises(CorrespondenceError, match="existiert bereits"):
        write_correspondence_outputs(
            preview,
            markdown_file=markdown_file,
            text_file=tmp_path / "output" / "neu.txt",
            allow_output_write=True,
        )
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / "output" / "neu.txt").exists()


def test_correspondence_configuration_rejects_unknown_design_binding(
    tmp_path: Path,
) -> None:
    designs_file, templates_file = _write_configuration(tmp_path)
    payload = json.loads(designs_file.read_text(encoding="utf-8"))
    payload["bindings"]["profiles"]["hanna"] = "fehlt"
    designs_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CorrespondenceError, match="fehlt"):
        load_correspondence_configuration(designs_file, templates_file)
