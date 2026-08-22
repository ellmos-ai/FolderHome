"""Contracts for evidenced document events and provider-neutral calendar handoffs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ACTION_ID_PATTERN = re.compile(r"calendar_action_[0-9a-f]{32}")
_APPROVAL_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_CANDIDATE_ID_PATTERN = re.compile(r"calendar_candidate_[0-9a-f]{64}")
_DOCUMENT_ID_PATTERN = re.compile(r"doc_[0-9a-f]{64}")
_EVENT_ID_PATTERN = re.compile(r"calendar_event_[0-9a-f]{64}")
_EVENT_UID_PATTERN = re.compile(r"[0-9a-f]{64}@folderhome\.local")
_EXECUTION_ID_PATTERN = re.compile(r"calendar_exec_[0-9a-f]{64}")
_PLAN_ID_PATTERN = re.compile(r"calendar_plan_[0-9a-f]{64}")
_REVISION_PATTERN = re.compile(r"calendar_revision_[0-9a-f]{64}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class CalendarBackend(StrEnum):
    """Calendar targets selectable through configuration and profile rules."""

    FOLDERHOME_LOCAL = "folderhome_local"
    UPTODAY_ICS = "uptoday_ics"
    ROUTINIKA = "routinika"
    GOOGLE = "google"


@dataclass(frozen=True, slots=True)
class CalendarConfiguration:
    """OS-account calendar defaults and local UpToday handoff location."""

    config_path: Path
    default_backend: CalendarBackend
    default_timezone: str
    uptoday_ics_directory: Path

    SCHEMA = "folderhome.calendar-config.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "config_path", self.config_path.resolve())
        object.__setattr__(
            self,
            "uptoday_ics_directory",
            self.uptoday_ics_directory.resolve(),
        )
        try:
            ZoneInfo(self.default_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"Unbekannte Standardzeitzone: {self.default_timezone}"
            ) from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "config_path": str(self.config_path),
            "default_backend": self.default_backend.value,
            "default_timezone": self.default_timezone,
            "uptoday_ics_directory": str(self.uptoday_ics_directory),
        }


@dataclass(frozen=True, slots=True)
class CalendarEvidence:
    """Exact labeled line supporting one normalized event field."""

    field: str
    line_number: int
    label: str

    def __post_init__(self) -> None:
        if not self.field or self.line_number < 1 or not self.label:
            raise ValueError("Terminevidenz benötigt Feld, Zeilennummer und Label.")

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "line_number": self.line_number,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class CalendarCandidate:
    """One normalized event candidate bound to immutable document evidence."""

    candidate_id: str
    event_uid: str
    profile_id: str
    area: str
    title: str
    event_date: str
    start_time: str | None
    end_time: str | None
    timezone: str
    timezone_basis: str
    location: str | None
    source_document_id: str
    source_sha256: str
    source_path: Path
    evidence: tuple[CalendarEvidence, ...]

    SCHEMA = "folderhome.calendar-candidate.v1"

    def __post_init__(self) -> None:
        if _CANDIDATE_ID_PATTERN.fullmatch(self.candidate_id) is None:
            raise ValueError("candidate_id muss calendar_candidate_<sha256> verwenden.")
        if _EVENT_UID_PATTERN.fullmatch(self.event_uid) is None:
            raise ValueError("event_uid muss <sha256>@folderhome.local verwenden.")
        if _DOCUMENT_ID_PATTERN.fullmatch(self.source_document_id) is None:
            raise ValueError("source_document_id muss doc_<sha256> verwenden.")
        if _SHA256_PATTERN.fullmatch(self.source_sha256) is None:
            raise ValueError("source_sha256 muss ein kleingeschriebener SHA-256 sein.")
        if not self.profile_id or not self.area or not self.title:
            raise ValueError("Terminkandidat benötigt Profil, Bereich und Titel.")
        try:
            date.fromisoformat(self.event_date)
            ZoneInfo(self.timezone)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Terminkandidat besitzt Datum oder Zeitzone ohne Gültigkeit.") from exc
        if self.start_time is None and self.end_time is not None:
            raise ValueError("Eine Endzeit benötigt eine Startzeit.")
        if not self.timezone_basis or not self.evidence:
            raise ValueError("Terminkandidat benötigt Zeitzonenbasis und Evidenz.")
        object.__setattr__(self, "source_path", self.source_path.resolve())

    @property
    def all_day(self) -> bool:
        return self.start_time is None

    @property
    def start_at(self) -> str:
        if self.start_time is None:
            return self.event_date
        local = datetime.fromisoformat(f"{self.event_date}T{self.start_time}:00")
        return local.replace(tzinfo=ZoneInfo(self.timezone)).isoformat()

    @property
    def conflict_key(self) -> tuple[str, str, str, str] | None:
        if self.start_time is None:
            return None
        return (
            self.profile_id.casefold(),
            self.area.casefold(),
            self.event_date,
            self.start_time,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "candidate_id": self.candidate_id,
            "event_uid": self.event_uid,
            "profile_id": self.profile_id,
            "area": self.area,
            "title": self.title,
            "event_date": self.event_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timezone": self.timezone,
            "timezone_basis": self.timezone_basis,
            "location": self.location,
            "all_day": self.all_day,
            "start_at": self.start_at,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class DocumentCalendarAnalysis:
    """One document's event result without unrelated source text."""

    document_id: str
    source_path: Path
    source_sha256: str
    status: str
    candidate: CalendarCandidate | None
    issues: tuple[str, ...]

    SCHEMA = "folderhome.document-calendar-analysis.v1"

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
class FolderCalendarItem:
    """One visible file outcome in deterministic folder event analysis."""

    relative_path: str
    status: str
    analysis: DocumentCalendarAnalysis | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderCalendarAnalysis:
    """Read-only event candidate set for one explicit document folder."""

    source_root: Path
    profile_id: str
    area: str
    recursive: bool
    items: tuple[FolderCalendarItem, ...]

    SCHEMA = "folderhome.folder-calendar-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    @property
    def candidates(self) -> tuple[CalendarCandidate, ...]:
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


