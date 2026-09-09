"""Real gateway/ledger under an in-memory HTTP boundary; no external account."""

from __future__ import annotations

import importlib
from copy import deepcopy
from dataclasses import replace

import pytest

from folderhome.contracts.calendar import CalendarBackend
from folderhome.contracts.calendar_connectors import (
    CalendarConnectorAccount,
    CalendarConnectorEvent,
    CalendarReminderSpec,
)


def api():
    assert importlib.util.find_spec("folderhome.bridges.google_calendar") is not None, (
        "Google gateway must execute and reconcile through a persistent ledger"
    )
    return importlib.import_module("folderhome.bridges.google_calendar")


@pytest.fixture
def account():
    return CalendarConnectorAccount(
        account_id="google-lukas",
        profile_id="lukas",
        backend=CalendarBackend.GOOGLE,
        display_name="Synthetic calendar",
        provider_id="google-calendar",
        provider_revision="v3",
        calendar_id="synthetic@example.invalid",
        credential_ref="connector://google-calendar/lukas",
    )


@pytest.fixture
def event(account):
    return CalendarConnectorEvent(
        event_uid="a" * 64 + "@folderhome.local",
        profile_id="lukas",
        calendar_id=account.calendar_id,
        title="Synthetische Prüfung",
        start="2100-01-01T10:00:00+01:00",
        end="2100-01-01T11:00:00+01:00",
        timezone="Europe/Berlin",
        all_day=False,
        location="Beispiel",
        attendees=(),
        transparency="opaque",
        reminders=(CalendarReminderSpec("popup", 60),),
        source_handoff_action_id="calendar_action_" + "b" * 32,
    )


class CalendarService:
    def __init__(self):
        self.events = {}
        self.calls = []
        self.timeout_after_write = False
        self.timeout_before_write = False
        self.unreadable = False

    def request(self, method, path, *, access_token, payload=None):
        assert access_token == "synthetic-token"
        self.calls.append((method, path, deepcopy(payload)))
        if method == "POST":
            if self.timeout_before_write:
                raise TimeoutError("private transport text")
            self.events[payload["id"]] = {
                **deepcopy(payload),
                "status": "confirmed",
                "etag": '"v1"',
            }
            if self.timeout_after_write:
                raise TimeoutError("private transport text")
            return 200, deepcopy(self.events[payload["id"]])
        assert method == "GET"
        if self.unreadable:
            raise TimeoutError("private readback text")
        value = self.events.get(path.rsplit("/", 1)[-1])
        return (200, deepcopy(value)) if value is not None else (404, {})


def gateway(tmp_path, account, service, *, enabled=True, token_provider=None):
    return api().GoogleCalendarGateway(
        account=account,
        ledger_path=tmp_path / "calendar-ledger.sqlite3",
        token_provider=token_provider or (lambda reference: "synthetic-token"),
        allow_network_write=enabled,
        transport=service,
    )


def test_create_readback_and_restart_never_duplicate_a_calendar_entry(tmp_path, account, event):
    service = CalendarService()
    first = gateway(tmp_path, account, service)
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()
    remote_id = first.create_event(event, idempotency_key="c" * 64)
    second = gateway(tmp_path, account, service)
    assert second.create_event(event, idempotency_key="c" * 64) == remote_id
    assert len(service.events) == 1
    assert sum(method == "POST" for method, _, _ in service.calls) == 1
    posted = next(payload for method, _, payload in service.calls if method == "POST")
    assert posted["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 60}],
    }
    assert "calendar_id" not in posted
    assert "folderhome_event_uid" not in posted
    assert posted["attendees"] == []
    assert "sendUpdates=none" in next(path for method, path, _ in service.calls if method == "POST")
    assert "synthetic%40example.invalid" in service.calls[0][1]
    ledger = (tmp_path / "calendar-ledger.sqlite3").read_bytes()
    assert b"synthetic-token" not in ledger
    assert event.title.encode("utf-8") not in ledger


@pytest.mark.parametrize("enabled", [False, 1, "true"])
def test_no_launch_gate_means_no_token_read_ledger_or_transport(tmp_path, account, event, enabled):
    service = CalendarService()

    def forbidden(reference):
        pytest.fail("Credentials read without separate approval")

    with pytest.raises(api().GoogleCalendarError):
        gateway(tmp_path, account, service, enabled=enabled, token_provider=forbidden).create_event(
            event,
            idempotency_key="c" * 64,
        )
    assert service.calls == []
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()


def test_timeout_after_insert_is_resolved_by_readback_not_second_post(tmp_path, account, event):
    service = CalendarService()
    service.timeout_after_write = True
    remote_id = gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert remote_id in service.events
    assert [method for method, _, _ in service.calls] == ["GET", "POST", "GET"]


