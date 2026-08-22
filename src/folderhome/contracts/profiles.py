"""Organizational user profiles and deterministic document policy rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,63}")


class RuleScope(StrEnum):
    """Rule inheritance levels from broadest to most specific."""

    GLOBAL = "global"
    AREA = "area"
    PROFILE = "profile"
    PROFILE_AREA = "profile_area"


class RuleKey(StrEnum):
    """Supported policy dimensions; unknown keys fail closed."""

    NAMING_TEMPLATE = "naming.template"
    ARCHIVE_AFTER_DAYS = "archive.after_days"
    ARCHIVE_FOLDER = "archive.folder"
    DELETE_AFTER_DAYS = "delete.after_days"
    DELETE_MODE = "delete.mode"
    FORMAT_REQUIRED = "format.required"
    CONVERSION_ORIGINAL = "conversion.original"
    SORT_TARGET = "sort.target"
    SCAN_INTERVAL_MINUTES = "scan.interval_minutes"
    CALENDAR_BACKEND = "calendar.backend"
    CALENDAR_TIMEZONE = "calendar.timezone"


RuleValue = str | int | bool


@dataclass(frozen=True, slots=True)
class ProfileRule:
    """One typed rule with an explicit inheritance scope."""

    rule_id: str
    key: RuleKey
    value: RuleValue
    scope: RuleScope
    profile_id: str | None = None
    area: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.rule_id, "rule_id")
        if self.profile_id is not None:
            _validate_id(self.profile_id, "profile_id")
        if self.area is not None:
            _validate_id(self.area, "area")
        requirements = {
            RuleScope.GLOBAL: (False, False),
            RuleScope.AREA: (False, True),
            RuleScope.PROFILE: (True, False),
            RuleScope.PROFILE_AREA: (True, True),
        }
        needs_profile, needs_area = requirements[self.scope]
        if bool(self.profile_id) is not needs_profile or bool(self.area) is not needs_area:
            raise ValueError(
                f"scope {self.scope.value} passt nicht zu profile_id/area"
            )
        _validate_rule_value(self.key, self.value)

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "key": self.key.value,
            "value": self.value,
            "scope": self.scope.value,
            "profile_id": self.profile_id,
            "area": self.area,
        }


@dataclass(frozen=True, slots=True)
class UserProfile:
    """Organizational preferences within one existing OS account."""

    profile_id: str
    display_name: str
    os_account: str
    organizational_only: bool
    rules: tuple[ProfileRule, ...]

    def __post_init__(self) -> None:
        _validate_id(self.profile_id, "profile_id")
        if not self.display_name.strip() or not self.os_account.strip():
            raise ValueError("display_name und os_account dürfen nicht leer sein")
        if self.organizational_only is not True:
            raise ValueError("Profile müssen organizational_only=true ausweisen")
        if any(rule.profile_id != self.profile_id for rule in self.rules):
            raise ValueError("Profilregeln müssen dieselbe profile_id verwenden")

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "os_account": self.os_account,
            "organizational_only": self.organizational_only,
            "rules": [rule.to_dict() for rule in self.rules],
        }


@dataclass(frozen=True, slots=True)
class ResolvedProfileRule:
    """Winning value plus the rules it superseded."""

    key: RuleKey
    value: RuleValue
    scope: RuleScope
    source_rule_ids: tuple[str, ...]
    overridden_rule_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key.value,
            "value": self.value,
            "scope": self.scope.value,
            "source_rule_ids": list(self.source_rule_ids),
            "overridden_rule_ids": list(self.overridden_rule_ids),
        }


@dataclass(frozen=True, slots=True)
class ResolvedProfilePolicy:
    """Effective organizational policy for one profile and area."""

    profile_id: str
    display_name: str
    area: str
    os_account: str
    organizational_only: bool
    security_boundary: str
    rules: tuple[ResolvedProfileRule, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "folderhome.resolved-profile-policy.v1",
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "area": self.area,
            "os_account": self.os_account,
            "organizational_only": self.organizational_only,
            "security_boundary": self.security_boundary,
            "rules": [rule.to_dict() for rule in self.rules],
        }


def _validate_id(value: str, field: str) -> None:
    if _ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} muss eine stabile Kleinbuchstaben-ID sein")


def _validate_rule_value(key: RuleKey, value: RuleValue) -> None:
    if key in {
        RuleKey.ARCHIVE_AFTER_DAYS,
        RuleKey.DELETE_AFTER_DAYS,
        RuleKey.SCAN_INTERVAL_MINUTES,
    }:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{key.value} benötigt eine nichtnegative Ganzzahl")
        if key is RuleKey.SCAN_INTERVAL_MINUTES and value < 1:
            raise ValueError("scan.interval_minutes muss mindestens 1 sein")
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key.value} benötigt einen nichtleeren Textwert")
    if key is RuleKey.DELETE_MODE and value not in {
        "disabled",
        "review_only",
        "recycle_bin",
    }:
        raise ValueError(
            "delete.mode erlaubt disabled, review_only oder recycle_bin; "
            f"hard_delete ist nicht zulässig: {value}"
        )
    if key is RuleKey.FORMAT_REQUIRED and value not in {
        "original",
        "pdf",
        "txt",
        "docx",
        "odt",
        "csv",
        "xlsx",
    }:
        raise ValueError(f"Nicht unterstütztes Zielformat: {value}")
    if key is RuleKey.CONVERSION_ORIGINAL and value not in {
        "keep",
        "archive",
        "recycle_bin",
        "gardener_storage",
    }:
        raise ValueError(f"Nicht unterstützte Originalregel: {value}")
    if key is RuleKey.NAMING_TEMPLATE and "{name}" not in value:
        raise ValueError("naming.template muss den Platzhalter {name} enthalten")
    if key is RuleKey.CALENDAR_BACKEND and value not in {
        "folderhome_local",
        "uptoday_ics",
        "routinika",
        "google",
    }:
        raise ValueError(f"Nicht unterstütztes Kalenderbackend: {value}")
    if key is RuleKey.CALENDAR_TIMEZONE:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unbekannte Kalenderzeitzone: {value}") from exc
