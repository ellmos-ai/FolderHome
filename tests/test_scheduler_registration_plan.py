from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from folderhome.application import scheduler_handoff
from folderhome.provider_locations import default_provider_root


@pytest.fixture
def registration_inputs(tmp_path):
    root = Path(__file__).parents[1]
    shutil.copytree(root / "examples" / "profiles", tmp_path / "profiles")
    shutil.copytree(root / "manifests" / "components", tmp_path / "manifests")
    for name in ("watched-folders.json", "routine-bindings.json"):
        shutil.copyfile(root / "examples" / "observation" / name, tmp_path / name)
    watched = tmp_path / "watched-folders.json"
    payload = json.loads(watched.read_text(encoding="utf-8"))
    payload["watches"][0]["source_dir"] = "documents/inbox"
    watched.write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "documents" / "inbox").mkdir(parents=True)
    handoff = scheduler_handoff.build_scheduler_handoff(
        task_name="synthetic_queue",
        interval_minutes=30,
        start_at="2026-09-10T08:00:00+02:00",
        timezone="Europe/Berlin",
        config_file=tmp_path / "watched-folders.json",
        bindings_file=tmp_path / "routine-bindings.json",
        profiles_dir=tmp_path / "profiles",
        state_dir=tmp_path / "queue-state",
        manifest_root=tmp_path / "manifests",
        doc_services_root=default_provider_root(root, "doc-services"),
        python_executable=Path(sys.executable),
        working_directory=root,
    )
    return dict(
        handoff=handoff,
        store_path=tmp_path / "scheduler" / "jobs.db",
        ledger_dir=tmp_path / "registration-ledger",
        provider_root=default_provider_root(root, "ellmos-scheduler"),
        provider_revision="d5103b9a733701f6db80dd08cfae408bf0af8ac5",
    )


def _api():
    # Import inside the tests so absence is a per-feature failure, not collection failure.
    from folderhome.application import scheduler_registration

    return scheduler_registration


def test_registration_plan_is_deterministic_and_has_no_store_or_state_effects(registration_inputs):
    api = _api()
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    assert plan == api.build_scheduler_registration_plan(**registration_inputs)
    assert api.validate_scheduler_registration_plan(plan) == plan
    assert plan.configuration_files
    assert not registration_inputs["store_path"].parent.exists()
    assert not registration_inputs["ledger_dir"].exists()
    assert not registration_inputs["handoff"].state_dir.exists()


@pytest.mark.parametrize(
    "kind", ["watch", "bindings", "profile", "manifest", "new_profile", "deleted_profile"]
)
def test_registration_confirmation_rejects_configuration_drift(registration_inputs, kind):
    api = _api()
    handoff = registration_inputs["handoff"]
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    if kind == "new_profile":
        (handoff.profiles_dir / "new.json").write_text("{}", encoding="utf-8")
    elif kind == "deleted_profile":
        next(p for p in handoff.profiles_dir.glob("*.json") if p.name != "household.json").unlink()
    else:
        target = {
            "watch": handoff.config_file,
            "bindings": handoff.bindings_file,
            "profile": handoff.profiles_dir / "household.json",
            "manifest": next(handoff.manifest_root.glob("*.toml")),
        }[kind]
        target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(api.SchedulerRegistrationError):
        api.validate_scheduler_registration_plan(plan)
    assert not registration_inputs["store_path"].exists()


def test_changed_watched_documents_do_not_invalidate_configuration_approval(registration_inputs):
    api = _api()
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    # Document contents are intentionally not registration inputs.
    documents = registration_inputs["handoff"].config_file.parent / "documents" / "inbox"
    (documents / "new.txt").write_text("new synthetic document", encoding="utf-8")
    assert api.validate_scheduler_registration_plan(plan) == plan


@pytest.mark.parametrize("kind", ["watch", "binding"])
def test_retargeted_directory_requires_new_registration_approval(
    registration_inputs, kind, tmp_path
):
    api = _api()
    handoff = registration_inputs["handoff"]
    source_a = tmp_path / "source-a"
    source_b = tmp_path / "source-b"
    source_a.mkdir()
    source_b.mkdir()
    redirect = tmp_path / "selected-directory"

    def link(target):
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(redirect), str(target)],
                check=True,
                capture_output=True,
            )
        else:
            redirect.symlink_to(target, target_is_directory=True)

    link(source_a)
    path = handoff.config_file if kind == "watch" else handoff.bindings_file
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries, field = ("watches", "source_dir") if kind == "watch" else ("bindings", "target_dir")
    payload[entries][0][field] = str(redirect)
    path.write_text(json.dumps(payload), encoding="utf-8")
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    before = path.read_bytes()
    if os.name == "nt":
        redirect.rmdir()  # Remove only this synthetic junction, not its target.
    else:
        redirect.unlink()
    link(source_b)
    assert path.read_bytes() == before
    with pytest.raises(api.SchedulerRegistrationError):
        api.validate_scheduler_registration_plan(plan)
    assert source_a.is_dir() and source_b.is_dir()


@pytest.mark.parametrize(
    "field", ["plan_id", "store_path", "ledger_dir", "provider_revision", "configuration_files"]
)
def test_registration_confirmation_reconstructs_all_approval_fields(registration_inputs, field):
    api = _api()
    plan = api.build_scheduler_registration_plan(**registration_inputs)
    values = {
        "plan_id": "registration_" + "0" * 64,
        "store_path": plan.store_path.with_name("other.db"),
        "ledger_dir": plan.ledger_dir.with_name("other-ledger"),
        "provider_revision": "0" * 40,
        "configuration_files": (),
    }
    with pytest.raises(api.SchedulerRegistrationError):
        api.validate_scheduler_registration_plan(replace(plan, **{field: values[field]}))