def test_unresolved_write_stays_unknown_across_restart_without_retry(tmp_path, account, event):
    service = CalendarService()
    service.timeout_before_write = True
    with pytest.raises(api().GoogleCalendarOutcomeUnknown) as failure:
        gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert "private" not in str(failure.value)
    service.timeout_before_write = False
    with pytest.raises(api().GoogleCalendarOutcomeUnknown):
        gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert sum(method == "POST" for method, _, _ in service.calls) == 1
    assert not service.events


def test_new_approval_does_not_recreate_the_same_document_event(tmp_path, account, event):
    service = CalendarService()
    remote_id = gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert (
        gateway(tmp_path, account, service).create_event(event, idempotency_key="d" * 64)
        == remote_id
    )
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


@pytest.mark.parametrize("change", ["title", "marker", "cancelled", "attendees", "reminders"])
def test_changed_remote_content_is_never_accepted_or_overwritten(tmp_path, account, event, change):
    service = CalendarService()
    remote_id = gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    remote = service.events[remote_id]
    if change == "title":
        remote["summary"] = "External edit"
    elif change == "marker":
        remote["extendedProperties"] = {}
    elif change == "cancelled":
        remote["status"] = "cancelled"
    elif change == "attendees":
        remote["attendees"] = [{"email": "another@example.invalid"}]
    else:
        remote["reminders"]["useDefault"] = True
    with pytest.raises(api().GoogleCalendarOutcomeUnknown):
        gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


@pytest.mark.parametrize("change", ["profile", "calendar", "end", "local_reminder"])
def test_invalid_or_wrong_account_event_is_rejected_before_io(tmp_path, account, event, change):
    changed = {
        "profile": {"profile_id": "hanna"},
        "calendar": {"calendar_id": "foreign"},
        "end": {"end": None},
        "local_reminder": {"reminders": (CalendarReminderSpec("local_notification", 5),)},
    }[change]
    service = CalendarService()
    with pytest.raises(api().GoogleCalendarError):
        gateway(tmp_path, account, service).create_event(
            replace(event, **changed), idempotency_key="c" * 64
        )
    assert not service.calls
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()


@pytest.mark.parametrize("error_type", [ValueError, KeyError, RuntimeError, OSError])
def test_token_resolver_failure_is_redacted_before_any_effect(tmp_path, account, event, error_type):
    service = CalendarService()

    def failed_token(reference):
        raise error_type("private token path and secret")

    with pytest.raises(api().GoogleCalendarError) as failure:
        gateway(tmp_path, account, service, token_provider=failed_token).create_event(
            event,
            idempotency_key="c" * 64,
        )
    assert "secret" not in str(failure.value)
    import traceback

    assert "private token path and secret" not in "".join(traceback.format_exception(failure.value))
    assert not service.calls
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"display_name": "Renamed"},
        {"credential_ref": "connector://google-calendar/rotated"},
        {"account_id": "renamed-account"},
    ],
)
def test_account_metadata_changes_do_not_reset_unknown_write(tmp_path, account, event, change):
    service = CalendarService()
    service.timeout_before_write = True
    with pytest.raises(api().GoogleCalendarOutcomeUnknown):
        gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    service.timeout_before_write = False
    with pytest.raises(api().GoogleCalendarOutcomeUnknown):
        gateway(tmp_path, replace(account, **change), service).create_event(
            event,
            idempotency_key="c" * 64,
        )
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


def test_failed_initial_read_does_not_consume_the_write_attempt(tmp_path, account, event):
    service = CalendarService()
    service.unreadable = True
    with pytest.raises(api().GoogleCalendarError):
        gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert all(method == "GET" for method, _, _ in service.calls)
    service.unreadable = False
    remote_id = gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert remote_id in service.events
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


def test_timezone_offset_must_match_the_declared_zone_before_io(tmp_path, account, event):
    service = CalendarService()
    changed = replace(event, start="2100-07-01T10:00:00+01:00", end="2100-07-01T11:00:00+01:00")
    with pytest.raises(api().GoogleCalendarError):
        gateway(tmp_path, account, service).create_event(changed, idempotency_key="c" * 64)
    assert not service.calls


def test_failed_receipt_commit_is_unknown_and_later_reconciles_without_reinsert(
    tmp_path,
    account,
    event,
    monkeypatch,
):
    service = CalendarService()
    first = gateway(tmp_path, account, service)

    def cannot_confirm(event_id, etag, *, payload_hash):
        raise OSError("private ledger path")

    monkeypatch.setattr(first, "_confirm", cannot_confirm)
    with pytest.raises(api().GoogleCalendarOutcomeUnknown):
        first.create_event(event, idempotency_key="c" * 64)
    remote_id = gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert remote_id in service.events
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


