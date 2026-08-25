# Capability Recipes — one confirmation for a whole journey

**English** | [Deutsch](./capability-recipes.de.md)

> **Last verified:** 2026-08-25

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

## Running one

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
