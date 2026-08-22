"""Loopback-only HTTP adapter for the FolderHome local application."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

from folderhome.application.local_app import LocalApplication


class LocalServerError(RuntimeError):
    """Raised before an unsafe or unapproved local listener is created."""


class _FolderHomeHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, server_address: tuple[str, int], application: LocalApplication) -> None:
        self.application = application
        self._request_slots = threading.BoundedSemaphore(
            application.settings.max_concurrent_requests
        )
        self._active_lock = threading.Lock()
        self._active_requests = 0
        super().__init__(server_address, _FolderHomeRequestHandler)

    @property
    def active_request_count(self) -> int:
        with self._active_lock:
            return self._active_requests

    def get_request(self):
        request, client_address = super().get_request()
        try:
            request.settimeout(float(self.application.settings.request_timeout_seconds))
        except BaseException:
            request.close()
            raise
        return request, client_address

    def process_request(self, request, client_address) -> None:
        if not self._request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        with self._active_lock:
            self._active_requests += 1
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._release_request_slot()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._release_request_slot()

    def _release_request_slot(self) -> None:
        with self._active_lock:
            self._active_requests -= 1
        self._request_slots.release()


class _FolderHomeRequestHandler(BaseHTTPRequestHandler):
    server: _FolderHomeHTTPServer
    server_version = "FolderHome"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch(b"")

    def do_POST(self) -> None:  # noqa: N802
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            length = self.server.application.settings.max_body_bytes + 1
        if length < 0:
            length = self.server.application.settings.max_body_bytes + 1
        maximum = self.server.application.settings.max_body_bytes
        body = self.rfile.read(min(length, maximum + 1))
        if length > maximum and len(body) <= maximum:
            body += b"x"
        self._dispatch(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._dispatch(b"")

    def _dispatch(self, body: bytes) -> None:
        response = self.server.application.handle(
            method=self.command,
            target=self.path,
            headers={key: value for key, value in self.headers.items()},
            body=body,
            server_port=int(self.server.server_address[1]),
        )
        self.send_response(response.status_code)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.content)))
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response.content)

    def log_message(self, format: str, *args: object) -> None:
        return


@dataclass(slots=True)
class LocalServer:
    _server: _FolderHomeHTTPServer

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def access_url(self) -> str:
        token = quote(self._server.application.session_token, safe="")
        return f"{self.base_url}/?token={token}"

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    @property
    def active_request_count(self) -> int:
        return self._server.active_request_count

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.local-server-start.v1",
            "status": "ready",
            "base_url": self.base_url,
            "access_url": self.access_url,
            "network_scope": "loopback_only",
            "security_boundary": "operating_system_account",
            "profiles_are_authorization_boundaries": False,
            "browser_opened": False,
            "external_network_used": False,
            "max_concurrent_requests": (
                self._server.application.settings.max_concurrent_requests
            ),
            "request_timeout_seconds": float(
                self._server.application.settings.request_timeout_seconds
            ),
        }

    def serve_forever(self) -> None:
        self._server.serve_forever(poll_interval=0.1)

    def shutdown(self) -> None:
        self._server.shutdown()

    def server_close(self) -> None:
        self._server.server_close()


def create_local_server(
    application: LocalApplication,
    *,
    allow_loopback_server: bool,
) -> LocalServer:
    if not allow_loopback_server:
        raise LocalServerError("Explizite lokale Serverfreigabe fehlt.")
    if application.settings.host != "127.0.0.1":
        raise LocalServerError("Serverbindung ist nicht auf 127.0.0.1 begrenzt.")
    if not application.settings.profiles_dir.is_dir():
        raise LocalServerError(
            f"Profilverzeichnis fehlt: {application.settings.profiles_dir}"
        )
    if not application.settings.state_dir.is_dir():
        raise LocalServerError(f"App-State-Verzeichnis fehlt: {application.settings.state_dir}")
    try:
        server = _FolderHomeHTTPServer(
            (application.settings.host, application.settings.port),
            application,
        )
    except OSError as exc:
        raise LocalServerError(f"Lokaler Server konnte nicht gebunden werden: {exc}") from exc
    return LocalServer(server)
