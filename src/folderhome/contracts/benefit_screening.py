"""Contracts for source-dated benefit routing without eligibility claims."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from folderhome.contracts.trusted_authorities import require_trusted_official_url

Scalar = str | int | bool

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_FACT_KEY = re.compile(r"[a-z][a-z0-9_]{1,63}")
_PROFILE_ID = re.compile(r"benefit_profile_[0-9a-f]{64}")
_CATALOG_ID = re.compile(r"benefit_catalog_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"benefit_screening_[0-9a-f]{64}")
_OUTPUT_ID = re.compile(r"benefit_output_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _aware(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Quellenzeitpunkt benötigt eine Zeitzone.")


@dataclass(frozen=True, slots=True)
class BenefitProfileFact:
    fact_key: str
    value: Scalar
    basis: str = "user_provided"

    SCHEMA = "folderhome.benefit-profile-fact.v1"

    def __post_init__(self) -> None:
        if _FACT_KEY.fullmatch(self.fact_key) is None:
            raise ValueError("Leistungsprofilfakt besitzt einen ungültigen Schlüssel.")
        if isinstance(self.value, str) and not self.value.strip():
            raise ValueError("Leistungsprofilfakt darf keinen leeren Text enthalten.")
        if not isinstance(self.value, (str, int, bool)):
            raise ValueError("Leistungsprofilfakt besitzt einen unbekannten Werttyp.")
        if self.basis != "user_provided":
            raise ValueError("Leistungsprofilfakt muss als user_provided ausgewiesen sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "fact_key": self.fact_key,
            "value": self.value,
            "basis": "user_provided",
        }


@dataclass(frozen=True, slots=True)
class BenefitProfileSnapshot:
    snapshot_id: str
    profile_id: str
    provided_on: str
    source_path: Path
    source_sha256: str
    facts: tuple[BenefitProfileFact, ...]

    SCHEMA = "folderhome.benefit-profile-snapshot.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if _PROFILE_ID.fullmatch(self.snapshot_id) is None or not self.profile_id.strip():
            raise ValueError("Leistungsprofilsnapshot besitzt ungültige IDs.")
        date.fromisoformat(self.provided_on)
        if _SHA256.fullmatch(self.source_sha256) is None:
            raise ValueError("Leistungsprofilsnapshot besitzt einen ungültigen Hash.")
        keys = [item.fact_key for item in self.facts]
        if len(keys) != len(set(keys)):
            raise ValueError("Leistungsprofilfakten müssen eindeutig sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "snapshot_id": self.snapshot_id,
            "profile_id": self.profile_id,
            "provided_on": self.provided_on,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "facts": [item.to_dict() for item in self.facts],
        }


@dataclass(frozen=True, slots=True)
class BenefitSource:
    source_id: str
    publisher: str
    title: str
    official_url: str
    checked_at: str
    evidence_summary: str
    evidence_summary_sha256: str
    authoritative: bool

    SCHEMA = "folderhome.benefit-source.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.source_id) is None:
            raise ValueError("Leistungsquelle besitzt eine ungültige ID.")
        if (
            not self.publisher.strip()
            or not self.title.strip()
            or not self.evidence_summary.strip()
        ):
            raise ValueError("Leistungsquelle besitzt unvollständige Metadaten.")
        require_trusted_official_url(self.official_url, publisher=self.publisher)
        _aware(self.checked_at)
        if _SHA256.fullmatch(self.evidence_summary_sha256) is None:
            raise ValueError("Leistungsquelle besitzt einen ungültigen Evidenzhash.")
        if self.authoritative is not True:
            raise ValueError("Leistungsquelle muss als amtlich bestätigt sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "source_id": self.source_id,
            "publisher": self.publisher,
            "title": self.title,
            "official_url": self.official_url,
            "checked_at": self.checked_at,
            "evidence_summary": self.evidence_summary,
            "evidence_summary_sha256": self.evidence_summary_sha256,
            "authoritative": True,
        }


@dataclass(frozen=True, slots=True)
class BenefitRoutingCriterion:
    criterion_id: str
    fact_key: str
    operator: str
    expected: Scalar | tuple[Scalar, ...]
    explanation: str
    source_id: str

    SCHEMA = "folderhome.benefit-routing-criterion.v1"

    def __post_init__(self) -> None:
        if _ID.fullmatch(self.criterion_id) is None or _FACT_KEY.fullmatch(
            self.fact_key
        ) is None:
            raise ValueError("Routingkriterium besitzt ungültige IDs.")
        if self.operator not in {"eq", "in", "gte", "lte"}:
            raise ValueError("Routingkriterium besitzt einen unbekannten Operator.")
        if self.operator == "in":
            if not isinstance(self.expected, tuple) or not self.expected:
                raise ValueError("in-Routingkriterium benötigt eine Werteliste.")
        elif isinstance(self.expected, tuple):
            raise ValueError("Routingkriterium besitzt einen unpassenden Erwartungswert.")
        if not self.explanation.strip() or _ID.fullmatch(self.source_id) is None:
            raise ValueError("Routingkriterium benötigt Erklärung und Quelle.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "criterion_id": self.criterion_id,
            "fact_key": self.fact_key,
            "operator": self.operator,
            "expected": (
                list(self.expected) if isinstance(self.expected, tuple) else self.expected
            ),
            "explanation": self.explanation,
            "source_id": self.source_id,
        }


@dataclass(frozen=True, slots=True)
class BenefitProgram:
    program_id: str
    name: str
    provider: str
    official_info_url: str
    official_precheck_url: str
    source_ids: tuple[str, ...]
    routing_criteria: tuple[BenefitRoutingCriterion, ...]
    unmodeled_requirements: tuple[str, ...]

    SCHEMA = "folderhome.benefit-program.v1"

    def __post_init__(self) -> None:
        if (
            _ID.fullmatch(self.program_id) is None
            or not self.name.strip()
            or not self.provider.strip()
        ):
            raise ValueError("Leistungsprogramm besitzt ungültige Stammdaten.")
        require_trusted_official_url(self.official_info_url, publisher=self.provider)
        require_trusted_official_url(self.official_precheck_url, publisher=self.provider)
        if not self.source_ids or not self.unmodeled_requirements:
            raise ValueError("Leistungsprogramm muss Quellen und offene Anforderungen nennen.")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("Leistungsprogramm enthält doppelte Quellen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "program_id": self.program_id,
            "name": self.name,
            "provider": self.provider,
            "official_info_url": self.official_info_url,
            "official_precheck_url": self.official_precheck_url,
            "source_ids": list(self.source_ids),
            "routing_criteria": [item.to_dict() for item in self.routing_criteria],
            "unmodeled_requirements": list(self.unmodeled_requirements),
        }


@dataclass(frozen=True, slots=True)
class BenefitCatalog:
    catalog_id: str
    catalog_version: str
    coverage_statement: str
    complete: bool
    source_path: Path
    source_sha256: str
    sources: tuple[BenefitSource, ...]
    programs: tuple[BenefitProgram, ...]

    SCHEMA = "folderhome.benefit-catalog.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", self.source_path.resolve())
        if _CATALOG_ID.fullmatch(self.catalog_id) is None:
            raise ValueError("Leistungskatalog besitzt eine ungültige ID.")
        date.fromisoformat(self.catalog_version)
        if not self.coverage_statement.strip() or self.complete is not False:
            raise ValueError("Leistungskatalog muss seine Unvollständigkeit ausweisen.")
        if _SHA256.fullmatch(self.source_sha256) is None or not self.sources or not self.programs:
            raise ValueError("Leistungskatalog besitzt unvollständige Bindungen.")


@dataclass(frozen=True, slots=True)
class BenefitCriterionEvaluation:
    criterion_id: str
    fact_key: str
    status: str
    actual_value: Scalar | None
    expected: Scalar | tuple[Scalar, ...]
    source_id: str
    explanation: str

    SCHEMA = "folderhome.benefit-criterion-evaluation.v1"

    def __post_init__(self) -> None:
        if self.status not in {"satisfied", "not_satisfied", "missing"}:
            raise ValueError("Kriterienauswertung besitzt einen ungültigen Status.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "criterion_id": self.criterion_id,
            "fact_key": self.fact_key,
            "status": self.status,
            "actual_value": self.actual_value,
            "expected": list(self.expected) if isinstance(self.expected, tuple) else self.expected,
            "source_id": self.source_id,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class BenefitScreeningResult:
    program_id: str
    name: str
    provider: str
    status: str
    official_info_url: str
    official_precheck_url: str
    source_ids: tuple[str, ...]
    source_ages_days: tuple[int, ...]
    criteria: tuple[BenefitCriterionEvaluation, ...]
    missing_fact_keys: tuple[str, ...]
    unmodeled_requirements: tuple[str, ...]
    eligibility_assessed: bool = False

    SCHEMA = "folderhome.benefit-screening-result.v1"

    def __post_init__(self) -> None:
        if self.status not in {
            "official_handoff_recommended",
            "needs_information",
            "routing_mismatch",
            "blocked_source_stale",
        }:
            raise ValueError("Leistungsvorcheckergebnis besitzt einen ungültigen Status.")
        if self.eligibility_assessed:
            raise ValueError("Leistungsvorcheck darf keine Berechtigung behaupten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "program_id": self.program_id,
            "name": self.name,
            "provider": self.provider,
            "status": self.status,
            "official_info_url": self.official_info_url,
            "official_precheck_url": self.official_precheck_url,
            "source_ids": list(self.source_ids),
            "source_ages_days": list(self.source_ages_days),
            "criteria": [item.to_dict() for item in self.criteria],
            "missing_fact_keys": list(self.missing_fact_keys),
            "unmodeled_requirements": list(self.unmodeled_requirements),
            "eligibility_assessed": False,
        }


@dataclass(frozen=True, slots=True)
class BenefitScreeningReport:
    report_id: str
    profile_id: str
    profile_snapshot_id: str
    profile_path: Path
    profile_sha256: str
    catalog_id: str
    catalog_path: Path
    catalog_sha256: str
    catalog_complete: bool
    coverage_statement: str
    as_of: str
    max_source_age_days: int
    results: tuple[BenefitScreeningResult, ...]
    warnings: tuple[str, ...]
    status: str = "review_required"
    eligibility_assessed: bool = False
    amount_estimated: bool = False
    application_generated: bool = False
    network_used: bool = False

    SCHEMA = "folderhome.benefit-screening-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_path", self.profile_path.resolve())
        object.__setattr__(self, "catalog_path", self.catalog_path.resolve())
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("Leistungsvorcheck besitzt eine ungültige ID.")
        _aware(self.as_of)
        if self.max_source_age_days < 1 or self.status != "review_required":
            raise ValueError("Leistungsvorcheck besitzt ungültige Prüfgrenzen.")
        if self.catalog_complete is not False:
            raise ValueError("Leistungsvorcheck darf keinen vollständigen Katalog behaupten.")
        if any(
            (
                self.eligibility_assessed,
                self.amount_estimated,
                self.application_generated,
                self.network_used,
            )
        ):
            raise ValueError("Leistungsvorcheck überschreitet die Orientierungsgrenze.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "profile_id": self.profile_id,
            "profile_snapshot_id": self.profile_snapshot_id,
            "profile_path": str(self.profile_path),
            "profile_sha256": self.profile_sha256,
            "catalog_id": self.catalog_id,
            "catalog_path": str(self.catalog_path),
            "catalog_sha256": self.catalog_sha256,
            "catalog_complete": False,
            "coverage_statement": self.coverage_statement,
            "as_of": self.as_of,
            "max_source_age_days": self.max_source_age_days,
            "results": [item.to_dict() for item in self.results],
            "warnings": list(self.warnings),
            "status": "review_required",
            "eligibility_assessed": False,
            "amount_estimated": False,
            "application_generated": False,
            "network_used": False,
            "external_actions": [],
        }


@dataclass(frozen=True, slots=True)
class BenefitScreeningOutputReport:
    output_id: str
    report_id: str
    markdown_path: Path
    markdown_sha256: str
    json_path: Path
    json_sha256: str
    status: str
    external_actions_performed: bool = False

    SCHEMA = "folderhome.benefit-screening-output-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "markdown_path", self.markdown_path.resolve())
        object.__setattr__(self, "json_path", self.json_path.resolve())
        if _OUTPUT_ID.fullmatch(self.output_id) is None or _REPORT_ID.fullmatch(
            self.report_id
        ) is None:
            raise ValueError("Leistungsvorcheckausgabe besitzt ungültige IDs.")
        if any(
            _SHA256.fullmatch(value) is None
            for value in (self.markdown_sha256, self.json_sha256)
        ):
            raise ValueError("Leistungsvorcheckausgabe besitzt ungültige Hashes.")
        if self.status != "executed" or self.external_actions_performed:
            raise ValueError("Leistungsvorcheckausgabe darf keine Außenwirkung behaupten.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "output_id": self.output_id,
            "report_id": self.report_id,
            "markdown_path": str(self.markdown_path),
            "markdown_sha256": self.markdown_sha256,
            "json_path": str(self.json_path),
            "json_sha256": self.json_sha256,
            "status": "executed",
            "external_actions_performed": False,
        }
