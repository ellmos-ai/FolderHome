"""Explicit, process-owned lifecycle for already registered scheduler consumers."""

from __future__ import annotations

import hmac
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import Event, RLock, Thread
from uuid import uuid4

from folderhome.application.directory_observation import load_watched_folder_configuration
from folderhome.application.scheduler_consumer import create_scheduler_consumer
from folderhome.application.scheduler_registration import (
    SchedulerRegistrationPlan,
    validate_scheduler_registration_plan,
)


@dataclass
class _Worker:
    worker_id: str
    registration_plan_id: str
    consumer: object
    stop_event: Event
    thread: Thread | None = None
    failed: bool = False


class SchedulerConsumerController:
    """No global daemon claims: only workers started and owned by this object."""

    def __init__(
        self,
        *,
        profile_ids: frozenset[str],
        allow_consumer_start: bool,
        poll_seconds=5.0,
        plan_provider=None,
    ):
        self._profile_ids = profile_ids
        self._allow_start = allow_consumer_start is True
        self._poll_seconds = poll_seconds
        self._plan_provider = plan_provider
        self._instance_id = "consumer_session_" + uuid4().hex
        self._lock = RLock()
        self._pending: dict[str, tuple[dict, SchedulerRegistrationPlan]] = {}
        self._workers: dict[str, _Worker] = {}
        self._closed = False

    def _profile(self, profile_id):
        if profile_id not in self._profile_ids:
            raise ValueError("Unbekanntes Scheduler-Profil.")

    def preview_configured(self, *, profile_id: str):
        self._profile(profile_id)
        if self._plan_provider is None:
            raise ValueError("Keine gespeicherte Scheduler-Konfiguration angebunden.")
        return self.preview(profile_id=profile_id, plan=self._plan_provider(profile_id))

    def preview(self, *, profile_id: str, plan: SchedulerRegistrationPlan):
        """Bind current configuration; actual job identity is checked again at start."""
        self._profile(profile_id)
        with self._lock:
            if self._closed:
                raise ValueError("Diese App-Steuerung ist geschlossen.")
            plan = validate_scheduler_registration_plan(plan)
            watches = load_watched_folder_configuration(plan.handoff.config_file).watches
            if not any(watch.enabled for watch in watches):
                raise ValueError("Keine aktive Scheduler-Watch für die Profilbindung vorhanden.")
            if any(watch.enabled and watch.profile_id != profile_id for watch in watches):
                raise ValueError("Scheduler-Watches gehören zu einem anderen Profil.")
            public = {
                "schema": "folderhome.scheduler-consumer-start-plan.v1",
                "plan_id": "consumer_start_" + uuid4().hex,
                "instance_id": self._instance_id,
                "profile_id": profile_id,
                "registration_plan_id": plan.plan_id,
                "interval_minutes": plan.handoff.interval_minutes,
                "start_at": plan.handoff.start_at,
                "timezone": plan.handoff.timezone,
                "watch_ids": [watch.watch_id for watch in watches if watch.enabled],
                "existing_registration_required": True,
                "registration_checked": False,
                "live_effect_approved": self._allow_start,
                "document_actions_authorized": False,
                "other_instances": "not_observed",
            }
            public["plan_sha256"] = sha256(
                json.dumps(
                    public,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            # One fresh proposal per profile bounds memory and invalidates older tabs.
            self._pending[profile_id] = (public, plan)
            return deepcopy(public)

    def start(self, *, profile_id: str, plan_id: str, plan_sha256: str):
        self._profile(profile_id)
        with self._lock:
            if self._closed or not self._allow_start:
                raise ValueError("Separate Consumer-Startfreigabe fehlt oder App geschlossen.")
            pending = self._pending.get(profile_id)
            if pending is None or not isinstance(plan_id, str) or not isinstance(plan_sha256, str):
                raise ValueError("Keine gültige Startvorschau vorhanden.")
            public, plan = pending
            if not hmac.compare_digest(public["plan_id"], plan_id) or not hmac.compare_digest(
                public["plan_sha256"],
                plan_sha256,
            ):
                raise ValueError("Die Startbestätigung stimmt nicht mit der Vorschau überein.")
            active = self._workers.get(profile_id)
            if active is not None and active.thread is not None and active.thread.is_alive():
                raise ValueError("Für dieses Profil läuft bereits ein eigener Dienst.")
            if self._plan_provider is not None and self._plan_provider(profile_id) != plan:
                raise ValueError("Gespeicherte Scheduler-Konfiguration hat sich geändert.")
            # The constructor revalidates bytes, ownership receipt and exact stored job.
            # It never registers or initializes a missing job/store.
            consumer = create_scheduler_consumer(
                plan,
                confirmed_plan_id=plan.plan_id,
                allow_consumer_state_write=True,
            )
            worker = _Worker("consumer_worker_" + uuid4().hex, plan.plan_id, consumer, Event())
            worker.thread = Thread(
                target=self._run,
                args=(worker,),
                name=f"folderhome-scheduler-{profile_id}",
                daemon=False,
            )
            self._workers[profile_id] = worker
            del self._pending[profile_id]
            try:
                worker.thread.start()
            except BaseException:
                worker.failed = True
                worker.stop_event.set()
                raise
            return self.status(profile_id=profile_id)

    def _run(self, worker):
        try:
            worker.consumer.serve(poll_seconds=self._poll_seconds, stop_event=worker.stop_event)
        except Exception:
            # Paths and provider exception text stay out of public status payloads.
            with self._lock:
                worker.failed = True

    def status(self, *, profile_id: str):
        self._profile(profile_id)
        with self._lock:
            public = {
                "schema": "folderhome.scheduler-consumer-status.v1",
                "instance_id": self._instance_id,
                "profile_id": profile_id,
                "observed_at": datetime.now(UTC).isoformat(),
                "other_instances": "not_observed",
                "status": "not_started_in_this_app",
                "worker_id": None,
                "last_observation": None,
            }
            worker = self._workers.get(profile_id)
            if worker is None:
                return public
            alive = worker.thread is not None and worker.thread.is_alive()
            public.update(
                worker_id=worker.worker_id,
                registration_plan_id=worker.registration_plan_id,
                status=("stopping" if worker.stop_event.is_set() else "running")
                if alive
                else ("failed" if worker.failed else "stopped"),
            )
            observation = worker.consumer.last_observation
            if observation is not None:
                public["last_observation"] = {
                    "observed_at": observation["observed_at"],
                    "status": observation["status"],
                    "runs": [
                        {key: row.get(key) for key in ("run_id", "status", "exit_code")}
                        for row in observation["runs"]
                    ],
                }
            return public

    def stop(self, *, profile_id: str, worker_id: str):
        self._profile(profile_id)
        with self._lock:
            worker = self._workers.get(profile_id)
            if (
                worker is None
                or not isinstance(worker_id, str)
                or not hmac.compare_digest(
                    worker.worker_id,
                    worker_id,
                )
            ):
                raise ValueError("Dieser Worker gehört nicht zur ausgewählten App-Steuerung.")
            worker.stop_event.set()
            return self.status(profile_id=profile_id)

    def close(self, *, timeout=1.0):
        """Signal every owned worker; do not claim that a draining worker has stopped."""
        with self._lock:
            self._closed = True
            self._pending.clear()
            workers = tuple(self._workers.values())
            for worker in workers:
                worker.stop_event.set()
        for worker in workers:
            if worker.thread is not None and worker.thread.ident is not None:
                worker.thread.join(timeout=timeout)
