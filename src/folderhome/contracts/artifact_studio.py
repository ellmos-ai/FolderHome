"""Contracts for provider-neutral office, media, and design artifact planning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_PLAN_ID = re.compile(r"artifact_plan_[0-9a-f]{64}")
_PREVIEW_ID = re.compile(r"design_preview_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"design_output_[0-9a-f]{64}")
_GIT_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
_FONT_NAME = re.compile(r"[\w .-]{1,80}")

ARTIFACT_KINDS = frozenset(
    {
        "presentation",
        "spreadsheet",
        "document",
        "odt",
        "design_set",
        "business_card",
        "media",
    }
)


@dataclass(frozen=True, slots=True)
class ArtifactStudioRequest:
    request_id: str
    profile_id: str
    purpose: str
    title: str
    artifact_kinds: tuple[str, ...]
    source_refs: tuple[str, ...]

    SCHEMA = "folderhome.artifact-studio-request.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.request_id) is None:
            raise ValueError("Artefaktanfrage benötigt eine gültige request_id.")
        if not self.profile_id.strip() or not self.purpose.strip() or not self.title.strip():
            raise ValueError("Artefaktanfrage benötigt Profil, Zweck und Titel.")
        if not self.artifact_kinds or len(self.artifact_kinds) != len(
            set(self.artifact_kinds)
        ):
            raise ValueError("Artefaktarten müssen nichtleer und eindeutig sein.")
        if any(kind not in ARTIFACT_KINDS for kind in self.artifact_kinds):
            raise ValueError("Artefaktanfrage enthält eine unbekannte Artefaktart.")
        if any(not item.strip() for item in self.source_refs):
            raise ValueError("Quellenreferenzen dürfen nicht leer sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "purpose": self.purpose,
            "title": self.title,
            "artifact_kinds": list(self.artifact_kinds),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class ArtifactRoute:
    artifact_kind: str
    provider_id: str | None
    provider_revision: str | None
    status: str
    reason: str
    required_gates: tuple[str, ...]
    provider_invoked: bool = False

    SCHEMA = "folderhome.artifact-route.v1"

    def __post_init__(self) -> None:
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise ValueError("Artefaktroute besitzt eine unbekannte Artefaktart.")
        if self.status not in {"ready", "review_required", "blocked"}:
            raise ValueError("Artefaktroute besitzt einen ungültigen Status.")
        if not self.reason.strip() or not self.required_gates:
            raise ValueError("Artefaktroute benötigt Grund und Gates.")
        if self.provider_revision is not None and _GIT_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("Artefaktroute besitzt eine ungültige Providerrevision.")
        if self.provider_invoked:
            raise ValueError("Ein Artefaktplan darf keinen Provider ausführen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "artifact_kind": self.artifact_kind,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "status": self.status,
            "reason": self.reason,
            "required_gates": list(self.required_gates),
            "provider_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class ArtifactStudioPlan:
    plan_id: str
    request: ArtifactStudioRequest
    routes: tuple[ArtifactRoute, ...]
    side_effects: tuple[str, ...] = ()
    provider_invoked: bool = False

    SCHEMA = "folderhome.artifact-studio-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Artefaktplan-ID ist ungültig.")
        if tuple(item.artifact_kind for item in self.routes) != self.request.artifact_kinds:
            raise ValueError("Artefaktrouten müssen der Anfragereihenfolge entsprechen.")
        if self.side_effects or self.provider_invoked:
            raise ValueError("Artefaktpläne müssen nebenwirkungsfrei sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "request": self.request.to_dict(),
            "routes": [item.to_dict() for item in self.routes],
            "side_effects": [],
            "provider_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class DesignColors:
    primary: str
    on_primary: str
    background: str
    text: str
    accent: str

    def __post_init__(self) -> None:
        if any(
            _HEX_COLOR.fullmatch(value) is None
            for value in (
                self.primary,
                self.on_primary,
                self.background,
                self.text,
                self.accent,
            )
        ):
            raise ValueError("Designfarben müssen #RRGGBB verwenden.")

    def to_dict(self) -> dict[str, str]:
        return {
            "primary": self.primary.upper(),
            "on_primary": self.on_primary.upper(),
            "background": self.background.upper(),
            "text": self.text.upper(),
            "accent": self.accent.upper(),
        }


@dataclass(frozen=True, slots=True)
class DesignFonts:
    heading: str
    body: str

    def __post_init__(self) -> None:
        for value in (self.heading, self.body):
            if value != value.strip() or _FONT_NAME.fullmatch(value) is None:
                raise ValueError("Designschrift muss einzeilig und nichtleer sein.")

    def to_dict(self) -> dict[str, str]:
        return {"heading": self.heading, "body": self.body}


@dataclass(frozen=True, slots=True)
class BusinessCardContent:
    name: str
    role: str
    organization: str
    email: str | None
    phone: str | None
    website: str | None

    def __post_init__(self) -> None:
        values = (self.name, self.role, self.organization, self.email, self.phone, self.website)
        if any(
            value is not None
            and (not value.strip() or len(value) > 160 or "\n" in value or "\r" in value)
            for value in values
        ):
            raise ValueError("Visitenkartenfelder müssen einzeilig und nichtleer sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "role": self.role,
            "organization": self.organization,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
        }


@dataclass(frozen=True, slots=True)
class DesignStudioRequest:
    profile_id: str
    design_set_id: str
    display_name: str
    purpose: str
    colors: DesignColors
    fonts: DesignFonts
    business_card: BusinessCardContent

    SCHEMA = "folderhome.design-studio-request.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.design_set_id) is None:
            raise ValueError("Designset benötigt eine gültige ID.")
        if any(
            not value.strip()
            for value in (self.profile_id, self.display_name, self.purpose)
        ):
            raise ValueError("Designset benötigt Profil, Bezeichnung und Zweck.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "profile_id": self.profile_id,
            "design_set_id": self.design_set_id,
            "display_name": self.display_name,
            "purpose": self.purpose,
            "colors": self.colors.to_dict(),
            "fonts": self.fonts.to_dict(),
            "business_card": self.business_card.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DesignPreview:
    preview_id: str
    request: DesignStudioRequest
    design_set_json: str
    design_css: str
    business_card_svg: str
    contrast_checks: tuple[tuple[str, bool], ...]
    json_sha256: str
    css_sha256: str
    svg_sha256: str

    SCHEMA = "folderhome.design-preview.v1"

    def __post_init__(self) -> None:
        if _PREVIEW_ID.fullmatch(self.preview_id) is None:
            raise ValueError("Designvorschau-ID ist ungültig.")
        if any(
            _SHA256.fullmatch(value) is None
            for value in (self.json_sha256, self.css_sha256, self.svg_sha256)
        ):
            raise ValueError("Designvorschau benötigt gültige Ausgabehashes.")

    @property
    def read_only(self) -> bool:
        return True

    @property
    def visual_qa_passed(self) -> bool:
        return False

    @property
    def remote_provider_invoked(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "preview_id": self.preview_id,
            "request": self.request.to_dict(),
            "design_set": json.loads(self.design_set_json),
            "design_css": self.design_css,
            "business_card_svg": self.business_card_svg,
            "contrast_checks": [
                {"check": name, "passed": passed}
                for name, passed in self.contrast_checks
            ],
            "json_sha256": self.json_sha256,
            "css_sha256": self.css_sha256,
            "svg_sha256": self.svg_sha256,
            "read_only": True,
            "visual_qa_passed": False,
            "contains_sensitive_data": True,
            "remote_provider_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class DesignOutputReport:
    report_id: str
    preview_id: str
    status: str
    json_file: Path
    css_file: Path
    business_card_file: Path
    json_sha256: str
    css_sha256: str
    svg_sha256: str

    SCHEMA = "folderhome.design-output-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None or self.status != "executed":
            raise ValueError("Designausgabereport ist ungültig.")
        if _PREVIEW_ID.fullmatch(self.preview_id) is None:
            raise ValueError("Designausgabereport benötigt eine gültige Vorschau-ID.")
        if any(
            _SHA256.fullmatch(value) is None
            for value in (self.json_sha256, self.css_sha256, self.svg_sha256)
        ):
            raise ValueError("Designausgabereport benötigt gültige Hashes.")
        object.__setattr__(self, "json_file", self.json_file.resolve())
        object.__setattr__(self, "css_file", self.css_file.resolve())
        object.__setattr__(
            self,
            "business_card_file",
            self.business_card_file.resolve(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "preview_id": self.preview_id,
            "status": self.status,
            "json_file": str(self.json_file),
            "css_file": str(self.css_file),
            "business_card_file": str(self.business_card_file),
            "json_sha256": self.json_sha256,
            "css_sha256": self.css_sha256,
            "svg_sha256": self.svg_sha256,
            "visual_qa_passed": False,
            "remote_provider_invoked": False,
        }
