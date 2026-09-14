#!/usr/bin/env python3
"""Interactive and headless starter module for FolderHome and Setup.

Provides numbered choices for FolderHome, Setup, both, and language selection.
Accepts numbers or names, defaults to English, persists language preference to
<config>/start_menu.json, honors FOLDERHOME_CONFIG_DIR, and strictly adheres to
security boundaries:
- Network and cloud data gates are never granted automatically.
- Remote / cloud presets require explicit confirmation (y/N).
- Ollama model presets receive --model-timeout-seconds 600.
- Subprocesses and URLs are safely supervised and verified upon cleanup.
- Supports dry-run, headless execution, wrapper script installation, and packaging.
"""

from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

MENU_CONFIG_SCHEMA = "folderhome.start-menu-config.v1"
MENU_CONFIG_FILENAME = "start_menu.json"
LAUNCH_CONFIG_FILENAME = "launch.json"
DEFAULT_LANGUAGE = "en"
DEFAULT_OLLAMA_TIMEOUT = 600
DEFAULT_APP_PORT = 8765
DEFAULT_SETUP_PORT = 8766

HOSTED_PROVIDERS = frozenset({"bedrock", "anthropic", "openai"})


def is_loopback_host(host: str | None) -> bool:
    """Return True only for localhost or a literal IP loopback address."""
    if not host or not isinstance(host, str):
        return False
    raw = host.strip()
    if not raw:
        return False
    direct_candidate = raw.strip("[]")
    if direct_candidate.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(direct_candidate).is_loopback
    except ValueError:
        pass

    try:
        parsed = urlsplit(raw) if "://" in raw or raw.startswith("//") else urlsplit("//" + raw)
        hostname = parsed.hostname
    except ValueError:
        return False
    if not hostname:
        return False
    clean = hostname.strip("[]").lower()
    if clean == "localhost":
        return True
    try:
        return ipaddress.ip_address(clean).is_loopback
    except ValueError:
        return False


TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "title": "=== FolderHome Starter ===",
        "option_1": "(1) FolderHome",
        "option_2": "(2) Setup",
        "option_3": "(3) both",
        "option_4": "(4) language",
        "option_quit": "(q) quit",
        "prompt_choice": "Select an option [1-4, q]: ",
        "invalid_choice": "Unknown option '{choice}'. Please select 1, 2, 3, 4, or q.",
        "language_menu_title": "Select language / Sprache wählen:",
        "language_opt_en": "(1) English",
        "language_opt_de": "(2) Deutsch",
        "language_prompt": "Choice [1-2, default: 1]: ",
        "language_changed": "Language set to English.",
        "config_dir_info": "Using configuration directory: {path}",
        "launching_app": "Starting FolderHome...",
        "launching_setup": "Starting Setup...",
        "launching_both": "Starting FolderHome and Setup...",
        "starter_missing": (
            "{script} was not found in config dir or scripts. "
            "Subprocess will not be started."
        ),
        "app_url": "FolderHome URL: {url}",
        "setup_url": "Setup URL: {url}",
        "remote_cloud_detected": (
            "Remote/cloud model preset '{preset}' (provider: {provider}) detected."
        ),
        "gate_confirmation": (
            "Do you want to grant network access and sensitive cloud data approval? (y/N): "
        ),
        "gates_granted": "Network and cloud data gates approved.",
        "gates_denied": "No network or cloud gates granted (fail-closed).",
        "ollama_timeout_applied": "Applied Ollama model timeout: {timeout}s",
        "stopping_processes": "\nStopping background processes...",
        "processes_stopped": "All processes stopped.",
        "dry_run_notice": "[Dry-run] Operation completed without launching subprocesses.",
        "quitting": "Exiting starter menu.",
    },
    "de": {
        "title": "=== FolderHome Starter ===",
        "option_1": "(1) FolderHome",
        "option_2": "(2) Setup",
        "option_3": "(3) beides",
        "option_4": "(4) Sprache",
        "option_quit": "(q) Beenden",
        "prompt_choice": "Option auswählen [1-4, q]: ",
        "invalid_choice": "Unbekannte Option '{choice}'. Bitte 1, 2, 3, 4 oder q wählen.",
        "language_menu_title": "Sprache wählen / Select language:",
        "language_opt_en": "(1) English",
        "language_opt_de": "(2) Deutsch",
        "language_prompt": "Auswahl [1-2, Standard: 1]: ",
        "language_changed": "Sprache auf Deutsch gesetzt.",
        "config_dir_info": "Verwende Konfigurationsordner: {path}",
        "launching_app": "Starte FolderHome...",
        "launching_setup": "Starte Setup...",
        "launching_both": "Starte FolderHome und Setup...",
        "starter_missing": (
            "{script} wurde im Konfigurationsordner oder in scripts nicht gefunden. "
            "Subprozess wird nicht gestartet."
        ),
        "app_url": "FolderHome URL: {url}",
        "setup_url": "Setup URL: {url}",
        "remote_cloud_detected": (
            "Remote-/Cloud-Modell-Preset '{preset}' (Anbieter: {provider}) erkannt."
        ),
        "gate_confirmation": (
            "Möchtest du Netzwerkfreigabe und Freigabe sensibler Cloud-Daten erteilen? (y/N): "
        ),
        "gates_granted": "Netzwerk- und Cloud-Datenfreigabe erteilt.",
        "gates_denied": "Keine Netzwerk- oder Cloud-Freigabe erteilt (Fail-Closed).",
        "ollama_timeout_applied": "Ollama-Modell-Timeout angewendet: {timeout}s",
        "stopping_processes": "\nBeende Hintergrundprozesse...",
        "processes_stopped": "Alle Prozesse beendet.",
        "dry_run_notice": "[Dry-run] Vorgang abgeschlossen ohne Subprozesse zu starten.",
        "quitting": "Starter-Menü beendet.",
    },
}


