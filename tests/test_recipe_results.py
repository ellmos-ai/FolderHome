"""v2 must not silently lose bindings, coerce values or widen authority."""

import json
import tracemalloc
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from folderhome.application.recipes import build_recipe_plan, parse_recipe, recipe_sha256
from folderhome.contracts.recipes import CapabilityRecipeError


def payload():
    original = json.loads(
        (Path(__file__).parents[1] / "src/folderhome/recipes/accident-aftercare.json").read_text(
            encoding="utf-8"
        )
    )
    original["schema"] = "folderhome.capability-recipe.v2"
    original["result_bindings"] = [
        {
            "from_step": "contacts",
            "to_step": "letter",
            "source_path": ["contacts", 0, "name"],
            "target_field": "recipient",
            "value_type": "string",
        }
    ]
    return original


def test_v2_preserves_typed_binding_and_hashes_its_meaning():
    raw = payload()
    recipe = parse_recipe(raw)
    public = recipe.to_dict()
    assert public["schema"] == "folderhome.capability-recipe.v2"
    assert public["result_bindings"] == raw["result_bindings"]
    baseline = recipe_sha256(recipe)
    raw["result_bindings"][0]["source_path"][-1] = "email"
    assert recipe_sha256(parse_recipe(raw)) != baseline
    assert recipe.to_dict()["result_bindings"][0]["source_path"][-1] == "name"
    public["result_bindings"][0]["source_path"][-1] = "modified"
    assert recipe_sha256(recipe) == baseline


@pytest.mark.parametrize(
    "change",
    [
        {"from_step": "letter"},
        {"from_step": "appointment"},
        {"from_step": "missing"},
        {"to_step": "missing"},
        {"source_path": []},
        {"source_path": [True]},
        {"source_path": [-1]},
        {"source_path": [""]},
        {"source_path": "contacts[0].name"},
        {"source_path": ["x"] * 9},
        {"value_type": "any"},
        {"extra": "ignored"},
    ],
)
def test_invalid_edges_and_ambiguous_paths_fail_closed(change):
    raw = payload()
    raw["result_bindings"][0].update(change)
    with pytest.raises(CapabilityRecipeError):
        parse_recipe(raw)


@pytest.mark.parametrize(
    "field",
    [
        "profile_id",
        "source_resource_id",
        "account_id",
        "workflow_id",
        "allow_sensitive",
        "approval_kind",
        "output_path",
        "state_dir",
        "credentials",
        "authorization",
        "token",
        "policy",
    ],
)
def test_result_cannot_select_authority(field):
    raw = payload()
    raw["result_bindings"][0]["target_field"] = field
    with pytest.raises(CapabilityRecipeError):
        parse_recipe(raw)


@pytest.mark.parametrize("conflict", ["duplicate", "static", "missing", "empty", "too_many"])
def test_result_slots_cannot_overwrite_or_disappear(conflict):
    raw = payload()
    if conflict == "duplicate":
        raw["result_bindings"] *= 2
    elif conflict == "static":
        raw["steps"][1]["request"]["recipient"] = "Keep this"
    elif conflict == "missing":
        del raw["result_bindings"]
    elif conflict == "empty":
        raw["result_bindings"] = []
    else:
        raw["result_bindings"] *= 33
    with pytest.raises(CapabilityRecipeError):
        parse_recipe(raw)


def test_v1_cannot_silently_consume_result_binding_document():
    raw = payload()
    raw["schema"] = "folderhome.capability-recipe.v1"
    with pytest.raises(CapabilityRecipeError):
        parse_recipe(raw)


def test_v1_planner_rejects_v2_before_any_adapter_preparation():
    recipe = parse_recipe(payload())
    prepared = []
    with pytest.raises(CapabilityRecipeError, match="[Aa]bschnitt|[Ss]tage"):
        build_recipe_plan(
            recipe,
            profile_id="lukas",
            language="en",
            prepare=lambda *args: prepared.append(args),
            endpoint_statuses={},
            known_resource_ids=frozenset(),
        )
    assert prepared == []


