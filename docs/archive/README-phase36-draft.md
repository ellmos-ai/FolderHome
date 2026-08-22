# FolderHome

> Assistantify your home.

FolderHome ist ein lokaler Dokument- und Assistenzservice-Agent für den
Alltag. Er verbindet vorhandene, offen ausgewiesene Komponenten über sichere
Plugin-Verträge und baut neue Fähigkeiten als wiederverwendbare Pakete. Der
erste Baustein ist ein fail-closed Integrationskern mit nachvollziehbaren
JSON-Laufberichten. FCSA erzeugt Sortierpläne ohne Dateibewegung; die lokale
Dokumenten-Pipeline extrahiert, indexiert, durchsucht und beschreibt Dateien
über exakt gepinnte Provider, ohne die Quelldokumente zu verändern.

## Status

Alle 36 Wettbewerbsphasen sind lokal umgesetzt und geprüft. Phase 36 ergänzt
einen echten, endlich begrenzten Strands-Agenten, gemeinsame
Ressourcenbudgets, den vollständigen Security-Scan, eine reproduzierbare
synthetische Demo und vorbereitete englische Einreichungsunterlagen. Die
vollständige Suite umfasst **331 bestandene Tests**. Externe Connectoren,
Amazon Bedrock, Veröffentlichung, Video-Upload und Devpost-Submit sind davon
getrennte Nutzer-Gates. Der Stand liegt auf `phase1-foundation` und besitzt
weiterhin keinen Remote.

Während des Wettbewerbs heißt das Projekt ausschließlich **FolderHome**.
Ein späteres Rebranding gehört nicht in diesen Wettbewerbsstand.

Der belegte Abschluss steht im
[`Phase-36-Completion-Audit`](../phase36-completion-audit.md), das
Sicherheitsmodell in [`SECURITY.md`](../../SECURITY.md). Die englischen Entwürfe
liegen unter [`docs/submission/`](../submission/).

## Reproduzierbare Wettbewerbsdemo

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,transform]"
.venv\Scripts\python.exe -m folderhome agent plan `
  --profiles-dir examples\profiles --state-dir .local-state --json
.venv\Scripts\python.exe -m folderhome demo run `
  --output-dir .local-demo\competition --approve-output-write --json
```

Die Demo durchläuft den echten `strands.Agent` und zwei echte FolderHome-
Tools mit einem deterministischen Fixture-Modell. Sie benötigt keine
Zugangsdaten, verwendet kein Netzwerk und schreibt nur vier neue Artefakte in
den ausdrücklich freigegebenen Ausgabeordner. Ein zweiter Lauf in denselben
Ordner blockiert statt zu überschreiben. Die mitgelieferte Referenzevidenz
liegt unter [`examples/competition/evidence/`](../../examples/competition/evidence/).

Bedrock ist optional und nur mit Modell-ID, AWS-Region und ausdrücklichem
`--allow-network` erreichbar; der lokale Nachweis behauptet keinen
Cloudbetrieb.

## Quick Start

```powershell
python -m pip install -e ".[transform]"
python -m folderhome plugins validate --json
python -m folderhome run synthetic --json --report-file run-reports\demo.json
python -m folderhome run fcsa-plan --config-dir examples\fcsa\config `
  --provider-root ..\file-collect-sort-action `
  --report-file run-reports\fcsa-demo.json --json

$demoState = Join-Path $env:TEMP "folderhome-demo-state"
python -m folderhome documents ingest `
  --source-dir examples\documents\inbox --state-dir $demoState `
  --approve-index-write --result-file run-reports\ingest.json `
  --report-file run-reports\ordnerbericht.md --json
python -m folderhome documents search --state-dir $demoState `
  --query "Ich suche nach einem Dokument über meine Krankenversicherung." --json
python -m folderhome documents dossier --state-dir $demoState `
  --topic Krankenversicherung --output-file run-reports\dossier.md --json
python -m folderhome app plan --profiles-dir examples\profiles `
  --state-dir $demoState --port 8765 --json
python -m folderhome app serve --profiles-dir examples\profiles `
  --state-dir $demoState --port 8765 --approve-loopback-server --json
python -m folderhome documents versions --state-dir $demoState `
  --query "Was ist meine neueste Krankenversicherung?" `
  --output-file run-reports\versionen.json --json
python -m folderhome profiles validate --profiles-dir examples\profiles --json
python -m folderhome profiles resolve --profiles-dir examples\profiles `
  --profile lukas --area versicherungen --json
