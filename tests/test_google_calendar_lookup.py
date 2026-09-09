"""Read-only identity discovery with real credentials and a synthetic HTTP boundary."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_google_calendar_credentials import authorized_file as authorized_file

SCOPE = "https://www.googleapis.com/auth/calendar.calendars.readonly"
REFERENCE = "connector://google-calendar/test"


def api():
    return importlib.import_module("folderhome.application.google_calendar_lookup")


class MetadataService:
    def __init__(self, *, status=200, response=None):
        self.status = status
        self.response = (
            response
            if response is not None
            else {"kind": "calendar#calendar", "id": "concrete@example.invalid"}
        )
        self.calls = []

    def request(self, method, path, *, access_token, payload=None):
        self.calls.append((method, path, payload))
        assert access_token == "synthetic-token"
        return self.status, self.response


def metadata_grant(path):
    data = json.loads(path.read_text())
    data["scopes"] = [SCOPE]
    path.write_text(json.dumps(data), encoding="utf-8")


def lookup(path, service, **changes):
    arguments = dict(
        credential_file=path,
        credential_ref=REFERENCE,
        calendar_id="primary",
        allow_network_read=True,
        transport=service,
    )
    arguments.update(changes)
    return api().resolve_google_calendar_id(**arguments)


def test_primary_lookup_uses_metadata_scope_and_never_persists(authorized_file):
    metadata_grant(authorized_file)
    before = authorized_file.read_bytes()
    service = MetadataService()
    result = lookup(authorized_file, service)
    assert result == {
        "schema": "folderhome.google-calendar-identity.v1",
        "requested_calendar_id": "primary",
        "calendar_id": "concrete@example.invalid",
        "provider_id": "google-calendar",
        "provider_revision": "v3",
        "read_only": True,
    }
    assert service.calls == [("GET", "/calendar/v3/calendars/primary", None)]
    assert authorized_file.read_bytes() == before
    assert "synthetic-token" not in json.dumps(result) and str(authorized_file) not in json.dumps(
        result
    )


@pytest.mark.parametrize("gate", [False, 1, "true"])
def test_lookup_rejects_missing_read_gate_before_opening_file(tmp_path, monkeypatch, gate):
    def forbidden(*args, **kwargs):
        pytest.fail("Private file opened without read approval")

    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(api().GoogleCalendarLookupError):
        lookup(tmp_path / "missing.json", MetadataService(), allow_network_read=gate)


def test_event_grant_does_not_authorize_calendar_metadata(authorized_file):
    service = MetadataService()
    with pytest.raises(api().GoogleCalendarLookupError):
        lookup(authorized_file, service)
    assert not service.calls


@pytest.mark.parametrize(
    "response",
    [
        {"kind": "calendar#calendar", "id": "primary"},
        {"kind": "calendar#event", "id": "concrete@example.invalid"},
        {"kind": "calendar#calendar", "id": "x\nprivate"},
        {"kind": "calendar#calendar", "id": "x" * 1025},
    ],
)
def test_invalid_metadata_cannot_become_a_saved_calendar_id(authorized_file, response):
    metadata_grant(authorized_file)
    service = MetadataService(response=response)
    with pytest.raises(api().GoogleCalendarLookupError):
        lookup(authorized_file, service)
    assert len(service.calls) == 1


def test_concrete_target_cannot_be_silently_replaced_by_another_calendar(authorized_file):
    metadata_grant(authorized_file)
    with pytest.raises(api().GoogleCalendarLookupError):
        lookup(authorized_file, MetadataService(), calendar_id="different@example.invalid")


def test_lookup_errors_are_neutral_and_never_retried(authorized_file):
    metadata_grant(authorized_file)
    service = MetadataService(status=403, response={"error": "synthetic-secret"})
    with pytest.raises(api().GoogleCalendarLookupError) as caught:
        lookup(authorized_file, service)
    assert "synthetic-secret" not in str(caught.value)
    assert len(service.calls) == 1


@pytest.mark.parametrize(
    "gate,confirmed,expected", [(False, True, 403), (True, False, 400), (True, True, 200)]
)
def test_setup_lookup_requires_start_gate_and_exact_action(
    authorized_file, tmp_path, monkeypatch, gate, confirmed, expected
):
    from test_setup_app import _app, _headers

    metadata_grant(authorized_file)
    app = _app(tmp_path)
    app.allow_calendar_read = gate
    service = MetadataService()
    monkeypatch.setattr(api(), "GoogleCalendarTransport", lambda: service)
    body = {
        "schema": "folderhome.google-calendar-lookup-request.v1",
        "profile_id": "lukas",
        "credential_file": str(authorized_file),
        "credential_ref": REFERENCE,
        "calendar_id": "primary",
        "confirm": confirmed,
    }
    response = app.handle(
        method="POST",
        target="/api/v1/setup/google-calendar-id",
        headers=_headers(8766),
        body=json.dumps(body).encode(),
        server_port=8766,
    )
    assert response.status_code == expected
    assert len(service.calls) == (1 if expected == 200 else 0)
    assert list(app.config_dir.iterdir()) == []
    if expected == 200:
        assert json.loads(response.content)["calendar_id"] == "concrete@example.invalid"


@pytest.mark.parametrize("gate", [False, True])
def test_calendar_identity_cli_uses_same_separate_read_gate(
    authorized_file, monkeypatch, capsys, gate
):
    from folderhome import cli

    metadata_grant(authorized_file)
    service = MetadataService()
    monkeypatch.setattr(api(), "GoogleCalendarTransport", lambda: service)
    args = [
        "calendar",
        "resolve-id",
        "--credential-file",
        str(authorized_file),
        "--credential-ref",
        REFERENCE,
        "--calendar-id",
        "primary",
        "--json",
    ]
    if gate:
        args.append("--approve-calendar-read")
    assert cli.main(args) == (0 if gate else 2)
    output = capsys.readouterr()
    assert "synthetic-token" not in output.out + output.err
    assert len(service.calls) == int(gate)
    if gate:
        assert json.loads(output.out)["calendar_id"] == "concrete@example.invalid"


@pytest.mark.parametrize(
    "change", ["token", "origin", "profile", "confirm", "extra", "schema", "method"]
)
def test_lookup_endpoint_rejects_invalid_authority_before_credentials(
    authorized_file, tmp_path, monkeypatch, change
):
    from test_setup_app import _app, _headers

    app = _app(tmp_path)
    app.allow_calendar_read = True
    headers = _headers(8766)
    request = {
        "schema": "folderhome.google-calendar-lookup-request.v1",
        "profile_id": "lukas",
        "credential_file": str(authorized_file),
        "credential_ref": REFERENCE,
        "calendar_id": "primary",
        "confirm": True,
    }
    method = "POST"
    if change == "token":
        headers["X-FolderHome-Token"] = "wrong"
    elif change == "origin":
        headers["Origin"] = "https://foreign.invalid"
    elif change == "profile":
        request["profile_id"] = "unknown"
    elif change == "confirm":
        request["confirm"] = 1
    elif change == "extra":
        request["url"] = "https://foreign.invalid"
    elif change == "schema":
        request["schema"] = "folderhome.setup-plan-request.v1"
    else:
        method = "GET"

    def forbidden(*args, **kwargs):
        pytest.fail("Rejected metadata request must not open credentials")

    monkeypatch.setattr(Path, "open", forbidden)
    response = app.handle(
        method=method,
        target="/api/v1/setup/google-calendar-id",
        headers=headers,
        body=json.dumps(request).encode(),
        server_port=8766,
    )
    assert response.status_code in {400, 401, 403, 405}


@pytest.mark.parametrize("calendar_id", ["", "\n", "x" * 1025, None])
def test_invalid_target_does_not_open_private_credentials(tmp_path, monkeypatch, calendar_id):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid calendar ID must fail before credential reads")

    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(api().GoogleCalendarLookupError):
        lookup(tmp_path / "missing.json", MetadataService(), calendar_id=calendar_id)


def test_target_is_path_encoded_not_interpreted_as_url_or_query(authorized_file):
    metadata_grant(authorized_file)
    target = "calendar/with?query#fragment@example.invalid"
    service = MetadataService(response={"kind": "calendar#calendar", "id": target})
    assert lookup(authorized_file, service, calendar_id=target)["calendar_id"] == target
    assert service.calls == [
        ("GET", "/calendar/v3/calendars/calendar%2Fwith%3Fquery%23fragment%40example.invalid", None)
    ]


@pytest.mark.parametrize("gate", [False, True])
def test_setup_cli_propagates_only_its_explicit_calendar_read_gate(tmp_path, gate):
    from folderhome import cli

    args = ["setup", "serve", "--config-dir", str(tmp_path / "config")]
    if gate:
        args.append("--approve-calendar-read")
    app = cli._build_setup_app(cli._build_parser().parse_args(args))
    assert app.state_payload()["google_calendar_read_enabled"] is gate
    assert not app.config_dir.exists()


@pytest.mark.parametrize("profile_id", [[], {}])
def test_setup_lookup_rejects_non_string_profile_without_uncaught_error(
    tmp_path, monkeypatch, profile_id
):
    from test_setup_app import _app, _headers

    app = _app(tmp_path)
    app.allow_calendar_read = True
    request = {
        "schema": "folderhome.google-calendar-lookup-request.v1",
        "profile_id": profile_id,
        "credential_file": str(tmp_path / "must-not-open.json"),
        "credential_ref": REFERENCE,
        "calendar_id": "primary",
        "confirm": True,
    }

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid profile must fail before credential access")

    monkeypatch.setattr(Path, "open", forbidden)
    response = app.handle(
        method="POST",
        target="/api/v1/setup/google-calendar-id",
        headers=_headers(8766),
        body=json.dumps(request).encode(),
        server_port=8766,
    )
    assert response.status_code == 400
    assert isinstance(json.loads(response.content), dict)


@pytest.mark.parametrize(
    "granted_scope", [SCOPE, "https://www.googleapis.com/auth/calendar.events"]
)
def test_metadata_refresh_preserves_scope_gate_and_private_file(
    authorized_file, monkeypatch, granted_scope
):
    credentials_module = importlib.import_module("folderhome.bridges.google_calendar_credentials")
    payload = json.loads(authorized_file.read_text(encoding="utf-8"))
    payload.update(scopes=[SCOPE], expiry="2000-01-01T00:00:00Z")
    authorized_file.write_text(json.dumps(payload), encoding="utf-8")
    before = authorized_file.read_bytes()
    refreshes = []
    closed = []

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "oauth2.googleapis.com" and timeout == 15

        def request(self, method, path, body, headers):
            refreshes.append((method, path))

        def getresponse(self):
            data = json.dumps(
                {
                    "access_token": "synthetic-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": granted_scope,
                }
            ).encode()
            return SimpleNamespace(
                status=200, read=lambda maximum: data[:maximum], getheaders=lambda: []
            )

        def close(self):
            closed.append(True)

    monkeypatch.setattr(credentials_module.http.client, "HTTPSConnection", Connection)
    service = MetadataService()
    if granted_scope == SCOPE:
        assert lookup(authorized_file, service)["calendar_id"] == "concrete@example.invalid"
        assert service.calls == [("GET", "/calendar/v3/calendars/primary", None)]
    else:
        with pytest.raises(api().GoogleCalendarLookupError):
            lookup(authorized_file, service)
        assert not service.calls
    assert refreshes == [("POST", "/token")]
    assert closed == [True]
    assert authorized_file.read_bytes() == before
