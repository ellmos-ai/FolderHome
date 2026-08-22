from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.contacts import (
    ContactWorkflowError,
    analyze_document_contact,
    analyze_folder_contacts,
    apply_contact_register_plan,
    build_contact_register_plan,
)
from folderhome.bridges.doc_services import UnsupportedDocumentError
from folderhome.capabilities.contact_registry import ContactRegisterStore
from folderhome.contracts import (
    ContactActionKind,
    ContactRegisterApproval,
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


class SyntheticExtractor:
    def extract(self, source_path: Path) -> DocumentRecord:
        if source_path.suffix.lower() != ".txt":
            raise UnsupportedDocumentError(
                f"Dateityp wird nicht unterstützt: {source_path.suffix}"
            )
        return _document(source_path, source_path.read_text(encoding="utf-8"))


def _document(
    source_path: Path,
    text: str,
    *,
    privacy_status: PrivacyStatus = PrivacyStatus.CLEAR,
) -> DocumentRecord:
    source_hash = sha256(source_path.read_bytes()).hexdigest()
    return DocumentRecord(
        document_id=build_document_id(source_path, source_hash),
        source_path=source_path,
        filename=source_path.name,
        media_type="text/plain",
        source_sha256=source_hash,
        size_bytes=source_path.stat().st_size,
        modified_at="2026-08-01T10:00:00Z",
        text=text,
        content_format=ContentFormat.TEXT,
        extraction_provider="synthetic-test",
        extraction_method="direct",
        privacy_status=privacy_status,
        privacy_summary="Synthetischer Datenschutzstatus.",
        index_status=IndexStatus.NOT_INDEXED,
        index_provider=None,
        index_ref=None,
    )


def _contact_text(
    *,
    name: str = "Erika Beispiel",
    email: str = "Erika.Beispiel@Example.invalid",
    phone: str = "+49 (30) 123 45 6",
    valid_from: str = "2026-08-01",
) -> str:
    return (
        "Dies ist ein vollständig synthetisches Dokument.\n"
        "Organisation: Beispiel Versicherung AG\n"
        f"Ansprechpartner: {name}\n"
        "Rolle: Kundenservice\n"
        "Zuständig für: KFZ-Versicherung\n"
        "Vertragsobjekt: Hyundai i10\n"
        f"E-Mail: {email}\n"
        f"Telefon: {phone}\n"
        f"Gültig ab: {valid_from}\n"
        "Interne Freitextnotiz: wird nicht in den Kontaktplan übernommen.\n"
    )


def _write_contact(path: Path, **kwargs: str) -> DocumentRecord:
    text = _contact_text(**kwargs)
    path.write_text(text, encoding="utf-8")
    return _document(path, text)


def _approval(plan, *, approval_id: str, approved_at: str):
    action_ids = tuple(
        action.action_id
        for action in plan.actions
        if action.status == "planned"
    )
    return ContactRegisterApproval(
        approval_id=approval_id,
        plan_id=plan.plan_id,
        register_revision=plan.register_revision,
        action_ids=action_ids,
        approved_at=approved_at,
    )


def test_labeled_contact_is_normalized_and_bound_to_line_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    document = _write_contact(source)

    result = analyze_document_contact(
        document,
        profile_id="lukas",
        area="versicherungen",
    )

    assert result.status == "candidate"
    assert result.candidate is not None
    candidate = result.candidate
    assert candidate.organization == "Beispiel Versicherung AG"
    assert candidate.contact_name == "Erika Beispiel"
    assert candidate.email == "erika.beispiel@example.invalid"
    assert candidate.phone == "+4930123456"
    assert candidate.purpose == "KFZ-Versicherung"
    assert candidate.object_ref == "Hyundai i10"
    assert candidate.effective_date == "2026-08-01"
    assert {evidence.field for evidence in candidate.evidence} >= {
        "organization",
        "email",
        "phone",
        "purpose",
        "object_ref",
    }
    assert all(evidence.line_number > 0 for evidence in candidate.evidence)
    payload = str(result.to_dict())
    assert "Interne Freitextnotiz" not in payload
    assert source.read_text(encoding="utf-8") == _contact_text()


def test_ambiguous_or_privacy_gated_contact_requires_review(tmp_path: Path) -> None:
    source = tmp_path / "Mehrdeutig.txt"
    text = _contact_text() + "E-Mail: zweite@example.invalid\n"
    source.write_text(text, encoding="utf-8")
    document = _document(source, text)

    ambiguous = analyze_document_contact(
        document,
        profile_id="lukas",
        area="versicherungen",
    )
    gated = analyze_document_contact(
        replace(document, privacy_status=PrivacyStatus.REVIEW_REQUIRED),
        profile_id="lukas",
        area="versicherungen",
    )

    assert ambiguous.status == "review_required"
    assert ambiguous.candidate is None
    assert any("mehrfach" in issue for issue in ambiguous.issues)
    assert gated.status == "review_required"
    assert gated.candidate is None
    assert any("Datenschutzstatus" in issue for issue in gated.issues)


def test_sensitive_local_contact_read_needs_explicit_gate_and_blocked_stays_blocked(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Kontakt.txt"
    document = _write_contact(source)
    review_document = replace(
        document,
        privacy_status=PrivacyStatus.REVIEW_REQUIRED,
    )
    blocked_document = replace(document, privacy_status=PrivacyStatus.BLOCKED)

    approved = analyze_document_contact(
        review_document,
        profile_id="lukas",
        area="versicherungen",
        allow_sensitive_local_read=True,
    )
    blocked = analyze_document_contact(
        blocked_document,
        profile_id="lukas",
        area="versicherungen",
        allow_sensitive_local_read=True,
    )

    assert approved.status == "candidate"
    assert approved.candidate is not None
    assert blocked.status == "blocked"
    assert blocked.candidate is None


def test_folder_analysis_keeps_unsupported_sources_visible_and_read_only(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Dokumente"
    source_root.mkdir()
    contact = source_root / "Police.txt"
    _write_contact(contact)
    unsupported = source_root / "Anlage.bin"
    unsupported.write_bytes(b"binary")
    before = {path: path.read_bytes() for path in source_root.iterdir()}

    analysis = analyze_folder_contacts(
        source_root,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
    )

    assert [item.relative_path for item in analysis.items] == [
        "Anlage.bin",
        "Police.txt",
    ]
    assert [item.status for item in analysis.items] == ["skipped", "candidate"]
    assert len(analysis.candidates) == 1
    assert {path: path.read_bytes() for path in source_root.iterdir()} == before


def test_register_plan_is_read_only_and_apply_requires_exact_gate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    document = _write_contact(source)
    analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )
    store = ContactRegisterStore(tmp_path / "state")

    plan = build_contact_register_plan(analysis, store=store)

    assert plan.actions[0].kind is ContactActionKind.CREATE
    assert plan.actions[0].status == "planned"
    assert not store.path.exists()
    with pytest.raises(ContactWorkflowError, match="State-Freigabe"):
        apply_contact_register_plan(
            plan,
            _approval(
                plan,
                approval_id="contact_create",
                approved_at="2026-08-21T22:00:00Z",
            ),
            store=store,
            allow_state_write=False,
        )
    assert not store.path.exists()
    assert source.read_text(encoding="utf-8") == document.text


def test_approved_contact_is_registered_and_queryable_by_object(tmp_path: Path) -> None:
    source = tmp_path / "Police.txt"
    before = _write_contact(source).source_sha256
    analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )
    store = ContactRegisterStore(tmp_path / "state")
    plan = build_contact_register_plan(analysis, store=store)

    report = apply_contact_register_plan(
        plan,
        _approval(
            plan,
            approval_id="contact_create",
            approved_at="2026-08-21T22:00:00Z",
        ),
        store=store,
        allow_state_write=True,
    )

    assert report.status == "applied"
    assert len(report.created_contact_ids) == 1
    contacts = store.list_contacts(
        profile_id="lukas",
        area="versicherungen",
        object_query="hyundai i10",
    )
    assert len(contacts) == 1
    assert contacts[0].status == "active"
    assert contacts[0].email == "erika.beispiel@example.invalid"
    assert sha256(source.read_bytes()).hexdigest() == before
    assert store.count_events() == 1


def test_newer_contact_replaces_active_and_only_marks_old_as_deletion_candidate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Police.txt"
    _write_contact(source)
    store = ContactRegisterStore(tmp_path / "state")
    first_analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )
    first_plan = build_contact_register_plan(first_analysis, store=store)
    apply_contact_register_plan(
        first_plan,
        _approval(
            first_plan,
            approval_id="contact_first",
            approved_at="2026-08-21T22:00:00Z",
        ),
        store=store,
        allow_state_write=True,
    )
    old_contact = store.list_contacts()[0]
    _write_contact(
        source,
        name="Max Neu",
        email="max.neu@example.invalid",
        phone="+49 30 999999",
        valid_from="2026-09-01",
    )
    second_analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )

    second_plan = build_contact_register_plan(second_analysis, store=store)

    assert second_plan.actions[0].kind is ContactActionKind.REPLACE
    assert second_plan.actions[0].prior_contact_id == old_contact.contact_id
    assert store.list_contacts()[0].status == "active"
    report = apply_contact_register_plan(
        second_plan,
        _approval(
            second_plan,
            approval_id="contact_replace",
            approved_at="2026-08-21T22:10:00Z",
        ),
        store=store,
        allow_state_write=True,
    )

    contacts = store.list_contacts(include_deletion_candidates=True)
    assert report.marked_contact_ids == (old_contact.contact_id,)
    assert len(contacts) == 2
    assert {contact.status for contact in contacts} == {
        "active",
        "deletion_candidate",
    }
    assert next(contact for contact in contacts if contact.status == "active").contact_name == (
        "Max Neu"
    )
    assert store.count_events() == 2


