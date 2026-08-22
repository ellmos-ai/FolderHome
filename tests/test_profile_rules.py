from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.application.profile_rules import (
    ProfileConfigurationError,
    load_profile_configuration,
    resolve_profile_policy,
)
from folderhome.contracts import ProfileRule, RuleKey, RuleScope


def _write_profiles(root: Path, *, conflict: bool = False) -> None:
    root.mkdir()
    household_rules = [
        {
            "rule_id": "rule_global_naming",
            "key": "naming.template",
            "value": "{date}_{name}",
            "scope": "global",
        },
        {
            "rule_id": "rule_insurance_archive",
            "key": "archive.after_days",
            "value": 3650,
            "scope": "area",
            "area": "versicherungen",
        },
        {
            "rule_id": "rule_global_delete",
            "key": "delete.mode",
            "value": "review_only",
            "scope": "global",
        },
    ]
    (root / "household.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.household-rules.v1",
                "os_account": "synthetic-family-account",
                "rules": household_rules,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rules = [
        {
            "rule_id": "rule_lukas_naming",
            "key": "naming.template",
            "value": "Lukas_{date}_{name}",
            "scope": "profile",
        },
        {
            "rule_id": "rule_lukas_insurance_archive",
            "key": "archive.after_days",
            "value": 1825,
            "scope": "profile_area",
            "area": "versicherungen",
        },
        {
            "rule_id": "rule_lukas_pdf",
            "key": "format.required",
            "value": "pdf",
            "scope": "profile_area",
            "area": "versicherungen",
        },
    ]
    if conflict:
        rules.append(
            {
                "rule_id": "rule_lukas_insurance_archive_conflict",
                "key": "archive.after_days",
                "value": 730,
                "scope": "profile_area",
                "area": "versicherungen",
            }
        )
    (root / "Lukas.json").write_text(
        json.dumps(
            {
                "schema": "folderhome.user-profile.v1",
                "profile_id": "lukas",
                "display_name": "Lukas Beispiel",
                "os_account": "synthetic-family-account",
                "organizational_only": True,
                "rules": rules,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_rule_contract_rejects_hard_delete() -> None:
    with pytest.raises(ValueError, match="hard_delete"):
        ProfileRule(
            rule_id="rule_unsafe_delete",
            key=RuleKey.DELETE_MODE,
            value="hard_delete",
            scope=RuleScope.GLOBAL,
        )


def test_profile_resolution_uses_global_area_profile_profile_area_precedence(
    tmp_path: Path,
) -> None:
    profile_dir = tmp_path / "profiles"
    _write_profiles(profile_dir)

    configuration = load_profile_configuration(profile_dir)
    resolved = resolve_profile_policy(
        configuration,
        profile_id="lukas",
        area="versicherungen",
    )

    by_key = {rule.key: rule for rule in resolved.rules}
    assert by_key[RuleKey.NAMING_TEMPLATE].value == "Lukas_{date}_{name}"
    assert by_key[RuleKey.NAMING_TEMPLATE].scope is RuleScope.PROFILE
    assert by_key[RuleKey.ARCHIVE_AFTER_DAYS].value == 1825
    assert by_key[RuleKey.ARCHIVE_AFTER_DAYS].scope is RuleScope.PROFILE_AREA
    assert by_key[RuleKey.FORMAT_REQUIRED].value == "pdf"
    assert by_key[RuleKey.DELETE_MODE].value == "review_only"
    assert resolved.organizational_only is True
    assert "keine Zugriffsgrenze" in resolved.security_boundary


def test_equal_precedence_conflict_fails_closed(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    _write_profiles(profile_dir, conflict=True)
    configuration = load_profile_configuration(profile_dir)

    with pytest.raises(ProfileConfigurationError, match="archive.after_days.*Konflikt"):
        resolve_profile_policy(
            configuration,
            profile_id="lukas",
            area="versicherungen",
        )


def test_profile_os_account_must_match_household_boundary(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    _write_profiles(profile_dir)
    path = profile_dir / "Lukas.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["os_account"] = "another-account"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProfileConfigurationError, match="OS-Konto"):
        load_profile_configuration(profile_dir)
