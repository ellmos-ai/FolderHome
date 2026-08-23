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

1. **Plan the bounded master-agent interface.**

   ```powershell
   folderhome agent plan --profiles-dir <profiles-dir> --state-dir <state-dir> --model-provider fixture --json
   ```


2. **Check the plan.** The framework must be `strands-agents`, tool execution `sequential`, the tools must be exactly allow‑listed and all limits must be finite. A plan does not trigger any model call.

3. **Start an in-process conversation with the master through the CLI.** The
   session keeps bounded model-visible history and displayed plans available
   for follow-ups and a separate `/confirm <plan_id>` command. The default
   history window is 24 messages and can be reduced with
   `--max-conversation-messages`. Add `--json` for NDJSON events.

   ```powershell
   folderhome agent session --profiles-dir <profiles-dir> --state-dir <state-dir> --profile-id lukas --model-provider fixture
   ```

   Use `/reset` to clear the selected profile's retained conversation and
   unconfirmed plans without deleting domain data. Use `/help`, `/catalog` and
   `/quit` for the other session controls.

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
- [ ] Follow-up context remained within the configured message window and
  `/reset` cleared it explicitly.
- [ ] Ordinary chat did not count as approval; `/confirm` used the displayed
  plan ID inside the same process.  
- [ ] The reproducible run required neither network nor credentials.  
- [ ] Demo artifacts contain exclusively synthetic data.  
- [ ] `EVIDENCE.json` and the SHA‑256 values mentioned therein are correct.  
- [ ] No existing target was overwritten.  
- [ ] A Bedrock or other external run was not started without user approval.

## Pitfalls

- The fixture provider occupies the Strands orchestration, but not model quality or AWS availability.  
- The application contains no keyword workflow router. Fixture branching exists only to make the offline read-only acceptance reproducible; live semantic selection belongs to the configured model.
- `--allow-network` is only the technical run gate. Sharing local search results additionally requires `--approve-sensitive-cloud-data`; both gates authorize neither costs, uploads nor publication.  
- Family profiles share the same file permissions within the same OS account.  
- Conversation history exists only in the current process. It is not restored
  after exit and must not be treated as a user profile database or audit log.
- The master allowlist contains two read-only document tools, capability discovery and a specialist consultation tool. Specialists receive one plan-only endpoint and no executor.

## Related

- [`../skills/folderhome-strands-agent/SKILL.md`](../skills/folderhome-strands-agent/SKILL.md)  
- [`./local-app.md`](./local-app.md)  
- [`./document-library.md`](./document-library.md)  
- [`../docs/phase36-completion-audit.md`](../docs/phase36-completion-audit.md)

## History

- **2026-08-22** — Strands Agent, fixture model, separate Bedrock gates and demo acceptance added
- **2026-08-22** — bounded conversational continuity and explicit `/reset` added

---
