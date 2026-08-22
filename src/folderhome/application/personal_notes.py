"""Plan and apply human-authored notes with separate LLM guidance."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.bridges.llm_note import LlmNoteBridge, LlmNoteBridgeError
from folderhome.contracts.personal_notes import (
    PersonalNoteAction,
    PersonalNoteApproval,
    PersonalNoteExecutionReport,
    PersonalNoteGuidance,
    PersonalNotePlan,
    PersonalNoteReference,
    PersonalNoteRequest,
    PersonalNoteVersion,
)


class PersonalNoteWorkflowError(RuntimeError):
    """Raised before an unapproved or inconsistent note write."""


class PersonalNoteGuide(Protocol):
    provider_id: str
    provider_revision: str
    network_required: bool

    def guide(
        self,
        request: PersonalNoteRequest,
        *,
        proposed_content: str,
    ) -> PersonalNoteGuidance: ...


def load_personal_note_request(path: Path) -> PersonalNoteRequest:
    payload = _read_object(path, schema=PersonalNoteRequest.SCHEMA, label="Notizanfrage")
    allowed = {
        "request_id",
        "action",
        "profile_id",
        "notebook_id",
        "area",
        "title",
        "human_content",
        "note_id",
        "expected_revision",
        "revert_to_revision",
        "references",
    }
    unknown = sorted(set(payload).difference(allowed))
    if unknown:
        raise PersonalNoteWorkflowError("Unbekannte Felder in Notizanfrage: " + ", ".join(unknown))
    required = {"request_id", "action", "profile_id", "notebook_id", "area", "title"}
    missing = sorted(required.difference(payload))
    if missing:
        raise PersonalNoteWorkflowError("Notizanfrage fehlt Feld: " + missing[0])
    raw_refs = payload.get("references", [])
    if not isinstance(raw_refs, list):
        raise PersonalNoteWorkflowError("Notizreferenzen müssen eine Liste sein.")
    references = tuple(_load_reference(item, index=index) for index, item in enumerate(raw_refs))
    try:
        return PersonalNoteRequest(
            request_id=payload["request_id"],
            action=PersonalNoteAction(payload["action"]),
            profile_id=payload["profile_id"],
            notebook_id=payload["notebook_id"],
            area=payload["area"],
            title=payload["title"],
            human_content=payload.get("human_content"),
            note_id=payload.get("note_id"),
            expected_revision=payload.get("expected_revision"),
            revert_to_revision=payload.get("revert_to_revision"),
            references=references,
        )
    except (TypeError, ValueError) as exc:
        raise PersonalNoteWorkflowError(f"Ungültige Notizanfrage: {exc}") from exc


def build_personal_note_plan(
    request: PersonalNoteRequest,
    *,
    store: LlmNoteBridge,
    guide: PersonalNoteGuide,
    allow_external_llm: bool = False,
) -> PersonalNotePlan:
    if guide.network_required and not allow_external_llm:
        raise PersonalNoteWorkflowError("Remote-LLM benötigt eine gesonderte Freigabe.")
    if guide.network_required:
        raise PersonalNoteWorkflowError("Remote-LLM ist in Phase 28 nicht ausführbar.")

    store_revision = store.revision()
    note_id = request.note_id or _note_id(request)
    history = store.history(note_id)
    if request.action is PersonalNoteAction.CREATE:
        if history:
            raise PersonalNoteWorkflowError("Notiz-ID ist bereits vorhanden.")
        proposed_content = request.human_content or ""
        next_revision = 1
        parent_revision = None
        reverts_revision = None
    else:
        if not history:
            raise PersonalNoteWorkflowError("Bestehende Notiz wurde nicht gefunden.")
        latest = history[-1]
        if latest.revision != request.expected_revision:
            raise PersonalNoteWorkflowError("Erwartete Notizrevision ist nicht aktuell.")
        if (
            latest.profile_id,
            latest.notebook_id,
            latest.area,
        ) != (request.profile_id, request.notebook_id, request.area):
            raise PersonalNoteWorkflowError(
                "Notiz gehört nicht zum angegebenen Profil und Bereich."
            )
        next_revision = latest.revision + 1
        parent_revision = latest.revision
        reverts_revision = request.revert_to_revision
        if request.action is PersonalNoteAction.REVERT:
            matches = [item for item in history if item.revision == request.revert_to_revision]
            if not matches:
                raise PersonalNoteWorkflowError("Rückkehrziel wurde nicht gefunden.")
            proposed_content = matches[0].human_content
        else:
            proposed_content = request.human_content or ""

    guidance = guide.guide(request, proposed_content=proposed_content)
    if guidance.confirmed_content_changed or guidance.network_invoked:
        raise PersonalNoteWorkflowError("Notizführung verletzte Inhalts- oder Netzwerkgrenze.")
    content_sha256 = _sha(proposed_content)
    core = {
        "request": request.to_dict(),
        "note_id": note_id,
        "proposed_content": proposed_content,
        "content_sha256": content_sha256,
        "next_revision": next_revision,
        "parent_revision": parent_revision,
        "reverts_revision": reverts_revision,
        "guidance": guidance.to_dict(),
        "store_revision": store_revision,
    }
    digest = _sha(_canonical_json(core))
    plan_id = f"personal_note_plan_{digest}"
    action_id = f"personal_note_action_{_sha(plan_id + ':' + request.action.value)}"
    plan_core = {**core, "plan_id": plan_id, "action_id": action_id}
    plan_sha256 = _sha(_canonical_json(plan_core))
    return PersonalNotePlan(
        plan_id=plan_id,
        plan_sha256=plan_sha256,
        action_id=action_id,
        request_id=request.request_id,
        action=request.action,
        note_id=note_id,
        profile_id=request.profile_id,
        notebook_id=request.notebook_id,
        area=request.area,
        title=request.title,
        proposed_content=proposed_content,
        content_sha256=content_sha256,
        next_revision=next_revision,
        parent_revision=parent_revision,
        reverts_revision=reverts_revision,
        references=request.references,
        guidance=guidance,
        store_revision=store_revision,
        status="review_required",
    )


def apply_personal_note_plan(
    plan: PersonalNotePlan,
    approval: PersonalNoteApproval,
    *,
    store: LlmNoteBridge,
    allow_state_write: bool,
) -> PersonalNoteExecutionReport:
    if not allow_state_write or not approval.allow_local_note_write:
        raise PersonalNoteWorkflowError("Lokale Notizablage benötigt beide Schreibfreigaben.")
    if approval.plan_id != plan.plan_id or approval.plan_sha256 != plan.plan_sha256:
        raise PersonalNoteWorkflowError("Notizfreigabe stimmt nicht mit dem Plan überein.")
    if approval.action_id != plan.action_id:
        raise PersonalNoteWorkflowError("Notizfreigabe stimmt nicht mit der Aktion überein.")
    if approval.content_sha256 != plan.content_sha256:
        raise PersonalNoteWorkflowError("Notizfreigabe besitzt einen anderen Inhaltshash.")
    if store.source_plan_applied(plan.plan_id):
        raise PersonalNoteWorkflowError("Notizplan wurde bereits angewendet.")
    if store.revision() != plan.store_revision:
        raise PersonalNoteWorkflowError("llm-note-Store-Revision hat sich seit dem Plan geändert.")
    history = store.history(plan.note_id)
    current_revision = history[-1].revision if history else 0
    if current_revision != plan.next_revision - 1:
        raise PersonalNoteWorkflowError("Notizrevision hat sich seit dem Plan geändert.")

    version = PersonalNoteVersion(
        note_id=plan.note_id,
        revision=plan.next_revision,
        action=plan.action,
        profile_id=plan.profile_id,
        notebook_id=plan.notebook_id,
        area=plan.area,
        title=plan.title,
        human_content=plan.proposed_content,
        references=plan.references,
        source_plan_id=plan.plan_id,
        parent_revision=plan.parent_revision,
        reverts_revision=plan.reverts_revision,
        created_at=approval.approved_at,
    )
    try:
        stored = store.append_version(version)
    except LlmNoteBridgeError as exc:
        raise PersonalNoteWorkflowError(str(exc)) from exc
    report_digest = _sha(f"{plan.plan_id}:{approval.approval_id}:{stored.provider_entry_id}")
    return PersonalNoteExecutionReport(
        report_id=f"personal_note_report_{report_digest}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        note_id=plan.note_id,
        revision=stored.revision,
        provider_id=store.provider_id,
        provider_revision=store.provider_revision,
        status="executed",
        network_invoked=False,
        external_sync_invoked=False,
    )


def _load_reference(payload: object, *, index: int) -> PersonalNoteReference:
    if not isinstance(payload, dict):
        raise PersonalNoteWorkflowError(f"Notizreferenz {index} ist kein Objekt.")
    data = dict(payload)
    if data.pop("schema", None) != PersonalNoteReference.SCHEMA:
        raise PersonalNoteWorkflowError(f"Notizreferenz {index} besitzt ein unbekanntes Schema.")
    expected = {"kind", "target_id", "label", "sha256"}
    unknown = sorted(set(data).difference(expected))
    missing = sorted(expected.difference(data))
    if unknown or missing:
        detail = unknown[0] if unknown else missing[0]
        raise PersonalNoteWorkflowError(f"Notizreferenz {index} besitzt ungültiges Feld: {detail}")
    try:
        return PersonalNoteReference(**data)
    except (TypeError, ValueError) as exc:
        raise PersonalNoteWorkflowError(f"Ungültige Notizreferenz {index}: {exc}") from exc


def _read_object(path: Path, *, schema: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PersonalNoteWorkflowError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise PersonalNoteWorkflowError(f"{label} besitzt ein unbekanntes Schema.")
    result = dict(payload)
    result.pop("schema")
    return result


def _note_id(request: PersonalNoteRequest) -> str:
    identity = ":".join(
        (request.profile_id, request.notebook_id, request.area, request.request_id)
    )
    return f"note_{_sha(identity)[:32]}"


def _sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
