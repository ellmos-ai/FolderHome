<img src="assets/banner.png" width="100%" alt="FolderHome Banner">

# FolderHome

[English](./README.md) | **Deutsch**

> Assistantify your home.

**Current concise README:** Phase 36 / 2026-08-23  
**Direct predecessor:**
[`docs/archive/README-phase36-draft.md`](docs/archive/README-phase36-draft.de.md)

FolderHome is a local-first Strands agent that turns scattered household
documents into searchable, explainable and safely actionable workflows.

FolderHome ist ein lokaler Dokument- und Assistenzservice-Agent. Er verbindet
Dokumentensuche, reversible Dateiarbeit und gekapselte Alltagsdienste, ohne
einer Analyse automatisch Mail-, Kalender-, Telefon-, Datei- oder
Cloudberechtigungen zu geben.

## Status

- 36 von 36 lokalen Wettbewerbsphasen umgesetzt
- ein echter `strands.Agent`-Master mit vier begrenzten Werkzeugen und bei Bedarf erzeugten Planungs-Fachagenten
- vollständige Feature-Suite: 503 bestanden, 0 fehlgeschlagen; nach dem
  Provenienz-Repin vom 27.08.2026 erneut 503/503 bestanden, auch die
  Manifestprüfung bestand 10/10
- synthetische No-network-Demo mit reproduzierbaren Hashes
- durchgehende synthetische Unfallgeschichte über vier echte,
  bestätigungspflichtige FolderHome-Workflowadapter
- zweisprachiger öffentlicher Showcase mit Hell-/Dunkelmodus in
  [`site/`](./site/) und eine bereitgestellte, quotenbegrenzte
  AgentCore-HTTP-Runtime; ihr öffentlicher Browserpfad bleibt deaktiviert,
  solange Bedrocks angewandte On-Demand-Quoten null sind
- vollständiger Baseline-Scan über 12/12 Oberflächen plus aktueller
  66-Dateien-Delta-Audit; vier Befunde behoben
