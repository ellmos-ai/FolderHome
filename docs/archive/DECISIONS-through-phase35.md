# DECISIONS.md — Architecture Decisions

**English** | [Deutsch](./DECISIONS-through-phase35.de.md)

## 2026-08-22: llm-note stores versions, FolderHome guides the human

### Context

The existing `llm-note` provider offers a small local SQLite store and a public Write API, but no FolderHome profiles, references, content approvals, or version relationships. A second note store would unnecessarily duplicate the inventory. Its public Store class initializes the schema already on read via the normal object construction.

### Decision

FolderHome uses the exactly pinned `llm-note` checkout as the sole writable note store. New FolderHome contracts store each approved version as a separate provider entry. Read‑only planning and history use a schema‑fixed SQLite seam, so no write‑on‑read occurs. A provider‑neutral guide provides only separate questions and suggestions; the human‑approved content is never silently replaced.

### Consequences

- Create, Edit, and Revert add versions; there is no overwriting or deletion.  
- Plan, action, content, and the complete store revision require an exact human approval.  
- Document and calendar references must be explicitly present in the request.  
- Remote LLMs and external synchronization remain separate, with gates closed in Phase 28.  
- Family profiles are organizational attributes, not security accounts.  
- The previous repository reference is corrected to the occupied canonical `doc-bricks/llm-note` path.

## 2026-08-22: Calendar connectors extend the Phase‑17 handoff

### Context

FolderHome already has appointment candidates, profile resolution, local calendar state, and UpToday‑ICS output. UpToday, Routinika, and Google have different contracts: file handoff, bundle exchange, and agentic live handoff must not be treated as equivalent sync.

### Decision

Phase 27 does not build a second calendar core. A new provider‑neutral connector plan references the complete Phase‑17 handoff and adopts its rule provenance. UpToday creation is delegated to ICS, Routinika remains blocked without a live contract, and Google remains a separately approval‑required skill handoff. Only a synthetic No‑Network gateway is run locally.

### Consequences

- Account and request must bind profile, backend, and explicit calendar ID.  
- Create, Update, Delete, and Remind are separate operations.  
- Update and Delete require an existing provider‑event reference.  
- Google payloads use solo participants, offset times, blocking transparency, and explicit reminders.  
- `ready`, `review_required`, `delegated` and `blocked` remain visible and claim no live calendar entry.

## 2026-08-22: Reading, mutating, and sending mail remain separate capabilities

### Context

The existing doc‑bricks suite provides IMAP document retrieval, invoice extraction, and mailbox cleanup, but no encapsulated FolderHome‑SMTP connector. Local checkouts of the two IMAP tools also contain foreign changes or divergent revisions.

### Decision

FolderHome does not copy any suite code. A new provider‑neutral contract models read‑only ingest, explicit contact/correspondence binding, and idempotent sending. UniversalDocsGrabber is the intended but currently blocked ingest provider. UniversalMailCleaner remains fully separate because of mailbox mutations. Phase 26 only accepts a synthetic No‑Network gateway.

### Consequences

- Account JSON contains only secret references, no credentials.  
- An ingest plan can neither move, delete, flag, nor send.  
- Drafts are not created by automatic contact search but by exact active contact ID and recipient address.  
- Sending requires a separate, hash‑bound approval and an at‑most‑once ledger.  
- A real IMAP/SMTP run remains blocked until a clean provider checkout, credential adapter, and user approval are in place.

## 2026-08-21: FolderHome as a new integration repository

### Context

The hackathon contribution should reuse existing competencies without mixing new competition code with pre‑existing inventory.

### Decision

`FolderHome` is the product name, `folderhome` the repository and package name. The new core lives in `src/`, new connection code in `bridges/`, and pre‑existing components are referenced only as pinned in `reused/`.

### Consequences

- FCSA, HungryCall, and Ringedingeding remain unchanged repositories.  
- Manifests become the verifiable integration boundary.  
- The Phase‑1 host runs only synthetic capabilities.  
- Later publication and live actions will require new decisions.

## 2026-08-21: Default deny for side‑effects

Plugins must fully declare capabilities and side‑effects. A side‑effect capability without a satisfied gate ends `blocked`; unknown values already invalidate the manifest.

## 2026-08-21: Traceable run contract

