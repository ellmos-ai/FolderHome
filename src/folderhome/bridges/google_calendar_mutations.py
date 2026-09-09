"""ETag-bound mutation core; app-level mutation approvals are a separate layer."""

import http.client
import re
from contextlib import closing, suppress
from copy import deepcopy
from urllib.parse import quote

from folderhome.bridges.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarOutcomeUnknown,
    _hash,
    _valid_etag,
)


class GoogleCalendarVersionConflict(GoogleCalendarError):
    """The approved prior version is not current; never automatically rebase."""


def _version(connection, namespace, event_id):
    return connection.execute(
        "SELECT payload_hash,status,etag FROM calendar_creations WHERE namespace=? AND event_id=?",
        (namespace, event_id),
    ).fetchone()


def _attempt(connection, namespace, event_id, etag):
    if not connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='calendar_mutations'"
    ).fetchone():
        return None
    return connection.execute(
        "SELECT operation_hash,status,result_etag FROM calendar_mutations "
        "WHERE namespace=? AND event_id=? AND expected_etag=?",
        (namespace, event_id, etag),
    ).fetchone()


def _validate(connection, namespace, event_id, etag, before_hash, operation_hash, key):
    used = connection.execute(
        "SELECT event_id,payload_hash FROM calendar_requests WHERE namespace=? AND request_key=?",
        (namespace, key),
    ).fetchone()
    if used is not None and used != (event_id, operation_hash):
        raise GoogleCalendarVersionConflict("Kalenderfreigabe wurde bereits anders verwendet.")
    attempt = _attempt(connection, namespace, event_id, etag)
    if attempt is not None:
        if attempt[0] != operation_hash or attempt[1] == "conflict":
            raise GoogleCalendarVersionConflict("Kalenderversion besitzt einen anderen Versuch.")
    elif _version(connection, namespace, event_id) != (before_hash, "confirmed", etag):
        raise GoogleCalendarVersionConflict("Bestätigte Kalenderreferenz ist nicht aktuell.")
    return attempt


def _reserve(gateway, event_id, etag, before_hash, operation_hash, key):
    with closing(gateway._connect()) as connection, connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS calendar_mutations (namespace TEXT,event_id TEXT,"
            "expected_etag TEXT,operation_hash TEXT NOT NULL,status TEXT NOT NULL,result_etag TEXT,"
            "PRIMARY KEY(namespace,event_id,expected_etag))"
        )
        connection.execute("BEGIN IMMEDIATE")
        attempt = _validate(
            connection,
            gateway._namespace,
            event_id,
            etag,
            before_hash,
            operation_hash,
            key,
        )
        connection.execute(
            "INSERT OR IGNORE INTO calendar_requests VALUES (?,?,?,?)",
            (gateway._namespace, key, event_id, operation_hash),
        )
        if attempt is None:
            connection.execute(
                "INSERT INTO calendar_mutations VALUES (?,?,?,?,'pending',NULL)",
                (gateway._namespace, event_id, etag, operation_hash),
            )
        return attempt is None


