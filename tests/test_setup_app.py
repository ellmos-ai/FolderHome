from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from folderhome.application.profile_rules import load_profile_configuration
from folderhome.contracts import LocalAppSettings
from folderhome.contracts.resources import ResourceRegistryError
from folderhome.setup_app import SetupAppError, SetupApplication

PROFILE_DIR = Path(__file__).parents[1] / "examples" / "profiles"
TOKEN = "setup-app-test-token-with-sufficient-entropy-12345678"


def _app(tmp_path: Path, *, config_dir: Path | None = None) -> SetupApplication:
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    target = config_dir or (tmp_path / "config")
    target.mkdir(parents=True, exist_ok=True)
    return SetupApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=0,
            profiles_dir=PROFILE_DIR,
            state_dir=state_dir,
        ),
        profiles=load_profile_configuration(PROFILE_DIR),
        config_dir=target,
        session_token=TOKEN,
    )


def _headers(port: int, token: str = TOKEN) -> dict[str, str]:
    return {
        "Host": f"127.0.0.1:{port}",
        "Origin": f"http://127.0.0.1:{port}",
        "Content-Type": "application/json",
        "X-FolderHome-Token": token,
    }


def _request(tmp_path: Path, **overrides: object) -> dict[str, object]:
    documents = tmp_path / "documents"
    output = tmp_path / "output"
    for directory in (documents, output):
        directory.mkdir(exist_ok=True)
    request: dict[str, object] = {
        "schema": "folderhome.setup-plan-request.v1",
        "folders": [
            {
                "profile_id": "lukas",
                "purpose": "documents.source",
                "path": str(documents),
            },
            {
                "profile_id": "lukas",
                "purpose": "insurance.source",
                "path": str(documents),
            },
            {
                "profile_id": "lukas",
                "purpose": "documents.output",
                "path": str(output),
            },
        ],
        "model": {"provider": "fixture"},
        "port": 8765,
        "state_dir": str(tmp_path / "state"),
    }
    request.update(overrides)
    return request


def _post(app: SetupApplication, path: str, payload: dict[str, object], port: int = 8766):
    return app.handle(
        method="POST",
        target=path,
        headers=_headers(port),
        body=json.dumps(payload).encode("utf-8"),
        server_port=port,
    )


def test_setup_state_lists_profiles_and_targets_without_writing(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8766

    state = app.handle(
        method="GET",
        target="/api/v1/setup/state",
        headers=_headers(port),
        body=b"",
        server_port=port,
    )
    unauthorized = app.handle(
        method="GET",
        target="/api/v1/setup/state",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )

    assert state.status_code == 200
    assert state.payload["schema"] == "folderhome.setup-state.v1"
    assert {item["profile_id"] for item in state.payload["profiles"]} == {
        "hanna",
        "lukas",
        "simon",
    }
    assert state.payload["configured"] is False
    assert state.payload["writes_credentials"] is False
    assert state.payload["resources_file"].endswith("resources.json")
    assert not app.resources_file.exists()
    assert unauthorized.status_code == 401


def test_setup_validate_rejects_missing_folder_and_unknown_purpose(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    missing = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            folders=[
                {
                    "profile_id": "lukas",
                    "purpose": "documents.source",
                    "path": str(tmp_path / "does-not-exist"),
                }
            ],
        ),
    )
    unknown = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            folders=[
                {
                    "profile_id": "lukas",
                    "purpose": "documents.everything",
                    "path": str(tmp_path),
                }
            ],
        ),
    )
    stranger = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            folders=[
                {
                    "profile_id": "nobody",
                    "purpose": "documents.source",
                    "path": str(tmp_path),
                }
            ],
        ),
    )

    assert missing.payload["valid"] is False
    assert "existiert nicht" in missing.payload["errors"][0]["message"]
    assert unknown.payload["valid"] is False
    assert "Unbekannter Zweck" in unknown.payload["errors"][0]["message"]
    assert stranger.payload["valid"] is False
    assert not app.resources_file.exists()
    assert not app.launch_file.exists()


