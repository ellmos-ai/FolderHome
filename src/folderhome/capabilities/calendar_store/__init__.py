"""Reusable local calendar state with append-only execution audit."""

from __future__ import annotations

import json
import os
import sqlite3
from hashlib import sha256
from pathlib import Path

from folderhome.contracts import (
    CalendarEventRecord,
    CalendarHandoffAction,
    CalendarHandoffApproval,
)

_SCHEMA_VERSION = "folderhome.calendar-store.v1"


class CalendarStoreError(RuntimeError):
    """Raised when local calendar state is stale, unsafe, or inconsistent."""


class CalendarStore:
    """Query local events and commit approved actions transactionally."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = _safe_state_root(state_dir)
        self.path = self.state_dir / "calendar" / "calendar.sqlite3"

    def revision(self) -> str:
        """Return a stable revision of active local events without creating state."""

        return _revision(self.list_events())

    def list_events(
        self,
        *,
        profile_id: str | None = None,
        area: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[CalendarEventRecord, ...]:
        """Read active events through an immutable SQLite connection."""

        if not self.path.exists():
            return ()
        connection = self._read_connection()
        try:
            _validate_schema(connection)
            clauses = ["status = 'active'"]
            parameters: list[str] = []
            for column, value in (
                ("profile_id", profile_id),
                ("area", area),
            ):
                if value is not None:
                    clauses.append(f"{column} = ?")
                    parameters.append(value)
            if date_from is not None:
                clauses.append("event_date >= ?")
                parameters.append(date_from)
            if date_to is not None:
                clauses.append("event_date <= ?")
                parameters.append(date_to)
            rows = connection.execute(
                "SELECT * FROM calendar_events WHERE "
                + " AND ".join(clauses)
                + " ORDER BY event_date, COALESCE(start_time, ''), event_id",
                parameters,
            ).fetchall()
            return tuple(_record(row) for row in rows)
        except sqlite3.Error as exc:
            raise CalendarStoreError(f"Kalenderstatus ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()

    def count_actions(self) -> int:
        """Count immutable calendar execution audit rows."""

        if not self.path.exists():
            return 0
        connection = self._read_connection()
        try:
            _validate_schema(connection)
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM calendar_action_events"
                ).fetchone()[0]
            )
        except sqlite3.Error as exc:
            raise CalendarStoreError(f"Kalenderstatus ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()

    def validate_execution(self, *, expected_revision: str, approval_id: str) -> None:
        """Recheck revision and approval replay without creating a database."""

        if not self.path.exists():
            if expected_revision != _revision(()):
                raise CalendarStoreError("Kalenderstatus wurde seit der Planung verändert.")
            return
        connection = self._read_connection()
        try:
            _validate_schema(connection)
            records = tuple(
                _record(row)
                for row in connection.execute(
                    "SELECT * FROM calendar_events WHERE status = 'active' "
                    "ORDER BY event_date, COALESCE(start_time, ''), event_id"
                ).fetchall()
            )
            if _revision(records) != expected_revision:
                raise CalendarStoreError("Kalenderstatus wurde seit der Planung verändert.")
            replay = connection.execute(
                "SELECT 1 FROM calendar_action_events WHERE approval_id = ? LIMIT 1",
                (approval_id,),
            ).fetchone()
            if replay is not None:
                raise CalendarStoreError("Kalenderfreigabe wurde bereits verwendet.")
        except sqlite3.Error as exc:
            raise CalendarStoreError(f"Kalenderstatus ist nicht lesbar: {exc}") from exc
        finally:
            connection.close()

    def apply_local(
        self,
        *,
        expected_revision: str,
        actions: tuple[CalendarHandoffAction, ...],
        approval: CalendarHandoffApproval,
    ) -> tuple[tuple[str, ...], str]:
        """Insert local events and audit rows in one SQLite transaction."""

        connection = self._write_connection()
        event_ids: list[str] = []
        try:
            _initialize_schema(connection)
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
            self._validate_write_transaction(
                connection,
                expected_revision=expected_revision,
                approval_id=approval.approval_id,
            )
            for action in actions:
                candidate = action.candidate
                event_id = _event_id(candidate.event_uid)
                connection.execute(
                    "INSERT INTO calendar_events "
                    "(event_id, event_uid, candidate_id, profile_id, area, title, "
                    "event_date, start_time, end_time, timezone, location, "
                    "source_document_id, source_sha256, source_path, status, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                    "?, ?, ?, ?, 'active', ?, ?)",
                    (
                        event_id,
                        candidate.event_uid,
                        candidate.candidate_id,
                        candidate.profile_id,
                        candidate.area,
                        candidate.title,
                        candidate.event_date,
                        candidate.start_time,
                        candidate.end_time,
                        candidate.timezone,
                        candidate.location,
                        candidate.source_document_id,
                        candidate.source_sha256,
                        str(candidate.source_path),
                        approval.approved_at,
                        approval.approved_at,
                    ),
                )
                self._insert_audit(
                    connection,
                    approval=approval,
                    action=action,
                    kind="local_event",
                    event_id=event_id,
                    output_path=None,
                    output_sha256=None,
                )
                event_ids.append(event_id)
            after = tuple(
                _record(row)
                for row in connection.execute(
                    "SELECT * FROM calendar_events WHERE status = 'active' "
                    "ORDER BY event_date, COALESCE(start_time, ''), event_id"
                ).fetchall()
            )
            revision_after = _revision(after)
            connection.commit()
            return tuple(event_ids), revision_after
        except CalendarStoreError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise CalendarStoreError(
                f"Lokaler Kalender konnte nicht aktualisiert werden: {exc}"
            ) from exc
        finally:
            connection.close()

    def record_external(
        self,
        *,
        expected_revision: str,
        actions: tuple[CalendarHandoffAction, ...],
        approval: CalendarHandoffApproval,
        receipts: tuple[tuple[Path, str], ...],
    ) -> str:
        """Append audit rows for already verified external handoff files."""

        if len(actions) != len(receipts):
            raise CalendarStoreError("ICS-Aktionen und Ausgabebelege passen nicht zusammen.")
        connection = self._write_connection()
        try:
            _initialize_schema(connection)
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
            self._validate_write_transaction(
                connection,
                expected_revision=expected_revision,
                approval_id=approval.approval_id,
            )
            for action, (output_path, output_sha256) in zip(actions, receipts, strict=True):
                self._insert_audit(
                    connection,
                    approval=approval,
                    action=action,
                    kind="ics_output",
                    event_id=None,
                    output_path=output_path,
                    output_sha256=output_sha256,
                )
            connection.commit()
            return expected_revision
        except CalendarStoreError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise CalendarStoreError(
                f"Kalender-Audit konnte nicht aktualisiert werden: {exc}"
            ) from exc
        finally:
            connection.close()

    def _validate_write_transaction(
        self,
        connection: sqlite3.Connection,
        *,
        expected_revision: str,
        approval_id: str,
    ) -> None:
        records = tuple(
            _record(row)
            for row in connection.execute(
                "SELECT * FROM calendar_events WHERE status = 'active' "
                "ORDER BY event_date, COALESCE(start_time, ''), event_id"
            ).fetchall()
        )
        if _revision(records) != expected_revision:
            raise CalendarStoreError("Kalenderstatus wurde seit der Planung verändert.")
        replay = connection.execute(
            "SELECT 1 FROM calendar_action_events WHERE approval_id = ? LIMIT 1",
            (approval_id,),
        ).fetchone()
        if replay is not None:
            raise CalendarStoreError("Kalenderfreigabe wurde bereits verwendet.")

    @staticmethod
    def _insert_audit(
        connection: sqlite3.Connection,
        *,
        approval: CalendarHandoffApproval,
        action: CalendarHandoffAction,
        kind: str,
        event_id: str | None,
        output_path: Path | None,
        output_sha256: str | None,
    ) -> None:
        material = f"{approval.approval_id}\0{action.action_id}\0{kind}"
        audit_id = f"calendar_audit_{sha256(material.encode('utf-8')).hexdigest()}"
        connection.execute(
            "INSERT INTO calendar_action_events "
            "(audit_id, approval_id, plan_id, action_id, kind, event_uid, "
            "event_id, output_path, output_sha256, applied_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                audit_id,
                approval.approval_id,
                approval.plan_id,
                action.action_id,
                kind,
                action.candidate.event_uid,
                event_id,
                str(output_path) if output_path else None,
                output_sha256,
                approval.approved_at,
            ),
        )

    def _write_connection(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise CalendarStoreError("Kalenderstatus darf kein symbolischer Link sein.")
        try:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error as exc:
            raise CalendarStoreError(f"Kalenderstatus ist nicht beschreibbar: {exc}") from exc

    def _read_connection(self) -> sqlite3.Connection:
        if self.path.is_symlink() or not self.path.is_file():
            raise CalendarStoreError(
                f"Kalenderstatus fehlt oder ist keine reguläre Datei: {self.path}"
            )
        try:
            connection = sqlite3.connect(
                f"{self.path.as_uri()}?mode=ro&immutable=1",
                uri=True,
            )
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error as exc:
            raise CalendarStoreError(f"Kalenderstatus ist nicht lesbar: {exc}") from exc


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calendar_events (
            event_id TEXT PRIMARY KEY,
            event_uid TEXT NOT NULL UNIQUE,
            candidate_id TEXT NOT NULL UNIQUE,
            profile_id TEXT NOT NULL,
            area TEXT NOT NULL,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            timezone TEXT NOT NULL,
            location TEXT,
            source_document_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_path TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status = 'active'),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calendar_action_events (
            audit_id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            action_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL CHECK(kind IN ('local_event', 'ics_output')),
            event_uid TEXT NOT NULL,
            event_id TEXT,
            output_path TEXT,
            output_sha256 TEXT,
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
        raise CalendarStoreError("Kalenderstatus verwendet ein unbekanntes Schema.")


def _validate_schema(connection: sqlite3.Connection) -> None:
    try:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema'"
        ).fetchone()
    except sqlite3.Error as exc:
        raise CalendarStoreError("Kalenderstatus besitzt kein gültiges Schema.") from exc
    if row is None or row[0] != _SCHEMA_VERSION:
        raise CalendarStoreError("Kalenderstatus verwendet ein unbekanntes Schema.")


def _record(row: sqlite3.Row) -> CalendarEventRecord:
    return CalendarEventRecord(
        event_id=str(row["event_id"]),
        event_uid=str(row["event_uid"]),
        candidate_id=str(row["candidate_id"]),
        profile_id=str(row["profile_id"]),
        area=str(row["area"]),
        title=str(row["title"]),
        event_date=str(row["event_date"]),
        start_time=row["start_time"],
        end_time=row["end_time"],
        timezone=str(row["timezone"]),
        location=row["location"],
        source_document_id=str(row["source_document_id"]),
        source_sha256=str(row["source_sha256"]),
        source_path=Path(str(row["source_path"])),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _revision(records: tuple[CalendarEventRecord, ...]) -> str:
    payload = [record.to_dict() for record in records]
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"calendar_revision_{sha256(material).hexdigest()}"


def _event_id(event_uid: str) -> str:
    return f"calendar_event_{sha256(event_uid.encode('utf-8')).hexdigest()}"


def _safe_state_root(state_dir: Path) -> Path:
    absolute = Path(os.path.abspath(state_dir))
    if absolute.is_symlink() or absolute.resolve(strict=False) != absolute:
        raise CalendarStoreError(
            f"State-Verzeichnis enthält einen symbolischen Link oder Alias: {absolute}"
        )
    return absolute


EMPTY_CALENDAR_REVISION = _revision(())
