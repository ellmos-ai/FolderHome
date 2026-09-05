# Changelog

**English** | [Deutsch](./CHANGELOG.de.md)

**Current short version:** 0.52 / 2026-08-27  
**Direct predecessor:**  
[`docs/archive/CHANGELOG-through-phase35.md`](./docs/archive/CHANGELOG-through-phase35.md)

All relevant changes are documented in this file. The detailed phase‑by‑phase history up to Phase 35 remains unchanged in the archive.

## [Unreleased]

_Nothing yet._

## [0.3.0] - 2026-09-05

### Added
- profiles are managed in the installer: section 1 lists them, adds one, renames
  one, edits its rules and deletes one behind a confirmation. Until now the
  answer to "can I delete an example profile and add my own?" was no, the
  browser could only read them
- the installer owns a profile folder, by default `<configuration folder>\profiles`
  instead of the `examples\profiles` of this repository, and starts even when
  that folder is still empty. A first run offers to copy the shipped examples or
  to begin with an empty list; the examples themselves stay a template and are
  refused as a write target
- deleting a profile cascades in the same plan: folder bindings that would then
  belong to nobody fall away, its calendar accounts leave
  `calendar-accounts.json`, and the preview names everything that goes. At least
  one profile has to remain, and the file itself moves into a dated
  `.deleted-<timestamp>` folder rather than being removed
- household and profile documents travel the existing plan and confirm path: the
  plan hash covers them, each is staged, read back through
  `parse_profile_configuration` and only then put in place, and a profile file
  name is derived from the validated id, never from typed text
- `--profiles-dir` is optional for `setup plan` and `setup serve`

## [0.2.0] - 2026-09-05

### Added
- results view: what a confirmed plan really executed stays retrievable in the
  local GUI, including runs started through the HTTP API or an editor over MCP,
  because all three drive the same process. New panel with a refresh button,
  reloaded automatically after an own confirmation
- new read-only routes `GET /api/v1/agent/results` and
  `GET /api/v1/agent/results/<execution_id>/artifacts/<index>`; the list carries
  basename, size and index but never a path, and the file is served as an
  attachment addressed only by that index
- executed reports are kept in a bounded in-process ring buffer; artifacts are
  resolved once at execution time and only inside a registered output resource
  of that profile, under the name the report itself declares
- MCP tool `folderhome_results` proxies the same list for editor agents
- the GUI downloads through the token-protected API and builds the file from a
  blob, so no token ever appears in a URL or in browser history

- installer section "Subscriptions" between the model and the API keys: Claude
  Code with a Claude subscription and the Codex CLI with a ChatGPT subscription
  drive FolderHome as a tool, so the agent is the brain and FolderHome needs no
  key of its own. Both editor entries are shown ready to copy, taken from the
  same `integration_plan` that `mcp plan` prints instead of being written a
  second time. The section is instructions only: it starts no server, writes no
  file and touches no plan hash
- `llms.txt` at the repository root and published under `site/`, in the shape of
  llmstxt.org: attaching over MCP, calling the loopback HTTP API, what the safety
  model refuses, which providers exist, and where the long documents are
- a test reads every route, schema and tool name out of `llms.txt` and asserts
  each one exists in the service, that the published copy is byte-identical, and
  that no key, token or real path is in it

- one finite HTTP budget for every provider that speaks HTTP:
  `model_timeout_seconds` (default 120, CLI `--model-timeout-seconds`) reaches
  the Ollama, Anthropic and OpenAI clients alike, and a timeout is reported as a
  stated failure naming the budget instead of a hang. Bedrock keeps its own
  connect and read pair
- the installer refuses a plan the loader would reject during the check, not
  only when saving: reading and checking are separate in all three loaders, so
  the real contracts run over the documents while they are still in memory and
  the error appears at its own field
- `configured` now means that the registry loads, not that a file exists
- installer fix: `calendar.export_output` ends in `_output`, not `.output`, so the
  suffix guess left it without operations. The written registry no longer loaded,
  the save answered 400, and both files were already on disk without a backup on
  a first install. An explicit purpose-to-operations table replaces the guess,
  and the export folder gets `create` plus `cloud_context: deny`
- the installer now stages every file it is about to write, loads each one back
  through its own contract, and replaces the live files only afterwards; a plan
  that turns out unloadable leaves the previous state exactly as it was
