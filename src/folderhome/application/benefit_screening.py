"""Route local profile facts to dated official benefit prechecks."""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from folderhome.contracts.benefit_screening import (
    BenefitCatalog,
    BenefitCriterionEvaluation,
    BenefitProfileFact,
    BenefitProfileSnapshot,
    BenefitProgram,
    BenefitRoutingCriterion,
    BenefitScreeningOutputReport,
    BenefitScreeningReport,
    BenefitScreeningResult,
    BenefitSource,
    Scalar,
)


class BenefitScreeningError(RuntimeError):
    """Raised when a benefit routing input or output is unsafe."""


def load_benefit_profile_snapshot(
    path: Path,
    *,
    allow_sensitive_local_read: bool,
) -> BenefitProfileSnapshot:
    if not allow_sensitive_local_read:
        raise BenefitScreeningError("Sensitivitätsfreigabe für Leistungsprofil fehlt.")
    payload = _load_json(path, "Leistungsprofil")
    if set(payload) != {"schema", "profile_id", "provided_on", "facts"}:
        raise BenefitScreeningError("Leistungsprofil besitzt unbekannte oder fehlende Felder.")
    if payload.get("schema") != BenefitProfileSnapshot.SCHEMA:
        raise BenefitScreeningError("Leistungsprofil verwendet ein unbekanntes Schema.")
    facts_raw = payload.get("facts")
    if not isinstance(facts_raw, list):
        raise BenefitScreeningError("Leistungsprofil benötigt eine facts-Liste.")
    try:
        facts = tuple(_parse_profile_fact(item) for item in facts_raw)
        digest = _file_sha(path)
        return BenefitProfileSnapshot(
            snapshot_id=f"benefit_profile_{digest}",
            profile_id=_text(payload, "profile_id"),
            provided_on=_text(payload, "provided_on"),
            source_path=path,
            source_sha256=digest,
            facts=facts,
        )
    except (TypeError, ValueError) as exc:
        raise BenefitScreeningError(f"Leistungsprofil ist ungültig: {exc}") from exc


def load_benefit_catalog(path: Path) -> BenefitCatalog:
    payload = _load_json(path, "Leistungskatalog")
    expected = {
        "schema",
        "catalog_version",
        "coverage_statement",
        "complete",
        "sources",
        "programs",
    }
    if set(payload) != expected:
        raise BenefitScreeningError("Leistungskatalog besitzt unbekannte oder fehlende Felder.")
    if payload.get("schema") != BenefitCatalog.SCHEMA:
        raise BenefitScreeningError("Leistungskatalog verwendet ein unbekanntes Schema.")
    sources_raw = payload.get("sources")
    programs_raw = payload.get("programs")
    if not isinstance(sources_raw, list) or not isinstance(programs_raw, list):
        raise BenefitScreeningError("Leistungskatalog benötigt Quellen und Programme.")
    try:
        sources = tuple(_parse_source(item) for item in sources_raw)
        programs = tuple(_parse_program(item) for item in programs_raw)
        source_ids = {item.source_id for item in sources}
        if len(source_ids) != len(sources):
            raise ValueError("Leistungsquellen müssen eindeutige IDs besitzen.")
        program_ids = {item.program_id for item in programs}
        if len(program_ids) != len(programs):
            raise ValueError("Leistungsprogramme müssen eindeutige IDs besitzen.")
        for program in programs:
            referenced = set(program.source_ids) | {
                item.source_id for item in program.routing_criteria
            }
            if not referenced.issubset(source_ids):
                raise ValueError(f"Programm {program.program_id} verweist auf fehlende Quelle.")
        digest = _file_sha(path)
        return BenefitCatalog(
            catalog_id=f"benefit_catalog_{digest}",
            catalog_version=_text(payload, "catalog_version"),
            coverage_statement=_text(payload, "coverage_statement"),
            complete=_boolean(payload, "complete"),
            source_path=path,
            source_sha256=digest,
            sources=sources,
            programs=programs,
        )
    except (TypeError, ValueError) as exc:
        raise BenefitScreeningError(f"Leistungskatalog ist ungültig: {exc}") from exc


