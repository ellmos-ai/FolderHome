# Phase 27 — Calendar Connectors and Reminder Handoffs

**English** | [Deutsch](./phase27-calendar-connector-plan.de.md)

**Status:** Google-v3 gateway, private credentials and app/CLI adapter implemented; live acceptance open  
**Updated:** 2026-09-09 (original phase acceptance: 233 tests on 2026-08-22)  
**Product name in competition:** FolderHome

## Goal

FolderHome connects the existing Phase-17 calendar core with explicit calendar accounts and provider‑neutral operations. Events from documents continue to be treated only as documented candidates. Create, update, delete, and remind are separate operations; a plan does not invoke any connector.

## Revision inventory

| Component | Revision finding | Phase-27 role |
|---|---|---|
| UpToday | clean local checkout `7582ca87e17e458bb99a7379d2c54003c15415a4`; 21 ICS tests green | reuse existing RFC-5545 file handoff from Phase 17, no live sync |
| Routinika | date‑based `routinika-bundle-v1` contract; `portable_bundle.py` SHA-256 `3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2` | hash‑bound design reference, blocked up to a live connector contract |
| Google Calendar | local skill `google-calendar` 1.2.5 | agentic, separately approvable handoff; no run in competition code |
| FolderHome Phase 17 | local calendar store and UpToday ICS output | source for candidates, profile resolution and local handoff; no duplicate build |
| FolderHome Synthetic Calendar | `working-tree`, new in competition period | deterministic no‑network fixture provider for local acceptance |

The inventory is a snapshot as of 22 August 2026. The Routinika inventory in OneDrive was only read and hashed via FileCommander. No external checkout, calendar, or user account was modified.

## New encapsulated core

- `folderhome.contracts.calendar_connectors`
- `folderhome.application.calendar_connectors`
- `folderhome.capabilities.calendar_connector_gateway`
- `folderhome-calendar-connectors`‑Skill

The contract models account, reminder, request, route, event payload, operation, approval, provider‑event reference and execution report. The configuration may contain only a `connector://` reference, no tokens. Unknown fields are rejected fail‑closed.

## Reuse instead of duplicate build

The connector plan is built exclusively on a complete `folderhome.calendar-handoff-plan.v1` from Phase 17. This keeps document extraction, line evidence, profile/area rule, time zone, duplicate detection, local store and ICS output in one place.

- UpToday creation is delegated to the existing ICS handoff.  
- The local FolderHome calendar remains the existing Phase‑17 store.  
- Routinika remains a file handoff reference and is not emitted as a live sync.  
- Google receives an explicit, verifiable handoff payload, but the skill is not invoked in the plan.

`backend_source` and `source_rule_ids` are incorporated into the connector plan. This makes visible whether the target originates from configuration standard or profile rule.

## Google handoff

A Google creation payload always includes an explicit `calendar_id`, an empty attendee list, `transparency=opaque`, structured popup reminders and start/end times with UTC offset as well as IANA time zone. Update and delete remain blocked until an existing provider‑event reference is present. Recurring events later also require the deliberate selection of master or single instance.

## Synthetic acceptance

The synthetic provider accepts only exact hash‑ and action‑bound approvals for `create` and optionally `remind`. It has no network path, does not write to a live calendar, and returns only synthetic provider‑event references. Duplicate idempotency keys are rejected within a gateway run. A gateway declared as network‑required is stopped before invocation without network approval.

## Product limits

### Approval integrity — 9 September 2026

The plan hash covers the complete public plan, including account, profile,
route, event fields and operations. An `input_sha256` additionally binds the
complete request, account configuration and Phase-17 handoff snapshot without
exposing their private source paths or connector references in the public plan.
This binds a snapshot; it does **not** reread source files at execution time.

Execution recomputes the content hash at entry and before and after each event.
Provider identity, revision and simulated/network/live effects must match the
approved route. A synthetic route cannot become a live route, even with network
approval. The exact payload is hashed before the gateway call and checked again
afterward, including when unapproved reminders were removed.

**Older approvals require a fresh proposal and review.** A failure detected
after a gateway call does not undo a possible effect. Do not automatically retry
or treat missing success evidence as proof that nothing happened. The gateway
implementation below adds persistent idempotency, uncertain-outcome handling
and provider readback. The app/credential implementation is described below;
live acceptance remains open.

