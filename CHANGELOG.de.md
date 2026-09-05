# Changelog

[English](./CHANGELOG.md) | **Deutsch**

**Aktuelle Kurzfassung:** 0.52 / 2026-08-27  
**Direkter Vorläufer:**
[`docs/archive/CHANGELOG-through-phase35.md`](docs/archive/CHANGELOG-through-phase35.de.md)

Alle relevanten Änderungen werden in dieser Datei dokumentiert. Der
ausführliche phasenweise Verlauf bis Phase 35 bleibt unverändert im Archiv.

## [Unreleased]

### Hinzugefügt

- lokaler Modell-Provider `ollama`: Der Master-Agent kann statt auf dem
  deterministischen Fixture oder Amazon Bedrock auf einem Modell im eigenen
  Zuhause laufen. Das Gate richtet sich nach dem Transportweg, nicht nach dem
  Anbieter: Ein Loopback-Host braucht keine Freigabe, weil nichts den Rechner
  verlässt, jeder andere Host dagegen dieselben zwei Freigaben wie Bedrock,
  `--allow-network` und `--approve-sensitive-cloud-data`
- neue CLI-Optionen `--model-provider ollama`, `--ollama-host` (Standard
  `http://127.0.0.1:11434`) und `--ollama-model-id`; die Modell-ID ist immer
  ausdrücklich und wird nie geraten
- neue Einstellungseigenschaften `network_used` und `is_live_model` trennen die
  Transportfrage von der Anbieterfrage; Agentenbericht, Live-Runden-Zähler und
  Statusausgabe fragen jetzt sie, statt einen Anbieternamen mit `"bedrock"` zu
  vergleichen
- Status und GUI benennen ein lokales Modell als lokales Modell:
  `model_inference_location` meldet `local_ollama_host` oder
  `remote_ollama_host` statt `aws_cloud`, und die Oberfläche kündigt ein
  laufendes Ollama-Modell nicht länger als konfiguriertes Amazon Bedrock an
- optionales Extra `folderhome[ollama]`; der Provider wird nur geladen, wenn er
  ausgewählt ist, und ein fehlendes Paket scheitert fail-closed mit dem
  Installationsbefehl
- MCP-Server `folderhome mcp serve`: Claude Code und die Codex-CLI können die
  begrenzte FolderHome-Oberfläche über stdio als Werkzeug nutzen. Der Server
  hält keinen eigenen Zustand, sondern spiegelt die Loopback-API eines
  laufenden `app serve`; Editor-Agent und GUI teilen sich damit einen Prozess,
  eine Unterhaltung und dieselben vorgeschlagenen Pläne
- zehn MCP-Werkzeuge mit dem Präfix `folderhome_` für Status, Profile,
  Fähigkeiten, Executoren, Ressourcen, Dokumentsuche, Themendossier, Chat,
  Planfreigabe und Gesprächsreset; eine Ablehnung der lokalen API erreicht den
  Editor wortgleich
- `folderhome mcp plan` gibt den fertigen `claude mcp add`-Befehl und den
  passenden Block `[mcp_servers.folderhome]` für `~/.codex/config.toml` aus,
  ohne irgendetwas zu starten
- der MCP-Proxy scheitert fail-closed vor dem Start: Nur `127.0.0.1` wird
  akzeptiert, ein Sitzungstoken ist Pflicht, und `--approve-mcp-server` muss
  gesetzt sein. stdout gehört dem Transport, deshalb gehen Diagnosen und Fehler
  ausschließlich nach stderr
- reiner Entwurfsendpunkt für Mail: ein vorbereitetes Schreiben wird hinter der
  getrennten Live-Effekt-Freigabe `--approve-mail-draft` an den Entwurfsordner
  des eigenen IMAP-Postfachs des Nutzers angehängt; es gibt keinen Versandweg,
  kein Empfänger wird kontaktiert, und das Postfachpasswort wird erst zur
  Ausführung aus seinem konfigurierten lokalen Fundort gelesen
