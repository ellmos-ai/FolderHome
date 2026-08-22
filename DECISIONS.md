# DECISIONS.md — Current Architecture Decisions

**English** | [Deutsch](./DECISIONS.de.md)

**Version:** 0.36  
**Date:** 2026-08-22  
**Direct predecessor:**  
[`docs/archive/DECISIONS-through-phase35.md`](./docs/archive/DECISIONS-through-phase35.md)

> The predecessor contains context, decision, and consequences for each phase up to 35.  
> This short version is the current decision index and supplements the phase‑36 decisions.

## Valid Guiding Decisions

| Decision | Consequence |
|---|---|
| FolderHome is a new integration repository | New core and new bridges remain visible, separated from pinned existing assets |
| Competition name remains FolderHome | Light-/Sovereign branding occurs no earlier than after the competition |
| Default deny for side‑effects | Analysis or agent tool does not grant any file, mail, calendar, phone, network, or publishing permission |
| Plan and execution are separated | Approval binds operation, source, destination, and hash; a recheck occurs immediately before execution |
| Operating‑system account is the security boundary | Family profiles organize rules but do not replace OS privileges |
| “Latest version” remains an explicit heuristic | Contract data overrides filename/modification time; archiving remains a separate reversible plan |
| User learning requires documented corrections | Examples generate only rule candidates that must be reviewed |
| Outputs are new and hash‑bound | Never‑overwrite, atomic publishing and rollback of own partial results |
| Existing modules are not re‑tagged | Exact revision, license, API/Seam and side‑effect boundary are listed in manifests |
| Domain states are evidence‑bound | Contacts, appointments, finances, inventory, medication, health, contracts and official notices retain source status and uncertainty |
| Specialist assistance is not a specialist opinion | No diagnosis, legal, tax, benefit, or financial decision |
| UI, CLI and agent use the same application boundary | No duplicated domain logic and no direct provider access from the UI |
| Live connectors have their own gates | Fixture, handoff, or dry‑run success is not live evidence |

## 2026-08-22: Strands is the constrained agent layer

### Context

The current Agents‑for‑Humans rules require a newly built agent using the Strands Agents SDK. The existing FolderHome core was already a broad deterministic assistance platform, but not a Strands orchestration.

### Decision

`strands-agents==1.53.0` is a mandatory runtime dependency. A real `strands.Agent` receives exactly two profile‑specific read‑only tools: document search and topic dossier. Both invoke `LocalApplication`.

Turns, tool calls, prompt, response, tool result and output tokens are limited. A deterministic fixture model adapter makes the same loop reproducible without credentials. Bedrock is optional and requires a model ID, region, and separate approvals for network access and for forwarding local search results to the cloud model.

### Consequences

- The agent meets the competition requirement without bypassing existing security boundaries.  
- Fixture evidence demonstrates orchestration, not model quality.  
- Writing domain capabilities are not prematurely released as agent tools.  
- A technical network approval alone does not authorize the sharing of potentially sensitive local document data.

## 2026-08-22: Resource budgets are a shared contract

### Context

The phase‑36 security scan observed unrestricted document processing and parallel loopback connections. Individual ad‑hoc limits would easily diverge with new modules.

### Decision

`capabilities/resource_budget` encapsulates file count, bytes, and runtime for all affected workflows. The loopback server adds semaphores, socket timeout, and overload rejection. The agent has its own finite model/tool budgets.

### Consequences

- New capabilities can reuse the same fail‑closed mechanism.  
- Budget overruns are treated as controlled errors rather than as partial results or resource exhaustion.

## 2026-08-22: Official URLs are publisher‑bound

### Decision

Benefit handoffs accept only HTTPS and exactly verified hosts of the declared publisher. Look‑alike subdomains, userinfo, other ports, trailing‑dot and percent‑encoding variants are blocked.

### Consequence

A data catalog cannot deem an arbitrary host trustworthy solely by the label “official”.

## 2026-08-22: Local completion and external submission remain separate

### Decision

The 36 phases conclude with a locally installable, tested, and demonstrable competition package. Public repository creation, video release, AWS Builder ID, live demo, and Devpost submission remain independent human gates.

### Consequence

A locally built artifact may be considered locally completed, but must never be described as published or submitted.

---
