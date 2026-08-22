# FolderHome

**English** | [Deutsch](./README-phase36-draft.de.md)

> Assistantify your home.

FolderHome is a local document and assistance service agent for everyday use. It connects existing, openly declared components via secure plugin contracts and builds new capabilities as reusable packages. The first building block is a fail‑closed integration core with traceable JSON run reports. FCSA generates sorting plans without moving files; the local document pipeline extracts, indexes, searches, and describes files through precisely pinned providers, without altering the source documents.

## Status

All 36 competition phases have been implemented and tested locally. Phase 36 adds a real, finitely bounded Strands agent, shared resource budgets, the full security scan, a reproducible synthetic demo, and prepared English submission materials. The complete suite comprises **331 passed tests**. External connectors, Amazon Bedrock, publication, video upload, and Devpost submit are separate user gates. The current state is at `phase1-foundation` and still has no remote.

During the competition the project is called **FolderHome** exclusively. A later rebranding is not part of this competition state.

The documented final version is in [`Phase-36-Completion-Audit`](../phase36-completion-audit.md), the security model in [`SECURITY.md`](../../SECURITY.md). The English drafts are available at [`docs/submission/`](../submission/).

## Reproducible Competition Demo

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,transform]"
.venv\Scripts\python.exe -m folderhome agent plan `
  --profiles-dir examples\profiles --state-dir .local-state --json
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir .local-demo\competition --approve-output-write --json
```


The demo runs the real `strands.Agent` and two real FolderHome tools with a deterministic fixture model. It requires no credentials, uses no network, and writes only four new artifacts to the explicitly approved output folder. A second run into the same folder blocks rather than overwriting. The supplied reference evidence is located at [`examples/competition/evidence/`](../../examples/competition/evidence/).

Bedrock is optional and reachable only with model ID, AWS region, and explicit `--allow-network`; the local evidence claims no cloud operation.

## Quick Start

```powershell
python -m pip install -e ".[transform]"
python -m folderhome plugins validate --json
python -m folderhome run synthetic --json --report-file run-reports\demo.json
python -m folderhome run fcsa-plan --config-dir examples\fcsa\config `
  --provider-root ..\file-collect-sort-action `
  --report-file run-reports\fcsa-demo.json --json

$demoState = Join-Path $env:TEMP "folderhome-demo-state"
python -m folderhome documents ingest `
  --source-dir examples\documents\inbox --state-dir $demoState `
  --approve-index-write --result-file run-reports\ingest.json `
  --report-file run-reports\ordnerbericht.md --json
python -m folderhome documents search --state-dir $demoState `
  --query "Ich suche nach einem Dokument über meine Krankenversicherung." --json
python -m folderhome documents dossier --state-dir $demoState `
  --topic Krankenversicherung --output-file run-reports\dossier.md --json
python -m folderhome app plan --profiles-dir examples\profiles `
  --state-dir $demoState --port 8765 --json
python -m folderhome app serve --profiles-dir examples\profiles `
  --state-dir $demoState --port 8765 --approve-loopback-server --json
python -m folderhome documents versions --state-dir $demoState `
  --query "Was ist meine neueste Krankenversicherung?" `
  --output-file run-reports\versionen.json --json
python -m folderhome profiles validate --profiles-dir examples\profiles --json
python -m folderhome profiles resolve --profiles-dir examples\profiles `
  --profile lukas --area versicherungen --json
python -m folderhome documents plan --profiles-dir examples\profiles `
  --profile lukas --area versicherungen `
  --source-file examples\documents\inbox\Krankenversicherung.txt `
  --target-root "$demoState\Ablage" --as-of 2026-08-21 --json
New-Item -ItemType Directory -Force "$demoState\Ausgabe" | Out-Null
python -m folderhome documents bundle `
  --source-dir examples\documents\inbox `
  --output-file "$demoState\Ausgabe\Dokumente.txt" --format txt `
  --approve-output-write --json
python -m folderhome documents package `
  --source-dir examples\documents\inbox `
  --output-zip "$demoState\Ausgabe\Dokumentpaket.zip" `
  --approve-output-write --json
