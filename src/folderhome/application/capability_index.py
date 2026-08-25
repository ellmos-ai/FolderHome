"""One generated capability index for the model prompt and the documentation.

Before this module the same facts lived in three places: the master capability
catalog knew the expert and the gates, the adapter descriptors knew the request
schema, and the workflow documents carried the purpose. This module joins them
once so a prompt excerpt and a documentation table can never drift apart.

It reads adapter descriptors statically from the adapter classes and therefore
never instantiates an adapter, never touches a registry, and never claims that
a specific installation has an endpoint connected.
"""

from __future__ import annotations

from dataclasses import dataclass

from folderhome.application import workflow_execution
from folderhome.application.master_agent import master_capability_catalog
from folderhome.contracts.workflow_execution import WorkflowAdapterDescriptor

SCHEMA = "folderhome.capability-index.v1"

_PURPOSES: dict[str, tuple[str, str]] = {
    "administrative-drafts": (
        "Prepare an unsent administrative letter from a recorded notice.",
        "Ein ungesendetes Behördenschreiben aus einem erfassten Bescheid vorbereiten.",
    ),
    "artifact-studio": (
        "Plan and render a local presentation, table, card or media artifact.",
        "Eine lokale Präsentation, Tabelle, Karte oder Mediendatei planen und erzeugen.",
    ),
    "benefit-screening": (
        "Match a local benefit profile against dated criteria as guidance only.",
        "Ein lokales Leistungsprofil gegen datierte Kriterien abgleichen, nur als Orientierung.",
    ),
    "calendar-connectors": (
        "Plan a provider-neutral external calendar connector without invoking one.",
        "Einen providerneutralen externen Kalender-Connector planen, ohne ihn aufzurufen.",
    ),
    "calendar-handoff": (
        "Record document appointments in the local calendar and optionally export them as ICS.",
        "Dokumenttermine im lokalen Kalender festhalten und auf Wunsch als ICS exportieren.",
    ),
    "contact-register": (
        "Extract labeled contact data from documents into the local contact register.",
        "Gelabelte Kontaktdaten aus Dokumenten in das lokale Kontaktregister übernehmen.",
    ),
    "contract-cockpit": (
        "Answer a contract or insurance question as an evidence-linked read-only overview.",
        "Eine Vertrags- oder Versicherungsfrage als belegverknüpfte Übersicht beantworten.",
    ),
    "correspondence-studio": (
        "Render one local letter from a controlled template and design.",
        "Einen lokalen Brief aus geprüfter Vorlage und Gestaltung erzeugen.",
    ),
    "daily-briefing": (
        "Bundle a provided weather and news snapshot into one local HTML brief.",
        "Einen bereitgestellten Wetter- und Nachrichtenstand als lokales HTML-Briefing bündeln.",
    ),
    "directory-observation": (
        "Compare an observed folder against its checkpoint without reading document text.",
        "Einen beobachteten Ordner gegen seinen Prüfpunkt vergleichen, ohne Dokumenttext zu lesen.",
    ),
    "document-action-execution": (
        "Execute one verified rename or move for exactly one document, reversibly.",
        "Genau eine geprüfte Umbenennung oder Verschiebung für ein Dokument reversibel ausführen.",
    ),
    "document-action-plan": (
        "Derive a traceable file action plan from profile rules without changing anything.",
        "Aus Profilregeln einen nachvollziehbaren Dateiaktionsplan ableiten, ohne etwas zu ändern.",
    ),
    "document-bundle": (
        "Merge a selected folder into one new TXT or PDF, leaving the originals untouched.",
        "Einen gewählten Ordner zu einer neuen TXT- oder PDF-Datei bündeln, Originale bleiben.",
    ),
    "document-library": (
        "Search the local document index and summarize it as a topic dossier.",
        "Den lokalen Dokumentindex durchsuchen und als Themendossier zusammenfassen.",
    ),
    "document-package": (
        "Group a nested folder by file type into one ZIP with a verification manifest.",
        "Einen verschachtelten Ordner nach Dateityp als ZIP mit Prüfmanifest gruppieren.",
    ),
    "fcsa-dry-run": (
        "Create a sorting plan with the pinned FCSA component without moving anything.",
        "Mit der gepinnten FCSA-Komponente einen Sortierplan erstellen, ohne etwas zu verschieben.",
    ),
    "finance-import": (
        "Import provided bank statements cent-accurately into the local finance store.",
        "Bereitgestellte Kontoauszüge centgenau in den lokalen Finanzspeicher übernehmen.",
    ),
    "findcall": (
        "Prepare a bounded provider inquiry as a strictly local simulation.",
        "Eine begrenzte Anbieteranfrage als strikt lokale Simulation vorbereiten.",
    ),
    "folder-cleanup": (
        "Plan a whole folder and execute only the deliberately approved subset.",
        "Einen ganzen Ordner planen und nur die bewusst freigegebene Teilmenge ausführen.",
    ),
    "folder-routine": (
        "Run the due changes of one observed folder against its last checkpoint.",
        "Die fälligen Änderungen eines beobachteten Ordners gegen den letzten Prüfpunkt ausführen.",
    ),
    "health-dossier": (
        "Build an extractive, evidence-bound health dossier from selected local documents.",
        "Ein extraktives, belegorientiertes Gesundheitsdossier aus lokalen Dokumenten bauen.",
    ),
    "inventory-import": (
        "Add documented household observations to the local append-only inventory.",
        "Dokumentierte Haushaltsbeobachtungen in den lokalen Append-only-Bestand aufnehmen.",
    ),
    "legal-change-monitor": (
        "Compare two dated legal snapshots and flag topics as review candidates.",
        "Zwei datierte Rechtsstände vergleichen und Themen als Prüfkandidaten markieren.",
    ),
    "local-app": (
        "Explain and plan the local FolderHome application surface.",
        "Die lokale FolderHome-Anwendungsoberfläche erklären und planen.",
    ),
    "mail-connector": (
        "Place one prepared letter as a draft in the user's own mailbox; never send.",
        "Ein vorbereitetes Schreiben als Entwurf im eigenen Postfach ablegen; nie senden.",
    ),
    "master-agent": (
        "Explain and plan the master agent, its experts and its endpoint catalog.",
        "Den Master-Agenten, seine Fachrollen und seinen Endpunktkatalog erklären und planen.",
    ),
    "medication-intake": (
        "Adopt a provided medication plan and confirm one scheduled dose.",
        "Einen bereitgestellten Medikationsplan übernehmen und eine geplante Einnahme bestätigen.",
    ),
    "official-notice-understanding": (
        "Explain a social-law notice from its own labeled content, verifiably.",
        "Einen Sozialrechtsbescheid nachprüfbar aus seinem eigenen gelabelten Inhalt erklären.",
    ),
    "personal-notes": (
        "Store a human-written note as a new revision in the pinned local note store.",
        "Eine menschlich geschriebene Notiz als neue Revision im gepinnten Notizspeicher ablegen.",
    ),
    "routine-queue": (
        "Evaluate all activated watches read-only and surface cross-watch conflicts.",
        "Alle aktivierten Beobachtungen nur lesend auswerten und übergreifende Konflikte zeigen.",
    ),
    "scheduler-handoff": (
        "Prepare a portable scheduler artifact without registering any system task.",
        "Ein portables Scheduler-Artefakt vorbereiten, ohne eine Systemaufgabe zu registrieren.",
    ),
    "strands-agent": (
        "Plan a bounded run of the real Strands agent loop with synthetic data.",
        "Einen begrenzten Lauf der echten Strands-Agentenschleife mit synthetischen Daten planen.",
    ),
    "tax-workpaper": (
        "Turn confirmed receipts into a private, non-official tax workpaper.",
        "Bestätigte Belege in eine private, nicht amtliche Steuerarbeitsmappe überführen.",
    ),
}

