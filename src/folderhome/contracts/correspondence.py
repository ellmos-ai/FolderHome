"""Contracts for deterministic, template-bound household correspondence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
_PREVIEW_ID = re.compile(r"correspondence_preview_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"correspondence_output_[0-9a-f]{64}")
_HANDOFF_ID = re.compile(r"correspondence_handoff_[0-9a-f]{64}")
_GIT_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class CorrespondenceParty:
    name: str
    address_lines: tuple[str, ...]
    email: str | None
    phone: str | None

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.address_lines:
            raise ValueError("Briefpartei benötigt Name und Anschrift.")
        if any(not line.strip() or "\n" in line or "\r" in line for line in self.address_lines):
            raise ValueError("Anschriftzeilen müssen nichtleer und einzeilig sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "address_lines": list(self.address_lines),
            "email": self.email,
            "phone": self.phone,
        }


@dataclass(frozen=True, slots=True)
class LetterDesign:
    design_id: str
    display_name: str
    page_size: str
    margins_mm: tuple[int, int, int, int]
    font_family: str
    font_size_pt: float
    accent_color: str
    header_text: str
    footer_text: str

    SCHEMA = "folderhome.letter-design.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.design_id) is None or not self.display_name.strip():
            raise ValueError("Briefdesign benötigt eine gültige ID und Bezeichnung.")
        if self.page_size != "A4":
            raise ValueError("Briefdesign unterstützt derzeit ausschließlich A4.")
        if len(self.margins_mm) != 4 or any(not 5 <= value <= 50 for value in self.margins_mm):
            raise ValueError("Briefdesign benötigt vier Ränder zwischen 5 und 50 mm.")
        if not self.font_family.strip() or not 8 <= self.font_size_pt <= 18:
            raise ValueError("Briefdesign besitzt eine ungültige Schriftdefinition.")
        if _HEX_COLOR.fullmatch(self.accent_color) is None:
            raise ValueError("accent_color muss #RRGGBB verwenden.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "design_id": self.design_id,
            "display_name": self.display_name,
            "page_size": self.page_size,
            "margins_mm": list(self.margins_mm),
            "font_family": self.font_family,
            "font_size_pt": self.font_size_pt,
            "accent_color": self.accent_color,
            "header_text": self.header_text,
            "footer_text": self.footer_text,
        }


@dataclass(frozen=True, slots=True)
class LetterTemplate:
    template_id: str
    display_name: str
    purpose: str
    subject: str
    salutation: str
    paragraphs: tuple[str, ...]
    closing: str
    placeholders: tuple[str, ...]

    SCHEMA = "folderhome.letter-template.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.template_id) is None or not self.display_name.strip():
            raise ValueError("Briefvorlage benötigt ID und Bezeichnung.")
        if not self.purpose or not self.subject or not self.salutation or not self.paragraphs:
            raise ValueError("Briefvorlage benötigt Zweck, Betreff, Anrede und Absätze.")
        if not self.closing:
            raise ValueError("Briefvorlage benötigt eine Grußformel.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "template_id": self.template_id,
            "display_name": self.display_name,
            "purpose": self.purpose,
            "subject": self.subject,
            "salutation": self.salutation,
            "paragraphs": list(self.paragraphs),
            "closing": self.closing,
            "placeholders": list(self.placeholders),
        }


@dataclass(frozen=True, slots=True)
class DesignBindings:
    areas: tuple[tuple[str, str], ...]
    purposes: tuple[tuple[str, str], ...]
    profiles: tuple[tuple[str, str], ...]
    profile_purposes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "areas": dict(self.areas),
            "purposes": dict(self.purposes),
            "profiles": dict(self.profiles),
            "profile_purposes": dict(self.profile_purposes),
        }


@dataclass(frozen=True, slots=True)
class CorrespondenceConfiguration:
    designs_path: Path
    templates_path: Path
    default_design_id: str
    designs: tuple[LetterDesign, ...]
    bindings: DesignBindings
    templates: tuple[LetterTemplate, ...]

    SCHEMA = "folderhome.correspondence-configuration.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "designs_path", self.designs_path.resolve())
        object.__setattr__(self, "templates_path", self.templates_path.resolve())


@dataclass(frozen=True, slots=True)
class CorrespondenceRequest:
    profile_id: str
    area: str
    purpose: str
    template_id: str
    created_on: str
    sender: CorrespondenceParty
    recipient: CorrespondenceParty
    variables: tuple[tuple[str, str], ...]
    attachments: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    SCHEMA = "folderhome.correspondence-request.v1"

    def __post_init__(self) -> None:
        for value in (self.profile_id, self.area, self.purpose, self.template_id):
            if not value.strip():
                raise ValueError("Korrespondenzanfrage besitzt ein leeres Zuordnungsfeld.")
        date.fromisoformat(self.created_on)
        if any(not key or not value for key, value in self.variables):
            raise ValueError("Korrespondenzvariablen müssen nichtleer sein.")
        if len(self.variables) != len({key for key, _ in self.variables}):
            raise ValueError("Korrespondenzvariablen müssen eindeutig sein.")
        if any(not value.strip() for value in (*self.attachments, *self.evidence_refs)):
            raise ValueError("Anlagen und Evidenzreferenzen dürfen nicht leer sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "profile_id": self.profile_id,
            "area": self.area,
            "purpose": self.purpose,
            "template_id": self.template_id,
            "created_on": self.created_on,
            "sender": self.sender.to_dict(),
            "recipient": self.recipient.to_dict(),
            "variables": dict(self.variables),
            "attachments": list(self.attachments),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class CorrespondenceRenderHandoff:
    handoff_id: str
    format: str
    provider_id: str | None
    provider_revision: str | None
    status: str
    reason: str
    provider_invoked: bool = False

    SCHEMA = "folderhome.correspondence-render-handoff.v1"

    def __post_init__(self) -> None:
        if _HANDOFF_ID.fullmatch(self.handoff_id) is None:
            raise ValueError("Korrespondenz-Handoff-ID ist ungültig.")
        if self.format not in {"docx", "odt"}:
            raise ValueError("Korrespondenz-Handoff unterstützt DOCX oder ODT.")
        if self.provider_revision is not None and _GIT_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("Providerrevision ist ungültig.")
        if self.status not in {"blocked", "review_required"} or not self.reason:
            raise ValueError("Korrespondenz-Handoff benötigt Status und Grund.")
        if self.provider_invoked:
            raise ValueError("Korrespondenz-Handoff darf keinen Provider aufrufen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "handoff_id": self.handoff_id,
            "format": self.format,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "status": self.status,
            "reason": self.reason,
            "provider_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class CorrespondencePreview:
    preview_id: str
    request: CorrespondenceRequest
    template: LetterTemplate
    design: LetterDesign
    design_resolution: tuple[str, ...]
    subject: str
    salutation: str
    paragraphs: tuple[str, ...]
    closing: str
    markdown: str
    text: str
    markdown_sha256: str
    text_sha256: str
    render_handoffs: tuple[CorrespondenceRenderHandoff, ...]

    SCHEMA = "folderhome.correspondence-preview.v1"

    def __post_init__(self) -> None:
        if _PREVIEW_ID.fullmatch(self.preview_id) is None:
            raise ValueError("Korrespondenz-Vorschau-ID ist ungültig.")
        if _SHA256.fullmatch(self.markdown_sha256) is None or _SHA256.fullmatch(
            self.text_sha256
        ) is None:
            raise ValueError("Korrespondenz-Vorschau benötigt Ausgabehashes.")

    @property
    def read_only(self) -> bool:
        return True

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "preview_id": self.preview_id,
            "request": self.request.to_dict(),
            "template": self.template.to_dict(),
            "design": self.design.to_dict(),
            "design_resolution": list(self.design_resolution),
            "subject": self.subject,
            "salutation": self.salutation,
            "paragraphs": list(self.paragraphs),
            "closing": self.closing,
            "markdown": self.markdown,
            "text": self.text,
            "markdown_sha256": self.markdown_sha256,
            "text_sha256": self.text_sha256,
            "render_handoffs": [item.to_dict() for item in self.render_handoffs],
            "read_only": True,
            "contains_sensitive_data": True,
            "llm_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class CorrespondenceOutputReport:
    report_id: str
    preview_id: str
    status: str
    markdown_file: Path
    text_file: Path
    markdown_sha256: str
    text_sha256: str
    provider_invoked: bool = False

    SCHEMA = "folderhome.correspondence-output-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Korrespondenz-Ausgabe-ID ist ungültig.")
        if _PREVIEW_ID.fullmatch(self.preview_id) is None or self.status != "executed":
            raise ValueError("Korrespondenz-Ausgabe benötigt Vorschau und Status.")
        object.__setattr__(self, "markdown_file", self.markdown_file.resolve())
        object.__setattr__(self, "text_file", self.text_file.resolve())
        if self.provider_invoked:
            raise ValueError("Markdown-/TXT-Ausgabe ruft keinen Provider auf.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "preview_id": self.preview_id,
            "status": self.status,
            "markdown_file": str(self.markdown_file),
            "text_file": str(self.text_file),
            "markdown_sha256": self.markdown_sha256,
            "text_sha256": self.text_sha256,
            "provider_invoked": False,
        }
