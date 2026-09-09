"""Conditional mutations with real SQLite and a synthetic HTTP boundary."""

from copy import deepcopy
from dataclasses import replace

import pytest
from test_google_calendar_gateway import CalendarService, gateway
from test_google_calendar_gateway import account as account
from test_google_calendar_gateway import event as event

from folderhome.bridges.google_calendar import GoogleCalendarError, GoogleCalendarOutcomeUnknown


def merge_patch(current, patch):
    for key, value in patch.items():
        if value is None:
            current.pop(key, None)
        elif isinstance(value, dict):
            merge_patch(current.setdefault(key, {}), value)
        else:
            current[key] = deepcopy(value)


class MutationService(CalendarService):
    def __init__(self):
        super().__init__()
        self.mutations = []
        self.conflict = False
        self.mutation_timeout_before = False
        self.mutation_timeout_after = False
        self.fail_readback = False
        self.after_fields = {}

    def request(self, method, path, *, access_token, payload=None, if_match=None):
        if method not in {"PATCH", "DELETE"}:
            if method == "GET" and self.fail_readback and self.mutations:
                raise TimeoutError("private read error")
            return super().request(method, path, access_token=access_token, payload=payload)
        assert access_token == "synthetic-token"
        self.mutations.append((method, path, deepcopy(payload), if_match))
        event_id = path.split("?", 1)[0].rsplit("/", 1)[-1]
        current = self.events[event_id]
        if self.conflict or current["etag"] != if_match:
            return 412, {}
        if self.mutation_timeout_before:
            raise TimeoutError("private mutation error")
        if method == "DELETE":
            assert payload is None
            del self.events[event_id]
        else:
            merge_patch(current, payload)
            current["etag"] = '"v2"'
            current.update(self.after_fields)
        if self.mutation_timeout_after:
            raise TimeoutError("private mutation error")
        return (204, {}) if method == "DELETE" else (200, deepcopy(current))


def created(tmp_path, account, event):
    service = MutationService()
    instance = gateway(tmp_path, account, service)
    event_id = instance.create_event(event, idempotency_key="c" * 64)
    return service, instance, event_id


def mutate(instance, event, operation):
    if operation == "update":
        return instance.update_event(
            replace(event, title="Geändert", location=None),
            previous_event=event,
            expected_etag='"v1"',
            idempotency_key="d" * 64,
        )
    return instance.delete_event(event, expected_etag='"v1"', idempotency_key="d" * 64)


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_conditional_mutation_and_restart_never_repeat_writes(tmp_path, account, event, operation):
    service, instance, event_id = created(tmp_path, account, event)
    service.events[event_id]["description"] = "Preserve unrelated fields"
    result = mutate(instance, event, operation)
    repeated = mutate(gateway(tmp_path, account, service), event, operation)
    assert repeated == result
    assert result["provider_event_id"] == event_id
    assert result["status"] == ("updated" if operation == "update" else "absent")
    assert len(service.mutations) == 1
    assert service.mutations[0][3] == '"v1"'
    assert "sendUpdates=none" in service.mutations[0][1]
    if operation == "update":
        assert service.events[event_id]["summary"] == "Geändert"
        assert service.events[event_id]["description"] == "Preserve unrelated fields"
        assert "location" not in service.events[event_id]
        assert result["etag"] == '"v2"'
    else:
        assert event_id not in service.events
        assert result["etag"] is None


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_disabled_mutation_gate_does_not_resolve_credentials(tmp_path, account, event, operation):
    def forbidden(*args):
        pytest.fail("No credentials without mutation approval")

    instance = gateway(
        tmp_path, account, MutationService(), enabled=False, token_provider=forbidden
    )
    with pytest.raises(GoogleCalendarError):
        mutate(instance, event, operation)
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_changed_remote_version_is_never_overwritten(tmp_path, account, event, operation):
    service, instance, event_id = created(tmp_path, account, event)
    service.events[event_id]["etag"] = '"manual"'
    with pytest.raises(GoogleCalendarError):
        mutate(instance, event, operation)
    assert not service.mutations


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_lost_write_response_is_reconciled_read_only(tmp_path, account, event, operation):
    service, instance, event_id = created(tmp_path, account, event)
    service.mutation_timeout_after = True
    result = mutate(instance, event, operation)
    assert result["status"] == ("updated" if operation == "update" else "absent")
    assert result["provider_event_id"] == event_id
    assert len(service.mutations) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_uncertain_attempt_is_not_repeated_after_restart(tmp_path, account, event, operation):
    service, instance, _ = created(tmp_path, account, event)
    service.mutation_timeout_before = True
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        mutate(instance, event, operation)
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        mutate(gateway(tmp_path, account, service), event, operation)
    assert len(service.mutations) == 1


