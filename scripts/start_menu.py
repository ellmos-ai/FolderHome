#!/usr/bin/env python3
"""Interactive and headless start menu for FolderHome and Setup.

Provides numbered choices for FolderHome, Setup, both, and language selection.
Accepts numbers or names, defaults to English, persists language preference to
<config>/start_menu.json, honors FOLDERHOME_CONFIG_DIR, and strictly adheres to
security boundaries:
- Network and cloud data gates are never granted automatically.
- Remote / cloud presets require explicit confirmation (y/N).
- Ollama model presets receive --model-timeout-seconds 600.
- Subprocesses and URLs are only handled if START-APP.cmd and START-SETUP.cmd exist.
- Supports dry-run and headless execution without user configuration.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MENU_CONFIG_SCHEMA = "folderhome.start-menu-config.v1"
MENU_CONFIG_FILENAME = "start_menu.json"
LAUNCH_CONFIG_FILENAME = "launch.json"
DEFAULT_LANGUAGE = "en"
DEFAULT_OLLAMA_TIMEOUT = 600
DEFAULT_APP_PORT = 8765
DEFAULT_SETUP_PORT = 8766

HOSTED_PROVIDERS = frozenset({"bedrock", "anthropic", "openai"})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def is_loopback_host(host: str | None) -> bool:
    """Return True only if host strictly targets 127.0.0.1, localhost, or ::1."""
    if not host or not isinstance(host, str):
        return False
    raw = host.strip()
    if not raw:
        return False
    try:
        parsed = urlsplit(raw) if "://" in raw or raw.startswith("//") else urlsplit("//" + raw)
        hostname = parsed.hostname
    except ValueError:
        return False

    if not hostname:
        clean = raw.strip("[]").lower()
        return clean in LOOPBACK_HOSTS

    clean = hostname.strip("[]").lower()
    return clean in LOOPBACK_HOSTS


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


def resolve_config_dir(explicit_dir: str | Path | None = None) -> Path:
    if explicit_dir is not None:
        return Path(explicit_dir).resolve()
    env_dir = os.environ.get("FOLDERHOME_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    repo_root = Path(__file__).resolve().parent.parent
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
    scripts_dir = Path(__file__).resolve().parent
    candidate = scripts_dir / name
    if candidate.is_file():
        return candidate
    repo_root = scripts_dir.parent
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


class StartMenuController:
    def __init__(
        self,
        config_dir: Path,
        *,
        language: str | None = None,
        dry_run: bool = False,
        confirm_gates: bool | None = None,
        open_browser: bool = True,
        input_func: Callable[[str], str] = input,
        print_func: Callable[..., None] = print,
        subprocess_runner: Callable[..., Any] = subprocess.Popen,
        browser_opener: Callable[[str], bool] = webbrowser.open,
    ) -> None:
        self.config_dir = config_dir
        self.dry_run = dry_run
        self.confirm_gates = confirm_gates
        self.open_browser = open_browser
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

        cmd = [str(starter)]
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

        url = f"http://127.0.0.1:{DEFAULT_APP_PORT}/"
        return cmd, url, None

    def resolve_setup_command_and_url(self) -> tuple[list[str] | None, str | None, str | None]:
        starter = find_starter_script("START-SETUP.cmd", self.config_dir)
        if starter is None:
            return None, None, self.t("starter_missing", script="START-SETUP.cmd")

        cmd = [str(starter), "--config-dir", str(self.config_dir)]
        url = f"http://127.0.0.1:{DEFAULT_SETUP_PORT}/"
        return cmd, url, None

    def run_action(self, action_key: str) -> int:
        norm = normalize_action(action_key)
        if norm == "4":
            self.change_language_flow()
            return 0
        if norm == "q":
            self.print_func(self.t("quitting"))
            return 0

        ResolverFn = Callable[[], tuple[list[str] | None, str | None, str | None]]
        targets: list[tuple[str, ResolverFn]] = []
        if norm == "1":
            targets.append((self.t("launching_app"), self.resolve_app_command_and_url))
        elif norm == "2":
            targets.append((self.t("launching_setup"), self.resolve_setup_command_and_url))
        elif norm == "3":
            targets.append((self.t("launching_app"), self.resolve_app_command_and_url))
            targets.append((self.t("launching_setup"), self.resolve_setup_command_and_url))
        else:
            self.print_func(self.t("invalid_choice", choice=action_key))
            return 1

        commands_to_run: list[tuple[list[str], str]] = []
        for msg, resolver in targets:
            self.print_func(msg)
            cmd, url, err = resolver()
            if err:
                self.print_func(err)
            elif cmd and url:
                commands_to_run.append((cmd, url))

        if not commands_to_run:
            return 0

        if self.dry_run:
            for cmd, url in commands_to_run:
                self.print_func(f"[Dry-run Command] {' '.join(cmd)}")
                self.print_func(f"[Dry-run URL] {url}")
            self.print_func(self.t("dry_run_notice"))
            return 0

        for cmd, url in commands_to_run:
            if "START-APP" in cmd[0]:
                self.print_func(self.t("app_url", url=url))
            else:
                self.print_func(self.t("setup_url", url=url))

            try:
                proc = self.subprocess_runner(cmd)
                self.processes.append(proc)
            except OSError as exc:
                self.print_func(f"Failed to start subprocess: {exc}")

            if self.open_browser:
                with contextlib.suppress(Exception):
                    self.browser_opener(url)

        if self.processes:
            try:
                while any(p.poll() is None for p in self.processes if hasattr(p, "poll")):
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.print_func(self.t("stopping_processes"))
            finally:
                self.cleanup_processes()
        return 0

    def cleanup_processes(self) -> None:
        for p in self.processes:
            if hasattr(p, "poll") and p.poll() is None:
                try:
                    p.terminate()
                    if hasattr(p, "wait"):
                        p.wait(timeout=2.0)
                except Exception:
                    with contextlib.suppress(Exception):
                        p.kill()
        self.print_func(self.t("processes_stopped"))
        self.processes.clear()

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
    return parser


def main(
    argv: list[str] | None = None,
    *,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
    subprocess_runner: Callable[..., Any] = subprocess.Popen,
    browser_opener: Callable[[str], bool] = webbrowser.open,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    config_dir = resolve_config_dir(args.config_dir)

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
