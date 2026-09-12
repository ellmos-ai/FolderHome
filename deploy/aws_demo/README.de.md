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
- Eine atomare DynamoDB-Transaktion lässt eine Weiterleitung nur zu, solange das
  kumulierte Tagesguthaben ihren geprüften Höchstbetrag in ganzzahligen **Mikro-USD**
  deckt (Policy P-010). Eine feste Tagesanzahl an Weiterleitungen gibt es nicht mehr;
  der Tageszähler ist Telemetrie. Das endliche Guthaben wird über UTC-Kalendertage freigegeben;
  ungenutzte Mittel werden auch über Tage ohne Aufrufe übertragen. Das Enddatum
  ist exklusiv. Abgelaufene Zeitfenster, fehlende Ledger und geänderte Policy-Hashes sperren.
- Der API-Gateway-Nutzungsplan (1000 Anfragen pro UTC-Tag) und die Drosselung sind
  strukturelle Missbrauchsschutzschichten und nicht die Kostengrenze.
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

**Das Ledger reserviert Geld für Weiterleitungen; es sperrt nicht die gesamte Kontorechnung.**
Die Reserve muss sämtliche abrechenbaren Folgearbeiten der geprüften Runtime
abdecken, einschließlich Modellaufrufen, Ein-/Ausgabelimits und Runtime-Lebensdauer.
Ein Proxy-Timeout beweist keinen Abbruch dieser Arbeiten; Reservierungen werden
deshalb nie erstattet. Statisches Hosting, abgelehnte Anfragen, Logs, DynamoDB-Zugriffe
und sonstige Infrastrukturkosten benötigen eine gesondert geprüfte Reserve und
Überwachung. Grüne lokale Tests belegen weder aktuelle Credits oder Preise noch
eine Live-Abnahme des Deployments.

Der Proxy verwendet einen eigenen Endpunkt mit geprüfter Runtime-Version statt
`DEFAULT` und kontrolliert dessen aktuelle Version vor der Zulassung. Betreiber
dürfen diesen Endpunkt im Betrieb nicht umstellen: Prüfung und Aufruf sind keine
gemeinsame AWS-Transaktion. Administrative Änderungen und kompromittierte
IAM-Zugangsdaten liegen außerhalb dieser Schutzschicht der Anwendung.

## Build und Vorabprüfung

```powershell
python deploy/agentcore/build_direct_code.py
python deploy/aws_demo/build_proxy.py
python deploy/aws_demo/manage.py preflight
```

Die beiden Build-Befehle paketieren lokal; dabei können Abhängigkeiten heruntergeladen
werden. **`preflight` liest zusätzlich AWS-Identität, Templates sowie Runtime-/Modellstatus**;
es ist kein Offline-Test. Bei aufgeschobener AWS-Arbeit nicht ausführen.

Build-Ausgaben verbleiben im ignorierten Ordner `build/`. API-Keys,
AWS-Konto-IDs, E-Mail-Adressen, generierte Laufzeitkonfiguration und Stack-Ausgaben
dürfen nicht committet werden.

## Erforderliche Kostenprüfung

Vor dem Deployment eine private `build/budget-review.json` nach dem Schema
`folderhome.cloud-budget-review.v1` vorbereiten. Pflichtfelder:

- `approved`: ausdrücklich der boolesche Wert `true`, erst nach Prüfung durch den Kontoinhaber.
- `available_funds_microusd`: geprüftes, unverbrauchtes Teilbudget; es muss der
  freigegebenen Billing-Warnschwelle entsprechen. Das bestehende Deployment-Gate bleibt bei 5 USD.
- `other_costs_reserved_microusd`: für Kosten außerhalb der Weiterleitungen zurückbehaltene Mittel.
- `total_microusd`, `forward_microusd`: positives ganzzahliges Aufrufbudget und
  belegbare Höchstreserve je Weiterleitung. Einheit ist ein Millionstel USD;
  Geldbeträge werden nicht als Gleitkommazahlen verarbeitet.
- `start_utc`, `end_utc`: `YYYY-MM-DD`, Anfang inklusiv und Ende exklusiv,
  ein bis 366 Tage. Das Ende liegt **nach der Gewinnerverkündung**, nicht der Einreichung.
- `agentcore_zip_sha256`, `proxy_zip_sha256`: vollständige Hashes der exakt geprüften
  Dateien `build/agentcore-direct.zip` und `build/aws-demo-proxy.zip`.
- `runtime_profile_sha256`: Hash des kanonischen Modell-/Umgebungs-/Lebensdauerprofils
  aus dem Offline-Befehl `python deploy/aws_demo/manage.py cost-profile`.
  Genau dieses Profil wird deployt; ein geändertes Modell oder Limit entwertet die Prüfung.
