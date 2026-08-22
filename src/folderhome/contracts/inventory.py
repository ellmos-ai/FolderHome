"""Contracts for evidenced household inventory observations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path

_ACTION_ID = re.compile(r"inventory_action_[0-9a-f]{32}")
_APPROVAL_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_DOCUMENT_ID = re.compile(r"doc_[0-9a-f]{64}")
_EVENT_ID = re.compile(r"inventory_event_[0-9a-f]{64}")
_ITEM_ID = re.compile(r"inventory_item_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"inventory_plan_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"inventory_report_[0-9a-f]{64}")
_REVISION = re.compile(r"inventory_revision_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class InventoryEvidence:
    """Exact labeled source line supporting one inventory field."""

    field: str
    line_number: int
    label: str

    def __post_init__(self) -> None:
        if not self.field or self.line_number < 1 or not self.label:
            raise ValueError("Inventarevidenz benötigt Feld, Zeilennummer und Label.")

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "line_number": self.line_number,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class InventoryObservationCandidate:
    """One exact stock observation bound to an immutable source document."""

    event_id: str
    item_id: str
    profile_id: str
    area: str
    name: str
    unit: str
    location: str
    quantity_milli: int
    minimum_quantity_milli: int
    observed_on: str
    expiry_date: str | None
    source_document_id: str
    source_sha256: str
    source_path: Path
    evidence: tuple[InventoryEvidence, ...]

    SCHEMA = "folderhome.inventory-observation-candidate.v1"

    def __post_init__(self) -> None:
        if _EVENT_ID.fullmatch(self.event_id) is None:
            raise ValueError("event_id muss inventory_event_<sha256> verwenden.")
        if _ITEM_ID.fullmatch(self.item_id) is None:
            raise ValueError("item_id muss inventory_item_<sha256> verwenden.")
        if _DOCUMENT_ID.fullmatch(self.source_document_id) is None:
            raise ValueError("source_document_id ist ungültig.")
        if _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("source_sha256 ist ungültig.")
        if not all((self.profile_id, self.area, self.name, self.unit, self.location)):
            raise ValueError("Inventarbeobachtung benötigt Profil, Bereich, Name, Einheit und Ort.")
        if self.quantity_milli < 0 or self.minimum_quantity_milli < 0:
            raise ValueError("Bestandsmengen dürfen nicht negativ sein.")
        date.fromisoformat(self.observed_on)
        if self.expiry_date is not None:
            date.fromisoformat(self.expiry_date)
        if not self.evidence:
            raise ValueError("Inventarbeobachtung benötigt Zeilenevidenz.")
        object.__setattr__(self, "source_path", self.source_path.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "event_id": self.event_id,
            "item_id": self.item_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "name": self.name,
            "unit": self.unit,
            "location": self.location,
            "quantity": _format_milli(self.quantity_milli),
            "quantity_milli": self.quantity_milli,
            "minimum_quantity": _format_milli(self.minimum_quantity_milli),
            "minimum_quantity_milli": self.minimum_quantity_milli,
            "observed_on": self.observed_on,
            "expiry_date": self.expiry_date,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": str(self.source_path),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class InventoryAnalysisItem:
    """One visible source-file outcome in an inventory analysis."""

    relative_path: str
    status: str
    observation: InventoryObservationCandidate | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "status": self.status,
            "observation": self.observation.to_dict() if self.observation else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class FolderInventoryAnalysis:
    """Read-only inventory observations for an explicit local folder."""

    source_root: Path
    profile_id: str
    items: tuple[InventoryAnalysisItem, ...]

    SCHEMA = "folderhome.folder-inventory-analysis.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_root", self.source_root.resolve())

    @property
    def observations(self) -> tuple[InventoryObservationCandidate, ...]:
        return tuple(item.observation for item in self.items if item.observation is not None)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "source_root": str(self.source_root),
            "profile_id": self.profile_id,
            "observation_count": len(self.observations),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class InventoryImportAction:
    """One append-only inventory import decision."""

    action_id: str
    observation: InventoryObservationCandidate
    status: str
    message: str

    def __post_init__(self) -> None:
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("action_id muss inventory_action_<hex> verwenden.")
        if self.status not in {"planned", "noop", "blocked"}:
            raise ValueError("Inventaraktionsstatus ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "observation": self.observation.to_dict(),
            "status": self.status,
            "message": self.message,
            "side_effect": "local_inventory_state" if self.status == "planned" else "none",
        }


@dataclass(frozen=True, slots=True)
class InventoryImportPlan:
    """Revision-bound inventory plan with no write side effect."""

    plan_id: str
    inventory_revision: str
    analysis: FolderInventoryAnalysis
    actions: tuple[InventoryImportAction, ...]

    SCHEMA = "folderhome.inventory-import-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss inventory_plan_<sha256> verwenden.")
        if _REVISION.fullmatch(self.inventory_revision) is None:
            raise ValueError("inventory_revision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "inventory_revision": self.inventory_revision,
            "analysis": self.analysis.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "automatic_purchase": False,
        }


@dataclass(frozen=True, slots=True)
class InventoryImportApproval:
    """Exact user approval for selected inventory actions."""

    approval_id: str
    plan_id: str
    inventory_revision: str
    action_ids: tuple[str, ...]
    approved_at: str

    SCHEMA = "folderhome.inventory-import-approval.v1"

    def __post_init__(self) -> None:
        if _APPROVAL_ID.fullmatch(self.approval_id) is None:
            raise ValueError("approval_id ist ungültig.")
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id ist ungültig.")
        if _REVISION.fullmatch(self.inventory_revision) is None:
            raise ValueError("inventory_revision ist ungültig.")
        if len(set(self.action_ids)) != len(self.action_ids):
            raise ValueError("Inventarfreigabe enthält doppelte Aktionen.")
        if any(_ACTION_ID.fullmatch(item) is None for item in self.action_ids):
            raise ValueError("Inventarfreigabe enthält eine ungültige Aktion.")
        timestamp = datetime.fromisoformat(self.approved_at)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("approved_at benötigt eine Zeitzone.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "inventory_revision": self.inventory_revision,
            "action_ids": list(self.action_ids),
            "approved_at": self.approved_at,
        }


@dataclass(frozen=True, slots=True)
class InventoryEventRecord:
    """One stored immutable inventory observation."""

    event_id: str
    item_id: str
    profile_id: str
    area: str
    name: str
    unit: str
    location: str
    quantity_milli: int
    minimum_quantity_milli: int
    observed_on: str
    expiry_date: str | None
    source_document_id: str
    source_sha256: str
    source_path: str
    evidence: tuple[InventoryEvidence, ...]
    recorded_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "item_id": self.item_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "name": self.name,
            "unit": self.unit,
            "location": self.location,
            "quantity": _format_milli(self.quantity_milli),
            "quantity_milli": self.quantity_milli,
            "minimum_quantity": _format_milli(self.minimum_quantity_milli),
            "minimum_quantity_milli": self.minimum_quantity_milli,
            "observed_on": self.observed_on,
            "expiry_date": self.expiry_date,
            "source_document_id": self.source_document_id,
            "source_sha256": self.source_sha256,
            "source_path": self.source_path,
            "evidence": [item.to_dict() for item in self.evidence],
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True)
class InventoryImportReport:
    """Auditable result of an approved inventory append."""

    report_id: str
    plan_id: str
    approval_id: str
    revision_before: str
    revision_after: str
    created_event_ids: tuple[str, ...]
    state_path: Path
    status: str = "executed"

    SCHEMA = "folderhome.inventory-import-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("report_id muss inventory_report_<sha256> verwenden.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "status": self.status,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "revision_before": self.revision_before,
            "revision_after": self.revision_after,
            "created_event_ids": list(self.created_event_ids),
            "state_path": str(self.state_path),
        }


@dataclass(frozen=True, slots=True)
class InventoryNeedCandidate:
    """Review-only restock or expiry candidate derived from current evidence."""

    candidate_id: str
    item_id: str
    event_id: str
    profile_id: str
    area: str
    name: str
    unit: str
    location: str
    quantity_milli: int
    minimum_quantity_milli: int
    shortfall_quantity_milli: int
    expiry_date: str | None
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "item_id": self.item_id,
            "event_id": self.event_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "name": self.name,
            "unit": self.unit,
            "location": self.location,
            "quantity": _format_milli(self.quantity_milli),
            "quantity_milli": self.quantity_milli,
            "minimum_quantity": _format_milli(self.minimum_quantity_milli),
            "minimum_quantity_milli": self.minimum_quantity_milli,
            "shortfall_quantity": _format_milli(self.shortfall_quantity_milli),
            "shortfall_quantity_milli": self.shortfall_quantity_milli,
            "expiry_date": self.expiry_date,
            "reasons": list(self.reasons),
            "status": "review_candidate",
        }


@dataclass(frozen=True, slots=True)
class InventoryNeedsReport:
    """Profile-scoped inventory needs at an explicit date."""

    profile_id: str
    as_of: str
    expiry_horizon_days: int
    candidates: tuple[InventoryNeedCandidate, ...]
    automatic_purchase: bool = False

    SCHEMA = "folderhome.inventory-needs-report.v1"

    def __post_init__(self) -> None:
        date.fromisoformat(self.as_of)
        if self.expiry_horizon_days < 0:
            raise ValueError("Ablaufhorizont darf nicht negativ sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "profile_id": self.profile_id,
            "as_of": self.as_of,
            "expiry_horizon_days": self.expiry_horizon_days,
            "candidates": [item.to_dict() for item in self.candidates],
            "automatic_purchase": self.automatic_purchase,
            "complete_inventory_claimed": False,
        }


def _format_milli(value: int) -> str:
    whole, remainder = divmod(value, 1000)
    if remainder == 0:
        return str(whole)
    return f"{whole}.{remainder:03d}".rstrip("0")


def build_inventory_item_id(
    *,
    profile_id: str,
    area: str,
    name: str,
    unit: str,
) -> str:
    """Build the stable cross-capability identity for one household item."""

    payload = {
        "profile_id": _normalize(profile_id),
        "area": _normalize(area),
        "name": _normalize(name),
        "unit": _normalize(unit),
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"inventory_item_{sha256(material).hexdigest()}"


def _normalize(value: str) -> str:
    if not value.strip():
        raise ValueError("Inventaridentität benötigt nichtleere Felder.")
    return " ".join(value.casefold().split())
