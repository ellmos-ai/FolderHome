from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.directory_observation import (
    load_watched_folder_configuration,
)
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.routine_queue import load_folder_routine_bindings
from folderhome.application.scheduler_handoff import (
    EXIT_ALREADY_RUNNING,
    EXIT_ATTENTION,
    EXIT_BLOCKED,
    EXIT_IDLE,
    SchedulerHandoffError,
    build_scheduler_handoff,
    run_scheduler_queue,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)

REPO_ROOT = Path(__file__).parents[1]


class SyntheticExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        if source_path.suffix.lower() != ".txt":
            raise UnsupportedDocumentError(
                f"Dateityp wird nicht unterstützt: {source_path.suffix}"
            )
        source_hash = sha256(source_path.read_bytes()).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, source_hash),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=source_hash,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-08-21T18:00:00Z",
            text=source_path.read_text(encoding="utf-8"),
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-test",
            extraction_method="direct",
            privacy_status=PrivacyStatus.CLEAR,
            privacy_summary="Synthetischer Datenschutzstatus.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _configuration(tmp_path: Path):
    source = tmp_path / "Eingang"
    source.mkdir()
    document = source / "Neu.txt"
    document.write_text("Neu", encoding="utf-8")
    watches_file = tmp_path / "watched-folders.json"
    watches_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.watched-folders.v1",
                "watches": [
                    {
                        "watch_id": "family_inbox",
                        "source_dir": str(source),
                        "profile_id": "hanna",
                        "area": "haushalt",
                        "interval_minutes": 60,
                        "recursive": True,
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    bindings_file = tmp_path / "routine-bindings.json"
    bindings_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.routine-bindings.v1",
                "bindings": [
                    {
                        "binding_id": "family_cleanup",
                        "watch_id": "family_inbox",
                        "target_dir": "Ablage",
                        "mode": "changes",
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profiles_dir = REPO_ROOT / "examples" / "profiles"
    state_dir = tmp_path / "state"
    plan = build_scheduler_handoff(
        task_name="folderhome_routine_queue",
        interval_minutes=30,
        start_at="2026-08-22T08:00:00+02:00",
        timezone="Europe/Berlin",
        config_file=watches_file,
        bindings_file=bindings_file,
        profiles_dir=profiles_dir,
        state_dir=state_dir,
        manifest_root=REPO_ROOT / "manifests" / "components",
        doc_services_root=REPO_ROOT.parent / "doc-services",
        python_executable=Path("C:/Program Files/Python312/python.exe"),
        working_directory=REPO_ROOT,
    )
    return source, document, watches_file, bindings_file, profiles_dir, state_dir, plan


def test_handoff_is_deterministic_and_does_not_register_or_write(tmp_path: Path) -> None:
    (
        source,
        document,
        watches_file,
        bindings_file,
        profiles_dir,
        state_dir,
        plan,
    ) = _configuration(tmp_path)
    before = document.read_bytes()

    duplicate = build_scheduler_handoff(
        task_name="folderhome_routine_queue",
        interval_minutes=30,
        start_at="2026-08-22T08:00:00+02:00",
        timezone="Europe/Berlin",
        config_file=watches_file,
        bindings_file=bindings_file,
        profiles_dir=profiles_dir,
        state_dir=state_dir,
        manifest_root=REPO_ROOT / "manifests" / "components",
        doc_services_root=REPO_ROOT.parent / "doc-services",
        python_executable=Path("C:/Program Files/Python312/python.exe"),
        working_directory=REPO_ROOT,
    )

    assert duplicate == plan
    assert plan.schedule_id.startswith("schedule_")
    assert plan.portable_argv[0] == "C:\\Program Files\\Python312\\python.exe"
    assert plan.portable_argv[1:4] == ("-m", "folderhome", "scheduler")
    assert "run" in plan.portable_argv
    assert "--approve-scheduler-state-write" in plan.portable_argv
    assert "<Task" in plan.windows_task_xml
    assert "IgnoreNew" in plan.windows_task_xml
    payload = plan.to_dict()
    assert payload["registration_performed"] is False
    assert payload["installation_supported"] is False
    assert "schtasks" not in json.dumps(payload).lower()
    assert document.read_bytes() == before
    assert source.is_dir()
    assert not state_dir.exists()
    assert not (tmp_path / "Ablage").exists()


def test_scheduler_run_requires_gate_then_writes_report_and_releases_lock(
    tmp_path: Path,
) -> None:
    source, document, watches_file, bindings_file, profiles_dir, state_dir, plan = (
        _configuration(tmp_path)
    )
    watches = load_watched_folder_configuration(watches_file)
    bindings = load_folder_routine_bindings(bindings_file)
    profiles = load_profile_configuration(profiles_dir)
    before = document.read_bytes()

    with pytest.raises(SchedulerHandoffError, match="State-Freigabe"):
        run_scheduler_queue(
            plan,
            captured_at="2026-08-22T06:01:00Z",
            watches=watches,
            bindings=bindings,
            profiles=profiles,
            extractor=SyntheticExtractor(),
            allow_scheduler_state_write=False,
        )
    assert not state_dir.exists()

    report = run_scheduler_queue(
        plan,
        captured_at="2026-08-22T06:01:00Z",
        watches=watches,
        bindings=bindings,
        profiles=profiles,
        extractor=SyntheticExtractor(),
        allow_scheduler_state_write=True,
    )

    assert report.status == "attention"
    assert report.exit_code == EXIT_ATTENTION
    assert report.queue is not None
    assert report.queue.summary == {"ready": 1}
    assert report.completed_file is not None
    assert report.completed_file.is_file()
    assert not (state_dir / "scheduler-locks" / plan.schedule_id).exists()
    assert document.read_bytes() == before
    assert source.is_dir()
    assert not (tmp_path / "Ablage").exists()


def test_existing_scheduler_lock_is_preserved_and_returns_distinct_exit_code(
    tmp_path: Path,
) -> None:
    _, document, watches_file, bindings_file, profiles_dir, state_dir, plan = (
        _configuration(tmp_path)
    )
    lock_dir = state_dir / "scheduler-locks" / plan.schedule_id
    lock_dir.mkdir(parents=True)
    owner = lock_dir / "owner.json"
    owner.write_text('{"owner":"foreign-test"}\n', encoding="utf-8")

    report = run_scheduler_queue(
        plan,
        captured_at="2026-08-22T06:01:00Z",
        watches=load_watched_folder_configuration(watches_file),
        bindings=load_folder_routine_bindings(bindings_file),
        profiles=load_profile_configuration(profiles_dir),
        extractor=SyntheticExtractor(),
        allow_scheduler_state_write=True,
    )

    assert report.status == "already_running"
    assert report.exit_code == EXIT_ALREADY_RUNNING
    assert report.queue is None
    assert report.completed_file is None
    assert owner.read_text(encoding="utf-8") == '{"owner":"foreign-test"}\n'
    assert document.read_text(encoding="utf-8") == "Neu"


def test_scheduler_run_exit_codes_distinguish_idle_and_blocked(tmp_path: Path) -> None:
    _, document, watches_file, bindings_file, profiles_dir, state_dir, plan = (
        _configuration(tmp_path)
    )
    document.unlink()
    idle = run_scheduler_queue(
        plan,
        captured_at="2026-08-22T06:01:00Z",
        watches=load_watched_folder_configuration(watches_file),
        bindings=load_folder_routine_bindings(bindings_file),
        profiles=load_profile_configuration(profiles_dir),
        extractor=SyntheticExtractor(),
        allow_scheduler_state_write=True,
    )

    assert idle.status == "idle"
    assert idle.exit_code == EXIT_IDLE
    assert idle.queue is not None
    assert idle.queue.summary == {"empty": 1}

    binding_payload = json.loads(bindings_file.read_text(encoding="utf-8"))
    binding_payload["bindings"][0]["enabled"] = False
    bindings_file.write_text(json.dumps(binding_payload), encoding="utf-8")
    blocked = run_scheduler_queue(
        plan,
        captured_at="2026-08-22T06:02:00Z",
        watches=load_watched_folder_configuration(watches_file),
        bindings=load_folder_routine_bindings(bindings_file),
        profiles=load_profile_configuration(profiles_dir),
        extractor=SyntheticExtractor(),
        allow_scheduler_state_write=True,
    )

    assert blocked.status == "blocked"
    assert blocked.exit_code == EXIT_BLOCKED
    assert blocked.queue is not None
    assert blocked.queue.summary == {"blocked": 1}
