"""Build scheduler-neutral, read-only queues for multiple watched folders."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
from pathlib import Path

from folderhome.application.directory_observation import WatchedFolderConfiguration
from folderhome.application.folder_cleanup import CleanupDocumentExtractor
from folderhome.application.folder_routine import (
    FolderRoutineError,
    build_folder_routine_plan,
)
from folderhome.application.profile_rules import (
    ProfileConfiguration,
    ProfileConfigurationError,
    resolve_profile_policy,
)
from folderhome.contracts import (
    FolderRoutineBinding,
    FolderRoutineMode,
    FolderRoutineQueue,
    FolderRoutineQueueItem,
)

_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")


class RoutineQueueError(ValueError):
    """Raised when routine bindings or a multi-watch queue are ambiguous."""


@dataclass(frozen=True, slots=True)
class FolderRoutineBindingConfiguration:
    """Validated routine bindings stored separately from watch definitions."""

    bindings: tuple[FolderRoutineBinding, ...]


def load_folder_routine_bindings(path: Path) -> FolderRoutineBindingConfiguration:
    """Load target/mode bindings while resolving relative targets locally."""

    origin = path.resolve()
    try:
        payload = json.loads(origin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoutineQueueError(f"Routinenbindungen sind nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        "folderhome.routine-bindings.v1"
    ):
        raise RoutineQueueError("Routinenbindungen verwenden ein unbekanntes Schema.")
    items = payload.get("bindings")
    if not isinstance(items, list) or not items:
        raise RoutineQueueError(
            "Routinenbindungen benötigen eine nichtleere bindings-Liste."
        )
    bindings = tuple(
        _parse_binding(item, origin, index) for index, item in enumerate(items)
    )
    binding_ids = [item.binding_id for item in bindings]
    if len(binding_ids) != len(set(binding_ids)):
        raise RoutineQueueError("binding_id ist nicht eindeutig.")
    watch_ids = [item.watch_id for item in bindings]
    if len(watch_ids) != len(set(watch_ids)):
        raise RoutineQueueError("Ein Watch darf nicht mehrfach gebunden werden.")
    return FolderRoutineBindingConfiguration(bindings=bindings)


def build_folder_routine_queue(
    watches: WatchedFolderConfiguration,
    bindings: FolderRoutineBindingConfiguration,
    *,
    profiles: ProfileConfiguration,
    as_of: date,
    captured_at: str,
    state_dir: Path,
    extractor: CleanupDocumentExtractor,
) -> FolderRoutineQueue:
    """Plan every enabled watch without file, state, network, or scheduler writes."""

    watches_by_id = {watch.watch_id: watch for watch in watches.watches}
    unknown = sorted(
        binding.watch_id
        for binding in bindings.bindings
        if binding.watch_id not in watches_by_id
    )
    if unknown:
        raise RoutineQueueError(
            f"Routinenbindung verweist auf unbekannten Watch: {', '.join(unknown)}"
        )
    bindings_by_watch = {binding.watch_id: binding for binding in bindings.bindings}
    items = []
    for watch in sorted(watches.watches, key=lambda item: item.watch_id):
        if not watch.enabled:
            continue
        binding = bindings_by_watch.get(watch.watch_id)
        if binding is None:
            items.append(
                FolderRoutineQueueItem(
                    watch_id=watch.watch_id,
                    binding_id=None,
                    target_root=None,
                    mode=None,
                    status="blocked",
                    reason="Für den aktiven Watch fehlt eine Routinenbindung.",
                    plan=None,
                )
            )
            continue
        if not binding.enabled:
            items.append(
                FolderRoutineQueueItem(
                    watch_id=watch.watch_id,
                    binding_id=binding.binding_id,
                    target_root=binding.target_root,
                    mode=binding.mode,
                    status="blocked",
                    reason="Die Routinenbindung für den aktiven Watch ist deaktiviert.",
                    plan=None,
                )
            )
            continue
        try:
            policy = resolve_profile_policy(
                profiles,
                profile_id=watch.profile_id,
                area=watch.area,
            )
            plan = build_folder_routine_plan(
                watch,
                policy=policy,
                target_root=binding.target_root,
                as_of=as_of,
                captured_at=captured_at,
                state_dir=state_dir,
                extractor=extractor,
                mode=binding.mode,
            )
            status, reason = _queue_status(plan)
            items.append(
                FolderRoutineQueueItem(
                    watch_id=watch.watch_id,
                    binding_id=binding.binding_id,
                    target_root=binding.target_root,
                    mode=binding.mode,
                    status=status,
                    reason=reason,
                    plan=plan,
                )
            )
        except (FolderRoutineError, ProfileConfigurationError, ValueError) as exc:
            items.append(
                FolderRoutineQueueItem(
                    watch_id=watch.watch_id,
                    binding_id=binding.binding_id,
                    target_root=binding.target_root,
                    mode=binding.mode,
                    status="blocked",
                    reason=str(exc),
                    plan=None,
                )
            )
    finalized = _block_cross_watch_conflicts(tuple(items), watches_by_id)
    queue_id = _queue_id(captured_at, as_of.isoformat(), finalized)
    return FolderRoutineQueue(
        queue_id=queue_id,
        captured_at=captured_at,
        as_of=as_of.isoformat(),
        items=finalized,
    )


def _parse_binding(item: object, origin: Path, index: int) -> FolderRoutineBinding:
    if not isinstance(item, dict):
        raise RoutineQueueError(f"Routinenbindung {index} muss ein JSON-Objekt sein.")
    binding_id = _required_id(item, "binding_id", index)
    watch_id = _required_id(item, "watch_id", index)
    target_value = item.get("target_dir")
    if not isinstance(target_value, str) or not target_value.strip():
        raise RoutineQueueError(
            f"Routinenbindung {index} benötigt einen target_dir."
        )
    target = Path(target_value)
    if not target.is_absolute():
        target = origin.parent / target
    try:
        mode = FolderRoutineMode(item.get("mode"))
    except ValueError as exc:
        raise RoutineQueueError(
            f"Routinenbindung {index} verwendet einen unbekannten Modus."
        ) from exc
    enabled = item.get("enabled")
    if not isinstance(enabled, bool):
        raise RoutineQueueError(
            f"Routinenbindung {index} benötigt einen booleschen enabled-Wert."
        )
    return FolderRoutineBinding(
        binding_id=binding_id,
        watch_id=watch_id,
        target_root=target,
        mode=mode,
        enabled=enabled,
    )


def _required_id(item: dict[str, object], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise RoutineQueueError(
            f"{field} in Routinenbindung {index} ist keine stabile Kleinbuchstaben-ID."
        )
    return value


def _queue_status(plan) -> tuple[str, str]:
    if plan.status == "not_due":
        return "not_due", plan.reason
    if plan.status == "no_changes":
        return "empty", plan.reason
    if plan.status == "planned" and plan.approval_required:
        return "ready", "Routinenplan ist fällig und enthält freigabefähige Aktionen."
    return "blocked", "Routinenplan enthält keine konfliktfrei freigabefähige Aktion."


def _block_cross_watch_conflicts(
    items: tuple[FolderRoutineQueueItem, ...],
    watches_by_id: dict[str, object],
) -> tuple[FolderRoutineQueueItem, ...]:
    reasons: dict[str, set[str]] = defaultdict(set)
    active = [item for item in items if item.plan is not None]
    for index, first in enumerate(active):
        first_watch = watches_by_id[first.watch_id]
        for second in active[index + 1 :]:
            second_watch = watches_by_id[second.watch_id]
            if _paths_overlap(first_watch.source_root, second_watch.source_root):
                reason = "Aktive Watches besitzen überlappende Eingangsordner."
                reasons[first.watch_id].add(reason)
                reasons[second.watch_id].add(reason)
            if first.target_root and _is_within(first.target_root, second_watch.source_root):
                reason = "Ein Routinenziel liegt im Eingangsordner eines anderen Watch."
                reasons[first.watch_id].add(reason)
                reasons[second.watch_id].add(reason)
            if second.target_root and _is_within(second.target_root, first_watch.source_root):
                reason = "Ein Routinenziel liegt im Eingangsordner eines anderen Watch."
                reasons[first.watch_id].add(reason)
                reasons[second.watch_id].add(reason)

    targets: dict[Path, set[str]] = defaultdict(set)
    for item in active:
        assert item.plan is not None
        for cleanup_item in item.plan.cleanup_plan.items:
            if cleanup_item.action_plan is None:
                continue
            approved = set(cleanup_item.executable_action_ids)
            for step in cleanup_item.action_plan.steps:
                if step.action_id in approved and step.target_path is not None:
                    targets[step.target_path].add(item.watch_id)
    for watch_ids in targets.values():
        if len(watch_ids) > 1:
            for watch_id in watch_ids:
                reasons[watch_id].add(
                    "Mehrere Watch-Routinen verwenden gemeinsame Ziele."
                )

    finalized = []
    for item in items:
        item_reasons = sorted(reasons.get(item.watch_id, ()))
        if item_reasons:
            finalized.append(
                replace(item, status="blocked", reason=" ".join(item_reasons))
            )
        else:
            finalized.append(item)
    return tuple(finalized)


def _paths_overlap(first: Path, second: Path) -> bool:
    return _is_within(first, second) or _is_within(second, first)


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _queue_id(
    captured_at: str,
    as_of: str,
    items: tuple[FolderRoutineQueueItem, ...],
) -> str:
    payload = {
        "schema": FolderRoutineQueue.SCHEMA,
        "captured_at": captured_at,
        "as_of": as_of,
        "items": [item.to_dict() for item in items],
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"routine_queue_{sha256(material).hexdigest()}"
