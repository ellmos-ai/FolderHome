"""Reusable local SQLite contact register with append-only change events."""

from __future__ import annotations

import json
import os
import sqlite3
from hashlib import sha256
from pathlib import Path

from folderhome.contracts import (
    ContactActionKind,
    ContactRecord,
    ContactRegisterAction,
    ContactRegisterApproval,
)

_SCHEMA_VERSION = "folderhome.contact-register.v1"


class ContactRegisterError(RuntimeError):
    """Raised when local contact state is missing, stale, or inconsistent."""


class ContactRegisterStore:
    """Read, query, and transactionally update the local contact register."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = _safe_state_root(state_dir)
        self.path = self.state_dir / "contacts" / "contacts.sqlite3"

    def revision(self) -> str:
        return _revision(self.list_contacts(include_deletion_candidates=True))

    def list_contacts(
        self,
        *,
        profile_id: str | None = None,
        area: str | None = None,
        object_query: str | None = None,
        include_deletion_candidates: bool = False,
    ) -> tuple[ContactRecord, ...]:
        if not self.path.exists():
            return ()
        connection = self._read_connection()
        try:
            _validate_schema(connection)
            clauses = []
            parameters: list[str] = []
            if not include_deletion_candidates:
                clauses.append("status = 'active'")
            if profile_id is not None:
                clauses.append("profile_id = ?")
                parameters.append(profile_id)
            if area is not None:
                clauses.append("area = ?")
                parameters.append(area)
            if object_query is not None:
                clauses.append("LOWER(COALESCE(object_ref, '')) LIKE ?")
                parameters.append(f"%{object_query.casefold()}%")
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = connection.execute(
                "SELECT * FROM contacts"
                f"{where} ORDER BY profile_id, area, purpose, object_ref, contact_id",
                parameters,
            ).fetchall()
            return tuple(_record(row) for row in rows)
        except sqlite3.Error as exc:
            raise ContactRegisterError(f"Kontaktregister ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()

    def count_events(self) -> int:
        if not self.path.exists():
            return 0
        connection = self._read_connection()
        try:
            _validate_schema(connection)
            return int(connection.execute("SELECT COUNT(*) FROM contact_events").fetchone()[0])
        except sqlite3.Error as exc:
            raise ContactRegisterError(f"Kontaktregister ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()

    def apply(
        self,
        *,
        expected_revision: str,
        actions: tuple[ContactRegisterAction, ...],
        approval: ContactRegisterApproval,
    ) -> tuple[tuple[str, ...], tuple[str, ...], str]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise ContactRegisterError("Kontaktregister darf kein symbolischer Link sein.")
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        created: list[str] = []
        marked: list[str] = []
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            _initialize_schema(connection)
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
            current_records = tuple(
                _record(row)
                for row in connection.execute(
                    "SELECT * FROM contacts ORDER BY contact_id"
                ).fetchall()
            )
            if _revision(current_records) != expected_revision:
                raise ContactRegisterError(
                    "Kontaktregister wurde seit der Planung verändert."
                )
            replay = connection.execute(
                "SELECT 1 FROM contact_events WHERE approval_id = ? LIMIT 1",
                (approval.approval_id,),
            ).fetchone()
            if replay is not None:
                raise ContactRegisterError("Kontaktfreigabe wurde bereits verwendet.")
            for action in actions:
                contact_id = _contact_id(action.candidate.candidate_id)
                if action.kind is ContactActionKind.REPLACE:
                    assert action.prior_contact_id is not None
                    cursor = connection.execute(
                        "UPDATE contacts SET status = 'deletion_candidate', updated_at = ? "
                        "WHERE contact_id = ? AND status = 'active'",
                        (approval.approved_at, action.prior_contact_id),
                    )
                    if cursor.rowcount != 1:
                        raise ContactRegisterError(
                            "Vorheriger Kontakt ist nicht mehr eindeutig aktiv."
                        )
                    marked.append(action.prior_contact_id)
                _insert_contact(
                    connection,
                    contact_id,
                    action,
                    approval.approved_at,
                )
                created.append(contact_id)
                event_material = (
                    f"{approval.approval_id}\0{action.action_id}\0{contact_id}"
                )
                event_id = f"contact_event_{sha256(event_material.encode('utf-8')).hexdigest()}"
                connection.execute(
                    "INSERT INTO contact_events "
                    "(event_id, approval_id, plan_id, action_id, kind, contact_id, "
                    "prior_contact_id, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        approval.approval_id,
                        approval.plan_id,
                        action.action_id,
                        action.kind.value,
                        contact_id,
                        action.prior_contact_id,
                        approval.approved_at,
                    ),
                )
            after_records = tuple(
                _record(row)
                for row in connection.execute(
                    "SELECT * FROM contacts ORDER BY contact_id"
                ).fetchall()
            )
            revision_after = _revision(after_records)
            connection.commit()
            return tuple(created), tuple(marked), revision_after
        except ContactRegisterError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise ContactRegisterError(
                f"Kontaktregister konnte nicht aktualisiert werden: {exc}"
            ) from exc
        finally:
            connection.close()

    def _read_connection(self) -> sqlite3.Connection:
        if self.path.is_symlink() or not self.path.is_file():
            raise ContactRegisterError(
                f"Kontaktregister fehlt oder ist kein reguläres File: {self.path}"
            )
        try:
            connection = sqlite3.connect(
                f"{self.path.as_uri()}?mode=ro&immutable=1",
                uri=True,
            )
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error as exc:
            raise ContactRegisterError(f"Kontaktregister ist nicht lesbar: {exc}") from exc


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS contacts (
            contact_id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL UNIQUE,
            profile_id TEXT NOT NULL,
            area TEXT NOT NULL,
            organization TEXT NOT NULL,
            contact_name TEXT,
            role TEXT,
            purpose TEXT NOT NULL,
            object_ref TEXT,
            email TEXT,
            phone TEXT,
            effective_date TEXT NOT NULL,
            source_document_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_path TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active', 'deletion_candidate')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS contact_events (
            event_id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            action_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL CHECK(kind IN ('create', 'replace')),
            contact_id TEXT NOT NULL,
            prior_contact_id TEXT,
            applied_at TEXT NOT NULL
        );
        """
    )
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'schema'"
    ).fetchone()
    if row is None:
        connection.execute(
            "INSERT INTO metadata (key, value) VALUES ('schema', ?)",
            (_SCHEMA_VERSION,),
        )
    elif row[0] != _SCHEMA_VERSION:
        raise ContactRegisterError("Kontaktregister verwendet ein unbekanntes Schema.")


