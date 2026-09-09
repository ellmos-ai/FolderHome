"""Explicitly started, single-job consumer using the pinned scheduler service."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import fields
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from folderhome.application.directory_observation import load_watched_folder_configuration
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.routine_queue import load_folder_routine_bindings
from folderhome.application.scheduler_handoff import (
    _run_id,
    _run_status,
    _safe_state_root,
    _safe_timestamp,
    _write_new_json,
    run_scheduler_queue,
)
from folderhome.application.scheduler_registration import (
    SchedulerRegistrationError,
    SchedulerRegistrationPlan,
    _check_store_identity,
    _job_definition,
    _matches_job,
    _read_job_snapshot,
    _scheduler_provider,
    build_scheduler_registration_plan,
    validate_scheduler_registration_plan,
)
from folderhome.bridges.doc_services import DocServicesBridge
from folderhome.contracts.routine_queue import FolderRoutineQueue
from folderhome.contracts.scheduler import SchedulerHandoffPlan, SchedulerRunReport
from folderhome.plugin_host import load_manifests


def create_scheduler_consumer(
    plan: SchedulerRegistrationPlan, *, confirmed_plan_id: str, allow_consumer_state_write: bool
):
    """Construct a stopped consumer; only explicit tick/serve calls perform runs.

    The provider owns scheduling, leases, run history and the polling loop. This
    adapter binds every tick and execution to one previously registered plan.
    """
    if allow_consumer_state_write is not True or confirmed_plan_id != plan.plan_id:
        raise SchedulerRegistrationError("Separate genaue Consumer-Startfreigabe fehlt.")
    plan = validate_scheduler_registration_plan(plan)
    provider = _scheduler_provider(plan)
    _check_store_identity(plan)
    authority_registry = provider.AuthorityResolverRegistry(include_standard=False)
    store = provider.SchedulerStore(plan.store_path, authority_registry=authority_registry)
    job_id = "folderhome-" + plan.plan_id
    definition = _job_definition(plan)

    def validate_job():
        validate_scheduler_registration_plan(plan)
        _check_store_identity(plan)
        attempt = _safe_state_root(plan.ledger_dir / f"attempt-{plan.plan_id}.json")
        if json.loads(attempt.read_text(encoding="utf-8")) != {
            "schema": "folderhome.scheduler-registration-attempt.v1",
            "plan": plan.to_dict(),
        }:
            raise SchedulerRegistrationError(
                "Registrierungsnachweis stimmt nicht mit dem Job überein."
            )
        row, history = _read_job_snapshot(store, job_id)
        if row is None or not _matches_job(row, definition, history):
            raise SchedulerRegistrationError(
                "Freigegebener Scheduler-Job fehlt oder wurde verändert."
            )

    validate_job()

    def executor(payload, timeout_seconds):
        if payload != definition["payload"] or timeout_seconds != definition["timeout_seconds"]:
            return provider.ExecutionResult(
                "failed", error="Jobdaten entsprechen nicht der Freigabe."
            )
        completed = None
        try:
            validate_scheduler_registration_plan(plan)
            invocation_id = uuid4().hex
            completed = _run_queue_process(plan, timeout_seconds, invocation_id=invocation_id)
            validate_scheduler_registration_plan(plan)
            _verify_child_report(plan, completed, invocation_id=invocation_id)
            return provider.ExecutionResult("succeeded", completed.returncode, completed.stdout)
        except subprocess.TimeoutExpired:
            return provider.ExecutionResult(
                "timed_out", error="Queue-Prozess überschritt sein Zeitlimit; Ergebnis unklar."
            )
        except Exception as exc:
            return provider.ExecutionResult(
                "failed",
                completed.returncode if completed is not None else None,
                completed.stdout if completed is not None else "",
                error=f"Queue-Lauf nicht bestätigt ({type(exc).__name__}): {exc}",
            )

    registry = provider.ExecutorRegistry(include_standard=False)
    registry.register(definition["executor"], executor)

    class BoundSchedulerService(provider.SchedulerService):
        _last_observation = None

        @property
        def last_observation(self):
            return deepcopy(self._last_observation)

        def tick(self, *, now=None, limit=1, job_ids=None):
            if type(limit) is not int or limit != 1 or job_ids not in (None, (job_id,), [job_id]):
                raise SchedulerRegistrationError(
                    "Dieser Consumer darf nur seinen eigenen Job prüfen."
                )
            if now is not None and (not isinstance(now, datetime) or now.tzinfo is None):
                raise SchedulerRegistrationError("Consumer-Zeit benötigt eine Zeitzone.")
            validate_job()
            results = super().tick(now=now, limit=1, job_ids=(job_id,))
            observation = {
                "schema": "folderhome.scheduler-consumer-observation.v1",
                "plan_id": plan.plan_id,
                "job_id": job_id,
                "worker_id": self.worker_id,
                "observed_at": datetime.now(UTC).isoformat(),
                "status": "tick_completed",
                "runs": deepcopy(results),
            }
            try:
                _write_new_json(
                    plan.ledger_dir / f"consumer-{plan.plan_id}-{uuid4().hex}.json", observation
                )
            except (OSError, RuntimeError):
                observation["status"] = "uncertain"
                observation["error"] = "Consumer-Beobachtung konnte nicht gespeichert werden."
            self._last_observation = observation
            return results

    return BoundSchedulerService(store, registry=registry, authority_registry=authority_registry)


def _run_queue_process(plan, timeout_seconds, *, invocation_id):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8:strict"
    # Use this FolderHome installation, not an unrelated editable checkout in
    # the chosen interpreter. No inherited provider-source search paths.
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return subprocess.run(
        [str(plan.handoff.python_executable), "-P", "-m", __name__, "--execute-approved-stdin"],
        input=json.dumps(
            {
                "plan": plan.to_dict(),
                "confirmed_plan_id": plan.plan_id,
                "allow_scheduler_state_write": True,
                "invocation_id": invocation_id,
            },
            ensure_ascii=False,
        ),
        cwd=plan.handoff.working_directory,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=timeout_seconds,
        shell=False,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def _plan_from_payload(payload):
    try:
        material = json.dumps(
            {**payload, "plan_id": ""}, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        if payload["plan_id"] != "registration_" + sha256(material).hexdigest():
            raise SchedulerRegistrationError(
                "Registrierungsinhalt stimmt nicht mit seiner ID überein."
            )
        raw_handoff = payload["handoff"]
        values = {field.name: raw_handoff[field.name] for field in fields(SchedulerHandoffPlan)}
        for name in (
            "config_file",
            "bindings_file",
            "profiles_dir",
            "state_dir",
            "manifest_root",
            "doc_services_root",
            "python_executable",
            "working_directory",
        ):
            if not isinstance(values[name], str):
                raise SchedulerRegistrationError("Ungültiger Konfigurationspfad.")
            values[name] = Path(values[name])
        values["portable_argv"] = tuple(values["portable_argv"])
        authorization_files = payload["authorization_files"]
        if not isinstance(authorization_files, list) or any(
            not isinstance(path, str) for path in authorization_files
        ):
            raise SchedulerRegistrationError("Ungültige Ressourcenfreigabedateien.")
        plan = build_scheduler_registration_plan(
            handoff=SchedulerHandoffPlan(**values),
            store_path=Path(payload["store_path"]),
            ledger_dir=Path(payload["ledger_dir"]),
            provider_root=Path(payload["provider_root"]),
            provider_revision=payload["provider_revision"],
            authorization_files=tuple(Path(path) for path in authorization_files),
        )
        if plan.to_dict() != payload:
            raise SchedulerRegistrationError(
                "Kindprozess sieht nicht mehr die bestätigte Konfiguration."
            )
        return plan
    except (KeyError, TypeError, ValueError, RuntimeError, OSError) as exc:
        raise SchedulerRegistrationError(
            f"Ungültiger freigegebener Registrierungsplan: {exc}"
        ) from exc


def execute_approved_queue(
    payload, *, confirmed_plan_id, allow_scheduler_state_write, invocation_id
):
    """Child boundary: revalidate, load immutable inputs, then invoke the existing runner."""
    if (
        allow_scheduler_state_write is not True
        or not isinstance(payload, dict)
        or payload.get("plan_id") != confirmed_plan_id
        or not isinstance(invocation_id, str)
        or re.fullmatch(r"[0-9a-f]{32}", invocation_id) is None
    ):
        raise SchedulerRegistrationError("Genaue Freigabe für den Queue-Kindprozess fehlt.")
    plan = _plan_from_payload(payload)
    handoff = plan.handoff
    watches = load_watched_folder_configuration(handoff.config_file)
    bindings = load_folder_routine_bindings(handoff.bindings_file)
    profiles = load_profile_configuration(handoff.profiles_dir)
    plugin = next(
        item for item in load_manifests(handoff.manifest_root) if item.plugin_id == "doc-services"
    )
    extractor = DocServicesBridge(plugin=plugin, provider_root=handoff.doc_services_root)
    # Recheck after loading and keep these loaded inputs for the entire run.
    # Changed config must never redirect subsequent extraction to another root.
    validate_scheduler_registration_plan(plan)
    report = run_scheduler_queue(
        handoff,
        captured_at=datetime.now(UTC).isoformat(),
        watches=watches,
        bindings=bindings,
        profiles=profiles,
        extractor=extractor,
        allow_scheduler_state_write=True,
    )
    validate_scheduler_registration_plan(plan)
    envelope = {
        "registration_plan_id": plan.plan_id,
        "invocation_id": invocation_id,
        "report": report.to_dict(),
    }
    _write_new_json(plan.ledger_dir / f"invocation-{invocation_id}.json", envelope)
    return envelope


def _verify_child_report(plan, completed, *, invocation_id):
    if type(completed.returncode) is not int or completed.returncode not in (0, 10):
        raise SchedulerRegistrationError(
            "Queue meldet keinen erfolgreich abgeschlossenen Prüflauf."
        )
    envelope = json.loads(completed.stdout)
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"registration_plan_id", "invocation_id", "report"}
        or envelope["registration_plan_id"] != plan.plan_id
        or envelope["invocation_id"] != invocation_id
    ):
        raise SchedulerRegistrationError(
            "Kindprozessbericht gehört zu einem anderen Plan oder Aufruf."
        )
    report = envelope["report"]
    required = {
        "schema",
        "run_id",
        "schedule_id",
        "captured_at",
        "status",
        "exit_code",
        "queue",
        "completed_file",
        "error",
        "document_side_effects",
        "checkpoint_written",
        "scheduler_registered",
    }
    if not isinstance(report, dict) or set(report) != required:
        raise SchedulerRegistrationError("Queue-Bericht ist unvollständig.")
    if (
        report["schema"] != SchedulerRunReport.SCHEMA
        or report["schedule_id"] != plan.handoff.schedule_id
        or type(report["exit_code"]) is not int
        or report["exit_code"] != completed.returncode
        or report["error"] is not None
        or report["document_side_effects"] != []
        or report["checkpoint_written"] is not False
        or report["scheduler_registered"] is not False
    ):
        raise SchedulerRegistrationError("Queue-Bericht verletzt seinen Vertrag.")
    captured = datetime.fromisoformat(report["captured_at"])
    if captured.tzinfo is None or report["run_id"] != _run_id(
        plan.handoff.schedule_id, report["captured_at"]
    ):
        raise SchedulerRegistrationError("Laufzeit und Lauf-ID sind nicht gebunden.")
    queue = report["queue"]
    if not isinstance(queue, dict) or set(queue) != {
        "schema",
        "queue_id",
        "captured_at",
        "as_of",
        "summary",
        "items",
        "side_effects",
        "scheduler_registered",
    }:
        raise SchedulerRegistrationError("Queue-Inhalt ist unvollständig.")
    if (
        queue["schema"] != FolderRoutineQueue.SCHEMA
        or queue["captured_at"] != report["captured_at"]
        or queue["as_of"] != captured.astimezone(ZoneInfo(plan.handoff.timezone)).date().isoformat()
        or queue["side_effects"] != []
        or queue["scheduler_registered"] is not False
        or not isinstance(queue["items"], list)
    ):
        raise SchedulerRegistrationError("Queue-Inhalt verletzt seinen Vertrag.")
    item_keys = {"watch_id", "binding_id", "target_root", "mode", "status", "reason", "plan"}
    for item in queue["items"]:
        if (
            not isinstance(item, dict)
            or set(item) != item_keys
            or item["status"] not in {"empty", "not_due", "ready"}
        ):
            raise SchedulerRegistrationError("Ungültiger Queue-Eintrag.")
    counts = dict(Counter(item["status"] for item in queue["items"]))
    if not isinstance(queue["summary"], dict) or any(
        type(count) is not int for count in queue["summary"].values()
    ):
        raise SchedulerRegistrationError("Queue-Zähler müssen Ganzzahlen sein.")
    expected_watches = {
        watch.watch_id
        for watch in load_watched_folder_configuration(plan.handoff.config_file).watches
        if watch.enabled
    }
    if (
        {item["watch_id"] for item in queue["items"]} != expected_watches
        or len(queue["items"]) != len(expected_watches)
        or counts != queue["summary"]
        or _run_status(counts) != (report["status"], report["exit_code"])
    ):
        raise SchedulerRegistrationError(
            "Queue-Zusammenfassung stimmt nicht mit ihren Einträgen überein."
        )
    material = json.dumps(
        {key: queue[key] for key in ("schema", "captured_at", "as_of", "items")},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if queue["queue_id"] != "routine_queue_" + sha256(material).hexdigest():
        raise SchedulerRegistrationError("Queue-ID bindet den Inhalt nicht.")
    path = _safe_state_root(Path(report["completed_file"]))
    expected = (
        plan.handoff.state_dir
        / "scheduler-runs"
        / f"{_safe_timestamp(report['captured_at'])}_{report['run_id']}.json"
    )
    if path != expected or _canonical_json(
        json.loads(path.read_text(encoding="utf-8"))
    ) != _canonical_json(report):
        raise SchedulerRegistrationError(
            "Persistierter Queue-Bericht stimmt nicht mit der Rückgabe überein."
        )
    receipt = _safe_state_root(plan.ledger_dir / f"invocation-{invocation_id}.json")
    if _canonical_json(json.loads(receipt.read_text(encoding="utf-8"))) != _canonical_json(
        envelope
    ):
        raise SchedulerRegistrationError(
            "Persistierter Aufrufnachweis stimmt nicht mit der Rückgabe überein."
        )


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _main():
    if sys.argv[1:] != ["--execute-approved-stdin"]:
        print("Expected explicit --execute-approved-stdin", file=sys.stderr)
        return 2
    try:
        request = json.load(sys.stdin)
        envelope = execute_approved_queue(
            request["plan"],
            confirmed_plan_id=request["confirmed_plan_id"],
            allow_scheduler_state_write=request["allow_scheduler_state_write"],
            invocation_id=request["invocation_id"],
        )
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True))
        return envelope["report"]["exit_code"]
    except Exception as exc:
        print(f"Queue-Ausführung abgewiesen ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