Every run uses `ellmos.home-agent.run-report.v1`, a stable `run_id`, unique action IDs, status, provenance, gate status, evidence, and optional undo metadata. Report files are written atomically.

## 2026-08-21: Competition name remains FolderHome

During the competition the product is exclusively referred to as `FolderHome`. The current repository receives no alternative competition branding. Only after the competition can this state be frozen or reduced and then rebranded; full further development should then be integrated into Sovereign.

## 2026-08-21: Separate document provider and read‑only search

`doc-services` is responsible for extraction and privacy checks; KnowledgeDigest handles indexing and ranking. FolderHome keeps identity, provenance, and user use‑cases together. KnowledgeDigest ingest runs only with `archive=False` and an explicit index gate. Because the public search method of the pinned provider mutates the database, a narrow FolderHome bridge reads its versioned schema exclusively in SQLite mode `ro`/`immutable`. This exception is encapsulated and will fail‑closed on any schema change.

## 2026-08-21: Latest version is an explicit heuristic

FolderHome orders versions first by explicit wording such as “effective from” or “contract state”, then by a date in the filename, and finally by the filesystem modification date. Base, evidence, and confidence are output. This ordering is not a legal determination.

Older versions are not automatically moved. FolderHome generates unapproved, reversible suggestions and also lets them be confirmed by the real FCSA dry‑run. A later live execution still requires its own gate.

## 2026-08-21: Profiles organize, but do not authorize

Person files like `Lukas.json`, `Hanna.json`, or `Simon.json` may contain their own document preferences. They reside within the existing security boundary of the operating‑system account and do not create separate access rights.

Rules are inherited in the fixed order global, domain, profile, and profile‑domain. Peer‑ranked differing values block resolution. Deletion rules can only be disabled, audit‑required, or directed to the trash; irrevocable deletion is not a valid value.

## 2026-08-21: Action plans are not execution approvals

Resolved profile rules are translated into a separate schema `folderhome.document-policy-action-plan.v1`. Each step lists rule sources including overridden rules, provider, capability, filesystem effect, gate, and return path. A plan never grants the filesystem gate itself.

Naming and sorting are projected sequentially. Archiving and trash are bound to FCSA’s real dry‑run pipeline; hard delete remains explicitly disabled in the generated configuration. Conversion is not attributed to any unchecked legacy module and remains so until binding to its own encapsulated provider `blocked`. Simultaneously due, competing sort, archive, or trash targets generate a visible review conflict instead of an implicit priority.

## 2026-08-21: Transformation is a new encapsulated core

The provider comparison yielded no unchanged reusable component for the entire bundle requirement. `doc-services` remains responsible for extraction; FCSA takes original movements later. MarkItDown generates analysis markdown, `report-forge` is locked due to conflicting version identity, and its PDF processor is a stub. `PDFtoPDFocr` is not imported directly because the existing merge function moves single files and the module loads GUI dependencies on import.

The gap is therefore encapsulated as `folderhome.capabilities.document_transform`. V1 supports TXT and PDF. A plan contains source hashes, handling, and loss threshold without raw text. Writing requires an explicit gate, re‑checks sources, is atomic, and never overwrites. PDF inputs remain page‑faithful; images are rasterized; extracted text is re‑laid out with visible layout loss. The original handling stays a separate FCSA step and is only plan‑able after a verified transformation result.

## 2026-08-21: Type groups are published in a ZIP instead of a working folder

The requirement “one document per type” is implemented as a new ZIP containing multiple group documents. Images and PDFs remain separate PDF groups; TXT, Markdown, and other extractable formats are output per type as text bundles. Unknown formats stay hashed and visible in the manifest.

A single ZIP avoids partially published output directories and simplifies undo to the deletion of exactly one newly created file. The package is built entirely in memory, receives fixed ZIP metadata, and is published atomically without overwriting. The manifest contains the hashes of all sources and internal outputs; the ZIP’s own hash appears only in the external result, as it cannot be consistently represented within the ZIP itself.

## 2026-08-21: Folder observation learns only from recorded corrections

Snapshots store relative paths, SHA‑256, size, and filesystem timestamp, but no document content. The observation moment is passed explicitly; snapshot files require a state gate and are appended immutably.

A move is asserted only when a unique, unchanged hash pair is present. Duplicates remain intentionally ambiguous. As a learning example, a move counts only if an earlier FolderHome storage record contains the same hash and source path. The result remains `candidate` with `automatic_promotion=false`; automatic rule changes are excluded.

