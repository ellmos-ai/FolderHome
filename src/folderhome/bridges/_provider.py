"""Shared verification and import helpers for pinned Python provider checkouts."""

from __future__ import annotations

import importlib
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from folderhome.contracts import PluginDescriptor


class ProviderCheckoutError(RuntimeError):
    """Raised when a provider checkout cannot prove its declared identity."""


def load_pinned_python_modules(
    *,
    plugin: PluginDescriptor,
    provider_root: Path,
    package_name: str,
    module_names: Iterable[str] = (),
    import_from_parent: bool = False,
) -> dict[str, ModuleType]:
    """Verify one clean Git checkout and import only the requested package modules."""

    provider_root = provider_root.resolve()
    _verify_checkout(plugin, provider_root)
    import_root = provider_root.parent if import_from_parent else provider_root
    with _import_path(import_root, package_name, provider_root):
        package = importlib.import_module(package_name)
        modules = {package_name: package}
        modules.update(
            (module_name, importlib.import_module(module_name))
            for module_name in module_names
        )
    package_path = Path(package.__file__ or "").resolve()
    if not package_path.is_relative_to(provider_root):
        raise ProviderCheckoutError(
            f"Geladener Provider liegt nicht im gepinnten Checkout: {package_path}"
        )
    actual_version = getattr(package, "__version__", None)
    if actual_version is None:
        actual_version = _declared_project_version(provider_root)
    if actual_version != plugin.version:
        raise ProviderCheckoutError(
            f"Provider-Version stimmt nicht mit dem Manifest überein: "
            f"erwartet {plugin.version}, gefunden {actual_version!r}"
        )
    return modules


def _declared_project_version(provider_root: Path) -> str | None:
    pyproject = provider_root / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        with pyproject.open("rb") as handle:
            payload = tomllib.load(handle)
        version = payload.get("project", {}).get("version")
    except (OSError, tomllib.TOMLDecodeError, AttributeError):
        return None
    return version if isinstance(version, str) else None


def _verify_checkout(plugin: PluginDescriptor, provider_root: Path) -> None:
    verify_checkout_revision(provider_root, plugin.source_revision)


def verify_checkout_revision(provider_root: Path, expected_revision: str) -> None:
    """Prove that a local provider checkout is at one clean expected revision."""

    if not provider_root.is_dir():
        raise ProviderCheckoutError(f"Provider-Checkout fehlt: {provider_root}")
    revision = _run_git(provider_root, "rev-parse", "HEAD")
    if revision != expected_revision:
        raise ProviderCheckoutError(
            "Provider-Git-Revision stimmt nicht mit dem Manifest überein: "
            f"erwartet {expected_revision}, gefunden {revision}"
        )
    dirty = _run_git(provider_root, "status", "--porcelain")
    if dirty:
        raise ProviderCheckoutError(
            "Der gepinnte Provider-Checkout enthält lokale Änderungen und wird nicht geladen."
        )


def _run_git(repository: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise ProviderCheckoutError(
            f"Git konnte für den Provider nicht gestartet werden: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unbekannter Git-Fehler"
        raise ProviderCheckoutError(f"Provider-Checkout konnte nicht geprüft werden: {detail}")
    return completed.stdout.strip()


@contextmanager
def _import_path(
    import_root: Path,
    package_name: str,
    provider_root: Path,
) -> Iterator[None]:
    existing = sys.modules.get(package_name)
    if existing is not None:
        existing_path = Path(existing.__file__ or "").resolve()
        if not existing_path.is_relative_to(provider_root):
            raise ProviderCheckoutError(
                f"Ein anderer {package_name}-Provider ist bereits geladen: {existing_path}"
            )
    root_text = str(import_root)
    sys.path.insert(0, root_text)
    try:
        yield
    finally:
        if sys.path and sys.path[0] == root_text:
            sys.path.pop(0)
