"""Contracts for a source-bound local weather and newspaper briefing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_ARTICLE_ID = re.compile(r"news_[0-9a-f]{64}")
_PLAN_ID = re.compile(r"briefing_plan_[0-9a-f]{64}")
_REPORT_ID = re.compile(r"briefing_(?:render|delivery)_report_[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_CATEGORY = re.compile(r"[a-z][a-z0-9_-]{1,31}")


def _timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} muss ein ISO-Zeitstempel sein.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} benötigt eine Zeitzone.")
    return parsed


def _https(value: str, field: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field} muss eine HTTPS-URL sein.")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ValueError(f"{field} muss eine HTTPS-URL ohne Zugangsdaten sein.")


@dataclass(frozen=True, slots=True)
class DailyBriefingRequest:
    request_id: str
    profile_id: str
    briefing_date: str
    as_of: str
    timezone: str
    title: str
    categories: tuple[str, ...]
    max_items_per_category: int
    max_weather_age_minutes: int
    max_news_age_minutes: int
    weather_snapshot_path: Path
    news_snapshot_path: Path

    SCHEMA = "folderhome.daily-briefing-request.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "weather_snapshot_path", self.weather_snapshot_path.resolve())
        object.__setattr__(self, "news_snapshot_path", self.news_snapshot_path.resolve())
        if not isinstance(self.request_id, str) or _ID.fullmatch(self.request_id) is None:
            raise ValueError("Briefinganfrage besitzt eine ungültige Anfrage-ID.")
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("Briefinganfrage benötigt ein Profil.")
        date.fromisoformat(self.briefing_date)
        _timestamp(self.as_of, "as_of")
        try:
            ZoneInfo(self.timezone)
        except (TypeError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Briefinganfrage besitzt eine unbekannte Zeitzone.") from exc
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 120:
            raise ValueError("Briefingtitel ist leer oder zu lang.")
        if not self.categories or len(set(self.categories)) != len(self.categories):
            raise ValueError("Briefingkategorien müssen eindeutig und nicht leer sein.")
        if any(
            not isinstance(item, str) or _CATEGORY.fullmatch(item) is None
            for item in self.categories
        ):
            raise ValueError("Briefingkategorie besitzt ein ungültiges Format.")
        for value, field, minimum, maximum in (
            (self.max_items_per_category, "max_items_per_category", 1, 25),
            (self.max_weather_age_minutes, "max_weather_age_minutes", 1, 1440),
            (self.max_news_age_minutes, "max_news_age_minutes", 1, 10080),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise ValueError(f"{field} liegt außerhalb des erlaubten Bereichs.")
        if self.weather_snapshot_path == self.news_snapshot_path:
            raise ValueError("Wetter- und Nachrichtensnapshot müssen getrennt sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "briefing_date": self.briefing_date,
            "as_of": self.as_of,
            "timezone": self.timezone,
            "title": self.title,
            "categories": list(self.categories),
            "max_items_per_category": self.max_items_per_category,
            "max_weather_age_minutes": self.max_weather_age_minutes,
            "max_news_age_minutes": self.max_news_age_minutes,
            "weather_snapshot_path": str(self.weather_snapshot_path),
            "news_snapshot_path": str(self.news_snapshot_path),
        }


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    provider_id: str
    provider_revision: str
    source_url: str
    location_label: str
    latitude_microdegrees: int
    longitude_microdegrees: int
    observed_at: str
    fetched_at: str
    condition: str
    temperature_tenths_c: int
    feels_like_tenths_c: int
    humidity_percent: int
    wind_speed_tenths_kmh: int
    forecast_date: str
    minimum_tenths_c: int
    maximum_tenths_c: int
    precipitation_probability_percent: int

    SCHEMA = "folderhome.weather-snapshot.v1"

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.provider_revision.strip():
            raise ValueError("Wettersnapshot benötigt eine Providerprovenienz.")
        _https(self.source_url, "Wetterquelle")
        if not self.location_label.strip() or len(self.location_label) > 120:
            raise ValueError("Wettersnapshot besitzt einen ungültigen Ort.")
        if not -90_000_000 <= self.latitude_microdegrees <= 90_000_000:
            raise ValueError("Breitengrad liegt außerhalb des erlaubten Bereichs.")
        if not -180_000_000 <= self.longitude_microdegrees <= 180_000_000:
            raise ValueError("Längengrad liegt außerhalb des erlaubten Bereichs.")
        _timestamp(self.observed_at, "observed_at")
        _timestamp(self.fetched_at, "fetched_at")
        if not self.condition.strip() or len(self.condition) > 120:
            raise ValueError("Wetterzustand ist leer oder zu lang.")
        for value, field, minimum, maximum in (
            (self.temperature_tenths_c, "temperature_tenths_c", -1000, 700),
            (self.feels_like_tenths_c, "feels_like_tenths_c", -1200, 800),
            (self.humidity_percent, "humidity_percent", 0, 100),
            (self.wind_speed_tenths_kmh, "wind_speed_tenths_kmh", 0, 5000),
            (self.minimum_tenths_c, "minimum_tenths_c", -1000, 700),
            (self.maximum_tenths_c, "maximum_tenths_c", -1000, 700),
            (
                self.precipitation_probability_percent,
                "precipitation_probability_percent",
                0,
                100,
            ),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise ValueError(f"{field} liegt außerhalb des erlaubten Bereichs.")
        if self.minimum_tenths_c > self.maximum_tenths_c:
            raise ValueError("Wetterminimum liegt über dem Maximum.")
        date.fromisoformat(self.forecast_date)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "source_url": self.source_url,
            "location_label": self.location_label,
            "latitude_microdegrees": self.latitude_microdegrees,
            "longitude_microdegrees": self.longitude_microdegrees,
            "observed_at": self.observed_at,
            "fetched_at": self.fetched_at,
            "condition": self.condition,
            "temperature_tenths_c": self.temperature_tenths_c,
            "feels_like_tenths_c": self.feels_like_tenths_c,
            "humidity_percent": self.humidity_percent,
            "wind_speed_tenths_kmh": self.wind_speed_tenths_kmh,
            "forecast_date": self.forecast_date,
            "minimum_tenths_c": self.minimum_tenths_c,
            "maximum_tenths_c": self.maximum_tenths_c,
            "precipitation_probability_percent": self.precipitation_probability_percent,
        }


@dataclass(frozen=True, slots=True)
class NewsArticle:
    article_id: str
    title: str
    summary: str
    source_name: str
    source_url: str
    article_url: str
    category: str
    published_at: str
    fetched_at: str

    SCHEMA = "folderhome.news-article.v1"

    def __post_init__(self) -> None:
        if _ARTICLE_ID.fullmatch(self.article_id) is None:
            raise ValueError("Nachrichtenartikel besitzt eine ungültige ID.")
        for value, field, limit in (
            (self.title, "Titel", 240),
            (self.summary, "Zusammenfassung", 1200),
            (self.source_name, "Quellenname", 160),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{field} ist leer oder zu lang.")
        _https(self.source_url, "Nachrichtenquelle")
        _https(self.article_url, "Artikellink")
        if _CATEGORY.fullmatch(self.category) is None:
            raise ValueError("Nachrichtenartikel besitzt eine ungültige Kategorie.")
        _timestamp(self.published_at, "published_at")
        _timestamp(self.fetched_at, "fetched_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "article_id": self.article_id,
            "title": self.title,
            "summary": self.summary,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "article_url": self.article_url,
            "category": self.category,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
        }


@dataclass(frozen=True, slots=True)
class NewsSnapshot:
    provider_id: str
    provider_revision: str
    fetched_at: str
    articles: tuple[NewsArticle, ...]

    SCHEMA = "folderhome.news-snapshot.v1"

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.provider_revision.strip():
            raise ValueError("Nachrichtensnapshot benötigt eine Providerprovenienz.")
        _timestamp(self.fetched_at, "fetched_at")
        ids = [article.article_id for article in self.articles]
        if len(ids) != len(set(ids)):
            raise ValueError("Nachrichtensnapshot enthält doppelte Artikel-IDs.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "provider_id": self.provider_id,
            "provider_revision": self.provider_revision,
            "fetched_at": self.fetched_at,
            "articles": [article.to_dict() for article in self.articles],
        }


@dataclass(frozen=True, slots=True)
class DailyBriefingPlan:
    plan_id: str
    plan_sha256: str
    request: DailyBriefingRequest
    weather: WeatherSnapshot
    articles: tuple[NewsArticle, ...]
    weather_snapshot_sha256: str
    news_snapshot_sha256: str
    weather_freshness: str
    news_freshness: str
    omitted_article_count: int
    warnings: tuple[str, ...]
    html_content: str
    html_sha256: str
    output_path: Path
    desktop_path: Path
    status: str
    render_allowed: bool
    network_invoked: bool = False
    scheduler_registered: bool = False

    SCHEMA = "folderhome.daily-briefing-plan.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", self.output_path.resolve())
        object.__setattr__(self, "desktop_path", self.desktop_path.resolve())
        if _PLAN_ID.fullmatch(self.plan_id) is None:
            raise ValueError("Briefingplan besitzt eine ungültige Plan-ID.")
        for value in (
            self.plan_sha256,
            self.weather_snapshot_sha256,
            self.news_snapshot_sha256,
            self.html_sha256,
        ):
            if _SHA256.fullmatch(value) is None:
                raise ValueError("Briefingplan besitzt eine ungültige Hashbindung.")
        if self.weather_freshness not in {"fresh", "stale"}:
            raise ValueError("Briefingplan besitzt einen unbekannten Wetterdatenstand.")
        if self.news_freshness not in {"fresh", "stale"}:
            raise ValueError("Briefingplan besitzt einen unbekannten Nachrichtendatenstand.")
        if self.status not in {"ready_for_approval", "review_required"}:
            raise ValueError("Briefingplan besitzt einen unbekannten Status.")
        if not self.render_allowed or self.network_invoked or self.scheduler_registered:
            raise ValueError("Briefingplan überschreitet die lokale Planungsgrenze.")
        if self.output_path == self.desktop_path:
            raise ValueError("Ausgabe und Desktopziel müssen getrennte Pfade sein.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "plan_id": self.plan_id,
            "plan_sha256": self.plan_sha256,
            "request": self.request.to_dict(),
            "weather": self.weather.to_dict(),
            "articles": [article.to_dict() for article in self.articles],
            "weather_snapshot_sha256": self.weather_snapshot_sha256,
            "news_snapshot_sha256": self.news_snapshot_sha256,
            "weather_freshness": self.weather_freshness,
            "news_freshness": self.news_freshness,
            "omitted_article_count": self.omitted_article_count,
            "warnings": list(self.warnings),
            "html_content": self.html_content,
            "html_sha256": self.html_sha256,
            "output_path": str(self.output_path),
            "desktop_path": str(self.desktop_path),
            "status": self.status,
            "render_allowed": self.render_allowed,
            "network_invoked": False,
            "scheduler_registered": False,
        }


@dataclass(frozen=True, slots=True)
class BriefingRenderApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    html_sha256: str
    output_path: Path
    approved_at: str
    allow_output_write: bool

    SCHEMA = "folderhome.briefing-render-approval.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", self.output_path.resolve())
        _validate_approval(self.approval_id, self.plan_id, self.plan_sha256, self.html_sha256)
        _timestamp(self.approved_at, "approved_at")
        if not isinstance(self.allow_output_write, bool):
            raise ValueError("Renderfreigabe benötigt einen booleschen Schreibschalter.")


@dataclass(frozen=True, slots=True)
class BriefingDeliveryApproval:
    approval_id: str
    plan_id: str
    plan_sha256: str
    html_sha256: str
    desktop_path: Path
    approved_at: str
    allow_desktop_write: bool

    SCHEMA = "folderhome.briefing-delivery-approval.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "desktop_path", self.desktop_path.resolve())
        _validate_approval(self.approval_id, self.plan_id, self.plan_sha256, self.html_sha256)
        _timestamp(self.approved_at, "approved_at")
        if not isinstance(self.allow_desktop_write, bool):
            raise ValueError("Desktopfreigabe benötigt einen booleschen Schreibschalter.")


@dataclass(frozen=True, slots=True)
class BriefingRenderReport:
    report_id: str
    plan_id: str
    approval_id: str
    output_path: Path
    output_sha256: str
    status: str
    network_invoked: bool = False

    SCHEMA = "folderhome.briefing-render-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", self.output_path.resolve())
        _validate_report(self.report_id, self.output_sha256, self.status)
        if self.network_invoked:
            raise ValueError("Briefingausgabe darf keinen Netzwerkzugriff ausweisen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "output_path": str(self.output_path),
            "output_sha256": self.output_sha256,
            "status": self.status,
            "network_invoked": False,
        }


@dataclass(frozen=True, slots=True)
class BriefingDeliveryReport:
    report_id: str
    plan_id: str
    approval_id: str
    desktop_path: Path
    output_sha256: str
    status: str
    desktop_written: bool
    scheduler_registered: bool = False
    network_invoked: bool = False

    SCHEMA = "folderhome.briefing-delivery-report.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "desktop_path", self.desktop_path.resolve())
        _validate_report(self.report_id, self.output_sha256, self.status)
        if not self.desktop_written or self.scheduler_registered or self.network_invoked:
            raise ValueError("Briefingzustellung besitzt eine ungültige Wirkungsangabe.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "desktop_path": str(self.desktop_path),
            "output_sha256": self.output_sha256,
            "status": self.status,
            "desktop_written": True,
            "scheduler_registered": False,
            "network_invoked": False,
        }


def _validate_approval(
    approval_id: str,
    plan_id: str,
    plan_sha256: str,
    html_sha256: str,
) -> None:
    if _ID.fullmatch(approval_id) is None or _PLAN_ID.fullmatch(plan_id) is None:
        raise ValueError("Briefingfreigabe besitzt ungültige IDs.")
    if _SHA256.fullmatch(plan_sha256) is None or _SHA256.fullmatch(html_sha256) is None:
        raise ValueError("Briefingfreigabe besitzt ungültige Hashbindungen.")


def _validate_report(report_id: str, output_sha256: str, status: str) -> None:
    if _REPORT_ID.fullmatch(report_id) is None or _SHA256.fullmatch(output_sha256) is None:
        raise ValueError("Briefingbericht besitzt eine ungültige Identität.")
    if status != "executed":
        raise ValueError("Briefingbericht besitzt einen ungültigen Status.")
