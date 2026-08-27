# FolderHome Submission Checklist

## Local package

- [x] Final full test count recorded in the completion audit
- [x] Ruff, compileall, plugin, documentation, workflow and skill checks green
- [x] Reproducible demo rerun from a clean new output directory
- [x] Demo artifact SHA-256 values recorded
- [x] README reflects Strands, installation and current limits
- [x] Architecture diagram matches the code
- [x] `COMPETITION_CODE_MAP.md` and `THIRD_PARTY_LICENSES.md` current
- [x] Security and privacy wording reviewed
- [x] English description and testing instructions proofread
- [x] Root `devpost-submission.md` consolidated against the authenticated
  submitted project, current product coverage and AWS readback
- [x] Video script contains only implemented or visibly qualified behavior
- [x] End-to-end synthetic accident story executes four real typed adapters
- [x] Token-gated bilingual local demo with light/dark themes tested
- [x] Public static showcase is visibly labelled as scripted and backend-free
- [x] Built static showcase smoke-tested in Edge and Chrome at 1440×1100 and
  390×844: HTTP 200, exact viewports, no horizontal overflow, EN→DE and
  dark→light switches working in four isolated browser contexts
- [x] AgentCore HTTP contract, session isolation and ARM64 container candidate tested locally
- [x] Earlier demo render explicitly rejected and excluded from submission evidence
- [x] Replacement-video learnings recorded in English and German
- [x] Final wheel installed outside the repository; packaged GUI, four-result
  accident journey and AgentCore `/ping` smoke tested without network use
- [x] First 150-second replacement render rejected after human review and
  excluded from submission evidence
- [x] New 179-second v2 candidate rendered without an embedded subtitle stream;
  1920×1080, 30 fps, H.264 High/AAC stereo, 5,370 frames, SHA-256
  `46cd9b8f23b4d3de27b731ab4a76dcd9f5f258a4ec1d555115c79359815faa5b`
- [x] V2 candidate checked with HyperFrames browser gates, `ffprobe`, loudness
  analysis and timestamped contact sheets

## Human-only external gates

- [x] Confirm participant eligibility and representative as an individual
- [x] Confirm AWS Builder ID to enter
- [x] Authorize and create public repository
- [x] Make MIT license available as root `LICENSE`
- [x] Insert public repository URL into README and testing instructions
- [x] Create the FolderHome Devpost project and associate it with Agents for Humans
- [x] Verify the Devpost project live as an authored, in-progress draft
- [x] Confirm the required Devpost repository field contains the public URL
- [x] Replace the older two-tool Devpost description with the four-tool
  master-agent and accident-demo narrative
- [x] Prepare an English Builder article draft with the current honest AWS boundary
- [x] Enable GitHub Pages and verify the public showcase URL
- [x] Deploy the quota-bounded direct-code AgentCore runtime and read it back as
  `READY`; verify one synthetic fixture invocation up to `confirmation_required`
- [ ] Verify one Bedrock-backed AgentCore journey only after AWS assigns non-zero
  on-demand quotas and the user separately authorizes `manage.py verify`
- [x] Record final working demo from the verified build
- [x] Verify that v2 has no embedded subtitle stream and retains privacy and
  synthetic-data labels
- [x] Human watched and accepted the v2 candidate as the submission video on
  2026-08-23
- [x] Authorize and complete public YouTube upload
- [x] Insert public video URL: <https://youtu.be/2LeWU_WJZKM>
- [x] Decide to provide the optional static GitHub Pages showcase
- [x] Upload the required architecture diagram
- [x] Enter the private AWS Builder ID without storing it in the repository
- [x] Add the live showcase and current testing instructions
- [x] Recheck official rules and deadline immediately before submission
- [x] Review every Devpost field
- [x] Complete the final Devpost submit through the authenticated human session
- [x] Read back a non-null submission timestamp after submission
- [ ] Review and authorize Builder article publication

## Live Devpost readback — 2026-08-23

- Project: `FolderHome` (`folderhome`, project ID `1395740`)
- State: submitted to Agents for Humans
- Hackathon: Agents for Humans
- Public project URL assigned by Devpost: <https://devpost.com/software/folderhome>
- Video URL: <https://youtu.be/2LeWU_WJZKM>
- Live showcase: <https://ellmos-ai.github.io/FolderHome/>
- Submitted at: `2026-08-23T17:14:05.813-04:00`
- Local plugin stage: Submit completed; post-submission review is next
- AWS credit request: submitted on 2026-08-23; the user reported the additional
  50 promotional credits as granted on 2026-08-26. This was not independently
  read back through a Billing API in the consolidation run

## Live AWS readbacks — 2026-08-26/27

- Bootstrap and application stacks: `CREATE_COMPLETE`
- AgentCore Runtime `FolderHomeDemo-V7fjgTH232`: `READY`, version 4, HTTP
- Public quota API key: enabled; CloudFront browser agent path: `enabled: false`
- Monthly budget: 5 USD; calculated actual spend: 0.018 USD
- EU Nova Micro profile: `ACTIVE`, but applied cross-region quotas remain zero
- Exactly one 16-token Converse request on 2026-08-26, no retry:
  `ThrottlingException`
- Rechecked after successful OAuth renewal on 2026-08-27: Runtime still
  `READY`, version 4; profile still `ACTIVE`; 0 tokens/minute,
  0 requests/minute and 0 tokens/day
- CloudWatch 24-hour readback: one throttled request, no successful invocation
  and no input or output tokens; no second model request was sent

## Post-submit maintenance

- [x] Detect that the branch-published showcase omitted three referenced brand assets
- [x] Add the canonical logo, icon and favicon below `site/assets/`
- [x] Replace the obsolete Actions-workflow test with a branch-publishing asset contract
- [x] Run the complete suite on the consolidated working tree and repeat it
  after the provider provenance repin: 503 passed, zero failed in both runs
- [x] Push the source commits and updated `gh-pages` branch
- [x] Verify the public page and brand asset URLs with HTTP 200
- [ ] Create and read back a fixed submission tag or release

## Never infer these states

- An empty or inaccessible remote is not a published source tree.
- A video file is not a public video URL.
- A saved Devpost draft is not a submitted entry.
- A fixture Strands run is not a Bedrock deployment.
- An architecture path is not a tested live connector.