def test_setup_validate_reuses_the_model_contract_for_provider_fields(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    incomplete = _post(
        app,
        "/api/v1/setup/validate",
        _request(tmp_path, model={"provider": "ollama"}),
    )
    complete = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            model={
                "provider": "ollama",
                "ollama_host": "http://127.0.0.1:11434",
                "ollama_model_id": "qwen3.8:27b-mlx",
            },
        ),
    )

    assert incomplete.payload["valid"] is False
    assert "Modell-ID" in incomplete.payload["errors"][0]["message"]
    assert complete.payload["valid"] is True
    assert complete.payload["launch_json"]["model_provider"] == "ollama"
    assert complete.payload["launch_json"]["ollama_model_id"] == "qwen3.8:27b-mlx"
    # Gates never travel in the file.
    assert "allow_network" not in complete.payload["launch_json"]
    assert "approve_sensitive_cloud_data" not in complete.payload["launch_json"]


def test_setup_save_needs_confirmation_and_the_exact_plan_hash(tmp_path: Path) -> None:
    app = _app(tmp_path)
    planned = _post(app, "/api/v1/setup/validate", _request(tmp_path))
    plan_sha256 = planned.payload["plan_sha256"]

    unconfirmed = _post(
        app,
        "/api/v1/setup/save",
        _request(tmp_path, plan_sha256=plan_sha256),
    )
    stale = _post(
        app,
        "/api/v1/setup/save",
        _request(tmp_path, confirm=True, plan_sha256="0" * 64),
    )

    assert planned.payload["valid"] is True
    assert unconfirmed.status_code == 400
    assert "Bestätigung" in unconfirmed.payload["message"]
    assert stale.status_code == 400
    assert "Plan-Hash" in stale.payload["message"]
    assert not app.resources_file.exists()
    assert not app.launch_file.exists()


def test_setup_save_writes_a_registry_the_existing_loader_accepts(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    planned = _post(app, "/api/v1/setup/validate", _request(tmp_path))
    saved = _post(
        app,
        "/api/v1/setup/save",
        _request(
            tmp_path,
            confirm=True,
            plan_sha256=planned.payload["plan_sha256"],
        ),
    )

    assert saved.status_code == 200, saved.payload
    assert saved.payload["written"] is True
    assert "app serve" in saved.payload["launch_command"]

    registry = json.loads(app.resources_file.read_text(encoding="utf-8"))
    assert registry["schema"] == "folderhome.resource-registry.v1"
    # Two purposes on one folder share one resource; the output folder is its own.
    assert len(registry["resources"]) == 2
    defaults = registry["profile_defaults"]["lukas"]
    assert defaults["documents.source"] == defaults["insurance.source"]
    assert defaults["documents.output"] != defaults["documents.source"]
    output = next(
        item
        for item in registry["resources"]
        if item["resource_id"] == defaults["documents.output"]
    )
    assert output["operations"] == ["create"]
    assert output["cloud_context"] == "deny"

    launch = json.loads(app.launch_file.read_text(encoding="utf-8"))
    assert launch["schema"] == "folderhome.launch-config.v1"
    assert launch["resources_file"] == str(app.resources_file)
    assert launch["port"] == 8765

    # A second save keeps the previous version instead of losing it.
    second = _post(
        app,
        "/api/v1/setup/save",
        _request(
            tmp_path,
            confirm=True,
            plan_sha256=planned.payload["plan_sha256"],
            port=8765,
        ),
    )
    assert second.status_code == 200
    assert len(second.payload["backups"]) == 2
    assert all(Path(item).is_file() for item in second.payload["backups"])


def test_setup_app_refuses_a_foreign_host_and_unknown_endpoints(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8766

    foreign = app.handle(
        method="GET",
        target="/api/v1/setup/state",
        headers={"Host": "example.invalid", "X-FolderHome-Token": TOKEN},
        body=b"",
        server_port=port,
    )
    unknown = app.handle(
        method="GET",
        target="/api/v1/setup/everything",
        headers=_headers(port),
        body=b"",
        server_port=port,
    )
    wrong_method = app.handle(
        method="GET",
        target="/api/v1/setup/save",
        headers=_headers(port),
        body=b"",
        server_port=port,
    )

    assert foreign.status_code == 403
    assert unknown.status_code == 404
    assert wrong_method.status_code == 405


def test_setup_save_rejects_a_folder_outside_home_without_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    (tmp_path / "home").mkdir()

    blocked = _post(app, "/api/v1/setup/validate", _request(tmp_path))
    allowed = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            folders=[
                {
                    "profile_id": "lukas",
                    "purpose": "documents.source",
                    "path": str(tmp_path / "documents"),
                    "confirm_outside_home": True,
                }
            ],
        ),
    )

    assert blocked.payload["valid"] is False
    assert "außerhalb" in blocked.payload["errors"][0]["message"]
    assert allowed.payload["valid"] is True


