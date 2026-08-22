"""Read-only probes for the pinned HungryCall and Ringedingeding plugins."""

from __future__ import annotations

from pathlib import Path

from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
)
from folderhome.contracts import CallPluginProbeResult, PluginDescriptor


class CallPluginBridgeError(RuntimeError):
    """Raised when a pinned calling plugin cannot prove its dry-run boundary."""


class CallPluginBridge:
    """Import only local dry-run seams after revision and cleanliness checks."""

    def __init__(self, *, plugin: PluginDescriptor, provider_root: Path) -> None:
        self._plugin = plugin
        self._provider_root = provider_root.resolve()

    def probe(self) -> CallPluginProbeResult:
        """Verify a provider without constructing or invoking any live transport."""

        try:
            if self._plugin.plugin_id == "hungrycall":
                modules = load_pinned_python_modules(
                    plugin=self._plugin,
                    provider_root=self._provider_root,
                    package_name="hungrycall",
                    module_names=("hungrycall.engine", "hungrycall.call_client"),
                )
                client = modules["hungrycall.call_client"].DryRunCallClient()
                if client.__class__.__name__ != "DryRunCallClient":
                    raise CallPluginBridgeError("HungryCall-Dry-Run-Client fehlt.")
                pattern = "sequential_early_stop"
            elif self._plugin.plugin_id == "ringedingeding":
                modules = load_pinned_python_modules(
                    plugin=self._plugin,
                    provider_root=self._provider_root,
                    package_name="ringedingeding",
                    module_names=(
                        "ringedingeding.runner",
                        "ringedingeding.transports.fixture",
                    ),
                )
                transport = modules[
                    "ringedingeding.transports.fixture"
                ].FixtureTransport({})
                if transport.is_live:
                    raise CallPluginBridgeError(
                        "Ringedingeding-Fixturetransport meldet unerwartet live."
                    )
                pattern = "group_poll"
            else:
                raise CallPluginBridgeError(
                    f"Nicht unterstütztes Call-Plugin: {self._plugin.plugin_id}"
                )
        except ProviderCheckoutError as exc:
            raise CallPluginBridgeError(str(exc)) from exc
        except CallPluginBridgeError:
            raise
        except Exception as exc:
            raise CallPluginBridgeError(
                f"Call-Plugin-Probe fehlgeschlagen: {exc}"
            ) from exc
        return CallPluginProbeResult(
            plugin_id=self._plugin.plugin_id,
            source_revision=self._plugin.source_revision,
            provider_root=self._provider_root,
            pattern=pattern,
            runtime_imported=True,
            dry_run_available=True,
        )
