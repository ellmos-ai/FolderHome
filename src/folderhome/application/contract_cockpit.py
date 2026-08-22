"""Compose a read-only household contract cockpit from existing capabilities."""

from __future__ import annotations

import json
import re
from hashlib import sha256

from folderhome.application.version_analysis import DocumentVersionAnalysis
from folderhome.contracts import (
    CalendarEventRecord,
    ContactRecord,
    ContractCockpitIssue,
    ContractCockpitReport,
    ContractCockpitRequest,
    FinanceCoverage,
    RecurringCostReport,
)

_WHITESPACE = re.compile(r"\s+")


def build_contract_cockpit(
    request: ContractCockpitRequest,
    *,
    version_analysis: DocumentVersionAnalysis,
    contacts: tuple[ContactRecord, ...],
    recurring_report: RecurringCostReport,
    calendar_events: tuple[CalendarEventRecord, ...],
    finance_coverages: tuple[FinanceCoverage, ...],
    component_revisions: dict[str, str],
) -> ContractCockpitReport:
    """Join only explicitly mapped evidence; never mutate any backing component."""

    if version_analysis.original_query != request.document_query:
        raise ValueError("Versionsanalyse gehört nicht zur angegebenen Dokumentanfrage.")
    if recurring_report.profile_id != request.profile_id:
        raise ValueError("Kostenbericht gehört nicht zum angegebenen Profil.")
    if recurring_report.as_of != request.as_of:
        raise ValueError("Kostenbericht und Cockpit verwenden verschiedene Stichtage.")

    matching_contacts = tuple(
        sorted(
            (
                item
                for item in contacts
                if item.profile_id.casefold() == request.profile_id.casefold()
                and item.area.casefold() == request.area.casefold()
                and _contains(item.object_ref or "", request.object_ref)
            ),
            key=lambda item: (item.effective_date, item.contact_id),
            reverse=True,
        )
    )
    current_contacts = tuple(item for item in matching_contacts if item.status == "active")
    prior_contacts = tuple(
        item for item in matching_contacts if item.status == "deletion_candidate"
    )

    counterparty_terms = tuple(_normalize(value) for value in request.counterparty_terms)
    account_refs = {value.casefold() for value in request.account_refs}
    recurring_costs = tuple(
        sorted(
            (
                item
                for item in recurring_report.candidates
                if item.profile_id.casefold() == request.profile_id.casefold()
                and (not account_refs or item.account_ref.casefold() in account_refs)
                and counterparty_terms
                and any(term in _normalize(item.counterparty) for term in counterparty_terms)
            ),
            key=lambda item: item.candidate_id,
        )
    )

    calendar_terms = tuple(_normalize(value) for value in request.calendar_terms)
    matching_events = tuple(
        sorted(
            (
                item
                for item in calendar_events
                if item.profile_id.casefold() == request.profile_id.casefold()
                and item.area.casefold() == request.area.casefold()
                and item.event_date >= request.as_of
                and calendar_terms
                and any(
                    term in _normalize(f"{item.title} {item.location or ''}")
                    for term in calendar_terms
                )
            ),
            key=lambda item: (item.event_date, item.start_time or "", item.event_id),
        )
    )
    matching_coverages = tuple(
        sorted(
            (
                item
                for item in finance_coverages
                if item.account_ref.casefold() in account_refs
            ),
            key=lambda item: item.account_ref.casefold(),
        )
    )

    issues: list[ContractCockpitIssue] = []
    if not current_contacts:
        issues.append(
            ContractCockpitIssue(
                "contacts",
                "not_available",
                "Keine passende Evidenz für einen aktuell aktiven Kontakt.",
            )
        )
    elif len(current_contacts) > 1:
        issues.append(
            ContractCockpitIssue(
                "contacts",
                "ambiguous",
                "Mehrere passende aktive Kontakte; keine automatische Auswahl.",
            )
        )
    if not recurring_costs:
        issues.append(
            ContractCockpitIssue(
                "costs",
                "not_available",
                "Keine passende Evidenz für wiederkehrende Kosten.",
            )
        )
    if not matching_events:
        issues.append(
            ContractCockpitIssue(
                "calendar",
                "not_available",
                "Keine passende Evidenz für einen zukünftigen Termin.",
            )
        )
    if request.account_refs and not matching_coverages:
        issues.append(
            ContractCockpitIssue(
                "finance_coverage",
                "not_available",
                "Keine passende Evidenz zur Kontoauszugsabdeckung.",
            )
        )

    archive_proposals = (
        version_analysis.archive_proposals if request.archive_older_versions else ()
    )
    report_material = {
        "request_id": request.request_id,
        "family_id": version_analysis.family.family_id,
        "latest_document_id": version_analysis.family.latest.document.document_id,
        "archive_ids": [item.document_id for item in archive_proposals],
        "contact_ids": [item.contact_id for item in matching_contacts],
        "cost_ids": [item.candidate_id for item in recurring_costs],
        "event_ids": [item.event_id for item in matching_events],
        "coverages": [item.to_dict() for item in matching_coverages],
        "component_revisions": dict(sorted(component_revisions.items())),
    }
    report_id = f"contract_cockpit_{_json_hash(report_material)}"
    markdown = _render_markdown(
        request=request,
        version_analysis=version_analysis,
        archive_proposals=archive_proposals,
        current_contacts=current_contacts,
        prior_contacts=prior_contacts,
        recurring_costs=recurring_costs,
        calendar_events=matching_events,
        finance_coverages=matching_coverages,
        issues=tuple(issues),
    )
    return ContractCockpitReport(
        report_id=report_id,
        request=request,
        latest_version=version_analysis.family.latest,
        older_versions=version_analysis.family.versions[1:],
        archive_proposals=archive_proposals,
        current_contacts=current_contacts,
        prior_contacts=prior_contacts,
        recurring_costs=recurring_costs,
        calendar_events=matching_events,
        finance_coverages=matching_coverages,
        component_revisions=dict(component_revisions),
        component_issues=tuple(issues),
        markdown=markdown,
    )


