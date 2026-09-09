"""Packaged v2 journey through real letter/mail adapters and synthetic transport."""

import json
from dataclasses import replace
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from hashlib import sha256
from pathlib import Path

import pytest
from test_local_app import _app
from test_local_recipes import request
from test_recipe_cli_session import confirm, next_section, session
from test_workflow_execution import _mail_draft_request, _recipe_environment

from folderhome.application.recipes import load_bundled_recipe
from folderhome.application.resource_registry import parse_resource_registry
from folderhome.application.workflow_execution import WorkflowExecutionError

RECIPE = "letter-to-mail-draft"
ROUTE = "/api/v1/agent/recipes"


@pytest.fixture
def environment(tmp_path):
    application = _app(tmp_path)
    gateway, registry, transport, _, output = _recipe_environment(
        tmp_path,
        allow_mail_draft=True,
    )
    # Own editable copies: never mutate packaged examples in a test.
    local_resources = []
    for resource in registry.resources:
        if resource.resource_id in {"letter_templates", "letter_designs"}:
            target = tmp_path / (resource.resource_id + ".json")
            target.write_bytes(resource.local_path.read_bytes())
            resource = replace(resource, local_path=target)
        local_resources.append(resource)
    registry = replace(registry, resources=tuple(local_resources))
    for adapter in gateway._adapters.values():
        adapter._registry = registry
    application.resource_registry = registry
    application.workflow_executor = gateway
    yield application, transport, output
    application.close()


def start(app):
    response = request(
        app,
        ROUTE + "/plan",
        payload={
            "schema": "folderhome.local-recipe-plan-request.v1",
            "profile_id": "lukas",
            "recipe_id": RECIPE,
            "language": "de",
        },
    )
    assert response.status_code == 200, response.payload
    return response.payload


def approve(app, proposal):
    plan = proposal["plan"]
    return request(
        app,
        "/api/v1/agent/confirm",
        payload={
            "schema": "folderhome.local-agent-confirmation-request.v1",
            "plan_id": plan["plan_id"],
            "plan_sha256": plan["plan_sha256"],
            "step_ids": [step["step_id"] for step in plan["steps"]],
        },
    )


def following(app, proposal):
    return request(
        app,
        ROUTE + "/next",
        payload={
            "schema": "folderhome.local-recipe-next-request.v1",
            "profile_id": "lukas",
            "run_id": proposal["run"]["run_id"],
        },
    )


def resource_file(app, resource_id):
    return next(
        r.local_path for r in app.resource_registry.resources if r.resource_id == resource_id
    )


def mutate(app, kind):
    name = "letter_templates" if kind == "template" else "letter_request"
    path = resource_file(app, name)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if kind == "recipient":
        raw["recipient"]["email"] = "changed@example.invalid"
    elif kind == "content":
        raw["variables"]["policy_number"] = "SYN-CHANGED"
    elif kind == "template":
        raw["templates"][0]["paragraphs"].append("Zusätzlicher geänderter Absatz.")
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")


def test_catalog_recipe_is_v2_with_two_explicit_result_bindings(environment):
    app, transport, output = environment
    recipe = load_bundled_recipe(RECIPE)
    assert recipe.to_dict()["schema"] == "folderhome.capability-recipe.v2"
    assert [s.workflow_id for s in recipe.steps] == ["correspondence-studio", "mail-connector"]
    assert {b.target_field for b in recipe.result_bindings} == {"expected_preview_id", "planned_at"}
    assert "planned_at" not in recipe.steps[1].request
    for language in ("en", "de"):
        catalog = app.recipe_catalog_payload(profile_id="lukas", language=language)
        entry = next(item for item in catalog["recipes"] if item["recipe_id"] == RECIPE)
        assert entry["approval_mode"] == "per_section" and entry["available"]
    assert transport.appended == [] and list(output.iterdir()) == []


