"""Provider-neutral contracts for simulated sequential provider inquiries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

_ACTION_ID = re.compile(r"findcall_action_[0-9a-f]{32}")
_CANDIDATE_ID = re.compile(r"findcall_candidate_[0-9a-f]{64}")
_EXECUTION_ID = re.compile(r"findcall_exec_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"findcall_plan_[0-9a-f]{64}")
_REQUEST_ID = re.compile(r"findcall_request_[0-9a-f]{64}")
_E164 = re.compile(r"\+[1-9][0-9]{7,14}")


class FindCallKind(StrEnum):
    """Supported administrative provider inquiry types."""

    APPOINTMENT = "appointment"
    QUOTE = "quote"


class FindCallStatus(StrEnum):
    """Terminal statuses retained from the calling-provider boundary."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_ANSWER = "NO_ANSWER"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    VOICEMAIL = "VOICEMAIL"
    BUSY = "BUSY"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class FindCallWindow:
    """One timezone-aware acceptable start/end interval."""

    start_at: str
    end_at: str

    def __post_init__(self) -> None:
        start = _aware_datetime(self.start_at, "start_at")
        end = _aware_datetime(self.end_at, "end_at")
        if end <= start:
            raise ValueError("FindCall-Zeitfenster muss vor seinem Ende beginnen.")

    def contains(self, offered: FindCallWindow) -> bool:
        return (
            _aware_datetime(offered.start_at, "start_at")
            >= _aware_datetime(self.start_at, "start_at")
            and _aware_datetime(offered.end_at, "end_at")
            <= _aware_datetime(self.end_at, "end_at")
        )

    def to_dict(self) -> dict[str, str]:
        return {"start_at": self.start_at, "end_at": self.end_at}


@dataclass(frozen=True, slots=True)
class FindCallRequest:
    """Administrative inquiry with explicit time, distance, and price authority."""

    request_id: str
    profile_id: str
    area: str
    kind: FindCallKind
    service: str
    location: str
    windows: tuple[FindCallWindow, ...]
    max_distance_km: float | None
    max_price_eur: float | None
    authority: str = "inquiry_only"

    SCHEMA = "folderhome.findcall-request.v1"

    def __post_init__(self) -> None:
        if _REQUEST_ID.fullmatch(self.request_id) is None:
            raise ValueError("request_id muss findcall_request_<sha256> verwenden.")
        if not all((self.profile_id, self.area, self.service, self.location)):
            raise ValueError("FindCall-Auftrag benötigt Profil, Bereich, Leistung und Ort.")
        if not self.windows:
            raise ValueError("FindCall-Auftrag benötigt mindestens ein Zeitfenster.")
        if self.max_distance_km is not None and self.max_distance_km < 0:
            raise ValueError("max_distance_km darf nicht negativ sein.")
        if self.max_price_eur is not None and self.max_price_eur < 0:
            raise ValueError("max_price_eur darf nicht negativ sein.")
        if self.authority != "inquiry_only":
            raise ValueError("FindCall V1 erlaubt ausschließlich inquiry_only.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "kind": self.kind.value,
            "service": self.service,
            "location": self.location,
            "windows": [window.to_dict() for window in self.windows],
            "max_distance_km": self.max_distance_km,
            "max_price_eur": self.max_price_eur,
            "authority": self.authority,
            "medical_scope": "administrative_only",
            "emergency_supported": False,
        }


@dataclass(frozen=True, slots=True)
class FindCallCandidate:
    """One local provider candidate; public serialization always masks its phone."""

    candidate_id: str
    name: str
    phone_e164: str
    services: tuple[str, ...]
    distance_km: float | None = None
    priority: int = 0

    def __post_init__(self) -> None:
        if _CANDIDATE_ID.fullmatch(self.candidate_id) is None:
            raise ValueError("candidate_id muss findcall_candidate_<sha256> verwenden.")
        if not self.name or not self.services or any(not service for service in self.services):
            raise ValueError("FindCall-Kandidat benötigt Name und Leistungen.")
        if _E164.fullmatch(self.phone_e164) is None:
            raise ValueError("FindCall-Rufnummer muss E.164 verwenden.")
        if self.distance_km is not None and self.distance_km < 0:
            raise ValueError("distance_km darf nicht negativ sein.")

    @property
    def phone_masked(self) -> str:
        return _mask_phone(self.phone_e164)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "phone_masked": self.phone_masked,
            "services": list(self.services),
            "distance_km": self.distance_km,
            "priority": self.priority,
        }


@dataclass(frozen=True, slots=True)
class FindCallAction:
    """One ordered simulated inquiry or a visibly filtered candidate."""

    action_id: str
    candidate: FindCallCandidate
    position: int
    status: str
    reason: str
    idempotency_key: str | None

    def __post_init__(self) -> None:
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("action_id muss findcall_action_<hex> verwenden.")
        if self.position < 1:
            raise ValueError("FindCall-Aktionsposition muss positiv sein.")
        if self.status not in {"planned", "filtered", "blocked"}:
            raise ValueError("FindCall-Aktionsstatus ist ungültig.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "candidate": self.candidate.to_dict(),
            "position": self.position,
            "status": self.status,
            "reason": self.reason,
            "idempotency_key": self.idempotency_key,
            "side_effects": [],
            "simulated": True,
        }