def test_setup_plan_hash_changes_with_the_content(tmp_path: Path) -> None:
    app = _app(tmp_path)

    first = _post(app, "/api/v1/setup/validate", _request(tmp_path))
    second = _post(app, "/api/v1/setup/validate", _request(tmp_path, port=8799))

    assert first.payload["plan_sha256"] != second.payload["plan_sha256"]


def test_setup_application_needs_a_long_enough_token(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    with pytest.raises(SetupAppError, match="Sitzungstoken"):
        SetupApplication(
            settings=LocalAppSettings(
                host="127.0.0.1",
                port=0,
                profiles_dir=PROFILE_DIR,
                state_dir=state_dir,
            ),
            profiles=load_profile_configuration(PROFILE_DIR),
            config_dir=tmp_path / "config",
            session_token="too-short",
        )


def test_setup_validate_rejects_launch_values_the_app_would_refuse(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    overlapping = _post(
        app,
        "/api/v1/setup/validate",
        _request(tmp_path, state_dir=str(PROFILE_DIR)),
    )

    assert overlapping.payload["valid"] is False
    assert "überlappen" in overlapping.payload["errors"][0]["message"]


def test_saved_launch_config_drives_the_app_plan_command(tmp_path: Path) -> None:
    """The brief's acceptance criterion: what save writes, `app plan` picks up."""

    app = _app(tmp_path)
    request = _request(tmp_path, port=8791)
    planned = _post(app, "/api/v1/setup/validate", request)
    saved = _post(
        app,
        "/api/v1/setup/save",
        {**request, "confirm": True, "plan_sha256": planned.payload["plan_sha256"]},
    )
    assert saved.status_code == 200, saved.payload

    environment = dict(os.environ, PYTHONPATH=str(PROFILE_DIR.parents[1] / "src"))
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "folderhome",
            "app",
            "plan",
            "--launch-config",
            str(app.launch_file),
            "--json",
        ],
        cwd=PROFILE_DIR.parents[1],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["settings"]["port"] == 8791
    assert payload["logical_resources_configured"] is True
    assert payload["agent"]["model_provider"] == "fixture"


@pytest.mark.parametrize(
    ("model", "expects_network_gates"),
    [
        ({"provider": "fixture"}, False),
        (
            {
                "provider": "ollama",
                "ollama_host": "http://127.0.0.1:11434",
                "ollama_model_id": "qwen3.8:27b-mlx",
            },
            False,
        ),
        (
            {
                "provider": "ollama",
                "ollama_host": "http://100.119.69.90:11434",
                "ollama_model_id": "qwen3.8:27b-mlx",
            },
            True,
        ),
        (
            {
                "provider": "bedrock",
                "bedrock_model_id": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
                "aws_region": "eu-central-1",
            },
            True,
        ),
    ],
)
def test_launch_command_names_every_gate_the_file_cannot_grant(
    tmp_path: Path,
    model: dict[str, str],
    expects_network_gates: bool,
) -> None:
    app = _app(tmp_path)

    planned = _post(app, "/api/v1/setup/validate", _request(tmp_path, model=model))
    command = planned.payload["launch_command"]

    assert planned.payload["valid"] is True, planned.payload["errors"]
    # The listener gate is never optional, and neither is machine-readable output.
    assert "--approve-loopback-server" in command
    assert command.endswith("--json")
    assert ("--allow-network" in command) is expects_network_gates
    assert ("--approve-sensitive-cloud-data" in command) is expects_network_gates
    # Gates stay start-up flags: nothing about them travels in the file.
    assert "network_used" not in planned.payload["launch_json"]
    assert "allow_network" not in planned.payload["launch_json"]


def test_calendar_export_folder_is_a_writable_output_that_never_leaves_the_machine(
    tmp_path: Path,
) -> None:
    """The one purpose that does not end in `.output` still is one."""

    export = tmp_path / "calendar-export"
    export.mkdir()
    app = _app(tmp_path)
    request = _request(
        tmp_path,
        folders=[
            {
                "profile_id": "lukas",
                "purpose": "calendar.export_output",
                "path": str(export),
            }
        ],
    )

    planned = _post(app, "/api/v1/setup/validate", request)
    assert planned.payload["valid"] is True, planned.payload["errors"]
    resource = planned.payload["resources_json"]["resources"][0]
    assert resource["operations"] == ["create"]
    assert resource["cloud_context"] == "deny"

    saved = _post(
        app,
        "/api/v1/setup/save",
        {**request, "confirm": True, "plan_sha256": planned.payload["plan_sha256"]},
    )
    assert saved.status_code == 200, saved.payload


def test_save_leaves_the_previous_state_untouched_when_the_registry_does_not_load(
    tmp_path: Path,
) -> None:
    """The reload test is a gate, not a report after the fact."""

    app = _app(tmp_path)
    request = _request(tmp_path)
    planned = _post(app, "/api/v1/setup/validate", request)

    def _refuse(*args: object, **kwargs: object) -> None:
        raise ResourceRegistryError("Testfehler beim Rückladen.")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("folderhome.setup_app.load_resource_registry", _refuse)
        refused = _post(
            app,
            "/api/v1/setup/save",
            {**request, "confirm": True, "plan_sha256": planned.payload["plan_sha256"]},
        )

    assert refused.status_code == 400
    assert "nicht ladbar" in refused.payload["message"]
    assert not app.resources_file.exists()
    assert not app.launch_file.exists()
    # No half-written scratch files are left behind either.
    assert sorted(item.name for item in app.config_dir.iterdir()) == []


def _pick(app: SetupApplication, port: int = 8766):
    return app.handle(
        method="POST",
        target="/api/v1/setup/pick-folder",
        headers=_headers(port),
        body=b"",
        server_port=port,
    )


def test_folder_dialog_returns_the_chosen_path(tmp_path: Path) -> None:
    app = _app(tmp_path)
    chosen = tmp_path / "picked"
    chosen.mkdir()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "folderhome.setup_app.subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess(
                args, 0, stdout=f"{chosen}\n", stderr=""
            ),
        )
        response = _pick(app)

    assert response.status_code == 200
    assert response.payload["path"] == str(chosen)


