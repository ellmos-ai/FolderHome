# Workflow: Start Local FolderHome App

**English** | [Deutsch](./local-app.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** per local work session  
> **Duration:** a few seconds plus interactive usage

## Purpose

Start the shared FolderHome interface on the exact current operating system account and operate the existing document search and topic dossiers in read‑only mode. The process does not create a second profile access control nor a general file or command access.

## Preconditions

- Profile and index state directory belong to the current OS account.
- The KnowledgeDigest checkout matches the pinned manifest.
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

6. **Use search or topic dossier.** Both functions only read the existing local index and do not expose source paths.

7. **Terminate the server after the session.** In the launching terminal press `Strg+C` and verify that the listener is no longer running.

## Exit-Criteria

- [ ] The preflight reports loopback and the OS account boundary.
- [ ] The server was started only with an explicit gate.
- [ ] HTML, assets and API were blocked without a valid session token.
- [ ] The interface used no external resources.
- [ ] No documents, profiles, or index data were modified.
- [ ] The session token was not stored permanently or shared.
- [ ] The local listener is terminated after use.

## Pitfalls

- Switching profiles is **not** a user switch. For true separation, a different operating system account with its own file permissions is required.
- `localhost` is intentionally not equivalent to `127.0.0.1`; the exact host contract protects against ambiguous browser and proxy resolution.
- A copied link contains the session token. It must not leave the local machine or the active session.
- Write or domain‑sensitive functions remain in their respective Approval and Gate workflows; the GUI does not bypass them.

## Related

- [`../docs/phase35-local-app-plan.md`](../docs/phase35-local-app-plan.md)
- [`../skills/folderhome-local-app/SKILL.md`](../skills/folderhome-local-app/SKILL.md)
- [`./document-library.md`](./document-library.md)
- [`./document-action-execution.md`](./document-action-execution.md)

## History

- **2026-08-22** — local API, GUI, OS account boundary and runtime contract approved

---
