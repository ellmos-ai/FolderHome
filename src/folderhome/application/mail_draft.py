"""Place one prepared letter into the user's own drafts folder; never send it.

The whole module has no delivery path. It renders exactly one correspondence
preview into an RFC 5322 message and appends it to one configured IMAP drafts
folder that belongs to the FolderHome user.
"""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.utils import format_datetime, formataddr
from hashlib import sha256
from pathlib import Path

from folderhome.capabilities.mail_draft import (
    MailDraftError,
    MailDraftLedger,
    MailDraftTransport,
)
from folderhome.contracts.correspondence import CorrespondencePreview
from folderhome.contracts.mail_draft import (
    MailDraftAccount,
    MailDraftMessage,
    MailDraftReport,
)

_ACCOUNT_FIELDS = {
    "schema",
    "account_id",
    "profile_id",
    "display_name",
    "from_address",
    "host",
    "port",
    "use_ssl",
    "username",
    "drafts_folder",
    "password_file",
}


def load_mail_draft_account(path: Path) -> MailDraftAccount:
    """Load one strict drafts-mailbox configuration without any embedded secret."""

    if path.is_symlink() or not path.is_file():
        raise MailDraftError(
            f"Entwurfskonto fehlt oder ist kein reguläres File: {path.name}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MailDraftError(f"Entwurfskonto ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise MailDraftError("Entwurfskonto muss ein JSON-Objekt sein.")
    unknown = sorted(set(payload).difference(_ACCOUNT_FIELDS))
    missing = sorted(_ACCOUNT_FIELDS.difference(payload))
    if unknown:
        raise MailDraftError(
            "Entwurfskonto enthält unbekannte Felder: " + ", ".join(unknown)
        )
    if missing:
        raise MailDraftError("Entwurfskonto benötigt Felder: " + ", ".join(missing))
    if payload["schema"] != MailDraftAccount.SCHEMA:
        raise MailDraftError("Entwurfskonto verwendet ein unbekanntes Schema.")
    raw_password_file = payload["password_file"]
    if not isinstance(raw_password_file, str) or not raw_password_file.strip():
        raise MailDraftError("Entwurfskonto benötigt einen Passwort-Fundort.")
    try:
        return MailDraftAccount(
            account_id=_text(payload, "account_id"),
            profile_id=_text(payload, "profile_id"),
            display_name=_text(payload, "display_name"),
            from_address=_text(payload, "from_address"),
            host=_text(payload, "host"),
            port=_integer(payload, "port"),
            use_ssl=_boolean(payload, "use_ssl"),
            username=_text(payload, "username"),
            drafts_folder=_text(payload, "drafts_folder"),
            password_file=Path(raw_password_file),
        )
    except ValueError as exc:
        raise MailDraftError(f"Entwurfskonto ist ungültig: {exc}") from exc


def build_mail_draft_message(
    preview: CorrespondencePreview,
    *,
    account: MailDraftAccount,
    planned_at: str,
) -> MailDraftMessage:
    """Render exactly one preview into one deterministic, unsent draft message."""

    if preview.request.profile_id != account.profile_id:
        raise MailDraftError("Schreiben und Entwurfskonto gehören zu anderen Profilen.")
    recipient_email = preview.request.recipient.email
    if recipient_email is None or not recipient_email.strip():
        raise MailDraftError(
            "Ein Mailentwurf benötigt eine E-Mail-Adresse im Empfängerdatensatz "
            "des Schreibens."
        )
    sender_email = preview.request.sender.email
    if sender_email is not None and sender_email != account.from_address:
        raise MailDraftError(
            "Briefabsender und Entwurfskonto weichen voneinander ab."
        )
    if preview.request.attachments:
        raise MailDraftError(
            "Diese Fassung legt ausschließlich Text ohne Anhänge als Entwurf ab; "
            "die im Schreiben genannten Anlagen sind vor dem Senden manuell "
            "anzuhängen."
        )
    try:
        timestamp = datetime.fromisoformat(planned_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MailDraftError("Entwurfszeitpunkt muss ein ISO-Zeitstempel sein.") from exc
    if timestamp.tzinfo is None:
        raise MailDraftError("Entwurfszeitpunkt benötigt eine Zeitzone.")

    material = _canonical_json(
        {
            "account_id": account.account_id,
            "profile_id": account.profile_id,
            "correspondence_preview_id": preview.preview_id,
            "subject": preview.subject,
            "body_sha256": preview.text_sha256,
            "drafts_folder": account.drafts_folder,
            "planned_at": planned_at,
            "from_address": account.from_address,
            "to_address": recipient_email,
        }
    )
    draft_digest = sha256(material).hexdigest()
    message = EmailMessage()
    message["From"] = formataddr((account.display_name, account.from_address))
    message["To"] = formataddr(
        (preview.request.recipient.name, recipient_email)
    )
    message["Subject"] = preview.subject
    message["Date"] = format_datetime(timestamp)
    message["Message-ID"] = (
        f"<folderhome-{draft_digest[:32]}@{account.from_address.split('@', 1)[1]}>"
    )
    message.set_content(
        preview.text,
        subtype="plain",
        charset="utf-8",
        cte="quoted-printable",
    )
    message_bytes = message.as_bytes(policy=policy.SMTP)
    message_sha256 = sha256(message_bytes).hexdigest()
    idempotency_material = (
        f"mail_draft_append_{draft_digest}\0{message_sha256}\0{account.account_id}"
    )
    try:
        return MailDraftMessage(
            draft_id=f"mail_draft_append_{draft_digest}",
            account_id=account.account_id,
            profile_id=account.profile_id,
            correspondence_preview_id=preview.preview_id,
            subject=preview.subject,
            body_sha256=preview.text_sha256,
            message_bytes=message_bytes,
            message_sha256=message_sha256,
            idempotency_key=(
                "mail_draft_key_"
                + sha256(idempotency_material.encode("utf-8")).hexdigest()
            ),
            drafts_folder=account.drafts_folder,
            planned_at=planned_at,
            attachment_count=0,
        )
    except ValueError as exc:
        raise MailDraftError(f"Entwurf ist ungültig: {exc}") from exc


def append_mail_draft(
    message: MailDraftMessage,
    *,
    account: MailDraftAccount,
    transport: MailDraftTransport,
    ledger: MailDraftLedger,
    allow_mailbox_write: bool,
    appended_at: str,
) -> MailDraftReport:
    """Append one reserved draft behind the separate live-effect approval."""

    if not allow_mailbox_write:
        raise MailDraftError(
            "Die Entwurfsablage in ein echtes Postfach benötigt die getrennte "
            "Freigabe --approve-mail-draft."
        )
    if (
        message.account_id != account.account_id
        or message.profile_id != account.profile_id
        or message.drafts_folder != account.drafts_folder
    ):
        raise MailDraftError("Entwurf gehört nicht zum ausgewählten Entwurfskonto.")
    if sha256(message.message_bytes).hexdigest() != message.message_sha256:
        raise MailDraftError("Entwurfsnachricht weicht vom geplanten Hash ab.")

    ledger.reserve(message)
    try:
        mailbox_reference = transport.append_draft(
            folder=message.drafts_folder,
            message_bytes=message.message_bytes,
        )
    except Exception as exc:
        with suppress(MailDraftError):
            ledger.finish(
                message.idempotency_key,
                status="failed",
                mailbox_reference="",
            )
        if isinstance(exc, MailDraftError):
            raise
        raise MailDraftError(f"Entwurfsablage ist fehlgeschlagen: {exc}") from exc
    ledger.finish(
        message.idempotency_key,
        status="drafted",
        mailbox_reference=mailbox_reference,
    )
    report_material = _canonical_json(
        {
            "draft_id": message.draft_id,
            "idempotency_key": message.idempotency_key,
            "message_sha256": message.message_sha256,
            "appended_at": appended_at,
        }
    )
    try:
        return MailDraftReport(
            report_id=f"mail_draft_report_{sha256(report_material).hexdigest()}",
            draft_id=message.draft_id,
            account_id=message.account_id,
            drafts_folder=message.drafts_folder,
            status="drafted",
            message_sha256=message.message_sha256,
            idempotency_key=message.idempotency_key,
            mailbox_reference=mailbox_reference,
            appended_at=appended_at,
        )
    except ValueError as exc:
        raise MailDraftError(f"Entwurfsbericht ist ungültig: {exc}") from exc


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MailDraftError(f"Entwurfskonto.{key} muss nichtleerer Text sein.")
    return value


def _integer(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise MailDraftError(f"Entwurfskonto.{key} muss eine Ganzzahl sein.")
    return value


def _boolean(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise MailDraftError(f"Entwurfskonto.{key} muss boolesch sein.")
    return value


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