$beforeSnapshot = (python -m folderhome folders snapshot `
  --source-dir examples\documents\inbox `
  --captured-at 2026-08-21T20:30:00Z `
  --state-dir $demoState --approve-state-write --json | ConvertFrom-Json).snapshot_file
$afterSnapshot = (python -m folderhome folders snapshot `
  --source-dir examples\documents\inbox `
  --captured-at 2026-08-21T20:31:00Z `
  --state-dir $demoState --approve-state-write --json | ConvertFrom-Json).snapshot_file
python -m folderhome folders diff `
  --before-file $beforeSnapshot --after-file $afterSnapshot --json
python -m folderhome folders scan `
  --config-file examples\observation\watched-folders.json `
  --watch-id synthetic_inbox --captured-at 2026-08-21T20:45:00Z `
  --state-dir $demoState --json
python -m folderhome folders routine-plan `
  --config-file examples\observation\watched-folders.json `
  --watch-id synthetic_inbox --captured-at 2026-08-21T21:45:00Z `
  --state-dir $demoState --profiles-dir examples\profiles `
  --target-root "$demoState\Ablage" --as-of 2026-08-21 `
  --mode changes --json
python -m folderhome folders routine-queue `
  --config-file examples\observation\watched-folders.json `
  --bindings-file examples\observation\routine-bindings.json `
  --captured-at 2026-08-21T21:46:00Z --state-dir $demoState `
  --profiles-dir examples\profiles --as-of 2026-08-21 --json
python -m folderhome scheduler plan `
  --task-name folderhome_routine_queue --interval-minutes 30 `
  --start-at 2026-08-22T08:00:00+02:00 --timezone Europe/Berlin `
  --config-file examples\observation\watched-folders.json `
  --bindings-file examples\observation\routine-bindings.json `
  --profiles-dir examples\profiles --state-dir $demoState --json
python -m folderhome contacts plan `
  --source-dir examples\documents\contacts --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas --area versicherungen `
  --approve-sensitive-local-read --json
python -m folderhome calendar plan `
  --source-dir examples\documents\calendar `
  --calendar-config examples\calendar\calendar-config.json `
  --profiles-dir examples\profiles --state-dir $demoState `
  --profile lukas --area gesundheit `
  --planned-at 2026-08-22T00:30:00+02:00 `
  --approve-sensitive-local-read --json
python -m folderhome calendar connectors --json
python -m folderhome calendar connector-plan `
  --source-dir examples\documents\calendar `
  --calendar-config examples\calendar\calendar-config-google.json `
  --profiles-dir examples\profiles --state-dir $demoState `
  --profile lukas --area gesundheit `
  --planned-at 2026-08-22T04:20:00+02:00 `
  --connector-accounts examples\calendar\connector-accounts.json `
  --connector-request examples\calendar\connector-request-google.json `
  --approve-sensitive-local-read --json
python -m folderhome findcall plugins --json
python -m folderhome findcall plan `
  --request-file examples\findcall\request-werkstatt.json `
  --candidates-file examples\findcall\candidates-werkstatt.json `
  --planned-at 2026-08-22T01:00:00+02:00 --json
python -m folderhome findcall simulate `
  --request-file examples\findcall\request-werkstatt.json `
  --candidates-file examples\findcall\candidates-werkstatt.json `
  --fixture-file examples\findcall\fixtures-werkstatt.json `
  --planned-at 2026-08-22T01:00:00+02:00 --json
python -m folderhome finance plan `
  --source-dir examples\documents\finance --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas `
  --approve-sensitive-local-read --json
python -m folderhome inventory plan `
  --source-dir examples\inventory\bestand --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas `
  --approve-sensitive-local-read --json
python -m folderhome medication plan `
  --source-dir examples\medication\plans --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas `
  --approve-sensitive-local-read --json
python -m folderhome health dossier `
  --source-dir examples\health --profiles-dir examples\profiles `
  --profile lukas --as-of 2026-08-22 `
  --approve-sensitive-local-read `
  --output-markdown "$demoState\Gesundheitsdossier.md" `
  --output-json "$demoState\Gesundheitsdossier.json" --json