- Postfach-Ordnernamen werden so konfiguriert, wie das Mailprogramm sie zeigt:
  `Entwürfe` wird angenommen und in den RFC-3501-Leitungsnamen `Entw&APw-rfe`
  kodiert, damit die Ablage in einem Nicht-ASCII-Entwurfsordner überhaupt
  funktioniert
- der Entwurfsordner wird vor der Ablage gegen die Ordnerliste des Postfachs
  geprüft; ein fehlender Ordner bricht ab und nennt die vorhandenen
- zwei Passwortquellen: Schlüsselbund des Betriebssystems (`keyring_service`
  und `keyring_user`) oder lokale Datei (`password_file`); der Wert erreicht nie
  ein Log, einen Plan, einen Bericht oder eine Fehlermeldung
- Registerzweck `mail.draft_account` samt striktem Konfigurationsschema
  `folderhome.mail-draft-account.v1`; ohne eine solche Ressource bleibt der
  Mailendpunkt ehrlich `not_connected`
- lokales SQLite-Entwurfsledger, das vor der Ablage einen deterministischen
  Idempotenzschlüssel reserviert, damit derselbe Entwurf nicht zweimal im
  selben Postfach landet
- Fähigkeitsrezepte: eine deklarative Geschichte über vorhandene Endpunkte wird
  zu einem hashgebundenen Mehrschrittplan mit einer einzigen `/confirm`, während
  jeder Schritt seinen eigenen Adapter, sein Anfrageschema und seine Gates behält
- deterministische Rezeptabnahme, gezeichnet von jeder beteiligten Fachrolle
  (eine bei einer Domäne, alle bei domänenübergreifenden Rezepten); die Abnahme
  ist Teil des Planhashes, wer den Plan bestätigt, bestätigt die Abnahme mit
- deklarierte Übergabekanten, die zwei Schritte an dieselbe logische
  Ressourcen-ID binden; kein Wert aus einem Schrittbericht wird in eine spätere
  Anfrage eingesetzt
- sequenzielle Kettenausführung, die beim ersten Fehler anhält und berichtet,
  welche Schritte liefen, welcher brach und welche nie versucht wurden
- mitgeliefertes Rezept `accident-aftercare` (Kontakt, Schadensschreiben,
  Mailentwurf, Kalendertermin mit ICS-Export) samt
  `folderhome recipes list|plan|run`
- ein generierter Fähigkeitsindex (`folderhome.application.capability_index`),
  der Endpunktkatalog, Adapter-Anfrageschemata und einen kurzen Zweck genau
  einmal zusammenführt und daraus sowohl den kompakten Prompt-Auszug des
  Master-Agenten als auch `CAPABILITY-INDEX.md` / `.de.md` speist
- `_tools/capability-index` mit `--check`, damit der dokumentierte Index nicht
  vom Code abweichen kann
- optionaler ICS-Export am lokalen Kalenderendpunkt: die festgehaltenen Termine
  werden als eine private RFC-5545-Datei in ein registergebundenes
  Ausgabeverzeichnis geschrieben (Zweck `calendar.export_output`), durch
  dieselbe Bestätigung hashgebunden, ohne Überschreiben und mit Rücknahme, falls
  der Kalenderstatus nicht geschrieben werden kann; kein Kalender-Connector ist
  beteiligt
- mit einem Befehl startbare, token-geschützte synthetische Hyundai-i10-
  Unfalldemo über den echten Strands-Suchpfad und vier vorhandene typisierte
  Workflowadapter
- standardmäßig englische, zweisprachige Unfalldemo-Oberfläche mit dauerhaftem
  Hell-/Dunkelmodus, exakter Planbestätigung, deterministischem Reset und lokal
  abrufbaren Ergebnissen
- eigenständiger zweisprachiger GitHub-Pages-Showcase unter `site/`, der
  ausdrücklich als skriptbasierter synthetischer Browser-Rundgang ohne
  Backend-Ausführung gekennzeichnet ist