@pytest.mark.parametrize(
    "kind,value",
    [
        ("string", "Müller"),
        ("integer", 0),
        ("number", 2.5),
        ("boolean", False),
        ("null", None),
        ("object", {"name": "Özlem"}),
        ("array", [{"name": "Özlem"}]),
    ],
)
def test_explicit_path_selects_exact_typed_detached_value(kind, value):
    raw = payload()
    raw["result_bindings"][0].update(source_path=["results", 0, "value"], value_type=kind)
    binding = parse_recipe(raw).result_bindings[0]
    report = {"results": [{"value": deepcopy(value)}]}
    selected = binding.select_value(report)
    assert selected == value
    if kind == "object":
        selected["name"] = "Changed"
    elif kind == "array":
        selected[0]["name"] = "Changed"
    assert report == {"results": [{"value": value}]}


@pytest.mark.parametrize(
    "kind,value",
    [
        ("integer", True),
        ("number", False),
        ("integer", "1"),
        ("integer", 1.0),
        ("string", None),
        ("boolean", 1),
        ("object", []),
        ("array", {}),
        ("null", "null"),
        ("number", float("nan")),
        ("number", float("inf")),
        ("object", {1: "bad key"}),
        ("array", [object()]),
        pytest.param("string", "ü" * 32769, id="utf8-byte-budget"),
        pytest.param("string", "\ud800", id="invalid-unicode"),
    ],
)
def test_values_are_not_coerced_and_must_be_bounded_json(kind, value):
    raw = payload()
    raw["result_bindings"][0].update(source_path=["value"], value_type=kind)
    binding = parse_recipe(raw).result_bindings[0]
    with pytest.raises(CapabilityRecipeError):
        binding.select_value({"value": value})


@pytest.mark.parametrize(
    "report",
    [
        {},
        {"contacts": []},
        {"contacts": {"0": {"name": "wrong"}}},
        {"contacts": [{"email": "wrong"}]},
    ],
)
def test_missing_path_is_not_replaced_by_null_or_object_index(report):
    binding = parse_recipe(payload()).result_bindings[0]
    with pytest.raises(CapabilityRecipeError):
        binding.select_value(report)


def test_cyclic_and_overdeep_values_fail_with_recipe_error():
    raw = payload()
    raw["result_bindings"][0].update(source_path=["value"], value_type="array")
    binding = parse_recipe(raw).result_bindings[0]
    cyclic = []
    cyclic.append(cyclic)
    deep = []
    for _ in range(18):
        deep = [deep]
    for value in (cyclic, deep):
        with pytest.raises(CapabilityRecipeError):
            binding.select_value({"value": value})


def test_direct_contract_replacement_revalidates_paths():
    binding = parse_recipe(payload()).result_bindings[0]
    with pytest.raises(CapabilityRecipeError):
        replace(binding, source_path=(False,))


def test_invalid_unicode_path_is_rejected_before_recipe_hashing():
    raw = payload()
    raw["result_bindings"][0]["source_path"] = ["\ud800"]
    with pytest.raises(CapabilityRecipeError):
        parse_recipe(raw)


def test_value_byte_budget_stops_before_materializing_large_combined_json():
    raw = payload()
    raw["result_bindings"][0].update(source_path=["value"], value_type="array")
    binding = parse_recipe(raw).result_bindings[0]
    value = ["x" * 65534] * 32  # Shared input; serializing all of it allocates >2 MiB.
    tracemalloc.start()
    try:
        baseline = tracemalloc.get_traced_memory()[0]
        tracemalloc.reset_peak()
        with pytest.raises(CapabilityRecipeError):
            binding.select_value({"value": value})
        peak = tracemalloc.get_traced_memory()[1] - baseline
    finally:
        tracemalloc.stop()
    assert peak < 1024 * 1024, "64-KiB rejection must not allocate the entire large value"


def test_exact_64_kib_json_string_is_accepted():
    binding = replace(parse_recipe(payload()).result_bindings[0], source_path=("value",))
    value = "x" * 65534
    assert binding.select_value({"value": value}) == value


def test_direct_recipe_construction_does_not_retain_mutable_binding_list():
    original = parse_recipe(payload())
    supplied = list(original.result_bindings)
    detached = replace(original, result_bindings=supplied)
    supplied.clear()
    assert len(detached.to_dict()["result_bindings"]) == 1
