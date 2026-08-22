"""Token-gated local API reusing existing read-only FolderHome services."""

from __future__ import annotations

import getpass
import hmac
import json
import os
import platform
import secrets
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs, quote, urlsplit

from folderhome.application.document_search import build_theme_dossier, search_documents
from folderhome.application.profile_rules import ProfileConfiguration
from folderhome.contracts.local_app import (
    LocalApiResponse,
    LocalAppSettings,
    OperatingSystemIdentity,
)


class LocalDocumentSearcher(Protocol):
    def search(self, query: str, *, limit: int = 20) -> tuple[object, ...]: ...


class LocalAppError(RuntimeError):
    """Raised when the local app boundary cannot be established safely."""


class LocalApplication:
    """Pure request dispatcher between local HTTP and existing app services."""

    def __init__(
        self,
        *,
        settings: LocalAppSettings,
        profiles: ProfileConfiguration,
        searcher: LocalDocumentSearcher,
        session_token: str | None = None,
    ) -> None:
        if profiles.os_account.strip() == "":
            raise LocalAppError("Profilkonfiguration besitzt kein OS-Konto-Label.")
        profile_ids = [item.profile_id for item in profiles.profiles]
        if not profile_ids or len(profile_ids) != len(set(profile_ids)):
            raise LocalAppError("Lokale App benötigt eindeutige organisatorische Profile.")
        token = session_token or secrets.token_urlsafe(32)
        if len(token) < 32:
            raise LocalAppError("Lokales Sitzungstoken ist zu kurz.")
        self.settings = settings
        self.profiles = profiles
        self.searcher = searcher
        self.session_token = token
        self._token_sha256 = sha256(token.encode("utf-8")).hexdigest()
        self._identity = capture_os_identity()
        self._profile_ids = frozenset(profile_ids)
        self._asset_root = Path(__file__).parents[1] / "web_ui"

    def plan(self) -> dict[str, object]:
        return {
            "schema": "folderhome.local-app-plan.v1",
            "settings": self.settings.to_dict(),
            "os_identity": self._identity.to_public_dict(),
            "profile_account_label": self.profiles.os_account,
            "profile_ids": sorted(self._profile_ids),
            "security_boundary": "operating_system_account",
            "profiles_are_authorization_boundaries": False,
            "session_token_generated": True,
            "session_token_disclosed_in_plan": False,
            "shell_execution_available": False,
            "request_paths_allowed": False,
            "cors_enabled": False,
            "external_resources": False,
            "server_started": False,
        }

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
        except _HttpError as exc:
            return self._error(exc.status_code, str(exc))
        except LocalAppError as exc:
            return self._error(400, str(exc))
        except ValueError as exc:
            return self._error(422, f"Lokaler Dienst konnte die Anfrage nicht ausführen: {exc}")
        except OSError:
            return self._error(503, "Lokale Datenquelle ist derzeit nicht verfügbar.")
        except RuntimeError:
            return self._error(503, "Lokaler Dokumentdienst ist derzeit nicht verfügbar.")

    def _handle(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes,
        server_port: int,
    ) -> LocalApiResponse:
        if capture_os_identity().identity_sha256 != self._identity.identity_sha256:
            return self._error(403, "Betriebssystemidentität des Prozesses hat sich geändert.")
        expected_host = f"{self.settings.host}:{server_port}"
        if headers.get("host") != expected_host:
            return self._error(403, "HTTP-Host stimmt nicht mit der Loopback-Bindung überein.")
        expected_origin = f"http://{expected_host}"
        origin = headers.get("origin")
        if origin is not None and origin != expected_origin:
            return self._error(403, "Browser-Origin liegt außerhalb der lokalen App.")
        parsed = urlsplit(target)
        is_api = parsed.path.startswith("/api/")
        supplied_token = headers.get("x-folderhome-token", "") if is_api else (
            parse_qs(parsed.query).get("token", [""])[0]
        )
        if not hmac.compare_digest(supplied_token, self.session_token):
            return self._error(401, "Lokales Sitzungstoken fehlt oder ist ungültig.")

        if method == "GET" and parsed.path == "/":
            return self._asset_response(
                "index.html",
                "text/html; charset=utf-8",
                replacements={"__FOLDERHOME_TOKEN__": quote(self.session_token, safe="")},
            )
        if method == "GET" and parsed.path == "/assets/app.css":
            return self._asset_response("app.css", "text/css; charset=utf-8")
        if method == "GET" and parsed.path == "/assets/app.js":
            return self._asset_response("app.js", "text/javascript; charset=utf-8")
        if method == "GET" and parsed.path == "/assets/favicon.svg":
            return self._asset_response("favicon.svg", "image/svg+xml; charset=utf-8")
        if parsed.path in {
            "/",
            "/assets/app.css",
            "/assets/app.js",
            "/assets/favicon.svg",
        }:
            return self._error(405, "Methode ist für diese lokale Ressource nicht erlaubt.")

        if method == "GET" and parsed.path == "/api/v1/status":
            return self._json_response(self._status_payload(server_port))
        if method == "GET" and parsed.path == "/api/v1/profiles":
            return self._json_response(self._profiles_payload())
        if method == "GET" and parsed.path == "/api/v1/capabilities":
            return self._json_response(self._capabilities_payload())
        if parsed.path in {
            "/api/v1/status",
            "/api/v1/profiles",
            "/api/v1/capabilities",
        }:
            return self._error(405, "API-Endpunkt ist ausschließlich read-only per GET verfügbar.")
        if method == "POST" and parsed.path == "/api/v1/documents/search":
            payload = self._json_request(headers, body)
            request = self._search_request(payload)
            result = search_documents(
                request["query"],
                searcher=self.searcher,
                limit=request["limit"],
            )
            return self._json_response(
                {
                    "schema": "folderhome.local-search-response.v1",
                    "profile_id": request["profile_id"],
                    "organizational_context_only": True,
                    "result": result.to_dict(),
                    "side_effects": [],
                }
            )
        if method == "POST" and parsed.path == "/api/v1/documents/dossier":
            payload = self._json_request(headers, body)
            request = self._dossier_request(payload)
            result = build_theme_dossier(
                request["topic"],
                searcher=self.searcher,
                limit=request["limit"],
            )
            return self._json_response(
                {
                    "schema": "folderhome.local-dossier-response.v1",
                    "profile_id": request["profile_id"],
                    "organizational_context_only": True,
                    "result": result.to_dict(),
                    "side_effects": [],
                }
            )
        if parsed.path in {
            "/api/v1/documents/search",
            "/api/v1/documents/dossier",
        }:
            return self._error(405, "Dokumentenpunkt benötigt eine POST-JSON-Anfrage.")
        return self._error(404, "Unbekannter lokaler Endpunkt.")

    def _status_payload(self, server_port: int) -> dict[str, object]:
        return {
            "schema": "folderhome.local-app-status.v1",
            "status": "ready",
            "base_url": f"http://{self.settings.host}:{server_port}",
            "network_scope": "loopback_only",
            "security_boundary": "operating_system_account",
            "profiles_are_authorization_boundaries": False,
            "profile_account_label": self.profiles.os_account,
            "process_identity": self._identity.to_public_dict(),
            "session_token_sha256": self._token_sha256,
            "session_token_disclosed": False,
            "read_only_api": True,
            "shell_execution_available": False,
            "request_paths_allowed": False,
            "cors_enabled": False,
        }

    def _profiles_payload(self) -> dict[str, object]:
        return {
            "schema": "folderhome.local-profile-list.v1",
            "security_boundary": "operating_system_account",
            "profiles": [
                {
                    "profile_id": item.profile_id,
                    "display_name": item.display_name,
                    "organizational_only": True,
                    "authorization_boundary": False,
                }
                for item in sorted(self.profiles.profiles, key=lambda value: value.profile_id)
            ],
        }

    @staticmethod
    def _capabilities_payload() -> dict[str, object]:
        interactive = {"documents.search", "documents.theme_dossier"}
        capabilities = (
            ("documents.search", "Dokumentensuche"),
            ("documents.theme_dossier", "Themendossier"),
            ("folders.organize", "Ordner organisieren"),
            ("documents.create", "Dokumente und Präsentationen erstellen"),
            ("communications.manage", "Briefe, Mail und Kontakte"),
            ("calendar.manage", "Termine und Kalenderhandoffs"),
            ("finance.overview", "Finanzen und Verträge überblicken"),
            ("health.organize", "Gesundheitsunterlagen organisieren"),
            ("legal.orient", "Bescheide und Rechtsänderungen orientieren"),
            ("household.manage", "Haushalt und Medikamente verwalten"),
        )
        return {
            "schema": "folderhome.local-capability-list.v1",
            "capabilities": [
                {
                    "capability_id": capability_id,
                    "title": title,
                    "surface_status": (
                        "interactive_read_only" if capability_id in interactive else "cli_only"
                    ),
                    "side_effects": [],
                }
                for capability_id, title in capabilities
            ],
        }

    def _json_request(self, headers: dict[str, str], body: bytes) -> dict[str, object]:
        if len(body) > self.settings.max_body_bytes:
            raise _HttpError(413, "JSON-Anfrage überschreitet die lokale Größenbegrenzung.")
        content_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
        if content_type != "application/json":
            raise _HttpError(415, "API akzeptiert ausschließlich application/json.")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise LocalAppError(f"JSON-Anfrage ist ungültig: {exc}") from exc
        if not isinstance(payload, dict):
            raise LocalAppError("JSON-Anfrage muss ein Objekt sein.")
        return payload

    def _search_request(self, payload: dict[str, object]) -> dict[str, object]:
        expected = {"schema", "profile_id", "query", "limit"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-search-request.v1"
        ):
            raise LocalAppError("Suchanfrage besitzt unbekannte oder fehlende Felder.")
        return self._validated_request(payload, text_key="query")

    def _dossier_request(self, payload: dict[str, object]) -> dict[str, object]:
        expected = {"schema", "profile_id", "topic", "limit"}
        if set(payload) != expected or payload.get("schema") != (
            "folderhome.local-dossier-request.v1"
        ):
            raise LocalAppError("Dossieranfrage besitzt unbekannte oder fehlende Felder.")
        return self._validated_request(payload, text_key="topic")

    def _validated_request(
        self,
        payload: dict[str, object],
        *,
        text_key: str,
    ) -> dict[str, object]:
        profile_id = payload.get("profile_id")
        text = payload.get(text_key)
        limit = payload.get("limit")
        if not isinstance(profile_id, str) or profile_id not in self._profile_ids:
            raise LocalAppError("Anfrage nennt kein bekanntes organisatorisches Profil.")
        if not isinstance(text, str) or not text.strip() or len(text) > 500:
            raise LocalAppError(f"{text_key} benötigt 1 bis 500 Zeichen.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not (
            1 <= limit <= self.settings.max_query_limit
        ):
            raise LocalAppError("Suchlimit liegt außerhalb der lokalen Grenze.")
        return {"profile_id": profile_id, text_key: text.strip(), "limit": limit}

    def _asset_response(
        self,
        filename: str,
        content_type: str,
        *,
        replacements: dict[str, str] | None = None,
    ) -> LocalApiResponse:
        path = self._asset_root / filename
        if not path.is_file():
            return self._error(500, "Lokales GUI-Asset fehlt.")
        content = path.read_text(encoding="utf-8")
        for old, new in (replacements or {}).items():
            content = content.replace(old, new)
        return LocalApiResponse(
            status_code=200,
            content_type=content_type,
            content=content.encode("utf-8"),
            headers=self._security_headers(),
        )

    def _json_response(
        self,
        payload: dict[str, object],
        status_code: int = 200,
    ) -> LocalApiResponse:
        content = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        ).encode("utf-8")
        return LocalApiResponse(
            status_code=status_code,
            content_type="application/json; charset=utf-8",
            content=content,
            headers=self._security_headers(),
            payload=payload,
        )

    def _error(self, status_code: int, message: str) -> LocalApiResponse:
        return self._json_response(
            {
                "schema": "folderhome.local-api-error.v1",
                "status": "blocked" if status_code in {401, 403} else "error",
                "status_code": status_code,
                "message": message,
            },
            status_code=status_code,
        )

    @staticmethod
    def _security_headers() -> dict[str, str]:
        return {
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            ),
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }


class _HttpError(LocalAppError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def capture_os_identity() -> OperatingSystemIdentity:
    account = getpass.getuser().strip()
    if os.name == "nt":
        domain = os.environ.get("USERDOMAIN", "").strip()
        if domain and "\\" not in account:
            account = f"{domain}\\{account}"
    home = Path.home().resolve()
    material = f"{platform.system()}\0{account.casefold()}\0{os.path.normcase(str(home))}"
    return OperatingSystemIdentity(
        account_name=account,
        platform=platform.system().casefold(),
        home_path=home,
        identity_sha256=sha256(material.encode("utf-8")).hexdigest(),
    )
