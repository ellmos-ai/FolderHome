from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.correspondence import (
    build_correspondence_preview,
    load_correspondence_configuration,
    load_correspondence_request,
)
from folderhome.application.mail_draft import (
    append_mail_draft,
    build_mail_draft_message,
    load_mail_draft_account,
)
from folderhome.capabilities.mail_draft import (
    MailDraftError,
    MailDraftLedger,
    SyntheticDraftTransport,
    read_mailbox_password,
)
from folderhome.contracts.correspondence import CorrespondencePreview

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples" / "correspondence"
REPORT_FORGE_REVISION = "355acb5ff1abe41b384a0d1e3a00925e6ac86215"
PLANNED_AT = "2026-08-25T09:00:00+02:00"


class _FailingTransport:
    transport_id = "folderhome.failing-draft"
    network_required = True

    def append_draft(self, *, folder: str, message_bytes: bytes) -> str:
        raise MailDraftError("Postfach hat die Entwurfsablage abgelehnt: NO.")


def _preview(
    tmp_path: Path,
    *,
    recipient_email: str | None,
    attachments: list[str],
) -> CorrespondencePreview:
    request_file = tmp_path / "letter.json"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.correspondence-request.v1",
                "profile_id": "lukas",
                "area": "versicherungen",
                "purpose": "kuendigung",
                "template_id": "insurance-cancellation",
                "created_on": "2026-08-22",
                "sender": {
                    "name": "Lukas Beispiel",
                    "address_lines": ["Musterweg 1", "12345 Beispielstadt"],
                    "email": "lukas@example.invalid",
                    "phone": None,
                },
                "recipient": {
                    "name": "Beispiel Versicherung AG",
                    "address_lines": ["Versicherungsplatz 2", "54321 Beispielstadt"],
                    "email": recipient_email,
                    "phone": None,
                },
                "variables": {
                    "policy_number": "SYN-4711",
                    "vehicle": "Hyundai i10",
                    "termination_date": "31.12.2026",
                },
                "attachments": attachments,
                "evidence_refs": [
                    "doc_" + "a" * 64,
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    configuration = load_correspondence_configuration(
        EXAMPLES / "designs.json",
        EXAMPLES / "templates.json",
    )
    return build_correspondence_preview(
        load_correspondence_request(request_file),
        configuration=configuration,
        report_forge_revision=REPORT_FORGE_REVISION,
        report_forge_distribution_version="1.1.4",
        report_forge_runtime_version="1.1.0",
    )


def _account_file(tmp_path: Path, *, password_file: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "schema": "folderhome.mail-draft-account.v1",
        "account_id": "family-mailbox",
        "profile_id": "lukas",
        "display_name": "Lukas Beispiel",
        "from_address": "lukas@example.invalid",
        "host": "imap.example.invalid",
        "port": 993,
        "use_ssl": True,
        "username": "lukas@example.invalid",
        "drafts_folder": "INBOX.Drafts",
        "password_file": str(password_file),
    }
    payload.update(overrides)
    path = tmp_path / "mail-draft-account.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _password_file(tmp_path: Path, value: str = "synthetisches-geheimnis") -> Path:
    path = tmp_path / "mailbox-password.txt"
    path.write_text(value, encoding="utf-8")
    return path


def test_account_loads_without_any_embedded_secret(tmp_path: Path) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )

    assert account.account_id == "family-mailbox"
    assert account.drafts_folder == "INBOX.Drafts"
    public = account.to_public_dict()
    assert public["credentials_disclosed"] is False
    assert public["host_disclosed"] is False
    assert "password_file" not in public
    assert "host" not in public
    assert "username" not in public


def test_account_rejects_unknown_field_and_plaintext_password(tmp_path: Path) -> None:
    path = tmp_path / "account.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.mail-draft-account.v1",
                "account_id": "family-mailbox",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "from_address": "lukas@example.invalid",
                "host": "imap.example.invalid",
                "port": 993,
                "use_ssl": True,
                "username": "lukas@example.invalid",
                "drafts_folder": "INBOX.Drafts",
                "password_file": str(tmp_path / "pw.txt"),
                "password": "geheim",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MailDraftError, match="unbekannte Felder"):
        load_mail_draft_account(path)


def test_account_requires_tls_and_ascii_folder(tmp_path: Path) -> None:
    password_file = _password_file(tmp_path)
    with pytest.raises(MailDraftError, match="TLS"):
        load_mail_draft_account(
            _account_file(tmp_path, password_file=password_file, use_ssl=False)
        )
    with pytest.raises(MailDraftError, match="ASCII-IMAP-Name"):
        load_mail_draft_account(
            _account_file(
                tmp_path,
                password_file=password_file,
                drafts_folder="Entwürfe",
            )
        )


def test_draft_message_is_deterministic_and_hides_body(tmp_path: Path) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )
    preview = _preview(tmp_path, recipient_email="service@example.invalid", attachments=[])

    first = build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)
    second = build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)

    assert first.draft_id == second.draft_id
    assert first.message_sha256 == second.message_sha256
    assert first.idempotency_key == second.idempotency_key
    assert sha256(first.message_bytes).hexdigest() == first.message_sha256
    assert b"Subject:" in first.message_bytes

    public = first.to_public_dict()
    assert public["delivery_attempted"] is False
    assert public["recipient_disclosed"] is False
    assert public["body_disclosed"] is False
    assert public["attachment_count"] == 0
    serialized = json.dumps(public, ensure_ascii=False)
    assert "service@example.invalid" not in serialized
    assert preview.text[:40] not in serialized


