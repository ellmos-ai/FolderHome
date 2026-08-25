"""Draft-only mailbox seam plus a local at-most-once draft ledger.

The seam appends one prepared message to the user's own drafts folder. It has
no send path at all, so no code in this capability can deliver mail to a third
party even if it is called incorrectly.

The connection lifecycle, the modified UTF-7 mailbox encoding and the two-way
credential lookup follow the patterns of the MIT-licensed ellmos
`mail-connector` module by the same author. Its code is not imported or pinned;
only the approach was reused, reimplemented here for the append-only case.
"""

from __future__ import annotations

import base64
import imaplib
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import Protocol

from folderhome.contracts.mail_draft import (
    MAIL_DRAFT_PROVIDER_ID,
    MailDraftAccount,
    MailDraftMessage,
)

_APPEND_TIMEOUT_SECONDS = 30
_MAX_PASSWORD_BYTES = 4096


class MailDraftError(RuntimeError):
    """Raised when a drafts mailbox, its credential, or its ledger is unsafe."""


class MailDraftTransport(Protocol):
    """Minimal append-only seam; real IMAP transports stay replaceable."""

    transport_id: str
    network_required: bool

    def append_draft(self, *, folder: str, message_bytes: bytes) -> str: ...


class SyntheticDraftTransport:
    """No-network fixture transport for deterministic acceptance runs."""

    transport_id = "folderhome.synthetic-draft"
    network_required = False

    def __init__(self) -> None:
        self.appended: list[tuple[str, bytes]] = []

    def append_draft(self, *, folder: str, message_bytes: bytes) -> str:
        self.appended.append((folder, message_bytes))
        return f"synthetic-draft-{len(self.appended)}"


def encode_modified_utf7(value: str) -> str:
    """Encode a mailbox name for the wire, as RFC 3501 requires.

    A German drafts folder is called `Entwürfe` on screen but travels as
    `Entw&APw-rfe`. Without this an append into a non-ASCII folder fails on
    every mailbox that has one.
    """

    output: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        if not pending:
            return
        raw = "".join(pending).encode("utf-16-be")
        encoded = base64.b64encode(raw).decode("ascii").rstrip("=").replace("/", ",")
        output.append(f"&{encoded}-")
        pending.clear()

    for char in value:
        if 0x20 <= ord(char) <= 0x7E:
            flush()
            output.append("&-" if char == "&" else char)
        else:
            pending.append(char)
    flush()
    return "".join(output)


def decode_modified_utf7(value: str) -> str:
    """Decode a wire mailbox name back into what the user reads."""

    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] != "&":
            output.append(value[index])
            index += 1
            continue
        end = value.find("-", index)
        if end == -1:
            output.append(value[index:])
            break
        encoded = value[index + 1 : end]
        if not encoded:
            output.append("&")
        else:
            standard = encoded.replace(",", "/")
            standard += "=" * (-len(standard) % 4)
            try:
                output.append(base64.b64decode(standard).decode("utf-16-be"))
            except (ValueError, UnicodeDecodeError):
                output.append(value[index : end + 1])
        index = end + 1
    return "".join(output)


