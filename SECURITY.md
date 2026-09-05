# Security Policy

**English** | [Deutsch](./SECURITY.de.md)

FolderHome processes potentially sensitive household, health, financial, and administrative documents. The competition state is therefore local‑first, fail‑closed, and separates planning, approval, and execution.

## Supported State

Security fixes are maintained on the current competition state on branch
`main`. There is no production cloud operation.

## Security Boundaries

- The operating system account together with file permissions is the security boundary. Family profiles organize rules and views, but they are not ACLs.
- The local HTTP adapter binds exclusively to `127.0.0.1`, requires a short‑lived session token, checks host and origin exactly, and does not allow CORS.
- Concurrent HTTP requests and incomplete connections have hard limits and timeouts.
- The synthetic accident runtime creates and resets only its marked workspace.
  It rejects filesystem roots, symbolic links, and pre-existing non-empty
  directories that do not carry the exact FolderHome ownership marker.
- File, parser, and renderer work is limited by non‑disableable budgets for entries, files, bytes, PDF pages, image frames, pixels, text, and outputs.
- The Strands master has five bounded tools: two profile-bound read-only
  document tools, capability discovery, logical-resource discovery, and
  specialist consultation. Physical resource locators never enter the public
  catalog or a resource-bound plan. A
  specialist receives exactly one planning endpoint and no executor. Turns,
  tool calls, prompt, tool result, and response are finitely limited; tool
  execution occurs sequentially.
- Conversation never grants approval. The browser must submit an exact plan ID,
  SHA-256 and step set through a separate endpoint. Only a plan carrying a
  prepared typed executor envelope can run, only once, and execution is proven
  by a separate domain report.
- Runtime coverage is explicit: connected, direct-read-only, planning-only and
  not-connected are different states. Missing adapters fail closed and cannot
  fall back to shell, arbitrary paths, generic HTTP or generic CLI execution.
- Conversation history is process-memory-only, profile-organized but not an
  authorization boundary, and bounded to 24 messages by default. An explicit
  reset also discards that profile's unconfirmed plans.
- The deterministic agent fixture uses no network. Amazon Bedrock requires a
  model ID, region, separate explicit approvals for network access and sharing
  potentially sensitive local search results, bounded connect/read timeouts,
  and exactly one total SDK attempt per model call.
- Every provider that speaks HTTP shares one finite budget,
  `model_timeout_seconds` (default 120, accepted range 5 to 900). A model that
  does not answer within it produces a stated failure naming the budget rather
  than a hanging request. Bedrock keeps its own connect and read pair.
- An API key is never a setting. Only the two names `ANTHROPIC_API_KEY` and
  `OPENAI_API_KEY` are read or written, in a `.env` file beside `launch.json`;
  any other line in that file is kept untouched and never interpreted. The key
  travels outside the plan, so it enters no plan hash, no preview, no status, no
  report and no log, and the state reports only whether one is stored. The file
  is written atomically with mode `0o600` and no backup copy, because a backup
  of a key is a second copy of a key. That mode is enforced where the platform
  enforces it; on Windows the user account boundary is what protects the file.
- The installer's folder dialog runs in a child process, is serialized to one
  open dialog, and gives up after five minutes so that a cancelled dialog is not
  the last one. It is reached only through the token-checked loopback route of
  the installer, never from the app. It answers with the chosen path on purpose:
  naming folders is what the installer is for. The rule that physical locators
  stay out of payloads belongs to the application API, which never returns one.
- The optional AgentCore adapter accepts JSON prompts only, rejects uploads,
  arbitrary local paths, duplicate JSON keys and non-synthetic requests, and
  returns no host paths or secrets. Runtime sessions, concurrent invocations,
  request bodies and socket time are bounded; capacity exhaustion fails with
  an explicit service-unavailable response.
- The public static showcase has no backend, performs no network request and
  changes no files. It is visibly labelled as a scripted synthetic walkthrough
  and is not evidence of a deployed AgentCore endpoint.
- Official benefit links are verified via HTTPS, exact host, and publisher binding. IP addresses, credentials, ports, and domain look‑alikes are blocked.
- Write actions require domain-separate approvals and gates, re-verify source
  hashes, and do not overwrite existing targets. Connected chat writes include
  append-only personal notes, medication intake evidence, resource-bound
  document bundles, contact state, local correspondence files and the own
  FolderHome calendar. Full correspondence content remains local.
- Live mail, live calendar, phone, banking, upload, and publishing are not implicit agent capabilities.

## Confidentiality and Test Data

The repository, tests, and competition demo use exclusively synthetic data. Real documents, credentials, session tokens, email addresses, account identifiers, or health information must not be committed, uploaded, or incorporated into public demo artifacts.

The demo output explicitly states that it is synthetic. A fixture run exercises the Strands agent loop, but neither model quality nor AWS availability. No demo action sends email, places a call, creates an external calendar event, uploads a document, or archives an older policy automatically.

## Security Review

The Phase‑36 scan captured 357 files across 12 of 12 declared areas and reported three findings. Fixed were unlimited document processing, freely claimable official benefit hosts, and unlimited loopback connections. The immutable pre‑fix scan and its separate fix report are stored in the local scan artifact; the final audit documents additional post‑fix and Strands checks.

Reproducible local checks:

```powershell
python -m pytest
python -m ruff check .
python -m compileall -q src tests
python -m folderhome plugins validate --json
python _tools\doc-lint
python _tools\workflows-sync --check
```


## Reporting a Vulnerability

Please do not post real sensitive example data in a public issue. Until a public security contact has been approved, report vulnerabilities confidentially to the repository owner. A report should include the affected version, minimal reproduction steps, expected impact, and known workarounds.

## No Security Claim Regarding Professional Decisions

FolderHome is not medical diagnosis, legal, tax, benefit, or financial advice. Evidence, deadline displays, conflicts, and candidates do not replace professional review. A technically successful tool result does not prove either completeness or factual correctness of a source document.

---
