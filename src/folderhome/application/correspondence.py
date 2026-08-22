"""Template-bound, deterministic household correspondence previews and outputs."""

from __future__ import annotations

import json
import os
import string
from hashlib import sha256
from pathlib import Path

from folderhome.contracts.correspondence import (
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

_PLACEHOLDER_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


class CorrespondenceError(RuntimeError):
    """Raised when correspondence configuration, rendering, or output is unsafe."""


def load_correspondence_configuration(
    designs_path: Path,
    templates_path: Path,
) -> CorrespondenceConfiguration:
    """Load and cross-check immutable letter designs, bindings, and templates."""

    designs_payload = _load_json_object(designs_path, label="Briefdesigns")
    templates_payload = _load_json_object(templates_path, label="Briefvorlagen")
    if designs_payload.get("schema") != "folderhome.letter-designs.v1":
        raise CorrespondenceError("Briefdesigns verwenden ein unbekanntes Schema.")
    if templates_payload.get("schema") != "folderhome.letter-templates.v1":
        raise CorrespondenceError("Briefvorlagen verwenden ein unbekanntes Schema.")
    designs_raw = designs_payload.get("designs")
    templates_raw = templates_payload.get("templates")
    if not isinstance(designs_raw, list) or not designs_raw:
        raise CorrespondenceError("Briefdesigns benötigen eine nichtleere designs-Liste.")
    if not isinstance(templates_raw, list) or not templates_raw:
        raise CorrespondenceError("Briefvorlagen benötigen eine nichtleere templates-Liste.")
    designs = tuple(_parse_design(item, index) for index, item in enumerate(designs_raw))
    templates = tuple(
        _parse_template(item, index) for index, item in enumerate(templates_raw)
    )
    design_ids = [item.design_id for item in designs]
    template_ids = [item.template_id for item in templates]
    if len(design_ids) != len(set(design_ids)):
        raise CorrespondenceError("Briefdesign-IDs müssen eindeutig sein.")
    if len(template_ids) != len(set(template_ids)):
        raise CorrespondenceError("Briefvorlagen-IDs müssen eindeutig sein.")
    default_design_id = _text(designs_payload, "default_design_id", "Briefdesigns")
    if default_design_id not in set(design_ids):
        raise CorrespondenceError(
            f"Standard-Briefdesign verweist auf unbekanntes Design {default_design_id}."
        )
    bindings_raw = designs_payload.get("bindings")
    if not isinstance(bindings_raw, dict):
        raise CorrespondenceError("Briefdesigns benötigen ein bindings-Objekt.")
    bindings = DesignBindings(
        areas=_binding_pairs(bindings_raw, "areas"),
        purposes=_binding_pairs(bindings_raw, "purposes"),
        profiles=_binding_pairs(bindings_raw, "profiles"),
        profile_purposes=_binding_pairs(bindings_raw, "profile_purposes"),
    )
    for _, design_id in (
        *bindings.areas,
        *bindings.purposes,
        *bindings.profiles,
        *bindings.profile_purposes,
    ):
        if design_id not in set(design_ids):
            raise CorrespondenceError(
                f"Briefdesign-Bindung verweist auf unbekanntes Design {design_id}."
            )
    return CorrespondenceConfiguration(
        designs_path=designs_path,
        templates_path=templates_path,
        default_design_id=default_design_id,
        designs=designs,
        bindings=bindings,
        templates=templates,
    )


def load_correspondence_request(path: Path) -> CorrespondenceRequest:
    payload = _load_json_object(path, label="Korrespondenzanfrage")
    if payload.get("schema") != CorrespondenceRequest.SCHEMA:
        raise CorrespondenceError("Korrespondenzanfrage verwendet ein unbekanntes Schema.")
    variables = payload.get("variables")
    if not isinstance(variables, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in variables.items()
    ):
        raise CorrespondenceError("Korrespondenzanfrage benötigt Textvariablen.")
    try:
        return CorrespondenceRequest(
            profile_id=_text(payload, "profile_id", "Korrespondenzanfrage"),
            area=_text(payload, "area", "Korrespondenzanfrage"),
            purpose=_text(payload, "purpose", "Korrespondenzanfrage"),
            template_id=_text(payload, "template_id", "Korrespondenzanfrage"),
            created_on=_text(payload, "created_on", "Korrespondenzanfrage"),
            sender=_parse_party(payload.get("sender"), label="Absender"),
            recipient=_parse_party(payload.get("recipient"), label="Empfänger"),
            variables=tuple(sorted(variables.items())),
            attachments=_text_list(payload, "attachments", allow_empty=True),
            evidence_refs=_text_list(payload, "evidence_refs", allow_empty=True),
        )
    except (TypeError, ValueError) as exc:
        raise CorrespondenceError(f"Korrespondenzanfrage ist ungültig: {exc}") from exc


def build_correspondence_preview(
    request: CorrespondenceRequest,
    *,
    configuration: CorrespondenceConfiguration,
    report_forge_revision: str,
    report_forge_distribution_version: str,
    report_forge_runtime_version: str,
) -> CorrespondencePreview:
    """Render Markdown/TXT in memory and describe blocked richer format handoffs."""

    template = next(
        (item for item in configuration.templates if item.template_id == request.template_id),
        None,
    )
    if template is None:
        raise CorrespondenceError(f"Unbekannte Briefvorlage: {request.template_id}")
    if template.purpose != request.purpose:
        raise CorrespondenceError("Briefvorlage und Anfragezweck stimmen nicht überein.")
    design, resolution = _resolve_design(request, configuration)
    variables = dict(request.variables)
    missing = sorted(set(template.placeholders).difference(variables))
    extra = sorted(set(variables).difference(template.placeholders))
    if missing:
        raise CorrespondenceError(f"Briefvariable fehlt: {missing[0]}")
    if extra:
        raise CorrespondenceError(f"Briefvariable wird nicht verwendet: {extra[0]}")
    try:
        subject = template.subject.format_map(variables)
        salutation = template.salutation.format_map(variables)
        paragraphs = tuple(item.format_map(variables) for item in template.paragraphs)
        closing = template.closing.format_map(variables)
    except (KeyError, ValueError) as exc:
        raise CorrespondenceError(f"Briefvorlage konnte nicht gefüllt werden: {exc}") from exc
    markdown = _render_markdown(
        request,
        design=design,
        subject=subject,
        salutation=salutation,
        paragraphs=paragraphs,
        closing=closing,
    )
    text = _render_text(
        request,
        design=design,
        subject=subject,
        salutation=salutation,
        paragraphs=paragraphs,
        closing=closing,
    )
    markdown_sha256 = _text_hash(markdown)
    text_sha256 = _text_hash(text)
    preview_material = {
        "request": request.to_dict(),
        "template_id": template.template_id,
        "design_id": design.design_id,
        "resolution": list(resolution),
        "markdown_sha256": markdown_sha256,
        "text_sha256": text_sha256,
    }
    preview_id = f"correspondence_preview_{_json_hash(preview_material)}"
    handoffs = _render_handoffs(
        preview_id=preview_id,
        report_forge_revision=report_forge_revision,
        report_forge_distribution_version=report_forge_distribution_version,
        report_forge_runtime_version=report_forge_runtime_version,
    )
    return CorrespondencePreview(
        preview_id=preview_id,
        request=request,
        template=template,
        design=design,
        design_resolution=resolution,
        subject=subject,
        salutation=salutation,
        paragraphs=paragraphs,
        closing=closing,
        markdown=markdown,
        text=text,
        markdown_sha256=markdown_sha256,
        text_sha256=text_sha256,
        render_handoffs=handoffs,
    )


def write_correspondence_outputs(
    preview: CorrespondencePreview,
    *,
    markdown_file: Path,
    text_file: Path,
    allow_output_write: bool,
) -> CorrespondenceOutputReport:
    """Publish a two-file output batch with gate, preflight, and owned rollback."""

    if not allow_output_write:
        raise CorrespondenceError("Output-Freigabe fehlt; es wurde kein Brief geschrieben.")
    markdown_path = markdown_file.resolve()
    text_path = text_file.resolve()
    if markdown_path == text_path:
        raise CorrespondenceError("Markdown- und TXT-Ausgabe benötigen verschiedene Pfade.")
    for path in (markdown_path, text_path):
        if path.exists():
            raise CorrespondenceError(f"Ausgabedatei existiert bereits: {path}")
        if path.is_symlink() or path.parent.is_symlink():
            raise CorrespondenceError("Korrespondenzausgabe darf keinen symbolischen Link nutzen.")
    created: list[tuple[Path, str]] = []
    try:
        for path, content, digest in (
            (markdown_path, preview.markdown, preview.markdown_sha256),
            (text_path, preview.text, preview.text_sha256),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if _file_hash(path) != digest:
                raise CorrespondenceError(f"Ausgabehash stimmt nicht: {path}")
            created.append((path, digest))
    except BaseException:
        for path, digest in reversed(created):
            if path.is_file() and not path.is_symlink() and _file_hash(path) == digest:
                path.unlink()
        raise
    report_material = {
        "preview_id": preview.preview_id,
        "markdown_file": str(markdown_path),
        "text_file": str(text_path),
        "markdown_sha256": preview.markdown_sha256,
        "text_sha256": preview.text_sha256,
    }
    return CorrespondenceOutputReport(
        report_id=f"correspondence_output_{_json_hash(report_material)}",
        preview_id=preview.preview_id,
        status="executed",
        markdown_file=markdown_path,
        text_file=text_path,
        markdown_sha256=preview.markdown_sha256,
        text_sha256=preview.text_sha256,
    )


def _parse_design(value: object, index: int) -> LetterDesign:
    if not isinstance(value, dict):
        raise CorrespondenceError(f"Briefdesign {index} muss ein Objekt sein.")
    margins = value.get("margins_mm")
    if not isinstance(margins, list) or len(margins) != 4 or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in margins
    ):
        raise CorrespondenceError(f"Briefdesign {index} benötigt vier ganzzahlige Ränder.")
    font_size = value.get("font_size_pt")
    if isinstance(font_size, bool) or not isinstance(font_size, (int, float)):
        raise CorrespondenceError(f"Briefdesign {index} benötigt font_size_pt.")
    try:
        return LetterDesign(
            design_id=_text(value, "design_id", f"Briefdesign {index}"),
            display_name=_text(value, "display_name", f"Briefdesign {index}"),
            page_size=_text(value, "page_size", f"Briefdesign {index}"),
            margins_mm=tuple(margins),
            font_family=_text(value, "font_family", f"Briefdesign {index}"),
            font_size_pt=float(font_size),
            accent_color=_text(value, "accent_color", f"Briefdesign {index}"),
            header_text=_optional_text(value, "header_text"),
            footer_text=_optional_text(value, "footer_text"),
        )
    except ValueError as exc:
        raise CorrespondenceError(f"Briefdesign {index} ist ungültig: {exc}") from exc


def _parse_template(value: object, index: int) -> LetterTemplate:
    if not isinstance(value, dict):
        raise CorrespondenceError(f"Briefvorlage {index} muss ein Objekt sein.")
    paragraphs = _text_list(value, "paragraphs", allow_empty=False)
    strings = (
        _text(value, "subject", f"Briefvorlage {index}"),
        _text(value, "salutation", f"Briefvorlage {index}"),
        *paragraphs,
        _text(value, "closing", f"Briefvorlage {index}"),
    )
    placeholders = _validate_and_collect_placeholders(strings)
    try:
        return LetterTemplate(
            template_id=_text(value, "template_id", f"Briefvorlage {index}"),
            display_name=_text(value, "display_name", f"Briefvorlage {index}"),
            purpose=_text(value, "purpose", f"Briefvorlage {index}"),
            subject=strings[0],
            salutation=strings[1],
            paragraphs=paragraphs,
            closing=strings[-1],
            placeholders=placeholders,
        )
    except ValueError as exc:
        raise CorrespondenceError(f"Briefvorlage {index} ist ungültig: {exc}") from exc


def _validate_and_collect_placeholders(values: tuple[str, ...]) -> tuple[str, ...]:
    formatter = string.Formatter()
    fields: set[str] = set()
    for value in values:
        try:
            parsed = formatter.parse(value)
            for _, field_name, format_spec, conversion in parsed:
                if field_name is None:
                    continue
                if (
                    not field_name
                    or field_name[0] not in "abcdefghijklmnopqrstuvwxyz"
                    or any(character not in _PLACEHOLDER_CHARS for character in field_name)
                    or format_spec
                    or conversion
                ):
                    raise CorrespondenceError(
                        f"Unsicherer oder ungültiger Platzhalter: {field_name}"
                    )
                fields.add(field_name)
        except ValueError as exc:
            raise CorrespondenceError(f"Briefvorlage besitzt ungültige Platzhalter: {exc}") from exc
    return tuple(sorted(fields))


def _resolve_design(
    request: CorrespondenceRequest,
    configuration: CorrespondenceConfiguration,
) -> tuple[LetterDesign, tuple[str, ...]]:
    design_id = configuration.default_design_id
    resolution = [f"default:{design_id}"]
    for scope, key, values in (
        ("area", request.area, dict(configuration.bindings.areas)),
        ("purpose", request.purpose, dict(configuration.bindings.purposes)),
        ("profile", request.profile_id, dict(configuration.bindings.profiles)),
        (
            "profile_purpose",
            f"{request.profile_id}|{request.purpose}",
            dict(configuration.bindings.profile_purposes),
        ),
    ):
        if key in values:
            design_id = values[key]
            resolution.append(f"{scope}:{key}={design_id}")
    design = next(item for item in configuration.designs if item.design_id == design_id)
    return design, tuple(resolution)


def _render_markdown(
    request: CorrespondenceRequest,
    *,
    design: LetterDesign,
    subject: str,
    salutation: str,
    paragraphs: tuple[str, ...],
    closing: str,
) -> str:
    lines = []
    if design.header_text:
        lines.extend((f"> {_markdown_inline(design.header_text)}", ""))
    lines.extend(
        (
            f"# {_markdown_inline(subject)}",
            "",
            f"**Absender:** {_markdown_inline(request.sender.name)}  ",
            *(_markdown_inline(line) + "  " for line in request.sender.address_lines),
            "",
            f"**Empfänger:** {_markdown_inline(request.recipient.name)}  ",
            *(_markdown_inline(line) + "  " for line in request.recipient.address_lines),
            "",
            f"**Datum:** {request.created_on}",
            "",
            _markdown_inline(salutation),
            "",
        )
    )
    for paragraph in paragraphs:
        lines.extend((_markdown_inline(paragraph), ""))
    lines.extend((_markdown_inline(closing), "", _markdown_inline(request.sender.name)))
    if request.attachments:
        lines.extend(("", "## Anlagen", ""))
        lines.extend(f"- {_markdown_inline(item)}" for item in request.attachments)
    if request.evidence_refs:
        lines.extend(("", "## Interne Evidenzreferenzen", ""))
        lines.extend(f"- `{_code_inline(item)}`" for item in request.evidence_refs)
    if design.footer_text:
        lines.extend(("", "---", "", _markdown_inline(design.footer_text)))
    return "\n".join(lines).rstrip() + "\n"


def _render_text(
    request: CorrespondenceRequest,
    *,
    design: LetterDesign,
    subject: str,
    salutation: str,
    paragraphs: tuple[str, ...],
    closing: str,
) -> str:
    lines = []
    if design.header_text:
        lines.extend((design.header_text, ""))
    lines.extend(
        (
            request.sender.name,
            *request.sender.address_lines,
            "",
            request.recipient.name,
            *request.recipient.address_lines,
            "",
            request.created_on,
            "",
            subject,
            "",
            salutation,
            "",
        )
    )
    for paragraph in paragraphs:
        lines.extend((paragraph, ""))
    lines.extend((closing, "", request.sender.name))
    if request.attachments:
        lines.extend(("", "Anlagen:"))
        lines.extend(f"- {item}" for item in request.attachments)
    if request.evidence_refs:
        lines.extend(("", "Interne Evidenzreferenzen:"))
        lines.extend(f"- {item}" for item in request.evidence_refs)
    if design.footer_text:
        lines.extend(("", design.footer_text))
    return "\n".join(lines).rstrip() + "\n"


def _render_handoffs(
    *,
    preview_id: str,
    report_forge_revision: str,
    report_forge_distribution_version: str,
    report_forge_runtime_version: str,
) -> tuple[CorrespondenceRenderHandoff, ...]:
    if report_forge_distribution_version != report_forge_runtime_version:
        docx_status = "blocked"
        docx_reason = (
            "report-forge-Provideridentität ist uneinheitlich: Distribution "
            f"{report_forge_distribution_version}, Runtime {report_forge_runtime_version}."
        )
    else:
        docx_status = "review_required"
        docx_reason = (
            "Provideridentität stimmt überein; Brief-Overlay und vollständige visuelle "
            "DOCX-Seitenprüfung fehlen."
        )
    return (
        _handoff(
            preview_id,
            format_name="docx",
            provider_id="report-forge",
            provider_revision=report_forge_revision,
            status=docx_status,
            reason=docx_reason,
        ),
        _handoff(
            preview_id,
            format_name="odt",
            provider_id=None,
            provider_revision=None,
            status="blocked",
            reason="Kein revisionsgebundener ODT-Renderer ist angebunden.",
        ),
    )


def _handoff(
    preview_id: str,
    *,
    format_name: str,
    provider_id: str | None,
    provider_revision: str | None,
    status: str,
    reason: str,
) -> CorrespondenceRenderHandoff:
    material = "\0".join(
        (
            preview_id,
            format_name,
            provider_id or "none",
            provider_revision or "none",
            status,
            reason,
        )
    )
    return CorrespondenceRenderHandoff(
        handoff_id=f"correspondence_handoff_{sha256(material.encode('utf-8')).hexdigest()}",
        format=format_name,
        provider_id=provider_id,
        provider_revision=provider_revision,
        status=status,
        reason=reason,
    )


def _parse_party(value: object, *, label: str) -> CorrespondenceParty:
    if not isinstance(value, dict):
        raise CorrespondenceError(f"{label} muss ein Objekt sein.")
    try:
        return CorrespondenceParty(
            name=_text(value, "name", label),
            address_lines=_text_list(value, "address_lines", allow_empty=False),
            email=_nullable_text(value, "email", label),
            phone=_nullable_text(value, "phone", label),
        )
    except ValueError as exc:
        raise CorrespondenceError(f"{label} ist ungültig: {exc}") from exc


def _binding_pairs(payload: dict[str, object], field: str) -> tuple[tuple[str, str], ...]:
    value = payload.get(field)
    if not isinstance(value, dict) or not all(
        isinstance(key, str)
        and key.strip()
        and isinstance(design_id, str)
        and design_id.strip()
        for key, design_id in value.items()
    ):
        raise CorrespondenceError(f"Briefdesign-Bindung {field} ist ungültig.")
    return tuple(sorted((key.strip(), design_id.strip()) for key, design_id in value.items()))


def _load_json_object(path: Path, *, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise CorrespondenceError(f"{label} fehlen oder sind kein reguläres File: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorrespondenceError(f"{label} sind nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise CorrespondenceError(f"{label} müssen ein JSON-Objekt sein.")
    return payload


def _text(payload: dict[str, object], field: str, label: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CorrespondenceError(f"{label} benötigt das Textfeld {field}.")
    return value.strip()


def _optional_text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field, "")
    if not isinstance(value, str):
        raise CorrespondenceError(f"Feld {field} muss Text sein.")
    return value.strip()


def _nullable_text(payload: dict[str, object], field: str, label: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CorrespondenceError(f"{label}.{field} muss Text oder null sein.")
    return value.strip()


def _text_list(
    payload: dict[str, object],
    field: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise CorrespondenceError(f"Feld {field} benötigt eine Textliste.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise CorrespondenceError(f"Feld {field} enthält einen ungültigen Eintrag.")
    return tuple(item.strip() for item in value)


def _markdown_inline(value: str) -> str:
    return " ".join(value.split()).replace("`", "'").replace("*", "\\*")


def _code_inline(value: str) -> str:
    return " ".join(value.split()).replace("`", "'")


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
