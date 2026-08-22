"""Contracts for the token-gated local FolderHome application surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LocalAppSettings:
    host: str
    port: int
    profiles_dir: Path
    state_dir: Path
    max_body_bytes: int = 65_536
    max_query_limit: int = 50
    max_concurrent_requests: int = 32
    request_timeout_seconds: float = 5.0

    SCHEMA = "folderhome.local-app-settings.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "profiles_dir", self.profiles_dir.resolve())
        object.__setattr__(self, "state_dir", self.state_dir.resolve())
        if self.host != "127.0.0.1":
            raise ValueError("Lokale App darf ausschließlich an 127.0.0.1 binden.")
        if isinstance(self.port, bool) or not 0 <= self.port <= 65_535:
            raise ValueError("App-Port muss zwischen 0 und 65535 liegen.")
        if isinstance(self.max_body_bytes, bool) or not 1024 <= self.max_body_bytes <= 1_048_576:
            raise ValueError("max_body_bytes muss zwischen 1024 und 1048576 liegen.")
        if isinstance(self.max_query_limit, bool) or not 1 <= self.max_query_limit <= 100:
            raise ValueError("max_query_limit muss zwischen 1 und 100 liegen.")
        if (
            isinstance(self.max_concurrent_requests, bool)
            or not isinstance(self.max_concurrent_requests, int)
            or not 1 <= self.max_concurrent_requests <= 256
        ):
            raise ValueError("max_concurrent_requests muss zwischen 1 und 256 liegen.")
        if (
            isinstance(self.request_timeout_seconds, bool)
            or not isinstance(self.request_timeout_seconds, (int, float))
            or not 0.1 <= float(self.request_timeout_seconds) <= 60.0
        ):
            raise ValueError(
                "request_timeout_seconds muss zwischen 0.1 und 60.0 liegen."
            )
        profiles = self.profiles_dir
        state = self.state_dir
        if profiles == state or profiles.is_relative_to(state) or state.is_relative_to(profiles):
            raise ValueError("Profil- und App-State-Verzeichnis dürfen sich nicht überlappen.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "host": self.host,
            "port": self.port,
            "profiles_dir": str(self.profiles_dir),
            "state_dir": str(self.state_dir),
            "max_body_bytes": self.max_body_bytes,
            "max_query_limit": self.max_query_limit,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout_seconds": float(self.request_timeout_seconds),
            "network_scope": "loopback_only",
        }


@dataclass(frozen=True, slots=True)
class OperatingSystemIdentity:
    account_name: str
    platform: str
    home_path: Path
    identity_sha256: str

    SCHEMA = "folderhome.operating-system-identity.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "home_path", self.home_path.resolve())
        if not self.account_name.strip() or len(self.identity_sha256) != 64:
            raise ValueError("Betriebssystemidentität ist unvollständig.")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "account_name": self.account_name,
            "platform": self.platform,
            "identity_fingerprint": self.identity_sha256[:16],
            "home_path_disclosed": False,
        }


@dataclass(frozen=True, slots=True)
class LocalApiResponse:
    status_code: int
    content_type: str
    content: bytes
    headers: dict[str, str]
    payload: dict[str, object] | None = None
