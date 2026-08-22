from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.contracts import LocalApiResponse, LocalAppSettings, OperatingSystemIdentity
from folderhome.local_server import LocalServerError, create_local_server

PROFILE_DIR = Path(__file__).parents[1] / "examples" / "profiles"


class StubSearcher:
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        return (
            KnowledgeDigestSearchHit(
                source="document",
                filename="Krankenversicherung.txt",
                file_type="txt",
                snippet=f"Fundstelle für >>>{query}<<<",
                relevance=-1.0,
                word_count=42,
            ),
        )[:limit]


class FailingSearcher:
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        raise RuntimeError("C:/private/index.sqlite ist nicht lesbar")


def _settings(tmp_path: Path, *, host: str = "127.0.0.1") -> LocalAppSettings:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return LocalAppSettings(
        host=host,
        port=0,
        profiles_dir=PROFILE_DIR,
        state_dir=state_dir,
        max_body_bytes=4096,
        max_query_limit=25,
        max_concurrent_requests=4,
        request_timeout_seconds=1.0,
    )


def _app(tmp_path: Path) -> LocalApplication:
    return LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="phase35-test-token-with-sufficient-entropy-123456",
    )


def _api_headers(port: int, token: str) -> dict[str, str]:
    return {
        "Host": f"127.0.0.1:{port}",
        "Origin": f"http://127.0.0.1:{port}",
        "Content-Type": "application/json",
        "X-FolderHome-Token": token,
    }


def test_settings_reject_non_loopback_and_overlapping_profile_state(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="127.0.0.1"):
        _settings(tmp_path, host="0.0.0.0")
    with pytest.raises(ValueError, match="überlappen"):
        LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=PROFILE_DIR / "state",
        )
    with pytest.raises(ValueError, match="max_concurrent_requests"):
        LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=tmp_path / "state-limit",
            max_concurrent_requests=0,
        )
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=PROFILE_DIR,
            state_dir=tmp_path / "state-timeout",
            request_timeout_seconds=0,
        )


def test_api_requires_token_exact_host_and_same_origin(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765

    missing = app.handle(
        method="GET",
        target="/api/v1/status",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    wrong_host = app.handle(
        method="GET",
        target="/api/v1/status",
        headers={
            "Host": f"localhost:{port}",
            "X-FolderHome-Token": app.session_token,
        },
        body=b"",
        server_port=port,
    )
    wrong_origin = app.handle(
        method="GET",
        target="/api/v1/status",
        headers={
            "Host": f"127.0.0.1:{port}",
            "Origin": "https://example.invalid",
            "X-FolderHome-Token": app.session_token,
        },
        body=b"",
        server_port=port,
    )

    assert missing.status_code == 401
    assert wrong_host.status_code == 403
    assert wrong_origin.status_code == 403


def test_status_and_profiles_expose_organizational_boundary(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)

    status = app.handle(
        method="GET",
        target="/api/v1/status",
        headers=headers,
        body=b"",
        server_port=port,
    )
    profiles = app.handle(
        method="GET",
        target="/api/v1/profiles",
        headers=headers,
        body=b"",
        server_port=port,
    )

    assert status.status_code == 200
    assert status.payload["security_boundary"] == "operating_system_account"
    assert status.payload["profiles_are_authorization_boundaries"] is False
    assert status.payload["network_scope"] == "loopback_only"
    assert "session_token" not in status.payload
    assert {item["profile_id"] for item in profiles.payload["profiles"]} == {
        "hanna",
        "lukas",
        "simon",
    }
    assert all(item["organizational_only"] for item in profiles.payload["profiles"])


def test_search_and_dossier_reuse_existing_services_without_paths(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)
    search_body = json.dumps(
        {
            "schema": "folderhome.local-search-request.v1",
            "profile_id": "lukas",
            "query": "Ich suche nach einem Dokument über meine Krankenversicherung.",
            "limit": 10,
        }
    ).encode("utf-8")
    dossier_body = json.dumps(
        {
            "schema": "folderhome.local-dossier-request.v1",
            "profile_id": "hanna",
            "topic": "Krankenversicherung",
            "limit": 10,
        }
    ).encode("utf-8")

    search = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=search_body,
        server_port=port,
    )
    dossier = app.handle(
        method="POST",
        target="/api/v1/documents/dossier",
        headers=headers,
        body=dossier_body,
        server_port=port,
    )

    assert search.status_code == 200
    assert search.payload["result"]["total_hits"] == 1
    assert search.payload["profile_id"] == "lukas"
    assert "source_path" not in json.dumps(search.payload)
    assert dossier.status_code == 200
    assert "Themendossier: Krankenversicherung" in dossier.payload["result"]["markdown"]
    assert dossier.payload["profile_id"] == "hanna"


def test_request_schema_size_profile_and_content_type_fail_closed(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    headers = _api_headers(port, app.session_token)
    unknown_field = json.dumps(
        {
            "schema": "folderhome.local-search-request.v1",
            "profile_id": "lukas",
            "query": "Versicherung",
            "limit": 10,
            "path": "C:/private",
        }
    ).encode("utf-8")
    unknown_profile = json.dumps(
        {
            "schema": "folderhome.local-search-request.v1",
            "profile_id": "admin",
            "query": "Versicherung",
            "limit": 10,
        }
    ).encode("utf-8")

    injected = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=unknown_field,
        server_port=port,
    )
    profile = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=unknown_profile,
        server_port=port,
    )
    too_large = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=headers,
        body=b"x" * 4097,
        server_port=port,
    )
    wrong_type_headers = dict(headers)
    wrong_type_headers["Content-Type"] = "text/plain"
    wrong_type = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=wrong_type_headers,
        body=b"{}",
        server_port=port,
    )

    assert injected.status_code == 400
    assert profile.status_code == 400
    assert too_large.status_code == 413
    assert wrong_type.status_code == 415
    assert all(
        response.payload["schema"] == "folderhome.local-api-error.v1"
        for response in (injected, profile, too_large, wrong_type)
    )