def test_changed_source_or_register_revision_blocks_before_write(tmp_path: Path) -> None:
    source = tmp_path / "Police.txt"
    _write_contact(source)
    store = ContactRegisterStore(tmp_path / "state")
    analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )
    plan = build_contact_register_plan(analysis, store=store)
    approval = _approval(
        plan,
        approval_id="contact_stale",
        approved_at="2026-08-21T22:00:00Z",
    )
    source.write_text("geändert", encoding="utf-8")

    with pytest.raises(ContactWorkflowError, match="Quellhash"):
        apply_contact_register_plan(
            plan,
            approval,
            store=store,
            allow_state_write=True,
        )

    assert not store.path.exists()


def test_folder_plan_uses_only_latest_candidate_for_one_assignment(tmp_path: Path) -> None:
    _write_contact(
        tmp_path / "Alt.txt",
        name="Erika Alt",
        email="erika.alt@example.invalid",
        valid_from="2026-08-01",
    )
    _write_contact(
        tmp_path / "Neu.txt",
        name="Max Neu",
        email="max.neu@example.invalid",
        valid_from="2026-09-01",
    )
    analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )

    plan = build_contact_register_plan(
        analysis,
        store=ContactRegisterStore(tmp_path / "state"),
    )

    assert [action.kind for action in plan.actions].count(ContactActionKind.CREATE) == 1
    assert [action.kind for action in plan.actions].count(ContactActionKind.NOOP) == 1
    selected = next(action for action in plan.actions if action.status == "planned")
    assert selected.candidate.contact_name == "Max Neu"


