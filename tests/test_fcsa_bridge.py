from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from folderhome import contracts
from folderhome.application.fcsa_plan import run_fcsa_plan
from folderhome.bridges.fcsa import (
    FcsaBridgeError,
    FcsaDryRunBridge,
    FcsaDryRunResult,
    FcsaFilePlan,
    FcsaPathPlan,
    FcsaPlanStep,
)
from folderhome.plugin_host import load_manifests

REPO_ROOT = Path(__file__).parents[1]
FCSA_ROOT = REPO_ROOT.parent / "file-collect-sort-action"
MANIFEST_ROOT = REPO_ROOT / "manifests" / "components"


def _fcsa_plugin() -> contracts.PluginDescriptor:
    return next(
        plugin
        for plugin in load_manifests(MANIFEST_ROOT)
        if plugin.plugin_id == "file-collect-sort-action"
    )


def _write_fcsa_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    config_dir = tmp_path / "config"
    scan_dir = tmp_path / "inbox"
    target_dir = tmp_path / "sorted"
    state_dir = tmp_path / "state"
    config_dir.mkdir()
    scan_dir.mkdir()
    target_dir.mkdir()
    (scan_dir / "Rechnung_August.txt").write_text(
        "Rechnungsnummer 2026-08-21",
        encoding="utf-8",
    )
    config = {
        "scan_paths": [str(scan_dir)],
        "include_formats": None,
        "exclude_formats": [],
        "duplication_detection_rules": {
            "on_duplicate": "rename",
            "hash_algorithm": "sha256",
        },
        "state_dir": str(state_dir),
        "trash_dir": str(state_dir / "trash"),
        "allow_hard_delete": False,
        "require_dry_run_before_live": True,
        "ocr_backend": {"type": "none"},
    }
    categories = {
        "categories": [
            {
                "id": "invoices",
                "display_name": "Rechnungen",
                "detection": {
                    "filename_patterns": ["(?i)rechnung"],
                    "extensions": [".txt"],
                    "content_patterns": ["(?i)rechnungsnummer"],
                },
                "checks": [],
                "gates": [],
                "default_target": str(target_dir),
                "default_actions": ["duplicate_check", "move"],
                "default_stepping": True,
            }
        ],
        "fallback_category": "unsorted",
    }
    action_rules = {
        "rules": {
            "invoices": {
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
    }
    for name, payload in (
        ("config.json", config),
        ("categories-definitions.json", categories),
        ("action-rules.json", action_rules),
    ):
        (config_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    return config_dir, scan_dir, target_dir, state_dir


@pytest.mark.skipif(not FCSA_ROOT.is_dir(), reason="pinned sibling FCSA checkout unavailable")
def test_real_fcsa_bridge_creates_plan_without_touching_user_state(tmp_path: Path) -> None:
    config_dir, scan_dir, target_dir, state_dir = _write_fcsa_fixture(tmp_path)
    before = (scan_dir / "Rechnung_August.txt").read_bytes()
    bridge = FcsaDryRunBridge(plugin=_fcsa_plugin(), provider_root=FCSA_ROOT)

    result = bridge.plan(config_dir)

    assert (scan_dir / "Rechnung_August.txt").read_bytes() == before
    assert list(target_dir.iterdir()) == []
    assert not state_dir.exists()
    assert result.settings_fingerprint
    assert result.paths[0].files[0].relative_path == "Rechnung_August.txt"
    assert result.paths[0].files[0].category_id == "invoices"
    assert [step.action for step in result.paths[0].files[0].steps] == [
        "duplicate_check",
        "move",
    ]
    assert result.paths[0].files[0].steps[1].would_mutate_fs is True


@pytest.mark.skipif(not FCSA_ROOT.is_dir(), reason="pinned sibling FCSA checkout unavailable")
def test_provider_revision_mismatch_fails_closed(tmp_path: Path) -> None:
    config_dir, _, _, _ = _write_fcsa_fixture(tmp_path)
    wrong_plugin = replace(_fcsa_plugin(), source_revision="0" * 40)
    bridge = FcsaDryRunBridge(plugin=wrong_plugin, provider_root=FCSA_ROOT)

    with pytest.raises(FcsaBridgeError, match="Git-Revision"):
        bridge.plan(config_dir)


class StubBridge:
    def plan(self, config_dir: Path) -> FcsaDryRunResult:
        assert config_dir.name == "config"
        return FcsaDryRunResult(
            settings_fingerprint="a" * 64,
            paths=(
                FcsaPathPlan(
                    scan_path=Path("C:/synthetic/inbox"),
                    unchanged_count=0,
                    skipped_locked=(),
                    was_stale=False,
                    files=(
                        FcsaFilePlan(
                            relative_path="Rechnung_August.txt",
                            category_id="invoices",
                            matched_category=True,
                            status="dry_run_only",
                            had_error=False,
                            steps=(
                                FcsaPlanStep(
                                    action="move",
                                    detail="würde nach Rechnungen verschieben",
                                    would_mutate_fs=True,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )


def test_application_maps_fcsa_plan_to_audited_folderhome_report(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    report = run_fcsa_plan(
        config_dir,
        run_id="run_fcsa_plan",
        plugin=_fcsa_plugin(),
        bridge=StubBridge(),
    )

    assert report.status is contracts.RunStatus.EXECUTED
    assert report.plugin_id == "file-collect-sort-action"
    assert report.capability_id == "documents.collect_sort"
    assert report.dry_run is True
    assert report.provider.source_revision == _fcsa_plugin().source_revision
    assert report.actions[0].status is contracts.RunStatus.PLANNED
    assert report.actions[0].side_effects == (contracts.SideEffect.FILESYSTEM_WRITE,)
    assert report.actions[0].gate.required is True
    assert report.actions[0].gate.granted is False
    assert report.decisions[0].status is contracts.DecisionStatus.PENDING


class FailingBridge:
    def plan(self, config_dir: Path) -> FcsaDryRunResult:
        raise FcsaBridgeError("Konfiguration ist ungültig")


def test_bridge_failure_becomes_an_auditable_failed_report(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    report = run_fcsa_plan(
        config_dir,
        run_id="run_fcsa_failure",
        plugin=_fcsa_plugin(),
        bridge=FailingBridge(),
    )

    assert report.status is contracts.RunStatus.FAILED
    assert report.actions[0].status is contracts.RunStatus.FAILED
    assert report.actions[0].message == "FCSA-Dry-Run fehlgeschlagen: Konfiguration ist ungültig"
    assert report.decisions == ()
