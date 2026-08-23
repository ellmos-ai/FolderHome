from __future__ import annotations

import json
from pathlib import Path

import pytest

from folderhome.application.resource_registry import (
    ResourceRegistryError,
    default_resource_registry_path,
    load_resource_registry,
)


def _write_registry(
    path: Path,
    *,
    source: Path,
    output: Path,
    os_account: str = "synthetic-family-account",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "folderhome.resource-registry.v1",
                "os_account": os_account,
                "resources": [
                    {
                        "resource_id": "documents_inbox",
                        "kind": "directory",
                        "locator": {"type": "local_path", "path": str(source)},
                        "operations": ["list", "read"],
                        "purposes": ["documents.source"],
                        "profile_ids": ["lukas"],
                        "cloud_context": "minimized_with_approval",
                    },
                    {
                        "resource_id": "documents_output",
                        "kind": "directory",
                        "locator": {"type": "local_path", "path": str(output)},
                        "operations": ["create"],
                        "purposes": ["documents.output"],
                        "profile_ids": ["lukas"],
                        "cloud_context": "deny",
                    },
                ],
                "profile_defaults": {
                    "lukas": {
                        "documents.source": "documents_inbox",
                        "documents.output": "documents_output",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_default_resource_registry_path_uses_local_app_data() -> None:
    path = default_resource_registry_path(
        environ={"LOCALAPPDATA": "C:/Users/Demo/AppData/Local"}
    )

    assert path == Path("C:/Users/Demo/AppData/Local/FolderHome/resources.json")


def test_registry_resolves_profile_default_without_disclosing_paths(tmp_path: Path) -> None:
    source = tmp_path / "inbox"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    registry_path = tmp_path / "resources.json"
    _write_registry(registry_path, source=source, output=output)

    registry = load_resource_registry(
        registry_path,
        expected_os_account="synthetic-family-account",
        known_profile_ids=frozenset({"lukas"}),
    )
    resolved = registry.resolve_default(
        profile_id="lukas",
        purpose="documents.source",
        required_kind="directory",
        required_operations=frozenset({"list", "read"}),
    )

    assert resolved.resource_id == "documents_inbox"
    assert resolved.local_path == source.resolve()
    assert resolved.cloud_context == "minimized_with_approval"
    public = registry.to_public_dict(profile_id="lukas")
    assert public["security_boundary"] == "operating_system_account"
    assert public["paths_disclosed"] is False
    assert str(source.resolve()) not in json.dumps(public)
    assert public["defaults"]["documents.source"] == "documents_inbox"


def test_registry_rejects_relative_paths_unknown_profiles_and_privilege_escalation(
    tmp_path: Path,
) -> None:
    source = tmp_path / "inbox"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    registry_path = tmp_path / "resources.json"
    _write_registry(registry_path, source=source, output=output)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["resources"][0]["locator"]["path"] = "relative/inbox"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ResourceRegistryError, match="absoluten lokalen Pfad"):
        load_resource_registry(
            registry_path,
            expected_os_account="synthetic-family-account",
            known_profile_ids=frozenset({"lukas"}),
        )

    _write_registry(registry_path, source=source, output=output)
    registry = load_resource_registry(
        registry_path,
        expected_os_account="synthetic-family-account",
        known_profile_ids=frozenset({"lukas"}),
    )
    with pytest.raises(ResourceRegistryError, match="Unbekanntes Profil"):
        registry.resolve_default(
            profile_id="hanna",
            purpose="documents.source",
            required_kind="directory",
            required_operations=frozenset({"read"}),
        )
    with pytest.raises(ResourceRegistryError, match="Operation create"):
        registry.resolve_default(
            profile_id="lukas",
            purpose="documents.source",
            required_kind="directory",
            required_operations=frozenset({"create"}),
        )


def test_registry_rejects_mismatched_account_unknown_fields_and_bad_defaults(
    tmp_path: Path,
) -> None:
    source = tmp_path / "inbox"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    registry_path = tmp_path / "resources.json"
    _write_registry(registry_path, source=source, output=output)

    with pytest.raises(ResourceRegistryError, match="OS-Konto"):
        load_resource_registry(
            registry_path,
            expected_os_account="other-account",
            known_profile_ids=frozenset({"lukas"}),
        )

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["resources"][0]["secret"] = "must-not-be-here"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ResourceRegistryError, match="unbekannte Felder"):
        load_resource_registry(
            registry_path,
            expected_os_account="synthetic-family-account",
            known_profile_ids=frozenset({"lukas"}),
        )

    _write_registry(registry_path, source=source, output=output)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["profile_defaults"]["lukas"]["documents.source"] = "missing"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ResourceRegistryError, match="unbekannte Ressource"):
        load_resource_registry(
            registry_path,
            expected_os_account="synthetic-family-account",
            known_profile_ids=frozenset({"lukas"}),
        )


def test_registry_requires_existing_directory_roots(tmp_path: Path) -> None:
    registry_path = tmp_path / "resources.json"
    _write_registry(
        registry_path,
        source=tmp_path / "missing-inbox",
        output=tmp_path / "missing-output",
    )

    with pytest.raises(ResourceRegistryError, match="Verzeichnis fehlt"):
        load_resource_registry(
            registry_path,
            expected_os_account="synthetic-family-account",
            known_profile_ids=frozenset({"lukas"}),
        )
