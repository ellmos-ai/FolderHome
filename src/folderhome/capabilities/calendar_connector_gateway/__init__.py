"""Provider-neutral calendar connector seam with a deterministic fixture gateway."""

from __future__ import annotations

from folderhome.contracts.calendar_connectors import CalendarConnectorEvent


class CalendarConnectorGatewayError(RuntimeError):
    """Raised when a calendar connector would violate its execution contract."""


class SyntheticCalendarConnectorGateway:
    """No-network gateway used only for local acceptance."""

    provider_id = "folderhome.synthetic-calendar"
    provider_revision = None
    network_required = False
    simulated = True

    def __init__(self) -> None:
        self.create_count = 0
        self._used_idempotency_keys: set[str] = set()

    def create_event(
        self,
        event: CalendarConnectorEvent,
        *,
        idempotency_key: str,
    ) -> str:
        if idempotency_key in self._used_idempotency_keys:
            raise CalendarConnectorGatewayError(
                "Kalenderconnector-Idempotenzschlüssel wurde bereits verwendet."
            )
        self._used_idempotency_keys.add(idempotency_key)
        self.create_count += 1
        return f"synthetic-event-{event.event_uid.split('@', 1)[0][:24]}"