def _render_markdown(
    *,
    request: ContractCockpitRequest,
    version_analysis: DocumentVersionAnalysis,
    archive_proposals,
    current_contacts: tuple[ContactRecord, ...],
    prior_contacts: tuple[ContactRecord, ...],
    recurring_costs,
    calendar_events: tuple[CalendarEventRecord, ...],
    finance_coverages: tuple[FinanceCoverage, ...],
    issues: tuple[ContractCockpitIssue, ...],
) -> str:
    latest = version_analysis.family.latest
    lines = [
        f"# Vertragscockpit: {_safe(request.display_name)}",
        "",
        f"**Profil:** {_safe(request.profile_id)}  ",
        f"**Stichtag:** {request.as_of}  ",
        f"**Vertragsobjekt:** {_safe(request.object_ref)}",
        "",
        "> Read-only und evidenzgebunden. Ein Vertragsstatus wird nicht bewiesen; ",
        "> Archivierung, Kontaktwechsel, Zahlung und Kalenderaktion werden nicht ausgeführt.",
        "",
        "## Aktuelle belegte Fassung",
        "",
        f"- `{_safe_code(latest.document.filename)}` — Stand {latest.version_date}",
        f"- Datumsbasis: `{latest.date_basis.value}` ({latest.date_confidence.value})",
        f"- Dokument-ID: `{latest.document.document_id}`",
        f"- Quellhash: `{latest.document.source_sha256}`",
        "",
        "## Ältere Fassungen und Archivierung",
        "",
    ]
    if len(version_analysis.family.versions) == 1:
        lines.append("Keine ältere belegte Fassung gefunden.")
    for version in version_analysis.family.versions[1:]:
        lines.append(
            f"- `{_safe_code(version.document.filename)}` — Stand {version.version_date}; "
            "bleibt unverändert."
        )
    if request.archive_older_versions:
        if archive_proposals:
            lines.append("- Archivierung ist konfiguriert, aber nur als ungefreigter Plan:")
            for proposal in archive_proposals:
                lines.append(
                    f"  - `{_safe_code(proposal.source_path.name)}` → "
                    f"`{_safe_code(str(proposal.target_path))}`"
                )
        else:
            lines.append("- Archivierung ist konfiguriert; es gibt keinen Kandidaten.")
    else:
        lines.append("- Automatische Archivierungsplanung ist für dieses Objekt deaktiviert.")

    lines.extend(("", "## Zuständige Kontakte", ""))
    if not current_contacts:
        lines.append("Keine passende Evidenz für einen aktuell aktiven Kontakt.")
    for contact in current_contacts:
        identity = contact.contact_name or contact.organization
        channels = " · ".join(value for value in (contact.email, contact.phone) if value)
        lines.append(
            f"- **{_safe(identity)}**, {_safe(contact.organization)}"
            f" — {_safe(channels)} · gültig ab {contact.effective_date}"
        )
        lines.append(f"  Quelle: `{contact.source_document_id}`")
    for contact in prior_contacts:
        lines.append(
            f"- Früherer Kontakt, nur zur Prüfung vorgemerkt: "
            f"{_safe(contact.contact_name or contact.organization)} ({contact.effective_date})"
        )

    lines.extend(("", "## Belegte Kostenkandidaten", ""))
    if not recurring_costs:
        lines.append("Keine passende Evidenz für wiederkehrende Kosten.")
    for cost in recurring_costs:
        lines.append(
            f"- {_safe(cost.counterparty)}: {_eur(cost.monthly_cost_cents)} monatlich, "
            f"{_eur(cost.annualized_cost_cents)} hochgerechnet jährlich "
            f"(`{cost.status}`)"
        )
        lines.append(
            f"  Belegte Buchungen: {cost.first_booking_date} bis {cost.last_booking_date}; "
            f"IDs: {', '.join(f'`{item}`' for item in cost.transaction_ids)}"
        )

    lines.extend(("", "## Zukünftige belegte Termine", ""))
    if not calendar_events:
        lines.append("Keine passende Evidenz für einen zukünftigen Termin.")
    for event in calendar_events:
        when = f"{event.event_date} {event.start_time or ''}".strip()
        lines.append(f"- {when} — {_safe(event.title)} · `{event.source_document_id}`")

    lines.extend(("", "## Kontoauszugsabdeckung", ""))
    if request.account_refs and not finance_coverages:
        lines.append("Keine passende Evidenz zur Kontoauszugsabdeckung.")
    if not request.account_refs:
        lines.append("Für dieses Vertragsobjekt wurde kein Konto zugeordnet.")
    for coverage in finance_coverages:
        lines.append(
            f"- `{_safe_code(coverage.account_ref)}`: "
            f"{'vollständig' if coverage.complete else 'lückenhaft'} für "
            f"{coverage.requested_range.start_date} bis {coverage.requested_range.end_date}"
        )
        for gap in coverage.gaps:
            lines.append(f"  - Lücke: {gap.start_date} bis {gap.end_date}")

    lines.extend(("", "## Offene Evidenzgrenzen", ""))
    if not issues:
        lines.append("Keine zusätzliche Komponentenlücke erkannt.")
    for issue in issues:
        lines.append(f"- `{issue.component}` / `{issue.status}`: {_safe(issue.message)}")
    return "\n".join(lines).rstrip() + "\n"


def _normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().casefold()


def _contains(value: str, term: str) -> bool:
    return _normalize(term) in _normalize(value)


def _safe(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().replace("`", "'").replace("*", "\\*")


def _safe_code(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().replace("`", "'")


def _eur(cents: int) -> str:
    euros, remainder = divmod(cents, 100)
    return f"{euros},{remainder:02d} EUR"


def _json_hash(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(material).hexdigest()
