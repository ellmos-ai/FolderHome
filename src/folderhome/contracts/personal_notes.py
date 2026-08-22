"""Contracts for human-authored, LLM-guided personal notes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

_ID = re.compile(r"[a-z0-9][a-z0-9._:-]{1,127}")
_NOTE_ID = re.compile(r"note_[0-9a-f]{32}")
_PLAN_ID = re.compile(r"personal_note_plan_[0-9a-f]{64}")
_ACTION_ID = re.compile(r"personal_note_action_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"personal_note_report_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _aware_timestamp(value: str, *, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} benötigt eine Zeitzone.")


class PersonalNoteAction(StrEnum):
    """Append-only changes supported by the personal note service."""

    CREATE = "create"
    EDIT = "edit"
    REVERT = "revert"


@dataclass(frozen=True, slots=True)
class PersonalNoteReference:
    kind: str
    target_id: str
    label: str
    sha256: str | None

    SCHEMA = "folderhome.personal-note-reference.v1"

    def __post_init__(self) -> None:
        if self.kind not in {"document", "calendar"}:
            raise ValueError("Notizreferenz muss Dokument oder Kalender sein.")
        if not self.target_id.strip() or any(char in self.target_id for char in "\r\n"):
            raise ValueError("Notizreferenz benötigt eine Ziel-ID.")
        if not self.label.strip() or any(char in self.label for char in "\r\n"):
            raise ValueError("Notizreferenz benötigt eine Bezeichnung.")
        if self.sha256 is not None and _SHA256.fullmatch(self.sha256) is None:
            raise ValueError("Notizreferenz besitzt einen ungültigen SHA-256.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "kind": self.kind,
            "target_id": self.target_id,
            "label": self.label,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class PersonalNoteRequest:
    request_id: str
    action: PersonalNoteAction
    profile_id: str
    notebook_id: str
    area: str
    title: str
    human_content: str | None
    note_id: str | None
    expected_revision: int | None
    revert_to_revision: int | None
    references: tuple[PersonalNoteReference, ...]

    SCHEMA = "folderhome.personal-note-request.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.request_id) is None:
            raise ValueError("Notizanfrage besitzt eine ungültige Anfrage-ID.")
        for label, value in (
            ("Profil", self.profile_id),
            ("Notizbuch", self.notebook_id),
            ("Bereich", self.area),
            ("Titel", self.title),
        ):
            if not value.strip() or any(char in value for char in "\r\n"):
                raise ValueError(f"Notizanfrage benötigt {label}.")
        reference_keys = {(item.kind, item.target_id) for item in self.references}
        if len(reference_keys) != len(self.references):
            raise ValueError("Notizreferenzen müssen eindeutig sein.")
        if self.action is PersonalNoteAction.CREATE:
            if self.note_id is not None or self.expected_revision is not None:
                raise ValueError("Neue Notiz darf keine bestehende Revision vorgeben.")
            if self.revert_to_revision is not None:
                raise ValueError("Neue Notiz darf kein Rückkehrziel vorgeben.")
            self._require_human_content()
        elif self.action is PersonalNoteAction.EDIT:
            self._require_existing_note()
            self._require_human_content()
            if self.revert_to_revision is not None:
                raise ValueError("Bearbeitung darf kein Rückkehrziel vorgeben.")
        else:
            self._require_existing_note()
            if self.human_content is not None:
                raise ValueError("Rückkehr übernimmt Inhalt einer früheren Revision.")
            if self.revert_to_revision is None or self.revert_to_revision < 1:
                raise ValueError("Rückkehr benötigt eine frühere Zielrevision.")
            if self.revert_to_revision >= (self.expected_revision or 0):
                raise ValueError("Rückkehrziel muss älter als die aktuelle Revision sein.")

    def _require_human_content(self) -> None:
        if self.human_content is None or not self.human_content.strip():
            raise ValueError("Notizanfrage benötigt bestätigbaren menschlichen Inhalt.")

    def _require_existing_note(self) -> None:
        if self.note_id is None or _NOTE_ID.fullmatch(self.note_id) is None:
            raise ValueError("Notizänderung benötigt eine gültige Notiz-ID.")
        if self.expected_revision is None or self.expected_revision < 1:
            raise ValueError("Notizänderung benötigt die erwartete Revision.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "action": self.action.value,
            "profile_id": self.profile_id,
            "notebook_id": self.notebook_id,
            "area": self.area,
            "title": self.title,
            "human_content": self.human_content,
            "note_id": self.note_id,
            "expected_revision": self.expected_revision,
            "revert_to_revision": self.revert_to_revision,
            "references": [item.to_dict() for item in self.references],
        }


@dataclass(frozen=True, slots=True)
class PersonalNoteGuidance:
    provider_id: str
    provider_revision: str
    questions: tuple[str, ...]
    suggestions: tuple[str, ...]
    confirmed_content_changed: bool
    network_invoked: bool

    SCHEMA = "folderhome.personal-note-guidance.v1"

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.provider_revision.strip():
            raise ValueError("Notizführung benötigt eine Provideridentität.")
        if not self.questions:
            raise ValueError("Notizführung benötigt mindestens eine Frage.")
        if self.confirmed_content_changed:
            raise ValueError("Notizführung darf bestätigten Inhalt nicht verändern.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "questions": list(self.questions),
            "suggestions": list(self.suggestions),
            "confirmed_content_changed": False,
            "network_invoked": self.network_invoked,
        }


@dataclass(frozen=True, slots=True)
class PersonalNotePlan:
    plan_id: str
    plan_sha256: str
    action_id: str
    request_id: str
    action: PersonalNoteAction
    note_id: str
    profile_id: str
    notebook_id: str
    area: str
    title: str
    proposed_content: str
    content_sha256: str
    next_revision: int
    parent_revision: int | None
    reverts_revision: int | None
    references: tuple[PersonalNoteReference, ...]
    guidance: PersonalNoteGuidance
    store_revision: str
    status: str
    author_kind: str = "human"
    external_sync_invoked: bool = False

    SCHEMA = "folderhome.personal-note-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None or _SHA256.fullmatch(
            self.plan_sha256
        ) is None:
            raise ValueError("Notizplan besitzt eine ungültige Identität.")
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("Notizplan besitzt eine ungültige Aktions-ID.")
        if _NOTE_ID.fullmatch(self.note_id) is None:
            raise ValueError("Notizplan besitzt eine ungültige Notiz-ID.")
        if _SHA256.fullmatch(self.content_sha256) is None or _SHA256.fullmatch(
            self.store_revision
        ) is None:
            raise ValueError("Notizplan besitzt ungültige Hashbindungen.")
        if self.status != "review_required":
            raise ValueError("Notizplan muss vor der Ablage menschlich geprüft werden.")
        if self.author_kind != "human" or self.external_sync_invoked:
            raise ValueError("Notizplan verletzt die Autorschafts- oder Sync-Grenze.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "action_id": self.action_id,
            "request_id": self.request_id,
            "action": self.action.value,
            "note_id": self.note_id,
            "profile_id": self.profile_id,
            "notebook_id": self.notebook_id,
            "area": self.area,
            "title": self.title,
            "proposed_content": self.proposed_content,
            "content_sha256": self.content_sha256,
            "next_revision": self.next_revision,
            "parent_revision": self.parent_revision,
            "reverts_revision": self.reverts_revision,
            "references": [item.to_dict() for item in self.references],
            "guidance": self.guidance.to_dict(),
            "store_revision": self.store_revision,
            "status": self.status,
            "author_kind": self.author_kind,
            "external_sync_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class PersonalNoteApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    action_id: str
    content_sha256: str
    approved_at: str
    allow_local_note_write: bool

    SCHEMA = "folderhome.personal-note-approval.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.approval_id) is None:
            raise ValueError("Notizfreigabe besitzt eine ungültige ID.")
        if _PLAN_ID.fullmatch(self.plan_id) is None or _SHA256.fullmatch(
            self.plan_sha256
        ) is None:
            raise ValueError("Notizfreigabe besitzt keine gültige Planbindung.")
        if _ACTION_ID.fullmatch(self.action_id) is None or _SHA256.fullmatch(
            self.content_sha256
        ) is None:
            raise ValueError("Notizfreigabe besitzt keine gültige Inhaltsbindung.")
        _aware_timestamp(self.approved_at, label="Notizfreigabezeit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "action_id": self.action_id,
            "content_sha256": self.content_sha256,
            "approved_at": self.approved_at,
            "allow_local_note_write": self.allow_local_note_write,
        }


@dataclass(frozen=True, slots=True)
class PersonalNoteVersion:
    note_id: str
    revision: int
    action: PersonalNoteAction
    profile_id: str
    notebook_id: str
    area: str
    title: str
    human_content: str
    references: tuple[PersonalNoteReference, ...]
    source_plan_id: str
    parent_revision: int | None
    reverts_revision: int | None
    created_at: str
    provider_entry_id: int | None = None
    author_kind: str = "human"
    os_account_is_security_boundary: bool = True
    profile_is_security_boundary: bool = False

    SCHEMA = "folderhome.personal-note-version.v1"

    def __post_init__(self) -> None:
        if _NOTE_ID.fullmatch(self.note_id) is None or self.revision < 1:
            raise ValueError("Notizversion besitzt eine ungültige Identität.")
        if self.author_kind != "human":
            raise ValueError("Notizversion muss menschliche Autorschaft ausweisen.")
        if not self.os_account_is_security_boundary or self.profile_is_security_boundary:
            raise ValueError("Notizversion verletzt die Betriebssystemkonto-Grenze.")
        _aware_timestamp(self.created_at, label="Notizversionszeit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "note_id": self.note_id,
            "revision": self.revision,
            "action": self.action.value,
            "profile_id": self.profile_id,
            "notebook_id": self.notebook_id,
            "area": self.area,
            "title": self.title,
            "human_content": self.human_content,
            "references": [item.to_dict() for item in self.references],
            "source_plan_id": self.source_plan_id,
            "parent_revision": self.parent_revision,
            "reverts_revision": self.reverts_revision,
            "created_at": self.created_at,
            "provider_entry_id": self.provider_entry_id,
            "author_kind": "human",
            "os_account_is_security_boundary": True,
            "profile_is_security_boundary": False,
        }


@dataclass(frozen=True, slots=True)
class PersonalNoteExecutionReport:
    report_id: str
    plan_id: str
    approval_id: str
    note_id: str
    revision: int
    provider_id: str
    provider_revision: str
    status: str
    network_invoked: bool
    external_sync_invoked: bool

    SCHEMA = "folderhome.personal-note-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Notizbericht besitzt eine ungültige ID.")
        if self.status != "executed":
            raise ValueError("Notizbericht besitzt einen unbekannten Status.")
        if self.network_invoked or self.external_sync_invoked:
            raise ValueError("Lokaler Notizbericht darf keine externe Wirkung ausweisen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "note_id": self.note_id,
            "revision": self.revision,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "status": self.status,
            "network_invoked": False,
            "external_sync_invoked": False,
        }
