"""Contracts for typed master-agent handoff to existing domain executors."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass

_ID = re.compile(r"[a-z][a-z0-9_.\-]{2,127}")
_ENVELOPE_ID = re.compile(r"workflow_envelope_[0-9a-f]{64}")
_EXECUTION_ID = re.compile(r"workflow_execution_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_STATUSES = {"connected", "direct_read_only", "planning_only", "not_connected"}


@dataclass(frozen=True, slots=True)
class WorkflowAdapterDescriptor:
    """Truthful runtime coverage for one FolderHome workflow."""

    workflow_id: str
    adapter_id: str | None
    status: str
    plan_schema: str | None
    report_schema: str | None
    side_effects: tuple[str, ...]
    reason: str
    request_schema: dict[str, object] | None = None

    SCHEMA = "folderhome.workflow-adapter-descriptor.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.workflow_id) is None:
            raise ValueError("workflow_id ist ungültig.")
        if self.adapter_id is not None and _ID.fullmatch(self.adapter_id) is None:
            raise ValueError("adapter_id ist ungültig.")
        if self.status not in _STATUSES:
            raise ValueError("Unbekannter Adapterstatus.")
        if self.status == "connected" and (
            self.adapter_id is None
            or self.plan_schema is None
            or self.report_schema is None
            or self.request_schema is None
        ):
            raise ValueError(
                "Verbundener Adapter benötigt ID sowie Anfrage-, Plan- und Berichtsschema."
            )
        if self.status != "connected" and self.adapter_id is not None:
            raise ValueError("Nicht verbundene Workflows dürfen keinen Adapter behaupten.")
        if self.status != "connected" and self.request_schema is not None:
            raise ValueError("Nicht verbundene Workflows dürfen kein Anfrageschema behaupten.")
        if self.request_schema is not None and (
            self.request_schema.get("type") != "object"
            or self.request_schema.get("additionalProperties") is not False
            or not isinstance(self.request_schema.get("properties"), dict)
            or not isinstance(self.request_schema.get("required"), list)
        ):
            raise ValueError("Adapter-Anfrageschema muss ein geschlossenes JSON-Objekt sein.")
        if not self.reason.strip():
            raise ValueError("Adapterstatus benötigt eine Begründung.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "workflow_id": self.workflow_id,
            "adapter_id": self.adapter_id,
            "status": self.status,
            "plan_schema": self.plan_schema,
            "report_schema": self.report_schema,
            "side_effects": list(self.side_effects),
            "reason": self.reason,
            "request_schema": deepcopy(self.request_schema),
        }


@dataclass(frozen=True, slots=True)
class WorkflowExecutionEnvelope:
    """Public, hash-bound domain plan attached to one master-plan step."""

    envelope_id: str
    workflow_id: str
    adapter_id: str
    domain_plan_id: str
    domain_plan_schema: str
    domain_plan_sha256: str
    domain_plan: dict[str, object]
    approval_kind: str
    side_effects: tuple[str, ...]
    status: str = "prepared"

    SCHEMA = "folderhome.workflow-execution-envelope.v1"

    def __post_init__(self) -> None:
        if _ENVELOPE_ID.fullmatch(self.envelope_id) is None:
            raise ValueError("envelope_id muss workflow_envelope_<sha256> verwenden.")
        for value, label in (
            (self.workflow_id, "workflow_id"),
            (self.adapter_id, "adapter_id"),
            (self.domain_plan_id, "domain_plan_id"),
            (self.domain_plan_schema, "domain_plan_schema"),
            (self.approval_kind, "approval_kind"),
        ):
            if not value.strip() or any(char in value for char in "\r\n"):
                raise ValueError(f"{label} ist ungültig.")
        if _SHA256.fullmatch(self.domain_plan_sha256) is None:
            raise ValueError("domain_plan_sha256 muss ein SHA-256 sein.")
        if self.domain_plan.get("schema") != self.domain_plan_schema:
            raise ValueError("Domainplan und angegebenes Schema stimmen nicht überein.")
        if self.status != "prepared":
            raise ValueError("Neue Ausführungshülle muss prepared sein.")
        if not self.side_effects:
            raise ValueError("Ausführungshülle benötigt sichtbare Side Effects.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "envelope_id": self.envelope_id,
            "workflow_id": self.workflow_id,
            "adapter_id": self.adapter_id,
            "domain_plan_id": self.domain_plan_id,
            "domain_plan_schema": self.domain_plan_schema,
            "domain_plan_sha256": self.domain_plan_sha256,
            "domain_plan": dict(self.domain_plan),
            "approval_kind": self.approval_kind,
            "side_effects": list(self.side_effects),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class WorkflowExecutionReport:
    """Wrapper around an authoritative existing domain execution report."""

    execution_id: str
    envelope_id: str
    workflow_id: str
    adapter_id: str
    domain_report_schema: str
    domain_report: dict[str, object]
    side_effects: tuple[str, ...]
    status: str = "executed"
    execution_performed: bool = True

    SCHEMA = "folderhome.workflow-execution-report.v1"

    def __post_init__(self) -> None:
        if _EXECUTION_ID.fullmatch(self.execution_id) is None:
            raise ValueError("execution_id muss workflow_execution_<sha256> verwenden.")
        if _ENVELOPE_ID.fullmatch(self.envelope_id) is None:
            raise ValueError("Ausführungsbericht besitzt eine ungültige envelope_id.")
        if self.status != "executed" or not self.execution_performed:
            raise ValueError("Ausführungsbericht muss eine echte Ausführung belegen.")
        if self.domain_report.get("schema") != self.domain_report_schema:
            raise ValueError("Domainbericht und Schema stimmen nicht überein.")
        if not self.side_effects:
            raise ValueError("Ausführungsbericht benötigt sichtbare Side Effects.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "execution_id": self.execution_id,
            "envelope_id": self.envelope_id,
            "workflow_id": self.workflow_id,
            "adapter_id": self.adapter_id,
            "domain_report_schema": self.domain_report_schema,
            "domain_report": dict(self.domain_report),
            "side_effects": list(self.side_effects),
            "status": self.status,
            "execution_performed": self.execution_performed,
        }
