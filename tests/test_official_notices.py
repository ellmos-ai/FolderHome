from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.official_notices import (
    OfficialNoticeError,
    analyze_official_notice,
    write_official_notice_report,
)
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


class SyntheticExtractor:
    provider_revision = "synthetic-notice-v1"

    def extract(self, source_path: Path) -> DocumentRecord:
        content = source_path.read_text(encoding="utf-8")
        digest = sha256(source_path.read_bytes()).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, digest),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=digest,
            size_bytes=source_path.stat().st_size,
            modified_at="2026-08-22T06:00:00+02:00",
            text=content,
            content_format=ContentFormat.TEXT,
            extraction_provider="synthetic-notice",
            extraction_method="direct",
            privacy_status=PrivacyStatus.REVIEW_REQUIRED,
            privacy_summary="Synthetischer Bescheid kann persönliche Daten enthalten.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _notice(tmp_path: Path, *, extra: str = "") -> Path:
    source = tmp_path / "Bescheid.txt"
    source.write_text(
        "\n".join(
            (
                "SYNTHETISCHER BESCHEID",
                "Bescheidart: Ablehnungsbescheid",
                "Behörde: Beispiel-Jobcenter",
                "Aktenzeichen: JC-SYNTH-2026-001",
                "Bescheiddatum: 2026-08-10",
                "Leistungszeitraum: September 2026",
                "Entscheidung: Der synthetische Antrag wird abgelehnt.",
                "Begründung: Eine erfundene Unterlage wurde nicht berücksichtigt.",
                "Rechtsbehelf: Widerspruch",
                "Fristtext: Innerhalb eines Monats nach Bekanntgabe.",
                "Explizites Fristdatum: 2026-09-15",
                "Rechtsbehelfsstelle: Beispiel-Jobcenter, Musterstraße 1",
                extra,
            )
        ),
        encoding="utf-8",
    )
    return source


def _analysis(tmp_path: Path, *, extra: str = ""):
    return analyze_official_notice(
        _notice(tmp_path, extra=extra),
        profile_id="lukas",
        received_on="2026-08-15",
        as_of="2026-08-22T06:00:00+02:00",
        extractor=SyntheticExtractor(),
        allow_sensitive_local_read=True,
    )


def test_notice_fields_are_extractive_and_evidence_bound(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)

    assert analysis.status == "ready_for_review"
    assert analysis.notice_type == "Ablehnungsbescheid"
    assert analysis.authority == "Beispiel-Jobcenter"
    assert analysis.decision == "Der synthetische Antrag wird abgelehnt."
    assert analysis.legal_remedy == "Widerspruch"
    assert analysis.explicit_deadline_date == "2026-09-15"
    assert analysis.days_until_explicit_deadline == 24
    assert analysis.deadline_urgency == "later"
    assert analysis.deadline_legally_calculated is False
    assert analysis.legal_review_status == "not_performed"
    assert analysis.response_generated is False
    assert all(item.document_id == analysis.document_id for item in analysis.evidence)
    assert all(item.source_sha256 == analysis.source_sha256 for item in analysis.evidence)
    assert {item.line_number for item in analysis.evidence} >= {2, 3, 4, 7, 9, 10}


def test_relative_deadline_text_is_not_turned_into_a_legal_deadline(
    tmp_path: Path,
) -> None:
    source = _notice(tmp_path)
    content = source.read_text(encoding="utf-8").replace(
        "Explizites Fristdatum: 2026-09-15\n",
        "",
    )
    source.write_text(content, encoding="utf-8")

    analysis = analyze_official_notice(
        source,
        profile_id="lukas",
        received_on="2026-08-15",
        as_of="2026-08-22T06:00:00+02:00",
        extractor=SyntheticExtractor(),
        allow_sensitive_local_read=True,
    )

    assert analysis.deadline_text == "Innerhalb eines Monats nach Bekanntgabe."
    assert analysis.explicit_deadline_date is None
    assert analysis.days_until_explicit_deadline is None
    assert analysis.deadline_legally_calculated is False
    assert analysis.status == "review_required"
    assert any("nicht rechtlich berechnet" in item for item in analysis.warnings)


def test_conflicting_singleton_fields_remain_visible(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path, extra="Behörde: Andere Beispielbehörde")

    assert analysis.status == "review_required"
    assert analysis.authority is None
    assert analysis.conflicts
    assert analysis.conflicts[0].field_name == "authority"
    assert set(analysis.conflicts[0].values) == {
        "Beispiel-Jobcenter",
        "Andere Beispielbehörde",
    }


def test_sensitivity_gate_blocks_before_extraction(tmp_path: Path) -> None:
    class FailIfCalled:
        def extract(self, source_path: Path) -> DocumentRecord:
            raise AssertionError("Extractor must not be called")

    with pytest.raises(OfficialNoticeError, match="Sensitivitätsfreigabe"):
        analyze_official_notice(
            _notice(tmp_path),
            profile_id="lukas",
            received_on="2026-08-15",
            as_of="2026-08-22T06:00:00+02:00",
            extractor=FailIfCalled(),
            allow_sensitive_local_read=False,
        )


def test_report_write_requires_gate_and_never_overwrites(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    markdown_file = tmp_path / "Ausgabe" / "Bescheidbericht.md"
    json_file = tmp_path / "Ausgabe" / "Bescheidbericht.json"

    with pytest.raises(OfficialNoticeError, match="Ausgabefreigabe"):
        write_official_notice_report(
            analysis,
            markdown_path=markdown_file,
            json_path=json_file,
            allow_output_write=False,
        )
    report = write_official_notice_report(
        analysis,
        markdown_path=markdown_file,
        json_path=json_file,
        allow_output_write=True,
    )

    assert report.status == "executed"
    assert report.source_document_modified is False
    assert "Keine Rechtsprüfung durchgeführt" in markdown_file.read_text(encoding="utf-8")
    with pytest.raises(OfficialNoticeError, match="existiert bereits"):
        write_official_notice_report(
            analysis,
            markdown_path=markdown_file,
            json_path=json_file,
            allow_output_write=True,
        )


def test_changed_source_blocks_report_write(tmp_path: Path) -> None:
    analysis = _analysis(tmp_path)
    analysis.source_path.write_text("nachträglich geändert", encoding="utf-8")

    with pytest.raises(OfficialNoticeError, match="Quellhash"):
        write_official_notice_report(
            analysis,
            markdown_path=tmp_path / "report.md",
            json_path=tmp_path / "report.json",
            allow_output_write=True,
        )
