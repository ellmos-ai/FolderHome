from __future__ import annotations

import json

import pytest

from folderhome.application.findcall import (
    FindCallWorkflowError,
    build_findcall_plan,
    build_findcall_request,
    run_findcall_dry_run,
)
from folderhome.capabilities.findcall import SyntheticFindCallProvider
from folderhome.contracts import (
    FindCallCandidate,
    FindCallFixtureOutcome,
    FindCallKind,
    FindCallStatus,
    FindCallWindow,
)


def _window(day: int) -> FindCallWindow:
    return FindCallWindow(
        start_at=f"2026-09-{day:02d}T09:00:00+02:00",
        end_at=f"2026-09-{day:02d}T12:00:00+02:00",
    )


def _candidate(
    suffix: str,
    *,
    service: str,
    phone: str,
    priority: int = 0,
    distance_km: float = 5.0,
) -> FindCallCandidate:
    return FindCallCandidate(
        candidate_id=f"findcall_candidate_{suffix * 64}",
        name=f"Anbieter {suffix.upper()}",
        phone_e164=phone,
        services=(service,),
        distance_km=distance_km,
        priority=priority,
    )


def test_findcall_plan_filters_and_orders_without_exposing_phone_numbers() -> None:
    request = build_findcall_request(
        profile_id="lukas",
        area="gesundheit",
        kind=FindCallKind.APPOINTMENT,
        service="Dermatologie",
        location="Beispielstadt",
        windows=(_window(14),),
        max_distance_km=20.0,
    )
    candidates = (
        _candidate("a", service="Dermatologie", phone="+4915111111111", priority=1),
        _candidate("b", service="Dermatologie", phone="+4915222222222", priority=5),
        _candidate(
            "c",
            service="Orthopädie",
            phone="+4915333333333",
            distance_km=2.0,
        ),
        _candidate(
            "d",
            service="Dermatologie",
            phone="+4915444444444",
            distance_km=40.0,
        ),
    )

    plan = build_findcall_plan(
        request,
        candidates,
        planned_at="2026-08-22T01:00:00+02:00",
    )

    assert [action.candidate.candidate_id[-64] for action in plan.actions] == [
        "b",
        "a",
        "c",
        "d",
    ]
    assert [action.status for action in plan.actions] == [
        "planned",
        "planned",
        "filtered",
        "filtered",
    ]
    payload = json.dumps(plan.to_dict(), ensure_ascii=False)
    assert "+4915111111111" not in payload
    assert "+4915222222222" not in payload
    assert "+49••••1111" in payload
    assert plan.connector_invoked is False
    assert plan.phone_calls_placed is False


def test_appointment_dry_run_is_serial_and_stops_at_first_matching_fixture() -> None:
    request = build_findcall_request(
        profile_id="lukas",
        area="gesundheit",
        kind=FindCallKind.APPOINTMENT,
        service="Dermatologie",
        location="Beispielstadt",
        windows=(_window(14), _window(15)),
        max_distance_km=20.0,
    )
    candidates = (
        _candidate("a", service="Dermatologie", phone="+4915111111111", priority=3),
        _candidate("b", service="Dermatologie", phone="+4915222222222", priority=2),
        _candidate("c", service="Dermatologie", phone="+4915333333333", priority=1),
    )
    plan = build_findcall_plan(
        request,
        candidates,
        planned_at="2026-08-22T01:00:00+02:00",
    )
    provider = SyntheticFindCallProvider(
        {
            candidates[0].candidate_id: FindCallFixtureOutcome(
                status=FindCallStatus.NO_ANSWER,
                service_confirmed=False,
                available=False,
                offered_window=None,
                price_known=False,
                price_eur=None,
                commitment_made=False,
                summary="Nicht erreicht.",
            ),
            candidates[1].candidate_id: FindCallFixtureOutcome(
                status=FindCallStatus.COMPLETED,
                service_confirmed=True,
                available=True,
                offered_window=FindCallWindow(
                    start_at="2026-09-15T10:00:00+02:00",
                    end_at="2026-09-15T10:30:00+02:00",
                ),
                price_known=False,
                price_eur=None,
                commitment_made=False,
                summary="Synthetischer Termin ist verfügbar.",
            ),
            candidates[2].candidate_id: FindCallFixtureOutcome(
                status=FindCallStatus.COMPLETED,
                service_confirmed=True,
                available=True,
                offered_window=_window(14),
                price_known=False,
                price_eur=None,
                commitment_made=False,
                summary="Darf wegen Early Stop nicht ausgewertet werden.",
            ),
        }
    )

    report = run_findcall_dry_run(plan, provider=provider)

    assert report.success is True
    assert report.simulated is True
    assert report.network_used is False
    assert report.phone_calls_placed is False
    assert len(report.attempts) == 2
    assert report.attempts[0].status is FindCallStatus.NO_ANSWER
    assert report.attempts[1].passed is True
    assert report.successful_candidate_id == candidates[1].candidate_id
    assert provider.requested_candidate_ids == [
        candidates[0].candidate_id,
        candidates[1].candidate_id,
    ]