def test_folder_dialog_reports_a_cancelled_choice_as_no_path(tmp_path: Path) -> None:
    app = _app(tmp_path)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "folderhome.setup_app.subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="\n", stderr=""),
        )
        response = _pick(app)

    assert response.status_code == 200
    assert response.payload["path"] is None


def test_folder_dialog_says_so_when_the_toolkit_is_missing(tmp_path: Path) -> None:
    app = _app(tmp_path)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("folderhome.setup_app.find_spec", lambda name: None)
        response = _pick(app)

    assert response.status_code == 501
    # Typing the path by hand has to stay an option, so the message says so.
    assert "von Hand" in response.payload["message"]


def test_folder_dialog_gives_up_instead_of_waiting_forever(tmp_path: Path) -> None:
    app = _app(tmp_path)

    def _hang(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="dialog", timeout=300)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("folderhome.setup_app.subprocess.run", _hang)
        response = _pick(app)

    assert response.status_code == 504
    # A timed-out dialog must not keep the lock: the next attempt still runs.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "folderhome.setup_app.subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="\n", stderr=""),
        )
        assert _pick(app).status_code == 200


def test_folder_dialog_refuses_a_second_window(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app._dialog_lock.acquire()
    try:
        response = _pick(app)
    finally:
        app._dialog_lock.release()

    assert response.status_code == 409


def test_two_document_sources_become_two_resources_with_the_first_as_default(
    tmp_path: Path,
) -> None:
    """A profile may read from several folders; only one of them is the default."""

    first = tmp_path / "papers"
    second = tmp_path / "scans"
    for directory in (first, second):
        directory.mkdir()
    app = _app(tmp_path)
    request = _request(
        tmp_path,
        folders=[
            {"profile_id": "lukas", "purpose": "documents.source", "path": str(first)},
            {"profile_id": "lukas", "purpose": "documents.source", "path": str(second)},
        ],
    )

    planned = _post(app, "/api/v1/setup/validate", request)
    assert planned.payload["valid"] is True, planned.payload["errors"]
    registry = planned.payload["resources_json"]
    paths = [item["locator"]["path"] for item in registry["resources"]]
    assert paths == [str(first), str(second)]
    default_id = registry["profile_defaults"]["lukas"]["documents.source"]
    assert default_id == registry["resources"][0]["resource_id"]

    saved = _post(
        app,
        "/api/v1/setup/save",
        {**request, "confirm": True, "plan_sha256": planned.payload["plan_sha256"]},
    )
    assert saved.status_code == 200, saved.payload

    state = app.state_payload()
    sources = [
        item for item in state["current_folders"] if item["purpose"] == "documents.source"
    ]
    # Reopening the installer has to show both folders, not just the default one.
    assert [item["path"] for item in sources] == [str(first), str(second)]
    assert [item["is_default"] for item in sources] == [True, False]
    assert "documents.source" in state["repeatable_purposes"]
    assert "documents.output" not in state["repeatable_purposes"]


def test_api_keys_are_written_to_env_and_never_reported_back(tmp_path: Path) -> None:
    """The installer stores the key; nothing reads it back out through the API."""

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "# kept by the user\nSOMETHING_ELSE=stays\n", encoding="utf-8"
    )
    app = _app(tmp_path, config_dir=config_dir)
    request = _request(tmp_path, model={"provider": "fixture"})

    planned = _post(app, "/api/v1/setup/validate", request)
    with_key = {
        **request,
        "confirm": True,
        "plan_sha256": planned.payload["plan_sha256"],
        "api_keys": {"ANTHROPIC_API_KEY": "test-key-not-a-real-secret"},
    }
    saved = _post(app, "/api/v1/setup/save", with_key)

    # The key is not part of the confirmed plan, so the hash still matches.
    assert saved.status_code == 200, saved.payload
    body = json.dumps(saved.payload, ensure_ascii=False)
    assert "test-key-not-a-real-secret" not in body

    env_text = (config_dir / ".env").read_text(encoding="utf-8")
    assert "SOMETHING_ELSE=stays" in env_text
    assert "# kept by the user" in env_text
    assert "ANTHROPIC_API_KEY=test-key-not-a-real-secret" in env_text

    state = app.state_payload()
    assert state["has_anthropic_key"] is True
    assert state["has_openai_key"] is False
    assert "test-key-not-a-real-secret" not in json.dumps(state, ensure_ascii=False)


