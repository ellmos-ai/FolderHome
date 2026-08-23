# Changelog

[English](./CHANGELOG.md) | **Deutsch**

**Aktuelle Kurzfassung:** 0.47 / 2026-08-23  
**Direkter Vorläufer:**
[`docs/archive/CHANGELOG-through-phase35.md`](docs/archive/CHANGELOG-through-phase35.de.md)

Alle relevanten Änderungen werden in dieser Datei dokumentiert. Der
ausführliche phasenweise Verlauf bis Phase 35 bleibt unverändert im Archiv.

## [Unreleased]

### Hinzugefügt

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

### Sicherheit

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

- 394 automatisierte Tests bestanden; drei externe Live-Checkout-Pinprüfungen
  wurden bewusst abgewählt, weil die aktuellen lokalen HungryCall- und
  Ringedingeding-Revisionen von ihren Manifest-Pins abweichen
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
