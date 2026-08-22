import json
from pathlib import Path

import pytest

from folderhome.application.personal_notes import (
    PersonalNoteWorkflowError,
    apply_personal_note_plan,
    build_personal_note_plan,
    load_personal_note_request,
)
from folderhome.bridges.llm_note import LlmNoteBridge
from folderhome.capabilities.personal_note_guide import SyntheticPersonalNoteGuide
from folderhome.contracts import (
    PersonalNoteAction,
    PersonalNoteApproval,
    PersonalNoteReference,
    PersonalNoteRequest,
    PluginDescriptor,
)

PROVIDER_ROOT = Path(__file__).parents[2] / "llm-note"
REVISION = "b5fe59fc155ded9603566aa0fb920a53181a2426"


def _plugin() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="llm-note",
        name="llm-note",
        version="1.0.3",
        source_repository="https://github.com/doc-bricks/llm-note.git",
        source_revision=REVISION,
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
        classification="REUSED_UNCHANGED",
        default_mode="dry-run",
        live_enabled=False,
    )


def _store(tmp_path: Path) -> LlmNoteBridge:
    return LlmNoteBridge(
        plugin=_plugin(),
        provider_root=PROVIDER_ROOT,
        db_path=tmp_path / "notes.db",
    )


def _request(
    *,
    action: PersonalNoteAction = PersonalNoteAction.CREATE,
    content: str | None = "Ich möchte den Arzttermin ruhig vorbereiten.",
    note_id: str | None = None,
    expected_revision: int | None = None,
    revert_to_revision: int | None = None,
) -> PersonalNoteRequest:
    return PersonalNoteRequest(
        request_id=f"request-{action.value}",
        action=action,
        profile_id="lukas",
        notebook_id="gesundheit",
        area="gesundheit",
        title="Vorbereitung Hausarzt",
        human_content=content,
        note_id=note_id,
        expected_revision=expected_revision,
        revert_to_revision=revert_to_revision,
        references=(
            PersonalNoteReference(
                kind="document",
                target_id="doc_hausarztbericht",
                label="Hausarztbericht",
                sha256="a" * 64,
            ),
            PersonalNoteReference(
                kind="calendar",
                target_id="calendar_event_kontrolltermin",
                label="Kontrolltermin",
                sha256=None,
            ),
        ),
    )


def _approval(plan) -> PersonalNoteApproval:
    return PersonalNoteApproval(
        approval_id=f"approval-{plan.action.value}",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        action_id=plan.action_id,
        content_sha256=plan.content_sha256,
        approved_at="2026-08-22T05:00:00+02:00",
        allow_local_note_write=True,
    )


