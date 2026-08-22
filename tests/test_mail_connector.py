from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.correspondence import (
    build_correspondence_preview,
    load_correspondence_configuration,
    load_correspondence_request,
)
from folderhome.application.mail_connector import (
    MailConnectorError,
    build_mail_draft_preview,
    build_mail_ingest_plan,
    execute_mail_ingest,
    execute_mail_send,
    load_mail_accounts,
    load_mail_draft_request,
    load_mail_ingest_request,
    mail_send_idempotency_key,
)
from folderhome.capabilities.mail_gateway import MailActionLedger, SyntheticMailGateway
from folderhome.contracts import (
    ContactRecord,
    MailAttachmentReference,
    MailIngestApproval,
    MailMessageReference,
    MailSendApproval,
)

REPO_ROOT = Path(__file__).parents[1]
DOCS_GRABBER_REVISION = "0ccd03455b63acbca6e71cc48ba464f208a759cd"


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _accounts_file(tmp_path: Path, *, include_password: bool = False) -> Path:
    account: dict[str, object] = {
        "account_id": "family-mail",
        "profile_id": "lukas",
        "display_name": "Familienpostfach",
        "address": "lukas@example.invalid",
        "inbound": {
            "protocol": "imap",
            "host": "imap.example.invalid",
            "port": 993,
            "folder": "INBOX",
            "credential_ref": "keyring://folderhome/family-mail/imap",
            "provider_id": "universal-docs-grabber",
            "provider_revision": DOCS_GRABBER_REVISION,
        },
        "outbound": {
            "protocol": "smtp",
            "host": "smtp.example.invalid",
            "port": 465,
            "credential_ref": "keyring://folderhome/family-mail/smtp",
            "provider_id": "folderhome.synthetic-mail",
            "provider_revision": None,
        },
    }
    if include_password:
        account["password"] = "darf-nie-in-die-konfiguration"
    return _write_json(
        tmp_path / "accounts.json",
        {"schema": "folderhome.mail-accounts.v1", "accounts": [account]},
    )


def _ingest_request_file(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "ingest.json",
        {
            "schema": "folderhome.mail-ingest-request.v1",
            "request_id": "insurance-mail",
            "profile_id": "lukas",
            "account_id": "family-mail",
            "folder": "INBOX",
            "query": "Hyundai i10 Versicherung",
            "max_messages": 25,
            "include_attachments": True,
            "target_ref": "folder://Versicherungen/Hyundai-i10/Eingang",
        },
    )


def _contact() -> ContactRecord:
    digest = sha256(b"synthetic contact").hexdigest()
    return ContactRecord(
        contact_id=f"contact_{digest}",
        candidate_id=f"contact_candidate_{digest}",
        profile_id="lukas",
        area="versicherungen",
        organization="Beispiel Versicherung AG",
        contact_name="Mara Muster",
        role="Kundenservice",
        purpose="kfz-versicherung",
        object_ref="Hyundai i10",
        email="service@example.invalid",
        phone="+49 30 123456",
        effective_date="2026-08-01",
        source_document_id=f"doc_{digest}",
        source_sha256=digest,
        source_path=(
            REPO_ROOT
            / "examples"
            / "documents"
            / "contacts"
            / "Hyundai-i10-Versicherung.txt"
        ),
        status="active",
        created_at="2026-08-22T00:00:00Z",
        updated_at="2026-08-22T00:00:00Z",
    )


def _correspondence_preview(tmp_path: Path):
    source = json.loads(
        (REPO_ROOT / "examples" / "correspondence" / "insurance-cancellation.json").read_text(
            encoding="utf-8"
        )
    )
    source["sender"]["email"] = "lukas@example.invalid"
    source["recipient"]["email"] = "service@example.invalid"
    request = load_correspondence_request(_write_json(tmp_path / "letter.json", source))
    configuration = load_correspondence_configuration(
        REPO_ROOT / "examples" / "correspondence" / "designs.json",
        REPO_ROOT / "examples" / "correspondence" / "templates.json",
    )
    return build_correspondence_preview(
        request,
        configuration=configuration,
        report_forge_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        report_forge_distribution_version="1.1.4",
        report_forge_runtime_version="1.1.0",
    )


