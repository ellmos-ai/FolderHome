"""Reusable mail gateway seam and local idempotency ledger."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from folderhome.contracts.mail import (
    MailDraftPreview,
    MailIngestPlan,
    MailMessageReference,
    MailSendApproval,
)


class MailGatewayError(RuntimeError):
    """Raised when a mail transport or its local audit ledger is unsafe."""


class MailGateway(Protocol):
    """Minimal provider-neutral seam; real transports live outside the core."""

    provider_id: str
    provider_revision: str | None
    network_required: bool
    read_only_ingest: bool

    def fetch(self, plan: MailIngestPlan) -> tuple[MailMessageReference, ...]: ...

    def send(self, draft: MailDraftPreview, approval: MailSendApproval) -> str: ...


class SyntheticMailGateway:
    """No-network fixture gateway for deterministic end-to-end acceptance."""

    provider_id = "folderhome.synthetic-mail"
    provider_revision = None
    read_only_ingest = True

    def __init__(
        self,
        *,
        messages: tuple[MailMessageReference, ...],
    ) -> None:
        self.messages = messages
        self.network_required = False
        self.fetch_count = 0
        self.send_count = 0

    def fetch(self, plan: MailIngestPlan) -> tuple[MailMessageReference, ...]:
        self.fetch_count += 1
        matches = tuple(
            message
            for message in self.messages
            if message.account_id == plan.account_id
            and message.folder == plan.folder.name
        )
        return matches[: plan.request.max_messages]

    def send(self, draft: MailDraftPreview, approval: MailSendApproval) -> str:
        self.send_count += 1
        return f"synthetic-mail-{draft.draft_sha256[:24]}"


class MailActionLedger:
    """Fail-closed local reservation ledger for at-most-once delivery attempts."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir.resolve()
        if self.state_dir.is_symlink():
            raise MailGatewayError("Mail-Ledger darf keinen symbolischen Link nutzen.")
        self.path = self.state_dir / "mail" / "mail-actions.sqlite3"

    def reserve(
        self,
        *,
        approval: MailSendApproval,
        draft: MailDraftPreview,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise MailGatewayError("Mail-Ledger darf keinen symbolischen Link nutzen.")
        connection = sqlite3.connect(self.path)
        try:
            _initialize(connection)
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                "SELECT status FROM deliveries WHERE idempotency_key = ? "
                "OR approval_id = ? LIMIT 1",
                (approval.idempotency_key, approval.approval_id),
            ).fetchone()
            if replay is not None:
                raise MailGatewayError(
                    "Mailversand-Freigabe oder Idempotenzschlüssel wurde bereits verwendet."
                )
            connection.execute(
                "INSERT INTO deliveries "
                "(idempotency_key, approval_id, draft_id, draft_sha256, recipient_email, "
                "status, transport_message_id, approved_at) "
                "VALUES (?, ?, ?, ?, ?, 'reserved', NULL, ?)",
                (
                    approval.idempotency_key,
                    approval.approval_id,
                    draft.draft_id,
                    draft.draft_sha256,
                    draft.to_address,
                    approval.approved_at,
                ),
            )
            connection.commit()
        except MailGatewayError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise MailGatewayError(f"Mail-Ledger konnte nicht reservieren: {exc}") from exc
        finally:
            connection.close()

    def finish(
        self,
        idempotency_key: str,
        *,
        status: str,
        transport_message_id: str,
    ) -> None:
        if status not in {"simulated", "sent", "failed"}:
            raise MailGatewayError("Mail-Ledger erhielt einen ungültigen Abschlussstatus.")
        connection = sqlite3.connect(self.path)
        try:
            _initialize(connection)
            cursor = connection.execute(
                "UPDATE deliveries SET status = ?, transport_message_id = ? "
                "WHERE idempotency_key = ? AND status = 'reserved'",
                (status, transport_message_id, idempotency_key),
            )
            if cursor.rowcount != 1:
                raise MailGatewayError("Mail-Ledger-Reservierung ist nicht mehr eindeutig.")
            connection.commit()
        except MailGatewayError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise MailGatewayError(f"Mail-Ledger konnte nicht abschließen: {exc}") from exc
        finally:
            connection.close()

    def status(self, idempotency_key: str) -> str | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT status FROM deliveries WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return None if row is None else str(row[0])
        except sqlite3.Error as exc:
            raise MailGatewayError(f"Mail-Ledger ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()


def _initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS deliveries ("
        "idempotency_key TEXT PRIMARY KEY, "
        "approval_id TEXT UNIQUE NOT NULL, "
        "draft_id TEXT NOT NULL, "
        "draft_sha256 TEXT NOT NULL, "
        "recipient_email TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "transport_message_id TEXT, "
        "approved_at TEXT NOT NULL"
        ")"
    )
