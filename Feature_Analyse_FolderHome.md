# Feature Analysis: FolderHome

**English** | [Deutsch](./Feature_Analyse_FolderHome.de.md)

**Version:** 0.36  
**Date:** 2026-08-22  
**Competition name:** FolderHome

FolderHome is a local document and assistance service agent. The new competition core connects declared existing modules, encapsulates new everyday capabilities, and executes natural document queries via a real, finitely bounded Strands agent.

## Status legend

- **Locally implemented:** executable FolderHome code with automated success and fail‑closed evidence.  
- **Handoff:** vetted plan or provider boundary, but deliberately no claimed live service.  
- **Partial:** the secure core is present; a desired renderer, connector, OCR/LLM provider, or a domain decision remains open.  
- **Outside:** only with a later product decision or external approval.

## Feature coverage

| Desired area | Status | Implementation and honest limitation |
|---|---|---|
| Collect documents | Locally implemented | Pinned doc‑services ingest, privacy gate, local index; source files remain unchanged |
| Photo/PDF OCR | Partial | Provider boundary is prepared; OCR of real photos was not performed in the competition proof |
| Natural document search | Locally implemented | Read‑only search, including “I’m looking for a document where …” |
| Find scattered topics | Locally implemented | Evidence‑bound topic dossier, e.g., on health insurance, with visible coverage |
| Folder summaries | Locally implemented | Document name plus two to three extractive sentences and freely generated folder dossier |
| Reports from folders | Locally implemented | Deterministic Markdown report; external LLM synthesis remains a separate provider |
| Compare document versions | Locally implemented | Declared latest‑version heuristic, sentence comparison and revision‑bound archiving plan |
| “Latest vehicle insurance” | Locally implemented | Contract cockpit links version, object, contact, cost, appointments and data coverage; archiving remains subject to approval |
| Organize loose folders | Locally implemented | FCSA dry run, profile rules, overall plan, goal conflicts and selective execution |
| Continue existing order | Locally implemented | Rule inheritance and observed folder states; no unsupported pattern claim |
| Learn from user corrections | Locally implemented | Hash‑bound correction examples become rule candidates requiring review, never silently activated |
| Regular directory scans | Locally implemented | Declared watches, immutable checkpoints, queue and portable scheduler handoff |
| Correct mis‑sorted files | Locally implemented | Plan, approval, fresh source hash, never‑overwrite, storage evidence and verified undo |
| Global/area‑specific rules | Locally implemented | Naming, archive, trash, file type and destination as fixed inheritance global → area → profile → profile area |
| One target format per folder | Locally implemented | PDF/TXT transformation with loss warnings; other formats blocked without provider |
| Bundle documents | Locally implemented | One TXT or PDF and one document per type in deterministic ZIP; videos are not masqueraded as content |
| Family profiles | Locally implemented | Lukas/Hanna/Simon fixtures and area‑specific rules; profiles are not security accounts |
| Audit and cleanup reports | Locally implemented | Atomic JSON reports, decisions, hashes, checkpoints and rollback status |
| Contacts from documents | Locally implemented | Evidence candidates, local register, object mapping and secure contact transfer without automatic deletion |
| Appointments from documents | Locally implemented | Candidates with line evidence, local calendar and atomic ICS handoff; no detection guarantee |
| Calendar selection | Handoff | UpToday‑ICS vetted; Routinika visibly blocked; Google only after own live approval |
| Account statements/virtual accounts | Locally implemented | Cent‑precise transactions, account reference, periods, balance and visible gaps; no banking access |
| Subscription and cost analysis | Locally implemented | Recurring costs, active/inactive candidate, monthly/annual sum and cautious next‑month forecast |
| Insurance overview | Locally implemented | Object‑bound policy, contact, cost, appointment and version view |
| Household/inventory stock | Locally implemented | Append‑only inventory events, locations, minimum stock as well as purchase and expiry candidates |
| Medication plan/intake | Locally implemented | Evidence‑bound plan and separate confirmed intake; no dosage decision |
| Synthesize medical reports | Locally implemented | Extractive health timeline, conflicts, medications, appointments and questions; no diagnosis |
| Understand official notices | Locally implemented | Types, labeled information, conflicts and provided deadlines; no legal review |
| Answer official notices / applications | Locally implemented | Controlled objection, response and application drafts from profile and evidence; no sending |
| Benefit and funding pre‑screen | Locally implemented | Dated routing catalog and official next review steps; no claim or amount notice |
| Legal changes | Locally implemented | Comparison of local snapshots and impact candidates; no web monitoring or legal judgment |
| Law‑Checker | Handoff | Cleanly pinned, read‑only source/registry bridge; no fabricated legal‑check API |
| Presentation/Table/Word/ODT | Handoff | Provider‑neutral artifact plan and quality gates; specialized renderers are not copied or claimed to run locally |
| Letter design/Design set | Locally implemented | Profile/purpose templates, contrast check, JSON/CSS tokens and controlled Markdown/TXT output |
| Business card | Locally implemented | Escaped SVG preview, visual approval and never‑overwrite batch |
| Media creation | Handoff | Revision‑bound ai‑media‑editor handoff without claimed media execution |
| Mail ingest/send | Handoff | IMAP plan, draft, exact send approval and synthetic idempotence ledger; no live mailbox test |
| Personal LLM notes | Locally implemented | Guided query, approval and append‑only versions via the pinned llm‑note provider |
| Tax agent | Locally implemented | Encapsulated receipt storage and private ZIP work file; no tax advice or portal transmission |
| Weather/Newspaper on desktop | Locally implemented | Local snapshots, freshness labeling, HTML render and separate desktop approval; no live feeds |
| HungryCall/Ringedingeding | Handoff | Revision‑bound local dry‑run probes, no telephony |
| FindCall | Locally implemented | Generic serial offer/appointment scheduling with time, price and stop limits; fixture provider only |
| Strands agent | Locally implemented | Real `strands.Agent` loop with two read‑only tools for search and topic dossier |
| Amazon Bedrock | Handoff | The same agent supports `BedrockModel`, but only with model ID, region and separate network/data transfer gates; not live tested |
| Local model (Ollama) | Locally implemented | `OllamaModel` provider on the same agent loop; a loopback host needs no gate, a remote one needs the same two gates as Bedrock. Smoke-tested against a remote Ollama host; the loopback smoke is still open and the client has no HTTP timeout |
| MCP adapter | Locally implemented | `mcp serve` hands eleven read-only and confirm tools over stdio to a running `app serve`; any non-loopback address is refused and stdout carries protocol only |
| Results view | Locally implemented | Executed reports stay in one bounded ring buffer and are listed per profile; artifacts are fetched by index, never by a path parameter, capped at 25 MB |
| Setup program | Locally implemented | A separate loopback installer is the only place that writes configuration; saving rewrites `resources.json` completely, so hand-added entries are lost and only the `.bak-<timestamp>` copy preserves them |
| API/GUI/CLI | Locally implemented | Shared application service, Loopback API, responsive local GUI and comprehensive CLI |
| OS account separation | Locally implemented | Operating system account and file permissions are the security boundary; no pseudo‑security between profiles |