- öffentliches MIT-Repository, [dreiminütiges öffentliches Demovideo](https://youtu.be/wPb1wBJcLjQ)
  und eine eingereichte [Agents-for-Humans-Teilnahme](https://devpost.com/software/folderhome)

Der kanonische Nachweis steht im
[`Phase-36-Completion-Audit`](docs/phase36-completion-audit.de.md). Während des
Wettbewerbs heißt das Projekt ausschließlich **FolderHome**. Ein späteres
Light-/Sovereign-Rebranding ist nicht Teil dieses Builds.

## Schnelltest für Jurorinnen und Juroren

Windows PowerShell:

```powershell
git clone https://github.com/ellmos-ai/FolderHome.git
cd FolderHome
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,transform]"
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir .local-demo\competition `
  --approve-output-write --json
```

macOS/Linux verwenden `.venv/bin/python` statt
`.venv\Scripts\python.exe`.

Erwartet werden `status=passed`, `strands-agents 1.53.0`, die Szenarien
`document-search` und `theme-dossier`, `network_used=false`, eine leere
`side_effects`-Liste sowie vier neue Dateien. Ein zweiter Lauf gegen denselben
Ordner blockiert statt zu überschreiben.

Die ausführliche englische Anleitung steht in
[`docs/submission/TESTING_INSTRUCTIONS_EN.md`](./docs/submission/TESTING_INSTRUCTIONS_EN.md).

## Interaktive Unfallgeschichte

Die echte lokale Demo startet mit einem Befehl:

```powershell
.venv\Scripts\python.exe -m folderhome demo accident-serve `
  --workspace-dir .local-demo\accident `
  --port 8767 --approve-loopback-server --json
```

Öffne die ausgegebene, tokenhaltige `access_url`. Die standardmäßig englische
Oberfläche bietet eine Deutsch-/Englisch-Umschaltung und Hell-/Dunkelmodus. Sie
durchsucht synthetische aktuelle und ältere Hyundai-i10-Policen, schlägt
Kontakt-, Schadensbrief-, Vertrags- und lokale Kalenderschritte vor und führt
die echten typisierten Adapter erst nach dem exakt angezeigten Befehl
`/confirm <plan_id>` aus. Sie versendet niemals E-Mails, ruft kein Cloudmodell
auf und archiviert die ältere Police nicht automatisch. Ein getrennt
freizugebendes Rezept kann das vorbereitete Schreiben ohne Versandweg als
prüfbaren Entwurf im eigenen Postfach ablegen. **Fall zurücksetzen** stellt das
deterministische Fixture wieder her.

Der öffentliche Browser-Rundgang liegt in [`site/`](./site/). Er ist
ausdrücklich als skriptbasierter synthetischer Showcase ohne Backend
gekennzeichnet. Der Repository-Befehl oben ist der ausführbare Nachweis.

Das abgenommene Wettbewerbsvideo ist öffentlich auf YouTube:
<https://youtu.be/wPb1wBJcLjQ>.

## Agentenarchitektur

```mermaid
flowchart LR
  H[Human / local OS account] --> UI[CLI or local GUI]
  UI --> A[FolderHome Master / Strands Agent 1.53.0]
  PUB[Öffentlicher skriptbasierter Showcase] -. kein Backend .-> UI
  AC[Optionaler AgentCore-HTTP-Runtime] --> A
  A --> F[Deterministic fixture model]
  A -. network + data disclosure gates .-> B[Amazon Bedrock]
  A -. Loopback: kein Gate / anderer Host: dieselben zwei Gates .-> O[Lokales Ollama-Modell]
  A --> S[search_home_documents]
  A --> D[build_home_theme_dossier]
  A --> C[list_home_capabilities]
  A --> X[consult_home_specialist]
  X --> P[Begrenzter Fachagent / ein Planungswerkzeug]
  P --> E[Typisiertes Executor-Gateway]
  E --> N[Vorhandener llm-note-Workflow]
  E --> M[Vorhandener Medikamenteneinnahme-Workflow]
  S --> L[FolderHome LocalApplication]
  D --> L
  L --> K[KnowledgeDigest read-only index]
  MCP[Claude Code / Codex CLI] -- stdio --> PX[folderhome mcp serve]
  PX -- Loopback-API + Token --> L
  UI --> W[Other gated domain workflows]
  P --> W
```

Der Fixture-Adapter durchläuft den echten Strands-Agenten und dessen
sequentiellen Tool-Executor ohne Zugangsdaten. Bedrock verwendet denselben
Agenten, verlangt aber Modell-ID, AWS-Region, `--allow-network` und die
getrennte Freigabe `--approve-sensitive-cloud-data`; ein Bedrock-Live-Lauf
wurde nicht behauptet. Ein lokales Ollama-Modell ist der dritte Provider und
wurde live verifiziert: Das Modell wählte und führte `list_home_capabilities`
über dieselbe Agentenschleife aus.
Die semantische Fachwahl gehört zum Modell. Endpoint-Auflösung, Plan-Hashes und
Bestätigung bleiben deterministisch und blockieren im Zweifel; Personas ändern
nur den Stil und erteilen niemals Kompetenzen. Ohne privates Ressourcenregister
zeigt der Live-Executor-Katalog drei verbundene Executoren: persönliche Notizen,
die Bestätigung einer bereits geplanten Medikamenteneinnahme und die strikt
lokale FindCall-Fixture-Kaskade. Mit konfiguriertem Register kommen 23
typisierte Ressourcenadapter für den vollständigen lokalen Dokument-,
Organisations-, Gesundheits-, Finanz-, Sozialrechts-, Bestands-, Steuer-,
Briefing-, Design-, FCSA- und Routinenstack hinzu. Ein Register, das zusätzlich
ein Entwurfspostfach (`mail.draft_account`) deklariert, verbindet auch den
reinen Entwurfsendpunkt für Mail. Damit sind 27 Endpunkte verbunden; hinzu
kommen ein direkter Nur-Lese-Pfad, drei absichtlich nur planende
Systemendpunkte und lediglich zwei sichtbare, fail-closed externe
Connectorlücken: externe Kalender und Scheduler-Registrierung. Ohne
konfiguriertes Postfach bleibt der Mailendpunkt ehrlich unverbunden; der
Katalog meldet dann 26 verbundene Endpunkte und drei Lücken. Jeder
verbundene Adapter veröffentlicht ein geschlossenes Anfrageschema. Eine
Chatnachricht schreibt nie; die exakte Bestätigung liefert für einen
verbundenen Plan einen eigenen Fach-Ausführungsbericht. Externe Effekte behalten
ihre eigene Konfiguration und getrennten Live-Effekt-Freigaben.

Ein Fähigkeitsrezept macht aus einer ganzen Geschichte einen Plan.
`recipes list` zeigt die mitgelieferten, `recipes plan` löst eines in einen
hashgebundenen Mehrschrittplan auf, und `recipes run` führt die bestätigte Kette
der Reihe nach aus. Das mitgelieferte Rezept `accident-aftercare` liest den
zuständigen Kontakt, erzeugt das Schadensschreiben, legt genau dieses Schreiben
als Entwurf im eigenen Postfach ab und hält den Folgetermin samt ICS-Export fest
— vier Endpunkte, eine Bestätigung. Ein Rezept verleiht keine neue Fähigkeit:
Jeder Schritt behält seinen Adapter und seine Gates, und ein nicht verbundener
Endpunkt lässt das Rezept fail-closed scheitern, statt still übersprungen zu
werden. Details:
[`docs/capability-recipes.md`](./docs/capability-recipes.de.md).

Der empfohlene CLI-Einstieg ist eine Sitzung im selben Prozess. Sie bewahrt
vorbereitete Pläne zwischen den Gesprächsschritten und akzeptiert eine Freigabe
ausschließlich über `/confirm <plan_id>`; mit `--json` wird pro Zeile ein
NDJSON-Ereignis für kontrollierte Automatisierung ausgegeben.
Der gleiche begrenzte Strands-Nachrichtenverlauf löst nun Folgebezüge in GUI und
CLI auf. Er ist nach organisatorischem Profil getrennt, standardmäßig auf 24
Nachrichten begrenzt, wird nicht dauerhaft gespeichert und lässt sich zusammen
mit unbestätigten Plänen über **Neue Unterhaltung** oder `/reset` löschen.
Die GUI zeigt den Modellzustand direkt: deterministisches Fixture, konfiguriertes
aber noch nicht verifiziertes Bedrock oder Bedrock nach mindestens einem
erfolgreichen Live-Modellturn im aktuellen Prozess. Eine Konfiguration allein
gilt niemals als Beleg einer funktionierenden Modellverbindung.

Die optionale AgentCore-Oberfläche implementiert den aktuellen AWS-HTTP-Vertrag
auf ARM64 (`GET /ping`, `POST /invocations`, Port 8080). Sie akzeptiert nur
synthetische Fixture-Prompts, trennt den Zustand nach AgentCore-Runtime-Sitzung
und kann weder Haushaltsdateien einlesen noch externe Aktionen ausführen. Der
Vertrag ist lokal getestet. Die quotenbegrenzte Runtime wurde bereitgestellt
und zuletzt am 27.08.2026 als `READY` rückgelesen; ihr Fixture-Roundtrip erreichte
`confirmation_required`. Die öffentliche CloudFront-Konfiguration bleibt
`enabled: false`. Solange Nova Micros angewandte On-Demand-Quoten null sind,
wird keine erfolgreiche Bedrock-gestützte Geschichte behauptet.

Mehr: [`ARCHITECTURE.md`](./ARCHITECTURE.md) und
[`docs/submission/ARCHITECTURE_DIAGRAM.md`](./docs/submission/ARCHITECTURE_DIAGRAM.md).

## Was FolderHome lokal kann

- Dokumente extrahieren, indexieren, natürlich suchen und als Themendossier
  oder Ordnerbericht zusammenfassen
- Versionen vergleichen und ältere Fassungen nur als freigabepflichtigen,
  reversiblen Archivplan behandeln
- Ordnerregeln, Watches, Korrekturlernen, Aufräumpläne, sichere Ausführung,
  Audit und Undo verbinden
- TXT-/PDF-Bündel sowie deterministische ZIP-Typpakete erzeugen
- Profile für Lukas, Hanna oder Simon und bereichsspezifische Regeln
  organisieren
- Kontakte, Terminkandidaten, lokale Kalender- und ICS-Handoffs verwalten und
  festgehaltene Termine als eine importierbare ICS-Datei exportieren
- Kontoauszüge, virtuelle Konten, Datenlücken, Abos und Vertragscockpits
  evidenzgebunden darstellen
- Haushalt, Lagerbestand, Medikamentenplan und bestätigte Einnahmen führen
- extraktive Gesundheitsdossiers und Arztbericht-Zeitlinien erstellen
- Bescheide strukturieren, Verwaltungsentwürfe vorbereiten und amtliche
  Leistungsvorchecks routen
- lokale Rechtsänderungs-Snapshots zu Review-Kandidaten vergleichen
- Briefdesigns, Designsets, SVG-Visitenkarten und Office-/Medienhandoffs planen
- kontrollierte Mail-, Kalender-, Notiz-, Steuer-, Daily-Briefing- und
  FindCall-Workflows bereitstellen

Die vollständige Zuordnung und alle Grenzen stehen in
[`Feature_Analyse_FolderHome.md`](Feature_Analyse_FolderHome.de.md).

## Sicherheitsmodell

- Default deny für jede Außenwirkung
- Betriebssystemkonto und Dateirechte als Sicherheitsgrenze; Profile sind nur
  Organisation innerhalb eines Kontos
- exakte Schemas, kanonische Pfade, Quellhashes und Never-overwrite
- getrennte Plan-, Approval-, Recheck-, Ausführungs-, Audit- und Undo-Stufen
- endliche Budgets für Dateien, Bytes, Parser, Renderer, HTTP-Verbindungen,
  Agententurns, Toolaufrufe und Ausgaben
- Loopback nur auf `127.0.0.1` mit Token, Host-/Origin-Prüfung und
  Überlastgrenze
- sensible lokale Reads nur nach ausdrücklichem Gate
- amtliche Links nur über HTTPS und publishergebundene Host-Allowlist

FolderHome diagnostiziert nicht, erteilt keine Rechts-, Steuer- oder
Finanzberatung, entscheidet keinen Leistungsanspruch und garantiert weder
Vollständigkeit noch die Erkennung jedes Termins.

Details und Meldungsweg: [`SECURITY.md`](SECURITY.de.md).

## Private logische Ressourcen

FolderHome hält physische Pfade aus modell-sichtbaren Plänen heraus. Kopiere
das anonyme Beispiel nach `%LOCALAPPDATA%\FolderHome\resources.json`, ersetze
nur die lokalen Locator und deklariere für jede stabile Ressourcen-ID die
minimal erforderlichen Operationen. Das Register ist an ein
Betriebssystemkonto, organisatorische Profile und ausdrückliche Zwecke
gebunden. Sein öffentlicher Katalog enthält keine Pfade.

- Schema: [`config/resources.schema.json`](./config/resources.schema.json)
- Anonymes Beispiel:
  [`examples/resources/resources.example.json`](./examples/resources/resources.example.json)

Mit konfiguriertem Register kann der Masteragent vorhandene FolderHome-Dienste
für Dokumentbündel, Kontakte, lokale Korrespondenz, den eigenen
FolderHome-Kalender, Gesundheitsdossiers, Finanzimport, Bescheidberichte,
ungeprüfte Verwaltungsentwürfe und Leistungsvorchecks ausführen. Jeder
Schreibvorgang benötigt weiterhin die getrennte exakte Planbestätigung. Reine
IMAP-Mailentwürfe stehen nur mit einer Ressource `mail.draft_account` und dem
getrennten Gate `--approve-mail-draft` bereit. Externe Kalenderconnectoren und
Scheduler-Registrierung bleiben unverbunden und separat gegatet.
Das vollständige Register weist 27 verbundene, einen direkt nur lesenden, drei
rein planende und zwei unverbundene Endpunkte aus.

## Lokales Modell über Ollama

Der Master-Agent kann statt auf dem deterministischen Fixture oder Amazon
Bedrock auf einem lokalen Ollama-Modell laufen. Die Gates richten sich nach dem
Transportweg, nicht nach dem Anbieter: Ein Ollama-Host auf der
Loopback-Schnittstelle braucht überhaupt kein Gate, weil nichts diesen Rechner
verlässt. Jeder andere Host, auch einer im eigenen privaten Netz, braucht exakt
dieselben zwei Freigaben wie Bedrock, `--allow-network` und
`--approve-sensitive-cloud-data`.

Das Wort „cloud“ im Namen dieses Schalters bedeutet hier „außerhalb dieses
Betriebssystemkontos“, nicht „außerhalb deines Zuhauses“. FolderHome kann nicht
wissen, ob der Rechner hinter einer Adresse dir gehört, und fragt deshalb in
beiden Fällen einmal nach dem Netz und einmal nach den Daten.

```powershell
# Optionales Extra; der Provider wird nur geladen, wenn du ihn auswählst
.venv\Scripts\pip.exe install -e ".[ollama]"

# Modell auf diesem Rechner: kein Gate, weil nichts die Loopback-Schnittstelle verlässt
.venv\Scripts\python.exe -m folderhome agent chat `
  --profiles-dir examples\profiles --state-dir .local-state `
  --model-provider ollama --ollama-model-id qwen3.8:27b-mlx `
  --profile-id lukas --prompt "Was kannst du?" --json

# Modell auf einem anderen Rechner: beide Freigaben, genau wie bei Bedrock
.venv\Scripts\python.exe -m folderhome agent chat `
  --profiles-dir examples\profiles --state-dir .local-state `
  --model-provider ollama --ollama-host http://192.0.2.10:11434 `
  --ollama-model-id qwen3.8:27b-mlx `
  --allow-network --approve-sensitive-cloud-data `
  --profile-id lukas --prompt "Was kannst du?" --json
```

`--ollama-host` steht standardmäßig auf `http://127.0.0.1:11434`. Die Modell-ID
ist immer Pflicht und wird nie geraten. Statusendpunkt und GUI melden ein
lokales Modell als lokales Modell: `model_inference_location` wird
`local_ollama_host` oder `remote_ollama_host` statt `aws_cloud`, und kein Lauf
behauptet eine bestätigte Verbindung, bevor eine Live-Runde im selben Prozess
erfolgreich war.

## FolderHome aus Claude Code oder Codex nutzen (MCP)

`folderhome mcp serve` veröffentlicht dieselbe begrenzte Oberfläche über das
Model Context Protocol auf stdio. Ein Coding-Agent kann damit deine Dokumente
durchsuchen, den Master-Agenten fragen und einen Plan freigeben. Der Server hält
keinen eigenen Zustand: Er ist ein Proxy auf die Loopback-API eines laufenden
`app serve`. Editor und GUI teilen sich deshalb einen Prozess, eine Unterhaltung
und dieselben vorgeschlagenen Pläne.

Zuerst die App starten und ihre Zugriffs-URL übernehmen; das Token ist bei jedem
Start neu.

```powershell
# 1. Lokale App starten und die ausgegebene access_url notieren
.venv\Scripts\python.exe -m folderhome app serve `
  --profiles-dir examples\profiles --state-dir .local-state `
  --port 8765 --approve-loopback-server --json

# 2. Fertige Einbindung für beide Editoren ausgeben
.venv\Scripts\python.exe -m folderhome mcp plan `
  --access-url "http://127.0.0.1:8765/?token=<token>" --json
```

`mcp plan` gibt den exakten Befehl `claude mcp add folderhome -- ...` und den
passenden Block `[mcp_servers.folderhome]` für `~/.codex/config.toml` aus. Die
Adresse muss `127.0.0.1` sein; jeder andere Host wird vor dem Serverstart
abgelehnt, ebenso ein fehlendes `--approve-mcp-server`. Zehn Werkzeuge stehen
bereit: `folderhome_status`, `_profiles`, `_capabilities`, `_executors`,
`_resources`, `_search_documents`, `_topic_dossier`, `_chat`, `_confirm_plan`
und `_reset_conversation`.

Ein Chat über MCP ist genauso wenig eine Freigabe wie ein Chat in der GUI. Ein
vorgeschlagener Plan läuft nur über `folderhome_confirm_plan` mit seinem exakten
Hash und den ausgewählten Schritt-IDs; ein falscher Hash wird abgelehnt, und die
Ablehnung erreicht den Editor wortgleich.

Weil das Token bei jedem Start von `app serve` neu ist, veraltet der
Editor-Eintrag mit ihm: Nach jedem Neustart `mcp plan` erneut aufrufen und den
hinterlegten Befehl ersetzen — oder die aktuelle URL als
`FOLDERHOME_ACCESS_URL` exportieren und den Server ohne `--access-url`
eintragen.

## Ergebnisse zum Abholen

Alles, was ein freigegebener Plan erzeugt, bleibt in der GUI erreichbar — auch
wenn der Lauf anderswo gestartet wurde. Das Panel **Ergebnisse** listet, was
dieser Prozess für das gewählte Profil ausgeführt hat, das Neueste zuerst, mit
Workflow, Status, Zeitpunkt und den geschriebenen Dateien. Ein Klick lädt eine
Datei über die tokengeschützte API; der Browser sieht dabei nie einen Dateipfad,
denn die Liste trägt nur Dateinamen, Größe und einen Index.

Damit schließt sich die Lücke zwischen den drei Zugängen: Ein über die API oder
über einen Editor per MCP freigegebener Plan erscheint im selben Panel wie einer
aus der GUI, weil alle drei denselben Prozess bedienen.

Angeboten werden ausschließlich Dateien innerhalb einer registrierten
Ausgaberessource dieses Profils, und nur unter dem Namen, den der
Ausführungsbericht selbst nennt. Läufe, die lediglich lokalen Zustand ändern,
etwa eine bestätigte Medikamentengabe, erscheinen ohne Datei und sagen das auch.

## Direkte HTTP-API

Derselbe Loopback-Dienst, den die GUI nutzt, ist eine schlichte JSON-API.
`app serve` gibt seine `access_url` aus; darin steckt das Sitzungstoken, das bei
jedem Start wechselt. Browser-Routen lesen dieses Token aus der Query, jede
`/api/`-Route dagegen aus dem Kopffeld `X-FolderHome-Token`.

| Methode und Route | Zweck |
|---|---|
| `GET /api/v1/status` | Laufzeitgrenze und Modellverbindung |
| `GET /api/v1/profiles` | organisatorische Profile |
| `GET /api/v1/capabilities` | Fähigkeiten und ihre Oberfläche |
| `GET /api/v1/agent/executors` | welche Workflows einen verbundenen Executor haben |
| `GET /api/v1/resources?profile_id=…` | logische Ressourcen, ohne Pfade |
| `GET /api/v1/agent/results?profile_id=…&limit=…` | was bereits lief, das Neueste zuerst |
| `GET /api/v1/agent/results/<execution_id>/artifacts/<index>` | eine erzeugte Datei als Download |
| `POST /api/v1/documents/search` | read-only Dokumentsuche |
| `POST /api/v1/documents/dossier` | Themendossier mit verknüpften Belegen |
| `POST /api/v1/agent/chat` | eine begrenzte Master-Agenten-Runde |
| `POST /api/v1/agent/confirm` | exakte Schritte eines Plans freigeben |
| `POST /api/v1/agent/conversation/reset` | neue prozesslokale Unterhaltung |

Jeder POST-Rumpf folgt einem geschlossenen Schema: Unbekannte oder fehlende
Felder werden abgelehnt statt ignoriert, und die Anfragegrenze liegt bei
65 536 Byte.

```bash
TOKEN="<Token aus access_url>"
BASE="http://127.0.0.1:8765"

# Den Agenten fragen; die Antwort kann einen vorgeschlagenen Plan enthalten
curl -s "$BASE/api/v1/agent/chat" \
  -H "X-FolderHome-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"schema":"folderhome.local-agent-chat-request.v1",
       "profile_id":"lukas","message":"Was kannst du?"}'

# Genau diesen Plan freigeben; ein Chat allein führt nie etwas aus
curl -s "$BASE/api/v1/agent/confirm" \
  -H "X-FolderHome-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"schema":"folderhome.local-agent-confirmation-request.v1",
       "plan_id":"<plan_id>","plan_sha256":"<plan_sha256>",
       "step_ids":["<step_id>"]}'

