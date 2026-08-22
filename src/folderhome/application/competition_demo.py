"""Self-contained, synthetic and deterministic competition evidence run."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from folderhome.application.local_app import LocalApplication
from folderhome.application.profile_rules import load_profile_configuration
from folderhome.application.strands_agent import (
    StrandsAgentSettings,
    run_folderhome_agent,
)
from folderhome.bridges.knowledge_digest import KnowledgeDigestSearchHit
from folderhome.capabilities.document_transform import (
    DocumentTransformCapabilityError,
    publish_new_bytes,
)
from folderhome.contracts import LocalAppSettings
from folderhome.contracts.strands_agent import FolderHomeAgentReport

_PROFILE_DIR = Path(__file__).resolve().parents[1] / "demo_data" / "profiles"


class CompetitionDemoError(RuntimeError):
    """Raised when a synthetic demo is unsafe, incomplete, or would overwrite output."""


@dataclass(frozen=True, slots=True)
class CompetitionDemoScenario:
    scenario_id: str
    status: str
    tool_name: str
    response_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "status": self.status,
            "tool_name": self.tool_name,
            "response_sha256": self.response_sha256,
        }


@dataclass(frozen=True, slots=True)
class CompetitionDemoReport:
    status: str
    framework: str
    framework_version: str
    scenarios: tuple[CompetitionDemoScenario, ...]
    artifact_sha256: dict[str, str]
    network_used: bool = False
    side_effects: tuple[str, ...] = ()

    SCHEMA = "folderhome.competition-demo-report.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.SCHEMA,
            "status": self.status,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "scenarios": [item.to_dict() for item in self.scenarios],
            "artifact_sha256": dict(sorted(self.artifact_sha256.items())),
            "network_used": self.network_used,
            "side_effects": list(self.side_effects),
        }


class _SyntheticDemoSearcher:
    _HITS = (
        KnowledgeDigestSearchHit(
            source="document",
            filename="Krankenversicherung-2026.txt",
            file_type="txt",
            snippet=(
                "Fundstelle für >>>Krankenversicherung<<<: synthetischer Tarifhinweis, "
                "Kontakt und Gültigkeit ab 2026."
            ),
            relevance=-2.0,
            word_count=31,
        ),
        KnowledgeDigestSearchHit(
            source="document",
            filename="Arztbericht-Hausarzt-2026.txt",
            file_type="txt",
            snippet=(
                "Synthetischer Arztbericht mit Hinweis zur >>>Krankenversicherung<<< "
                "und einer kontrollbedürftigen Fundstelle."
            ),
            relevance=-1.0,
            word_count=47,
        ),
    )

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[KnowledgeDigestSearchHit, ...]:
        terms = {
            token.casefold().strip(".,:;!?()")
            for token in query.replace("-", " ").split()
            if len(token.strip(".,:;!?()")) >= 5
        }
        matches = tuple(
            hit
            for hit in self._HITS
            if not terms
            or any(
                term in f"{hit.filename} {hit.snippet}".casefold()
                for term in terms
            )
        )
        return matches[:limit]


def run_competition_demo(
    output_dir: Path,
    *,
    allow_output_write: bool,
) -> CompetitionDemoReport:
    """Run two real Strands loops against synthetic local data and publish evidence."""

    if not allow_output_write:
        raise CompetitionDemoError("Ausgabefreigabe für Wettbewerbsdemo fehlt.")
    targets = {
        "01-document-search.json": output_dir / "01-document-search.json",
        "02-theme-dossier.json": output_dir / "02-theme-dossier.json",
        "DEMO.md": output_dir / "DEMO.md",
        "EVIDENCE.json": output_dir / "EVIDENCE.json",
    }
    existing = [path for path in targets.values() if path.exists()]
    if existing:
        raise CompetitionDemoError(f"Demoausgabe existiert bereits: {existing[0]}")

    application = LocalApplication(
        settings=LocalAppSettings(
            host="127.0.0.1",
            port=8765,
            profiles_dir=_PROFILE_DIR,
            state_dir=output_dir / ".fixture-state",
            max_query_limit=10,
        ),
        profiles=load_profile_configuration(_PROFILE_DIR),
        searcher=_SyntheticDemoSearcher(),
        session_token="phase36-competition-fixture-token-with-sufficient-entropy",
    )
    settings = StrandsAgentSettings(model_provider="fixture")
    search = run_folderhome_agent(
        application=application,
        prompt=(
            "Ich suche nach einem Dokument, in dem Informationen über meine "
            "Krankenversicherung stehen."
        ),
        profile_id="lukas",
        settings=settings,
    )
    dossier = run_folderhome_agent(
        application=application,
        prompt="Gib mir alles, was in meinen Dokumenten zur Krankenversicherung steht.",
        profile_id="lukas",
        settings=settings,
    )
    scenarios = (
        _scenario("document-search", search, "search_home_documents"),
        _scenario("theme-dossier", dossier, "build_home_theme_dossier"),
    )
    scenario_bytes = {
        "01-document-search.json": _pretty_json(search.to_dict()),
        "02-theme-dossier.json": _pretty_json(dossier.to_dict()),
    }
    markdown = _demo_markdown(search, dossier).encode("utf-8")
    artifact_bytes = {**scenario_bytes, "DEMO.md": markdown}
    artifact_sha256 = {
        name: sha256(payload).hexdigest() for name, payload in artifact_bytes.items()
    }
    evidence = {
        "schema": "folderhome.competition-demo-evidence.v1",
        "status": "passed",
        "fixture_only": True,
        "checks": {
            "strands_agent_loop": True,
            "sequential_tool_execution": True,
            "external_network_used": False,
            "sensitive_cloud_data_authorized": False,
            "side_effects_performed": False,
            "real_personal_data_used": False,
            "organizational_profiles_are_authorization_boundaries": False,
        },
        "scenarios": [item.to_dict() for item in scenarios],
        "artifact_sha256": dict(sorted(artifact_sha256.items())),
    }
    payloads = {**artifact_bytes, "EVIDENCE.json": _pretty_json(evidence)}
    created_output_dir = not output_dir.exists()
    published: list[Path] = []
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, path in targets.items():
            publish_new_bytes(path, payloads[name])
            published.append(path)
    except (OSError, DocumentTransformCapabilityError) as exc:
        rollback_errors = []
        for path in reversed(published):
            try:
                path.unlink()
            except OSError as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        if created_output_dir:
            try:
                output_dir.rmdir()
            except OSError as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        suffix = f" Rücknahmefehler: {'; '.join(rollback_errors)}" if rollback_errors else ""
        raise CompetitionDemoError(f"Demoausgabe fehlgeschlagen: {exc}.{suffix}") from exc
    return CompetitionDemoReport(
        status="passed",
        framework=search.framework,
        framework_version=search.framework_version,
        scenarios=scenarios,
        artifact_sha256={
            **artifact_sha256,
            "EVIDENCE.json": sha256(payloads["EVIDENCE.json"]).hexdigest(),
        },
    )


def _scenario(
    scenario_id: str,
    report: FolderHomeAgentReport,
    expected_tool: str,
) -> CompetitionDemoScenario:
    names = [item.tool_name for item in report.tool_events]
    status = "passed" if report.stop_reason == "end_turn" and names == [expected_tool] else "failed"
    if status != "passed":
        raise CompetitionDemoError(f"Demoszenario ist fehlgeschlagen: {scenario_id}")
    return CompetitionDemoScenario(
        scenario_id=scenario_id,
        status=status,
        tool_name=expected_tool,
        response_sha256=sha256(report.response_text.encode("utf-8")).hexdigest(),
    )


def _demo_markdown(
    search: FolderHomeAgentReport,
    dossier: FolderHomeAgentReport,
) -> str:
    return (
        "# FolderHome — Synthetische Wettbewerbsdemo\n\n"
        "> Vollständig synthetisch: keine echten personenbezogenen Daten, kein Netzwerk "
        "und keine Außenwirkung.\n\n"
        "## 1. Dokumentensuche über den Strands-Agenten\n\n"
        f"{search.response_text}\n\n"
        "## 2. Themendossier über denselben Agentenloop\n\n"
        f"{dossier.response_text}\n\n"
        "## Nachweisgrenzen\n\n"
        "Der Fixture-Modelladapter macht Toolwahl und Antwort reproduzierbar. Der gleiche "
        "Strands-Agent kann nach getrennten Netzwerk- und Datenweitergabefreigaben mit "
        "Amazon Bedrock laufen; dieser Demo-Lauf verwendet weder AWS-Zugangsdaten noch "
        "einen Cloudaufruf.\n"
    )


def _pretty_json(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


__all__ = [
    "CompetitionDemoError",
    "CompetitionDemoReport",
    "run_competition_demo",
]