def test_mail_accounts_use_secret_references_and_reject_embedded_passwords(
    tmp_path: Path,
) -> None:
    accounts = load_mail_accounts(_accounts_file(tmp_path))
    assert accounts[0].inbound.credential_ref.startswith("keyring://")
    assert accounts[0].outbound is not None
    assert accounts[0].outbound.credential_ref.startswith("keyring://")
    assert "password" not in accounts[0].to_dict()

    with pytest.raises(MailConnectorError, match="unbekannte Felder"):
        load_mail_accounts(_accounts_file(tmp_path, include_password=True))


def test_ingest_plan_is_read_only_and_keeps_mailbox_mutations_out(
    tmp_path: Path,
) -> None:
    account = load_mail_accounts(_accounts_file(tmp_path))[0]
    request = load_mail_ingest_request(_ingest_request_file(tmp_path))
    plan = build_mail_ingest_plan(request, account=account, provider_ready=False)

    assert plan.status == "blocked"
    assert plan.provider_invoked is False
    assert plan.operations == ("fetch_headers", "fetch_attachments")
    assert plan.mailbox_mutations == ()
    assert "send" not in plan.to_dict()["operations"]
    assert "delete" not in plan.to_dict()["operations"]
    assert "move" not in plan.to_dict()["operations"]


def test_synthetic_read_only_ingest_requires_exact_approval(tmp_path: Path) -> None:
    account = load_mail_accounts(_accounts_file(tmp_path))[0]
    request = load_mail_ingest_request(_ingest_request_file(tmp_path))
    plan = build_mail_ingest_plan(
        request,
        account=account,
        provider_ready=True,
        provider_id="folderhome.synthetic-mail",
        provider_revision=None,
    )
    attachment = MailAttachmentReference(
        attachment_id=f"mail_attachment_{sha256(b'policy.pdf').hexdigest()}",
        filename="Police.pdf",
        media_type="application/pdf",
        size_bytes=1234,
        sha256=sha256(b"synthetic policy").hexdigest(),
        provider_ref="fixture://mail/42/attachment/1",
    )
    message = MailMessageReference(
        message_ref=f"mail_message_{sha256(b'message 42').hexdigest()}",
        account_id="family-mail",
        folder="INBOX",
        provider_uid="42",
        rfc_message_id="<synthetic-42@example.invalid>",
        sender="service@example.invalid",
        recipients=("lukas@example.invalid",),
        subject="Neue Police für Hyundai i10",
        received_at="2026-08-21T09:30:00Z",
        attachments=(attachment,),
    )
    gateway = SyntheticMailGateway(messages=(message,))
    approval = MailIngestApproval(
        approval_id="mail-ingest-fixture",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        approved_at="2026-08-22T03:00:00Z",
        allow_network_read=False,
        allow_attachment_write=False,
    )

    report = execute_mail_ingest(plan, approval=approval, gateway=gateway)

    assert report.status == "executed"
    assert report.messages == (message,)
    assert report.network_invoked is False
    assert report.mailbox_mutations == ()
    assert gateway.fetch_count == 1

    wrong = MailIngestApproval(
        approval_id="mail-ingest-wrong",
        plan_id=plan.plan_id,
        plan_sha256="0" * 64,
        approved_at="2026-08-22T03:00:00Z",
        allow_network_read=False,
        allow_attachment_write=False,
    )
    with pytest.raises(MailConnectorError, match="Planhash"):
        execute_mail_ingest(plan, approval=wrong, gateway=gateway)
    assert gateway.fetch_count == 1


def test_draft_requires_explicit_active_contact_and_exact_correspondence(
    tmp_path: Path,
) -> None:
    account = load_mail_accounts(_accounts_file(tmp_path))[0]
    contact = _contact()
    correspondence = _correspondence_preview(tmp_path)
    request_file = _write_json(
        tmp_path / "draft.json",
        {
            "schema": "folderhome.mail-draft-request.v1",
            "request_id": "send-insurance-letter",
            "profile_id": "lukas",
            "account_id": "family-mail",
            "recipient_contact_id": contact.contact_id,
            "recipient_email": "service@example.invalid",
            "correspondence_preview_id": correspondence.preview_id,
            "correspondence_text_sha256": correspondence.text_sha256,
            "attachments": [],
        },
    )
    request = load_mail_draft_request(request_file)

    preview = build_mail_draft_preview(
        request,
        account=account,
        contact=contact,
        correspondence=correspondence,
    )

    assert preview.to_address == "service@example.invalid"
    assert preview.contact_id == contact.contact_id
    assert preview.subject == correspondence.subject
    assert preview.body_text == correspondence.text
    assert preview.read_only is True
    assert preview.transport_invoked is False

    changed_contact = replace(contact, email="other@example.invalid")
    with pytest.raises(MailConnectorError, match="Empfängerzuordnung"):
        build_mail_draft_preview(
            request,
            account=account,
            contact=changed_contact,
            correspondence=correspondence,
        )