def test_concurrent_gateways_share_one_persistent_write_reservation(tmp_path, account, event):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    service = CalendarService()
    actual_request = service.request
    ready, mutex = Barrier(2), Lock()
    reads = [0]

    def request(method, path, **kwargs):
        with mutex:
            wait = method == "GET" and reads[0] < 2
            if method == "GET":
                reads[0] += 1
        if wait:
            ready.wait(timeout=5)
        return actual_request(method, path, **kwargs)

    service.request = request

    def create(_):
        try:
            return gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
        except api().GoogleCalendarOutcomeUnknown:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert any(value in service.events for value in results if value is not None)
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


@pytest.mark.parametrize("status,raw", [(200, b'{"id":"event"}'), (302, b"private error body")])
def test_transport_pins_google_host_closes_connection_and_never_follows_redirects(
    monkeypatch,
    status,
    raw,
):
    import json

    module = api()
    calls = []

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "www.googleapis.com"
            assert timeout == 15

        def request(self, method, path, *, body, headers):
            calls.append((method, path, body, headers))

        def getresponse(self):
            from types import SimpleNamespace

            return SimpleNamespace(status=status, read=lambda maximum: raw[:maximum])

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    result = module.GoogleCalendarTransport().request(
        "POST",
        "/calendar/v3/calendars/primary/events",
        access_token="synthetic",
        payload={"summary": "Prüfung"},
    )
    assert result == (status, {"id": "event"} if status == 200 else {})
    assert len(calls) == 2 and calls[-1] == "closed"
    assert json.loads(calls[0][2]) == {"summary": "Prüfung"}
    assert calls[0][3]["Authorization"] == "Bearer synthetic"


@pytest.mark.parametrize(
    "raw",
    [b'{"secret":', b"\xff", b"[]", b"x" * 1_048_577],
    ids=["json", "encoding", "array", "oversized"],
)
def test_transport_rejects_invalid_or_oversized_success_without_exposing_body(monkeypatch, raw):
    import traceback
    from types import SimpleNamespace

    module = api()
    closed = []

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            def read(maximum):
                assert maximum == 1_048_577
                return raw[:maximum]

            return SimpleNamespace(status=200, read=read)

        def close(self):
            closed.append(True)

    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    with pytest.raises(module.GoogleCalendarError) as failure:
        module.GoogleCalendarTransport().request(
            "GET", "/calendar/v3/test", access_token="synthetic"
        )
    assert closed == [True]
    assert "UnicodeDecodeError" not in "".join(traceback.format_exception(failure.value))


def test_all_day_event_keeps_exclusive_end_and_explicit_empty_reminders(tmp_path, account, event):
    service = CalendarService()
    changed = replace(
        event, all_day=True, start="2100-01-01", end="2100-01-02", reminders=(), location=None
    )
    remote_id = gateway(tmp_path, account, service).create_event(changed, idempotency_key="c" * 64)
    remote = service.events[remote_id]
    assert remote["start"] == {"date": "2100-01-01"}
    assert remote["end"] == {"date": "2100-01-02"}
    assert remote["reminders"] == {"useDefault": False, "overrides": []}
    assert "location" not in remote


@pytest.mark.parametrize(
    "change", [{"title": "Changed"}, {"event_uid": "d" * 64 + "@folderhome.local"}]
)
def test_reusing_approval_for_other_content_never_causes_another_post(
    tmp_path, account, event, change
):
    service = CalendarService()
    gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    with pytest.raises(api().GoogleCalendarError):
        gateway(tmp_path, account, service).create_event(
            replace(event, **change), idempotency_key="c" * 64
        )
    assert sum(method == "POST" for method, _, _ in service.calls) == 1


def test_remote_read_failure_has_no_private_exception_chain(tmp_path, account, event):
    import traceback

    service = CalendarService()
    service.unreadable = True
    with pytest.raises(api().GoogleCalendarError) as failure:
        gateway(tmp_path, account, service).create_event(event, idempotency_key="c" * 64)
    assert "TimeoutError" not in "".join(traceback.format_exception(failure.value))


def test_primary_alias_requires_resolved_calendar_identity_before_io(tmp_path, account, event):
    service = CalendarService()

    def forbidden(reference):
        pytest.fail("Alias must be rejected before credential resolution")

    with pytest.raises(api().GoogleCalendarError):
        gateway(
            tmp_path, replace(account, calendar_id="primary"), service, token_provider=forbidden
        ).create_event(
            replace(event, calendar_id="primary"),
            idempotency_key="c" * 64,
        )
    assert not service.calls
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()
