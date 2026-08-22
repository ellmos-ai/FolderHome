from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest

from folderhome.application.health_dossier import (
    HealthDossierGateError,
    build_health_dossier,
)
from folderhome.bridges.doc_services import DocServicesBridgeError
from folderhome.capabilities.health_report_handoff import prepare_health_report_handoff
from folderhome.contracts import (
    ContentFormat,
    DocumentRecord,
    IndexStatus,
    PrivacyStatus,
    build_document_id,
)


class FakeHealthExtractor:
    def __init__(
        self,
        texts: dict[str, str],
        *,
        blocked: frozenset[str] = frozenset(),
        unreadable: frozenset[str] = frozenset(),
    ) -> None:
        self.texts = texts
        self.blocked = blocked
        self.unreadable = unreadable
        self.calls: list[Path] = []

    def extract(self, source_path: Path) -> DocumentRecord:
        self.calls.append(source_path)
        if source_path.name in self.unreadable:
            raise DocServicesBridgeError("Dokument konnte nicht extrahiert werden.")
        content = source_path.read_bytes()
        digest = sha256(content).hexdigest()
        return DocumentRecord(
            document_id=build_document_id(source_path, digest),
            source_path=source_path,
            filename=source_path.name,
            media_type="text/plain",
            source_sha256=digest,
            size_bytes=len(content),
            modified_at="2026-08-22T00:00:00Z",
            text=self.texts[source_path.name],
            content_format=ContentFormat.TEXT,
            extraction_provider="fake-doc-services",
            extraction_method="direct",
            privacy_status=(
                PrivacyStatus.BLOCKED
                if source_path.name in self.blocked
                else PrivacyStatus.REVIEW_REQUIRED
            ),
            privacy_summary="Sensible Gesundheitsdaten erkannt.",
            index_status=IndexStatus.NOT_INDEXED,
            index_provider=None,
            index_ref=None,
        )


def _source_folder(tmp_path: Path, texts: dict[str, str]) -> Path:
    source_dir = tmp_path / "Gesundheit"
    source_dir.mkdir()
    for filename, text in texts.items():
        (source_dir / filename).write_text(text, encoding="utf-8")
    return source_dir


def test_health_dossier_requires_explicit_sensitive_local_read_before_extraction(
    tmp_path: Path,
) -> None:
    texts = {
        "bericht.txt": "Dokumenttyp: Arztbericht\nDokumentdatum: 2026-01-10\n",
    }
    source_dir = _source_folder(tmp_path, texts)
    extractor = FakeHealthExtractor(texts)

    with pytest.raises(HealthDossierGateError, match="Sensitivitätsfreigabe"):
        build_health_dossier(
            source_dir,
            profile_id="lukas",
            as_of=date(2026, 8, 22),
            extractor=extractor,
            allow_sensitive_local_read=False,
        )

    assert extractor.calls == []


def test_health_dossier_builds_extractive_timeline_with_line_evidence(
    tmp_path: Path,
) -> None:
    texts = {
        "hausarzt.txt": (
            "Dokumenttyp: Arztbericht\n"
            "Dokumentdatum: 2026-01-10\n"
            "Fachbereich: Hausarzt\n"
            "Befund: Blutdruck wurde mit 120/80 dokumentiert.\n"
            "Medikament: DemoMed 1 Tablette morgens.\n"
            "Dokumentierte Angabe: Allergie = keine\n"
            "Offene Frage: Ist der nächste Kontrolltermin bereits vereinbart?\n"
        ),
        "kardiologie.txt": (
            "Dokumenttyp: Arztbericht\n"
            "Dokumentdatum: 2026-06-20\n"
            "Fachbereich: Kardiologie\n"
            "Befund: Ein Ruhe-EKG wurde durchgeführt.\n"
            "Termin: 2026-09-03 10:30 Europe/Berlin | Kontrolltermin Kardiologie\n"
            "Dokumentierte Angabe: Allergie = Penicillin\n"
        ),
    }
    source_dir = _source_folder(tmp_path, texts)

    report = build_health_dossier(
        source_dir,
        profile_id="lukas",
        as_of=date(2026, 8, 22),
        extractor=FakeHealthExtractor(texts),
        allow_sensitive_local_read=True,
        gap_threshold_days=90,
    )

    assert report.schema == "folderhome.health-dossier.v1"
    assert report.profile_id == "lukas"
    assert [item.documented_date for item in report.timeline] == [
        "2026-01-10",
        "2026-01-10",
        "2026-01-10",
        "2026-01-10",
        "2026-06-20",
        "2026-06-20",
        "2026-06-20",
    ]
    finding = next(item for item in report.timeline if item.kind == "finding")
    assert finding.statement == "Blutdruck wurde mit 120/80 dokumentiert."
    assert finding.evidence.line_number == 4
    assert finding.evidence.relative_path == "hausarzt.txt"
    assert finding.evidence.source_sha256
    assert {item.kind for item in report.timeline} == {
        "finding",
        "medication",
        "documented_fact",
        "question",
        "appointment",
    }
    assert len(report.conflicts) == 1
    assert report.conflicts[0].field == "Allergie"
    assert report.conflicts[0].values == ("keine", "Penicillin")
    assert len(report.coverage.missing_periods) == 1
    assert report.coverage.missing_periods[0].days_without_document == 161
    assert report.unreadable_sources == ()
    assert report.medical_advice is False
    assert report.completeness_claimed is False
    assert "Keine Diagnose oder medizinische Empfehlung" in report.markdown
    assert "hausarzt.txt:4" in report.markdown
    assert "Penicillin" in report.markdown
    assert "161 Tage" in report.markdown


