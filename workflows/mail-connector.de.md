# Workflow: Mail sicher lesen, zuordnen und freigeben

[English](./mail-connector.md) | **Deutsch**

> **Last verified:** 2026-08-25
> **Frequency:** bei ausdrücklich ausgelöstem Mailabruf oder Entwurfsablage
> **Duration:** Plan unter einer Sekunde; Providerlauf abhängig vom Postfach

## Purpose

Einen Postfachabruf ohne Postfachänderung planen, eingehende
Nachrichtenreferenzen providerneutral übernehmen und ein vorbereitetes
Schreiben als Entwurf in das eigene Postfach des Nutzers legen — niemals als
Zustellung an Dritte.

## Preconditions

- Mailkonto enthält nur Secret-Referenzen und gehört zum gewählten Profil.
- Postfach, Suchanfrage und Anhangsziel wurden ausdrücklich gewählt.
- Für einen Entwurf liegen ein aktiver Kontakt und eine unveränderte
  Korrespondenzvorschau vor.
- Reale Netzwerkaktionen besitzen eine separate Freigabe.

## Entwurfsablage über den Chat-Executor

Der verbundene Endpunkt legt ausschließlich Entwürfe ab. Er rendert genau eine
Korrespondenzvorschau in eine RFC-5322-Nachricht und hängt sie an den
konfigurierten Entwurfsordner des eigenen IMAP-Postfachs des Nutzers an. Dieser
Endpunkt besitzt keinen SMTP-Weg; kein Empfänger wird kontaktiert.

1. **Postfach im privaten Register deklarieren** — eine `file`-Ressource mit
   dem Zweck `mail.draft_account`, die auf ein Dokument nach
   `folderhome.mail-draft-account.v1` zeigt. Vorlage:
   [`../examples/mail/draft-account.example.json`](../examples/mail/draft-account.example.json).
   Den Entwurfsordner so eintragen, wie ihn das eigene Mailprogramm anzeigt,
   Umlaute eingeschlossen: `Entwürfe` ist richtig, und der Transport kodiert ihn
   selbst in den RFC-3501-Leitungsnamen `Entw&APw-rfe`. Beim Passwort wird nur
   die Quelle genannt, nie der Wert: entweder `keyring_service` und
   `keyring_user` oder `password_file` mit absolutem Pfad auf eine lokale Datei.
   Der Wert erscheint nie in Plan, Bericht, Chat oder Repository.

2. **Vorbereiten** — der Executor löst Postfach, Briefanfrage, Designs und
   Vorlagen über logische Ressourcen-IDs auf, baut die Korrespondenzvorschau
   erneut auf und rendert einen deterministischen Entwurf. Der Plan zeigt
   Betreff und Hashes, niemals den Brieftext, die Empfängeradresse, den Host
   oder den Passwort-Fundort.

3. **Genau einmal freigeben** — `/confirm <plan_id>` führt die vorbereitete,
   hashgebundene Hülle ein einziges Mal aus.

4. **Live-Effekt-Gate** — ohne `--approve-mail-draft` plant der Endpunkt, rührt
   das Postfach aber nicht an. Mit der Freigabe öffnet der Transport eine
   Sitzung, gleicht den konfigurierten Ordner gegen die Ordnerliste des
   Postfachs ab, hängt die Nachricht mit dem Flag `\Draft` an und meldet sich
   wieder ab. Ein Ordner, den das Postfach nicht kennt, bricht den Lauf ab; die
   Meldung nennt die tatsächlich vorhandenen Ordner.

5. **Ledger** — ein lokales SQLite-Ledger reserviert den deterministischen
   Idempotenzschlüssel vor der Ablage und hält `drafted` oder `failed` fest.
   Derselbe Entwurf kann nicht zweimal in dasselbe Postfach gelegt werden.

Anhänge werden in dieser Fassung fail-closed abgelehnt: Der Entwurf trägt nur
Text, und im Brief genannte Anlagen sind vor dem Senden von Hand anzuhängen.
Ohne deklarierte `mail.draft_account`-Ressource bleibt der Endpunkt ehrlich
`not_connected`.

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
- [ ] Der Entwurfsendpunkt hat höchstens eine Nachricht abgelegt und nichts
  versendet.
- [ ] Passwort, Host und Passwort-Fundort blieben aus Plan, Bericht und Chat
  heraus.

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

- [`../docs/phase26-mail-connector-plan.md`](../docs/phase26-mail-connector-plan.de.md)
- [`../skills/folderhome-mail-assistant/SKILL.md`](../skills/folderhome-mail-assistant/SKILL.md)

## Historie

- **2026-08-22** — Providerinventur, read-only Ingest und synthetischer
  Entwurfs-/Versandablauf erstmals lokal abgenommen
- **2026-08-25** — Reiner IMAP-Entwurfsendpunkt hinter `--approve-mail-draft`
  an den Chat-Executor angebunden; kein Versandweg ergänzt

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