def test_removing_an_api_key_drops_only_that_line(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "ANTHROPIC_API_KEY=old\nOPENAI_API_KEY=other\nSOMETHING_ELSE=stays\n",
        encoding="utf-8",
    )
    app = _app(tmp_path, config_dir=config_dir)
    request = _request(tmp_path)
    planned = _post(app, "/api/v1/setup/validate", request)

    saved = _post(
        app,
        "/api/v1/setup/save",
        {
            **request,
            "confirm": True,
            "plan_sha256": planned.payload["plan_sha256"],
            "api_keys": {"ANTHROPIC_API_KEY": None},
        },
    )

    assert saved.status_code == 200, saved.payload
    env_text = (config_dir / ".env").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" not in env_text
    assert "OPENAI_API_KEY=other" in env_text
    assert "SOMETHING_ELSE=stays" in env_text
    assert app.state_payload()["has_openai_key"] is True


def test_an_unknown_environment_name_is_refused(tmp_path: Path) -> None:
    app = _app(tmp_path)
    request = _request(tmp_path)
    planned = _post(app, "/api/v1/setup/validate", request)

    refused = _post(
        app,
        "/api/v1/setup/save",
        {
            **request,
            "confirm": True,
            "plan_sha256": planned.payload["plan_sha256"],
            "api_keys": {"PATH": "C:\\evil"},
        },
    )

    assert refused.status_code == 400
    assert "PATH" in refused.payload["message"]
    assert not (app.config_dir / ".env").exists()


_PRESETS = {
    "local": {
        "provider": "ollama",
        "ollama_host": "http://127.0.0.1:11434",
        "ollama_model_id": "qwen3.8:27b-mlx",
    },
    "work": {
        "provider": "bedrock",
        "bedrock_model_id": "eu.amazon.nova-micro-v1:0",
        "aws_region": "eu-central-1",
    },
}


def test_model_presets_are_saved_and_the_active_one_drives_the_start_command(
    tmp_path: Path,
) -> None:
    """Switching models is picking another saved preset, not retyping fields."""

    app = _app(tmp_path)
    request = _request(tmp_path, model_presets=_PRESETS, model_preset="local")

    planned = _post(app, "/api/v1/setup/validate", request)
    assert planned.payload["valid"] is True, planned.payload["errors"]
    launch = planned.payload["launch_json"]
    assert sorted(launch["model_presets"]) == ["local", "work"]
    assert launch["model_preset"] == "local"
    # A loopback model needs no approval, so the command must not ask for one.
    assert "--allow-network" not in planned.payload["launch_command"]

    switched = _post(
        app,
        "/api/v1/setup/validate",
        {**request, "model_preset": "work"},
    )
    assert switched.payload["launch_json"]["model_preset"] == "work"
    assert "--allow-network" in switched.payload["launch_command"]
    assert "--approve-sensitive-cloud-data" in switched.payload["launch_command"]

    saved = _post(
        app,
        "/api/v1/setup/save",
        {
            **request,
            "model_preset": "work",
            "confirm": True,
            "plan_sha256": switched.payload["plan_sha256"],
        },
    )
    assert saved.status_code == 200, saved.payload
    stored = json.loads(app.launch_file.read_text(encoding="utf-8"))
    assert stored["model_preset"] == "work"
    assert stored["model_presets"]["local"]["ollama_model_id"] == "qwen3.8:27b-mlx"

    # Reopening the installer has to find the saved presets, or the next save
    # would quietly delete them.
    state = app.state_payload()
    assert sorted(state["model_presets"]) == ["local", "work"]
    assert state["model_preset"] == "work"


