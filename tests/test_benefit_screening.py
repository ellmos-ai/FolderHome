from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.benefit_screening import (
    BenefitScreeningError,
    load_benefit_catalog,
    load_benefit_profile_snapshot,
    screen_benefits,
    write_benefit_screening_report,
)


def _summary_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _catalog(tmp_path: Path, *, checked_at: str = "2026-08-22T06:30:00+02:00") -> Path:
    summary = "Synthetischer amtlicher Lotsenhinweis für die Vertragsabnahme."
    path = tmp_path / "benefit-catalog.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.benefit-catalog.v1",
                "catalog_version": "2026-08-22",
                "coverage_statement": (
                    "Unvollständige Orientierung; nicht alle Leistungen oder Regeln erfasst."
                ),
                "complete": False,
                "sources": [
                    {
                        "source_id": "source-official-finder",
                        "publisher": "Sozialplattform",
                        "title": "Amtlicher Leistungslotse",
                        "official_url": (
                            "https://sozialplattform.de/inhalt/sozialleistungen-finden"
                        ),
                        "checked_at": checked_at,
                        "evidence_summary": summary,
                        "evidence_summary_sha256": _summary_sha(summary),
                        "authoritative": True,
                    }
                ],
                "programs": [
                    {
                        "program_id": "synthetic-family-support",
                        "name": "Synthetische Familienunterstützung",
                        "provider": "Sozialplattform",
                        "official_info_url": (
                            "https://sozialplattform.de/inhalt/sozialleistungen-finden"
                        ),
                        "official_precheck_url": (
                            "https://sozialplattform.de/inhalt/sozialleistungen-finden"
                        ),
                        "source_ids": ["source-official-finder"],
                        "routing_criteria": [
                            {
                                "criterion_id": "criterion-country",
                                "fact_key": "residence_country",
                                "operator": "eq",
                                "expected": "DE",
                                "explanation": "Wohnsitzstaat für die Lotsenroute",
                                "source_id": "source-official-finder",
                            },
                            {
                                "criterion_id": "criterion-child",
                                "fact_key": "has_child_in_household",
                                "operator": "eq",
                                "expected": True,
                                "explanation": "Kind im Haushalt als grobes Routingmerkmal",
                                "source_id": "source-official-finder",
                            },
                        ],
                        "unmodeled_requirements": [
                            "Einkommen, Vermögen und weitere Einzelfallvoraussetzungen"
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _profile(tmp_path: Path, *, include_child: bool = True, country: str = "DE") -> Path:
    facts: list[dict[str, object]] = [
        {
            "fact_key": "residence_country",
            "value": country,
            "basis": "user_provided",
        }
    ]
    if include_child:
        facts.append(
            {
                "fact_key": "has_child_in_household",
                "value": True,
                "basis": "user_provided",
            }
        )
    path = tmp_path / "profile-facts.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.benefit-profile-snapshot.v1",
                "profile_id": "lukas",
                "provided_on": "2026-08-22",
                "facts": facts,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _report(
    tmp_path: Path,
    *,
    include_child: bool = True,
    country: str = "DE",
    checked_at: str = "2026-08-22T06:30:00+02:00",
):
    catalog = load_benefit_catalog(_catalog(tmp_path, checked_at=checked_at))
    profile = load_benefit_profile_snapshot(
        _profile(tmp_path, include_child=include_child, country=country),
        allow_sensitive_local_read=True,
    )
    return screen_benefits(
        profile,
        catalog,
        as_of="2026-08-22T07:00:00+02:00",
        max_source_age_days=30,
        allow_sensitive_local_read=True,
    )


def test_screening_recommends_official_handoff_without_eligibility_claim(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)

    assert report.status == "review_required"
    assert report.results[0].status == "official_handoff_recommended"
    assert report.results[0].official_precheck_url.startswith(
        "https://sozialplattform.de/"
    )
    assert all(item.status == "satisfied" for item in report.results[0].criteria)
    assert report.results[0].unmodeled_requirements
    assert report.eligibility_assessed is False
    assert report.amount_estimated is False
    assert report.application_generated is False
    assert report.network_used is False
    assert report.catalog_complete is False


def test_missing_fact_stays_unknown_and_mismatch_is_not_ineligibility(
    tmp_path: Path,
) -> None:
    missing = _report(tmp_path, include_child=False)
    mismatch = _report(tmp_path, country="FR")

    assert missing.results[0].status == "needs_information"
    assert missing.results[0].missing_fact_keys == ("has_child_in_household",)
    assert mismatch.results[0].status == "routing_mismatch"
    assert mismatch.results[0].eligibility_assessed is False
    assert any("kein Leistungsbescheid" in item for item in mismatch.warnings)


def test_stale_source_blocks_routing_instead_of_using_old_rules(tmp_path: Path) -> None:
    report = _report(tmp_path, checked_at="2026-06-01T06:30:00+02:00")

    assert report.results[0].status == "blocked_source_stale"
    assert report.results[0].criteria == ()
    assert report.status == "review_required"


def test_catalog_rejects_non_https_and_unverified_sources(tmp_path: Path) -> None:
    catalog_file = _catalog(tmp_path)
    payload = json.loads(catalog_file.read_text(encoding="utf-8"))
    payload["sources"][0]["official_url"] = "http://example.invalid/unsicher"
    catalog_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenefitScreeningError, match="HTTPS"):
        load_benefit_catalog(catalog_file)

    catalog_file = _catalog(tmp_path)
    payload = json.loads(catalog_file.read_text(encoding="utf-8"))
    payload["sources"][0]["authoritative"] = False
    catalog_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenefitScreeningError, match="amtlich"):
        load_benefit_catalog(catalog_file)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/leistung",
        "https://sozialplattform.de.evil.example/leistung",
        "https://sozialplattform.de./leistung",
        "https://sozialplattform%2ede/leistung",
        "https://127.0.0.1/leistung",
        "https://sozialplattform.de:443/leistung",
        "https://sozialplattform.de:444/leistung",
        "https://untrusted@sozialplattform.de/leistung",
    ],
)
def test_catalog_rejects_unregistered_or_ambiguous_official_hosts(
    tmp_path: Path,
    url: str,
) -> None:
    catalog_file = _catalog(tmp_path)
    payload = json.loads(catalog_file.read_text(encoding="utf-8"))
    payload["programs"][0]["official_precheck_url"] = url
    catalog_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenefitScreeningError, match="amtlichen Host"):
        load_benefit_catalog(catalog_file)


