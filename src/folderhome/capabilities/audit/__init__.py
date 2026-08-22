"""Run-report persistence."""

import json
import os
import tempfile
from pathlib import Path

from folderhome.contracts import RunReport


class ReportConflictError(RuntimeError):
    """Raised when a report path already belongs to another run."""


def write_report(report: RunReport, target: Path) -> None:
    """Atomically publish one UTF-8 JSON run report."""

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        existing_run_id = existing.get("run_id")
        if existing_run_id != report.run_id:
            raise ReportConflictError(
                f"Report path belongs to {existing_run_id}, not {report.run_id}"
            )
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
