"""Plan existing artifact providers and render local reusable design assets."""

from __future__ import annotations

import json
import os
from hashlib import sha256
from html import escape
from pathlib import Path

from folderhome.contracts.artifact_studio import (
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


class ArtifactStudioError(RuntimeError):
    """Raised when an artifact plan or local design output is unsafe."""


def load_artifact_request(path: Path) -> ArtifactStudioRequest:
    payload = _load_json_object(path, "Artefaktanfrage")
    _strict_fields(
        payload,
        {
            "schema",
            "request_id",
            "profile_id",
            "purpose",
            "title",
            "artifact_kinds",
            "source_refs",
        },
        "Artefaktanfrage",
    )
    if payload.get("schema") != ArtifactStudioRequest.SCHEMA:
        raise ArtifactStudioError("Artefaktanfrage verwendet ein unbekanntes Schema.")
    try:
        return ArtifactStudioRequest(
            request_id=_text(payload, "request_id", "Artefaktanfrage"),
            profile_id=_text(payload, "profile_id", "Artefaktanfrage"),
            purpose=_text(payload, "purpose", "Artefaktanfrage"),
            title=_text(payload, "title", "Artefaktanfrage"),
            artifact_kinds=_text_list(payload, "artifact_kinds"),
            source_refs=_text_list(payload, "source_refs", allow_empty=True),
        )
    except ValueError as exc:
        raise ArtifactStudioError(f"Artefaktanfrage ist ungültig: {exc}") from exc


def build_artifact_studio_plan(
    request: ArtifactStudioRequest,
    *,
    office_visual_renderer_available: bool,
    spreadsheet_workspace_loader_available: bool,
    ai_media_editor_revision: str,
    ai_media_editor_clean: bool,
    ai_media_editor_tests_passed: int,
) -> ArtifactStudioPlan:
    routes = tuple(
        _route_for(
            kind,
            office_visual_renderer_available=office_visual_renderer_available,
            spreadsheet_workspace_loader_available=(
                spreadsheet_workspace_loader_available
            ),
            ai_media_editor_revision=ai_media_editor_revision,
            ai_media_editor_clean=ai_media_editor_clean,
            ai_media_editor_tests_passed=ai_media_editor_tests_passed,
        )
        for kind in request.artifact_kinds
    )
    material = {
        "request": request.to_dict(),
        "routes": [route.to_dict() for route in routes],
    }
    return ArtifactStudioPlan(
        plan_id=f"artifact_plan_{_json_hash(material)}",
        request=request,
        routes=routes,
    )


def load_design_request(path: Path) -> DesignStudioRequest:
    payload = _load_json_object(path, "Designanfrage")
    _strict_fields(
        payload,
        {
            "schema",
            "profile_id",
            "design_set_id",
            "display_name",
            "purpose",
            "colors",
            "fonts",
            "business_card",
        },
        "Designanfrage",
    )
    if payload.get("schema") != DesignStudioRequest.SCHEMA:
        raise ArtifactStudioError("Designanfrage verwendet ein unbekanntes Schema.")
    colors = _object(payload, "colors", "Designanfrage")
    fonts = _object(payload, "fonts", "Designanfrage")
    card = _object(payload, "business_card", "Designanfrage")
    _strict_fields(
        colors,
        {"primary", "on_primary", "background", "text", "accent"},
        "Designfarben",
    )
    _strict_fields(fonts, {"heading", "body"}, "Designschriften")
    _strict_fields(
        card,
        {"name", "role", "organization", "email", "phone", "website"},
        "Visitenkarte",
    )
    try:
        return DesignStudioRequest(
            profile_id=_text(payload, "profile_id", "Designanfrage"),
            design_set_id=_text(payload, "design_set_id", "Designanfrage"),
            display_name=_text(payload, "display_name", "Designanfrage"),
            purpose=_text(payload, "purpose", "Designanfrage"),
            colors=DesignColors(
                primary=_text(colors, "primary", "Designfarben"),
                on_primary=_text(colors, "on_primary", "Designfarben"),
                background=_text(colors, "background", "Designfarben"),
                text=_text(colors, "text", "Designfarben"),
                accent=_text(colors, "accent", "Designfarben"),
            ),
            fonts=DesignFonts(
                heading=_text(fonts, "heading", "Designschriften"),
                body=_text(fonts, "body", "Designschriften"),
            ),
            business_card=BusinessCardContent(
                name=_text(card, "name", "Visitenkarte"),
                role=_text(card, "role", "Visitenkarte"),
                organization=_text(card, "organization", "Visitenkarte"),
                email=_nullable_text(card, "email", "Visitenkarte"),
                phone=_nullable_text(card, "phone", "Visitenkarte"),
                website=_nullable_text(card, "website", "Visitenkarte"),
            ),
        )
    except ValueError as exc:
        raise ArtifactStudioError(f"Designanfrage ist ungültig: {exc}") from exc


def build_design_preview(request: DesignStudioRequest) -> DesignPreview:
    colors = request.colors.to_dict()
    checks = (
        (
            "text_on_background",
            _contrast_ratio(colors["text"], colors["background"]) >= 4.5,
        ),
        (
            "text_on_primary",
            _contrast_ratio(colors["on_primary"], colors["primary"]) >= 4.5,
        ),
    )
    if not all(passed for _, passed in checks):
        raise ArtifactStudioError(
            "Designset unterschreitet den erforderlichen WCAG-Kontrast von 4,5:1."
        )
    design_set = {
        "schema": "folderhome.design-set.v1",
        "design_set_id": request.design_set_id,
        "display_name": request.display_name,
        "purpose": request.purpose,
        "profile_id": request.profile_id,
        "colors": colors,
        "fonts": request.fonts.to_dict(),
        "contrast_checks": [
            {"check": name, "passed": passed} for name, passed in checks
        ],
    }
    design_set_json = json.dumps(
        design_set,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    design_css = _design_css(request)
    business_card_svg = _business_card_svg(request)
    json_sha256 = _text_hash(design_set_json)
    css_sha256 = _text_hash(design_css)
    svg_sha256 = _text_hash(business_card_svg)
    preview_material = {
        "request": request.to_dict(),
        "json_sha256": json_sha256,
        "css_sha256": css_sha256,
        "svg_sha256": svg_sha256,
    }
    return DesignPreview(
        preview_id=f"design_preview_{_json_hash(preview_material)}",
        request=request,
        design_set_json=design_set_json,
        design_css=design_css,
        business_card_svg=business_card_svg,
        contrast_checks=checks,
        json_sha256=json_sha256,
        css_sha256=css_sha256,
        svg_sha256=svg_sha256,
    )


def write_design_outputs(
    preview: DesignPreview,
    *,
    json_file: Path,
    css_file: Path,
    business_card_file: Path,
    allow_output_write: bool,
) -> DesignOutputReport:
    if not allow_output_write:
        raise ArtifactStudioError(
            "Output-Freigabe fehlt; Designset wurde nicht geschrieben."
        )
    paths = tuple(path.resolve() for path in (json_file, css_file, business_card_file))
    if len(set(paths)) != len(paths):
        raise ArtifactStudioError("Designausgaben benötigen drei verschiedene Pfade.")
    for path in paths:
        if path.exists():
            raise ArtifactStudioError(f"Ausgabedatei existiert bereits: {path}")
        if path.is_symlink() or path.parent.is_symlink():
            raise ArtifactStudioError("Designausgabe darf keinen symbolischen Link nutzen.")
    created: list[tuple[Path, str]] = []
    try:
        for path, content, digest in (
            (paths[0], preview.design_set_json, preview.json_sha256),
            (paths[1], preview.design_css, preview.css_sha256),
            (paths[2], preview.business_card_svg, preview.svg_sha256),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                created.append((path, digest))
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if _file_hash(path) != digest:
                raise ArtifactStudioError(f"Ausgabehash stimmt nicht: {path}")
    except BaseException:
        for path, digest in reversed(created):
            if path.is_file() and not path.is_symlink() and _file_hash(path) == digest:
                path.unlink()
        raise
    report_material = {
        "preview_id": preview.preview_id,
        "paths": [str(path) for path in paths],
        "hashes": [preview.json_sha256, preview.css_sha256, preview.svg_sha256],
    }
    return DesignOutputReport(
        report_id=f"design_output_{_json_hash(report_material)}",
        preview_id=preview.preview_id,
        status="executed",
        json_file=paths[0],
        css_file=paths[1],
        business_card_file=paths[2],
        json_sha256=preview.json_sha256,
        css_sha256=preview.css_sha256,
        svg_sha256=preview.svg_sha256,
    )


def _route_for(
    kind: str,
    *,
    office_visual_renderer_available: bool,
    spreadsheet_workspace_loader_available: bool,
    ai_media_editor_revision: str,
    ai_media_editor_clean: bool,
    ai_media_editor_tests_passed: int,
) -> ArtifactRoute:
    if kind == "presentation":
        status = "review_required" if office_visual_renderer_available else "blocked"
        reason = (
            "PPTX-Skill ist vorhanden; Inhalts-, Render- und visuelle Prüfung bleiben Pflicht."
            if office_visual_renderer_available
            else "PPTX-Skill ist vorhanden, aber der visuelle Office-Renderer soffice fehlt."
        )
        return ArtifactRoute(
            kind,
            "skill:pptx",
            None,
            status,
            reason,
            ("approve_artifact_generation", "visual_qa"),
        )
    if kind == "spreadsheet":
        status = (
            "review_required" if spreadsheet_workspace_loader_available else "blocked"
        )
        reason = (
            "Spreadsheet-Skill und Workspace-Abhängigkeiten sind verfügbar; Formeln und "
            "visuelle Ausgabe müssen geprüft werden."
            if spreadsheet_workspace_loader_available
            else "Spreadsheet-Skill ist vorhanden, aber sein Workspace-Dependency-Loader fehlt."
        )
        return ArtifactRoute(
            kind,
            "skill:Spreadsheets",
            None,
            status,
            reason,
            ("approve_artifact_generation", "formula_qa", "visual_qa"),
        )
    if kind == "document":
        status = "review_required" if office_visual_renderer_available else "blocked"
        reason = (
            "Documents-Skill ist vorhanden; strukturelle und visuelle DOCX-Prüfung bleiben Pflicht."
            if office_visual_renderer_available
            else "Documents-Skill ist vorhanden; soffice und die visuelle DOCX-Abnahme fehlen. "
            "report-forge bleibt zusätzlich wegen Versionsdrift blockiert."
        )
        return ArtifactRoute(
            kind,
            "skill:documents",
            None,
            status,
            reason,
            ("approve_artifact_generation", "visual_qa"),
        )
    if kind == "odt":
        return ArtifactRoute(
            kind,
            None,
            None,
            "blocked",
            "Kein revisionsgebundener ODT-Renderer mit visueller Abnahme ist verfügbar.",
            ("provider_binding", "visual_qa"),
        )
    if kind == "design_set":
        return ArtifactRoute(
            kind,
            "folderhome:design-studio",
            None,
            "ready",
            "FolderHome kann zugängliche JSON-/CSS-Designtokens lokal erzeugen.",
            ("approve_sensitive_local_read", "approve_output_write"),
        )
    if kind == "business_card":
        return ArtifactRoute(
            kind,
            "folderhome:design-studio",
            None,
            "review_required",
            "FolderHome kann eine lokale SVG-Vorschau erzeugen; Druckfreigabe und "
            "visuelle Endabnahme bleiben menschlich.",
            ("approve_sensitive_local_read", "approve_output_write", "visual_qa"),
        )
    if kind == "media":
        healthy = (
            ai_media_editor_clean
            and ai_media_editor_tests_passed > 0
            and len(ai_media_editor_revision) == 40
        )
        return ArtifactRoute(
            kind,
            "module:ai-media-editor",
            ai_media_editor_revision,
            "review_required" if healthy else "blocked",
            (
                f"ai-media-editor ist sauber und mit {ai_media_editor_tests_passed} Tests "
                "verifiziert; reale Medien und Schnittstrategie benötigen eigene Freigaben."
                if healthy
                else "ai-media-editor ist nicht als sauberer, getesteter Provider belegt."
            ),
            ("approve_media_read", "approve_edit_strategy", "approve_output_write"),
        )
    raise ArtifactStudioError(f"Unbekannte Artefaktart: {kind}")


def _design_css(request: DesignStudioRequest) -> str:
    colors = request.colors.to_dict()
    return (
        ":root {\n"
        f"  --folderhome-primary: {colors['primary']};\n"
        f"  --folderhome-on-primary: {colors['on_primary']};\n"
        f"  --folderhome-background: {colors['background']};\n"
        f"  --folderhome-text: {colors['text']};\n"
        f"  --folderhome-accent: {colors['accent']};\n"
        f"  --folderhome-font-heading: \"{request.fonts.heading}\";\n"
        f"  --folderhome-font-body: \"{request.fonts.body}\";\n"
        "}\n"
    )


def _business_card_svg(request: DesignStudioRequest) -> str:
    colors = request.colors.to_dict()
    card = request.business_card
    initials = "".join(part[0] for part in card.name.split()[:2]).upper()
    contact_lines = [item for item in (card.email, card.phone, card.website) if item]
    contact_svg = "\n".join(
        f'  <text x="360" y="{390 + index * 42}" class="contact">{escape(item)}</text>'
        for index, item in enumerate(contact_lines)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="600" '
        'viewBox="0 0 1050 600" role="img" aria-labelledby="title desc">\n'
        f"  <title id=\"title\">Visitenkarte {escape(card.name)}</title>\n"
        f"  <desc id=\"desc\">{escape(request.purpose)}</desc>\n"
        "  <style>\n"
        f"    .name {{ font: 700 58px {escape(request.fonts.heading)}; fill: {colors['text']}; }}\n"
        f"    .meta {{ font: 32px {escape(request.fonts.body)}; fill: {colors['text']}; }}\n"
        f"    .contact {{ font: 26px {escape(request.fonts.body)}; fill: {colors['text']}; }}\n"
        f"    .initials {{ font: 700 88px {escape(request.fonts.heading)}; "
        f"fill: {colors['on_primary']}; }}\n"
        "  </style>\n"
        f"  <rect width=\"1050\" height=\"600\" fill=\"{colors['background']}\"/>\n"
        f"  <rect width=\"290\" height=\"600\" fill=\"{colors['primary']}\"/>\n"
        f"  <circle cx=\"145\" cy=\"245\" r=\"92\" fill=\"{colors['accent']}\"/>\n"
        "  <text x=\"145\" y=\"274\" text-anchor=\"middle\" "
        f"class=\"initials\">{escape(initials)}</text>\n"
        f"  <text x=\"360\" y=\"170\" class=\"name\">{escape(card.name)}</text>\n"
        f"  <text x=\"360\" y=\"232\" class=\"meta\">{escape(card.role)}</text>\n"
        f"  <text x=\"360\" y=\"282\" class=\"meta\">{escape(card.organization)}</text>\n"
        f"{contact_svg}\n"
        "</svg>\n"
    )


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: str) -> float:
    values = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ArtifactStudioError(f"{label} fehlt oder ist kein reguläres File: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactStudioError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactStudioError(f"{label} muss ein JSON-Objekt sein.")
    return payload


def _strict_fields(payload: dict[str, object], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload).difference(allowed))
    if unknown:
        raise ArtifactStudioError(f"{label} enthält unbekannte Felder: {unknown[0]}")


def _object(payload: dict[str, object], field: str, label: str) -> dict[str, object]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ArtifactStudioError(f"{label}.{field} muss ein Objekt sein.")
    return value


def _text(payload: dict[str, object], field: str, label: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ArtifactStudioError(f"{label} benötigt das Textfeld {field}.")
    return value.strip()


def _nullable_text(
    payload: dict[str, object],
    field: str,
    label: str,
) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ArtifactStudioError(f"{label}.{field} muss Text oder null sein.")
    return value.strip()


def _text_list(
    payload: dict[str, object],
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ArtifactStudioError(f"{field} muss eine Textliste sein.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ArtifactStudioError(f"{field} enthält einen ungültigen Eintrag.")
    return tuple(item.strip() for item in value)


def _text_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()
