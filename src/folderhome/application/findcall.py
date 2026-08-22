"""Build and run generic FindCall cascades without real communication."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Protocol

from folderhome.contracts import (
    FindCallAction,
    FindCallAttempt,
    FindCallCandidate,
    FindCallFixtureOutcome,
    FindCallKind,
    FindCallPlan,
    FindCallReport,
    FindCallRequest,
    FindCallStatus,
    FindCallWindow,
)

_PROHIBITED_HEALTH_TERMS = re.compile(
    r"(?:\b(?:notfall|emergency|herzinfarkt|schlaganfall|suizid|diagnose|"
    r"diagnostiziere|akute\s+atemnot)\b|\b112\b)",
    re.IGNORECASE,
)


class FindCallWorkflowError(RuntimeError):
    """Raised when a FindCall plan or fixture execution is unsafe."""


class FindCallDryRunProvider(Protocol):
    """Strictly local provider port used by the phase-18 execution."""

    simulated: bool
    network_used: bool
    phone_calls_placed: bool

    def inquire(
        self,
        action: FindCallAction,
        request: FindCallRequest,
    ) -> FindCallFixtureOutcome: ...


def build_findcall_request(
    *,
    profile_id: str,
    area: str,
    kind: FindCallKind,
    service: str,
    location: str,
    windows: tuple[FindCallWindow, ...],
    max_distance_km: float | None = None,
    max_price_eur: float | None = None,
) -> FindCallRequest:
    """Normalize an administrative-only inquiry and derive its stable ID."""

    if _PROHIBITED_HEALTH_TERMS.search(service):
        raise FindCallWorkflowError(
            "Notfall- oder Diagnoseinhalte sind kein FindCall-Anwendungsfall."
        )
    payload = {
        "profile_id": profile_id,
        "area": area,
        "kind": kind.value,
        "service": service.strip(),
        "location": location.strip(),
        "windows": [window.to_dict() for window in windows],
        "max_distance_km": max_distance_km,
        "max_price_eur": max_price_eur,
        "authority": "inquiry_only",
    }
    return FindCallRequest(
        request_id=f"findcall_request_{_json_hash(payload)}",
        profile_id=profile_id,
        area=area,
        kind=kind,
        service=service.strip(),
        location=location.strip(),
        windows=windows,
        max_distance_km=max_distance_km,
        max_price_eur=max_price_eur,
    )


def build_findcall_plan(
    request: FindCallRequest,
    candidates: tuple[FindCallCandidate, ...],
    *,
    planned_at: str,
) -> FindCallPlan:
    """Build deterministic serial order and visible prefilter decisions."""

    if not candidates:
        raise FindCallWorkflowError("FindCall benötigt mindestens einen Kandidaten.")
    if len({candidate.candidate_id for candidate in candidates}) != len(candidates):
        raise FindCallWorkflowError("FindCall-Kandidaten-IDs müssen eindeutig sein.")
    if len({candidate.phone_e164 for candidate in candidates}) != len(candidates):
        raise FindCallWorkflowError("FindCall-Rufnummern müssen eindeutig sein.")
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.priority,
            candidate.distance_km if candidate.distance_km is not None else float("inf"),
            candidate.candidate_id,
        ),
    )
    actions = []
    for position, candidate in enumerate(ordered, start=1):
        services = {service.casefold() for service in candidate.services}
        if request.service.casefold() not in services:
            status = "filtered"
            reason = "Anbieter bestätigt die angefragte Leistung nicht."
            idempotency_key = None
        elif (
            request.max_distance_km is not None
            and candidate.distance_km is not None
            and candidate.distance_km > request.max_distance_km
        ):
            status = "filtered"
            reason = "Anbieter liegt außerhalb der Entfernungsgrenze."
            idempotency_key = None
        else:
            status = "planned"
            reason = "Lokale Fixture-Anfrage in serieller Kaskade geplant."
            idempotency_key = (
                "findcall_idem_"
                f"{_text_hash(request.request_id, candidate.candidate_id)}"
            )
        action_material = {
            "request_id": request.request_id,
            "candidate_id": candidate.candidate_id,
            "position": position,
            "status": status,
            "idempotency_key": idempotency_key,
        }
        actions.append(
            FindCallAction(
                action_id=f"findcall_action_{_json_hash(action_material)[:32]}",
                candidate=candidate,
                position=position,
                status=status,
                reason=reason,
                idempotency_key=idempotency_key,
            )
        )
    action_tuple = tuple(actions)
    payload = {
        "schema": FindCallPlan.SCHEMA,
        "planned_at": planned_at,
        "request": request.to_dict(),
        "actions": [action.to_dict() for action in action_tuple],
        "pattern_provider": "hungrycall",
        "coordination_plugin": "ringedingeding",
    }
    try:
        return FindCallPlan(
            plan_id=f"findcall_plan_{_json_hash(payload)}",
            planned_at=planned_at,
            request=request,
            actions=action_tuple,
        )
    except ValueError as exc:
        raise FindCallWorkflowError(str(exc)) from exc


def run_findcall_dry_run(
    plan: FindCallPlan,
    *,
    provider: FindCallDryRunProvider,
) -> FindCallReport:
    """Run a serial fixture cascade and stop after the first valid outcome."""

    if not (
        provider.simulated
        and not provider.network_used
        and not provider.phone_calls_placed
    ):
        raise FindCallWorkflowError(
            "FindCall V1 akzeptiert ausschließlich eine strikt lokale Simulation."
        )
    attempts = []
    successful_candidate_id = None
    for action in plan.actions:
        if action.status != "planned":
            continue
        try:
            outcome = provider.inquire(action, plan.request)
        except Exception as exc:
            raise FindCallWorkflowError(f"FindCall-Fixture fehlgeschlagen: {exc}") from exc
        passed, reason = _evaluate(plan.request, outcome)
        attempts.append(
            FindCallAttempt(
                action_id=action.action_id,
                candidate_id=action.candidate.candidate_id,
                candidate_name=action.candidate.name,
                phone_masked=action.candidate.phone_masked,
                status=outcome.status,
                passed=passed,
                rejection_reason=reason,
                offered_window=outcome.offered_window,
                price_known=outcome.price_known,
                price_eur=outcome.price_eur,
                summary=outcome.summary,
            )
        )
        if passed:
            successful_candidate_id = action.candidate.candidate_id
            break
    attempt_tuple = tuple(attempts)
    payload = {
        "plan_id": plan.plan_id,
        "attempts": [attempt.to_dict() for attempt in attempt_tuple],
        "successful_candidate_id": successful_candidate_id,
    }
    return FindCallReport(
        execution_id=f"findcall_exec_{_json_hash(payload)}",
        plan_id=plan.plan_id,
        success=successful_candidate_id is not None,
        attempts=attempt_tuple,
        successful_candidate_id=successful_candidate_id,
    )


def _evaluate(
    request: FindCallRequest,
    outcome: FindCallFixtureOutcome,
) -> tuple[bool, str | None]:
    if outcome.status is not FindCallStatus.COMPLETED:
        return False, f"Anfrage endete mit Status {outcome.status.value}."
    if outcome.commitment_made:
        return False, "Fixture überschreitet inquiry_only durch eine Zusage."
    if not outcome.service_confirmed:
        return False, "Angefragte Leistung wurde nicht bestätigt."
    if not outcome.available:
        return False, "Im erlaubten Zeitraum wurde keine Verfügbarkeit bestätigt."
    if outcome.offered_window is None or not any(
        allowed.contains(outcome.offered_window) for allowed in request.windows
    ):
        return False, "Angebotenes Zeitfenster liegt außerhalb der Vorgabe."
    if request.kind is FindCallKind.QUOTE:
        if not outcome.price_known:
            return False, "Angebot besitzt keinen exakten Preis."
        if (
            request.max_price_eur is not None
            and outcome.price_eur is not None
            and outcome.price_eur > request.max_price_eur
        ):
            return False, "Angebot überschreitet die freigegebene Preisgrenze."
    return True, None


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()


def _text_hash(*values: str) -> str:
    return sha256("\0".join(values).encode("utf-8")).hexdigest()