def screen_benefits(
    profile: BenefitProfileSnapshot,
    catalog: BenefitCatalog,
    *,
    as_of: str,
    max_source_age_days: int,
    allow_sensitive_local_read: bool,
) -> BenefitScreeningReport:
    if not allow_sensitive_local_read:
        raise BenefitScreeningError("Sensitivitätsfreigabe für Leistungsvorcheck fehlt.")
    if isinstance(max_source_age_days, bool) or max_source_age_days < 1:
        raise BenefitScreeningError("max_source_age_days muss positiv sein.")
    as_of_time = _aware(as_of, "as_of")
    if _file_sha(profile.source_path) != profile.source_sha256:
        raise BenefitScreeningError("Leistungsprofilhash hat sich geändert.")
    if _file_sha(catalog.source_path) != catalog.source_sha256:
        raise BenefitScreeningError("Leistungskataloghash hat sich geändert.")
    fact_values = {item.fact_key: item.value for item in profile.facts}
    sources = {item.source_id: item for item in catalog.sources}
    source_ages: dict[str, int] = {}
    for source in catalog.sources:
        checked_at = _aware(source.checked_at, "checked_at")
        seconds = (as_of_time - checked_at).total_seconds()
        if seconds < 0:
            raise BenefitScreeningError(
                f"Leistungsquelle liegt in der Zukunft: {source.source_id}"
            )
        source_ages[source.source_id] = int(seconds // 86400)

    results = tuple(
        _screen_program(
            program,
            fact_values=fact_values,
            sources=sources,
            source_ages=source_ages,
            max_source_age_days=max_source_age_days,
        )
        for program in catalog.programs
    )
    warnings = (
        catalog.coverage_statement,
        "Der Vorcheck ist kein Leistungsbescheid und keine Rechtsberatung.",
        "Ein Routing-Mismatch beweist keine fehlende Leistungsberechtigung.",
        "Nur der amtliche Vorcheck oder die zuständige Stelle kann den Einzelfall prüfen.",
    )
    material = {
        "profile_snapshot_id": profile.snapshot_id,
        "catalog_id": catalog.catalog_id,
        "as_of": as_of,
        "max_source_age_days": max_source_age_days,
        "results": [item.to_dict() for item in results],
    }
    return BenefitScreeningReport(
        report_id=f"benefit_screening_{_json_sha(material)}",
        profile_id=profile.profile_id,
        profile_snapshot_id=profile.snapshot_id,
        profile_path=profile.source_path,
        profile_sha256=profile.source_sha256,
        catalog_id=catalog.catalog_id,
        catalog_path=catalog.source_path,
        catalog_sha256=catalog.source_sha256,
        catalog_complete=False,
        coverage_statement=catalog.coverage_statement,
        as_of=as_of,
        max_source_age_days=max_source_age_days,
        results=results,
        warnings=warnings,
    )


def write_benefit_screening_report(
    report: BenefitScreeningReport,
    *,
    markdown_file: Path,
    json_file: Path,
    allow_output_write: bool,
) -> BenefitScreeningOutputReport:
    if not allow_output_write:
        raise BenefitScreeningError("Output-Gate für Leistungsvorcheck fehlt.")
    markdown_path = markdown_file.resolve()
    json_path = json_file.resolve()
    if markdown_path.suffix.lower() != ".md" or json_path.suffix.lower() != ".json":
        raise BenefitScreeningError("Leistungsvorcheck benötigt Markdown und JSON.")
    if markdown_path == json_path:
        raise BenefitScreeningError("Leistungsvorcheckausgaben benötigen getrennte Pfade.")
    for path in (markdown_path, json_path):
        if path.exists():
            raise BenefitScreeningError(f"Leistungsvorcheckausgabe existiert bereits: {path}")
    if _file_sha(report.catalog_path) != report.catalog_sha256:
        raise BenefitScreeningError("Kataloghash hat sich seit dem Vorcheck geändert.")
    if _file_sha(report.profile_path) != report.profile_sha256:
        raise BenefitScreeningError("Leistungsprofilhash hat sich seit dem Vorcheck geändert.")
    markdown = _render_markdown(report)
    json_text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    created: list[Path] = []
    try:
        for path, content in ((markdown_path, markdown), (json_path, json_text)):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            created.append(path)
    except (OSError, UnicodeError) as exc:
        for path in created:
            with suppress(OSError):
                path.unlink()
        raise BenefitScreeningError(f"Leistungsvorcheckausgabe fehlgeschlagen: {exc}") from exc
    markdown_sha = _file_sha(markdown_path)
    json_sha = _file_sha(json_path)
    material = f"{report.report_id}:{markdown_sha}:{json_sha}"
    return BenefitScreeningOutputReport(
        output_id=f"benefit_output_{sha256(material.encode('utf-8')).hexdigest()}",
        report_id=report.report_id,
        markdown_path=markdown_path,
        markdown_sha256=markdown_sha,
        json_path=json_path,
        json_sha256=json_sha,
        status="executed",
    )


def _screen_program(
    program: BenefitProgram,
    *,
    fact_values: dict[str, Scalar],
    sources: dict[str, BenefitSource],
    source_ages: dict[str, int],
    max_source_age_days: int,
) -> BenefitScreeningResult:
    del sources  # validated during catalog load; kept explicit in the seam
    ages = tuple(source_ages[source_id] for source_id in program.source_ids)
    if any(age > max_source_age_days for age in ages):
        return _result(program, "blocked_source_stale", ages, (), ())
    evaluations = tuple(
        _evaluate_criterion(item, fact_values) for item in program.routing_criteria
    )
    missing = tuple(item.fact_key for item in evaluations if item.status == "missing")
    if any(item.status == "not_satisfied" for item in evaluations):
        status = "routing_mismatch"
    elif missing:
        status = "needs_information"
    else:
        status = "official_handoff_recommended"
    return _result(program, status, ages, evaluations, missing)


def _result(
    program: BenefitProgram,
    status: str,
    ages: tuple[int, ...],
    criteria: tuple[BenefitCriterionEvaluation, ...],
    missing: tuple[str, ...],
) -> BenefitScreeningResult:
    return BenefitScreeningResult(
        program_id=program.program_id,
        name=program.name,
        provider=program.provider,
        status=status,
        official_info_url=program.official_info_url,
        official_precheck_url=program.official_precheck_url,
        source_ids=program.source_ids,
        source_ages_days=ages,
        criteria=criteria,
        missing_fact_keys=missing,
        unmodeled_requirements=program.unmodeled_requirements,
    )


def _evaluate_criterion(
    criterion: BenefitRoutingCriterion,
    facts: dict[str, Scalar],
) -> BenefitCriterionEvaluation:
    if criterion.fact_key not in facts:
        status = "missing"
        actual = None
    else:
        actual = facts[criterion.fact_key]
        status = "satisfied" if _matches(actual, criterion) else "not_satisfied"
    return BenefitCriterionEvaluation(
        criterion_id=criterion.criterion_id,
        fact_key=criterion.fact_key,
        status=status,
        actual_value=actual,
        expected=criterion.expected,
        source_id=criterion.source_id,
        explanation=criterion.explanation,
    )


def _matches(actual: Scalar, criterion: BenefitRoutingCriterion) -> bool:
    expected = criterion.expected
    if criterion.operator == "eq":
        return type(actual) is type(expected) and actual == expected
    if criterion.operator == "in":
        assert isinstance(expected, tuple)
        return any(type(actual) is type(item) and actual == item for item in expected)
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False
    if not isinstance(actual, int) or not isinstance(expected, int):
        return False
    return actual >= expected if criterion.operator == "gte" else actual <= expected


def _parse_profile_fact(value: object) -> BenefitProfileFact:
    if not isinstance(value, dict) or set(value) != {"fact_key", "value", "basis"}:
        raise ValueError("Leistungsprofilfakt besitzt unbekannte oder fehlende Felder.")
    return BenefitProfileFact(
        fact_key=_text(value, "fact_key"),
        value=_scalar(value.get("value"), "value"),
        basis=_text(value, "basis"),
    )


def _parse_source(value: object) -> BenefitSource:
    expected = {
        "source_id",
        "publisher",
        "title",
        "official_url",
        "checked_at",
        "evidence_summary",
        "evidence_summary_sha256",
        "authoritative",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Leistungsquelle besitzt unbekannte oder fehlende Felder.")
    summary = _text(value, "evidence_summary")
    if _text(value, "evidence_summary_sha256") != sha256(summary.encode("utf-8")).hexdigest():
        raise ValueError("Evidenzzusammenfassung stimmt nicht mit ihrem Hash überein.")
    return BenefitSource(
        source_id=_text(value, "source_id"),
        publisher=_text(value, "publisher"),
        title=_text(value, "title"),
        official_url=_text(value, "official_url"),
        checked_at=_text(value, "checked_at"),
        evidence_summary=summary,
        evidence_summary_sha256=_text(value, "evidence_summary_sha256"),
        authoritative=_boolean(value, "authoritative"),
    )


def _parse_program(value: object) -> BenefitProgram:
    expected = {
        "program_id",
        "name",
        "provider",
        "official_info_url",
        "official_precheck_url",
        "source_ids",
        "routing_criteria",
        "unmodeled_requirements",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Leistungsprogramm besitzt unbekannte oder fehlende Felder.")
    criteria_raw = value.get("routing_criteria")
    if not isinstance(criteria_raw, list):
        raise ValueError("Leistungsprogramm benötigt Routingkriterien.")
    return BenefitProgram(
        program_id=_text(value, "program_id"),
        name=_text(value, "name"),
        provider=_text(value, "provider"),
        official_info_url=_text(value, "official_info_url"),
        official_precheck_url=_text(value, "official_precheck_url"),
        source_ids=_text_list(value, "source_ids", allow_empty=False),
        routing_criteria=tuple(_parse_criterion(item) for item in criteria_raw),
        unmodeled_requirements=_text_list(
            value,
            "unmodeled_requirements",
            allow_empty=False,
        ),
    )


def _parse_criterion(value: object) -> BenefitRoutingCriterion:
    expected_fields = {
        "criterion_id",
        "fact_key",
        "operator",
        "expected",
        "explanation",
        "source_id",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise ValueError("Routingkriterium besitzt unbekannte oder fehlende Felder.")
    operator = _text(value, "operator")
    raw_expected = value.get("expected")
    expected: Scalar | tuple[Scalar, ...]
    if operator == "in":
        if not isinstance(raw_expected, list):
            raise ValueError("in-Routingkriterium benötigt eine Liste.")
        expected = tuple(_scalar(item, "expected") for item in raw_expected)
    else:
        expected = _scalar(raw_expected, "expected")
    return BenefitRoutingCriterion(
        criterion_id=_text(value, "criterion_id"),
        fact_key=_text(value, "fact_key"),
        operator=operator,
        expected=expected,
        explanation=_text(value, "explanation"),
        source_id=_text(value, "source_id"),
    )


def _render_markdown(report: BenefitScreeningReport) -> str:
    lines = [
        "# Leistungs- und Fördervorcheck",
        "",
        f"**Status:** `{report.status}`  ",
        f"**Profil:** {_md(report.profile_id)}  ",
        f"**Stand:** `{report.as_of}`  ",
        "**Katalog vollständig:** `false`  ",
        f"**Abdeckung:** {_md(report.coverage_statement)}",
        "",
        "## Orientierungsergebnisse",
        "",
    ]
    for result in report.results:
        lines.extend(
            [
                f"### {_md(result.name)}",
                "",
                f"- Routingstatus: `{result.status}`",
                f"- Anbieter: {_md(result.provider)}",
                f"- Amtliche Information: <{result.official_info_url}>",
                f"- Amtlicher Vorcheck: <{result.official_precheck_url}>",
                "- Nicht modellierte Anforderungen: "
                + _md("; ".join(result.unmodeled_requirements)),
                "- Fehlende Profilangaben: "
                + _md(", ".join(result.missing_fact_keys) or "keine im Routingmodell"),
                "",
            ]
        )
        for criterion in result.criteria:
            lines.append(
                f"  - `{criterion.fact_key}`: `{criterion.status}` "
                f"(Quelle `{criterion.source_id}`)"
            )
        lines.append("")
    lines.extend(["## Grenzen", ""])
    lines.extend(f"- {_md(item)}" for item in report.warnings)
    lines.extend(
        [
            "",
            "**Keine Leistungsberechtigung geprüft.** Es wurden weder Höhe noch "
            "Antragserfolg bestimmt und kein Antrag erzeugt oder übermittelt.",
            "",
            "---",
            "<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenefitScreeningError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenefitScreeningError(f"{label} muss ein JSON-Objekt sein.")
    return payload


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} benötigt Text.")
    return value


def _boolean(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} benötigt einen booleschen Wert.")
    return value


def _scalar(value: object, key: str) -> Scalar:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, (int, bool)):
        return value
    raise ValueError(f"{key} benötigt Text, Ganzzahl oder Boolean.")


def _text_list(
    payload: dict[str, object],
    key: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{key} benötigt eine Liste.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{key} enthält ungültige Einträge.")
    return tuple(value)


def _aware(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise BenefitScreeningError(f"{field} muss ein ISO-Zeitstempel sein.") from exc
    if parsed.tzinfo is None:
        raise BenefitScreeningError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _file_sha(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise BenefitScreeningError(f"Datei ist nicht lesbar: {path}: {exc}") from exc
    return digest.hexdigest()


def _json_sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _md(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("|", "*", "_", "`", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r", " ").replace("\n", " ")