def test_provider_failure_is_sanitized_and_contracts_are_public(tmp_path: Path) -> None:
    app = LocalApplication(
        settings=_settings(tmp_path),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=FailingSearcher(),
        session_token="phase35-provider-failure-token-with-sufficient-entropy",
    )
    port = 8765
    response = app.handle(
        method="POST",
        target="/api/v1/documents/search",
        headers=_api_headers(port, app.session_token),
        body=json.dumps(
            {
                "schema": "folderhome.local-search-request.v1",
                "profile_id": "lukas",
                "query": "Krankenversicherung",
                "limit": 10,
            }
        ).encode("utf-8"),
        server_port=port,
    )

    assert response.status_code == 503
    assert "C:/private" not in response.payload["message"]
    assert LocalApiResponse.__module__ == "folderhome.contracts.local_app"
    assert LocalAppSettings.__module__ == "folderhome.contracts.local_app"
    assert OperatingSystemIdentity.__module__ == "folderhome.contracts.local_app"


def test_gui_is_local_token_gated_and_contains_no_remote_assets(tmp_path: Path) -> None:
    app = _app(tmp_path)
    port = 8765
    root = app.handle(
        method="GET",
        target=f"/?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    blocked_asset = app.handle(
        method="GET",
        target="/assets/app.css",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )
    favicon = app.handle(
        method="GET",
        target=f"/assets/favicon.svg?token={app.session_token}",
        headers={"Host": f"127.0.0.1:{port}"},
        body=b"",
        server_port=port,
    )

    assert root.status_code == 200
    html = root.content.decode("utf-8")
    assert "FolderHome" in html
    assert "Betriebssystemkonto" in html
    assert "https://" not in html
    assert "http://" not in html
    assert blocked_asset.status_code == 401
    assert favicon.status_code == 200
    assert favicon.content_type.startswith("image/svg+xml")
    assert root.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert root.headers["Referrer-Policy"] == "no-referrer"


def test_real_loopback_server_requires_gate_and_serves_authenticated_api(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    with pytest.raises(LocalServerError, match="Serverfreigabe"):
        create_local_server(app, allow_loopback_server=False)

    server = create_local_server(app, allow_loopback_server=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(server.access_url, timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Server"].strip() == "FolderHome"
            assert "Dokumentensuche" in html

        request = urllib.request.Request(
            f"{server.base_url}/api/v1/status",
            headers={
                "X-FolderHome-Token": app.session_token,
                "Origin": server.base_url,
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["network_scope"] == "loopback_only"

        with pytest.raises(urllib.error.HTTPError) as unauthorized:
            urllib.request.urlopen(f"{server.base_url}/api/v1/status", timeout=5)
        assert unauthorized.value.code == 401
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_loopback_server_bounds_slow_connections_before_token_dispatch(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    app = LocalApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=0,
            profiles_dir=PROFILE_DIR,
            state_dir=state_dir,
            max_body_bytes=4096,
            max_query_limit=25,
            max_concurrent_requests=1,
            request_timeout_seconds=0.2,
        ),
        profiles=load_profile_configuration(PROFILE_DIR),
        searcher=StubSearcher(),
        session_token="phase36-bounded-loopback-token-with-sufficient-entropy",
    )
    server = create_local_server(app, allow_loopback_server=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    first = socket.create_connection(server.address, timeout=2)
    second = None
    try:
        first.sendall(b"G")
        deadline = time.monotonic() + 2
        while server.active_request_count != 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.active_request_count == 1

        second = socket.create_connection(server.address, timeout=2)
        second.settimeout(1)
        second.sendall(b"GET / HTTP/1.1\r\n")
        assert second.recv(1) == b""

        deadline = time.monotonic() + 2
        while server.active_request_count and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.active_request_count == 0

        with urllib.request.urlopen(server.access_url, timeout=2) as response:
            assert response.status == 200
    finally:
        first.close()
        if second is not None:
            second.close()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