class ImapDraftTransport:
    """Append one message to one IMAP drafts folder over implicit TLS."""

    transport_id = MAIL_DRAFT_PROVIDER_ID
    network_required = True

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout_seconds: int = _APPEND_TIMEOUT_SECONDS,
        connection_factory: object | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout_seconds = timeout_seconds
        self._connection_factory = connection_factory
        self._connection: object | None = None

    def __enter__(self) -> ImapDraftTransport:
        self._connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._close()

    def _connect(self) -> None:
        try:
            if self._connection_factory is not None:
                self._connection = self._connection_factory()
            else:
                self._connection = imaplib.IMAP4_SSL(
                    self._host,
                    self._port,
                    timeout=self._timeout_seconds,
                )
            self._connection.login(self._username, self._password)
        except (imaplib.IMAP4.error, OSError) as exc:
            self._close()
            raise MailDraftError(
                f"Postfachverbindung ist fehlgeschlagen: {_redact(exc)}"
            ) from None

    def _close(self) -> None:
        if self._connection is not None:
            with suppress(imaplib.IMAP4.error, OSError, AttributeError):
                self._connection.logout()
            self._connection = None

    def available_folders(self) -> tuple[str, ...]:
        """List mailbox names as the user reads them, not as the wire spells them."""

        if self._connection is None:
            raise MailDraftError("Postfachverbindung ist nicht offen.")
        try:
            status, data = self._connection.list()
        except (imaplib.IMAP4.error, OSError) as exc:
            raise MailDraftError(
                f"Postfachordner sind nicht lesbar: {_redact(exc)}"
            ) from None
        if status != "OK" or not data:
            raise MailDraftError("Postfach lieferte keine Ordnerliste.")
        folders: list[str] = []
        for item in data:
            if not item:
                continue
            text = (
                item.decode("utf-8", errors="replace")
                if isinstance(item, bytes)
                else str(item)
            )
            stripped = text.strip()
            if stripped.endswith('"'):
                opening = stripped.rfind('"', 0, len(stripped) - 1)
                name = stripped[opening + 1 : -1]
            else:
                name = stripped.rsplit(" ", 1)[-1].strip('"')
            if name:
                folders.append(decode_modified_utf7(name))
        return tuple(folders)

    def append_draft(self, *, folder: str, message_bytes: bytes) -> str:
        with self:
            known = self.available_folders()
            if folder not in known:
                raise MailDraftError(
                    f"Das Postfach kennt keinen Ordner {folder!r}. Vorhanden sind: "
                    + ", ".join(sorted(known))
                )
            try:
                status, response = self._connection.append(  # type: ignore[union-attr]
                    encode_modified_utf7(folder),
                    r"(\Draft)",
                    None,
                    message_bytes,
                )
            except (imaplib.IMAP4.error, OSError) as exc:
                raise MailDraftError(
                    f"Entwurf konnte nicht im Postfach abgelegt werden: {_redact(exc)}"
                ) from None
        if status != "OK":
            raise MailDraftError(
                "Postfach hat die Entwurfsablage abgelehnt: "
                f"{_decode_response(response)}"
            )
        return _decode_response(response)


def read_mailbox_password(account: MailDraftAccount) -> str:
    """Resolve the password from the configured source, exactly once.

    Two sources are supported, in this order: the operating system keyring, and
    a local file. Neither the value nor its location ever leaves this function.
    """

    if account.keyring_service is not None and account.keyring_user is not None:
        password = _keyring_password(
            service=account.keyring_service,
            user=account.keyring_user,
        )
        if password:
            return password
        if account.password_file is None:
            raise MailDraftError(
                "Der Schlüsselbund enthält für dieses Konto kein Passwort."
            )
    if account.password_file is None:
        raise MailDraftError("Mailkonto besitzt keinen nutzbaren Passwort-Fundort.")
    return _password_from_file(account.password_file)


def _keyring_password(*, service: str, user: str) -> str | None:
    try:
        import keyring
    except ImportError:
        raise MailDraftError(
            "Das Konto verweist auf den Schlüsselbund, aber das Paket keyring "
            "ist nicht installiert."
        ) from None
    try:
        value = keyring.get_password(service, user)
    except Exception as exc:  # noqa: BLE001 - backend errors must stay opaque
        raise MailDraftError(
            f"Schlüsselbund ist nicht lesbar: {_redact(exc)}"
        ) from None
    if value is None or not value.strip():
        return None
    return value