- optionaler Amazon-Bedrock-AgentCore-HTTP-Adapter mit `/ping`,
  `/invocations`, Runtime-Sitzungstrennung, begrenzter JSON-Eingabe und
  pfadfreier synthetischer Ausgabe
- mehrstufiger ARM64-AgentCore-Containerkandidat ohne Rootrechte
- englisch voreingestellte Dashboard-Lokalisierung mit dauerhaft gespeichertem
  Englisch-/Deutsch-Umschalter
- dauerhaft gespeicherter heller und dunkler Dashboard-Modus mit
  tastaturbedienbaren Steuerelementen
- zweisprachige Modellstatus-Karte in der GUI, die deterministisches Fixture,
  konfiguriertes aber unverifiziertes Bedrock und eine durch einen erfolgreichen
  Modellturn im Prozess verifizierte Bedrock-Verbindung unterscheidet
- maschinenlesbare Laufzeittopologie für rein lokalen beziehungsweise
  Local-first-Hybridbetrieb; FolderHome-Zustand und Workflows bleiben lokal,
  während die optionale Bedrock-Inferenz die AWS-Cloud nutzt
- ein GUI-zentrierter FolderHome-Master-Agent, den Browser und CLI gemeinsam
  über den Einzeldurchlauf `agent chat` und die prozessgebundene interaktive
  Sitzung `agent session` verwenden
- begrenzte prozesslokale Strands-Gesprächskontinuität je organisatorischem
  Profil mit GUI-/CLI-Reset, der auch unbestätigte Pläne und ihre noch nicht
  ausgeführten typisierten Hüllen verwirft
- semantische Fachrollenwahl, explizite fail-closed Workflow-Auflösung und reine
  Stilpersonas
- bei Bedarf erzeugte Fachagenten mit genau einem Planungsendpunkt
- getrennte hashgebundene GUI-/API-Planbestätigung ohne falsche
  Ausführungsbehauptung
- typisierter, fail-closed Executor-Katalog für alle 33 Master-Workflows mit
  sichtbaren Zuständen für verbunden, direkt nur lesend, nur planend und nicht
  verbunden
- erster vollständiger Chat-Ausführungsadapter für den vorhandenen append-only
  llm-note-Workflow für persönliche Notizen, mit Replay-Schutz und Fachbericht
- zweiter vollständiger GUI-/CLI-Chat-Adapter zur Bestätigung einer bereits
  geplanten Medikamenteneinnahme; er verwendet den revisionsgebundenen
  Medikamentenworkflow wieder, legt keine State-Pfade offen, gibt keine
  medizinischen Ratschläge und verändert keine Medikation
- geschlossene maschinenlesbare Anfrageschemas im Executor-Katalog und im
  begrenzten Fachagenten-Prompt für jeden verbundenen Adapter
- privates, schemageprüftes Register logischer Ressourcen mit Profilumfang,
  Zweckbindung, Least-Privilege-Operationen und modell-sicherem pfadfreiem
  Katalog
- 23 typisierte Ressourcen-ID-Adapter vervollständigen den lokalen Dokument-
  und Assistenzstack: Dokumentaktionen, Aufräumen, Beobachtung, Pakete,
  Routinen, FCSA, Kontakte, Korrespondenz, lokaler Kalender, Verträge, Design,
  Gesundheit, Finanzen, Sozialrecht, Bestand, Steuer und Daily Briefing
- fail-closed Runtime-Klassifikation der drei verbleibenden Lücken: Mail,
  externe Kalender und Scheduler-Registrierung benötigen konfigurierte externe
  Connectoren mit getrennten Live-Effekt-Freigaben
- typisierte, freigabegebundene Ausführung der vorhandenen strikt lokalen
  FindCall-Fixture-Kaskade mit maskierten Rufnummern und ohne Netzwerk,
  Telefonanruf, Buchung oder Verpflichtung
- echter, endlich begrenzter Strands-Agent mit profilspezifischer
  Dokumentensuche und Themendossier
