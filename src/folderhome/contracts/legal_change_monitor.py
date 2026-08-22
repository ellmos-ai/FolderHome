"""Contracts for source-bound legal change review candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

_ID = re.compile(r"[a-z][a-z0-9_-]{1,79}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SNAPSHOT_ID = re.compile(r"law_snapshot_[0-9a-f]{64}")
_INTEREST_ID = re.compile(r"legal_interests_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"legal_monitor_[0-9a-f]{64}")
_OUTPUT_ID = re.compile(r"legal_output_[0-9a-f]{64}")
_OFFICIAL_HOSTS = frozenset(
    {
        "www.gesetze-im-internet.de",
        "gesetze-im-internet.de",
        "www.recht.bund.de",
        "recht.bund.de",
        "www.bundestag.de",
        "bundestag.de",
        "dip.bundestag.de",
        "eur-lex.europa.eu",
    }
)


def _aware(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Quellenzeitpunkt benötigt eine Zeitzone.")


def _source_url(value: str, *, fixture_only: bool) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Rechtsquelle benötigt eine sichere HTTPS-URL.")
    host = (parsed.hostname or "").casefold()
    if fixture_only:
        if host != "example.invalid":
            raise ValueError("Testfixture muss example.invalid verwenden.")
    elif host not in _OFFICIAL_HOSTS:
        raise ValueError("Rechtsquelle liegt nicht auf einer zugelassenen amtlichen Domain.")


@dataclass(frozen=True, slots=True)
class LegalProvisionSnapshot:
    provision_id: str
    heading: str
    text: str
    topics: tuple[str, ...]
    text_sha256: str

    SCHEMA = "folderhome.legal-provision-snapshot.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.provision_id) is None or not self.heading.strip():
            raise ValueError("Normabschnitt besitzt ungültige Stammdaten.")
        if not self.text.strip() or _SHA256.fullmatch(self.text_sha256) is None:
            raise ValueError("Normabschnitt benötigt Text und Text-Hash.")
        if not self.topics or len(self.topics) != len(set(self.topics)):
            raise ValueError("Normabschnitt benötigt eindeutige Themen-Tags.")
        if any(_ID.fullmatch(item) is None for item in self.topics):
            raise ValueError("Normabschnitt besitzt ungültige Themen-Tags.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "provision_id": self.provision_id,
            "heading": self.heading,
            "text_sha256": self.text_sha256,
            "topics": list(self.topics),
        }


@dataclass(frozen=True, slots=True)
class LegalSourceSnapshot:
    snapshot_id: str
    law_id: str
    law_title: str
    law_checker_registry_key: str | None
    publication_stage: str
    publisher: str
    official_url: str
    checked_at: str
    source_date: str
    authoritative: bool
    fixture_only: bool
    complete: bool
    coverage_statement: str
    source_path: Path
    source_sha256: str
    provisions: tuple[LegalProvisionSnapshot, ...]

    SCHEMA = "folderhome.legal-source-snapshot.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if _SNAPSHOT_ID.fullmatch(self.snapshot_id) is None or _ID.fullmatch(self.law_id) is None:
            raise ValueError("Rechtsquellensnapshot besitzt ungültige IDs.")
        if not self.law_title.strip() or not self.publisher.strip():
            raise ValueError("Rechtsquellensnapshot besitzt unvollständige Metadaten.")
        if self.law_checker_registry_key is not None and _ID.fullmatch(
            self.law_checker_registry_key
        ) is None:
            raise ValueError("law-checker-Registry-Schlüssel ist ungültig.")
        if self.publication_stage not in {
            "consolidated_current",
            "promulgated",
            "legislative_proposal",
        }:
            raise ValueError(
                "Rechtsquellensnapshot besitzt eine unbekannte Veröffentlichungsstufe."
            )
        _source_url(self.official_url, fixture_only=self.fixture_only)
        _aware(self.checked_at)
        date.fromisoformat(self.source_date)
        if self.fixture_only == self.authoritative:
            raise ValueError("Nur Nicht-Testquellen dürfen als amtlich bestätigt sein.")
        if self.complete is not False or not self.coverage_statement.strip():
            raise ValueError("Rechtsquellensnapshot muss seine Unvollständigkeit ausweisen.")
        if _SHA256.fullmatch(self.source_sha256) is None or not self.provisions:
            raise ValueError("Rechtsquellensnapshot besitzt unvollständige Bindungen.")
        ids = [item.provision_id for item in self.provisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Normabschnitte müssen eindeutige IDs besitzen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "snapshot_id": self.snapshot_id,
            "law_id": self.law_id,
            "law_title": self.law_title,
            "law_checker_registry_key": self.law_checker_registry_key,
            "publication_stage": self.publication_stage,
            "publisher": self.publisher,
            "official_url": self.official_url,
            "checked_at": self.checked_at,
            "source_date": self.source_date,
            "authoritative": self.authoritative,
            "fixture_only": self.fixture_only,
            "complete": False,
            "coverage_statement": self.coverage_statement,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "provisions": [item.to_dict() for item in self.provisions],
        }


@dataclass(frozen=True, slots=True)
class LegalInterest:
    interest_id: str
    subject_kind: str
    subject_ref: str
    topics: tuple[str, ...]
    basis: str = "user_provided"

    SCHEMA = "folderhome.legal-interest.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.interest_id) is None:
            raise ValueError("Rechtsinteresse besitzt eine ungültige ID.")
        if self.subject_kind not in {"profile", "contract"} or not self.subject_ref.strip():
            raise ValueError("Rechtsinteresse besitzt einen ungültigen Gegenstandsbezug.")
        if not self.topics or len(self.topics) != len(set(self.topics)):
            raise ValueError("Rechtsinteresse benötigt eindeutige Themen-Tags.")
        if any(_ID.fullmatch(item) is None for item in self.topics):
            raise ValueError("Rechtsinteresse besitzt ungültige Themen-Tags.")
        if self.basis != "user_provided":
            raise ValueError("Rechtsinteresse muss als user_provided ausgewiesen sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "interest_id": self.interest_id,
            "subject_kind": self.subject_kind,
            "subject_ref": self.subject_ref,
            "topics": list(self.topics),
            "basis": "user_provided",
        }


@dataclass(frozen=True, slots=True)
class LegalInterestSnapshot:
    snapshot_id: str
    profile_id: str
    provided_on: str
    source_path: Path
    source_sha256: str
    interests: tuple[LegalInterest, ...]

    SCHEMA = "folderhome.legal-interest-snapshot.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if _INTEREST_ID.fullmatch(self.snapshot_id) is None or not self.profile_id.strip():
            raise ValueError("Rechtsinteressensnapshot besitzt ungültige IDs.")
        date.fromisoformat(self.provided_on)
        if _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("Rechtsinteressensnapshot besitzt einen ungültigen Hash.")


@dataclass(frozen=True, slots=True)
class LegalProvisionChange:
    provision_id: str
    heading_before: str | None
    heading_after: str | None
    change_kind: str
    before_text_sha256: str | None
    after_text_sha256: str | None
    topics: tuple[str, ...]

    SCHEMA = "folderhome.legal-provision-change.v1"

    def __post_init__(self) -> None:
        if self.change_kind not in {"added", "modified", "removed"}:
            raise ValueError("Normänderung besitzt einen unbekannten Typ.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "provision_id": self.provision_id,
            "heading_before": self.heading_before,
            "heading_after": self.heading_after,
            "change_kind": self.change_kind,
            "before_text_sha256": self.before_text_sha256,
            "after_text_sha256": self.after_text_sha256,
            "topics": list(self.topics),
        }


@dataclass(frozen=True, slots=True)
class LegalReviewCandidate:
    candidate_id: str
    interest_id: str
    subject_kind: str
    subject_ref: str
    provision_ids: tuple[str, ...]
    matching_topics: tuple[str, ...]
    status: str = "review_candidate"
    affected_determined: bool = False

    SCHEMA = "folderhome.legal-review-candidate.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.candidate_id) is None or self.status != "review_candidate":
            raise ValueError("Rechtsprüfkandidat besitzt ungültige Stammdaten.")
        if not self.provision_ids or not self.matching_topics or self.affected_determined:
            raise ValueError("Rechtsprüfkandidat darf keine Betroffenheit behaupten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "candidate_id": self.candidate_id,
            "interest_id": self.interest_id,
            "subject_kind": self.subject_kind,
            "subject_ref": self.subject_ref,
            "provision_ids": list(self.provision_ids),
            "matching_topics": list(self.matching_topics),
            "status": "review_candidate",
            "affected_determined": False,
        }


@dataclass(frozen=True, slots=True)
class LegalChangeMonitorReport:
    report_id: str
    status: str
    as_of: str
    law_id: str
    publication_stage: str
    before_snapshot_id: str
    after_snapshot_id: str
    before_path: Path
    after_path: Path
    interests_path: Path
    before_sha256: str
    after_sha256: str
    interests_sha256: str
    provider_id: str | None
    provider_revision: str | None
    registry_coverage_status: str
    changes: tuple[LegalProvisionChange, ...]
    candidates: tuple[LegalReviewCandidate, ...]
    warnings: tuple[str, ...]
    legal_effect_assessed: bool = False
    deadline_legally_calculated: bool = False
    notification_sent: bool = False
    network_used: bool = False

    SCHEMA = "folderhome.legal-change-monitor-report.v1"

    def __post_init__(self) -> None:
        for name in ("before_path", "after_path", "interests_path"):
            object.__setattr__(self, name, getattr(self, name).resolve())
        if _REPORT_ID.fullmatch(self.report_id) is None or self.status not in {
            "no_change",
            "review_required",
            "proposal_review_required",
        }:
            raise ValueError("Rechtsänderungsbericht besitzt einen ungültigen Status.")
        if any(
            (
                self.legal_effect_assessed,
                self.deadline_legally_calculated,
                self.notification_sent,
                self.network_used,
            )
        ):
            raise ValueError("Rechtsänderungsbericht überschreitet die sichere Monitorgrenze.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "status": self.status,
            "as_of": self.as_of,
            "law_id": self.law_id,
            "publication_stage": self.publication_stage,
            "before_snapshot_id": self.before_snapshot_id,
            "after_snapshot_id": self.after_snapshot_id,
            "source_bindings": {
                "before_path": str(self.before_path),
                "after_path": str(self.after_path),
                "interests_path": str(self.interests_path),
                "before_sha256": self.before_sha256,
                "after_sha256": self.after_sha256,
                "interests_sha256": self.interests_sha256,
            },
            "law_checker": {
                "provider_id": self.provider_id,
                "provider_revision": self.provider_revision,
                "registry_coverage_status": self.registry_coverage_status,
            },
            "changes": [item.to_dict() for item in self.changes],
            "candidates": [item.to_dict() for item in self.candidates],
            "warnings": list(self.warnings),
            "legal_effect_assessed": False,
            "deadline_legally_calculated": False,
            "notification_sent": False,
            "network_used": False,
        }


@dataclass(frozen=True, slots=True)
class LegalChangeOutputReport:
    output_id: str
    report_id: str
    status: str
    markdown_file: Path
    json_file: Path
    markdown_sha256: str
    json_sha256: str
    external_actions_performed: bool = False

    SCHEMA = "folderhome.legal-change-output-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "markdown_file", self.markdown_file.resolve())
        object.__setattr__(self, "json_file", self.json_file.resolve())
        if _OUTPUT_ID.fullmatch(self.output_id) is None or self.status != "executed":
            raise ValueError("Rechtsänderungsausgabe besitzt ungültige Stammdaten.")
        if self.external_actions_performed:
            raise ValueError("Rechtsänderungsausgabe darf keine Außenwirkung behaupten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "output_id": self.output_id,
            "report_id": self.report_id,
            "status": self.status,
            "markdown_file": str(self.markdown_file),
            "json_file": str(self.json_file),
            "markdown_sha256": self.markdown_sha256,
            "json_sha256": self.json_sha256,
            "external_actions_performed": False,
        }
