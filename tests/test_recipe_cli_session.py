"""Actual CLI loop and local section lifecycle; synthetic adapters and input."""

import json
from argparse import Namespace
from dataclasses import replace
from io import StringIO

import pytest
from test_local_recipe_runs import app as app
from test_recipe_results import payload

from folderhome import cli
from folderhome.application.recipes import parse_recipe


def session(monkeypatch, application, commands, *, as_json=True):
    events = []
    original = cli._print_agent_session_event

    def output(payload, *, as_json):
        events.append(payload)
        original(payload, as_json=as_json)

    class Input:
        def isatty(self):
            return False

        def readline(self):
            try:
                command = next(iterator)
                return (command(events) if callable(command) else command) + "\n"
            except StopIteration:
                return ""

    iterator = iter(commands)
    monkeypatch.setattr(cli, "_prepare_local_app", lambda _: application)
    monkeypatch.setattr(cli, "_print_agent_session_event", output)
    monkeypatch.setattr(cli.sys, "stdin", Input())
    status = cli._run_strands_agent_session(
        Namespace(profile_id="lukas", as_json=as_json, language="de")
    )
    return status, events


def proposal(events):
    return next(e["recipe"] for e in reversed(events) if e["event"] == "recipe_plan")


def confirm(events):
    return "/confirm " + proposal(events)["plan"]["plan_id"]


def next_section(events):
    return "/next " + proposal(events)["run"]["run_id"]


@pytest.mark.parametrize("as_json", [True, False])
def test_direct_recipe_commands_complete_two_separately_approved_sections(
    app, monkeypatch, capsys, as_json
):
    application, driver = app

    def no_model(**kwargs):
        pytest.fail("Recipe control must not call a model")

    monkeypatch.setattr(application, "run_agent_chat", no_model)
    status, events = session(monkeypatch, application, [
        "/recipes", "/runs", "/recipe accident-aftercare", confirm,
        "/runs", next_section, confirm, "/runs", "/quit",
    ], as_json=as_json)
    output = capsys.readouterr().out
    assert status == 0
    assert driver.executed == [
        "contact-register", "correspondence-studio", "mail-connector", "calendar-handoff"
    ]
    stages = [e["recipe"] for e in events if e["event"] == "recipe_plan"]
    assert len(stages) == 2
    assert stages[1]["plan"]["approval_context"]["result_bindings"][0]["value"] == "Müller"
    states = [e["runs"]["runs"] for e in events if e["event"] == "recipe_runs"]
    assert states[0] == []
    assert states[1][0]["status"] == "ready"
    assert states[2][0]["status"] == "completed"
    assert application.recipe_runs_payload(profile_id="lukas")["runs"] == []
    if as_json:
        assert [json.loads(line) for line in output.splitlines()] == events
    else:
        assert "Müller" in output and "source_path" in output
        assert "domain_plan" in output and "plan_sha256" in output
        assert "ready" in output and "completed" in output
        assert "/next " in output


@pytest.mark.parametrize("ending", ["quit", "eof", "interrupt"])
def test_session_end_discards_pending_sections_without_execution(app, monkeypatch, ending):
    application, driver = app

    def interrupt(events):
        raise KeyboardInterrupt

    commands = ["/recipe accident-aftercare"]
    if ending == "quit":
        commands.append("/quit")
    if ending == "interrupt":
        commands.append(interrupt)
    status, events = session(monkeypatch, application, commands)
    assert status == 0
    plan_id = proposal(events)["plan"]["plan_id"]
    assert application.proposed_agent_plan(plan_id) is None
    assert application.recipe_runs_payload(profile_id="lukas")["runs"] == []
    assert driver.executed == []
    assert events[-1]["event"] == "closed"


def test_close_invalidates_plan_and_does_not_confirm_or_restart(app, monkeypatch):
    application, driver = app
    status, events = session(monkeypatch, application, [
        "/recipe accident-aftercare",
        lambda e: "/close " + proposal(e)["run"]["run_id"],
        confirm, next_section,
    ])
    assert status == 2
    assert driver.executed == []
    assert len([e for e in events if e["event"] == "error"]) == 2
    assert any(e["event"] == "recipe_closed" for e in events)


@pytest.mark.parametrize("command", [
    "/recipe", "/recipe accident-aftercare extra", "/recipes extra",
    "/runs extra", "/next", "/next missing", "/close missing", "/close",
])
def test_malformed_commands_are_errors_without_effects(app, monkeypatch, command):
    application, driver = app
    status, events = session(monkeypatch, application, [command, "/help"])
    assert status == 2
    assert any(e["event"] == "error" for e in events)
    assert events[-2]["event"] == "help"
    assert driver.executed == []


