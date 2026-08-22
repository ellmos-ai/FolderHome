"""Contracts for evidenced document contacts and an approval-gated register."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

_ACTION_ID_PATTERN = re.compile(r"contact_action_[0-9a-f]{32}")
_APPROVAL_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_CANDIDATE_ID_PATTERN = re.compile(r"contact_candidate_[0-9a-f]{64}")
_CONTACT_ID_PATTERN = re.compile(r"contact_[0-9a-f]{64}")
_DOCUMENT_ID_PATTERN = re.compile(r"doc_[0-9a-f]{64}")
_PLAN_ID_PATTERN = re.compile(r"contact_plan_[0-9a-f]{64}")
_REVISION_PATTERN = re.compile(r"contact_revision_[0-9a-f]{64}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class ContactEvidence:
    """Exact labeled line location supporting one normalized contact field."""

    field: str
    line_number: int
    label: str

    def __post_init__(self) -> None:
        if not self.field or self.line_number < 1 or not self.label:
            raise ValueError("Kontaktevidenz benötigt Feld, Zeilennummer und Label.")

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "line_number": self.line_number,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class ContactCandidate:
    """One normalized assignment candidate tied to one immutable document hash."""

    candidate_id: str
    profile_id: str
    area: str
    organization: str
    contact_name: str | None
    role: str | None
    purpose: str
    object_ref: str | None
    email: str | None
    phone: str | None
    effective_date: str
    effective_date_basis: str
    source_document_id: str
    source_sha256: str
    source_path: Path
    evidence: tuple[ContactEvidence, ...]

    SCHEMA = "folderhome.contact-candidate.v1"

    def __post_init__(self) -> None:
        if _CANDIDATE_ID_PATTERN.fullmatch(self.candidate_id) is None:
            raise ValueError("candidate_id muss contact_candidate_<sha256> verwenden.")
        if not self.profile_id or not self.area or not self.organization or not self.purpose:
            raise ValueError("Kontaktkandidat benötigt Profil, Bereich, Organisation und Zweck.")
        if self.email is None and self.phone is None:
            raise ValueError("Kontaktkandidat benötigt E-Mail oder Telefon.")
        if _DOCUMENT_ID_PATTERN.fullmatch(self.source_document_id) is None:
            raise ValueError("source_document_id muss doc_<sha256> verwenden.")
        if _SHA256_PATTERN.fullmatch(self.source_sha256) is None:
            raise ValueError("source_sha256 muss ein kleingeschriebener SHA-256 sein.")
        try:
            date.fromisoformat(self.effective_date)
        except ValueError as exc:
            raise ValueError("effective_date muss ein ISO-Datum sein.") from exc
        if not self.effective_date_basis or not self.evidence:
            raise ValueError("Kontaktkandidat benötigt Datumsbasis und Evidenz.")
        object.__setattr__(self, "source_path", self.source_path.resolve())

    @property
    def assignment_key(self) -> tuple[str, str, str, str]:
        return (
            self.profile_id.casefold(),
            self.area.casefold(),
            self.purpose.casefold(),
            (self.object_ref or "").casefold(),
        )

    @property
    def identity_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.organization.casefold(),
            (self.contact_name or "").casefold(),
            (self.role or "").casefold(),
            (self.email or "").casefold(),
            self.phone or "",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "candidate_id": self.candidate_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "organization": self.organization,
            "contact_name": self.contact_name,
            "role": self.role,
            "purpose": self.purpose,
            "object_ref": self.object_ref,
            "email": self.email,
            "phone": self.phone,
            "effective_date": self.effective_date,
            "effective_date_basis": self.effective_date_basis,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class DocumentContactAnalysis:
    """One document's contact result without unrelated source text."""

    document_id: str
    source_path: Path
    source_sha256: str
    status: str
    candidate: ContactCandidate | None
    issues: tuple[str, ...]

    SCHEMA = "folderhome.document-contact-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "document_id": self.document_id,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "status": self.status,
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "issues": list(self.issues),
        }


@dataclass(frozen=True, slots=True)
class FolderContactItem:
    """One visible file outcome in deterministic folder contact analysis."""

    relative_path: str
    status: str
    analysis: DocumentContactAnalysis | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderContactAnalysis:
    """Read-only contact candidate set for one explicit source folder."""

    source_root: Path
    profile_id: str
    area: str
    recursive: bool
    items: tuple[FolderContactItem, ...]

    SCHEMA = "folderhome.folder-contact-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    @property
    def candidates(self) -> tuple[ContactCandidate, ...]:
        return tuple(
            item.analysis.candidate
            for item in self.items
            if item.analysis is not None and item.analysis.candidate is not None
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "source_root": str(self.source_root),
            "profile_id": self.profile_id,
            "area": self.area,
            "recursive": self.recursive,
            "candidate_count": len(self.candidates),
            "items": [item.to_dict() for item in self.items],
        }


