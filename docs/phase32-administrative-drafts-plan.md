# Phase 32: Controlled Administrative Drafts

**English** | [Deutsch](./phase32-administrative-drafts-plan.de.md)

**Status:** 2026-08-22  
**Purpose:** Generate appeal, authority‑response, and benefit‑application drafts from profile data, official‑notice evidence, and provided user statements, without asserting any legal review, benefit verification, or transmission.

## Reuse Alignment

Phase 32 does not build a second letter generator. The Phase‑24 core continues to handle:

- sender, recipient and addresses,
- design resolution by area, purpose and profile,
- strictly validated templates and placeholders,
- deterministic Markdown/TXT previews,
- output hashes, Never‑overwrite and partial rollback,
- visible, still blocked DOCX/ODT handoffs.

Phase 31 provides official‑notice type, authority, file reference, official‑notice date, legal remedy and additional fields with line, document ID and source hash. New are only the capsule `contracts.administrative_drafts` and `application.administrative_drafts`, which securely connect both records.

## Current Official Countercheck

For the product boundary, three official statutory pages were examined on 2026-08-22:

- [§ 84 SGG](https://www.gesetze-im-internet.de/sgg/__84.html) concerning form, filing office and the appeal deadline generally tied to the announcement,
- [§ 36 SGB X](https://www.gesetze-im-internet.de/sgb_10/__36.html) regarding the information required for a legal‑remedy instruction,
- [§ 16 SGB I](https://www.gesetze-im-internet.de/sgb_1/__16.html) concerning application submission and forwarding.

These sources are not written into the draft as a blanket case‑by‑case decision. Which legal route, which deadline, which form and which carrier actually apply requires a current professional assessment. Therefore Phase 32 does not calculate any deadline and does not confirm any jurisdiction.

## New Encapsulated Draft Contract

A request specifies exactly one type:

- `objection` for an appeal draft,
- `authority_response` for an authority‑response draft,
- `benefit_application` for a benefit‑application draft.

Official‑notice‑related drafts must be bound to the expected source SHA‑256. FolderHome re‑analyzes the source and requires the same profile, unique authority, file reference, official‑notice type and official‑notice date. The recipient must match the read authority. An appeal draft is only prepared if the document explicitly mentions the legal remedy `Widerspruch`. This check does not constitute a statement about whether it is permissible or timely in a particular case.

User statements and the desired outcome are called `user_provided` in the preview. They are not emitted as document facts. Only a separate approval confirms the concrete preview content for a local output. Document facts remain bound to their Phase‑31 evidence.

## Process and Side‑Effect Boundary

```text
Anfrage + Profil + Sensitivitätsfreigabe
  → bei Bescheidentwurf Quelle erneut analysieren und Hash prüfen
  → Dokumentevidenz und bereitgestellte Nutzeraussagen getrennt sammeln
  → Zweck und sichere Verwaltungsbriefvorlage fest binden
  → Phase-24-Korrespondenzvorschau nur im Speicher erzeugen
  → sichtbaren ENTWURF-/Prüfhinweis in den Brief aufnehmen
  → Plan, Briefhashes, offene Punkte und Warnungen anzeigen
  → Mensch prüft den vollständigen Inhalt
  → exakte Approval + Output-Gate schreibt neue Markdown-/TXT-Dateien
```


There is no send command. `send_supported`, `sent`, `eligibility_assessed` and `deadline_legally_calculated` remain `false`. The local approval is not an approval for email, upload, authority portal, printing or postal dispatch.

## Acceptance

The synthetic acceptance checks appeal, response and application boundaries, document/user provenance, profile and authority binding, explicit legal remedy, portable source‑hash binding, boolean approval fields, source changes, output gate and Never‑overwrite. The CLI test performs official‑notice analysis, preview, hash‑bound confirmation and local output end‑to‑end and confirms that no external effect occurred.

---