def test_request_loader_is_strict_and_keeps_only_explicit_references(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema": "folderhome.personal-note-request.v1",
                "request_id": "request-create",
                "action": "create",
                "profile_id": "lukas",
                "notebook_id": "gesundheit",
                "area": "gesundheit",
                "title": "Arzttermin",
                "human_content": "Meine Fragen für den Termin.",
                "note_id": None,
                "expected_revision": None,
                "revert_to_revision": None,
                "references": [
                    {
                        "schema": "folderhome.personal-note-reference.v1",
                        "kind": "document",
                        "target_id": "doc_bericht",
                        "label": "Bericht",
                        "sha256": "b" * 64,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    request = load_personal_note_request(request_path)

    assert request.human_content == "Meine Fragen für den Termin."
    assert [(ref.kind, ref.target_id) for ref in request.references] == [
        ("document", "doc_bericht")
    ]

    payload = json.loads(request_path.read_text(encoding="utf-8"))
    payload["api_key"] = "must-not-be-accepted"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PersonalNoteWorkflowError, match="Unbekannte Felder.*api_key"):
        load_personal_note_request(request_path)


def test_synthetic_guide_separates_questions_from_human_content(tmp_path: Path) -> None:
    plan = build_personal_note_plan(
        _request(),
        store=_store(tmp_path),
        guide=SyntheticPersonalNoteGuide(),
    )

    assert plan.status == "review_required"
    assert plan.proposed_content == "Ich möchte den Arzttermin ruhig vorbereiten."
    assert plan.guidance.questions
    assert plan.guidance.suggestions
    assert plan.guidance.confirmed_content_changed is False
    assert plan.guidance.network_invoked is False
    assert plan.external_sync_invoked is False
    assert [ref.kind for ref in plan.references] == ["document", "calendar"]


def test_network_guide_is_blocked_before_invocation(tmp_path: Path) -> None:
    class RemoteGuide:
        provider_id = "remote-guide"
        provider_revision = "remote@1"
        network_required = True

        def __init__(self) -> None:
            self.called = False

        def guide(self, request, *, proposed_content):
            self.called = True
            raise AssertionError("must not be called")

    guide = RemoteGuide()
    with pytest.raises(PersonalNoteWorkflowError, match="Remote-LLM.*Freigabe"):
        build_personal_note_plan(_request(), store=_store(tmp_path), guide=guide)
    assert guide.called is False


def test_apply_uses_llm_note_append_only_and_replay_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    plan = build_personal_note_plan(
        _request(),
        store=store,
        guide=SyntheticPersonalNoteGuide(),
    )

    report = apply_personal_note_plan(
        plan,
        _approval(plan),
        store=store,
        allow_state_write=True,
    )

    assert report.status == "executed"
    assert report.provider_id == "llm-note"
    assert report.provider_revision == REVISION
    assert report.network_invoked is False
    assert report.external_sync_invoked is False
    history = store.history(plan.note_id)
    assert [(item.revision, item.human_content) for item in history] == [
        (1, "Ich möchte den Arzttermin ruhig vorbereiten.")
    ]
    assert history[0].author_kind == "human"
    assert history[0].source_plan_id == plan.plan_id

    with pytest.raises(PersonalNoteWorkflowError, match="bereits angewendet"):
        apply_personal_note_plan(
            plan,
            _approval(plan),
            store=store,
            allow_state_write=True,
        )
    assert len(store.history(plan.note_id)) == 1


def test_edit_and_revert_create_new_versions_without_overwrite(tmp_path: Path) -> None:
    store = _store(tmp_path)
    guide = SyntheticPersonalNoteGuide()
    create_plan = build_personal_note_plan(_request(), store=store, guide=guide)
    apply_personal_note_plan(
        create_plan,
        _approval(create_plan),
        store=store,
        allow_state_write=True,
    )

    edit_plan = build_personal_note_plan(
        _request(
            action=PersonalNoteAction.EDIT,
            content="Ich notiere drei konkrete Fragen für den Hausarzt.",
            note_id=create_plan.note_id,
            expected_revision=1,
        ),
        store=store,
        guide=guide,
    )
    apply_personal_note_plan(
        edit_plan,
        _approval(edit_plan),
        store=store,
        allow_state_write=True,
    )

    revert_plan = build_personal_note_plan(
        _request(
            action=PersonalNoteAction.REVERT,
            content=None,
            note_id=create_plan.note_id,
            expected_revision=2,
            revert_to_revision=1,
        ),
        store=store,
        guide=guide,
    )
    assert revert_plan.proposed_content == create_plan.proposed_content
    assert revert_plan.reverts_revision == 1
    apply_personal_note_plan(
        revert_plan,
        _approval(revert_plan),
        store=store,
        allow_state_write=True,
    )

    history = store.history(create_plan.note_id)
    assert [item.revision for item in history] == [1, 2, 3]
    assert history[0].human_content == history[2].human_content
    assert history[1].human_content != history[2].human_content
    assert history[2].action is PersonalNoteAction.REVERT
    assert history[2].reverts_revision == 1


def test_stale_revision_and_wrong_approval_block_before_write(tmp_path: Path) -> None:
    store = _store(tmp_path)
    plan = build_personal_note_plan(
        _request(), store=store, guide=SyntheticPersonalNoteGuide()
    )
    approval = _approval(plan)
    wrong = PersonalNoteApproval(
        approval_id="approval-wrong",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        action_id=plan.action_id,
        content_sha256="f" * 64,
        approved_at=approval.approved_at,
        allow_local_note_write=True,
    )
    with pytest.raises(PersonalNoteWorkflowError, match="Inhaltshash"):
        apply_personal_note_plan(plan, wrong, store=store, allow_state_write=True)
    assert store.history(plan.note_id) == ()

    apply_personal_note_plan(plan, approval, store=store, allow_state_write=True)
    stale = build_personal_note_plan(
        _request(
            action=PersonalNoteAction.EDIT,
            content="Neue Fassung",
            note_id=plan.note_id,
            expected_revision=1,
        ),
        store=store,
        guide=SyntheticPersonalNoteGuide(),
    )
    newer = build_personal_note_plan(
        _request(
            action=PersonalNoteAction.EDIT,
            content="Zwischenfassung",
            note_id=plan.note_id,
            expected_revision=1,
        ),
        store=store,
        guide=SyntheticPersonalNoteGuide(),
    )
    apply_personal_note_plan(newer, _approval(newer), store=store, allow_state_write=True)

    with pytest.raises(PersonalNoteWorkflowError, match="Store-Revision"):
        apply_personal_note_plan(
            stale,
            _approval(stale),
            store=store,
            allow_state_write=True,
        )
    assert len(store.history(plan.note_id)) == 2


def test_list_current_is_profile_not_security_boundary(tmp_path: Path) -> None:
    store = _store(tmp_path)
    plan = build_personal_note_plan(
        _request(), store=store, guide=SyntheticPersonalNoteGuide()
    )
    apply_personal_note_plan(plan, _approval(plan), store=store, allow_state_write=True)

    current = store.list_current(profile_id="lukas", area="gesundheit")

    assert [item.note_id for item in current] == [plan.note_id]
    assert current[0].os_account_is_security_boundary is True
    assert current[0].profile_is_security_boundary is False