def test_quote_dry_run_rejects_vague_and_over_budget_results() -> None:
    request = build_findcall_request(
        profile_id="lukas",
        area="mobilität",
        kind=FindCallKind.QUOTE,
        service="Bremsenprüfung Hyundai i10",
        location="Beispielstadt",
        windows=(_window(16),),
        max_price_eur=180.0,
    )
    candidates = tuple(
        _candidate(
            suffix,
            service="Bremsenprüfung Hyundai i10",
            phone=phone,
            priority=priority,
        )
        for suffix, phone, priority in (
            ("a", "+4915111111111", 3),
            ("b", "+4915222222222", 2),
            ("c", "+4915333333333", 1),
        )
    )
    plan = build_findcall_plan(
        request,
        candidates,
        planned_at="2026-08-22T01:00:00+02:00",
    )
    common = {
        "status": FindCallStatus.COMPLETED,
        "service_confirmed": True,
        "available": True,
        "offered_window": FindCallWindow(
            start_at="2026-09-16T10:00:00+02:00",
            end_at="2026-09-16T11:00:00+02:00",
        ),
        "commitment_made": False,
    }
    provider = SyntheticFindCallProvider(
        {
            candidates[0].candidate_id: FindCallFixtureOutcome(
                **common,
                price_known=False,
                price_eur=None,
                summary="Preis ist ungefähr und nicht verbindlich.",
            ),
            candidates[1].candidate_id: FindCallFixtureOutcome(
                **common,
                price_known=True,
                price_eur=240.0,
                summary="Synthetisches Angebot über der Grenze.",
            ),
            candidates[2].candidate_id: FindCallFixtureOutcome(
                **common,
                price_known=True,
                price_eur=175.0,
                summary="Synthetisches Angebot innerhalb der Grenze.",
            ),
        }
    )

    report = run_findcall_dry_run(plan, provider=provider)

    assert report.success is True
    assert [attempt.rejection_reason for attempt in report.attempts] == [
        "Angebot besitzt keinen exakten Preis.",
        "Angebot überschreitet die freigegebene Preisgrenze.",
        None,
    ]
    assert report.successful_candidate_id == candidates[2].candidate_id


def test_findcall_rejects_emergency_or_diagnostic_request_text() -> None:
    with pytest.raises(FindCallWorkflowError, match="Notfall"):
        build_findcall_request(
            profile_id="lukas",
            area="gesundheit",
            kind=FindCallKind.APPOINTMENT,
            service="Notfall wegen Herzinfarkt",
            location="Beispielstadt",
            windows=(_window(14),),
        )


def test_findcall_no_match_retains_every_terminal_status_and_reason() -> None:
    request = build_findcall_request(
        profile_id="lukas",
        area="gesundheit",
        kind=FindCallKind.APPOINTMENT,
        service="Dermatologie",
        location="Beispielstadt",
        windows=(_window(14),),
    )
    candidates = (
        _candidate("a", service="Dermatologie", phone="+4915111111111", priority=2),
        _candidate("b", service="Dermatologie", phone="+4915222222222", priority=1),
    )
    plan = build_findcall_plan(
        request,
        candidates,
        planned_at="2026-08-22T01:00:00+02:00",
    )
    provider = SyntheticFindCallProvider(
        {
            candidates[0].candidate_id: FindCallFixtureOutcome(
                status=FindCallStatus.DECLINED,
                service_confirmed=False,
                available=False,
                offered_window=None,
                price_known=False,
                price_eur=None,
                commitment_made=False,
                summary="Anfrage abgelehnt.",
            ),
            candidates[1].candidate_id: FindCallFixtureOutcome(
                status=FindCallStatus.COMPLETED,
                service_confirmed=True,
                available=True,
                offered_window=FindCallWindow(
                    start_at="2026-09-14T13:00:00+02:00",
                    end_at="2026-09-14T13:30:00+02:00",
                ),
                price_known=False,
                price_eur=None,
                commitment_made=False,
                summary="Nur außerhalb des Fensters verfügbar.",
            ),
        }
    )

    report = run_findcall_dry_run(plan, provider=provider)

    assert report.success is False
    assert report.successful_candidate_id is None
    assert [attempt.status for attempt in report.attempts] == [
        FindCallStatus.DECLINED,
        FindCallStatus.COMPLETED,
    ]
    assert report.attempts[1].rejection_reason == (
        "Angebotenes Zeitfenster liegt außerhalb der Vorgabe."
    )


def test_findcall_refuses_provider_that_is_not_strictly_local_simulation() -> None:
    request = build_findcall_request(
        profile_id="lukas",
        area="gesundheit",
        kind=FindCallKind.APPOINTMENT,
        service="Dermatologie",
        location="Beispielstadt",
        windows=(_window(14),),
    )
    plan = build_findcall_plan(
        request,
        (_candidate("a", service="Dermatologie", phone="+4915111111111"),),
        planned_at="2026-08-22T01:00:00+02:00",
    )

    class UnsafeProvider:
        simulated = False
        network_used = True
        phone_calls_placed = True

        def inquire(self, action, request):  # pragma: no cover - must not be called
            raise AssertionError("unsafe provider was called")

    with pytest.raises(FindCallWorkflowError, match="lokale Simulation"):
        run_findcall_dry_run(plan, provider=UnsafeProvider())
