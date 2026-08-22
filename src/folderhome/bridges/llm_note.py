"""Pinned adapter for the standalone llm-note storage provider."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
    verify_checkout_revision,
)
from folderhome.contracts import PluginDescriptor
from folderhome.contracts.personal_notes import (
    PersonalNoteAction,
    PersonalNoteReference,
    PersonalNoteVersion,
)

_ENTRY_TYPE = "folderhome_note_version"
_SCHEMA_COLUMNS = {
    "id",
    "entry_type",
    "title",
    "content",
    "category",
    "source",
}


class LlmNoteBridgeError(RuntimeError):
    """Raised when the pinned note provider or its data cannot be trusted."""


class LlmNoteBridge:
    """Append versions through llm-note and read them without write-on-read."""

    def __init__(
        self,
        *,
        plugin: PluginDescriptor,
        provider_root: Path,
        db_path: Path,
    ) -> None:
        if plugin.plugin_id != "llm-note":
            raise LlmNoteBridgeError("Die Notizbrücke benötigt das llm-note-Manifest.")
        self.plugin = plugin
        self.provider_root = provider_root.resolve()
        self.db_path = db_path.resolve()
        try:
            verify_checkout_revision(self.provider_root, plugin.source_revision)
        except ProviderCheckoutError as exc:
            raise LlmNoteBridgeError(str(exc)) from exc

    @property
    def provider_id(self) -> str:
        return self.plugin.plugin_id

    @property
    def provider_revision(self) -> str:
        return self.plugin.source_revision

    def revision(self) -> str:
        versions = [item.to_dict() for item in self._all_versions()]
        return sha256(_canonical_json(versions).encode("utf-8")).hexdigest()

    def history(self, note_id: str) -> tuple[PersonalNoteVersion, ...]:
        return tuple(item for item in self._all_versions() if item.note_id == note_id)

    def list_current(
        self,
        *,
        profile_id: str,
        area: str | None = None,
        notebook_id: str | None = None,
    ) -> tuple[PersonalNoteVersion, ...]:
        current: dict[str, PersonalNoteVersion] = {}
        for item in self._all_versions():
            if item.profile_id != profile_id:
                continue
            if area is not None and item.area != area:
                continue
            if notebook_id is not None and item.notebook_id != notebook_id:
                continue
            current[item.note_id] = item
        return tuple(
            sorted(
                current.values(),
                key=lambda item: (item.area, item.title, item.note_id),
            )
        )

    def source_plan_applied(self, plan_id: str) -> bool:
        return any(item.source_plan_id == plan_id for item in self._all_versions())

    def append_version(self, version: PersonalNoteVersion) -> PersonalNoteVersion:
        if self.source_plan_applied(version.source_plan_id):
            raise LlmNoteBridgeError("Der Notizplan wurde bereits angewendet.")
        payload = version.to_dict()
        payload.pop("provider_entry_id")
        try:
            modules = load_pinned_python_modules(
                plugin=self.plugin,
                provider_root=self.provider_root,
                package_name="llm_note",
            )
            note_store = modules["llm_note"].NoteStore(self.db_path)
            entry = note_store.write(
                _canonical_json(payload),
                entry_type=_ENTRY_TYPE,
                category=f"folderhome:{version.area}",
                title=version.title,
                source="folderhome-human",
            )
        except (ProviderCheckoutError, OSError, sqlite3.Error, AttributeError) as exc:
            raise LlmNoteBridgeError(f"llm-note konnte die Version nicht speichern: {exc}") from exc
        stored = replace(version, provider_entry_id=int(entry.id))
        roundtrip = self.history(version.note_id)
        if not roundtrip or roundtrip[-1] != stored:
            raise LlmNoteBridgeError("Gespeicherte llm-note-Version bestand den Readback nicht.")
        return stored

    def _all_versions(self) -> tuple[PersonalNoteVersion, ...]:
        if not self.db_path.is_file():
            return ()
        uri = f"file:{self.db_path.as_posix()}?mode=ro&immutable=1"
        try:
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(note_entries)").fetchall()
            }
            if not _SCHEMA_COLUMNS.issubset(columns):
                raise LlmNoteBridgeError("llm-note-Datenbank besitzt ein unbekanntes Schema.")
            rows = connection.execute(
                "SELECT id, content FROM note_entries WHERE entry_type = ? ORDER BY id",
                (_ENTRY_TYPE,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise LlmNoteBridgeError(f"llm-note-Datenbank ist nicht lesbar: {exc}") from exc
        finally:
            if "connection" in locals():
                connection.close()
        versions = tuple(_version_from_row(row) for row in rows)
        by_note: dict[str, int] = {}
        for item in versions:
            expected = by_note.get(item.note_id, 0) + 1
            if item.revision != expected:
                raise LlmNoteBridgeError("llm-note-Versionsfolge ist nicht lückenlos.")
            by_note[item.note_id] = item.revision
        return versions


def _version_from_row(row: sqlite3.Row) -> PersonalNoteVersion:
    try:
        payload = json.loads(str(row["content"]))
        if payload.pop("schema", None) != PersonalNoteVersion.SCHEMA:
            raise ValueError("unbekanntes Schema")
        references = tuple(_reference_from_payload(item) for item in payload.pop("references"))
        version = PersonalNoteVersion(
            note_id=payload.pop("note_id"),
            revision=payload.pop("revision"),
            action=PersonalNoteAction(payload.pop("action")),
            profile_id=payload.pop("profile_id"),
            notebook_id=payload.pop("notebook_id"),
            area=payload.pop("area"),
            title=payload.pop("title"),
            human_content=payload.pop("human_content"),
            references=references,
            source_plan_id=payload.pop("source_plan_id"),
            parent_revision=payload.pop("parent_revision"),
            reverts_revision=payload.pop("reverts_revision"),
            created_at=payload.pop("created_at"),
            provider_entry_id=int(row["id"]),
            author_kind=payload.pop("author_kind"),
            os_account_is_security_boundary=payload.pop("os_account_is_security_boundary"),
            profile_is_security_boundary=payload.pop("profile_is_security_boundary"),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LlmNoteBridgeError(f"Ungültiger FolderHome-Eintrag in llm-note: {exc}") from exc
    if payload:
        raise LlmNoteBridgeError(
            "Unbekannte Felder im FolderHome-llm-note-Eintrag: " + ", ".join(sorted(payload))
        )
    return version


def _reference_from_payload(payload: object) -> PersonalNoteReference:
    if not isinstance(payload, dict):
        raise ValueError("Notizreferenz ist kein Objekt")
    data = dict(payload)
    if data.pop("schema", None) != PersonalNoteReference.SCHEMA:
        raise ValueError("Notizreferenz besitzt ein unbekanntes Schema")
    expected = {"kind", "target_id", "label", "sha256"}
    if set(data) != expected:
        raise ValueError("Notizreferenz besitzt unbekannte Felder")
    return PersonalNoteReference(**data)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
