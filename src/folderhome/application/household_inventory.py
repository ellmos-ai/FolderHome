"""Analyze household inventory documents and append approved observations."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.inventory_store import InventoryStore, InventoryStoreError
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    DocumentRecord,
    FolderInventoryAnalysis,
    InventoryAnalysisItem,
    InventoryEvidence,
    InventoryImportAction,
    InventoryImportApproval,
    InventoryImportPlan,
    InventoryImportReport,
    InventoryNeedCandidate,
    InventoryNeedsReport,
    InventoryObservationCandidate,
    PrivacyStatus,
    build_inventory_item_id,
)

_LINE = re.compile(r"^\s*([^:]{1,48}):\s*(\S(?:.*\S)?)\s*$")
_LABELS = {
    "gegenstand": "name",
    "bereich": "area",
    "ort": "location",
    "einheit": "unit",
    "menge": "quantity",
    "mindestbestand": "minimum_quantity",
    "erfasst-am": "observed_on",
    "ablaufdatum": "expiry_date",
}
_REQUIRED_FIELDS = {
    "name",
    "area",
    "location",
    "unit",
    "quantity",
    "minimum_quantity",
    "observed_on",
}


class InventoryWorkflowError(RuntimeError):
    """Raised when inventory evidence or execution state is unsafe."""


class InventoryDocumentExtractor(Protocol):
    def extract(self, source_path: Path) -> DocumentRecord: ...


def analyze_folder_inventory(
    source_dir: Path,
    *,
    profile_id: str,
    extractor: InventoryDocumentExtractor,
    recursive: bool = True,
    allow_sensitive_local_read: bool = False,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderInventoryAnalysis:
    """Analyze visible inventory files without writing inventory state."""

    root = source_dir.resolve()
    if root.is_symlink() or not root.is_dir():
        raise InventoryWorkflowError(f"Bestandsordner fehlt oder ist ein Link: {root}")
    if not profile_id.strip():
        raise InventoryWorkflowError("Inventaranalyse benötigt eine Profil-ID.")
    try:
        inventory = inventory_files(root, recursive=recursive, policy=resource_policy)
    except (ResourceLimitExceeded, ValueError) as exc:
        raise InventoryWorkflowError(str(exc)) from exc
    paths = inventory.all_paths
    items = []
    text_budget = ResourceBudget(resource_policy)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            items.append(
                InventoryAnalysisItem(
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
            observation, status, message = _analyze_document(
                document,
                profile_id=profile_id,
                allow_sensitive_local_read=allow_sensitive_local_read,
            )
            items.append(InventoryAnalysisItem(relative, status, observation, message))
        except UnsupportedDocumentError as exc:
            items.append(InventoryAnalysisItem(relative, "skipped", None, str(exc)))
        except DocServicesBridgeError as exc:
            items.append(InventoryAnalysisItem(relative, "failed", None, str(exc)))
        except ResourceLimitExceeded as exc:
            raise InventoryWorkflowError(str(exc)) from exc
    return FolderInventoryAnalysis(root, profile_id, tuple(items))


def build_inventory_import_plan(
    analysis: FolderInventoryAnalysis,
    *,
    store: InventoryStore,
) -> InventoryImportPlan:
    """Plan append-only observations against the current inventory revision."""

    revision = store.revision()
    existing = store.list_events()
    existing_ids = {item.event_id for item in existing}
    existing_by_item_date = defaultdict(list)
    for event in existing:
        existing_by_item_date[(event.item_id, event.observed_on)].append(event)
    incoming_by_item_date = defaultdict(list)
    for observation in analysis.observations:
        incoming_by_item_date[(observation.item_id, observation.observed_on)].append(
            observation
        )

    actions = []
    for observation in sorted(analysis.observations, key=lambda item: item.event_id):
        key = (observation.item_id, observation.observed_on)
        incoming = incoming_by_item_date[key]
        incoming_signatures = {_observation_signature(item) for item in incoming}
        existing_signatures = {
            _event_signature(item) for item in existing_by_item_date.get(key, ())
        }
        same_signature_ids = sorted(
            item.event_id
            for item in incoming
            if _observation_signature(item) == _observation_signature(observation)
        )
        if observation.event_id in existing_ids:
            status = "noop"
            message = "Identische Bestandsbeobachtung ist bereits importiert."
        elif len(incoming_signatures) > 1:
            status = "blocked"
            message = "Gleichzeitig erfasste Bestandsbeobachtungen sind widersprüchlich."
        elif existing_signatures and _observation_signature(observation) not in existing_signatures:
            status = "blocked"
            message = "Bestandsbeobachtung widerspricht einem vorhandenen Ereignis desselben Tages."
        elif existing_signatures:
            status = "noop"
            message = "Gleicher Bestandszustand ist für diesen Tag bereits belegt."
        elif observation.event_id != same_signature_ids[0]:
            status = "noop"
            message = "Gleicher Bestandszustand ist im aktuellen Plan bereits enthalten."
        else:
            status = "planned"
            message = "Bestandsbeobachtung nach separater State-Freigabe ergänzen."
        material = {
            "revision": revision,
            "event_id": observation.event_id,
            "status": status,
        }
        actions.append(
            InventoryImportAction(
                action_id=f"inventory_action_{_json_hash(material)[:32]}",
                observation=observation,
                status=status,
                message=message,
            )
        )
    action_tuple = tuple(actions)
    payload = {
        "schema": InventoryImportPlan.SCHEMA,
        "inventory_revision": revision,
        "analysis": analysis.to_dict(),
        "actions": [action.to_dict() for action in action_tuple],
    }
    return InventoryImportPlan(
        plan_id=f"inventory_plan_{_json_hash(payload)}",
        inventory_revision=revision,
        analysis=analysis,
        actions=action_tuple,
    )


def apply_inventory_import_plan(
    plan: InventoryImportPlan,
    approval: InventoryImportApproval,
    *,
    store: InventoryStore,
    allow_state_write: bool,
) -> InventoryImportReport:
    """Recheck source and revision, then atomically append selected events."""

    if not allow_state_write:
        raise InventoryWorkflowError("Inventarimport benötigt eine State-Freigabe.")
    if approval.plan_id != plan.plan_id:
        raise InventoryWorkflowError("Inventarfreigabe gehört nicht zu diesem Plan.")
    if approval.inventory_revision != plan.inventory_revision:
        raise InventoryWorkflowError("Inventarfreigabe bindet eine andere Revision.")
    action_by_id = {action.action_id: action for action in plan.actions}
    try:
        selected = tuple(action_by_id[action_id] for action_id in approval.action_ids)
    except KeyError as exc:
        raise InventoryWorkflowError(
            f"Inventarfreigabe enthält eine unbekannte Aktion: {exc.args[0]}"
        ) from exc
    if any(action.status != "planned" for action in selected):
        raise InventoryWorkflowError("Nur geplante Inventaraktionen dürfen ausgeführt werden.")
    try:
        store.validate_execution(
            expected_revision=plan.inventory_revision,
            approval_id=approval.approval_id,
        )
    except InventoryStoreError as exc:
        raise InventoryWorkflowError(str(exc)) from exc
    for action in selected:
        _verify_source(action.observation)
    try:
        event_ids, revision_after = store.apply(
            expected_revision=plan.inventory_revision,
            actions=selected,
            approval=approval,
        )
    except InventoryStoreError as exc:
        raise InventoryWorkflowError(str(exc)) from exc
    payload = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "event_ids": list(event_ids),
        "revision_after": revision_after,
    }
    return InventoryImportReport(
        report_id=f"inventory_report_{_json_hash(payload)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        revision_before=plan.inventory_revision,
        revision_after=revision_after,
        created_event_ids=event_ids,
        state_path=store.path,
    )


def build_inventory_needs_report(
    *,
    store: InventoryStore,
    profile_id: str,
    as_of: str,
    expiry_horizon_days: int = 30,
) -> InventoryNeedsReport:
    """Build review-only minimum-stock and expiry candidates."""

    as_of_date = date.fromisoformat(as_of)
    if expiry_horizon_days < 0:
        raise InventoryWorkflowError("Ablaufhorizont darf nicht negativ sein.")
    candidates = []
    for event in store.current_items(profile_id=profile_id, as_of=as_of):
        reasons = []
        shortfall = max(0, event.minimum_quantity_milli - event.quantity_milli)
        if shortfall:
            reasons.append("below_minimum")
        if event.expiry_date is not None:
            expiry = date.fromisoformat(event.expiry_date)
            if expiry < as_of_date:
                reasons.append("expired")
            elif expiry <= as_of_date + timedelta(days=expiry_horizon_days):
                reasons.append("expires_soon")
        if not reasons:
            continue
        material = {
            "event_id": event.event_id,
            "as_of": as_of,
            "reasons": reasons,
        }
        candidates.append(
            InventoryNeedCandidate(
                candidate_id=f"inventory_need_{_json_hash(material)}",
                item_id=event.item_id,
                event_id=event.event_id,
                profile_id=event.profile_id,
                area=event.area,
                name=event.name,
                unit=event.unit,
                location=event.location,
                quantity_milli=event.quantity_milli,
                minimum_quantity_milli=event.minimum_quantity_milli,
                shortfall_quantity_milli=shortfall,
                expiry_date=event.expiry_date,
                reasons=tuple(reasons),
            )
        )
    return InventoryNeedsReport(
        profile_id=profile_id,
        as_of=as_of,
        expiry_horizon_days=expiry_horizon_days,
        candidates=tuple(sorted(candidates, key=lambda item: item.candidate_id)),
    )


def _analyze_document(
    document: DocumentRecord,
    *,
    profile_id: str,
    allow_sensitive_local_read: bool,
) -> tuple[InventoryObservationCandidate | None, str, str]:
    if document.privacy_status in {PrivacyStatus.BLOCKED, PrivacyStatus.NOT_CHECKED}:
        return None, "blocked", "Datenschutzstatus blockiert die Inventaranalyse."
    if (
        document.privacy_status is PrivacyStatus.REVIEW_REQUIRED
        and not allow_sensitive_local_read
    ):
        return None, "review_required", "Lokale sensible Inventaranalyse benötigt Freigabe."
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
        missing = sorted(_REQUIRED_FIELDS.difference(fields))
        if missing:
            raise ValueError(f"Pflichtfeld {missing[0]} fehlt.")
        name = fields["name"][0]
        area = fields["area"][0]
        location = fields["location"][0]
        unit = fields["unit"][0]
        observed_on = date.fromisoformat(fields["observed_on"][0]).isoformat()
        expiry_date = (
            date.fromisoformat(fields["expiry_date"][0]).isoformat()
            if "expiry_date" in fields
            else None
        )
        quantity_milli = _decimal_milli(fields["quantity"][0])
        minimum_milli = _decimal_milli(fields["minimum_quantity"][0])
        item_id = build_inventory_item_id(
            profile_id=profile_id,
            area=area,
            name=name,
            unit=unit,
        )
        event_material = {
            "item_id": item_id,
            "observed_on": observed_on,
            "quantity_milli": quantity_milli,
            "minimum_quantity_milli": minimum_milli,
            "location": location,
            "expiry_date": expiry_date,
            "source_document_id": document.document_id,
        }
        evidence = tuple(
            InventoryEvidence(field, value[1], value[2])
            for field, value in sorted(fields.items())
        )
        observation = InventoryObservationCandidate(
            event_id=f"inventory_event_{_json_hash(event_material)}",
            item_id=item_id,
            profile_id=profile_id,
            area=area,
            name=name,
            unit=unit,
            location=location,
            quantity_milli=quantity_milli,
            minimum_quantity_milli=minimum_milli,
            observed_on=observed_on,
            expiry_date=expiry_date,
            source_document_id=document.document_id,
            source_sha256=document.source_sha256,
            source_path=document.source_path,
            evidence=evidence,
        )
        return observation, "candidate", "Exakte Bestandsbeobachtung mit Zeilenevidenz erkannt."
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        return None, "review_required", str(exc)


def _decimal_milli(value: str) -> int:
    normalized = value.strip().replace(",", ".")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", normalized) is None:
        raise ValueError("Bestandsmengen müssen nichtnegative Dezimalzahlen sein.")
    fraction = normalized.partition(".")[2]
    if len(fraction) > 3:
        raise ValueError("Bestandsmengen dürfen höchstens drei Nachkommastellen haben.")
    quantity = Decimal(normalized) * 1000
    return int(quantity)


def _verify_source(observation: InventoryObservationCandidate) -> None:
    source = observation.source_path
    if source.is_symlink() or not source.is_file():
        raise InventoryWorkflowError(
            f"Inventarquelle fehlt oder ist keine reguläre Datei: {source}"
        )
    digest = sha256()
    try:
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise InventoryWorkflowError(f"Inventarquelle ist nicht lesbar: {source}: {exc}") from exc
    if digest.hexdigest() != observation.source_sha256:
        raise InventoryWorkflowError(f"Quellhash hat sich seit der Planung verändert: {source}")


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _observation_signature(observation: InventoryObservationCandidate) -> tuple[object, ...]:
    return (
        _normalize(observation.area),
        _normalize(observation.name),
        _normalize(observation.unit),
        _normalize(observation.location),
        observation.quantity_milli,
        observation.minimum_quantity_milli,
        observation.expiry_date,
    )


def _event_signature(event: object) -> tuple[object, ...]:
    return (
        _normalize(event.area),
        _normalize(event.name),
        _normalize(event.unit),
        _normalize(event.location),
        event.quantity_milli,
        event.minimum_quantity_milli,
        event.expiry_date,
    )


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()