python -m folderhome documents ingest `
  --source-dir examples\contracts\documents --state-dir $demoState `
  --approve-index-write --json
python -m folderhome contracts cockpit `
  --request-file examples\contracts\cockpit-hyundai-i10.json `
  --state-dir $demoState --profiles-dir examples\profiles `
  --approve-sensitive-local-read `
  --output-markdown "$env:TEMP\FolderHome-Vertragscockpit.md" `
  --output-json "$env:TEMP\FolderHome-Vertragscockpit.json" --json
python -m folderhome correspondence preview `
  --request-file examples\correspondence\insurance-cancellation.json `
  --designs-file examples\correspondence\designs.json `
  --templates-file examples\correspondence\templates.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome correspondence render `
  --request-file examples\correspondence\insurance-cancellation.json `
  --designs-file examples\correspondence\designs.json `
  --templates-file examples\correspondence\templates.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read `
  --markdown-file "$env:TEMP\FolderHome-Brief.md" `
  --text-file "$env:TEMP\FolderHome-Brief.txt" `
  --approve-output-write --json
python -m folderhome artifacts plan `
  --request-file examples\artifacts\artifact-request.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome artifacts design-preview `
  --request-file examples\artifacts\design-request.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome mail providers --json
python -m folderhome mail ingest-plan `
  --accounts-file examples\mail\accounts.json `
  --request-file examples\mail\ingest-request.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome notes providers --provider-root ..\llm-note --json
python -m folderhome notes guide `
  --request-file examples\notes\create-request.json `
  --profiles-dir examples\profiles --state-dir $demoState `
  --provider-root ..\llm-note --json
python -m folderhome tax providers `
  --provider-root ..\steuer-assistent --json
python -m folderhome briefing plan `
  --request-file examples\briefing\briefing-request.json `
  --profiles-dir examples\profiles `
  --output-file "$demoState\Morgenbrief.html" `
  --desktop-file "$env:TEMP\Desktop\Morgenbrief.html" `
  --approve-sensitive-local-read --json
python -m folderhome notices inspect `
  --source-file examples\notices\Bescheid.txt `
  --profiles-dir examples\profiles --profile lukas `
  --received-on 2026-08-21 --as-of 2026-08-22T12:00:00+02:00 `
  --approve-sensitive-local-read --json
python -m folderhome drafts preview `
  --request-file examples\notices\objection-draft-request.json `
  --source-file examples\notices\Bescheid.txt `
  --designs-file examples\correspondence\designs.json `
  --templates-file examples\notices\administrative-templates.json `
  --profiles-dir examples\profiles --received-on 2026-08-15 `
  --as-of 2026-08-22T06:00:00+02:00 `
  --approve-sensitive-local-read --json
python -m folderhome benefits check `
  --profile-facts-file examples\benefits\Lukas-benefit-profile.json `
  --catalog-file examples\benefits\official-routing-catalog.json `
  --profiles-dir examples\profiles `
  --as-of 2026-08-22T07:00:00+02:00 `
  --max-source-age-days 30 --approve-sensitive-local-read --json
python -m folderhome legal compare `
  --before-file examples\legal\before.json `
  --after-file examples\legal\after.json `
  --interests-file examples\legal\Lukas-interests.json `
  --as-of 2026-08-22T08:00:00+02:00 `
  --max-source-age-days 7 --approve-sensitive-local-read `
  --allow-test-fixture --json
```