## 2026-08-21: Scan runs use an immutable checkpoint history

Observed folders are declared via `folderhome.watched-folders.v1` with stable ID, source root, organizational profile, domain, interval, recursion, and active status. FolderHome does not introduce a scheduler in Phase 10; an explicitly started scan merely indicates whether the interval is due.

The final state is determined from identity‑verified snapshot files. A writable pointer file is deliberately avoided. Before a new checkpoint, FolderHome re‑examines the history so competing changes fail‑closed visibly. Without a state gate the entire scan run is read‑only; even with a gate, neither source documents nor profile rules are changed.

## 2026-08-21: Single‑file execution separates plan provider and executor

An execution approval binds to the SHA‑256 ID of the complete content‑free plan, the source hash, and an ordered, gap‑free prefix of concrete action IDs. On CLI invocation the plan is rebuilt from source and profile rules; any interim content or rule change produces a different plan ID and invalidates the approval.

FCSA remains responsible for classification and real dry‑run but is not emitted as a single‑document live executor. Its public entry scans an entire folder, writes processing memory, and can rename collision targets. FolderHome therefore encapsulates a tighter `folderhome.filesystem-transaction`: it does not classify, accepts only an already approved exact move, never overwrites, and aborts on cross‑volume targets. Plan provider and actual executor are listed separately in the audit.

Before the first file change an immutable intent is written. The final report contains a storage record and is checked against this intent on later reads. Undo requires a new approval and the unchanged target hash; an existing source, a changed target, or a diverted audit path blocks the rollback.

## 2026-08-21: A cleanup run is checked across the folder before each approval

FolderHome generates for each supported file the same already‑verified single‑document plan. Only after that are all intermediate and final targets considered together. Multiple documents with the same target, a target that is the source of another document, or an already occupied target block all involved plans. File order or automatic renaming does not silently resolve these conflicts.

A batch approval may deliberately select only a subset. It binds to the batch ID and, for each document, again to document ID, source hash, plan ID, and action prefix. If execution later fails, FolderHome uses the already written single reports for a rollback in reverse order. Only a fully successful batch yields active storage records; after a successful rollback the error report remains as audit.

## 2026-08-21: Routines compose scan and batch without implicit automation

A routine plan remains fully read‑only. In mode `changes` only files that have reached the watch interval, are newly content‑changed, or are unambiguously moved are passed to the folder‑wide cleanup plan. Pure metadata changes stay visible in the scan but do not trigger re‑processing. `full` is an expressly chosen full mode.

Execution still uses the independent batch approval and requires both file and state gates. Before changes the last checkpoint and full scan ID are re‑checked. A new checkpoint is added only after a successful batch. If this final step fails, file actions are rolled back via existing undo contracts. A target in the observed root is excluded to prevent re‑entry loops. Phase 13 deliberately registers no operating‑system scheduler.

## 2026-08-21: Watch observation and routine target remain separate contracts

`folderhome.watched-folders.v1` remains responsible for source, profile, domain, recursion, interval, and active status. A separate `folderhome.routine-bindings.v1` maps a watch target root and `changes`/`full` mode. Thus the same watch can be observed without a cleanup routine, and a scheduler receives no implicit file permissions.

The queue plans all active watches read‑only and writes neither checkpoint nor report file. Missing bindings are visibly blocked. Additionally it checks input overlaps, targets in other observed inputs, and shared action targets across routines. It does not register any operating‑system task; that step remains a later, separately approval‑gated adapter boundary.

## 2026-08-21: Scheduler plan, queue run, and installation are three boundaries

The handoff generates a portable argument list and Windows‑Task XML only as a JSON plan. FolderHome does not invoke `schtasks` nor any other registration interface. The artifact therefore explicitly exposes `registration_performed=false` and `installation_supported=false`.

A headless run is separate. It recomputes the schedule ID, loads current configurations, and runs only the read‑only queue. A tight gate permits a schedule‑specific lock and an append‑only run report in the FolderHome state. Existing locks are not automatically interpreted as orphaned or removed. Exit codes 0, 10, 20, and 30 distinguish idle, approval needed, blocked, and parallel/rest lock. Later installation remains a separate user decision.

## 2026-08-22: Document contacts are evidence‑bound candidates

