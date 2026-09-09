"""Resolve an existing private Google OAuth grant only after explicit approval."""

from __future__ import annotations

import http.client
import json
from pathlib import Path
from types import SimpleNamespace


class GoogleCalendarCredentialError(RuntimeError):
    """Neutral credential failure; never contains a token or private provider text."""


class _RefreshRequest:
    """google-auth request protocol with one pinned, bounded network attempt."""

    def __init__(self):
        self._used = False

    def __call__(self, url, method="GET", body=None, headers=None, **kwargs):
        if self._used or url != "https://oauth2.googleapis.com/token" or method != "POST":
            raise GoogleCalendarCredentialError("Google-Token-Erneuerung ist nicht freigegeben.")
        self._used = True
        connection = http.client.HTTPSConnection("oauth2.googleapis.com", timeout=15)
        try:
            connection.request(method, "/token", body=body, headers=headers or {})
            response = connection.getresponse()
            raw = response.read(65_537)
            if len(raw) > 65_536 or response.status != 200:
                # Raise before google-auth can apply its own retry/backoff policy.
                raise GoogleCalendarCredentialError("Google-Token-Erneuerung ist fehlgeschlagen.")
            return SimpleNamespace(
                status=response.status, data=raw, headers=dict(response.getheaders())
            )
        finally:
            connection.close()


class GoogleCalendarCredentialResolver:
    """Read Google authorized-user JSON; no login, token persistence or ambient auth."""

    def __init__(
        self,
        *,
        credential_file: Path,
        credential_ref: str,
        allow_network: bool,
        required_scope: str = "https://www.googleapis.com/auth/calendar.events",
    ):
        if required_scope not in {
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.calendars.readonly",
        }:
            raise GoogleCalendarCredentialError("Unbekannter Google-Kalenderzugriff.")
        self._required_scope = required_scope
        self._path = Path(credential_file)
        self._reference = credential_ref
        self._allowed = allow_network is True

    def __call__(self, reference: str) -> str:
        if not self._allowed or reference != self._reference:
            raise GoogleCalendarCredentialError("Google-Zugangsreferenz ist nicht freigegeben.")
        try:
            path = self._path
            if not path.is_absolute() or any(
                parent.is_symlink() or getattr(parent, "is_junction", lambda: False)()
                for parent in (path, *path.parents)
            ):
                raise ValueError("Invalid private file")
            with path.open("rb") as handle:
                raw = handle.read(65_537)
            if len(raw) > 65_536:
                raise ValueError("Credential file too large")
            payload = json.loads(raw)
            if (
                not isinstance(payload, dict)
                or payload.get("type", "authorized_user") != "authorized_user"
                or payload.get("token_uri", "https://oauth2.googleapis.com/token")
                != "https://oauth2.googleapis.com/token"
                or payload.get("universe_domain", "googleapis.com") != "googleapis.com"
            ):
                raise ValueError("Invalid credential authority")
            from google.oauth2.credentials import Credentials

            credentials = Credentials.from_authorized_user_info(payload)
            if not credentials.has_scopes([self._required_scope]):
                raise ValueError("Calendar grant missing")
            if not credentials.valid:
                credentials.refresh(_RefreshRequest())
            if credentials.granted_scopes is not None and (
                self._required_scope not in credentials.granted_scopes
            ):
                raise ValueError("Actual calendar grant missing")
            token = credentials.token
            if (
                not credentials.valid
                or not isinstance(token, str)
                or not token
                or any(ord(char) < 33 or ord(char) > 126 for char in token)
            ):
                raise ValueError("Invalid access token")
            return token
        except Exception:
            raise GoogleCalendarCredentialError(
                "Google-Zugang ist nicht verfügbar; Kalenderextra und Kontofreigabe prüfen."
            ) from None