python -m folderhome documents plan --profiles-dir examples\profiles `
  --profile lukas --area versicherungen `
  --source-file examples\documents\inbox\Krankenversicherung.txt `
  --target-root "$demoState\Ablage" --as-of 2026-08-21 --json
New-Item -ItemType Directory -Force "$demoState\Ausgabe" | Out-Null
python -m folderhome documents bundle `
  --source-dir examples\documents\inbox `
  --output-file "$demoState\Ausgabe\Dokumente.txt" --format txt `
  --approve-output-write --json
python -m folderhome documents package `
  --source-dir examples\documents\inbox `
  --output-zip "$demoState\Ausgabe\Dokumentpaket.zip" `
  --approve-output-write --json
$beforeSnapshot = (python -m folderhome folders snapshot `
  --source-dir examples\documents\inbox `
  --captured-at 2026-08-21T20:30:00Z `
  --state-dir $demoState --approve-state-write --json | ConvertFrom-Json).snapshot_file
$afterSnapshot = (python -m folderhome folders snapshot `
  --source-dir examples\documents\inbox `
  --captured-at 2026-08-21T20:31:00Z `
  --state-dir $demoState --approve-state-write --json | ConvertFrom-Json).snapshot_file
python -m folderhome folders diff `
  --before-file $beforeSnapshot --after-file $afterSnapshot --json
python -m folderhome folders scan `
  --config-file examples\observation\watched-folders.json `
  --watch-id synthetic_inbox --captured-at 2026-08-21T20:45:00Z `
  --state-dir $demoState --json
python -m folderhome folders routine-plan `
  --config-file examples\observation\watched-folders.json `
  --watch-id synthetic_inbox --captured-at 2026-08-21T21:45:00Z `
  --state-dir $demoState --profiles-dir examples\profiles `
  --target-root "$demoState\Ablage" --as-of 2026-08-21 `
  --mode changes --json
python -m folderhome folders routine-queue `
  --config-file examples\observation\watched-folders.json `
  --bindings-file examples\observation\routine-bindings.json `
  --captured-at 2026-08-21T21:46:00Z --state-dir $demoState `
  --profiles-dir examples\profiles --as-of 2026-08-21 --json
python -m folderhome scheduler plan `
  --task-name folderhome_routine_queue --interval-minutes 30 `
  --start-at 2026-08-22T08:00:00+02:00 --timezone Europe/Berlin `
  --config-file examples\observation\watched-folders.json `
  --bindings-file examples\observation\routine-bindings.json `
  --profiles-dir examples\profiles --state-dir $demoState --json
python -m folderhome contacts plan `
  --source-dir examples\documents\contacts --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas --area versicherungen `
  --approve-sensitive-local-read --json
python -m folderhome calendar plan `
  --source-dir examples\documents\calendar `
  --calendar-config examples\calendar\calendar-config.json `
  --profiles-dir examples\profiles --state-dir $demoState `
  --profile lukas --area gesundheit `
  --planned-at 2026-08-22T00:30:00+02:00 `
  --approve-sensitive-local-read --json
python -m folderhome calendar connectors --json
python -m folderhome calendar connector-plan `
  --source-dir examples\documents\calendar `
  --calendar-config examples\calendar\calendar-config-google.json `
  --profiles-dir examples\profiles --state-dir $demoState `
  --profile lukas --area gesundheit `
  --planned-at 2026-08-22T04:20:00+02:00 `
  --connector-accounts examples\calendar\connector-accounts.json `
  --connector-request examples\calendar\connector-request-google.json `
  --approve-sensitive-local-read --json
python -m folderhome findcall plugins --json
python -m folderhome findcall plan `
  --request-file examples\findcall\request-werkstatt.json `
  --candidates-file examples\findcall\candidates-werkstatt.json `
  --planned-at 2026-08-22T01:00:00+02:00 --json
python -m folderhome findcall simulate `
  --request-file examples\findcall\request-werkstatt.json `
  --candidates-file examples\findcall\candidates-werkstatt.json `
  --fixture-file examples\findcall\fixtures-werkstatt.json `
  --planned-at 2026-08-22T01:00:00+02:00 --json
python -m folderhome finance plan `
  --source-dir examples\documents\finance --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas `
  --approve-sensitive-local-read --json
python -m folderhome inventory plan `
  --source-dir examples\inventory\bestand --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas `
  --approve-sensitive-local-read --json
python -m folderhome medication plan `
  --source-dir examples\medication\plans --state-dir $demoState `
  --profiles-dir examples\profiles --profile lukas `
  --approve-sensitive-local-read --json
python -m folderhome health dossier `
  --source-dir examples\health --profiles-dir examples\profiles `
  --profile lukas --as-of 2026-08-22 `
  --approve-sensitive-local-read `
  --output-markdown "$demoState\Gesundheitsdossier.md" `
  --output-json "$demoState\Gesundheitsdossier.json" --json
python -m folderhome documents ingest `
  --source-dir examples\contracts\documents --state-dir $demoState `
  --approve-index-write --json
python -m folderhome contracts cockpit `
  --request-file examples\contracts\cockpit-hyundai-i10.json `
  --state-dir $demoState --profiles-dir examples\profiles `
  --approve-sensitive-local-read `
  --output-markdown "$env:TEMP\FolderHome-Vertragscockpit.md" `
  --output-json "$env:TEMP\FolderHome-Vertragscockpit.json" --json
python -m folderhome correspondence preview `
  --request-file examples\correspondence\insurance-cancellation.json `
  --designs-file examples\correspondence\designs.json `
  --templates-file examples\correspondence\templates.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome correspondence render `
  --request-file examples\correspondence\insurance-cancellation.json `
  --designs-file examples\correspondence\designs.json `
  --templates-file examples\correspondence\templates.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read `
  --markdown-file "$env:TEMP\FolderHome-Brief.md" `
  --text-file "$env:TEMP\FolderHome-Brief.txt" `
  --approve-output-write --json
python -m folderhome artifacts plan `
  --request-file examples\artifacts\artifact-request.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome artifacts design-preview `
  --request-file examples\artifacts\design-request.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome mail providers --json
python -m folderhome mail ingest-plan `
  --accounts-file examples\mail\accounts.json `
  --request-file examples\mail\ingest-request.json `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read --json
python -m folderhome notes providers --provider-root ..\llm-note --json
python -m folderhome notes guide `
  --request-file examples\notes\create-request.json `
  --profiles-dir examples\profiles --state-dir $demoState `
  --provider-root ..\llm-note --json
python -m folderhome tax providers `
  --provider-root ..\steuer-assistent --json
python -m folderhome briefing plan `
  --request-file examples\briefing\briefing-request.json `
  --profiles-dir examples\profiles `
  --output-file "$demoState\Morgenbrief.html" `
  --desktop-file "$env:TEMP\Desktop\Morgenbrief.html" `
  --approve-sensitive-local-read --json
python -m folderhome notices inspect `
  --source-file examples\notices\Bescheid.txt `
  --profiles-dir examples\profiles --profile lukas `
  --received-on 2026-08-21 --as-of 2026-08-22T12:00:00+02:00 `
  --approve-sensitive-local-read --json
python -m folderhome drafts preview `
  --request-file examples\notices\objection-draft-request.json `
  --source-file examples\notices\Bescheid.txt `
  --designs-file examples\correspondence\designs.json `
  --templates-file examples\notices\administrative-templates.json `
  --profiles-dir examples\profiles --received-on 2026-08-15 `
  --as-of 2026-08-22T06:00:00+02:00 `
  --approve-sensitive-local-read --json
python -m folderhome benefits check `
  --profile-facts-file examples\benefits\Lukas-benefit-profile.json `
  --catalog-file examples\benefits\official-routing-catalog.json `
  --profiles-dir examples\profiles `
  --as-of 2026-08-22T07:00:00+02:00 `
  --max-source-age-days 30 --approve-sensitive-local-read --json
python -m folderhome legal compare `
  --before-file examples\legal\before.json `
  --after-file examples\legal\after.json `
  --interests-file examples\legal\Lukas-interests.json `
  --as-of 2026-08-22T08:00:00+02:00 `
  --max-source-age-days 7 --approve-sensitive-local-read `
  --allow-test-fixture --json
```

Die absichtlich getrennten Approval- und Apply-Sequenzen stehen im
[Kontaktregister-Workflow](../../workflows/contact-register.md) und im
[Kalender-Handoff-Workflow](../../workflows/calendar-handoff.md), im
[Finanz-Workflow](../../workflows/finance-import.md) und im
[Inventar-Workflow](../../workflows/inventory-import.md).
Der getrennte Plan-/Bestätigungsablauf für Einnahmen steht im
[Medikamenten-Workflow](../../workflows/medication-intake.md). Vorschau und
kontrollierte Briefausgabe beschreibt der
[Korrespondenz-Workflow](../../workflows/correspondence-studio.md).
Office-/Medienrouting und lokale Designausgaben stehen im
[Artefaktstudio-Workflow](../../workflows/artifact-studio.md).
Read-only Postfachabruf, Kontaktbindung und gesonderten Versand beschreibt der
[Mail-Workflow](../../workflows/mail-connector.md).
Geführte persönliche Notizen, Freigabe und append-only Historie beschreibt
der [Notiz-Workflow](../../workflows/personal-notes.md).
Bestätigte Steuerbelege und den getrennt freigegebenen privaten ZIP-Export
beschreibt der [Steuer-Workflow](../../workflows/tax-workpaper.md).
Lokale Wetter- und Nachrichtensnapshots sowie die getrennte Desktopzustellung
beschreibt der [Briefing-Workflow](../../workflows/daily-briefing.md).
Evidenzgebundenes Bescheidverständnis ohne Rechtsprüfung beschreibt der
[Bescheid-Workflow](../../workflows/official-notice-understanding.md).
Kontrollierte lokale Widerspruchs-, Antwort- und Antragsentwürfe beschreibt
der [Verwaltungsentwurf-Workflow](../../workflows/administrative-drafts.md).
Den lokalen Orientierungslauf und amtliche nächste Prüfschritte beschreibt der
[Leistungsvorcheck-Workflow](../../workflows/benefit-screening.md).
Technische Normänderungen und unverbindliche Profil-/Vertragsprüfkandidaten
beschreibt der
[Rechtsänderungs-Workflow](../../workflows/legal-change-monitor.md).
Die endlich begrenzte Strands-Schleife und ihre beiden read-only Tools
beschreibt der [Agenten-Workflow](../../workflows/strands-agent.md).

## Entwicklungsprüfung

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m folderhome plugins validate --json
.venv\Scripts\python.exe _tools\doc-lint
.venv\Scripts\python.exe _tools\workflows-sync --check
```

## Repository-Grenzen

```text
src/folderhome/       neuer Wettbewerbskern einschließlich installierbarer Bridges
bridges/              Provider-Dokumentation und Integrationsgrenzen
skills/               neue agentische Skills
manifests/            Komponenten- und später Stack-Manifeste
reused/               gepinnte Referenzen auf vorbestehende Komponenten
tests/                Vertrags-, Sicherheits- und Integrationstests
examples/synthetic/   ausschließlich synthetische Beispieldaten
examples/documents/   synthetischer Dokumentenbestand für die lokale Demo
examples/profiles/    synthetische Profile und Regelvererbung
examples/inventory/   synthetische Bestandsaufnahmen
examples/medication/  synthetische Medikamentenpläne
examples/health/      synthetische Gesundheitsdokumente
examples/mail/        synthetische Konten und read-only Ingest-Anfrage
examples/notes/       synthetische persönliche Notizanfrage
examples/tax/         synthetischer Beleg und sichere Anfragevorlage
examples/briefing/    synthetische Wetter- und Nachrichtensnapshots
examples/notices/     synthetischer Bescheidfall ohne echte Personendaten
examples/benefits/    synthetisches Leistungsprofil und amtliche Handoffs
examples/competition/ reproduzierbare synthetische Strands-Evidenz
examples/contracts/   synthetischer Versicherungs- und Vertragsfall
examples/correspondence/ synthetische Briefvorlage, Designs und Anfrage
examples/artifacts/   synthetischer Office-/Medienplan und lokales Designset
```

Die genaue Einordnung steht in
[`COMPETITION_CODE_MAP.md`](../../COMPETITION_CODE_MAP.md), die Revisionen und
Lizenzen in [`THIRD_PARTY_LICENSES.md`](../../THIRD_PARTY_LICENSES.md).

## Sicherheitsgrenzen

- Side-Effects werden standardmäßig blockiert.
- FCSA führt keine echten Datei-, Netzwerk- oder Telefonaktionen aus.
- Der FCSA-Dry-Run verwendet einen temporären Schattenzustand und bestätigt
  dadurch keinen späteren Live-Lauf im produktiven FCSA-State.
- Der Dokumenten-Ingest schreibt ausschließlich nach ausdrücklichem CLI-Gate
  in einen angegebenen lokalen Indexordner; Quellen werden nie archiviert,
  verschoben oder überschrieben.
- Dokumentensuche verwendet einen schreibgeschützten SQLite-Zugriff und lässt
  die KnowledgeDigest-Indexdatei bytegenau unverändert.
- Versionsanalysen bevorzugen explizite Vertragsdaten, erklären schwächere
  Dateiname-/Änderungsdatum-Fallbacks und lassen ältere Fassungen von FCSA nur
  als ungefreigten, reversiblen Dry-Run-Plan bestätigen.
- Profile sind nur organisatorische Präferenzen im selben OS-Konto. Die feste
  Vererbung lautet global → Bereich → Profil → Profilbereich; gleichrangige
  Widersprüche blockieren die Auflösung und `hard_delete` ist unzulässig.
- Dokumentaktionspläne nennen für jeden Schritt Regelquelle, Ziel, Provider,
  Gate und Rückweg. Benennen, Sortieren, Konvertieren, Archivieren und
  Papierkorb bleiben ungefreigt; Zielkonflikte werden sichtbar blockiert.
- Archivierungs- und Papierkorbschritte werden gegen den real gepinnten
  FCSA-Dry-Run geprüft. PDF/TXT werden durch den neuen Transformationskern
  geplant; andere Zielformate bleiben ohne geprüften Provider blockiert.
- Der neue Transformationskern bündelt ausgewählte Quellen als UTF-8-TXT oder
  PDF. PDF-Seiten bleiben erhalten, Bilder werden gerastert und andere
  Dokumente aus extrahiertem Text neu gesetzt; jeder Layoutverlust steht im
  Plan. Ohne `--approve-output-write` wird keine Ausgabe geschrieben.
- Transformationen veröffentlichen atomar, überschreiben nie, prüfen vor dem
  Schreiben alle Quellhashes erneut und verändern Originale nicht. Eine
  Originalaktion wird erst nach verifiziertem Ausgabehash freischaltbar.
- `documents package` gruppiert einen Ordner nach Dateityp: Bilder und PDFs
  werden jeweils ein PDF, Text-/Markdown- und weitere extrahierbare Typen je
  ein TXT. Ein deterministisches ZIP enthält alle Gruppenausgaben und ein
  Manifest; unbekannte Formate bleiben darin mit Hash und Grund sichtbar.
- `folders snapshot` speichert nach ausdrücklichem State-Gate nur Pfad,
  Dateigröße, Zeitstempel und SHA-256. `folders diff` unterscheidet neue,
  entfernte, geänderte und nur bei eindeutigem Hash verschobene Dateien.
- Eine manuelle Verschiebung wird nur zusammen mit einem früheren
  Ablagebeleg zum Lernkandidaten. `folders learning` schreibt nichts und
  übernimmt niemals automatisch eine Regel.
- `folders scan` bindet diese Bausteine an ein deklaratives
  Beobachtungsprofil. Es findet den letzten verifizierten Checkpoint desselben
  Roots, meldet Intervallfälligkeit, Diff und Lernkandidaten in einem
  Auditbericht und schreibt nur mit `--approve-state-write` einen neuen
  unveränderlichen Checkpoint.
- `documents execute` baut den Plan aus Quelle und Profil erneut auf. Nur wenn
  angegebene Plan-ID und ein lückenloser Präfix konkreter Aktions-IDs passen,
  darf `--approve-file-write` Rename-/Move-Schritte ausführen. Quelle und
  jedes Zwischenziel werden erneut gehasht; vorhandene Ziele werden nie
  überschrieben.
- Jede Ausführung schreibt vor der Dateiaktion ein unveränderliches Intent
  und danach Abschlussbericht sowie Ablagebeleg ohne Rohtext. `documents undo`
  benötigt eine eigene, an Ausführungs-ID und Hash gebundene Freigabe und
  blockiert bei geändertem Ziel oder manipuliertem Audit.
- `folders cleanup-plan` erstellt für einen ganzen ausdrücklich gewählten
  Ordner deterministische Einzelpläne und eine gemeinsame Batch-ID. Nicht
  unterstützte Dateien bleiben mit Hash und Grund sichtbar; gemeinsame Ziele,
  bestehende Ziele und Quelle-Ziel-Abhängigkeiten blockieren betroffene
  Dokumente vor jeder Ausführung.
- `folders cleanup-execute` liest eine eigenständige Approval-Datei und führt
  nur die dort genannten Dokument-/Plan-/Aktionskombinationen aus. Scheitert
  ein späteres Dokument, werden bereits abgeschlossene Dokumentaktionen
  rückwärts ausgeführt und der Batch als `rolled_back` oder `failed`
  protokolliert.
- `folders routine-plan` verbindet einen Watch mit seinem letzten Checkpoint
  und einem gefilterten Cleanup-Plan, schreibt aber weder Checkpoint noch
  Datei. `changes` plant nur fällige neue, geänderte oder eindeutig
  verschobene Dateien; `full` prüft den vollständigen Bestand ausdrücklich.
- `folders routine-execute` benötigt dieselbe exakte Batchfreigabe sowie
  Datei- und State-Gate. Vor der ersten Änderung werden Watch-Historie und
  Ordnerzustand erneut geprüft. Erst nach erfolgreichem Batch folgt der neue
  Checkpoint; scheitert er, werden die Dateiaktionen rückwärts ausgeführt.
- Ein Routinenziel innerhalb des beobachteten Eingangs wird blockiert, damit
  verschobene Dateien nicht erneut als Eingang verarbeitet werden.
- `folders routine-queue` liest Watch- und Binding-Konfiguration gemeinsam
  und gibt alle aktiven Watches als `ready`, `not_due`, `empty` oder
  `blocked` aus. Überlappende Eingänge, Ziele in einem anderen beobachteten
  Eingang und gemeinsame Aktionsziele blockieren betroffene Queue-Einträge.
- Die Queue schreibt weder Dateien noch State, registriert keinen Scheduler
  und besitzt deshalb absichtlich kein Approval- oder Installationsflag.
- `scheduler plan` serialisiert einen portablen Argumentvektor und ein
  Windows-Task-XML, führt aber keine Installation aus. Der Plan weist
  `registration_performed=false` und `installation_supported=false` aus.
- `scheduler run` benötigt ein enges Scheduler-State-Gate, sperrt nur seine
  eigene Schedule-ID und schreibt einen append-only Queue-Bericht. Exitcodes
  unterscheiden Leerlauf (0), Freigabebedarf (10), Blockierung (20) und einen
  bereits laufenden oder ungeklärten Lauf (30).
- Ein bestehendes Scheduler-Lock wird weder übernommen noch automatisch
  gelöscht. Der Lock betrifft ausschließlich operativen FolderHome-State,
  niemals beobachtete Ordner oder Nutzerdokumente.
- `contacts plan` speichert weder Dokumentrohtext noch Registerstate. Gelabelte
  Kontaktfelder bleiben an Dokument-ID, Quellhash und genaue Zeilenevidenz
  gebunden; widersprüchliche neueste Kontakte blockieren die Planung.
- `review_required` benötigt für die lokale Kontaktextraktion ein eigenes
  Gate. Dieses erlaubt keine externe Weitergabe; `blocked` und `not_checked`
  bleiben gesperrt.
- `contacts apply` prüft Plan, Registerrevision und Quellhash erneut und
  schreibt nur nach `--approve-state-write` eine SQLite-Transaktion samt
  append-only Ereignissen. Es existiert keine automatische Löschoperation.
- `calendar plan` erkennt ausschließlich gelabelte Terminfelder und weist
  ausdrücklich `completeness_guaranteed=false` aus. Backend und Zeitzone
  folgen Konfigurationsfallback und derselben Profilvererbung wie Dokumentregeln.
- `calendar apply` baut den Plan erneut auf und bindet die Freigabe an Plan-ID,
  Kalenderrevision und konkrete Aktionen. Quellen, Ziele und Inhaltshashes
  werden vor jeder Ausführung erneut geprüft.
- `folderhome_local` schreibt nach State-Gate Ereignis und append-only Audit in
  einer SQLite-Transaktion. Identische UIDs werden beim nächsten Plan `noop`;
  Zeitkonflikte bleiben blockiert.
- `uptoday_ics` publiziert nach getrenntem State- und Output-Gate pro Kandidat
  nur eine neue deterministische ICS-Datei. Ein Batchfehler nimmt eigene,
  unveränderte Ausgaben zurück. UpToday wird weder aufgerufen noch importiert.
  Routinika und Google bleiben ohne eigenen geprüften Connector blockiert.
- `calendar connector-plan` übernimmt Kandidaten, Profilregelquelle und
  Zeitzone aus Phase 17. UpToday delegiert weiter an ICS; Routinika bleibt
  blockiert; Google erzeugt nur einen prüfpflichtigen Handoff mit expliziter
  Kalender-ID, Solo-Teilnehmerliste, Offsetzeiten und Reminderstruktur.
- `calendar connector-simulate` läuft nur mit zwei ausdrücklichen
  Synthetikschaltern. Der Fixture-Provider nutzt weder Netzwerk noch echten
  Kalender; Update und Löschen bleiben ohne Provider-Ereignisreferenz gesperrt.
- `findcall plugins` importiert ausschließlich die lokalen Dry-Run-Seams der
  exakt gepinnten, sauberen HungryCall- und Ringedingeding-Checkouts. Es wird
  kein Live-Transport konstruiert.
- FindCall übernimmt HungryCalls serielles Early-Stop-Muster in einen neuen
  providerneutralen Kern; Restaurantmodelle werden nicht für Arztpraxen oder
  Werkstätten missbraucht. Ringedingeding bleibt das getrennte Plugin für
  Mehrpersonen-Polls und Terminabstimmungen.
- `findcall simulate` akzeptiert ausschließlich einen Provider mit
  `simulated=true`, ohne Netzwerk und Telefonwirkung. Ergebnisse bewahren
  Call-Status und Ablehnungsgründe, maskieren Rufnummern und dürfen bei
  `inquiry_only` keine Buchung, Bestellung oder Preiszusage erzeugen.
- Kontoauszüge verwenden die bestehende doc-services-Extraktion und ein enges
  deklaratives V1-Format. Beträge sind ganzzahlige Cent; Anfangssaldo plus
  Buchungen muss exakt dem Endsaldo entsprechen.
- `finance apply` baut den Plan neu, prüft Approval, Finanzrevision und
  Quellhash und ergänzt Konto, Auszug, Buchungen und append-only Audit in einer
  SQLite-Transaktion. Es existieren weder Bankzugriff noch Löschoperation.
- `finance coverage` zeigt ausschließlich belegte Auszugsbereiche und Lücken.
  `finance period` gibt Salden nur bei vollständiger Abdeckung und
  kontinuierlichen angrenzenden Auszügen aus; es interpoliert nichts.
- `finance recurring` gruppiert nur centgleiche monatliche Belastungen mit
  mindestens zwei Belegen. Aktiv/inaktiv, Folgemonatsfenster und
  Jahressumme sind Kandidaten/Prognosen, keine Vertrags- oder Zahlungsbeweise.
- `inventory plan` normalisiert höchstens drei Dezimalstellen ohne Rundung und
  schreibt nichts. Widersprüchliche Beobachtungen desselben Gegenstands und
  Tages werden vor einer Freigabe blockiert.
- `inventory apply` bindet Approval, Inventarrevision, konkrete Aktionen und
  Quellhashes. Der lokale Store ergänzt ausschließlich Ereignisse und Audit;
  eine aktuelle Sicht wird aus der Historie abgeleitet.
- `inventory needs` meldet Unterbestand und Ablaufdaten nur als
  prüfpflichtige Kandidaten. FolderHome bestellt nichts und behauptet keinen
  vollständigen Haushaltsbestand.
- `medication plan/apply` übernimmt nur dokumentierte Zeitpläne und bindet
  jede Version an Profil, Quelle, Hash, Zeilenevidenz, Revision und Approval.
- `medication day` erzeugt stabile Dosis-IDs ohne Write-on-read. Statuswerte
  unterscheiden bevorstehend, Bestätigung ausstehend und ausdrücklich
  bestätigt, ohne eine tatsächliche Einnahme zu erraten.
- `medication confirm` ergänzt genau ein idempotentes Einnahmeereignis nach
  State-Gate. Bestand, Kalender, Nachrichten und Erinnerungen bleiben
  unverändert; medizinische Richtigkeit wird nicht behauptet.
- `health dossier` liest erst nach lokaler Sensitivitätsfreigabe. Ein roter
  Providerbefund wird nur verarbeitet, wenn sämtliche roten Fundstellen
  ausschließlich Gesundheitsdaten betreffen; weitere rote Muster bleiben
  blockiert. Zeitlinie und Konflikte bleiben extraktiv und quellgebunden.
- `contracts cockpit` liest den gemeinsamen State erst nach
  Sensitivitätsfreigabe und verknüpft nur ausdrücklich konfigurierte Begriffe.
  Es ändert weder State noch Quelldateien und führt keinen Archivierungs-,
  Kontakt-, Kalender-, Bank- oder Zahlungsvorgang aus.
- `correspondence preview` liest Anfragedaten erst nach
  Sensitivitätsfreigabe. Nur einfache sichere Platzhalter sind erlaubt;
  `render` schreibt Markdown/TXT erst nach getrenntem Output-Gate als
  Never-overwrite-Batch. DOCX/ODT, Versand, Druck und Remote-Provider bleiben
  aus.
- `artifacts plan` ruft weder Office-Skills noch ai-media-editor auf und hält
  fehlende Runtime-/Rendergates sichtbar. Lokale Designtokens und SVG werden
  erst nach Sensitivitäts- und Output-Gate geschrieben; jede konkrete Karte
  braucht eine eigene visuelle Prüfung vor Druck oder Veröffentlichung.
- `mail ingest-plan` enthält nur Header- und optionalen Anhangsabruf. Ein
  abweichender oder veränderter Provider-Checkout blockiert; Verschieben,
  Löschen, Markieren und Senden sind keine Ingest-Operationen.
- Mailentwürfe binden aktive Kontakt-ID, Empfängeradresse,
  Korrespondenz-Vorschau-ID und Texthash. Versand benötigt eine exakte
  Freigabe und eine einmalige Ledger-Reservierung; ein echter SMTP-Transport
  ist noch nicht implementiert oder getestet.
- `notes guide` liest die gepinnte `llm-note`-Historie ohne Write-on-read und
  hält Fragen sowie Vorschläge strikt vom menschlich bestätigbaren Inhalt
  getrennt. Ein Remote-LLM wird in Phase 28 nicht aufgerufen.
- `notes apply` bindet Approval an Plan, Aktion, Inhaltshash und Store-Revision
  und hängt über die öffentliche `llm-note`-API genau eine Version an. Edit und
  Revert überschreiben oder löschen keine frühere Fassung.
- Dokument- und Kalenderreferenzen werden nur explizit übernommen. Profile
  ordnen die Notizen; allein das Betriebssystemkonto bleibt Sicherheitsgrenze.
- `tax receipt-plan` bindet einen Beleg an Dokumenthash, Profil, optional eine
  passende Finanzbuchung und den aktuellen Providerstore. Ein
  Kategorienkandidat bleibt ohne menschliche Bestätigung nicht ausführbar.
- `tax receipt-apply` schreibt über die öffentliche Provider-API genau einen
  bestätigten Beleg. `tax export` benötigt eine separate Freigabe und erzeugt
  nur eine neue private ZIP-Arbeitsunterlage; Steuerberatung, amtliches Format
  und Portalübermittlung sind ausgeschlossen.
- `briefing plan` liest lokale Wetter- und Nachrichtensnapshots nach
  Sensitivitätsfreigabe, markiert veraltete Daten und erzeugt deterministisches
  HTML nur im Speicher. Live-Connectoren bleiben sichtbar blockiert.
- `briefing render` und `briefing deliver` besitzen getrennte Approvals und
  Schreibgates. Die Desktopkopie muss exakt dem gerenderten Hash entsprechen;
  ein Scheduler wird nicht registriert.
- `notices inspect` übernimmt ausschließlich bekannte, ausdrücklich
  beschriftete Bescheidangaben und bindet sie an Zeile, Dokument-ID und
  Quellhash. Relative Fristtexte werden nicht umgerechnet; `notices render`
  schreibt nur neue Berichte und führt keine Rechtsprüfung oder Antwort aus.
- `drafts preview` hält Dokumentevidenz und bereitgestellte Angaben getrennt,
  erzwingt einen sichtbaren Entwurfshinweis und verwendet den vorhandenen
  Korrespondenzkern. `drafts render` benötigt eine exakte Inhaltsfreigabe;
  Leistungsprüfung, Rechtsprüfung und Versand sind nicht implementiert.
- `benefits check` verwendet einen datierten, unvollständigen Routingkatalog
  und lokale Nutzerangaben. Veraltete Quellen blockieren; passende Routen
  verweisen nur auf amtliche Vorchecks. Anspruch, Höhe, Antrag und Webaufruf
  bleiben ausgeschlossen.
- `legal providers` lädt keinen Rechtsprüfagenten, sondern qualifiziert nur
  den sauberen gepinnten `law-checker`-Checkout und dessen Registry.
  `legal compare` verarbeitet bereits beschaffte lokale Snapshots; Themen-
  Treffer sind ausschließlich `review_candidate`. Rechtswirkung,
  Betroffenheit, Fristen, Netzwerk und Benachrichtigung bleiben ausgeschlossen.
- OCR, externe LLM-Synthesen und reale Nutzerordner sind nicht Teil der
  bisherigen synthetischen Abnahme.
- Der Strands-Agent besitzt in der Wettbewerbsfassung genau zwei
  profilspezifische read-only Tools. Prompt, Antwort, Toolresultat, Turns,
  Toolaufrufe und Ausgabetokens sind hart begrenzt; der Fixture-Lauf bleibt
  ohne Netzwerk und Side-Effects.
- Gesundheits-, Rechts- und Finanzfunktionen sind als administrative
  Assistenz geplant, nicht als Diagnose oder verbindliche Beratung.
- OS-Konten bilden die Sicherheitsgrenze; Familienprofile sind nur
  Organisationsregeln innerhalb eines Kontos.

## Lizenz

FolderHome ist für eine Veröffentlichung unter MIT vorgesehen. Bis zur
ausdrücklichen Freigabe bleibt dieses Repository lokal und ohne Remote.