def get_text(lang: str, key: str, **kwargs: Any) -> str:
    bundle = TEXTS.get(lang) or TEXTS[DEFAULT_LANGUAGE]
    template = bundle.get(key) or TEXTS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


START_APP_WRAPPER_TEMPLATE = """\
@echo off
setlocal
set "ROOT=%~dp0.."
set "PYTHON="
if exist "%ROOT%\\.venv\\Scripts\\python.exe" (
    set "PYTHON=%ROOT%\\.venv\\Scripts\\python.exe"
)
if not defined PYTHON if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\\.venv\\Scripts\\python.exe" (
        set "PYTHON=%VIRTUAL_ENV%\\.venv\\Scripts\\python.exe"
    )
    if exist "%VIRTUAL_ENV%\\Scripts\\python.exe" (
        set "PYTHON=%VIRTUAL_ENV%\\Scripts\\python.exe"
    )
)
if not defined PYTHON set "PYTHON=python"
"%PYTHON%" -m folderhome app serve --approve-loopback-server %*
exit /b %errorlevel%
"""

START_SETUP_WRAPPER_TEMPLATE = """\
@echo off
setlocal
set "ROOT=%~dp0.."
set "PYTHON="
if exist "%ROOT%\\.venv\\Scripts\\python.exe" (
    set "PYTHON=%ROOT%\\.venv\\Scripts\\python.exe"
)
if not defined PYTHON if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\\.venv\\Scripts\\python.exe" (
        set "PYTHON=%VIRTUAL_ENV%\\.venv\\Scripts\\python.exe"
    )
    if exist "%VIRTUAL_ENV%\\Scripts\\python.exe" (
        set "PYTHON=%VIRTUAL_ENV%\\Scripts\\python.exe"
    )
)
if not defined PYTHON set "PYTHON=python"
"%PYTHON%" -m folderhome setup serve --approve-loopback-server %*
exit /b %errorlevel%
"""


