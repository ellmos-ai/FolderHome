# Phase 3: Document Reuse Inventory

**English** | [Deutsch](./phase3-document-reuse-inventory.de.md)

**Status:** 2026-08-21  
**Purpose:** Prevents duplicate building in ingest, search, summarization, and report generation.

## Desired FolderHome Functions

1. Read documents from folders and capture them with stable provenance.  
2. Answer “I’m looking for a document that …” via local full‑text search.  
3. Consolidate scattered information on a topic into a dossier.  
4. Provide the filename and two to three descriptive sentences for each document.  
5. Generate a structured report from a folder.  
6. Later generate PDFs, Word, ODT, presentations, and spreadsheets from results.  
7. Administratively support health, legal, and financial documents without claiming diagnosis or binding advice.

## Verified Inventory

| Component | Current Status | Reuse in FolderHome | Do not rebuild |
|---|---|---|---|
| `file-collect-sort-action` | `0.1.0`, Commit `8ebac273…`, 63 Tests green | Detect file inventory, categorize, and provide reversible sorting plans | Scanner, action ordering, duplicate logic and processing state |
| `doc-services` | `0.1.0`, local Commit `037a432b…`, test suite green | Preferred extraction, OCR selection and content‑based privacy traffic light | Format converter, OCR routing and privacy detection |
| `KnowledgeDigest` | `0.4.0`, Commit `7040c66a…`, 130 Tests green | Local SQLite‑FTS5 store, chunking, search and hit ranking | Own document index, BM25 search and second chunking system |
| `report-forge` | Distribution `1.1.4`, Runtime `1.1.0`, Commit `355acb5f…`, test suite green | After correcting version drift: schema‑bound report generation and DOCX output | Own template or Word renderer |
| `llm-note` | `1.0.3`, Commit `b5fe59fc…`, 19 Tests green | Since Phase 28: append‑only storage for human‑verified personal notes | Second note database |
| `document-chunker` | Skill `1.0.0`, Zero Dependencies | Fallback for text paths without KnowledgeDigest | Do not additionally chunk in the normal KnowledgeDigest path |
| `dokument-ingest` | Skill `1.0.0`, uses `doc-services` | Agentic backend selection and privacy check | No standalone runtime alongside `doc-services` |
| `docs-analysis` | Skill `1.0.0` | Development‑side target‑actual alignment | Do not expose as end‑user document search |

The skill `find-docs` is explicitly not a FolderHome document search. It queries current developer documentation via Context7 and remains outside this product path.

## Existing Bundle Definition

The declarative Sovereign bundle `ellmos-doc-handler-bundle` already includes `report-forge`, `KnowledgeDigest`, `llm-note`, `docs-analysis` and `document-chunker`. It deliberately separates document handling from the actual knowledge search.

Current gap: `doc-services` and the skill `dokument-ingest` are still missing in the bundle and in the component binding. FolderHome therefore uses them during the competition via its own pinned component manifests. A change to the Sovereign bundle will only happen after integration post‑competition.

## Binding Responsibility Limits

```text
FCSA
  erkennt Dateien und plant Dateibewegungen

doc-services
  extrahiert Text und bewertet Datenschutzrisiken

KnowledgeDigest
  speichert normalisierte Dokumente und beantwortet lokale Suchanfragen

FolderHome
  hält Identität und Provenienz zusammen und orchestriert Nutzer-Usecases

report-forge
  erzeugt aus freigegebenen strukturierten Ergebnissen fertige Berichte

llm-note
  speichert ausdrücklich angelegte oder übernommene Nutzernotizen
```


## Required New FolderHome Code

1. A stable `DocumentRecord` with document ID, original path, content hash, media type, extraction provenance, privacy status, and index status.  
2. Pinned bridge manifests for `doc-services` and `KnowledgeDigest`; since Phase 28 also for `llm-note`, for `report-forge` only after a clarified runtime identity.  
3. Adapters that translate provider outputs into FolderHome contracts and treat unknown fields or states as fail‑closed.  
4. An application layer for ingest, search, topic dossier, and folder report.  
5. A later LLM port for free syntheses. The current folder report is deliberately deterministic and includes at most two or three supported sentences; a real model selection remains a separate gate.

## Required Adjustments to the Existing Inventory

- KnowledgeDigest archives originals by default at `ingest()`. The FolderHome bridge must always explicitly set `archive=False`.  
- KnowledgeDigest uses its own extractor internally. Until an official ingest‑for‑normalized‑text port exists, FolderHome does not write directly to its SQLite schema. The index bridge uses the public API and documents the remaining extraction duplication.  
- KnowledgeDigest performs its public search `ensure_schema()` with WAL switching and `INSERT OR REPLACE`. Therefore FolderHome reads only the pinned schema via SQLite `mode=ro&immutable=1` for search, checks its version, and does not modify the index file.  
- `report-forge` reports in the runtime package `1.1.0`, while `pyproject.toml` and changelog `1.1.4` are listed. The checkout is clean, but before a version‑checked bridge this provider identity must be unified upstream; FolderHome does not build its own Word renderer in the meantime.  
- `doc-services` currently has no remote and is not yet bound in the Sovereign component registry. Before release it needs a reliable source reference; locally the existing Git commit can be pinned.  
- Report generation with external LLM, OCR, and real user folders remain separate approvals. The synthetic Phase‑3 path does not require them.

## Sequence for Phase 3

1. Add provider‑neutral document contracts in a test‑driven manner.  
2. Validate `doc-services` and KnowledgeDigest manifests along with pins.  
3. Build synthetic ingest with a temporary database and `archive=False`.  
4. Offer local search and topic dossier via the KnowledgeDigest bridge.  
5. Add deterministic short descriptions and folder report as an application service.  
6. After correcting version drift, bind `report-forge` for formatted output documents.

## Acceptance Criteria

Phase 3 is complete: A fully synthetic folder can be read, searched, and summarized as a report via the CLI without moving source files, calling external networks, or using personal data. The full suite additionally demonstrates that a pure search leaves the index file byte‑exactly unchanged.
