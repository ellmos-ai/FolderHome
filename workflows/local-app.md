# Workflow: Start Local FolderHome App

**English** | [Deutsch](./local-app.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** per local work session  
> **Duration:** a few seconds plus interactive usage

## Purpose

Start the shared FolderHome chat interface on the current operating-system account. The GUI calls the same master-agent service as the CLI, shows read-only tool results, proposed plans, executor coverage and execution reports, and keeps conversation separate from exact confirmation. It creates neither a second profile access control nor general file or command access.

## Preconditions

- Profile and index state directory belong to the current OS account.
- The KnowledgeDigest checkout matches the pinned manifest.
- For chat-controlled personal notes, the llm-note checkout matches its pinned
  manifest and the state directory is writable.
- The desired port is free on `127.0.0.1` or `0` will be used for a dynamic port.
- It is understood that family profiles only separate organizationally.

## Steps

1. **Run preflight read‑only.**

   ```powershell
   folderhome app plan --profiles-dir <profiles-dir> --state-dir <state-dir> --json
   ```


2. **Check limits in the plan.** `security_boundary` must be `operating_system_account`; server start, shell, CORS, free paths and external resources must remain `false`.

3. **Deliberately expose the loopback server.**

   ```powershell
   folderhome app serve --profiles-dir <profiles-dir> --state-dir <state-dir> --port 8765 --approve-loopback-server --json
   ```


4. **Open only the provided session URL.** The token is short‑lived and must not appear in logs, messages, or permanent browser bookmarks.

5. **Select the profile organizationally.** The selection controls the work context but does not grant new read rights within the OS account.

6. **Talk to the FolderHome agent.** Simple search and dossier requests use
   bounded read-only tools. Follow-up messages reuse a bounded, process-local
   conversation for the selected organizational profile. Domain work may
   produce a visible specialist plan.
7. **Start fresh when needed.** **New conversation** clears that profile's
   retained messages and discards its unconfirmed plans together with their
   unexecuted typed envelopes. It does not delete documents, indexes, completed
   receipts, or another profile's conversation.
8. **Check model state and executor coverage.** Fixture is explicitly not a
   live LLM. Configured Bedrock remains unverified until one successful agent
   turn in the current process. A connected step is labeled **Confirm and
   execute**. A missing adapter is labeled as a handoff only and must not claim
   execution.
9. **Confirm deliberately.** Use the plan button only after reviewing plan ID,
   hash, exact steps and possible effects. The receipt proves approval. A
   connected step additionally returns a separate domain execution report and
   can be executed only once.

10. **Terminate the server after the session.** In the launching terminal
    press `Ctrl+C` and verify that the listener is no longer running.

## Exit-Criteria

- [ ] The preflight reports loopback and the OS account boundary.
- [ ] The server was started only with an explicit gate.
- [ ] HTML, assets and API were blocked without a valid session token.
- [ ] The interface used no external resources.
- [ ] The model-status card did not present fixture or unverified Bedrock as a
  working live model connection.
- [ ] Chat and confirmation used separate token-protected API actions.
- [ ] Follow-ups used only bounded process memory and **New conversation**
  cleared the selected profile's retained context.
- [ ] No state was modified before a separate exact confirmation.
- [ ] Every confirmed write has a typed domain execution report and declared
  side effects.
- [ ] The session token was not stored permanently or shared.
- [ ] The local listener is terminated after use.

## Pitfalls

- Switching profiles is **not** a user switch. For true separation, a different operating system account with its own file permissions is required.
- `localhost` is intentionally not equivalent to `127.0.0.1`; the exact host contract protects against ambiguous browser and proxy resolution.
- A copied link contains the session token. It must not leave the local machine or the active session.
- A chat message is never approval; only the dedicated hash-bound confirmation
  action can execute a connected envelope or create a handoff receipt.
- Conversation history is not durable storage. It is lost when the app stops,
  is bounded to the configured message window, and profiles remain an
  organizational convenience rather than an authorization boundary.
- `not_connected` is a runtime boundary, not a promise that an existing CLI
  workflow was executed.
- Write or domain‑sensitive functions remain in their respective Approval and Gate workflows; the GUI does not bypass them.

## Related

- [`../docs/phase35-local-app-plan.md`](../docs/phase35-local-app-plan.md)
- [`../skills/folderhome-local-app/SKILL.md`](../skills/folderhome-local-app/SKILL.md)
- [`./document-library.md`](./document-library.md)
- [`./document-action-execution.md`](./document-action-execution.md)

## History

- **2026-08-22** — local API, GUI, OS account boundary and runtime contract approved
- **2026-08-22** — executor catalog and first typed personal-notes execution path added
- **2026-08-22** — bounded per-profile process conversation and explicit reset added

---
