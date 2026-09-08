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
import re
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

from folderhome.application.app_calendar_configuration import (
    read_app_calendar_configuration,
    read_calendar_document,
)
from folderhome.application.calendar_connectors import (
    CalendarConnectorError,
    load_calendar_connector_accounts,
    parse_calendar_connector_accounts,
)
from folderhome.application.calendar_handoff import (
    CalendarWorkflowError,
    load_calendar_configuration,
    parse_calendar_configuration,
)
from folderhome.application.local_app import capture_os_identity
from folderhome.application.profile_rules import (
    ProfileConfiguration,
    ProfileConfigurationError,
    parse_profile_configuration,
)
from folderhome.application.resource_registry import (
    default_resource_registry_path,
    load_resource_registry,
    parse_resource_registry,
)
from folderhome.contracts.calendar import CalendarBackend
from folderhome.contracts.local_app import LocalApiResponse, LocalAppSettings
from folderhome.contracts.profiles import INTEGER_RULE_KEYS, RuleKey, RuleScope
from folderhome.contracts.resources import ResourceRegistry, ResourceRegistryError
from folderhome.contracts.strands_agent import StrandsAgentSettings
from folderhome.mcp_server import integration_plan

# One explicit table instead of guessing from name suffixes: `calendar.export_output`
# ends in `_output`, not `.output`, and silently got no operations at all.
_PURPOSE_OPERATIONS: dict[str, tuple[str, ...]] = {
    "documents.source": ("list", "read"),
    "insurance.source": ("list", "read"),
    "calendar.source": ("list", "read"),
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
# The only environment names the installer writes and the app reads back.
# A closed list means a config folder cannot quietly redefine PATH or a proxy.
ENV_FILENAME = ".env"
ENV_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
_PRESET_NAME = re.compile(r"[A-Za-z0-9_.-]{1,40}")
# Outlook has no backend in this code base, so the installer does not offer one.
CALENDAR_BACKENDS = tuple(item.value for item in CalendarBackend)
CALENDAR_ACCOUNT_FIELDS = (
    "account_id",
    "display_name",
    "provider_id",
    "provider_revision",
    "calendar_id",
    "credential_ref",
)
HOUSEHOLD_FILENAME = "household.json"
PROFILE_SCHEMA = "folderhome.user-profile.v1"
HOUSEHOLD_SCHEMA = "folderhome.household-rules.v1"
# The closed key set of the rule contract, so the browser offers exactly what loads.
RULE_KEYS = tuple(item.value for item in RuleKey)
INTEGER_RULE_KEY_VALUES = tuple(sorted(item.value for item in INTEGER_RULE_KEYS))
PROFILE_RULE_SCOPES = (RuleScope.PROFILE.value, RuleScope.PROFILE_AREA.value)
HOUSEHOLD_RULE_SCOPES = (RuleScope.GLOBAL.value, RuleScope.AREA.value)
# The file name always comes from the validated id, never from typed text.
_PROFILE_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_TEMPLATE_DIRECTORIES = (
    Path(__file__).parents[2] / "examples" / "profiles",
    Path(__file__).parent / "demo_data" / "profiles",
)
_MODEL_FIELDS = (
    "ollama_host",
    "ollama_model_id",
    "bedrock_model_id",
    "aws_region",
    "anthropic_model_id",
    "openai_model_id",
    "openai_base_url",
)


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


def default_profiles_dir(*, environ: dict[str, str] | None = None) -> Path:
    """Return the profile folder the installer owns, beside the other config."""

    return default_config_dir(environ=environ) / "profiles"


class SetupApplication:
    """Plan and write `resources.json` and `launch.json` for one OS account."""

    def __init__(
        self,
        *,
        settings: LocalAppSettings,
        profiles: ProfileConfiguration | None,
        config_dir: Path,
        session_token: str | None = None,
    ) -> None:
        token = session_token or secrets.token_urlsafe(32)
        if len(token) < 32:
            raise SetupAppError("Lokales Sitzungstoken ist zu kurz.")
        self.settings = settings
        # No profile folder yet is a first run, not an error: the installer is the
        # program that creates one, so it has to start without it.
        self.profiles = profiles if profiles is not None else empty_profile_configuration()
        self.profiles_configured = profiles is not None
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

    @property
    def env_file(self) -> Path:
        return self.config_dir / ENV_FILENAME

    @property
    def calendar_file(self) -> Path:
        return self.config_dir / "calendar.json"

    @property
    def calendar_accounts_file(self) -> Path:
        return self.config_dir / "calendar-accounts.json"

    @property
    def profiles_dir(self) -> Path:
        return self.settings.profiles_dir

    # ------------------------------------------------------------------ plans
    def state_payload(self) -> dict[str, Any]:
        """Describe what the installer can configure and what is configured now."""

        stored_keys = read_env_file(self.env_file)
        launch = self._current_launch()
        registry = self._load_registry()
        current_calendar, calendar_load_error, external_calendar = self._current_calendar(launch)
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
            "profiles_configured": self.profiles_configured,
            "profiles_dir_is_template": is_template_directory(self.profiles_dir),
            "default_profiles_dir": str(self.config_dir / "profiles"),
            "household_rules": _household_form(self.profiles),
            "profile_forms": _profile_form(self.profiles),
            "profile_templates": profile_templates(),
            "rule_keys": list(RULE_KEYS),
            "integer_rule_keys": list(INTEGER_RULE_KEY_VALUES),
            "profile_rule_scopes": list(PROFILE_RULE_SCOPES),
            "household_rule_scopes": list(HOUSEHOLD_RULE_SCOPES),
            "calendar_backends": list(CALENDAR_BACKENDS),
            "calendar_read_by_app": True,
            "current_calendar": current_calendar,
            "calendar_load_error": calendar_load_error,
            "calendar_external_configuration": external_calendar,
            "repeatable_purposes": [
                purpose for purpose in SETUP_PURPOSES if purpose not in _OUTPUT_PURPOSES
            ],
            "model_providers": [
                "fixture",
                "ollama",
                "bedrock",
                "anthropic",
                "openai",
            ],
            "config_dir": str(self.config_dir),
            "resources_file": str(self.resources_file),
            "launch_file": str(self.launch_file),
            "calendar_file": str(self.calendar_file),
            "calendar_accounts_file": str(self.calendar_accounts_file),
            "household_file": str(self.profiles_dir / HOUSEHOLD_FILENAME),
            "home": str(Path.home().resolve()),
            "profiles_dir": str(self.profiles_dir),
            # The written file wins, so a reopen keeps the folder the app uses.
            "state_dir": launch.get("state_dir") or str(self.config_dir / "state"),
            "configured": registry is not None,
            "has_anthropic_key": "ANTHROPIC_API_KEY" in stored_keys,
            "has_openai_key": "OPENAI_API_KEY" in stored_keys,
            "current_folders": _configured_folders(registry),
            "model_presets": launch.get("model_presets") or {},
            "model_preset": launch.get("model_preset"),
            # Instructions only: the same plan `mcp plan` prints, no server started.
            "integrations": integration_plan(None),
            "writes_credentials": False,
        }

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        """Build both file contents and their hash without touching the disk."""

        errors: list[dict[str, str]] = []
        household_json, profiles_json = _profile_documents(
            request, self.profiles, configured=self.profiles_configured, errors=errors
        )
        # Folders and calendar accounts bind to the profiles this plan will write,
        # not to the ones on disk: otherwise a new profile could never get a folder.
        planned = self._planned_profiles(household_json, profiles_json, errors)
        removed = [
            profile_id
            for profile_id in _existing_profile_ids(self.profiles_dir)
            if profiles_json is not None and profile_id not in profiles_json
        ]
        folders = _folder_entries(request, planned, errors)
        model, presets, preset_name = _model_settings(request, errors)
        calendar_json, calendar_accounts_json = _calendar_documents(
            request, planned, errors
        )
        raw_calendar = request.get("calendar")
        clear_calendar_accounts = (
            isinstance(raw_calendar, dict) and raw_calendar.get("accounts") == []
        )
        cascade, calendar_accounts_json = self._cascade(
            removed, calendar_accounts_json, errors=errors, clear_accounts=clear_calendar_accounts,
        )
        port = _port(request, errors)
        state_dir = _directory(request.get("state_dir"), "state_dir", errors)
        profiles_dir = _writable_directory(
            request.get("profiles_dir") or str(self.profiles_dir),
            "profiles_dir",
            errors,
        )
        if (
            profiles_json is not None
            and profiles_dir is not None
            and is_template_directory(profiles_dir)
        ):
            errors.append(
                {
                    "field": "profiles_dir",
                    "message": (
                        "Der Beispielordner ist eine Vorlage und wird nicht "
                        "beschrieben; wähle einen eigenen Profilordner, etwa "
                        f"{self.config_dir / 'profiles'}."
                    ),
                }
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
            _resources_document(planned.os_account, folders) if folders else None
        )
        if resources_json is not None:
            resources_json = self._merge_resources(resources_json, planned, errors)
        launch_json = (
            None
            if errors
            else _launch_document(
                profiles_dir=profiles_dir,
                state_dir=state_dir,
                resources_file=self.resources_file if folders else None,
                model=model,
                presets=presets,
                preset_name=preset_name,
                port=port,
            )
        )
        if launch_json is not None:
            current_launch = self._current_launch()
            for field, path, document in (
                ("calendar_config", self.calendar_file, calendar_json),
                ("connector_accounts", self.calendar_accounts_file, calendar_accounts_json),
            ):
                if field == "connector_accounts" and (
                    clear_calendar_accounts or cascade.get("calendar_accounts_unbound")
                ):
                    continue
                if str(path) in cascade["retired_files"]:
                    continue
                if document is not None:
                    launch_json[field] = str(path)
                elif current_launch.get(field) is not None:
                    launch_json[field] = current_launch[field]
                elif path.is_file():
                    # Adopt a pre-existing setup file without moving or rewriting it.
                    launch_json[field] = str(path)
        payload: dict[str, Any] = {
            "schema": "folderhome.setup-plan.v1",
            "valid": not errors and resources_json is not None,
            "errors": errors,
            "targets": {
                "resources_file": str(self.resources_file),
                "launch_file": str(self.launch_file),
                "calendar_file": str(self.calendar_file),
                "calendar_accounts_file": str(self.calendar_accounts_file),
                "profiles_dir": str(profiles_dir) if profiles_dir else None,
                "household_file": (
                    str(profiles_dir / HOUSEHOLD_FILENAME) if profiles_dir else None
                ),
            },
            "resources_json": resources_json,
            "launch_json": launch_json,
            "calendar_json": calendar_json,
            "calendar_accounts_json": calendar_accounts_json,
            "household_json": household_json,
            "profiles_json": profiles_json,
            "removed_profile_ids": removed,
            "cascade": cascade,
            "written": False,
            "side_effects": [],
        }
        if not folders and not errors:
            payload["errors"] = [
                {"field": "folders", "message": "Mindestens ein Ordner wird benötigt."}
            ]
            payload["valid"] = False
        if payload["valid"]:
            # The reload check belongs here, not only in save: a plan the loader
            # would reject must never light up the save button.
            payload["errors"] = self._document_errors(payload)
            payload["valid"] = not payload["errors"]
        if payload["valid"] and profiles_json is not None and profiles_dir is None:
            payload["errors"] = [
                {"field": "profiles_dir", "message": "Profilordner fehlt."}
            ]
            payload["valid"] = False
        payload["launch_command"] = _launch_command(self.launch_file, model)
        payload["plan_sha256"] = _plan_digest(payload)
        return payload

    def _merge_resources(
        self,
        proposed: dict[str, Any],
        planned: ProfileConfiguration,
        errors: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Edit supported folder bindings without discarding private configuration."""

        if not self.resources_file.exists():
            return proposed
        profile_ids = {item.profile_id for item in planned.profiles}
        try:
            existing = json.loads(self.resources_file.read_text(encoding="utf-8"))
            parse_resource_registry(
                existing,
                expected_os_account=planned.os_account,
                known_profile_ids=frozenset(
                    profile_ids | {item.profile_id for item in self.profiles.profiles}
                ),
            )
        except (OSError, ValueError) as exc:
            errors.append({
                "field": "resources_file",
                "message": f"Bestehendes Ressourcenregister zuerst reparieren: {exc}",
            })
            return proposed
        return _merge_resource_documents(existing, proposed, profile_ids)

    def _planned_profiles(
        self,
        household_json: dict[str, Any] | None,
        profiles_json: dict[str, dict[str, Any]] | None,
        errors: list[dict[str, str]],
    ) -> ProfileConfiguration:
        """Return the profile set this plan describes, checked by its own contract."""

        if household_json is None or profiles_json is None:
            return self.profiles
        try:
            return parse_profile_configuration(
                household_json,
                {_profile_filename(key): value for key, value in profiles_json.items()},
            )
        except (ProfileConfigurationError, SetupAppError) as exc:
            errors.append({"field": "profiles", "message": str(exc)})
            return self.profiles

    def _cascade(
        self,
        removed: list[str],
        calendar_accounts_json: dict[str, Any] | None,
        *,
        errors: list[dict[str, str]],
        clear_accounts: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Say what a deleted profile takes with it, and take it in the same plan.

        A folder binding or a calendar account of a profile that no longer exists
        would keep the app from starting, so it cannot be left behind.
        """

        cascade: dict[str, Any] = {
            "resource_ids": [],
            "calendar_account_ids": [],
            "retired_files": [],
        }
        if not removed and not clear_accounts:
            return cascade, calendar_accounts_json
        gone = set(removed)
        registry = self._load_registry()
        if registry is not None:
            cascade["resource_ids"] = sorted(
                resource.resource_id
                for resource in registry.resources
                if resource.profile_ids.issubset(gone)
            )
        launch = self._current_launch()
        try:
            value = launch.get("connector_accounts", str(self.calendar_accounts_file))
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Ungültiger Kontenpfad.")
            accounts_path = Path(value)
            stored = (
                [
                    {key: value for key, value in account.to_dict().items() if key != "schema"}
                    for account in parse_calendar_connector_accounts(
                        read_calendar_document(accounts_path)
                    )
                ]
                if "connector_accounts" in launch or accounts_path.exists() else []
            )
        except (OSError, ValueError, RuntimeError):
            errors.append({
                "field": "calendar.accounts",
                "message": (
                    "Aktive Kalenderkonten sind nicht lesbar; vor der Profiländerung prüfen."
                ),
            })
            return cascade, calendar_accounts_json
        if clear_accounts:
            cascade["calendar_account_ids"] = sorted(
                str(account.get("account_id")) for account in stored
                if isinstance(account, dict)
            )
            if self.calendar_accounts_file.exists():
                cascade["retired_files"] = [str(self.calendar_accounts_file)]
            return cascade, None
        orphaned = [
            account
            for account in stored
            if isinstance(account, dict) and account.get("profile_id") in gone
        ]
        if not orphaned:
            return cascade, calendar_accounts_json
        cascade["calendar_account_ids"] = sorted(
            str(account.get("account_id")) for account in orphaned
        )
        if calendar_accounts_json is not None:
            # The request rewrites the file anyway; it already left them out.
            return cascade, calendar_accounts_json
        remaining = [account for account in stored if account not in orphaned]
        if remaining:
            return cascade, {
                "schema": "folderhome.calendar-connector-accounts.v1",
                "accounts": remaining,
            }
        # An empty account list is not a valid document, so the file is retired.
        cascade["calendar_accounts_unbound"] = True
        if self.calendar_accounts_file.exists():
            cascade["retired_files"] = [str(self.calendar_accounts_file)]
        return cascade, None

    def _document_errors(self, payload: dict[str, Any]) -> list[dict[str, str]]:
        """Run each written document through the contract that will load it."""

        errors: list[dict[str, str]] = []
        planned = self._planned_profiles(
            payload["household_json"], payload["profiles_json"], errors
        )
        try:
            parse_resource_registry(
                payload["resources_json"],
                expected_os_account=planned.os_account,
                known_profile_ids=frozenset(
                    item.profile_id for item in planned.profiles
                ),
            )
        except ResourceRegistryError as exc:
            errors.append({"field": "folders", "message": str(exc)})
        if payload["calendar_json"] is not None:
            try:
                parse_calendar_configuration(
                    payload["calendar_json"], config_path=self.calendar_file
                )
            except CalendarWorkflowError as exc:
                errors.append({"field": "calendar", "message": str(exc)})
        if payload["calendar_accounts_json"] is not None:
            try:
                accounts = parse_calendar_connector_accounts(payload["calendar_accounts_json"])
                known_profiles = {item.profile_id for item in planned.profiles}
                if any(account.profile_id not in known_profiles for account in accounts):
                    errors.append({
                        "field": "calendar.accounts",
                        "message": "Kalenderkonten müssen zu den geplanten Profilen gehören.",
                    })
            except CalendarConnectorError as exc:
                errors.append({"field": "calendar.accounts", "message": str(exc)})
        return errors

    def save(self, request: dict[str, Any]) -> dict[str, Any]:
        """Serialize revalidation and save; roll back on reported write failures."""

        with self._lock:
            return self._save_confirmed(request)

    def _save_confirmed(self, request: dict[str, Any]) -> dict[str, Any]:

        if request.get("confirm") is not True:
            raise SetupAppError("Speichern benötigt eine ausdrückliche Bestätigung.")
        supplied = request.get("plan_sha256")
        if not isinstance(supplied, str) or len(supplied) != 64:
            raise SetupAppError("Speichern benötigt den Hash des geprüften Plans.")
        # Keys travel outside the plan on purpose: they must not reach the hash,
        # the preview or any response. They are checked before anything is written.
        api_keys = _api_key_changes(request)
        plan = self.plan(request)
        if not plan["valid"]:
            raise SetupAppError("Plan ist nicht gültig; erst die Fehler beheben.")
        if not hmac.compare_digest(supplied, str(plan["plan_sha256"])):
            raise SetupAppError("Plan-Hash stimmt nicht mit der geprüften Fassung überein.")
        planned = self._planned_profiles(
            plan["household_json"], plan["profiles_json"], []
        )
        profiles_dir = (
            Path(plan["targets"]["profiles_dir"])
            if plan["profiles_json"] is not None
            else None
        )
        with self._lock:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if profiles_dir is not None:
                profiles_dir.mkdir(parents=True, exist_ok=True)
            # Stage every file, load the staged documents, and only then replace the
            # live ones. A refused plan leaves the previous state exactly as it was.
            staged: list[tuple[Path, Path]] = []
            try:
                if profiles_dir is not None:
                    profile_files: list[tuple[Path, Path]] = []
                    for profile_id, document in sorted(plan["profiles_json"].items()):
                        target = profiles_dir / _profile_filename(profile_id)
                        entry = (_stage_json(target, document), target)
                        profile_files.append(entry)
                        staged.append(entry)
                    household_target = profiles_dir / HOUSEHOLD_FILENAME
                    household_staged = _stage_json(
                        household_target, plan["household_json"]
                    )
                    staged.append((household_staged, household_target))
                    _verify_profiles(household_staged, profile_files)
                staged.append(
                    (
                        _stage_json(self.resources_file, plan["resources_json"]),
                        self.resources_file,
                    )
                )
                staged.append(
                    (_stage_json(self.launch_file, plan["launch_json"]), self.launch_file)
                )
                self._verify_registry(staged[-2][0], planned)
                for document, target, check in (
                    (
                        plan["calendar_json"],
                        self.calendar_file,
                        _verify_calendar_configuration,
                    ),
                    (
                        plan["calendar_accounts_json"],
                        self.calendar_accounts_file,
                        _verify_calendar_accounts,
                    ),
                ):
                    if document is None:
                        continue
                    temporary = _stage_json(target, document)
                    staged.append((temporary, target))
                    check(temporary)
            except BaseException:
                for temporary, _target in staged:
                    temporary.unlink(missing_ok=True)
                raise
            retired_targets = [Path(item) for item in plan["cascade"]["retired_files"]]
            if profiles_dir is not None:
                retired_targets.extend(
                    profiles_dir / _profile_filename(profile_id)
                    for profile_id in plan["removed_profile_ids"]
                )
            targets = [target for _, target in staged] + retired_targets
            if api_keys:
                targets.append(self.env_file)
            snapshots = {}
            try:
                snapshots = {
                    target: (target.read_bytes(), target.stat()) if target.exists() else None
                    for target in targets
                }
                written = [_commit_staged(temporary, target) for temporary, target in staged]
                # Retired copies and backups remain available even if rollback is needed.
                retired = (
                    _retire_profiles(profiles_dir, plan["removed_profile_ids"])
                    if profiles_dir is not None
                    else []
                )
                retired += [
                    _retire_file(Path(item)) for item in plan["cascade"]["retired_files"]
                ]
                retired = [item for item in retired if item is not None]
                if api_keys:
                    write_env_file(self.env_file, api_keys)
            except BaseException:
                _restore_setup_files(snapshots)
                raise
            finally:
                for temporary, _target in staged:
                    temporary.unlink(missing_ok=True)
        plan["written"] = True
        plan["backups"] = [str(item) for item in written if item is not None]
        plan["retired_profiles"] = [str(item) for item in retired]
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

    def _verify_registry(self, path: Path, planned: ProfileConfiguration) -> None:
        try:
            load_resource_registry(
                path,
                expected_os_account=planned.os_account,
                known_profile_ids=frozenset(
                    item.profile_id for item in planned.profiles
                ),
            )
        except ResourceRegistryError as exc:
            raise SetupAppError(
                f"Geschriebenes Register ist nicht ladbar: {exc}"
            ) from exc

    def _current_calendar(
        self, launch: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        """Read active launch paths without silently falling back from invalid files."""

        external = False
        try:
            paths = []
            for field, owned in (
                ("calendar_config", self.calendar_file),
                ("connector_accounts", self.calendar_accounts_file),
            ):
                if field in launch:
                    value = launch[field]
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError("Ungültiger Kalenderpfad.")
                    path = Path(value)
                    external = external or path.resolve() != owned.resolve()
                else:
                    path = owned if owned.exists() else None
                paths.append(path)
            config_path, accounts_path = paths
            if config_path is None:
                return None, accounts_path is not None, external
            configuration = read_app_calendar_configuration(config_path)
            accounts = (
                parse_calendar_connector_accounts(read_calendar_document(accounts_path))
                if accounts_path is not None else ()
            )
            known_profiles = {item.profile_id for item in self.profiles.profiles}
            if any(account.profile_id not in known_profiles for account in accounts):
                raise ValueError("Kalenderkonto verweist auf ein unbekanntes Profil.")
            return {
                "default_backend": configuration.default_backend.value,
                "timezone": configuration.default_timezone,
                "ics_directory": str(configuration.uptoday_ics_directory),
                "accounts": [
                    {key: value for key, value in account.to_dict().items() if key != "schema"}
                    for account in accounts
                ],
            }, False, external
        except (OSError, ValueError, RuntimeError):
            return None, True, external

    def _current_launch(self) -> dict[str, Any]:
        """Read the written launch file so saved presets survive a reopen."""

        try:
            payload = json.loads(self.launch_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict) or payload.get("schema") != (
            LAUNCH_CONFIG_SCHEMA
        ):
            return {}
        return payload

    def _load_registry(self) -> ResourceRegistry | None:
        """Return the configured registry, or nothing when it does not load."""

        if not self.resources_file.is_file():
            return None
        try:
            return load_resource_registry(
                self.resources_file,
                expected_os_account=self.profiles.os_account,
                known_profile_ids=frozenset(
                    item.profile_id for item in self.profiles.profiles
                ),
            )
        except ResourceRegistryError:
            return None

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


def empty_profile_configuration() -> ProfileConfiguration:
    """Stand in for a household that does not exist yet on a first run.

    The account label is real even when no file carries it, so a household the
    installer writes later already belongs to the right operating system account.
    """

    return ProfileConfiguration(
        os_account=capture_os_identity().account_name,
        common_rules=(),
        profiles=(),
    )


def is_template_directory(directory: Path) -> bool:
    """Say whether a folder is one of the shipped examples, which stay read-only."""

    resolved = directory.resolve()
    return any(item.resolve() == resolved for item in _TEMPLATE_DIRECTORIES if item.exists())


def profile_templates() -> dict[str, Any]:
    """Return the shipped example household and profiles as plain documents."""

    for directory in _TEMPLATE_DIRECTORIES:
        household = directory / HOUSEHOLD_FILENAME
        if not household.is_file():
            continue
        try:
            documents = {
                path.stem: json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(
                    directory.glob("*.json"), key=lambda item: item.name.casefold()
                )
                if path.name.casefold() != HOUSEHOLD_FILENAME
            }
            return {
                "household": json.loads(household.read_text(encoding="utf-8")),
                "profiles": documents,
            }
        except (OSError, json.JSONDecodeError):
            continue
    return {"household": None, "profiles": {}}


def _profile_form(configuration: ProfileConfiguration) -> list[dict[str, Any]]:
    """Describe the configured profiles the way the form edits them."""

    return [
        {
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "organizational_only": profile.organizational_only,
            "rules": [
                {
                    "key": rule.key.value,
                    "value": rule.value,
                    "scope": rule.scope.value,
                    "area": rule.area,
                }
                for rule in profile.rules
            ],
        }
        for profile in sorted(configuration.profiles, key=lambda item: item.profile_id)
    ]


def _household_form(configuration: ProfileConfiguration) -> list[dict[str, Any]]:
    return [
        {
            "key": rule.key.value,
            "value": rule.value,
            "scope": rule.scope.value,
            "area": rule.area,
        }
        for rule in configuration.common_rules
    ]


def _rule_documents(
    raw: object,
    *,
    prefix: str,
    allowed_scopes: tuple[str, ...],
    field: str,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Turn typed rule rows into documents; ids are generated, never supplied."""

    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append({"field": field, "message": "Regeln müssen eine Liste sein."})
        return []
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        where = f"{field}[{index}]"
        if not isinstance(item, dict):
            errors.append({"field": where, "message": "Regel muss ein Objekt sein."})
            continue
        key = item.get("key")
        if key not in RULE_KEYS:
            errors.append({"field": where, "message": f"Unbekannter Regelschlüssel: {key}"})
            continue
        scope = item.get("scope")
        if scope not in allowed_scopes:
            errors.append({"field": where, "message": f"Unzulässige Reichweite: {scope}"})
            continue
        area = item.get("area")
        if isinstance(area, str):
            area = area.strip() or None
        elif area is not None:
            errors.append({"field": where, "message": "Bereich muss Text sein."})
            continue
        value = item.get("value")
        if isinstance(value, str):
            value = value.strip()
        rules.append(
            {
                "rule_id": f"rule_{prefix}_{index + 1}",
                "key": key,
                "value": value,
                "scope": scope,
                "area": area,
            }
        )
    return rules


def _profile_documents(
    request: dict[str, Any],
    current: ProfileConfiguration,
    *,
    configured: bool,
    errors: list[dict[str, str]],
) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]] | None]:
    """Build household.json and one document per profile, or leave both alone."""

    raw = request.get("profiles")
    if raw is None:
        if not configured:
            errors.append({"field": "profiles", "message": "Es ist noch kein Profil angelegt."})
        # An unchanged profile set is the normal case: nothing to write.
        return None, None
    if not isinstance(raw, list):
        errors.append({"field": "profiles", "message": "profiles muss eine Liste sein."})
        return None, None
    if not raw:
        errors.append(
            {"field": "profiles", "message": "Mindestens ein Profil muss bestehen bleiben."}
        )
        return None, None

    # The configured account wins; only a first run takes the running one.
    os_account = current.os_account
    documents: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        where = f"profiles[{index}]"
        if not isinstance(item, dict):
            errors.append({"field": where, "message": "Profil muss ein Objekt sein."})
            continue
        profile_id = item.get("profile_id")
        if not isinstance(profile_id, str) or _PROFILE_ID.fullmatch(profile_id) is None:
            errors.append(
                {
                    "field": where,
                    "message": (
                        "Profil-ID muss mit einem Kleinbuchstaben beginnen und darf "
                        "Kleinbuchstaben, Ziffern, _ und - enthalten (2 bis 64 Zeichen)."
                    ),
                }
            )
            continue
        if profile_id in documents:
            errors.append({"field": where, "message": f"Profil-ID doppelt: {profile_id}"})
            continue
        display_name = item.get("display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            errors.append({"field": where, "message": "Anzeigename fehlt."})
            continue
        documents[profile_id] = {
            "schema": PROFILE_SCHEMA,
            "profile_id": profile_id,
            "display_name": display_name.strip(),
            "os_account": os_account,
            # The example profiles declare this, and the contract insists on it.
            "organizational_only": True,
            "rules": _rule_documents(
                item.get("rules"),
                prefix=profile_id,
                allowed_scopes=PROFILE_RULE_SCOPES,
                field=f"{where}.rules",
                errors=errors,
            ),
        }
    household = {
        "schema": HOUSEHOLD_SCHEMA,
        "os_account": os_account,
        "rules": _rule_documents(
            request.get("household_rules"),
            prefix="household",
            allowed_scopes=HOUSEHOLD_RULE_SCOPES,
            field="household_rules",
            errors=errors,
        ),
    }
    return household, documents


def _profile_filename(profile_id: str) -> str:
    """Derive the file name from the validated id, never from typed text."""

    if _PROFILE_ID.fullmatch(profile_id) is None:
        raise SetupAppError(f"Unzulässige Profil-ID: {profile_id}")
    return f"{profile_id}.json"


def _existing_profile_ids(directory: Path) -> list[str]:
    """List the profile ids currently on disk, ignoring the household file."""

    if not directory.is_dir():
        return []
    return sorted(
        path.stem
        for path in directory.glob("*.json")
        if path.name.casefold() != HOUSEHOLD_FILENAME
    )


def _api_key_changes(request: dict[str, Any]) -> dict[str, str | None]:
    """Read the key changes a save carries, without ever echoing a value."""

    raw = request.get("api_keys")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SetupAppError("api_keys muss ein Objekt sein.")
    changes: dict[str, str | None] = {}
    for name, value in raw.items():
        if name not in ENV_KEYS:
            raise SetupAppError(f"Unbekannter Umgebungsname: {name}")
        if value is None:
            changes[name] = None
            continue
        if not isinstance(value, str) or not value.strip():
            raise SetupAppError(f"Wert für {name} fehlt.")
        if len(value) > 4_096 or any(item in value for item in "\r\n"):
            raise SetupAppError(f"Wert für {name} ist keine einzelne Textzeile.")
        changes[name] = value.strip()
    return changes


def read_env_file(target: Path) -> dict[str, str]:
    """Return the known keys stored in one .env file; unknown names are ignored."""

    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in text.splitlines():
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value:
            values[name] = value
    return values


def write_env_file(target: Path, changes: dict[str, str | None]) -> None:
    """Set or drop single keys, keep every other line, and never leave a backup."""

    existing = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
    pending = dict(changes)
    lines: list[str] = []
    for line in existing:
        name = line.partition("=")[0].strip()
        if name in pending:
            value = pending.pop(name)
            if value is not None:
                lines.append(f"{name}={value}")
            continue
        lines.append(line)
    for name, value in pending.items():
        if value is not None:
            lines.append(f"{name}={value}")
    temporary = target.with_name(f"{target.name}.tmp-{secrets.token_hex(6)}")
    try:
        with temporary.open("wb") as handle:
            handle.write(("\n".join(lines) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        # Owner-only where the platform enforces it. On Windows the user account
        # boundary is what protects the file, which the installer says out loud.
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _calendar_documents(
    request: dict[str, Any],
    profiles: ProfileConfiguration,
    errors: list[dict[str, str]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Build the calendar configuration and its accounts, or nothing at all."""

    raw = request.get("calendar")
    if not isinstance(raw, dict) or not raw:
        return None, None
    backend = raw.get("default_backend")
    if backend not in CALENDAR_BACKENDS:
        errors.append(
            {"field": "calendar", "message": f"Unbekanntes Kalender-Backend: {backend}"}
        )
        return None, None
    directory = _directory(raw.get("ics_directory"), "calendar.ics_directory", errors)
    timezone = raw.get("timezone")
    if not isinstance(timezone, str) or not timezone.strip():
        errors.append({"field": "calendar.timezone", "message": "Zeitzone fehlt."})
        timezone = None
    configuration = (
        None
        if directory is None or timezone is None
        else {
            "schema": "folderhome.calendar-config.v1",
            "default_backend": backend,
            "default_timezone": timezone.strip(),
            "uptoday_ics_directory": str(directory),
        }
    )
    accounts = _calendar_accounts(raw.get("accounts"), profiles, errors)
    if not accounts:
        return configuration, None
    return configuration, {
        "schema": "folderhome.calendar-connector-accounts.v1",
        "accounts": accounts,
    }


def _calendar_accounts(
    raw: object,
    profiles: ProfileConfiguration,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append(
            {"field": "calendar.accounts", "message": "accounts muss eine Liste sein."}
        )
        return []
    known = {item.profile_id for item in profiles.profiles}
    accounts: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        field = f"calendar.accounts[{index}]"
        if not isinstance(item, dict):
            errors.append({"field": field, "message": "Eintrag muss ein Objekt sein."})
            continue
        if item.get("profile_id") not in known:
            errors.append({"field": field, "message": "Unbekanntes Profil."})
            continue
        if item.get("backend") not in CALENDAR_BACKENDS:
            errors.append({"field": field, "message": "Unbekanntes Kalender-Backend."})
            continue
        # The loader rejects a per-account schema field; only the file carries one.
        account: dict[str, Any] = {
            "profile_id": item["profile_id"],
            "backend": item["backend"],
        }
        for name in CALENDAR_ACCOUNT_FIELDS:
            value = item.get(name)
            account[name] = value.strip() if isinstance(value, str) and value.strip() else None
        accounts.append(account)
    return accounts


def _verify_profiles(household: Path, staged: list[tuple[Path, Path]]) -> None:
    """Read the staged bytes back through the profile contract before replacing."""

    try:
        documents = {
            target.name: json.loads(temporary.read_text(encoding="utf-8"))
            for temporary, target in staged
        }
        parse_profile_configuration(
            json.loads(household.read_text(encoding="utf-8")), documents
        )
    except (OSError, json.JSONDecodeError, ProfileConfigurationError) as exc:
        raise SetupAppError(f"Geschriebene Profile sind nicht ladbar: {exc}") from exc


def _retire_file(target: Path) -> Path | None:
    """Move a file out of the way under a dated name, keeping its content."""

    if not target.is_file():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = target.with_name(f"{target.name}.bak-{stamp}-{secrets.token_hex(6)}")
    os.rename(target, destination)
    return destination


def _retire_profiles(directory: Path, profile_ids: list[str]) -> list[Path]:
    """Move deleted profile files into a dated folder instead of deleting them."""

    if not profile_ids:
        return []
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    attic = directory / f".deleted-{stamp}-{secrets.token_hex(6)}"
    attic.mkdir(parents=True, exist_ok=False)
    retired = []
    for profile_id in sorted(profile_ids):
        source = directory / _profile_filename(profile_id)
        if not source.is_file():
            continue
        destination = attic / source.name
        os.replace(source, destination)
        retired.append(destination)
    return retired


def _verify_calendar_configuration(path: Path) -> None:
    try:
        load_calendar_configuration(path)
    except CalendarWorkflowError as exc:
        raise SetupAppError(f"Geschriebene Kalenderkonfiguration ist nicht ladbar: {exc}") from exc


def _verify_calendar_accounts(path: Path) -> None:
    try:
        load_calendar_connector_accounts(path)
    except CalendarConnectorError as exc:
        raise SetupAppError(f"Geschriebene Kalenderkonten sind nicht ladbar: {exc}") from exc


def _configured_folders(registry: ResourceRegistry | None) -> list[dict[str, Any]]:
    """List every configured folder, marking the default of each purpose."""

    if registry is None:
        return []
    current = []
    for resource in registry.resources:
        if resource.kind != "directory":
            continue
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
    return sorted(
        current,
        key=lambda item: (
            item["profile_id"], item["purpose"], not item["is_default"], item["path"]
        ),
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


def _model_values(
    raw: object,
    field: str,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    """Check one model choice against the real contract, not a second rule set."""

    model = raw if isinstance(raw, dict) else {}
    provider = model.get("provider", "fixture")
    values: dict[str, Any] = {"provider": provider, "network_used": False}
    for name in _MODEL_FIELDS:
        values[name] = model.get(name) or None
    try:
        settings = StrandsAgentSettings(
            model_provider=str(provider),
            # The gates are shown in the UI and stay start-up flags; a file never
            # grants them, so they are assumed here only to reach the verdict.
            allow_network=provider != "fixture",
            allow_sensitive_cloud_data=provider != "fixture",
            **{name: values[name] for name in _MODEL_FIELDS},
        )
    except ValueError as exc:
        errors.append({"field": field, "message": str(exc)})
    else:
        # The same verdict the app uses, so the printed command matches the gates.
        values["network_used"] = settings.network_used
    return values


def _model_settings(
    request: dict[str, Any],
    errors: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str | None]:
    """Return the active model, every saved preset, and the active preset's name."""

    raw_presets = request.get("model_presets")
    if raw_presets is not None and not isinstance(raw_presets, dict):
        errors.append(
            {"field": "model_presets", "message": "model_presets muss ein Objekt sein."}
        )
        raw_presets = None
    presets: dict[str, dict[str, Any]] = {}
    for name, entry in (raw_presets or {}).items():
        if not isinstance(name, str) or _PRESET_NAME.fullmatch(name) is None:
            errors.append(
                {
                    "field": "model_presets",
                    "message": (
                        f"Preset-Name {name} darf nur Buchstaben, Ziffern, _ . - "
                        "enthalten (1 bis 40 Zeichen)."
                    ),
                }
            )
            continue
        # Inactive presets are checked as well: storing an unusable one helps nobody.
        presets[name] = _model_values(entry, f"model_presets[{name}]", errors)
    active = request.get("model_preset")
    if active is not None and not isinstance(active, str):
        errors.append({"field": "model_preset", "message": "model_preset muss Text sein."})
        active = None
    if isinstance(active, str) and active not in presets:
        errors.append(
            {"field": "model_preset", "message": f"Unbekanntes Modell-Preset: {active}"}
        )
        active = None
    if active is not None:
        return presets[active], presets, active
    return _model_values(request.get("model"), "model", errors), presets, None


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


def _writable_directory(value: object, field: str, errors: list[dict[str, str]]) -> Path | None:
    """Accept a folder the save will create, but never a path that cannot be one."""

    if not isinstance(value, str) or not value.strip():
        errors.append({"field": field, "message": f"{field} fehlt."})
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        errors.append({"field": field, "message": f"{field} muss absolut sein."})
        return None
    resolved = path.resolve()
    if resolved.exists() and not resolved.is_dir():
        errors.append({"field": field, "message": f"{resolved} ist kein Verzeichnis."})
        return None
    if not resolved.exists() and not resolved.parent.is_dir():
        errors.append(
            {"field": field, "message": f"Übergeordnetes Verzeichnis fehlt: {resolved.parent}"}
        )
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


def _merge_resource_documents(
    existing: dict[str, Any], proposed: dict[str, Any], profile_ids: set[str]
) -> dict[str, Any]:
    """Preserve opaque resources, stable IDs and stricter policy while editing folders."""

    reserved_ids = {item["resource_id"] for item in existing["resources"]}
    requested = {
        (profile, Path(item["locator"]["path"]).resolve(), purpose)
        for item in proposed["resources"]
        for profile in item["profile_ids"]
        for purpose in item["purposes"]
    }
    old = []
    retained_ids = {}
    for item in existing["resources"]:
        groups: dict[tuple[str, ...], list[str]] = {}
        for profile in item["profile_ids"]:
            if profile not in profile_ids:
                continue
            purposes = tuple(
                purpose for purpose in item["purposes"]
                if item["kind"] != "directory" or purpose not in SETUP_PURPOSES
                or (profile, Path(item["locator"]["path"]).resolve(), purpose) in requested
            )
            if purposes:
                groups.setdefault(purposes, []).append(profile)
        for index, (purposes, profiles) in enumerate(groups.items()):
            resource_id = item["resource_id"]
            if index:
                suffix = 1
                while (resource_id := f"setup_resource_{suffix}") in reserved_ids:
                    suffix += 1
                reserved_ids.add(resource_id)
            old.append({
                **item, "resource_id": resource_id,
                "profile_ids": profiles, "purposes": list(purposes),
            })
            for profile in profiles:
                retained_ids[(item["resource_id"], profile)] = resource_id
    used_ids = {item["resource_id"] for item in old}
    resources = list(old)
    replacements = {}
    for item in proposed["resources"]:
        # Existing resources retain their own purpose/permission boundaries.
        # Only genuinely new purposes receive generated bindings.
        profile = item["profile_ids"][0]
        path = Path(item["locator"]["path"]).resolve()
        missing = []
        for purpose in item["purposes"]:
            matches = [
                previous for previous in old
                if previous["kind"] == item["kind"]
                and Path(previous["locator"]["path"]).resolve() == path
                and profile in previous["profile_ids"] and purpose in previous["purposes"]
            ]
            if not matches:
                missing.append(purpose)
                continue
            old_default = existing["profile_defaults"].get(profile, {}).get(purpose)
            preferred_id = retained_ids.get((old_default, profile))
            chosen = next(
                (previous for previous in matches if previous["resource_id"] == preferred_id),
                matches[0],
            )
            replacements[(item["resource_id"], purpose)] = chosen["resource_id"]
        if not missing:
            continue
        resource = {
            **item, "purposes": missing,
            "operations": sorted({op for p in missing for op in _PURPOSE_OPERATIONS[p]}),
        }
        candidate = item["resource_id"]
        suffix = 1
        while candidate in reserved_ids or candidate in used_ids:
            candidate = f"setup_resource_{suffix}"
            suffix += 1
        resource["resource_id"] = candidate
        # The form cannot grant cloud access. A new profile binding must not
        # bypass a stricter binding already registered for the same location.
        cloud_rank = {"deny": 0, "synthetic_only": 1, "minimized_with_approval": 2}
        overlapping = [
            previous for previous in existing["resources"]
            if path.is_relative_to(Path(previous["locator"]["path"]).resolve())
            or Path(previous["locator"]["path"]).resolve().is_relative_to(path)
        ]
        resource["cloud_context"] = min(
            [resource["cloud_context"], *(p["cloud_context"] for p in overlapping)],
            key=cloud_rank.__getitem__,
        )
        for purpose in missing:
            replacements[(item["resource_id"], purpose)] = resource["resource_id"]
        used_ids.add(resource["resource_id"])
        resources.append(resource)
    # Outputs and pre-existing privacy boundaries also constrain retained source
    # bindings: splitting purposes must never create a second path to cloud data.
    cloud_rank = {"deny": 0, "synthetic_only": 1, "minimized_with_approval": 2}
    boundaries = [
        (Path(item["locator"]["path"]).resolve(), item["cloud_context"])
        for item in [*existing["resources"], *proposed["resources"]]
    ]
    changed = True
    while changed:
        changed = False
        current_boundaries = boundaries + [
            (Path(item["locator"]["path"]).resolve(), item["cloud_context"])
            for item in resources
        ]
        for resource in resources:
            path = Path(resource["locator"]["path"]).resolve()
            policy = min(
                [resource["cloud_context"], *(
                    policy for boundary, policy in current_boundaries
                    if path.is_relative_to(boundary) or boundary.is_relative_to(path)
                )],
                key=cloud_rank.__getitem__,
            )
            if policy != resource["cloud_context"]:
                resource["cloud_context"] = policy
                changed = True
    defaults = {
        profile: {
            purpose: retained_ids[(rid, profile)] for purpose, rid in bindings.items()
            if (rid, profile) in retained_ids and retained_ids[(rid, profile)] in used_ids
        }
        for profile, bindings in existing["profile_defaults"].items()
        if profile in profile_ids
    }
    by_id = {item["resource_id"]: item for item in resources}
    for profile, bindings in proposed["profile_defaults"].items():
        for purpose, rid in bindings.items():
            current = defaults.setdefault(profile, {}).get(purpose)
            # Non-folder defaults are invisible in this form and cannot be edited here.
            if current is None or by_id[current]["kind"] == "directory":
                defaults[profile][purpose] = replacements[(rid, purpose)]
    # Removed supported purposes must not leave stale defaults on retained resources.
    for profile, bindings in defaults.items():
        defaults[profile] = {
            purpose: rid for purpose, rid in bindings.items()
            if purpose in by_id[rid]["purposes"] and profile in by_id[rid]["profile_ids"]
        }
    return {**proposed, "resources": resources, "profile_defaults": defaults}


def _launch_document(
    *,
    profiles_dir: Path | None,
    state_dir: Path | None,
    resources_file: Path | None,
    model: dict[str, Any],
    presets: dict[str, dict[str, Any]],
    preset_name: str | None,
    port: int,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema": LAUNCH_CONFIG_SCHEMA,
        "profiles_dir": str(profiles_dir) if profiles_dir else None,
        "state_dir": str(state_dir) if state_dir else None,
        "resources_file": str(resources_file) if resources_file else None,
        "port": port,
        # The flat fields describe the choice; the preset name says where it came
        # from, so switching models later means changing one line, not seven.
        "model_provider": model["provider"],
        "model_preset": preset_name,
        "model_presets": {
            name: {
                "model_provider": entry["provider"],
                **{field: entry[field] for field in _MODEL_FIELDS},
            }
            for name, entry in sorted(presets.items())
        },
    }
    for field in _MODEL_FIELDS:
        document[field] = model[field]
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
        # Every file the save may write belongs in the confirmed hash.
        "calendar_json": payload["calendar_json"],
        "calendar_accounts_json": payload["calendar_accounts_json"],
        "household_json": payload["household_json"],
        "profiles_json": payload["profiles_json"],
        "removed_profile_ids": payload["removed_profile_ids"],
        "cascade": payload["cascade"],
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
    return _stage_bytes(target, content)


def _stage_bytes(target: Path, content: bytes) -> Path:
    temporary = target.with_name(f"{target.name}.tmp-{secrets.token_hex(6)}")
    created = False
    try:
        with temporary.open("xb") as handle:
            created = True
            os.chmod(temporary, 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return temporary
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise


def _restore_setup_files(
    snapshots: dict[Path, tuple[bytes, os.stat_result] | None],
) -> None:
    """Best-effort restoration of all files; credentials never get backup copies."""

    failures = []
    for target, snapshot in snapshots.items():
        try:
            if snapshot is None:
                target.unlink(missing_ok=True)
                continue
            content, metadata = snapshot
            if target.is_file() and target.read_bytes() == content:
                continue
            temporary = _stage_bytes(target, content)
            try:
                os.chmod(temporary, metadata.st_mode)
                os.replace(temporary, target)
                os.utime(target, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            finally:
                temporary.unlink(missing_ok=True)
        except OSError:
            failures.append(target.name)
    if failures:
        raise SetupAppError(
            "Speichern und Rücksetzen fehlgeschlagen. Sicherungen prüfen: "
            + ", ".join(failures), status_code=500,
        )


def _commit_staged(temporary: Path, target: Path) -> Path | None:
    """Replace changed content and retain each previous version without collisions."""

    backup: Path | None = None
    if target.is_file():
        previous = target.read_bytes()
        if previous == temporary.read_bytes():
            temporary.unlink()
            return None
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(f"{target.name}.bak-{stamp}-{secrets.token_hex(6)}")
        with backup.open("xb") as handle:
            handle.write(previous)
            handle.flush()
            os.fsync(handle.fileno())
    os.replace(temporary, target)
    return backup


__all__ = [
    "CALENDAR_BACKENDS",
    "ENV_FILENAME",
    "ENV_KEYS",
    "HOUSEHOLD_FILENAME",
    "HOUSEHOLD_RULE_SCOPES",
    "LAUNCH_CONFIG_SCHEMA",
    "PROFILE_RULE_SCOPES",
    "RULE_KEYS",
    "SETUP_PURPOSES",
    "SetupAppError",
    "SetupApplication",
    "default_config_dir",
    "default_profiles_dir",
    "is_template_directory",
    "empty_profile_configuration",
    "profile_templates",
    "read_env_file",
    "write_env_file",
]