- installer usability: the save button is called Save and one line under it says
  that nothing is stored automatically. Every folder field can ask the operating
  system for a directory (`POST /api/v1/setup/pick-folder`, one dialog at a time,
  501 without a dialog toolkit, so typing a path stays the fallback)
- a source purpose takes several folders; the first one becomes the profile
  default and the agent sees all of them in its catalogue. Reopening the
  installer lists every configured source instead of the default alone
- installer writes `calendar.json` and `calendar-accounts.json` when that section
  is enabled, through the same confirm, verify and replace path. There is no
  Outlook backend in this build, so none is offered, and `app serve` reads
  neither file: only the `calendar` commands do
- hosted model providers `anthropic` and `openai`, with the same two approvals as
  Bedrock and `--openai-base-url` for a compatible endpoint. An API key is not a
  setting: it is read from `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` at model build
  time and appears in no plan, status, report or log
- the installer stores those keys in a `.env` beside `launch.json`, owner-only,
  keeping every other line of that file and leaving no backup of a key; the state
  answers only whether a key is stored. `app serve --launch-config` fills those
  two names into the environment when they are not already set
- model presets in `launch.json` (`model_presets`, `model_preset`): save several
  model choices, activate one, delete one. Start-up precedence is explicit and
  tested, an explicit flag over a flat field over the active preset
- a static test checks that the installer page references only ids and text keys
  that exist and that both languages carry the same keys; it found the cloud card
  printing its own key names for want of a translation
- separate installer `folderhome setup serve`: a second loopback application on
  its own port and token is the only place that writes FolderHome configuration.
  The app GUI keeps no write path to it
- the installer plans first and writes only against the hash of exactly the plan
  it displayed, with an explicit confirmation; folders are checked for existence,
  symbolic links and location inside the user's own folder beforehand
- it writes `resources.json` and `launch.json` atomically through a temporary
  file, keeps the previous version as `.bak-<timestamp>` and loads the written
  registry back through the existing contract before reporting success
- provider fields are validated by constructing the real `StrandsAgentSettings`
  instead of a second rule set; no password and no mailbox credential is ever
  written
- `app serve --launch-config <file>` takes those start-up values as defaults. An
  explicit flag always wins, and the gates are not on the allowlist, so no file
  can grant network access, a cloud data approval or a listener
- cloud variant delivers result files inline: the AgentCore runtime answer now
  carries `content`, `content_type` and `content_encoding` per result, so the
  browser can offer a download although that runtime exposes only `/ping` and
  `/invocations` and no file route. No API Gateway and no S3 were added
- two honest limits: a file above 262 144 bytes travels as metadata only
  (`inline: false`, reason `size_limit`), and a file whose text contains the
  workspace path is withheld the same way (reason `local_paths`) rather than
  shipping local paths to a browser
- the public walkthrough builds the download from that inline content and falls
  back to the local file route when a result carries none
- local model provider `ollama`: the master agent can run on a model in the
  user's own home instead of the deterministic fixture or Amazon Bedrock. The
  gate follows the transport, not the vendor: a loopback host needs no approval
  because nothing leaves the machine, while any other host needs the same two
  approvals as Bedrock, `--allow-network` and `--approve-sensitive-cloud-data`
- new CLI options `--model-provider ollama`, `--ollama-host` (default
  `http://127.0.0.1:11434`) and `--ollama-model-id`; the model id is always
  explicit and never guessed
- new settings properties `network_used` and `is_live_model` separate the
  transport question from the provider question; the agent report, the live-turn
  counter and the status payload now ask them instead of comparing a provider
  name to `"bedrock"`
- status and GUI name a local model as a local model: `model_inference_location`
  reports `local_ollama_host` or `remote_ollama_host` instead of `aws_cloud`,
  and the interface no longer announces a running Ollama model as configured
  Amazon Bedrock
- optional extra `folderhome[ollama]`; the provider is imported only when it is
  selected, and a missing package fails closed with the install command
- MCP server `folderhome mcp serve`: Claude Code and the Codex CLI can use the
  bounded FolderHome surface as a tool over stdio. The server keeps no state of
  its own but proxies the loopback API of a running `app serve`, so an editor
  agent and the GUI share one process, one conversation and one set of proposed
  plans
- ten MCP tools behind the `folderhome_` prefix for status, profiles,
  capabilities, executors, resources, document search, topic dossier, chat, plan
  confirmation and conversation reset; a refusal from the local API reaches the
  editor verbatim
- `folderhome mcp plan` prints the ready-made `claude mcp add` command and the
  matching `[mcp_servers.folderhome]` block for `~/.codex/config.toml` without
  starting anything
