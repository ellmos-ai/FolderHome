# Capability Recipes — one confirmation for a whole journey

**English** | [Deutsch](./capability-recipes.de.md)

> **Last verified:** 2026-09-09

## Why recipes exist

A real household task is rarely one endpoint. After a car accident you need the
responsible contact, a claim letter, that letter in your drafts folder, and the
follow-up appointment in your calendar. Before recipes, FolderHome could do all
four — but you had to ask four times and confirm four times, and nothing
guaranteed that step three used the same letter as step two.

A recipe is that journey written down. The master resolves it into **one** plan
with several ordered steps, and you confirm the whole chain once.

## What a recipe is not

A recipe grants no new capability. Every step is an existing typed endpoint with
its own adapter, its own request schema and its own gates. If `mail-connector`
needs `--approve-mail-draft`, it still needs it inside a recipe. If an endpoint
is not connected in your installation, the recipe fails closed instead of
quietly skipping the step.

## The three rules that keep it safe

**One endpoint, one owner.** Each step declares the expert it belongs to, and
the review rejects the recipe if the capability catalog disagrees. A recipe can
therefore span domains without weakening the rule that an endpoint may only be
used by the expert that owns it — the rule is simply checked per step instead of
once per plan.

**Data moves only as logical resource IDs.** A handoff declares that a named
field of an earlier step and a named field of a later step must resolve to the
same logical resource: a store one step writes and a later one reads, or a
source both must agree on. No value from a step report is ever substituted into
a later request. Every request is therefore complete before anything runs, which
is what makes a single hash over the whole chain possible.

**The review is part of the confirmation.** Before you see the plan, a
deterministic check runs:

| Check | Refuses when |
| --- | --- |
| `endpoint_owned_by_declared_expert` | the recipe claims the wrong expert for an endpoint |
| `endpoint_connected_at_runtime` | an endpoint is not connected in this installation |
| `side_effects_have_approval_gates` | a step has an effect but declares no gate |
| `referenced_resources_are_registered` | a request names a resource your registry does not have |
| `handoffs_bind_the_same_logical_resource` | a declared handoff links two different resources |

Every involved expert signs the result: one for a single-domain recipe, all of
them for a recipe that spans domains. The endorsement goes into the plan hash,
so confirming the plan confirms the review with it.

## In the app and chat

Choose an organizational profile, then a **Multi-step journey** below the chat.
**Prepare whole journey** creates a proposal only. Read the prepared steps and
their exact domain plans, then use the separate **Confirm and execute** button.
An unavailable journey remains visible but cannot be prepared from the selector.
The resource IDs in the packaged recipe must be configured for that profile;
the app does not invent bindings or bypass individual adapter gates.

The Strands master can also use `list_home_recipes` and `propose_home_recipe`.
These tools only list or prepare; neither can confirm or execute. Selection by a
live model still depends on that model; deterministic tests verify tool wiring,
not the quality of live-model routing. The recipe review is a **deterministic
catalog and resource check**, not an independent human or model review.

The authenticated local API exposes:

- `GET /api/v1/agent/recipes?profile_id=lukas&language=en`
- `POST /api/v1/agent/recipes/plan` with schema
  `folderhome.local-recipe-plan-request.v1`, `profile_id`, `recipe_id`, and `language`.
- `POST /api/v1/agent/confirm` with the returned plan ID, exact hash and **all** step IDs.

Plans remain in the current process only. Reset removes unconfirmed plans;
concurrent or repeated confirmations cannot restart a journey. A failed chain
retains the reports of completed steps, stops the remaining steps, and invalidates
other proposals sharing its execution envelopes. There is no cross-step rollback.
Adapter error details are redacted at this API boundary. A new app session does
not replace an adapter's persistent idempotency protections.

Local adapter integration is tested with synthetic data and synthetic mail
transport, including the absent-mail-approval case. Browser click acceptance and
real mailbox/calendar effects are separate checks, not implied by those tests.

## Running one from the CLI

```powershell
$env:PYTHONPATH = "src"
python -m folderhome recipes list --json

python -m folderhome recipes plan `
  --profiles-dir examples\profiles --state-dir .local-state `
  --resources-file $env:LOCALAPPDATA\FolderHome\resources.json `
  --profile-id lukas --recipe-id accident-aftercare --json
```

The plan prints its own confirmation command. Passing it back executes the chain
in order:

```powershell
python -m folderhome recipes run `
  --profiles-dir examples\profiles --state-dir .local-state `
  --resources-file $env:LOCALAPPDATA\FolderHome\resources.json `
  --profile-id lukas --recipe-id accident-aftercare `
  --approve-mail-draft `
  --confirm plan_<id> --approved-at 2026-08-25T09:05:00+02:00 --json
```

A recipe plan is deterministic, so preparing it again yields the same plan ID.
That is what lets a stateless command line confirm a plan it printed earlier
without keeping a session open.

## When a step fails

The chain stops at the first failure. The report is returned rather than thrown,
because a caller that only saw an exception could not tell what already took
effect. It names three groups explicitly:

- `executed_step_refs` — these ran and their effects stand
- `failed_step_refs` — exactly one step, with the adapter's own message
- `not_attempted_step_refs` — everything after it, untouched

Nothing is rolled back across steps: each adapter keeps its own atomicity
guarantee, and a completed step stays completed. The report tells you exactly
where to resume.

## Known limit of this version

Handoffs bind resources, not values. A recipe cannot yet take a value out of one
step's report and put it into the next step's request — that would require
resolving requests after execution starts and would break the single hash over
the chain. The handoff edges are declared explicitly so a later version can add
value substitution into declared slots without changing the recipe format.

## Where recipes live

Recipes ship inside the package (`folderhome/recipes/*.json`), not beside the
checkout, so an installed FolderHome has them too. The loader is strict:
unknown fields, unknown endpoints and out-of-order handoffs fail closed.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
