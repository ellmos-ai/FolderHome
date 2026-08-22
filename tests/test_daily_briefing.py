from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.application.daily_briefing import (
    DailyBriefingError,
    build_daily_briefing_plan,
    deliver_daily_briefing,
    load_daily_briefing_request,
    render_daily_briefing,
)
from folderhome.contracts import (
    BriefingDeliveryApproval,
    BriefingRenderApproval,
)


def _write_inputs(tmp_path: Path, *, weather_at: str, news_at: str) -> Path:
    weather_file = tmp_path / "weather.json"
    weather_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.weather-snapshot.v1",
                "provider_id": "synthetic-weather",
                "provider_revision": "fixture-v1",
                "source_url": "https://weather.example.invalid/berlin",
                "location_label": "Berlin",
                "latitude_microdegrees": 52520000,
                "longitude_microdegrees": 13405000,
                "observed_at": weather_at,
                "fetched_at": weather_at,
                "condition": "Leicht bewölkt",
                "temperature_tenths_c": 184,
                "feels_like_tenths_c": 179,
                "humidity_percent": 61,
                "wind_speed_tenths_kmh": 126,
                "forecast_date": "2026-08-22",
                "minimum_tenths_c": 142,
                "maximum_tenths_c": 231,
                "precipitation_probability_percent": 20,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.news-snapshot.v1",
                "provider_id": "synthetic-news",
                "provider_revision": "fixture-v1",
                "fetched_at": news_at,
                "articles": [
                    {
                        "schema": "folderhome.news-article.v1",
                        "article_id": "news_" + "a" * 64,
                        "title": "Neue Bibliothek eröffnet",
                        "summary": "Die erfundene Stadtbibliothek erweitert ihr Angebot.",
                        "source_name": "Beispiel Nachrichten",
                        "source_url": "https://news.example.invalid/feed.xml",
                        "article_url": "https://news.example.invalid/bibliothek",
                        "category": "lokales",
                        "published_at": "2026-08-22T05:30:00+02:00",
                        "fetched_at": news_at,
                    },
                    {
                        "schema": "folderhome.news-article.v1",
                        "article_id": "news_" + "b" * 64,
                        "title": "Forschungsteam veröffentlicht Datensatz",
                        "summary": "Ein rein synthetischer Datensatz steht zur Prüfung bereit.",
                        "source_name": "Beispiel Wissenschaft",
                        "source_url": "https://science.example.invalid/feed.xml",
                        "article_url": "https://science.example.invalid/datensatz",
                        "category": "wissenschaft",
                        "published_at": "2026-08-22T05:00:00+02:00",
                        "fetched_at": news_at,
                    },
                    {
                        "schema": "folderhome.news-article.v1",
                        "article_id": "news_" + "c" * 64,
                        "title": "Nicht gewählte Sportmeldung",
                        "summary": "Dieser Artikel wird nach Kategorie gefiltert.",
                        "source_name": "Beispiel Sport",
                        "source_url": "https://sport.example.invalid/feed.xml",
                        "article_url": "https://sport.example.invalid/spiel",
                        "category": "sport",
                        "published_at": "2026-08-22T04:30:00+02:00",
                        "fetched_at": news_at,
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    request_file = tmp_path / "request.json"
    request_file.write_text(
        json.dumps(
            {
                "schema": "folderhome.daily-briefing-request.v1",
                "request_id": "morning-brief-demo",
                "profile_id": "lukas",
                "briefing_date": "2026-08-22",
                "as_of": "2026-08-22T06:00:00+02:00",
                "timezone": "Europe/Berlin",
                "title": "FolderHome Morgenbrief",
                "categories": ["lokales", "wissenschaft"],
                "max_items_per_category": 1,
                "max_weather_age_minutes": 180,
                "max_news_age_minutes": 180,
                "weather_snapshot_path": str(weather_file),
                "news_snapshot_path": str(news_file),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return request_file


def _plan(tmp_path: Path, *, weather_at: str, news_at: str):
    request = load_daily_briefing_request(
        _write_inputs(tmp_path, weather_at=weather_at, news_at=news_at)
    )
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    return build_daily_briefing_plan(
        request,
        known_profile_ids={"lukas", "hanna"},
        output_path=tmp_path / "Ausgabe" / "Morgenbrief.html",
        desktop_path=desktop / "Morgenbrief.html",
        allow_sensitive_local_read=True,
    )


def test_fresh_plan_filters_categories_and_is_read_only(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        weather_at="2026-08-22T05:45:00+02:00",
        news_at="2026-08-22T05:50:00+02:00",
    )

    assert plan.status == "ready_for_approval"
    assert [article.category for article in plan.articles] == [
        "lokales",
        "wissenschaft",
    ]
    assert plan.omitted_article_count == 1
    assert plan.weather_freshness == "fresh"
    assert plan.news_freshness == "fresh"
    assert plan.network_invoked is False
    assert "Leicht bewölkt" in plan.html_content
    assert "Neue Bibliothek eröffnet" in plan.html_content
    assert "Nicht gewählte Sportmeldung" not in plan.html_content
    assert not plan.output_path.exists()
    assert not plan.desktop_path.exists()


def test_stale_snapshots_remain_visible_and_require_review(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        weather_at="2026-08-21T18:00:00+02:00",
        news_at="2026-08-21T18:00:00+02:00",
    )

    assert plan.status == "review_required"
    assert plan.render_allowed is True
    assert plan.weather_freshness == "stale"
    assert plan.news_freshness == "stale"
    assert any("veraltet" in warning for warning in plan.warnings)
    assert "Datenstand und Grenzen" in plan.html_content


def test_render_requires_exact_approval_and_never_overwrites(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        weather_at="2026-08-22T05:45:00+02:00",
        news_at="2026-08-22T05:50:00+02:00",
    )
    approval = BriefingRenderApproval(
        approval_id="briefing-render-approval",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        html_sha256=plan.html_sha256,
        output_path=plan.output_path,
        approved_at="2026-08-22T06:01:00+02:00",
        allow_output_write=True,
    )

    with pytest.raises(DailyBriefingError, match="Ausgabefreigabe"):
        render_daily_briefing(plan, approval, allow_output_write=False)
    report = render_daily_briefing(plan, approval, allow_output_write=True)

    assert report.output_path.read_text(encoding="utf-8") == plan.html_content
    assert report.network_invoked is False
    with pytest.raises(DailyBriefingError, match="existiert bereits"):
        render_daily_briefing(plan, approval, allow_output_write=True)


def test_desktop_delivery_has_separate_gate_and_exact_source_hash(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        weather_at="2026-08-22T05:45:00+02:00",
        news_at="2026-08-22T05:50:00+02:00",
    )
    render_approval = BriefingRenderApproval(
        approval_id="briefing-render-approval",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        html_sha256=plan.html_sha256,
        output_path=plan.output_path,
        approved_at="2026-08-22T06:01:00+02:00",
        allow_output_write=True,
    )
    render_daily_briefing(plan, render_approval, allow_output_write=True)
    delivery_approval = BriefingDeliveryApproval(
        approval_id="briefing-delivery-approval",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        html_sha256=plan.html_sha256,
        desktop_path=plan.desktop_path,
        approved_at="2026-08-22T06:02:00+02:00",
        allow_desktop_write=True,
    )

    with pytest.raises(DailyBriefingError, match="Desktopfreigabe"):
        deliver_daily_briefing(plan, delivery_approval, allow_desktop_write=False)
    report = deliver_daily_briefing(
        plan,
        delivery_approval,
        allow_desktop_write=True,
    )

    assert report.desktop_path.read_bytes() == plan.output_path.read_bytes()
    assert report.desktop_written is True
    assert report.scheduler_registered is False


def test_changed_rendered_file_blocks_desktop_delivery(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        weather_at="2026-08-22T05:45:00+02:00",
        news_at="2026-08-22T05:50:00+02:00",
    )
    plan.output_path.parent.mkdir(parents=True)
    plan.output_path.write_text("verändert", encoding="utf-8")
    approval = BriefingDeliveryApproval(
        approval_id="briefing-delivery-approval",
        plan_id=plan.plan_id,
        plan_sha256=plan.plan_sha256,
        html_sha256=plan.html_sha256,
        desktop_path=plan.desktop_path,
        approved_at="2026-08-22T06:02:00+02:00",
        allow_desktop_write=True,
    )

    with pytest.raises(DailyBriefingError, match="Ausgabehash"):
        deliver_daily_briefing(plan, approval, allow_desktop_write=True)
    assert not plan.desktop_path.exists()


def test_future_snapshot_and_non_https_source_are_rejected(tmp_path: Path) -> None:
    request_file = _write_inputs(
        tmp_path,
        weather_at="2026-08-22T07:00:00+02:00",
        news_at="2026-08-22T05:50:00+02:00",
    )
    request = load_daily_briefing_request(request_file)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()

    with pytest.raises(DailyBriefingError, match="Zukunft"):
        build_daily_briefing_plan(
            request,
            known_profile_ids={"lukas"},
            output_path=tmp_path / "out.html",
            desktop_path=desktop / "out.html",
            allow_sensitive_local_read=True,
        )

    weather_payload = json.loads(request.weather_snapshot_path.read_text(encoding="utf-8"))
    weather_payload["observed_at"] = "2026-08-22T05:45:00+02:00"
    weather_payload["fetched_at"] = "2026-08-22T05:45:00+02:00"
    weather_payload["source_url"] = "file:///private/weather.json"
    request.weather_snapshot_path.write_text(json.dumps(weather_payload), encoding="utf-8")
    with pytest.raises(DailyBriefingError, match="HTTPS"):
        build_daily_briefing_plan(
            request,
            known_profile_ids={"lukas"},
            output_path=tmp_path / "out.html",
            desktop_path=desktop / "out.html",
            allow_sensitive_local_read=True,
        )


def test_unknown_profile_and_missing_sensitivity_gate_block_before_read(
    tmp_path: Path,
) -> None:
    request = load_daily_briefing_request(
        _write_inputs(
            tmp_path,
            weather_at="2026-08-22T05:45:00+02:00",
            news_at="2026-08-22T05:50:00+02:00",
        )
    )
    desktop = tmp_path / "Desktop"
    desktop.mkdir()

    with pytest.raises(DailyBriefingError, match="Sensitivitätsfreigabe"):
        build_daily_briefing_plan(
            request,
            known_profile_ids={"lukas"},
            output_path=tmp_path / "out.html",
            desktop_path=desktop / "out.html",
            allow_sensitive_local_read=False,
        )
    with pytest.raises(DailyBriefingError, match="Unbekanntes Profil"):
        build_daily_briefing_plan(
            request,
            known_profile_ids={"hanna"},
            output_path=tmp_path / "out.html",
            desktop_path=desktop / "out.html",
            allow_sensitive_local_read=True,
        )
