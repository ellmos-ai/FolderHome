# Workflow: Mail sicher lesen, zuordnen und freigeben

> **Last verified:** 2026-08-22
> **Frequency:** bei ausdrücklich ausgelöstem Mailabruf oder Versand
> **Duration:** Plan unter einer Sekunde; Providerlauf abhängig vom Postfach

## Purpose

Einen Postfachabruf ohne Postfachänderung planen, eingehende
Nachrichtenreferenzen providerneutral übernehmen und einen Brief nur über eine
explizite Kontaktzuordnung für einen idempotenten Versand vorbereiten.

## Preconditions

- Mailkonto enthält nur Secret-Referenzen und gehört zum gewählten Profil.
- Postfach, Suchanfrage und Anhangsziel wurden ausdrücklich gewählt.
- Für einen Entwurf liegen ein aktiver Kontakt und eine unveränderte
  Korrespondenzvorschau vor.
- Reale Netzwerkaktionen besitzen eine separate Freigabe.

## Steps

1. **Provider inventarisieren** — Launcher, IMAP-Ingest, Cleaner,
   Rechnungsarchiv und synthetischen Gateway voneinander unterscheiden.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome mail providers --json
   ```

2. **Konfiguration lesen** — erst nach Freigabe; eingebettete Passwörter und
   unbekannte Felder werden blockiert.

3. **Read-only Plan erzeugen** — Providerrevision, Konto, Ordner, Suche und
   Maximalzahl prüfen. Ein blockierter Checkout beendet den Lauf.

   ```powershell
   python -m folderhome mail ingest-plan `
     --accounts-file examples\mail\accounts.json `
     --request-file examples\mail\ingest-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```

4. **Ingest exakt freigeben** — Plan-ID und Planhash binden. Netzwerklesen und
   lokales Schreiben von Anhängen getrennt erlauben. Das Gateway muss
   `read_only_ingest=true` garantieren.

5. **Empfänger ausdrücklich binden** — aktive Kontakt-ID und E-Mail-Adresse
   müssen zur Profilzuordnung sowie zum Empfänger der Briefvorschau passen.

6. **Entwurf prüfen** — Betreff, Absender, Empfänger, Brieftext, Anlagen und
   Hashes vollständig kontrollieren. Eine Vorschau ruft keinen Transport auf.

7. **Versand gesondert freigeben** — Entwurfs-ID, Entwurfshash, exakten
   Empfänger und deterministischen Idempotenzschlüssel bestätigen. Bei einem
   realen Gateway zusätzlich Netzwerkversand erlauben.

8. **Ledger prüfen** — Status `simulated` oder `sent` und Transport-ID lesen.
   Dieselbe Freigabe oder derselbe Idempotenzschlüssel darf kein zweites Mal
   verwendet werden.

## Exit-Criteria

- [ ] Konto und Profil stimmen überein; keine Zugangsdaten liegen im JSON.
- [ ] Ingest enthält keine Move-, Delete-, Flag- oder Send-Operation.
- [ ] Providerrevision und Checkoutstatus sind sichtbar.
- [ ] Kontakt und Korrespondenz sind exakt und ausdrücklich gebunden.
- [ ] Versandfreigabe und Ledger verhindern einen Wiederholungslauf.
- [ ] Ohne reales Nutzer-Gate wurden weder Netzwerk noch E-Mail ausgelöst.

## Fallstricke

- MailProcessor startet andere Programme, führt aber selbst keinen IMAP-Abruf
  für FolderHome aus.
- Ein vorhandener UniversalDocsGrabber-Ordner ist kein Beleg für eine saubere,
  passende Revision.
- UniversalMailCleaner darf wegen Lösch-/Verschiebefunktionen nicht als
  read-only Ingest-Gateway behandelt werden.
- `simulated` bedeutet ausdrücklich, dass keine E-Mail versendet wurde.
- `reserved` nach einem Abbruch ist ein Prüfzustand, keine Einladung zum
  automatischen Wiederholen.

## Verwandte

- [`../docs/phase26-mail-connector-plan.md`](../docs/phase26-mail-connector-plan.md)
- [`../skills/folderhome-mail-assistant/SKILL.md`](../skills/folderhome-mail-assistant/SKILL.md)

## Historie

- **2026-08-22** — Providerinventur, read-only Ingest und synthetischer
  Entwurfs-/Versandablauf erstmals lokal abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
