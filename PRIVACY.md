# Privacy and Data Flows

**English** | [Deutsch](./PRIVACY.de.md)

**Reviewed:** 14 September 2026. This describes the software's data flows,
not a legal compliance certification or a hosting provider's privacy policy.

## What stays on this computer

FolderHome reads explicitly selected resources. Local extraction, document
search, household stores, letter rendering and approval checks run under your
operating-system account. Profiles organize household work; they do **not**
securely isolate people who share that account.

| Data | Storage / lifetime |
|---|---|
| Source documents | Your selected folders; ingest does not alter them |
| Search index and domain state | Configured local SQLite databases and state directories |
| Generated letters, bundles and receipts | Local output files; closing the app does not delete them |
| Chat history, pending plans, recipe runs and result views | Bounded process memory; not a restart-resume archive |
| Google event versions and calendar/mail attempt ledgers | Private persistent state used to prevent unsafe replay |
| Provider credentials | Configured private files; not part of model-facing resource catalogs |

Local files may themselves be in a synchronized or backed-up directory.
**Local processing does not disable your operating system's cloud sync.**
File permissions and storage protection belong to the operating-system account,
not the FolderHome profile selector.

## What can leave the computer

| Optional path | Data disclosed and boundary |
|---|---|
| Hosted model or non-loopback Ollama | Prompt, retained conversation and selected tool context go to the configured model endpoint, after network and data-disclosure gates |
| Google calendar | Approved event data and authenticated API requests go to Google; token refresh also contacts Google's OAuth endpoint |
| Own-mail draft | The prepared message, including recipient headers and body, goes to the configured IMAP provider; **unsent is not unshared** |
| Static public showcase | The hosting service receives ordinary web requests; the showcase does not read local household documents |

The deterministic fixture uses no model network call. Loopback Ollama uses a
local endpoint; a private-network address is still outside this computer.
Before remote model calls, default-on cloud pseudonymization replaces known
local identities and conservatively recognized sensitive patterns with stable,
process-local placeholders and restores them locally. This reduces exposure but
is not anonymity: unknown free-text identifiers may remain. It never replaces
the explicit network and sensitive-data approval gates.
Google metadata lookup requires a separate read approval. Calendar writes and
mail drafts require their own launch gates **and** exact plan confirmations.
The optional AgentCore competition runtime accepts the synthetic demo journey,
not private document uploads. Provider retention rules are outside FolderHome's
control; a local reset cannot delete copies held by an external service.

## What reset and close do not erase

Conversation reset clears the selected profile's retained chat and pending
plans and closes its recipe runs. It does not undo confirmed effects or erase
source documents, saved output, domain stores or durable connector ledgers.
Closing the app signals its owned scheduler workers; a bounded in-flight check
may still finish. This is not a global stop for other app instances.

There is no universal "erase all personal data" or remote-account deletion
command. In particular, **do not remove an attempt ledger to retry an uncertain
operation**: a remote effect may already exist. Reconcile the provider state
and the retained evidence first. Deleting local state does not revoke OAuth
consent or remove an IMAP draft or a Google event.

## Sharing diagnostics

Use synthetic examples for issues, screenshots and public evidence. Never share
OAuth JSON, API keys, mailbox passwords, session tokens or real household files.
Reports and generated artifacts can contain private domain content even when
their resource locators are hidden. Review them before sharing.

Implementation boundaries and confidential reporting:
[Security](./SECURITY.md). Detailed gates:
[calendar](./docs/phase27-calendar-connector-plan.md),
[mail](./docs/phase26-mail-connector-plan.md),
[scheduler](./docs/phase15-scheduler-handoff-plan.md).