A general contact CRUD from the BACH legacy store is not re‑extracted. It has neither document‑hash evidence nor plan/action approvals nor an atomic exchange contract. FolderHome instead uses the already extracted doc‑services bridge, profiles, and document identity and encapsulates the new register core under `capabilities/contact_registry`.

V1 interprets only declaratively labeled lines. This prevents arbitrary free text from being silently stored as contact data. A candidate binds its normalized fields to document ID, SHA‑256, path, and line numbers. Folder‑wide competing newest candidates are fail‑closed checked before a register action.

The privacy traffic light evaluates a possible disclosure. `review_required` therefore can be processed only with its own gate for purely local contact extraction; the gate grants no network or mail approval. `blocked` and `not_checked` remain disallowed.

A new contact never replaces the old by deletion. A single SQLite transaction creates the new record, marks the previous one as `deletion_candidate`, and adds an append‑only event. Approval files are bound to plan ID, register revision, and concrete actions; revision and source hashes are reread before the transaction.

## 2026-08-22: Calendar selection is reused, calendar access not claimed

The existing `kalender` skill already describes an adaptive backend choice between local store, UpToday, Routinika, and Google. Its core, however, implements only local behavior, is not tied to a Git revision, and offers direct write/delete operations without FolderHome gates. FolderHome therefore adopts the preference model as typed configuration and profile rule, not the core as a runtime adapter.

UpToday has a tested local ICS channel. The loose coupling via a new ICS file is more stable than a write to the internal SQLite schema. Phase 17 therefore plans deterministic ICS handoffs with FolderHome UID and content hash, but does not invoke the import. An existing target or overlap with the document root blocks the operation.

For Routinika only an old, explicitly unused UpToday bridge was found, which does not open SQLite read‑only. The backend remains selectable so no silent fallback occurs; its plan is `blocked`. Google remains blocked due to network and privacy boundaries.

Local execution uses its own approval contract and two encapsulated capabilities. `folderhome_local` writes transactionally to a FolderHome‑owned SQLite store. `uptoday_ics` publishes only new hash‑verified ICS files and writes the result to an append‑only audit; it invokes neither UpToday nor its database. Both paths re‑verify revision and source hash. ICS also requires, in addition to the state gate, an output gate and returns only its own unchanged files on partial failures.

## 2026-08-22: FindCall adopts the pattern, not the restaurant model

HungryCall already holds the decisive orchestration: pre‑filter and order candidates, query serially, check structured results against hard limits, and stop after the first success. Its public data types, however, are deliberately restaurant, order, and table‑reservation models. Modeling medical practices or workshops as restaurants would be a misuse.

FindCall therefore encapsulates a new generic contract and designates HungryCall as the pattern source. Ringedingeding remains the complementary plugin for multi‑person polls; its parallel/group logic is not reinterpreted as a provider cascade. FolderHome checks both real checkouts and loads only their local dry‑run entry points.

Phase 18 runs only explicit fixtures. Candidate numbers are masked before each serialization, call status is not merged, and emergency/diagnostic content is rejected. The sole authority is `inquiry_only`. A later real request, booking, or confirmation requires a separate live connector, privacy, cost, and approval contract; no CLI flag exists for this.

## 2026-08-22: Virtual accounts show only recorded financial states

The extracted tax assistant performs cent‑accurate local SQLite processing but is a self‑categorized receipt work document. A bank statement, balance, or subscription is not a tax receipt. FolderHome therefore adopts the cent/privacy principle, not the tax‑specific schema. No previously extracted subscription tracker or statement parser existed locally; the gap is encapsulated as `capabilities.finance_store`.

V1 requires a declarative format with integer cents, period, opening/closing balance, and a unique transaction reference. Free‑form bank layouts are not guessed. A statement is a candidate only if its transaction sum exactly explains the closing balance. Adjacent statements must also continue the same balance chain; otherwise the plan is blocked.

The store imports exclusively after plan, revision, action, source hash, and state approval. It adds data and audit, deletes nothing, and does not communicate with any bank. Coverage is calculated from periods. Without a continuous, gap‑less chain FolderHome emits no boundary balances.

A cent‑equal roughly monthly charge is only labeled `active_candidate` or `inactive_candidate`. This does not prove a contract, termination, or next charge; annual values are merely extrapolations from recorded monthly costs.

## 2026-08-22: The artifact studio routes specialists instead of copying a renderer