def test_output_failure_still_closes_app(app, monkeypatch):
    application, driver = app
    first = application.propose_recipe(
        profile_id="lukas", recipe_id="accident-aftercare", language="de"
    )
    monkeypatch.setattr(cli, "_prepare_local_app", lambda _: application)

    def broken_output(*args, **kwargs):
        raise BrokenPipeError

    monkeypatch.setattr(cli, "_print_agent_session_event", broken_output)
    monkeypatch.setattr(cli.sys, "stdin", StringIO("/quit\n"))
    with pytest.raises(BrokenPipeError):
        cli._run_strands_agent_session(Namespace(profile_id="lukas", as_json=True))
    assert application.proposed_agent_plan(first.plan_id) is None
    assert application.recipe_runs_payload(profile_id="lukas")["runs"] == []
    assert driver.executed == []


def test_unknown_section_preserves_failed_steps_and_delivery_warning_in_text(capsys):
    cli._print_agent_session_event({
        "event": "confirmation", "plan_id": "plan_test",
        "result": {
            "execution_outcome_unknown": True, "result_delivery_incomplete": True,
            "recipe_run": {"run_id": "recipe_run_test", "status": "aborted"},
            "recipe_execution": {
                "status": "aborted", "completed_step_refs": ["first"],
                "outcomes": [
                    {"step_ref": "second", "status": "failed"},
                    {"step_ref": "third", "status": "not_attempted"},
                ],
            },
        },
    }, as_json=False)
    output = capsys.readouterr().out
    assert "first" in output and "second" in output and "third" in output
    assert "delivery" in output.lower() and "incomplete" in output.lower()
    assert "Do not retry automatically" in output


def test_chat_proposed_recipe_prints_full_values_before_confirmation(app, capsys):
    application, _ = app
    first = application.propose_recipe(
        profile_id="lukas", recipe_id="accident-aftercare", language="de"
    )
    cli._print_agent_session_event({
        "event": "chat", "conversation": {"turn": 1},
        "agent": {
            "response_text": "Bitte prüfen.",
            "proposed_plans": [first.plan.to_dict()],
            "proposed_recipes": [first.to_dict()],
        },
    }, as_json=False)
    output = capsys.readouterr().out
    assert "domain_plan" in output and "approval_context" in output
    assert first.run_id in output
    application.close()


def test_foreign_profile_plan_is_rejected_before_confirmation_dispatch(app, monkeypatch):
    application, driver = app
    first = application.propose_recipe(
        profile_id="lukas", recipe_id="accident-aftercare", language="de"
    )
    foreign = replace(first.plan, profile_id="hanna")
    monkeypatch.setattr(application, "proposed_agent_plan", lambda _: foreign)

    def forbidden(**kwargs):
        pytest.fail("Foreign profile reached the confirmation boundary")

    monkeypatch.setattr(application, "confirm_agent_plan", forbidden)
    status, events = session(monkeypatch, application, [f"/confirm {first.plan_id}"])
    assert status == 2
    assert any(e["event"] == "error" for e in events)
    assert driver.executed == []


def test_cleanup_failure_has_no_successful_closed_event(app, monkeypatch):
    application, driver = app
    first = application.propose_recipe(
        profile_id="lukas", recipe_id="accident-aftercare", language="de"
    )
    run = application._recipe_runs[first.run_id]
    original = run._discard

    def cannot_discard(ids):
        raise OSError("private cleanup path must not escape")

    monkeypatch.setattr(run, "_discard", cannot_discard)
    status, events = session(monkeypatch, application, ["/quit"])
    assert status == 2
    assert events[-1]["event"] == "error"
    assert not any(e["event"] == "closed" for e in events)
    assert "private cleanup path" not in json.dumps(events)
    assert driver.executed == []
    monkeypatch.setattr(run, "_discard", original)
    application.close()


def test_next_without_confirmation_only_reopens_same_section(app, monkeypatch):
    application, driver = app
    status, events = session(monkeypatch, application, [
        "/recipe accident-aftercare", next_section, "/runs",
    ])
    plans = [e["recipe"] for e in events if e["event"] == "recipe_plan"]
    assert status == 0 and driver.executed == []
    assert plans[0]["plan"] == plans[1]["plan"]
    assert next(e for e in events if e["event"] == "recipe_runs")["runs"]["runs"][0][
        "status"
    ] == "awaiting_approval"


def test_stateless_cli_explains_that_v2_needs_a_session(app, monkeypatch, capsys):
    application, driver = app
    monkeypatch.setattr(cli, "_prepare_local_app", lambda _: application)
    monkeypatch.setattr(cli, "load_bundled_recipe", lambda _: parse_recipe(payload()))
    status = cli._run_recipes_plan(Namespace(
        profile_id="lukas", recipe_id="accident-aftercare", language="de",
    ))
    assert status == 2
    assert "agent session" in capsys.readouterr().out
    assert driver.prepared == [] and driver.executed == []


def test_stateless_catalog_identifies_per_section_approval(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_bundled_recipes", lambda: (parse_recipe(payload()),))
    assert cli._run_recipes_list(Namespace(language="en")) == 0
    item = json.loads(capsys.readouterr().out)["recipes"][0]
    assert item["approval_mode"] == "per_section"
