"""Extract evidenced contacts and orchestrate approval-gated register updates."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from folderhome.bridges.doc_services import (
    DocServicesBridgeError,
    UnsupportedDocumentError,
)
from folderhome.capabilities.contact_registry import (
    ContactRegisterError,
    ContactRegisterStore,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    ResourceBudget,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import (
    ContactActionKind,
    ContactCandidate,
    ContactEvidence,
    ContactRecord,
    ContactRegisterAction,
    ContactRegisterApproval,
    ContactRegisterPlan,
    ContactRegisterReport,
    DocumentContactAnalysis,
    DocumentRecord,
    FolderContactAnalysis,
    FolderContactItem,
    PrivacyStatus,
)

_EMAIL_PATTERN = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
_LABELED_LINE = re.compile(r"^\s*([^:]{1,48}):\s*(\S(?:.*\S)?)\s*$")
_LABELS = {
    "organisation": "organization",
    "unternehmen": "organization",
    "ansprechpartner": "contact_name",
    "ansprechpartnerin": "contact_name",
    "kontakt": "contact_name",
    "rolle": "role",
    "position": "role",
    "zuständig für": "purpose",
    "zustaendig fuer": "purpose",
    "zweck": "purpose",
    "vertragsobjekt": "object_ref",
    "objekt": "object_ref",
    "e-mail": "email",
    "email": "email",
    "telefon": "phone",
    "tel": "phone",
    "gültig ab": "effective_date",
    "gueltig ab": "effective_date",
    "wirksam ab": "effective_date",
}


class ContactWorkflowError(RuntimeError):
    """Raised when contact evidence, approvals, or register state are stale."""


class ContactDocumentExtractor(Protocol):
    """Read-only document extraction port for contact analysis."""

    def extract(self, source_path: Path) -> DocumentRecord: ...


def analyze_document_contact(
    document: DocumentRecord,
    *,
    profile_id: str,
    area: str,
    allow_sensitive_local_read: bool = False,
) -> DocumentContactAnalysis:
    """Extract one candidate from explicit labels without retaining other text."""

    if document.privacy_status in {PrivacyStatus.BLOCKED, PrivacyStatus.NOT_CHECKED}:
        return _analysis(
            document,
            status="blocked",
            issues=(
                "Datenschutzstatus blockiert die lokale Kontaktübernahme.",
            ),
        )
    if (
        document.privacy_status is PrivacyStatus.REVIEW_REQUIRED
        and not allow_sensitive_local_read
    ):
        return _analysis(
            document,
            status="review_required",
            issues=(
                "Datenschutzstatus erfordert eine Freigabe für die lokale Kontaktextraktion.",
            ),
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
    for field in ("organization", "purpose"):
        if field not in selected:
            issues.append(f"Pflichtfeld {field} fehlt.")
    if "email" not in selected and "phone" not in selected:
        issues.append("Mindestens E-Mail oder Telefon fehlt.")

    email = None
    if "email" in selected:
        email = selected["email"][0].casefold()
        if _EMAIL_PATTERN.fullmatch(email) is None:
            issues.append("E-Mail-Adresse ist ungültig.")
    phone = None
    if "phone" in selected:
        try:
            phone = _normalize_phone(selected["phone"][0])
        except ValueError as exc:
            issues.append(str(exc))
    effective_date_basis = "document_modified_at"
    effective_date = _date_from_timestamp(document.modified_at)
    if "effective_date" in selected:
        try:
            effective_date = _normalize_date(selected["effective_date"][0])
            effective_date_basis = "explicit_label"
        except ValueError as exc:
            issues.append(str(exc))
    if issues:
        return _analysis(
            document,
            status="review_required",
            issues=tuple(sorted(set(issues))),
        )

    evidence = tuple(
        ContactEvidence(field=field, line_number=value[1], label=value[2])
        for field, value in sorted(selected.items())
    )
    payload = {
        "profile_id": profile_id,
        "area": area,
        "organization": selected["organization"][0],
        "contact_name": _optional(selected, "contact_name"),
        "role": _optional(selected, "role"),
        "purpose": selected["purpose"][0],
        "object_ref": _optional(selected, "object_ref"),
        "email": email,
        "phone": phone,
        "effective_date": effective_date,
        "effective_date_basis": effective_date_basis,
        "source_document_id": document.document_id,
        "source_sha256": document.source_sha256,
        "source_path": str(document.source_path),
        "evidence": [item.to_dict() for item in evidence],
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    candidate = ContactCandidate(
        candidate_id=f"contact_candidate_{sha256(material).hexdigest()}",
        profile_id=profile_id,
        area=area,
        organization=selected["organization"][0],
        contact_name=_optional(selected, "contact_name"),
        role=_optional(selected, "role"),
        purpose=selected["purpose"][0],
        object_ref=_optional(selected, "object_ref"),
        email=email,
        phone=phone,
        effective_date=effective_date,
        effective_date_basis=effective_date_basis,
        source_document_id=document.document_id,
        source_sha256=document.source_sha256,
        source_path=document.source_path,
        evidence=evidence,
    )
    return _analysis(document, status="candidate", candidate=candidate)


def analyze_folder_contacts(
    source_dir: Path,
    *,
    profile_id: str,
    area: str,
    extractor: ContactDocumentExtractor,
    recursive: bool = True,
    allow_sensitive_local_read: bool = False,
    resource_policy: ResourcePolicy = DEFAULT_RESOURCE_POLICY,
) -> FolderContactAnalysis:
    """Analyze every visible file while preserving unsupported/error outcomes."""

    root = source_dir.resolve()
    if root.is_symlink() or not root.is_dir():
        raise ContactWorkflowError(f"Dokumentenordner fehlt oder ist ein Link: {root}")
    try:
        inventory = inventory_files(root, recursive=recursive, policy=resource_policy)
    except (ResourceLimitExceeded, ValueError) as exc:
        raise ContactWorkflowError(str(exc)) from exc
    paths = inventory.all_paths
    items = []
    text_budget = ResourceBudget(resource_policy)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            items.append(
                FolderContactItem(relative, "skipped", None, "Symbolischer Link ausgelassen.")
            )
            continue
        try:
            document = extractor.extract(path)
            text_budget.consume_extracted_text(len(document.text))
            analysis = analyze_document_contact(
                document,
                profile_id=profile_id,
                area=area,
                allow_sensitive_local_read=allow_sensitive_local_read,
            )
            items.append(
                FolderContactItem(
                    relative,
                    analysis.status,
                    analysis,
                    (
                        "Kontaktkandidat mit Zeilenevidenz erkannt."
                        if analysis.status == "candidate"
                        else "Dokument benötigt Kontaktprüfung."
                    ),
                )
            )
        except UnsupportedDocumentError as exc:
            items.append(FolderContactItem(relative, "skipped", None, str(exc)))
        except DocServicesBridgeError as exc:
            items.append(FolderContactItem(relative, "failed", None, str(exc)))
        except ResourceLimitExceeded as exc:
            raise ContactWorkflowError(str(exc)) from exc
    return FolderContactAnalysis(
        source_root=root,
        profile_id=profile_id,
        area=area,
        recursive=recursive,
        items=tuple(items),
    )


def build_contact_register_plan(
    analysis: FolderContactAnalysis,
    *,
    store: ContactRegisterStore,
) -> ContactRegisterPlan:
    """Compare candidates with active assignments without creating register state."""

    revision = store.revision()
    active = store.list_contacts()
    active_by_key: dict[tuple[str, str, str, str], list[ContactRecord]] = defaultdict(list)
    for contact in active:
        active_by_key[contact.assignment_key].append(contact)
    candidate_groups: dict[tuple[str, str, str, str], list[ContactCandidate]] = defaultdict(list)
    for candidate in analysis.candidates:
        candidate_groups[candidate.assignment_key].append(candidate)
    actions = []
    for key in sorted(candidate_groups):
        group = sorted(candidate_groups[key], key=lambda item: item.candidate_id)
        newest_date = max(candidate.effective_date for candidate in group)
        newest = [candidate for candidate in group if candidate.effective_date == newest_date]
        newest_identities = {candidate.identity_key for candidate in newest}
        if len(newest_identities) > 1:
            for candidate in group:
                if candidate.effective_date == newest_date:
                    actions.append(
                        _contact_action(
                            ContactActionKind.BLOCKED,
                            "blocked",
                            candidate,
                            None,
                            revision,
                            "Abweichende Dokumentkontakte besitzen dasselbe neueste "
                            "Wirksamkeitsdatum.",
                        )
                    )
                else:
                    actions.append(
                        _contact_action(
                            ContactActionKind.NOOP,
                            "noop",
                            candidate,
                            None,
                            revision,
                            "Dokumentkontakt ist älter als der neueste Ordnerkontakt.",
                        )
                    )
            continue
        selected = min(newest, key=lambda item: item.candidate_id)
        for candidate in group:
            if candidate.candidate_id != selected.candidate_id:
                message = (
                    "Gleichlautender Dokumentkontakt ist bereits durch einen neueren oder "
                    "deterministisch ausgewählten Ordnerkontakt vertreten."
                )
                actions.append(
                    _contact_action(
                        ContactActionKind.NOOP,
                        "noop",
                        candidate,
                        None,
                        revision,
                        message,
                    )
                )
                continue
            actions.append(
                _compare_contact_candidate(
                    candidate,
                    active_by_key.get(key, []),
                    revision,
                )
            )
    action_tuple = tuple(sorted(actions, key=lambda action: action.candidate.candidate_id))
    plan_id = _plan_id(revision, analysis, action_tuple)
    return ContactRegisterPlan(
        plan_id=plan_id,
        register_revision=revision,
        analysis=analysis,
        actions=action_tuple,
    )


def apply_contact_register_plan(
    plan: ContactRegisterPlan,
    approval: ContactRegisterApproval,
    *,
    store: ContactRegisterStore,
    allow_state_write: bool,
) -> ContactRegisterReport:
    """Apply selected create/replace actions after complete read-only preflight."""

    if not allow_state_write:
        raise ContactWorkflowError("Explizite State-Freigabe für das Kontaktregister fehlt.")
    if (
        approval.plan_id != plan.plan_id
        or approval.register_revision != plan.register_revision
    ):
        raise ContactWorkflowError("Kontaktfreigabe passt nicht zu Plan oder Registerrevision.")
    action_map = {action.action_id: action for action in plan.actions}
    selected = []
    for action_id in approval.action_ids:
        action = action_map.get(action_id)
        if action is None or action.status != "planned" or action.kind not in {
            ContactActionKind.CREATE,
            ContactActionKind.REPLACE,
        }:
            raise ContactWorkflowError(
                f"Kontaktfreigabe nennt keine ausführbare Planaktion: {action_id}"
            )
        selected.append(action)
    if store.revision() != plan.register_revision:
        raise ContactWorkflowError("Kontaktregister wurde seit der Planung verändert.")
    for action in selected:
        source = action.candidate.source_path
        if source.is_symlink() or not source.is_file():
            raise ContactWorkflowError(f"Kontaktquelle fehlt oder ist ein Link: {source}")
        if _sha256_file(source) != action.candidate.source_sha256:
            raise ContactWorkflowError(f"Quellhash hat sich geändert: {source}")
    try:
        created, marked, revision_after = store.apply(
            expected_revision=plan.register_revision,
            actions=tuple(selected),
            approval=approval,
        )
    except ContactRegisterError as exc:
        raise ContactWorkflowError(str(exc)) from exc
    material = json.dumps(
        approval.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return ContactRegisterReport(
        execution_id=f"contact_exec_{sha256(material).hexdigest()}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        register_revision_before=plan.register_revision,
        register_revision_after=revision_after,
        created_contact_ids=created,
        marked_contact_ids=marked,
        register_path=store.path,
    )


def _analysis(
    document: DocumentRecord,
    *,
    status: str,
    candidate: ContactCandidate | None = None,
    issues: tuple[str, ...] = (),
) -> DocumentContactAnalysis:
    return DocumentContactAnalysis(
        document_id=document.document_id,
        source_path=document.source_path,
        source_sha256=document.source_sha256,
        status=status,
        candidate=candidate,
        issues=issues,
    )


def _optional(values: dict[str, tuple[str, int, str]], field: str) -> str | None:
    return values[field][0] if field in values else None


def _normalize_phone(value: str) -> str:
    if re.search(r"[A-Za-z]", value):
        raise ValueError("Telefonnummer enthält Buchstaben.")
    compact = re.sub(r"[\s()/.\-]", "", value)
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if compact.startswith("+"):
        digits = compact[1:]
        normalized = compact
    else:
        digits = compact
        normalized = compact
    if not digits.isdigit() or not 7 <= len(digits) <= 15:
        raise ValueError("Telefonnummer muss 7 bis 15 Ziffern enthalten.")
    return normalized


def _normalize_date(value: str) -> str:
    for pattern in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Gültig-ab-Datum muss YYYY-MM-DD oder DD.MM.YYYY verwenden.")


def _date_from_timestamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise ContactWorkflowError(f"Dokumentzeitpunkt ist ungültig: {value}") from exc


def _action_id(
    kind: ContactActionKind,
    candidate: ContactCandidate,
    prior_contact_id: str | None,
    revision: str,
) -> str:
    material = "\0".join(
        (kind.value, candidate.candidate_id, prior_contact_id or "", revision)
    )
    return f"contact_action_{sha256(material.encode('utf-8')).hexdigest()[:32]}"


def _contact_action(
    kind: ContactActionKind,
    status: str,
    candidate: ContactCandidate,
    prior_contact_id: str | None,
    revision: str,
    message: str,
) -> ContactRegisterAction:
    return ContactRegisterAction(
        action_id=_action_id(kind, candidate, prior_contact_id, revision),
        kind=kind,
        status=status,
        candidate=candidate,
        prior_contact_id=prior_contact_id,
        message=message,
    )


def _compare_contact_candidate(
    candidate: ContactCandidate,
    matches: list[ContactRecord],
    revision: str,
) -> ContactRegisterAction:
    if not matches:
        return _contact_action(
            ContactActionKind.CREATE,
            "planned",
            candidate,
            None,
            revision,
            "Neuen belegten Kontakt nach Freigabe anlegen.",
        )
    if len(matches) > 1:
        return _contact_action(
            ContactActionKind.BLOCKED,
            "blocked",
            candidate,
            None,
            revision,
            "Mehrere aktive Kontakte besitzen denselben Zuständigkeitsschlüssel.",
        )
    current = matches[0]
    if current.identity_key == candidate.identity_key:
        kind = ContactActionKind.NOOP
        status = "noop"
        message = "Kontakt ist bereits mit denselben Kanälen aktiv."
    elif candidate.effective_date > current.effective_date:
        kind = ContactActionKind.REPLACE
        status = "planned"
        message = (
            "Neueren Kontakt anlegen und bisherigen Kontakt nur als Löschkandidat markieren."
        )
    elif candidate.effective_date < current.effective_date:
        kind = ContactActionKind.NOOP
        status = "noop"
        message = "Dokumentkontakt ist älter als der aktive Registerkontakt."
    else:
        kind = ContactActionKind.BLOCKED
        status = "blocked"
        message = "Abweichende Kontakte besitzen dasselbe Wirksamkeitsdatum."
    return _contact_action(
        kind,
        status,
        candidate,
        current.contact_id,
        revision,
        message,
    )


def _plan_id(
    revision: str,
    analysis: FolderContactAnalysis,
    actions: tuple[ContactRegisterAction, ...],
) -> str:
    payload = {
        "schema": ContactRegisterPlan.SCHEMA,
        "register_revision": revision,
        "analysis": analysis.to_dict(),
        "actions": [action.to_dict() for action in actions],
    }
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"contact_plan_{sha256(material).hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
