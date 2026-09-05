# Changelog

[English](./CHANGELOG.md) | **Deutsch**

**Aktuelle Kurzfassung:** 0.52 / 2026-08-27  
**Direkter Vorläufer:**
[`docs/archive/CHANGELOG-through-phase35.md`](docs/archive/CHANGELOG-through-phase35.de.md)

Alle relevanten Änderungen werden in dieser Datei dokumentiert. Der
ausführliche phasenweise Verlauf bis Phase 35 bleibt unverändert im Archiv.

- Ergebnisansicht: Was ein freigegebener Plan wirklich ausgeführt hat, bleibt in
  der lokalen GUI abrufbar — auch Läufe, die über die HTTP-API oder einen Editor
  per MCP gestartet wurden, weil alle drei denselben Prozess bedienen. Neues
  Panel mit Aktualisieren-Knopf, nach eigener Freigabe automatisch nachgeladen
- neue read-only-Routen `GET /api/v1/agent/results` und
  `GET /api/v1/agent/results/<execution_id>/artifacts/<index>`; die Liste trägt
  Dateiname, Größe und Index, aber nie einen Pfad, und die Datei wird
  ausschließlich über diesen Index als Anhang ausgeliefert
- ausgeführte Berichte liegen in einem begrenzten prozesslokalen Ringpuffer;
  Artefakte werden einmal zur Ausführungszeit aufgelöst und nur innerhalb einer
  registrierten Ausgaberessource dieses Profils, unter dem Namen, den der
  Bericht selbst nennt
- MCP-Werkzeug `folderhome_results` spiegelt dieselbe Liste für Editor-Agenten
- die GUI lädt über die tokengeschützte API und baut die Datei aus einem Blob;
  so steht nie ein Token in einer URL oder im Browserverlauf
## [Unreleased]

### Hinzugefügt

- Profile werden im Einrichtungsprogramm verwaltet: Abschnitt 1 listet sie,
  legt eines an, benennt es um, bearbeitet seine Regeln und löscht es nach einer
  Rückfrage. Bisher lautete die Antwort auf „Kann ich ein Beispielprofil löschen
  und ein eigenes anlegen?" nein, der Browser konnte sie nur lesen
- die Einrichtung besitzt einen eigenen Profilordner, standardmäßig
  `<Konfigurationsordner>\profiles` statt des `examples\profiles` dieses
  Repositorys, und startet auch dann, wenn dieser Ordner noch leer ist. Ein
  erster Lauf bietet an, die mitgelieferten Beispiele zu übernehmen oder mit
  einer leeren Liste zu beginnen; die Beispiele selbst bleiben eine Vorlage und
  werden als Schreibziel abgelehnt
- das Löschen eines Profils kaskadiert im selben Plan: Ordnerbindungen, die
  danach zu niemandem mehr gehören, entfallen, seine Kalenderkonten verlassen
  `calendar-accounts.json`, und die Vorschau nennt alles, was mitgeht.
  Mindestens ein Profil muss bestehen bleiben, und die Datei selbst wandert in
  einen datierten `.deleted-<Zeitstempel>`-Ordner, statt entfernt zu werden
- Haushalts- und Profildokumente gehen denselben Weg aus Plan und Bestätigung:
  Der Plan-Hash deckt sie ab, jedes wird temporär geschrieben, über
  `parse_profile_configuration` zurückgelesen und erst dann an seinen Platz
  gelegt; der Dateiname eines Profils folgt der geprüften ID, nie einer
  Texteingabe
- `--profiles-dir` ist für `setup plan` und `setup serve` optional

- Abschnitt „Abonnements" im Einrichtungsprogramm, zwischen Modell und
  API-Schlüsseln: Claude Code mit Claude-Abo und die Codex-CLI mit ChatGPT-Abo
  steuern FolderHome als Werkzeug, der Agent ist also das Gehirn und FolderHome
  braucht keinen eigenen Schlüssel. Beide Editor-Einträge stehen fertig zum
  Kopieren bereit und stammen aus demselben `integration_plan`, den `mcp plan`
  ausgibt, statt ein zweites Mal geschrieben zu werden. Der Abschnitt ist reine
  Anleitung: Er startet keinen Server, schreibt keine Datei und berührt keinen
  Plan-Hash
- `llms.txt` im Wurzelverzeichnis des Repositorys und veröffentlicht unter
  `site/`, in der Form von llmstxt.org: Anbindung über MCP, Aufruf der
  Loopback-HTTP-API, was das Sicherheitsmodell ablehnt, welche Provider es gibt
  und wo die ausführlichen Dokumente liegen
- ein Test liest jede Route, jeden Schema- und Werkzeugnamen aus `llms.txt` und
  belegt, dass es sie im Dienst gibt, dass die veröffentlichte Kopie byte-gleich
  ist und dass kein Schlüssel, Token oder echter Pfad darin steht

- ein endliches HTTP-Budget für jeden Provider, der über HTTP spricht:
  `model_timeout_seconds` (Vorgabe 120, CLI `--model-timeout-seconds`) erreicht
  den Ollama-, Anthropic- und OpenAI-Client gleichermaßen, und eine
  Zeitüberschreitung wird als benannter Fehler gemeldet statt als Hänger.
  Bedrock behält sein eigenes Paar aus Verbindungs- und Lesezeit
- das Einrichtungsprogramm lehnt einen Plan, den der Loader ablehnen würde,
  schon beim Prüfen ab und nicht erst beim Speichern: Lesen und Prüfen sind in
  allen drei Loadern getrennt, sodass die echten Verträge über die noch im
  Speicher liegenden Dokumente laufen und der Fehler an seinem Feld erscheint
- `configured` bedeutet jetzt, dass das Register lädt, nicht dass eine Datei
  existiert
