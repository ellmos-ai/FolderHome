# Öffentliche FolderHome-AWS-Demo

[English](./README.md) | **Deutsch**

Dieses Deployment hält die öffentliche Website statisch und leitet ausschließlich
den synthetischen Unfall-Use-Case an eine nur über IAM erreichbare Amazon Bedrock
AgentCore Runtime weiter. Der Master-Aufruf verwendet Strands Agents mit Amazon Nova
Micro. Nach dem exakten `/confirm` werden die vier lokalen Spezialistenpläne
deterministisch ausgeführt, damit Kosten und Antwortdauer der Browseranfrage begrenzt
bleiben.

## Sicherheits- und Kostengrenze

- Die Demo verarbeitet ausschließlich synthetische Testdaten.
- Sie kann keine E-Mail versenden, keinen externen Kalender verändern, keine
  Telefonnummer anrufen und keine Dateien der Besucher verändern.
- Der Browser-API-Key ist eine öffentliche Quotenkennung und keine Authentifizierung.
- Eine atomare DynamoDB-Bedingung erlaubt höchstens 20 gültige Weiterleitungen an
  AgentCore pro UTC-Tag. Das entspricht zehn vollständigen Demonstrationen mit jeweils
  zwei Anfragen.
- Quote und Drosselung des API-Gateway-Nutzungsplans sind zusätzliche
  Best-effort-Schutzschichten und nicht die harte Kostengrenze.
- API Gateway begrenzt Lastspitzen auf zwei Anfragen und 0,2 Anfragen pro Sekunde.
  Der AgentCore-SDK-Aufruf bricht nach 25 Sekunden ohne Wiederholungsversuch ab.
  Eine reservierte Lambda-Parallelität wird absichtlich nicht gesetzt, weil neue
  AWS-Konten nur die verpflichtenden zehn unreservierten Lambda-Ausführungen
  bereitstellen können; die atomare DynamoDB-Zulassung bleibt die harte Grenze
  vor AgentCore.
- CloudWatch verschlüsselt jede Loggruppe im Ruhezustand mit der serviceverwalteten
  AES-256-GCM-Verschlüsselung. Ein kundenseitig verwalteter KMS-Schlüssel wird bewusst
  nicht verwendet, damit für synthetische Daten keine monatlichen Fixkosten entstehen.
- Das AWS-Budget über 5 USD versendet Warnungen; es ist keine harte Ausgabensperre.
- Das Anlegen oder Aktualisieren von AWS-Ressourcen benötigt eine ausdrückliche
  Kostenfreigabe durch einen Menschen.

## Lokale Vorabprüfung

```powershell
python deploy/agentcore/build_direct_code.py
python deploy/aws_demo/build_proxy.py
python deploy/aws_demo/manage.py preflight
```

Build-Ausgaben verbleiben im ignorierten Ordner `build/`. API-Keys,
AWS-Konto-IDs, E-Mail-Adressen, generierte Laufzeitkonfiguration und Stack-Ausgaben
dürfen nicht committet werden.

## Deployment-Reihenfolge

1. Den Bootstrap-Stack mit einer Benachrichtigungsadresse sowie den exakten ARNs des
   Nova-Micro-Inferenzprofils und der Foundation Models anlegen.
2. Das versionierte Direct-Code-ZIP und das Lambda-Proxy-ZIP in den privaten
   Artefakt-Bucket hochladen.
3. Die Direct-Code-AgentCore-Runtime mit der Ausführungsrolle des Bootstrap-Stacks
   anlegen.
4. Die Runtime unmittelbar so aktualisieren, dass IMDSv2 erforderlich ist, und auf
   `READY` warten.
5. Den Anwendungs-Stack mit der Runtime-ARN und der Proxy-Objektversion anlegen.
6. `runtime-config.js` ausschließlich im ignorierten Site-Build-Ordner erzeugen, die
   statische Site in den privaten S3-Bucket synchronisieren und CloudFront
   invalidieren.
7. Einen vollständigen synthetischen Plan-und-Bestätigungsablauf über CloudFront
   prüfen.
8. API-Quote, API-Drosselung, Logaufbewahrung, Runtime-Einstellungen und
   Budgetbenachrichtigungen zurücklesen, bevor das Deployment als abgeschlossen gilt.

Die AWS-Site ist die Live-Demonstration. Die GitHub-Pages-Site bleibt eine
deterministische Fixture-Demo und enthält nie die öffentliche Live-Quotenkennung.

Der Deploy-Befehl ist ohne die geprüfte 5-USD-Warnschwelle und ein exaktes
Freigabetoken absichtlich nicht verwendbar. Er darf erst aufgerufen werden, nachdem
der Kontoinhaber ausdrücklich akzeptiert hat, dass AWS-Kosten entstehen können und
das Budget nur warnt, statt Ausgaben hart zu sperren:

```powershell
python deploy/aws_demo/manage.py deploy `
  --budget-alert-email "ACCOUNT-OWNER-EMAIL" `
  --budget-usd 5 `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

Nach dem Deployment erlaubt dasselbe Freigabe-Gate genau einen synthetischen Ablauf
mit zwei Anfragen und das anschließende Zurücklesen der Betriebsgrenzen:

```powershell
python deploy/aws_demo/manage.py verify `
  --budget-usd 5 `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```
