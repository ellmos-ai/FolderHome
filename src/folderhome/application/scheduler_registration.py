"""Content-bound planning and explicitly approved registration; no consumer startup."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from folderhome.application.directory_observation import load_watched_folder_configuration
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.routine_queue import load_folder_routine_bindings
from folderhome.application.scheduler_handoff import (
    SchedulerHandoffError,
    _safe_state_root,
    _write_new_json,
    validate_scheduler_handoff,
)
from folderhome.bridges._provider import load_pinned_python_modules, verify_checkout_revision
from folderhome.contracts import PluginDescriptor
from folderhome.contracts.scheduler import SchedulerHandoffPlan
from folderhome.plugin_host import load_manifests


class SchedulerRegistrationError(ValueError):
    """Registration configuration no longer matches the reviewed proposal."""


@dataclass(frozen=True, slots=True)
class SchedulerRegistrationPlan:
    """Private execution inputs; physical paths must not become model arguments."""

    plan_id: str
    handoff: SchedulerHandoffPlan
    store_path: Path
    ledger_dir: Path
    provider_root: Path
    provider_revision: str
    configuration_files: tuple[tuple[str, str], ...]
    resolved_directories: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.scheduler-registration-plan.v1",
            "plan_id": self.plan_id,
            "handoff": self.handoff.to_dict(),
            "store_path": str(self.store_path),
            "ledger_dir": str(self.ledger_dir),
            "provider_root": str(self.provider_root),
            "provider_revision": self.provider_revision,
            "configuration_files": [
                {"path": path, "sha256": digest} for path, digest in self.configuration_files
            ],
            "resolved_directories": [
                {"resource": resource, "path": path} for resource, path in self.resolved_directories
            ],
        }


def build_scheduler_registration_plan(
    *,
    handoff: SchedulerHandoffPlan,
    store_path: Path,
    ledger_dir: Path,
    provider_root: Path,
    provider_revision: str,
) -> SchedulerRegistrationPlan:
    """Bind configuration membership and bytes, not changing watched documents.

    Construction performs only reads. This proposal alone grants no permission
    and does not imply that any job is registered or any consumer is running.
    """
    try:
        handoff = validate_scheduler_handoff(handoff)
        store_path = _safe_state_root(store_path)
        ledger_dir = _safe_state_root(ledger_dir)
        provider_root = _safe_state_root(provider_root)
        verify_checkout_revision(provider_root, provider_revision)
        files = _configuration_files(handoff)
        resolved_directories = _resolved_directories(handoff)
        _validate_output_separation(
            handoff, store_path, ledger_dir, provider_root, resolved_directories
        )
        load_profile_configuration(handoff.profiles_dir)
        load_manifests(handoff.manifest_root)
        if files != _configuration_files(handoff) or resolved_directories != _resolved_directories(
            handoff
        ):
            raise SchedulerRegistrationError("Konfiguration wurde während der Planung verändert.")
        provisional = SchedulerRegistrationPlan(
            plan_id="",
            handoff=handoff,
            store_path=store_path,
            ledger_dir=ledger_dir,
            provider_root=provider_root,
            provider_revision=provider_revision,
            configuration_files=files,
            resolved_directories=resolved_directories,
        )
        encoded = json.dumps(
            provisional.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return SchedulerRegistrationPlan(
            plan_id="registration_" + sha256(encoded).hexdigest(),
            handoff=handoff,
            store_path=store_path,
            ledger_dir=ledger_dir,
            provider_root=provider_root,
            provider_revision=provider_revision,
            configuration_files=files,
            resolved_directories=resolved_directories,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        raise SchedulerRegistrationError(
            f"Scheduler-Konfiguration ist nicht freigabefähig: {exc}"
        ) from exc


def validate_scheduler_registration_plan(
    plan: SchedulerRegistrationPlan,
) -> SchedulerRegistrationPlan:
    """Reconstruct an independent snapshot before registration and later runs."""
    current = build_scheduler_registration_plan(
        handoff=plan.handoff,
        store_path=plan.store_path,
        ledger_dir=plan.ledger_dir,
        provider_root=plan.provider_root,
        provider_revision=plan.provider_revision,
    )
    if current != plan:
        raise SchedulerRegistrationError(
            "Registrierungsplan wurde verändert; neu planen und prüfen."
        )
    return current


def _configuration_files(handoff: SchedulerHandoffPlan) -> tuple[tuple[str, str], ...]:
    profiles = _safe_state_root(handoff.profiles_dir)
    manifests = _safe_state_root(handoff.manifest_root)
    if not profiles.is_dir() or not manifests.is_dir():
        raise SchedulerRegistrationError("Profil- oder Manifestverzeichnis fehlt.")
    paths = {handoff.config_file, handoff.bindings_file}
    paths.update(profiles.glob("*.json"))
    paths.update(manifests.glob("*.toml"))
    return tuple(
        (str(path), sha256(_safe_state_root(path).read_bytes()).hexdigest())
        for path in sorted(paths, key=str)
    )


def _resolved_directories(handoff: SchedulerHandoffPlan) -> tuple[tuple[str, str], ...]:
    watches = load_watched_folder_configuration(handoff.config_file)
    bindings = load_folder_routine_bindings(handoff.bindings_file)
    return tuple(
        sorted(
            [("watch:" + item.watch_id, str(item.source_root)) for item in watches.watches]
            + [("binding:" + item.binding_id, str(item.target_root)) for item in bindings.bindings]
        )
    )


def _validate_output_separation(handoff, store, ledger, provider, directories):
    protected = [Path(path) for _, path in directories]
    protected.extend(
        [handoff.profiles_dir, handoff.manifest_root, provider, handoff.doc_services_root]
    )
    protected_files = {handoff.config_file, handoff.bindings_file, handoff.python_executable}
    outputs = [store, ledger, _safe_state_root(handoff.state_dir)]
    for output in outputs:
        if output in protected_files or any(output.is_relative_to(root) for root in protected):
            raise SchedulerRegistrationError("Scheduler-Ausgaben überlappen freigegebene Eingaben.")
    for index, output in enumerate(outputs):
        if any(
            output.is_relative_to(other) or other.is_relative_to(output)
            for other in outputs[index + 1 :]
        ):
            raise SchedulerRegistrationError(
                "Store, Nachweise und Laufberichte müssen getrennt sein."
            )


@dataclass(frozen=True, slots=True)
class SchedulerRegistrationReport:
    plan_id: str
    job_id: str
    status: str
    attempt_file: Path | None
    consumer_status: str = "not_observed"
    reconciled: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.scheduler-registration-report.v1",
            "plan_id": self.plan_id,
            "job_id": self.job_id,
            "status": self.status,
            "attempt_file": str(self.attempt_file) if self.attempt_file else None,
            "consumer_status": self.consumer_status,
            "reconciled": self.reconciled,
            "error": self.error,
        }


def register_scheduler_job(
    plan: SchedulerRegistrationPlan,
    *,
    confirmed_plan_id: str,
    allow_scheduler_write: bool,
) -> SchedulerRegistrationReport:
    """Register one exact proposal, with durable attempt evidence before DB access.

    A repeated attempt only reconciles: even an absent job after an interrupted
    insert never authorizes a blind retry. Existing stores need this ledger's
    ownership receipt; unknown databases are not opened or migrated. The caller
    must obtain these private inputs from trusted application configuration.
    """
    if allow_scheduler_write is not True or confirmed_plan_id != plan.plan_id:
        raise SchedulerRegistrationError("Exakte Bestätigung und Scheduler-Schreibfreigabe fehlen.")
    plan = validate_scheduler_registration_plan(plan)
    provider = _scheduler_provider(plan)
    job_id = "folderhome-" + plan.plan_id
    definition = {
        "schedule": {"kind": "interval", "seconds": plan.handoff.interval_minutes * 60},
        "executor": "folderhome.routine-queue.v1",
        "payload": {"registration_plan": plan.to_dict()},
        "enabled": True,
        "next_due_at": datetime.fromisoformat(plan.handoff.start_at).astimezone(UTC),
        "lease_seconds": 900,
        "timeout_seconds": 600,
        "authorities": [],
    }
    try:
        attempt_file = _safe_state_root(plan.ledger_dir / f"attempt-{plan.plan_id}.json")
    except SchedulerHandoffError:
        # On Windows an atomically published hardlink may still resolve to
        # its publisher's temporary name. Do not weaken the alias guard or
        # proceed with DB access; a later confirmation may safely reconcile.
        return SchedulerRegistrationReport(
            plan.plan_id,
            job_id,
            "uncertain",
            None,
            error="Nachweispfad ist nicht eindeutig; vor Wiederholung erneut prüfen.",
        )
    plan.ledger_dir.mkdir(parents=True, exist_ok=True)
    attempt = {"schema": "folderhome.scheduler-registration-attempt.v1", "plan": plan.to_dict()}
    fresh = True
    try:
        _write_new_json(attempt_file, attempt)
    except SchedulerHandoffError as exc:
        if not attempt_file.exists():
            raise
        fresh = False
        try:
            previous_attempt = json.loads(
                _safe_state_root(attempt_file).read_text(encoding="utf-8")
            )
        except SchedulerHandoffError:
            return SchedulerRegistrationReport(
                plan.plan_id,
                job_id,
                "uncertain",
                None,
                error="Veröffentlichter Nachweispfad ist noch nicht eindeutig; erneut prüfen.",
            )
        if previous_attempt != attempt:
            raise SchedulerRegistrationError(
                "Registrierungsnachweis gehört zu einem anderen Plan."
            ) from exc

    def finish(status, *, error=None, reconciled=False):
        report = SchedulerRegistrationReport(
            plan.plan_id, job_id, status, attempt_file, reconciled=reconciled, error=error
        )
        # Each observation is immutable; never replace a prior success with a
        # later conflict or discard a failed attempt's evidence.
        try:
            _write_new_json(
                plan.ledger_dir / f"result-{plan.plan_id}-{uuid4().hex}.json", report.to_dict()
            )
        except (OSError, RuntimeError):
            return SchedulerRegistrationReport(
                plan.plan_id,
                job_id,
                "uncertain",
                attempt_file,
                error="Ergebnisnachweis konnte nicht gespeichert werden; vor Wiederholung prüfen.",
            )
        return report

    try:
        store = provider.SchedulerStore(plan.store_path)
        if not _prepare_owned_store(plan, store, create=fresh):
            return finish("uncertain", error="Storeanlage ist noch nicht abschließend belegt.")
        existing, latest_run = _read_job_snapshot(store, job_id)
        if existing is not None:
            status = (
                "already_registered"
                if _matches_job(existing, definition, latest_run)
                else "conflict"
            )
            return finish(status, reconciled=not fresh)
        if not fresh:
            return finish(
                "uncertain", error="Vorheriger Versuch ohne belegten Job; kein automatischer Retry."
            )
        validate_scheduler_registration_plan(plan)
        _check_store_identity(plan)
        failure = None
        try:
            store.add_job(job_id, **definition)
        except Exception as exc:
            # A lost response says nothing about whether INSERT committed.
            failure = type(exc).__name__
        _check_store_identity(plan)
        existing, latest_run = _read_job_snapshot(store, job_id)
        if existing is not None and _matches_job(existing, definition, latest_run):
            return finish("registered", reconciled=failure is not None)
        if existing is not None:
            return finish(
                "conflict",
                error="Gespeicherte Jobdefinition stimmt nicht mit der Freigabe überein.",
            )
        return finish("uncertain", error="Providerwrite nicht durch Rücklesen bestätigt.")
    except SchedulerRegistrationError as exc:
        return finish("conflict", error=str(exc))
    except Exception as exc:
        return finish(
            "uncertain", error=f"Registrierung nicht abschließend belegt ({type(exc).__name__})."
        )


def _scheduler_provider(plan):
    descriptor = PluginDescriptor(
        plugin_id="ellmos-scheduler",
        name="ellmos-scheduler",
        version="0.3.1",
        source_repository="https://github.com/ellmos-ai/ellmos-scheduler.git",
        source_revision="d5103b9a733701f6db80dd08cfae408bf0af8ac5",
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
    )
    if plan.provider_revision != descriptor.source_revision:
        raise SchedulerRegistrationError(
            "Scheduler-Revision wird von dieser Bridge nicht unterstützt."
        )
    return load_pinned_python_modules(
        plugin=descriptor,
        provider_root=plan.provider_root,
        package_name="ellmos_scheduler",
        src_layout=True,
    )["ellmos_scheduler"]


def _store_receipt_path(plan):
    key = sha256(str(plan.store_path).encode("utf-8")).hexdigest()
    return _safe_state_root(plan.ledger_dir / f"store-{key}.json")


def _store_identity(plan):
    path = _safe_state_root(plan.store_path)
    stat = path.stat()
    if not path.is_file() or stat.st_nlink != 1:
        raise SchedulerRegistrationError("Scheduler-Store ist keine eigene reguläre Datei.")
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = _safe_state_root(path.with_name(path.name + suffix))
        if sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_nlink != 1):
            raise SchedulerRegistrationError(
                "Scheduler-SQLite-Zustand enthält eine fremde Verknüpfung."
            )
    return {
        "store_path": str(path),
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "provider_revision": plan.provider_revision,
    }


def _check_store_identity(plan):
    receipt = _store_receipt_path(plan)
    if not receipt.is_file():
        raise SchedulerRegistrationError(
            "Vorhandener Store hat keinen eigenen Initialisierungsnachweis."
        )
    if json.loads(receipt.read_text(encoding="utf-8")) != _store_identity(plan):
        raise SchedulerRegistrationError(
            "Store wurde ersetzt oder stammt aus einem anderen Providerstand."
        )


def _prepare_owned_store(plan, store, *, create):
    path = _safe_state_root(plan.store_path)
    if path.exists():
        if not _store_receipt_path(plan).exists() and not create:
            return False  # Another confirmation may still be initializing it.
        _check_store_identity(plan)
        return True
    if not create:
        return False
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = _safe_state_root(path.with_name(path.name + suffix))
        if sidecar.exists():
            raise SchedulerRegistrationError(
                "Vorhandene SQLite-Begleitdateien verhindern die neue Storeanlage."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            reserved = os.fstat(handle.fileno())
    except FileExistsError:
        return False
    identity = _store_identity(plan)
    if identity["device"] != reserved.st_dev or identity["inode"] != reserved.st_ino:
        raise SchedulerRegistrationError("Storepfad wurde während der Anlage ersetzt.")
    store.init()  # Only our exclusively created empty file, never a foreign DB.
    if _store_identity(plan) != identity:
        raise SchedulerRegistrationError("Store wurde während der Initialisierung ersetzt.")
    _write_new_json(_store_receipt_path(plan), identity)
    return True


def _read_job_snapshot(store, job_id):
    # A single read transaction prevents mixing a job row from before a claim
    # with the run history from after it. Provider.connect is gated above.
    with store.connect() as conn:
        conn.execute("BEGIN")
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        latest_row = conn.execute(
            "SELECT scheduled_for, status FROM runs WHERE job_id = ? "
            "ORDER BY scheduled_for DESC, attempt DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        latest = dict(latest_row) if latest_row else None
        if row is not None and latest is not None:
            due_run = conn.execute(
                "SELECT status FROM runs WHERE job_id = ? AND scheduled_for = ? "
                "ORDER BY attempt DESC LIMIT 1",
                (job_id, row["next_due_at"]),
            ).fetchone()
            latest["due_run_abandoned"] = due_run is not None and due_run["status"] == "abandoned"
        return dict(row) if row else None, latest


def _matches_job(row, definition, latest_run):
    matches = (
        json.loads(row["schedule_json"]) == definition["schedule"]
        and row["executor"] == definition["executor"]
        and json.loads(row["payload_json"]) == definition["payload"]
        and row["enabled"] == 1
        and row["generation"] == 1
        and row["lease_seconds"] == definition["lease_seconds"]
        and row["timeout_seconds"] == definition["timeout_seconds"]
        and json.loads(row["authorities_json"]) == []
    )
    expected_due = definition["next_due_at"]
    if latest_run is not None:
        scheduled = datetime.fromisoformat(latest_run["scheduled_for"])
        interval = timedelta(seconds=definition["schedule"]["seconds"])
        if scheduled.tzinfo is None or scheduled < expected_due:
            return False
        if (scheduled - expected_due) % interval != timedelta(0):
            return False
        expected_due = scheduled + interval
        # A paused job may await retry of an older abandoned slot even when
        # newer slots have completed. Check the latest attempt of that exact
        # due slot, in the same snapshot, not merely the latest time overall.
        due = datetime.fromisoformat(row["next_due_at"])
        if latest_run["due_run_abandoned"]:
            start = definition["next_due_at"]
            if due.tzinfo is None or due < start or (due - start) % interval != timedelta(0):
                return False
            expected_due = due
    return matches and datetime.fromisoformat(row["next_due_at"]) == expected_due
