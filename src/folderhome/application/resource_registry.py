"""Load FolderHome's private, OS-account-local logical resource registry."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from folderhome.contracts.resources import (
    LogicalResource,
    ResourceRegistry,
    ResourceRegistryError,
)


def default_resource_registry_path(
    *, environ: Mapping[str, str] | None = None
) -> Path:
    """Return the per-OS-account FolderHome registry location."""

    values = os.environ if environ is None else environ
    base = values.get("LOCALAPPDATA", "").strip()
    local_app_data = Path(base) if base else Path.home() / "AppData" / "Local"
    return local_app_data / "FolderHome" / "resources.json"


def load_resource_registry(
    path: Path,
    *,
    expected_os_account: str,
    known_profile_ids: frozenset[str],
) -> ResourceRegistry:
    """Load exact schema, local paths and profile defaults without creating anything."""

    path = path.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceRegistryError(f"Ressourcenregister ist nicht lesbar: {exc}") from exc
    return parse_resource_registry(
        payload,
        expected_os_account=expected_os_account,
        known_profile_ids=known_profile_ids,
    )


def parse_resource_registry(
    payload: object,
    *,
    expected_os_account: str,
    known_profile_ids: frozenset[str],
) -> ResourceRegistry:
    """Apply the same checks to a document that is not on disk yet."""

    if not isinstance(payload, dict):
        raise ResourceRegistryError("Ressourcenregister muss ein JSON-Objekt sein.")
    expected_fields = {"schema", "os_account", "resources", "profile_defaults"}
    if set(payload) != expected_fields:
        raise ResourceRegistryError("Ressourcenregister besitzt unbekannte oder fehlende Felder.")
    if payload["schema"] != ResourceRegistry.SCHEMA:
        raise ResourceRegistryError("Ressourcenregister verwendet ein unbekanntes Schema.")
    if payload["os_account"] != expected_os_account:
        raise ResourceRegistryError("Ressourcenregister gehört nicht zum konfigurierten OS-Konto.")
    if not known_profile_ids:
        raise ResourceRegistryError("Ressourcenregister benötigt bekannte Profile.")

    resources_payload = payload["resources"]
    if not isinstance(resources_payload, list) or not resources_payload:
        raise ResourceRegistryError("Ressourcenregister benötigt eine Ressourcenliste.")
    resources = tuple(
        _parse_resource(item, known_profile_ids=known_profile_ids)
        for item in resources_payload
    )
    resource_ids = [item.resource_id for item in resources]
    if len(resource_ids) != len(set(resource_ids)):
        raise ResourceRegistryError("Ressourcen-IDs sind nicht eindeutig.")
    defaults = _parse_defaults(
        payload["profile_defaults"],
        resources=resources,
        known_profile_ids=known_profile_ids,
    )
    try:
        return ResourceRegistry(
            os_account=expected_os_account,
            resources=resources,
            profile_defaults=defaults,
            known_profile_ids=known_profile_ids,
        )
    except ValueError as exc:
        raise ResourceRegistryError(str(exc)) from exc


def _parse_resource(
    payload: object,
    *,
    known_profile_ids: frozenset[str],
) -> LogicalResource:
    expected = {
        "resource_id",
        "kind",
        "locator",
        "operations",
        "purposes",
        "profile_ids",
        "cloud_context",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ResourceRegistryError("Ressource besitzt unbekannte Felder oder es fehlen Felder.")
    locator = payload["locator"]
    if not isinstance(locator, dict) or set(locator) != {"type", "path"}:
        raise ResourceRegistryError("Ressourcen-Locator besitzt unbekannte oder fehlende Felder.")
    if locator["type"] != "local_path" or not isinstance(locator["path"], str):
        raise ResourceRegistryError("Ressource benötigt einen lokalen Pfad-Locator.")
    local_path = Path(locator["path"])
    if not local_path.is_absolute():
        raise ResourceRegistryError("Ressource benötigt einen absoluten lokalen Pfad.")
    operations = _string_set(payload["operations"], "Operationen")
    purposes = _string_set(payload["purposes"], "Zwecke")
    profile_ids = _string_set(payload["profile_ids"], "Profile")
    if not profile_ids.issubset(known_profile_ids):
        raise ResourceRegistryError("Ressource verweist auf ein unbekanntes Profil.")
    try:
        resource = LogicalResource(
            resource_id=str(payload["resource_id"]),
            kind=str(payload["kind"]),
            local_path=local_path,
            operations=operations,
            purposes=purposes,
            profile_ids=profile_ids,
            cloud_context=str(payload["cloud_context"]),
        )
    except ValueError as exc:
        raise ResourceRegistryError(str(exc)) from exc
    _validate_local_target(resource)
    return resource


def _parse_defaults(
    payload: object,
    *,
    resources: tuple[LogicalResource, ...],
    known_profile_ids: frozenset[str],
) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict):
        raise ResourceRegistryError("profile_defaults muss ein JSON-Objekt sein.")
    by_id = {item.resource_id: item for item in resources}
    defaults: dict[str, dict[str, str]] = {}
    for profile_id, raw_bindings in payload.items():
        if profile_id not in known_profile_ids:
            raise ResourceRegistryError("profile_defaults verweist auf ein unbekanntes Profil.")
        if not isinstance(raw_bindings, dict):
            raise ResourceRegistryError("Profildefaults müssen ein JSON-Objekt sein.")
        bindings: dict[str, str] = {}
        for purpose, resource_id in raw_bindings.items():
            if not isinstance(purpose, str) or not isinstance(resource_id, str):
                raise ResourceRegistryError("Profildefault benötigt Zweck- und Ressourcen-ID.")
            resource = by_id.get(resource_id)
            if resource is None:
                raise ResourceRegistryError("Profildefault verweist auf eine unbekannte Ressource.")
            if profile_id not in resource.profile_ids or purpose not in resource.purposes:
                raise ResourceRegistryError("Profildefault verletzt Profil- oder Zweckbindung.")
            bindings[purpose] = resource_id
        defaults[profile_id] = bindings
    return defaults


def _string_set(value: object, label: str) -> frozenset[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ResourceRegistryError(f"{label} müssen eine nichtleere Textliste sein.")
    if len(value) != len(set(value)):
        raise ResourceRegistryError(f"{label} dürfen keine Duplikate enthalten.")
    return frozenset(value)


def _validate_local_target(resource: LogicalResource) -> None:
    path = resource.local_path
    if resource.kind in {"directory", "local_calendar"}:
        if not path.is_dir():
            raise ResourceRegistryError(f"Konfiguriertes Verzeichnis fehlt: {resource.resource_id}")
        return
    if resource.kind == "file" and "read" in resource.operations and not path.is_file():
        raise ResourceRegistryError(f"Konfigurierte Datei fehlt: {resource.resource_id}")
    if resource.kind in {"file", "sqlite_store"} and not path.parent.is_dir():
        raise ResourceRegistryError(
            f"Elternverzeichnis der Ressource fehlt: {resource.resource_id}"
        )
