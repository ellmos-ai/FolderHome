"""Guarded mail ingest, correspondence drafts, and provider-neutral delivery."""

from __future__ import annotations

import json
from contextlib import suppress
from hashlib import sha256
from pathlib import Path

from folderhome.capabilities.mail_gateway import (
    MailActionLedger,
    MailGateway,
    MailGatewayError,
)
from folderhome.contracts.contacts import ContactRecord
from folderhome.contracts.correspondence import CorrespondencePreview
from folderhome.contracts.mail import (
    MailAccountConfiguration,
    MailAttachmentReference,
    MailDraftPreview,
    MailDraftRequest,
    MailFolderReference,
    MailInboundConfiguration,
    MailIngestApproval,
    MailIngestPlan,
    MailIngestReport,
    MailIngestRequest,
    MailOutboundConfiguration,
    MailSendApproval,
    MailSendReport,
)


class MailConnectorError(RuntimeError):
    """Raised when a mail request, provider, or approval is unsafe."""


def load_mail_accounts(path: Path) -> tuple[MailAccountConfiguration, ...]:
    payload = _load_json_object(path, "Mailkonten")
    _strict_fields(payload, {"schema", "accounts"}, "Mailkonten")
    if payload.get("schema") != "folderhome.mail-accounts.v1":
        raise MailConnectorError("Mailkonten verwenden ein unbekanntes Schema.")
    raw_accounts = payload.get("accounts")
    if not isinstance(raw_accounts, list) or not raw_accounts:
        raise MailConnectorError("Mailkonten benötigen eine nichtleere accounts-Liste.")
    accounts = tuple(_parse_account(item, index) for index, item in enumerate(raw_accounts))
    ids = [item.account_id for item in accounts]
    if len(ids) != len(set(ids)):
        raise MailConnectorError("Mailkonto-IDs müssen eindeutig sein.")
    return accounts


def load_mail_ingest_request(path: Path) -> MailIngestRequest:
    payload = _load_json_object(path, "Mail-Ingest-Anfrage")
    _strict_fields(
        payload,
        {
            "schema",
            "request_id",
            "profile_id",
            "account_id",
            "folder",
            "query",
            "max_messages",
            "include_attachments",
            "target_ref",
        },
        "Mail-Ingest-Anfrage",
    )
    if payload.get("schema") != MailIngestRequest.SCHEMA:
        raise MailConnectorError("Mail-Ingest-Anfrage verwendet ein unbekanntes Schema.")
    try:
        return MailIngestRequest(
            request_id=_text(payload, "request_id", "Mail-Ingest-Anfrage"),
            profile_id=_text(payload, "profile_id", "Mail-Ingest-Anfrage"),
            account_id=_text(payload, "account_id", "Mail-Ingest-Anfrage"),
            folder=_text(payload, "folder", "Mail-Ingest-Anfrage"),
            query=_text(payload, "query", "Mail-Ingest-Anfrage"),
            max_messages=_integer(payload, "max_messages", "Mail-Ingest-Anfrage"),
            include_attachments=_boolean(
                payload, "include_attachments", "Mail-Ingest-Anfrage"
            ),
            target_ref=_optional_text(payload, "target_ref", "Mail-Ingest-Anfrage"),
        )
    except ValueError as exc:
        raise MailConnectorError(f"Mail-Ingest-Anfrage ist ungültig: {exc}") from exc


def build_mail_ingest_plan(
    request: MailIngestRequest,
    *,
    account: MailAccountConfiguration,
    provider_ready: bool,
    provider_id: str | None = None,
    provider_revision: str | None = None,
) -> MailIngestPlan:
    """Build a side-effect-free, read-only mailbox access plan."""

    if request.account_id != account.account_id or request.profile_id != account.profile_id:
        raise MailConnectorError("Mail-Ingest-Anfrage passt nicht zum ausgewählten Konto.")
    if request.folder != account.inbound.folder:
        raise MailConnectorError("Mail-Ingest darf nur den konfigurierten Ordner lesen.")
    selected_provider = provider_id or account.inbound.provider_id
    selected_revision = (
        provider_revision
        if provider_id is not None
        else account.inbound.provider_revision
    )
    operations = ("fetch_headers",) + (
        ("fetch_attachments",) if request.include_attachments else ()
    )
    material = {
        "request": request.to_dict(),
        "account_id": account.account_id,
        "provider_id": selected_provider,
        "provider_revision": selected_revision,
        "operations": list(operations),
    }
    plan_sha256 = _json_hash(material)
    return MailIngestPlan(
        plan_id=f"mail_ingest_plan_{plan_sha256}",
        plan_sha256=plan_sha256,
        request=request,
        account_id=account.account_id,
        folder=MailFolderReference(account_id=account.account_id, name=request.folder),
        provider_id=selected_provider,
        provider_revision=selected_revision,
        status="ready" if provider_ready else "blocked",
        reason=(
            "Provider ist für einen explizit freigegebenen read-only Abruf bereit."
            if provider_ready
            else "Provider-Checkout ist nicht revisionsgenau und sauber verfügbar."
        ),
        operations=operations,
    )


