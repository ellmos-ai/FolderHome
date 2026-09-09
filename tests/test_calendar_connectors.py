from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.calendar_connectors import (
    CalendarConnectorError,
    build_calendar_connector_plan,
    execute_calendar_connector_plan,
    load_calendar_connector_accounts,
    load_calendar_connector_request,
)
from folderhome.capabilities.calendar_connector_gateway import (
    SyntheticCalendarConnectorGateway,
)
from folderhome.contracts import (
    CalendarBackend,
    CalendarCandidate,
    CalendarConfiguration,
    CalendarConnectorApproval,
    CalendarConnectorOperation,
    CalendarEvidence,
    CalendarHandoffAction,
    CalendarHandoffPlan,
    DocumentCalendarAnalysis,
    FolderCalendarAnalysis,
    FolderCalendarItem,
)

REPO_ROOT = Path(__file__).parents[1]
UPTODAY_REVISION = "7582ca87e17e458bb99a7379d2c54003c15415a4"
ROUTINIKA_BUNDLE_SHA256 = "3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2"


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _accounts_file(tmp_path: Path, *, embedded_token: bool = False) -> Path:
    google: dict[str, object] = {
        "account_id": "google-lukas",
        "profile_id": "lukas",
        "backend": "google",
        "display_name": "Google Kalender",
        "provider_id": "skill:google-calendar",
        "provider_revision": "google-calendar-skill@1.2.5",
        "calendar_id": "primary",
        "credential_ref": "connector://google-calendar/default",
    }
    if embedded_token:
        google["access_token"] = "darf-nicht-hier-stehen"
    return _write_json(
        tmp_path / "calendar-accounts.json",
        {
            "schema": "folderhome.calendar-connector-accounts.v1",
            "accounts": [
                {
                    "account_id": "uptoday-lukas",
                    "profile_id": "lukas",
                    "backend": "uptoday_ics",
                    "display_name": "UpToday ICS",
                    "provider_id": "module:uptoday-ics",
                    "provider_revision": UPTODAY_REVISION,
                    "calendar_id": "uptoday-local",
                    "credential_ref": None,
                },
                {
                    "account_id": "routinika-lukas",
                    "profile_id": "lukas",
                    "backend": "routinika",
                    "display_name": "Routinika",
                    "provider_id": "bundle:routinika",
                    "provider_revision": ROUTINIKA_BUNDLE_SHA256,
                    "calendar_id": "routinika-local",
                    "credential_ref": None,
                },
                google,
            ],
        },
    )


def _request_file(
    tmp_path: Path,
    *,
    account_id: str = "google-lukas",
    operations: list[str] | None = None,
) -> Path:
    requested_operations = operations or ["create", "remind"]
    return _write_json(
        tmp_path / f"request-{account_id}.json",
        {
            "schema": "folderhome.calendar-connector-request.v1",
            "request_id": f"connect-{account_id}",
            "profile_id": "lukas",
            "account_id": account_id,
            "operations": requested_operations,
            "reminders": (
                [{"method": "popup", "minutes_before": 60}]
                if "remind" in requested_operations
                else []
            ),
        },
    )


