# Workflow: Persönliche Notiz geführt und revisionssicher ablegen

> **Last verified:** 2026-08-22
> **Frequency:** bei ausdrücklich gewünschter persönlicher Notiz
> **Duration:** Planung und lokale Ablage wenige Sekunden

## Purpose

Einen menschlich formulierten Notizinhalt mit getrennten Fragen und
Vorschlägen prüfen, exakt freigeben und als neue Version im gepinnten lokalen
`llm-note`-Store ablegen.

## Preconditions

- Profil, Notizbuch, Bereich und State-Ordner sind ausdrücklich gewählt.
- Der `llm-note`-Checkout ist sauber und auf der Manifestrevision.
- Der Mensch hat den zu speichernden Inhalt selbst formuliert oder sichtbar
  bestätigt.
- Eine reale Remote-LLM- oder Synchronisierungsfreigabe ist nicht Bestandteil
  dieses Workflows.

## Steps

1. **Provider prüfen** — Checkout, Revision und Paketversion müssen `ready`
   sein.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome notes providers --provider-root ..\llm-note --json
   ```

2. **Anfrage erstellen** — `create`, `edit` oder `revert` sowie ausschließlich
   explizite Referenzen deklarieren.
3. **Führung planen** — der read-only Lauf erzeugt Fragen und Vorschläge, aber
   keinen State.

   ```powershell
   $plan = python -m folderhome notes guide `
     --request-file examples\notes\create-request.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-note-demo" `
     --provider-root ..\llm-note --json | ConvertFrom-Json
   ```

4. **Menschlich prüfen** — `proposed_content`, Referenzen, Fragen,
   Vorschläge, `plan_id`, `plan_sha256` und `content_sha256` kontrollieren.
5. **Approval getrennt erstellen** — die Datei übernimmt exakt Plan-ID,
   Planhash, Aktions-ID und Inhaltshash, einen Offset-Zeitstempel sowie
   `allow_local_note_write=true`.
6. **Version anhängen** — erst jetzt beide Schreibgates setzen.

   ```powershell
   python -m folderhome notes apply `
     --request-file examples\notes\create-request.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-note-demo" `
     --provider-root ..\llm-note `
     --approval-file <approval.json> --approve-state-write --json
   ```

7. **Historie lesen** — Notiz-ID aus dem Plan verwenden.

   ```powershell
   python -m folderhome notes history --note-id $plan.note_id `
     --state-dir "$env:TEMP\folderhome-note-demo" `
     --provider-root ..\llm-note --json
   ```

## Exit-Criteria

- [ ] Providerrevision und Paketversion sind bestätigt.
- [ ] Fragen und Vorschläge stehen getrennt vom bestätigten Inhalt.
- [ ] Ohne Approval und State-Gate wurde nichts geschrieben.
- [ ] Der Readback enthält genau die neue append-only Revision.
- [ ] Frühere Revisionen blieben erhalten.
- [ ] Netzwerk und externe Synchronisierung blieben aus.

## Fallstricke

- `llm-note` erzeugt selbst keine LLM-Fragen; es ist der lokale Speicher.
- Ein Profil ist keine Zugriffskontrolle gegenüber anderen Prozessen im
  selben Betriebssystemkonto.
- `revert` löscht keine spätere Fassung, sondern hängt eine neue Version mit
  dem früheren Inhalt an.
- Ein Dokumenthash in einer Referenz beweist nicht, dass das Dokument später
  unverändert verfügbar ist.
- Ein Guide-Plan ist keine Speicherfreigabe.

## Verwandte

- [`../docs/phase28-llm-note-reuse-and-plan.md`](../docs/phase28-llm-note-reuse-and-plan.md)
- [`../skills/folderhome-personal-notes/SKILL.md`](../skills/folderhome-personal-notes/SKILL.md)
- [`../reused/llm-note/README.md`](../reused/llm-note/README.md)

## Historie

- **2026-08-22** — gepinnten llm-note-Speicher, getrennte Führung und
  append-only Versionsablage lokal abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
