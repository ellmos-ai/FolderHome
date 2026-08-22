"""Non-executing, provider-neutral health report handoff preparation."""

from __future__ import annotations

import json
from hashlib import sha256

from folderhome.contracts.health import HealthDossierReport, HealthReportHandoff


def prepare_health_report_handoff(
    report: HealthDossierReport,
    *,
    provider_id: str,
    provider_revision: str,
    distribution_version: str,
    runtime_version: str,
    requested_format: str,
) -> HealthReportHandoff:
    """Describe a possible local render handoff without invoking the provider."""

    payload = json.dumps(
        report.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload_sha256 = sha256(payload).hexdigest()
    if distribution_version != runtime_version:
        status = "blocked"
        reason = (
            "Provideridentität ist uneinheitlich: Distribution "
            f"{distribution_version}, Runtime {runtime_version}."
        )
    else:
        status = "review_required"
        reason = (
            "Provideridentität stimmt überein; ein separater lokaler Adapter, "
            "eine Ausgabeprüfung und eine ausdrückliche Freigabe fehlen noch."
        )
    material = "\0".join(
        (
            "folderhome.health_handoff.v1",
            report.report_id,
            provider_id,
            provider_revision,
            requested_format,
            payload_sha256,
            distribution_version,
            runtime_version,
        )
    )
    return HealthReportHandoff(
        handoff_id=f"health_handoff_{sha256(material.encode('utf-8')).hexdigest()}",
        report_id=report.report_id,
        provider_id=provider_id,
        provider_revision=provider_revision,
        requested_format=requested_format,
        payload_sha256=payload_sha256,
        status=status,
        reason=reason,
    )