Presentations, tables, Word documents, and media already have their own skills or modules with differing quality contracts. A shared FolderHome renderer would duplicate these rules and especially dilute content verification, formulas, Office rendering, visual acceptance, and media rights. Phase 25 therefore introduces a provider‑neutral artifact plan.

Each artifact type receives exactly one designated provider status. `blocked` may not be bypassed by a similar system library; `review_required` is not a finished claim. The plan does not call any provider. PPTX, spreadsheets, and DOCX stay bound to their existing skills; ODT remains blocked without a renderer. ai‑media‑editor is assigned to revision `4e4c79d8c16a117bf69c0f72ad946575110a6b84`, but real media, slicing strategy, and output retain separate approvals.

Only the previously missing, generally reusable design core is newly built. It generates contrast‑checked JSON/CSS tokens and an escaped SVG business card. Sensitivity and output gates are separate; three files are never overwritten and, on a partial internal error, are hash‑bound rolled back. Every concrete card requires a renewed visual check before printing or publishing.

## 2026-08-22: Correspondence separates preview, output, and office handoff

Letter contents regularly contain personal data and can later have legal or financial effect. Direct coupling of document discovery, free LLM formulation, Office rendering, and sending would invisibly mix these effects. Phase 24 therefore introduces its own provider‑neutral correspondence core.

Request, template, and design are explicit contracts. Design resolution is deterministic; fuzzy free mapping does not occur. Templates may use only simple variable names. Missing or extra variables, as well as Python attribute, index, conversion, or format syntax, block the process.

The first stage is a read‑only preview after sensitivity approval. A second approval permits only new Markdown and TXT files as hash‑verified batch. Existing targets are never overwritten; a partial error rolls back only files it created. Sending, printing, and publishing are not implicit follow‑ups.

report‑forge remains at revision `355acb5ff1abe41b384a0d1e3a00925e6ac86215` inventory‑listed, but is not invoked because distribution `1.1.4` versus runtime `1.1.0` is omitted. Without a complete visual Office acceptance, the locally available python‑docx is also not emitted as a finished DOCX function. ODT has no revision‑bound renderer. Both formats remain visible, not executed handoffs.

## 2026-08-22: Contract cockpits connect only explicitly associated evidence

Documents, contacts, bookings, and appointments currently have different, domain‑appropriate identities. Similar names alone do not prove that a charge or contact belongs to a particular contract. An implicit fuzzy or LLM‑based join would turn correlation into a contractual claim.

Phase 23 therefore introduces an explicit request contract. It lists document search, contract object, counter‑party terms, calendar terms, account identifiers, period, and archiving preference. Only this mapping may combine the existing read‑only views. Missing or ambiguous evidence remains visible as a component hint.

The cockpit has no own domain store. It uses version analysis, contact register, recurring costs, calendar store, and financial coverage from their existing contracts. Older documents are shown, when the preference is active, only as unapproved reversible archiving suggestions. Contact changes, calendar actions, payments, bank access, and contract status are not executed or claimed. The CLI end‑to‑end test keeps the shared state byte‑exact unchanged.

## 2026-08-22: Health dossiers remain local, extractive, and incomplete

doc‑services deliberately classifies health terms RED because its traffic light secures third‑party sharing. FolderHome needs these contents only for an expressly chosen local dossier run. A blanket override of RED would simultaneously expose credentials, bank identifiers, or private keys and is therefore excluded.

After the local sensitivity gate, a red content line is processed only if all red findings in the provider report exclusively involve `Gesundheitsdaten`. Any additional red finding blocks the content transfer. No network or LLM call occurs.

Synthesis remains extractive. Statements are sorted by an explicit document date and annotated with document ID, source hash, relative path, and line. Identically named documented fields with differing values are not resolved but shown as conflict candidates. Time gaps between sources are not claimed as care gaps. Undated, future, blocked, and unreadable files stay visible.

Markdown and JSON are the canonical Phase‑22 outputs. The optional report handoff is non‑executing and blocks report‑forge as long as its distribution `1.1.4`, but the runtime `1.1.0` reports. Diagnosis, therapy decision, and completeness claim are not product features of this dossier.

## 2026-08-22: The competition roadmap comprises 36 phases

