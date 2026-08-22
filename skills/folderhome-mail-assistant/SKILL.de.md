---
name: folderhome-mail-assistant
description: Plane FolderHome-Mailabrufe read-only, verbinde einen Brief ausdrücklich mit einem aktiven Kontakt und bereite einen exakt freigegebenen, idempotenten Versand vor.
---

# FolderHome Mail Assistant

[English](./SKILL.md) | **Deutsch**

Beginne mit der revisionsgenauen Providerinventur:

```powershell
python -m folderhome mail providers --json
```

Erzeuge danach einen Ingest-Plan. Der Plan liest noch kein Postfach und führt
keinen Provider aus:

```powershell
python -m folderhome mail ingest-plan `
  --accounts-file <mail-accounts.json> `
  --request-file <mail-ingest-request.json> `
  --profiles-dir <profiles-dir> `
  --approve-sensitive-local-read `
  --json
```

## Verbindliche Grenzen

- Hinterlege nur `keyring://`, `env://` oder synthetische Secret-Referenzen,
  niemals Passwörter oder Tokens in einer Konfigurationsdatei.
- Ein Ingest-Plan enthält ausschließlich `fetch_headers` und optional
  `fetch_attachments`. Verschieben, Löschen, Markieren und Senden sind davon
  getrennte Fähigkeiten.
- Verwende einen Entwurf nur, wenn Profil, Konto, aktive Kontakt-ID,
  Empfängeradresse, Korrespondenz-Vorschau-ID und Texthash exakt passen.
- Vorschau bedeutet nicht Versand. Eine Versandfreigabe bindet Entwurfs-ID,
  Entwurfshash, Empfänger und Idempotenzschlüssel.
- Reale Netzwerk-Lese- und Versandaktionen brauchen jeweils ein eigenes
  Nutzer-Gate. Der synthetische Gateway beweist nur den Ablauf ohne Netzwerk
  und ohne echte E-Mail.
- Eine reservierte Versandfreigabe wird nicht automatisch wiederholt. Ein
  unklar abgebrochener Lauf muss im Ledger geprüft werden.

UniversalDocsGrabber bleibt der vorgesehene IMAP-Dokumentprovider. Lade ihn
nur an der im Plan genannten sauberen Revision. UniversalMailCleaner bleibt
wegen seiner Postfachmutationen außerhalb des read-only Ingests. MailProcessor
ist ein Launcher, kein Runtime-Connector. Der lokale SMTP-Seam besitzt in
Phase 26 ausschließlich einen synthetischen Provider.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