def execute_mail_ingest(
    plan: MailIngestPlan,
    *,
    approval: MailIngestApproval,
    gateway: MailGateway,
) -> MailIngestReport:
    if plan.status != "ready":
        raise MailConnectorError("Blockierter Mail-Ingest-Plan darf nicht ausgeführt werden.")
    if approval.plan_id != plan.plan_id:
        raise MailConnectorError("Mail-Ingest-Freigabe gehört zu einem anderen Plan.")
    if approval.plan_sha256 != plan.plan_sha256:
        raise MailConnectorError("Mail-Ingest-Freigabe besitzt einen anderen Planhash.")
    if (
        gateway.provider_id != plan.provider_id
        or gateway.provider_revision != plan.provider_revision
    ):
        raise MailConnectorError("Mail-Gateway stimmt nicht mit dem Planprovider überein.")
    if not gateway.read_only_ingest:
        raise MailConnectorError("Mail-Gateway garantiert keinen read-only Ingest.")
    if gateway.network_required and not approval.allow_network_read:
        raise MailConnectorError("Netzwerk-Lesefreigabe fehlt.")
    if (
        plan.request.include_attachments
        and gateway.network_required
        and not approval.allow_attachment_write
    ):
        raise MailConnectorError("Anhangs-Schreibfreigabe fehlt.")
    messages = gateway.fetch(plan)
    if any(
        message.account_id != plan.account_id or message.folder != plan.folder.name
        for message in messages
    ):
        raise MailConnectorError("Mail-Gateway lieferte Nachrichten außerhalb des Plans.")
    report_material = {
        "plan_id": plan.plan_id,
        "approval_id": approval.approval_id,
        "messages": [item.message_ref for item in messages],
    }
    return MailIngestReport(
        report_id=f"mail_ingest_report_{_json_hash(report_material)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        status="executed",
        messages=messages,
        network_invoked=gateway.network_required,
        attachment_write_invoked=(
            gateway.network_required and plan.request.include_attachments
        ),
    )


def load_mail_draft_request(path: Path) -> MailDraftRequest:
    payload = _load_json_object(path, "Mailentwurfsanfrage")
    _strict_fields(
        payload,
        {
            "schema",
            "request_id",
            "profile_id",
            "account_id",
            "recipient_contact_id",
            "recipient_email",
            "correspondence_preview_id",
            "correspondence_text_sha256",
            "attachments",
        },
        "Mailentwurfsanfrage",
    )
    if payload.get("schema") != MailDraftRequest.SCHEMA:
        raise MailConnectorError("Mailentwurfsanfrage verwendet ein unbekanntes Schema.")
    raw_attachments = payload.get("attachments")
    if not isinstance(raw_attachments, list):
        raise MailConnectorError("Mailentwurfsanfrage benötigt eine attachments-Liste.")
    try:
        attachments = tuple(
            _parse_attachment(item, index) for index, item in enumerate(raw_attachments)
        )
        return MailDraftRequest(
            request_id=_text(payload, "request_id", "Mailentwurfsanfrage"),
            profile_id=_text(payload, "profile_id", "Mailentwurfsanfrage"),
            account_id=_text(payload, "account_id", "Mailentwurfsanfrage"),
            recipient_contact_id=_text(
                payload, "recipient_contact_id", "Mailentwurfsanfrage"
            ),
            recipient_email=_text(
                payload, "recipient_email", "Mailentwurfsanfrage"
            ),
            correspondence_preview_id=_text(
                payload, "correspondence_preview_id", "Mailentwurfsanfrage"
            ),
            correspondence_text_sha256=_text(
                payload, "correspondence_text_sha256", "Mailentwurfsanfrage"
            ),
            attachments=attachments,
        )
    except ValueError as exc:
        raise MailConnectorError(f"Mailentwurfsanfrage ist ungültig: {exc}") from exc


