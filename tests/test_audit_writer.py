import json
from pathlib import Path

import pytest

from folderhome import contracts
from folderhome.capabilities import audit


def build_report(*, run_id: str = "run_atomic") -> contracts.RunReport:
    return contracts.RunReport(
        run_id=run_id,
        started_at="2026-08-21T16:30:00Z",
        finished_at="2026-08-21T16:30:01Z",
        status=contracts.RunStatus.EXECUTED,
        plugin_id="folderhome.synthetic",
        capability_id="synthetic.inspect",
        dry_run=True,
        provider=contracts.ProviderProvenance(
            plugin_id="folderhome.synthetic",
            version="0.1.0",
            source_repository="local://folderhome",
            source_revision="working-tree",
        ),
        actions=(),
        decisions=(),
    )


def test_write_report_publishes_one_complete_utf8_json_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "run.json"

    audit.write_report(build_report(), target)

    assert json.loads(target.read_text(encoding="utf-8"))["run_id"] == "run_atomic"
    assert [path.name for path in target.parent.iterdir()] == ["run.json"]


def test_write_report_refuses_to_replace_a_different_run(tmp_path: Path) -> None:
    target = tmp_path / "run.json"
    audit.write_report(build_report(run_id="run_first"), target)

    with pytest.raises(audit.ReportConflictError, match="run_first.*run_second"):
        audit.write_report(build_report(run_id="run_second"), target)

    assert json.loads(target.read_text(encoding="utf-8"))["run_id"] == "run_first"
