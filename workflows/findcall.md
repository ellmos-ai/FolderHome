# Workflow: Prepare a bounded provider inquiry with FindCall

**English** | [Deutsch](./findcall.de.md)

> **Last verified:** 2026-08-23  
> **Frequency:** ad hoc for appointment or quote searches  
> **Duration:** seconds for local planning and fixture simulation

## Purpose

Prepare a serial inquiry for an appointment or quote from explicitly configured candidates. FindCall applies the user's time, location and price limits, stops after the first valid result and never makes a commitment on the user's behalf.

The current FolderHome master agent connects deterministic planning and the
strictly local fixture simulation through a typed, approval-bound adapter. It
does not place phone calls, access a network, book an appointment or accept a
quote.

## Preconditions

- Profile, request type, service, location, time windows and optional price ceiling are explicit.
- Candidate and fixture files use the documented FindCall schemas.
- HungryCall and Ringedingeding probes match their pinned clean revisions when they are inspected.
- A future live run additionally requires an explicitly configured connector and a workflow-specific approval.
- Emergency requests and requests for diagnosis are not FindCall use cases.

## Steps

1. **Validate request** — reject missing limits, commitments, emergency content and diagnosis requests.
2. **Load candidates** — use only the explicitly configured candidate set; never infer a hidden directory or contact source.
3. **Build plan** — order compatible candidates deterministically and display masked phone numbers, time windows, distance, price limit and stop conditions.
4. **Review exact plan** — check the plan ID, selected actions, candidate order and all constraints.
5. **Approve live effect separately** — ordinary chat confirmation is insufficient; a future connector must receive the exact workflow approval.
6. **Run serially** — query one candidate at a time and stop after the first result that satisfies every hard limit.
7. **Report evidence** — return attempts, rejection reasons, the accepted result if any and explicit effect flags.

## Exit criteria

- [ ] No unconfigured candidate, directory or connector was used.
- [ ] Phone numbers are masked in plans and reports.
- [ ] Time, service, location and price constraints are preserved.
- [ ] No booking, order, diagnosis or financial commitment was made.
- [ ] Local fixture reports state `simulated=true`, `network_used=false` and `phone_calls_placed=false`.
- [ ] A live inquiry is reported only when its connector and exact approval are independently verified.

## Pitfalls

- A master-agent plan is not permission to place a phone call.
- The local fixture provider proves orchestration, not telephony or provider availability.
- HungryCall supplies the serial early-stop pattern; its restaurant model is not reused for medical practices or workshops.
- Ringedingeding remains a separate coordination plugin and is not a live call transport.
- Changed or dirty plugin checkouts invalidate revision-bound probes.

## Related

- [`../docs/phase18-findcall-reuse-and-plan.md`](../docs/phase18-findcall-reuse-and-plan.md)
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — FindCall safety boundary
- [`./master-agent.md`](./master-agent.md) — semantic routing and exact approval

## History

- **2026-08-23** — Connected the strictly local fixture executor through an exact approval
- **2026-08-23** — Added as an explicit fail-closed master-agent endpoint
