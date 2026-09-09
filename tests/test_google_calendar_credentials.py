"""Private OAuth resolution using real google-auth and a synthetic HTTPS boundary."""

from __future__ import annotations

import importlib
import json
from types import SimpleNamespace

import pytest


def api():
    assert importlib.util.find_spec("folderhome.bridges.google_calendar_credentials") is not None
    return importlib.import_module("folderhome.bridges.google_calendar_credentials")


@pytest.fixture
def authorized_file(tmp_path):
    path = tmp_path / "private-oauth.json"
    path.write_text(
        json.dumps(
            {
                "token": "synthetic-token",
                "expiry": "2100-01-01T00:00:00Z",
                "refresh_token": "synthetic-refresh",
                "client_id": "synthetic-client",
                "client_secret": "synthetic-secret",
                "type": "authorized_user",
                "scopes": ["https://www.googleapis.com/auth/calendar.events"],
            }
        ),
        encoding="utf-8",
    )
    return path


def resolver(path, enabled=True):
    return api().GoogleCalendarCredentialResolver(
        credential_file=path,
        credential_ref="connector://google-calendar/test",
        allow_network=enabled,
    )


def test_valid_authorized_user_token_is_loaded_only_on_matching_call(authorized_file, monkeypatch):
    module = api()
    before = authorized_file.read_bytes()
    instance = resolver(authorized_file)

    def forbidden(*args, **kwargs):
        pytest.fail("Valid token must not cause a refresh")

    monkeypatch.setattr(module.http.client, "HTTPSConnection", forbidden)
    assert instance("connector://google-calendar/test") == "synthetic-token"
    assert authorized_file.read_bytes() == before


@pytest.mark.parametrize(
    "enabled,reference",
    [
        (False, "connector://google-calendar/test"),
        (1, "connector://google-calendar/test"),
        ("true", "connector://google-calendar/test"),
        (True, "connector://google-calendar/other"),
    ],
)
def test_no_gate_or_wrong_reference_does_not_open_private_file(
    tmp_path, monkeypatch, enabled, reference
):
    from pathlib import Path

    instance = resolver(tmp_path / "missing.json", enabled)

    def forbidden(*args, **kwargs):
        pytest.fail("Credentials opened before approval/reference validation")

    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(api().GoogleCalendarCredentialError):
        instance(reference)


@pytest.mark.parametrize(
    "status,granted_scope",
    [
        (200, None),
        (302, None),
        (503, None),
        (200, "https://www.googleapis.com/auth/drive"),
        (200, "https://www.googleapis.com/auth/calendar.events"),
    ],
)
def test_expired_token_refresh_is_pinned_bounded_once_and_never_persisted(
    authorized_file, monkeypatch, status, granted_scope
):
    from urllib.parse import parse_qs

    module = api()
    payload = json.loads(authorized_file.read_text(encoding="utf-8"))
    payload["expiry"] = "2000-01-01T00:00:00Z"
    authorized_file.write_text(json.dumps(payload), encoding="utf-8")
    before = authorized_file.read_bytes()
    calls = []
    closed = []

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "oauth2.googleapis.com"
            assert timeout == 15

        def request(self, method, path, body, headers):
            calls.append((method, path, body, headers))

        def getresponse(self):
            data = json.dumps(
                {
                    "access_token": "refreshed-synthetic",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    **({"scope": granted_scope} if granted_scope is not None else {}),
                }
                if status == 200
                else {"error": "synthetic_error"}
            ).encode()
            return SimpleNamespace(
                status=status, read=lambda maximum: data[:maximum], getheaders=lambda: []
            )

        def close(self):
            closed.append(True)

    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    if status == 200 and (granted_scope is None or granted_scope.endswith("calendar.events")):
        assert (
            resolver(authorized_file)("connector://google-calendar/test") == "refreshed-synthetic"
        )
    else:
        with pytest.raises(module.GoogleCalendarCredentialError):
            resolver(authorized_file)("connector://google-calendar/test")
    assert len(calls) == 1 and closed == [True]
    assert calls[0][:2] == ("POST", "/token")
    form = parse_qs(calls[0][2].decode())
    assert form["grant_type"] == ["refresh_token"]
    assert form["refresh_token"] == ["synthetic-refresh"]
    assert authorized_file.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        {"token_uri": "https://example.invalid/token"},
        {"universe_domain": "example.invalid"},
        {"scopes": ["https://www.googleapis.com/auth/drive"]},
        {"type": "service_account"},
    ],
)
def test_foreign_authorities_and_wrong_credential_types_are_rejected(authorized_file, mutation):
    payload = json.loads(authorized_file.read_text(encoding="utf-8"))
    authorized_file.write_text(json.dumps({**payload, **mutation}), encoding="utf-8")
    with pytest.raises(api().GoogleCalendarCredentialError):
        resolver(authorized_file)("connector://google-calendar/test")


def test_bad_credentials_are_redacted_and_size_limited(tmp_path):
    import traceback

    path = tmp_path / "private.json"
    path.write_bytes(b"private-secret" * 10000)
    with pytest.raises(api().GoogleCalendarCredentialError) as failure:
        resolver(path)("connector://google-calendar/test")
    assert "private-secret" not in "".join(traceback.format_exception(failure.value))
