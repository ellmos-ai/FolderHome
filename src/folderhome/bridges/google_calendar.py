"""Google v3 solo-event creation with persistent, fail-closed reconciliation."""

from __future__ import annotations

import http.client
import json
import re
import sqlite3
from contextlib import closing, suppress
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from folderhome.capabilities.calendar_connector_gateway import (
    CalendarConnectorGatewayError,
    CalendarConnectorGatewayOutcomeUnknown,
)
from folderhome.contracts.calendar import CalendarBackend
from folderhome.contracts.calendar_connectors import (
    CalendarConnectorAccount,
    CalendarConnectorEvent,
)


class GoogleCalendarError(CalendarConnectorGatewayError):
    """Rejected configuration or input; never exposes credentials or provider text."""


class GoogleCalendarOutcomeUnknown(GoogleCalendarError, CalendarConnectorGatewayOutcomeUnknown):
    """An event may exist; only readback is safe, not a new write attempt."""


def _hash(value):
    return sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _valid_etag(value):
    return isinstance(value, str) and re.fullmatch(r'"[\x21\x23-\x7e]{1,510}"', value) is not None


class GoogleCalendarTransport:
    """One HTTPS request, bounded response, no redirects and no automatic retries."""

    def request(self, method, path, *, access_token, payload=None, if_match=None):
        if method in {"PATCH", "PUT", "DELETE"} and not _valid_etag(if_match):
            raise GoogleCalendarError("Kalenderänderung benötigt ein starkes Versionsmerkmal.")
        if if_match is not None and (
            method not in {"PATCH", "PUT", "DELETE"} or not _valid_etag(if_match)
        ):
            raise GoogleCalendarError("Bedingter Kalenderzugriff ist ungültig.")
        connection = http.client.HTTPSConnection("www.googleapis.com", timeout=15)
        try:
            connection.request(
                method,
                path,
                body=None if payload is None else json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    **({"If-Match": if_match} if if_match is not None else {}),
                },
            )
            response = connection.getresponse()
            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise GoogleCalendarError("Kalenderantwort überschreitet das Lesebudget.")
            # HTTP error bodies can contain private details; callers need only status.
            if not 200 <= response.status < 300:
                return response.status, {}
            if method == "DELETE" and response.status == 204 and not raw:
                return 204, {}
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeError):
                raise GoogleCalendarError(
                    "Kalenderantwort besitzt ein ungültiges Format."
                ) from None
            if not isinstance(value, dict):
                raise GoogleCalendarError("Kalenderantwort besitzt ein ungültiges Format.")
            return response.status, value
        finally:
            connection.close()