def test_same_date_conflicting_folder_contacts_are_all_blocked(tmp_path: Path) -> None:
    _write_contact(
        tmp_path / "A.txt",
        name="Erika A",
        email="erika.a@example.invalid",
    )
    _write_contact(
        tmp_path / "B.txt",
        name="Max B",
        email="max.b@example.invalid",
    )
    analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )

    plan = build_contact_register_plan(
        analysis,
        store=ContactRegisterStore(tmp_path / "state"),
    )

    assert len(plan.actions) == 2
    assert all(action.kind is ContactActionKind.BLOCKED for action in plan.actions)
    assert all(action.status == "blocked" for action in plan.actions)


def test_contact_approval_requires_timezone_aware_timestamp(tmp_path: Path) -> None:
    _write_contact(tmp_path / "Police.txt")
    analysis = analyze_folder_contacts(
        tmp_path,
        profile_id="lukas",
        area="versicherungen",
        extractor=SyntheticExtractor(),
        recursive=False,
    )
    plan = build_contact_register_plan(
        analysis,
        store=ContactRegisterStore(tmp_path / "state"),
    )

    with pytest.raises(ValueError, match="Zeitzone"):
        _approval(
            plan,
            approval_id="contact_time",
            approved_at="2026-08-21T22:00:00",
        )
