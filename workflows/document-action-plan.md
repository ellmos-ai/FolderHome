# Workflow: Create Document Action Plan from Profile Rules

**English** | [Deutsch](./document-action-plan.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** ad-hoc or before each subsequent file execution  
> **Duration:** a few seconds per document  

## Purpose

Check a synthetic or explicitly selected document against the rules of an organization profile and generate a traceable plan without altering the source, target folder, or the production FCSA state.

## Preconditions

- `household.json` and profile files are validated with `profiles validate`.  
- The profile resides within the same declared OS account; there is no access limit.  
- Source path, target root, and deadline are explicitly specified.  
- doc-services and FCSA match their pinned, clean checkouts.

## Steps

1. **Resolve rules** — global → domain → profile → profile segment; conflicts at the same level block.  
2. **Extract source read-only** — doc-services operates without OCR and without learning write access; the action plan does not take any raw text.  
3. **Validate naming** — only fixed placeholders are allowed; path separators, reserved names, and escape from the target root are blocked.  
4. **Project actions** — naming, sorting, conversion, original handling, and retention remain separate steps.  
5. **Check deadlines** — only the explicit `as_of` deadline decides, not a hidden system time.  
6. **Stop conflicts** — simultaneously due sorting, archiving, or trash targets are blocked and handed over to review.  
7. **Confirm FCSA** — executable move/trash steps run only through the temporary FCSA dry run; hard delete remains disabled.  
8. **Verify immutability** — source is byte-identical, target root and production provider state were not created or altered.

## Exit-Criteria

- [ ] Each action lists source rules, provider, capability, gate, and undo.  
- [ ] All filesystem gates are set to `granted=false`.  
- [ ] No raw text appears in the JSON plan.  
- [ ] Missing providers and competing targets are visibly set to `blocked` or `review_required`.  
- [ ] FCSA confirms only `move`, `duplicate_check`, or `delete-to-trash` in the dry run; `allow_hard_delete` is false.  
- [ ] Source and target state are unchanged.

## Pitfalls

- A plan is not an execution approval.  
- A profile-based rule is not a file permission.  
- `modified_at` is only an organizational deadline signal, not a legal statement regarding retention obligations.  
- A conversion request remains blocked until a vetted provider.

## Related

- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Phase-6 data flow  
- [`../examples/profiles/README.md`](../examples/profiles/README.md) — synthetic profiles  
- [`./fcsa-dry-run.md`](./fcsa-dry-run.md) — Provider-Dry-Run  
- [`./document-action-execution.md`](./document-action-execution.md) — separate plan- and hash-bound execution with undo  

## History

- **2026-08-21** — Created after Phase-6 end-to-end acceptance  
- **2026-08-21** — Phase-11 execution workflow linked
