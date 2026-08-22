"""Import evidenced medication schedules and record explicit intake confirmations."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.inventory_store import InventoryStore
from folderhome.capabilities.medication_store import MedicationStore, MedicationStoreError
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    DocumentRecord,
    FolderMedicationPlanAnalysis,
    MedicationConfirmationReport,
    MedicationDayReport,
    MedicationDoseView,
    MedicationEvidence,
    MedicationImportAction,
    MedicationImportApproval,
    MedicationImportPlan,
    MedicationImportReport,
    MedicationIntakeConfirmation,
    MedicationPlanAnalysisItem,
    MedicationScheduleCandidate,
    PrivacyStatus,
    build_inventory_item_id,
)

_LINE = re.compile(r"^\s*([^:]{1,48}):\s*(\S(?:.*\S)?)\s*$")
_TIME = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")
_LABELS = {
    "präparat": "medication_name",
    "dosis": "dose_quantity",
    "dosiseinheit": "dose_unit",
    "zeitpunkt": "scheduled_time",
    "zeitzone": "timezone",
    "wochentage": "weekdays",
    "gültig-von": "valid_from",
    "gültig-bis": "valid_to",
    "bestandsbereich": "inventory_area",
    "bestandsgegenstand": "inventory_name",
    "bestandseinheit": "inventory_unit",
}
_REQUIRED = {
    "medication_name",
    "dose_quantity",
    "dose_unit",
    "scheduled_time",
    "timezone",
    "weekdays",
    "valid_from",
    "inventory_area",
    "inventory_name",
    "inventory_unit",
}
_WEEKDAYS = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}


class MedicationWorkflowError(RuntimeError):
    """Raised when medication evidence or state is unsafe."""


class MedicationDocumentExtractor(Protocol):
    def extract(self, source_path: Path) -> DocumentRecord: ...


def analyze_folder_medication_plans(
    source_dir: Path,
    *,
    profile_id: str,
    extractor: MedicationDocumentExtractor,
    recursive: bool = True,
    allow_sensitive_local_read: bool = False,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderMedicationPlanAnalysis:
    root = source_dir.resolve()
    if root.is_symlink() or not root.is_dir():
        raise MedicationWorkflowError(f"Medikamentenordner fehlt oder ist ein Link: {root}")
    if not profile_id.strip():
        raise MedicationWorkflowError("Medikamentenanalyse benötigt eine Profil-ID.")
    try:
        inventory = inventory_files(root, recursive=recursive, policy=resource_policy)
    except (ResourceLimitExceeded, ValueError) as exc:
        raise MedicationWorkflowError(str(exc)) from exc
    paths = inventory.all_paths
    items = []
    text_budget = ResourceBudget(resource_policy)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            items.append(
                MedicationPlanAnalysisItem(
                    relative,
                    "skipped",
                    None,
                    "Symbolischer Link ausgelassen.",
                )
            )
            continue
        try:
            document = extractor.extract(path)
            text_budget.consume_extracted_text(len(document.text))
            schedule, status, message = _analyze_document(
                document,
                profile_id=profile_id,
                allow_sensitive_local_read=allow_sensitive_local_read,
            )
            items.append(MedicationPlanAnalysisItem(relative, status, schedule, message))
        except UnsupportedDocumentError as exc:
            items.append(MedicationPlanAnalysisItem(relative, "skipped", None, str(exc)))
        except DocServicesBridgeError as exc:
            items.append(MedicationPlanAnalysisItem(relative, "failed", None, str(exc)))
        except ResourceLimitExceeded as exc:
            raise MedicationWorkflowError(str(exc)) from exc
    return FolderMedicationPlanAnalysis(root, profile_id, tuple(items))


def build_medication_import_plan(
    analysis: FolderMedicationPlanAnalysis,
    *,
    store: MedicationStore,
) -> MedicationImportPlan:
    revision = store.revision()
    existing = store.list_schedules()
    existing_ids = {item.schedule_id for item in existing}
    existing_by_key_start = defaultdict(list)
    incoming_by_key_start = defaultdict(list)
    for schedule in existing:
        existing_by_key_start[(schedule.schedule_key, schedule.valid_from)].append(schedule)
    for schedule in analysis.schedules:
        incoming_by_key_start[(schedule.schedule_key, schedule.valid_from)].append(schedule)

    actions = []
    for schedule in sorted(analysis.schedules, key=lambda item: item.schedule_id):
        key = (schedule.schedule_key, schedule.valid_from)
        incoming = incoming_by_key_start[key]
        incoming_signatures = {_schedule_signature(item) for item in incoming}
        existing_signatures = {
            _schedule_signature(item) for item in existing_by_key_start.get(key, ())
        }
        same_signature_ids = sorted(
            item.schedule_id
            for item in incoming
            if _schedule_signature(item) == _schedule_signature(schedule)
        )
        if schedule.schedule_id in existing_ids:
            status = "noop"
            message = "Identischer Medikamentenplan ist bereits importiert."
        elif len(incoming_signatures) > 1:
            status = "blocked"
            message = "Medikamentenpläne mit gleichem Beginn und Zeitpunkt sind widersprüchlich."
        elif existing_signatures and _schedule_signature(schedule) not in existing_signatures:
            status = "blocked"
            message = "Medikamentenplan widerspricht einer vorhandenen Version mit gleichem Beginn."
        elif existing_signatures:
            status = "noop"
            message = "Gleicher Medikamentenplan ist für diesen Beginn bereits belegt."
        elif schedule.schedule_id != same_signature_ids[0]:
            status = "noop"
            message = "Gleicher Medikamentenplan ist im aktuellen Plan bereits enthalten."
        else:
            status = "planned"
            message = "Dokumentierten Zeitplan nach separater State-Freigabe ergänzen."
        material = {
            "revision": revision,
            "schedule_id": schedule.schedule_id,
            "status": status,
        }
        actions.append(
            MedicationImportAction(
                action_id=f"medication_action_{_json_hash(material)[:32]}",
                schedule=schedule,
                status=status,
                message=message,
            )
        )
    action_tuple = tuple(actions)
    payload = {
        "schema": MedicationImportPlan.SCHEMA,
        "medication_revision": revision,
        "analysis": analysis.to_dict(),
        "actions": [item.to_dict() for item in action_tuple],
    }
    return MedicationImportPlan(
        plan_id=f"medication_plan_{_json_hash(payload)}",
        medication_revision=revision,
        analysis=analysis,
        actions=action_tuple,
    )


def apply_medication_import_plan(
    plan: MedicationImportPlan,
    approval: MedicationImportApproval,
    *,
    store: MedicationStore,
    allow_state_write: bool,
) -> MedicationImportReport:
    if not allow_state_write:
        raise MedicationWorkflowError("Medikamentenimport benötigt eine State-Freigabe.")
    if approval.plan_id != plan.plan_id:
        raise MedicationWorkflowError("Medikamentenfreigabe gehört nicht zu diesem Plan.")
    if approval.medication_revision != plan.medication_revision:
        raise MedicationWorkflowError("Medikamentenfreigabe bindet eine andere Revision.")
    action_by_id = {item.action_id: item for item in plan.actions}
    try:
        selected = tuple(action_by_id[action_id] for action_id in approval.action_ids)
    except KeyError as exc:
        raise MedicationWorkflowError(
            f"Medikamentenfreigabe enthält eine unbekannte Aktion: {exc.args[0]}"
        ) from exc
    if any(item.status != "planned" for item in selected):
        raise MedicationWorkflowError("Nur geplante Medikamentenaktionen sind ausführbar.")
    try:
        store.validate_execution(
            expected_revision=plan.medication_revision,
            approval_id=approval.approval_id,
        )
    except MedicationStoreError as exc:
        raise MedicationWorkflowError(str(exc)) from exc
    for action in selected:
        _verify_source(action.schedule)
    try:
        schedule_ids, revision_after = store.apply_import(
            expected_revision=plan.medication_revision,
            actions=selected,
            approval=approval,
        )
    except MedicationStoreError as exc:
        raise MedicationWorkflowError(str(exc)) from exc
    payload = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "schedule_ids": list(schedule_ids),
        "revision_after": revision_after,
    }
    return MedicationImportReport(
        report_id=f"medication_report_{_json_hash(payload)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        revision_before=plan.medication_revision,
        revision_after=revision_after,
        created_schedule_ids=schedule_ids,
        state_path=store.path,
    )


def build_medication_day_report(
    *,
    store: MedicationStore,
    profile_id: str,
    on_date: str,
    as_of: str,
    inventory_store: InventoryStore | None = None,
) -> MedicationDayReport:
    target_date = date.fromisoformat(on_date)
    as_of_time = _aware_datetime(as_of)
    revision = store.revision()
    intake_by_dose = {
        item.dose_id: item for item in store.list_intake_events(profile_id=profile_id)
    }
    inventory_by_id = {}
    if inventory_store is not None:
        inventory_by_id = {
            item.item_id: item
            for item in inventory_store.current_items(profile_id=profile_id, as_of=on_date)
        }
    doses = []
    for schedule in store.current_schedules(profile_id=profile_id, on_date=on_date):
        if target_date.weekday() not in schedule.weekdays:
            continue
        dose_id = build_medication_dose_id(schedule.schedule_id, on_date)
        zone = ZoneInfo(schedule.timezone)
        scheduled_at = datetime.combine(
            target_date,
            time.fromisoformat(schedule.scheduled_time),
            tzinfo=zone,
        )
        confirmed = intake_by_dose.get(dose_id)
        if confirmed is not None:
            status = "confirmed"
            confirmed_at = confirmed.confirmed_at
        elif as_of_time < scheduled_at:
            status = "upcoming"
            confirmed_at = None
        else:
            status = "confirmation_pending"
            confirmed_at = None
        inventory_status = "not_checked"
        if inventory_store is not None:
            inventory = inventory_by_id.get(schedule.inventory_item_id)
            if inventory is None:
                inventory_status = "missing_evidence"
            elif inventory.quantity_milli >= schedule.dose_quantity_milli:
                inventory_status = "available_candidate"
            else:
                inventory_status = "insufficient_candidate"
        doses.append(
            MedicationDoseView(
                dose_id=dose_id,
                schedule_id=schedule.schedule_id,
                profile_id=profile_id,
                medication_name=schedule.medication_name,
                dose_quantity_milli=schedule.dose_quantity_milli,
                dose_unit=schedule.dose_unit,
                scheduled_date=on_date,
                scheduled_time=schedule.scheduled_time,
                timezone=schedule.timezone,
                scheduled_at=scheduled_at.isoformat(),
                status=status,
                confirmed_at=confirmed_at,
                inventory_item_id=schedule.inventory_item_id,
                inventory_status=inventory_status,
            )
        )
    return MedicationDayReport(
        profile_id=profile_id,
        on_date=on_date,
        as_of=as_of,
        medication_revision=revision,
        doses=tuple(sorted(doses, key=lambda item: (item.scheduled_at, item.dose_id))),
    )


def confirm_medication_intake(
    confirmation: MedicationIntakeConfirmation,
    *,
    store: MedicationStore,
    allow_state_write: bool,
) -> MedicationConfirmationReport:
    if not allow_state_write:
        raise MedicationWorkflowError("Einnahmebestätigung benötigt eine State-Freigabe.")
    revision_before = store.revision()
    if revision_before != confirmation.medication_revision:
        raise MedicationWorkflowError("Medikamenten-State wurde seit der Tagesansicht verändert.")
    schedule = store.get_schedule(confirmation.schedule_id)
    if schedule is None:
        raise MedicationWorkflowError("Einnahmebestätigung verweist auf unbekannten Zeitplan.")
    current_ids = {
        item.schedule_id
        for item in store.current_schedules(
            profile_id=schedule.profile_id,
            on_date=confirmation.scheduled_date,
        )
    }
    if schedule.schedule_id not in current_ids:
        raise MedicationWorkflowError("Zeitplan ist am bestätigten Tag nicht gültig.")
    target_date = date.fromisoformat(confirmation.scheduled_date)
    if target_date.weekday() not in schedule.weekdays:
        raise MedicationWorkflowError("Für diesen Wochentag ist keine Einnahme geplant.")
    expected_dose_id = build_medication_dose_id(
        schedule.schedule_id,
        confirmation.scheduled_date,
    )
    if confirmation.dose_id != expected_dose_id:
        raise MedicationWorkflowError("Dosis-ID passt nicht zu Zeitplan und Tag.")
    existing = store.find_intake_event(confirmation.dose_id)
    if existing is not None:
        payload = {
            "confirmation_id": confirmation.confirmation_id,
            "dose_id": confirmation.dose_id,
            "status": "noop",
            "revision": revision_before,
        }
        return MedicationConfirmationReport(
            report_id=f"medication_report_{_json_hash(payload)}",
            confirmation_id=confirmation.confirmation_id,
            dose_id=confirmation.dose_id,
            revision_before=revision_before,
            revision_after=revision_before,
            created_event_id=None,
            state_path=store.path,
            status="noop",
        )
    event_id = f"medication_intake_event_{_json_hash(confirmation.to_dict())}"
    try:
        created_event_id, revision_after = store.append_intake(
            confirmation=confirmation,
            schedule=schedule,
            event_id=event_id,
        )
    except MedicationStoreError as exc:
        raise MedicationWorkflowError(str(exc)) from exc
    payload = {
        "confirmation_id": confirmation.confirmation_id,
        "dose_id": confirmation.dose_id,
        "event_id": created_event_id,
        "revision_after": revision_after,
    }
    return MedicationConfirmationReport(
        report_id=f"medication_report_{_json_hash(payload)}",
        confirmation_id=confirmation.confirmation_id,
        dose_id=confirmation.dose_id,
        revision_before=revision_before,
        revision_after=revision_after,
        created_event_id=created_event_id,
        state_path=store.path,
        status="executed",
    )


def build_medication_dose_id(schedule_id: str, scheduled_date: str) -> str:
    date.fromisoformat(scheduled_date)
    return f"medication_dose_{_json_hash({'schedule_id': schedule_id, 'date': scheduled_date})}"


def _analyze_document(
    document: DocumentRecord,
    *,
    profile_id: str,
    allow_sensitive_local_read: bool,
) -> tuple[MedicationScheduleCandidate | None, str, str]:
    if document.privacy_status in {PrivacyStatus.BLOCKED, PrivacyStatus.NOT_CHECKED}:
        return None, "blocked", "Datenschutzstatus blockiert die Medikamentenanalyse."
    if (
        document.privacy_status is PrivacyStatus.REVIEW_REQUIRED
        and not allow_sensitive_local_read
    ):
        return None, "review_required", "Lokale sensible Medikamentenanalyse benötigt Freigabe."
    fields: dict[str, tuple[str, int, str]] = {}
    try:
        for line_number, line in enumerate(document.text.splitlines(), start=1):
            match = _LINE.fullmatch(line)
            if match is None:
                continue
            label, value = match.groups()
            field = _LABELS.get(label.strip().casefold())
            if field is None:
                continue
            if field in fields:
                raise ValueError(f"Feld {field} ist mehrfach vorhanden.")
            fields[field] = (value.strip(), line_number, label.strip())
        missing = sorted(_REQUIRED.difference(fields))
        if missing:
            raise ValueError(f"Pflichtfeld {missing[0]} fehlt.")
        medication_name = fields["medication_name"][0]
        dose_unit = fields["dose_unit"][0]
        scheduled_time = fields["scheduled_time"][0]
        if _TIME.fullmatch(scheduled_time) is None:
            raise ValueError("Zeitpunkt muss HH:MM im 24-Stunden-Format verwenden.")
        timezone = fields["timezone"][0]
        ZoneInfo(timezone)
        weekdays = _parse_weekdays(fields["weekdays"][0])
        valid_from = date.fromisoformat(fields["valid_from"][0]).isoformat()
        valid_to = (
            date.fromisoformat(fields["valid_to"][0]).isoformat()
            if "valid_to" in fields
            else None
        )
        dose_quantity_milli = _decimal_milli(fields["dose_quantity"][0])
        schedule_key_material = {
            "profile_id": _normalize(profile_id),
            "medication_name": _normalize(medication_name),
            "scheduled_time": scheduled_time,
            "timezone": timezone,
        }
        schedule_key = f"medication_schedule_key_{_json_hash(schedule_key_material)}"
        inventory_item_id = build_inventory_item_id(
            profile_id=profile_id,
            area=fields["inventory_area"][0],
            name=fields["inventory_name"][0],
            unit=fields["inventory_unit"][0],
        )
        schedule_material = {
            "schedule_key": schedule_key,
            "dose_quantity_milli": dose_quantity_milli,
            "dose_unit": dose_unit,
            "weekdays": weekdays,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "inventory_item_id": inventory_item_id,
            "source_document_id": document.document_id,
        }
        evidence = tuple(
            MedicationEvidence(field, value[1], value[2])
            for field, value in sorted(fields.items())
        )
        schedule = MedicationScheduleCandidate(
            schedule_id=f"medication_schedule_{_json_hash(schedule_material)}",
            schedule_key=schedule_key,
            profile_id=profile_id,
            medication_name=medication_name,
            dose_quantity_milli=dose_quantity_milli,
            dose_unit=dose_unit,
            scheduled_time=scheduled_time,
            timezone=timezone,
            weekdays=weekdays,
            valid_from=valid_from,
            valid_to=valid_to,
            inventory_item_id=inventory_item_id,
            source_document_id=document.document_id,
            source_sha256=document.source_sha256,
            source_path=document.source_path,
            evidence=evidence,
        )
        return schedule, "candidate", "Dokumentierter Einnahmezeitplan mit Zeilenevidenz erkannt."
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        return None, "review_required", str(exc)


def _parse_weekdays(value: str) -> tuple[int, ...]:
    normalized = _normalize(value)
    if normalized == "täglich":
        return tuple(range(7))
    if normalized in {"bei bedarf", "bedarf"}:
        raise ValueError("Bedarfseinnahmen werden in V1 nicht automatisch terminiert.")
    days = []
    for raw in value.split(","):
        day = _WEEKDAYS.get(_normalize(raw))
        if day is None:
            raise ValueError(f"Unbekannter Wochentag: {raw.strip()}")
        days.append(day)
    if len(set(days)) != len(days) or not days:
        raise ValueError("Wochentage müssen eindeutig und nichtleer sein.")
    return tuple(sorted(days))


def _decimal_milli(value: str) -> int:
    normalized = value.strip().replace(",", ".")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", normalized) is None:
        raise ValueError("Dosis muss eine positive Dezimalzahl sein.")
    fraction = normalized.partition(".")[2]
    if len(fraction) > 3:
        raise ValueError("Dosis darf höchstens drei Nachkommastellen haben.")
    result = int(Decimal(normalized) * 1000)
    if result <= 0:
        raise ValueError("Dosis muss größer als null sein.")
    return result


def _verify_source(schedule: MedicationScheduleCandidate) -> None:
    source = schedule.source_path
    if source.is_symlink() or not source.is_file():
        raise MedicationWorkflowError(
            f"Medikamentenquelle fehlt oder ist keine reguläre Datei: {source}"
        )
    digest = sha256()
    try:
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise MedicationWorkflowError(
            f"Medikamentenquelle ist nicht lesbar: {source}: {exc}"
        ) from exc
    if digest.hexdigest() != schedule.source_sha256:
        raise MedicationWorkflowError(f"Quellhash hat sich seit der Planung verändert: {source}")


def _schedule_signature(schedule: object) -> tuple[object, ...]:
    return (
        _normalize(schedule.medication_name),
        schedule.dose_quantity_milli,
        _normalize(schedule.dose_unit),
        schedule.scheduled_time,
        schedule.timezone,
        schedule.weekdays,
        schedule.valid_to,
        schedule.inventory_item_id,
    )


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MedicationWorkflowError("Auswertungszeitpunkt benötigt eine Zeitzone.")
    return parsed


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()