- deterministischer No-network-Modelladapter über das öffentliche Strands-
  `Model`-Interface
- optionaler Amazon-Bedrock-Pfad mit getrennten Netzwerk- und
  Datenweitergabegates
- ausdrückliche Bedrock-Verbindungs-/Lese-Timeouts und insgesamt ein
  SDK-Versuch pro Modellaufruf
- der AgentCore-HTTP-Adapter nutzt jetzt dasselbe fail-closed Bedrock-Opt-in-
  Gate wie die Unfalldemo (`FOLDERHOME_AGENTCORE_MODEL_PROVIDER`,
  `FOLDERHOME_AGENTCORE_ALLOW_BEDROCK`,
  `FOLDERHOME_AGENTCORE_ALLOW_SYNTHETIC_CLOUD_DATA`), verwendet standardmäßig
  das lokale Fixture-Modell und meldet in jeder Antwort den aktiven
  Modellanbieter sowie das echte `network_used`-Flag statt eines fest
  verdrahteten `false`
- reproduzierbare synthetische Wettbewerbsdemo mit vier gehashten Artefakten
- `agent plan`, `agent run`, `agent chat`, `agent session` und `demo run` in der CLI
- wiederverwendbarer Ressourcenbudget-Vertrag für Dateizahl, Bytes und Laufzeit
- publishergebundene HTTPS-Vertrauensprüfung für amtliche Leistungs-Handoffs
- Verbindungsgrenzen, Sockettimeout und Überlastabweisung im Loopbackserver
- `SECURITY.md`, englisches Submission-Paket und 36-Phasen-Completion-Audit
- neue Skills `folderhome-strands-agent` und `folderhome-master-agent` mit ihren
  zugehörigen Workflows
- Windows-Runtimeabhängigkeit `tzdata==2026.3`

### Geändert

- Runtime bindet `strands-agents==1.53.0` exakt ein
- Dev-Abhängigkeit verlangt mindestens `pytest 9.0.3`
- Ingest, Snapshot, Transformation, Paket, Kontakte, Kalender, Finanzen,
  Cleanup, Gesundheit, Inventar und Medikation verwenden gemeinsame Budgets
- README, Architektur, Featureanalyse, Herkunfts- und Lizenzregister auf
  Phase 36 aktualisiert
- überlange Projektdokumente archiviert und durch kurze aktuelle Fassungen mit
  direktem Vorläuferverweis ersetzt
- Workflowrouter auf 33 Playbooks aktualisiert
- Englisch ist jetzt für 122 Dokumentationsseiten die Standardsprache; die
  erhaltenen deutschen Fassungen tragen das Suffix `.de.md` und verlinken
  wechselseitig auf die jeweilige Sprachfassung
- die Workflowrouter-Erzeugung synchronisiert nun 33 englische und 33 deutsche
  Playbooks, ohne lokalisierte Spiegel doppelt zu zählen
- lokale Agentenanweisungen, Aufgabenlisten, Statusdateien und Ausführungspläne
  bleiben lokal erhalten, werden aber aus Git ausgeschlossen
- Einreichungsunterlagen mit dem authentifizierten Devpost-Stand vom
  23. August 2026 abgeglichen, einschließlich aktueller Titelregel für
  Bonusartikel, Credit-Frist und der durchgehenden Hyundai-i10-Unfallgeschichte
- 26.08.2026: Post-Submission-Stand in README, Einreichungspaket und lokalen
  Operator-Dateien konsolidiert; veraltete Draft-, Pages-, Upload- und
  Submit-Gates durch den authentifizierten Abschlussstand ersetzt
- AgentCore-Dokumentation unterscheidet jetzt die bereitgestellte, als `READY`
  rückgelesene Direct-Code-Runtime samt Fixture-Roundtrip von der weiterhin
  unverifizierten Bedrock-Geschichte und dem deaktivierten Browserpfad

### Behoben

