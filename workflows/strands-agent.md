# Workflow: Run Strands Agent and Competition Demo

**English** | [Deutsch](./strands-agent.de.md)

> **Last verified:** 2026-08-22  
> **Frequency:** per demo or agent acceptance  
> **Duration:** a few seconds without Bedrock; provider‑dependent with Bedrock  

## Purpose

Plan a limited execution of the real Strands‑Agents loop from FolderHome, run it reproducibly with synthetic data, and generate a hash‑bound competition evidence. The process separates no‑network evidence from an optionally approved Bedrock run.

## Preconditions

- Python 3.11 or newer and `strands-agents==1.53.0` are installed.  
- For a production local index run, a profile directory, KnowledgeDigest state, and an exactly pinned provider checkout exist.  
- The self‑contained competition demo requires no provider credentials or real personal data.  
- A Bedrock run has separate network, data‑sharing, and cost decisions.

## Steps

1. **Plan the agent interface as read‑only.**

   ```powershell
   folderhome agent plan --profiles-dir <profiles-dir> --state-dir <state-dir> --model-provider fixture --json
   ```


2. **Check the plan.** The framework must be `strands-agents`, tool execution `sequential`, the tools must be exactly allow‑listed and all limits must be finite. A plan does not trigger any model call.

3. **Execute a local request via the fixture agent.**

   ```powershell
   folderhome agent run --profiles-dir <profiles-dir> --state-dir <state-dir> --profile-id lukas --prompt "Gib mir alles zum Thema Krankenversicherung." --model-provider fixture --json
   ```


4. **Read the agent report.** Verify `stop_reason=end_turn`, at least one executed tool event, correct input/output hashes, `network_used=false`, and an empty side‑effect list.

5. **Generate a self‑contained competition demo.** The target must be new.

   ```powershell
   folderhome demo run --output-dir <new-demo-dir> --approve-output-write --json
   ```


6. **Read back the evidence.** Verify `EVIDENCE.json`, the three artifact hashes mentioned there, both scenarios, and the visible labeling of synthetic data in `DEMO.md`.

7. **Decide the optional Bedrock run separately.** Only after explicit user approval provide model ID, region, `--allow-network` and `--approve-sensitive-cloud-data`. Log the result as Bedrock evidence rather than as a fixture proof.

## Exit-Criteria

- [ ] The real Strands SDK loop has executed at least one FolderHome tool.  
- [ ] Tool order, turn count, and result size were limited.  
- [ ] The reproducible run required neither network nor credentials.  
- [ ] Demo artifacts contain exclusively synthetic data.  
- [ ] `EVIDENCE.json` and the SHA‑256 values mentioned therein are correct.  
- [ ] No existing target was overwritten.  
- [ ] A Bedrock or other external run was not started without user approval.

## Pitfalls

- The fixture provider occupies the Strands orchestration, but not model quality or AWS availability.  
- `--allow-network` is only the technical run gate. Sharing local search results additionally requires `--approve-sensitive-cloud-data`; both gates authorize neither costs, uploads nor publication.  
- Family profiles share the same file permissions within the same OS account.  
- The agent allowlist intentionally contains no write‑capable domain workflows.

## Related

- [`../skills/folderhome-strands-agent/SKILL.md`](../skills/folderhome-strands-agent/SKILL.md)  
- [`./local-app.md`](./local-app.md)  
- [`./document-library.md`](./document-library.md)  
- [`../docs/phase36-completion-audit.md`](../docs/phase36-completion-audit.md)

## History

- **2026-08-22** — Strands Agent, fixture model, separate Bedrock gates and demo acceptance added

---