def _handoff_plan(tmp_path: Path, backend: CalendarBackend) -> CalendarHandoffPlan:
    source_path = REPO_ROOT / "examples" / "documents" / "calendar" / "Kontrolltermin.txt"
    source_sha = sha256(source_path.read_bytes()).hexdigest()
    candidate = CalendarCandidate(
        candidate_id=f"calendar_candidate_{sha256(b'candidate').hexdigest()}",
        event_uid=f"{sha256(b'event').hexdigest()}@folderhome.local",
        profile_id="lukas",
        area="gesundheit",
        title="Kontrolltermin",
        event_date="2026-09-14",
        start_time="10:30",
        end_time="11:00",
        timezone="Europe/Berlin",
        timezone_basis="explicit_label",
        location="Praxis Beispiel",
        source_document_id=f"doc_{source_sha}",
        source_sha256=source_sha,
        source_path=source_path,
        evidence=(CalendarEvidence("title", 1, "Termin"),),
    )
    analysis = DocumentCalendarAnalysis(
        document_id=candidate.source_document_id,
        source_path=source_path,
        source_sha256=source_sha,
        status="candidate",
        candidate=candidate,
        issues=(),
    )
    folder_analysis = FolderCalendarAnalysis(
        source_root=source_path.parent,
        profile_id="lukas",
        area="gesundheit",
        recursive=True,
        items=(
            FolderCalendarItem(
                relative_path=source_path.name,
                status="candidate",
                analysis=analysis,
                message="Synthetischer Terminkandidat.",
            ),
        ),
    )
    action = CalendarHandoffAction(
        action_id=f"calendar_action_{sha256(backend.value.encode()).hexdigest()[:32]}",
        candidate=candidate,
        backend=backend,
        status="planned" if backend is CalendarBackend.UPTODAY_ICS else "blocked",
        side_effect="new_ics_file" if backend is CalendarBackend.UPTODAY_ICS else "none",
        target_path=(
            (tmp_path / "uptoday" / "event.ics") if backend is CalendarBackend.UPTODAY_ICS else None
        ),
        content_sha256=(
            sha256(b"ics").hexdigest() if backend is CalendarBackend.UPTODAY_ICS else None
        ),
        message="Synthetischer Phase-17-Handoff.",
    )
    return CalendarHandoffPlan(
        plan_id=f"calendar_plan_{sha256((backend.value + 'plan').encode()).hexdigest()}",
        planned_at="2026-08-22T04:00:00+02:00",
        calendar_revision=f"calendar_revision_{sha256(b'empty').hexdigest()}",
        backend=backend,
        backend_source="profile_rule:calendar.backend",
        source_rule_ids=("rule_lukas_calendar",),
        configuration=CalendarConfiguration(
            config_path=tmp_path / "calendar-config.json",
            default_backend=CalendarBackend.UPTODAY_ICS,
            default_timezone="Europe/Berlin",
            uptoday_ics_directory=tmp_path / "uptoday",
        ),
        analysis=folder_analysis,
        actions=(action,),
    )


def test_connector_accounts_are_provider_neutral_and_reject_embedded_tokens(
    tmp_path: Path,
) -> None:
    accounts = load_calendar_connector_accounts(_accounts_file(tmp_path))
    google = next(item for item in accounts if item.backend is CalendarBackend.GOOGLE)
    assert google.calendar_id == "primary"
    assert google.credential_ref == "connector://google-calendar/default"
    assert "access_token" not in google.to_dict()

    with pytest.raises(CalendarConnectorError, match="unbekannte Felder"):
        load_calendar_connector_accounts(_accounts_file(tmp_path, embedded_token=True))


def test_google_plan_uses_explicit_calendar_solo_attendees_and_popup_reminder(
    tmp_path: Path,
) -> None:
    accounts = load_calendar_connector_accounts(_accounts_file(tmp_path))
    account = next(item for item in accounts if item.backend is CalendarBackend.GOOGLE)
    request = load_calendar_connector_request(_request_file(tmp_path))
    plan = build_calendar_connector_plan(
        _handoff_plan(tmp_path, CalendarBackend.GOOGLE),
        request=request,
        account=account,
        provider_ready=True,
    )

    assert plan.status == "review_required"
    assert plan.backend_source == "profile_rule:calendar.backend"
    assert plan.source_rule_ids == ("rule_lukas_calendar",)
    assert {item.operation for item in plan.actions} == {
        CalendarConnectorOperation.CREATE,
        CalendarConnectorOperation.REMIND,
    }
    assert all(item.status == "review_required" for item in plan.actions)
    payload = plan.events[0].google_create_payload()
    assert payload["calendar_id"] == "primary"
    assert payload["attendees"] == []
    assert payload["transparency"] == "opaque"
    assert payload["start"]["dateTime"].endswith("+02:00")
    assert payload["end"]["dateTime"].endswith("+02:00")
    assert payload["reminders"] == {
        "use_default": False,
        "overrides": [{"method": "popup", "minutes": 60}],
    }
    assert plan.connector_invoked is False
    assert plan.live_calendar_written is False


