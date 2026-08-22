---
name: folderhome-strands-agent
description: Plans or starts the limited Strands‑Agents loop of FolderHome via profile‑bound read‑only document search and topic dossiers; uses the No‑Network‑Fixture‑Provider for reproducible tests and Bedrock only after separate network and data transfer approvals.
---

# FolderHome Strands Agent

**English** | [Deutsch](./SKILL.de.md)

Use this skill when a natural user request should be routed through the real Strands‑Agents loop to existing FolderHome document services, or when a verifiable competitive evidence is required.

## Procedure

1. Verify that `strands-agents==1.53.0` and the pinned KnowledgeDigest checkout are available.  
2. Execute `folderhome agent plan` with the profile and state directory.  
3. Check in the plan the OS account limit, the sequential tool mode, finite turn/tool/output limits, and `model_call_performed=false`.  
4. Use `--model-provider fixture` for reproducible No‑Network runs.  
5. Start `folderhome agent run` with a known organizational profile and a natural search or dossier prompt.  
6. Check in the report the framework version, stop reason, tool events, hash bindings, network status, and empty side‑effect list.  
7. Use Bedrock only upon explicit user request with model ID, AWS region, `--allow-network` and `--approve-sensitive-cloud-data`. None of the approvals replace a cost or publication permission.

## Binding Limits

- Do not provide arbitrary file paths, shell commands, or generic plugin calls as agent tools.  
- Only use the two approved read‑only tools `search_home_documents` and `build_home_theme_dossier`.  
- Never expose profiles as access or privacy boundaries.  
- Clearly label fixture results as synthetic and not as a Bedrock run.  
- Do not derive medical, legal, tax, or social‑law decisions from search results.  
- Do not infer network, email, calendar, phone, file, or cost effects from a mere agent request.  
- Never treat `--allow-network` as an approval to transfer local document contents or metadata.  
- On limit, provider, or schema errors, fail‑closed and stop.

---