def test_draft_requires_recipient_address_and_rejects_attachments(tmp_path: Path) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )

    without_email = _preview(tmp_path, recipient_email=None, attachments=[])
    with pytest.raises(MailDraftError, match="E-Mail-Adresse"):
        build_mail_draft_message(without_email, account=account, planned_at=PLANNED_AT)

    with_attachment = _preview(
        tmp_path,
        recipient_email="service@example.invalid",
        attachments=["Versicherungsschein in Kopie"],
    )
    with pytest.raises(MailDraftError, match="ohne Anhänge"):
        build_mail_draft_message(
            with_attachment, account=account, planned_at=PLANNED_AT
        )


def test_append_is_blocked_without_the_separate_live_effect_approval(
    tmp_path: Path,
) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )
    preview = _preview(tmp_path, recipient_email="service@example.invalid", attachments=[])
    message = build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)
    transport = SyntheticDraftTransport()
    ledger = MailDraftLedger(tmp_path / "state")

    with pytest.raises(MailDraftError, match="--approve-mail-draft"):
        append_mail_draft(
            message,
            account=account,
            transport=transport,
            ledger=ledger,
            allow_mailbox_write=False,
            appended_at=PLANNED_AT,
        )

    assert transport.appended == []
    assert ledger.status(message.idempotency_key) is None


def test_append_places_exactly_one_draft_and_refuses_a_replay(tmp_path: Path) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )
    preview = _preview(tmp_path, recipient_email="service@example.invalid", attachments=[])
    message = build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)
    transport = SyntheticDraftTransport()
    ledger = MailDraftLedger(tmp_path / "state")

    report = append_mail_draft(
        message,
        account=account,
        transport=transport,
        ledger=ledger,
        allow_mailbox_write=True,
        appended_at=PLANNED_AT,
    )

    assert report.status == "drafted"
    assert report.to_dict()["email_sent"] is False
    assert report.to_dict()["delivery_attempted"] is False
    assert ledger.status(message.idempotency_key) == "drafted"
    assert len(transport.appended) == 1
    folder, raw = transport.appended[0]
    assert folder == "INBOX.Drafts"
    assert b"service@example.invalid" in raw

    with pytest.raises(MailDraftError, match="bereits abgelegt"):
        append_mail_draft(
            message,
            account=account,
            transport=transport,
            ledger=ledger,
            allow_mailbox_write=True,
            appended_at=PLANNED_AT,
        )
    assert len(transport.appended) == 1


def test_failed_append_is_recorded_and_does_not_block_a_later_retry(
    tmp_path: Path,
) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )
    preview = _preview(tmp_path, recipient_email="service@example.invalid", attachments=[])
    message = build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)
    ledger = MailDraftLedger(tmp_path / "state")

    with pytest.raises(MailDraftError, match="abgelehnt"):
        append_mail_draft(
            message,
            account=account,
            transport=_FailingTransport(),
            ledger=ledger,
            allow_mailbox_write=True,
            appended_at=PLANNED_AT,
        )

    assert ledger.status(message.idempotency_key) == "failed"


def test_password_is_read_from_the_configured_file_only(tmp_path: Path) -> None:
    password_file = _password_file(tmp_path, "synthetisches-geheimnis\n")
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=password_file)
    )

    assert read_mailbox_password(account) == "synthetisches-geheimnis"

    password_file.write_text("", encoding="utf-8")
    with pytest.raises(MailDraftError, match="leer"):
        read_mailbox_password(account)

    password_file.unlink()
    with pytest.raises(MailDraftError, match="Passwort-Fundort fehlt"):
        read_mailbox_password(account)


def test_draft_is_bound_to_its_own_account(tmp_path: Path) -> None:
    account = load_mail_draft_account(
        _account_file(tmp_path, password_file=_password_file(tmp_path))
    )
    other = load_mail_draft_account(
        _account_file(
            tmp_path,
            password_file=_password_file(tmp_path),
            account_id="other-mailbox",
        )
    )
    preview = _preview(tmp_path, recipient_email="service@example.invalid", attachments=[])
    message = build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)

    with pytest.raises(MailDraftError, match="nicht zum ausgewählten Entwurfskonto"):
        append_mail_draft(
            message,
            account=other,
            transport=SyntheticDraftTransport(),
            ledger=MailDraftLedger(tmp_path / "state"),
            allow_mailbox_write=True,
            appended_at=PLANNED_AT,
        )


def test_profile_mismatch_between_letter_and_mailbox_fails_closed(
    tmp_path: Path,
) -> None:
    account = load_mail_draft_account(
        _account_file(
            tmp_path,
            password_file=_password_file(tmp_path),
            profile_id="mila",
        )
    )
    preview = _preview(tmp_path, recipient_email="service@example.invalid", attachments=[])

    with pytest.raises(MailDraftError, match="anderen Profilen"):
        build_mail_draft_message(preview, account=account, planned_at=PLANNED_AT)