- the MCP proxy fails closed before it starts: only `127.0.0.1` is accepted, a
  session token is required, and `--approve-mcp-server` must be given. stdout
  belongs to the transport, so every diagnostic and every error goes to stderr
- draft-only mail endpoint: one prepared letter is appended to the drafts
  folder of the user's own IMAP mailbox behind the separate live-effect
  approval `--approve-mail-draft`; there is no send path, no recipient is
  contacted, and the mailbox password is read only at execution time from its
  configured local file
- mailbox folder names are configured the way a mail program shows them:
  `Entwürfe` is accepted and encoded to the RFC 3501 wire name `Entw&APw-rfe`,
  so appending into a non-ASCII drafts folder works at all
- the drafts folder is verified against the mailbox's own folder list before an
  append, and a missing folder aborts with the folders that do exist
- two password sources: the operating system keyring (`keyring_service` plus
  `keyring_user`) or a local file (`password_file`); the value never reaches a
  log, a plan, a report or an error message
- private registry purpose `mail.draft_account` plus the strict configuration
  schema `folderhome.mail-draft-account.v1`; without such a resource the mail
  endpoint stays honestly `not_connected`
- local SQLite draft ledger that reserves a deterministic idempotency key
  before the append, so the same draft cannot land twice in the same mailbox
- capability recipes: a declarative journey over existing endpoints resolves
  into one hash-bound multi-step plan with a single `/confirm`, while every step
  keeps its own adapter, request schema and gates
- deterministic recipe review signed by every involved expert (one for a single
  domain, all of them across domains); the endorsement is part of the plan hash,
  so confirming the plan confirms the review
- declared handoff edges that bind two steps to the same logical resource ID; no
  value from a step report is ever substituted into a later request
- sequential chain execution that stops at the first failure and reports which
  steps ran, which one broke and which were never attempted
- packaged `accident-aftercare` recipe (contact, claim letter, mail draft,
  calendar appointment with ICS export) plus `folderhome recipes list|plan|run`
- one generated capability index (`folderhome.application.capability_index`)
  that joins the endpoint catalog, the adapter request schemas and a short
  purpose exactly once, and feeds both the compact master-agent prompt
  excerpt and the generated `CAPABILITY-INDEX.md` / `.de.md`
- `_tools/capability-index` with `--check`, so the documented index cannot
  drift away from the code
- optional ICS export on the local calendar endpoint: the recorded
  appointments are written as one private RFC 5545 file into a registry-bound
  output directory (purpose `calendar.export_output`), hash-bound by the same
  confirmation, never overwriting, and rolled back if the calendar state write
  fails; no calendar connector is involved
- one-command, token-gated synthetic Hyundai i10 accident demo over the real
  Strands search path and four existing typed workflow adapters
- English-default bilingual accident-demo UI with persistent light/dark theme,
  exact plan confirmation, deterministic reset and downloadable local results
- standalone bilingual GitHub Pages showcase in `site/`, explicitly marked as
  a scripted synthetic browser walkthrough without backend execution
- optional Amazon Bedrock AgentCore HTTP adapter with `/ping`, `/invocations`,
  runtime-session isolation, bounded JSON input and path-free synthetic output
- ARM64 multi-stage AgentCore container candidate running as a non-root user
- English-default dashboard localization with a persistent English/German switch
- persistent light and dark dashboard themes with accessible keyboard controls
- bilingual runtime model-status card distinguishing deterministic fixture,
  configured-but-unverified Bedrock, and a Bedrock connection verified by a
  successful in-process model turn
- machine-readable local-only versus local-first-hybrid runtime topology;
  FolderHome state and workflows stay local while optional Bedrock inference
  uses the AWS cloud
- one GUI-first FolderHome master agent shared by browser and CLI, with
  one-shot `agent chat` and an in-process interactive `agent session`
- bounded process-local Strands conversation continuity per organizational
  profile, with GUI and CLI reset that also discards unconfirmed plans and
  their unexecuted typed envelopes
- semantic expert selection, explicit fail-closed workflow endpoint resolution and style-only personas
- on-demand specialist agents restricted to one planning endpoint
- separate hash-bound GUI/API plan confirmation without false execution claims
- typed, fail-closed executor catalog for all 33 master workflows, with visible
  connected, direct-read-only, planning-only and not-connected states
