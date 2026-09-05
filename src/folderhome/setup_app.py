"""Separate loopback installer that is the only place writing FolderHome config.

The app GUI never writes configuration. This second application does, on its own
port, with its own token and behind the same explicit listener gate. It plans
first, shows the exact file contents, and writes only after the browser confirms
that exact plan by its hash.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
from datetime import UTC, datetime
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from folderhome.application.profile_rules import ProfileConfiguration
from folderhome.application.resource_registry import (
    default_resource_registry_path,
    load_resource_registry,
)
from folderhome.contracts.local_app import LocalApiResponse, LocalAppSettings
from folderhome.contracts.resources import ResourceRegistryError
from folderhome.contracts.strands_agent import StrandsAgentSettings

# One explicit table instead of guessing from name suffixes: `calendar.export_output`
# ends in `_output`, not `.output`, and silently got no operations at all.
_PURPOSE_OPERATIONS: dict[str, tuple[str, ...]] = {
    "documents.source": ("list", "read"),
    "insurance.source": ("list", "read"),
    "documents.output": ("create",),
    "correspondence.output": ("create",),
    "calendar.export_output": ("create",),
}
SETUP_PURPOSES = tuple(_PURPOSE_OPERATIONS)
# A folder we write into is a folder that stays here.
_OUTPUT_PURPOSES = frozenset(
    purpose for purpose, operations in _PURPOSE_OPERATIONS.items() if "create" in operations
)
LAUNCH_CONFIG_SCHEMA = "folderhome.launch-config.v1"


class SetupAppError(RuntimeError):
    """Raised when the installer boundary cannot be established safely."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


# The browser deliberately cannot hand over an absolute path, so the folder is
# chosen by the operating system itself, in a short-lived child process.
_PICK_FOLDER_TIMEOUT_SECONDS = 300
_PICK_FOLDER_SCRIPT = """
import sys
import tkinter
import tkinter.filedialog

root = tkinter.Tk()
root.withdraw()
root.attributes("-topmost", True)
chosen = tkinter.filedialog.askdirectory(initialdir=sys.argv[1], mustexist=True)
root.destroy()
print(chosen or "")
"""


def default_config_dir(*, environ: dict[str, str] | None = None) -> Path:
    """Return the per-OS-account FolderHome configuration directory."""

    return default_resource_registry_path(environ=environ).parent