def test_documented_registry_example_has_all_required_recipe_resources(environment):
    app, _, _ = environment
    example = Path(__file__).parents[1] / "examples/resources/letter-to-mail-draft.example.json"
    payload = json.loads(example.read_text(encoding="utf-8"))
    # Substitute real temporary paths only; verify the documented IDs/purposes/operations.
    paths = {r.resource_id: r.local_path for r in app.resource_registry.resources}
    for resource in payload["resources"]:
        resource["locator"]["path"] = str(paths[resource["resource_id"]])
    registry = parse_resource_registry(
        payload,
        expected_os_account="synthetic-family-account",
        known_profile_ids=frozenset({"lukas"}),
    )
    app.resource_registry = registry
    for adapter in app.workflow_executor._adapters.values():
        adapter._registry = registry
    first = start(app)
    assert approve(app, first).status_code == 200
    second = following(app, first)
    assert second.status_code == 200, second.payload
    assert approve(app, second.payload).payload["recipe_run"]["status"] == "completed"


def test_normal_api_keeps_exact_letter_and_requires_two_confirmations(environment):
    app, transport, output = environment
    first = start(app)
    assert len(first["plan"]["steps"]) == 1
    assert list(output.iterdir()) == [] and transport.appended == []
    result = approve(app, first)
    assert result.status_code == 200, result.payload
    assert result.payload["recipe_run"]["status"] == "ready"
    letter = result.payload["execution_reports"][0]["domain_report"]
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert len(before) == 2 and transport.appended == []
    stored = app.execution_results_payload(profile_id="lukas", limit=25)["results"][0]
    assert {item["name"] for item in stored["artifacts"]} == set(before)
    for artifact in stored["artifacts"]:
        downloaded = request(
            app,
            f"/api/v1/agent/results/{stored['execution_id']}/artifacts/{artifact['index']}",
        )
        assert downloaded.status_code == 200
        assert downloaded.content == before[artifact["name"]]
    text = before[letter["text_name"]].decode("utf-8")
    assert sha256(before[letter["text_name"]]).hexdigest() == letter["text_sha256"]
    second = following(app, first)
    assert second.status_code == 200, second.payload
    proposal = second.payload
    assert transport.appended == []
    plan = proposal["plan"]["steps"][0]["execution_envelope"]["domain_plan"]
    assert plan["expected_preview_id"] == plan["correspondence_preview_id"] == letter["preview_id"]
    assert plan["body_sha256"] == letter["text_sha256"]
    assert plan["planned_at"] == letter["approved_at"]
    bindings = proposal["plan"]["approval_context"]["result_bindings"]
    assert {b["value"] for b in bindings} == {letter["preview_id"], letter["approved_at"]}
    final = approve(app, proposal)
    assert final.status_code == 200, final.payload
    assert final.payload["recipe_run"]["status"] == "completed"
    assert len(transport.appended) == 1
    assert final.payload["execution_reports"][0]["domain_report"]["email_sent"] is False
    folder, raw = transport.appended[0]
    message = BytesParser(policy=policy.default).parsebytes(raw)
    assert folder == "INBOX.Drafts"
    assert message["To"].addresses[0].addr_spec == "erika@example.invalid"
    assert message.get_content().replace("\r\n", "\n") == text
    assert parsedate_to_datetime(message["Date"]) == datetime.fromisoformat(
        letter["approved_at"]
    ).replace(microsecond=0)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert approve(app, proposal).status_code == 400
    assert following(app, first).status_code == 400
    assert len(transport.appended) == 1
    public = json.dumps([first, result.payload, proposal, final.payload])
    for private in (str(output), "synthetisches-postfach-geheimnis", "erika@example.invalid"):
        assert private not in public


@pytest.mark.parametrize("kind", ["content", "recipient", "template"])
def test_changed_letter_between_sections_is_rejected_before_mail_preparation(environment, kind):
    app, transport, output = environment
    first = start(app)
    assert approve(app, first).status_code == 200
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    mutate(app, kind)
    second = following(app, first)
    assert second.status_code != 200
    assert transport.appended == []
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    status = app.recipe_runs_payload(profile_id="lukas")["runs"][0]
    assert status["completed_step_refs"] == ["letter"]
    assert status["pending_plan_id"] is None