Local verification: 19 new red-to-green integrity regressions, 38 focused
calendar tests, and a full suite of **831 passed in 251.39 seconds** with
warnings treated as errors. The real `calendar connector-simulate` CLI returned
one synthetic event reference with both live-calendar and network flags false.

### Google-v3 implementation — 9 September 2026

The application can execute exact `create`/`remind` approvals through
`folderhome.bridges.google_calendar.GoogleCalendarGateway`. Only the native
`google-calendar@v3` route with a concrete calendar ID becomes executable;
historical skill routes remain review-only. A typed
`external_connector_required` marker allows replacing a missing route without
lifting document time-conflict blocks. Unknown or unmarked blocks stay blocked.

The gateway reads a stable remote event ID, atomically reserves a write in a
private SQLite ledger, attempts at most one POST, then compares the returned
event's actual fields. A failed initial GET consumes no write attempt. A possibly
completed POST is never automatically repeated. Renaming local accounts or
rotating credential references does not reset the ledger. The token-dependent
`primary` alias must first be resolved to a concrete calendar ID by the future
account integration.

Both the exact approval and the separate gateway network gate must explicitly
allow execution. The transport pins the Google HTTPS host, does not follow
redirects, limits response bodies to 1 MiB, and keeps credential/provider error
details out of user-visible exceptions. Tokens and event text are not stored in
the ledger. `CalendarConnectorOutcomeUnknown` preserves confirmed references
when a later event fails; missing success is not a rollback.

Local verification: **107 calendar tests** and **102 workflow, recipe and resource
tests passed**, with warnings treated as errors. Tests use the real gateway,
executor and temporary ledger behind an in-memory HTTP boundary. They do not
establish OAuth or live-account acceptance. The following adapter extends this
baseline; initial login, live testing and reference/ETag-based updates remain open.

### Private credentials and normal app/CLI execution

Install the optional dependency from this checkout with
`python -m pip install ".[calendar]"`. Google `authorized_user` JSON remains in a
private OS-account file, outside repository and document folders. FolderHome uses
`google-auth` to load the existing grant and refresh an expired token. It does not
start a login or write refreshed credentials back to disk. Refresh is limited to
one request to `https://oauth2.googleapis.com/token`; redirected, failed or oversized
responses are rejected. Both requested and explicitly granted scopes must include
`https://www.googleapis.com/auth/calendar.events`.

Declare these five resources explicitly in the private registry:

| Purpose | Kind | Operations |
|---|---|---|
| `calendar.source` | `directory` | `list`, `read`; `sensitive_read` only when approved |
| `calendar.configuration` | `file` | `read` |
| `calendar.connector_accounts` | `file` | `read` |
| `calendar.google_credentials` | `file` | `read` |
| `calendar.connector_ledger` | `directory` | `read`, `state_write` |

The account reference must be `connector://google-calendar/<credential_resource_id>`.
The configured account needs `google-calendar@v3` and a concrete calendar ID, not
`primary`; the profile policy must select Google. The normal app/CLI factory then
exposes the closed `calendar-connectors` request schema. Start with
`--approve-calendar-write` and separately confirm the exact prepared plan. A chat
request, configured account or launch JSON cannot grant this write permission.

Preparation reads no credentials and creates no ledger. Execution reconstructs
the plan from current profile, source, configuration and resource permissions
before credential resolution and before/after each calendar request. Changed
inputs or revoked rights stop further effects, including local confirmation writes.
Uncertain/partial outcomes stay typed across the workflow boundary; confirmed
references are retained on the exception. Dedicated partial-result UI and account
setup assistance remain open. This adapter currently expects explicit registry
bindings, not calendar defaults synthesized only in app memory.

The OAuth tests use real `google-auth 2.57.1` behind a synthetic HTTPS boundary.
Normal app-factory tests cover the separate gate and a persisted registry-rights
revocation. No real Google grant or account was used. Protocol reference:
[Google OAuth credentials](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html).

### Remaining boundaries

- `ready` or `review_required` does not mean that a calendar was modified.  
- A synthetic event reference is not a live calendar entry.  
- No real Google credentials or accounts were accessed during acceptance.  
- UpToday receives an ICS file only via the separately approved Phase‑17 handoff.  
- Routinika live sync, update, delete and series events remain open.  
- Automatic appointment detection is best effort and carries no completeness guarantee.  
- Profiles within an operating system account are organizational rules, not cryptographic tenant separation.

---