The intentionally separated approval and apply sequences are in the [Kontaktregister-Workflow](../../workflows/contact-register.md), the [Kalender-Handoff-Workflow](../../workflows/calendar-handoff.md), the [Finanz-Workflow](../../workflows/finance-import.md), and the [Inventar-Workflow](../../workflows/inventory-import.md). The separate plan/confirmation flow for income is in the [Medikamenten-Workflow](../../workflows/medication-intake.md). Preview and controlled letter output is described by the [Korrespondenz-Workflow](../../workflows/correspondence-studio.md). Office/media routing and local design outputs are in the [Artefaktstudio-Workflow](../../workflows/artifact-studio.md). Read‑only mailbox retrieval, contact binding, and separate dispatch are described by the [Mail-Workflow](../../workflows/mail-connector.md). Guided personal notes, approval, and append‑only history are described by the [Notiz-Workflow](../../workflows/personal-notes.md). Confirmed tax receipts and the separately approved private ZIP export are described by the [Steuer-Workflow](../../workflows/tax-workpaper.md). Local weather and news snapshots as well as the separate desktop delivery are described by the [Briefing-Workflow](../../workflows/daily-briefing.md). Evidence‑bound notice understanding without legal review is described by the [Bescheid-Workflow](../../workflows/official-notice-understanding.md). Controlled local objection, response, and application drafts are described by the [Verwaltungsentwurf-Workflow](../../workflows/administrative-drafts.md). The local orientation run and official next review steps are described by the [Leistungsvorcheck-Workflow](../../workflows/benefit-screening.md). Technical standard changes and non‑binding profile/contract review candidates are described by the [Rechtsänderungs-Workflow](../../workflows/legal-change-monitor.md). The finitely bounded Strands loop and its two read‑only tools are described by the [Agenten-Workflow](../../workflows/strands-agent.md).

