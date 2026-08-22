"""Reusable strictly local fixture provider for generic FindCall cascades."""

from __future__ import annotations

from folderhome.contracts import (
    FindCallAction,
    FindCallFixtureOutcome,
    FindCallRequest,
)


class SyntheticFindCallProvider:
    """Return only caller-supplied fixture outcomes without network access."""

    simulated = True
    network_used = False
    phone_calls_placed = False

    def __init__(self, outcomes: dict[str, FindCallFixtureOutcome]) -> None:
        self._outcomes = dict(outcomes)
        self.requested_candidate_ids: list[str] = []

    def inquire(
        self,
        action: FindCallAction,
        request: FindCallRequest,
    ) -> FindCallFixtureOutcome:
        """Resolve one explicit fixture and record deterministic call order."""

        del request
        candidate_id = action.candidate.candidate_id
        self.requested_candidate_ids.append(candidate_id)
        try:
            return self._outcomes[candidate_id]
        except KeyError as exc:
            raise KeyError(
                f"Synthetisches FindCall-Ergebnis fehlt für {candidate_id}."
            ) from exc