def _password_from_file(path: Path) -> str:
    try:
        if path.is_symlink() or not path.is_file():
            raise MailDraftError(
                "Passwort-Fundort fehlt oder ist kein reguläres File."
            )
        raw = path.read_bytes()
    except OSError:
        raise MailDraftError("Passwort-Fundort ist nicht lesbar.") from None
    if not raw or len(raw) > _MAX_PASSWORD_BYTES:
        raise MailDraftError("Passwort-Fundort ist leer oder unplausibel groß.")
    try:
        password = raw.decode("utf-8").strip("\r\n")
    except UnicodeError:
        raise MailDraftError("Passwort-Fundort ist nicht UTF-8-kodiert.") from None
    if not password.strip():
        raise MailDraftError("Passwort-Fundort enthält kein Passwort.")
    return password


class MailDraftLedger:
    """Fail-closed local reservation ledger for at-most-once draft appends."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir.resolve()
        if state_dir.is_symlink():
            raise MailDraftError("Entwurfs-Ledger darf keinen symbolischen Link nutzen.")
        self.path = self.state_dir / "mail" / "mail-drafts.sqlite3"

    def reserve(self, message: MailDraftMessage) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise MailDraftError("Entwurfs-Ledger darf keinen symbolischen Link nutzen.")
        connection = sqlite3.connect(self.path)
        try:
            _initialize(connection)
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                "SELECT status FROM drafts WHERE idempotency_key = ? LIMIT 1",
                (message.idempotency_key,),
            ).fetchone()
            if replay is not None:
                raise MailDraftError(
                    "Dieser Entwurf wurde in diesem Postfach bereits abgelegt."
                )
            connection.execute(
                "INSERT INTO drafts "
                "(idempotency_key, draft_id, account_id, drafts_folder, "
                "message_sha256, status, mailbox_reference, planned_at) "
                "VALUES (?, ?, ?, ?, ?, 'reserved', NULL, ?)",
                (
                    message.idempotency_key,
                    message.draft_id,
                    message.account_id,
                    message.drafts_folder,
                    message.message_sha256,
                    message.planned_at,
                ),
            )
            connection.commit()
        except MailDraftError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise MailDraftError(
                f"Entwurfs-Ledger konnte nicht reservieren: {exc}"
            ) from exc
        finally:
            connection.close()

    def finish(
        self,
        idempotency_key: str,
        *,
        status: str,
        mailbox_reference: str,
    ) -> None:
        if status not in {"drafted", "failed"}:
            raise MailDraftError("Entwurfs-Ledger erhielt einen ungültigen Status.")
        connection = sqlite3.connect(self.path)
        try:
            _initialize(connection)
            cursor = connection.execute(
                "UPDATE drafts SET status = ?, mailbox_reference = ? "
                "WHERE idempotency_key = ? AND status = 'reserved'",
                (status, mailbox_reference, idempotency_key),
            )
            if cursor.rowcount != 1:
                raise MailDraftError(
                    "Entwurfs-Ledger-Reservierung ist nicht mehr eindeutig."
                )
            connection.commit()
        except MailDraftError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise MailDraftError(
                f"Entwurfs-Ledger konnte nicht abschließen: {exc}"
            ) from exc
        finally:
            connection.close()

    def status(self, idempotency_key: str) -> str | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT status FROM drafts WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return None if row is None else str(row[0])
        except sqlite3.Error as exc:
            raise MailDraftError(f"Entwurfs-Ledger ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()


def _initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS drafts ("
        "idempotency_key TEXT PRIMARY KEY, "
        "draft_id TEXT NOT NULL, "
        "account_id TEXT NOT NULL, "
        "drafts_folder TEXT NOT NULL, "
        "message_sha256 TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "mailbox_reference TEXT, "
        "planned_at TEXT NOT NULL"
        ")"
    )


def _decode_response(response: object) -> str:
    if isinstance(response, list):
        parts = [
            item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
            for item in response
            if item is not None
        ]
        return " ".join(parts).strip()
    if isinstance(response, bytes):
        return response.decode("utf-8", errors="replace")
    return str(response)


def _redact(exc: BaseException) -> str:
    """Return a transport error text without the configured credential."""

    return type(exc).__name__
