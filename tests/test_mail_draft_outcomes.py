"""A lost reply or receipt must not erase an already possible mailbox effect."""

import json

import pytest
from test_local_app import _api_headers, _app
from test_mail_draft import (
    PLANNED_AT,
    _account_file,
    _FakeImapConnection,
    _imap_transport,
    _password_file,
    _preview,
)
from test_workflow_execution import _mail_draft_registry, _mail_draft_request

from folderhome.application import workflow_execution as workflow
from folderhome.application.mail_draft import (
    append_mail_draft,
    build_mail_draft_message,
    load_mail_draft_account,
)
from folderhome.application.recipes import build_recipe_plan
from folderhome.capabilities.mail_draft import (
    MailDraftError,
    MailDraftLedger,
    MailDraftOutcomeUnknown,
    SyntheticDraftTransport,
)
from folderhome.contracts.recipes import CapabilityRecipe, CapabilityRecipeStep


@pytest.mark.parametrize("route", ["ordinary", "recipe"])
@pytest.mark.parametrize("failure", [
    "reply", "ledger", "reply_and_ledger", "report", "reply_and_retention",
    "reply_and_evidence",
])
def test_possible_mail_effect_remains_visible_and_nonrepeatable(
    tmp_path, monkeypatch, route, failure,
):
    registry, _ = _mail_draft_registry(tmp_path)

    class Transport(SyntheticDraftTransport):
        def append_draft(self, *, folder, message_bytes):
            reference = super().append_draft(folder=folder, message_bytes=message_bytes)
            if failure in {
                "reply", "reply_and_ledger", "reply_and_retention", "reply_and_evidence",
            }:
                raise OSError("private response includes synthetic-password")
            return reference

    transport = Transport()

    def make_gateway():
        return workflow.WorkflowExecutionGateway((workflow.MailDraftWorkflowAdapter(
            registry=registry, state_dir=tmp_path / "mail-state",
            report_forge_revision="0123456789abcdef0123456789abcdef01234567",
            report_forge_distribution_version="1.1.4", report_forge_runtime_version="1.1.0",
            allow_mail_draft=True, transport_factory=lambda account: transport,
        ),))

    gateway = make_gateway()
    recipe = CapabilityRecipe(
        recipe_id="synthetic-mail-outcome", title_en="Draft", title_de="Entwurf",
        summary_en="Save one draft", summary_de="Einen Entwurf ablegen",
        lead_expert_id="communication_expert",
        steps=(CapabilityRecipeStep(
            step_ref="draft", workflow_id="mail-connector", expert_id="communication_expert",
            goal_en="Save draft", goal_de="Entwurf ablegen", request=_mail_draft_request(),
        ),),
    )
    prepared = build_recipe_plan(
        recipe, profile_id="lukas", language="en",
        prepare=lambda workflow_id, request: gateway.prepare(
            workflow_id=workflow_id, profile_id="lukas", request=request,
        ), endpoint_statuses={"mail-connector": "connected"},
        known_resource_ids=frozenset(r.resource_id for r in registry.resources),
    )
    envelope = prepared.plan.steps[0].execution_envelope
    app = _app(tmp_path)
    app.workflow_executor = gateway
    app.resource_registry = registry
    app._retain_agent_plan(prepared.plan)
    if route == "recipe":
        app._recipe_plans[prepared.plan_id] = prepared

    def fail(*args, **kwargs):
        raise OSError("private receipt includes synthetic-password")

    if failure in {"ledger", "reply_and_ledger"}:
        monkeypatch.setattr(MailDraftLedger, "finish", fail)
    if failure == "report":
        monkeypatch.setattr(workflow, "WorkflowExecutionReport", fail)
    if failure == "reply_and_retention":
        monkeypatch.setattr(app, "_retain_uncertain_result", fail)
    if failure == "reply_and_evidence":
        monkeypatch.setattr(workflow.MailDraftWorkflowOutcomeUnknown, "public_evidence", fail)
    body = json.dumps({
        "schema": "folderhome.local-agent-confirmation-request.v1",
        "plan_id": prepared.plan_id, "plan_sha256": prepared.plan.plan_sha256,
        "step_ids": [step.step_id for step in prepared.plan.steps],
    }).encode()
    try:
        response = app.handle(
            method="POST", target="/api/v1/agent/confirm",
            headers=_api_headers(8765, app.session_token), body=body, server_port=8765,
        )
        assert response.status_code == (409 if route == "ordinary" else 200)
        assert response.payload.get("execution_outcome_unknown") is True
        results = app.execution_results_payload(profile_id="lukas", limit=25)["results"]
        if failure == "reply_and_retention":
            assert results == []
            assert response.payload["result_delivery_incomplete"] is True
            results = response.payload["uncertain_results"]
        assert len(results) == 1
        assert results[0]["status"] == "uncertain"
        assert results[0]["retry_safe"] is False
        assert results[0]["possible_side_effects"] == ["external.mailbox.draft_write"]
        evidence = results[0]["evidence"]
        if failure == "reply_and_evidence":
            assert results[0]["evidence_unavailable"] is True
            assert evidence == {}
        else:
            assert evidence["draft_id"] == envelope.domain_plan["draft_id"]
            assert evidence["mailbox_acknowledged"] is (failure in {"ledger", "report"})
        assert "synthetic-password" not in str(response.payload) + str(results)
        assert str(tmp_path) not in str(response.payload) + str(results)
        assert len(transport.appended) == 1
        with pytest.raises(workflow.WorkflowExecutionError, match="bereits ausgeführt"):
            gateway.execute(envelope_id=envelope.envelope_id, approved_at="2026-09-09T17:00:00Z")
        # A new app session must respect the durable reservation too.
        restarted = make_gateway()
        new = restarted.prepare(
            workflow_id="mail-connector", profile_id="lukas", request=_mail_draft_request(),
        )
        with pytest.raises(workflow.WorkflowExecutionError):
            restarted.execute(envelope_id=new.envelope_id, approved_at="2026-09-09T17:01:00Z")
        assert len(transport.appended) == 1
    finally:
        app.close()