def build_mail_draft_preview(
    request: MailDraftRequest,
    *,
    account: MailAccountConfiguration,
    contact: ContactRecord,
    correspondence: CorrespondencePreview,
) -> MailDraftPreview:
    """Bind one exact contact and one exact correspondence into a read-only draft."""

    if account.account_id != request.account_id or account.profile_id != request.profile_id:
        raise MailConnectorError("Mailentwurf passt nicht zum ausgewählten Konto.")
    if account.outbound is None:
        raise MailConnectorError("Mailkonto besitzt keinen konfigurierten Ausgang.")
    if (
        contact.status != "active"
        or contact.contact_id != request.recipient_contact_id
        or contact.profile_id != request.profile_id
        or contact.email != request.recipient_email
    ):
        raise MailConnectorError(
            "Explizite Empfängerzuordnung stimmt nicht mit dem Kontakt überein."
        )
    if (
        correspondence.preview_id != request.correspondence_preview_id
        or correspondence.text_sha256 != request.correspondence_text_sha256
        or correspondence.request.profile_id != request.profile_id
    ):
        raise MailConnectorError(
            "Korrespondenzreferenz stimmt nicht exakt mit der Vorschau überein."
        )
    if correspondence.request.recipient.email != request.recipient_email:
        raise MailConnectorError("Briefempfänger und explizite Empfängerzuordnung weichen ab.")
    if correspondence.request.sender.email not in {None, account.address}:
        raise MailConnectorError("Briefabsender und ausgewähltes Mailkonto weichen ab.")
    body_sha256 = _text_hash(correspondence.text)
    material = {
        "request_id": request.request_id,
        "profile_id": request.profile_id,
        "account_id": request.account_id,
        "provider_id": account.outbound.provider_id,
        "provider_revision": account.outbound.provider_revision,
        "from": account.address,
        "to": request.recipient_email,
        "contact_id": contact.contact_id,
        "correspondence_preview_id": correspondence.preview_id,
        "subject": correspondence.subject,
        "body_sha256": body_sha256,
        "attachments": [item.to_dict() for item in request.attachments],
    }
    draft_sha256 = _json_hash(material)
    return MailDraftPreview(
        draft_id=f"mail_draft_{draft_sha256}",
        draft_sha256=draft_sha256,
        request_id=request.request_id,
        profile_id=request.profile_id,
        account_id=request.account_id,
        provider_id=account.outbound.provider_id,
        provider_revision=account.outbound.provider_revision,
        from_address=account.address,
        to_address=request.recipient_email,
        contact_id=contact.contact_id,
        correspondence_preview_id=correspondence.preview_id,
        subject=correspondence.subject,
        body_text=correspondence.text,
        body_sha256=body_sha256,
        attachments=request.attachments,
    )


def mail_send_idempotency_key(draft: MailDraftPreview) -> str:
    material = f"{draft.draft_id}\0{draft.draft_sha256}\0{draft.to_address}"
    return f"mail_send_{sha256(material.encode('utf-8')).hexdigest()}"


def execute_mail_send(
    draft: MailDraftPreview,
    *,
    approval: MailSendApproval,
    gateway: MailGateway,
    ledger: MailActionLedger,
) -> MailSendReport:
    """Attempt one exact delivery after binding and reserving all approval data."""

    if (
        approval.draft_id != draft.draft_id
        or approval.draft_sha256 != draft.draft_sha256
    ):
        raise MailConnectorError("Mailversand-Freigabe gehört zu einem anderen Entwurf.")
    if approval.recipient_email != draft.to_address:
        raise MailConnectorError("Mailversand-Freigabe besitzt einen anderen Empfänger.")
    if approval.idempotency_key != mail_send_idempotency_key(draft):
        raise MailConnectorError("Mailversand-Freigabe besitzt falsche Idempotenzbindung.")
    if (
        gateway.provider_id != draft.provider_id
        or gateway.provider_revision != draft.provider_revision
    ):
        raise MailConnectorError("Mail-Gateway stimmt nicht mit dem freigegebenen Entwurf überein.")
    if gateway.network_required and not approval.allow_network_send:
        raise MailConnectorError("Netzwerk-Versandfreigabe fehlt.")
    try:
        ledger.reserve(approval=approval, draft=draft)
    except MailGatewayError as exc:
        raise MailConnectorError(str(exc)) from exc
    try:
        transport_message_id = gateway.send(draft, approval)
        status = "sent" if gateway.network_required else "simulated"
        ledger.finish(
            approval.idempotency_key,
            status=status,
            transport_message_id=transport_message_id,
        )
    except Exception as exc:
        with suppress(MailGatewayError):
            ledger.finish(
                approval.idempotency_key,
                status="failed",
                transport_message_id="",
            )
        if isinstance(exc, MailConnectorError):
            raise
        raise MailConnectorError(f"Mail-Gateway ist fehlgeschlagen: {exc}") from exc
    report_material = {
        "draft_id": draft.draft_id,
        "approval_id": approval.approval_id,
        "idempotency_key": approval.idempotency_key,
        "transport_message_id": transport_message_id,
    }
    return MailSendReport(
        report_id=f"mail_send_report_{_json_hash(report_material)}",
        draft_id=draft.draft_id,
        approval_id=approval.approval_id,
        idempotency_key=approval.idempotency_key,
        status=status,
        provider_id=gateway.provider_id,
        provider_revision=gateway.provider_revision,
        recipient_email=draft.to_address,
        transport_message_id=transport_message_id,
        network_invoked=gateway.network_required,
        email_sent=gateway.network_required,
    )