def _validate_schema(connection: sqlite3.Connection) -> None:
    try:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema'"
        ).fetchone()
    except sqlite3.Error as exc:
        raise ContactRegisterError("Kontaktregister besitzt kein gültiges Schema.") from exc
    if row is None or row[0] != _SCHEMA_VERSION:
        raise ContactRegisterError("Kontaktregister verwendet ein unbekanntes Schema.")


def _insert_contact(
    connection: sqlite3.Connection,
    contact_id: str,
    action: ContactRegisterAction,
    applied_at: str,
) -> None:
    candidate = action.candidate
    connection.execute(
        "INSERT INTO contacts "
        "(contact_id, candidate_id, profile_id, area, organization, contact_name, "
        "role, purpose, object_ref, email, phone, effective_date, "
        "source_document_id, source_sha256, source_path, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
        (
            contact_id,
            candidate.candidate_id,
            candidate.profile_id,
            candidate.area,
            candidate.organization,
            candidate.contact_name,
            candidate.role,
            candidate.purpose,
            candidate.object_ref,
            candidate.email,
            candidate.phone,
            candidate.effective_date,
            candidate.source_document_id,
            candidate.source_sha256,
            str(candidate.source_path),
            applied_at,
            applied_at,
        ),
    )


def _record(row: sqlite3.Row) -> ContactRecord:
    return ContactRecord(
        contact_id=str(row["contact_id"]),
        candidate_id=str(row["candidate_id"]),
        profile_id=str(row["profile_id"]),
        area=str(row["area"]),
        organization=str(row["organization"]),
        contact_name=row["contact_name"],
        role=row["role"],
        purpose=str(row["purpose"]),
        object_ref=row["object_ref"],
        email=row["email"],
        phone=row["phone"],
        effective_date=str(row["effective_date"]),
        source_document_id=str(row["source_document_id"]),
        source_sha256=str(row["source_sha256"]),
        source_path=Path(str(row["source_path"])),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _revision(records: tuple[ContactRecord, ...]) -> str:
    payload = [record.to_dict() for record in records]
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"contact_revision_{sha256(material).hexdigest()}"


def _contact_id(candidate_id: str) -> str:
    return f"contact_{sha256(candidate_id.encode('utf-8')).hexdigest()}"


def _safe_state_root(state_dir: Path) -> Path:
    absolute = Path(os.path.abspath(state_dir))
    if absolute.is_symlink() or absolute.resolve(strict=False) != absolute:
        raise ContactRegisterError(
            f"State-Verzeichnis enthält einen symbolischen Link oder Alias: {absolute}"
        )
    return absolute