def test_deleting_a_preset_removes_it_from_the_written_file(tmp_path: Path) -> None:
    app = _app(tmp_path)
    full = _request(tmp_path, model_presets=_PRESETS, model_preset="local")
    first = _post(app, "/api/v1/setup/validate", full)
    _post(
        app,
        "/api/v1/setup/save",
        {**full, "confirm": True, "plan_sha256": first.payload["plan_sha256"]},
    )

    remaining = {"local": _PRESETS["local"]}
    reduced = _request(tmp_path, model_presets=remaining, model_preset="local")
    planned = _post(app, "/api/v1/setup/validate", reduced)
    saved = _post(
        app,
        "/api/v1/setup/save",
        {**reduced, "confirm": True, "plan_sha256": planned.payload["plan_sha256"]},
    )

    assert saved.status_code == 200, saved.payload
    stored = json.loads(app.launch_file.read_text(encoding="utf-8"))
    assert sorted(stored["model_presets"]) == ["local"]


def test_a_broken_or_badly_named_preset_is_refused_before_anything_is_written(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    unnamed = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            model_presets={"has spaces": _PRESETS["local"]},
            model_preset="has spaces",
        ),
    )
    assert unnamed.payload["valid"] is False
    assert any("has spaces" in item["message"] for item in unnamed.payload["errors"])

    # An inactive preset is checked too: saving an unusable one helps nobody.
    incomplete = _post(
        app,
        "/api/v1/setup/validate",
        _request(
            tmp_path,
            model_presets={"local": _PRESETS["local"], "broken": {"provider": "ollama"}},
            model_preset="local",
        ),
    )
    assert incomplete.payload["valid"] is False
    assert any("broken" in item["field"] for item in incomplete.payload["errors"])

    missing = _post(
        app,
        "/api/v1/setup/validate",
        _request(tmp_path, model_presets=_PRESETS, model_preset="gone"),
    )
    assert missing.payload["valid"] is False


SETUP_UI = Path(__file__).parents[1] / "src" / "folderhome" / "setup_ui"


def _translation_keys(script: str, language: str) -> set[str]:
    start = script.index(f"  {language}: {{")
    end = script.index("\n  },", start)
    return set(re.findall(r"^    ([A-Za-z0-9_]+):", script[start:end], re.M))


def test_setup_ui_only_references_ids_and_texts_that_exist() -> None:
    """A typo in an id or a text key breaks the installer silently in the browser."""

    script = (SETUP_UI / "app.js").read_text(encoding="utf-8")
    markup = (SETUP_UI / "index.html").read_text(encoding="utf-8")

    english = _translation_keys(script, "en")
    german = _translation_keys(script, "de")
    assert english == german, sorted(english ^ german)

    used = set(re.findall(r'\bt\("([A-Za-z0-9_]+)"', script))
    used |= set(re.findall(r'dataset\.i18n = "([A-Za-z0-9_]+)"', script))
    used |= set(re.findall(r'data-i18n="([A-Za-z0-9_]+)"', markup))
    assert not used - english, sorted(used - english)

    # Every id the script reaches for must exist in the markup or be built by it.
    declared = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', markup))
    declared |= set(re.findall(r'\.id = "([A-Za-z0-9_-]+)"', script))
    queried = set(re.findall(r'querySelector\("#([A-Za-z0-9_-]+)"\)', script))
    assert not queried - declared, sorted(queried - declared)


def test_setup_ui_offers_every_provider_the_service_reports(tmp_path: Path) -> None:
    markup = (SETUP_UI / "index.html").read_text(encoding="utf-8")
    offered = set(re.findall(r'<option value="([a-z]+)"', markup))

    assert offered == set(_app(tmp_path).state_payload()["model_providers"])