def _parse_account(raw: object, index: int) -> MailAccountConfiguration:
    label = f"Mailkonto {index + 1}"
    if not isinstance(raw, dict):
        raise MailConnectorError(f"{label} muss ein Objekt sein.")
    _strict_fields(
        raw,
        {"account_id", "profile_id", "display_name", "address", "inbound", "outbound"},
        label,
    )
    inbound = raw.get("inbound")
    outbound = raw.get("outbound")
    if not isinstance(inbound, dict):
        raise MailConnectorError(f"{label}.inbound muss ein Objekt sein.")
    _strict_fields(
        inbound,
        {
            "protocol",
            "host",
            "port",
            "folder",
            "credential_ref",
            "provider_id",
            "provider_revision",
        },
        f"{label}.inbound",
    )
    if outbound is not None and not isinstance(outbound, dict):
        raise MailConnectorError(f"{label}.outbound muss ein Objekt oder null sein.")
    if isinstance(outbound, dict):
        _strict_fields(
            outbound,
            {
                "protocol",
                "host",
                "port",
                "credential_ref",
                "provider_id",
                "provider_revision",
            },
            f"{label}.outbound",
        )
    try:
        return MailAccountConfiguration(
            account_id=_text(raw, "account_id", label),
            profile_id=_text(raw, "profile_id", label),
            display_name=_text(raw, "display_name", label),
            address=_text(raw, "address", label),
            inbound=MailInboundConfiguration(
                protocol=_text(inbound, "protocol", f"{label}.inbound"),
                host=_text(inbound, "host", f"{label}.inbound"),
                port=_integer(inbound, "port", f"{label}.inbound"),
                folder=_text(inbound, "folder", f"{label}.inbound"),
                credential_ref=_text(
                    inbound, "credential_ref", f"{label}.inbound"
                ),
                provider_id=_text(inbound, "provider_id", f"{label}.inbound"),
                provider_revision=_optional_text(
                    inbound, "provider_revision", f"{label}.inbound"
                ),
            ),
            outbound=(
                MailOutboundConfiguration(
                    protocol=_text(outbound, "protocol", f"{label}.outbound"),
                    host=_text(outbound, "host", f"{label}.outbound"),
                    port=_integer(outbound, "port", f"{label}.outbound"),
                    credential_ref=_text(
                        outbound, "credential_ref", f"{label}.outbound"
                    ),
                    provider_id=_text(
                        outbound, "provider_id", f"{label}.outbound"
                    ),
                    provider_revision=_optional_text(
                        outbound, "provider_revision", f"{label}.outbound"
                    ),
                )
                if isinstance(outbound, dict)
                else None
            ),
        )
    except ValueError as exc:
        raise MailConnectorError(f"{label} ist ungültig: {exc}") from exc


def _parse_attachment(raw: object, index: int) -> MailAttachmentReference:
    label = f"Mailanhang {index + 1}"
    if not isinstance(raw, dict):
        raise MailConnectorError(f"{label} muss ein Objekt sein.")
    _strict_fields(
        raw,
        {"attachment_id", "filename", "media_type", "size_bytes", "sha256", "provider_ref"},
        label,
    )
    return MailAttachmentReference(
        attachment_id=_text(raw, "attachment_id", label),
        filename=_text(raw, "filename", label),
        media_type=_text(raw, "media_type", label),
        size_bytes=_integer(raw, "size_bytes", label),
        sha256=_text(raw, "sha256", label),
        provider_ref=_text(raw, "provider_ref", label),
    )


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise MailConnectorError(f"{label} fehlt oder ist kein reguläres File: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MailConnectorError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise MailConnectorError(f"{label} muss ein JSON-Objekt sein.")
    return payload


def _strict_fields(payload: dict[str, object], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload).difference(allowed))
    missing = sorted(allowed.difference(payload))
    if unknown:
        raise MailConnectorError(f"{label} enthält unbekannte Felder: {', '.join(unknown)}")
    if missing:
        raise MailConnectorError(f"{label} benötigt Felder: {', '.join(missing)}")


def _text(payload: dict[str, object], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MailConnectorError(f"{label}.{key} muss nichtleerer Text sein.")
    return value


def _optional_text(payload: dict[str, object], key: str, label: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise MailConnectorError(f"{label}.{key} muss Text oder null sein.")
    return value


def _integer(payload: dict[str, object], key: str, label: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise MailConnectorError(f"{label}.{key} muss eine Ganzzahl sein.")
    return value


def _boolean(payload: dict[str, object], key: str, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise MailConnectorError(f"{label}.{key} muss boolesch sein.")
    return value


def _json_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _text_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
