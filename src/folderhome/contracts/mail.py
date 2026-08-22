"""Provider-neutral contracts for guarded mail ingest, drafts, and delivery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_PROVIDER_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,79}")
_EMAIL = re.compile(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_REVISION = re.compile(r"[0-9a-f]{40}")
_MESSAGE_REF = re.compile(r"mail_message_[0-9a-f]{64}")
_ATTACHMENT_ID = re.compile(r"mail_attachment_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"mail_ingest_plan_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"mail_(?:ingest|send)_report_[0-9a-f]{64}")
_DRAFT_ID = re.compile(r"mail_draft_[0-9a-f]{64}")
_IDEMPOTENCY_KEY = re.compile(r"mail_send_[0-9a-f]{64}")
_CONTACT_ID = re.compile(r"contact_[0-9a-f]{64}")
_CORRESPONDENCE_PREVIEW_ID = re.compile(r"correspondence_preview_[0-9a-f]{64}")
_CREDENTIAL_REF = re.compile(r"(?:keyring|env|synthetic)://[^\s]{3,240}")


def _require_email(value: str, *, label: str) -> None:
    if value != value.strip() or _EMAIL.fullmatch(value) is None:
        raise ValueError(f"{label} ist keine gültige E-Mail-Adresse.")


def _require_timestamp(value: str, *, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} benötigt eine Zeitzone.")


@dataclass(frozen=True, slots=True)
class MailInboundConfiguration:
    protocol: str
    host: str
    port: int
    folder: str
    credential_ref: str
    provider_id: str
    provider_revision: str | None

    def __post_init__(self) -> None:
        if self.protocol != "imap":
            raise ValueError("Eingangskonto unterstützt ausschließlich IMAP.")
        if not self.host.strip() or not 1 <= self.port <= 65535:
            raise ValueError("IMAP-Host oder -Port ist ungültig.")
        if not self.folder.strip() or any(char in self.folder for char in "\r\n"):
            raise ValueError("IMAP-Ordner ist ungültig.")
        if _CREDENTIAL_REF.fullmatch(self.credential_ref) is None:
            raise ValueError("IMAP-Zugang benötigt eine Secret-Referenz.")
        if _PROVIDER_ID.fullmatch(self.provider_id) is None:
            raise ValueError("IMAP-Provider-ID ist ungültig.")
        if self.provider_revision is not None and _GIT_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("IMAP-Providerrevision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "folder": self.folder,
            "credential_ref": self.credential_ref,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
        }


@dataclass(frozen=True, slots=True)
class MailOutboundConfiguration:
    protocol: str
    host: str
    port: int
    credential_ref: str
    provider_id: str
    provider_revision: str | None

    def __post_init__(self) -> None:
        if self.protocol != "smtp":
            raise ValueError("Ausgangskonto unterstützt ausschließlich SMTP.")
        if not self.host.strip() or not 1 <= self.port <= 65535:
            raise ValueError("SMTP-Host oder -Port ist ungültig.")
        if _CREDENTIAL_REF.fullmatch(self.credential_ref) is None:
            raise ValueError("SMTP-Zugang benötigt eine Secret-Referenz.")
        if _PROVIDER_ID.fullmatch(self.provider_id) is None:
            raise ValueError("SMTP-Provider-ID ist ungültig.")
        if self.provider_revision is not None and _GIT_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("SMTP-Providerrevision ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "credential_ref": self.credential_ref,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
        }


@dataclass(frozen=True, slots=True)
class MailAccountConfiguration:
    account_id: str
    profile_id: str
    display_name: str
    address: str
    inbound: MailInboundConfiguration
    outbound: MailOutboundConfiguration | None

    SCHEMA = "folderhome.mail-account.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.account_id) is None:
            raise ValueError("Mailkonto-ID ist ungültig.")
        if not self.profile_id.strip() or not self.display_name.strip():
            raise ValueError("Mailkonto benötigt Profil und Bezeichnung.")
        _require_email(self.address, label="Konto-Adresse")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "account_id": self.account_id,
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "address": self.address,
            "inbound": self.inbound.to_dict(),
            "outbound": self.outbound.to_dict() if self.outbound else None,
        }


@dataclass(frozen=True, slots=True)
class MailFolderReference:
    account_id: str
    name: str
    read_only: bool = True

    SCHEMA = "folderhome.mail-folder-ref.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.account_id) is None or not self.name.strip():
            raise ValueError("Mailordner-Referenz ist ungültig.")
        if not self.read_only:
            raise ValueError("Ingest-Ordner müssen schreibgeschützt sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "account_id": self.account_id,
            "name": self.name,
            "read_only": True,
        }


@dataclass(frozen=True, slots=True)
class MailAttachmentReference:
    attachment_id: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    provider_ref: str

    SCHEMA = "folderhome.mail-attachment-ref.v1"

    def __post_init__(self) -> None:
        if _ATTACHMENT_ID.fullmatch(self.attachment_id) is None:
            raise ValueError("Mailanhang-ID ist ungültig.")
        if (
            not self.filename.strip()
            or self.filename != self.filename.split("/")[-1].split("\\")[-1]
            or any(char in self.filename for char in "\r\n")
        ):
            raise ValueError("Mailanhang benötigt einen sicheren Dateinamen.")
        if not self.media_type.strip() or self.size_bytes < 0:
            raise ValueError("Mailanhang benötigt Typ und nichtnegative Größe.")
        if _SHA256.fullmatch(self.sha256) is None or not self.provider_ref.strip():
            raise ValueError("Mailanhang benötigt Hash und Providerreferenz.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "attachment_id": self.attachment_id,
            "filename": self.filename,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "provider_ref": self.provider_ref,
        }


@dataclass(frozen=True, slots=True)
class MailMessageReference:
    message_ref: str
    account_id: str
    folder: str
    provider_uid: str
    rfc_message_id: str | None
    sender: str
    recipients: tuple[str, ...]
    subject: str
    received_at: str
    attachments: tuple[MailAttachmentReference, ...]

    SCHEMA = "folderhome.mail-message-ref.v1"

    def __post_init__(self) -> None:
        if _MESSAGE_REF.fullmatch(self.message_ref) is None:
            raise ValueError("Mailnachrichten-Referenz ist ungültig.")
        if _ID.fullmatch(self.account_id) is None:
            raise ValueError("Mailnachricht besitzt eine ungültige Konto-ID.")
        for value in (self.folder, self.provider_uid, self.subject):
            if not value.strip() or any(char in value for char in "\r\n"):
                raise ValueError("Mailnachricht besitzt ungültige Metadaten.")
        _require_email(self.sender, label="Mail-Absender")
        if not self.recipients:
            raise ValueError("Mailnachricht benötigt mindestens einen Empfänger.")
        for recipient in self.recipients:
            _require_email(recipient, label="Mail-Empfänger")
        _require_timestamp(self.received_at, label="Empfangszeit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "message_ref": self.message_ref,
            "account_id": self.account_id,
            "folder": self.folder,
            "provider_uid": self.provider_uid,
            "rfc_message_id": self.rfc_message_id,
            "sender": self.sender,
            "recipients": list(self.recipients),
            "subject": self.subject,
            "received_at": self.received_at,
            "attachments": [item.to_dict() for item in self.attachments],
        }


@dataclass(frozen=True, slots=True)
class MailIngestRequest:
    request_id: str
    profile_id: str
    account_id: str
    folder: str
    query: str
    max_messages: int
    include_attachments: bool
    target_ref: str | None

    SCHEMA = "folderhome.mail-ingest-request.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.request_id) is None or _ID.fullmatch(self.account_id) is None:
            raise ValueError("Mail-Ingest benötigt gültige Anfrage- und Konto-IDs.")
        if not self.profile_id.strip() or not self.folder.strip() or not self.query.strip():
            raise ValueError("Mail-Ingest benötigt Profil, Ordner und Suchanfrage.")
        if not 1 <= self.max_messages <= 500:
            raise ValueError("Mail-Ingest erlaubt 1 bis 500 Nachrichten.")
        if self.include_attachments != (self.target_ref is not None):
            raise ValueError("Anhangs-Ingest benötigt genau eine Zielreferenz.")
        if self.target_ref is not None and not self.target_ref.startswith("folder://"):
            raise ValueError("Anhangsziel muss eine folder://-Referenz sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "account_id": self.account_id,
            "folder": self.folder,
            "query": self.query,
            "max_messages": self.max_messages,
            "include_attachments": self.include_attachments,
            "target_ref": self.target_ref,
        }


@dataclass(frozen=True, slots=True)
class MailIngestPlan:
    plan_id: str
    plan_sha256: str
    request: MailIngestRequest
    account_id: str
    folder: MailFolderReference
    provider_id: str
    provider_revision: str | None
    status: str
    reason: str
    operations: tuple[str, ...]
    mailbox_mutations: tuple[str, ...] = ()
    provider_invoked: bool = False

    SCHEMA = "folderhome.mail-ingest-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None or _SHA256.fullmatch(
            self.plan_sha256
        ) is None:
            raise ValueError("Mail-Ingest-Plan besitzt ungültige Identität.")
        if self.status not in {"ready", "blocked"} or not self.reason:
            raise ValueError("Mail-Ingest-Plan besitzt ungültigen Status.")
        if _PROVIDER_ID.fullmatch(self.provider_id) is None:
            raise ValueError("Mail-Ingest-Plan besitzt eine ungültige Provider-ID.")
        allowed = {"fetch_headers", "fetch_attachments"}
        if not self.operations or any(item not in allowed for item in self.operations):
            raise ValueError("Mail-Ingest-Plan enthält eine unerlaubte Operation.")
        if self.mailbox_mutations or self.provider_invoked:
            raise ValueError("Mail-Ingest-Plan muss read-only und nebenwirkungsfrei sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "request": self.request.to_dict(),
            "account_id": self.account_id,
            "folder": self.folder.to_dict(),
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "status": self.status,
            "reason": self.reason,
            "operations": list(self.operations),
            "mailbox_mutations": [],
            "provider_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class MailIngestApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    approved_at: str
    allow_network_read: bool
    allow_attachment_write: bool

    SCHEMA = "folderhome.mail-ingest-approval.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.approval_id) is None or _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Mail-Ingest-Freigabe besitzt ungültige IDs.")
        if _SHA256.fullmatch(self.plan_sha256) is None:
            raise ValueError("Mail-Ingest-Freigabe benötigt einen gültigen Planhash.")
        _require_timestamp(self.approved_at, label="Freigabezeit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "approved_at": self.approved_at,
            "allow_network_read": self.allow_network_read,
            "allow_attachment_write": self.allow_attachment_write,
        }


@dataclass(frozen=True, slots=True)
class MailIngestReport:
    report_id: str
    plan_id: str
    approval_id: str
    status: str
    messages: tuple[MailMessageReference, ...]
    network_invoked: bool
    attachment_write_invoked: bool
    mailbox_mutations: tuple[str, ...] = ()

    SCHEMA = "folderhome.mail-ingest-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None or self.status != "executed":
            raise ValueError("Mail-Ingest-Report ist ungültig.")
        if self.mailbox_mutations:
            raise ValueError("Read-only Mail-Ingest darf das Postfach nicht ändern.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "status": self.status,
            "messages": [item.to_dict() for item in self.messages],
            "network_invoked": self.network_invoked,
            "attachment_write_invoked": self.attachment_write_invoked,
            "mailbox_mutations": [],
        }


@dataclass(frozen=True, slots=True)
class MailDraftRequest:
    request_id: str
    profile_id: str
    account_id: str
    recipient_contact_id: str
    recipient_email: str
    correspondence_preview_id: str
    correspondence_text_sha256: str
    attachments: tuple[MailAttachmentReference, ...]

    SCHEMA = "folderhome.mail-draft-request.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.request_id) is None or _ID.fullmatch(self.account_id) is None:
            raise ValueError("Mailentwurf benötigt gültige Anfrage- und Konto-IDs.")
        if not self.profile_id.strip() or _CONTACT_ID.fullmatch(
            self.recipient_contact_id
        ) is None:
            raise ValueError("Mailentwurf benötigt Profil und Kontakt-ID.")
        _require_email(self.recipient_email, label="Expliziter Empfänger")
        if _CORRESPONDENCE_PREVIEW_ID.fullmatch(
            self.correspondence_preview_id
        ) is None or _SHA256.fullmatch(self.correspondence_text_sha256) is None:
            raise ValueError("Mailentwurf benötigt eine exakte Korrespondenzreferenz.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "account_id": self.account_id,
            "recipient_contact_id": self.recipient_contact_id,
            "recipient_email": self.recipient_email,
            "correspondence_preview_id": self.correspondence_preview_id,
            "correspondence_text_sha256": self.correspondence_text_sha256,
            "attachments": [item.to_dict() for item in self.attachments],
        }


@dataclass(frozen=True, slots=True)
class MailDraftPreview:
    draft_id: str
    draft_sha256: str
    request_id: str
    profile_id: str
    account_id: str
    provider_id: str
    provider_revision: str | None
    from_address: str
    to_address: str
    contact_id: str
    correspondence_preview_id: str
    subject: str
    body_text: str
    body_sha256: str
    attachments: tuple[MailAttachmentReference, ...]

    SCHEMA = "folderhome.mail-draft-preview.v1"

    def __post_init__(self) -> None:
        if _DRAFT_ID.fullmatch(self.draft_id) is None or _SHA256.fullmatch(
            self.draft_sha256
        ) is None:
            raise ValueError("Mailentwurf-Vorschau besitzt ungültige Identität.")
        _require_email(self.from_address, label="Entwurfsabsender")
        _require_email(self.to_address, label="Entwurfsempfänger")
        if _PROVIDER_ID.fullmatch(self.provider_id) is None:
            raise ValueError("Mailentwurf-Vorschau besitzt eine ungültige Provider-ID.")
        if self.provider_revision is not None and _GIT_REVISION.fullmatch(
            self.provider_revision
        ) is None:
            raise ValueError("Mailentwurf-Vorschau besitzt eine ungültige Providerrevision.")
        if _SHA256.fullmatch(self.body_sha256) is None or not self.subject.strip():
            raise ValueError("Mailentwurf-Vorschau benötigt Betreff und Texthash.")

    @property
    def read_only(self) -> bool:
        return True

    @property
    def transport_invoked(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "draft_id": self.draft_id,
            "draft_sha256": self.draft_sha256,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "account_id": self.account_id,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "contact_id": self.contact_id,
            "correspondence_preview_id": self.correspondence_preview_id,
            "subject": self.subject,
            "body_text": self.body_text,
            "body_sha256": self.body_sha256,
            "attachments": [item.to_dict() for item in self.attachments],
            "read_only": True,
            "contains_sensitive_data": True,
            "transport_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class MailSendApproval:
    approval_id: str
    draft_id: str
    draft_sha256: str
    recipient_email: str
    approved_at: str
    idempotency_key: str
    allow_network_send: bool

    SCHEMA = "folderhome.mail-send-approval.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.approval_id) is None or _DRAFT_ID.fullmatch(
            self.draft_id
        ) is None:
            raise ValueError("Mailversand-Freigabe besitzt ungültige IDs.")
        if _SHA256.fullmatch(self.draft_sha256) is None or _IDEMPOTENCY_KEY.fullmatch(
            self.idempotency_key
        ) is None:
            raise ValueError("Mailversand-Freigabe besitzt ungültige Hashbindung.")
        _require_email(self.recipient_email, label="Freigegebener Empfänger")
        _require_timestamp(self.approved_at, label="Freigabezeit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "approval_id": self.approval_id,
            "draft_id": self.draft_id,
            "draft_sha256": self.draft_sha256,
            "recipient_email": self.recipient_email,
            "approved_at": self.approved_at,
            "idempotency_key": self.idempotency_key,
            "allow_network_send": self.allow_network_send,
        }


@dataclass(frozen=True, slots=True)
class MailSendReport:
    report_id: str
    draft_id: str
    approval_id: str
    idempotency_key: str
    status: str
    provider_id: str
    provider_revision: str | None
    recipient_email: str
    transport_message_id: str
    network_invoked: bool
    email_sent: bool

    SCHEMA = "folderhome.mail-send-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Mailversand-Report besitzt eine ungültige ID.")
        if self.status not in {"simulated", "sent"}:
            raise ValueError("Mailversand-Report besitzt einen ungültigen Status.")
        if self.email_sent != (self.status == "sent"):
            raise ValueError("Mailversand-Status und Side-Effect widersprechen sich.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "draft_id": self.draft_id,
            "approval_id": self.approval_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "recipient_email": self.recipient_email,
            "transport_message_id": self.transport_message_id,
            "network_invoked": self.network_invoked,
            "email_sent": self.email_sent,
        }
