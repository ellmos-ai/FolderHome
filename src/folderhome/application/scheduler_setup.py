"""Plan setup-owned scheduler configuration; never register or start a job."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from folderhome.application.directory_observation import _parse_watch
from folderhome.application.routine_queue import _parse_binding
from folderhome.application.scheduler_handoff import _safe_state_root, _timestamp, _timezone

_FORM_FIELDS = {
    "profile_id",
    "source_dir",
    "target_dir",
    "area",
    "interval_minutes",
    "start_at",
    "timezone",
    "recursive",
    "allow_sensitive_local_read",
    "confirm_outside_home",
}
_SCHEMA = "folderhome.scheduler-setup.v1"


def plan_scheduler_setup(raw, *, config_dir, profiles, resources):
    """Return exact file contents and logical grants for one selected profile."""
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != _FORM_FIELDS:
        raise ValueError("Scheduler-Einstellungen besitzen fehlende oder unbekannte Felder.")
    profile = raw["profile_id"]
    if profile not in {item.profile_id for item in profiles.profiles}:
        raise ValueError("Scheduler benötigt ein vorhandenes Profil.")
    if raw["allow_sensitive_local_read"] is not True:
        raise ValueError("Lokales Lesen benötigt eine ausdrückliche Freigabe.")
    if type(raw["recursive"]) is not bool or type(raw["confirm_outside_home"]) is not bool:
        raise ValueError("Scheduler-Schalter müssen boolesch sein.")
    interval = raw["interval_minutes"]
    if type(interval) is not int or not 5 <= interval <= 1440:
        raise ValueError("Prüfintervall muss 5 bis 1440 ganze Minuten betragen.")
    start = _timestamp(raw["start_at"], "start_at")
    zone = _timezone(raw["timezone"])
    if start.astimezone(zone).utcoffset() != start.utcoffset():
        raise ValueError("Termin und Zeitzone besitzen unterschiedliche UTC-Versätze.")
    source, target = (_directory(raw[field]) for field in ("source_dir", "target_dir"))
    if source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Quell- und Zielordner müssen getrennt sein.")
    if not raw["confirm_outside_home"] and any(
        not path.is_relative_to(Path.home().resolve()) for path in (source, target)
    ):
        raise ValueError("Ordner außerhalb des Benutzerordners benötigen eine Bestätigung.")
    config_dir = _safe_state_root(config_dir)
    if any(config_dir.is_relative_to(path) for path in (source, target)):
        raise ValueError("Scheduler-Betriebsdaten dürfen nicht im Quell- oder Zielordner liegen.")
    prefix = "fh_sched_" + sha256(profile.encode("utf-8")).hexdigest()[:12]
    base = config_dir / prefix
    if any(path.is_relative_to(base) or base.is_relative_to(path) for path in (source, target)):
        raise ValueError("Dokumentordner und Scheduler-Betriebsverzeichnisse müssen getrennt sein.")
    paths = {
        "watches": config_dir / f"{prefix}-watches.json",
        "bindings": config_dir / f"{prefix}-bindings.json",
        "request": config_dir / f"{prefix}-request.json",
        "store": base / "jobs.db",
        "ledger": base / "receipts",
        "state": base / "runner",
    }
    for path in paths.values():
        _safe_state_root(path)
    if paths["store"].exists() or any(
        Path(str(paths["store"]) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")
    ):
        raise ValueError(
            "Vorhandene Registrierung zuerst separat prüfen und stoppen; "
            "Setup verändert keine bestehenden Jobs. Unbearbeitet bleibt sie erhalten."
        )
    owner = paths["request"]
    if owner.exists():
        previous = json.loads(owner.read_text(encoding="utf-8"))
        if previous.get("schema") != _SCHEMA or previous.get("profile_id") != profile:
            raise ValueError("Vorhandene Scheduler-Datei gehört nicht zu diesem Setup-Profil.")
        for key, collection in (("watches", "watches"), ("bindings", "bindings")):
            content = json.loads(paths[key].read_text(encoding="utf-8"))
            items = content.get(collection)
            if (
                set(content) != {"schema", collection}
                or not isinstance(items, list)
                or (
                    len(items) != 1
                    or not isinstance(items[0], dict)
                    or items[0].get("watch_id") != prefix
                )
            ):
                raise ValueError("Zusätzliche oder fremde Watch-Bindungen bleiben unverändert.")
    elif paths["watches"].exists() or paths["bindings"].exists() or base.exists():
        raise ValueError("Vorhandene Scheduler-Pfade ohne Setup-Zuordnung bleiben unverändert.")
    watch = {
        "watch_id": prefix,
        "source_dir": str(source),
        "profile_id": profile,
        "area": raw["area"],
        "interval_minutes": interval,
        "recursive": raw["recursive"],
        "enabled": True,
    }
    binding = {
        "binding_id": prefix,
        "watch_id": prefix,
        "target_dir": str(target),
        "mode": "changes",
        "enabled": True,
    }
    _parse_watch(watch, paths["watches"], 0)
    _parse_binding(binding, paths["bindings"], 0)
    request = {
        f"{key}_resource_id": f"{prefix}_{key}"
        for key in ("watches", "bindings", "store", "ledger", "state")
    }
    request.update(
        task_name=prefix,
        interval_minutes=interval,
        start_at=raw["start_at"],
        timezone=raw["timezone"],
        allow_sensitive_local_read=True,
    )
    documents = [
        {
            "path": str(paths["watches"]),
            "document": {
                "schema": "folderhome.watched-folders.v1",
                "watches": [watch],
            },
        },
        {
            "path": str(paths["bindings"]),
            "document": {
                "schema": "folderhome.routine-bindings.v1",
                "bindings": [binding],
            },
        },
        {
            "path": str(owner),
            "document": {
                "schema": _SCHEMA,
                "profile_id": profile,
                "request": request,
            },
        },
    ]
    declarations = []
    for key, kind, operations in (
        ("watches", "file", ["read"]),
        ("bindings", "file", ["read"]),
        ("request", "file", ["read"]),
        ("store", "sqlite_store", ["read", "state_write"]),
        ("ledger", "directory", ["read", "state_write"]),
        ("state", "directory", ["read", "state_write"]),
        ("source", "directory", ["list", "read", "sensitive_read"]),
        ("target", "directory", ["list", "read"]),
    ):
        path = source if key == "source" else target if key == "target" else paths[key]
        purpose = f"routine_queue.{key}" if key in {"source", "target"} else f"scheduler.{key}"
        declarations.append(
            {
                "resource_id": f"{prefix}_{key}",
                "kind": kind,
                "locator": {"type": "local_path", "path": str(path)},
                "operations": operations,
                "purposes": [purpose],
                "profile_ids": [profile],
                "cloud_context": "deny",
            }
        )
    identifiers = {item["resource_id"] for item in declarations}
    expected = {item["resource_id"]: item for item in declarations}
    existing = resources["resources"]
    for item in existing:
        if item["resource_id"] in identifiers and (
            not owner.exists() or item["profile_ids"] != [profile]
        ):
            raise ValueError("Scheduler-Ressourcen kollidieren mit einer fremden Zuordnung.")
        if item["resource_id"] in identifiers and any(
            set(item[field]) != set(expected[item["resource_id"]][field])
            for field in ("operations", "purposes")
        ):
            raise ValueError("Geänderte Scheduler-Berechtigungen bleiben unverändert.")
        if (
            item["resource_id"] not in identifiers
            and profile in item["profile_ids"]
            and any(
                purpose in item["purposes"]
                for purpose in ("routine_queue.source", "routine_queue.target")
            )
            and Path(item["locator"]["path"]).resolve() in {source, target}
        ):
            raise ValueError("Scheduler-Ordner besitzt bereits eine andere Queue-Zuordnung.")
    resources["resources"] = [item for item in existing if item["resource_id"] not in identifiers]
    resources["resources"].extend(declarations)
    return {
        "profile_id": profile,
        "documents": documents,
        "directories": [str(base), str(paths["ledger"]), str(paths["state"])],
        "previous_files": [
            {
                "path": item["path"],
                "sha256": sha256(Path(item["path"]).read_bytes()).hexdigest()
                if Path(item["path"]).is_file()
                else None,
            }
            for item in documents
        ],
        "request": request,
        "registration_performed": False,
        "consumer_started": False,
    }


def scheduler_planned_targets(plan):
    if plan is None:
        return {}
    return {
        **{Path(item["path"]): "file" for item in plan["documents"]},
        **{Path(path): "directory" for path in plan["directories"]},
    }


def read_scheduler_forms(registry):
    """Read saved forms from the same files the runtime will use."""
    forms = {}
    if registry is None:
        return forms
    by_id = {item.resource_id: item for item in registry.resources}
    for item in registry.resources:
        if "scheduler.request" not in item.purposes:
            continue
        document = json.loads(item.local_path.read_text(encoding="utf-8"))
        profile = document["profile_id"]
        if document["schema"] != _SCHEMA or item.profile_ids != frozenset({profile}):
            raise ValueError("Gespeicherter Scheduler-Antrag besitzt eine ungültige Zuordnung.")
        request = document["request"]
        watch_file = by_id[request["watches_resource_id"]].local_path
        binding_file = by_id[request["bindings_resource_id"]].local_path
        watches = json.loads(watch_file.read_text(encoding="utf-8"))["watches"]
        bindings = json.loads(binding_file.read_text(encoding="utf-8"))["bindings"]
        if len(watches) != 1 or len(bindings) != 1:
            raise ValueError("Mehrfach-Watches werden im einfachen Setup nicht überschrieben.")
        watch = _parse_watch(watches[0], watch_file, 0)
        binding = _parse_binding(bindings[0], binding_file, 0)
        if watch.profile_id != profile or binding.watch_id != watch.watch_id:
            raise ValueError("Gespeicherte Watch-Zuordnung ist widersprüchlich.")
        forms[profile] = {
            "profile_id": profile,
            "source_dir": str(watch.source_root),
            "target_dir": str(binding.target_root),
            "area": watch.area,
            "interval_minutes": request["interval_minutes"],
            "start_at": request["start_at"],
            "timezone": request["timezone"],
            "recursive": watch.recursive,
            "allow_sensitive_local_read": request["allow_sensitive_local_read"],
            "confirm_outside_home": False,
        }
    return forms


def _directory(value):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError("Scheduler-Ordner benötigen absolute lokale Pfade.")
    path = _safe_state_root(Path(value))
    if not path.is_dir():
        raise ValueError("Scheduler-Quell- und Zielordner müssen bereits existieren.")
    return path
