"""Token-gated HTTP application for the synthetic FolderHome accident demo."""

from __future__ import annotations

import hmac
import json
import secrets
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from folderhome.application.accident_demo import (
    DEFAULT_ACCIDENT_PROMPT,
    SyntheticAccidentDemo,
    SyntheticAccidentDemoError,
)
from folderhome.contracts.local_app import LocalApiResponse, LocalAppSettings

_ASSET_ROOT = Path(__file__).resolve().parent / "static"
_PROFILE_DIR = Path(__file__).resolve().parents[1] / "demo_data" / "profiles"
_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'"
)


class DemoSiteApplication:
    """Serve only the packaged UI and a synthetic, fixture-only demo runtime."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        host: str = "127.0.0.1",
        port: int = 8767,
        session_token: str | None = None,
    ) -> None:
        self.demo = SyntheticAccidentDemo(workspace_root)
        self.settings = LocalAppSettings(
            host=host,
            port=port,
            profiles_dir=_PROFILE_DIR,
            state_dir=self.demo.runtime_root / "state",
            max_body_bytes=32_768,
            max_query_limit=10,
            max_concurrent_requests=4,
            request_timeout_seconds=30,
        )
        self.session_token = session_token or secrets.token_urlsafe(32)
        if len(self.session_token) < 32:
            raise ValueError("Demo session token is too short.")

    def handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        try:
            return self._handle(
                method=method.upper(),
                target=target,
                headers={key.casefold(): value for key, value in headers.items()},
                body=body,
                server_port=server_port,
            )
        except SyntheticAccidentDemoError as exc:
            return self._error(400, str(exc))
        except OSError:
            return self._error(500, "The synthetic demo workspace is unavailable.")
        except (UnicodeError, ValueError) as exc:
            return self._error(400, str(exc))

    def _handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        expected_host = f"{self.settings.host}:{server_port}"
        if not hmac.compare_digest(headers.get("host", ""), expected_host):
            return self._error(403, "Unexpected Host header.")
        parsed = urlsplit(target)
        supplied_token = headers.get("x-folderhome-token", "") or parse_qs(
            parsed.query
        ).get("token", [""])[0]
        if not hmac.compare_digest(supplied_token, self.session_token):
            return self._error(401, "The local demo token is missing or invalid.")
        if method == "POST":
            expected_origin = f"http://{expected_host}"
            if not hmac.compare_digest(headers.get("origin", ""), expected_origin):
                return self._error(403, "Unexpected Origin header.")
        if len(body) > self.settings.max_body_bytes:
            return self._error(413, "Request body exceeds the demo limit.")

        if method == "GET" and parsed.path == "/":
            html = (_ASSET_ROOT / "index.html").read_text(encoding="utf-8").replace(
                "__FOLDERHOME_TOKEN__",
                quote(self.session_token, safe=""),
            )
            return self._bytes(200, "text/html; charset=utf-8", html.encode("utf-8"))
        if method == "GET" and parsed.path in {
            "/demo/assets/app.css",
            "/demo/assets/app.js",
            "/demo/assets/favicon.svg",
        }:
            name = parsed.path.rsplit("/", 1)[-1]
            content_types = {
                "app.css": "text/css; charset=utf-8",
                "app.js": "text/javascript; charset=utf-8",
                "favicon.svg": "image/svg+xml; charset=utf-8",
            }
            return self._bytes(
                200,
                content_types[name],
                (_ASSET_ROOT / name).read_bytes(),
            )
        if method == "GET" and parsed.path == "/demo/api/status":
            return self._json(
                200,
                {
                    "schema": "folderhome.demo-site-status-response.v1",
                    "status": "ready",
                    "deployment": "local_fixture",
                    "synthetic_data_only": True,
                    "default_prompt": DEFAULT_ACCIDENT_PROMPT,
                    "demo": self.demo.status(),
                    "architecture": {
                        "agent": "Strands Agents SDK 1.53.0",
                        "model": "deterministic fixture adapter",
                        "tools": "real FolderHome local tools",
                        "confirmation": "exact /confirm command",
                        "cloud": "disabled",
                    },
                },
            )
        if method == "POST" and parsed.path == "/demo/api/prepare":
            payload = self._json_request(headers, body)
            self._exact_schema(
                payload,
                schema="folderhome.synthetic-accident-demo-prepare-request.v1",
                fields={"schema", "prompt"},
            )
            prompt = payload["prompt"]
            if not isinstance(prompt, str):
                raise ValueError("Demo prompt must be text.")
            return self._json(
                200,
                {
                    "schema": "folderhome.demo-site-prepare-response.v1",
                    "plan": self.demo.prepare(prompt),
                },
            )
        if method == "POST" and parsed.path == "/demo/api/confirm":
            payload = self._json_request(headers, body)
            self._exact_schema(
                payload,
                schema="folderhome.synthetic-accident-demo-confirm-request.v1",
                fields={"schema", "command"},
            )
            command = payload["command"]
            if not isinstance(command, str):
                raise ValueError("Confirmation command must be text.")
            return self._json(
                200,
                {
                    "schema": "folderhome.demo-site-confirm-response.v1",
                    "result": self.demo.confirm(command),
                },
            )
        if method == "POST" and parsed.path == "/demo/api/reset":
            payload = self._json_request(headers, body)
            self._exact_schema(
                payload,
                schema="folderhome.synthetic-accident-demo-reset-request.v1",
                fields={"schema"},
            )
            return self._json(
                200,
                {
                    "schema": "folderhome.demo-site-reset-response.v1",
                    "reset": self.demo.reset(),
                },
            )
        result_prefix = "/demo/results/"
        if method == "GET" and parsed.path.startswith(result_prefix):
            filename = unquote(parsed.path[len(result_prefix) :])
            path = self.demo.result_file(filename)
            content_type = (
                "application/json; charset=utf-8"
                if path.suffix == ".json"
                else "text/markdown; charset=utf-8"
                if path.suffix == ".md"
                else "text/plain; charset=utf-8"
            )
            disposition = (
                "attachment"
                if parse_qs(parsed.query).get("download", [""])[0] == "1"
                else "inline"
            )
            return self._bytes(
                200,
                content_type,
                path.read_bytes(),
                extra_headers={
                    "Content-Disposition": f'{disposition}; filename="{path.name}"'
                },
            )
        if parsed.path in {
            "/demo/api/status",
            "/demo/api/prepare",
            "/demo/api/confirm",
            "/demo/api/reset",
        }:
            return self._error(405, "Method is not allowed for this demo endpoint.")
        return self._error(404, "Unknown demo endpoint.")

    @staticmethod
    def _exact_schema(
        payload: dict[str, object],
        *,
        schema: str,
        fields: set[str],
    ) -> None:
        if payload.get("schema") != schema or set(payload) != fields:
            raise ValueError("Demo request has an unknown schema or fields.")

    def _json_request(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, object]:
        if headers.get("content-type", "").split(";", 1)[0].strip() != (
            "application/json"
        ):
            raise ValueError("Demo API requires application/json.")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Demo request is not valid UTF-8 JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Demo request must be a JSON object.")
        return payload

    def _json(self, status: int, payload: dict[str, object]) -> LocalApiResponse:
        content = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        ).encode("utf-8")
        return self._bytes(
            status,
            "application/json; charset=utf-8",
            content,
            payload=payload,
        )

    def _error(self, status: int, message: str) -> LocalApiResponse:
        return self._json(
            status,
            {
                "schema": "folderhome.demo-site-error.v1",
                "status": "blocked",
                "message": message,
                "side_effects": [],
            },
        )

    @staticmethod
    def _bytes(
        status: int,
        content_type: str,
        content: bytes,
        *,
        payload: dict[str, object] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> LocalApiResponse:
        headers = {
            "Cache-Control": "no-store",
            "Content-Security-Policy": _CSP,
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        headers.update(extra_headers or {})
        return LocalApiResponse(status, content_type, content, headers, payload)


__all__ = ["DemoSiteApplication"]
