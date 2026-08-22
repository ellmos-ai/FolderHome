# Phase 27 — Calendar Connectors and Reminder Handoffs

**English** | [Deutsch](./phase27-calendar-connector-plan.de.md)

**Status:** locally completed, 233 tests green  
**Stand:** 2026-08-22  
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

- `ready` or `review_required` does not mean that a calendar was modified.  
- A synthetic event reference is not a live calendar entry.  
- No Google credentials were read nor were Google tools invoked.  
- UpToday receives an ICS file only via the separately approved Phase‑17 handoff.  
- Routinika live sync, update, delete and series events remain open.  
- Automatic appointment detection is best effort and carries no completeness guarantee.  
- Profiles within an operating system account are organizational rules, not cryptographic tenant separation.

---
