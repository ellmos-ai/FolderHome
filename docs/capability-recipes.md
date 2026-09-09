# Capability Recipes — whole journeys and separately approved sections

**English** | [Deutsch](./capability-recipes.de.md)

> **Last verified:** 2026-09-09

## Why recipes exist

A real household task is rarely one endpoint. After a car accident you need the
responsible contact, a claim letter, that letter in your drafts folder, and the
follow-up appointment in your calendar. Before recipes, FolderHome could do all
four — but you had to ask four times and confirm four times, and nothing
guaranteed that step three used the same letter as step two.

A recipe is that journey written down. For v1, the master resolves it into
**one** plan with several ordered steps, and you confirm the whole chain once.
Result-bound v2 recipes require **separate approval for each concrete section**.
The existing selector and CLI below currently offer v1 recipes.

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

**In v1, data moves only as logical resource IDs.** A handoff declares that a named
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

## Plan integrity

Confirmation recomputes the hash from the current plan content; matching stored
hash strings is not enough. The hash covers the complete public master-plan
object except `plan_id` and `plan_sha256`, encoded as UTF-8 JSON with sorted keys,
no extra whitespace and no non-finite numbers. `approval_context` includes the
recipe ID and digest, handoffs, endorsement and ordered step references.

The app checks this binding before accepting approval, and the chain checks it
again before each step. Changed content stops the next step; already completed
effects and their reports remain. Nested request, plan and report data are
copied at their input/export boundaries, so editing an exported object cannot
silently change its source. This is an integrity check, not a new security
boundary against code running under the same operating-system account.

Plans created using the older hash formula must be proposed and reviewed again
after updating. They are not silently converted or approved under the new hash.

An execution report must also match the requested envelope, workflow and adapter.
A mismatched report is not stored or credited to that step; the chain stops.
At the local API, `execution_outcome_unknown: true` and
`result_delivery_incomplete: true` mark that case. `execution_performed` counts
verified reports only: when the outcome is unknown, `false` does **not** prove
that no effect happened. Inspect the underlying state before any manual retry;
the current recipe attempt cannot be started again.

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

A recipe plan is deterministic: preparing the same inputs and domain state with
the same code yields the same plan ID.
That is what lets a stateless command line confirm a plan it printed earlier
without keeping a session open.

## When a step fails

Invalid plan integrity before the chain starts is rejected without execution.
Once started, the chain stops at the first failure. A report is returned rather
than thrown,
because a caller that only saw an exception could not tell what already took
effect. It names three groups explicitly:

- `executed_step_refs` — these ran and their effects stand
- `failed_step_refs` — exactly one step, with its adapter or integrity-check error
- `not_attempted_step_refs` — everything after it, untouched

Nothing is rolled back across steps: each adapter keeps its own atomicity
guarantee, and a completed step stays completed. The report tells you exactly
where to resume.

## Limits of single-confirmation recipes

Handoffs bind resources, not values. A v1 recipe cannot take a value out of one
step's report and put it into the next step's request — that would require
resolving requests after execution starts and would break the single hash over
the chain. Existing resource handoffs remain unchanged; result-value slots use
a separate versioned format.

## Result bindings: v2 runtime, API and chat

The parser also recognizes `folderhome.capability-recipe.v2` with an explicit
`result_bindings` list. Each binding names an earlier `from_step`, a later
`to_step`, a literal `source_path` (JSON member names and nonnegative array
indices), a top-level `target_field`, and a `value_type`:
`string`, `integer`, `number`, `boolean`, `object`, `array`, or `null`.

Bindings cannot overwrite static request values or another binding. Reserved
authority fields, including profiles, accounts, resources and approvals, cannot
be result targets. The eventual destination adapter must additionally validate
the complete resolved request; passing this format check does not authorize a
field or an operation.

Value selection performs no coercion: `false` is not an integer, missing data is
not `null`, and non-finite numbers are rejected. Selected values are detached
copies bounded to 64 KiB of UTF-8 JSON, 16 levels of nesting and 4,096 visited
nodes (including object keys). Paths have at most eight segments; v2 recipes
have at most 32 steps and 32 bindings.

The existing single-confirmation planner rejects v2 before preparing an adapter.
The separate Python `create_recipe_run()` runtime now executes v2 in sections:

1. `plan_next()` prepares only the next consecutive steps whose input values are
   already known. A result produced inside that section is available only to a
   later section.
2. `confirm()` requires exact approval of that section and consumes it before
   calling an adapter. It retains matching execution reports, stops on failure
   or uncertain effects, and does not automatically plan or run another section.
3. Calling `plan_next()` again resolves result slots from retained same-run
   reports. A new plan binds the run, profile, recipe, preceding plans, report
   lineage and selected values. Raw requests are hashed, not re-exposed where an
   adapter deliberately redacted them. The new plan needs its own approval.

Each run has an independent in-memory preparation store using the configured
domain adapters. Closing one run cannot discard another run's identical
envelopes. Adapter-level durable idempotency, resource checks and effect gates
still apply. Failed cleanup retains its targets for another `close()` attempt;
it does not permit restarting uncertain effects. Snapshots are detached copies.

This Python runtime has been tested through the real local notes adapter:
create a note, carry its confirmed ID and revision into an edit, then separately
approve revision 2. No network or external synchronization is involved.

The normal application now dispatches a bundled v2 recipe through the same
`POST /api/v1/agent/recipes/plan` and exact `POST /api/v1/agent/confirm` boundary.
A section proposal uses `folderhome.recipe-stage-plan.v1`, includes its `run`
state, and approves only the returned plan. Catalog entries declare
`approval_mode: per_section` or `whole_chain`.

| Action | Authenticated endpoint / request |
| --- | --- |
| List this profile's runs | `GET /api/v1/agent/recipes/runs?profile_id=lukas` |
| Prepare the next section | `POST /api/v1/agent/recipes/next`; schema `folderhome.local-recipe-next-request.v1`, `profile_id`, `run_id` |
| Close a run without rollback | `POST /api/v1/agent/recipes/close`; schema `folderhome.local-recipe-close-request.v1`, `profile_id`, `run_id` |

The Strands tools `list_home_recipe_runs` and `propose_next_recipe_stage` use
this same process-local state. They never approve effects. Confirmation returns
`recipe_run` plus the actual `recipe_execution` section outcomes. Successful
reports and explicitly uncertain provider evidence also use the normal result
list. A secondary result-storage failure preserves the no-retry warning and
sets `result_delivery_incomplete`; it must not look like an unattempted action.

At most 128 runs are retained. Close old runs to free capacity. Reset, plan
eviction and app shutdown discard the affected pending sections, not completed
effects. Failed cleanup remains available for an explicit close retry. A failed
recipe cleanup does not prevent the app's own scheduler consumer from stopping.
If a model turn fails while proposing a follow-up section, only that unexecuted
proposal is discarded. Confirmed source reports remain in the same run so the
section can be prepared again without repeating earlier effects.

**Still pending:** a useful bundled v2 recipe, GUI section controls and a
session-capable CLI. API/Strands integration tests use synthetic domain adapters;
they do not prove browser acceptance or live-model selection quality. Runs cannot
be restored after process restart or populated with client-provided reports.
A selected JSON value alone proves neither execution nor provenance.

## Where recipes live

Recipes ship inside the package (`folderhome/recipes/*.json`), not beside the
checkout, so an installed FolderHome has them too. The loader is strict:
unknown fields, unknown endpoints and out-of-order handoffs fail closed.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
