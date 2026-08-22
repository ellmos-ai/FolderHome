"""Validate archive proposals through the real pinned FCSA dry-run pipeline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from folderhome.bridges.fcsa import FcsaDryRunResult
from folderhome.contracts import ArchiveProposal


class ArchivePlanValidationError(RuntimeError):
    """Raised when FCSA does not confirm the proposed reversible move plan."""


class FcsaArchivePlanner(Protocol):
    """Dry-run port implemented by the pinned FCSA bridge."""

    def plan(self, config_dir: Path) -> FcsaDryRunResult: ...


@dataclass(frozen=True, slots=True)
class FcsaArchivePlan:
    """Provider-confirmed but still ungranted archive plan."""

    document_id: str
    provider_id: str
    source_path: Path
    target_directory: Path
    planned_actions: tuple[str, ...]
    settings_fingerprint: str
    would_mutate_fs: bool
    gate_granted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.fcsa-archive-plan.v1",
            "document_id": self.document_id,
            "provider_id": self.provider_id,
            "source_path": str(self.source_path),
            "target_directory": str(self.target_directory),
            "planned_actions": list(self.planned_actions),
            "settings_fingerprint": self.settings_fingerprint,
            "would_mutate_fs": self.would_mutate_fs,
            "gate": {"required": True, "granted": self.gate_granted},
        }


def validate_archive_proposals(
    proposals: tuple[ArchiveProposal, ...],
    *,
    bridge: FcsaArchivePlanner,
) -> tuple[FcsaArchivePlan, ...]:
    """Run one isolated FCSA dry-run per proposal and return confirmed plans."""

    plans = []
    for proposal in proposals:
        if proposal.gate_granted or proposal.status != "planned":
            raise ArchivePlanValidationError(
                "Nur ungefreigte Archivierungsvorschläge dürfen validiert werden."
            )
        source = proposal.source_path.resolve()
        if not source.is_file():
            raise ArchivePlanValidationError(f"Archivierungsquelle fehlt: {source}")
        before_hash = _sha256_file(source)
        with TemporaryDirectory(prefix="folderhome-archive-plan-") as temporary:
            config_dir = Path(temporary) / "config"
            config_dir.mkdir()
            _write_config(proposal, config_dir, Path(temporary))
            result = bridge.plan(config_dir)
        if _sha256_file(source) != before_hash:
            raise ArchivePlanValidationError(
                f"FCSA-Dry-Run hat die Archivierungsquelle verändert: {source}"
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
            raise ArchivePlanValidationError(
                f"FCSA hat keinen gültigen Plan für {source.name} bestätigt."
            )
        planned_actions = tuple(step.action for step in file_plan.steps)
        if "move" not in planned_actions:
            raise ArchivePlanValidationError(
                f"FCSA-Plan enthält keine Verschiebung für {source.name}."
            )
        plans.append(
            FcsaArchivePlan(
                document_id=proposal.document_id,
                provider_id=proposal.provider_id,
                source_path=source,
                target_directory=proposal.target_path.parent.resolve(),
                planned_actions=planned_actions,
                settings_fingerprint=result.settings_fingerprint,
                would_mutate_fs=any(
                    step.would_mutate_fs for step in file_plan.steps
                ),
            )
        )
    return tuple(plans)


def _write_config(
    proposal: ArchiveProposal,
    config_dir: Path,
    temporary_root: Path,
) -> None:
    source = proposal.source_path.resolve()
    category_id = f"archive_{proposal.document_id[4:20]}"
    payloads = {
        "config.json": {
            "scan_paths": [str(source.parent)],
            "include_formats": None,
            "exclude_formats": [],
            "duplication_detection_rules": {
                "on_duplicate": proposal.collision_policy,
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
                    "display_name": "Ältere Dokumentfassung archivieren",
                    "detection": {
                        "filename_patterns": [f"^{re.escape(source.name)}$"],
                        "extensions": [source.suffix.lower()],
                    },
                    "checks": [],
                    "gates": [],
                    "default_target": str(proposal.target_path.parent.resolve()),
                    "default_actions": ["duplicate_check", "move"],
                    "default_stepping": True,
                }
            ],
            "fallback_category": "unsorted",
        },
        "action-rules.json": {
            "rules": {
                category_id: {
                    "move": {"target": "default"},
                    "duplicate_check": {"mode": proposal.collision_policy},
                    "delete": {"hard_delete": False},
                    "information_placement_order": ["sidecar_file"],
                }
            },
            "default_rule": {
                "move": {"target": "default"},
                "duplicate_check": {"mode": proposal.collision_policy},
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