def test_uptoday_create_reuses_existing_ics_handoff_without_live_sync(
    tmp_path: Path,
) -> None:
    accounts = load_calendar_connector_accounts(_accounts_file(tmp_path))
    account = next(item for item in accounts if item.backend is CalendarBackend.UPTODAY_ICS)
    request = load_calendar_connector_request(
        _request_file(
            tmp_path,
            account_id="uptoday-lukas",
            operations=["create"],
        )
    )
    plan = build_calendar_connector_plan(
        _handoff_plan(tmp_path, CalendarBackend.UPTODAY_ICS),
        request=request,
        account=account,
        provider_ready=True,
    )

    assert plan.status == "ready"
    assert plan.route.provider_revision == UPTODAY_REVISION
    assert plan.actions[0].status == "delegated"
    assert plan.actions[0].delegated_to_existing_handoff is True
    assert plan.actions[0].connector_invoked is False
    assert plan.live_calendar_written is False


def test_routinika_is_hash_bound_but_blocked_without_live_contract(tmp_path: Path) -> None:
    accounts = load_calendar_connector_accounts(_accounts_file(tmp_path))
    account = next(item for item in accounts if item.backend is CalendarBackend.ROUTINIKA)
    request = load_calendar_connector_request(_request_file(tmp_path, account_id="routinika-lukas"))
    plan = build_calendar_connector_plan(
        _handoff_plan(tmp_path, CalendarBackend.ROUTINIKA),
        request=request,
        account=account,
        provider_ready=False,
    )

    assert plan.status == "blocked"
    assert plan.route.provider_revision == ROUTINIKA_BUNDLE_SHA256
    assert plan.route.live_supported is False
    assert all(item.status == "blocked" for item in plan.actions)


def test_update_and_delete_remain_separate_blocked_operations(tmp_path: Path) -> None:
    accounts = load_calendar_connector_accounts(_accounts_file(tmp_path))
    account = next(item for item in accounts if item.backend is CalendarBackend.GOOGLE)
    request = load_calendar_connector_request(
        _request_file(tmp_path, operations=["update", "delete"])
    )
    plan = build_calendar_connector_plan(
        _handoff_plan(tmp_path, CalendarBackend.GOOGLE),
        request=request,
        account=account,
        provider_ready=True,
    )

    assert {item.operation.value for item in plan.actions} == {"update", "delete"}
    assert all(item.status == "blocked" for item in plan.actions)
    assert all("bestehende Provider-Ereignisreferenz" in item.reason for item in plan.actions)


def test_synthetic_connector_requires_exact_operations_and_never_writes_live(
    tmp_path: Path,
) -> None:
    account = next(
        item
        for item in load_calendar_connector_accounts(_accounts_file(tmp_path))
        if item.backend is CalendarBackend.GOOGLE
    )
    request = load_calendar_connector_request(_request_file(tmp_path))
    plan = build_calendar_connector_plan(
        _handoff_plan(tmp_path, CalendarBackend.GOOGLE),
        request=request,
        account=account,
        provider_ready=True,
        synthetic_override=True,
    )
    approval = CalendarConnectorApproval(
        approval_id="calendar-synthetic-once",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        action_ids=tuple(item.action_id for item in plan.actions),
        allowed_operations=(
            CalendarConnectorOperation.CREATE,
            CalendarConnectorOperation.REMIND,
        ),
        approved_at="2026-08-22T04:10:00+02:00",
        allow_network_write=False,
    )
    gateway = SyntheticCalendarConnectorGateway()

    report = execute_calendar_connector_plan(
        plan,
        approval=approval,
        gateway=gateway,
    )

    assert report.status == "simulated"
    assert report.network_invoked is False
    assert report.live_calendar_written is False
    assert len(report.event_references) == 1
    assert report.event_references[0].provider_event_id.startswith("synthetic-event-")
    assert gateway.create_count == 1

    with pytest.raises(CalendarConnectorError, match="bereits verwendet"):
        execute_calendar_connector_plan(plan, approval=approval, gateway=gateway)
    assert gateway.create_count == 1