def test_changed_request_after_second_review_cannot_replace_prepared_message(environment):
    app, transport, _ = environment
    first = start(app)
    assert approve(app, first).status_code == 200
    second = following(app, first)
    assert second.status_code == 200, second.payload
    mutate(app, "recipient")
    mutate(app, "content")
    assert approve(app, second.payload).status_code == 200
    message = BytesParser(policy=policy.default).parsebytes(transport.appended[0][1])
    assert message["To"].addresses[0].addr_spec == "erika@example.invalid"
    assert "SYN-4711" in message.get_content() and "SYN-CHANGED" not in message.get_content()


def test_without_mail_gate_letter_remains_but_no_mailbox_write(environment):
    app, transport, output = environment
    app.workflow_executor._adapters["mail-connector"]._allow_mail_draft = False
    first = start(app)
    assert approve(app, first).status_code == 200
    second = following(app, first)
    assert second.status_code == 200
    outcome = approve(app, second.payload)
    assert outcome.status_code == 200
    assert outcome.payload["recipe_run"]["status"] == "aborted"
    assert transport.appended == [] and len(list(output.iterdir())) == 2
    assert following(app, first).status_code != 200


def test_packaged_recipe_works_in_real_cli_loop(environment, monkeypatch):
    app, transport, output = environment
    status, events = session(
        monkeypatch,
        app,
        [
            "/recipes",
            f"/recipe {RECIPE}",
            confirm,
            next_section,
            confirm,
            "/quit",
        ],
    )
    assert status == 0
    assert len(transport.appended) == 1 and len(list(output.iterdir())) == 2
    outcomes = [e["result"] for e in events if e["event"] == "confirmation"]
    assert [e["recipe_run"]["status"] for e in outcomes] == ["ready", "completed"]


def test_adapter_accepts_matching_expected_preview_id_and_binds_it(environment):
    app, transport, _ = environment
    gateway = app.workflow_executor
    ordinary = gateway.prepare(
        workflow_id="mail-connector",
        profile_id="lukas",
        request=_mail_draft_request(),
    )
    expected = ordinary.domain_plan["correspondence_preview_id"]
    bound = gateway.prepare(
        workflow_id="mail-connector",
        profile_id="lukas",
        request={
            **_mail_draft_request(),
            "expected_preview_id": expected,
        },
    )
    assert bound.domain_plan["expected_preview_id"] == expected
    assert bound.envelope_id != ordinary.envelope_id
    assert bound.domain_plan["message_sha256"] == ordinary.domain_plan["message_sha256"]
    assert transport.appended == []


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        3,
        "",
        "correspondence_preview_" + "G" * 64,
        "correspondence_preview_" + "a" * 64 + "\n",
    ],
)
def test_adapter_rejects_malformed_expected_id_before_reading_resources(
    environment, monkeypatch, value
):
    app, transport, _ = environment
    adapter = app.workflow_executor._adapters["mail-connector"]

    def forbidden(**kwargs):
        pytest.fail("Invalid expected ID reached resource reads")

    monkeypatch.setattr(
        type(adapter._registry), "resolve", lambda self, **kwargs: forbidden(**kwargs)
    )
    with pytest.raises(WorkflowExecutionError, match="expected_preview_id"):
        adapter.prepare(
            profile_id="lukas",
            request={
                **_mail_draft_request(),
                "expected_preview_id": value,
            },
        )
    assert transport.appended == []


def test_adapter_rejects_valid_but_different_expected_id(environment):
    app, transport, _ = environment
    with pytest.raises(WorkflowExecutionError, match="Vorschau"):
        app.workflow_executor.prepare(
            workflow_id="mail-connector",
            profile_id="lukas",
            request={
                **_mail_draft_request(),
                "expected_preview_id": "correspondence_preview_" + "0" * 64,
            },
        )
    assert transport.appended == []