@pytest.mark.parametrize("failure", ["login", "folder", "refusal"])
def test_proven_imap_rejection_is_not_recorded_as_a_possible_write(tmp_path, failure):
    account = load_mail_draft_account(_account_file(
        tmp_path, password_file=_password_file(tmp_path), drafts_folder="Entwürfe",
    ))
    message = build_mail_draft_message(
        _preview(tmp_path, recipient_email="service@example.invalid", attachments=[]),
        account=account, planned_at=PLANNED_AT,
    )

    class Connection(_FakeImapConnection):
        def login(self, username, password):
            if failure == "login":
                raise OSError("private authentication failure")
            return super().login(username, password)

    connection = Connection(
        folders=() if failure == "folder" else _FakeImapConnection().folders,
        append_status="NO" if failure == "refusal" else "OK",
    )
    ledger = MailDraftLedger(tmp_path / "state")
    with pytest.raises(MailDraftError):
        append_mail_draft(
            message, account=account, transport=_imap_transport(connection), ledger=ledger,
            allow_mailbox_write=True, appended_at=PLANNED_AT,
        )
    assert ledger.status(message.idempotency_key) == "not_applied"
    assert connection.logged_out is True
    if failure != "refusal":
        assert connection.appended == []


@pytest.mark.parametrize("status", ["reserved", "failed", "uncertain"])
def test_unresolved_durable_attempt_is_not_replayed_or_misreported_as_success(tmp_path, status):
    account = load_mail_draft_account(_account_file(
        tmp_path, password_file=_password_file(tmp_path),
    ))
    message = build_mail_draft_message(
        _preview(tmp_path, recipient_email="service@example.invalid", attachments=[]),
        account=account, planned_at=PLANNED_AT,
    )
    ledger = MailDraftLedger(tmp_path / "state")
    ledger.reserve(message)
    if status != "reserved":
        ledger.finish(message.idempotency_key, status=status, mailbox_reference="")
    transport = SyntheticDraftTransport()
    with pytest.raises(MailDraftOutcomeUnknown) as caught:
        append_mail_draft(
            message, account=account, transport=transport,
            ledger=MailDraftLedger(tmp_path / "state"),
            allow_mailbox_write=True, appended_at=PLANNED_AT,
        )
    assert caught.value.public_evidence()["status"] == "uncertain"
    assert caught.value.public_evidence()["retry_safe"] is False
    assert transport.appended == []
    assert ledger.status(message.idempotency_key) == status