def install_starter_wrappers(target_dir: Path, *, overwrite: bool = False) -> list[Path]:
    """Install standard starter wrapper scripts into target_dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    app_script = target_dir / "START-APP.cmd"
    if overwrite or not app_script.exists():
        app_script.write_text(START_APP_WRAPPER_TEMPLATE, encoding="ascii")
        installed.append(app_script)
    setup_script = target_dir / "START-SETUP.cmd"
    if overwrite or not setup_script.exists():
        setup_script.write_text(START_SETUP_WRAPPER_TEMPLATE, encoding="ascii")
        installed.append(setup_script)
    return installed


def resolve_config_dir(explicit_dir: str | Path | None = None) -> Path:
    if explicit_dir is not None:
        return Path(explicit_dir).resolve()
    env_dir = os.environ.get("FOLDERHOME_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    # Path(__file__) is src/folderhome/starter.py -> parents[2] is repo root
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / ".local-state" / "config").resolve()


def load_menu_config(config_dir: Path) -> dict[str, Any]:
    path = config_dir / MENU_CONFIG_FILENAME
    if not path.is_file():
        return {"language": DEFAULT_LANGUAGE}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"language": DEFAULT_LANGUAGE}


def save_menu_language(config_dir: Path, language: str) -> None:
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        path = config_dir / MENU_CONFIG_FILENAME
        current = load_menu_config(config_dir)
        current["schema"] = MENU_CONFIG_SCHEMA
        current["language"] = language
        path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def find_starter_script(name: str, config_dir: Path) -> Path | None:
    candidate = config_dir / name
    if candidate.is_file():
        return candidate
    candidate = config_dir / "scripts" / name
    if candidate.is_file():
        return candidate
    # If installed in repository worktree, search scripts/ in repo root
    repo_root = Path(__file__).resolve().parents[2]
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        candidate = scripts_dir / name
        if candidate.is_file():
            return candidate
    candidate = repo_root / name
    if candidate.is_file():
        return candidate
    return None


def inspect_launch_config(launch_path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "exists": False,
        "preset": None,
        "provider": "fixture",
        "is_ollama": False,
        "is_remote_or_cloud": False,
    }
    if not launch_path.is_file():
        return info

    try:
        payload = json.loads(launch_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return info

    if not isinstance(payload, dict):
        return info

    info["exists"] = True
    model_preset = payload.get("model_preset")
    if isinstance(model_preset, str) and model_preset.strip():
        info["preset"] = model_preset.strip()

    preset_dict: dict[str, Any] = {}
    presets = payload.get("model_presets")
    if isinstance(presets, dict) and info["preset"] in presets:
        raw_entry = presets[info["preset"]]
        if isinstance(raw_entry, dict):
            preset_dict = raw_entry

    provider = payload.get("model_provider") or preset_dict.get("model_provider") or "fixture"
    info["provider"] = str(provider)

    preset_name_lower = (info["preset"] or "").lower()
    is_ollama = (
        info["provider"] == "ollama"
        or "ollama" in preset_name_lower
    )
    info["is_ollama"] = is_ollama

    is_remote_or_cloud = False
    if info["provider"] in HOSTED_PROVIDERS:
        is_remote_or_cloud = True
    elif info["provider"] == "ollama" or info["is_ollama"]:
        raw_host = payload.get("ollama_host") or preset_dict.get("ollama_host")
        if raw_host is not None:
            is_remote_or_cloud = not is_loopback_host(str(raw_host))

    info["is_remote_or_cloud"] = is_remote_or_cloud
    return info


def normalize_action(raw: str) -> str | None:
    token = raw.strip().lower()
    if token in (
        "1", "folderhome", "app", "folder-home", "1. folderhome", "1 folderhome"
    ):
        return "1"
    if token in ("2", "setup", "einrichtung", "2. setup", "2 setup"):
        return "2"
    if token in ("3", "both", "beides", "3. both", "3 both", "3. beides", "3 beides"):
        return "3"
    if token in (
        "4", "language", "sprache", "lang",
        "4. language", "4 language", "4. sprache", "4 sprache",
    ):
        return "4"
    if token in ("q", "quit", "exit", "beenden", "stop", "close"):
        return "q"
    return None


normalize_choice = normalize_action


_URL_PATTERN = re.compile(r'(?:https?://|[a-zA-Z0-9_.-]+:[^\s@/]+@)[^\s"\'<>\\]+')
_USERINFO_PATTERN = re.compile(r"([a-zA-Z0-9_.+-]+):([^@\s/:]+)@")
_AUTH_HEADER_PATTERN = re.compile(r"(?i)\b(authorization\s*:\s*)[^\r\n]+")
_SIGV4_CRED_PATTERN = re.compile(r"(?i)\b(credential\s*=\s*)[^\s,;'\"]+")
_SIGV4_SIG_PATTERN = re.compile(r"(?i)\b(signature\s*=\s*)[^\s,;'\"]+")
_SIGV4_SIGNED_PATTERN = re.compile(r"(?i)\b(signedheaders\s*=\s*)[^\s,;'\"]+")
_BEARER_PATTERN = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.~+/]+=*")
_BASIC_PATTERN = re.compile(r"(?i)\b(basic\s+)[A-Za-z0-9+/=]{4,}")
_JSON_SECRET_PATTERN = re.compile(
    r'''(?ix)
    (
        "(?:[a-z0-9]+[_-])*
        (?:api[_-]?key|secret(?:[_-](?:access[_-]?key|key))?|password|passwd|
           session[_-]?token|access[_-]?token|auth[_-]?token|token|
           access[_-]?key[_-]?id)"\s*:\s*"
    )
    (?:\\.|[^"\\])*
    (")
    '''
)
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r'''(?ix)
    (?<![\w-])
    (
        (?:[a-z0-9]+[_-])*
        (?:api[_-]?key|secret(?:[_-](?:access[_-]?key|key))?|password|passwd|
           session[_-]?token|access[_-]?token|auth[_-]?token|token|
           access[_-]?key[_-]?id)
    )
    (?![\w-])
    (\s*(?:=|:)\s*)
    ("(?:\\.|[^"\r\n])*"|'(?:\\.|[^'\r\n])*'|[^\s,;]+)
    '''
)
_QUERY_SECRET_PATTERN = re.compile(
    r"(?i)([?&](?:token|api[_-]?key|secret|password|passwd|auth[_-]?token|access[_-]?token|sig|signature)=)[^&\s\"'<>\\]+"
)


def redact_url_credentials(url: str | None) -> str:
    """Redact query parameters (such as tokens) and credentials for safe exposure."""
    if not url or not isinstance(url, str) or not url.strip():
        return ""
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return ""
    if not parsed.scheme or not hostname:
        return ""
    if port is not None and not (1 <= port <= 65535):
        return ""
    host = f"[{hostname}]" if ":" in hostname else hostname
    port_str = f":{port}" if port is not None else ""
    return f"{parsed.scheme}://{host}{port_str}{parsed.path}"


def redact_diagnostics(text: str | None) -> str:
    """Centrally redact tokens, credentials, and sensitive URLs from diagnostics."""
    if not text or not isinstance(text, str):
        return ""

    def _replace_url(match: re.Match[str]) -> str:
        raw_url = match.group(0)
        trailing = ""
        while raw_url and raw_url[-1] in ".,;:!?)":
            trailing = raw_url[-1] + trailing
            raw_url = raw_url[:-1]

        if not raw_url.startswith(("http://", "https://")):
            return "[REDACTED_URL]" + trailing

        redacted = redact_url_credentials(raw_url)
        if not redacted:
            return "[REDACTED_URL]" + trailing
        return redacted + trailing

    def _replace_assignment(match: re.Match[str]) -> str:
        value = match.group(3)
        quote = value[0] if value and value[0] in "\"'" else ""
        return f"{match.group(1)}{match.group(2)}{quote}[REDACTED]{quote}"

    cleaned = _AUTH_HEADER_PATTERN.sub(r"\1[REDACTED]", text)
    cleaned = _URL_PATTERN.sub(_replace_url, cleaned)
    cleaned = _USERINFO_PATTERN.sub(r"\1:[REDACTED]@", cleaned)
    cleaned = _SIGV4_CRED_PATTERN.sub(r"\1[REDACTED]", cleaned)
    cleaned = _SIGV4_SIG_PATTERN.sub(r"\1[REDACTED]", cleaned)
    cleaned = _SIGV4_SIGNED_PATTERN.sub(r"\1[REDACTED]", cleaned)
    cleaned = _BEARER_PATTERN.sub(r"\1[REDACTED]", cleaned)
    cleaned = _BASIC_PATTERN.sub(r"\1[REDACTED]", cleaned)
    cleaned = _JSON_SECRET_PATTERN.sub(r"\1[REDACTED]\2", cleaned)
    cleaned = _SENSITIVE_ASSIGNMENT_PATTERN.sub(_replace_assignment, cleaned)
    cleaned = _QUERY_SECRET_PATTERN.sub(r"\1[REDACTED]", cleaned)
    return cleaned


def validate_access_url(url: str) -> str | None:
    """Validate that access URL is an HTTP loopback URL containing a non-empty session token."""
    if not url or not isinstance(url, str):
        return "Missing or empty access URL"
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return "Malformed access URL or invalid port"

    if scheme.lower() != "http":
        return f"Access URL must use HTTP scheme, got: {scheme}"

    if not is_loopback_host(hostname):
        return "Access URL must target loopback host"

    if port is None or not (1 <= port <= 65535):
        return "Access URL must include a valid port"

    try:
        query_params = parse_qs(parsed.query, keep_blank_values=True)
    except Exception:
        return "Malformed query parameters in access URL"

    tokens = query_params.get("token")
    if not tokens or not tokens[0].strip():
        return "Access URL must contain non-empty session token in query parameter"

    return None


class ProcessOutputHandler:
    def __init__(self, proc: Any, target_name: str) -> None:
        self.proc = proc
        self.target_name = target_name
        self.stdout_queue: queue.Queue[str | None] = queue.Queue()
        self.stderr_lines: list[str] = []
        self.access_url: str | None = None
        self.error_message: str | None = None
        self.stream_closed: bool = False

        self.stdout_thread = threading.Thread(
            target=self._read_stdout, daemon=True
        )
        self.stderr_thread = threading.Thread(
            target=self._read_stderr, daemon=True
        )
        self.stdout_thread.start()
        self.stderr_thread.start()

    def _read_stdout(self) -> None:
        try:
            stream = getattr(self.proc, "stdout", None)
            if stream is not None:
                for raw_line in iter(stream.readline, ""):
                    if not raw_line:
                        break
                    if isinstance(raw_line, str):
                        line = raw_line
                    else:
                        line = raw_line.decode("utf-8", errors="replace")
                    self.stdout_queue.put(line)
        except Exception:
            pass
        finally:
            self.stdout_queue.put(None)

    def _read_stderr(self) -> None:
        try:
            stream = getattr(self.proc, "stderr", None)
            if stream is not None:
                for raw_line in iter(stream.readline, ""):
                    if not raw_line:
                        break
                    if isinstance(raw_line, str):
                        line = raw_line
                    else:
                        line = raw_line.decode("utf-8", errors="replace")
                    sanitized = redact_diagnostics(line.rstrip())
                    self.stderr_lines.append(sanitized)
                    if len(self.stderr_lines) > 100:
                        self.stderr_lines.pop(0)
        except Exception:
            pass

    def _check_line(self, line: str) -> tuple[str | None, str | None]:
        stripped = line.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            return None, None
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return None, None

        if not isinstance(data, dict):
            return None, None

        if "access_url" not in data:
            return None, None

        raw_url = data.get("access_url")
        if not isinstance(raw_url, str):
            return None, f"Invalid access_url in JSON from {self.target_name}"

        try:
            val_err = validate_access_url(raw_url)
        except Exception:
            val_err = f"Malformed access_url from {self.target_name}"

        if val_err:
            return None, redact_diagnostics(val_err)

        return raw_url, None

    def poll_bootstrap(self) -> tuple[str | None, str | None]:
        """Poll for access_url or error without long blocking."""
        if self.access_url is not None:
            return self.access_url, None
        if self.error_message is not None:
            return None, self.error_message

        while not self.stdout_queue.empty():
            try:
                line = self.stdout_queue.get_nowait()
            except queue.Empty:
                break

            if line is None:
                self.stream_closed = True
                err_msg = redact_diagnostics("\n".join(self.stderr_lines).strip())
                detail = f": {err_msg}" if err_msg else ""
                self.error_message = (
                    f"Subprocess {self.target_name} closed output stream without "
                    f"emitting access_url{detail}"
                )
                return None, self.error_message

            url, err = self._check_line(line)
            if err:
                self.error_message = redact_diagnostics(err)
                return None, self.error_message
            if url:
                self.access_url = url
                return self.access_url, None

        return None, None

    def wait_for_bootstrap(self, timeout: float = 15.0) -> tuple[str | None, str | None]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if hasattr(self.proc, "poll"):
                code = self.proc.poll()
                if code is not None:
                    err_msg = redact_diagnostics("\n".join(self.stderr_lines).strip())
                    detail = f": {err_msg}" if err_msg else ""
                    return None, (
                        f"Subprocess {self.target_name} exited prematurely with "
                        f"code {code}{detail}"
                    )

            url, err = self.poll_bootstrap()
            if err:
                return None, redact_diagnostics(err)
            if url:
                return url, None

            time.sleep(0.02)

        err_msg = redact_diagnostics("\n".join(self.stderr_lines).strip())
        detail = f": {err_msg}" if err_msg else ""
        return None, (
            f"Timed out after {timeout}s waiting for access_url from "
            f"{self.target_name}{detail}"
        )


class StartMenuController:
    def __init__(
        self,
        config_dir: Path,
        *,
        language: str | None = None,
        dry_run: bool = False,
        confirm_gates: bool | None = None,
        open_browser: bool = True,
        bootstrap_timeout: float = 15.0,
        input_func: Callable[[str], str] = input,
        print_func: Callable[..., None] = print,
        subprocess_runner: Callable[..., Any] = subprocess.Popen,
        browser_opener: Callable[[str], bool] = webbrowser.open,
    ) -> None:
        self.config_dir = config_dir
        self.dry_run = dry_run
        self.confirm_gates = confirm_gates
        self.open_browser = open_browser
        self.bootstrap_timeout = bootstrap_timeout
        self.input_func = input_func
        self.print_func = print_func
        self.subprocess_runner = subprocess_runner
        self.browser_opener = browser_opener

        if language in ("en", "de"):
            self.language = language
            if not self.dry_run:
                save_menu_language(self.config_dir, language)
        else:
            loaded = load_menu_config(self.config_dir)
            loaded_lang = loaded.get("language")
            self.language = loaded_lang if loaded_lang in ("en", "de") else DEFAULT_LANGUAGE

        self.processes: list[Any] = []

    def t(self, key: str, **kwargs: Any) -> str:
        return get_text(self.language, key, **kwargs)

    def change_language_flow(self) -> None:
        self.print_func(self.t("language_menu_title"))
        self.print_func(self.t("language_opt_en"))
        self.print_func(self.t("language_opt_de"))
        try:
            choice = self.input_func(self.t("language_prompt")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return

        if choice in ("2", "de", "deutsch"):
            self.language = "de"
        else:
            self.language = "en"

        if not self.dry_run:
            save_menu_language(self.config_dir, self.language)
        self.print_func(self.t("language_changed"))

    def resolve_app_command_and_url(self) -> tuple[list[str] | None, str | None, str | None]:
        starter = find_starter_script("START-APP.cmd", self.config_dir)
        if starter is None:
            return None, None, self.t("starter_missing", script="START-APP.cmd")

        launch_path = self.config_dir / LAUNCH_CONFIG_FILENAME
        info = inspect_launch_config(launch_path)

        cmd = [str(starter), "--json"]
        if info["exists"]:
            cmd.extend(["--launch-config", str(launch_path)])

        if info["is_ollama"]:
            cmd.extend(["--model-timeout-seconds", str(DEFAULT_OLLAMA_TIMEOUT)])
            self.print_func(self.t("ollama_timeout_applied", timeout=DEFAULT_OLLAMA_TIMEOUT))

        allow_gates = False
        if info["is_remote_or_cloud"]:
            self.print_func(
                self.t(
                    "remote_cloud_detected",
                    preset=info["preset"] or "unnamed",
                    provider=info["provider"],
                )
            )
            if self.confirm_gates is True:
                allow_gates = True
            elif self.confirm_gates is False:
                allow_gates = False
            else:
                try:
                    ans = self.input_func(self.t("gate_confirmation")).strip().lower()
                    allow_gates = ans in ("y", "yes", "j", "ja")
                except (EOFError, KeyboardInterrupt):
                    allow_gates = False

            if allow_gates:
                cmd.extend(["--allow-network", "--approve-sensitive-cloud-data"])
                self.print_func(self.t("gates_granted"))
            else:
                self.print_func(self.t("gates_denied"))

        return cmd, None, None

    def resolve_setup_command_and_url(self) -> tuple[list[str] | None, str | None, str | None]:
        starter = find_starter_script("START-SETUP.cmd", self.config_dir)
        if starter is None:
            return None, None, self.t("starter_missing", script="START-SETUP.cmd")

        cmd = [str(starter), "--config-dir", str(self.config_dir), "--json"]
        return cmd, None, None

    def run_action(self, action_key: str) -> int:
        norm = normalize_action(action_key)
        if norm == "4":
            self.change_language_flow()
            return 0
        if norm == "q":
            self.print_func(self.t("quitting"))
            return 0

        ResolverFn = Callable[[], tuple[list[str] | None, str | None, str | None]]
        targets: list[tuple[str, str, ResolverFn]] = []
        if norm == "1":
            targets.append(("app", self.t("launching_app"), self.resolve_app_command_and_url))
        elif norm == "2":
            targets.append(("setup", self.t("launching_setup"), self.resolve_setup_command_and_url))
        elif norm == "3":
            targets.append(("app", self.t("launching_app"), self.resolve_app_command_and_url))
            targets.append(("setup", self.t("launching_setup"), self.resolve_setup_command_and_url))
        else:
            self.print_func(self.t("invalid_choice", choice=action_key))
            return 1

        has_error = False
        commands_to_run: list[tuple[str, list[str]]] = []
        for kind, msg, resolver in targets:
            self.print_func(msg)
            cmd, _, err = resolver()
            if err:
                self.print_func(err)
                has_error = True
            elif cmd:
                commands_to_run.append((kind, cmd))

        if has_error or not commands_to_run:
            return 1

        for _kind, cmd in commands_to_run:
            if "--json" not in cmd:
                cmd.append("--json")

        if self.dry_run:
            for _, cmd in commands_to_run:
                self.print_func(f"[Dry-run Command] {' '.join(cmd)}")
            self.print_func(self.t("dry_run_notice"))
            return 0

        exit_code = 0
        try:
            started_entries: list[tuple[str, Any, ProcessOutputHandler]] = []
            for kind, cmd in commands_to_run:
                try:
                    proc = self.subprocess_runner(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                    )
                except TypeError:
                    try:
                        proc = self.subprocess_runner(cmd)
                    except OSError as exc:
                        self.print_func(f"Failed to start subprocess: {exc}")
                        has_error = True
                        break
                except OSError as exc:
                    self.print_func(f"Failed to start subprocess: {exc}")
                    has_error = True
                    break

                self.processes.append(proc)
                handler = ProcessOutputHandler(proc, kind)
                started_entries.append((kind, proc, handler))

            if has_error or len(started_entries) != len(commands_to_run):
                self.cleanup_processes()
                return 1

            # Concurrent bootstrap of all started processes
            deadline = time.monotonic() + self.bootstrap_timeout
            validated_urls: dict[str, str] = {}
            exit_code = 0

            while time.monotonic() < deadline:
                # 1. Concurrently check if ANY child process has terminated prematurely
                for kind, proc, handler in started_entries:
                    if hasattr(proc, "poll"):
                        code = proc.poll()
                        if code is not None:
                            has_error = True
                            if code != 0:
                                exit_code = code
                                lines_text = "\n".join(handler.stderr_lines).strip()
                                err_msg = redact_diagnostics(lines_text)
                                detail = f": {err_msg}" if err_msg else ""
                                self.print_func(
                                    f"Subprocess {kind} exited prematurely with code {code}{detail}"
                                )
                            else:
                                exit_code = 1
                                self.print_func(
                                    f"Subprocess {kind} exited prematurely before browser launch."
                                )
                            break

                if has_error:
                    break

                # 2. Check output from all handlers concurrently
                for kind, proc, handler in started_entries:
                    if kind not in validated_urls:
                        url, err = handler.poll_bootstrap()
                        if err:
                            self.print_func(redact_diagnostics(err))
                            has_error = True
                            code = proc.poll() if hasattr(proc, "poll") else None
                            exit_code = code if code not in (0, None) else 1
                            break
                        if url:
                            validated_urls[kind] = url

                if has_error:
                    break

                # 3. Check if all started processes have yielded their validated access_url
                if len(validated_urls) == len(commands_to_run):
                    break

                time.sleep(0.02)

            if not has_error and len(validated_urls) != len(commands_to_run):
                has_error = True
                if exit_code == 0:
                    exit_code = 1
                for kind, _proc, handler in started_entries:
                    if kind not in validated_urls:
                        err_msg = redact_diagnostics("\n".join(handler.stderr_lines).strip())
                        detail = f": {err_msg}" if err_msg else ""
                        self.print_func(
                            f"Timed out waiting for access_url from {kind}{detail}"
                        )

            if has_error or len(validated_urls) != len(commands_to_run):
                self.cleanup_processes()
                return exit_code if exit_code != 0 else 1

            # Print sanitized loopback URLs (no session tokens) to console and open in browser
            for kind, _ in commands_to_run:
                url = validated_urls[kind]
                sanitized_url = redact_url_credentials(url)
                if kind == "app":
                    self.print_func(self.t("app_url", url=sanitized_url))
                else:
                    self.print_func(self.t("setup_url", url=sanitized_url))

            if self.open_browser:
                # Joint pre-browser alive check of all processes before opening any browser
                for check_kind, check_proc, check_handler in started_entries:
                    if hasattr(check_proc, "poll"):
                        check_code = check_proc.poll()
                        if check_code is not None:
                            has_error = True
                            if check_code != 0 and exit_code == 0:
                                exit_code = check_code
                            elif exit_code == 0:
                                exit_code = 1
                            lines_text = "\n".join(check_handler.stderr_lines).strip()
                            err_msg = redact_diagnostics(lines_text)
                            detail = f": {err_msg}" if err_msg else ""
                            if check_code != 0:
                                msg = (
                                    f"Subprocess {check_kind} exited prematurely with code "
                                    f"{check_code}{detail}"
                                )
                            else:
                                msg = (
                                    f"Subprocess {check_kind} exited prematurely before "
                                    "browser launch."
                                )
                            self.print_func(msg)
                            break
                if has_error:
                    self.cleanup_processes()
                    return exit_code if exit_code != 0 else 1

                for kind, _ in commands_to_run:
                    # Check ALL started processes together before each browser call
                    for check_kind, check_proc, check_handler in started_entries:
                        if hasattr(check_proc, "poll"):
                            check_code = check_proc.poll()
                            if check_code is not None:
                                has_error = True
                                if check_code != 0 and exit_code == 0:
                                    exit_code = check_code
                                elif exit_code == 0:
                                    exit_code = 1
                                lines_text = "\n".join(check_handler.stderr_lines).strip()
                                err_msg = redact_diagnostics(lines_text)
                                detail = f": {err_msg}" if err_msg else ""
                                if check_code != 0:
                                    msg = (
                                        f"Subprocess {check_kind} exited prematurely with code "
                                        f"{check_code}{detail}"
                                    )
                                else:
                                    msg = (
                                        f"Subprocess {check_kind} exited prematurely before "
                                        "browser launch."
                                    )
                                self.print_func(msg)
                                break
                    if has_error:
                        break

                    url = validated_urls[kind]
                    try:
                        opened = self.browser_opener(url)
                        if opened is False:
                            has_error = True
                            if exit_code == 0:
                                exit_code = 1
                            self.print_func(f"Failed to open browser for {kind} URL.")
                            break
                    except Exception as exc:
                        has_error = True
                        if exit_code == 0:
                            exit_code = 1
                        err_detail = redact_diagnostics(str(exc))
                        self.print_func(f"Failed to open browser for {kind} URL: {err_detail}")
                        break

            if has_error:
                self.cleanup_processes()
                return exit_code if exit_code != 0 else 1

            # Supervision loop: monitor processes until completion or error
            while True:
                # Option 3 & general supervision: detect premature or non-zero child exit
                terminated_procs = [
                    (p, p.poll())
                    for p in self.processes
                    if hasattr(p, "poll") and p.poll() is not None
                ]

                # Single process mode (Option 1/2): terminates with child's exit code
                if len(self.processes) == 1 and terminated_procs:
                    exit_code = terminated_procs[0][1] or 0
                    break
                elif len(self.processes) > 1 and terminated_procs:
                    # Multi-process mode (Option 3):
                    # Any premature exit of a long-lived child (even exit code 0) must be
                    # treated as an error: siblings must be terminated, non-zero returncode.
                    # Only intentional Ctrl+C/menu lifecycle may exit cleanly with code 0.
                    non_zero = [(p, c) for p, c in terminated_procs if c != 0]
                    exit_code = non_zero[0][1] if non_zero else 1
                    break

                time.sleep(0.05)
        except KeyboardInterrupt:
            self.print_func(self.t("stopping_processes"))
            exit_code = 0
        finally:
            cleaned = self.cleanup_processes()
            if not cleaned and exit_code == 0:
                exit_code = 1

        return exit_code

    def cleanup_processes(self) -> bool:
        had_processes = bool(self.processes)
        unverified_processes: set[Any] = set()

        for p in list(self.processes):
            if hasattr(p, "poll") and p.poll() is None:
                pid = getattr(p, "pid", None)
                if (
                    sys.platform == "win32"
                    and isinstance(pid, int)
                    and pid > 0
                    and isinstance(p, subprocess.Popen)
                ):
                    try:
                        res = subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        taskkill_error = (res.stderr or "").strip()
                        if res.returncode != 0 or taskkill_error:
                            unverified_processes.add(p)
                    except Exception:
                        unverified_processes.add(p)

                try:
                    p.terminate()
                    if hasattr(p, "wait"):
                        try:
                            p.wait(timeout=1.0)
                        except Exception:
                            p.kill()
                            if hasattr(p, "wait"):
                                with contextlib.suppress(Exception):
                                    p.wait(timeout=1.0)
                except Exception:
                    with contextlib.suppress(Exception):
                        p.kill()
                        if hasattr(p, "wait"):
                            p.wait(timeout=1.0)

                if hasattr(p, "poll") and p.poll() is None:
                    unverified_processes.add(p)

        surviving = [
            p
            for p in self.processes
            if (hasattr(p, "poll") and p.poll() is None) or (p in unverified_processes)
        ]
        self.processes = surviving
        if had_processes and not surviving:
            self.print_func(self.t("processes_stopped"))
        return len(self.processes) == 0

    def interactive_loop(self) -> int:
        while True:
            self.print_func(self.t("title"))
            self.print_func(self.t("config_dir_info", path=str(self.config_dir)))
            self.print_func(self.t("option_1"))
            self.print_func(self.t("option_2"))
            self.print_func(self.t("option_3"))
            self.print_func(self.t("option_4"))
            self.print_func(self.t("option_quit"))

            try:
                raw = self.input_func(self.t("prompt_choice"))
            except (EOFError, KeyboardInterrupt):
                self.print_func(f"\n{self.t('quitting')}")
                return 0

            norm = normalize_action(raw)
            if norm is None:
                self.print_func(self.t("invalid_choice", choice=raw.strip()))
                continue

            if norm == "4":
                self.change_language_flow()
                continue

            if norm == "q":
                self.print_func(self.t("quitting"))
                return 0

            return self.run_action(norm)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="start_menu",
        description="FolderHome and Setup Starter Menu",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="Path to folderhome configuration directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute in dry-run mode without spawning subprocesses or modifying user state",
    )
    parser.add_argument(
        "--action",
        "--choice",
        dest="action",
        help="Run a specific action directly (1/folderhome, 2/setup, 3/both, 4/language, q/quit)",
    )
    parser.add_argument(
        "--language",
        choices=("en", "de"),
        help="Preset language for the menu (en or de)",
    )
    gates_group = parser.add_mutually_exclusive_group()
    gates_group.add_argument(
        "--confirm-gates",
        action="store_true",
        default=None,
        help="Explicitly approve network and cloud gates for remote/cloud presets",
    )
    gates_group.add_argument(
        "--deny-gates",
        action="store_true",
        default=None,
        help="Explicitly deny network and cloud gates for remote/cloud presets",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open URLs in standard browser",
    )
    parser.add_argument(
        "--install-wrappers",
        action="store_true",
        help="Install standard starter wrapper scripts into target directory",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    bootstrap_timeout: float = 15.0,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
    subprocess_runner: Callable[..., Any] = subprocess.Popen,
    browser_opener: Callable[[str], bool] = webbrowser.open,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    config_dir = resolve_config_dir(args.config_dir)

    if args.install_wrappers:
        target = args.config_dir if args.config_dir else (Path(__file__).resolve().parent)
        installed = install_starter_wrappers(target)
        for p in installed:
            print_func(f"Installed starter wrapper: {p}")
        return 0

    confirm_gates: bool | None = None
    if args.confirm_gates:
        confirm_gates = True
    elif args.deny_gates:
        confirm_gates = False

    controller = StartMenuController(
        config_dir=config_dir,
        language=args.language,
        dry_run=args.dry_run,
        confirm_gates=confirm_gates,
        open_browser=not args.no_browser,
        bootstrap_timeout=bootstrap_timeout,
        input_func=input_func,
        print_func=print_func,
        subprocess_runner=subprocess_runner,
        browser_opener=browser_opener,
    )

    if args.action:
        return controller.run_action(args.action)

    return controller.interactive_loop()


if __name__ == "__main__":
    sys.exit(main())