class SetupApplication:
    """Plan and write `resources.json` and `launch.json` for one OS account."""

    def __init__(
        self,
        *,
        settings: LocalAppSettings,
        profiles: ProfileConfiguration,
        config_dir: Path,
        session_token: str | None = None,
    ) -> None:
        token = session_token or secrets.token_urlsafe(32)
        if len(token) < 32:
            raise SetupAppError("Lokales Sitzungstoken ist zu kurz.")
        self.settings = settings
        self.profiles = profiles
        self.config_dir = config_dir.resolve()
        self.session_token = token
        self._lock = threading.RLock()
        self._dialog_lock = threading.Lock()
        self._asset_root = Path(__file__).parent / "setup_ui"

    # ------------------------------------------------------------------ paths
    @property
    def resources_file(self) -> Path:
        return self.config_dir / "resources.json"

    @property
    def launch_file(self) -> Path:
        return self.config_dir / "launch.json"

    # ------------------------------------------------------------------ plans
    def state_payload(self) -> dict[str, Any]:
        """Describe what the installer can configure and what is configured now."""

        return {
            "schema": "folderhome.setup-state.v1",
            "os_account": self.profiles.os_account,
            "profiles": [
                {"profile_id": item.profile_id, "display_name": item.display_name}
                for item in sorted(
                    self.profiles.profiles, key=lambda value: value.profile_id
                )
            ],
            "purposes": list(SETUP_PURPOSES),
            "repeatable_purposes": [
                purpose for purpose in SETUP_PURPOSES if purpose not in _OUTPUT_PURPOSES
            ],
            "model_providers": ["fixture", "ollama", "bedrock"],
            "config_dir": str(self.config_dir),
            "resources_file": str(self.resources_file),
            "launch_file": str(self.launch_file),
            "home": str(Path.home().resolve()),
            "profiles_dir": str(self.settings.profiles_dir),
            "configured": self.resources_file.is_file(),
            "current_folders": self._current_folders(),
            "writes_credentials": False,
        }

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        """Build both file contents and their hash without touching the disk."""

        errors: list[dict[str, str]] = []
        folders = _folder_entries(request, self.profiles, errors)
        model = _model_settings(request, errors)
        port = _port(request, errors)
        state_dir = _directory(request.get("state_dir"), "state_dir", errors)
        profiles_dir = _directory(
            request.get("profiles_dir") or str(self.settings.profiles_dir),
            "profiles_dir",
            errors,
        )
        for entry in folders:
            _check_folder(entry, errors)
        if not errors and state_dir is not None and profiles_dir is not None:
            # The app would reject an overlap only at start-up; catch it here.
            try:
                LocalAppSettings(
                    host="127.0.0.1",
                    port=port,
                    profiles_dir=profiles_dir,
                    state_dir=state_dir,
                )
            except ValueError as exc:
                errors.append({"field": "state_dir", "message": str(exc)})
        resources_json = (
            _resources_document(self.profiles.os_account, folders) if folders else None
        )
        launch_json = (
            None
            if errors
            else _launch_document(
                profiles_dir=profiles_dir,
                state_dir=state_dir,
                resources_file=self.resources_file if folders else None,
                model=model,
                port=port,
            )
        )
        payload: dict[str, Any] = {
            "schema": "folderhome.setup-plan.v1",
            "valid": not errors and resources_json is not None,
            "errors": errors,
            "targets": {
                "resources_file": str(self.resources_file),
                "launch_file": str(self.launch_file),
            },
            "resources_json": resources_json,
            "launch_json": launch_json,
            "written": False,
            "side_effects": [],
        }
        if not folders and not errors:
            payload["errors"] = [
                {"field": "folders", "message": "Mindestens ein Ordner wird benötigt."}
            ]
            payload["valid"] = False
        payload["launch_command"] = _launch_command(self.launch_file, model)
        payload["plan_sha256"] = _plan_digest(payload)
        return payload

    def save(self, request: dict[str, Any]) -> dict[str, Any]:
        """Write both files atomically after an exact, confirmed plan."""

        if request.get("confirm") is not True:
            raise SetupAppError("Speichern benötigt eine ausdrückliche Bestätigung.")
        supplied = request.get("plan_sha256")
        if not isinstance(supplied, str) or len(supplied) != 64:
            raise SetupAppError("Speichern benötigt den Hash des geprüften Plans.")
        plan = self.plan(request)
        if not plan["valid"]:
            raise SetupAppError("Plan ist nicht gültig; erst die Fehler beheben.")
        if not hmac.compare_digest(supplied, str(plan["plan_sha256"])):
            raise SetupAppError("Plan-Hash stimmt nicht mit der geprüften Fassung überein.")
        with self._lock:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # Stage both files, load the staged registry, and only then replace the
            # live ones. A refused plan leaves the previous state exactly as it was.
            staged: list[tuple[Path, Path]] = []
            try:
                staged.append(
                    (
                        _stage_json(self.resources_file, plan["resources_json"]),
                        self.resources_file,
                    )
                )
                staged.append(
                    (_stage_json(self.launch_file, plan["launch_json"]), self.launch_file)
                )
                self._verify_registry(staged[0][0])
            except BaseException:
                for temporary, _target in staged:
                    temporary.unlink(missing_ok=True)
                raise
            written = [_commit_staged(temporary, target) for temporary, target in staged]
        plan["written"] = True
        plan["backups"] = [str(item) for item in written if item is not None]
        plan["side_effects"] = ["file.create", "file.update"]
        return plan

    def pick_folder(self) -> dict[str, Any]:
        """Let the operating system name one folder; typing a path stays possible."""

        if find_spec("tkinter") is None:
            raise SetupAppError(
                "Der Verzeichnisdialog braucht tkinter; bitte den Pfad von Hand eingeben.",
                status_code=501,
            )
        if not self._dialog_lock.acquire(blocking=False):
            raise SetupAppError(
                "Es ist bereits ein Verzeichnisdialog offen.", status_code=409
            )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", _PICK_FOLDER_SCRIPT, str(Path.home())],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=_PICK_FOLDER_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SetupAppError(
                "Der Verzeichnisdialog wurde nicht beantwortet.", status_code=504
            ) from exc
        finally:
            self._dialog_lock.release()
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip().splitlines()[-1:] or [""]
            raise SetupAppError(
                f"Der Verzeichnisdialog ist fehlgeschlagen: {detail[0]}", status_code=500
            )
        lines = (completed.stdout or "").strip().splitlines()
        chosen = lines[-1].strip() if lines else ""
        return {"schema": "folderhome.setup-folder-pick.v1", "path": chosen or None}

    def _verify_registry(self, path: Path) -> None:
        try:
            load_resource_registry(
                path,
                expected_os_account=self.profiles.os_account,
                known_profile_ids=frozenset(
                    item.profile_id for item in self.profiles.profiles
                ),
            )
        except ResourceRegistryError as exc:
            raise SetupAppError(
                f"Geschriebenes Register ist nicht ladbar: {exc}"
            ) from exc

    def _current_folders(self) -> list[dict[str, str]]:
        if not self.resources_file.is_file():
            return []
        try:
            registry = load_resource_registry(
                self.resources_file,
                expected_os_account=self.profiles.os_account,
                known_profile_ids=frozenset(
                    item.profile_id for item in self.profiles.profiles
                ),
            )
        except ResourceRegistryError:
            return []
        current = []
        for resource in registry.resources:
            for profile_id in sorted(resource.profile_ids):
                defaults = registry.profile_defaults.get(profile_id, {})
                for purpose in sorted(resource.purposes):
                    if purpose not in SETUP_PURPOSES:
                        continue
                    current.append(
                        {
                            "profile_id": profile_id,
                            "purpose": purpose,
                            "path": str(resource.local_path),
                            "is_default": defaults.get(purpose) == resource.resource_id,
                        }
                    )
        return current

    # ------------------------------------------------------------------- HTTP
    def handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        try:
            return self._handle(
                method=method.upper(),
                target=target,
                headers={key.casefold(): value for key, value in headers.items()},
                body=body,
                server_port=server_port,
            )
        except SetupAppError as exc:
            return self._error(exc.status_code, str(exc))
        except ValueError as exc:
            return self._error(422, f"Einrichtung konnte die Anfrage nicht ausführen: {exc}")
        except OSError as exc:
            return self._error(503, f"Konfiguration ist nicht schreibbar: {exc}")

    def _handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        expected_host = f"{self.settings.host}:{server_port}"
        if headers.get("host") != expected_host:
            return self._error(403, "HTTP-Host stimmt nicht mit der Loopback-Bindung überein.")
        origin = headers.get("origin")
        if origin is not None and origin != f"http://{expected_host}":
            return self._error(403, "Browser-Origin liegt außerhalb der Einrichtung.")
        parsed = urlsplit(target)
        is_api = parsed.path.startswith("/api/")
        supplied = headers.get("x-folderhome-token", "") if is_api else (
            parse_qs(parsed.query).get("token", [""])[0]
        )
        if not hmac.compare_digest(supplied, self.session_token):
            return self._error(401, "Lokales Sitzungstoken fehlt oder ist ungültig.")

        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
            "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        if parsed.path in assets:
            if method != "GET":
                return self._error(405, "Methode ist für diese lokale Ressource nicht erlaubt.")
            filename, content_type = assets[parsed.path]
            return self._asset_response(filename, content_type)
        if method == "GET" and parsed.path == "/api/v1/setup/state":
            return self._json_response(self.state_payload())
        if method == "POST" and parsed.path == "/api/v1/setup/validate":
            return self._json_response(self.plan(self._json_request(headers, body)))
        if method == "POST" and parsed.path == "/api/v1/setup/save":
            return self._json_response(self.save(self._json_request(headers, body)))
        if method == "POST" and parsed.path == "/api/v1/setup/pick-folder":
            return self._json_response(self.pick_folder())
        if parsed.path in {
            "/api/v1/setup/state",
            "/api/v1/setup/validate",
            "/api/v1/setup/save",
            "/api/v1/setup/pick-folder",
        }:
            return self._error(405, "Einrichtungsendpunkt erwartet eine andere Methode.")
        return self._error(404, "Unbekannter Einrichtungsendpunkt.")

    def _json_request(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        if len(body) > self.settings.max_body_bytes:
            raise SetupAppError("Anfrage überschreitet die lokale Größenbegrenzung.")
        content_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
        if content_type != "application/json":
            raise SetupAppError("Einrichtung akzeptiert ausschließlich application/json.")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise SetupAppError(f"JSON-Anfrage ist ungültig: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema") != (
            "folderhome.setup-plan-request.v1"
        ):
            raise SetupAppError("Einrichtungsanfrage verwendet ein unbekanntes Schema.")
        return payload

    def _asset_response(self, filename: str, content_type: str) -> LocalApiResponse:
        path = self._asset_root / filename
        if not path.is_file():
            return self._error(500, "Lokales Einrichtungs-Asset fehlt.")
        content = path.read_text(encoding="utf-8").replace(
            "__FOLDERHOME_TOKEN__",
            quote(self.session_token, safe=""),
        )
        return LocalApiResponse(
            status_code=200,
            content_type=content_type,
            content=content.encode("utf-8"),
            headers=_security_headers(),
        )

    def _json_response(
        self,
        payload: dict[str, Any],
        status_code: int = 200,
    ) -> LocalApiResponse:
        content = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        ).encode("utf-8")
        return LocalApiResponse(
            status_code=status_code,
            content_type="application/json; charset=utf-8",
            content=content,
            headers=_security_headers(),
            payload=payload,
        )

    def _error(self, status_code: int, message: str) -> LocalApiResponse:
        return self._json_response(
            {
                "schema": "folderhome.local-api-error.v1",
                "status": "blocked" if status_code in {401, 403} else "error",
                "status_code": status_code,
                "message": message,
            },
            status_code=status_code,
        )


