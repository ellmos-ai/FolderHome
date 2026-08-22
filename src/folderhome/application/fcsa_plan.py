"""Application service for audited FCSA dry-run plans."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from folderhome.bridges.fcsa import FcsaBridgeError, FcsaDryRunResult
from folderhome.contracts import (
    ActionEvent,
    DecisionCard,
    DecisionStatus,
    EvidenceRef,
    GateDecision,
    PluginDescriptor,
    ProviderProvenance,
    RunReport,
    RunStatus,
    SideEffect,
    UndoDescriptor,
)

CAPABILITY_ID = "documents.collect_sort"


class FcsaPlanProvider(Protocol):
    """Small port implemented by the pinned provider bridge."""

    def plan(self, config_dir: Path) -> FcsaDryRunResult: ...


def run_fcsa_plan(
    config_dir: Path,
    *,
    run_id: str,
    plugin: PluginDescriptor,
    bridge: FcsaPlanProvider,
) -> RunReport:
    """Execute one FCSA dry-run and translate it into the public audit contract."""

    started_at = _utc_now()
    provider = _provider(plugin)
    try:
        _validate_capability(plugin)
        result = bridge.plan(config_dir)
    except FcsaBridgeError as exc:
        return _failure_report(
            run_id=run_id,
            started_at=started_at,
            provider=provider,
            message=f"FCSA-Dry-Run fehlgeschlagen: {_display_text(str(exc))}",
        )

    actions: list[ActionEvent] = []
    sequence = 1
    has_provider_error = False
    mutating_plan_count = 0
    for path_plan in result.paths:
        scan_ref = _scan_ref(path_plan.scan_path)
        for relative_path in path_plan.skipped_locked:
            actions.append(
                _action(
                    run_id=run_id,
                    sequence=sequence,
                    name="fcsa.inspect_locked",
                    status=RunStatus.SKIPPED,
                    message=f"{relative_path}: gesperrt oder nicht lesbar; übersprungen.",
                    evidence=_evidence(
                        result.settings_fingerprint,
                        scan_ref,
                        relative_path,
                        "locked",
                        {},
                    ),
                )
            )
            sequence += 1
        if path_plan.unchanged_count:
            actions.append(
                _action(
                    run_id=run_id,
                    sequence=sequence,
                    name="fcsa.unchanged",
                    status=RunStatus.SKIPPED,
                    message=(
                        f"{path_plan.unchanged_count} bereits bekannte Datei(en) im "
                        "Verarbeitungsstand unverändert."
                    ),
                    evidence=_evidence(
                        result.settings_fingerprint,
                        scan_ref,
                        "unchanged",
                        "summary",
                        {"count": path_plan.unchanged_count},
                    ),
                )
            )
            sequence += 1
        for file_plan in path_plan.files:
            has_provider_error = has_provider_error or file_plan.had_error
            if not file_plan.steps:
                actions.append(
                    _action(
                        run_id=run_id,
                        sequence=sequence,
                        name="fcsa.inspect",
                        status=(RunStatus.FAILED if file_plan.had_error else RunStatus.EXECUTED),
                        message=(
                            f"{file_plan.relative_path} → {file_plan.category_id}: "
                            "keine Folgeaktion geplant."
                        ),
                        evidence=_evidence(
                            result.settings_fingerprint,
                            scan_ref,
                            file_plan.relative_path,
                            "inspect",
                            {"category_id": file_plan.category_id},
                        ),
                    )
                )
                sequence += 1
                continue
            for step in file_plan.steps:
                detail = _display_text(step.detail)
                mutating_plan_count += int(step.would_mutate_fs)
                status = RunStatus.FAILED if file_plan.had_error else (
                    RunStatus.PLANNED if step.would_mutate_fs else RunStatus.EXECUTED
                )
                actions.append(
                    _action(
                        run_id=run_id,
                        sequence=sequence,
                        name=f"fcsa.{step.action}",
                        status=status,
                        message=(
                            f"{file_plan.relative_path} → {file_plan.category_id}: {detail}"
                        ),
                        evidence=_evidence(
                            result.settings_fingerprint,
                            scan_ref,
                            file_plan.relative_path,
                            step.action,
                            {
                                "category_id": file_plan.category_id,
                                "detail": detail,
                                "would_mutate_fs": step.would_mutate_fs,
                            },
                        ),
                        would_mutate_fs=step.would_mutate_fs,
                    )
                )
                sequence += 1
    if not actions:
        actions.append(
            _action(
                run_id=run_id,
                sequence=1,
                name="fcsa.inspect",
                status=RunStatus.EXECUTED,
                message="FCSA-Dry-Run abgeschlossen; keine Dateien zu planen.",
                evidence=_evidence(
                    result.settings_fingerprint,
                    "none",
                    "empty",
                    "inspect",
                    {},
                ),
            )
        )

    decisions: tuple[DecisionCard, ...] = ()
    if mutating_plan_count:
        decisions = (
            DecisionCard(
                decision_id=f"{run_id}:decision:0001",
                title="Sortierplan später ausführen?",
                question=(
                    f"Der Dry-Run enthält {mutating_plan_count} geplante "
                    "Dateisystemaktion(en). Eine Live-Ausführung bleibt gesperrt, bis sie "
                    "separat implementiert und freigegeben wurde."
                ),
                status=DecisionStatus.PENDING,
                options=("review_only", "reject"),
                selected=None,
            ),
        )
    return RunReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=_utc_now(),
        status=RunStatus.FAILED if has_provider_error else RunStatus.EXECUTED,
        plugin_id=plugin.plugin_id,
        capability_id=CAPABILITY_ID,
        dry_run=True,
        provider=provider,
        actions=tuple(actions),
        decisions=decisions,
    )


def _validate_capability(plugin: PluginDescriptor) -> None:
    capability = next(
        (item for item in plugin.capabilities if item.capability_id == CAPABILITY_ID),
        None,
    )
    if capability is None or not capability.dry_run_supported or not capability.gate_required:
        raise FcsaBridgeError(
            f"Manifest autorisiert keinen abgesicherten Dry-Run für {CAPABILITY_ID}."
        )
    if plugin.live_enabled:
        raise FcsaBridgeError("Die Phase-2-Bridge akzeptiert keinen live aktivierten Provider.")


def _failure_report(
    *,
    run_id: str,
    started_at: str,
    provider: ProviderProvenance,
    message: str,
) -> RunReport:
    return RunReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=_utc_now(),
        status=RunStatus.FAILED,
        plugin_id=provider.plugin_id,
        capability_id=CAPABILITY_ID,
        dry_run=True,
        provider=provider,
        actions=(
            _action(
                run_id=run_id,
                sequence=1,
                name="fcsa.inspect_plan",
                status=RunStatus.FAILED,
                message=message,
            ),
        ),
        decisions=(),
    )


def _action(
    *,
    run_id: str,
    sequence: int,
    name: str,
    status: RunStatus,
    message: str,
    evidence: EvidenceRef | None = None,
    would_mutate_fs: bool = False,
) -> ActionEvent:
    side_effects = (SideEffect.FILESYSTEM_WRITE,) if would_mutate_fs else ()
    return ActionEvent(
        action_id=f"{run_id}:{sequence:04d}",
        sequence=sequence,
        name=name,
        status=status,
        side_effects=side_effects,
        gate=GateDecision(
            required=would_mutate_fs,
            granted=not would_mutate_fs,
            reason=(
                "Dry-Run-Plan; Live-Ausführung nicht freigegeben."
                if would_mutate_fs
                else "Keine Nebenwirkung im Dry-Run."
            ),
        ),
        evidence=(evidence,) if evidence is not None else (),
        undo=UndoDescriptor(supported=False, action=None),
        message=message,
    )


def _evidence(
    fingerprint: str,
    scan_ref: str,
    relative_path: str,
    action: str,
    payload: dict[str, object],
) -> EvidenceRef:
    material = json.dumps(
        {
            "fingerprint": fingerprint,
            "scan_ref": scan_ref,
            "relative_path": relative_path,
            "action": action,
            "payload": payload,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return EvidenceRef(
        kind="fcsa.dry-run-plan",
        uri=f"fcsa://{scan_ref}/{quote(relative_path)}#{quote(action)}",
        sha256=sha256(material.encode("utf-8")).hexdigest(),
    )


def _scan_ref(scan_path: Path) -> str:
    return sha256(str(scan_path.resolve()).casefold().encode("utf-8")).hexdigest()[:16]


def _provider(plugin: PluginDescriptor) -> ProviderProvenance:
    return ProviderProvenance(
        plugin_id=plugin.plugin_id,
        version=plugin.version,
        source_repository=plugin.source_repository,
        source_revision=plugin.source_revision,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


_PROVIDER_WORDS = {
    "ausfuehren": "ausführen",
    "bestaetigter": "bestätigter",
    "fuer": "für",
    "geaendert": "geändert",
    "geloescht": "gelöscht",
    "gewuenschten": "gewünschten",
    "naechste": "nächste",
    "uebersprungen": "übersprungen",
    "ungueltiges": "ungültiges",
    "unveraendert": "unverändert",
    "veraendern": "verändern",
    "vorgemerkt": "vorgemerkt",
    "wuerde": "würde",
}
_PROVIDER_WORD_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in _PROVIDER_WORDS) + r")\b"
)


def _display_text(value: str) -> str:
    """Normalize known legacy German words without rewriting paths wholesale."""

    return _PROVIDER_WORD_PATTERN.sub(lambda match: _PROVIDER_WORDS[match.group(0)], value)