## Reuse

| Role | Asset | FolderHome adaptation |
|---|---|---|
| Collecting and sorting | file-collect-sort-action | Dry‑run bridge, hash/approval contract and FolderHome rule model |
| Extraction and search | doc-services, KnowledgeDigest | Pinned ingest as well as read‑only search and dossier adapter |
| Phone patterns | HungryCall, Ringedingeding | Check capabilities; generic FindCall domain remains new core |
| Calendar | UpToday, Routinika, Google-Calendar-Skill | Provider‑neutral accounts and separate live gates |
| Notes/Taxes | llm-note, steuer-assistent | Tight public API, profile‑specific stores and FolderHome audit |
| Medical/analysis | gesundheit, docs-analysis | Security and extraction patterns; no copied runtime code |
| Law/briefing | law-checker, BACH | Read‑only registry or design reference; new workflows remain encapsulated |
| Media/Office/Mail | ai-media-editor und doc-bricks | Revision‑bound handoffs instead of duplicated renderers/connectors |

The exact revisions and provenance classes are listed in
[`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md) and
[`COMPETITION_CODE_MAP.md`](./COMPETITION_CODE_MAP.md).

## Evaluation of competition version

| Category | Rating (1–5) | Justification |
|---|:---:|---|
| Feature set | 4 | All desired areas have at least an honest local core or clear handoff; live providers remain separate |
| Agentic | 4 | Real, finitely bounded Strands loop; for competition acceptance deliberately only two read‑only tools |
| UI/UX | 4 | Responsive Loopback GUI and CLI on the same service, plus a separate browser-based installer; no native desktop installer yet |
| Stability | 5 | Success, abuse, gate, rollback and never‑overwrite paths are broadly automatedly checked |
| Documentation | 5 | Architecture, decisions, provenance, security, current status and submission package are documented separately |
| Privacy/Security | 5 | Local‑first, OS account boundary, default deny, resource budgets, provenance and explicit outward‑effect gates |
| Live integration | 2 | Deliberately conservative: no cloud, phone, mail, calendar or portal effect without separate approval. A real local model over the network is the one live path that has been exercised |

## What remains after the local full build‑out

The 36 competition phases deliver the local, demonstrable FolderHome full build‑out. Not as an unfinished core defect, but as separate product/external‑effect gates remain:

1. public repository and video release as well as Devpost submission;  
2. real Bedrock, IMAP/SMTP, calendar, phone, OCR and web connector tests;  
3. visual acceptance of additional office/media renderers;  
4. later integration into FolderHome‑Sovereign and possible light rebranding.

## Technical core

- Python 3.11+, `strands-agents==1.53.0`  
- on Windows `tzdata==2026.3`  
- Entry point: `python -m folderhome`  
- Agent: `src/folderhome/application/strands_agent.py`  
- reproducible demo: `python -m folderhome demo run`  
- Security model: [`SECURITY.md`](./SECURITY.md)  
- Architecture: [`ARCHITECTURE.md`](./ARCHITECTURE.md)  
- complete phase evidence: [`docs/phase36-completion-audit.md`](./docs/phase36-completion-audit.md)

---