# Abholen, was dabei entstanden ist
curl -s "$BASE/api/v1/agent/results?profile_id=lukas" \
  -H "X-FolderHome-Token: $TOKEN"
curl -s -OJ "$BASE/api/v1/agent/results/<execution_id>/artifacts/0" \
  -H "X-FolderHome-Token: $TOKEN"
```

Der Dienst bindet ausschließlich an `127.0.0.1`, prüft das `Host`-Kopffeld gegen
diese Bindung, weist einen fremden Browser-`Origin` ab und sendet keine
CORS-Kopfzeilen. Er ist eine Schnittstelle für Programme auf diesem Rechner,
kein Netzwerkdienst.

## Wichtige Befehle

```powershell
# Validate the private resource registry without disclosing physical paths
.venv\Scripts\python.exe -m folderhome resources validate `
  --profiles-dir examples\profiles --json

# List the model-safe logical catalog for one organizational profile
.venv\Scripts\python.exe -m folderhome resources catalog `
  --profiles-dir examples\profiles --profile lukas --json

# Validate the agent configuration without invoking a model
.venv\Scripts\python.exe -m folderhome agent plan `
  --profiles-dir examples\profiles --state-dir .local-state --json

# Start an interactive session with the same master service used by the GUI
.venv\Scripts\python.exe -m folderhome agent session `
  --profiles-dir examples\profiles --state-dir .local-state `
  --profile-id lukas

# Run one non-interactive chat turn
.venv\Scripts\python.exe -m folderhome agent chat `
  --profiles-dir examples\profiles --state-dir .local-state `
  --profile-id lukas --prompt "Was kannst du?" --json

# Run the reproducible agent demo
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir .local-demo\competition --approve-output-write --json

# Plan the local loopback chat interface
.venv\Scripts\python.exe -m folderhome app plan `
  --profiles-dir examples\profiles --state-dir .local-state `
  --port 8765 --json

# Start the interface only after the explicit listener gate
.venv\Scripts\python.exe -m folderhome app serve `
  --profiles-dir examples\profiles --state-dir .local-state `
  --port 8765 --approve-loopback-server --json

# Show all CLI commands
.venv\Scripts\python.exe -m folderhome --help
```

