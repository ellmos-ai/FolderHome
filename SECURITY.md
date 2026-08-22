# Security Policy

**English** | [Deutsch](./SECURITY.de.md)

FolderHome processes potentially sensitive household, health, financial, and administrative documents. The competition state is therefore local‑first, fail‑closed, and separates planning, approval, and execution.

## Supported State

Security fixes are maintained on the current competition state on the branch `phase1-foundation`. There is no published release series yet and no production cloud operation.

## Security Boundaries

- The operating system account together with file permissions is the security boundary. Family profiles organize rules and views, but they are not ACLs.
- The local HTTP adapter binds exclusively to `127.0.0.1`, requires a short‑lived session token, checks host and origin exactly, and does not allow CORS.
- Concurrent HTTP requests and incomplete connections have hard limits and timeouts.
- File, parser, and renderer work is limited by non‑disableable budgets for entries, files, bytes, PDF pages, image frames, pixels, text, and outputs.
- The Strands agent has only two profile‑bound read‑only tools. Turns, tool calls, prompt, tool result, and response are finitely limited; tool execution occurs sequentially.
- The deterministic agent fixture uses no network. Amazon Bedrock requires a model ID, region, as well as separate explicit approvals for network access and the sharing of potentially sensitive local search results.
- Official benefit links are verified via HTTPS, exact host, and publisher binding. IP addresses, credentials, ports, and domain look‑alikes are blocked.
- Write actions require domain‑separate approvals and gates, re‑verify source hashes, and do not overwrite existing targets.
- Live mail, live calendar, phone, banking, upload, and publishing are not implicit agent capabilities.

## Confidentiality and Test Data

The repository, tests, and competition demo use exclusively synthetic data. Real documents, credentials, session tokens, email addresses, account identifiers, or health information must not be committed, uploaded, or incorporated into public demo artifacts.

The demo output explicitly states that it is synthetic. A fixture run exercises the Strands agent loop, but neither model quality nor AWS availability.

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
