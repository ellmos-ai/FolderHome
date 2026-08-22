"""Translate resolved profile rules into read-only document action plans."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from string import Formatter

from folderhome.contracts import (
    ActionRuleProvenance,
    DocumentBundleResult,
    DocumentPolicyActionPlan,
    DocumentRecord,
    GateDecision,
    PolicyActionKind,
    PolicyActionStatus,
    PolicyActionStep,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    SideEffect,
    UndoDescriptor,
)
from folderhome.contracts.action_plans import compute_document_policy_plan_id

_ALLOWED_TEMPLATE_FIELDS = {"area", "date", "ext", "name", "profile"}
_WINDOWS_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_SUPPORTED_TRANSFORM_OUTPUTS = {"pdf", "txt"}
_TRANSFORM_PROVIDER_ID = "folderhome.document-transform"


class DocumentActionPlanError(ValueError):
    """Raised when rules cannot be translated into one safe, explicit plan."""


def build_document_action_plan(
    document: DocumentRecord,
    policy: ResolvedProfilePolicy,
    *,
    target_root: Path,
    as_of: date,
) -> DocumentPolicyActionPlan:
    """Build a deterministic plan without creating, moving, or deleting files."""

    if not isinstance(as_of, date):
        raise DocumentActionPlanError("as_of muss ein explizites Datum sein.")
    root = target_root.resolve()
    rules = _rule_map(policy)
    _validate_rule_pairs(rules)
    modified_date = _modified_date(document.modified_at)
    current_path = document.source_path.resolve()
    steps: list[PolicyActionStep] = []

    naming_rule = rules.get(RuleKey.NAMING_TEMPLATE)
    if naming_rule is not None:
        target_name = _render_filename(
            _text_value(naming_rule),
            document=document,
            policy=policy,
            modified_date=modified_date,
        )
        target_path = current_path.with_name(target_name).resolve()
        if target_path != current_path:
            steps.append(
                _step(
                    steps,
                    document=document,
                    kind=PolicyActionKind.RENAME,
                    source_path=current_path,
                    target_path=target_path,
                    provider_id="folderhome.document-actions",
                    capability_id="rename",
                    status=PolicyActionStatus.PLANNED,
                    rules=(naming_rule,),
                    undo=UndoDescriptor(True, "move-back-to-source"),
                    message=(
                        "Benennung ist nur vorgeplant; die Datei bleibt bis zur "
                        "expliziten Freigabe unverändert."
                    ),
                )
            )
            current_path = target_path

    sort_rule = rules.get(RuleKey.SORT_TARGET)
    if sort_rule is not None:
        target_directory = _directory_below_root(_text_value(sort_rule), root)
        target_path = (target_directory / current_path.name).resolve()
        if target_path != current_path:
            steps.append(
                _step(
                    steps,
                    document=document,
                    kind=PolicyActionKind.SORT,
                    source_path=current_path,
                    target_path=target_path,
                    provider_id="file-collect-sort-action",
                    capability_id="move",
                    status=PolicyActionStatus.PLANNED,
                    rules=(sort_rule,),
                    undo=UndoDescriptor(True, "move-back-to-source"),
                    message=(
                        "Sortierziel ist FCSA-kompatibel vorgeplant; der "
                        "Dateisystem-Gate bleibt geschlossen."
                    ),
                )
            )
            current_path = target_path

    format_rule = rules.get(RuleKey.FORMAT_REQUIRED)
    original_rule = rules.get(RuleKey.CONVERSION_ORIGINAL)
    conversion_planned = False
    if format_rule is not None:
        required_format = _text_value(format_rule).lower()
        current_format = current_path.suffix.removeprefix(".").lower()
        if required_format != "original" and required_format != current_format:
            conversion_planned = True
            converted_path = current_path.with_suffix(f".{required_format}").resolve()
            supported = required_format in _SUPPORTED_TRANSFORM_OUTPUTS
            steps.append(
                _step(
                    steps,
                    document=document,
                    kind=PolicyActionKind.CONVERT,
                    source_path=current_path,
                    target_path=converted_path,
                    provider_id=_TRANSFORM_PROVIDER_ID if supported else None,
                    capability_id=f"convert-to-{required_format}",
                    status=(
                        PolicyActionStatus.PLANNED
                        if supported
                        else PolicyActionStatus.BLOCKED
                    ),
                    rules=(format_rule,),
                    undo=UndoDescriptor(True, "remove-converted-output"),
                    message=(
                        "Gekapselte Dokumenttransformation ist vorgeplant; "
                        "die Ausgabe benötigt eine explizite Schreibfreigabe."
                        if supported
                        else "Für dieses Zielformat ist kein geprüfter Provider "
                        "gebunden; die Konvertierung bleibt blockiert."
                    ),
                )
            )
            if original_rule is not None and _text_value(original_rule) != "keep":
                steps.append(
                    _original_step(
                        steps,
                        document=document,
                        source_path=current_path,
                        root=root,
                        rule=original_rule,
                        blocked=True,
                    )
                )
    if original_rule is not None and not conversion_planned:
        # A rule about conversion originals has no effect unless conversion is needed.
        pass

    archive_rule = rules.get(RuleKey.ARCHIVE_AFTER_DAYS)
    archive_folder_rule = rules.get(RuleKey.ARCHIVE_FOLDER)
    if archive_rule is not None and _is_due(
        modified_date,
        as_of,
        _integer_value(archive_rule),
    ):
        assert archive_folder_rule is not None
        archive_directory = _directory_below_root(
            _text_value(archive_folder_rule),
            root,
        )
        steps.append(
            _step(
                steps,
                document=document,
                kind=PolicyActionKind.ARCHIVE,
                source_path=current_path,
                target_path=(archive_directory / current_path.name).resolve(),
                provider_id="file-collect-sort-action",
                capability_id="move",
                status=PolicyActionStatus.PLANNED,
                rules=(archive_rule, archive_folder_rule),
                undo=UndoDescriptor(True, "move-back-to-source"),
                message=(
                    "Archivierung ist als reversible FCSA-Verschiebung vorgeplant; "
                    "die Freigabe wurde nicht erteilt."
                ),
            )
        )

    delete_age_rule = rules.get(RuleKey.DELETE_AFTER_DAYS)
    delete_mode_rule = rules.get(RuleKey.DELETE_MODE)
    if delete_age_rule is not None and _is_due(
        modified_date,
        as_of,
        _integer_value(delete_age_rule),
    ):
        assert delete_mode_rule is not None
        delete_mode = _text_value(delete_mode_rule)
        if delete_mode == "review_only":
            steps.append(
                _step(
                    steps,
                    document=document,
                    kind=PolicyActionKind.REVIEW,
                    source_path=current_path,
                    target_path=None,
                    provider_id="folderhome.document-policy-planner",
                    capability_id="human-review",
                    status=PolicyActionStatus.REVIEW_REQUIRED,
                    rules=(delete_age_rule, delete_mode_rule),
                    side_effects=(),
                    undo=UndoDescriptor(False, None),
                    message=(
                        "Die Aufbewahrungsdauer ist erreicht; die Regel verlangt "
                        "ausschließlich eine menschliche Prüfung."
                    ),
                )
            )
        elif delete_mode == "recycle_bin":
            steps.append(
                _step(
                    steps,
                    document=document,
                    kind=PolicyActionKind.RECYCLE,
                    source_path=current_path,
                    target_path=None,
                    provider_id="file-collect-sort-action",
                    capability_id="delete-to-trash",
                    status=PolicyActionStatus.PLANNED,
                    rules=(delete_age_rule, delete_mode_rule),
                    undo=UndoDescriptor(True, "restore-from-recycle-bin"),
                    message=(
                        "Nur eine verschiebbare Papierkorbaktion ist vorgeplant; "
                        "Hard Delete ist ausgeschlossen."
                    ),
                )
            )

    steps = _block_destination_conflicts(steps, document=document)
    plan_steps = tuple(steps)
    plan_id = compute_document_policy_plan_id(
        profile_id=policy.profile_id,
        area=policy.area,
        as_of=as_of.isoformat(),
        target_root=root,
        document=document,
        steps=plan_steps,
    )
    return DocumentPolicyActionPlan(
        plan_id=plan_id,
        profile_id=policy.profile_id,
        area=policy.area,
        as_of=as_of.isoformat(),
        target_root=root,
        document=document,
        steps=plan_steps,
    )


def release_original_handling(
    plan: DocumentPolicyActionPlan,
    result: DocumentBundleResult,
) -> DocumentPolicyActionPlan:
    """Release a blocked original step only after verified transform output."""

    if result.provider_id != _TRANSFORM_PROVIDER_ID:
        raise DocumentActionPlanError(
            f"Falscher Transformationsprovider: {result.provider_id}"
        )
    if result.source_document_ids != (plan.document.document_id,):
        raise DocumentActionPlanError(
            "Transformationsergebnis gehört nicht ausschließlich zum Plandokument."
        )
    output = result.output_path.resolve()
    conversion = next(
        (
            step
            for step in plan.steps
            if step.kind is PolicyActionKind.CONVERT
            and step.provider_id == _TRANSFORM_PROVIDER_ID
            and step.status is PolicyActionStatus.PLANNED
            and step.target_path == output
        ),
        None,
    )
    if conversion is None:
        raise DocumentActionPlanError(
            "Transformationsergebnis passt zu keinem freigabefähigen Konvertierungsschritt."
        )
    if not output.is_file() or _sha256_file(output) != result.output_sha256:
        raise DocumentActionPlanError(
            "Transformationsergebnis fehlt oder stimmt nicht mit dem Ausgabehash überein."
        )
    released = False
    updated = []
    for step in plan.steps:
        if (
            step.kind is PolicyActionKind.HANDLE_ORIGINAL
            and step.status is PolicyActionStatus.BLOCKED
        ):
            updated.append(
                replace(
                    step,
                    status=PolicyActionStatus.PLANNED,
                    message=(
                        "Die erfolgreiche Transformation ist durch Ausgabehash und "
                        "Quelldokumentbezug nachgewiesen; die getrennte "
                        "Originalbehandlung bleibt weiterhin ungefreigt."
                    ),
                )
            )
            released = True
        else:
            updated.append(step)
    if not released:
        raise DocumentActionPlanError(
            "Der Aktionsplan enthält keine blockierte Originalbehandlung."
        )
    updated_steps = tuple(updated)
    plan_id = compute_document_policy_plan_id(
        profile_id=plan.profile_id,
        area=plan.area,
        as_of=plan.as_of,
        target_root=plan.target_root,
        document=plan.document,
        steps=updated_steps,
    )
    return replace(plan, plan_id=plan_id, steps=updated_steps)


def _rule_map(policy: ResolvedProfilePolicy) -> dict[RuleKey, ResolvedProfileRule]:
    rules: dict[RuleKey, ResolvedProfileRule] = {}
    for rule in policy.rules:
        if rule.key in rules:
            raise DocumentActionPlanError(
                f"Aufgelöste Richtlinie enthält {rule.key.value} mehrfach."
            )
        rules[rule.key] = rule
    return rules


def _validate_rule_pairs(rules: dict[RuleKey, ResolvedProfileRule]) -> None:
    pairs = (
        (RuleKey.ARCHIVE_AFTER_DAYS, RuleKey.ARCHIVE_FOLDER),
        (RuleKey.DELETE_AFTER_DAYS, RuleKey.DELETE_MODE),
    )
    for first, second in pairs:
        if first in rules and second not in rules:
            raise DocumentActionPlanError(
                f"{first.value} benötigt zusätzlich {second.value}."
            )


def _modified_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise DocumentActionPlanError(
            f"modified_at ist kein gültiger ISO-Zeitpunkt: {value}"
        ) from exc


def _render_filename(
    template: str,
    *,
    document: DocumentRecord,
    policy: ResolvedProfilePolicy,
    modified_date: date,
) -> str:
    formatter = Formatter()
    try:
        parsed = tuple(formatter.parse(template))
    except ValueError as exc:
        raise DocumentActionPlanError(f"Ungültige Benennungsvorlage: {exc}") from exc
    fields = set()
    for _, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name not in _ALLOWED_TEMPLATE_FIELDS:
            raise DocumentActionPlanError(
                f"Nicht erlaubter Platzhalter in naming.template: {field_name}"
            )
        if format_spec or conversion:
            raise DocumentActionPlanError(
                "Formatangaben und Konvertierungen sind in naming.template nicht erlaubt."
            )
        fields.add(field_name)
    if "name" not in fields:
        raise DocumentActionPlanError("naming.template muss {name} enthalten.")
    try:
        filename = template.format(
            area=policy.area,
            date=modified_date.isoformat(),
            ext=Path(document.filename).suffix.removeprefix("."),
            name=Path(document.filename).stem,
            profile=policy.profile_id,
        )
    except (IndexError, KeyError, ValueError) as exc:
        raise DocumentActionPlanError(f"Benennungsvorlage ist nicht auswertbar: {exc}") from exc
    if "ext" not in fields and Path(document.filename).suffix:
        filename = f"{filename}{Path(document.filename).suffix}"
    _validate_filename(filename)
    return filename


def _validate_filename(filename: str) -> None:
    if not filename or filename in {".", ".."}:
        raise DocumentActionPlanError("Der geplante Dateiname ist leer oder reserviert.")
    if any(character in _WINDOWS_INVALID_FILENAME_CHARS for character in filename):
        raise DocumentActionPlanError(
            "Der geplante Dateiname enthält Trennzeichen oder ungültige Zeichen."
        )
    if filename[-1] in {" ", "."} or any(ord(character) < 32 for character in filename):
        raise DocumentActionPlanError(
            "Der geplante Dateiname endet ungültig oder enthält Steuerzeichen."
        )
    if Path(filename).stem.upper() in _WINDOWS_RESERVED_NAMES:
        raise DocumentActionPlanError("Der geplante Dateiname ist unter Windows reserviert.")


def _directory_below_root(value: str, root: Path) -> Path:
    relative = Path(value)
    unsafe_part = any(part in {"", ".", ".."} for part in relative.parts)
    if relative.is_absolute() or relative.drive or unsafe_part:
        raise DocumentActionPlanError(
            f"Zielordner muss relativ und innerhalb von target_root liegen: {value}"
        )
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise DocumentActionPlanError(
            f"Zielordner verlässt target_root: {value}"
        )
    return target


def _is_due(modified_date: date, as_of: date, after_days: int) -> bool:
    return (as_of - modified_date).days >= after_days


def _original_step(
    steps: list[PolicyActionStep],
    *,
    document: DocumentRecord,
    source_path: Path,
    root: Path,
    rule: ResolvedProfileRule,
    blocked: bool,
) -> PolicyActionStep:
    mode = _text_value(rule)
    target_path: Path | None
    provider_id = "file-collect-sort-action"
    capability_id = "move"
    undo = UndoDescriptor(True, "move-back-to-source")
    if mode == "archive":
        target_path = (root / "Originale" / "Archiv" / source_path.name).resolve()
    elif mode == "gardener_storage":
        target_path = (
            root / ".folderhome" / "gardener-storage" / source_path.name
        ).resolve()
    elif mode == "recycle_bin":
        target_path = None
        capability_id = "delete-to-trash"
        undo = UndoDescriptor(True, "restore-from-recycle-bin")
    else:
        raise DocumentActionPlanError(f"Unbekannte Originalbehandlung: {mode}")
    return _step(
        steps,
        document=document,
        kind=PolicyActionKind.HANDLE_ORIGINAL,
        source_path=source_path,
        target_path=target_path,
        provider_id=provider_id,
        capability_id=capability_id,
        status=(PolicyActionStatus.BLOCKED if blocked else PolicyActionStatus.PLANNED),
        rules=(rule,),
        undo=undo,
        message=(
            "Die Originalbehandlung bleibt blockiert, solange die vorgelagerte "
            "Konvertierung keinen geprüften Provider hat."
        ),
    )


def _block_destination_conflicts(
    steps: list[PolicyActionStep],
    *,
    document: DocumentRecord,
) -> list[PolicyActionStep]:
    destination_kinds = {
        PolicyActionKind.SORT,
        PolicyActionKind.ARCHIVE,
        PolicyActionKind.RECYCLE,
    }
    destination_steps = [step for step in steps if step.kind in destination_kinds]
    lifecycle = [
        step
        for step in destination_steps
        if step.kind in {PolicyActionKind.ARCHIVE, PolicyActionKind.RECYCLE}
    ]
    conflict = len(lifecycle) > 1 or (lifecycle and len(destination_steps) > len(lifecycle))
    if not conflict:
        return steps
    blocked_ids = {step.action_id for step in destination_steps}
    updated = [
        replace(
            step,
            status=PolicyActionStatus.BLOCKED,
            message=f"Zielkonflikt: {step.message}",
        )
        if step.action_id in blocked_ids
        else step
        for step in steps
    ]
    combined_rules = tuple(
        provenance
        for step in destination_steps
        for provenance in step.rules
    )
    updated.append(
        _step(
            updated,
            document=document,
            kind=PolicyActionKind.REVIEW,
            source_path=document.source_path,
            target_path=None,
            provider_id="folderhome.document-policy-planner",
            capability_id="resolve-destination-conflict",
            status=PolicyActionStatus.REVIEW_REQUIRED,
            rules=combined_rules,
            side_effects=(),
            undo=UndoDescriptor(False, None),
            message=(
                "Konflikt zwischen Sortier-, Archivierungs- oder Papierkorbziel; "
                "keine der betroffenen Aktionen darf automatisch ausgeführt werden."
            ),
        )
    )
    return updated


def _step(
    steps: list[PolicyActionStep],
    *,
    document: DocumentRecord,
    kind: PolicyActionKind,
    source_path: Path,
    target_path: Path | None,
    provider_id: str | None,
    capability_id: str,
    status: PolicyActionStatus,
    rules: tuple[ResolvedProfileRule, ...],
    undo: UndoDescriptor,
    message: str,
    side_effects: tuple[SideEffect, ...] = (SideEffect.FILESYSTEM_WRITE,),
) -> PolicyActionStep:
    sequence = len(steps) + 1
    material = "\0".join(
        (
            document.document_id,
            str(sequence),
            kind.value,
            str(source_path.resolve()),
            str(target_path.resolve()) if target_path else "",
        )
    )
    action_id = f"act_{sha256(material.encode('utf-8')).hexdigest()[:24]}"
    return PolicyActionStep(
        action_id=action_id,
        sequence=sequence,
        kind=kind,
        document_id=document.document_id,
        source_path=source_path,
        target_path=target_path,
        provider_id=provider_id,
        capability_id=capability_id,
        status=status,
        side_effects=side_effects,
        gate=GateDecision(
            required=True,
            granted=False,
            reason="Planungsmodus: keine Dateisystemfreigabe erteilt.",
        ),
        undo=undo,
        rules=tuple(_provenance(rule) for rule in rules),
        message=message,
    )


def _provenance(rule: ResolvedProfileRule) -> ActionRuleProvenance:
    return ActionRuleProvenance(
        key=rule.key,
        value=rule.value,
        scope=rule.scope,
        source_rule_ids=rule.source_rule_ids,
        overridden_rule_ids=rule.overridden_rule_ids,
    )


def _text_value(rule: ResolvedProfileRule) -> str:
    if not isinstance(rule.value, str):
        raise DocumentActionPlanError(f"{rule.key.value} muss Text enthalten.")
    return rule.value


def _integer_value(rule: ResolvedProfileRule) -> int:
    if isinstance(rule.value, bool) or not isinstance(rule.value, int):
        raise DocumentActionPlanError(f"{rule.key.value} muss eine Ganzzahl enthalten.")
    return rule.value


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
