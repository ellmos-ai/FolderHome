# Agents for Humans — Requirements Snapshot

**Checked:** 2026-08-23 via the authenticated Devpost event data  
**Official rules:** <https://agentsforhumans.devpost.com/rules>  
**FAQ:** <https://agentsforhumans.devpost.com/details/faqs>  
**Submission deadline:** 2026-09-14, 17:00 PDT

This file is a dated implementation checklist, not a substitute for the
official rules. Recheck the official pages immediately before submission.

## Mandatory project requirements

- Build a new AI agent during the submission period.
- Use the Strands Agents SDK as a required developer tool.
- Solve a real problem for real people and handle actual work, not only chat.
- Run consistently on the declared platform and match the submitted demo.
- Disclose incorporated pre-existing work.
- Hold the rights and satisfy licenses for third-party integrations.

FolderHome response:

- Repository and `NEW_CORE` implementation were created during the submission
  period.
- `strands-agents==1.53.0` is an exact runtime dependency.
- The Strands loop executes bounded, sequential FolderHome document tools.
- The core solves recurring household-document work while preserving human
  review and side-effect gates.
- `COMPETITION_CODE_MAP.md` and `THIRD_PARTY_LICENSES.md` disclose reused work.
- The self-contained demo uses only synthetic data and no credentials.

## Mandatory submission materials

- English project description.
- Public GitHub, GitLab or Bitbucket repository with all required code,
  assets and instructions.
- MIT or Apache license visible in the repository.
- README.
- Architecture diagram showing interface, Strands loop, tools/integrations
  and used AWS services.
- Public YouTube or Vimeo video, no longer than five minutes, with a working
  demo and a pitch covering problem, audience and importance.
- AWS Builder ID.
- A project that installs and runs consistently as described, with the public
  repository containing the source, assets and setup instructions required to
  test it. A public live-demo URL is optional and can strengthen the
  Technological Implementation score.

Prepared locally:

- `DEVPOST_DRAFT_EN.md`
- `TESTING_INSTRUCTIONS_EN.md`
- `VIDEO_SCRIPT_EN.md`
- `ARCHITECTURE_DIAGRAM.md`
- `SUBMISSION_CHECKLIST.md`
- Repository `LICENSE`, `README.md` and synthetic `folderhome demo run`

Published repository:

- <https://github.com/ellmos-ai/FolderHome>

Published video:

- <https://youtu.be/wPb1wBJcLjQ> (3:26, v3 with orchestral score, accepted 2026-08-30; v2 was 2:59)

Still requiring the human's external gate:

- AWS Builder ID entry.
- GitHub Pages deployment and live-demo readback.
- Final Devpost review and submit.

## Recommended track

**Everyday Agents.** The primary user is a person or household managing daily
documents, contracts, appointments, money, health administration and errands.
The track is selected by primary audience rather than implementation details.

## Judging alignment

- **Technological Implementation:** real Strands loop, finite sequential tools,
  testable contracts, separately gated Bedrock path, deterministic
  no-credential demo.
- **Design:** coherent local CLI, API and responsive GUI on one application
  service, not a collection of unrelated prompts.
- **Potential Impact:** reduces repetitive work around scattered household
  documents while keeping sensitive data and consequential actions controlled.
- **Creativity and Originality:** combines document gardening, evidence-bound
  household assistance and reusable domain modules under one agent.
- **Presentation:** the proposed video follows one problem-to-outcome story and
  demonstrates the actual agent tool loop end to end.

## Optional items

- Bedrock AgentCore or a public live demo can strengthen Technological
  Implementation, but neither is required by the rules.
- Registered individuals may request USD 50 in AWS promotional credits while
  supplies last. The official request deadline is 2026-09-11, 12:00 PDT
  (21:00 CEST); the credits expire on 2026-10-31.
- Public builder.aws posts can add bonus points. Following the official
  2026-08-12 rules update, the title must contain `Agents for Humans`; the
  former `#AgentsforHumans` requirement no longer applies.
- No optional publication is authorized by this prepared package.
