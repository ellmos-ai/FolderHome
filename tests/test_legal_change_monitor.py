from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.legal_change_monitor import (
    LegalChangeMonitorError,
    compare_legal_source_snapshots,
    load_legal_interest_snapshot,
    load_legal_source_snapshot,
    write_legal_change_report,
)


def _text_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _snapshot(
    tmp_path: Path,
    name: str,
    text: str,
    *,
    checked_at: str,
    source_date: str,
    publication_stage: str = "consolidated_current",
    fixture_only: bool = True,
    registry_key: str | None = None,
) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.legal-source-snapshot.v1",
                "law_id": "synthetic-social-law" if fixture_only else "sgb-v",
                "law_title": "Synthetisches Sozialgesetz" if fixture_only else "SGB V",
                "law_checker_registry_key": registry_key,
                "publication_stage": publication_stage,
                "publisher": "Teststelle" if fixture_only else "Bundesministerium der Justiz",
                "official_url": (
                    "https://example.invalid/synthetic-law"
                    if fixture_only
                    else "https://www.gesetze-im-internet.de/sgb_5/xml.zip"
                ),
                "checked_at": checked_at,
                "source_date": source_date,
                "authoritative": not fixture_only,
                "fixture_only": fixture_only,
                "complete": False,
                "coverage_statement": "Nur der synthetische Testabschnitt ist erfasst.",
                "provisions": [
                    {
                        "provision_id": "section-demo",
                        "heading": "Synthetischer Testabschnitt",
                        "text": text,
                        "text_sha256": _text_sha(text),
                        "topics": ["krankenversicherung", "beitraege"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _interests(tmp_path: Path, *, topics: list[str] | None = None) -> Path:
    path = tmp_path / "interests.json"
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.legal-interest-snapshot.v1",
                "profile_id": "lukas",
                "provided_on": "2026-08-22",
                "interests": [
                    {
                        "interest_id": "hyundai-insurance",
                        "subject_kind": "contract",
                        "subject_ref": "contract-hyundai-i10",
                        "topics": topics or ["krankenversicherung"],
                        "basis": "user_provided",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _report(
    tmp_path: Path,
    *,
    after_stage: str = "consolidated_current",
    after_checked_at: str = "2026-08-22T07:30:00+02:00",
    topics: list[str] | None = None,
):
    before = load_legal_source_snapshot(
        _snapshot(
            tmp_path,
            "before",
            "Alter synthetischer Wortlaut.",
            checked_at="2026-08-21T07:30:00+02:00",
            source_date="2026-08-21",
        ),
        allow_test_fixture=True,
    )
    after = load_legal_source_snapshot(
        _snapshot(
            tmp_path,
            "after",
            "Neuer synthetischer Wortlaut.",
            checked_at=after_checked_at,
            source_date="2026-08-22",
            publication_stage=after_stage,
        ),
        allow_test_fixture=True,
    )
    interests = load_legal_interest_snapshot(
        _interests(tmp_path, topics=topics),
        allow_sensitive_local_read=True,
    )
    return compare_legal_source_snapshots(
        before,
        after,
        interests,
        as_of="2026-08-22T08:00:00+02:00",
        max_source_age_days=7,
        allow_sensitive_local_read=True,
        allow_test_fixture=True,
    )


def test_changed_topic_creates_review_candidate_without_legal_conclusion(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)

    assert report.status == "review_required"
    assert report.changes[0].change_kind == "modified"
    assert report.candidates[0].status == "review_candidate"
    assert report.candidates[0].affected_determined is False
    assert report.legal_effect_assessed is False
    assert report.deadline_legally_calculated is False
    assert report.notification_sent is False
    assert report.network_used is False


def test_nonmatching_explicit_interest_does_not_create_candidate(tmp_path: Path) -> None:
    report = _report(tmp_path, topics=["mietrecht"])

    assert report.status == "review_required"
    assert report.changes
    assert report.candidates == ()


def test_proposal_is_never_reported_as_enacted_change(tmp_path: Path) -> None:
    report = _report(tmp_path, after_stage="legislative_proposal")

    assert report.status == "proposal_review_required"
    assert report.publication_stage == "legislative_proposal"
    assert any("Entwurf" in warning for warning in report.warnings)
    assert report.legal_effect_assessed is False


def test_stale_source_blocks_instead_of_generating_warning_candidates(tmp_path: Path) -> None:
    with pytest.raises(LegalChangeMonitorError, match="veraltet"):
        _report(tmp_path, after_checked_at="2026-07-01T07:30:00+02:00")


def test_production_snapshot_rejects_nonofficial_domain(tmp_path: Path) -> None:
    path = _snapshot(
        tmp_path,
        "unsafe",
        "Text",
        checked_at="2026-08-22T07:30:00+02:00",
        source_date="2026-08-22",
        fixture_only=False,
        registry_key="sgb_v",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["official_url"] = "https://not-official.invalid/law"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(LegalChangeMonitorError, match="amtlichen Domain"):
        load_legal_source_snapshot(path)


def test_sensitive_and_fixture_gates_fail_closed(tmp_path: Path) -> None:
    source = _snapshot(
        tmp_path,
        "fixture",
        "Test",
        checked_at="2026-08-22T07:30:00+02:00",
        source_date="2026-08-22",
    )
    with pytest.raises(LegalChangeMonitorError, match="Testfixture-Freigabe"):
        load_legal_source_snapshot(source)
    with pytest.raises(LegalChangeMonitorError, match="Sensitivitätsfreigabe"):
        load_legal_interest_snapshot(
            _interests(tmp_path),
            allow_sensitive_local_read=False,
        )


def test_output_is_hash_bound_gated_and_never_overwrites(tmp_path: Path) -> None:
    report = _report(tmp_path)
    markdown_file = tmp_path / "out" / "Rechtsaenderungen.md"
    json_file = tmp_path / "out" / "Rechtsaenderungen.json"

    with pytest.raises(LegalChangeMonitorError, match="Output-Gate"):
        write_legal_change_report(
            report,
            markdown_file=markdown_file,
            json_file=json_file,
            allow_output_write=False,
        )
    output = write_legal_change_report(
        report,
        markdown_file=markdown_file,
        json_file=json_file,
        allow_output_write=True,
    )
    assert output.status == "executed"
    assert output.external_actions_performed is False
    assert "Keine Rechtswirkung geprüft" in markdown_file.read_text(encoding="utf-8")
    with pytest.raises(LegalChangeMonitorError, match="existiert bereits"):
        write_legal_change_report(
            report,
            markdown_file=markdown_file,
            json_file=json_file,
            allow_output_write=True,
        )


def test_changed_bound_snapshot_blocks_output(tmp_path: Path) -> None:
    report = _report(tmp_path)
    report.after_path.write_text("geändert", encoding="utf-8")

    with pytest.raises(LegalChangeMonitorError, match="Nachher-Snapshot-Hash"):
        write_legal_change_report(
            report,
            markdown_file=tmp_path / "report.md",
            json_file=tmp_path / "report.json",
            allow_output_write=True,
        )
