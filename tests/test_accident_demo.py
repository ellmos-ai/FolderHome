from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.application.accident_demo import (
    DEFAULT_ACCIDENT_PROMPT,
    SyntheticAccidentDemo,
    SyntheticAccidentDemoError,
)
from folderhome.capabilities.calendar_store import CalendarStore
from folderhome.capabilities.contact_registry import ContactRegisterStore


def test_accident_demo_prepares_one_path_free_hash_bound_journey(
    tmp_path: Path,
) -> None:
    demo = SyntheticAccidentDemo(tmp_path / "workspace")

    before = demo.status()
    prepared = demo.prepare()

    assert before["mode"] == "synthetic_fixture"
    assert before["runtime_status"] == "ready"
    assert before["generated_results"] == []
    assert prepared["schema"] == "folderhome.synthetic-accident-demo-plan.v1"
    assert prepared["status"] == "confirmation_required"
    assert prepared["prompt"] == DEFAULT_ACCIDENT_PROMPT
    assert prepared["confirmation_command"] == f"/confirm {prepared['plan_id']}"
    assert len(prepared["plan_sha256"]) == 64
    assert prepared["agent_search"]["tool_events"][0]["tool_name"] == (
        "search_home_documents"
    )
    assert prepared["detected_documents"] == [
        {
            "filename": "KFZ_Hyundai_i10_2026.txt",
            "classification": "current",
        },
        {
            "filename": "KFZ_Hyundai_i10_2025.txt",
            "classification": "older",
        },
    ]
    assert [step["workflow_id"] for step in prepared["steps"]] == [
        "contact-register",
        "calendar-handoff",
        "contract-cockpit",
        "correspondence-studio",
    ]
    assert all(step["confirmation_required"] for step in prepared["steps"])
    assert str(tmp_path) not in json.dumps(prepared, ensure_ascii=False)
    assert prepared["network_used"] is False
    assert prepared["external_actions_performed"] == []


def test_accident_demo_requires_exact_confirm_and_executes_real_local_outputs(
    tmp_path: Path,
) -> None:
    demo = SyntheticAccidentDemo(tmp_path / "workspace")
    prepared = demo.prepare()

    with pytest.raises(SyntheticAccidentDemoError, match="exactly"):
        demo.confirm(f"confirm {prepared['plan_id']}")
    with pytest.raises(SyntheticAccidentDemoError, match="unknown"):
        demo.confirm("/confirm accident_demo_unknown")

    result = demo.confirm(prepared["confirmation_command"])

    assert result["schema"] == "folderhome.synthetic-accident-demo-result.v1"
    assert result["status"] == "executed"
    assert result["plan_id"] == prepared["plan_id"]
    assert result["plan_sha256"] == prepared["plan_sha256"]
    assert result["network_used"] is False
    assert result["external_actions_performed"] == []
    assert result["local_actions_performed"] == [
        "state.contacts.write",
        "state.calendar.write",
        "filesystem.contract_cockpit.write",
        "file.create",
    ]
    assert [item["filename"] for item in result["generated_results"]] == [
        "Hyundai-i10-claim-letter.md",
        "Hyundai-i10-claim-letter.txt",
        "Hyundai-i10-insurance-overview.json",
        "Hyundai-i10-insurance-overview.md",
    ]
    assert all(len(item["sha256"]) == 64 for item in result["generated_results"])
    assert all(
        item["view_url"].startswith("/demo/results/")
        and item["download_url"].endswith("?download=1")
        for item in result["generated_results"]
    )
    assert all(
        item["download_url"].startswith("/demo/results/")
        for item in result["generated_results"]
    )
    assert str(tmp_path) not in json.dumps(result, ensure_ascii=False)

    state_root = demo.runtime_root / "state"
    contacts = ContactRegisterStore(state_root).list_contacts(
        profile_id="lukas",
        object_query="Hyundai i10",
        include_deletion_candidates=True,
    )
    events = CalendarStore(state_root).list_events(profile_id="lukas")
    assert len(contacts) == 1
    assert contacts[0].contact_name == "Jordan Current"
    assert contacts[0].email == "claims-2026@example.invalid"
    assert len(events) == 1
    assert events[0].title == "Review Hyundai i10 accident claim"
    letter = (demo.runtime_root / "outputs" / "Hyundai-i10-claim-letter.md").read_text(
        encoding="utf-8"
    )
    overview = (
        demo.runtime_root / "outputs" / "Hyundai-i10-insurance-overview.md"
    ).read_text(encoding="utf-8")
    assert "SYN-I10-2026" in letter
    assert "KFZ_Hyundai_i10_2026.txt" in overview
    assert "KFZ_Hyundai_i10_2025.txt" in overview
    assert "Archivierung" in overview

    with pytest.raises(SyntheticAccidentDemoError, match="already executed"):
        demo.confirm(prepared["confirmation_command"])


def test_accident_demo_reset_is_reproducible_without_touching_unknown_files(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    demo = SyntheticAccidentDemo(workspace)
    first = demo.prepare()
    demo.confirm(first["confirmation_command"])
    unknown = demo.runtime_root / "keep-me.txt"
    unknown.write_text("not owned by the demo reset", encoding="utf-8")

    reset = demo.reset()
    second = demo.prepare()

    assert reset["status"] == "reset"
    assert unknown.read_text(encoding="utf-8") == "not owned by the demo reset"
    assert demo.status()["generated_results"] == []
    assert first["plan_id"] == second["plan_id"]
    assert first["plan_sha256"] == second["plan_sha256"]
    assert (demo.runtime_root / "documents" / "KFZ_Hyundai_i10_2026.txt").is_file()
    assert (demo.runtime_root / "documents" / "KFZ_Hyundai_i10_2025.txt").is_file()


def test_accident_demo_refuses_an_unowned_existing_runtime_directory(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    runtime = workspace / "synthetic-accident-demo"
    runtime.mkdir(parents=True)
    existing = runtime / "keep-me.txt"
    existing.write_text("belongs to somebody else", encoding="utf-8")

    with pytest.raises(SyntheticAccidentDemoError, match="ownership marker"):
        SyntheticAccidentDemo(workspace)

    assert existing.read_text(encoding="utf-8") == "belongs to somebody else"