def test_health_dossier_keeps_unreadable_blocked_and_undated_sources_visible(
    tmp_path: Path,
) -> None:
    texts = {
        "lesbar.txt": (
            "Dokumenttyp: Arztbericht\n"
            "Dokumentdatum: 2026-01-10\n"
            "Befund: Dokumentierter Satz.\n"
        ),
        "ohne-datum.txt": "Dokumenttyp: Arztbericht\nBefund: Ohne Datum.\n",
        "blockiert.txt": (
            "Dokumenttyp: Arztbericht\n"
            "Dokumentdatum: 2026-02-10\n"
            "Befund: Darf nicht in das Dossier.\n"
        ),
        "kaputt.txt": "nicht lesbar",
    }
    source_dir = _source_folder(tmp_path, texts)

    report = build_health_dossier(
        source_dir,
        profile_id="lukas",
        as_of=date(2026, 8, 22),
        extractor=FakeHealthExtractor(
            texts,
            blocked=frozenset({"blockiert.txt"}),
            unreadable=frozenset({"kaputt.txt"}),
        ),
        allow_sensitive_local_read=True,
    )

    statuses = {item.relative_path: item.status for item in report.sources}
    assert statuses == {
        "blockiert.txt": "blocked",
        "kaputt.txt": "unreadable",
        "lesbar.txt": "included",
        "ohne-datum.txt": "missing_date",
    }
    assert report.unreadable_sources == ("kaputt.txt",)
    assert report.blocked_sources == ("blockiert.txt",)
    assert report.undated_sources == ("ohne-datum.txt",)
    assert "Darf nicht in das Dossier" not in report.markdown
    assert "blockiert.txt" in report.markdown
    assert "kaputt.txt" in report.markdown


def test_health_dossier_rejects_future_document_dates_and_invalid_gap_threshold(
    tmp_path: Path,
) -> None:
    texts = {
        "zukunft.txt": (
            "Dokumenttyp: Arztbericht\n"
            "Dokumentdatum: 2027-01-10\n"
            "Befund: Noch nicht dokumentierbar.\n"
        ),
    }
    source_dir = _source_folder(tmp_path, texts)

    report = build_health_dossier(
        source_dir,
        profile_id="lukas",
        as_of=date(2026, 8, 22),
        extractor=FakeHealthExtractor(texts),
        allow_sensitive_local_read=True,
    )
    assert report.sources[0].status == "future_date"
    assert report.timeline == ()

    with pytest.raises(ValueError, match="gap_threshold_days"):
        build_health_dossier(
            source_dir,
            profile_id="lukas",
            as_of=date(2026, 8, 22),
            extractor=FakeHealthExtractor(texts),
            allow_sensitive_local_read=True,
            gap_threshold_days=0,
        )


def test_health_report_handoff_is_non_executing_and_blocks_version_drift(
    tmp_path: Path,
) -> None:
    texts = {
        "bericht.txt": (
            "Dokumenttyp: Arztbericht\n"
            "Dokumentdatum: 2026-01-10\n"
            "Befund: Dokumentierter Satz.\n"
        ),
    }
    report = build_health_dossier(
        _source_folder(tmp_path, texts),
        profile_id="lukas",
        as_of=date(2026, 8, 22),
        extractor=FakeHealthExtractor(texts),
        allow_sensitive_local_read=True,
    )

    blocked = prepare_health_report_handoff(
        report,
        provider_id="report-forge",
        provider_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        distribution_version="1.1.4",
        runtime_version="1.1.0",
        requested_format="docx",
    )
    reviewed = prepare_health_report_handoff(
        report,
        provider_id="report-forge",
        provider_revision="355acb5ff1abe41b384a0d1e3a00925e6ac86215",
        distribution_version="1.1.4",
        runtime_version="1.1.4",
        requested_format="docx",
    )

    assert blocked.status == "blocked"
    assert "1.1.4" in blocked.reason and "1.1.0" in blocked.reason
    assert reviewed.status == "review_required"
    assert reviewed.payload_sha256 == blocked.payload_sha256
    assert reviewed.to_dict()["provider_invoked"] is False
    assert reviewed.to_dict()["network_used"] is False
    assert reviewed.to_dict()["contains_sensitive_data"] is True