- Fehler im Einrichtungsprogramm behoben: `calendar.export_output` endet auf
  `_output`, nicht auf `.output`, weshalb die Suffix-Raterei ihm keine
  Operationen gab. Das geschriebene Register war nicht mehr ladbar, das Speichern
  antwortete mit 400, und beide Dateien lagen bereits auf der Platte, bei einer
  Ersteinrichtung ohne Sicherung. Eine ausdrückliche Tabelle Zweck zu Operationen
  ersetzt das Raten; der Exportordner bekommt `create` und `cloud_context: deny`
- die Einrichtung legt jede zu schreibende Datei zuerst temporär an, lädt sie
  über ihren eigenen Vertrag zurück und ersetzt die echten Dateien erst danach;
  ein Plan, der sich als nicht ladbar erweist, lässt den Vorzustand unverändert
- Bedienbarkeit: Der Knopf heißt Speichern, und eine Zeile darunter sagt, dass
  nichts automatisch gespeichert wird. Jedes Ordnerfeld kann das Betriebssystem
  nach einem Verzeichnis fragen (`POST /api/v1/setup/pick-folder`, immer nur ein
  Dialog, 501 ohne Dialog-Toolkit, damit die Eingabe von Hand der Rückfallweg
  bleibt)
- ein Quellzweck nimmt mehrere Ordner auf; der erste wird der Standard des
  Profils, und der Agent sieht alle in seinem Katalog. Beim erneuten Öffnen zeigt
  die Einrichtung jede eingerichtete Quelle statt nur des Standards
- die Einrichtung schreibt `calendar.json` und `calendar-accounts.json`, wenn der
  Abschnitt eingeschaltet ist, über denselben Weg aus Bestätigen, Prüfen und
  Ersetzen. Ein Outlook-Backend gibt es in dieser Fassung nicht, deshalb wird
  keines angeboten, und `app serve` liest keine der beiden Dateien: das tun nur
  die `calendar`-Befehle
- fremdgehostete Modell-Provider `anthropic` und `openai`, mit denselben zwei
  Freigaben wie Bedrock und `--openai-base-url` für einen kompatiblen Endpunkt.
  Ein API-Schlüssel ist keine Einstellung: Er wird beim Bau des Modells aus
  `ANTHROPIC_API_KEY` oder `OPENAI_API_KEY` gelesen und taucht in keinem Plan,
  Status, Bericht und Log auf
- die Einrichtung legt diese Schlüssel in einer `.env` neben `launch.json` ab,
  nur für den Eigentümer lesbar, erhält jede andere Zeile dieser Datei und
  hinterlässt keine Sicherung eines Schlüssels; der Zustand sagt nur, ob ein
  Schlüssel hinterlegt ist. `app serve --launch-config` füllt diese zwei Namen in
  die Umgebung, wenn sie dort noch nicht stehen
- Modell-Presets in `launch.json` (`model_presets`, `model_preset`): mehrere
  Modellwahlen speichern, eine aktivieren, eine löschen. Der Vorrang beim Start
  ist ausdrücklich und getestet: Schalter vor flachem Feld vor aktivem Preset
- ein statischer Test prüft, dass die Einrichtungsseite nur vorhandene IDs und
  Textschlüssel anspricht und beide Sprachen dieselben Schlüssel führen; er fand
  die Cloud-Karte, die mangels Übersetzung ihre eigenen Schlüsselnamen anzeigte
- getrenntes Einrichtungsprogramm `folderhome setup serve`: Eine zweite
  Loopback-Anwendung mit eigenem Port und eigenem Token ist der einzige Ort, der
  FolderHome-Konfiguration schreibt. Die App-GUI behält keinen Schreibweg dorthin
- die Einrichtung plant zuerst und schreibt nur gegen den Hash genau des Plans,
  den sie angezeigt hat, und nur mit ausdrücklicher Bestätigung; Ordner werden
  vorher auf Existenz, Symlinks und Lage im eigenen Benutzerordner geprüft
- sie schreibt `resources.json` und `launch.json` atomar über eine temporäre
  Datei, behält die Vorversion als `.bak-<Zeitstempel>` und lädt das
  geschriebene Register über den bestehenden Vertrag zurück, bevor sie Erfolg
  meldet
- Provider-Felder werden geprüft, indem die echten `StrandsAgentSettings`
  konstruiert werden, statt ein zweites Regelwerk zu pflegen; kein Passwort und
  keine Postfach-Zugangsdaten werden je geschrieben
- `app serve --launch-config <datei>` übernimmt diese Startwerte als Vorgaben.
  Ein ausdrücklicher Schalter gewinnt immer, und die Gates stehen nicht auf der
  Allowlist: Keine Datei kann Netzzugang, eine Datenweitergabefreigabe oder
  einen Listener erteilen
- die Cloud-Variante liefert Ergebnisdateien inline: Die Antwort der
  AgentCore-Runtime trägt jetzt je Ergebnis `content`, `content_type` und
  `content_encoding`, sodass der Browser einen Download anbieten kann, obwohl
  diese Runtime nur `/ping` und `/invocations` kennt und keine Dateiroute. Kein
  API Gateway und kein S3 kamen hinzu
- zwei ehrliche Grenzen: Eine Datei über 262 144 Byte reist nur als Metadaten
  (`inline: false`, Grund `size_limit`), und eine Datei, deren Text den
  Arbeitsverzeichnispfad enthält, wird genauso zurückgehalten (Grund
  `local_paths`), statt lokale Pfade an einen Browser zu schicken
- der öffentliche Walkthrough baut den Download aus diesem Inline-Inhalt und
  fällt auf die lokale Dateiroute zurück, wenn ein Ergebnis keinen trägt
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