- first end-to-end chat execution adapter for the existing append-only llm-note
  personal-notes workflow, including one-time replay protection and a domain report
- second end-to-end GUI/CLI chat adapter for confirming an existing scheduled
  medication dose, reusing the revision-bound medication workflow without
  exposing state paths, providing medical advice, or changing medication
- closed machine-readable request schemas in the executor catalog and bounded
  specialist prompt for every connected adapter
- private, schema-validated logical resource registry with profile scope,
  purpose binding, least-privilege operations and a model-safe path-free catalog
- 23 typed resource-ID adapters completing the local document and assistance
  stack: document actions, cleanup, observation, packages, routines, FCSA,
  contacts, correspondence, local calendar, contracts, design, health, finance,
  social law, inventory, tax and Daily Briefing
- fail-closed runtime classification of the three remaining gaps: mail,
  external calendars and scheduler registration require configured external
  connectors with separate live-effect approvals
- typed, approval-bound execution of the existing strictly local FindCall
  fixture cascade, with masked numbers and no network, calls, booking, or
  commitment
- real, finally limited Strands agent with profile‑specific document search and topic dossier
- deterministic no‑network model adapter over the public Strands‑ `Model` interface
- optional Amazon Bedrock path with separate network and data transfer gates
- explicit Bedrock connect/read timeouts and one total SDK attempt per model call
- the AgentCore HTTP adapter now honors the same fail-closed Bedrock opt-in
  gate as the accident demo (`FOLDERHOME_AGENTCORE_MODEL_PROVIDER`,
  `FOLDERHOME_AGENTCORE_ALLOW_BEDROCK`,
  `FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA`), defaults to the local
  fixture model, and reports the active model provider and real
  `network_used` flag in every response instead of a hardcoded `false`
- reproducible synthetic competition demo with four hashed artifacts
- `agent plan`, `agent run`, `agent chat`, `agent session` and `demo run` in the CLI
- reusable resource budget contract for file count, bytes and runtime
- publisher‑bound HTTPS trust verification for official performance handoffs
- connection limits, socket timeout and overload rejection in the loopback server
- `SECURITY.md`, English submission package and 36‑phase completion audit
- new skills `folderhome-strands-agent` and `folderhome-master-agent` with their
  associated workflows
- Windows runtime dependency `tzdata==2026.3`

### Changed

- Runtime binds `strands-agents==1.53.0` exactly
- Dev dependency requires at least `pytest 9.0.3`
- Ingest, Snapshot, Transformation, Package, Contacts, Calendar, Finance, Cleanup, Health, Inventory and Medication use shared budgets
- README, architecture, feature analysis, provenance and license register updated to Phase 36
- Overly long project documents archived and replaced with short current versions with direct predecessor reference
- Workflow router updated to 33 playbooks
- English is now the default for 122 documentation pages; the preserved German versions use the `.de.md` suffix and include reciprocal language links
- Workflow router generation now synchronizes 33 English and 33 German playbooks without counting localized mirrors twice
- Local agent instructions, task lists, state files and implementation plans are retained locally but excluded from Git
- Submission materials aligned with the authenticated 2026-08-23 Devpost
  readback, including the current bonus-post title rule, credit deadline and
  the single end-to-end Hyundai i10 accident narrative
- 2026-08-26: post-submission state consolidated across README, submission
  packet and local operator files; obsolete draft, Pages, upload and submit
  gates were replaced by their authenticated completed state
- AgentCore documentation now distinguishes the deployed `READY` direct-code
  Runtime and verified fixture roundtrip from the still-unverified
  Bedrock-backed journey and disabled public browser path

### Fixed

- 2026-08-24: HungryCall, law-checker and Ringedingeding component-manifest
  pins were stale against their current public repository HEADs, causing
  fail-closed revision-mismatch failures in four automated tests; all three
  pins were refreshed to the verified current public HEADs
  (`82c28e2de95b1b0d0343a40adfd8585938c305f8`,
  `a5b0cd51bc3666962f2fae8017c855dea0a712a2`,
  `d80dd81a6d7bf64298d4ef290c3b54ab5f50e990`) and the affected tests pass
  again
- 2026-08-24: the local doc-services checkout moved to
  `e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2` during the same window; the
  doc-services pin in the manifest, third-party tables, phase documents and
  the manifest contract test was refreshed accordingly
- 2026-08-24: the public `gh-pages` showcase was missing `assets/`
  (logo, icon, favicon) and `runtime-config.js`, both referenced by the
  current `site/index.html`; the header logo failed to load. `gh-pages` now
  ships the complete current `site/` folder