- `basis`: Herleitung mit datierten Preisen, maximaler Modellarbeit und Runtime-
  Lebensdauer, Infrastrukturreserve, aktuellem Guthaben und Abschaltnachweisen.

Der Loader verwirft unbekannte/doppelte Felder, veraltete Artefakte, ungültige
Beträge und überbuchte Mittel. Er prüft das Dokument, **nicht die Wahrheit der
Kostenschätzung**. Es gibt keine aktivierungsfertigen Beispielbeträge. Der Hash
des Prüfdokuments gehört zur Ledger-Policy. Jede Änderung benötigt eine ausdrückliche
Prüfung und Migration unter Erhalt bereits verbrauchter Mittel; sie darf das Ledger nie nullsetzen.

Das feste Ledger `_budget_v1` hat keine TTL. CloudFormation erhält die Tabelle bei
Löschung/Ersetzung; der Proxy darf keine Ledger-Einträge anlegen oder löschen.
Ein neues Deployment legt den Anfangsstand bedingt an und liest ihn konsistent
zurück, bevor die Browserkonfiguration veröffentlicht wird. Der Fresh-Deploy-Befehl
verweigert bestehende Anwendungen einschließlich sichtbarer gelöschter Stack-Historie.
**Eine bestehende Demo benötigt eine gesondert geprüfte Migration; Tabellenlöschen ist keine Migration.**

Die zugrunde liegende Atomarität und Wiederholungssemantik stehen in der
[DynamoDB-Transaktions-API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html).

## Deployment-Reihenfolge

1. Den Bootstrap-Stack mit einer Benachrichtigungsadresse sowie den exakten ARNs des
   Nova-Micro-Inferenzprofils und der Foundation Models anlegen.
2. Das versionierte Direct-Code-ZIP und das Lambda-Proxy-ZIP in den privaten
   Artefakt-Bucket hochladen.
3. Die Direct-Code-AgentCore-Runtime mit der Ausführungsrolle des Bootstrap-Stacks
   anlegen.
4. Die Runtime unmittelbar so aktualisieren, dass IMDSv2 erforderlich ist, und auf
   `READY` warten.
5. Einen eigenen versionsgebundenen Endpunkt und den Anwendungs-Stack mit den
   geprüften Geld-/Zeitfensterparametern anlegen. Das dauerhafte Ledger initialisieren und zurücklesen.
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
  --budget-review build/budget-review.json `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

Nach dem Deployment erlaubt dasselbe Freigabe-Gate genau einen synthetischen Ablauf
mit zwei Anfragen und das anschließende Zurücklesen der Betriebsgrenzen:

```powershell
python deploy/aws_demo/manage.py verify `
  --budget-usd 5 `
  --budget-review build/budget-review.json `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

`verify` prüft vor kostenpflichtigen Proben die deployte Geld-Policy, das verbleibende
Guthaben, die Runtime-Version und die bewusst unreservierte Lambda-Konfiguration.
Es vergleicht außerdem den deployten Lambda-Codehash, das versionierte Runtime-Artefakt,
IMDSv2 und das vollständige Runtime-Kostenprofil mit dem freigegebenen Material.
Danach liest es die beiden Reservierungen zurück. Dies aktiviert oder migriert keine
bestehende statische Demo und bestätigt weder die gesamte Kontorechnung noch das Aufräumen.
Am geprüften Ende stoppt die Zulassung; Ressourcenabschaltung, Umgang mit der erhaltenen
Tabelle und Restguthabenprüfung bleiben Teil des gesondert freizugebenden AWS-Abschlusses.

## Bestehende Demo auf das geprüfte Budget migrieren

`deploy` verweigert eine bereits vorhandene Anwendung. Eine bestehende Demo, die
noch nie Geld reserviert hat (kein `_budget_v1`-Ledger-Eintrag), wird mit `migrate`
unter das Budget gestellt: aktuelle Artefakte hochladen, die vorhandene Runtime
aktualisieren (IMDSv2 erforderlich, neue Version), den versionsgebundenen
Endpunkt `budget_v<N>` anlegen, den Anwendungs-Stack mit den geprüften Geld-/
Fensterparametern aktualisieren und das Ledger konditional anlegen. Die statische
Seite bleibt unangetastet, sofern nicht `--publish-site` gesetzt ist; ohne den
Schalter bleibt der Browser-Agent deaktiviert.

```powershell
python deploy/aws_demo/manage.py migrate `
  --budget-usd 5 `
  --budget-review build/budget-review.json `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

Ein Ledger, das bereits reserviertes Geld trägt, wird abgewiesen; das Mitführen
verbrauchter Mittel braucht eine eigene geprüfte Migration.
