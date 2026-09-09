"""Finite UTC monetary entitlement; amounts are integer millionths of one USD.

This accounts for conservative reservations, not AWS billing measurements.
The deployment owner must substantiate the per-forward upper bound separately.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime


@dataclass(frozen=True, slots=True)
class CloudDemoBudget:
    total_microusd: int
    forward_microusd: int
    start_utc: date
    end_utc: date

    def __post_init__(self) -> None:
        for value in (self.total_microusd, self.forward_microusd):
            if type(value) is not int or not 1 <= value <= 1_000_000_000_000:
                raise ValueError("Budget requires positive bounded integer micro-USD.")
        if self.forward_microusd > self.total_microusd:
            raise ValueError("A forward reservation cannot exceed the total budget.")
        if type(self.start_utc) is not date or type(self.end_utc) is not date:
            raise ValueError("Budget window requires UTC calendar dates.")
        if not 1 <= (self.end_utc - self.start_utc).days <= 366:
            raise ValueError("Budget window must span one to 366 UTC days.")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> CloudDemoBudget:
        amounts = []
        for key in ("TOTAL", "FORWARD"):
            raw = environment.get(f"FOLDERHOME_BUDGET_{key}_MICROUSD", "")
            if not isinstance(raw, str) or re.fullmatch(r"[0-9]{1,13}", raw) is None:
                raise ValueError("Budget amounts must be explicit integer micro-USD.")
            amounts.append(int(raw))
        dates = []
        for key in ("START", "END"):
            raw = environment.get(f"FOLDERHOME_BUDGET_{key}_UTC", "")
            if not isinstance(raw, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw) is None:
                raise ValueError("Budget dates must be explicit YYYY-MM-DD UTC dates.")
            dates.append(date.fromisoformat(raw))
        return cls(amounts[0], amounts[1], dates[0], dates[1])

    def accrued_microusd(self, instant: datetime) -> int:
        """Release day one's share at start; remainder becomes available on later days."""
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("Budget clock must be timezone-aware.")
        today = instant.astimezone(UTC).date()
        if not self.start_utc <= today < self.end_utc:
            raise ValueError("Budget window is not active.")
        elapsed_days = (today - self.start_utc).days + 1
        return self.total_microusd * elapsed_days // (self.end_utc - self.start_utc).days
