"""Pinned, dry-run-only adapter for file-collect-sort-action."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
)
from folderhome.contracts import PluginDescriptor

CONFIG_FILENAMES = (
    "config.json",
    "categories-definitions.json",
    "action-rules.json",
)


class FcsaBridgeError(RuntimeError):
    """Raised when the pinned FCSA provider cannot produce a trusted plan."""


@dataclass(frozen=True, slots=True)
class FcsaPlanStep:
    """One provider action proposed for a single file."""

    action: str
    detail: str
    would_mutate_fs: bool


@dataclass(frozen=True, slots=True)
class FcsaFilePlan:
    """Categorization and action plan for one relative file path."""

    relative_path: str
    category_id: str
    matched_category: bool
    status: str
    had_error: bool
    steps: tuple[FcsaPlanStep, ...]


@dataclass(frozen=True, slots=True)
class FcsaPathPlan:
    """Dry-run result for one configured scan path."""

    scan_path: Path
    unchanged_count: int
    skipped_locked: tuple[str, ...]
    was_stale: bool
    files: tuple[FcsaFilePlan, ...]


@dataclass(frozen=True, slots=True)
class FcsaDryRunResult:
    """Provider-neutral result returned to the FolderHome application layer."""

    settings_fingerprint: str
    paths: tuple[FcsaPathPlan, ...]


class FcsaDryRunBridge:
    """Load an exact FCSA checkout and run it against a shadow state directory."""

    def __init__(self, *, plugin: PluginDescriptor, provider_root: Path) -> None:
        self._plugin = plugin
        self._provider_root = provider_root.resolve()

    def plan(self, config_dir: Path) -> FcsaDryRunResult:
        """Return a dry-run plan without confirming or changing the user setup."""

        package, config, pipeline = self._load_provider()
        config_dir = config_dir.resolve()
        try:
            loaded = config.load_all(config_dir)
        except Exception as exc:  # FCSA owns its concrete exception hierarchy.
            raise FcsaBridgeError(f"FCSA-Konfiguration konnte nicht geladen werden: {exc}") from exc

        try:
            fingerprint = pipeline.compute_fingerprint(loaded)
            with TemporaryDirectory(prefix="folderhome-fcsa-") as temporary:
                shadow_dir = Path(temporary) / "config"
                shadow_dir.mkdir()
                self._write_shadow_config(loaded, shadow_dir, Path(temporary))
                shadow_loaded = config.load_all(shadow_dir)
                path_plans = tuple(
                    self._map_path_result(
                        pipeline.run_scan_path(
                            shadow_loaded,
                            scan_path,
                            dry_run=True,
                            force_first_run=False,
                        )
                    )
                    for scan_path in loaded.config.scan_paths
                )
        except FcsaBridgeError:
            raise
        except Exception as exc:
            raise FcsaBridgeError(f"FCSA-Dry-Run konnte nicht ausgeführt werden: {exc}") from exc
        return FcsaDryRunResult(settings_fingerprint=fingerprint, paths=path_plans)

    def _load_provider(self) -> tuple[object, object, object]:
        if self._plugin.plugin_id != "file-collect-sort-action":
            raise FcsaBridgeError(
                f"Falscher Provider für die FCSA-Bridge: {self._plugin.plugin_id}"
            )
        try:
            modules = load_pinned_python_modules(
                plugin=self._plugin,
                provider_root=self._provider_root,
                package_name="fcsa",
                module_names=("fcsa.config", "fcsa.pipeline"),
            )
        except ProviderCheckoutError as exc:
            raise FcsaBridgeError(str(exc).replace("Provider", "FCSA-Provider")) from exc
        return modules["fcsa"], modules["fcsa.config"], modules["fcsa.pipeline"]

    @staticmethod
    def _write_shadow_config(loaded: object, shadow_dir: Path, temporary_root: Path) -> None:
        raw_config = deepcopy(loaded.raw_config)
        raw_config["state_dir"] = str(temporary_root / "state")
        raw_config["trash_dir"] = str(temporary_root / "trash")
        payloads = {
            "config.json": raw_config,
            "categories-definitions.json": loaded.raw_categories,
            "action-rules.json": loaded.raw_action_rules,
        }
        for filename in CONFIG_FILENAMES:
            (shadow_dir / filename).write_text(
                json.dumps(payloads[filename], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @staticmethod
    def _map_path_result(result: object) -> FcsaPathPlan:
        files = tuple(
            FcsaFilePlan(
                relative_path=file_result.rel_path,
                category_id=file_result.category_id,
                matched_category=file_result.matched_category,
                status=file_result.status,
                had_error=file_result.had_error,
                steps=tuple(
                    FcsaPlanStep(
                        action=step["action"],
                        detail=step["detail"],
                        would_mutate_fs=bool(step["would_mutate_fs"]),
                    )
                    for step in file_result.plan
                ),
            )
            for file_result in result.files
        )
        return FcsaPathPlan(
            scan_path=Path(result.scan_path),
            unchanged_count=result.unchanged_count,
            skipped_locked=tuple(result.skipped_locked),
            was_stale=result.was_stale,
            files=files,
        )
