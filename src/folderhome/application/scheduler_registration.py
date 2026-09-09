"""Content-bound registration planning; no scheduler writes or consumer startup."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from folderhome.application.directory_observation import load_watched_folder_configuration
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.routine_queue import load_folder_routine_bindings
from folderhome.application.scheduler_handoff import (
    _safe_state_root,
    validate_scheduler_handoff,
)
from folderhome.bridges._provider import verify_checkout_revision
from folderhome.contracts.scheduler import SchedulerHandoffPlan
from folderhome.plugin_host import load_manifests


class SchedulerRegistrationError(ValueError):
    """Registration configuration no longer matches the reviewed proposal."""


@dataclass(frozen=True, slots=True)
class SchedulerRegistrationPlan:
    """Private execution inputs; physical paths must not become model arguments."""

    plan_id: str
    handoff: SchedulerHandoffPlan
    store_path: Path
    ledger_dir: Path
    provider_root: Path
    provider_revision: str
    configuration_files: tuple[tuple[str, str], ...]
    resolved_directories: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.scheduler-registration-plan.v1",
            "plan_id": self.plan_id,
            "handoff": self.handoff.to_dict(),
            "store_path": str(self.store_path),
            "ledger_dir": str(self.ledger_dir),
            "provider_root": str(self.provider_root),
            "provider_revision": self.provider_revision,
            "configuration_files": [
                {"path": path, "sha256": digest} for path, digest in self.configuration_files
            ],
            "resolved_directories": [
                {"resource": resource, "path": path} for resource, path in self.resolved_directories
            ],
        }


def build_scheduler_registration_plan(
    *,
    handoff: SchedulerHandoffPlan,
    store_path: Path,
    ledger_dir: Path,
    provider_root: Path,
    provider_revision: str,
) -> SchedulerRegistrationPlan:
    """Bind configuration membership and bytes, not changing watched documents.

    Construction performs only reads. This proposal alone grants no permission
    and does not imply that any job is registered or any consumer is running.
    """
    try:
        handoff = validate_scheduler_handoff(handoff)
        store_path = _safe_state_root(store_path)
        ledger_dir = _safe_state_root(ledger_dir)
        provider_root = _safe_state_root(provider_root)
        verify_checkout_revision(provider_root, provider_revision)
        files = _configuration_files(handoff)
        resolved_directories = _resolved_directories(handoff)
        load_profile_configuration(handoff.profiles_dir)
        load_manifests(handoff.manifest_root)
        if files != _configuration_files(handoff) or resolved_directories != _resolved_directories(
            handoff
        ):
            raise SchedulerRegistrationError("Konfiguration wurde während der Planung verändert.")
        provisional = SchedulerRegistrationPlan(
            plan_id="",
            handoff=handoff,
            store_path=store_path,
            ledger_dir=ledger_dir,
            provider_root=provider_root,
            provider_revision=provider_revision,
            configuration_files=files,
            resolved_directories=resolved_directories,
        )
        encoded = json.dumps(
            provisional.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return SchedulerRegistrationPlan(
            plan_id="registration_" + sha256(encoded).hexdigest(),
            handoff=handoff,
            store_path=store_path,
            ledger_dir=ledger_dir,
            provider_root=provider_root,
            provider_revision=provider_revision,
            configuration_files=files,
            resolved_directories=resolved_directories,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        raise SchedulerRegistrationError(
            f"Scheduler-Konfiguration ist nicht freigabefähig: {exc}"
        ) from exc


def validate_scheduler_registration_plan(
    plan: SchedulerRegistrationPlan,
) -> SchedulerRegistrationPlan:
    """Reconstruct an independent snapshot before registration and later runs."""
    current = build_scheduler_registration_plan(
        handoff=plan.handoff,
        store_path=plan.store_path,
        ledger_dir=plan.ledger_dir,
        provider_root=plan.provider_root,
        provider_revision=plan.provider_revision,
    )
    if current != plan:
        raise SchedulerRegistrationError(
            "Registrierungsplan wurde verändert; neu planen und prüfen."
        )
    return current


def _configuration_files(handoff: SchedulerHandoffPlan) -> tuple[tuple[str, str], ...]:
    profiles = _safe_state_root(handoff.profiles_dir)
    manifests = _safe_state_root(handoff.manifest_root)
    if not profiles.is_dir() or not manifests.is_dir():
        raise SchedulerRegistrationError("Profil- oder Manifestverzeichnis fehlt.")
    paths = {handoff.config_file, handoff.bindings_file}
    paths.update(profiles.glob("*.json"))
    paths.update(manifests.glob("*.toml"))
    return tuple(
        (str(path), sha256(_safe_state_root(path).read_bytes()).hexdigest())
        for path in sorted(paths, key=str)
    )


def _resolved_directories(handoff: SchedulerHandoffPlan) -> tuple[tuple[str, str], ...]:
    watches = load_watched_folder_configuration(handoff.config_file)
    bindings = load_folder_routine_bindings(handoff.bindings_file)
    return tuple(
        sorted(
            [("watch:" + item.watch_id, str(item.source_root)) for item in watches.watches]
            + [("binding:" + item.binding_id, str(item.target_root)) for item in bindings.bindings]
        )
    )