The previously rolling phase count is fixed to 36 competition phases so that “full build‑out” has a verifiable scope. Phases 1‑22 are completed, Phase 23 starts with the insurance and contract cockpit. The later planned integration into FolderHome‑Sovereign occurs after the competition and is not an additional FolderHome competition phase.

## 2026-08-22: Medication intakes are confirmed facts, not recommendations

UpToday Health demonstrates the useful separation of medication, schedule, and intake log. The public `gesundheit` skill adds the boundary of providing health information to organize, without diagnosis or therapy decision. FolderHome displays both sources, loads no old runtime, and copies no source code.

A V1 plan therefore uses only tightly labeled, human‑provided data. Dose, unit, time, timezone, weekdays, and validity are stored together with document ID, source hash, and line evidence as an append‑only schedule version. Free‑text entries like “as needed” are not reinterpreted as an intake time but block the entry for review.

The daily view is a pure read projection. It does not present a scheduled time as an actual intake. Only a separate confirmation bound to the plan revision and a stable dose ID creates an intake event. Stock level is also only a hint; neither stock quantity nor calendar is automatically altered. Diagnosis, prescription, dosing decision, reminder, and medical completeness explicitly remain outside this phase.

## 2026-08-22: Household inventory is an event history

UpToday already contains a local stock model with items, domains, locations, units, minimum stock, and purchase derivation. These domain terms are referenced as design at revision `7582ca8`. The existing engine is not loaded: floating‑point numbers, a global DB singleton, direct stock updates, delete operations, and implicit day dates violate the deterministic FolderHome contract. No UpToday source code is copied.

FolderHome V1 therefore reads a tight, labeled observation format via the already pinned doc‑services provider. Quantities have at most three decimal places and are stored as integer thousandths of the given unit without rounding. An item is stably identified by profile, domain, name, and unit; location, quantity, minimum stock, and expiry belong to the respective observation.

The inventory store has no silently overwritten current quantity. Every approved stock snapshot is appended as a new event with document ID, hash, line evidence, and audit. The current view derives from the newest recorded observation. Contradictory observations on the same day block; plan, approval, revision, actions, source hash, and state gate must all match before the atomic import.

Under‑stock, expired, and soon‑to‑expire are solely audit‑required candidates. There is no ordering, no supplier contact, no automatic deletion, and no guarantee that the captured household is complete. Family profiles organize views but do not change the operating‑system account’s security boundary.

## 2026-08-22: The tax agent remains a receipt store and private work document

The pinned `steuer-assistent` provides a small, tested API for user‑categorized advertising expense receipts and a ZIP export. This is a suitable reuse boundary; an additional tax engine would duplicate the same store.

FolderHome only adds missing links to the document catalog, financial posting, profile, and approval. A category candidate remains visible but not executable. Only the human‑approved input group may be saved after exact plan, document hash, provider store, and state binding. The approval is explicitly not a statement about tax deductibility.

Because the provider lacks a profile field, each organizational profile receives its own store. This separation isolates work documents but does not change the security boundary: it remains the operating‑system account.

The ZIP export is a private, non‑official work document and has its own approval as well as state and output gates. Tax consulting, tax calculation, ELSTER, ERiC, tax‑authority transmission, network, and mailing are offered neither by the provider nor as a FolderHome fallback.

## 2026-08-22: The daily brief starts with local snapshots

The product search found no already extracted weather or newspaper provider. BACH does contain a weather service, newspaper generator, and daily agent, but ties them to the BACH database, implicit system time, fixed location, network, edge, and direct desktop and Telegram effects. The overall checkout is also foreign‑modified. A runtime binding or re‑extraction would violate the intended module boundary.

FolderHome therefore first defines a provider‑neutral snapshot contract. Weather and news must carry source and fetch timestamps; the briefing binds both files by hash and processes only explicit categories. Stale data are not discarded or presented as current but remain as audit‑required offline fallbacks.

Rendering and desktop delivery are separate actions. A render approval may not create a desktop file; a desktop approval copies only the exactly rendered hash and overwrites nothing. Live connectors and scheduler registration stay open, because a single approval does not establish a lasting network or write authority.

## 2026-08-22: Official notice understanding remains separate from legal review

The existing law‑checker already formulates a conservative first orientation with official sources and escalation on deadlines. The checked local checkout, however, is one commit behind upstream, foreign‑modified, and lacks a sufficiently complete general social‑administrative and social‑court law corpus for arbitrary official notices. Executing it would suggest an unsupported legal review.

