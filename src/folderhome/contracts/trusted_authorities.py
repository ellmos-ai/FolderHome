"""Publisher-bound exact HTTPS authorities for trusted user handoffs."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_AUTHORITY_ID = re.compile(r"[a-z][a-z0-9_-]{1,63}")
_HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?")


@dataclass(frozen=True, slots=True)
class TrustedWebAuthority:
    """One reviewed publisher and its exact official HTTPS hostnames."""

    authority_id: str
    publisher: str
    hosts: frozenset[str]

    SCHEMA = "folderhome.trusted-web-authority.v1"

    def __post_init__(self) -> None:
        if _AUTHORITY_ID.fullmatch(self.authority_id) is None:
            raise ValueError("Vertrauensstelle besitzt eine ungültige ID.")
        if not self.publisher.strip() or not self.hosts:
            raise ValueError("Vertrauensstelle benötigt Publisher und Hosts.")
        normalized = frozenset(host.casefold() for host in self.hosts)
        if any(_HOST.fullmatch(host) is None or host.endswith(".") for host in normalized):
            raise ValueError("Vertrauensstelle enthält einen ungültigen Host.")
        object.__setattr__(self, "hosts", normalized)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "authority_id": self.authority_id,
            "publisher": self.publisher,
            "hosts": sorted(self.hosts),
        }


OFFICIAL_BENEFIT_AUTHORITIES = (
    TrustedWebAuthority(
        authority_id="sozialplattform",
        publisher="Sozialplattform",
        hosts=frozenset({"sozialplattform.de"}),
    ),
    TrustedWebAuthority(
        authority_id="bundesagentur-arbeit",
        publisher="Bundesagentur für Arbeit",
        hosts=frozenset({"www.arbeitsagentur.de", "web.arbeitsagentur.de"}),
    ),
    TrustedWebAuthority(
        authority_id="bmwsb",
        publisher="Bundesministerium für Wohnen, Stadtentwicklung und Bauwesen",
        hosts=frozenset({"www.bmwsb.bund.de"}),
    ),
)


def require_trusted_official_url(
    value: str,
    *,
    publisher: str,
    authorities: tuple[TrustedWebAuthority, ...] = OFFICIAL_BENEFIT_AUTHORITIES,
) -> None:
    """Require canonical HTTPS syntax and an exact host bound to the publisher."""

    message = (
        "Amtliche Quellen und Handoffs benötigen eine sichere HTTPS-URL mit "
        "registriertem amtlichen Host für den angegebenen Publisher."
    )
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError(message) from exc
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or hostname is None
        or port is not None
    ):
        raise ValueError(message)
    host = hostname.casefold()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError(message)
    if not any(
        authority.publisher == publisher and host in authority.hosts
        for authority in authorities
    ):
        raise ValueError(message)
