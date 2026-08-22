from __future__ import annotations

import json
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
            (tmp_path / "uptoday" / "event.ics")
            if backend is CalendarBackend.UPTODAY_ICS
            else None
        ),
        content_sha256=(
            sha256(b"ics").hexdigest()
            if backend is CalendarBackend.UPTODAY_ICS
            else None
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
    request = load_calendar_connector_request(
        _request_file(tmp_path, account_id="routinika-lukas")
    )
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
