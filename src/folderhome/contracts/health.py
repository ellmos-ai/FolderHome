"""Contracts for source-grounded personal health dossiers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_ENTRY_ID = re.compile(r"health_entry_[0-9a-f]{64}")
_CONFLICT_ID = re.compile(r"health_conflict_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"health_dossier_[0-9a-f]{64}")
_HANDOFF_ID = re.compile(r"health_handoff_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_REVISION = re.compile(r"[0-9a-f]{40}")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True, slots=True)
class HealthEvidence:
    """One exact line from one locally extracted source document."""

    document_id: str
    relative_path: str
    source_sha256: str
    line_number: int
    label: str
    excerpt: str

    def __post_init__(self) -> None:
        if _DOCUMENT_ID.fullmatch(self.document_id) is None:
            raise ValueError("Gesundheitsevidenz benötigt eine gültige document_id.")
        if not self.relative_path or Path(self.relative_path).is_absolute():
            raise ValueError("Gesundheitsevidenz benötigt einen relativen Quellpfad.")
        if _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("Gesundheitsevidenz benötigt einen gültigen Quellhash.")
        if self.line_number < 1 or not self.label or not self.excerpt:
            raise ValueError("Gesundheitsevidenz benötigt Zeile, Label und Auszug.")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "line_number": self.line_number,
            "label": self.label,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True, slots=True)
class HealthTimelineEntry:
    """One extractive statement positioned by its documented source date."""

    entry_id: str
    documented_date: str
    kind: str
    label: str
    statement: str
    specialty: str | None
    evidence: HealthEvidence

    def __post_init__(self) -> None:
        if _ENTRY_ID.fullmatch(self.entry_id) is None:
            raise ValueError("entry_id muss health_entry_<sha256> verwenden.")
        if _DATE.fullmatch(self.documented_date) is None:
            raise ValueError("documented_date muss ein ISO-Datum sein.")
        if self.kind not in {
            "finding",
            "medication",
            "appointment",
            "question",
            "documented_fact",
            "source_excerpt",
        }:
            raise ValueError("Unbekannte Art eines Gesundheits-Zeitlinieneintrags.")
        if not self.label or not self.statement:
            raise ValueError("Zeitlinieneintrag benötigt Label und Aussage.")

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "documented_date": self.documented_date,
            "kind": self.kind,
            "label": self.label,
            "statement": self.statement,
            "specialty": self.specialty,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class HealthSource:
    """Visible processing status for every file considered for the dossier."""

    relative_path: str
    status: str
    message: str
    document_id: str | None
    source_sha256: str | None
    documented_date: str | None
    document_type: str | None
    specialty: str | None
    privacy_status: str | None

    def __post_init__(self) -> None:
        if not self.relative_path or Path(self.relative_path).is_absolute():
            raise ValueError("Gesundheitsquelle benötigt einen relativen Pfad.")
        if self.status not in {
            "included",
            "blocked",
            "unreadable",
            "missing_date",
            "invalid_date",
            "future_date",
            "unsupported",
        }:
            raise ValueError("Unbekannter Gesundheitsquellenstatus.")
        if not self.message:
            raise ValueError("Gesundheitsquelle benötigt eine Statusmeldung.")
        if self.document_id is not None and _DOCUMENT_ID.fullmatch(self.document_id) is None:
            raise ValueError("Ungültige document_id der Gesundheitsquelle.")
        if self.source_sha256 is not None and _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("Ungültiger Quellhash der Gesundheitsquelle.")

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status,
            "message": self.message,
            "document_id": self.document_id,
            "source_sha256": self.source_sha256,
            "documented_date": self.documented_date,
            "document_type": self.document_type,
            "specialty": self.specialty,
            "privacy_status": self.privacy_status,
        }


@dataclass(frozen=True, slots=True)
class HealthConflictCandidate:
    """Direct conflict between differently documented values of one labeled field."""

    conflict_id: str
    field: str
    values: tuple[str, ...]
    evidence: tuple[HealthEvidence, ...]

    def __post_init__(self) -> None:
        if _CONFLICT_ID.fullmatch(self.conflict_id) is None:
            raise ValueError("conflict_id muss health_conflict_<sha256> verwenden.")
        if not self.field or len(self.values) < 2 or len(self.evidence) < 2:
            raise ValueError("Konfliktkandidat benötigt Feld, Werte und Evidenz.")

    def to_dict(self) -> dict[str, object]:
        return {
            "conflict_id": self.conflict_id,
            "field": self.field,
            "values": list(self.values),
            "evidence": [item.to_dict() for item in self.evidence],
            "requires_human_review": True,
        }


@dataclass(frozen=True, slots=True)
class HealthMissingPeriod:
    """A visible interval between two dated source documents."""

    start: str
    end: str
    days_without_document: int
    previous_document_date: str
    next_document_date: str

    def __post_init__(self) -> None:
        if self.days_without_document < 1:
            raise ValueError("Fehlzeitraum benötigt mindestens einen Tag.")
        if any(
            _DATE.fullmatch(value) is None
            for value in (
                self.start,
                self.end,
                self.previous_document_date,
                self.next_document_date,
            )
        ):
            raise ValueError("Fehlzeitraum benötigt ISO-Daten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "start": self.start,
            "end": self.end,
            "days_without_document": self.days_without_document,
            "previous_document_date": self.previous_document_date,
            "next_document_date": self.next_document_date,
        }


@dataclass(frozen=True, slots=True)
class HealthCoverage:
    """Observed source-date coverage without claiming medical completeness."""

    first_document_date: str | None
    last_document_date: str | None
    gap_threshold_days: int
    missing_periods: tuple[HealthMissingPeriod, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "first_document_date": self.first_document_date,
            "last_document_date": self.last_document_date,
            "gap_threshold_days": self.gap_threshold_days,
            "missing_periods": [item.to_dict() for item in self.missing_periods],
            "coverage_means_medical_completeness": False,
        }


@dataclass(frozen=True, slots=True)
class HealthDossierReport:
    """Structured and Markdown views of one local, extractive health dossier."""

    report_id: str
    profile_id: str
    source_root: Path
    as_of: str
    sources: tuple[HealthSource, ...]
    timeline: tuple[HealthTimelineEntry, ...]
    conflicts: tuple[HealthConflictCandidate, ...]
    coverage: HealthCoverage
    markdown: str

    SCHEMA = "folderhome.health-dossier.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("report_id muss health_dossier_<sha256> verwenden.")
        if not self.profile_id:
            raise ValueError("Gesundheitsdossier benötigt ein Profil.")
        object.__setattr__(self, "source_root", self.source_root.resolve())
        if _DATE.fullmatch(self.as_of) is None:
            raise ValueError("as_of muss ein ISO-Datum sein.")

    @property
    def schema(self) -> str:
        return self.SCHEMA

    @property
    def unreadable_sources(self) -> tuple[str, ...]:
        return tuple(item.relative_path for item in self.sources if item.status == "unreadable")

    @property
    def blocked_sources(self) -> tuple[str, ...]:
        return tuple(item.relative_path for item in self.sources if item.status == "blocked")

    @property
    def undated_sources(self) -> tuple[str, ...]:
        return tuple(item.relative_path for item in self.sources if item.status == "missing_date")

    @property
    def medical_advice(self) -> bool:
        return False

    @property
    def completeness_claimed(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "profile_id": self.profile_id,
            "source_root": str(self.source_root),
            "as_of": self.as_of,
            "sources": [item.to_dict() for item in self.sources],
            "timeline": [item.to_dict() for item in self.timeline],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "coverage": self.coverage.to_dict(),
            "unreadable_sources": list(self.unreadable_sources),
            "blocked_sources": list(self.blocked_sources),
            "undated_sources": list(self.undated_sources),
            "markdown": self.markdown,
            "medical_advice": self.medical_advice,
            "completeness_claimed": self.completeness_claimed,
            "remote_provider_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class HealthReportHandoff:
    """Non-executing handoff description for an optional local report provider."""

    handoff_id: str
    report_id: str
    provider_id: str
    provider_revision: str
    requested_format: str
    payload_sha256: str
    status: str
    reason: str

    SCHEMA = "folderhome.health-report-handoff.v1"

    def __post_init__(self) -> None:
        if _HANDOFF_ID.fullmatch(self.handoff_id) is None:
            raise ValueError("handoff_id muss health_handoff_<sha256> verwenden.")
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Handoff benötigt eine gültige Dossier-ID.")
        if not self.provider_id or _GIT_REVISION.fullmatch(self.provider_revision) is None:
            raise ValueError("Handoff benötigt Provider und Revision.")
        if self.requested_format not in {"docx", "odt"}:
            raise ValueError("Gesundheitsbericht-Handoff unterstützt DOCX oder ODT.")
        if _SHA256.fullmatch(self.payload_sha256) is None:
            raise ValueError("Handoff benötigt einen gültigen Payload-Hash.")
        if self.status not in {"blocked", "review_required"} or not self.reason:
            raise ValueError("Handoff benötigt einen prüfbaren Status und Grund.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "handoff_id": self.handoff_id,
            "report_id": self.report_id,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "requested_format": self.requested_format,
            "input_schema": HealthDossierReport.SCHEMA,
            "payload_sha256": self.payload_sha256,
            "status": self.status,
            "reason": self.reason,
            "contains_sensitive_data": True,
            "provider_invoked": False,
            "network_used": False,
        }