@dataclass(frozen=True, slots=True)
class CalendarHandoffAction:
    """One planned local calendar or ICS side effect, or a blocked boundary."""

    action_id: str
    candidate: CalendarCandidate
    backend: CalendarBackend
    status: str
    side_effect: str
    target_path: Path | None
    content_sha256: str | None
    message: str

    def __post_init__(self) -> None:
        if _ACTION_ID_PATTERN.fullmatch(self.action_id) is None:
            raise ValueError("action_id muss calendar_action_<hex> verwenden.")
        if self.target_path is not None:
            object.__setattr__(self, "target_path", self.target_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "candidate": self.candidate.to_dict(),
            "backend": self.backend.value,
            "status": self.status,
            "side_effect": self.side_effect,
            "target_path": str(self.target_path) if self.target_path else None,
            "content_sha256": self.content_sha256,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CalendarEventRecord:
    """One active event in the local FolderHome calendar store."""

    event_id: str
    event_uid: str
    candidate_id: str
    profile_id: str
    area: str
    title: str
    event_date: str
    start_time: str | None
    end_time: str | None
    timezone: str
    location: str | None
    source_document_id: str
    source_sha256: str
    source_path: Path
    status: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if _EVENT_ID_PATTERN.fullmatch(self.event_id) is None:
            raise ValueError("event_id muss calendar_event_<sha256> verwenden.")
        if _EVENT_UID_PATTERN.fullmatch(self.event_uid) is None:
            raise ValueError("event_uid ist ungültig.")
        if self.status != "active":
            raise ValueError("Kalenderereignisse unterstützen derzeit nur active.")
        object.__setattr__(self, "source_path", self.source_path.resolve())

    @property
    def conflict_key(self) -> tuple[str, str, str, str] | None:
        if self.start_time is None:
            return None
        return (
            self.profile_id.casefold(),
            self.area.casefold(),
            self.event_date,
            self.start_time,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_uid": self.event_uid,
            "candidate_id": self.candidate_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "title": self.title,
            "event_date": self.event_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timezone": self.timezone,
            "location": self.location,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class CalendarHandoffPlan:
    """Read-only event-to-backend plan with no connector invocation."""

    plan_id: str
    planned_at: str
    calendar_revision: str
    backend: CalendarBackend
    backend_source: str
    source_rule_ids: tuple[str, ...]
    configuration: CalendarConfiguration
    analysis: FolderCalendarAnalysis
    actions: tuple[CalendarHandoffAction, ...]

    SCHEMA = "folderhome.calendar-handoff-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss calendar_plan_<sha256> verwenden.")
        if _REVISION_PATTERN.fullmatch(self.calendar_revision) is None:
            raise ValueError("calendar_revision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "planned_at": self.planned_at,
            "calendar_revision": self.calendar_revision,
            "backend": self.backend.value,
            "backend_source": self.backend_source,
            "source_rule_ids": list(self.source_rule_ids),
            "configuration": self.configuration.to_dict(),
            "analysis": self.analysis.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "connector_invoked": False,
            "automatic_calendar_write": False,
            "completeness_guaranteed": False,
        }


@dataclass(frozen=True, slots=True)
class CalendarHandoffApproval:
    """Exact approval for selected planned calendar handoff actions."""

    approval_id: str
    plan_id: str
    calendar_revision: str
    action_ids: tuple[str, ...]
    approved_at: str

    SCHEMA = "folderhome.calendar-handoff-approval.v1"

    def __post_init__(self) -> None:
        if _APPROVAL_ID_PATTERN.fullmatch(self.approval_id) is None:
            raise ValueError("approval_id muss eine stabile Kleinbuchstaben-ID sein.")
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id ist ungültig.")
        if _REVISION_PATTERN.fullmatch(self.calendar_revision) is None:
            raise ValueError("calendar_revision ist ungültig.")
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
            "calendar_revision": self.calendar_revision,
            "action_ids": list(self.action_ids),
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class CalendarExecutionItem:
    """Verified result for one selected calendar handoff action."""

    action_id: str
    event_uid: str
    event_id: str | None
    output_path: Path | None
    output_sha256: str | None
    status: str
    undo_supported: bool
    undo_action: str | None

    def __post_init__(self) -> None:
        if _ACTION_ID_PATTERN.fullmatch(self.action_id) is None:
            raise ValueError("action_id ist ungültig.")
        if self.output_path is not None:
            object.__setattr__(self, "output_path", self.output_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "event_uid": self.event_uid,
            "event_id": self.event_id,
            "output_path": str(self.output_path) if self.output_path else None,
            "output_sha256": self.output_sha256,
            "status": self.status,
            "undo": {
                "supported": self.undo_supported,
                "action": self.undo_action,
            },
        }


@dataclass(frozen=True, slots=True)
class CalendarExecutionReport:
    """Audited calendar execution without implicit connector invocation."""

    execution_id: str
    plan_id: str
    approval_id: str
    backend: CalendarBackend
    calendar_revision_before: str
    calendar_revision_after: str
    items: tuple[CalendarExecutionItem, ...]
    state_path: Path
    status: str = "executed"

    SCHEMA = "folderhome.calendar-execution-report.v1"

    def __post_init__(self) -> None:
        if _EXECUTION_ID_PATTERN.fullmatch(self.execution_id) is None:
            raise ValueError("execution_id muss calendar_exec_<sha256> verwenden.")
        object.__setattr__(self, "state_path", self.state_path.resolve())

    @property
    def created_event_ids(self) -> tuple[str, ...]:
        return tuple(item.event_id for item in self.items if item.event_id is not None)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "backend": self.backend.value,
            "calendar_revision_before": self.calendar_revision_before,
            "calendar_revision_after": self.calendar_revision_after,
            "items": [item.to_dict() for item in self.items],
            "created_event_ids": list(self.created_event_ids),
            "state_path": str(self.state_path),
            "status": self.status,
            "connector_invoked": False,
            "deleted_event_ids": [],
        }