class GoogleCalendarGateway:
    provider_id = "google-calendar"
    provider_revision = "v3"
    network_required = True
    simulated = False

    def update_event(self, event, *, previous_event, expected_etag, idempotency_key):
        from folderhome.bridges.google_calendar_mutations import mutate_event

        return mutate_event(
            self,
            previous_event,
            replacement=event,
            expected_etag=expected_etag,
            idempotency_key=idempotency_key,
        )

    def delete_event(self, event, *, expected_etag, idempotency_key):
        from folderhome.bridges.google_calendar_mutations import mutate_event

        return mutate_event(
            self,
            event,
            replacement=None,
            expected_etag=expected_etag,
            idempotency_key=idempotency_key,
        )

    def __init__(
        self,
        *,
        account: CalendarConnectorAccount,
        ledger_path: Path,
        token_provider,
        allow_network_write: bool,
        transport=None,
    ):
        if (
            account.backend is not CalendarBackend.GOOGLE
            or account.provider_id != self.provider_id
            or account.provider_revision != self.provider_revision
        ):
            raise GoogleCalendarError("Kalenderkonto benötigt den Google-v3-Provider.")
        if account.calendar_id == "primary":
            raise GoogleCalendarError("Google-Kalender benötigt eine aufgelöste Kalender-ID.")
        self._account = account
        # Presentation, local account IDs and credential rotation cannot reset a
        # potentially completed remote write. Event IDs already bind the profile.
        self._namespace = _hash([self.provider_id, account.calendar_id])
        self._ledger_path = Path(ledger_path)
        self._token_provider = token_provider
        self._allowed = allow_network_write is True
        self._transport = transport if transport is not None else GoogleCalendarTransport()

    def _payload(self, event):
        if (
            event.profile_id != self._account.profile_id
            or event.calendar_id != self._account.calendar_id
        ):
            raise GoogleCalendarError("Kalenderereignis gehört nicht zum ausgewählten Konto.")
        try:
            zone = ZoneInfo(event.timezone)
            if type(event.all_day) is not bool or event.end is None:
                raise ValueError("Invalid event interval")
            if event.all_day:
                start, end = date.fromisoformat(event.start), date.fromisoformat(event.end)
            else:
                start, end = datetime.fromisoformat(event.start), datetime.fromisoformat(event.end)
                if start.tzinfo is None or end.tzinfo is None:
                    raise ValueError("Missing offset")
                if any(
                    value.utcoffset() != value.astimezone(zone).utcoffset()
                    for value in (start, end)
                ):
                    raise ValueError("Offset does not match declared timezone")
            if end <= start or event.attendees or event.transparency != "opaque":
                raise ValueError("Invalid solo event")
            if len(event.reminders) > 5 or any(
                item.method != "popup"
                or type(item.minutes_before) is not int
                or not 0 <= item.minutes_before <= 40320
                for item in event.reminders
            ):
                raise ValueError("Invalid reminder")
            payload = event.google_create_payload()
        except (ValueError, KeyError, TypeError) as exc:
            raise GoogleCalendarError(
                "Kalenderereignis besitzt ungültige Zeit-/Erinnerungsdaten."
            ) from exc
        del payload["calendar_id"]
        del payload["folderhome_event_uid"]
        payload["reminders"]["useDefault"] = payload["reminders"].pop("use_default")
        if payload["location"] is None:
            del payload["location"]
        return payload

    def _connect(self):
        path = self._ledger_path
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise GoogleCalendarError("Kalendernachweis darf keine Links verwenden.")
        path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(path, timeout=5)

    def _reserve(self, event_id, payload_hash, key):
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS calendar_creations ("
                "namespace TEXT, event_id TEXT, payload_hash TEXT NOT NULL, "
                "status TEXT NOT NULL, etag TEXT, PRIMARY KEY(namespace,event_id))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS calendar_requests ("
                "namespace TEXT, request_key TEXT, event_id TEXT NOT NULL, "
                "payload_hash TEXT NOT NULL, PRIMARY KEY(namespace,request_key))"
            )
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT event_id,payload_hash FROM calendar_requests "
                "WHERE namespace=? AND request_key=?",
                (self._namespace, key),
            ).fetchone()
            if previous is not None and previous != (event_id, payload_hash):
                raise GoogleCalendarError("Kalenderfreigabe wurde für andere Daten verwendet.")
            existing = connection.execute(
                "SELECT payload_hash FROM calendar_creations WHERE namespace=? AND event_id=?",
                (self._namespace, event_id),
            ).fetchone()
            if existing is not None and existing[0] != payload_hash:
                raise GoogleCalendarError(
                    "Bestehender Termin benötigt eine getrennte Änderungsfreigabe."
                )
            connection.execute(
                "INSERT OR IGNORE INTO calendar_requests VALUES (?,?,?,?)",
                (self._namespace, key, event_id, payload_hash),
            )
            connection.execute(
                "INSERT OR IGNORE INTO calendar_creations VALUES (?,?,?,'pending',NULL)",
                (self._namespace, event_id, payload_hash),
            )
            return existing is None

    def _confirm(self, event_id, etag, *, payload_hash):
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE calendar_creations SET status='confirmed',etag=? "
                "WHERE namespace=? AND event_id=? AND payload_hash=? "
                "AND ((status='pending' AND etag IS NULL) OR (status='confirmed' AND etag=?))",
                (etag, self._namespace, event_id, payload_hash, etag),
            )
            if cursor.rowcount != 1:
                raise GoogleCalendarOutcomeUnknown("Kalendernachweis ist nicht mehr vorhanden.")

    @staticmethod
    def _matches(remote, expected):
        try:
            if (
                remote.get("id") != expected["id"]
                or remote.get("status") != "confirmed"
                or not isinstance(remote.get("etag"), str)
                or not remote["etag"]
                or remote.get("attendees", [])
                or remote.get("recurrence", [])
                or remote.get("summary") != expected["summary"]
                or remote.get("location") != expected.get("location")
                or remote.get("transparency", "opaque") != "opaque"
            ):
                return False
            markers = remote.get("extendedProperties", {}).get("private", {})
            if any(
                markers.get(key) != value
                for key, value in expected["extendedProperties"]["private"].items()
            ):
                return False
            for field in ("start", "end"):
                wanted, actual = expected[field], remote[field]
                if "date" in wanted:
                    if actual.get("date") != wanted["date"] or "dateTime" in actual:
                        return False
                elif (
                    datetime.fromisoformat(actual["dateTime"])
                    != datetime.fromisoformat(wanted["dateTime"])
                    or actual.get("timeZone", wanted["timeZone"]) != wanted["timeZone"]
                ):
                    return False
            reminders = remote["reminders"]
            return reminders.get("useDefault") is False and sorted(
                (item["method"], item["minutes"]) for item in reminders.get("overrides", [])
            ) == sorted(
                (item["method"], item["minutes"]) for item in expected["reminders"]["overrides"]
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    def create_event(self, event: CalendarConnectorEvent, *, idempotency_key: str) -> str:
        if not self._allowed:
            raise GoogleCalendarError("Separate Google-Kalenderschreibfreigabe fehlt.")
        if (
            not isinstance(idempotency_key, str)
            or re.fullmatch(r"[0-9a-f]{64}", idempotency_key) is None
        ):
            raise GoogleCalendarError(
                "Kalenderfreigabe benötigt einen gültigen Idempotenzschlüssel."
            )
        payload = self._payload(event)
        payload_hash = _hash(payload)
        event_id = "fh" + _hash([event.profile_id, event.event_uid])
        payload.update(
            id=event_id,
            extendedProperties={
                "private": {
                    "folderhome_uid": event.event_uid,
                    "folderhome_payload_sha256": payload_hash,
                }
            },
        )
        try:
            token = self._token_provider(self._account.credential_ref)
        except Exception:
            # Resolver implementations may raise arbitrary ordinary exceptions
            # containing paths or secrets; even formatted tracebacks stay neutral.
            raise GoogleCalendarError("Google-Zugangsreferenz ist nicht verfügbar.") from None
        if not isinstance(token, str) or not token or any(char.isspace() for char in token):
            raise GoogleCalendarError("Google-Zugangsreferenz ist nicht verfügbar.")
        base = f"/calendar/v3/calendars/{quote(event.calendar_id, safe='')}/events"
        try:
            status, remote = self._transport.request(
                "GET", f"{base}/{event_id}", access_token=token
            )
            # A failed read is not a write attempt. Persist the atomic reservation
            # only after the probe, and always before the possible POST.
            if status not in (200, 404):
                raise GoogleCalendarOutcomeUnknown("Kalender konnte nicht geprüft werden.")
            fresh = self._reserve(event_id, payload_hash, idempotency_key)
            if status == 404 and fresh:
                # Never repeat the POST; resolve a possible effect through GET.
                with suppress(OSError, http.client.HTTPException, GoogleCalendarError, ValueError):
                    self._transport.request(
                        "POST", f"{base}?sendUpdates=none", access_token=token, payload=payload
                    )
                status, remote = self._transport.request(
                    "GET", f"{base}/{event_id}", access_token=token
                )
            if status != 200 or not self._matches(remote, payload):
                raise GoogleCalendarOutcomeUnknown(
                    "Kalenderergebnis unklar; nur Rücklesen ist sicher."
                )
            self._confirm(event_id, remote["etag"], payload_hash=payload_hash)
            return event_id
        except (
            OSError,
            sqlite3.Error,
            http.client.HTTPException,
            GoogleCalendarError,
            ValueError,
        ):
            raise GoogleCalendarOutcomeUnknown(
                "Kalenderergebnis unklar; keinen Schreibversuch wiederholen."
            ) from None
