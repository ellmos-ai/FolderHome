# Phase 26 — Controlled Mail Connector

**English** | [Deutsch](./phase26-mail-connector-plan.de.md)

**Status:** locally completed, 225 tests green  
**As of:** 2026-08-22  
**Product name in competition:** FolderHome

## Goal

FolderHome shall collect documents from explicitly selected IMAP mailboxes and be able to hand over existing correspondence to an explicitly confirmed contact. Mailbox reading, local attachment output, mailbox mutations and email sending remain four separate approval areas.

## Revision inventory

| Component | Revision finding | Phase‑26 role |
|---|---|---|
| MailProcessor 0.1.0 | Remote `704575901b8b526dcd1436a86d6f42818b4079cd`; local clean checkout is on a different revision | Suite launcher and inventory proof, no runtime connector |
| UniversalDocsGrabber 1.1.4 | Remote `0ccd03455b63acbca6e71cc48ba464f208a759cd`; local checkout is older and contains foreign web changes | intended read‑only IMAP/attachment provider, currently blocked |
| UniversalMailCleaner 1.2.0 | Remote `85de4dd2e84c499152b09d4e5688332ff3bb2ed4`; local checkout contains foreign changes | mailbox cleaning deliberately remains outside the ingest |
| UniversalInvoiceMail 2.3.0 | Remote `c58be4cdf92d8265694037cf1dbf7f14c84b39f9`; no local checkout | specialized invoice reference, not integrated |
| `connectors` 1.1.0 | local checkout `15a98fe77e61d0b371fbe8499f78e884f442398d`, diverges from remote; contains Telegram, Discord, Signal, WhatsApp, Home Assistant and Webhook, but no mail | no mail provider; unchanged |
| FolderHome Mail Gateway | `working-tree`, new in the competition period | provider‑neutral contract, synthetic no‑network gateway and local ledger |

The revision‑related statements are a snapshot from 22 August 2026. No foreign checkout was altered, updated or cleaned.

## New encapsulated core

- `folderhome.contracts.mail`
- `folderhome.application.mail_connector`
- `folderhome.capabilities.mail_gateway`
- `folderhome-mail-assistant`‑Skill

The contracts model mail account, IMAP and SMTP endpoint, `MailFolderReference`, message and attachment references, ingest plan, recipient binding, draft preview, approvals as well as reports. In the account JSON only `keyring://`, `env://` or `synthetic://` are allowed as credential references. Unknown fields such as `password` are fail‑closed rejected.

## Ingest boundary

A `folderhome.mail-ingest-plan.v1` may contain only `fetch_headers` and optionally `fetch_attachments`. `mailbox_mutations=[]` and `provider_invoked=false` are contract invariants. Before execution, the plan ID, plan hash, provider ID, provider revision and the read‑only guarantee of the gateway are re‑checked. Network reading and local writing of attachments have separate approvals.

## Contact, letter and dispatch

A mail draft is created only when the following values match simultaneously:

- profile and mail account
- active contact ID and its current email address
- recipient address of the correspondence
- correspondence preview ID and text hash
- letter sender and account address, if the letter mentions an email

The preview is read‑only. A downstream approval binds draft ID, draft hash, recipient, timestamp and deterministic idempotency key. The SQLite ledger reserves the approval and key before transport. This blocks an automatic second dispatch; an unclear abort remains subject to verification.

## Synthetic acceptance

The `SyntheticMailGateway` performs neither network activity nor real dispatch. The test case reads a synthetic insurance message with PDF reference, links a letter with the active Hyundai‑i10 insurance contact, simulates exactly one delivery and rejects the repetition in the ledger. Additionally, a dedicated test shows that a gateway marked as network‑required without dispatch approval is stopped before transport.

## Product limits

- A `ready` plan is not yet a mailbox fetch.
- `simulated` is expressly not a sent email.
- A real SMTP transport was not implemented or tested.
- Moving, deleting and flagging messages are not part of the read‑only ingest.
- Real credentials, network accesses and dispatch remain user gates.
- The profiles within an operating‑system account are organizational rules and not a cryptographic tenant separation.

---
