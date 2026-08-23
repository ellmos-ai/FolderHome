from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.demo_site import DemoSiteApplication


def _headers(port: int, token: str, *, content_type: bool = False) -> dict[str, str]:
    headers = {
        "Host": f"127.0.0.1:{port}",
        "Origin": f"http://127.0.0.1:{port}",
        "X-FolderHome-Token": token,
    }
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _post(
    app: DemoSiteApplication,
    path: str,
    payload: dict[str, object],
    *,
    port: int,
):
    return app.handle(
        method="POST",
        target=path,
        headers=_headers(port, app.session_token, content_type=True),
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        server_port=port,
    )


def test_demo_site_is_english_first_bilingual_and_token_gated(tmp_path: Path) -> None:
    app = DemoSiteApplication(tmp_path / "workspace")
    port = app.settings.port

    unauthorized = app.handle(
        method="GET",
        target="/",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    page = app.handle(
        method="GET",
        target=f"/?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )

    assert unauthorized.status_code == 401
    assert page.status_code == 200
    html = page.content.decode("utf-8")
    assert '<html lang="en">' in html
    assert "Synthetic demo data" in html
    assert "Assistantify your home" in html
    assert 'data-language="de"' in html
    assert 'data-theme-mode="dark"' in html
    assert 'data-i18n="beforeState"' in html
    assert 'data-i18n="afterState"' in html
    assert 'data-i18n="simulatedOnly"' in html
    assert "127.0.0.1" not in html
    assert app.session_token in html
    assert page.headers["Content-Security-Policy"].startswith("default-src 'self'")
    javascript = (
        Path(__file__).parents[1]
        / "src"
        / "folderhome"
        / "demo_site"
        / "static"
        / "app.js"
    ).read_text(encoding="utf-8")
    assert "innerHTML" not in javascript
    assert "item.view_url" in javascript
    assert "item.download_url" in javascript
    assert 'view.dataset.i18n = "openResult"' in javascript
    assert 'download.dataset.i18n = "downloadResult"' in javascript
    assert 'heading.dataset.i18n = "results"' in javascript


def test_demo_site_runs_chat_plan_confirm_download_and_reset(tmp_path: Path) -> None:
    app = DemoSiteApplication(tmp_path / "workspace")
    port = app.settings.port

    status = app.handle(
        method="GET",
        target="/demo/api/status",
        headers=_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    prepared = _post(
        app,
        "/demo/api/prepare",
        {
            "schema": "folderhome.synthetic-accident-demo-prepare-request.v1",
            "prompt": (
                "I had an accident with my Hyundai i10. Find my current car insurance, "
                "compare it with older policies, identify the right contact, prepare a "
                "claim letter, and save the next follow-up locally."
            ),
        },
        port=port,
    )
    plan = prepared.payload["plan"]
    confirmed = _post(
        app,
        "/demo/api/confirm",
        {
            "schema": "folderhome.synthetic-accident-demo-confirm-request.v1",
            "command": plan["confirmation_command"],
        },
        port=port,
    )
    generated = confirmed.payload["result"]["generated_results"][0]
    viewed = app.handle(
        method="GET",
        target=generated["view_url"],
        headers=_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    downloaded = app.handle(
        method="GET",
        target=generated["download_url"],
        headers=_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )
    reset = _post(
        app,
        "/demo/api/reset",
        {"schema": "folderhome.synthetic-accident-demo-reset-request.v1"},
        port=port,
    )

    assert status.status_code == 200
    assert status.payload["demo"]["mode"] == "synthetic_fixture"
    assert prepared.status_code == 200
    assert plan["status"] == "confirmation_required"
    assert confirmed.status_code == 200
    assert confirmed.payload["result"]["status"] == "executed"
    assert viewed.status_code == 200
    assert viewed.headers["Content-Disposition"].startswith("inline;")
    assert downloaded.status_code == 200
    assert downloaded.headers["Content-Disposition"].startswith("attachment;")
    assert b"SYN-I10-2026" in downloaded.content
    assert reset.status_code == 200
    assert reset.payload["reset"]["status"] == "reset"
    assert app.demo.status()["generated_results"] == []


def test_demo_site_rejects_cross_origin_and_fake_or_unknown_routes(tmp_path: Path) -> None:
    app = DemoSiteApplication(tmp_path / "workspace")
    port = app.settings.port
    body = json.dumps(
        {
            "schema": "folderhome.synthetic-accident-demo-reset-request.v1",
        }
    ).encode("utf-8")

    cross_origin = app.handle(
        method="POST",
        target="/demo/api/reset",
        headers={
            "Host": f"127.0.0.1:{port}",
            "Origin": "https://example.invalid",
            "Content-Type": "application/json",
            "X-FolderHome-Token": app.session_token,
        },
        body=body,
        server_port=port,
    )
    unknown = app.handle(
        method="GET",
        target="/demo/api/not-real",
        headers=_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )

    assert cross_origin.status_code == 403
    assert unknown.status_code == 404


def test_demo_site_hides_local_paths_from_filesystem_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = DemoSiteApplication(tmp_path / "workspace")
    port = app.settings.port

    def unavailable_status() -> dict[str, object]:
        raise OSError(r"private failure at C:\Users\Example\Documents")

    monkeypatch.setattr(app.demo, "status", unavailable_status)
    response = app.handle(
        method="GET",
        target="/demo/api/status",
        headers=_headers(port, app.session_token),
        body=b"",
        server_port=port,
    )

    assert response.status_code == 500
    assert response.payload == {
        "schema": "folderhome.demo-site-error.v1",
        "status": "blocked",
        "message": "The synthetic demo workspace is unavailable.",
        "side_effects": [],
    }
    assert b"C:\\Users" not in response.content
