"""Contracts for a read-only, cross-capability contract cockpit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from hashlib import sha256

from folderhome.contracts.calendar import CalendarEventRecord
from folderhome.contracts.contacts import ContactRecord
from folderhome.contracts.finance import FinanceCoverage, RecurringCostCandidate
from folderhome.contracts.versions import ArchiveProposal, DocumentVersion

_REPORT_ID = re.compile(r"contract_cockpit_[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class ContractCockpitRequest:
    """Explicit join instructions for one household contract subject."""

    profile_id: str
    area: str
    display_name: str
    document_query: str
    object_ref: str
    counterparty_terms: tuple[str, ...]
    calendar_terms: tuple[str, ...]
    account_refs: tuple[str, ...]
    coverage_start: str
    as_of: str
    archive_older_versions: bool

    SCHEMA = "folderhome.contract-cockpit-request.v1"

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "area",
            "display_name",
            "document_query",
            "object_ref",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} darf nicht leer sein.")
        start = date.fromisoformat(self.coverage_start)
        end = date.fromisoformat(self.as_of)
        if start > end:
            raise ValueError("coverage_start darf nicht nach as_of liegen.")
        for field_name in ("counterparty_terms", "calendar_terms", "account_refs"):
            values = getattr(self, field_name)
            if any(not value.strip() for value in values) or len(values) != len(set(values)):
                raise ValueError(f"{field_name} muss eindeutige, nichtleere Werte enthalten.")

    @property
    def request_id(self) -> str:
        material = "\0".join(
            (
                "folderhome.contract-cockpit-request.v1",
                self.profile_id.casefold(),
                self.area.casefold(),
                self.display_name.casefold(),
                self.document_query.casefold(),
                self.object_ref.casefold(),
                *sorted(value.casefold() for value in self.counterparty_terms),
                *sorted(value.casefold() for value in self.calendar_terms),
                *sorted(value.casefold() for value in self.account_refs),
                self.coverage_start,
                self.as_of,
                str(self.archive_older_versions),
            )
        )
        return f"contract_request_{sha256(material.encode('utf-8')).hexdigest()}"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "area": self.area,
            "display_name": self.display_name,
            "document_query": self.document_query,
            "object_ref": self.object_ref,
            "counterparty_terms": list(self.counterparty_terms),
            "calendar_terms": list(self.calendar_terms),
            "account_refs": list(self.account_refs),
            "coverage_start": self.coverage_start,
            "as_of": self.as_of,
            "archive_older_versions": self.archive_older_versions,
        }


@dataclass(frozen=True, slots=True)
class ContractCockpitIssue:
    """One visible absence, ambiguity, or evidence limitation."""

    component: str
    status: str
    message: str

    def __post_init__(self) -> None:
        if not self.component or self.status not in {
            "not_available",
            "ambiguous",
            "incomplete",
        }:
            raise ValueError("Cockpit-Hinweis benötigt Komponente und gültigen Status.")
        if not self.message:
            raise ValueError("Cockpit-Hinweis benötigt eine Begründung.")

    def to_dict(self) -> dict[str, str]:
        return {
            "component": self.component,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ContractCockpitReport:
    """Read-only synthesis of existing document, contact, cost, and event evidence."""

    report_id: str
    request: ContractCockpitRequest
    latest_version: DocumentVersion
    older_versions: tuple[DocumentVersion, ...]
    archive_proposals: tuple[ArchiveProposal, ...]
    current_contacts: tuple[ContactRecord, ...]
    prior_contacts: tuple[ContactRecord, ...]
    recurring_costs: tuple[RecurringCostCandidate, ...]
    calendar_events: tuple[CalendarEventRecord, ...]
    finance_coverages: tuple[FinanceCoverage, ...]
    component_revisions: dict[str, str]
    component_issues: tuple[ContractCockpitIssue, ...]
    markdown: str

    SCHEMA = "folderhome.contract-cockpit.v1"

    def __post_init__(self) -> None:
        if _REPORT_ID.fullmatch(self.report_id) is None:
            raise ValueError("report_id muss contract_cockpit_<sha256> verwenden.")
        if any(not key or not value for key, value in self.component_revisions.items()):
            raise ValueError("Komponentenrevisionen benötigen Schlüssel und Wert.")

    @property
    def read_only(self) -> bool:
        return True

    @property
    def contract_status_proven(self) -> bool:
        return False

    @property
    def automatic_archive_executed(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "report_id": self.report_id,
            "request": self.request.to_dict(),
            "latest_version": self.latest_version.to_dict(),
            "older_versions": [item.to_dict() for item in self.older_versions],
            "archive_proposals": [item.to_dict() for item in self.archive_proposals],
            "current_contacts": [item.to_dict() for item in self.current_contacts],
            "prior_contacts": [item.to_dict() for item in self.prior_contacts],
            "recurring_costs": [item.to_dict() for item in self.recurring_costs],
            "calendar_events": [item.to_dict() for item in self.calendar_events],
            "finance_coverages": [item.to_dict() for item in self.finance_coverages],
            "component_revisions": dict(sorted(self.component_revisions.items())),
            "component_issues": [item.to_dict() for item in self.component_issues],
            "markdown": self.markdown,
            "read_only": self.read_only,
            "contract_status_proven": self.contract_status_proven,
            "automatic_archive_executed": self.automatic_archive_executed,
            "automatic_contact_change": False,
            "automatic_calendar_action": False,
            "payment_or_bank_access": False,
        }

    def to_export_dict(self) -> dict[str, object]:
        """Export private evidence without internal filesystem locator fields.

        The cockpit export itself is not an anonymizer: names, contact details
        and user-supplied text remain private. The separate remote-model boundary
        pseudonymizes model traffic when enabled. Internal ``to_dict`` and typed
        records retain the paths needed for plan hashing and source revalidation.
        """
        return {
            "schema": "folderhome.contract-cockpit-export.v1",
            "source_schema": self.SCHEMA,
            "report_id": self.report_id,
            "request": self.request.to_dict(),
            "latest_version": _export_version(self.latest_version),
            "older_versions": [_export_version(item) for item in self.older_versions],
            "archive_proposals": [
                {
                    "document_id": item.document_id,
                    "retained_document_id": item.retained_document_id,
                    "source_filename": item.source_path.name,
                    "target_filename": item.target_path.name,
                    "target_role": "configured_archive",
                    "provider_id": item.provider_id,
                    "capability_id": item.capability_id,
                    "action": item.action,
                    "collision_policy": item.collision_policy,
                    "status": item.status,
                    "gate": {"required": item.gate_required, "granted": item.gate_granted},
                    "undo_action": item.undo_action,
                }
                for item in self.archive_proposals
            ],
            "current_contacts": [_export_contact(item) for item in self.current_contacts],
            "prior_contacts": [_export_contact(item) for item in self.prior_contacts],
            "recurring_costs": [item.to_dict() for item in self.recurring_costs],
            "calendar_events": [_export_event(item) for item in self.calendar_events],
            "finance_coverages": [item.to_dict() for item in self.finance_coverages],
            "component_revisions": dict(sorted(self.component_revisions.items())),
            "component_issues": [item.to_dict() for item in self.component_issues],
            "markdown": self.markdown,
            "read_only": self.read_only,
            "contract_status_proven": self.contract_status_proven,
            "automatic_archive_executed": self.automatic_archive_executed,
            "automatic_contact_change": False,
            "automatic_calendar_action": False,
            "payment_or_bank_access": False,
        }


def _export_version(version: DocumentVersion) -> dict[str, object]:
    document = version.document
    return {
        "family_id": version.family_id,
        "family_label": version.family_label,
        "document": {
            "document_id": document.document_id,
            "filename": document.source_path.name,
            "media_type": document.media_type,
            "source_sha256": document.source_sha256,
            "size_bytes": document.size_bytes,
            "modified_at": document.modified_at,
            "content_format": document.content_format.value,
            "extraction": {
                "provider": document.extraction_provider,
                "method": document.extraction_method,
            },
            "privacy": {
                "status": document.privacy_status.value,
                "summary": document.privacy_summary,
            },
            "index": {
                "status": document.index_status.value,
                "provider": document.index_provider,
            },
        },
        "version_date": version.version_date,
        "date_basis": version.date_basis.value,
        "date_confidence": version.date_confidence.value,
        "date_evidence": version.date_evidence,
    }


def _export_contact(contact: ContactRecord) -> dict[str, object]:
    # Explicit fields prevent newly added internal locators from leaking by default.
    return {
        key: getattr(contact, key)
        for key in (
            "contact_id", "candidate_id", "profile_id", "area", "organization",
            "contact_name", "role", "purpose", "object_ref", "email", "phone",
            "effective_date", "source_document_id", "source_sha256", "status",
            "created_at", "updated_at",
        )
    }


def _export_event(event: CalendarEventRecord) -> dict[str, object]:
    return {
        key: getattr(event, key)
        for key in (
            "event_id", "event_uid", "candidate_id", "profile_id", "area", "title",
            "event_date", "start_time", "end_time", "timezone", "location",
            "source_document_id", "source_sha256", "status", "created_at", "updated_at",
        )
    }
