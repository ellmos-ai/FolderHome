"""Contracts for source-bound understanding of official notices."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

_ANALYSIS_ID = re.compile(r"notice_analysis_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"notice_output_report_[0-9a-f]{64}")
_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FIELD = re.compile(r"[a-z][a-z0-9_]{1,47}")


def _aware(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Zeitstempel benötigt eine Zeitzone.")


@dataclass(frozen=True, slots=True)
class NoticeEvidence:
    field_name: str
    value: str
    line_number: int
    document_id: str
    source_sha256: str

    SCHEMA = "folderhome.notice-evidence.v1"

    def __post_init__(self) -> None:
        if _FIELD.fullmatch(self.field_name) is None or not self.value.strip():
            raise ValueError("Bescheidevidenz besitzt ein ungültiges Feld.")
        if isinstance(self.line_number, bool) or self.line_number < 1:
            raise ValueError("Bescheidevidenz benötigt eine positive Zeilennummer.")
        if _DOCUMENT_ID.fullmatch(self.document_id) is None:
            raise ValueError("Bescheidevidenz besitzt eine ungültige Dokument-ID.")
        if _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("Bescheidevidenz besitzt einen ungültigen Quellhash.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "field_name": self.field_name,
            "value": self.value,
            "line_number": self.line_number,
            "document_id": self.document_id,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class NoticeConflict:
    field_name: str
    values: tuple[str, ...]
    evidence_lines: tuple[int, ...]

    SCHEMA = "folderhome.notice-conflict.v1"

    def __post_init__(self) -> None:
        if _FIELD.fullmatch(self.field_name) is None or len(self.values) < 2:
            raise ValueError("Bescheidkonflikt besitzt kein mehrdeutiges Feld.")
        if len(set(self.values)) != len(self.values):
            raise ValueError("Bescheidkonflikt enthält doppelte Werte.")
        if len(self.values) != len(self.evidence_lines):
            raise ValueError("Bescheidkonflikt besitzt unvollständige Evidenz.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "field_name": self.field_name,
            "values": list(self.values),
            "evidence_lines": list(self.evidence_lines),
        }


@dataclass(frozen=True, slots=True)
class OfficialNoticeAnalysis:
    analysis_id: str
    profile_id: str
    as_of: str
    received_on: str | None
    received_on_basis: str | None
    source_path: Path
    source_sha256: str
    document_id: str
    extraction_provider: str
    extraction_provider_revision: str
    privacy_status: str
    notice_type: str | None
    notice_type_basis: str | None
    authority: str | None
    file_reference: str | None
    notice_date: str | None
    benefit_period: str | None
    decision: str | None
    reasons: tuple[str, ...]
    legal_remedy: str | None
    deadline_text: str | None
    explicit_deadline_date: str | None
    legal_remedy_office: str | None
    days_until_explicit_deadline: int | None
    deadline_urgency: str | None
    evidence: tuple[NoticeEvidence, ...]
    missing_fields: tuple[str, ...]
    conflicts: tuple[NoticeConflict, ...]
    warnings: tuple[str, ...]
    status: str
    legal_review_status: str = "not_performed"
    legal_review_reason: str = "law-checker runtime unavailable or not requested"
    deadline_legally_calculated: bool = False
    response_generated: bool = False
    source_document_modified: bool = False

    SCHEMA = "folderhome.official-notice-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if _ANALYSIS_ID.fullmatch(self.analysis_id) is None:
            raise ValueError("Bescheidanalyse besitzt eine ungültige ID.")
        if not self.profile_id.strip() or _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("Bescheidanalyse besitzt eine ungültige Profil-/Quellbindung.")
        if _DOCUMENT_ID.fullmatch(self.document_id) is None:
            raise ValueError("Bescheidanalyse besitzt eine ungültige Dokument-ID.")
        _aware(self.as_of)
        if self.received_on is not None:
            date.fromisoformat(self.received_on)
            if self.received_on_basis != "user_provided":
                raise ValueError("Zugangsdatum muss als Nutzerangabe ausgewiesen sein.")
        if self.notice_date is not None:
            date.fromisoformat(self.notice_date)
        if self.explicit_deadline_date is not None:
            date.fromisoformat(self.explicit_deadline_date)
        if self.deadline_urgency not in {None, "overdue", "today", "urgent", "soon", "later"}:
            raise ValueError("Bescheidanalyse besitzt eine ungültige Fristdringlichkeit.")
        if self.status not in {"ready_for_review", "review_required"}:
            raise ValueError("Bescheidanalyse besitzt einen unbekannten Status.")
        if self.legal_review_status != "not_performed":
            raise ValueError("Phase 31 darf keine durchgeführte Rechtsprüfung behaupten.")
        if (
            self.deadline_legally_calculated
            or self.response_generated
            or self.source_document_modified
        ):
            raise ValueError("Bescheidanalyse überschreitet die reine Verständnisgrenze.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "analysis_id": self.analysis_id,
            "profile_id": self.profile_id,
            "as_of": self.as_of,
            "received_on": self.received_on,
            "received_on_basis": self.received_on_basis,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "document_id": self.document_id,
            "extraction_provider": self.extraction_provider,
            "extraction_provider_revision": self.extraction_provider_revision,
            "privacy_status": self.privacy_status,
            "notice_type": self.notice_type,
            "notice_type_basis": self.notice_type_basis,
            "authority": self.authority,
            "file_reference": self.file_reference,
            "notice_date": self.notice_date,
            "benefit_period": self.benefit_period,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "legal_remedy": self.legal_remedy,
            "deadline_text": self.deadline_text,
            "explicit_deadline_date": self.explicit_deadline_date,
            "legal_remedy_office": self.legal_remedy_office,
            "days_until_explicit_deadline": self.days_until_explicit_deadline,
            "deadline_urgency": self.deadline_urgency,
            "evidence": [item.to_dict() for item in self.evidence],
            "missing_fields": list(self.missing_fields),
            "conflicts": [item.to_dict() for item in self.conflicts],
            "warnings": list(self.warnings),
            "status": self.status,
            "legal_review_status": "not_performed",
            "legal_review_reason": self.legal_review_reason,
            "deadline_legally_calculated": False,
            "response_generated": False,
            "source_document_modified": False,
            "external_actions": [],
        }


@dataclass(frozen=True, slots=True)
class OfficialNoticeOutputReport:
    report_id: str
    analysis_id: str
    markdown_path: Path
    markdown_sha256: str
    json_path: Path
    json_sha256: str
    status: str
    source_document_modified: bool = False
    external_actions_performed: bool = False

    SCHEMA = "folderhome.official-notice-output-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "markdown_path", self.markdown_path.resolve())
        object.__setattr__(self, "json_path", self.json_path.resolve())
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Bescheidausgabebericht besitzt eine ungültige ID.")
        if _ANALYSIS_ID.fullmatch(self.analysis_id) is None:
            raise ValueError("Bescheidausgabebericht besitzt eine ungültige Analyse-ID.")
        if any(
            _SHA256.fullmatch(value) is None
            for value in (self.markdown_sha256, self.json_sha256)
        ):
            raise ValueError("Bescheidausgabebericht besitzt ungültige Hashes.")
        if self.status != "executed":
            raise ValueError("Bescheidausgabebericht besitzt einen ungültigen Status.")
        if self.source_document_modified or self.external_actions_performed:
            raise ValueError("Bescheidausgabebericht darf keine Außenwirkung ausweisen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "analysis_id": self.analysis_id,
            "markdown_path": str(self.markdown_path),
            "markdown_sha256": self.markdown_sha256,
            "json_path": str(self.json_path),
            "json_sha256": self.json_sha256,
            "status": self.status,
            "source_document_modified": False,
            "external_actions_performed": False,
        }