def _finish(gateway, event_id, etag, before_hash, after_hash, result_etag, operation_hash):
    new_version = (after_hash, "deleted" if after_hash is None else "confirmed", result_etag)
    # Keep the original payload fingerprint on a tombstone; it must not become
    # a new creation reservation on replay of an old create approval.
    if after_hash is None:
        new_version = (before_hash, "deleted", None)
    with closing(gateway._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        attempt = _attempt(connection, gateway._namespace, event_id, etag)
        if attempt is None or attempt[0] != operation_hash or attempt[1] == "conflict":
            raise GoogleCalendarOutcomeUnknown("Kalenderänderungsnachweis ist nicht aktuell.")
        current = _version(connection, gateway._namespace, event_id)
        if current not in ((before_hash, "confirmed", etag), new_version):
            raise GoogleCalendarOutcomeUnknown("Neueren Kalendernachweis nicht überschreiben.")
        connection.execute(
            "UPDATE calendar_creations SET payload_hash=?,status=?,etag=? "
            "WHERE namespace=? AND event_id=?",
            (*new_version, gateway._namespace, event_id),
        )
        connection.execute(
            "UPDATE calendar_mutations SET status='confirmed',result_etag=? "
            "WHERE namespace=? AND event_id=? AND expected_etag=?",
            (result_etag, gateway._namespace, event_id, etag),
        )


def _marked(gateway, event):
    payload = gateway._payload(event)
    fingerprint = _hash(payload)
    payload.update(
        id="fh" + _hash([event.profile_id, event.event_uid]),
        extendedProperties={
            "private": {
                "folderhome_uid": event.event_uid,
                "folderhome_payload_sha256": fingerprint,
            }
        },
    )
    return payload, fingerprint


def _solo_default(remote):
    return (
        isinstance(remote, dict)
        and not remote.get("recurringEventId")
        and remote.get("eventType", "default") == "default"
        and not remote.get("attendeesOmitted")
    )


def mutate_event(gateway, previous, *, replacement, expected_etag, idempotency_key):
    if gateway._allowed is not True:
        raise GoogleCalendarError("Separate Google-Kalenderschreibfreigabe fehlt.")
    if (
        not _valid_etag(expected_etag)
        or not isinstance(idempotency_key, str)
        or re.fullmatch(r"[0-9a-f]{64}", idempotency_key) is None
    ):
        raise GoogleCalendarError("Kalenderänderung benötigt Version und genaue Freigabe.")
    before, before_hash = _marked(gateway, previous)
    after, after_hash = (None, None) if replacement is None else _marked(gateway, replacement)
    event_id = before["id"]
    if after is not None and (after["id"] != event_id or after_hash == before_hash):
        raise GoogleCalendarError("Kalenderänderung benötigt dasselbe Ziel und geänderte Daten.")
    operation = "delete" if replacement is None else "update"
    operation_hash = _hash([operation, event_id, expected_etag, before_hash, after_hash])
    attempted = False
    try:
        if not gateway._ledger_path.is_file():
            raise GoogleCalendarVersionConflict("Bestätigter Kalendernachweis fehlt.")
        with closing(gateway._connect()) as connection:
            attempt = _validate(
                connection,
                gateway._namespace,
                event_id,
                expected_etag,
                before_hash,
                operation_hash,
                idempotency_key,
            )
        attempted = attempt is not None
        token = gateway._token_provider(gateway._account.credential_ref)
        if not isinstance(token, str) or not token or any(not 33 <= ord(c) <= 126 for c in token):
            raise ValueError("Invalid token")
        path = f"/calendar/v3/calendars/{quote(previous.calendar_id, safe='')}/events/{event_id}"
        status, remote = gateway._transport.request("GET", path, access_token=token)
        if attempt is None:
            if (
                status != 200
                or not gateway._matches(remote, before)
                or remote.get("etag") != expected_etag
                or not _solo_default(remote)
            ):
                raise GoogleCalendarVersionConflict(
                    "Kalendertermin hat nicht die bestätigte Version."
                )
            fresh = _reserve(
                gateway,
                event_id,
                expected_etag,
                before_hash,
                operation_hash,
                idempotency_key,
            )
            attempted = True
            if fresh:
                patch = None
                if after is not None:
                    patch = deepcopy(after)
                    del patch["id"]
                    patch["location"] = after.get("location")
                    for name in ("start", "end"):
                        for field in {"date", "dateTime", "timeZone"} - set(patch[name]):
                            patch[name][field] = None
                    properties = deepcopy(remote.get("extendedProperties", {}))
                    properties.setdefault("private", {}).update(
                        after["extendedProperties"]["private"]
                    )
                    patch["extendedProperties"] = properties
                result_status = None
                with suppress(OSError, http.client.HTTPException, GoogleCalendarError, ValueError):
                    result_status, _ = gateway._transport.request(
                        "DELETE" if after is None else "PATCH",
                        path + "?sendUpdates=none",
                        access_token=token,
                        payload=patch,
                        if_match=expected_etag,
                    )
                if result_status == 412:
                    with closing(gateway._connect()) as connection, connection:
                        connection.execute(
                            "UPDATE calendar_mutations SET status='conflict' "
                            "WHERE namespace=? AND event_id=? AND expected_etag=?",
                            (gateway._namespace, event_id, expected_etag),
                        )
                    raise GoogleCalendarVersionConflict(
                        "Kalenderversion wurde zwischenzeitlich geändert."
                    )
            status, remote = gateway._transport.request("GET", path, access_token=token)
        elif _reserve(
            gateway,
            event_id,
            expected_etag,
            before_hash,
            operation_hash,
            idempotency_key,
        ):
            raise GoogleCalendarOutcomeUnknown("Vorheriger Änderungsversuch ist nicht mehr belegt.")
        result_etag = None
        if after is None:
            if status not in (404, 410) and not (
                status == 200
                and remote.get("id") == event_id
                and remote.get("status") == "cancelled"
                and not remote.get("recurringEventId")
            ):
                raise GoogleCalendarOutcomeUnknown("Kalenderlöschung ist nicht bestätigt.")
        else:
            if status != 200 or not gateway._matches(remote, after) or not _solo_default(remote):
                raise GoogleCalendarOutcomeUnknown("Kalenderänderung ist nicht bestätigt.")
            result_etag = remote["etag"]
            if not _valid_etag(result_etag):
                raise GoogleCalendarOutcomeUnknown("Kalenderversion ist nicht bestätigt.")
            if attempt is not None and attempt[1] == "confirmed" and attempt[2] != result_etag:
                raise GoogleCalendarOutcomeUnknown(
                    "Kalender wurde nach der Änderung erneut geändert."
                )
        _finish(
            gateway, event_id, expected_etag, before_hash, after_hash, result_etag, operation_hash
        )
        return {
            "schema": "folderhome.google-calendar-mutation-result.v1",
            "provider_event_id": event_id,
            "calendar_id": previous.calendar_id,
            "operation": operation,
            "status": "absent" if after is None else "updated",
            "etag": result_etag,
            "payload_sha256": after_hash,
        }
    except GoogleCalendarVersionConflict:
        raise
    except Exception:
        error = GoogleCalendarOutcomeUnknown if attempted else GoogleCalendarError
        raise error(
            "Kalenderänderung nicht bestätigt; keinen Schreibversuch wiederholen."
        ) from None
