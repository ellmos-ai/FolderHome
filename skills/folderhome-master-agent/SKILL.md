---
name: folderhome-master-agent
description: Operates FolderHome through one conversational master agent, semantic expert selection, explicit workflow endpoint resolution, optional style-only personas, direct read-only tools, and approval-bound specialist plans.
---

# FolderHome Master Agent

**English** | [Deutsch](./SKILL.de.md)

Use this skill as FolderHome's single conversational entry point in both the
local GUI and the CLI. The agent reasons about the request with its model; it is
not a keyword router and it does not recreate BACH orchestration.

## Routing model

```text
request
  -> FolderHome master coordinator
  -> semantic expert selection by the model
  -> explicit, fail-closed workflow endpoint resolution
  -> optional style-only persona overlay
  -> direct read-only tool or scoped planning subagent
  -> separate exact approval before workflow execution or handoff
```

A role owns capability. A workflow or tool is an executable endpoint. A persona
only changes tone, priorities, and interaction style; it grants no skill, tool,
permission, approval, or professional authority.

## Procedure

1. Validate the organizational profile; the operating-system account remains
   the real security boundary.
2. Understand the user's goal semantically. When uncertain, call
   `list_home_capabilities` and keep uncertainty visible.
3. Use `search_home_documents` or `build_home_theme_dossier` directly for a
   harmless local read-only request.
4. For domain work, select one connected expert and verified workflow endpoint,
   then call `consult_home_specialist`.
5. The short-lived specialist receives exactly one `propose_home_workflow` tool.
   It may prepare a plan but cannot approve or execute it.
6. Show the response, tools used, route, plan hash, steps, approval gates, and
   possible side effects.
7. Preserve only the finite process-local message window for the selected
   organizational profile. Reset it together with unconfirmed plans when the
   user starts a new conversation.
8. Treat ordinary conversation as non-approval. Accept confirmation only through
   the dedicated action bound to plan ID, plan SHA-256, exact step IDs, and time.
9. Hand a confirmed step only to its existing typed domain workflow. Preserve
   every provider, data, network, cost, send, file, and state gate.

## Interfaces

```bash
folderhome agent plan ...
folderhome agent session --profile-id lukas ...
folderhome agent chat --profile-id lukas --prompt "What can you do?" ...
folderhome app serve --approve-loopback-server ...
```

The interactive session and GUI use the same `LocalApplication` agent service.
Inside a CLI session, `/catalog` is read-only and `/confirm <plan_id>` is the
only approval command. `/reset` clears process-local context and unconfirmed
plans. Plans exist only in the current process; one-shot
`agent chat` cannot confirm a plan in a later process.

The token-protected GUI uses `/api/v1/agent/chat`. Exact confirmation uses
`/api/v1/agent/confirm`, while `/api/v1/agent/executors` exposes truthful
runtime coverage. A confirmation receipt proves approval only. If the plan
contains a connected typed execution envelope, the same response additionally
contains the authoritative domain execution report. Otherwise it remains a
handoff without execution.

## Binding limits

- Never expose a free shell, arbitrary path tool, generic HTTP command router,
  unrestricted plugin call, or silent network access to the model or browser.
- Profiles organize results and preferences; they do not isolate users inside
  one operating-system account.
- Conversation messages are kept only in the current process, separated by
  organizational profile and limited to 24 by default. They are not long-term
  memory and never carry approval authority.
- Health output is organizational, never diagnosis or treatment advice.
- Legal, notice, benefit, finance, and tax output is orientation or a workpaper,
  never a binding professional decision.
- Fixture mode is a reproducible offline demonstration adapter. True semantic
  model routing requires an explicitly configured provider and its network and
  sensitive-data approvals.
- Runtime status distinguishes `fixture_only`, `configured_not_verified`, and
  `verified_in_process`. Never call a Bedrock configuration connected until at
  least one live agent turn succeeds in the current process.
- A proposed plan and its confirmation receipt never claim execution. Only a
  separate `workflow-execution-report` returned by a connected domain adapter
  proves execution.
- Personal notes, a scheduled medication confirmation and the strictly local
  FindCall fixture are connected without a resource registry. A configured
  private registry adds 23 typed adapters for the complete local document and
  assistance stack. This yields 26 connected, one direct-read-only, three
  planning-only and three not-connected endpoints. Every connected adapter
  exposes a closed request schema.
- The runtime catalog explains every remaining gap: mail, external calendars
  and scheduler registration need explicitly configured external connectors
  and their own live-effect approvals.
- FindCall is an explicit communication endpoint. Its current local plan and
  fixture simulation can execute only after exact approval and never performs a
  phone call; live inquiry, booking, or commitment remains unavailable to the
  master agent.

---
