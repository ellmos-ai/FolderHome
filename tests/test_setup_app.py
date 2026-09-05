from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from folderhome.application.profile_rules import load_profile_configuration
from folderhome.contracts import LocalAppSettings
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