def test_network_calendar_gateway_is_blocked_before_invocation(tmp_path: Path) -> None:
    account = next(
        item
        for item in load_calendar_connector_accounts(_accounts_file(tmp_path))
        if item.backend is CalendarBackend.GOOGLE
    )
    request = load_calendar_connector_request(_request_file(tmp_path))
    plan = build_calendar_connector_plan(
        _handoff_plan(tmp_path, CalendarBackend.GOOGLE),
        request=request,
        account=account,
        provider_ready=True,
        synthetic_override=True,
    )

    class NetworkProbeGateway:
        provider_id = "folderhome.synthetic-calendar"
        provider_revision = None
        network_required = True
        simulated = False

        def __init__(self) -> None:
            self.create_count = 0

        def create_event(self, event, *, idempotency_key):
            self.create_count += 1
            raise AssertionError("darf nicht aufgerufen werden")

    gateway = NetworkProbeGateway()
    approval = CalendarConnectorApproval(
        approval_id="calendar-network-denied",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        action_ids=tuple(item.action_id for item in plan.actions),
        allowed_operations=(
            CalendarConnectorOperation.CREATE,
            CalendarConnectorOperation.REMIND,
        ),
        approved_at="2026-08-22T04:15:00+02:00",
        allow_network_write=False,
    )

    with pytest.raises(CalendarConnectorError, match="Netzwerk-Kalenderfreigabe"):
        execute_calendar_connector_plan(plan, approval=approval, gateway=gateway)
    assert gateway.create_count == 0


def _synthetic_plan_and_approval(tmp_path: Path, *, multiple: bool = False):
    account = next(
        item
        for item in load_calendar_connector_accounts(_accounts_file(tmp_path))
        if item.backend is CalendarBackend.GOOGLE
    )
    handoff = _handoff_plan(tmp_path, CalendarBackend.GOOGLE)
    if multiple:
        second = replace(
            handoff.actions[0],
            action_id="calendar_action_" + "b" * 32,
            candidate=replace(
                handoff.actions[0].candidate,
                event_uid="b" * 64 + "@folderhome.local",
                title="Zweiter Termin",
            ),
        )
        handoff = replace(handoff, actions=(*handoff.actions, second))
    plan = build_calendar_connector_plan(
        handoff,
        request=load_calendar_connector_request(_request_file(tmp_path)),
        account=account,
        provider_ready=True,
        synthetic_override=True,
    )
    approval = CalendarConnectorApproval(
        approval_id="calendar-integrity",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        action_ids=tuple(item.action_id for item in plan.actions),
        allowed_operations=(CalendarConnectorOperation.CREATE, CalendarConnectorOperation.REMIND),
        approved_at="2026-09-09T03:00:00+02:00",
        allow_network_write=False,
    )
    return plan, approval


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile_id", "other-profile"),
        ("account_id", "other-account"),
        ("backend", CalendarBackend.ROUTINIKA),
        ("backend_source", "other-source"),
        ("source_rule_ids", ("other-rule",)),
        ("handoff_plan_id", "calendar_plan_" + "a" * 64),
    ],
)
def test_connector_rejects_changed_plan_metadata_before_effect(tmp_path, field, value):
    plan, approval = _synthetic_plan_and_approval(tmp_path)
    changed = replace(plan, **{field: value})
    gateway = SyntheticCalendarConnectorGateway()
    with pytest.raises(CalendarConnectorError, match="Inhalt|Hash"):
        execute_calendar_connector_plan(changed, approval=approval, gateway=gateway)
    assert gateway.create_count == 0
    # Rejection must not consume the unchanged proposal's idempotency key.
    report = execute_calendar_connector_plan(plan, approval=approval, gateway=gateway)
    assert report.status == "simulated"
    assert gateway.create_count == 1


def test_connector_stops_when_plan_changes_during_first_provider_call(tmp_path):
    plan, approval = _synthetic_plan_and_approval(tmp_path, multiple=True)

    class MutatingGateway(SyntheticCalendarConnectorGateway):
        def create_event(self, event, *, idempotency_key):
            result = super().create_event(event, idempotency_key=idempotency_key)
            object.__setattr__(plan, "account_id", "different-account")
            return result

    gateway = MutatingGateway()
    with pytest.raises(CalendarConnectorError, match="Inhalt|Hash"):
        execute_calendar_connector_plan(plan, approval=approval, gateway=gateway)
    assert gateway.create_count == 1