_SIDE_EFFECT_CLASSES: tuple[tuple[str, str], ...] = (
    ("external.", "external_effect"),
    ("simulation.", "local_simulation"),
    ("state.", "local_state_write"),
    ("filesystem.", "local_file_write"),
    ("file.", "local_file_write"),
)


class CapabilityIndexError(RuntimeError):
    """Raised when the endpoint catalog and the index have drifted apart."""


@dataclass(frozen=True, slots=True)
class CapabilityIndexEntry:
    """One endpoint described exactly once for both model and reader."""

    workflow_id: str
    expert_id: str
    purpose_en: str
    purpose_de: str
    execution_mode: str
    implementation: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    side_effect_class: str
    side_effects: tuple[str, ...]
    approval_gates: tuple[str, ...]

    def to_dict(self, *, language: str = "en") -> dict[str, object]:
        if language not in {"de", "en"}:
            raise CapabilityIndexError("language muss de oder en sein.")
        return {
            "workflow_id": self.workflow_id,
            "expert_id": self.expert_id,
            "purpose": self.purpose_de if language == "de" else self.purpose_en,
            "execution_mode": self.execution_mode,
            "implementation": self.implementation,
            "required_inputs": list(self.required_inputs),
            "optional_inputs": list(self.optional_inputs),
            "side_effect_class": self.side_effect_class,
            "side_effects": list(self.side_effects),
            "approval_gates": list(self.approval_gates),
        }


