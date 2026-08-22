"""Build and deliver a deterministic local weather and newspaper briefing."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from hashlib import sha256
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from folderhome.contracts.daily_briefing import (
    BriefingDeliveryApproval,
    BriefingDeliveryReport,
    BriefingRenderApproval,
    BriefingRenderReport,
    DailyBriefingPlan,
    DailyBriefingRequest,
    NewsArticle,
    NewsSnapshot,
    WeatherSnapshot,
)


class DailyBriefingError(RuntimeError):
    """Raised before an untrusted briefing read, render, or delivery."""


def load_daily_briefing_request(path: Path) -> DailyBriefingRequest:
    payload = _load_object(path, DailyBriefingRequest.SCHEMA, "Briefinganfrage")
    expected = {
        "schema",
        "request_id",
        "profile_id",
        "briefing_date",
        "as_of",
        "timezone",
        "title",
        "categories",
        "max_items_per_category",
        "max_weather_age_minutes",
        "max_news_age_minutes",
        "weather_snapshot_path",
        "news_snapshot_path",
    }
    if set(payload) != expected:
        raise DailyBriefingError("Briefinganfrage besitzt unbekannte oder fehlende Felder.")
    categories = payload["categories"]
    if not isinstance(categories, list) or not all(isinstance(item, str) for item in categories):
        raise DailyBriefingError("Briefinganfrage benötigt eine gültige Kategorienliste.")
    try:
        return DailyBriefingRequest(
            request_id=payload["request_id"],
            profile_id=payload["profile_id"],
            briefing_date=payload["briefing_date"],
            as_of=payload["as_of"],
            timezone=payload["timezone"],
            title=payload["title"],
            categories=tuple(categories),
            max_items_per_category=payload["max_items_per_category"],
            max_weather_age_minutes=payload["max_weather_age_minutes"],
            max_news_age_minutes=payload["max_news_age_minutes"],
            weather_snapshot_path=_resolve_input_path(
                payload["weather_snapshot_path"],
                relative_to=path.parent,
                field="weather_snapshot_path",
            ),
            news_snapshot_path=_resolve_input_path(
                payload["news_snapshot_path"],
                relative_to=path.parent,
                field="news_snapshot_path",
            ),
        )
    except (TypeError, ValueError) as exc:
        raise DailyBriefingError(f"Briefinganfrage ist ungültig: {exc}") from exc


def build_daily_briefing_plan(
    request: DailyBriefingRequest,
    *,
    known_profile_ids: set[str],
    output_path: Path,
    desktop_path: Path,
    allow_sensitive_local_read: bool,
    allow_existing_output: bool = False,
) -> DailyBriefingPlan:
    if not allow_sensitive_local_read:
        raise DailyBriefingError("Sensitivitätsfreigabe für lokale Briefingdaten fehlt.")
    if request.profile_id not in known_profile_ids:
        raise DailyBriefingError(f"Unbekanntes Profil: {request.profile_id}")
    output_path = output_path.resolve()
    desktop_path = desktop_path.resolve()
    _validate_output_paths(
        request,
        output_path=output_path,
        desktop_path=desktop_path,
        allow_existing_output=allow_existing_output,
    )
    weather_sha = _file_sha(request.weather_snapshot_path)
    news_sha = _file_sha(request.news_snapshot_path)
    weather = _load_weather_snapshot(request.weather_snapshot_path)
    news = _load_news_snapshot(request.news_snapshot_path)
    as_of = _timestamp(request.as_of)
    zone = ZoneInfo(request.timezone)
    if as_of.astimezone(zone).date().isoformat() != request.briefing_date:
        raise DailyBriefingError("Briefingdatum passt nicht zum lokalen as_of-Datum.")
    _reject_future("Wetterbeobachtung", _timestamp(weather.observed_at), as_of)
    _reject_future("Wetterabruf", _timestamp(weather.fetched_at), as_of)
    _reject_future("Nachrichtenabruf", _timestamp(news.fetched_at), as_of)
    for article in news.articles:
        _reject_future("Artikelveröffentlichung", _timestamp(article.published_at), as_of)
        _reject_future("Artikelabruf", _timestamp(article.fetched_at), as_of)

    weather_age = int((as_of - _timestamp(weather.fetched_at)).total_seconds() // 60)
    news_age = int((as_of - _timestamp(news.fetched_at)).total_seconds() // 60)
    weather_freshness = (
        "fresh" if weather_age <= request.max_weather_age_minutes else "stale"
    )
    news_freshness = "fresh" if news_age <= request.max_news_age_minutes else "stale"
    warnings: list[str] = []
    if weather_freshness == "stale":
        warnings.append(f"Wetterdaten sind mit {weather_age} Minuten veraltet.")
    if news_freshness == "stale":
        warnings.append(f"Nachrichtendaten sind mit {news_age} Minuten veraltet.")
    if weather.forecast_date != request.briefing_date:
        warnings.append(
            "Wetterprognose gehört nicht zum Briefingdatum und muss geprüft werden."
        )

    selected = _select_articles(news, request)
    omitted = len(news.articles) - len(selected)
    if not selected:
        warnings.append("Keine Nachricht passt zu den gewählten Kategorien.")
    status = "ready_for_approval" if not warnings else "review_required"
    html_content = _render_html(
        request,
        weather=weather,
        articles=selected,
        warnings=tuple(warnings),
    )
    html_sha = _text_sha(html_content)
    core = {
        "request": request.to_dict(),
        "weather_snapshot_sha256": weather_sha,
        "news_snapshot_sha256": news_sha,
        "article_ids": [article.article_id for article in selected],
        "warnings": warnings,
        "html_sha256": html_sha,
        "output_path": str(output_path),
        "desktop_path": str(desktop_path),
        "status": status,
    }
    plan_id = f"briefing_plan_{_text_sha(_canonical(core))}"
    plan_sha = _text_sha(_canonical({**core, "plan_id": plan_id}))
    return DailyBriefingPlan(
        plan_id=plan_id,
        plan_sha256=plan_sha,
        request=request,
        weather=weather,
        articles=selected,
        weather_snapshot_sha256=weather_sha,
        news_snapshot_sha256=news_sha,
        weather_freshness=weather_freshness,
        news_freshness=news_freshness,
        omitted_article_count=omitted,
        warnings=tuple(warnings),
        html_content=html_content,
        html_sha256=html_sha,
        output_path=output_path,
        desktop_path=desktop_path,
        status=status,
        render_allowed=True,
    )


def render_daily_briefing(
    plan: DailyBriefingPlan,
    approval: BriefingRenderApproval,
    *,
    allow_output_write: bool,
) -> BriefingRenderReport:
    if not allow_output_write or not approval.allow_output_write:
        raise DailyBriefingError("Ausgabefreigabe für den Briefingrender fehlt.")
    if (
        approval.plan_id != plan.plan_id
        or approval.plan_sha256 != plan.plan_sha256
        or approval.html_sha256 != plan.html_sha256
        or approval.output_path != plan.output_path
    ):
        raise DailyBriefingError("Renderfreigabe stimmt nicht exakt mit dem Plan überein.")
    if _text_sha(plan.html_content) != plan.html_sha256:
        raise DailyBriefingError("Briefinginhalt stimmt nicht mit dem Planhash überein.")
    _verify_input_hashes(plan)
    if plan.output_path.exists():
        raise DailyBriefingError(f"Briefingausgabe existiert bereits: {plan.output_path}")
    try:
        plan.output_path.parent.mkdir(parents=True, exist_ok=True)
        with plan.output_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(plan.html_content)
    except (OSError, UnicodeError) as exc:
        raise DailyBriefingError(f"Briefingausgabe konnte nicht geschrieben werden: {exc}") from exc
    output_sha = _file_sha(plan.output_path)
    if output_sha != plan.html_sha256:
        raise DailyBriefingError("Briefingausgabe bestand den Hash-Readback nicht.")
    return BriefingRenderReport(
        report_id=f"briefing_render_report_{_text_sha(plan.plan_id + ':' + output_sha)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        output_path=plan.output_path,
        output_sha256=output_sha,
        status="executed",
    )


def deliver_daily_briefing(
    plan: DailyBriefingPlan,
    approval: BriefingDeliveryApproval,
    *,
    allow_desktop_write: bool,
) -> BriefingDeliveryReport:
    if not allow_desktop_write or not approval.allow_desktop_write:
        raise DailyBriefingError("Desktopfreigabe für die Briefingzustellung fehlt.")
    if (
        approval.plan_id != plan.plan_id
        or approval.plan_sha256 != plan.plan_sha256
        or approval.html_sha256 != plan.html_sha256
        or approval.desktop_path != plan.desktop_path
    ):
        raise DailyBriefingError("Desktopfreigabe stimmt nicht exakt mit dem Plan überein.")
    if not plan.output_path.is_file() or _file_sha(plan.output_path) != plan.html_sha256:
        raise DailyBriefingError("Briefing-Ausgabehash stimmt nicht mit dem Plan überein.")
    if plan.desktop_path.exists():
        raise DailyBriefingError(f"Desktopziel existiert bereits: {plan.desktop_path}")
    if not plan.desktop_path.parent.is_dir():
        raise DailyBriefingError("Der ausdrücklich gewählte Desktopordner existiert nicht.")
    content = plan.output_path.read_bytes()
    try:
        with plan.desktop_path.open("xb") as handle:
            handle.write(content)
    except OSError as exc:
        raise DailyBriefingError(
            f"Desktopzustellung konnte nicht geschrieben werden: {exc}"
        ) from exc
    output_sha = _file_sha(plan.desktop_path)
    if output_sha != plan.html_sha256:
        raise DailyBriefingError("Desktopzustellung bestand den Hash-Readback nicht.")
    return BriefingDeliveryReport(
        report_id=f"briefing_delivery_report_{_text_sha(plan.plan_id + ':' + output_sha)}",
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        desktop_path=plan.desktop_path,
        output_sha256=output_sha,
        status="executed",
        desktop_written=True,
    )


def _load_weather_snapshot(path: Path) -> WeatherSnapshot:
    payload = _load_object(path, WeatherSnapshot.SCHEMA, "Wettersnapshot")
    expected = {
        "schema",
        "provider_id",
        "provider_revision",
        "source_url",
        "location_label",
        "latitude_microdegrees",
        "longitude_microdegrees",
        "observed_at",
        "fetched_at",
        "condition",
        "temperature_tenths_c",
        "feels_like_tenths_c",
        "humidity_percent",
        "wind_speed_tenths_kmh",
        "forecast_date",
        "minimum_tenths_c",
        "maximum_tenths_c",
        "precipitation_probability_percent",
    }
    if set(payload) != expected:
        raise DailyBriefingError("Wettersnapshot besitzt unbekannte oder fehlende Felder.")
    try:
        return WeatherSnapshot(**{key: value for key, value in payload.items() if key != "schema"})
    except (TypeError, ValueError) as exc:
        raise DailyBriefingError(f"Wettersnapshot ist ungültig: {exc}") from exc


def _load_news_snapshot(path: Path) -> NewsSnapshot:
    payload = _load_object(path, NewsSnapshot.SCHEMA, "Nachrichtensnapshot")
    if set(payload) != {"schema", "provider_id", "provider_revision", "fetched_at", "articles"}:
        raise DailyBriefingError("Nachrichtensnapshot besitzt unbekannte oder fehlende Felder.")
    raw_articles = payload["articles"]
    if not isinstance(raw_articles, list):
        raise DailyBriefingError("Nachrichtensnapshot benötigt eine Artikelliste.")
    articles = tuple(_load_news_article(item, index) for index, item in enumerate(raw_articles))
    try:
        return NewsSnapshot(
            provider_id=payload["provider_id"],
            provider_revision=payload["provider_revision"],
            fetched_at=payload["fetched_at"],
            articles=articles,
        )
    except (TypeError, ValueError) as exc:
        raise DailyBriefingError(f"Nachrichtensnapshot ist ungültig: {exc}") from exc


def _load_news_article(payload: object, index: int) -> NewsArticle:
    expected = {
        "schema",
        "article_id",
        "title",
        "summary",
        "source_name",
        "source_url",
        "article_url",
        "category",
        "published_at",
        "fetched_at",
    }
    if not isinstance(payload, dict) or payload.get("schema") != NewsArticle.SCHEMA:
        raise DailyBriefingError(f"Nachrichtenartikel {index} besitzt ein unbekanntes Schema.")
    if set(payload) != expected:
        raise DailyBriefingError(f"Nachrichtenartikel {index} besitzt ungültige Felder.")
    try:
        return NewsArticle(**{key: value for key, value in payload.items() if key != "schema"})
    except (TypeError, ValueError) as exc:
        raise DailyBriefingError(f"Nachrichtenartikel {index} ist ungültig: {exc}") from exc


def _select_articles(
    snapshot: NewsSnapshot,
    request: DailyBriefingRequest,
) -> tuple[NewsArticle, ...]:
    selected: list[NewsArticle] = []
    for category in request.categories:
        matches = sorted(
            (article for article in snapshot.articles if article.category == category),
            key=lambda article: (_timestamp(article.published_at), article.article_id),
            reverse=True,
        )
        selected.extend(matches[: request.max_items_per_category])
    return tuple(selected)


def _render_html(
    request: DailyBriefingRequest,
    *,
    weather: WeatherSnapshot,
    articles: tuple[NewsArticle, ...],
    warnings: tuple[str, ...],
) -> str:
    sections = []
    for category in request.categories:
        category_articles = [article for article in articles if article.category == category]
        if not category_articles:
            continue
        article_html = []
        for article in category_articles:
            article_html.append(
                "<article>"
                f"<h3>{escape(article.title)}</h3>"
                f"<p>{escape(article.summary)}</p>"
                f'<p class="source">{escape(article.source_name)} · '
                f'<a href="{escape(article.article_url, quote=True)}">Quelle öffnen</a> · '
                f"{escape(article.published_at)}</p>"
                "</article>"
            )
        sections.append(
            f"<section><h2>{escape(category.title())}</h2>{''.join(article_html)}</section>"
        )
    warning_html = "".join(f"<li>{escape(item)}</li>" for item in warnings)
    if not warning_html:
        warning_html = "<li>Lokale Snapshots liegen innerhalb der gewählten Altersgrenzen.</li>"
    return (
        "<!doctype html>\n"
        '<html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(request.title)}</title>"
        "<style>body{font:18px/1.55 system-ui,sans-serif;max-width:850px;margin:2rem auto;"
        "padding:0 1rem;color:#17202a;background:#fff}h1,h2{color:#123b5d}"
        ".weather,article,.limits{border:1px solid #ccd6dd;border-radius:12px;"
        "padding:1rem;margin:1rem 0}.source{font-size:.85rem;color:#40515f}"
        "a{color:#005ea8}</style></head><body>"
        f"<header><h1>{escape(request.title)}</h1>"
        f"<p>{escape(request.briefing_date)} · Profil {escape(request.profile_id)}</p></header>"
        '<section class="weather"><h2>Wetter</h2>'
        f"<h3>{escape(weather.location_label)} · {escape(weather.condition)}</h3>"
        f"<p>{_tenths(weather.temperature_tenths_c)} °C, gefühlt "
        f"{_tenths(weather.feels_like_tenths_c)} °C · Luftfeuchtigkeit "
        f"{weather.humidity_percent} % · Wind {_tenths(weather.wind_speed_tenths_kmh)} km/h</p>"
        f"<p>Tagesbereich {_tenths(weather.minimum_tenths_c)} bis "
        f"{_tenths(weather.maximum_tenths_c)} °C · Niederschlagswahrscheinlichkeit "
        f"{weather.precipitation_probability_percent} %</p>"
        f'<p class="source"><a href="{escape(weather.source_url, quote=True)}">Wetterquelle</a> · '
        f"beobachtet {escape(weather.observed_at)} · abgerufen {escape(weather.fetched_at)}</p>"
        "</section>"
        f"{''.join(sections)}"
        '<section class="limits"><h2>Datenstand und Grenzen</h2><ul>'
        f"{warning_html}</ul>"
        f"<p>Erzeugt aus lokalen Snapshots zum Stand {escape(request.as_of)}. "
        "Kein Live-Abruf, keine Vollständigkeitsgarantie und keine automatische "
        "Desktop- oder Scheduler-Aktion.</p></section>"
        "</body></html>\n"
    )


def _validate_output_paths(
    request: DailyBriefingRequest,
    *,
    output_path: Path,
    desktop_path: Path,
    allow_existing_output: bool,
) -> None:
    if output_path.suffix.lower() != ".html" or desktop_path.suffix.lower() != ".html":
        raise DailyBriefingError("Briefingausgabe und Desktopziel müssen HTML-Dateien sein.")
    if output_path == desktop_path:
        raise DailyBriefingError("Briefingausgabe und Desktopziel müssen getrennt sein.")
    if output_path.is_relative_to(desktop_path.parent):
        raise DailyBriefingError(
            "Zwischenausgabe darf nicht bereits im gewählten Desktopordner liegen."
        )
    for target in (output_path, desktop_path):
        if target in {request.weather_snapshot_path, request.news_snapshot_path}:
            raise DailyBriefingError("Briefingziel darf keinen Eingabesnapshot ersetzen.")
        if target.exists() and not (allow_existing_output and target == output_path):
            raise DailyBriefingError(f"Briefingziel existiert bereits: {target}")


def _verify_input_hashes(plan: DailyBriefingPlan) -> None:
    if _file_sha(plan.request.weather_snapshot_path) != plan.weather_snapshot_sha256:
        raise DailyBriefingError("Wettersnapshot hat sich seit dem Plan geändert.")
    if _file_sha(plan.request.news_snapshot_path) != plan.news_snapshot_sha256:
        raise DailyBriefingError("Nachrichtensnapshot hat sich seit dem Plan geändert.")


def _load_object(path: Path, schema: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DailyBriefingError(f"{label} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise DailyBriefingError(f"{label} besitzt ein unbekanntes Schema.")
    return payload


def _resolve_input_path(value: object, *, relative_to: Path, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise DailyBriefingError(f"{field} muss ein Dateipfad sein.")
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (relative_to / candidate).resolve()


def _reject_future(label: str, value: datetime, as_of: datetime) -> None:
    if value > as_of + timedelta(minutes=5):
        raise DailyBriefingError(f"{label} liegt unzulässig in der Zukunft.")


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _file_sha(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise DailyBriefingError(f"Briefingdatei ist nicht lesbar: {path}: {exc}") from exc
    return digest.hexdigest()


def _text_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _tenths(value: int) -> str:
    return f"{value / 10:.1f}".replace(".", ",")
