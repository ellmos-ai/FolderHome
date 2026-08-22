---
name: folderhome-local-app
description: Checks and launches the shared local FolderHome interface exclusively on 127.0.0.1, protects it with a short-lived session token, and uses existing document search as well as read‑only theme dossiers within the security boundary of the operating system account.
---

# FolderHome Local App

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a human wants to operate the local FolderHome interface for document search, theme dossiers, and the overview of available capabilities.

## Procedure

1. Require an existing profile directory and an existing local KnowledgeDigest state of the current operating system account.  
2. First execute `folderhome app plan` and verify the provider revision, loopback binding, profile contract, and disabled side effects.  
3. Visibly explain that profiles are only organizational and do not represent access boundaries within the same OS account.  
4. Start `folderhome app serve` only after an intentional local approval using `--approve-loopback-server`.  
5. Use exclusively the token URL emitted by the startup run.  
6. In the GUI, use only the allowlisted read‑only functions search and theme dossier.  
7. Terminate the server after the session and treat the session token as a short‑lived local secret.

## Binding Limits

- Never bind to `0.0.0.0`, a LAN address, or an external host.  
- No port forwarding, reverse proxy, CORS, or external browser access.  
- Do not log, transmit, or persist the session token.  
- Do not pass arbitrary paths, shell commands, or generic plugin calls to the API.  
- Do not expose profile selection as authentication or access protection.  
- Do not modify documents, profiles, or index data from the GUI.  
- Display provider errors without internal paths or technical secrets.  
- Write, legal, medical, and financial actions must only be continued through their separate domain, approval, and execution workflows.

---
