"""Real session loop and calendar execution, synthetic HTTP and stdin only."""

import json
from argparse import Namespace
from io import StringIO

import pytest
from test_google_calendar_workflow import prepare_uncertain_calendar_app
from test_google_calendar_workflow import setup as setup


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("route", ["ordinary", "recipe"])
@pytest.mark.parametrize("confirmed_count", [0, 1])
def test_cli_reports_uncertain_effect_and_confirmed_subset_without_success_exit(
    setup, tmp_path, monkeypatch, capsys, as_json, route, confirmed_count
):
    from folderhome import cli

    app, prepared, service, body, secret = prepare_uncertain_calendar_app(
        setup,
        tmp_path,
        route,
        confirmed_count,
    )
    monkeypatch.setattr(cli, "_prepare_local_app", lambda args: app)
    monkeypatch.setattr(cli.sys, "stdin", StringIO(f"/confirm {prepared.plan_id}\n/quit\n"))
    try:
        status = cli._run_strands_agent_session(Namespace(profile_id="lukas", as_json=as_json))
        output = capsys.readouterr().out
        assert status == 2, "Uncertain or aborted execution must not produce a success exit"
        assert str(secret) not in output and "synthetic-token" not in output
        assert "private readback text" not in output
        assert len(service.events) == confirmed_count + 1
        if as_json:
            events = [json.loads(line) for line in output.splitlines()]
            outcome = next(
                item for item in events if item["event"] in {"execution_uncertain", "confirmation"}
            )
            report = outcome if route == "ordinary" else outcome["result"]
            assert report["execution_outcome_unknown"] is True
            assert report["retry_safe"] is False
            refs = report["uncertain_results"][0]["evidence"]["confirmed_event_references"]
            assert len(refs) == confirmed_count
            assert all(ref["provider_event_id"] in service.events for ref in refs)
            assert outcome["plan_id"] == prepared.plan_id
        else:
            assert "Do not retry automatically" in output
            assert f"Confirmed calendar entries: {confirmed_count}" in output
            if confirmed_count:
                refs = app.execution_results_payload(profile_id="lukas", limit=25)["results"][0][
                    "evidence"
                ]["confirmed_event_references"]
                assert refs[0]["provider_event_id"] in output
        before = len(service.calls)
        monkeypatch.setattr(cli.sys, "stdin", StringIO(f"/confirm {prepared.plan_id}\n/quit\n"))
        assert cli._run_strands_agent_session(Namespace(profile_id="lukas", as_json=as_json)) == 2
        assert len(service.calls) == before
    finally:
        app.close()


@pytest.mark.parametrize("as_json", [False, True])
def test_cli_reports_a_rejected_recipe_as_aborted_not_as_uncertain_or_successful(
    setup, tmp_path, monkeypatch, capsys, as_json
):
    from folderhome import cli

    app, prepared, service, body, secret = prepare_uncertain_calendar_app(
        setup, tmp_path, "recipe", 0,
    )
    app.workflow_executor._adapters["calendar-connectors"]._allowed = False
    monkeypatch.setattr(cli, "_prepare_local_app", lambda args: app)
    monkeypatch.setattr(cli.sys, "stdin", StringIO(f"/confirm {prepared.plan_id}\n/quit\n"))
    try:
        status = cli._run_strands_agent_session(Namespace(profile_id="lukas", as_json=as_json))
        output = capsys.readouterr().out
        assert status == 2
        assert service.calls == [] and service.events == {}
        if as_json:
            events = [json.loads(line) for line in output.splitlines()]
            result = next(item["result"] for item in events if item["event"] == "confirmation")
            assert result["execution_outcome_unknown"] is False
            assert result["recipe_execution"]["status"] == "aborted"
            assert result["recipe_execution"]["failed_step_refs"] == ["calendar"]
        else:
            assert "Recipe aborted" in output and "failed_step_refs" in output
            assert "uncertain" not in output.casefold()
    finally:
        app.close()
