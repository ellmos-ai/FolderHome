"""Contracts for private logical resources exposed to agents only by ID."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_PURPOSE = re.compile(r"[a-z][a-z0-9_.-]{2,127}")
RESOURCE_KINDS = frozenset({"directory", "file", "sqlite_store", "local_calendar"})
RESOURCE_OPERATIONS = frozenset(
    {
        "read",
        "sensitive_read",
        "list",
        "create",
        "append",
        "update",
        "move",
        "recycle",
        "state_write",
    }
)
CLOUD_CONTEXT_POLICIES = frozenset(
    {"deny", "synthetic_only", "minimized_with_approval"}
)


class ResourceRegistryError(ValueError):
    """Raised when a resource declaration or resolution is not trustworthy."""


@dataclass(frozen=True, slots=True)
class LogicalResource:
    """One local resource whose physical locator never reaches the model."""

    resource_id: str
    kind: str
    local_path: Path
    operations: frozenset[str]
    purposes: frozenset[str]
    profile_ids: frozenset[str]
    cloud_context: str

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.resource_id) is None:
            raise ValueError("resource_id muss eine stabile Kleinbuchstaben-ID sein.")
        if self.kind not in RESOURCE_KINDS:
            raise ValueError(f"Unbekannte Ressourcenart: {self.kind}")
        if not self.local_path.is_absolute():
            raise ValueError("Ressource benötigt einen absoluten lokalen Pfad.")
        object.__setattr__(self, "local_path", self.local_path.resolve())
        if not self.operations or not self.operations.issubset(RESOURCE_OPERATIONS):
            raise ValueError("Ressource besitzt unbekannte oder leere Operationen.")
        if not self.purposes or any(_PURPOSE.fullmatch(item) is None for item in self.purposes):
            raise ValueError("Ressource benötigt gültige Zweck-IDs.")
        if not self.profile_ids or any(_ID.fullmatch(item) is None for item in self.profile_ids):
            raise ValueError("Ressource benötigt gültige Profil-IDs.")
        if self.cloud_context not in CLOUD_CONTEXT_POLICIES:
            raise ValueError("Ressource besitzt eine unbekannte Cloud-Kontextregel.")

    def to_public_dict(self) -> dict[str, object]:
        """Return model-safe metadata without account or path material."""

        return {
            "resource_id": self.resource_id,
            "kind": self.kind,
            "operations": sorted(self.operations),
            "purposes": sorted(self.purposes),
            "cloud_context": self.cloud_context,
            "path_disclosed": False,
        }


@dataclass(frozen=True, slots=True)
class ResourceRegistry:
    """Validated resources and profile-specific defaults for one OS account."""

    os_account: str
    resources: tuple[LogicalResource, ...]
    profile_defaults: dict[str, dict[str, str]]
    known_profile_ids: frozenset[str]

    SCHEMA = "folderhome.resource-registry.v1"

    def __post_init__(self) -> None:
        if not self.os_account.strip() or not self.known_profile_ids:
            raise ValueError("Ressourcenregister benötigt OS-Konto und Profile.")
        resource_ids = [item.resource_id for item in self.resources]
        if not resource_ids or len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Ressourcen-IDs müssen vorhanden und eindeutig sein.")

    def resolve_default(
        self,
        *,
        profile_id: str,
        purpose: str,
        required_kind: str,
        required_operations: frozenset[str],
    ) -> LogicalResource:
        """Resolve one default and verify profile, purpose, kind and least privilege."""

        if profile_id not in self.known_profile_ids:
            raise ResourceRegistryError(f"Unbekanntes Profil: {profile_id}")
        try:
            resource_id = self.profile_defaults[profile_id][purpose]
        except KeyError as exc:
            raise ResourceRegistryError(
                f"Kein Ressourcen-Default für Profil {profile_id} und Zweck {purpose}."
            ) from exc
        resource = next(item for item in self.resources if item.resource_id == resource_id)
        if profile_id not in resource.profile_ids or purpose not in resource.purposes:
            raise ResourceRegistryError(
                "Ressourcen-Default verletzt Profil- oder Zweckbindung."
            )
        if resource.kind != required_kind:
            raise ResourceRegistryError(
                f"Ressource {resource.resource_id} besitzt Art {resource.kind} "
                f"statt {required_kind}."
            )
        missing = sorted(required_operations.difference(resource.operations))
        if missing:
            raise ResourceRegistryError(
                f"Operation {missing[0]} ist für Ressource {resource.resource_id} nicht erlaubt."
            )
        return resource

    def resolve(
        self,
        *,
        resource_id: str,
        profile_id: str,
        purpose: str,
        required_kind: str,
        required_operations: frozenset[str],
    ) -> LogicalResource:
        """Resolve one named resource with the same least-privilege checks as defaults."""

        if profile_id not in self.known_profile_ids:
            raise ResourceRegistryError(f"Unbekanntes Profil: {profile_id}")
        resource = next(
            (item for item in self.resources if item.resource_id == resource_id),
            None,
        )
        if resource is None:
            raise ResourceRegistryError(f"Unbekannte Ressourcen-ID: {resource_id}")
        if profile_id not in resource.profile_ids or purpose not in resource.purposes:
            raise ResourceRegistryError(
                "Ressource verletzt die konfigurierte Profil- oder Zweckbindung."
            )
        if resource.kind != required_kind:
            raise ResourceRegistryError(
                f"Ressource {resource.resource_id} besitzt Art {resource.kind} "
                f"statt {required_kind}."
            )
        missing = sorted(required_operations.difference(resource.operations))
        if missing:
            raise ResourceRegistryError(
                f"Operation {missing[0]} ist für Ressource {resource.resource_id} nicht erlaubt."
            )
        return resource

    def to_public_dict(self, *, profile_id: str) -> dict[str, object]:
        """Expose only resources visible to an organizational profile."""

        if profile_id not in self.known_profile_ids:
            raise ResourceRegistryError(f"Unbekanntes Profil: {profile_id}")
        visible = [
            item.to_public_dict()
            for item in sorted(self.resources, key=lambda value: value.resource_id)
            if profile_id in item.profile_ids
        ]
        return {
            "schema": "folderhome.logical-resource-catalog.v1",
            "profile_id": profile_id,
            "security_boundary": "operating_system_account",
            "profiles_are_authorization_boundaries": False,
            "paths_disclosed": False,
            "resources": visible,
            "defaults": dict(sorted(self.profile_defaults.get(profile_id, {}).items())),
        }
