# Phase 26 — Kontrollierter Mail-Connector

**Status:** lokal abgeschlossen, 225 Tests grün  
**Stand:** 2026-08-22  
**Produktname im Wettbewerb:** FolderHome

## Ziel

FolderHome soll Dokumente aus ausdrücklich gewählten IMAP-Postfächern
einsammeln und vorhandene Korrespondenz an einen ausdrücklich bestätigten
Kontakt übergeben können. Postfachlesen, lokale Anhangsausgabe,
Postfachmutationen und E-Mail-Versand bleiben vier getrennte
Freigabebereiche.

## Revisionsinventur

| Baustein | Revisionsbefund | Phase-26-Rolle |
|---|---|---|
| MailProcessor 0.1.0 | Remote `704575901b8b526dcd1436a86d6f42818b4079cd`; lokaler sauberer Checkout steht auf einer anderen Revision | Suite-Launcher und Bestandsnachweis, kein Runtime-Connector |
| UniversalDocsGrabber 1.1.4 | Remote `0ccd03455b63acbca6e71cc48ba464f208a759cd`; lokaler Checkout ist älter und enthält fremde Web-Änderungen | vorgesehener read-only IMAP-/Anhangsprovider, aktuell blockiert |
| UniversalMailCleaner 1.2.0 | Remote `85de4dd2e84c499152b09d4e5688332ff3bb2ed4`; lokaler Checkout enthält fremde Änderungen | Postfachbereinigung bleibt bewusst außerhalb des Ingests |
| UniversalInvoiceMail 2.3.0 | Remote `c58be4cdf92d8265694037cf1dbf7f14c84b39f9`; kein lokaler Checkout | spezialisierte Rechnungsreferenz, nicht angebunden |
| `connectors` 1.1.0 | lokaler Checkout `15a98fe77e61d0b371fbe8499f78e884f442398d`, gegenüber Remote divergiert; enthält Telegram, Discord, Signal, WhatsApp, Home Assistant und Webhook, aber keine Mail | kein Mailprovider; nicht verändert |
| FolderHome Mail Gateway | `working-tree`, neu im Wettbewerbszeitraum | providerneutraler Vertrag, synthetischer No-Network-Gateway und lokales Ledger |

Die revisionsbezogenen Aussagen sind ein Snapshot vom 22. August 2026. Kein
fremder Checkout wurde verändert, aktualisiert oder bereinigt.

## Neuer gekapselter Kern

- `folderhome.contracts.mail`
- `folderhome.application.mail_connector`
- `folderhome.capabilities.mail_gateway`
- `folderhome-mail-assistant`-Skill

Die Verträge modellieren Mailkonto, IMAP- und SMTP-Endpunkt,
`MailFolderReference`, Nachrichten- und Anhangsreferenzen, Ingest-Plan,
Empfängerbindung, Entwurfsvorschau, Freigaben sowie Reports. In Konto-JSON ist
nur `keyring://`, `env://` oder `synthetic://` als Credential-Referenz erlaubt.
Unbekannte Felder wie `password` werden fail-closed abgewiesen.

## Ingest-Grenze

Ein `folderhome.mail-ingest-plan.v1` darf nur `fetch_headers` und optional
`fetch_attachments` enthalten. `mailbox_mutations=[]` und
`provider_invoked=false` sind Vertragsinvarianten. Vor einer Ausführung werden
Plan-ID, Planhash, Provider-ID, Providerrevision und die read-only Garantie des
Gateways erneut geprüft. Netzwerklesen und lokales Schreiben von Anhängen
besitzen getrennte Freigaben.

## Kontakt, Brief und Versand

Ein Mailentwurf entsteht nur, wenn folgende Werte gleichzeitig passen:

- Profil und Mailkonto
- aktive Kontakt-ID und deren aktuelle E-Mail-Adresse
- Empfängeradresse der Korrespondenz
- Korrespondenz-Vorschau-ID und Texthash
- Briefabsender und Konto-Adresse, sofern der Brief eine E-Mail nennt

Die Vorschau ist read-only. Eine nachgelagerte Freigabe bindet Entwurfs-ID,
Entwurfshash, Empfänger, Zeitpunkt und deterministischen Idempotenzschlüssel.
Das SQLite-Ledger reserviert Freigabe und Schlüssel vor dem Transport. Dadurch
wird ein automatischer zweiter Versand blockiert; ein unklarer Abbruch bleibt
prüfpflichtig.

## Synthetische Abnahme

Der `SyntheticMailGateway` führt weder Netzwerk noch echten Versand aus. Der
Testfall liest eine synthetische Versicherungsnachricht mit PDF-Referenz,
verbindet einen Brief mit dem aktiven Hyundai-i10-Versicherungskontakt,
simuliert genau eine Zustellung und weist die Wiederholung am Ledger ab.
Zusätzlich belegt ein eigener Test, dass ein als netzwerkpflichtig markierter
Gateway ohne Versandfreigabe vor dem Transport gestoppt wird.

## Produktgrenzen

- Ein `ready`-Plan ist noch kein Postfachabruf.
- `simulated` ist ausdrücklich keine versendete E-Mail.
- Ein echter SMTP-Transport wurde nicht implementiert oder getestet.
- Verschieben, Löschen und Markieren von Nachrichten gehören nicht zum
  read-only Ingest.
- Reale Credentials, Netzwerkzugriffe und Versand bleiben Nutzer-Gates.
- Die Profile innerhalb eines Betriebssystemkontos sind organisatorische
  Regeln und keine kryptografische Mandantentrennung.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