def adapter_descriptors() -> dict[str, WorkflowAdapterDescriptor]:
    """Collect every typed adapter descriptor without instantiating an adapter."""

    descriptors: dict[str, WorkflowAdapterDescriptor] = {}
    for name in workflow_execution.__all__:
        if not name.endswith("WorkflowAdapter"):
            continue
        descriptor = getattr(getattr(workflow_execution, name), "descriptor", None)
        if not isinstance(descriptor, WorkflowAdapterDescriptor):
            continue
        if descriptor.workflow_id in descriptors:
            raise CapabilityIndexError(
                f"Zwei Adapter beanspruchen denselben Workflow: {descriptor.workflow_id}"
            )
        descriptors[descriptor.workflow_id] = descriptor
    return descriptors


def master_capability_index() -> tuple[CapabilityIndexEntry, ...]:
    """Join catalog, adapter schema and purpose into one ordered index."""

    descriptors = adapter_descriptors()
    entries: list[CapabilityIndexEntry] = []
    for capability in master_capability_catalog():
        purpose = _PURPOSES.get(capability.workflow_id)
        if purpose is None:
            raise CapabilityIndexError(
                f"Endpunkt besitzt keinen Indexzweck: {capability.workflow_id}"
            )
        descriptor = descriptors.get(capability.workflow_id)
        required, optional = _inputs(descriptor)
        entries.append(
            CapabilityIndexEntry(
                workflow_id=capability.workflow_id,
                expert_id=capability.expert_id,
                purpose_en=purpose[0],
                purpose_de=purpose[1],
                execution_mode=capability.execution_mode,
                implementation=_implementation(capability.execution_mode, descriptor),
                required_inputs=required,
                optional_inputs=optional,
                side_effect_class=_side_effect_class(capability.side_effects),
                side_effects=capability.side_effects,
                approval_gates=capability.approval_gates,
            )
        )
    return tuple(sorted(entries, key=lambda item: (item.expert_id, item.workflow_id)))


def capability_index_document(*, language: str = "en") -> dict[str, object]:
    """Return the machine-readable index used by the model and the generator."""

    return {
        "schema": SCHEMA,
        "language": language,
        "endpoint_count": len(master_capability_index()),
        "paths_disclosed": False,
        "entries": [
            item.to_dict(language=language) for item in master_capability_index()
        ],
    }


