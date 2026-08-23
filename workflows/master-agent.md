# Workflow: Use the FolderHome Master Agent

**English** | [Deutsch](./master-agent.de.md)

> **Last verified:** 2026-08-23  
> **Frequency:** per conversational request  
> **Duration:** model-dependent; domain execution remains a separate workflow

## Purpose

Use one model-driven agent from GUI or CLI for FolderHome discovery, local
read-only tools, and bounded domain planning. Keep semantic selection,
deterministic endpoint resolution, persona style, approval, and execution as
separate layers.

## Steps

1. Run `folderhome agent plan` and inspect the finite tool surface.
2. Start the same service with `folderhome agent session` or the local GUI. Use
   `folderhome agent chat` for a single non-interactive turn.
3. Retain a finite Strands message window per organizational profile in the
   current process so follow-up references have context. Use **New conversation**
   or `/reset` to clear messages and unconfirmed plans.
4. Let the model choose the narrowest connected expert by meaning. There is no
   application keyword table.
5. Resolve the selected workflow against the explicit live catalog. Reject
   unknown or cross-expert endpoints.
6. For simple local search or a topic dossier, use the read-only tool directly.
7. For domain work, create a short-lived specialist with one plan-only workflow
   tool and an optional style-only persona.
8. Display tool events, delegation, route, plan ID, hash, gates, and effects.
9. Inspect `/api/v1/agent/executors`. A connected step carries a typed,
   hash-bound execution envelope; an unconnected step remains visibly blocked
   from chat execution.
10. Confirm a plan only with the dedicated hash-bound GUI/API action or, inside
   the same CLI process, `/confirm <plan_id>`. Ordinary chat never confirms a
   plan. The confirmation receipt itself proves approval, not execution.
11. For a connected envelope, run the existing typed domain workflow and return
    its separate authoritative execution report. Otherwise create a handoff
    receipt without claiming execution.

## Exit criteria

- [ ] GUI and CLI call the same master-agent service.
- [ ] Every repository workflow resolves through exactly one expert.
- [ ] Capability records contain no prompt keywords or routing terms.
- [ ] Personas have `style_only` authority.
- [ ] A specialist sees only its selected planning endpoint.
- [ ] Chat cannot act as approval.
- [ ] The CLI retains plans only in its current process and requires the exact
  displayed plan ID for `/confirm`.
- [ ] Follow-up context is profile-local, finite and process-only; reset removes
  both retained messages and unconfirmed plans.
- [ ] Stale plan hashes fail closed.
- [ ] A chat message alone performs no write; an exact confirmation executes a
  connected envelope at most once.
- [ ] Browser and model have no shell, arbitrary path, generic plugin, or open
  network tool.

## Current implementation boundary

The executor catalog reports 33 workflow endpoints. Without a private resource
registry, personal notes, confirmation of an existing scheduled medication
dose, and the strictly local FindCall fixture are connected. A configured
registry adds 23 typed adapters for the complete local document and assistance
stack. That configuration reports 26 `connected`, one `direct_read_only`, three
`planning_only`, and three `not_connected` endpoints. Connected endpoints
publish a closed request schema to the scoped specialist. The remaining gaps
are mail, external calendars and scheduler registration; each requires an
explicitly configured external connector with its separate live-effect gate.
The connected FindCall adapter executes only the deterministic local fixture
after exact approval. The master agent still has no live telephone executor and
cannot call, book, order, or commit.
A confirmation can execute only a connected envelope; domain
execution reports remain authoritative.

## Related

- [`../skills/folderhome-master-agent/SKILL.md`](../skills/folderhome-master-agent/SKILL.md)
- [`./strands-agent.md`](./strands-agent.md)
- [`./local-app.md`](./local-app.md)
- [`../SECURITY.md`](../SECURITY.md)

---
