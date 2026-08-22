"""Contracts for evidenced medication schedules and confirmed intake events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ACTION_ID = re.compile(r"medication_action_[0-9a-f]{32}")
_APPROVAL_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_DOSE_ID = re.compile(r"medication_dose_[0-9a-f]{64}")
_EVENT_ID = re.compile(r"medication_intake_event_[0-9a-f]{64}")
_INVENTORY_ITEM_ID = re.compile(r"inventory_item_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"medication_plan_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"medication_report_[0-9a-f]{64}")
_REVISION = re.compile(r"medication_revision_[0-9a-f]{64}")
_SCHEDULE_ID = re.compile(r"medication_schedule_[0-9a-f]{64}")
_SCHEDULE_KEY = re.compile(r"medication_schedule_key_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class MedicationEvidence:
    field: str
    line_number: int
    label: str

    def __post_init__(self) -> None:
        if not self.field or self.line_number < 1 or not self.label:
            raise ValueError("Medikamentenevidenz benötigt Feld, Zeilennummer und Label.")

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "line_number": self.line_number,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class MedicationScheduleCandidate:
    schedule_id: str
    schedule_key: str
    profile_id: str
    medication_name: str
    dose_quantity_milli: int
    dose_unit: str
    scheduled_time: str
    timezone: str
    weekdays: tuple[int, ...]
    valid_from: str
    valid_to: str | None
    inventory_item_id: str
    source_document_id: str
    source_sha256: str
    source_path: Path
    evidence: tuple[MedicationEvidence, ...]

    SCHEMA = "folderhome.medication-schedule-candidate.v1"

    def __post_init__(self) -> None:
        _validate_schedule_fields(self)
        object.__setattr__(self, "source_path", self.source_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "schedule_id": self.schedule_id,
            "schedule_key": self.schedule_key,
            "profile_id": self.profile_id,
            "medication_name": self.medication_name,
            "dose_quantity": _format_milli(self.dose_quantity_milli),
            "dose_quantity_milli": self.dose_quantity_milli,
            "dose_unit": self.dose_unit,
            "scheduled_time": self.scheduled_time,
            "timezone": self.timezone,
            "weekdays": list(self.weekdays),
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "inventory_item_id": self.inventory_item_id,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class MedicationPlanAnalysisItem:
    relative_path: str
    status: str
    schedule: MedicationScheduleCandidate | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status,
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderMedicationPlanAnalysis:
    source_root: Path
    profile_id: str
    items: tuple[MedicationPlanAnalysisItem, ...]

    SCHEMA = "folderhome.folder-medication-plan-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    @property
    def schedules(self) -> tuple[MedicationScheduleCandidate, ...]:
        return tuple(item.schedule for item in self.items if item.schedule is not None)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "source_root": str(self.source_root),
            "profile_id": self.profile_id,
            "schedule_count": len(self.schedules),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class MedicationImportAction:
    action_id: str
    schedule: MedicationScheduleCandidate
    status: str
    message: str

    def __post_init__(self) -> None:
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("action_id muss medication_action_<hex> verwenden.")
        if self.status not in {"planned", "noop", "blocked"}:
            raise ValueError("Medikamentenaktionsstatus ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "schedule": self.schedule.to_dict(),
            "status": self.status,
            "message": self.message,
            "side_effect": "local_medication_state" if self.status == "planned" else "none",
        }


@dataclass(frozen=True, slots=True)
class MedicationImportPlan:
    plan_id: str
    medication_revision: str
    analysis: FolderMedicationPlanAnalysis
    actions: tuple[MedicationImportAction, ...]

    SCHEMA = "folderhome.medication-import-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss medication_plan_<sha256> verwenden.")
        if _REVISION.fullmatch(self.medication_revision) is None:
            raise ValueError("medication_revision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "medication_revision": self.medication_revision,
            "analysis": self.analysis.to_dict(),
            "actions": [item.to_dict() for item in self.actions],
            "medical_advice": False,
            "automatic_medication_change": False,
        }


@dataclass(frozen=True, slots=True)
class MedicationImportApproval:
    approval_id: str
    plan_id: str
    medication_revision: str
    action_ids: tuple[str, ...]
    approved_at: str

    SCHEMA = "folderhome.medication-import-approval.v1"

    def __post_init__(self) -> None:
        _validate_approval_id(self.approval_id)
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id ist ungültig.")
        if _REVISION.fullmatch(self.medication_revision) is None:
            raise ValueError("medication_revision ist ungültig.")
        if len(set(self.action_ids)) != len(self.action_ids):
            raise ValueError("Medikamentenfreigabe enthält doppelte Aktionen.")
        if any(_ACTION_ID.fullmatch(item) is None for item in self.action_ids):
            raise ValueError("Medikamentenfreigabe enthält eine ungültige Aktion.")
        _aware_datetime(self.approved_at, "approved_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "medication_revision": self.medication_revision,
            "action_ids": list(self.action_ids),
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class MedicationScheduleRecord:
    schedule_id: str
    schedule_key: str
    profile_id: str
    medication_name: str
    dose_quantity_milli: int
    dose_unit: str
    scheduled_time: str
    timezone: str
    weekdays: tuple[int, ...]
    valid_from: str
    valid_to: str | None
    inventory_item_id: str
    source_document_id: str
    source_sha256: str
    source_path: str
    evidence: tuple[MedicationEvidence, ...]
    recorded_at: str

    def __post_init__(self) -> None:
        _validate_schedule_fields(self)

    def to_dict(self) -> dict[str, object]:
        return {
            "schedule_id": self.schedule_id,
            "schedule_key": self.schedule_key,
            "profile_id": self.profile_id,
            "medication_name": self.medication_name,
            "dose_quantity": _format_milli(self.dose_quantity_milli),
            "dose_quantity_milli": self.dose_quantity_milli,
            "dose_unit": self.dose_unit,
            "scheduled_time": self.scheduled_time,
            "timezone": self.timezone,
            "weekdays": list(self.weekdays),
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "inventory_item_id": self.inventory_item_id,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": self.source_path,
            "evidence": [item.to_dict() for item in self.evidence],
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True)
class MedicationImportReport:
    report_id: str
    plan_id: str
    approval_id: str
    revision_before: str
    revision_after: str
    created_schedule_ids: tuple[str, ...]
    state_path: Path
    status: str = "executed"

    SCHEMA = "folderhome.medication-import-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("report_id muss medication_report_<sha256> verwenden.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "status": self.status,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "revision_before": self.revision_before,
            "revision_after": self.revision_after,
            "created_schedule_ids": list(self.created_schedule_ids),
            "state_path": str(self.state_path),
        }


@dataclass(frozen=True, slots=True)
class MedicationIntakeConfirmation:
    confirmation_id: str
    medication_revision: str
    dose_id: str
    schedule_id: str
    scheduled_date: str
    confirmed_at: str

    SCHEMA = "folderhome.medication-intake-confirmation.v1"

    def __post_init__(self) -> None:
        _validate_approval_id(self.confirmation_id)
        if _REVISION.fullmatch(self.medication_revision) is None:
            raise ValueError("medication_revision ist ungültig.")
        if _DOSE_ID.fullmatch(self.dose_id) is None:
            raise ValueError("dose_id ist ungültig.")
        if _SCHEDULE_ID.fullmatch(self.schedule_id) is None:
            raise ValueError("schedule_id ist ungültig.")
        date.fromisoformat(self.scheduled_date)
        _aware_datetime(self.confirmed_at, "confirmed_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "confirmation_id": self.confirmation_id,
            "medication_revision": self.medication_revision,
            "dose_id": self.dose_id,
            "schedule_id": self.schedule_id,
            "scheduled_date": self.scheduled_date,
            "confirmed_at": self.confirmed_at,
        }


@dataclass(frozen=True, slots=True)
class MedicationIntakeEventRecord:
    event_id: str
    dose_id: str
    schedule_id: str
    profile_id: str
    scheduled_date: str
    confirmed_at: str
    confirmation_id: str

    def __post_init__(self) -> None:
        if _EVENT_ID.fullmatch(self.event_id) is None:
            raise ValueError("event_id ist ungültig.")
        if _DOSE_ID.fullmatch(self.dose_id) is None:
            raise ValueError("dose_id ist ungültig.")
        date.fromisoformat(self.scheduled_date)
        _aware_datetime(self.confirmed_at, "confirmed_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "dose_id": self.dose_id,
            "schedule_id": self.schedule_id,
            "profile_id": self.profile_id,
            "scheduled_date": self.scheduled_date,
            "confirmed_at": self.confirmed_at,
            "confirmation_id": self.confirmation_id,
        }


@dataclass(frozen=True, slots=True)
class MedicationDoseView:
    dose_id: str
    schedule_id: str
    profile_id: str
    medication_name: str
    dose_quantity_milli: int
    dose_unit: str
    scheduled_date: str
    scheduled_time: str
    timezone: str
    scheduled_at: str
    status: str
    confirmed_at: str | None
    inventory_item_id: str
    inventory_status: str

    def __post_init__(self) -> None:
        if self.status not in {"upcoming", "confirmation_pending", "confirmed"}:
            raise ValueError("Dosisstatus ist ungültig.")
        if self.inventory_status not in {
            "not_checked",
            "missing_evidence",
            "available_candidate",
            "insufficient_candidate",
        }:
            raise ValueError("Medikamenten-Bestandsstatus ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "dose_id": self.dose_id,
            "schedule_id": self.schedule_id,
            "profile_id": self.profile_id,
            "medication_name": self.medication_name,
            "dose_quantity": _format_milli(self.dose_quantity_milli),
            "dose_quantity_milli": self.dose_quantity_milli,
            "dose_unit": self.dose_unit,
            "scheduled_date": self.scheduled_date,
            "scheduled_time": self.scheduled_time,
            "timezone": self.timezone,
            "scheduled_at": self.scheduled_at,
            "status": self.status,
            "confirmed_at": self.confirmed_at,
            "inventory_item_id": self.inventory_item_id,
            "inventory_status": self.inventory_status,
        }


@dataclass(frozen=True, slots=True)
class MedicationDayReport:
    profile_id: str
    on_date: str
    as_of: str
    medication_revision: str
    doses: tuple[MedicationDoseView, ...]
    automatic_reminder_sent: bool = False

    SCHEMA = "folderhome.medication-day-report.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "profile_id": self.profile_id,
            "on_date": self.on_date,
            "as_of": self.as_of,
            "medication_revision": self.medication_revision,
            "doses": [item.to_dict() for item in self.doses],
            "automatic_reminder_sent": self.automatic_reminder_sent,
            "medical_advice": False,
            "completeness_guaranteed": False,
            "inventory_changed": False,
        }


@dataclass(frozen=True, slots=True)
class MedicationConfirmationReport:
    report_id: str
    confirmation_id: str
    dose_id: str
    revision_before: str
    revision_after: str
    created_event_id: str | None
    state_path: Path
    status: str

    SCHEMA = "folderhome.medication-confirmation-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("report_id ist ungültig.")
        if self.status not in {"executed", "noop"}:
            raise ValueError("Bestätigungsstatus ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "status": self.status,
            "confirmation_id": self.confirmation_id,
            "dose_id": self.dose_id,
            "revision_before": self.revision_before,
            "revision_after": self.revision_after,
            "created_event_id": self.created_event_id,
            "state_path": str(self.state_path),
            "inventory_changed": False,
        }


def _validate_schedule_fields(schedule: object) -> None:
    if _SCHEDULE_ID.fullmatch(schedule.schedule_id) is None:
        raise ValueError("schedule_id ist ungültig.")
    if _SCHEDULE_KEY.fullmatch(schedule.schedule_key) is None:
        raise ValueError("schedule_key ist ungültig.")
    if _INVENTORY_ITEM_ID.fullmatch(schedule.inventory_item_id) is None:
        raise ValueError("inventory_item_id ist ungültig.")
    if not all((schedule.profile_id, schedule.medication_name, schedule.dose_unit)):
        raise ValueError("Medikamentenplan benötigt Profil, Präparat und Dosiseinheit.")
    if schedule.dose_quantity_milli <= 0:
        raise ValueError("Dokumentierte Dosis muss größer als null sein.")
    time.fromisoformat(schedule.scheduled_time)
    try:
        ZoneInfo(schedule.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Zeitzone ist unbekannt.") from exc
    if not schedule.weekdays or tuple(sorted(set(schedule.weekdays))) != schedule.weekdays:
        raise ValueError("Wochentage müssen eindeutig und sortiert sein.")
    if any(day < 0 or day > 6 for day in schedule.weekdays):
        raise ValueError("Wochentag liegt außerhalb 0 bis 6.")
    start = date.fromisoformat(schedule.valid_from)
    if schedule.valid_to is not None and date.fromisoformat(schedule.valid_to) < start:
        raise ValueError("Gültigkeitszeitraum ist umgekehrt.")
    if _DOCUMENT_ID.fullmatch(schedule.source_document_id) is None:
        raise ValueError("source_document_id ist ungültig.")
    if _SHA256.fullmatch(schedule.source_sha256) is None:
        raise ValueError("source_sha256 ist ungültig.")


def _aware_datetime(value: str, field: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _validate_approval_id(value: str) -> None:
    if _APPROVAL_ID.fullmatch(value) is None:
        raise ValueError("Bestätigungs-/Freigabe-ID ist ungültig.")


def _format_milli(value: int) -> str:
    whole, remainder = divmod(value, 1000)
    if remainder == 0:
        return str(whole)
    return f"{whole}.{remainder:03d}".rstrip("0")
