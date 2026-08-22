# Phase 35: Shared Local API, GUI and Operating System Account Boundary

**English** | [Deutsch](./phase35-local-app-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Make existing FolderHome capabilities usable across a small local application boundary, without building a second domain core or an apparent profile access control.

## Current State

Phases 1 through 34 already have shared Python contracts and an extensive CLI. Document search and topic dossier use the pinned KnowledgeDigest index read‑only. Family profiles share exactly one `os_account` according to the existing contract and are expressly only organizational.

There is still no shared server and no visual interface. The new layer should therefore call existing application services and not duplicate domain logic.

## Functional Scope

The first local interface provides:

- System status and visible security boundary,
- organizational profile selection,
- capability overview of the existing stack,
- natural local document search,
- local topic dossier as an extractive hit list.

Further write or domain‑sensitive processes remain initially in their existing CLI, Approval, and Gate contracts. The API must not circumvent their boundaries through a generic command or path parameter.

## Security Contract

```text
explizites Server-Gate + 127.0.0.1 + konfigurierte Roots
  → aktuelles Prozesskonto erfassen
  → kurzlebiges kryptografisches Sitzungstoken erzeugen
  → URL nur an den startenden Prozess ausgeben
  → jeden HTML-/Asset-/API-Aufruf am Token prüfen
  → Host und Browser-Origin auf die konkrete Loopback-Adresse begrenzen
  → JSON-Größe, Schema, Profil-ID, Query und Limit fail-closed validieren
  → ausschließlich allowlistete read-only Handler aufrufen
  → keine CORS-Freigabe, Shell, freien Pfade oder externen Ressourcen anbieten
```


The session token is an additional local process hurdle, but not a second user or rights management system. Permanent data isolation remains the responsibility of the operating system account and its file permissions. Profiles such as Lukas, Hanna, or Simon organize content and rules; they do not separate secrets within the same account.

## Technical Form

- Python standard library `ThreadingHTTPServer`, no new runtime dependency
- bound host exclusively `127.0.0.1`; dynamic test port `0` allowed
- a testable `LocalApplication` between HTTP and existing services
- packaged static HTML/CSS/JS files without CDN or telemetry
- Content‑Security‑Policy, `no-store`, `nosniff`, frame and referrer protection
- `app plan` for read‑only preflight and `app serve` behind an explicit gate

## Visual Direction

**Subject:** private document work for people who do not want to first learn a document management system. **Only primary task:** to search a known local collection intelligibly or bundle it by topic.

- **Colors:** desktop gray `#edf2f5`, paper white `#fbfdfe`, ink `#152638`, filing‑cabinet blue `#194d68`, folder turquoise `#25796d` and archive yellow `#f2b84b`.
- **Typography:** `Bahnschrift`/`Aptos Display` for concise headings, `Segoe UI` for calm body text and a monospaced font for technical status labels.
- **Layout:** generous header, followed by a single active work folder; the capabilities are presented as ordered tabs in the lower grid.
- **Signature:** The yellow tab “Active Work Folder” connects the physical everyday experience of a filing system with the local digital search.

The initial cream/serif direction was discarded because it seemed interchangeable and did not make the functional document subject visible. Motion remains limited to a brief result state and respects `prefers-reduced-motion`.

## Acceptance Criteria

- Non‑loopback binding blocked before start.
- Without an explicit server gate, no listener is created.
- Missing/invalid token, wrong host and foreign origin block.
- Requests cannot inject file paths or commands.
- Only known profiles of the same OS‑account contract are accepted.
- Search and dossier use the existing Search service.
- The GUI works without external assets and is usable via keyboard / mobile.
- API and GUI do not modify documents and do not write any state.
- A real loopback end‑to‑end test demonstrates status, search and security headers.

## Acceptance Evidence

- `297 passed in 89.60s` in the full FolderHome test run
- Ruff over `src` and `tests` without findings; `compileall` without errors
- Real temporary index with two synthetic documents, including one health‑insurance hit in the GUI run
- Desktop viewport `1440 × 1100` and mobile viewport `390 × 844` with `scrollWidth == innerWidth`
- In both viewports: one hit, profile `lukas`, focus returned to the search action, `aria-busy=false`, no console errors and no HTTP errors
- Acceptance listener verified terminated after the run
- Isolated wheel build `folderhome-0.1.0-py3-none-any.whl`; all four GUI assets (`index.html`, `app.css`, `app.js`, `favicon.svg`) read back from the package file

---
