# COMPETITION_CODE_MAP — Origin of the Competition Code

**English** | [Deutsch](./COMPETITION_CODE_MAP.de.md)

**Version:** 0.38  
**Updated:** 2026-09-05  
**Reason:** Local Ollama provider and MCP server classified  
**Purpose:** Assigns each relevant repository area to an origin class.

> If you discover outdated passages or references, correct this file and the associated manifests. The Git history remains the technical evidence.

| Area | Class | Meaning |
|---|---|---|
| `src/folderhome/` | `NEW_CORE` | Core newly built during the competition period |
| `src/folderhome/bridges/` | `NEW_BRIDGE` | Installable connection code to disclosed components |
| `bridges/` | `NEW_BRIDGE` | Documented provider boundaries of the new connection code |
| `skills/` | `NEW_CORE` | New agent‑usable FolderHome skills |
| `manifests/` | `NEW_CORE` | New machine‑readable component and stack contracts |
| `reused/` | `REUSED_UNCHANGED` / `REUSED_DESIGN_REFERENCE` | Pinned runtime references or clearly marked local design sources, no copied source code |
| `tests/` | `NEW_CORE` | New contract, security, and integration tests |
| `site/`, `.github/workflows/pages.yml` | `NEW_CORE` | New transparent static showcase and its bounded publication workflow |
| `deploy/agentcore/` | `NEW_CORE` | New optional synthetic-only AgentCore HTTP container contract |
| `docs/submission/ARCHITECTURE_DIAGRAM.*` | `NEW_CORE` | New architecture evidence for the delivered competition state |
| `examples/synthetic/`, `examples/fcsa/`, `examples/documents/`, `examples/profiles/`, `examples/inventory/`, `examples/medication/`, `examples/health/`, `examples/contracts/`, `examples/correspondence/`, `examples/artifacts/`, `examples/mail/`, `examples/calendar/`, `examples/notes/`, `examples/tax/`, `examples/briefing/`, `examples/notices/`, `examples/benefits/`, `examples/legal/`, `examples/competition/` | `GENERATED_OR_TEST_DATA` | Synthetic demo/test data, reproducible agent evidence, and marked official handoff metadata without copied portal code |
| `_tools/`, Root-Projektdokumente | `REUSED_UNCHANGED` | Instantiated from the local `project-docs` template and adapted per project |

## Competition Boundary