@pytest.mark.parametrize(
    "method,status,raw", [("PATCH", 200, b'{"id":"event"}'), ("DELETE", 204, b"")]
)
def test_real_transport_sends_if_match_and_accepts_empty_delete_response(
    monkeypatch, method, status, raw
):
    from types import SimpleNamespace

    from folderhome.bridges import google_calendar

    calls = []
    closed = []

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "www.googleapis.com" and timeout == 15

        def request(self, verb, path, *, body, headers):
            calls.append((verb, path, body, headers))

        def getresponse(self):
            return SimpleNamespace(status=status, read=lambda maximum: raw[:maximum])

        def close(self):
            closed.append(True)

    monkeypatch.setattr(google_calendar.http.client, "HTTPSConnection", Connection)
    result = google_calendar.GoogleCalendarTransport().request(
        method,
        "/calendar/v3/calendars/own/events/event?sendUpdates=none",
        access_token="synthetic",
        payload=None if method == "DELETE" else {"summary": "Changed"},
        if_match='"v1"',
    )
    assert result == (status, {} if method == "DELETE" else {"id": "event"})
    assert calls[0][3]["If-Match"] == '"v1"'
    assert closed == [True]


@pytest.mark.parametrize("etag", ["*", 'W/"weak"', "", '"bad\r\nheader"', '"' + "x" * 511 + '"'])
def test_bad_if_match_is_rejected_before_connection(monkeypatch, etag):
    from folderhome.bridges import google_calendar

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid conditional headers must fail before network")

    monkeypatch.setattr(google_calendar.http.client, "HTTPSConnection", forbidden)
    with pytest.raises(GoogleCalendarError):
        google_calendar.GoogleCalendarTransport().request(
            "DELETE",
            "/calendar/v3/test",
            access_token="synthetic",
            if_match=etag,
        )


@pytest.mark.parametrize(
    "fields",
    [
        {"recurringEventId": "series-parent"},
        {"eventType": "outOfOffice"},
        {"attendeesOmitted": True},
    ],
)
def test_unsafe_post_write_representation_stays_unknown(tmp_path, account, event, fields):
    service, instance, _ = created(tmp_path, account, event)
    service.after_fields = fields
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        mutate(instance, event, "update")
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        mutate(gateway(tmp_path, account, service), event, "update")
    assert len(service.mutations) == 1


def test_replayed_operation_key_is_bound_and_cannot_authorize_a_later_deletion(
    tmp_path, account, event
):
    service, instance, _ = created(tmp_path, account, event)
    changed = replace(event, title="Geändert", location=None)
    mutate(instance, event, "update")
    instance.update_event(
        changed, previous_event=event, expected_etag='"v1"', idempotency_key="e" * 64
    )
    with pytest.raises(GoogleCalendarError):
        instance.delete_event(changed, expected_etag='"v2"', idempotency_key="e" * 64)
    assert len(service.mutations) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_server_precondition_conflict_is_not_unknown_or_retried(
    tmp_path, account, event, operation
):
    from folderhome.bridges.google_calendar_mutations import GoogleCalendarVersionConflict

    service, instance, _ = created(tmp_path, account, event)
    service.conflict = True
    for _ in range(2):
        with pytest.raises(GoogleCalendarVersionConflict):
            mutate(instance, event, operation)
    assert len(service.mutations) == 1


