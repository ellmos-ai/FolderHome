"""Plugin manifest loading and validation."""

import re
import tomllib
from pathlib import Path

from folderhome.contracts import CapabilityDescriptor, PluginDescriptor, SideEffect


class ManifestValidationError(ValueError):
    """Raised when a plugin manifest cannot be trusted."""


def load_manifests(directory: Path) -> tuple[PluginDescriptor, ...]:
    """Load component manifests in deterministic filename order."""

    plugins: list[PluginDescriptor] = []
    plugin_ids: set[str] = set()
    for path in sorted(directory.glob("*.toml")):
        plugin = _load_manifest(path)
        if plugin.plugin_id in plugin_ids:
            raise ManifestValidationError(f"Duplicate plugin id {plugin.plugin_id}")
        plugin_ids.add(plugin.plugin_id)
        plugins.append(plugin)
    return tuple(plugins)


def _load_manifest(path: Path) -> PluginDescriptor:
    with path.open("rb") as handle:
        payload = tomllib.load(handle)

    schema = payload.get("schema")
    if schema != "folderhome.component-manifest.v1":
        raise ManifestValidationError(f"Unsupported schema {schema!r} in {path.name}")
    required_fields = {
        "id",
        "name",
        "version",
        "license",
        "interface_version",
        "classification",
        "default_mode",
        "live_enabled",
        "source",
        "capabilities",
    }
    missing = sorted(required_fields.difference(payload))
    if missing:
        raise ManifestValidationError(
            f"Missing required field {missing[0]!r} in {path.name}"
        )
    source = payload["source"]
    missing_source = sorted({"repository", "revision"}.difference(source))
    if missing_source:
        raise ManifestValidationError(
            f"Missing required field source.{missing_source[0]} in {path.name}"
        )
    if re.fullmatch(r"[0-9a-fA-F]{40}", source["revision"]) is None:
        raise ManifestValidationError(
            f"source.revision must be a 40-character Git commit in {path.name}"
        )
    if payload["live_enabled"] is not False:
        raise ManifestValidationError(
            f"live_enabled must be false in the foundation host: {path.name}"
        )
    if payload["default_mode"] != "dry-run":
        raise ManifestValidationError(
            f"default_mode must be dry-run in the foundation host: {path.name}"
        )
    try:
        capabilities = tuple(
            CapabilityDescriptor(
                capability_id=item["id"],
                title=item["title"],
                side_effects=tuple(SideEffect(value) for value in item["side_effects"]),
                dry_run_supported=item["dry_run_supported"],
                gate_required=item["gate_required"],
            )
            for item in payload["capabilities"]
        )
    except ValueError as exc:
        invalid_value = str(exc).split(":", maxsplit=1)[0]
        raise ManifestValidationError(
            f"Unknown side effect {invalid_value} in {path.name}"
        ) from exc
    for capability in capabilities:
        if capability.side_effects and not (
            capability.dry_run_supported and capability.gate_required
        ):
            raise ManifestValidationError(
                f"Capability {capability.capability_id} must support dry-run and require a gate"
            )
    return PluginDescriptor(
        plugin_id=payload["id"],
        name=payload["name"],
        version=payload["version"],
        source_repository=source["repository"],
        source_revision=source["revision"],
        license_id=payload["license"],
        interface_version=payload["interface_version"],
        capabilities=capabilities,
        classification=payload["classification"],
        default_mode=payload["default_mode"],
        live_enabled=payload["live_enabled"],
    )