- 2026-08-24: Die Komponenten-Manifest-Pins von HungryCall, law-checker und
  Ringedingeding waren gegenüber ihren aktuellen öffentlichen Repository-
  HEADs veraltet und verursachten fail-closed Revisionsabweichungen in vier
  automatisierten Tests; alle drei Pins wurden auf die geprüften aktuellen
  öffentlichen HEADs nachgezogen
  (`82c28e2de95b1b0d0343a40adfd8585938c305f8`,
  `a5b0cd51bc3666962f2fae8017c855dea0a712a2`,
  `d80dd81a6d7bf64298d4ef290c3b54ab5f50e990`); die betroffenen Tests
  bestehen wieder
- 2026-08-24: Der lokale doc-services-Checkout wanderte im selben Zeitraum
  auf `e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2`; der doc-services-Pin in
  Manifest, Drittanbieter-Tabellen, Phasendokumenten und dem
  Manifest-Vertragstest wurde entsprechend nachgezogen
- 2026-08-24: Dem öffentlichen `gh-pages`-Showcase fehlten `assets/`
  (Logo, Icon, Favicon) und `runtime-config.js`, beide im aktuellen
  `site/index.html` referenziert; dadurch lud das Logo im Header nicht.
  `gh-pages` liefert jetzt den vollständigen aktuellen `site/`-Ordner

### Sicherheit

- der öffentliche Showcase hat kein Backend und keine Netzwerkanfragen; die
  ausführbare Unfalldemo bleibt hinter einem zufälligen Sitzungstoken auf
  Loopback begrenzt
- der AgentCore-Adapter akzeptiert weder Haushaltsuploads noch beliebige Pfade,
  Secrets oder externe Effekte und trennt Sitzungsarbeitsbereiche durch
  Einweg-Fingerabdrücke
- GitHub-Pages-Actions und das Python-Basisimage des AgentCore-Containers sind
  auf unveränderliche Revisionen gepinnt; die SHA-gepinnten CI-Abhängigkeiten
  stehen im Drittanbieterregister
- Security-Scan über 357 Dateien und 12/12 Oberflächen abgeschlossen
- drei Befunde behoben: unbeschränkte Dokumentarbeit, beliebige amtliche Hosts
  und unbeschränkte Loopback-Threads
- zusätzliche adversariale URL-Fälle für Trailing dot, percent-encoding und
  expliziten Port ergänzt
- potenziell sensible lokale Suchtreffer dürfen Bedrock erst nach einer vom
  technischen Netzwerkgate getrennten Datenweitergabefreigabe erreichen
- der nachgelagerte 66-Dateien-Delta-Audit bestätigte diese Freigabelücke als
  vierten, inzwischen behobenen Befund
- `pip-audit` nach Update der lokalen Prüfwerkzeuge ohne bekannte
  Schwachstellen

### Verifiziert

- AWS-Live-Readback vom 26.08.2026: beide CloudFormation-Stacks
  `CREATE_COMPLETE`; AgentCore-Runtime `READY`, Version 4, HTTP; öffentlicher
  Quota-API-Key aktiviert; CloudFront-`runtime-config.js` weiterhin
  `enabled: false`
- EU Nova Micro blieb `ACTIVE`, seine angewandten On-Demand-Quoten standen
  jedoch auf null. Genau ein Converse-Aufruf mit 16 Ausgabetokens und ohne
  Retry endete mit `ThrottlingException: Too many tokens per day`; kein zweiter
  Modellaufruf und kein `manage.py verify`
- Erneuter AWS-Readback vom 27.08.2026 nach erfolgreicher OAuth-Erneuerung:
  AgentCore weiterhin `READY`, Version 4, EU Nova Micro weiterhin `ACTIVE` und
  alle drei Echtzeitquoten weiterhin null. CloudWatch zeigte in 24 Stunden eine
  Drosselung und keine erfolgreiche Invocation; deshalb erfolgte kein weiterer
  Modellaufruf