class ContactActionKind(StrEnum):
    """Register operation proposed for one contact candidate."""

    CREATE = "create"
    REPLACE = "replace"
    NOOP = "noop"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ContactRecord:
    """One local registered contact; deletion candidates remain queryable."""

    contact_id: str
    candidate_id: str
    profile_id: str
    area: str
    organization: str
    contact_name: str | None
    role: str | None
    purpose: str
    object_ref: str | None
    email: str | None
    phone: str | None
    effective_date: str
    source_document_id: str
    source_sha256: str
    source_path: Path
    status: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if _CONTACT_ID_PATTERN.fullmatch(self.contact_id) is None:
            raise ValueError("contact_id muss contact_<sha256> verwenden.")
        object.__setattr__(self, "source_path", self.source_path.resolve())

    @property
    def assignment_key(self) -> tuple[str, str, str, str]:
        return (
            self.profile_id.casefold(),
            self.area.casefold(),
            self.purpose.casefold(),
            (self.object_ref or "").casefold(),
        )

    @property
    def identity_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.organization.casefold(),
            (self.contact_name or "").casefold(),
            (self.role or "").casefold(),
            (self.email or "").casefold(),
            self.phone or "",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "contact_id": self.contact_id,
            "candidate_id": self.candidate_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "organization": self.organization,
            "contact_name": self.contact_name,
            "role": self.role,
            "purpose": self.purpose,
            "object_ref": self.object_ref,
            "email": self.email,
            "phone": self.phone,
            "effective_date": self.effective_date,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class ContactRegisterAction:
    """Atomic create/replace proposal or an explicit non-action."""

    action_id: str
    kind: ContactActionKind
    status: str
    candidate: ContactCandidate
    prior_contact_id: str | None
    message: str

    def __post_init__(self) -> None:
        if _ACTION_ID_PATTERN.fullmatch(self.action_id) is None:
            raise ValueError("action_id muss contact_action_<hex> verwenden.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "kind": self.kind.value,
            "status": self.status,
            "candidate": self.candidate.to_dict(),
            "prior_contact_id": self.prior_contact_id,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ContactRegisterPlan:
    """Read-only candidate-to-register comparison bound to one revision."""

    plan_id: str
    register_revision: str
    analysis: FolderContactAnalysis
    actions: tuple[ContactRegisterAction, ...]

    SCHEMA = "folderhome.contact-register-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss contact_plan_<sha256> verwenden.")
        if _REVISION_PATTERN.fullmatch(self.register_revision) is None:
            raise ValueError("register_revision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "register_revision": self.register_revision,
            "analysis": self.analysis.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "automatic_deletion": False,
        }


@dataclass(frozen=True, slots=True)
class ContactRegisterApproval:
    """Exact approval for selected planned contact actions."""

    approval_id: str
    plan_id: str
    register_revision: str
    action_ids: tuple[str, ...]
    approved_at: str

    SCHEMA = "folderhome.contact-register-approval.v1"

    def __post_init__(self) -> None:
        if _APPROVAL_ID_PATTERN.fullmatch(self.approval_id) is None:
            raise ValueError("approval_id muss eine stabile Kleinbuchstaben-ID sein.")
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id ist ungültig.")
        if _REVISION_PATTERN.fullmatch(self.register_revision) is None:
            raise ValueError("register_revision ist ungültig.")
        if not self.action_ids or len(self.action_ids) != len(set(self.action_ids)):
            raise ValueError("action_ids müssen nichtleer und eindeutig sein.")
        if any(_ACTION_ID_PATTERN.fullmatch(value) is None for value in self.action_ids):
            raise ValueError("action_ids enthalten eine ungültige ID.")
        try:
            timestamp = datetime.fromisoformat(self.approved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                f"approved_at ist kein ISO-Zeitpunkt: {self.approved_at}"
            ) from exc
        if timestamp.tzinfo is None:
            raise ValueError("approved_at benötigt eine Zeitzone.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "register_revision": self.register_revision,
            "action_ids": list(self.action_ids),
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class ContactRegisterReport:
    """Applied register transaction with no deletion operation."""

    execution_id: str
    plan_id: str
    approval_id: str
    register_revision_before: str
    register_revision_after: str
    created_contact_ids: tuple[str, ...]
    marked_contact_ids: tuple[str, ...]
    register_path: Path
    status: str = "applied"

    SCHEMA = "folderhome.contact-register-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "register_path", self.register_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "register_revision_before": self.register_revision_before,
            "register_revision_after": self.register_revision_after,
            "created_contact_ids": list(self.created_contact_ids),
            "marked_contact_ids": list(self.marked_contact_ids),
            "register_path": str(self.register_path),
            "status": self.status,
            "deleted_contact_ids": [],
        }
