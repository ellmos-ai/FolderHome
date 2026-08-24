# Phase 34: Law-Checker Integration and Legal Change Monitor

**English** | [Deutsch](./phase34-legal-change-monitor-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Precisely qualify an existing source‑bound legal workflow and output technical changes between local legal source versions as justified but non‑binding profile/contract review candidates.

## Baseline Reconciliation

The previous synchronized checkout was outdated and could not be qualified as a runtime due to external modifications. Therefore, Phase 34 used a separate clean `law-checker` checkout validated against revision `a5b0cd51bc3666962f2fae8017c855dea0a712a2`. Its four tests passed on 2026-08-22.

`law-checker` version 0.2.2 provides a skill, a versioned law registry, and a fetcher. It does not have a stable Python API for automatic case‑by‑case verification. Consequently, FolderHome does not import an agent run. The new read‑only bridge instead checks:

- clean, precisely pinned Git revision,
- package name and version,
- stable module ID and declared source functions,
- registry version and activated law keys.

A snapshot can bind an active registry key. A missing or deactivated key blocks the process. The current registry contains SGB V, but not a complete general social administration and social court law. Therefore, FolderHome does not claim comprehensive social law verification.

## Official Publication Channels

For production snapshots, only expressly authorized official domains are permitted. The [Federal Announcement Platform](https://www.recht.bund.de/de/home/home_node.html) provides the official version of the Federal Law Gazette. The [DIP of the German Bundestag](https://www.bundestag.de/dokumente/parlamentsdokumentation) documents parliamentary proceedings up to the proclamation. Consolidated federal statutes may originate from `gesetze-im-internet.de`.

These sources serve different roles: a parliamentary draft is not a proclamation; a proclamation is not automatically the same representation type as a consolidated normative state. Consequently, the snapshot model keeps `legislative_proposal`, `promulgated`, and `consolidated_current` separate. The acquisition itself is not part of the local comparison run.

## New Encapsulated Core

`contracts.legal_change_monitor` and `application.legal_change_monitor` are provider‑agnostic and reusable later. They model:

- incomplete, source‑ and hash‑bound norm‑section snapshots,
- explicit `user_provided` interests for profile or contract,
- technical changes `added`, `modified`, and `removed`,
- pure `review_candidate` assignments via shared topic tags,
- local Markdown/JSON outputs behind a Never‑overwrite gate.

The files are re‑hashed before comparison and output. Sources must not be dated in the future and must not exceed the configured age limit. Production sources outside the allowlist are blocked. The synthetic competition case is isolated by `fixture_only=true`, `authoritative=false`, `example.invalid`, and an explicit CLI test gate.

## Non‑Sticky Follow‑up Steps

The monitor deliberately does not automatically connect:

- official notice extraction or administrative draft,
- legal case‑by‑case verification,
- transition and deadline calculation,
- periodic web acquisition,
- desktop, calendar, or email notification.

This separation prevents a technical text diff from being interpreted as legal effect or a tag match as personal impact. Future providers can feed the encapsulated snapshot contract; approvals and expert review remain separate boundaries.

## Acceptance

The Phase‑34 tests cover provider identity, incorrect revision, missing registry key, altered wording, mismatched interest, draft, source age, non‑official domain, sensitivity/fixture gates, hash change, output gate, and never‑overwrite. The CLI use case qualifies the provider, compares the synthetic state, and writes a local report without network access or external impact.

---
