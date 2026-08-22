"""Extract evidenced document events and build read-only calendar handoffs."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.calendar_ics import (
    CalendarIcsError,
    IcsArtifact,
    publish_ics_batch,
    render_calendar_ics,
    rollback_published_ics,
)
from folderhome.capabilities.calendar_store import (
    EMPTY_CALENDAR_REVISION,
    CalendarStore,
    CalendarStoreError,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    CalendarBackend,
    CalendarCandidate,
    CalendarConfiguration,
    CalendarEventRecord,
    CalendarEvidence,
    CalendarExecutionItem,
    CalendarExecutionReport,
    CalendarHandoffAction,
    CalendarHandoffApproval,
    CalendarHandoffPlan,
    DocumentCalendarAnalysis,
    DocumentRecord,
    FolderCalendarAnalysis,
    FolderCalendarItem,
    PrivacyStatus,
    ResolvedProfilePolicy,
    RuleKey,
)

_LABELED_LINE = re.compile(r"^\s*([^:]{1,48}):\s*(\S(?:.*\S)?)\s*$")
_TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
_LABELS = {
    "termin": "title",
    "terminname": "title",
    "titel": "title",
    "datum": "event_date",
    "termin am": "event_date",
    "uhrzeit": "start_time",
    "beginn": "start_time",
    "start": "start_time",
    "ende": "end_time",
    "endzeit": "end_time",
    "ort": "location",
    "adresse": "location",
    "zeitzone": "timezone",
    "timezone": "timezone",
}


class CalendarWorkflowError(RuntimeError):
    """Raised when event evidence or calendar configuration is unsafe."""


class CalendarDocumentExtractor(Protocol):
    """Read-only document extraction port for calendar analysis."""

    def extract(self, source_path: Path) -> DocumentRecord: ...


def load_calendar_configuration(path: Path) -> CalendarConfiguration:
    """Load one explicit OS-account calendar configuration."""

    path = path.resolve()
    if path.is_symlink() or not path.is_file():
        raise CalendarWorkflowError(f"Kalenderkonfiguration fehlt oder ist ein Link: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalendarWorkflowError(f"Kalenderkonfiguration ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != CalendarConfiguration.SCHEMA:
        raise CalendarWorkflowError("Kalenderkonfiguration verwendet ein unbekanntes Schema.")
    try:
        raw_directory = _required_text(payload, "uptoday_ics_directory")
        directory = Path(raw_directory)
        if not directory.is_absolute():
            directory = path.parent / directory
        return CalendarConfiguration(
            config_path=path,
            default_backend=CalendarBackend(_required_text(payload, "default_backend")),
            default_timezone=_required_text(payload, "default_timezone"),
            uptoday_ics_directory=directory,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CalendarWorkflowError(f"Kalenderkonfiguration ist ungültig: {exc}") from exc


def resolve_calendar_preferences(
    configuration: CalendarConfiguration,
    policy: ResolvedProfilePolicy,
) -> tuple[CalendarBackend, str, str, tuple[str, ...]]:
    """Resolve backend and timezone from existing deterministic profile rules."""

    backend = configuration.default_backend
    backend_source = "config_default"
    source_rule_ids: tuple[str, ...] = ()
    timezone = configuration.default_timezone
    for rule in policy.rules:
        if rule.key is RuleKey.CALENDAR_BACKEND:
            backend = CalendarBackend(str(rule.value))
            backend_source = "profile_rule"
            source_rule_ids = rule.source_rule_ids
        elif rule.key is RuleKey.CALENDAR_TIMEZONE:
            timezone = str(rule.value)
    return backend, backend_source, timezone, source_rule_ids


def analyze_document_calendar(
    document: DocumentRecord,
    *,
    profile_id: str,
    area: str,
    default_timezone: str,
    allow_sensitive_local_read: bool = False,
) -> DocumentCalendarAnalysis:
    """Extract one event candidate from explicit labels only."""

    if document.privacy_status in {PrivacyStatus.BLOCKED, PrivacyStatus.NOT_CHECKED}:
        return _analysis(
            document,
            status="blocked",
            issues=("Datenschutzstatus blockiert die lokale Terminerfassung.",),
        )
    if (
        document.privacy_status is PrivacyStatus.REVIEW_REQUIRED
        and not allow_sensitive_local_read
    ):
        return _analysis(
            document,
            status="review_required",
            issues=(
                "Datenschutzstatus erfordert eine Freigabe für die lokale "
                "Terminerfassung.",
            ),
        )
    try:
        ZoneInfo(default_timezone)
    except ZoneInfoNotFoundError:
        return _analysis(
            document,
            status="review_required",
            issues=(f"Unbekannte Standardzeitzone: {default_timezone}",),
        )

    values: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for line_number, line in enumerate(document.text.splitlines(), start=1):
        match = _LABELED_LINE.fullmatch(line)
        if match is None:
            continue
        raw_label, raw_value = match.groups()
        field = _LABELS.get(raw_label.strip().casefold())
        if field is None:
            continue
        value = raw_value.strip()
        if len(value) > 256:
            return _analysis(
                document,
                status="review_required",
                issues=(f"Feld {field} überschreitet die zulässige Länge.",),
            )
        values[field].append((value, line_number, raw_label.strip()))

    issues = []
    selected: dict[str, tuple[str, int, str]] = {}
    for field, occurrences in values.items():
        unique = {value.casefold() for value, _, _ in occurrences}
        if len(unique) > 1:
            issues.append(f"Feld {field} wurde mehrfach mit verschiedenen Werten gefunden.")
        else:
            selected[field] = occurrences[0]
    for field in ("title", "event_date"):
        if field not in selected:
            issues.append(f"Pflichtfeld {field} fehlt.")

    event_date = None
    if "event_date" in selected:
        try:
            event_date = _normalize_date(selected["event_date"][0])
        except ValueError as exc:
            issues.append(str(exc))
    start_time = None
    if "start_time" in selected:
        try:
            start_time = _normalize_time(selected["start_time"][0])
        except ValueError as exc:
            issues.append(str(exc))
    end_time = None
    if "end_time" in selected:
        try:
            end_time = _normalize_time(selected["end_time"][0])
        except ValueError as exc:
            issues.append(str(exc))
    if end_time is not None and start_time is None:
        issues.append("Eine Endzeit benötigt eine Startzeit.")
    if start_time is not None and end_time is not None and end_time <= start_time:
        issues.append("Die Endzeit muss nach der Startzeit liegen.")

    timezone = default_timezone
    timezone_basis = "configuration_or_profile"
    if "timezone" in selected:
        timezone = selected["timezone"][0]
        timezone_basis = "explicit_label"
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        issues.append(f"Unbekannte Zeitzone: {timezone}")

    if issues:
        return _analysis(
            document,
            status="review_required",
            issues=tuple(sorted(set(issues))),
        )
    assert event_date is not None
    evidence = tuple(
        CalendarEvidence(field=field, line_number=value[1], label=value[2])
        for field, value in sorted(selected.items())
    )
    title = selected["title"][0]
    location = selected["location"][0] if "location" in selected else None
    uid_payload = {
        "profile_id": profile_id,
        "area": area,
        "title": title,
        "event_date": event_date,
        "start_time": start_time,
        "end_time": end_time,
        "timezone": timezone,
        "location": location,
    }
    uid_hash = _json_hash(uid_payload)
    event_uid = f"{uid_hash}@folderhome.local"
    candidate_payload = {
        **uid_payload,
        "event_uid": event_uid,
        "timezone_basis": timezone_basis,
        "source_document_id": document.document_id,
        "source_sha256": document.source_sha256,
        "source_path": str(document.source_path),
        "evidence": [item.to_dict() for item in evidence],
    }
    candidate = CalendarCandidate(
        candidate_id=f"calendar_candidate_{_json_hash(candidate_payload)}",
        event_uid=event_uid,
        profile_id=profile_id,
        area=area,
        title=title,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
        timezone_basis=timezone_basis,
        location=location,
        source_document_id=document.document_id,
        source_sha256=document.source_sha256,
        source_path=document.source_path,
        evidence=evidence,
    )
    return _analysis(document, status="candidate", candidate=candidate)


def analyze_folder_calendar(
    source_dir: Path,
    *,
    profile_id: str,
    area: str,
    default_timezone: str,
    extractor: CalendarDocumentExtractor,
    recursive: bool = True,
    allow_sensitive_local_read: bool = False,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderCalendarAnalysis:
    """Analyze visible files while retaining skips and failures."""

    root = source_dir.resolve()
    if root.is_symlink() or not root.is_dir():
        raise CalendarWorkflowError(f"Dokumentenordner fehlt oder ist ein Link: {root}")
    try:
        inventory = inventory_files(root, recursive=recursive, policy=resource_policy)
    except (ResourceLimitExceeded, ValueError) as exc:
        raise CalendarWorkflowError(str(exc)) from exc
    paths = inventory.all_paths
    items = []
    text_budget = ResourceBudget(resource_policy)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            items.append(
                FolderCalendarItem(relative, "skipped", None, "Symbolischer Link ausgelassen.")
            )
            continue
        try:
            document = extractor.extract(path)
            text_budget.consume_extracted_text(len(document.text))
            analysis = analyze_document_calendar(
                document,
                profile_id=profile_id,
                area=area,
                default_timezone=default_timezone,
                allow_sensitive_local_read=allow_sensitive_local_read,
            )
            message = (
                "Terminkandidat mit Zeilenevidenz erkannt."
                if analysis.status == "candidate"
                else "Dokument benötigt Terminprüfung."
            )
            items.append(FolderCalendarItem(relative, analysis.status, analysis, message))
        except UnsupportedDocumentError as exc:
            items.append(FolderCalendarItem(relative, "skipped", None, str(exc)))
        except DocServicesBridgeError as exc:
            items.append(FolderCalendarItem(relative, "failed", None, str(exc)))
        except ResourceLimitExceeded as exc:
            raise CalendarWorkflowError(str(exc)) from exc
    return FolderCalendarAnalysis(
        source_root=root,
        profile_id=profile_id,
        area=area,
        recursive=recursive,
        items=tuple(items),
    )


def build_calendar_handoff_plan(
    analysis: FolderCalendarAnalysis,
    *,
    configuration: CalendarConfiguration,
    policy: ResolvedProfilePolicy,
    planned_at: str,
    calendar_revision: str = EMPTY_CALENDAR_REVISION,
    existing_events: tuple[CalendarEventRecord, ...] = (),
) -> CalendarHandoffPlan:
    """Build a deterministic, connector-free event handoff plan."""

    _validate_timestamp(planned_at)
    if policy.profile_id != analysis.profile_id or policy.area != analysis.area:
        raise CalendarWorkflowError("Profilrichtlinie passt nicht zur Terminanalyse.")
    backend, source, timezone, source_rule_ids = resolve_calendar_preferences(
        configuration,
        policy,
    )
    if any(
        candidate.timezone_basis == "configuration_or_profile"
        and candidate.timezone != timezone
        for candidate in analysis.candidates
    ):
        raise CalendarWorkflowError(
            "Terminanalyse wurde nicht mit der aktuell aufgelösten Profilzeitzone erstellt."
        )

    conflicts: set[str] = set()
    grouped: dict[tuple[str, str, str, str], list[CalendarCandidate]] = defaultdict(list)
    for candidate in analysis.candidates:
        if candidate.conflict_key is not None:
            grouped[candidate.conflict_key].append(candidate)
    for candidates in grouped.values():
        if len({candidate.event_uid for candidate in candidates}) > 1:
            conflicts.update(candidate.candidate_id for candidate in candidates)

    existing_uids = {
        event.event_uid for event in existing_events if event.status == "active"
    }
    existing_conflicts = {
        event.conflict_key: event.event_uid
        for event in existing_events
        if event.status == "active" and event.conflict_key is not None
    }

    actions = []
    for candidate in sorted(analysis.candidates, key=lambda item: item.candidate_id):
        target_path = None
        content_sha256 = None
        if candidate.candidate_id in conflicts:
            status = "blocked"
            side_effect = "none"
            message = "Zeitkonflikt zwischen verschiedenen Dokumentterminen."
        elif backend is CalendarBackend.UPTODAY_ICS:
            filename = f"{candidate.event_uid.split('@', 1)[0]}.ics"
            target_path = configuration.uptoday_ics_directory / filename
            content = render_calendar_ics(candidate, planned_at)
            content_sha256 = sha256(content.encode("utf-8")).hexdigest()
            if _paths_overlap(analysis.source_root, configuration.uptoday_ics_directory):
                status = "blocked"
                side_effect = "none"
                message = "ICS-Handoff und Dokumentquelle dürfen sich nicht überlappen."
            elif target_path.exists() or target_path.is_symlink():
                status = "blocked"
                side_effect = "none"
                message = "Geplante ICS-Zieldatei existiert bereits."
            else:
                status = "planned"
                side_effect = "new_ics_file"
                message = "Neue ICS-Handoff-Datei planen; UpToday-Import bleibt getrennt."
        elif backend is CalendarBackend.FOLDERHOME_LOCAL:
            if candidate.event_uid in existing_uids:
                status = "noop"
                side_effect = "none"
                message = "Identischer Termin ist im lokalen Kalender bereits vorhanden."
            elif (
                candidate.conflict_key is not None
                and candidate.conflict_key in existing_conflicts
                and existing_conflicts[candidate.conflict_key] != candidate.event_uid
            ):
                status = "blocked"
                side_effect = "none"
                message = "Zeitkonflikt mit einem vorhandenen lokalen Termin."
            else:
                status = "planned"
                side_effect = "local_calendar_state"
                message = "Lokalen FolderHome-Kalendereintrag nach separater Freigabe planen."
        elif backend is CalendarBackend.ROUTINIKA:
            status = "blocked"
            side_effect = "none"
            message = "Es ist kein geprüfter Routinika-Connector verfügbar."
        else:
            status = "blocked"
            side_effect = "none"
            message = "Google Calendar benötigt einen separaten externen Connectorvertrag."
        actions.append(
            CalendarHandoffAction(
                action_id=_action_id(candidate, backend, status, target_path, content_sha256),
                candidate=candidate,
                backend=backend,
                status=status,
                side_effect=side_effect,
                target_path=target_path,
                content_sha256=content_sha256,
                message=message,
            )
        )
    action_tuple = tuple(actions)
    payload = {
        "schema": CalendarHandoffPlan.SCHEMA,
        "planned_at": planned_at,
        "calendar_revision": calendar_revision,
        "backend": backend.value,
        "backend_source": source,
        "source_rule_ids": list(source_rule_ids),
        "configuration": configuration.to_dict(),
        "analysis": analysis.to_dict(),
        "actions": [action.to_dict() for action in action_tuple],
    }
    return CalendarHandoffPlan(
        plan_id=f"calendar_plan_{_json_hash(payload)}",
        planned_at=planned_at,
        calendar_revision=calendar_revision,
        backend=backend,
        backend_source=source,
        source_rule_ids=source_rule_ids,
        configuration=configuration,
        analysis=analysis,
        actions=action_tuple,
    )


def apply_calendar_handoff_plan(
    plan: CalendarHandoffPlan,
    approval: CalendarHandoffApproval,
    *,
    store: CalendarStore,
    allow_state_write: bool,
    allow_output_write: bool,
) -> CalendarExecutionReport:
    """Execute exact approved actions behind explicit state and output gates."""

    if not allow_state_write:
        raise CalendarWorkflowError("Kalenderausführung benötigt eine State-Freigabe.")
    if plan.backend is CalendarBackend.UPTODAY_ICS and not allow_output_write:
        raise CalendarWorkflowError("ICS-Ausführung benötigt eine Output-Freigabe.")
    if approval.plan_id != plan.plan_id:
        raise CalendarWorkflowError("Kalenderfreigabe gehört nicht zu diesem Plan.")
    if approval.calendar_revision != plan.calendar_revision:
        raise CalendarWorkflowError("Kalenderfreigabe bindet eine andere Revision.")
    if plan.backend not in {
        CalendarBackend.FOLDERHOME_LOCAL,
        CalendarBackend.UPTODAY_ICS,
    }:
        raise CalendarWorkflowError("Der geplante Kalender-Backend ist nicht ausführbar.")
    action_by_id = {action.action_id: action for action in plan.actions}
    try:
        selected = tuple(action_by_id[action_id] for action_id in approval.action_ids)
    except KeyError as exc:
        raise CalendarWorkflowError(
            f"Kalenderfreigabe enthält eine unbekannte Aktion: {exc.args[0]}"
        ) from exc
    if any(action.status != "planned" for action in selected):
        raise CalendarWorkflowError("Nur geplante Kalenderaktionen dürfen ausgeführt werden.")
    if any(action.backend is not plan.backend for action in selected):
        raise CalendarWorkflowError("Kalenderaktion und Plan verwenden verschiedene Backends.")
    if _paths_overlap(plan.analysis.source_root, store.state_dir):
        raise CalendarWorkflowError(
            "Kalender-State und Dokumentquelle dürfen sich nicht überlappen."
        )
    if (
        plan.backend is CalendarBackend.UPTODAY_ICS
        and _paths_overlap(store.state_dir, plan.configuration.uptoday_ics_directory)
    ):
        raise CalendarWorkflowError("Kalender-State und ICS-Ausgabe dürfen sich nicht überlappen.")

    try:
        store.validate_execution(
            expected_revision=plan.calendar_revision,
            approval_id=approval.approval_id,
        )
    except CalendarStoreError as exc:
        raise CalendarWorkflowError(str(exc)) from exc
    for action in selected:
        _verify_calendar_source(action)

    if plan.backend is CalendarBackend.FOLDERHOME_LOCAL:
        try:
            event_ids, revision_after = store.apply_local(
                expected_revision=plan.calendar_revision,
                actions=selected,
                approval=approval,
            )
        except CalendarStoreError as exc:
            raise CalendarWorkflowError(str(exc)) from exc
        items = tuple(
            CalendarExecutionItem(
                action_id=action.action_id,
                event_uid=action.candidate.event_uid,
                event_id=event_id,
                output_path=None,
                output_sha256=None,
                status="created",
                undo_supported=False,
                undo_action=None,
            )
            for action, event_id in zip(selected, event_ids, strict=True)
        )
    else:
        artifacts = []
        for action in selected:
            if action.target_path is None or action.content_sha256 is None:
                raise CalendarWorkflowError("ICS-Aktion besitzt keinen vollständigen Ausgabeplan.")
            content = render_calendar_ics(action.candidate, plan.planned_at)
            if sha256(content.encode("utf-8")).hexdigest() != action.content_sha256:
                raise CalendarWorkflowError("ICS-Inhalt weicht vom freigegebenen Plan ab.")
            if action.target_path.exists() or action.target_path.is_symlink():
                raise CalendarWorkflowError(
                    f"ICS-Zieldatei existiert bereits: {action.target_path}"
                )
            artifacts.append(
                IcsArtifact(action.target_path, content, action.content_sha256)
            )
        try:
            published = publish_ics_batch(tuple(artifacts))
        except CalendarIcsError as exc:
            raise CalendarWorkflowError(str(exc)) from exc
        receipts = tuple(
            (output.target_path, output.content_sha256)
            for output in published.outputs
        )
        try:
            revision_after = store.record_external(
                expected_revision=plan.calendar_revision,
                actions=selected,
                approval=approval,
                receipts=receipts,
            )
        except CalendarStoreError as exc:
            try:
                rollback_published_ics(published)
            except CalendarIcsError as rollback_exc:
                raise CalendarWorkflowError(
                    f"{exc}; ICS-Rücknahme fehlgeschlagen: {rollback_exc}"
                ) from exc
            raise CalendarWorkflowError(str(exc)) from exc
        items = tuple(
            CalendarExecutionItem(
                action_id=action.action_id,
                event_uid=action.candidate.event_uid,
                event_id=None,
                output_path=output.target_path,
                output_sha256=output.content_sha256,
                status="published",
                undo_supported=True,
                undo_action="remove_if_hash_matches",
            )
            for action, output in zip(selected, published.outputs, strict=True)
        )

    execution_payload = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "action_ids": list(approval.action_ids),
        "calendar_revision_after": revision_after,
    }
    return CalendarExecutionReport(
        execution_id=f"calendar_exec_{_json_hash(execution_payload)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        backend=plan.backend,
        calendar_revision_before=plan.calendar_revision,
        calendar_revision_after=revision_after,
        items=items,
        state_path=store.path,
    )


def _analysis(
    document: DocumentRecord,
    *,
    status: str,
    candidate: CalendarCandidate | None = None,
    issues: tuple[str, ...] = (),
) -> DocumentCalendarAnalysis:
    return DocumentCalendarAnalysis(
        document_id=document.document_id,
        source_path=document.source_path,
        source_sha256=document.source_sha256,
        status=status,
        candidate=candidate,
        issues=issues,
    )


def _required_text(payload: dict[str, object], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} muss ein nichtleerer Text sein.")
    return value


def _normalize_date(value: str) -> str:
    for pattern in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Datum muss YYYY-MM-DD oder DD.MM.YYYY verwenden.")


def _normalize_time(value: str) -> str:
    if _TIME_PATTERN.fullmatch(value) is None:
        raise ValueError("Uhrzeit muss HH:MM im 24-Stunden-Format verwenden.")
    return value


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()


def _validate_timestamp(value: str) -> None:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalendarWorkflowError(f"planned_at ist kein ISO-Zeitpunkt: {value}") from exc
    if timestamp.tzinfo is None:
        raise CalendarWorkflowError("planned_at benötigt eine Zeitzone.")


def _paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def _action_id(
    candidate: CalendarCandidate,
    backend: CalendarBackend,
    status: str,
    target_path: Path | None,
    content_sha256: str | None,
) -> str:
    material = "\0".join(
        (
            candidate.candidate_id,
            backend.value,
            status,
            str(target_path) if target_path else "",
            content_sha256 or "",
        )
    )
    return f"calendar_action_{sha256(material.encode('utf-8')).hexdigest()[:32]}"


def _verify_calendar_source(action: CalendarHandoffAction) -> None:
    source = action.candidate.source_path
    if source.is_symlink() or not source.is_file():
        raise CalendarWorkflowError(f"Terminquelle fehlt oder ist kein reguläres File: {source}")
    digest = sha256()
    try:
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CalendarWorkflowError(f"Terminquelle ist nicht lesbar: {source}: {exc}") from exc
    if digest.hexdigest() != action.candidate.source_sha256:
        raise CalendarWorkflowError(f"Quellhash hat sich seit der Planung verändert: {source}")
