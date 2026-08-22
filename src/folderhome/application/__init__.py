"""FolderHome application services."""

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

from folderhome.contracts import (
    ActionEvent,
    DecisionCard,
    DecisionStatus,
    EvidenceRef,
    GateDecision,
    ProviderProvenance,
    RunReport,
    RunStatus,
    SideEffect,
    UndoDescriptor,
)


def run_synthetic(scenario: str, *, run_id: str) -> RunReport:
    """Execute one side-effect-free synthetic scenario."""

    if scenario == "blocked":
        started_at = _utc_now()
        action = ActionEvent(
            action_id=f"{run_id}:0001",
            sequence=1,
            name="synthetic.phone_call",
            status=RunStatus.BLOCKED,
            side_effects=(SideEffect.PHONE_CALL,),
            gate=GateDecision(
                required=True,
                granted=False,
                reason="human approval missing",
            ),
            evidence=(),
            undo=UndoDescriptor(supported=False, action=None),
            message="Aktion wurde vor der Nebenwirkung blockiert.",
        )
        decision = DecisionCard(
            decision_id=f"{run_id}:decision:0001",
            title="Echten Anruf starten?",
            question="Darf FolderHome den Telefon-Connector verwenden?",
            status=DecisionStatus.PENDING,
            options=("approve_once", "reject"),
            selected=None,
        )
        return RunReport(
            run_id=run_id,
            started_at=started_at,
            finished_at=_utc_now(),
            status=RunStatus.BLOCKED,
            plugin_id="folderhome.synthetic",
            capability_id="synthetic.phone_call",
            dry_run=True,
            provider=_synthetic_provider(),
            actions=(action,),
            decisions=(decision,),
        )
    if scenario == "failure":
        started_at = _utc_now()
        action = ActionEvent(
            action_id=f"{run_id}:0001",
            sequence=1,
            name="synthetic.inspect",
            status=RunStatus.FAILED,
            side_effects=(),
            gate=GateDecision(required=False, granted=True, reason="no side effect"),
            evidence=(),
            undo=UndoDescriptor(supported=False, action=None),
            message="synthetic failure",
        )
        return RunReport(
            run_id=run_id,
            started_at=started_at,
            finished_at=_utc_now(),
            status=RunStatus.FAILED,
            plugin_id="folderhome.synthetic",
            capability_id="synthetic.inspect",
            dry_run=True,
            provider=_synthetic_provider(),
            actions=(action,),
            decisions=(),
        )
    if scenario != "success":
        raise ValueError(f"Unsupported synthetic scenario: {scenario}")

    started_at = _utc_now()
    evidence_uri = "fixture://success"
    action = ActionEvent(
        action_id=f"{run_id}:0001",
        sequence=1,
        name="synthetic.inspect",
        status=RunStatus.EXECUTED,
        side_effects=(),
        gate=GateDecision(required=False, granted=True, reason="no side effect"),
        evidence=(
            EvidenceRef(
                kind="synthetic.fixture",
                uri=evidence_uri,
                sha256=sha256(evidence_uri.encode("utf-8")).hexdigest(),
            ),
        ),
        undo=UndoDescriptor(supported=False, action=None),
        message="Synthetische Prüfung abgeschlossen.",
    )
    return RunReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=_utc_now(),
        status=RunStatus.EXECUTED,
        plugin_id="folderhome.synthetic",
        capability_id="synthetic.inspect",
        dry_run=True,
        provider=_synthetic_provider(),
        actions=(action,),
        decisions=(),
    )


def resume_synthetic(previous: RunReport, scenario: str) -> RunReport:
    """Resume a synthetic run while preserving identity and action history."""

    continuation = run_synthetic(scenario, run_id=previous.run_id)
    next_sequence = max((action.sequence for action in previous.actions), default=0) + 1
    continued_actions = tuple(
        replace(
            action,
            sequence=next_sequence + offset,
            action_id=f"{previous.run_id}:{next_sequence + offset:04d}",
        )
        for offset, action in enumerate(continuation.actions)
    )
    return replace(
        continuation,
        started_at=previous.started_at,
        actions=previous.actions + continued_actions,
        decisions=previous.decisions + continuation.decisions,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _synthetic_provider() -> ProviderProvenance:
    return ProviderProvenance(
        plugin_id="folderhome.synthetic",
        version="0.1.0",
        source_repository="local://folderhome",
        source_revision="working-tree",
    )