Phase 31 therefore does not load the law‑checker. FolderHome uses the caution methodology only as a design reference and builds a smaller document‑understanding capsule. It adopts exclusively known, explicitly labeled fields and binds each result to line number, document ID, and source hash. Missing or contradictory single fields remain visible.

A human‑provided access date is marked as a user input. An explicitly printed deadline may be counted against an explicit analysis timestamp; this calendar arithmetic is not a legal deadline calculation. Relative texts like “within a month” are not reinterpreted. The output explicitly states that no legal review has taken place and produces neither objection nor mailing.

## 2026-08-22: Administrative drafts use the brief core and remain local

Phase 24 already has the secure brief mechanism: parties, profile‑dependent design resolution, vetted placeholders, deterministic preview, output hashes, and never‑overwrite. Phase 32 therefore does not build a second renderer. The new capsule creates a strictly bound `CorrespondenceRequest` and adopts the existing preview and output.

The official cross‑check of § 84 SGG, § 36 SGB X, and § 16 SGB I shows that deadline, form, legal remedy, and responsible authority have context‑dependent legal consequences. FolderHome does not adopt these norms as general decision rules. An objection draft is allowed only if the provided official notice itself names `Widerspruch`; timeliness and admissibility remain unchecked. An application draft does not assess benefit eligibility or jurisdiction.

User statements are called `user_provided` until output. A separate approval binds the fully read brief to both output hashes and confirms only the local output. The visible draft hint is a forced template placeholder. No send command exists; email, portal, print, and post remain separate later user decisions.

## 2026-08-22: Benefit assessment is handed over to official guides

The central `foerderplaner` is an educational planning aid and not a social benefit module. BACH only contains general old wiki articles. A local rebuild of complex entitlement and amount calculations would therefore be duplicate work without reliable currency or completeness basis.

The social platform provides its own benefit finder as orientation. Federal agency and BMWSB offer official pre‑checks with KiZ‑guide and housing‑benefit‑plus calculator. Phase 33 therefore models only coarse local routing criteria and deliberately points to these official offers afterward. Personal data are not automatically transmitted.

The local catalog must remain `complete=false`. Each source carries a check timestamp and a hash of its short evidence summary. Out‑of‑date sources block. `routing_mismatch` is explicitly not a rejection and `official_handoff_recommended` not a claim. Benefit eligibility, amount, application, and portal access stay outside the pre‑check.

## 2026-08-22: Legal changes generate review candidates, not legal judgments

The current clean `law-checker` checkout is verified as a source‑bound skill, registry, and fetcher. It does not provide a stable Python API that FolderHome could call for automatic case‑by‑case review. Exposing an agent answer as a runtime contract would overstate capabilities and coverage.

FolderHome therefore binds only immutable provider identity, registry, and source metadata. The new bridge requires a clean exactly pinned revision and starts neither fetcher nor legal agent. A registered law key can additionally qualify a snapshot; missing or disabled keys block.

The new monitor compares already acquired, dated statutory sections technically. Profile and contract linkage arise solely from explicit `user_provided` topics. Even with overlap the result remains `review_candidate` and `affected_determined=false`. Drafts receive their own status and are not described as promulgated or asserted.

Automatic web acquisition, legal effect, transitional law, deadline calculation, official notice response, and notification remain separate follow‑ups. This enables later reusable providers without reinterpreting a text diff as legal advice or a tag hit as personal impact.

## 2026-08-22: The local GUI is a narrow service surface, not a second core

The 34 existing phases already have encapsulated application services and a broad CLI. A general HTTP command router or arbitrarily supplied file paths would bypass side‑effect, sensitivity, and approval boundaries. Phase 35 therefore exposes only status, profile, capabilities, document search, and theme dossier via a fixed read‑only allowlist.

The standard library suffices for the competition scope and avoids a second web runtime. The listener is created only after an explicit gate on `127.0.0.1`. A short‑lived token, exact host, same‑origin, CSP, and strict request limits protect the local browser session. The token is a process hurdle, not a new identity manager.

Family profiles order rules and results but do not separate data within the same operating‑system account. The GUI makes this boundary visible. Real isolation continues to rely solely on separate OS accounts and their file permissions. Writing, legal, medical, and financial actions remain in their separate domain workflows and are not unlocked by the new interface.
