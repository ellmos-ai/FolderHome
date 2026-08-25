"""Contracts for placing a prepared letter into the owner's own drafts folder.

This surface never delivers mail. It appends one prepared message to one
configured IMAP mailbox that belongs to the FolderHome user, so the owner can
review and send it later inside their own mail program.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_ACCOUNT_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_PROFILE_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_EMAIL = re.compile(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_DRAFT_ID = re.compile(r"mail_draft_append_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"mail_draft_report_[0-9a-f]{64}")
_IDEMPOTENCY_KEY = re.compile(r"mail_draft_key_[0-9a-f]{64}")
_CORRESPONDENCE_PREVIEW_ID = re.compile(r"correspondence_preview_[0-9a-f]{64}")

MAIL_DRAFT_PROVIDER_ID = "folderhome.imap-draft"
MAIL_DRAFT_TRANSPORT = "imap_append"


def _require_timestamp(value: str, *, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} benötigt eine Zeitzone.")


def _require_folder(value: str, *, label: str) -> None:
    if not value.strip() or value != value.strip():
        raise ValueError(f"{label} darf nicht leer sein.")
    if any(char in value for char in "\r\n\"\\"):
        raise ValueError(f"{label} enthält unzulässige Zeichen.")
    if not value.isascii():
        raise ValueError(
            f"{label} muss der ASCII-IMAP-Name sein, zum Beispiel INBOX.Drafts; "
            "in der Oberfläche angezeigte Namen wie Entwürfe sind nicht der "
            "Protokollname."
        )


@dataclass(frozen=True, slots=True)
class MailDraftAccount:
    """One IMAP mailbox of the user that may receive drafts of their own letters.

    The password itself is never part of this contract. Only the local file that
    holds it is configured, and it is read exactly once during execution.
    """

    account_id: str
    profile_id: str
    display_name: str
    from_address: str
    host: str
    port: int
    use_ssl: bool
    username: str
    drafts_folder: str
    password_file: Path

    SCHEMA = "folderhome.mail-draft-account.v1"

    def __post_init__(self) -> None:
        if _ACCOUNT_ID.fullmatch(self.account_id) is None:
            raise ValueError("Mailkonto benötigt eine stabile Konto-ID.")
        if _PROFILE_ID.fullmatch(self.profile_id) is None:
            raise ValueError("Mailkonto benötigt eine gültige Profil-ID.")
        if not self.display_name.strip():
            raise ValueError("Mailkonto benötigt einen Anzeigenamen.")
        if _EMAIL.fullmatch(self.from_address) is None:
            raise ValueError("Mailkonto benötigt eine gültige eigene Adresse.")
        if not self.host.strip() or any(char in self.host for char in "\r\n \t"):
            raise ValueError("IMAP-Host ist ungültig.")
        if isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            raise ValueError("IMAP-Port ist ungültig.")
        if not isinstance(self.use_ssl, bool):
            raise ValueError("IMAP-Verschlüsselung muss boolesch sein.")
        if not self.use_ssl:
            raise ValueError("Entwurfsablage erlaubt ausschließlich IMAP über TLS.")
        if not self.username.strip() or any(char in self.username for char in "\r\n"):
            raise ValueError("IMAP-Benutzername ist ungültig.")
        _require_folder(self.drafts_folder, label="Entwurfsordner")
        if not self.password_file.is_absolute():
            raise ValueError("Passwort-Fundort benötigt einen absoluten Pfad.")
        object.__setattr__(self, "password_file", self.password_file.resolve())

    def to_public_dict(self) -> dict[str, object]:
        """Return model-safe metadata without host secrets or the password path."""

        return {
            "account_id": self.account_id,
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "drafts_folder": self.drafts_folder,
            "transport": MAIL_DRAFT_TRANSPORT,
            "transport_security": "implicit_tls",
            "provider_id": MAIL_DRAFT_PROVIDER_ID,
            "credentials_disclosed": False,
            "password_path_disclosed": False,
            "host_disclosed": False,
        }


@dataclass(frozen=True, slots=True)
class MailDraftMessage:
    """One rendered draft bound by hash to exactly one correspondence preview."""

    draft_id: str
    account_id: str
    profile_id: str
    correspondence_preview_id: str
    subject: str
    body_sha256: str
    message_bytes: bytes
    message_sha256: str
    idempotency_key: str
    drafts_folder: str
    planned_at: str
    attachment_count: int

    SCHEMA = "folderhome.mail-draft-message.v1"

    def __post_init__(self) -> None:
        if _DRAFT_ID.fullmatch(self.draft_id) is None:
            raise ValueError("Entwurfs-ID ist ungültig.")
        if _ACCOUNT_ID.fullmatch(self.account_id) is None:
            raise ValueError("Entwurf benötigt eine gültige Konto-ID.")
        if _PROFILE_ID.fullmatch(self.profile_id) is None:
            raise ValueError("Entwurf benötigt eine gültige Profil-ID.")
        if _CORRESPONDENCE_PREVIEW_ID.fullmatch(self.correspondence_preview_id) is None:
            raise ValueError("Entwurf benötigt eine gültige Korrespondenzvorschau.")
        if not self.subject.strip():
            raise ValueError("Entwurf benötigt einen Betreff.")
        if _SHA256.fullmatch(self.body_sha256) is None:
            raise ValueError("Entwurfstext-Hash ist ungültig.")
        if not self.message_bytes:
            raise ValueError("Entwurf benötigt eine gerenderte Nachricht.")
        if _SHA256.fullmatch(self.message_sha256) is None:
            raise ValueError("Entwurfsnachricht-Hash ist ungültig.")
        if _IDEMPOTENCY_KEY.fullmatch(self.idempotency_key) is None:
            raise ValueError("Entwurf benötigt eine gültige Idempotenzbindung.")
        _require_folder(self.drafts_folder, label="Entwurfsordner")
        _require_timestamp(self.planned_at, label="Entwurfszeitpunkt")
        if isinstance(self.attachment_count, bool) or self.attachment_count != 0:
            raise ValueError(
                "Entwurfsablage unterstützt in dieser Fassung keine Anhänge."
            )

    def to_public_dict(self) -> dict[str, object]:
        """Return the plan surface: no body text and no recipient address."""

        return {
            "draft_id": self.draft_id,
            "account_id": self.account_id,
            "profile_id": self.profile_id,
            "correspondence_preview_id": self.correspondence_preview_id,
            "subject": self.subject,
            "body_sha256": self.body_sha256,
            "message_sha256": self.message_sha256,
            "idempotency_key": self.idempotency_key,
            "drafts_folder": self.drafts_folder,
            "planned_at": self.planned_at,
            "attachment_count": self.attachment_count,
            "transport": MAIL_DRAFT_TRANSPORT,
            "delivery_attempted": False,
            "recipient_disclosed": False,
            "body_disclosed": False,
            "credentials_disclosed": False,
        }


@dataclass(frozen=True, slots=True)
class MailDraftReport:
    """Receipt for exactly one appended draft; never a delivery receipt."""

    report_id: str
    draft_id: str
    account_id: str
    drafts_folder: str
    status: str
    message_sha256: str
    idempotency_key: str
    mailbox_reference: str
    appended_at: str

    SCHEMA = "folderhome.mail-draft-report.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Entwurfsbericht-ID ist ungültig.")
        if _DRAFT_ID.fullmatch(self.draft_id) is None:
            raise ValueError("Entwurfsbericht benötigt eine gültige Entwurfs-ID.")
        if _ACCOUNT_ID.fullmatch(self.account_id) is None:
            raise ValueError("Entwurfsbericht benötigt eine gültige Konto-ID.")
        _require_folder(self.drafts_folder, label="Entwurfsordner")
        if self.status != "drafted":
            raise ValueError("Entwurfsbericht kennt ausschließlich den Status drafted.")
        if _SHA256.fullmatch(self.message_sha256) is None:
            raise ValueError("Entwurfsbericht-Hash ist ungültig.")
        if _IDEMPOTENCY_KEY.fullmatch(self.idempotency_key) is None:
            raise ValueError("Entwurfsbericht benötigt eine gültige Idempotenzbindung.")
        if any(char in self.mailbox_reference for char in "\r\n"):
            raise ValueError("Postfachreferenz ist ungültig.")
        _require_timestamp(self.appended_at, label="Ablagezeitpunkt")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "draft_id": self.draft_id,
            "account_id": self.account_id,
            "drafts_folder": self.drafts_folder,
            "status": self.status,
            "message_sha256": self.message_sha256,
            "idempotency_key": self.idempotency_key,
            "mailbox_reference": self.mailbox_reference,
            "appended_at": self.appended_at,
            "delivery_attempted": False,
            "email_sent": False,
            "recipient_disclosed": False,
            "credentials_disclosed": False,
        }