def test_update_switches_time_representation_and_preserves_extra_private_properties(
    tmp_path, account, event
):
    service, instance, event_id = created(tmp_path, account, event)
    service.events[event_id]["extendedProperties"]["private"]["unrelated"] = "retain"
    changed = replace(event, all_day=True, start="2100-01-02", end="2100-01-03")
    instance.update_event(
        changed, previous_event=event, expected_etag='"v1"', idempotency_key="d" * 64
    )
    assert service.events[event_id]["start"] == {"date": "2100-01-02"}
    assert service.events[event_id]["end"] == {"date": "2100-01-03"}
    assert service.events[event_id]["extendedProperties"]["private"]["unrelated"] == "retain"


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_missing_ledger_cannot_adopt_an_arbitrary_remote_event(tmp_path, account, event, operation):
    def forbidden(*args):
        pytest.fail("Missing own reference must block before token access")

    service = MutationService()
    instance = gateway(tmp_path, account, service, token_provider=forbidden)
    with pytest.raises(GoogleCalendarError):
        mutate(instance, event, operation)
    assert not service.calls and not service.mutations
    assert not (tmp_path / "calendar-ledger.sqlite3").exists()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_old_create_confirmation_cannot_rewind_a_newer_mutation(
    tmp_path, account, event, monkeypatch, operation
):
    import sqlite3
    from contextlib import closing

    service, creator, event_id = created(tmp_path, account, event)
    original_reserve = creator._reserve

    def reserve_then_mutate(*args):
        result = original_reserve(*args)
        mutate(gateway(tmp_path, account, service), event, operation)
        return result

    monkeypatch.setattr(creator, "_reserve", reserve_then_mutate)
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        creator.create_event(event, idempotency_key="c" * 64)
    with closing(sqlite3.connect(tmp_path / "calendar-ledger.sqlite3")) as connection:
        row = connection.execute(
            "SELECT status,etag FROM calendar_creations WHERE event_id=?", (event_id,)
        ).fetchone()
    assert row == (("confirmed", '"v2"') if operation == "update" else ("deleted", None))
    assert len(service.mutations) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_concurrent_mutations_reserve_only_one_write(tmp_path, account, event, operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    service, _, _ = created(tmp_path, account, event)
    original = service.request
    barrier, lock = Barrier(2), Lock()
    initial_reads = 0

    def simultaneous_reads(method, path, **kwargs):
        nonlocal initial_reads
        result = original(method, path, **kwargs)
        synchronize = False
        if method == "GET":
            with lock:
                initial_reads += 1
                synchronize = initial_reads <= 2
        if synchronize:
            barrier.wait(timeout=5)
        return result

    service.request = simultaneous_reads

    def run():
        try:
            return mutate(gateway(tmp_path, account, service), event, operation)
        except GoogleCalendarOutcomeUnknown:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert any(result is not None for result in results)
    assert len(service.mutations) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_unreadable_after_effect_can_resume_only_with_get(tmp_path, account, event, operation):
    service, instance, _ = created(tmp_path, account, event)
    service.fail_readback = True
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        mutate(instance, event, operation)
    service.fail_readback = False
    result = mutate(gateway(tmp_path, account, service), event, operation)
    assert result["status"] == ("updated" if operation == "update" else "absent")
    assert len(service.mutations) == 1


def test_changed_payload_cannot_reuse_reserved_version_after_timeout(tmp_path, account, event):
    service, instance, _ = created(tmp_path, account, event)
    service.mutation_timeout_before = True
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        mutate(instance, event, "update")
    service.mutation_timeout_before = False
    with pytest.raises(GoogleCalendarError):
        gateway(tmp_path, replace(account, account_id="renamed-account"), service).update_event(
            replace(event, title="Different target data"),
            previous_event=event,
            expected_etag='"v1"',
            idempotency_key="f" * 64,
        )
    assert len(service.mutations) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"profile_id": "hanna"},
        {"calendar_id": "another@example.invalid"},
        {"event_uid": "b" * 64 + "@folderhome.local"},
    ],
)
def test_replacement_cannot_change_identity_before_token_access(tmp_path, account, event, change):
    service, _, _ = created(tmp_path, account, event)

    def forbidden(*args):
        pytest.fail("Identity change must fail before resolving credentials")

    with pytest.raises(GoogleCalendarError):
        gateway(tmp_path, account, service, token_provider=forbidden).update_event(
            replace(event, title="Changed", **change),
            previous_event=event,
            expected_etag='"v1"',
            idempotency_key="d" * 64,
        )
    assert not service.mutations


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_failed_local_receipt_remains_unknown_then_reconciles(
    tmp_path, account, event, monkeypatch, operation
):
    from folderhome.bridges import google_calendar_mutations

    service, instance, _ = created(tmp_path, account, event)
    original = google_calendar_mutations._finish

    def broken(*args):
        raise OSError("private receipt failure")

    monkeypatch.setattr(google_calendar_mutations, "_finish", broken)
    with pytest.raises(GoogleCalendarOutcomeUnknown) as failure:
        mutate(instance, event, operation)
    assert "private receipt failure" not in str(failure.value)
    monkeypatch.setattr(google_calendar_mutations, "_finish", original)
    assert mutate(instance, event, operation)["status"] in {"updated", "absent"}
    assert len(service.mutations) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_gateway_and_real_transport_share_the_conditional_http_contract(
    tmp_path, account, event, monkeypatch, operation
):
    import json
    from types import SimpleNamespace

    from folderhome.bridges import google_calendar

    service = MutationService()
    opened, closed = [], []

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "www.googleapis.com" and timeout == 15
            opened.append(self)

        def request(self, method, path, *, body, headers):
            assert headers["Authorization"] == "Bearer synthetic-token"
            self.result = service.request(
                method,
                path,
                access_token="synthetic-token",
                payload=None if body is None else json.loads(body),
                if_match=headers.get("If-Match"),
            )

        def getresponse(self):
            status, payload = self.result
            raw = b"" if status == 204 else json.dumps(payload).encode()
            return SimpleNamespace(status=status, read=lambda maximum: raw[:maximum])

        def close(self):
            closed.append(self)

    monkeypatch.setattr(google_calendar.http.client, "HTTPSConnection", Connection)
    instance = gateway(tmp_path, account, google_calendar.GoogleCalendarTransport())
    event_id = instance.create_event(event, idempotency_key="c" * 64)
    assert mutate(instance, event, operation)["provider_event_id"] == event_id
    assert opened == closed
    assert len(opened) == 6  # creation GET/POST/GET, mutation GET/PATCH-or-DELETE/GET
    assert len(service.mutations) == 1


def test_deleted_event_is_not_recreated_by_old_create_approval(tmp_path, account, event):
    service, instance, event_id = created(tmp_path, account, event)
    mutate(instance, event, "delete")
    with pytest.raises(GoogleCalendarOutcomeUnknown):
        instance.create_event(event, idempotency_key="c" * 64)
    assert event_id not in service.events
    assert sum(method == "POST" for method, _, _ in service.calls) == 1