def test_connector_does_not_report_success_after_gateway_effect_mode_changes(tmp_path):
    plan, approval = _synthetic_plan_and_approval(tmp_path)

    class MutatingGateway(SyntheticCalendarConnectorGateway):
        def create_event(self, event, *, idempotency_key):
            result = super().create_event(event, idempotency_key=idempotency_key)
            self.simulated = False
            return result

    gateway = MutatingGateway()
    with pytest.raises(CalendarConnectorError, match="Gateway"):
        execute_calendar_connector_plan(plan, approval=approval, gateway=gateway)
    assert gateway.create_count == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Anderer Termin"),
        ("calendar_id", "different-calendar"),
        ("profile_id", "other-profile"),
        ("start", "2026-09-14T15:00:00+02:00"),
        ("location", "Anderer Ort"),
        ("reminders", ()),
    ],
)
def test_connector_rejects_changed_event_before_effect(tmp_path, field, value):
    plan, approval = _synthetic_plan_and_approval(tmp_path)
    changed = replace(plan, events=(replace(plan.events[0], **{field: value}),))
    gateway = SyntheticCalendarConnectorGateway()
    with pytest.raises(CalendarConnectorError, match="Inhalt|Hash"):
        execute_calendar_connector_plan(changed, approval=approval, gateway=gateway)
    assert gateway.create_count == 0


def test_connector_rejects_changed_route_before_effect(tmp_path):
    plan, approval = _synthetic_plan_and_approval(tmp_path)
    changed = replace(plan, route=replace(plan.route, live_supported=True))
    gateway = SyntheticCalendarConnectorGateway()
    with pytest.raises(CalendarConnectorError, match="Inhalt|Hash"):
        execute_calendar_connector_plan(changed, approval=approval, gateway=gateway)
    assert gateway.create_count == 0


@pytest.mark.parametrize("network_required", [False, True])
def test_synthetic_plan_cannot_be_promoted_to_live_gateway(tmp_path, network_required):
    plan, approval = _synthetic_plan_and_approval(tmp_path)

    class LiveProbe(SyntheticCalendarConnectorGateway):
        simulated = False

    gateway = LiveProbe()
    gateway.network_required = network_required
    with pytest.raises(CalendarConnectorError, match="Gateway|synthetisch"):
        execute_calendar_connector_plan(
            plan, approval=replace(approval, allow_network_write=True), gateway=gateway
        )
    assert gateway.create_count == 0


def test_connector_binds_handoff_evidence_not_only_its_supplied_id(tmp_path):
    account = load_calendar_connector_accounts(_accounts_file(tmp_path))[-1]
    request = load_calendar_connector_request(_request_file(tmp_path))
    handoff = _handoff_plan(tmp_path, CalendarBackend.GOOGLE)
    changed_action = replace(
        handoff.actions[0],
        candidate=replace(handoff.actions[0].candidate, source_sha256="a" * 64),
    )
    changed_handoff = replace(handoff, actions=(changed_action,))
    original = build_calendar_connector_plan(
        handoff, account=account, request=request, provider_ready=True, synthetic_override=True
    )
    changed = build_calendar_connector_plan(
        changed_handoff,
        account=account,
        request=request,
        provider_ready=True,
        synthetic_override=True,
    )
    assert original.plan_sha256 != changed.plan_sha256


def test_connector_rejects_gateway_mutation_of_filtered_event_payload(tmp_path):
    plan, approval = _synthetic_plan_and_approval(tmp_path)
    create = next(a for a in plan.actions if a.operation is CalendarConnectorOperation.CREATE)
    approval = replace(
        approval,
        action_ids=(create.action_id,),
        allowed_operations=(CalendarConnectorOperation.CREATE,),
    )

    class PayloadMutatingGateway(SyntheticCalendarConnectorGateway):
        def create_event(self, event, *, idempotency_key):
            assert event.reminders == ()
            result = super().create_event(event, idempotency_key=idempotency_key)
            object.__setattr__(event, "calendar_id", "other-calendar")
            return result

    gateway = PayloadMutatingGateway()
    with pytest.raises(CalendarConnectorError, match="Inhalt|Payload"):
        execute_calendar_connector_plan(plan, approval=approval, gateway=gateway)
    assert gateway.create_count == 1
