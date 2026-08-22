"""Build evidence-bound administrative drafts through the correspondence core."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from folderhome.application.correspondence import (
    CorrespondenceError,
    build_correspondence_preview,
    write_correspondence_outputs,
)
from folderhome.contracts.administrative_drafts import (
    AdministrativeDraftApproval,
    AdministrativeDraftFact,
    AdministrativeDraftKind,
    AdministrativeDraftOutputReport,
    AdministrativeDraftPlan,
    AdministrativeDraftRequest,
)
from folderhome.contracts.correspondence import (
    CorrespondenceConfiguration,
    CorrespondenceParty,
    CorrespondenceRequest,
)
from folderhome.contracts.official_notices import OfficialNoticeAnalysis

_TEMPLATE_BINDING = {
    AdministrativeDraftKind.OBJECTION: (
        "widerspruchsentwurf",
        "official-objection-draft",
    ),
    AdministrativeDraftKind.AUTHORITY_RESPONSE: (
        "behoerdenantwortentwurf",
        "official-response-draft",
    ),
    AdministrativeDraftKind.BENEFIT_APPLICATION: (
        "leistungsantragsentwurf",
        "benefit-application-draft",
    ),
}
_REVIEW_NOTICE = (
    "ENTWURF – nicht versandt und nicht rechtlich geprüft. Fristen, "
    "Zuständigkeit und Inhalt müssen vor Verwendung menschlich geprüft werden."
)


class AdministrativeDraftError(RuntimeError):
    """Raised before an unsupported or insufficiently bound draft operation."""


def load_administrative_draft_request(path: Path) -> AdministrativeDraftRequest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdministrativeDraftError(f"Entwurfsanfrage ist nicht lesbar: {exc}") from exc
    expected = {
        "schema",
        "draft_kind",
        "profile_id",
        "created_on",
        "sender",
        "recipient",
        "requested_outcome",
        "user_statements",
        "attachments",
        "expected_notice_source_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise AdministrativeDraftError(
            "Entwurfsanfrage besitzt unbekannte oder fehlende Felder."
        )
    if payload.get("schema") != AdministrativeDraftRequest.SCHEMA:
        raise AdministrativeDraftError("Entwurfsanfrage verwendet ein unbekanntes Schema.")
    try:
        kind = AdministrativeDraftKind(payload["draft_kind"])
        material = {
            "draft_kind": kind,
            "profile_id": _text(payload, "profile_id"),
            "created_on": _text(payload, "created_on"),
            "sender": _party(payload.get("sender"), "Absender"),
            "recipient": _party(payload.get("recipient"), "Empfänger"),
            "requested_outcome": _text(payload, "requested_outcome"),
            "user_statements": _text_list(payload, "user_statements", allow_empty=False),
            "attachments": _text_list(payload, "attachments", allow_empty=True),
            "expected_notice_source_sha256": _optional_text(
                payload,
                "expected_notice_source_sha256",
            ),
        }
        request_material = {
            key: (
                value.value
                if isinstance(value, AdministrativeDraftKind)
                else value.to_dict()
                if isinstance(value, CorrespondenceParty)
                else list(value)
                if isinstance(value, tuple)
                else value
            )
            for key, value in material.items()
        }
        return AdministrativeDraftRequest(
            request_id=f"admin_draft_request_{_json_sha(request_material)}",
            **material,
        )
    except (TypeError, ValueError) as exc:
        raise AdministrativeDraftError(f"Entwurfsanfrage ist ungültig: {exc}") from exc


def build_administrative_draft_plan(
    request: AdministrativeDraftRequest,
    *,
    notice_analysis: OfficialNoticeAnalysis | None,
    correspondence_configuration: CorrespondenceConfiguration,
    report_forge_revision: str,
    report_forge_distribution_version: str,
    report_forge_runtime_version: str,
) -> AdministrativeDraftPlan:
    needs_notice = request.draft_kind is not AdministrativeDraftKind.BENEFIT_APPLICATION
    if needs_notice and notice_analysis is None:
        raise AdministrativeDraftError("Bescheidentwurf benötigt eine aktuelle Analyse.")
    if not needs_notice and notice_analysis is not None:
        raise AdministrativeDraftError("Antragsentwurf darf keinen Bescheid voraussetzen.")

    facts: list[AdministrativeDraftFact] = []
    unresolved: list[str] = []
    warnings = [
        "Keine Rechtsprüfung durchgeführt; der Entwurf wurde nicht versandt.",
        "Fristen, Zuständigkeit und Inhalt müssen vor Verwendung geprüft werden.",
    ]
    variables = {
        "requested_outcome": request.requested_outcome,
        "user_statements": " | ".join(request.user_statements),
        "review_notice": _REVIEW_NOTICE,
    }
    evidence_refs: list[str] = []
    source_path: Path | None = None
    source_sha256: str | None = None
    analysis_id: str | None = None

    if notice_analysis is not None:
        _validate_notice_binding(request, notice_analysis)
        source_path = notice_analysis.source_path
        source_sha256 = notice_analysis.source_sha256
        analysis_id = notice_analysis.analysis_id
        evidence_refs.extend((analysis_id, notice_analysis.document_id))
        variables.update(
            {
                "notice_type": notice_analysis.notice_type or "nicht eindeutig",
                "notice_date": notice_analysis.notice_date or "nicht eindeutig",
                "file_reference": notice_analysis.file_reference or "nicht eindeutig",
            }
        )
        for evidence in notice_analysis.evidence:
            fact = _document_fact(evidence.field_name, evidence.value, evidence.line_number,
                                  evidence.document_id, evidence.source_sha256)
            facts.append(fact)
            evidence_refs.append(fact.fact_id)
        unresolved.extend(notice_analysis.missing_fields)
        unresolved.extend(f"Konflikt: {item.field_name}" for item in notice_analysis.conflicts)
        if notice_analysis.explicit_deadline_date is None:
            unresolved.append("Kein ausdrücklich gedrucktes Fristdatum vorhanden.")
        warnings.extend(notice_analysis.warnings)

    for statement in request.user_statements:
        facts.append(_user_fact(statement))
    facts.append(_user_fact(f"Gewünschtes Ergebnis: {request.requested_outcome}"))
    purpose, template_id = _TEMPLATE_BINDING[request.draft_kind]
    correspondence_request = CorrespondenceRequest(
        profile_id=request.profile_id,
        area="sozialrecht",
        purpose=purpose,
        template_id=template_id,
        created_on=request.created_on,
        sender=request.sender,
        recipient=request.recipient,
        variables=tuple(sorted(variables.items())),
        attachments=request.attachments,
        evidence_refs=tuple(evidence_refs),
    )
    try:
        preview = build_correspondence_preview(
            correspondence_request,
            configuration=correspondence_configuration,
            report_forge_revision=report_forge_revision,
            report_forge_distribution_version=report_forge_distribution_version,
            report_forge_runtime_version=report_forge_runtime_version,
        )
    except CorrespondenceError as exc:
        raise AdministrativeDraftError(f"Korrespondenzbaustein blockiert: {exc}") from exc
    plan_material = {
        "request_id": request.request_id,
        "notice_analysis_id": analysis_id,
        "facts": [item.to_dict() for item in facts],
        "unresolved_items": unresolved,
        "preview_id": preview.preview_id,
        "markdown_sha256": preview.markdown_sha256,
        "text_sha256": preview.text_sha256,
    }
    return AdministrativeDraftPlan(
        plan_id=f"admin_draft_plan_{_json_sha(plan_material)}",
        request=request,
        notice_analysis_id=analysis_id,
        notice_source_path=source_path,
        notice_source_sha256=source_sha256,
        facts=tuple(facts),
        unresolved_items=tuple(dict.fromkeys(unresolved)),
        warnings=tuple(dict.fromkeys(warnings)),
        correspondence_preview=preview,
    )


def write_administrative_draft(
    plan: AdministrativeDraftPlan,
    approval: AdministrativeDraftApproval,
    *,
    markdown_file: Path,
    text_file: Path,
    allow_output_write: bool,
) -> AdministrativeDraftOutputReport:
    if not allow_output_write:
        raise AdministrativeDraftError("Output-Gate für den Verwaltungsentwurf fehlt.")
    expected = (
        plan.plan_id,
        plan.correspondence_preview.markdown_sha256,
        plan.correspondence_preview.text_sha256,
    )
    actual = (approval.plan_id, approval.markdown_sha256, approval.text_sha256)
    if actual != expected:
        raise AdministrativeDraftError("Entwurfsfreigabe stimmt nicht mit dem Plan überein.")
    if not (
        approval.confirmed_content_review
        and approval.confirmed_no_legal_review
        and approval.allow_local_output_write
    ):
        raise AdministrativeDraftError("Entwurfsfreigabe ist unvollständig.")
    if plan.notice_source_path is not None and _file_sha(
        plan.notice_source_path
    ) != plan.notice_source_sha256:
        raise AdministrativeDraftError("Bescheid-Quellhash hat sich seit dem Plan geändert.")
    try:
        output = write_correspondence_outputs(
            plan.correspondence_preview,
            markdown_file=markdown_file,
            text_file=text_file,
            allow_output_write=True,
        )
    except CorrespondenceError as exc:
        raise AdministrativeDraftError(str(exc)) from exc
    report_material = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "correspondence_report_id": output.report_id,
    }
    return AdministrativeDraftOutputReport(
        report_id=f"admin_draft_output_{_json_sha(report_material)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        correspondence_output=output,
        status="executed",
    )


def _validate_notice_binding(
    request: AdministrativeDraftRequest,
    analysis: OfficialNoticeAnalysis,
) -> None:
    if request.expected_notice_source_sha256 != analysis.source_sha256:
        raise AdministrativeDraftError("Bescheid-Quellhash stimmt nicht mit der Anfrage überein.")
    if request.profile_id != analysis.profile_id:
        raise AdministrativeDraftError("Profil und Bescheidanalyse stimmen nicht überein.")
    if _file_sha(analysis.source_path) != analysis.source_sha256:
        raise AdministrativeDraftError("Bescheid-Quellhash hat sich geändert.")
    required = {
        "Bescheidart": analysis.notice_type,
        "Behörde": analysis.authority,
        "Aktenzeichen": analysis.file_reference,
        "Bescheiddatum": analysis.notice_date,
    }
    missing = next((label for label, value in required.items() if value is None), None)
    if missing:
        raise AdministrativeDraftError(f"Bescheidentwurf benötigt eindeutige Angabe: {missing}")
    if request.recipient.name.casefold() != (analysis.authority or "").casefold():
        raise AdministrativeDraftError("Empfänger stimmt nicht mit der gelesenen Behörde überein.")
    if request.draft_kind is AdministrativeDraftKind.OBJECTION and (
        analysis.legal_remedy is None
        or "widerspruch" not in analysis.legal_remedy.casefold()
    ):
        raise AdministrativeDraftError(
            "Widerspruchsentwurf benötigt den ausdrücklich gelesenen Rechtsbehelf Widerspruch."
        )


def _document_fact(
    field_name: str,
    value: str,
    line_number: int,
    document_id: str,
    source_sha256: str,
) -> AdministrativeDraftFact:
    material = {
        "basis": "document_evidence",
        "field_name": field_name,
        "value": value,
        "line_number": line_number,
        "document_id": document_id,
        "source_sha256": source_sha256,
    }
    return AdministrativeDraftFact(
        fact_id=f"admin_draft_fact_{_json_sha(material)}",
        text=value,
        basis="document_evidence",
        field_name=field_name,
        line_number=line_number,
        document_id=document_id,
        source_sha256=source_sha256,
    )


def _user_fact(value: str) -> AdministrativeDraftFact:
    material = {"basis": "user_provided", "text": value}
    return AdministrativeDraftFact(
        fact_id=f"admin_draft_fact_{_json_sha(material)}",
        text=value,
        basis="user_provided",
        field_name=None,
        line_number=None,
        document_id=None,
        source_sha256=None,
    )


def _party(value: object, label: str) -> CorrespondenceParty:
    if not isinstance(value, dict) or set(value) != {
        "name",
        "address_lines",
        "email",
        "phone",
    }:
        raise ValueError(f"{label} besitzt unbekannte oder fehlende Felder.")
    address_lines = value.get("address_lines")
    if not isinstance(address_lines, list) or not all(
        isinstance(item, str) for item in address_lines
    ):
        raise ValueError(f"{label} benötigt Anschriftzeilen.")
    for field in ("email", "phone"):
        if value.get(field) is not None and not isinstance(value[field], str):
            raise ValueError(f"{label}.{field} muss Text oder null sein.")
    return CorrespondenceParty(
        name=_text(value, "name"),
        address_lines=tuple(address_lines),
        email=value.get("email"),
        phone=value.get("phone"),
    )


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} benötigt Text.")
    return value


def _optional_text(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} muss Text oder null sein.")
    return value


def _text_list(
    payload: dict[str, object],
    key: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{key} benötigt eine Liste.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{key} enthält ungültige Einträge.")
    return tuple(value)


def _file_sha(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise AdministrativeDraftError(f"Bescheidquelle ist nicht lesbar: {exc}") from exc
    return digest.hexdigest()


def _json_sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