def test_catalog_binds_official_hosts_to_declared_publisher(tmp_path: Path) -> None:
    catalog_file = _catalog(tmp_path)
    payload = json.loads(catalog_file.read_text(encoding="utf-8"))
    payload["programs"][0]["provider"] = "Bundesagentur für Arbeit"
    catalog_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenefitScreeningError, match="amtlichen Host"):
        load_benefit_catalog(catalog_file)


def test_sensitive_gate_and_report_output_are_fail_closed(tmp_path: Path) -> None:
    catalog = load_benefit_catalog(_catalog(tmp_path))
    with pytest.raises(BenefitScreeningError, match="Sensitivitätsfreigabe"):
        load_benefit_profile_snapshot(
            _profile(tmp_path),
            allow_sensitive_local_read=False,
        )
    profile = load_benefit_profile_snapshot(
        _profile(tmp_path),
        allow_sensitive_local_read=True,
    )
    with pytest.raises(BenefitScreeningError, match="Sensitivitätsfreigabe"):
        screen_benefits(
            profile,
            catalog,
            as_of="2026-08-22T07:00:00+02:00",
            max_source_age_days=30,
            allow_sensitive_local_read=False,
        )
    report = screen_benefits(
        profile,
        catalog,
        as_of="2026-08-22T07:00:00+02:00",
        max_source_age_days=30,
        allow_sensitive_local_read=True,
    )
    markdown_file = tmp_path / "out" / "Leistungsvorcheck.md"
    json_file = tmp_path / "out" / "Leistungsvorcheck.json"
    with pytest.raises(BenefitScreeningError, match="Output-Gate"):
        write_benefit_screening_report(
            report,
            markdown_file=markdown_file,
            json_file=json_file,
            allow_output_write=False,
        )
    output = write_benefit_screening_report(
        report,
        markdown_file=markdown_file,
        json_file=json_file,
        allow_output_write=True,
    )
    assert output.status == "executed"
    assert output.external_actions_performed is False
    assert "Keine Leistungsberechtigung geprüft" in markdown_file.read_text(
        encoding="utf-8"
    )
    with pytest.raises(BenefitScreeningError, match="existiert bereits"):
        write_benefit_screening_report(
            report,
            markdown_file=markdown_file,
            json_file=json_file,
            allow_output_write=True,
        )


def test_changed_catalog_blocks_report_output(tmp_path: Path) -> None:
    report = _report(tmp_path)
    report.catalog_path.write_text("geändert", encoding="utf-8")

    with pytest.raises(BenefitScreeningError, match="Kataloghash"):
        write_benefit_screening_report(
            report,
            markdown_file=tmp_path / "report.md",
            json_file=tmp_path / "report.json",
            allow_output_write=True,
        )
