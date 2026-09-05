"""Load and resolve organizational FolderHome profile rules."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from folderhome.contracts import (
    ProfileRule,
    ResolvedProfilePolicy,
    ResolvedProfileRule,
    RuleKey,
    RuleScope,
    UserProfile,
)

_PRECEDENCE = {
    RuleScope.GLOBAL: 0,
    RuleScope.AREA: 1,
    RuleScope.PROFILE: 2,
    RuleScope.PROFILE_AREA: 3,
}


class ProfileConfigurationError(ValueError):
    """Raised when profile files or rule inheritance are ambiguous."""


@dataclass(frozen=True, slots=True)
class ProfileConfiguration:
    """One OS-account configuration with organizational subprofiles."""

    os_account: str
    common_rules: tuple[ProfileRule, ...]
    profiles: tuple[UserProfile, ...]


def load_profile_configuration(directory: Path) -> ProfileConfiguration:
    """Read one household rule file and all individual JSON profiles from disk."""

    directory = directory.resolve()
    household_path = directory / "household.json"
    if not household_path.is_file():
        raise ProfileConfigurationError(f"household.json fehlt: {household_path}")
    profiles = {
        path.name: _read_json(path)
        for path in sorted(directory.glob("*.json"), key=lambda item: item.name.casefold())
        if path.name.casefold() != "household.json"
    }
    return parse_profile_configuration(_read_json(household_path), profiles)


def parse_profile_configuration(
    household: object,
    profile_documents: Mapping[str, object],
) -> ProfileConfiguration:
    """Apply the same checks to documents that are not on disk yet.

    The installer validates a planned profile set before it writes anything, so the
    contract has to run on documents, not only on files.
    """

    household = _as_object(household, "household.json")
    if household.get("schema") != "folderhome.household-rules.v1":
        raise ProfileConfigurationError("household.json verwendet ein unbekanntes Schema.")
    os_account = household.get("os_account")
    if not isinstance(os_account, str) or not os_account.strip():
        raise ProfileConfigurationError("household.json enthält kein gültiges OS-Konto.")
    common_rules = tuple(
        _parse_rule(item, profile_id=None, origin="household.json")
        for item in _rule_items(household, "household.json")
    )
    if any(rule.scope not in {RuleScope.GLOBAL, RuleScope.AREA} for rule in common_rules):
        raise ProfileConfigurationError(
            "household.json darf nur globale oder bereichsspezifische Regeln enthalten."
        )

    profiles = []
    for name in sorted(profile_documents, key=str.casefold):
        payload = _as_object(profile_documents[name], name)
        if payload.get("schema") != "folderhome.user-profile.v1":
            raise ProfileConfigurationError(f"Unbekanntes Profilschema in {name}.")
        profile_id = payload.get("profile_id")
        if not isinstance(profile_id, str):
            raise ProfileConfigurationError(f"profile_id fehlt in {name}.")
        rules = tuple(
            _parse_rule(item, profile_id=profile_id, origin=name)
            for item in _rule_items(payload, name)
        )
        if any(
            rule.scope not in {RuleScope.PROFILE, RuleScope.PROFILE_AREA}
            for rule in rules
        ):
            raise ProfileConfigurationError(
                f"{name} darf nur Profil- oder Profilbereichsregeln enthalten."
            )
        try:
            profile = UserProfile(
                profile_id=profile_id,
                display_name=str(payload.get("display_name", "")),
                os_account=str(payload.get("os_account", "")),
                organizational_only=payload.get("organizational_only") is True,
                rules=rules,
            )
        except ValueError as exc:
            raise ProfileConfigurationError(f"Ungültiges Profil {name}: {exc}") from exc
        if profile.os_account != os_account:
            raise ProfileConfigurationError(
                f"Profil {profile.profile_id} gehört nicht zum gemeinsamen OS-Konto."
            )
        profiles.append(profile)

    profile_ids = [profile.profile_id for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ProfileConfigurationError("Profil-IDs sind nicht eindeutig.")
    all_rule_ids = [
        rule.rule_id
        for rule in (*common_rules, *(rule for profile in profiles for rule in profile.rules))
    ]
    if len(all_rule_ids) != len(set(all_rule_ids)):
        raise ProfileConfigurationError("Regel-IDs sind nicht eindeutig.")
    return ProfileConfiguration(
        os_account=os_account,
        common_rules=common_rules,
        profiles=tuple(profiles),
    )


def resolve_profile_policy(
    configuration: ProfileConfiguration,
    *,
    profile_id: str,
    area: str,
) -> ResolvedProfilePolicy:
    """Resolve fixed precedence and fail closed on same-level conflicts."""

    profile = next(
        (item for item in configuration.profiles if item.profile_id == profile_id),
        None,
    )
    if profile is None:
        raise ProfileConfigurationError(f"Unbekanntes Profil: {profile_id}")
    applicable = [
        rule
        for rule in (*configuration.common_rules, *profile.rules)
        if rule.scope is RuleScope.GLOBAL
        or (rule.scope is RuleScope.AREA and rule.area == area)
        or (rule.scope is RuleScope.PROFILE and rule.profile_id == profile_id)
        or (
            rule.scope is RuleScope.PROFILE_AREA
            and rule.profile_id == profile_id
            and rule.area == area
        )
    ]
    grouped: dict[RuleKey, list[ProfileRule]] = {}
    for rule in applicable:
        grouped.setdefault(rule.key, []).append(rule)

    resolved = []
    for key in sorted(grouped, key=lambda item: item.value):
        candidates = grouped[key]
        best_precedence = max(_PRECEDENCE[item.scope] for item in candidates)
        winners = [
            item for item in candidates if _PRECEDENCE[item.scope] == best_precedence
        ]
        distinct_values = {item.value for item in winners}
        if len(distinct_values) != 1:
            raise ProfileConfigurationError(
                f"{key.value}: Konflikt zwischen gleichrangigen Regeln "
                f"{', '.join(sorted(item.rule_id for item in winners))}."
            )
        winner = min(winners, key=lambda item: item.rule_id)
        winner_ids = tuple(sorted(item.rule_id for item in winners))
        overridden_ids = tuple(
            sorted(item.rule_id for item in candidates if item.rule_id not in winner_ids)
        )
        resolved.append(
            ResolvedProfileRule(
                key=key,
                value=winner.value,
                scope=winner.scope,
                source_rule_ids=winner_ids,
                overridden_rule_ids=overridden_ids,
            )
        )
    return ResolvedProfilePolicy(
        profile_id=profile.profile_id,
        display_name=profile.display_name,
        area=area,
        os_account=configuration.os_account,
        organizational_only=True,
        security_boundary=(
            "Dieses Profil organisiert Dokumentregeln innerhalb eines OS-Kontos; "
            "es ist keine Zugriffsgrenze."
        ),
        rules=tuple(resolved),
    )


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileConfigurationError(f"{path.name} ist nicht lesbar: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProfileConfigurationError(f"{path.name} muss ein JSON-Objekt enthalten.")
    return payload


def _as_object(payload: object, name: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ProfileConfigurationError(f"{name} muss ein JSON-Objekt enthalten.")
    return payload


def _rule_items(payload: dict[str, object], name: str) -> list[object]:
    items = payload.get("rules")
    if not isinstance(items, list):
        raise ProfileConfigurationError(f"{name} enthält keine Regelliste.")
    return items


def _parse_rule(
    payload: object,
    *,
    profile_id: str | None,
    origin: str,
) -> ProfileRule:
    if not isinstance(payload, dict):
        raise ProfileConfigurationError(f"Ungültiger Regeleintrag in {origin}.")
    try:
        scope = RuleScope(str(payload["scope"]))
        return ProfileRule(
            rule_id=str(payload["rule_id"]),
            key=RuleKey(str(payload["key"])),
            value=payload["value"],
            scope=scope,
            profile_id=(
                profile_id
                if scope in {RuleScope.PROFILE, RuleScope.PROFILE_AREA}
                else None
            ),
            area=(str(payload["area"]) if payload.get("area") is not None else None),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProfileConfigurationError(
            f"Ungültige Regel in {origin}: {exc}"
        ) from exc