Die ausführlichen Playbooks liegen unter [`workflows/`](./workflows/) und im
generierten [`WORKFLOWS.md`](WORKFLOWS.de.md).

## Entwicklungsprüfung

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m folderhome plugins validate --json
.venv\Scripts\python.exe _tools\doc-lint
.venv\Scripts\python.exe _tools\workflows-sync --check
```

Die mitgelieferte Referenzevidenz liegt unter
[`examples/competition/evidence/`](./examples/competition/evidence/).

## Repositorystruktur und Herkunft

```text
src/folderhome/       neuer Wettbewerbs- und Bridgecode
config/               versionierte Schemas für ausschließlich lokale Konfiguration
skills/               neue agentisch nutzbare FolderHome-Skills
workflows/            ausführbare Arbeitsverträge
manifests/            Komponenten- und spätere Stackverträge
reused/               gepinnte Bestandsreferenzen, kein umbenannter Quellcode
examples/             ausschließlich synthetische Fixtures und Evidenz
tests/                Vertrags-, Sicherheits- und Integrationstests
docs/submission/      lokal vorbereitete englische Einreichungsunterlagen
docs/archive/         direkte historische Vorgänger langer Projektdokumente
```

FCSA, KnowledgeDigest, doc-services, HungryCall, Ringedingeding, llm-note,
steuer-assistent, law-checker und weitere Bestandskomponenten bleiben
offengelegt und revisionsgebunden. FolderHome kopiert ihren Quellcode nicht.

- Herkunft: [`COMPETITION_CODE_MAP.md`](./COMPETITION_CODE_MAP.md)
- Lizenzen und Pins: [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.de.md)
- Entscheidungen: [`DECISIONS.md`](./DECISIONS.md)
- Changelog: [`CHANGELOG.md`](./CHANGELOG.md)

## Submission-Grenze

Englische Beschreibung, Diagramm, Tests, Videoskript und Checkliste sind unter
[`docs/submission/`](./docs/submission/) vorbereitet. Das öffentliche
Repository liegt unter <https://github.com/ellmos-ai/FolderHome>. AWS Builder
ID bleibt ausschließlich im privaten Devpost-Formular. Das freigegebene
Demovideo ist unter <https://youtu.be/wPb1wBJcLjQ> öffentlich. Der Nutzer hat
FolderHome am 23.08.2026 bei Agents for Humans eingereicht; der authentifizierte
Readback enthält `submitted_at=2026-08-23T17:14:05.813-04:00`.

## Lizenz

FolderHome steht unter der [MIT-Lizenz](./LICENSE). Der Wettbewerbscode wird
öffentlich auf GitHub bereitgestellt; reale Dienste und personenbezogene
Daten bleiben davon ausgeschlossen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
