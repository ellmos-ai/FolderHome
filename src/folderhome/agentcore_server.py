"""Minimal production entry point for AWS Bedrock AgentCore Runtime."""

from __future__ import annotations

import json
import os
import signal
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from folderhome.application.agentcore_runtime import AgentCoreRuntimeApplication


class _AgentCoreHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        address: tuple[str, int],
        application: AgentCoreRuntimeApplication,
    ) -> None:
        self.application = application
        self._request_slots = threading.BoundedSemaphore(
            application.max_concurrent_requests
        )
        self._active_lock = threading.Lock()
        self._active_requests = 0
        super().__init__(address, _AgentCoreRequestHandler)

    @property
    def active_request_count(self) -> int:
        with self._active_lock:
            return self._active_requests

    def get_request(self):
        request, client_address = super().get_request()
        try:
            request.settimeout(self.application.request_timeout_seconds)
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


class _AgentCoreRequestHandler(BaseHTTPRequestHandler):
    server: _AgentCoreHTTPServer
    server_version = "FolderHome-AgentCore"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch(b"")

    def do_POST(self) -> None:  # noqa: N802
        maximum = self.server.application.max_body_bytes
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = maximum + 1
        if length < 0:
            length = maximum + 1
        body = self.rfile.read(min(length, maximum + 1))
        if length > maximum and len(body) <= maximum:
            body += b"x"
        self._dispatch(body)

    def _dispatch(self, body: bytes) -> None:
        response = self.server.application.handle(
            method=self.command,
            path=self.path,
            headers={key: value for key, value in self.headers.items()},
            body=body,
        )
        self.send_response(response.status_code)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.content)))
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    in_container = os.environ.get("FOLDERHOME_AGENTCORE_CONTAINER") == "1"
    host = "0.0.0.0" if in_container else "127.0.0.1"
    port = int(os.environ.get("PORT", "8080"))
    default_root = Path(tempfile.gettempdir()) / "folderhome-agentcore"
    workspace = Path(os.environ.get("FOLDERHOME_AGENTCORE_WORKSPACE", str(default_root)))
    application = AgentCoreRuntimeApplication(workspace)
    server = _AgentCoreHTTPServer((host, port), application)
    stopping = threading.Event()

    def request_shutdown(_signum: int, _frame: object) -> None:
        stopping.set()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    server.timeout = 0.5
    print(
        json.dumps(
            {
                "event": "ready",
                "protocol": "HTTP",
                "host": host,
                "port": port,
                "runtime_id_present": bool(os.environ.get("RUNTIME_ID")),
                "aws_region_present": bool(os.environ.get("AWS_REGION")),
                "synthetic_data_only": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        while not stopping.is_set():
            server.handle_request()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
