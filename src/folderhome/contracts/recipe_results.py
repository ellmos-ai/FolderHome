"""Typed v2 result slots, not authorization or proof of execution.

The stage runner must obtain reports from its own verified execution path.
Selecting a JSON value here does not establish its origin or allow an effect.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import dataclass

from folderhome.contracts.recipes import (
    _FIELD,
    _STEP_REF,
    CapabilityRecipe,
    CapabilityRecipeError,
)

RESULT_RECIPE_SCHEMA = "folderhome.capability-recipe.v2"
_TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}
_AUTHORITY_PARTS = {
    "resource",
    "profile",
    "account",
    "workflow",
    "allow",
    "approval",
    "approved",
    "path",
    "dir",
    "directory",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "token",
    "policy",
    "permissions",
    "gates",
}


@dataclass(frozen=True, slots=True)
class RecipeResultBinding:
    """One literal report path feeding one later top-level data field."""

    from_step: str
    to_step: str
    source_path: tuple[str | int, ...]
    target_field: str
    value_type: str

    def __post_init__(self) -> None:
        for ref in (self.from_step, self.to_step):
            if not isinstance(ref, str) or _STEP_REF.fullmatch(ref) is None:
                raise CapabilityRecipeError("Ergebnisübergabe benötigt gültige Schritte.")
        if self.from_step == self.to_step:
            raise CapabilityRecipeError("Ergebnisübergabe benötigt zwei Schritte.")
        if (
            not isinstance(self.target_field, str)
            or _FIELD.fullmatch(self.target_field) is None
            or _AUTHORITY_PARTS.intersection(self.target_field.split("_"))
        ):
            raise CapabilityRecipeError("Ergebnisziel muss ein Nutzdatenfeld sein.")
        if not isinstance(self.value_type, str) or self.value_type not in _TYPES:
            raise CapabilityRecipeError("Ergebnisübergabe benötigt einen JSON-Typ.")
        if not isinstance(self.source_path, tuple) or not 1 <= len(self.source_path) <= 8:
            raise CapabilityRecipeError("Ergebnispfad benötigt 1 bis 8 Segmente.")
        for segment in self.source_path:
            if type(segment) is int and segment >= 0:
                continue
            if type(segment) is str and 1 <= len(segment) <= 128:
                try:
                    segment.encode("utf-8")
                except UnicodeError as exc:
                    raise CapabilityRecipeError("Ergebnispfad benötigt gültiges UTF-8.") from exc
                continue
            raise CapabilityRecipeError("Ergebnispfad enthält ein ungültiges Segment.")

    def to_dict(self) -> dict[str, object]:
        return {
            "from_step": self.from_step,
            "to_step": self.to_step,
            "source_path": list(self.source_path),
            "target_field": self.target_field,
            "value_type": self.value_type,
        }

    def select_value(self, domain_report: dict[str, object]) -> object:
        """Select and copy bounded JSON, without coercion or provenance claims."""

        value: object = domain_report
        for segment in self.source_path:
            if (
                type(segment) is str
                and type(value) is dict
                and segment in value
                or type(segment) is int
                and type(value) is list
                and segment < len(value)
            ):
                value = value[segment]
            else:
                raise CapabilityRecipeError("Deklarierter Ergebniswert fehlt im Bericht.")
        expected = {
            "string": (str,),
            "integer": (int,),
            "number": (int, float),
            "boolean": (bool,),
            "object": (dict,),
            "array": (list,),
            "null": (type(None),),
        }
        if type(value) not in expected[self.value_type]:
            raise CapabilityRecipeError("Ergebniswert entspricht nicht dem deklarierten Typ.")
        _validate_json(value)
        return deepcopy(value)


@dataclass(frozen=True, slots=True)
class ResultBoundRecipe(CapabilityRecipe):
    """A journey requiring fresh approval after concrete results become known."""

    result_bindings: tuple[RecipeResultBinding, ...] = ()
    SCHEMA = RESULT_RECIPE_SCHEMA

    def __post_init__(self) -> None:
        CapabilityRecipe.__post_init__(self)
        if not isinstance(self.result_bindings, (tuple, list)):
            raise CapabilityRecipeError("Ergebnisübergaben müssen eine Liste sein.")
        object.__setattr__(self, "result_bindings", tuple(self.result_bindings))
        if len(self.steps) > 32 or not 1 <= len(self.result_bindings) <= 32:
            raise CapabilityRecipeError("v2 erlaubt höchstens 32 Schritte und 1 bis 32 Slots.")
        by_ref = {step.step_ref: (index, step) for index, step in enumerate(self.steps)}
        targets: set[tuple[str, str]] = set()
        for binding in self.result_bindings:
            if not isinstance(binding, RecipeResultBinding):
                raise CapabilityRecipeError("Ergebnisübergabe ist ungültig.")
            source = by_ref.get(binding.from_step)
            target = by_ref.get(binding.to_step)
            if source is None or target is None or source[0] >= target[0]:
                raise CapabilityRecipeError("Ergebnisübergabe muss vorwärts gerichtet sein.")
            slot = (binding.to_step, binding.target_field)
            if slot in targets or binding.target_field in target[1].request:
                raise CapabilityRecipeError("Ergebnisslot darf keinen Wert überschreiben.")
            targets.add(slot)

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        result = CapabilityRecipe.to_dict(self, language=language)
        result["result_bindings"] = [item.to_dict() for item in self.result_bindings]
        return result


def _validate_json(value: object) -> None:
    # Bounds apply before copying/serialization; depth also catches cyclic containers.
    remaining = 4096
    byte_budget = 65536

    def charge(amount: int) -> None:
        nonlocal byte_budget
        byte_budget -= amount
        if byte_budget < 0:
            raise CapabilityRecipeError("Ergebniswert überschreitet 64 KiB.")

    def scalar(item: object) -> None:
        if type(item) is str and len(item) > byte_budget:
            raise CapabilityRecipeError("Ergebniswert überschreitet 64 KiB.")
        try:
            size = len(json.dumps(item, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise CapabilityRecipeError("Ergebniswert ist kein gültiges UTF-8-JSON.") from exc
        charge(size)

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 16:
            raise CapabilityRecipeError("Ergebniswert ist zu groß oder zu tief verschachtelt.")
        if type(item) in (str, int, bool, type(None)):
            scalar(item)
            return
        if type(item) is float and math.isfinite(item):
            scalar(item)
            return
        if type(item) is list:
            charge(2 + max(0, len(item) - 1) * 2)  # brackets and default JSON ', '
            for child in item:
                visit(child, depth + 1)
            return
        if type(item) is dict:
            charge(2 + max(0, len(item) - 1) * 2 + len(item) * 2)  # braces, ', ', ': '
            for key, child in item.items():
                if type(key) is not str:
                    raise CapabilityRecipeError("JSON-Ergebnis benötigt Textschlüssel.")
                visit(key, depth + 1)
                visit(child, depth + 1)
            return
        raise CapabilityRecipeError("Ergebniswert ist kein endlicher JSON-Wert.")

    visit(value, 0)
