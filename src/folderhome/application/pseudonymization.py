"""Reversible, process-local pseudonymization at the remote model boundary."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import AsyncIterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

try:
    from strands.models import Model as _StrandsModel
except ImportError:  # Keep CLI/help and the packaged starter importable for --no-deps smoke runs.
    class _StrandsModel:
        """Import-time fallback; live agent execution still requires strands-agents."""

        pass

from folderhome.capabilities.catalog import DocumentCatalogError, DocumentCatalogStore
from folderhome.capabilities.contact_registry import ContactRegisterError, ContactRegisterStore

_KINDS = ("PERSON", "EMAIL", "PHONE", "IBAN", "ADDRESS", "DOC", "ID")
_NAME_PART = re.compile(r"[^\W\d_][^\W\d_'’-]*", re.UNICODE)


class PseudonymizationError(RuntimeError):
    """Raised when the local protection boundary cannot be prepared safely."""


@dataclass(frozen=True, slots=True)
class _KnownValue:
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class _Pattern:
    kind: str
    regex: re.Pattern[str]
    group: int = 0


@dataclass(frozen=True, slots=True)
class _Candidate:
    start: int
    end: int
    kind: str
    known: bool


_PATTERNS = (
    _Pattern(
        "ADDRESS",
        re.compile(
            r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'’ -]{0,50}"
            r"(?:straße|strasse|str\.|weg|allee|platz|gasse|ring)\s+"
            r"\d{1,5}[A-Za-z]?(?:\s*[,;\n]\s*|\s+)"
            r"\d{5}\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'’ -]{1,50}\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "EMAIL",
        re.compile(
            r"(?<![\w@])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[A-Z0-9.-]+\.[A-Z]{2,}(?![\w@])",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "IBAN",
        re.compile(r"(?<![A-Z0-9])[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}(?![A-Z0-9])", re.IGNORECASE),
    ),
    _Pattern(
        "DOC",
        re.compile(r"(?<![A-Za-z0-9_])doc_[0-9a-f]{64}(?![A-Za-z0-9_])", re.IGNORECASE),
    ),
    _Pattern(
        "ID",
        re.compile(r"(?<![A-Z0-9-])SYN-[A-Z0-9]+(?:-[A-Z0-9]+)+(?![A-Z0-9-])", re.IGNORECASE),
    ),
    _Pattern(
        "ID",
        re.compile(
            r"\b(?:Policenummer|Police|Policy(?: number)?|Versicherungsnummer|"
            r"Vertragsnummer|Contract(?: number)?)\s*(?:Nr\.?|No\.?)?\s*[:#-]?\s*"
            r"([A-Z0-9][A-Z0-9./_-]{3,})\b",
            re.IGNORECASE,
        ),
        1,
    ),
    _Pattern(
        "ID",
        re.compile(
            r"\b(?:geboren(?: am)?|Geburtsdatum|born(?: on)?)\s*[:,-]?\s*"
            r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b",
            re.IGNORECASE,
        ),
        1,
    ),
    _Pattern(
        "PHONE",
        re.compile(
            r"(?<![\w+])(?:\+\d{1,3}|00\d{1,3}|0)(?:[\s()./-]*\d){7,14}(?!\w)"
        ),
    ),
    _Pattern(
        "ADDRESS",
        re.compile(
            r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'’ -]{0,50}"
            r"(?:straße|strasse|str\.|weg|allee|platz|gasse|ring)\s+"
            r"\d{1,5}[A-Za-z]?\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "ADDRESS",
        re.compile(r"(?<!\d)\d{5}\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'’ -]{1,50}\b"),
    ),
    _Pattern(
        "ID",
        re.compile(r"(?<![A-ZÄÖÜ0-9-])[A-ZÄÖÜ]{1,3}[- ][A-Z]{1,2}[- ]\d{1,4}(?![A-Z0-9-])"),
    ),
)


class PseudonymVault:
    """Keep original-to-placeholder mappings only in this local process."""

    def __init__(self) -> None:
        self._known: dict[tuple[str, str], _KnownValue] = {}
        self._original_to_placeholder: dict[tuple[str, str], str] = {}
        self._placeholder_to_original: dict[str, str] = {}
        self._next_by_kind: Counter[str] = Counter()
        self._turn_placeholders: set[str] = set()

    def begin_turn(self) -> None:
        """Start last-turn accounting without discarding session-stable mappings."""

        self._turn_placeholders.clear()

    def add_known(self, kind: str, value: str | None) -> None:
        if kind not in _KINDS or not isinstance(value, str):
            return
        normalized = value.strip()
        if len(normalized) < 2:
            return
        self._known.setdefault((kind, normalized.casefold()), _KnownValue(kind, normalized))

    def pseudonymize(self, text: str) -> str:
        """Replace longest non-overlapping spans; known values win equal spans."""

        candidates: list[_Candidate] = []
        values = sorted(self._known.values(), key=lambda item: len(item.value), reverse=True)
        for item in values:
            boundary = re.compile(
                rf"(?<!\w){re.escape(item.value)}(?!\w)",
                re.IGNORECASE,
            )
            candidates.extend(
                _Candidate(match.start(), match.end(), item.kind, True)
                for match in boundary.finditer(text)
            )
        for pattern in _PATTERNS:
            candidates.extend(
                _Candidate(
                    match.start(pattern.group),
                    match.end(pattern.group),
                    pattern.kind,
                    False,
                )
                for match in pattern.regex.finditer(text)
            )
        selected: list[_Candidate] = []
        for candidate in sorted(
            candidates,
            key=lambda item: (-(item.end - item.start), not item.known, item.start),
        ):
            if any(
                candidate.start < current.end and current.start < candidate.end
                for current in selected
            ):
                continue
            selected.append(candidate)
        protected = text
        replacements = [
            (candidate, self._replace(text[candidate.start:candidate.end], candidate.kind))
            for candidate in sorted(selected, key=lambda item: item.start)
        ]
        for candidate, placeholder in reversed(replacements):
            protected = (
                protected[:candidate.start]
                + placeholder
                + protected[candidate.end:]
            )
        return protected

    def restore(self, text: str) -> str:
        """Restore canonical values, accepting common bracket mutations by models."""

        restored = text
        for placeholder in sorted(self._placeholder_to_original, key=len, reverse=True):
            token = placeholder[1:-1]
            tolerant = re.compile(
                rf"(?<![A-Z0-9_])(?:⟨|\[|<)?{re.escape(token)}(?:⟩|\]|>)?(?![A-Z0-9_])",
                re.IGNORECASE,
            )
            restored = tolerant.sub(
                lambda _match, original=self._placeholder_to_original[placeholder]: original,
                restored,
            )
        return restored

    def pseudonymize_object(self, value: Any) -> Any:
        return _map_strings(value, self.pseudonymize)

    def restore_object(self, value: Any) -> Any:
        return _map_strings(value, self.restore)

    def restore_json_text(self, value: str) -> str:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return self.restore(value)
        return json.dumps(
            _map_strings(payload, self.restore, transform_keys=True),
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def summary(self, *, active: bool) -> dict[str, object]:
        counts = Counter(
            placeholder[1:-1].rsplit("_", 1)[0]
            for placeholder in self._turn_placeholders
        )
        return {
            "active": active,
            "replacements": len(self._turn_placeholders),
            "kinds": {kind: counts[kind] for kind in _KINDS if counts[kind]},
        }

    def _replace(self, original: str, kind: str) -> str:
        key = (kind, original.casefold())
        placeholder = self._original_to_placeholder.get(key)
        if placeholder is None:
            self._next_by_kind[kind] += 1
            placeholder = f"⟨{kind}_{self._next_by_kind[kind]}⟩"
            self._original_to_placeholder[key] = placeholder
            self._placeholder_to_original[placeholder] = original
        self._turn_placeholders.add(placeholder)
        return placeholder


class PseudonymizingModel(_StrandsModel):
    """Strands model decorator that protects every remote request and response."""

    def __init__(self, inner_model: Model, vault: PseudonymVault) -> None:
        self.inner_model = inner_model
        self.vault = vault

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner_model, name)

    @property
    def stateful(self) -> bool:
        return self.inner_model.stateful

    def update_config(self, **model_config: Any) -> None:
        self.inner_model.update_config(**model_config)

    def get_config(self) -> Any:
        return self.inner_model.get_config()

    async def count_tokens(
        self,
        messages,
        tool_specs=None,
        system_prompt: str | None = None,
        system_prompt_content=None,
    ) -> int:
        return await self.inner_model.count_tokens(
            self.vault.pseudonymize_object(messages),
            tool_specs,
            self.vault.pseudonymize(system_prompt) if system_prompt is not None else None,
            self.vault.pseudonymize_object(system_prompt_content),
        )

    async def structured_output(
        self,
        output_model,
        prompt,
        system_prompt: str | None = None,
        **kwargs: Any,
    ):
        async for event in self.inner_model.structured_output(
            output_model,
            self.vault.pseudonymize_object(prompt),
            self.vault.pseudonymize(system_prompt) if system_prompt is not None else None,
            **kwargs,
        ):
            yield self.vault.restore_object(event)

    async def stream(
        self,
        messages,
        tool_specs=None,
        system_prompt: str | None = None,
        *,
        tool_choice=None,
        system_prompt_content=None,
        invocation_state=None,
        **kwargs: Any,
    ) -> AsyncIterable[dict[str, object]]:
        stream = self.inner_model.stream(
            self.vault.pseudonymize_object(messages),
            tool_specs,
            self.vault.pseudonymize(system_prompt) if system_prompt is not None else None,
            tool_choice=tool_choice,
            system_prompt_content=self.vault.pseudonymize_object(system_prompt_content),
            invocation_state=invocation_state,
            **kwargs,
        )
        buffered_kind: str | None = None
        buffered_value = ""

        async def flush():
            nonlocal buffered_kind, buffered_value
            if buffered_kind is None:
                return None
            value = (
                self.vault.restore_json_text(buffered_value)
                if buffered_kind == "toolUse"
                else self.vault.restore(buffered_value)
            )
            event = {"contentBlockDelta": {"delta": {buffered_kind: (
                {"input": value} if buffered_kind == "toolUse" else value
            )}}}
            buffered_kind = None
            buffered_value = ""
            return event

        async for event in stream:
            delta = event.get("contentBlockDelta", {}).get("delta", {})
            kind = "text" if isinstance(delta.get("text"), str) else (
                "toolUse"
                if isinstance(delta.get("toolUse"), dict)
                and isinstance(delta["toolUse"].get("input"), str)
                else None
            )
            if kind is not None:
                if buffered_kind not in {None, kind}:
                    pending = await flush()
                    if pending is not None:
                        yield pending
                buffered_kind = kind
                buffered_value += delta[kind]["input"] if kind == "toolUse" else delta[kind]
                continue
            pending = await flush()
            if pending is not None:
                yield pending
            yield self.vault.restore_object(deepcopy(event))
        pending = await flush()
        if pending is not None:
            yield pending


def seed_vault_from_application(
    vault: PseudonymVault,
    application: Any,
    *,
    profile_id: str,
) -> None:
    """Load known values through existing typed local stores, never by scanning files."""

    for profile in application.profiles.profiles:
        vault.add_known("PERSON", profile.display_name)
        for part in _NAME_PART.findall(profile.display_name):
            vault.add_known("PERSON", part)
    for account in (
        application.profiles.os_account,
        getattr(getattr(application, "_identity", None), "account_name", None),
    ):
        vault.add_known("ID", account)
    try:
        contacts = ContactRegisterStore(application.settings.state_dir).list_contacts(
            profile_id=profile_id,
        )
        documents = DocumentCatalogStore(application.settings.state_dir).load()
    except (ContactRegisterError, DocumentCatalogError, OSError, ValueError) as exc:
        raise PseudonymizationError(
            "Lokale Pseudonymisierung konnte bekannte Werte nicht sicher laden."
        ) from exc
    for contact in contacts:
        vault.add_known("PERSON", contact.contact_name)
        vault.add_known("EMAIL", contact.email)
        vault.add_known("PHONE", contact.phone)
    for document in documents:
        vault.add_known("DOC", _text_value(document.get("document_id")))
        _add_number_fields(vault, document)


def _add_number_fields(vault: PseudonymVault, value: object, key: str = "") -> None:
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            _add_number_fields(vault, child, str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            _add_number_fields(vault, child, key)
    elif isinstance(value, str) and any(
        marker in key.casefold()
        for marker in ("policy_number", "contract_number", "insurance_number")
    ):
        vault.add_known("ID", value)


def _text_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _map_strings(value: Any, transform, *, transform_keys: bool = False) -> Any:
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, BaseModel):
        payload = _map_strings(
            value.model_dump(),
            transform,
            transform_keys=transform_keys,
        )
        return value.__class__.model_validate(payload)
    if isinstance(value, dict):
        return {
            transform(key) if transform_keys and isinstance(key, str) else key: _map_strings(
                item,
                transform,
                transform_keys=(transform_keys or key == "json"),
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _map_strings(item, transform, transform_keys=transform_keys)
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            _map_strings(item, transform, transform_keys=transform_keys)
            for item in value
        )
    return value


__all__ = [
    "PseudonymizationError",
    "PseudonymizingModel",
    "PseudonymVault",
    "seed_vault_from_application",
]