- FCSA, HungryCall, and Ringedingeding remain separate repositories.  
- UpToday remains a local, revision‑accurate documented design reference. The existing inventory engine is not imported and no source code is copied.  
- The public health skill remains a revision‑accurate design reference for organizational and security boundaries; it stores nothing itself in the FolderHome run.  
- FolderHome does not copy any source code from these projects. New bridges import only precisely pinned, clean checkouts via their public API or a documented, read‑only schema seam.  
- FCSA remains dry‑run‑only. doc‑services reads sources; KnowledgeDigest may write to a specified FolderHome state folder only after an explicit gate. Source documents remain unchanged.  
- The new profile action planner is encapsulated under `src/folderhome/`. FCSA confirms only its own move/trash capabilities; a still‑missing conversion provider is not emitted as a reuse.  
- The new transformation core resides under `src/folderhome/capabilities/document_transform/` and is `NEW_CORE`. pypdf, Pillow, and ReportLab are used only as optional libraries; their source code is not copied into the repository.  
- The new correspondence core is located under `contracts.correspondence` and `application.correspondence` and is `NEW_CORE`. report‑forge is inventoried only as a pinned, currently blocked provider reference; no source code is copied and no runtime is loaded.  
- Artifact plan, design set, and SVG business card under `contracts.artifact_studio` and `application.artifact_studio` are `NEW_CORE`. ai‑media‑editor remains a revision‑bound `REUSED_UNCHANGED` reference; the specialized office skills are not copied into this repository.  
- Mail contracts, ingest/draft logic, synthetic gateway, and ledger under `contracts.mail`, `application.mail_connector`, and `capabilities.mail_gateway` are `NEW_CORE`. The four doc‑bricks mail projects remain unchanged, revision‑accurate references; no source code was copied nor a modified checkout loaded.  
- Calendar connector contracts, routing, and synthetic gateway under `contracts.calendar_connectors`, `application.calendar_connectors`, and `capabilities.calendar_connector_gateway` are `NEW_CORE`. UpToday, Routinika, and the Google‑Calendar skill remain unchanged or hash‑bound references. The existing Phase‑17 handoff is referenced, not duplicated.  
- Personal note contracts, leadership, and approval logic under `contracts.personal_notes`, `application.personal_notes`, and `capabilities.personal_note_guide` are `NEW_CORE`. `bridges.llm_note` is `NEW_BRIDGE`; the provider remains unchanged on the manifest revision and its source code is not copied. The bridge uses its public Write‑API and a tightly limited read‑only schema seam.  
- Tax receipt, approval, and export contracts under `contracts.tax` and the orchestration under `application.tax_workpaper` are `NEW_CORE`. `bridges.tax_assistant` is `NEW_BRIDGE`; the provider remains unchanged on the manifest revision. FolderHome uses its public Write and Export APIs, separates stores per profile, and does not add tax advice or portal transmission.  
- Weather, news, briefing, render, and desktop contracts under `contracts.daily_briefing` and the orchestration under `application.daily_briefing` are `NEW_CORE`. BACH remains `REUSED_DESIGN_REFERENCE`: the monolithic code is neither copied nor loaded. Live connectors and scheduler registration are not emitted as competition code.  
- Notice, evidence, conflict, and output contracts under `contracts.official_notices` and the orchestration under `application.official_notices` are `NEW_CORE`. law‑checker remains `REUSED_DESIGN_REFERENCE`: the historic, externally modified checkout is neither copied nor loaded. Phase 31 performs no legal review or statutory deadline calculation.  
- Administrative draft, fact, approval, and output contracts under `contracts.administrative_drafts` and the connection under `application.administrative_drafts` are `NEW_CORE`. Phase 24 is reused via its public correspondence API; no letter generator is copied or duplicated. Legal review and dispatch are not part of this phase's competition code.  
- Benefit profile, source, routing, catalog, and report contracts under `contracts.benefit_screening` and the evaluation under `application.benefit_screening` are `NEW_CORE`. Social benefit finder, KiZ‑Lodge, and housing‑benefit‑plus calculator are external official `REUSED_DESIGN_REFERENCE` handoffs; no portal code is copied, loaded, or invoked automatically.  
- Legal source, interest, amendment, candidate, and output contracts under `contracts.legal_change_monitor` and the local comparison under `application.legal_change_monitor` are `NEW_CORE`. `bridges.law_checker` is `NEW_BRIDGE`; the provider remains unchanged on the manifest revision. FolderHome reads only identity, registry, and source metadata and does not claim a legal‑review API. The files under `examples/legal/` are clearly isolated synthetic fixtures.  
- Local app contracts, handler allowlist, and HTTP adapters under `contracts.local_app`, `application.local_app`, and `local_server` and the assets under `web_ui/` are `NEW_CORE`. They use only the Python standard library and existing FolderHome services; no web framework, frontend package, or external source code is embedded.  
- Strands contracts, agent adapters, and competition demo under `contracts.strands_agent`, `application.strands_agent`, and `application.competition_demo` and the exclusively synthetic package fixtures under `demo_data/` are `NEW_CORE` and `GENERATED_OR_TEST_DATA` respectively. The adapter instantiates the real `strands.Agent`, limits turns and tool calls, and provides exactly two profile‑specific read‑only FolderHome tools. The deterministic fixture implements only the public Strands model interface and is also new FolderHome code; it is not emitted as a model‑quality proof or Bedrock execution.  
- The `ollama` model provider under `contracts.strands_agent`, `application.strands_agent` and `cli` is `NEW_CORE`. It selects the Strands SDK's own `OllamaModel`; no provider code is copied. The MIT‑licensed `ollama` package is an optional extra and is installed, not vendored. The loopback‑aware gate logic is new FolderHome code.  
- `src/folderhome/mcp_server.py` and `tests/test_mcp_server.py` are `NEW_CORE`. The server registers FolderHome tools on the MIT‑licensed `mcp` SDK and proxies the existing loopback API with the Python standard library; it holds no state, adds no endpoint and copies no SDK code.  
- `strands-agents==1.53.0` is a required Apache‑2.0 runtime dependency. `tzdata==2026.3` is needed on Windows because a system‑wide IANA time‑zone database cannot be assumed there. Both packages are installed, not copied into the repository.  
- The synthetic accident journey under `application.accident_demo`, its local token-gated UI under `demo_site`, the backend-free `site/` walkthrough and the optional AgentCore HTTP adapter are `NEW_CORE`. The public walkthrough is explicitly not presented as runtime or cloud evidence.  
- The Pages workflow and ARM64 Dockerfile use immutable action and base-image digests. They package new FolderHome code; they do not change the origin classification of disclosed reused modules.  
- `examples/competition/evidence/` is generated solely from synthetic internal fixtures. The four artifacts demonstrate tool selection, output hash, no‑network, and lack of side‑effects; they contain no personal data.  
- Later submodules, live connectors, public releases, and paid actions require their own decisions and gates.

---