### Security

- public showcase has no backend or network requests; the executable accident
  demo remains loopback-only behind a random session token
- AgentCore adapter accepts no household upload, arbitrary path, secret or
  external effect and separates session workspaces by one-way fingerprints
- GitHub Pages actions and the AgentCore Python base image are pinned to
  immutable revisions; the SHA-pinned CI dependencies are disclosed in the
  third-party registry
- Security scan of 357 files and 12/12 surfaces completed
- three findings fixed: unrestricted document processing, arbitrary official hosts and unrestricted loopback threads
- additional adversarial URL cases for trailing dot, percent‑encoding and explicit port added
- potentially sensitive local search hits may reach Bedrock only after a data transfer release separated from the technical network gate
- the downstream 66‑file delta audit confirmed this approval gap as the fourth, now fixed finding
- `pip-audit` after update of local testing tools without known vulnerabilities

### Verified

- 2026-08-26 live AWS readback: both CloudFormation stacks
  `CREATE_COMPLETE`; AgentCore Runtime `READY`, version 4, HTTP; public quota
  API key enabled; CloudFront `runtime-config.js` remains `enabled: false`
- EU Nova Micro remained `ACTIVE`, but applied on-demand quotas were zero. One
  16-output-token Converse request with no retry returned
  `ThrottlingException: Too many tokens per day`; no second model call and no
  `manage.py verify` were performed
- 2026-08-27 AWS recheck after a successful OAuth renewal: AgentCore remained
  `READY`, version 4, EU Nova Micro remained `ACTIVE`, and all three real-time
  quotas remained zero. CloudWatch showed one throttle and no successful
  invocation over 24 hours, so no further model request was sent
- AWS budget readback: 5 USD monthly limit and 0.018 USD calculated actual
  spend; the P-010 cumulative carry-over cap is not yet implemented
- Current full feature suite on the consolidated working tree based on HEAD
  `436928f`: 503 passed, zero failed in 370.04 seconds; its final manifest check
  also passed 10/10
- synthetic accident demo, local HTTP site, CLI start gate and AgentCore
  contract covered by focused automated tests
- AgentCore `/ping` and one prepare invocation passed as a real loopback HTTP
  process; no AWS resource was created
- public showcase inspected in Edge at 1440 × 1100; HTML/CSS/JavaScript and
  bounded Pages artifact tests passed
- 414 automated tests passed; three external live-checkout pin tests were
  deliberately deselected because the current local HungryCall and
  Ringedingeding revisions differ from their pinned manifests
- the final unfiltered run recorded `414 passed, 3 failed`; the final bounded
  product run recorded `414 passed, 3 deselected`
- English/light and German/dark dashboard states visually inspected at 1440 × 1100; focused GUI tests and JavaScript syntax check passed
- Ruff and Compileall with no findings
- 8/8 plugin manifests valid; the master-agent skill is covered by the current repository skill checks
- 33 workflows synchronized
- the configured EU Nova Micro inference profile was active, but the single
  bounded synthetic FolderHome turn returned neither response nor error within
  60 seconds; it was terminated without retry and is not claimed verified
- synthetic Strands run: two scenarios, no network, no side‑effects; repeat blocked at the Never‑overwrite gate
- Wheel contains agent, demo, resource budget, host verification and GUI
- a clean virtual environment installed the built wheel and executed the
  four-result accident journey plus AgentCore `/ping` without network use
- final wheel SHA-256:
  `8b5929c855226a4c2c78223b65e85adc12dcd4b5aa61445d010e7fdf8d0eb24a`

## Historical Milestones

| Phases | Result |
|---|---|
| 1–8 | integration core, FCSA, document library, versions, profiles, actions, transformation and type packages |
| 9–15 | folder monitoring, correction learning, scans, execution/undo, routines, queue and scheduler handoff |
| 16–21 | contacts, calendar, FindCall, finance, household and medication |
| 22–30 | health, contracts, correspondence, Office/Design, mail, calendar connectors, notes, taxes and Daily Brief |
| 31–35 | official notices, administrative drafts, benefit and funding pre‑screen, legal changes and local GUI/API |
| 36 | hardening, Strands agent, competition demo and submission‑ready local package |

The individual changes and the test states at that time are in the direct predecessor; the current requirement evidence is in [`docs/phase36-completion-audit.md`](./docs/phase36-completion-audit.md).

---
