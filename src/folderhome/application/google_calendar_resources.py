"""Shared current account/resource binding for creation and reference-based mutations."""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from folderhome.application.calendar_connectors import parse_calendar_connector_accounts
from folderhome.application.calendar_handoff import (
    parse_calendar_configuration,
    resolve_calendar_preferences,
)
from folderhome.application.profile_rules import parse_profile_configuration, resolve_profile_policy
from folderhome.application.resource_registry import parse_resource_registry
from folderhome.application.workflow_execution import _canonical_json, _require_separate_resources
from folderhome.contracts.calendar import CalendarBackend

RESOURCE_REQUIREMENTS = {
    "source_resource_id": ("calendar.source", "directory", {"read", "list"}),
    "configuration_resource_id": ("calendar.configuration", "file", {"read"}),
    "accounts_resource_id": ("calendar.connector_accounts", "file", {"read"}),
    "credential_resource_id": ("calendar.google_credentials", "file", {"read"}),
    "ledger_resource_id": ("calendar.connector_ledger", "directory", {"read", "state_write"}),
}


@dataclass(frozen=True)
class GoogleCalendarResources:
    account: object
    policy: object
    configuration: object
    timezone: str
    source_path: Path | None
    credential_path: Path
    ledger_path: Path
    binding_sha256: str
    snapshots: tuple
    profile_files: tuple


def verify_snapshots(context, profiles_dir, load):
    if context.profile_files != tuple(sorted(profiles_dir.glob("*.json"))) or any(
        load(path)[0] != raw for path, raw in context.snapshots
    ):
        raise ValueError("Configuration changed during preparation")


def resolve_google_calendar_resources(adapter, profile_id, request, *, include_source, load):
    snapshots = {}

    def document(path):
        raw, payload = load(path)
        snapshots[path] = raw
        return payload

    registry = adapter._registry
    if adapter._registry_file is not None:
        registry = parse_resource_registry(
            document(adapter._registry_file),
            expected_os_account=registry.os_account,
            known_profile_ids=registry.known_profile_ids,
        )
        additions = []
        for item in adapter._launch_resources:
            if any(current.resource_id == item.resource_id for current in registry.resources):
                continue
            profiles = item.profile_ids
            for current in registry.resources:
                if current.purposes & item.purposes:
                    profiles = profiles - current.profile_ids
            if profiles:
                additions.append(replace(item, profile_ids=profiles))
        registry = replace(registry, resources=registry.resources + tuple(additions))

    resources = {}
    for key, (purpose, kind, operations) in RESOURCE_REQUIREMENTS.items():
        if key == "source_resource_id" and not include_source:
            continue
        required = set(operations)
        if key == "source_resource_id" and request["allow_sensitive_local_read"]:
            required.add("sensitive_read")
        resources[key] = registry.resolve(
            resource_id=request[key],
            profile_id=profile_id,
            purpose=purpose,
            required_kind=kind,
            required_operations=frozenset(required),
        )
    source = resources["source_resource_id"].local_path if include_source else None
    ledger = resources["ledger_resource_id"].local_path
    credential = resources["credential_resource_id"].local_path
    if source is not None:
        _require_separate_resources(source, ledger)
        _require_separate_resources(source, credential)
    _require_separate_resources(ledger, credential)
    profile_files = tuple(sorted(adapter._profiles_dir.glob("*.json")))
    household = adapter._profiles_dir / "household.json"
    profiles = parse_profile_configuration(
        document(household),
        {
            path.name: document(path)
            for path in profile_files
            if path.name.casefold() != "household.json"
        },
    )
    if profiles.os_account != registry.os_account:
        raise ValueError("Profile and resource account differ")
    configuration_path = resources["configuration_resource_id"].local_path
    configuration = parse_calendar_configuration(
        document(configuration_path),
        config_path=configuration_path,
    )
    accounts = parse_calendar_connector_accounts(
        document(resources["accounts_resource_id"].local_path)
    )
    account = next(item for item in accounts if item.account_id == request["account_id"])
    if (
        account.profile_id != profile_id
        or account.provider_id != "google-calendar"
        or account.provider_revision != "v3"
        or account.calendar_id == "primary"
        or account.credential_ref
        != "connector://google-calendar/" + request["credential_resource_id"]
    ):
        raise ValueError("Invalid Google account binding")
    policy = resolve_profile_policy(profiles, profile_id=profile_id, area=request["area"])
    backend, _, timezone, _ = resolve_calendar_preferences(configuration, policy)
    if backend is not CalendarBackend.GOOGLE:
        raise ValueError("Profile does not select Google")
    binding = {
        "files": [(str(path), sha256(raw).hexdigest()) for path, raw in snapshots.items()],
        "resources": [
            {
                "id": item.resource_id,
                "path": str(item.local_path),
                "operations": sorted(item.operations),
                "profiles": sorted(item.profile_ids),
                "purposes": sorted(item.purposes),
                "kind": item.kind,
                "cloud_context": item.cloud_context,
            }
            for item in resources.values()
        ],
    }
    context = GoogleCalendarResources(
        account,
        policy,
        configuration,
        timezone,
        source,
        credential,
        ledger / "google-calendar.sqlite3",
        sha256(_canonical_json(binding)).hexdigest(),
        tuple(snapshots.items()),
        profile_files,
    )
    verify_snapshots(context, adapter._profiles_dir, load)
    return context