- AWS-Budget-Readback: 5 USD Monatslimit und 0,018 USD berechneter bisheriger
  Verbrauch; der kumulierende P-010-Deckel mit Restübertrag ist noch nicht
  implementiert
- Aktuelle vollständige Feature-Suite auf dem konsolidierten Arbeitsstand zu
  HEAD `436928f`: 503 bestanden, 0 fehlgeschlagen in 370,04 Sekunden; auch die
  abschließende Manifestprüfung bestand 10/10
- synthetische Unfalldemo, lokale HTTP-Seite, CLI-Startgate und
  AgentCore-Vertrag durch fokussierte automatisierte Tests abgedeckt
- AgentCore-`/ping` und ein Prepare-Aufruf als echter Loopback-HTTP-Prozess
  bestanden; keine AWS-Ressource wurde erstellt
- öffentlichen Showcase in Edge bei 1440 × 1100 geprüft; HTML-/CSS-/JavaScript-
  und begrenzte Pages-Artefakttests bestanden
- 414 automatisierte Tests bestanden; drei externe Live-Checkout-Pinprüfungen
  wurden bewusst abgewählt, weil die aktuellen lokalen HungryCall- und
  Ringedingeding-Revisionen von ihren Manifest-Pins abweichen
- der abschließende ungefilterte Lauf meldete `414 bestanden, 3
  fehlgeschlagen`; der abschließende begrenzte Produktlauf meldete `414
  bestanden, 3 abgewählt`
- Englisch/Hell und Deutsch/Dunkel bei 1440 × 1100 visuell geprüft;
  fokussierte GUI-Tests und JavaScript-Syntaxprüfung bestanden
- Ruff und Compileall ohne Befund
- 8/8 Pluginmanifeste gültig; der Master-Agent-Skill ist durch die aktuellen
  Repository-Skillprüfungen abgedeckt
- 33 Workflows synchron
- das konfigurierte EU-Nova-Micro-Inferenzprofil war aktiv; der einzige
  begrenzte synthetische FolderHome-Turn lieferte innerhalb von 60 Sekunden
  weder Antwort noch Fehler, wurde ohne Retry beendet und gilt nicht als
  verifiziert
- synthetischer Strands-Lauf: zwei Szenarien, kein Netzwerk, keine
  Side-Effects; Wiederholung blockiert am Never-overwrite-Gate
- Wheel enthält Agent, Demo, Ressourcenbudget, Hostprüfung und GUI
- eine frische virtuelle Umgebung installierte das gebaute Wheel und führte
  die Unfallgeschichte mit vier Ergebnissen sowie AgentCore-`/ping` ohne
  Netzwerknutzung aus
- finaler Wheel-SHA-256:
  `8b5929c855226a4c2c78223b65e85adc12dcd4b5aa61445d010e7fdf8d0eb24a`

## Historische Meilensteine

| Phasen | Ergebnis |
|---|---|
| 1–8 | Integrationskern, FCSA, Dokumentenbibliothek, Versionen, Profile, Aktionen, Transformation und Typpakete |
| 9–15 | Ordnerbeobachtung, Korrekturlernen, Scans, Ausführung/Undo, Routinen, Queue und Scheduler-Handoff |
| 16–21 | Kontakte, Kalender, FindCall, Finanzen, Haushalt und Medikation |
| 22–30 | Gesundheit, Verträge, Korrespondenz, Office/Design, Mail, Kalenderconnectoren, Notizen, Steuern und Daily Brief |
| 31–35 | Bescheide, Verwaltungsentwürfe, Leistungsvorcheck, Rechtsänderungen und lokale GUI/API |
| 36 | Härtung, Strands-Agent, Wettbewerbsdemo und einreichungsfertiges lokales Paket |

Die einzelnen Änderungen und damaligen Teststände stehen im direkten
Vorläufer; der aktuelle Requirement-Nachweis steht in
[`docs/phase36-completion-audit.md`](docs/phase36-completion-audit.de.md).

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