def _security_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Content-Security-Policy": (
            "default-src 'none'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'"
        ),
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }


def _folder_entries(
    request: dict[str, Any],
    profiles: ProfileConfiguration,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    raw = request.get("folders")
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append({"field": "folders", "message": "folders muss eine Liste sein."})
        return []
    known = {item.profile_id for item in profiles.profiles}
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        field = f"folders[{index}]"
        if not isinstance(item, dict):
            errors.append({"field": field, "message": "Eintrag muss ein Objekt sein."})
            continue
        profile_id = item.get("profile_id")
        purpose = item.get("purpose")
        path = item.get("path")
        if profile_id not in known:
            errors.append({"field": field, "message": "Unbekanntes Profil."})
            continue
        if purpose not in SETUP_PURPOSES:
            errors.append({"field": field, "message": f"Unbekannter Zweck: {purpose}"})
            continue
        if not isinstance(path, str) or not path.strip():
            errors.append({"field": field, "message": "Ordnerpfad fehlt."})
            continue
        entries.append(
            {
                "field": field,
                "profile_id": profile_id,
                "purpose": purpose,
                "path": Path(path).expanduser(),
                "confirm_outside_home": item.get("confirm_outside_home") is True,
            }
        )
    return entries


def _check_folder(entry: dict[str, Any], errors: list[dict[str, str]]) -> None:
    path: Path = entry["path"]
    if not path.is_absolute():
        errors.append({"field": entry["field"], "message": "Ordnerpfad muss absolut sein."})
        return
    resolved = path.resolve()
    entry["path"] = resolved
    if path.is_symlink():
        errors.append({"field": entry["field"], "message": "Ordner darf kein Symlink sein."})
        return
    if not resolved.is_dir():
        errors.append(
            {"field": entry["field"], "message": f"Ordner existiert nicht: {resolved}"}
        )
        return
    if not resolved.is_relative_to(Path.home().resolve()) and not entry[
        "confirm_outside_home"
    ]:
        errors.append(
            {
                "field": entry["field"],
                "message": (
                    "Ordner liegt außerhalb des eigenen Benutzerordners; bestätige das "
                    "ausdrücklich."
                ),
            }
        )


def _model_settings(
    request: dict[str, Any],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    raw = request.get("model")
    model = raw if isinstance(raw, dict) else {}
    provider = model.get("provider", "fixture")
    values = {
        "provider": provider,
        "ollama_host": model.get("ollama_host") or None,
        "ollama_model_id": model.get("ollama_model_id") or None,
        "bedrock_model_id": model.get("bedrock_model_id") or None,
        "aws_region": model.get("aws_region") or None,
        "network_used": False,
    }
    try:
        # Reuse the real contract instead of a second rule set. The gates are shown
        # in the UI and stay start-up flags; they are never written to a file.
        settings = StrandsAgentSettings(
            model_provider=str(provider),
            ollama_host=values["ollama_host"],
            ollama_model_id=values["ollama_model_id"],
            bedrock_model_id=values["bedrock_model_id"],
            aws_region=values["aws_region"],
            allow_network=provider != "fixture",
            allow_sensitive_cloud_data=provider != "fixture",
        )
    except ValueError as exc:
        errors.append({"field": "model", "message": str(exc)})
    else:
        # The same verdict the app uses, so the printed command matches the gates.
        values["network_used"] = settings.network_used
    return values


def _port(request: dict[str, Any], errors: list[dict[str, str]]) -> int:
    value = request.get("port", 8765)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65_535:
        errors.append({"field": "port", "message": "Port muss zwischen 1 und 65535 liegen."})
        return 8765
    return value


def _directory(value: object, field: str, errors: list[dict[str, str]]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append({"field": field, "message": f"{field} fehlt."})
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        errors.append({"field": field, "message": f"{field} muss absolut sein."})
        return None
    resolved = path.resolve()
    if not resolved.is_dir():
        errors.append({"field": field, "message": f"Verzeichnis existiert nicht: {resolved}"})
        return None
    return resolved


def _resources_document(
    os_account: str,
    folders: list[dict[str, Any]],
) -> dict[str, Any]:
    """Group the chosen folders into one registry the existing loader accepts."""

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in folders:
        key = (entry["profile_id"], str(entry["path"]))
        record = grouped.setdefault(
            key,
            {"profile_id": entry["profile_id"], "path": entry["path"], "purposes": set()},
        )
        record["purposes"].add(entry["purpose"])
    resources = []
    defaults: dict[str, dict[str, str]] = {}
    counters: dict[str, int] = {}
    # Form order, not path order: a purpose may appear several times and the first
    # folder the user named is the one the app falls back to.
    for (profile_id, _path), record in grouped.items():
        counters[profile_id] = counters.get(profile_id, 0) + 1
        resource_id = f"{profile_id}_resource_{counters[profile_id]}"
        purposes = sorted(record["purposes"])
        is_output = any(item in _OUTPUT_PURPOSES for item in purposes)
        operations = sorted(
            {operation for item in purposes for operation in _PURPOSE_OPERATIONS[item]}
        )
        resources.append(
            {
                "resource_id": resource_id,
                "kind": "directory",
                "locator": {"type": "local_path", "path": str(record["path"])},
                "operations": operations,
                "purposes": purposes,
                "profile_ids": [profile_id],
                # Stricter wins: a folder that also receives output never leaves the machine.
                "cloud_context": "deny" if is_output else "minimized_with_approval",
            }
        )
        bindings = defaults.setdefault(profile_id, {})
        for purpose in purposes:
            bindings.setdefault(purpose, resource_id)
    return {
        "schema": "folderhome.resource-registry.v1",
        "os_account": os_account,
        "resources": resources,
        "profile_defaults": defaults,
    }


def _launch_document(
    *,
    profiles_dir: Path | None,
    state_dir: Path | None,
    resources_file: Path | None,
    model: dict[str, Any],
    port: int,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema": LAUNCH_CONFIG_SCHEMA,
        "profiles_dir": str(profiles_dir) if profiles_dir else None,
        "state_dir": str(state_dir) if state_dir else None,
        "resources_file": str(resources_file) if resources_file else None,
        "port": port,
        "model_provider": model["provider"],
        "ollama_host": model["ollama_host"],
        "ollama_model_id": model["ollama_model_id"],
        "bedrock_model_id": model["bedrock_model_id"],
        "aws_region": model["aws_region"],
    }
    return document


def _launch_command(launch_file: Path, model: dict[str, Any]) -> str:
    """Spell out the gates, because a launch file is deliberately not allowed to."""

    gates = ["--approve-loopback-server"]
    if model.get("network_used"):
        gates[:0] = ["--allow-network", "--approve-sensitive-cloud-data"]
    return (
        f'"{sys.executable}" -m folderhome app serve '
        f'--launch-config "{launch_file}" {" ".join(gates)} --json'
    )


def _plan_digest(payload: dict[str, Any]) -> str:
    material = {
        "resources_json": payload["resources_json"],
        "launch_json": payload["launch_json"],
        "targets": payload["targets"],
    }
    return sha256(
        json.dumps(material, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _stage_json(target: Path, document: dict[str, Any]) -> Path:
    """Write encoded bytes to a temporary file beside the target, nothing more."""

    content = (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    temporary = target.with_name(f"{target.name}.tmp-{secrets.token_hex(6)}")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def _commit_staged(temporary: Path, target: Path) -> Path | None:
    """Replace the target with the staged file; keep the previous version."""

    backup: Path | None = None
    if target.is_file():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(f"{target.name}.bak-{stamp}")
        backup.write_bytes(target.read_bytes())
    os.replace(temporary, target)
    return backup


__all__ = [
    "LAUNCH_CONFIG_SCHEMA",
    "SETUP_PURPOSES",
    "SetupAppError",
    "SetupApplication",
    "default_config_dir",
]
