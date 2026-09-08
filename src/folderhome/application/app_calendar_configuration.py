"""Bind explicitly launched calendar files to private logical resources, read-only."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from folderhome.application.calendar_connectors import parse_calendar_connector_accounts
from folderhome.application.calendar_handoff import (
    CalendarConfiguration,
    parse_calendar_configuration,
)
from folderhome.contracts.resources import LogicalResource, ResourceRegistry

_MAX_CONFIGURATION_BYTES = 65_536


def read_calendar_document(path: Path) -> dict[str, object]:
    # A launch is not permission to follow a replaced file or read an unbounded secret.
    if path.is_symlink() or not path.is_file():
        raise ValueError("Kalenderdatei fehlt oder ist ein Link.")
    with path.open("rb") as handle:
        content = handle.read(_MAX_CONFIGURATION_BYTES + 1)
    if len(content) > _MAX_CONFIGURATION_BYTES:
        raise ValueError("Kalenderdatei überschreitet das Konfigurationsbudget.")
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Kalenderdatei muss ein Objekt sein.")
    return payload


def read_app_calendar_configuration(path: Path) -> CalendarConfiguration:
    """Use one strict file contract for app startup and setup reload."""
    payload = read_calendar_document(path)
    if set(payload) != {
        "schema",
        "default_backend",
        "default_timezone",
        "uptoday_ics_directory",
    }:
        raise ValueError("Kalenderkonfiguration besitzt unbekannte oder fehlende Felder.")
    return parse_calendar_configuration(payload, config_path=path.resolve())


def bind_app_calendar_resources(
    registry: ResourceRegistry | None,
    *,
    calendar_config: Path | None,
    connector_accounts: Path | None,
    state_dir: Path,
    os_account: str,
    profile_ids: frozenset[str],
) -> ResourceRegistry | None:
    """Fill missing defaults without replacing explicit private bindings or writing files.

    Loading an external account does not construct a gateway or grant any network
    permission. The running calendar adapter still checks its supported backend.
    """

    if calendar_config is None and connector_accounts is None:
        return registry
    resources = list(registry.resources) if registry is not None else []
    defaults = (
        {key: dict(value) for key, value in registry.profile_defaults.items()}
        if registry is not None
        else {}
    )

    def bind(
        path: Path,
        purpose: str,
        kind: str,
        operations: frozenset[str],
        visible_profiles: frozenset[str],
    ) -> None:
        # A declared resource without a default still expresses a boundary.
        # Reuse its exact permissions; never create a more powerful fallback.
        for profile in sorted(visible_profiles):
            if purpose in defaults.get(profile, {}):
                continue
            candidates = [
                item
                for item in resources
                if profile in item.profile_ids and purpose in item.purposes
            ]
            if len(candidates) > 1:
                raise ValueError("Mehrdeutige Kalenderressourcen benötigen einen Default.")
            if candidates:
                defaults.setdefault(profile, {})[purpose] = candidates[0].resource_id
        missing = frozenset(
            profile for profile in visible_profiles if purpose not in defaults.get(profile, {})
        )
        if not missing:
            return
        path = path.resolve()
        material = json.dumps([str(path), purpose, sorted(missing)], sort_keys=True)
        prefix = "launch_calendar_" + sha256(material.encode()).hexdigest()[:32]
        resource_id = prefix
        used = {item.resource_id for item in resources}
        suffix = 1
        while resource_id in used:
            resource_id = f"{prefix}_{suffix}"
            suffix += 1
        resources.append(
            LogicalResource(
                resource_id=resource_id,
                kind=kind,
                local_path=path,
                operations=operations,
                purposes=frozenset({purpose}),
                profile_ids=missing,
                cloud_context="deny",
            )
        )
        for profile in missing:
            defaults.setdefault(profile, {})[purpose] = resource_id

    try:
        if calendar_config is not None:
            read_app_calendar_configuration(calendar_config)
            bind(
                calendar_config, "calendar.configuration", "file", frozenset({"read"}), profile_ids
            )
            bind(
                state_dir,
                "calendar.state",
                "local_calendar",
                frozenset({"read", "state_write"}),
                profile_ids,
            )
        if connector_accounts is not None:
            accounts = parse_calendar_connector_accounts(read_calendar_document(connector_accounts))
            account_profiles = frozenset(item.profile_id for item in accounts)
            if not account_profiles <= profile_ids:
                raise ValueError("Kalenderkonto verweist auf ein unbekanntes Profil.")
            bind(
                connector_accounts,
                "calendar.connector_accounts",
                "file",
                frozenset({"read"}),
                account_profiles,
            )
    except (OSError, ValueError, RuntimeError) as exc:
        # Parser diagnostics can contain private file paths or account values.
        raise ValueError("Explizite Kalenderkonfiguration ist ungültig oder nicht lesbar.") from exc
    return ResourceRegistry(
        os_account=os_account,
        resources=tuple(resources),
        profile_defaults=defaults,
        known_profile_ids=profile_ids,
    )