def capability_index_prompt_excerpt(*, language: str = "en") -> str:
    """Return the compact endpoint overview a model can hold in its prompt.

    The excerpt names the endpoint, its purpose and its effect class, and only
    counts the inputs. The exact request schema stays in `list_home_capabilities`,
    where the model can fetch it for the one endpoint it actually selected.
    """

    if language not in {"de", "en"}:
        raise CapabilityIndexError("language muss de oder en sein.")
    lines: list[str] = []
    current_expert = ""
    for entry in master_capability_index():
        if entry.expert_id != current_expert:
            current_expert = entry.expert_id
            lines.append(f"[{current_expert}]")
        purpose = entry.purpose_de if language == "de" else entry.purpose_en
        lines.append(
            f"- {entry.workflow_id}: {purpose} "
            f"[{len(entry.required_inputs)} inputs, effect: {entry.side_effect_class}]"
        )
    return "\n".join(lines)


def capability_index_markdown(*, language: str = "en") -> str:
    """Return the documentation table generated from the same single index."""

    if language == "de":
        header = (
            "| Endpunkt | Fachrolle | Zweck | Eingaben | Wirkung | Umsetzung |\n"
            "| --- | --- | --- | --- | --- | --- |"
        )
    else:
        header = (
            "| Endpoint | Expert | Purpose | Inputs | Effect | Implementation |\n"
            "| --- | --- | --- | --- | --- | --- |"
        )
    rows = [header]
    for entry in master_capability_index():
        inputs = ", ".join(f"`{item}`" for item in entry.required_inputs) or "—"
        if entry.optional_inputs:
            optional = ", ".join(f"`{item}?`" for item in entry.optional_inputs)
            inputs = f"{inputs}, {optional}"
        purpose = entry.purpose_de if language == "de" else entry.purpose_en
        rows.append(
            f"| `{entry.workflow_id}` | `{entry.expert_id}` | {purpose} | {inputs} "
            f"| `{entry.side_effect_class}` | `{entry.implementation}` |"
        )
    return "\n".join(rows)


def _inputs(
    descriptor: WorkflowAdapterDescriptor | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if descriptor is None or descriptor.request_schema is None:
        return (), ()
    schema = descriptor.request_schema
    raw_required = schema.get("required")
    raw_properties = schema.get("properties")
    if not isinstance(raw_required, list) or not isinstance(raw_properties, dict):
        raise CapabilityIndexError(
            f"Anfrageschema ist unvollständig: {descriptor.workflow_id}"
        )
    required = tuple(sorted(str(item) for item in raw_required))
    optional = tuple(sorted(set(map(str, raw_properties)).difference(required)))
    return required, optional


def _implementation(
    execution_mode: str,
    descriptor: WorkflowAdapterDescriptor | None,
) -> str:
    if descriptor is not None:
        return "typed_adapter_available"
    if execution_mode == "direct_read_only":
        return "direct_read_only_tool"
    if execution_mode == "planning_only":
        return "planning_only"
    return "no_typed_adapter"


def _side_effect_class(side_effects: tuple[str, ...]) -> str:
    if not side_effects:
        return "none"
    classes = set()
    for effect in side_effects:
        for prefix, label in _SIDE_EFFECT_CLASSES:
            if effect.startswith(prefix):
                classes.add(label)
                break
        else:
            raise CapabilityIndexError(f"Unbekannte Side-Effect-Klasse: {effect}")
    if "external_effect" in classes:
        return "external_effect"
    if "local_simulation" in classes:
        return "local_simulation"
    if "local_file_write" in classes and "local_state_write" in classes:
        return "local_state_and_file_write"
    return next(iter(classes))


__all__ = [
    "SCHEMA",
    "CapabilityIndexEntry",
    "CapabilityIndexError",
    "adapter_descriptors",
    "capability_index_document",
    "capability_index_markdown",
    "capability_index_prompt_excerpt",
    "master_capability_index",
]
