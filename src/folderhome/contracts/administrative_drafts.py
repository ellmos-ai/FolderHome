"""Contracts for evidence-bound, unsubmitted administrative draft letters."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from folderhome.contracts.correspondence import (
    CorrespondenceOutputReport,
    CorrespondenceParty,
    CorrespondencePreview,
)

_REQUEST_ID = re.compile(r"admin_draft_request_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"admin_draft_plan_[0-9a-f]{64}")
_FACT_ID = re.compile(r"admin_draft_fact_[0-9a-f]{64}")
_APPROVAL_ID = re.compile(r"admin_draft_approval_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"admin_draft_output_[0-9a-f]{64}")
_ANALYSIS_ID = re.compile(r"notice_analysis_[0-9a-f]{64}")
_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FIELD_NAME = re.compile(r"[a-z][a-z0-9_]{1,47}")


class AdministrativeDraftKind(StrEnum):
    OBJECTION = "objection"
    AUTHORITY_RESPONSE = "authority_response"
    BENEFIT_APPLICATION = "benefit_application"


@dataclass(frozen=True, slots=True)
class AdministrativeDraftFact:
    fact_id: str
    text: str
    basis: str
    field_name: str | None
    line_number: int | None
    document_id: str | None
    source_sha256: str | None

    SCHEMA = "folderhome.administrative-draft-fact.v1"

    def __post_init__(self) -> None:
        if _FACT_ID.fullmatch(self.fact_id) is None or not self.text.strip():
            raise ValueError("Entwurfsfakt benötigt ID und Inhalt.")
        if self.basis not in {"document_evidence", "user_provided"}:
            raise ValueError("Entwurfsfakt besitzt eine unbekannte Grundlage.")
        document_bound = self.basis == "document_evidence"
        if document_bound:
            if self.field_name is None or _FIELD_NAME.fullmatch(self.field_name) is None:
                raise ValueError("Dokumentfakt benötigt einen gültigen Feldnamen.")
            if self.line_number is None or self.line_number < 1:
                raise ValueError("Dokumentfakt benötigt eine Evidenzzeile.")
            if self.document_id is None or _DOCUMENT_ID.fullmatch(self.document_id) is None:
                raise ValueError("Dokumentfakt benötigt eine Dokument-ID.")
            if self.source_sha256 is None or _SHA256.fullmatch(self.source_sha256) is None:
                raise ValueError("Dokumentfakt benötigt einen Quellhash.")
        elif any(
            value is not None
            for value in (
                self.field_name,
                self.line_number,
                self.document_id,
                self.source_sha256,
            )
        ):
            raise ValueError("Nutzerfakt darf keine Dokumentevidenz vortäuschen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "fact_id": self.fact_id,
            "text": self.text,
            "basis": self.basis,
            "field_name": self.field_name,
            "line_number": self.line_number,
            "document_id": self.document_id,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class AdministrativeDraftRequest:
    request_id: str
    draft_kind: AdministrativeDraftKind
    profile_id: str
    created_on: str
    sender: CorrespondenceParty
    recipient: CorrespondenceParty
    requested_outcome: str
    user_statements: tuple[str, ...]
    attachments: tuple[str, ...]
    expected_notice_source_sha256: str | None

    SCHEMA = "folderhome.administrative-draft-request.v1"

    def __post_init__(self) -> None:
        if _REQUEST_ID.fullmatch(self.request_id) is None or not self.profile_id.strip():
            raise ValueError("Verwaltungsentwurfsanfrage besitzt ungültige IDs.")
        if not isinstance(self.draft_kind, AdministrativeDraftKind):
            raise ValueError("Verwaltungsentwurfsanfrage besitzt eine ungültige Art.")
        date.fromisoformat(self.created_on)
        if not self.requested_outcome.strip() or not self.user_statements:
            raise ValueError("Entwurfsanfrage benötigt Ziel und bestätigte Angaben.")
        if any(not value.strip() for value in (*self.user_statements, *self.attachments)):
            raise ValueError("Entwurfsangaben und Anlagen dürfen nicht leer sein.")
        needs_notice = self.draft_kind is not AdministrativeDraftKind.BENEFIT_APPLICATION
        if needs_notice != (self.expected_notice_source_sha256 is not None):
            raise ValueError("Bescheidentwurf und Analysebindung passen nicht zusammen.")
        if self.expected_notice_source_sha256 is not None and _SHA256.fullmatch(
            self.expected_notice_source_sha256
        ) is None:
            raise ValueError("Erwarteter Bescheid-Quellhash ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "draft_kind": self.draft_kind.value,
            "profile_id": self.profile_id,
            "created_on": self.created_on,
            "sender": self.sender.to_dict(),
            "recipient": self.recipient.to_dict(),
            "requested_outcome": self.requested_outcome,
            "user_statements": list(self.user_statements),
            "attachments": list(self.attachments),
            "expected_notice_source_sha256": self.expected_notice_source_sha256,
        }


@dataclass(frozen=True, slots=True)
class AdministrativeDraftPlan:
    plan_id: str
    request: AdministrativeDraftRequest
    notice_analysis_id: str | None
    notice_source_path: Path | None
    notice_source_sha256: str | None
    facts: tuple[AdministrativeDraftFact, ...]
    unresolved_items: tuple[str, ...]
    warnings: tuple[str, ...]
    correspondence_preview: CorrespondencePreview
    status: str = "review_required"
    legal_review_status: str = "not_performed"
    deadline_legally_calculated: bool = False
    eligibility_assessed: bool = False
    human_confirmation_required: bool = True
    send_supported: bool = False

    SCHEMA = "folderhome.administrative-draft-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Verwaltungsentwurfsplan besitzt eine ungültige ID.")
        if self.notice_source_path is not None:
            object.__setattr__(self, "notice_source_path", self.notice_source_path.resolve())
        notice_bound = self.notice_analysis_id is not None
        if notice_bound:
            if _ANALYSIS_ID.fullmatch(self.notice_analysis_id or "") is None:
                raise ValueError("Entwurfsplan besitzt eine ungültige Analyse-ID.")
            if self.notice_source_path is None or self.notice_source_sha256 is None:
                raise ValueError("Bescheidentwurf benötigt Quelle und Quellhash.")
            if _SHA256.fullmatch(self.notice_source_sha256) is None:
                raise ValueError("Bescheidentwurf besitzt einen ungültigen Quellhash.")
        elif self.notice_source_path is not None or self.notice_source_sha256 is not None:
            raise ValueError("Antragsentwurf darf keine Bescheidquelle vortäuschen.")
        if self.status != "review_required" or self.legal_review_status != "not_performed":
            raise ValueError("Verwaltungsentwurf muss ungeprüft bleiben.")
        if (
            self.deadline_legally_calculated
            or self.eligibility_assessed
            or not self.human_confirmation_required
            or self.send_supported
        ):
            raise ValueError("Verwaltungsentwurf überschreitet die sichere Entwurfsgrenze.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "request": self.request.to_dict(),
            "notice_analysis_id": self.notice_analysis_id,
            "notice_source_path": (
                str(self.notice_source_path) if self.notice_source_path else None
            ),
            "notice_source_sha256": self.notice_source_sha256,
            "facts": [item.to_dict() for item in self.facts],
            "unresolved_items": list(self.unresolved_items),
            "warnings": list(self.warnings),
            "correspondence_preview": self.correspondence_preview.to_dict(),
            "status": "review_required",
            "legal_review_status": "not_performed",
            "deadline_legally_calculated": False,
            "eligibility_assessed": False,
            "human_confirmation_required": True,
            "send_supported": False,
            "sent": False,
            "external_actions": [],
        }


@dataclass(frozen=True, slots=True)
class AdministrativeDraftApproval:
    approval_id: str
    plan_id: str
    markdown_sha256: str
    text_sha256: str
    approved_at: str
    confirmed_content_review: bool
    confirmed_no_legal_review: bool
    allow_local_output_write: bool

    SCHEMA = "folderhome.administrative-draft-approval.v1"

    def __post_init__(self) -> None:
        if _APPROVAL_ID.fullmatch(self.approval_id) is None:
            raise ValueError("Verwaltungsentwurfsfreigabe besitzt eine ungültige ID.")
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Verwaltungsentwurfsfreigabe besitzt eine ungültige Plan-ID.")
        if any(
            _SHA256.fullmatch(value) is None
            for value in (self.markdown_sha256, self.text_sha256)
        ):
            raise ValueError("Verwaltungsentwurfsfreigabe besitzt ungültige Hashes.")
        parsed = datetime.fromisoformat(self.approved_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Verwaltungsentwurfsfreigabe benötigt eine Zeitzone.")
        if not all(
            isinstance(value, bool)
            for value in (
                self.confirmed_content_review,
                self.confirmed_no_legal_review,
                self.allow_local_output_write,
            )
        ):
            raise ValueError("Verwaltungsentwurfsfreigabe benötigt boolesche Bestätigungen.")
        if not (
            self.confirmed_content_review
            and self.confirmed_no_legal_review
            and self.allow_local_output_write
        ):
            raise ValueError("Verwaltungsentwurfsfreigabe benötigt alle Bestätigungen.")

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        markdown_sha256: str,
        text_sha256: str,
        approved_at: str,
        confirmed_content_review: bool,
        confirmed_no_legal_review: bool,
        allow_local_output_write: bool,
    ) -> AdministrativeDraftApproval:
        material = {
            "plan_id": plan_id,
            "markdown_sha256": markdown_sha256,
            "text_sha256": text_sha256,
            "approved_at": approved_at,
            "confirmed_content_review": confirmed_content_review,
            "confirmed_no_legal_review": confirmed_no_legal_review,
            "allow_local_output_write": allow_local_output_write,
        }
        approval_id = f"admin_draft_approval_{_json_sha(material)}"
        return cls(approval_id=approval_id, **material)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "markdown_sha256": self.markdown_sha256,
            "text_sha256": self.text_sha256,
            "approved_at": self.approved_at,
            "confirmed_content_review": self.confirmed_content_review,
            "confirmed_no_legal_review": self.confirmed_no_legal_review,
            "allow_local_output_write": self.allow_local_output_write,
        }


@dataclass(frozen=True, slots=True)
class AdministrativeDraftOutputReport:
    report_id: str
    plan_id: str
    approval_id: str
    correspondence_output: CorrespondenceOutputReport
    status: str
    sent: bool = False
    external_actions_performed: bool = False

    SCHEMA = "folderhome.administrative-draft-output-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Verwaltungsentwurfsausgabe besitzt eine ungültige ID.")
        if _PLAN_ID.fullmatch(self.plan_id) is None or _APPROVAL_ID.fullmatch(
            self.approval_id
        ) is None:
            raise ValueError("Verwaltungsentwurfsausgabe besitzt ungültige Bindungen.")
        if self.status != "executed" or self.sent or self.external_actions_performed:
            raise ValueError("Verwaltungsentwurfsausgabe darf keine Außenwirkung behaupten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "correspondence_output": self.correspondence_output.to_dict(),
            "status": "executed",
            "sent": False,
            "external_actions_performed": False,
        }


def _json_sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