def test_synthetic_send_is_exactly_gated_audited_and_idempotent(tmp_path: Path) -> None:
    account = load_mail_accounts(_accounts_file(tmp_path))[0]
    contact = _contact()
    correspondence = _correspondence_preview(tmp_path)
    request = load_mail_draft_request(
        _write_json(
            tmp_path / "draft.json",
            {
                "schema": "folderhome.mail-draft-request.v1",
                "request_id": "send-insurance-letter",
                "profile_id": "lukas",
                "account_id": "family-mail",
                "recipient_contact_id": contact.contact_id,
                "recipient_email": contact.email,
                "correspondence_preview_id": correspondence.preview_id,
                "correspondence_text_sha256": correspondence.text_sha256,
                "attachments": [],
            },
        )
    )
    draft = build_mail_draft_preview(
        request,
        account=account,
        contact=contact,
        correspondence=correspondence,
    )
    approval = MailSendApproval(
        approval_id="mail-send-once",
        draft_id=draft.draft_id,
        draft_sha256=draft.draft_sha256,
        recipient_email=draft.to_address,
        approved_at="2026-08-22T03:05:00Z",
        idempotency_key=mail_send_idempotency_key(draft),
        allow_network_send=False,
    )
    gateway = SyntheticMailGateway(messages=())
    ledger = MailActionLedger(tmp_path / "state")

    report = execute_mail_send(
        draft,
        approval=approval,
        gateway=gateway,
        ledger=ledger,
    )

    assert report.status == "simulated"
    assert report.email_sent is False
    assert report.network_invoked is False
    assert report.recipient_email == "service@example.invalid"
    assert report.transport_message_id.startswith("synthetic-mail-")
    assert gateway.send_count == 1
    assert ledger.status(approval.idempotency_key) == "simulated"

    with pytest.raises(MailConnectorError, match="bereits verwendet"):
        execute_mail_send(
            draft,
            approval=approval,
            gateway=gateway,
            ledger=ledger,
        )
    assert gateway.send_count == 1


def test_network_gateway_cannot_send_without_separate_network_gate(tmp_path: Path) -> None:
    account = load_mail_accounts(_accounts_file(tmp_path))[0]
    contact = _contact()
    correspondence = _correspondence_preview(tmp_path)
    request = load_mail_draft_request(
        _write_json(
            tmp_path / "draft.json",
            {
                "schema": "folderhome.mail-draft-request.v1",
                "request_id": "network-gate",
                "profile_id": "lukas",
                "account_id": "family-mail",
                "recipient_contact_id": contact.contact_id,
                "recipient_email": contact.email,
                "correspondence_preview_id": correspondence.preview_id,
                "correspondence_text_sha256": correspondence.text_sha256,
                "attachments": [],
            },
        )
    )
    draft = build_mail_draft_preview(
        request,
        account=account,
        contact=contact,
        correspondence=correspondence,
    )
    class NetworkProbeGateway:
        provider_id = "folderhome.synthetic-mail"
        provider_revision = None
        network_required = True
        read_only_ingest = True

        def __init__(self) -> None:
            self.send_count = 0

        def send(self, draft, approval):
            self.send_count += 1
            return "must-not-run"

    gateway = NetworkProbeGateway()
    approval = MailSendApproval(
        approval_id="mail-network-denied",
        draft_id=draft.draft_id,
        draft_sha256=draft.draft_sha256,
        recipient_email=draft.to_address,
        approved_at="2026-08-22T03:10:00Z",
        idempotency_key=mail_send_idempotency_key(draft),
        allow_network_send=False,
    )

    with pytest.raises(MailConnectorError, match="Netzwerk-Versandfreigabe"):
        execute_mail_send(
            draft,
            approval=approval,
            gateway=gateway,
            ledger=MailActionLedger(tmp_path / "state"),
        )
    assert gateway.send_count == 0