## Development Review

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m folderhome plugins validate --json
.venv\Scripts\python.exe _tools\doc-lint
.venv\Scripts\python.exe _tools\workflows-sync --check
```


## Repository Boundaries

```text
src/folderhome/       neuer Wettbewerbskern einschließlich installierbarer Bridges
bridges/              Provider-Dokumentation und Integrationsgrenzen
skills/               neue agentische Skills
manifests/            Komponenten- und später Stack-Manifeste
reused/               gepinnte Referenzen auf vorbestehende Komponenten
tests/                Vertrags-, Sicherheits- und Integrationstests
examples/synthetic/   ausschließlich synthetische Beispieldaten
examples/documents/   synthetischer Dokumentenbestand für die lokale Demo
examples/profiles/    synthetische Profile und Regelvererbung
examples/inventory/   synthetische Bestandsaufnahmen
examples/medication/  synthetische Medikamentenpläne
examples/health/      synthetische Gesundheitsdokumente
examples/mail/        synthetische Konten und read-only Ingest-Anfrage
examples/notes/       synthetische persönliche Notizanfrage
examples/tax/         synthetischer Beleg und sichere Anfragevorlage
examples/briefing/    synthetische Wetter- und Nachrichtensnapshots
examples/notices/     synthetischer Bescheidfall ohne echte Personendaten
examples/benefits/    synthetisches Leistungsprofil und amtliche Handoffs
examples/competition/ reproduzierbare synthetische Strands-Evidenz
examples/contracts/   synthetischer Versicherungs- und Vertragsfall
examples/correspondence/ synthetische Briefvorlage, Designs und Anfrage
examples/artifacts/   synthetischer Office-/Medienplan und lokales Designset
```


The precise classification is in [`COMPETITION_CODE_MAP.md`](../../COMPETITION_CODE_MAP.md), the revisions and licenses in [`THIRD_PARTY_LICENSES.md`](../../THIRD_PARTY_LICENSES.md).

## Security Boundaries

- Side effects are blocked by default.  
- FCSA performs no real file, network, or telephone actions.  
- The FCSA dry run uses a temporary shadow state and therefore does not confirm any later live run in the production FCSA state.  
- The document ingest writes only after an explicit CLI gate to a specified local index folder; sources are never archived, moved, or overwritten.  
- Document search uses a read‑only SQLite access and leaves the KnowledgeDigest index file byte‑exactly unchanged.  
- Version analyses prefer explicit contract data, explain weaker filename/modification‑date fallbacks, and treat older FCSA versions only as unapproved, reversible dry‑run plans.  
- Profiles are merely organizational preferences within the same OS account. The fixed inheritance is global → domain → profile → profile‑area; peer‑level conflicts block resolution and `hard_delete` is prohibited.  
- Document action plans specify for each step the rule source, target, provider, gate, and rollback. Naming, sorting, converting, archiving, and trash remain unapproved; target conflicts are visibly blocked.  
- Archiving and trash steps are validated against the real pinned FCSA dry run. PDF/TXT are planned by the new transformation core; other target formats remain blocked without a verified provider.  
- The new transformation core bundles selected sources as UTF‑8 TXT or PDF. PDF pages are preserved, images are rasterized, and other documents are reconstituted from extracted text; any layout loss is recorded in the plan. No output is written without `--approve-output-write`.  
- Transformations are published atomically, never overwrite, re‑verify all source hashes before writing, and do not modify originals. An original action becomes unlockable only after a verified output hash.  
- `documents package` groups a folder by file type: images and PDFs each become a PDF, text/Markdown and other extractable types each become a TXT. A deterministic ZIP contains all group outputs and a manifest; unknown formats remain inside with hash and reason visible.  
- `folders snapshot` stores only path, file size, timestamp, and SHA‑256 after an explicit state gate. `folders diff` distinguishes new, removed, modified, and only uniquely‑hashed moved files.  
- A manual move is only performed together with an earlier storage receipt for the learning candidate. `folders learning` writes nothing and never automatically adopts a rule.  
- `folders scan` binds these building blocks to a declarative observation profile. It finds the last verified checkpoint of the same root, reports interval expiry, diff, and learning candidates in an audit report, and writes a new immutable checkpoint only with `--approve-state-write`.  
- `documents execute` rebuilds the plan from source and profile. Only if the specified plan ID and a seamless prefix of concrete action IDs match may `--approve-file-write` execute rename/move steps. Source and each intermediate target are re‑hashed; existing targets are never overwritten.  
- Each execution writes an immutable intent before the file action and then a completion report plus storage receipt without raw text. `documents undo` requires its own approval bound to execution ID and hash and blocks if the target is changed or the audit is tampered with.  
- `folders cleanup-plan` creates deterministic individual plans and a shared batch ID for an entirely explicitly selected folder. Unsupported files remain visible with hash and reason; shared targets, existing targets, and source‑target dependencies block affected documents before any execution.  
- `folders cleanup-execute` reads a standalone approval file and executes only the document/plan/action combinations listed there. If a later document fails, already completed document actions are rolled back and the batch is logged as `rolled_back` or `failed`.  
- `folders routine-plan` links a watch with its last checkpoint and a filtered cleanup plan, but writes neither checkpoint nor file. `changes` schedules only due new, modified, or uniquely moved files; `full` explicitly checks the full inventory.  
- `folders routine-execute` requires the same exact batch approval as well as file and state gates. Before the first change, the watch history and folder state are re‑checked. Only after a successful batch does the new checkpoint follow; if it fails, file actions are rolled back.  
- A routine target within the observed input is blocked so that moved files are not processed again as input.  
- `folders routine-queue` reads watch and binding configuration together and outputs all active watches as `ready`, `not_due`, `empty`, or `blocked`. Overlapping inputs, targets in another observed input, and shared action targets block affected queue entries.  
- The queue writes neither files nor state, registers no scheduler, and therefore intentionally has no approval or installation flag.  
- `scheduler plan` serializes a portable argument vector and a Windows task XML, but performs no installation. The plan references `registration_performed=false` and `installation_supported=false`.  
- `scheduler run` requires a tight scheduler‑state gate, locks only its own schedule ID, and writes an append‑only queue report. Exit codes distinguish idle (0), approval needed (10), blocked (20), and an already running or unresolved run (30).  
- An existing scheduler lock is neither taken over nor automatically removed. The lock applies only to operational FolderHome state, never to observed folders or user documents.  
- `contacts plan` stores neither document raw text nor register state. Labeled contact fields remain bound to document ID, source hash, and precise line evidence; contradictory latest contacts block planning.  
- `review_required` requires its own gate for local contact extraction. This permits no external sharing; `blocked` and `not_checked` remain locked.  
- `contacts apply` re‑checks plan, register revision, and source hash and writes only after `--approve-state-write` a SQLite transaction with append‑only events. No automatic delete operation exists.  
- `calendar plan` detects only labeled appointment fields and explicitly references `completeness_guaranteed=false`. Backend and timezone follow configuration fallback and the same profile inheritance as document rules.  
- `calendar apply` rebuilds the plan and binds approval to plan ID, calendar revision, and concrete actions. Sources, targets, and content hashes are re‑checked before each execution.  
- `folderhome_local` writes an event and append‑only audit after a state gate in a SQLite transaction. Identical UIDs are handled in the next plan `noop`; time conflicts remain blocked.  
- `uptoday_ics` publishes, after separate state and output gates per candidate, only a new deterministic ICS file. A batch error rolls back its own unchanged outputs. UpToday is neither called nor imported. Routinika and Google remain blocked without their own verified connector.  
- `calendar connector-plan` inherits candidates, profile rule source, and timezone from Phase 17. UpToday delegates further to ICS; Routinika remains blocked; Google generates only a compliance‑required handoff with explicit calendar ID, solo participant list, offset times, and reminder structure.  
- `calendar connector-simulate` runs only with two explicit synthetic switches. The fixture provider uses neither network nor a real calendar; update and delete remain locked without a provider event reference.  
- `findcall plugins` imports only the local dry‑run seams of the precisely pinned, clean HungryCall and Ringedingeding checkouts. No live transport is constructed.  
- FindCall adopts HungryCalls' serial early‑stop pattern into a new provider‑neutral core; restaurant models are not misused for medical practices or workshops. Ringedingeding remains the separate plugin for multi‑person polls and appointment voting.  
- `findcall simulate` accepts only a provider with `simulated=true`, without network or telephone effect. Results preserve call status and rejection reasons, mask phone numbers, and must not generate a booking, order, or price quote at `inquiry_only`.  
- Account statements use the existing doc‑services extraction and a tight declarative V1 format. Amounts are integer cents; opening balance plus transactions must exactly equal the ending balance.  
- `finance apply` rebuilds the plan, checks approval, financial revision, and source hash, and adds account, statement, transactions, and an append‑only audit in a SQLite transaction. There is no bank access nor delete operation.  
- `finance coverage` displays only covered statement ranges and gaps. `finance period` reports balances only when there is full coverage and continuous adjacent statements; it does not interpolate.  
- `finance recurring` groups only cent‑equal monthly charges with at least two receipts. Active/inactive, follow‑month window, and annual sum are candidates/forecasts, not contract or payment evidence.  
- `inventory plan` normalizes to at most three decimal places without rounding and writes nothing. Contradictory observations of the same item and day are blocked before approval.  
- `inventory apply` binds approval, inventory revision, concrete actions, and source hashes. The local store adds only events and audit; a current view is derived from history.  
- `inventory needs` reports under‑stock and expiration dates only as compliance‑required candidates. FolderHome orders nothing and does not claim a complete household inventory.  
- `medication plan/apply` adopts only documented schedules and binds each version to profile, source, hash, line evidence, revision, and approval.  
- `medication day` generates stable dose IDs without write‑on‑read. Status values distinguish upcoming, confirmation pending, and explicitly confirmed, without guessing an actual intake.  
- `medication confirm` adds exactly one idempotent intake event after a state gate. Inventory, calendar, messages, and reminders remain unchanged; medical accuracy is not claimed.  
- `health dossier` reads only after local sensitivity approval. A red provider finding is processed only if all red findings exclusively involve health data; other red patterns remain blocked. Timeline and conflicts remain extractive and source‑bound.  
- `contracts cockpit` reads the shared state only after sensitivity approval and links only explicitly configured terms. It changes neither state nor source files and performs no archiving, contact, calendar, banking, or payment operation.  
- `correspondence preview` reads request data only after sensitivity approval. Only simple safe placeholders are allowed; `render` writes Markdown/TXT only after a separate output gate as a never‑overwrite batch. DOCX/ODT, shipping, printing, and remote providers are omitted.  
- `artifacts plan` does not invoke Office skills nor ai‑media‑editor and keeps missing runtime/render gates visible. Local design tokens and SVG are written only after sensitivity and output gates; each concrete card requires its own visual review before printing or publishing.  
- `mail ingest-plan` contains only header and optional attachment retrieval. A deviating or altered provider checkout is blocked; moving, deleting, tagging, and sending are not ingest operations.  
- Mail drafts bind active contact ID, recipient address, correspondence preview ID, and text hash. Sending requires an exact approval and a one‑time ledger reservation; a real SMTP transport is not yet implemented or tested.  
- `notes guide` reads the pinned `llm-note` history without write‑on‑read and keeps questions and suggestions strictly separate from human‑verifiable content. A remote LLM is not invoked in Phase 28.  
- `notes apply` binds approval to plan, action, content hash, and store revision and attaches exactly one version via the public `llm-note` API. Edit and revert do not overwrite or delete an earlier version.  
- Document and calendar references are only taken over explicitly. Profiles organize the notes; only the operating system account remains the security boundary.  
- `tax receipt-plan` binds a receipt to document hash, profile, optionally a matching financial entry, and the current provider store. A category candidate is not executable without human confirmation.  
- `tax receipt-apply` writes exactly one confirmed receipt via the public provider API. `tax export` requires a separate approval and creates only a new private ZIP tax worksheet; tax consulting, official format, and portal transmission are excluded.  
- `briefing plan` reads local weather and news snapshots after sensitivity approval, marks outdated data, and generates deterministic HTML only in memory. Live connectors remain visibly blocked.  
- `briefing render` and `briefing deliver` have separate approvals and write gates. The desktop copy must exactly match the rendered hash; a scheduler is not registered.  
- `notices inspect` adopts only known, explicitly labeled notice information and binds it to line, document ID, and source hash. Relative deadline wording is not recalculated; `notices render` writes only new reports and performs no legal review or response.  
- `drafts preview` keeps document evidence and provided information separate, enforces a visible draft notice, and uses the existing correspondence core. `drafts render` requires an exact content approval; performance verification, legal review, and sending are not implemented.  
- `benefits check` uses a dated, incomplete routing catalog and local user data. Outdated sources are blocked; appropriate routes point only to official pre‑checks. Claim, amount, application, and web call remain excluded.  
- `legal providers` does not load a legal‑review agent but only qualifies the clean pinned `law-checker` checkout and its registry. `legal compare` processes already acquired local snapshots; topic matches are exclusively `review_candidate`. Legal effect, affected parties, deadlines, network, and notification remain excluded.  
- OCR, external LLM syntheses, and real user folders are not part of the current synthetic acceptance.  
- The Strands agent in the competition version has exactly two profile‑specific read‑only tools. Prompt, response, tool result, turns, tool calls, and output tokens are tightly limited; the fixture run remains without network or side effects.  
- Health, legal, and financial functions are intended as administrative assistance, not as diagnosis or binding advice.  
- OS accounts form the security boundary; family profiles are merely organizational rules within an account.

## License

FolderHome is intended for release under the MIT license. Until explicit approval, this repository remains local and without remote.
