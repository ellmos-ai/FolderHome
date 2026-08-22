"""Auditable, provider-aware document action-plan contracts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from folderhome.contracts.documents import DocumentRecord
from folderhome.contracts.profiles import RuleKey, RuleScope, RuleValue

if TYPE_CHECKING:
    from folderhome.contracts import GateDecision, SideEffect, UndoDescriptor

_PLAN_ID_PATTERN = re.compile(r"plan_[0-9a-f]{64}")


class PolicyActionKind(StrEnum):
    """Kinds of organizational action a resolved profile may request."""

    RENAME = "rename"
    SORT = "sort"
    CONVERT = "convert"
    HANDLE_ORIGINAL = "handle_original"
    ARCHIVE = "archive"
    RECYCLE = "recycle"
    REVIEW = "review"


class PolicyActionStatus(StrEnum):
    """Planning state; no value in this enum means that execution occurred."""

    PLANNED = "planned"
    BLOCKED = "blocked"
    REVIEW_REQUIRED = "review_required"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ActionRuleProvenance:
    """Resolved rule value and its complete winning/overridden provenance."""

    key: RuleKey
    value: RuleValue
    scope: RuleScope
    source_rule_ids: tuple[str, ...]
    overridden_rule_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key.value,
            "value": self.value,
            "scope": self.scope.value,
            "source_rule_ids": list(self.source_rule_ids),
            "overridden_rule_ids": list(self.overridden_rule_ids),
        }


@dataclass(frozen=True, slots=True)
class PolicyActionStep:
    """One deterministic action request with gate, undo, and rule evidence."""

    action_id: str
    sequence: int
    kind: PolicyActionKind
    document_id: str
    source_path: Path
    target_path: Path | None
    provider_id: str | None
    capability_id: str
    status: PolicyActionStatus
    side_effects: tuple[SideEffect, ...]
    gate: GateDecision
    undo: UndoDescriptor
    rules: tuple[ActionRuleProvenance, ...]
    message: str

    def __post_init__(self) -> None:
        if not self.action_id or self.sequence < 1:
            raise ValueError("Aktions-ID und positive Sequenz sind erforderlich.")
        if not self.capability_id or not self.message.strip():
            raise ValueError("Capability und Aktionshinweis dürfen nicht leer sein.")
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if self.target_path is not None:
            object.__setattr__(self, "target_path", self.target_path.resolve())
        if self.side_effects and (not self.gate.required or self.gate.granted):
            raise ValueError(
                "Dateiverändernde Planaktionen müssen ungefreigabegated bleiben."
            )
        if self.status is PolicyActionStatus.PLANNED and self.provider_id is None:
            raise ValueError("Ausführbare Planaktionen benötigen einen Provider.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "sequence": self.sequence,
            "kind": self.kind.value,
            "document_id": self.document_id,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path) if self.target_path else None,
            "provider_id": self.provider_id,
            "capability_id": self.capability_id,
            "status": self.status.value,
            "side_effects": [effect.value for effect in self.side_effects],
            "gate": self.gate.to_dict(),
            "undo": self.undo.to_dict(),
            "rules": [rule.to_dict() for rule in self.rules],
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class DocumentPolicyActionPlan:
    """Read-only result of applying one resolved profile policy to one document."""

    plan_id: str
    profile_id: str
    area: str
    as_of: str
    target_root: Path
    document: DocumentRecord
    steps: tuple[PolicyActionStep, ...]

    SCHEMA = "folderhome.document-policy-action-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID_PATTERN.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss plan_<sha256> verwenden.")
        if not self.profile_id or not self.area or not self.as_of:
            raise ValueError("Profil, Bereich und Stichtag sind erforderlich.")
        object.__setattr__(self, "target_root", self.target_root.resolve())
        expected = tuple(range(1, len(self.steps) + 1))
        if tuple(step.sequence for step in self.steps) != expected:
            raise ValueError("Aktionsschritte müssen lückenlos ab 1 sequenziert sein.")
        if any(step.document_id != self.document.document_id for step in self.steps):
            raise ValueError("Alle Aktionsschritte müssen zum Plandokument gehören.")
        expected_id = compute_document_policy_plan_id(
            profile_id=self.profile_id,
            area=self.area,
            as_of=self.as_of,
            target_root=self.target_root,
            document=self.document,
            steps=self.steps,
        )
        if self.plan_id != expected_id:
            raise ValueError("plan_id stimmt nicht mit dem vollständigen Plan überein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "as_of": self.as_of,
            "target_root": str(self.target_root),
            "document": self.document.to_dict(include_text=False),
            "steps": [step.to_dict() for step in self.steps],
        }


def compute_document_policy_plan_id(
    *,
    profile_id: str,
    area: str,
    as_of: str,
    target_root: Path,
    document: DocumentRecord,
    steps: tuple[PolicyActionStep, ...],
) -> str:
    """Bind approval identity to every serialized, content-free plan field."""

    payload = {
        "schema": DocumentPolicyActionPlan.SCHEMA,
        "profile_id": profile_id,
        "area": area,
        "as_of": as_of,
        "target_root": str(target_root.resolve()),
        "document": document.to_dict(include_text=False),
        "steps": [step.to_dict() for step in steps],
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"plan_{sha256(material).hexdigest()}"
