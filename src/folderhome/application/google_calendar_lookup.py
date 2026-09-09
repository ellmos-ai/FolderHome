"""Explicitly approved, read-only Google calendar identity discovery."""

import re
from pathlib import Path
from urllib.parse import quote

from folderhome.bridges.google_calendar import GoogleCalendarTransport
from folderhome.bridges.google_calendar_credentials import GoogleCalendarCredentialResolver

_REFERENCE = re.compile(r"connector://google-calendar/[a-z][a-z0-9_-]{1,63}")
METADATA_SCOPE = "https://www.googleapis.com/auth/calendar.calendars.readonly"


class GoogleCalendarLookupError(ValueError):
    """Neutral discovery failure without private provider details."""


def resolve_google_calendar_id(
    *,
    credential_file,
    credential_ref,
    calendar_id,
    allow_network_read,
    transport=None,
):
    if allow_network_read is not True:
        raise GoogleCalendarLookupError("Google-Kalenderabfrage benötigt eine eigene Lesefreigabe.")
    try:
        if (
            not _identifier(calendar_id)
            or not isinstance(credential_ref, str)
            or not _REFERENCE.fullmatch(credential_ref)
        ):
            raise ValueError("Invalid identity request")
        token = GoogleCalendarCredentialResolver(
            credential_file=Path(credential_file),
            credential_ref=credential_ref,
            allow_network=True,
            required_scope=METADATA_SCOPE,
        )(credential_ref)
        client = transport if transport is not None else GoogleCalendarTransport()
        status, response = client.request(
            "GET",
            "/calendar/v3/calendars/" + quote(calendar_id, safe=""),
            access_token=token,
        )
        resolved = response.get("id")
        if (
            status != 200
            or response.get("kind") != "calendar#calendar"
            or not _identifier(resolved)
            or resolved.casefold() == "primary"
            or (calendar_id != "primary" and resolved != calendar_id)
        ):
            raise ValueError("Unverified calendar identity")
        return {
            "schema": "folderhome.google-calendar-identity.v1",
            "requested_calendar_id": calendar_id,
            "calendar_id": resolved,
            "provider_id": "google-calendar",
            "provider_revision": "v3",
            "read_only": True,
        }
    except Exception:
        raise GoogleCalendarLookupError(
            "Kalender-ID konnte nicht geprüft werden; "
            "private Datei, Metadaten-Scope und Konto prüfen."
        ) from None


def _identifier(value):
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 1024
        and all(33 <= ord(char) <= 126 for char in value)
    )
