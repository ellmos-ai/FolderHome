"""Tests for scripts/start_menu.py and scripts/START.cmd.

Covers:
- Pure ASCII validation for START.cmd.
- Menu options 1, 2, 3, 4, quit, and normalization of numeric and name choices.
- English default language and fallback behavior.
- start_menu.json language persistence and schema conformity.
- Explicit network and cloud gates (remote/cloud presets, fail-closed default).
- Ollama 600 second model timeout enforcement.
- Dry-run mode with zero subprocess execution and zero user-config mutation.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
START_MENU_PATH = SCRIPTS_DIR / "start_menu.py"

_spec = importlib.util.spec_from_file_location("start_menu", START_MENU_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load spec from {START_MENU_PATH}")
start_menu = importlib.util.module_from_spec(_spec)
sys.modules["start_menu"] = start_menu
_spec.loader.exec_module(start_menu)

DEFAULT_APP_PORT = start_menu.DEFAULT_APP_PORT
DEFAULT_OLLAMA_TIMEOUT = start_menu.DEFAULT_OLLAMA_TIMEOUT
DEFAULT_SETUP_PORT = start_menu.DEFAULT_SETUP_PORT
MENU_CONFIG_FILENAME = start_menu.MENU_CONFIG_FILENAME
MENU_CONFIG_SCHEMA = start_menu.MENU_CONFIG_SCHEMA
StartMenuController = start_menu.StartMenuController
build_parser = start_menu.build_parser
get_text = start_menu.get_text
inspect_launch_config = start_menu.inspect_launch_config
is_loopback_host = start_menu.is_loopback_host
load_menu_config = start_menu.load_menu_config
main = start_menu.main
normalize_action = start_menu.normalize_action
save_menu_language = start_menu.save_menu_language



# ============================================================================
# 1. START.cmd Pure ASCII Verification
# ============================================================================

def test_start_cmd_remains_pure_ascii() -> None:
    """Verify that scripts/START.cmd exists and contains strictly pure ASCII characters."""
    start_cmd = SCRIPTS_DIR / "START.cmd"
    assert start_cmd.is_file(), f"scripts/START.cmd not found at {start_cmd}"

    raw_bytes = start_cmd.read_bytes()
    assert len(raw_bytes) > 0, "scripts/START.cmd must not be empty"

    non_ascii_bytes = [(i, b) for i, b in enumerate(raw_bytes) if b >= 128]
    assert not non_ascii_bytes, f"Non-ASCII bytes found in START.cmd: {non_ascii_bytes}"

    # Must decode cleanly with strict ASCII codec
    text = raw_bytes.decode("ascii")
    assert "@echo off" in text
    assert "start_menu.py" in text

    # Check root START.cmd if it exists
    root_cmd = REPO_ROOT / "START.cmd"
    if root_cmd.is_file():
        root_raw = root_cmd.read_bytes()
        root_non_ascii = [b for b in root_raw if b >= 128]
        assert not root_non_ascii, f"Non-ASCII bytes in root START.cmd: {root_non_ascii}"
        root_raw.decode("ascii")


# ============================================================================
# 2. Action Normalization (Numeric and Name Choices)
# ============================================================================

@pytest.mark.parametrize(
    ("raw_input", "expected"),
    [
        # Option 1: FolderHome app
        ("1", "1"),
        (" 1 ", "1"),
        ("folderhome", "1"),
        ("FolderHome", "1"),
        ("FOLDERHOME", "1"),
        ("app", "1"),
        ("APP", "1"),
        ("folder-home", "1"),
        ("1. folderhome", "1"),
        ("1 folderhome", "1"),
        # Option 2: Setup
        ("2", "2"),
        (" 2 ", "2"),
        ("setup", "2"),
        ("Setup", "2"),
        ("SETUP", "2"),
        ("einrichtung", "2"),
        ("Einrichtung", "2"),
        ("EINRICHTUNG", "2"),
        ("2. setup", "2"),
        ("2 setup", "2"),
        # Option 3: Both
        ("3", "3"),
        (" 3 ", "3"),
        ("both", "3"),
        ("Both", "3"),
        ("BOTH", "3"),
        ("beides", "3"),
        ("Beides", "3"),
        ("BEIDES", "3"),
        ("3. both", "3"),
        ("3 both", "3"),
        ("3. beides", "3"),
        ("3 beides", "3"),
        # Option 4: Language
        ("4", "4"),
        (" 4 ", "4"),
        ("language", "4"),
        ("Language", "4"),
        ("LANGUAGE", "4"),
        ("sprache", "4"),
        ("Sprache", "4"),
        ("SPRACHE", "4"),
        ("lang", "4"),
        ("4. language", "4"),
        ("4 language", "4"),
        ("4. sprache", "4"),
        ("4 sprache", "4"),
        # Option q: Quit
        ("q", "q"),
        ("Q", "q"),
        ("quit", "q"),
        ("Quit", "q"),
        ("QUIT", "q"),
        ("exit", "q"),
        ("EXIT", "q"),
        ("beenden", "q"),
        ("Beenden", "q"),
        ("stop", "q"),
        ("close", "q"),
        # Invalid / Unrecognized
        ("0", None),
        ("5", None),
        ("-1", None),
        ("help", None),
        ("unknown", None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_action_choices(raw_input: str, expected: str | None) -> None:
    assert normalize_action(raw_input) == expected


# ============================================================================
# 3. English Default and Translations
# ============================================================================

def test_default_language_is_english_when_no_config(tmp_path: Path) -> None:
    config = load_menu_config(tmp_path)
    assert config == {"language": "en"}

    controller = StartMenuController(tmp_path)
    assert controller.language == "en"
    assert "=== FolderHome Starter ===" in controller.t("title")
    assert "Select an option" in controller.t("prompt_choice")
    assert "Starting FolderHome..." in controller.t("launching_app")


def test_load_menu_config_handles_missing_corrupt_or_malformed_files(tmp_path: Path) -> None:
    # Non-existent config
    assert load_menu_config(tmp_path / "nonexistent") == {"language": "en"}

    # Corrupt JSON
    cfg_file = tmp_path / MENU_CONFIG_FILENAME
    cfg_file.write_text("NOT_VALID_JSON{", encoding="utf-8")
    assert load_menu_config(tmp_path) == {"language": "en"}

    # JSON with primitive or list rather than dict
    cfg_file.write_text('"english"', encoding="utf-8")
    assert load_menu_config(tmp_path) == {"language": "en"}

    cfg_file.write_text('["en", "de"]', encoding="utf-8")
    assert load_menu_config(tmp_path) == {"language": "en"}

    # Unsupported language in config falls back to default 'en' in controller
    cfg_file.write_text(json.dumps({"language": "es"}), encoding="utf-8")
    ctrl = StartMenuController(tmp_path)
    assert ctrl.language == "en"


def test_get_text_fallbacks_and_placeholders() -> None:
    # Existing key with placeholder
    rendered = get_text("en", "config_dir_info", path="C:/test/path")
    assert "C:/test/path" in rendered

    # Fallback when key missing in German
    rendered_fallback = get_text("de", "non_existent_key")
    assert rendered_fallback == "non_existent_key"


# ============================================================================
# 4. start_menu.json Language Persistence
# ============================================================================

def test_save_menu_language_persists_schema_and_language(tmp_path: Path) -> None:
    save_menu_language(tmp_path, "de")
    cfg_path = tmp_path / MENU_CONFIG_FILENAME
    assert cfg_path.is_file()

    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert payload["schema"] == MENU_CONFIG_SCHEMA
    assert payload["language"] == "de"

    # New controller instance automatically picks up saved language
    controller = StartMenuController(tmp_path)
    assert controller.language == "de"
    assert "Option auswählen" in controller.t("prompt_choice")


def test_change_language_flow_interactive_switch_and_persistence(tmp_path: Path) -> None:
    logs: list[str] = []
    # Initial controller with English default
    controller = StartMenuController(
        tmp_path,
        input_func=lambda prompt: "2",  # Choose Deutsch
        print_func=logs.append,
    )
    assert controller.language == "en"

    controller.change_language_flow()
    assert controller.language == "de"
    assert any("Sprache auf Deutsch gesetzt" in msg for msg in logs)

    cfg = json.loads((tmp_path / MENU_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert cfg["language"] == "de"

    # Now switch back to English with "1"
    logs.clear()
    controller.input_func = lambda prompt: "1"  # Choose English
    controller.change_language_flow()
    assert controller.language == "en"
    assert any("Language set to English" in msg for msg in logs)

    cfg = json.loads((tmp_path / MENU_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert cfg["language"] == "en"


def test_controller_explicit_language_override_persists(tmp_path: Path) -> None:
    # Explicit language='de' passed at init
    controller = StartMenuController(tmp_path, language="de")
    assert controller.language == "de"
    cfg = json.loads((tmp_path / MENU_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert cfg["language"] == "de"


# ============================================================================
# 5. Menu Options Resolution (1, 2, 3, 4, q)
# ============================================================================

def test_option_1_resolves_app_cmd_and_url(tmp_path: Path) -> None:
    app_script = tmp_path / "START-APP.cmd"
    app_script.write_text("@echo off\n", encoding="ascii")

    controller = StartMenuController(tmp_path, dry_run=True)
    cmd, url, err = controller.resolve_app_command_and_url()

    assert err is None
    assert cmd is not None
    assert cmd[0] == str(app_script)
    assert url == f"http://127.0.0.1:{DEFAULT_APP_PORT}/"


def test_option_2_resolves_setup_cmd_and_url(tmp_path: Path) -> None:
    setup_script = tmp_path / "START-SETUP.cmd"
    setup_script.write_text("@echo off\n", encoding="ascii")

    controller = StartMenuController(tmp_path, dry_run=True)
    cmd, url, err = controller.resolve_setup_command_and_url()

    assert err is None
    assert cmd is not None
    assert cmd[0] == str(setup_script)
    assert "--config-dir" in cmd
    assert str(tmp_path) in cmd
    assert url == f"http://127.0.0.1:{DEFAULT_SETUP_PORT}/"


def test_option_3_resolves_both_app_and_setup(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    (tmp_path / "START-SETUP.cmd").write_text("@echo off\n", encoding="ascii")

    logs: list[str] = []
    controller = StartMenuController(tmp_path, dry_run=True, print_func=logs.append)
    code = controller.run_action("3")

    assert code == 0
    full_log = "\n".join(logs)
    assert "Starting FolderHome..." in full_log
    assert "Starting Setup..." in full_log
    assert f"http://127.0.0.1:{DEFAULT_APP_PORT}/" in full_log
    assert f"http://127.0.0.1:{DEFAULT_SETUP_PORT}/" in full_log
    assert "[Dry-run] Operation completed without launching subprocesses." in full_log


def test_option_4_via_run_action_switches_language(tmp_path: Path) -> None:
    logs: list[str] = []
    controller = StartMenuController(
        tmp_path,
        input_func=lambda prompt: "2",
        print_func=logs.append,
    )
    code = controller.run_action("4")
    assert code == 0
    assert controller.language == "de"


def test_option_quit_returns_cleanly(tmp_path: Path) -> None:
    logs: list[str] = []
    controller = StartMenuController(tmp_path, print_func=logs.append)
    code = controller.run_action("q")
    assert code == 0
    assert any("Exiting starter menu" in msg for msg in logs)


def test_option_invalid_returns_code_1(tmp_path: Path) -> None:
    logs: list[str] = []
    controller = StartMenuController(tmp_path, print_func=logs.append)
    code = controller.run_action("unrecognized_action")
    assert code == 1
    assert any("Unknown option 'unrecognized_action'" in msg for msg in logs)


def test_missing_starter_scripts_fail_gracefully_with_nonzero_exitcode(tmp_path: Path) -> None:
    # Option 1 (FolderHome) without START-APP.cmd
    logs1: list[str] = []
    controller1 = StartMenuController(tmp_path, dry_run=True, print_func=logs1.append)
    code1 = controller1.run_action("1")
    assert code1 == 1
    assert any("START-APP.cmd was not found" in msg for msg in logs1)

    # Option 2 (Setup) without START-SETUP.cmd
    logs2: list[str] = []
    controller2 = StartMenuController(tmp_path, dry_run=True, print_func=logs2.append)
    code2 = controller2.run_action("2")
    assert code2 == 1
    assert any("START-SETUP.cmd was not found" in msg for msg in logs2)

    # Option 3 (Both) without wrappers
    logs3: list[str] = []
    controller3 = StartMenuController(tmp_path, dry_run=True, print_func=logs3.append)
    code3 = controller3.run_action("3")
    assert code3 == 1
    assert any("START-APP.cmd was not found" in msg for msg in logs3)
    assert any("START-SETUP.cmd was not found" in msg for msg in logs3)


def test_start_cmd_propagates_nonzero_exit_codes(tmp_path: Path) -> None:
    import subprocess

    start_cmd = SCRIPTS_DIR / "START.cmd"
    assert start_cmd.is_file()

    # 1. Missing wrapper on action 1 must propagate exit code 1
    res1 = subprocess.run(
        ["cmd.exe", "/c", str(start_cmd), "--config-dir", str(tmp_path), "--action", "1"],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 1
    assert "START-APP.cmd" in res1.stdout

    # 2. Mutually exclusive arguments must propagate parser exit code 2
    res2 = subprocess.run(
        [
            "cmd.exe",
            "/c",
            str(start_cmd),
            "--config-dir",
            str(tmp_path),
            "--confirm-gates",
            "--deny-gates",
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 2


# ============================================================================
# 6. Explicit Network and Cloud Gates
# ============================================================================

def test_inspect_launch_config_remote_and_cloud_detection(tmp_path: Path) -> None:
    launch_path = tmp_path / "launch.json"

    # Hosted providers: bedrock, anthropic, openai
    for provider in ("bedrock", "anthropic", "openai"):
        launch_path.write_text(
            json.dumps({"model_preset": f"{provider}-model", "model_provider": provider}),
            encoding="utf-8",
        )
        info = inspect_launch_config(launch_path)
        assert info["is_remote_or_cloud"] is True, f"{provider} should be remote/cloud"
        assert info["is_ollama"] is False

    # Ollama on loopback host: not remote/cloud (127.0.0.1, localhost, ::1 only)
    for host in (
        "127.0.0.1:11434",
        "localhost:11434",
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "::1",
        "[::1]:11434",
        "http://[::1]:11434",
    ):
        launch_path.write_text(
            json.dumps({
                "model_preset": "deepseek-coder",
                "model_provider": "ollama",
                "ollama_host": host,
            }),
            encoding="utf-8",
        )
        info = inspect_launch_config(launch_path)
        assert info["is_ollama"] is True
        assert info["is_remote_or_cloud"] is False, f"Loopback host {host} should not be cloud"

    # Ollama on remote host or non-loopback lookalikes: remote/cloud detected
    for remote_host in (
        "http://192.168.1.80:11434",
        "0.0.0.0",
        "0.0.0.0:11434",
        "http://0.0.0.0:11434",
        "127.0.0.1.evil.invalid",
        "http://127.0.0.1.evil.invalid:11434",
        "localhost.evil.invalid",
    ):
        launch_path.write_text(
            json.dumps({
                "model_preset": "deepseek-coder",
                "model_provider": "ollama",
                "ollama_host": remote_host,
            }),
            encoding="utf-8",
        )
        info = inspect_launch_config(launch_path)
        assert info["is_ollama"] is True
        assert info["is_remote_or_cloud"] is True, f"Host {remote_host} should be remote/cloud"

    # Nested model_presets dictionary lookup
    launch_path.write_text(
        json.dumps({
            "model_preset": "remote-preset",
            "model_presets": {
                "remote-preset": {"model_provider": "openai"}
            },
        }),
        encoding="utf-8",
    )
    info = inspect_launch_config(launch_path)
    assert info["provider"] == "openai"
    assert info["is_remote_or_cloud"] is True


def test_cloud_gates_explicitly_granted_with_confirm_flag(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"
    launch_path.write_text(
        json.dumps({"model_preset": "claude-sonnet", "model_provider": "anthropic"}),
        encoding="utf-8",
    )

    logs: list[str] = []
    controller = StartMenuController(
        tmp_path,
        confirm_gates=True,
        dry_run=True,
        print_func=logs.append,
    )
    cmd, _, _ = controller.resolve_app_command_and_url()

    assert cmd is not None
    assert "--allow-network" in cmd
    assert "--approve-sensitive-cloud-data" in cmd
    assert any("Network and cloud data gates approved" in msg for msg in logs)


def test_cloud_gates_explicitly_denied_with_deny_flag(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"
    launch_path.write_text(
        json.dumps({"model_preset": "claude-sonnet", "model_provider": "anthropic"}),
        encoding="utf-8",
    )

    logs: list[str] = []
    controller = StartMenuController(
        tmp_path,
        confirm_gates=False,
        dry_run=True,
        print_func=logs.append,
    )
    cmd, _, _ = controller.resolve_app_command_and_url()

    assert cmd is not None
    assert "--allow-network" not in cmd
    assert "--approve-sensitive-cloud-data" not in cmd
    assert any("No network or cloud gates granted (fail-closed)" in msg for msg in logs)


def test_cloud_gates_interactive_prompt_requires_explicit_yes(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"
    launch_path.write_text(
        json.dumps({"model_preset": "gpt-4o", "model_provider": "openai"}),
        encoding="utf-8",
    )

    # Empty answer / Enter -> fail closed
    logs_denied: list[str] = []
    ctrl_denied = StartMenuController(
        tmp_path,
        confirm_gates=None,
        input_func=lambda prompt: "",
        dry_run=True,
        print_func=logs_denied.append,
    )
    cmd_denied, _, _ = ctrl_denied.resolve_app_command_and_url()
    assert "--allow-network" not in (cmd_denied or [])
    assert any("No network or cloud gates granted" in m for m in logs_denied)

    # Explicit 'y' -> granted
    logs_granted: list[str] = []
    ctrl_granted = StartMenuController(
        tmp_path,
        confirm_gates=None,
        input_func=lambda prompt: "y",
        dry_run=True,
        print_func=logs_granted.append,
    )
    cmd_granted, _, _ = ctrl_granted.resolve_app_command_and_url()
    assert "--allow-network" in (cmd_granted or [])
    assert any("Network and cloud data gates approved" in m for m in logs_granted)


# ============================================================================
# 7. Ollama 600 Second Timeout
# ============================================================================

def test_ollama_timeout_600s_applied_for_ollama_provider(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"
    launch_path.write_text(
        json.dumps({"model_preset": "qwen2.5-coder", "model_provider": "ollama"}),
        encoding="utf-8",
    )

    logs: list[str] = []
    controller = StartMenuController(tmp_path, dry_run=True, print_func=logs.append)
    cmd, _, _ = controller.resolve_app_command_and_url()

    assert cmd is not None
    assert "--model-timeout-seconds" in cmd
    idx = cmd.index("--model-timeout-seconds")
    assert cmd[idx + 1] == str(DEFAULT_OLLAMA_TIMEOUT)
    assert str(DEFAULT_OLLAMA_TIMEOUT) == "600"
    assert any(f"Applied Ollama model timeout: {DEFAULT_OLLAMA_TIMEOUT}s" in m for m in logs)


def test_ollama_timeout_applied_when_preset_name_contains_ollama(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"
    launch_path.write_text(
        json.dumps({"model_preset": "my-ollama-runner", "model_provider": "local"}),
        encoding="utf-8",
    )

    logs: list[str] = []
    controller = StartMenuController(tmp_path, dry_run=True, print_func=logs.append)
    cmd, _, _ = controller.resolve_app_command_and_url()

    assert cmd is not None
    assert "--model-timeout-seconds" in cmd
    idx = cmd.index("--model-timeout-seconds")
    assert cmd[idx + 1] == "600"


def test_non_ollama_presets_do_not_receive_ollama_timeout(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"
    launch_path.write_text(
        json.dumps({"model_preset": "default-fixture", "model_provider": "fixture"}),
        encoding="utf-8",
    )

    controller = StartMenuController(tmp_path, dry_run=True)
    cmd, _, _ = controller.resolve_app_command_and_url()

    assert cmd is not None
    assert "--model-timeout-seconds" not in cmd


# ============================================================================
# 8. Dry-Run (No Subprocess & No User-Config Mutation)
# ============================================================================

def test_dry_run_never_spawns_subprocesses_or_browser(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    (tmp_path / "START-SETUP.cmd").write_text("@echo off\n", encoding="ascii")

    mock_runner = MagicMock()
    mock_browser = MagicMock()
    logs: list[str] = []

    controller = StartMenuController(
        tmp_path,
        dry_run=True,
        subprocess_runner=mock_runner,
        browser_opener=mock_browser,
        print_func=logs.append,
    )

    # Run actions 1, 2, 3
    for act in ("1", "2", "3"):
        code = controller.run_action(act)
        assert code == 0

    assert mock_runner.call_count == 0, "Subprocess runner was invoked during dry-run"
    assert mock_browser.call_count == 0, "Browser opener was invoked during dry-run"

    full_output = "\n".join(logs)
    assert "[Dry-run Command]" in full_output
    assert "[Dry-run URL]" in full_output
    assert "[Dry-run] Operation completed without launching subprocesses." in full_output


def test_dry_run_leaves_user_config_unmutated(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_file = tmp_path / "launch.json"
    initial_content = json.dumps({"model_preset": "original", "user_key": 12345}, indent=2)
    launch_file.write_text(initial_content, encoding="utf-8")

    controller = StartMenuController(tmp_path, dry_run=True)
    controller.run_action("1")

    # Verify launch.json is byte-for-byte unchanged
    assert launch_file.read_text(encoding="utf-8") == initial_content


# ============================================================================
# 9. CLI Parser and Main Entrypoint Integration
# ============================================================================

def test_cli_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.config_dir is None
    assert args.dry_run is False
    assert args.action is None
    assert args.language is None
    assert args.confirm_gates is None
    assert args.deny_gates is None
    assert args.no_browser is False


def test_main_cli_dry_run_action_execution(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    logs: list[str] = []

    code = main(
        ["--config-dir", str(tmp_path), "--dry-run", "--action", "folderhome"],
        print_func=logs.append,
    )
    assert code == 0
    full_output = "\n".join(logs)
    assert "Starting FolderHome..." in full_output
    assert "[Dry-run Command]" in full_output


def test_main_cli_interactive_loop_flow(tmp_path: Path) -> None:
    # User tries invalid input, then selects '4' (language), picks '2' (de), then 'q' (quit)
    user_inputs = iter(["invalid_choice", "4", "2", "q"])
    logs: list[str] = []

    code = main(
        ["--config-dir", str(tmp_path)],
        input_func=lambda prompt: next(user_inputs),
        print_func=logs.append,
    )
    assert code == 0
    full_output = "\n".join(logs)
    assert "=== FolderHome Starter ===" in full_output
    assert "Unknown option 'invalid_choice'" in full_output
    assert "Sprache auf Deutsch gesetzt" in full_output
    assert "Starter-Menü beendet." in full_output

    # start_menu.json should reflect German selection
    cfg = json.loads((tmp_path / MENU_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert cfg["language"] == "de"


# ============================================================================
# 10. Regression Tests: Dry-Run Language Persistence & Host Classification
# ============================================================================

def test_dry_run_with_explicit_language_never_writes_start_menu_json(tmp_path: Path) -> None:
    # Initializing with explicit language 'de' in dry_run mode
    ctrl_de = StartMenuController(tmp_path, language="de", dry_run=True)
    assert ctrl_de.language == "de"
    assert not (tmp_path / MENU_CONFIG_FILENAME).exists()

    # Initializing with explicit language 'en' in dry_run mode
    ctrl_en = StartMenuController(tmp_path, language="en", dry_run=True)
    assert ctrl_en.language == "en"
    assert not (tmp_path / MENU_CONFIG_FILENAME).exists()


def test_dry_run_menu_option_4_never_writes_start_menu_json(tmp_path: Path) -> None:
    logs: list[str] = []
    ctrl = StartMenuController(
        tmp_path,
        dry_run=True,
        input_func=lambda prompt: "2",
        print_func=logs.append,
    )
    # Direct change_language_flow call
    ctrl.change_language_flow()
    assert ctrl.language == "de"
    assert not (tmp_path / MENU_CONFIG_FILENAME).exists()

    # Via run_action("4")
    ctrl.input_func = lambda prompt: "1"
    code = ctrl.run_action("4")
    assert code == 0
    assert ctrl.language == "en"
    assert not (tmp_path / MENU_CONFIG_FILENAME).exists()


def test_dry_run_main_cli_option_4_and_explicit_language_never_write(tmp_path: Path) -> None:
    # CLI with --language de --dry-run
    code = main(
        ["--config-dir", str(tmp_path), "--dry-run", "--language", "de", "--action", "q"],
        print_func=lambda _: None,
    )
    assert code == 0
    assert not (tmp_path / MENU_CONFIG_FILENAME).exists()

    # CLI with --dry-run --action 4
    code2 = main(
        ["--config-dir", str(tmp_path), "--dry-run", "--action", "4"],
        input_func=lambda _: "2",
        print_func=lambda _: None,
    )
    assert code2 == 0
    assert not (tmp_path / MENU_CONFIG_FILENAME).exists()


def test_dry_run_preserves_preexisting_start_menu_json(tmp_path: Path) -> None:
    cfg_file = tmp_path / MENU_CONFIG_FILENAME
    original_content = json.dumps({"schema": MENU_CONFIG_SCHEMA, "language": "en"}, indent=2) + "\n"
    cfg_file.write_text(original_content, encoding="utf-8")

    ctrl = StartMenuController(
        tmp_path,
        language="de",
        dry_run=True,
        input_func=lambda _: "2",
        print_func=lambda _: None,
    )
    ctrl.change_language_flow()
    assert ctrl.language == "de"
    # The file on disk must still contain the unmutated original content
    assert cfg_file.read_text(encoding="utf-8") == original_content


def test_is_loopback_host_exact_and_fail_closed() -> None:
    # Exact loopback hosts
    for loopback in (
        "127.0.0.1",
        "localhost",
        "::1",
        "[::1]",
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
        "http://127.0.0.1:11434/",
        "127.0.0.1:11434",
        "localhost:11434",
        "[::1]:11434",
        "https://127.0.0.1:11434",
        "https://localhost:11434",
    ):
        assert is_loopback_host(loopback) is True, f"{loopback} must be loopback"

    # Remote hosts, 0.0.0.0, and lookalikes must fail closed
    for remote in (
        "0.0.0.0",
        "0.0.0.0:11434",
        "http://0.0.0.0:11434",
        "https://0.0.0.0:11434",
        "127.0.0.1.evil.invalid",
        "http://127.0.0.1.evil.invalid:11434",
        "127.0.0.1.evil.invalid:11434",
        "localhost.evil.invalid",
        "http://localhost.evil.invalid:11434",
        "::1.evil.invalid",
        "http://127.0.0.2:11434",
        "127.0.0.2",
        "192.168.1.1",
        "http://192.168.1.80:11434",
        "http://example.com:11434",
        "127.0.0.1@evil.com",
        "http://user:pass@127.0.0.1.evil.com",
        "",
        "   ",
        None,
    ):
        assert is_loopback_host(remote) is False, f"{remote} must be remote"


def test_remote_lookalikes_and_all_interfaces_require_both_explicit_gates(tmp_path: Path) -> None:
    (tmp_path / "START-APP.cmd").write_text("@echo off\n", encoding="ascii")
    launch_path = tmp_path / "launch.json"

    for remote_host in ("http://0.0.0.0:11434", "http://127.0.0.1.evil.invalid:11434"):
        launch_path.write_text(
            json.dumps({
                "model_preset": "test-remote",
                "model_provider": "ollama",
                "ollama_host": remote_host,
            }),
            encoding="utf-8",
        )

        # 1. Fail-closed: unconfirmed prompt -> neither gate granted
        logs_denied: list[str] = []
        ctrl_denied = StartMenuController(
            tmp_path,
            confirm_gates=None,
            input_func=lambda prompt: "n",
            dry_run=True,
            print_func=logs_denied.append,
        )
        cmd_denied, _, _ = ctrl_denied.resolve_app_command_and_url()
        assert cmd_denied is not None
        assert "--allow-network" not in cmd_denied
        assert "--approve-sensitive-cloud-data" not in cmd_denied
        assert any("Remote/cloud model preset" in m for m in logs_denied)
        assert any("No network or cloud gates granted (fail-closed)" in m for m in logs_denied)

        # 2. Confirmed: both gates granted
        logs_granted: list[str] = []
        ctrl_granted = StartMenuController(
            tmp_path,
            confirm_gates=True,
            dry_run=True,
            print_func=logs_granted.append,
        )
        cmd_granted, _, _ = ctrl_granted.resolve_app_command_and_url()
        assert cmd_granted is not None
        assert "--allow-network" in cmd_granted
        assert "--approve-sensitive-cloud-data" in cmd_granted
        assert any("Network and cloud data gates approved" in m for m in logs_granted)


def test_confirm_and_deny_gates_are_mutually_exclusive() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--confirm-gates", "--deny-gates"])


def test_confirm_gates_and_deny_gates_parse_individually() -> None:
    parser = build_parser()
    args_confirm = parser.parse_args(["--confirm-gates"])
    assert args_confirm.confirm_gates is True
    assert args_confirm.deny_gates is None

    args_deny = parser.parse_args(["--deny-gates"])
    assert args_deny.deny_gates is True
    assert args_deny.confirm_gates is None


def test_main_with_mutually_exclusive_gates_raises_exit(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--config-dir", str(tmp_path), "--confirm-gates", "--deny-gates"])