@dataclass(frozen=True, slots=True)
class FindCallPlan:
    """Content-minimized dry-run cascade with no live connector invocation."""

    plan_id: str
    planned_at: str
    request: FindCallRequest
    actions: tuple[FindCallAction, ...]
    pattern_provider: str = "hungrycall"
    coordination_plugin: str = "ringedingeding"

    SCHEMA = "folderhome.findcall-plan.v1"

    def __post_init__(self) -> None:
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("plan_id muss findcall_plan_<sha256> verwenden.")
        _aware_datetime(self.planned_at, "planned_at")

    @property
    def connector_invoked(self) -> bool:
        return False

    @property
    def phone_calls_placed(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "planned_at": self.planned_at,
            "request": self.request.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "pattern_provider": self.pattern_provider,
            "coordination_plugin": self.coordination_plugin,
            "connector_invoked": False,
            "network_used": False,
            "phone_calls_placed": False,
            "live_enabled": False,
        }


@dataclass(frozen=True, slots=True)
class FindCallFixtureOutcome:
    """One explicit local fixture outcome; never evidence of a real offer."""

    status: FindCallStatus
    service_confirmed: bool
    available: bool
    offered_window: FindCallWindow | None
    price_known: bool
    price_eur: float | None
    commitment_made: bool
    summary: str

    def __post_init__(self) -> None:
        if self.price_eur is not None and self.price_eur < 0:
            raise ValueError("Fixture-Preis darf nicht negativ sein.")
        if self.price_known != (self.price_eur is not None):
            raise ValueError("price_known und price_eur müssen zusammenpassen.")


@dataclass(frozen=True, slots=True)
class FindCallAttempt:
    """Evaluated simulated attempt with retained terminal status."""

    action_id: str
    candidate_id: str
    candidate_name: str
    phone_masked: str
    status: FindCallStatus
    passed: bool
    rejection_reason: str | None
    offered_window: FindCallWindow | None
    price_known: bool
    price_eur: float | None
    summary: str

    def __post_init__(self) -> None:
        if _ACTION_ID.fullmatch(self.action_id) is None:
            raise ValueError("FindCall-Versuch besitzt eine ungültige action_id.")
        if _CANDIDATE_ID.fullmatch(self.candidate_id) is None:
            raise ValueError("FindCall-Versuch besitzt eine ungültige candidate_id.")
        if _E164.search(self.phone_masked) is not None or "•" not in self.phone_masked:
            raise ValueError("FindCall-Versuch benötigt eine maskierte Rufnummer.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "phone_masked": self.phone_masked,
            "status": self.status.value,
            "passed": self.passed,
            "rejection_reason": self.rejection_reason,
            "offered_window": (
                self.offered_window.to_dict() if self.offered_window else None
            ),
            "price_known": self.price_known,
            "price_eur": self.price_eur,
            "summary": _mask_phones_in_text(self.summary),
            "simulated": True,
        }


@dataclass(frozen=True, slots=True)
class FindCallReport:
    """Result of a strictly local, serial, early-stop fixture cascade."""

    execution_id: str
    plan_id: str
    success: bool
    attempts: tuple[FindCallAttempt, ...]
    successful_candidate_id: str | None
    simulated: bool = True
    network_used: bool = False
    phone_calls_placed: bool = False

    SCHEMA = "folderhome.findcall-report.v1"

    def __post_init__(self) -> None:
        if _EXECUTION_ID.fullmatch(self.execution_id) is None:
            raise ValueError("execution_id muss findcall_exec_<sha256> verwenden.")
        if not self.simulated or self.network_used or self.phone_calls_placed:
            raise ValueError("FindCall V1 akzeptiert ausschließlich lokale Simulation.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "success": self.success,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "successful_candidate_id": self.successful_candidate_id,
            "simulated": True,
            "network_used": False,
            "phone_calls_placed": False,
            "commitment_made": False,
        }


@dataclass(frozen=True, slots=True)
class CallPluginProbeResult:
    """Read-only evidence that a pinned call plugin exposes a local dry-run path."""

    plugin_id: str
    source_revision: str
    provider_root: Path
    pattern: str
    runtime_imported: bool
    dry_run_available: bool
    live_invoked: bool = False
    network_used: bool = False
    phone_calls_placed: bool = False

    SCHEMA = "folderhome.call-plugin-probe.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_root", self.provider_root.resolve())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plugin_id": self.plugin_id,
            "source_revision": self.source_revision,
            "provider_root": str(self.provider_root),
            "pattern": self.pattern,
            "runtime_imported": self.runtime_imported,
            "dry_run_available": self.dry_run_available,
            "live_invoked": False,
            "network_used": False,
            "phone_calls_placed": False,
        }


def _aware_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} ist kein ISO-Zeitpunkt: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _mask_phone(value: str) -> str:
    prefix_length = 3 if value.startswith("+49") else min(2, len(value) - 4)
    return f"{value[:prefix_length]}••••{value[-4:]}"


def _mask_phones_in_text(value: str) -> str:
    return _E164.sub(lambda match: _mask_phone(match.group(0)), value)
