"""Read-only, revision-pinned bridge to the law-checker source registry."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from folderhome.bridges._provider import ProviderCheckoutError, verify_checkout_revision
from folderhome.contracts import PluginDescriptor


class LawCheckerBridgeError(RuntimeError):
    """Raised when the law-checker checkout or registry cannot be trusted."""


class LawCheckerBridge:
    """Qualify law-checker metadata without importing its agent workflow."""

    def __init__(self, *, plugin: PluginDescriptor, provider_root: Path) -> None:
        if plugin.plugin_id != "law-checker":
            raise LawCheckerBridgeError("Rechtsbrücke benötigt das law-checker-Manifest.")
        self.plugin = plugin
        self.provider_root = provider_root.resolve()
        try:
            verify_checkout_revision(self.provider_root, plugin.source_revision)
            self._project = self._read_toml(self.provider_root / "pyproject.toml")
            self._module = self._read_json(self.provider_root / "ellmos-module.v2.json")
            self._config = self._read_json(self.provider_root / "config.json")
            self._validate_identity()
        except (ProviderCheckoutError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            raise LawCheckerBridgeError(str(exc)) from exc

    @property
    def provider_id(self) -> str:
        return self.plugin.plugin_id

    @property
    def provider_revision(self) -> str:
        return self.plugin.source_revision

    def qualification(self) -> dict[str, object]:
        registry = self._registry()
        return {
            "schema": "folderhome.law-checker-qualification.v1",
            "provider_id": self.provider_id,
            "provider_version": self.plugin.version,
            "provider_revision": self.provider_revision,
            "module_id": self._module["id"],
            "registry_version": self._config["version"],
            "active_registry_keys": sorted(
                key for key, value in registry.items() if value.get("enabled") is True
            ),
            "provides": sorted(self._module["provides"]),
            "legal_review_api_available": False,
            "registry_and_source_metadata_only": True,
            "network_invoked": False,
        }

    def require_registry_key(self, key: str) -> dict[str, object]:
        entry = self._registry().get(key)
        if not isinstance(entry, dict):
            raise LawCheckerBridgeError(
                f"Gesetz {key!r} ist im gepinnten law-checker nicht registriert."
            )
        if entry.get("enabled") is not True:
            raise LawCheckerBridgeError(
                f"Gesetz {key!r} ist im gepinnten law-checker nicht aktiviert."
            )
        return dict(entry)

    def _validate_identity(self) -> None:
        project = self._project.get("project")
        if not isinstance(project, dict):
            raise ValueError("law-checker-pyproject besitzt kein project-Objekt.")
        if project.get("name") != "law-checker" or project.get("version") != self.plugin.version:
            raise ValueError("law-checker-Name oder Version stimmt nicht mit dem Manifest überein.")
        if self._module.get("schema") != "ellmos.module.v2" or self._module.get("id") != (
            "rechtsabteilung"
        ):
            raise ValueError("law-checker-Modulmanifest besitzt eine unbekannte Identität.")
        provides = self._module.get("provides")
        if not isinstance(provides, list) or not {
            "domain.legal.orientation",
            "domain.legal.sources",
        }.issubset(provides):
            raise ValueError("law-checker-Modulmanifest deklariert die Quellenfunktion nicht.")
        version = self._config.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("law-checker-Registry besitzt keine gültige Version.")
        self._registry()

    def _registry(self) -> dict[str, dict[str, object]]:
        registry = self._config.get("gesetzbuecher")
        if not isinstance(registry, dict) or not registry:
            raise ValueError("law-checker-Registry ist leer oder unbekannt.")
        if not all(
            isinstance(key, str) and isinstance(value, dict)
            for key, value in registry.items()
        ):
            raise ValueError("law-checker-Registry besitzt ungültige Einträge.")
        return registry

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Providerdatei muss ein JSON-Objekt sein: {path}")
        return payload

    @staticmethod
    def _read_toml(path: Path) -> dict[str, object]:
        with path.open("rb") as handle:
            return tomllib.load(handle)
