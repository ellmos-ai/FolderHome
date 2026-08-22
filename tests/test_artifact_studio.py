import json
from pathlib import Path

import pytest

from folderhome.application.artifact_studio import (
    ArtifactStudioError,
    build_artifact_studio_plan,
    build_design_preview,
    load_artifact_request,
    load_design_request,
    write_design_outputs,
)


def _write_artifact_request(tmp_path: Path) -> Path:
    path = tmp_path / "artifact-request.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.artifact-studio-request.v1",
                "request_id": "family-overview",
                "profile_id": "lukas",
                "purpose": "Haushaltsüberblick für die Familie",
                "title": "FolderHome Familienüberblick",
                "artifact_kinds": [
                    "presentation",
                    "spreadsheet",
                    "document",
                    "odt",
                    "design_set",
                    "business_card",
                    "media",
                ],
                "source_refs": ["doc_" + "a" * 64],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_design_request(tmp_path: Path) -> Path:
    path = tmp_path / "design-request.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.design-studio-request.v1",
                "profile_id": "lukas",
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
                "fonts": {
                    "heading": "Arial",
                    "body": "Arial",
                },
                "business_card": {
                    "name": "Lukas Grüner",
                    "role": "Familienorganisation",
                    "organization": "FolderHome",
                    "email": "lukas@example.invalid",
                    "phone": "+49 000 000000",
                    "website": "https://example.invalid",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_artifact_studio_routes_existing_skills_and_modules_without_invocation(
    tmp_path: Path,
) -> None:
    request = load_artifact_request(_write_artifact_request(tmp_path))

    plan = build_artifact_studio_plan(
        request,
        office_visual_renderer_available=False,
        spreadsheet_workspace_loader_available=False,
        ai_media_editor_revision="4e4c79d8c16a117bf69c0f72ad946575110a6b84",
        ai_media_editor_clean=True,
        ai_media_editor_tests_passed=45,
    )

    routes = {item.artifact_kind: item for item in plan.routes}
    assert routes["presentation"].provider_id == "skill:pptx"
    assert routes["presentation"].status == "blocked"
    assert routes["spreadsheet"].provider_id == "skill:Spreadsheets"
    assert routes["spreadsheet"].status == "blocked"
    assert routes["document"].provider_id == "skill:documents"
    assert routes["document"].status == "blocked"
    assert routes["odt"].provider_id is None
    assert routes["odt"].status == "blocked"
    assert routes["design_set"].provider_id == "folderhome:design-studio"
    assert routes["design_set"].status == "ready"
    assert routes["business_card"].status == "review_required"
    assert routes["media"].provider_revision == (
        "4e4c79d8c16a117bf69c0f72ad946575110a6b84"
    )
    assert routes["media"].status == "review_required"
    assert plan.provider_invoked is False
    assert plan.side_effects == ()


def test_design_preview_is_deterministic_accessible_and_escapes_svg(tmp_path: Path) -> None:
    request_file = _write_design_request(tmp_path)
    payload = json.loads(request_file.read_text(encoding="utf-8"))
    payload["business_card"]["organization"] = "FolderHome & Familie <lokal>"
    request_file.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    request = load_design_request(request_file)

    preview = build_design_preview(request)
    repeated = build_design_preview(request)

    assert preview.preview_id == repeated.preview_id
    assert preview.read_only is True
    assert preview.visual_qa_passed is False
    assert preview.remote_provider_invoked is False
    assert "Lukas Grüner" in preview.business_card_svg
    assert "FolderHome &amp; Familie &lt;lokal&gt;" in preview.business_card_svg
    assert "--folderhome-primary: #17324D;" in preview.design_css
    assert preview.contrast_checks == (
        ("text_on_background", True),
        ("text_on_primary", True),
    )


def test_design_request_rejects_low_contrast_and_unknown_fields(tmp_path: Path) -> None:
    request_file = _write_design_request(tmp_path)
    payload = json.loads(request_file.read_text(encoding="utf-8"))
    payload["colors"]["text"] = "#F8F4EC"
    request_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactStudioError, match="Kontrast"):
        build_design_preview(load_design_request(request_file))

    payload["colors"]["text"] = "#1B1D20"
    payload["unexpected"] = "silent schema drift"
    request_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactStudioError, match="unbekannte Felder"):
        load_design_request(request_file)

    payload.pop("unexpected")
    payload["fonts"]["heading"] = "Arial; }</style><script>unsafe</script>"
    request_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactStudioError, match="Designschrift"):
        load_design_request(request_file)


def test_design_output_requires_gate_never_overwrites_and_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = build_design_preview(load_design_request(_write_design_request(tmp_path)))
    json_file = tmp_path / "output" / "design-set.json"
    css_file = tmp_path / "output" / "design-set.css"
    svg_file = tmp_path / "output" / "visitenkarte.svg"

    with pytest.raises(ArtifactStudioError, match="Output-Freigabe"):
        write_design_outputs(
            preview,
            json_file=json_file,
            css_file=css_file,
            business_card_file=svg_file,
            allow_output_write=False,
        )
    assert not json_file.exists()

    report = write_design_outputs(
        preview,
        json_file=json_file,
        css_file=css_file,
        business_card_file=svg_file,
        allow_output_write=True,
    )
    assert report.status == "executed"
    assert json.loads(json_file.read_text(encoding="utf-8"))["schema"] == (
        "folderhome.design-set.v1"
    )
    assert css_file.read_text(encoding="utf-8") == preview.design_css
    assert svg_file.read_text(encoding="utf-8") == preview.business_card_svg

    before = {path: path.read_bytes() for path in (json_file, css_file, svg_file)}
    with pytest.raises(ArtifactStudioError, match="existiert bereits"):
        write_design_outputs(
            preview,
            json_file=json_file,
            css_file=css_file,
            business_card_file=svg_file,
            allow_output_write=True,
        )
    assert {path: path.read_bytes() for path in before} == before

    rollback_root = tmp_path / "rollback"
    original_fsync = __import__("folderhome.application.artifact_studio", fromlist=["os"]).os.fsync
    calls = 0

    def fail_second_fsync(file_descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetischer zweiter Schreibfehler")
        original_fsync(file_descriptor)

    monkeypatch.setattr(
        "folderhome.application.artifact_studio.os.fsync",
        fail_second_fsync,
    )
    with pytest.raises(OSError, match="synthetischer"):
        write_design_outputs(
            preview,
            json_file=rollback_root / "design-set.json",
            css_file=rollback_root / "design-set.css",
            business_card_file=rollback_root / "visitenkarte.svg",
            allow_output_write=True,
        )
    assert not any(rollback_root.glob("*"))
