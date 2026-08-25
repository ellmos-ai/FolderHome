from __future__ import annotations

import pytest

from folderhome.application.capability_index import (
    CapabilityIndexError,
    adapter_descriptors,
    capability_index_document,
    capability_index_markdown,
    capability_index_prompt_excerpt,
    master_capability_index,
)
from folderhome.application.master_agent import (
    master_capability_catalog,
    master_expert_catalog,
)


def test_index_covers_every_catalog_endpoint_exactly_once() -> None:
    catalog = master_capability_catalog()
    index = master_capability_index()

    assert len(index) == len(catalog)
    assert {item.workflow_id for item in index} == {
        item.workflow_id for item in catalog
    }
    assert len({item.workflow_id for item in index}) == len(index)


def test_index_reuses_the_catalog_facts_instead_of_restating_them() -> None:
    catalog = {item.workflow_id: item for item in master_capability_catalog()}

    for entry in master_capability_index():
        capability = catalog[entry.workflow_id]
        assert entry.expert_id == capability.expert_id
        assert entry.execution_mode == capability.execution_mode
        assert entry.side_effects == capability.side_effects
        assert entry.approval_gates == capability.approval_gates


def test_index_reads_inputs_from_the_adapter_request_schema() -> None:
    descriptors = adapter_descriptors()
    index = {item.workflow_id: item for item in master_capability_index()}

    calendar = index["calendar-handoff"]
    schema = descriptors["calendar-handoff"].request_schema
    assert schema is not None
    assert set(calendar.required_inputs) == set(schema["required"])
    assert "export_resource_id" in calendar.optional_inputs
    assert "export_basename" in calendar.optional_inputs

    connectors = index["calendar-connectors"]
    assert connectors.required_inputs == ()
    assert connectors.implementation == "no_typed_adapter"


def test_index_states_code_availability_not_runtime_connection() -> None:
    index = {item.workflow_id: item for item in master_capability_index()}

    assert index["mail-connector"].implementation == "typed_adapter_available"
    assert index["document-library"].implementation == "direct_read_only_tool"
    assert index["master-agent"].implementation == "planning_only"
    assert index["scheduler-handoff"].implementation == "no_typed_adapter"


def test_side_effect_classes_stay_within_the_known_vocabulary() -> None:
    known = {
        "none",
        "local_simulation",
        "local_state_write",
        "local_file_write",
        "local_state_and_file_write",
        "external_effect",
    }

    classes = {item.side_effect_class for item in master_capability_index()}

    assert classes.issubset(known)
    index = {item.workflow_id: item for item in master_capability_index()}
    assert index["mail-connector"].side_effect_class == "external_effect"
    assert index["document-library"].side_effect_class == "none"
    assert index["findcall"].side_effect_class == "local_simulation"
    assert index["calendar-handoff"].side_effect_class == "local_state_and_file_write"


def test_calendar_handoff_no_longer_claims_an_external_calendar_write() -> None:
    catalog = {item.workflow_id: item for item in master_capability_catalog()}

    assert catalog["calendar-handoff"].side_effects == (
        "state.calendar.write",
        "file.create",
    )
    assert catalog["calendar-connectors"].side_effects == ("external.calendar.write",)


def test_eight_expert_roles_partition_the_catalog() -> None:
    experts = master_expert_catalog()
    catalog = master_capability_catalog()

    assert len(experts) == 8
    assigned: list[str] = []
    for expert in experts:
        assigned.extend(expert.workflow_ids)
    assert len(assigned) == len(set(assigned))
    assert set(assigned) == {item.workflow_id for item in catalog}
    for capability in catalog:
        owner = next(
            expert
            for expert in experts
            if capability.workflow_id in expert.workflow_ids
        )
        assert owner.expert_id == capability.expert_id


def test_prompt_excerpt_is_compact_grouped_and_path_free() -> None:
    excerpt = capability_index_prompt_excerpt(language="en")

    assert "[communication_expert]" in excerpt
    assert "mail-connector" in excerpt
    assert "effect: external_effect" in excerpt
    assert "C:\\" not in excerpt
    assert len(excerpt) < 4_500
    assert len(excerpt.splitlines()) == len(master_capability_index()) + 8


def test_prompt_excerpt_and_markdown_share_the_same_purpose_text() -> None:
    entry = next(
        item for item in master_capability_index() if item.workflow_id == "mail-connector"
    )

    assert entry.purpose_en in capability_index_prompt_excerpt(language="en")
    assert entry.purpose_en in capability_index_markdown(language="en")
    assert entry.purpose_de in capability_index_prompt_excerpt(language="de")
    assert entry.purpose_de in capability_index_markdown(language="de")


def test_document_is_machine_readable_and_language_checked() -> None:
    payload = capability_index_document(language="de")

    assert payload["schema"] == "folderhome.capability-index.v1"
    assert payload["endpoint_count"] == len(master_capability_index())
    assert payload["paths_disclosed"] is False
    first = payload["entries"][0]
    assert set(first) == {
        "workflow_id",
        "expert_id",
        "purpose",
        "execution_mode",
        "implementation",
        "required_inputs",
        "optional_inputs",
        "side_effect_class",
        "side_effects",
        "approval_gates",
    }

    with pytest.raises(CapabilityIndexError):
        capability_index_prompt_excerpt(language="fr")
