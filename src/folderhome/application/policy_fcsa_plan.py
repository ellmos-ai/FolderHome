"""Confirm supported document-policy actions through pinned FCSA dry-runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from folderhome.bridges.fcsa import FcsaDryRunResult
from folderhome.contracts import (
    DocumentPolicyActionPlan,
    PolicyActionStatus,
    PolicyActionStep,
)


class PolicyFcsaValidationError(RuntimeError):
    """Raised when FCSA cannot confirm an otherwise executable policy step."""


class FcsaPolicyPlanner(Protocol):
    """Dry-run port implemented by the exact-pinned FCSA bridge."""

    def plan(self, config_dir: Path) -> FcsaDryRunResult: ...


@dataclass(frozen=True, slots=True)
class FcsaPolicyActionValidation:
    """Provider confirmation for one still-ungranted policy action."""

    action_id: str
    provider_id: str
    source_path: Path
    target_directory: Path | None
    planned_actions: tuple[str, ...]
    settings_fingerprint: str
    would_mutate_fs: bool
    gate_granted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.fcsa-policy-action-validation.v1",
            "action_id": self.action_id,
            "provider_id": self.provider_id,
            "source_path": str(self.source_path),
            "target_directory": (
                str(self.target_directory) if self.target_directory else None
            ),
            "planned_actions": list(self.planned_actions),
            "settings_fingerprint": self.settings_fingerprint,
            "would_mutate_fs": self.would_mutate_fs,
            "gate": {"required": True, "granted": self.gate_granted},
        }


def validate_fcsa_policy_actions(
    plan: DocumentPolicyActionPlan,
    *,
    bridge: FcsaPolicyPlanner,
) -> tuple[FcsaPolicyActionValidation, ...]:
    """Confirm planned FCSA steps while preserving source and target state."""

    candidates = tuple(
        step
        for step in plan.steps
        if step.provider_id == "file-collect-sort-action"
        and step.status is PolicyActionStatus.PLANNED
    )
    validations = []
    for step in candidates:
        source = step.source_path.resolve()
        if step.gate.granted:
            raise PolicyFcsaValidationError(
                f"Bereits freigegebene Aktion darf nicht dry-run-validiert werden: {step.action_id}"
            )
        if not source.is_file():
            raise PolicyFcsaValidationError(
                f"FCSA-Quelle fehlt oder ist nur projiziert: {source}"
            )
        expected_actions = _expected_actions(step)
        before_hash = _sha256_file(source)
        with TemporaryDirectory(prefix="folderhome-policy-fcsa-") as temporary:
            temporary_root = Path(temporary)
            config_dir = temporary_root / "config"
            config_dir.mkdir()
            _write_config(
                step,
                config_dir=config_dir,
                temporary_root=temporary_root,
                fallback_target=plan.target_root,
            )
            result = bridge.plan(config_dir)
        if _sha256_file(source) != before_hash:
            raise PolicyFcsaValidationError(
                f"FCSA-Dry-Run hat die Quelle verändert: {source}"
            )
        file_plan = next(
            (
                item
                for path_plan in result.paths
                for item in path_plan.files
                if item.relative_path == source.name
            ),
            None,
        )
        if file_plan is None or file_plan.had_error:
            raise PolicyFcsaValidationError(
                f"FCSA hat keinen gültigen Plan für {source.name} bestätigt."
            )
        planned_actions = tuple(item.action for item in file_plan.steps)
        if planned_actions != expected_actions:
            raise PolicyFcsaValidationError(
                f"FCSA-Aktionen weichen ab: erwartet {expected_actions}, "
                f"erhalten {planned_actions}."
            )
        validations.append(
            FcsaPolicyActionValidation(
                action_id=step.action_id,
                provider_id="file-collect-sort-action",
                source_path=source,
                target_directory=(
                    step.target_path.parent.resolve() if step.target_path else None
                ),
                planned_actions=planned_actions,
                settings_fingerprint=result.settings_fingerprint,
                would_mutate_fs=any(
                    item.would_mutate_fs for item in file_plan.steps
                ),
            )
        )
    return tuple(validations)


def _expected_actions(step: PolicyActionStep) -> tuple[str, ...]:
    if step.capability_id == "move":
        if step.target_path is None:
            raise PolicyFcsaValidationError(
                f"Verschiebeaktion hat kein Ziel: {step.action_id}"
            )
        return ("duplicate_check", "move")
    if step.capability_id == "delete-to-trash":
        return ("delete",)
    raise PolicyFcsaValidationError(
        f"Nicht unterstützte FCSA-Capability: {step.capability_id}"
    )


def _write_config(
    step: PolicyActionStep,
    *,
    config_dir: Path,
    temporary_root: Path,
    fallback_target: Path,
) -> None:
    source = step.source_path.resolve()
    expected_actions = list(_expected_actions(step))
    target_directory = (
        step.target_path.parent.resolve()
        if step.target_path is not None
        else (fallback_target / ".fcsa-unused-target").resolve()
    )
    category_id = f"policy_{step.action_id.removeprefix('act_')}"
    payloads = {
        "config.json": {
            "scan_paths": [str(source.parent)],
            "include_formats": None,
            "exclude_formats": [],
            "duplication_detection_rules": {
                "on_duplicate": "rename",
                "hash_algorithm": "sha256",
            },
            "state_dir": str(temporary_root / "state"),
            "trash_dir": str(temporary_root / "trash"),
            "allow_hard_delete": False,
            "require_dry_run_before_live": True,
            "ocr_backend": {"type": "none"},
        },
        "categories-definitions.json": {
            "categories": [
                {
                    "id": category_id,
                    "display_name": "FolderHome-Richtlinienaktion",
                    "detection": {
                        "filename_patterns": [f"^{re.escape(source.name)}$"],
                        "extensions": [source.suffix.lower()],
                    },
                    "checks": [],
                    "gates": [],
                    "default_target": str(target_directory),
                    "default_actions": expected_actions,
                    "default_stepping": True,
                }
            ],
            "fallback_category": "unsorted",
        },
        "action-rules.json": {
            "rules": {
                category_id: {
                    "move": {"target": "default"},
                    "duplicate_check": {"mode": "rename"},
                    "delete": {"hard_delete": False},
                    "information_placement_order": ["sidecar_file"],
                }
            },
            "default_rule": {
                "move": {"target": "default"},
                "duplicate_check": {"mode": "rename"},
                "delete": {"hard_delete": False},
                "information_placement_order": ["sidecar_file"],
            },
        },
    }
    for filename, payload in payloads.items():
        (config_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
