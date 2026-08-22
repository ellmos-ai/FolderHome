from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from folderhome.application.calendar_handoff import (
    CalendarWorkflowError,
    analyze_folder_calendar,
)
from folderhome.application.contacts import ContactWorkflowError, analyze_folder_contacts
from folderhome.application.finance_statements import (
    FinanceWorkflowError,
    analyze_folder_statements,
)
from folderhome.application.folder_cleanup import (
    FolderCleanupError,
    build_folder_cleanup_plan,
)
from folderhome.application.health_dossier import build_health_dossier
from folderhome.application.household_inventory import (
    InventoryWorkflowError,
    analyze_folder_inventory,
)
from folderhome.application.medication_intake import (
    MedicationWorkflowError,
    analyze_folder_medication_plans,
)
from folderhome.capabilities.resource_budget import (
    DEFAULT_RESOURCE_POLICY,
    BoundedBytesIO,
    ResourceLimitExceeded,
    ResourcePolicy,
    inventory_files,
)
from folderhome.contracts import ResolvedProfilePolicy


def test_resource_policy_is_finite_and_rejects_unsafe_values() -> None:
    assert DEFAULT_RESOURCE_POLICY.max_files > 0
    assert DEFAULT_RESOURCE_POLICY.max_total_source_bytes >= (
        DEFAULT_RESOURCE_POLICY.max_file_bytes
    )

    with pytest.raises(ValueError, match="max_files"):
        ResourcePolicy(max_files=0)
    with pytest.raises(ValueError, match="max_output_bytes"):
        ResourcePolicy(max_output_bytes=True)


def test_inventory_stops_before_unbounded_file_or_byte_collection(tmp_path: Path) -> None:
    root = tmp_path / "Dokumente"
    root.mkdir()
    (root / "A.txt").write_bytes(b"1234")
    (root / "B.txt").write_bytes(b"5678")

    one_file = replace(DEFAULT_RESOURCE_POLICY, max_files=1)
    with pytest.raises(ResourceLimitExceeded, match="Dateianzahl-Budget"):
        inventory_files(root, recursive=True, policy=one_file)

    seven_bytes = replace(
        DEFAULT_RESOURCE_POLICY,
        max_file_bytes=7,
        max_total_source_bytes=7,
    )
    with pytest.raises(ResourceLimitExceeded, match="Gesamtquellgrößen-Budget"):
        inventory_files(root, recursive=True, policy=seven_bytes)


def test_bounded_bytes_buffer_blocks_growth_and_allows_in_limit_seek_writes() -> None:
    buffer = BoundedBytesIO(8, budget_name="Ausgabebyte-Budget")
    buffer.write(b"12345678")
    buffer.seek(2)
    buffer.write(b"ab")
    assert buffer.getvalue() == b"12ab5678"

    buffer.seek(8)
    with pytest.raises(ResourceLimitExceeded, match="Ausgabebyte-Budget"):
        buffer.write(b"9")


def _cleanup_policy() -> ResolvedProfilePolicy:
    return ResolvedProfilePolicy(
        profile_id="lukas",
        display_name="Lukas",
        area="dokumente",
        os_account="synthetic",
        organizational_only=True,
        security_boundary="Organisationsprofil, keine Zugriffsgrenze.",
        rules=(),
    )


@pytest.mark.parametrize(
    ("invoke", "error_type"),
    [
        (
            lambda root, extractor, policy: analyze_folder_contacts(
                root,
                profile_id="lukas",
                area="dokumente",
                extractor=extractor,
                resource_policy=policy,
            ),
            ContactWorkflowError,
        ),
        (
            lambda root, extractor, policy: analyze_folder_calendar(
                root,
                profile_id="lukas",
                area="dokumente",
                default_timezone="Europe/Berlin",
                extractor=extractor,
                resource_policy=policy,
            ),
            CalendarWorkflowError,
        ),
        (
            lambda root, extractor, policy: analyze_folder_statements(
                root,
                profile_id="lukas",
                extractor=extractor,
                resource_policy=policy,
            ),
            FinanceWorkflowError,
        ),
        (
            lambda root, extractor, policy: build_folder_cleanup_plan(
                root,
                policy=_cleanup_policy(),
                target_root=root.parent / "Ziel",
                as_of=date(2026, 8, 22),
                extractor=extractor,
                resource_policy=policy,
            ),
            FolderCleanupError,
        ),
        (
            lambda root, extractor, policy: build_health_dossier(
                root,
                profile_id="lukas",
                as_of=date(2026, 8, 22),
                extractor=extractor,
                allow_sensitive_local_read=True,
                resource_policy=policy,
            ),
            ResourceLimitExceeded,
        ),
        (
            lambda root, extractor, policy: analyze_folder_inventory(
                root,
                profile_id="lukas",
                extractor=extractor,
                resource_policy=policy,
            ),
            InventoryWorkflowError,
        ),
        (
            lambda root, extractor, policy: analyze_folder_medication_plans(
                root,
                profile_id="lukas",
                extractor=extractor,
                resource_policy=policy,
            ),
            MedicationWorkflowError,
        ),
    ],
)
def test_all_document_folder_entrypoints_share_the_inventory_budget(
    tmp_path: Path,
    invoke: Callable[[Path, object, ResourcePolicy], object],
    error_type: type[Exception],
) -> None:
    class UnusedExtractor:
        def extract(self, source_path: Path):
            raise AssertionError(f"Extractor darf nicht aufgerufen werden: {source_path}")

    root = tmp_path / "Dokumente"
    root.mkdir()
    (root / "A.txt").write_text("A", encoding="utf-8")
    (root / "B.txt").write_text("B", encoding="utf-8")
    policy = replace(DEFAULT_RESOURCE_POLICY, max_files=1)

    with pytest.raises(error_type, match="Dateianzahl-Budget"):
        invoke(root, UnusedExtractor(), policy)
