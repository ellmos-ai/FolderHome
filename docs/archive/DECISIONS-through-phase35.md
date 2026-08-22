# DECISIONS.md — Architekturentscheidungen

## 2026-08-22: llm-note speichert Versionen, FolderHome führt den Menschen

### Kontext

Der vorhandene `llm-note`-Provider bietet eine kleine lokale SQLite-Ablage und
eine öffentliche Write-API, aber keine FolderHome-Profile, Referenzen,
Inhaltsfreigaben oder Versionsbeziehungen. Ein zweiter Notizstore würde den
Bestand unnötig duplizieren. Seine öffentliche Storeklasse initialisiert das
Schema bereits beim Lesen über die normale Objektkonstruktion.

### Entscheidung

FolderHome verwendet den exakt gepinnten `llm-note`-Checkout als einzige
schreibende Notizablage. Neue FolderHome-Verträge legen jede bestätigte
Fassung als eigenen Provider-Eintrag ab. Read-only Planung und Historie nutzen
einen schemafesten SQLite-Seam, damit kein Write-on-read entsteht. Ein
providerneutraler Guide liefert nur getrennte Fragen und Vorschläge; der
menschlich bestätigte Inhalt wird nie still ersetzt.

### Folgen

- Create, Edit und Revert ergänzen Versionen; es gibt kein Überschreiben oder
  Löschen.
- Plan, Aktion, Inhalt und vollständige Store-Revision benötigen eine exakte
  menschliche Freigabe.
- Dokument- und Kalenderreferenzen müssen ausdrücklich in der Anfrage stehen.
- Remote-LLMs und externe Synchronisierung bleiben eigene, in Phase 28
  geschlossene Gates.
- Familienprofile sind Organisationsmerkmale, keine Sicherheitskonten.
- Die bisherige Repositoryangabe wird auf den belegten kanonischen
  `doc-bricks/llm-note`-Pfad korrigiert.

## 2026-08-22: Kalenderconnectoren erweitern den Phase-17-Handoff

### Kontext

FolderHome besitzt bereits Terminkandidaten, Profilauflösung, lokalen
Kalenderstate und UpToday-ICS-Ausgabe. UpToday, Routinika und Google haben
unterschiedliche Verträge: Dateiübergabe, Bundle-Austausch und agentischer
Live-Handoff dürfen nicht als gleichwertiger Sync behandelt werden.

### Entscheidung

Phase 27 baut keinen zweiten Kalenderkern. Ein neuer providerneutraler
Connectorplan referenziert den vollständigen Phase-17-Handoff und übernimmt
dessen Regelprovenienz. UpToday-Erstellung wird an ICS delegiert, Routinika
bleibt ohne Live-Vertrag blockiert und Google bleibt ein separat
freizugebender Skill-Handoff. Nur ein synthetischer No-Network-Gateway wird
lokal ausgeführt.

### Folgen

- Konto und Anfrage müssen Profil, Backend und explizite Kalender-ID binden.
- Erstellen, Aktualisieren, Löschen und Erinnern sind getrennte Operationen.
- Update und Löschen benötigen eine bestehende Provider-Ereignisreferenz.
- Google-Payloads verwenden Solo-Teilnehmer, Offsetzeiten, blockierende
  Transparenz und explizite Reminder.
- `ready`, `review_required`, `delegated` und `blocked` bleiben sichtbar und
  behaupten keinen Live-Kalendereintrag.

## 2026-08-22: Mail lesen, mutieren und senden bleiben getrennte Fähigkeiten

### Kontext

Die vorhandene doc-bricks-Suite bietet IMAP-Dokumentabruf,
Rechnungsextraktion und Postfachbereinigung, aber keinen gekapselten
FolderHome-SMTP-Connector. Lokale Checkouts der zwei IMAP-Werkzeuge enthalten
zudem fremde Änderungen oder abweichende Revisionen.

### Entscheidung

FolderHome kopiert keinen Suite-Code. Ein neuer providerneutraler Vertrag
modelliert read-only Ingest, explizite Kontakt-/Korrespondenzbindung und
idempotenten Versand. UniversalDocsGrabber ist vorgesehener, aber derzeit
blockierter Ingest-Provider. UniversalMailCleaner bleibt wegen
Postfachmutationen vollständig getrennt. Phase 26 nimmt nur einen
synthetischen No-Network-Gateway ab.

### Folgen

- Konto-JSON enthält nur Secret-Referenzen, keine Zugangsdaten.
- Ein Ingest-Plan kann weder verschieben, löschen, markieren noch senden.
- Entwürfe entstehen nicht durch automatische Kontaktsuche, sondern durch
  exakte aktive Kontakt-ID und Empfängeradresse.
- Versand benötigt eine separate, hashgebundene Freigabe und ein
  At-most-once-Ledger.
- Ein echter IMAP-/SMTP-Lauf bleibt bis zu sauberem Providercheckout,
  Credential-Adapter und Nutzerfreigabe blockiert.

## 2026-08-21: FolderHome als neues Integrations-Repository

### Kontext

Der Hackathon-Beitrag soll vorhandene Kompetenzen wiederverwenden, ohne neuen
Wettbewerbscode und vorbestehenden Bestand zu vermischen.

### Entscheidung

`FolderHome` ist der Produktname, `folderhome` der Repository- und Paketname.
Der neue Kern lebt in `src/`, neuer Verbindungscode in `bridges/` und
vorbestehende Komponenten werden in `reused/` nur gepinnt referenziert.

### Folgen

- FCSA, HungryCall und Ringedingeding bleiben unveränderte Repositories.
- Manifeste werden zur prüfbaren Integrationsgrenze.
- Der Phase-1-Host führt nur synthetische Fähigkeiten aus.
- Spätere Veröffentlichung und Live-Aktionen benötigen neue Entscheidungen.

## 2026-08-21: Default deny für Side-Effects

Plugins müssen Fähigkeiten und Side-Effects vollständig deklarieren. Eine
Side-Effect-Fähigkeit ohne erfülltes Gate endet `blocked`; unbekannte Werte
machen bereits das Manifest ungültig.

## 2026-08-21: Nachvollziehbarer Laufvertrag

Jeder Lauf verwendet `ellmos.home-agent.run-report.v1`, eine stabile `run_id`,
eindeutige Aktions-IDs, Status, Provenienz, Gate-Status, Evidenz und optional
Undo-Metadaten. Berichtsdateien werden atomar geschrieben.

## 2026-08-21: Wettbewerbsname bleibt FolderHome

Während des Wettbewerbs wird das Produkt ausschließlich als `FolderHome`
geführt. Das aktuelle Repository erhält kein alternatives
Wettbewerbsbranding. Erst nach dem Wettbewerb kann dieser Stand eingefroren
oder reduziert und dann neu gebrandet werden; die volle Weiterentwicklung
soll anschließend in Sovereign integriert werden.

## 2026-08-21: Getrennte Dokumentprovider und schreibgeschützte Suche

`doc-services` verantwortet Extraktion und Datenschutzprüfung;
KnowledgeDigest verantwortet Index und Ranking. FolderHome hält Identität,
Provenienz und Nutzer-Usecases zusammen. Der KnowledgeDigest-Ingest wird nur
mit `archive=False` und ausdrücklichem Index-Gate ausgeführt. Da die
öffentliche Suchmethode des gepinnten Providers die Datenbank verändert,
liest eine schmale FolderHome-Bridge dessen versioniertes Schema ausschließlich
im SQLite-Modus `ro`/`immutable`. Diese Ausnahme ist gekapselt und wird bei
einem Schemawechsel fail-closed beendet.

## 2026-08-21: Neueste Fassung ist eine erklärte Heuristik

FolderHome ordnet Fassungen zuerst nach expliziten Formulierungen wie
„gültig ab“ oder „Vertragsstand“, danach nach einem Datum im Dateinamen und
erst zuletzt nach dem Dateisystem-Änderungsdatum. Basis, Evidenz und
Konfidenz werden ausgegeben. Diese Ordnung ist keine rechtliche Feststellung.

Ältere Fassungen werden nicht automatisch verschoben. FolderHome erzeugt
ungefreigte, reversible Vorschläge und lässt sie zusätzlich durch den echten
FCSA-Dry-Run bestätigen. Eine spätere Live-Ausführung benötigt weiterhin ein
eigenes Gate.

## 2026-08-21: Profile organisieren, aber autorisieren nicht

Personendateien wie `Lukas.json`, `Hanna.json` oder `Simon.json` dürfen eigene
Dokumentpräferenzen enthalten. Sie liegen jedoch innerhalb der bestehenden
Sicherheitsgrenze des Betriebssystemkontos und erzeugen keine getrennten
Zugriffsrechte.

Regeln werden in der festen Reihenfolge global, Bereich, Profil und
Profilbereich vererbt. Gleichrangige unterschiedliche Werte blockieren die
Auflösung. Löschregeln können nur deaktiviert, prüfpflichtig oder auf den
Papierkorb gerichtet sein; unwiderrufliches Löschen ist kein gültiger Wert.

## 2026-08-21: Aktionspläne sind keine Ausführungsfreigabe

Aufgelöste Profilregeln werden in ein eigenes Schema
`folderhome.document-policy-action-plan.v1` übersetzt. Jeder Schritt nennt
Regelquellen einschließlich überstimmter Regeln, Provider, Capability,
Dateisystemwirkung, Gate und Rückweg. Ein Plan gewährt niemals selbst den
Dateisystem-Gate.

Benennung und Sortierung werden sequenziell projiziert. Archivierung und
Papierkorb sind an FCSAs echte Dry-Run-Pipeline gebunden; Hard Delete bleibt
in der erzeugten Konfiguration ausdrücklich deaktiviert. Konvertierung wird
keinem ungeprüften Altmodul zugeschrieben und bleibt bis zur Bindung eines
eigenen gekapselten Providers `blocked`. Gleichzeitig fällige, konkurrierende
Sortier-, Archivierungs- oder Papierkorbziele erzeugen einen sichtbaren
Review-Konflikt statt einer impliziten Priorität.

## 2026-08-21: Transformation ist ein neuer gekapselter Kern

Der Providerabgleich ergab keinen unverändert wiederverwendbaren Baustein für
die gesamte Bündelanforderung. `doc-services` bleibt für Extraktion zuständig;
FCSA übernimmt erst später Originalbewegungen. MarkItDown erzeugt
Analyse-Markdown, `report-forge` ist wegen widersprüchlicher Versionsidentität
gesperrt und sein PDF-Prozessor ein Stub. `PDFtoPDFocr` wird nicht direkt
importiert, weil die vorhandene Merge-Funktion Einzeldateien verschiebt und
das Modul die GUI-Abhängigkeiten beim Import lädt.

Die Lücke wird daher als `folderhome.capabilities.document_transform`
gekapselt. V1 unterstützt TXT und PDF. Ein Plan enthält Quellhashes,
Behandlung und Verlustgrenze ohne Rohtext. Schreiben braucht einen expliziten
Gate, prüft Quellen erneut, ist atomar und überschreibt nie. PDF-Eingaben
bleiben seitengetreu; Bilder werden gerastert; extrahierter Text wird mit
sichtbarem Layoutverlust neu gesetzt. Die Originalbehandlung bleibt ein
separater FCSA-Schritt und wird erst nach einem verifizierten
Transformationsergebnis planbar.

## 2026-08-21: Typgruppen werden in einem ZIP statt in einem Arbeitsordner veröffentlicht

Die Anforderung „ein Dokument pro Typ“ wird als ein neues ZIP mit mehreren
Gruppendokumenten umgesetzt. Bilder und PDFs bleiben getrennte PDF-Gruppen;
TXT, Markdown und weitere extrahierbare Formate werden je Typ als Textbündel
ausgegeben. Unbekannte Formate bleiben gehasht im Manifest sichtbar.

Ein einziges ZIP vermeidet teilweise veröffentlichte Ausgabeverzeichnisse und
vereinfacht Undo auf das Löschen genau einer neu erzeugten Datei. Das Paket
wird vollständig im Speicher aufgebaut, erhält feste ZIP-Metadaten und wird
atomar ohne Überschreiben publiziert. Das Manifest enthält die Hashes aller
Quellen und internen Ausgaben; der Hash des ZIP selbst steht nur im externen
Resultat, da er innerhalb des ZIP selbst nicht widerspruchsfrei abbildbar ist.

## 2026-08-21: Ordnerbeobachtung lernt nur aus belegten Korrekturen

Snapshots speichern relative Pfade, SHA-256, Größe und Dateisystemzeit, aber
keinen Dokumentinhalt. Der Beobachtungszeitpunkt wird explizit übergeben;
Snapshot-Dateien benötigen ein State-Gate und werden unveränderlich ergänzt.

Eine Verschiebung wird nur bei einem eindeutigen, unveränderten Hashpaar
behauptet. Duplikate bleiben absichtlich mehrdeutig. Als Lernbeispiel zählt
ein Move nur dann, wenn ein früherer FolderHome-Ablagebeleg denselben Hash und
Ausgangspfad enthält. Das Ergebnis bleibt `candidate` mit
`automatic_promotion=false`; automatische Regeländerungen sind ausgeschlossen.

## 2026-08-21: Scanläufe verwenden eine unveränderliche Checkpoint-Historie

Beobachtete Ordner werden über `folderhome.watched-folders.v1` mit stabiler
ID, Quellroot, organisatorischem Profil, Bereich, Intervall, Rekursion und
Aktivstatus deklariert. FolderHome führt in Phase 10 keinen Scheduler ein;
ein explizit gestarteter Scan weist lediglich aus, ob das Intervall fällig ist.

Der letzte Zustand wird aus identitätsgeprüften Snapshot-Dateien bestimmt.
Eine überschreibbare Pointer-Datei wird bewusst vermieden. Vor einem neuen
Checkpoint prüft FolderHome die Historie erneut, damit konkurrierende
Änderungen fail-closed auffallen. Ohne State-Gate bleibt der gesamte Scanlauf
read-only; auch mit Gate werden weder Quelldokumente noch Profilregeln geändert.

## 2026-08-21: Einzeldatei-Ausführung trennt Planprovider und Executor

Eine Ausführungsfreigabe bindet sich an die SHA-256-ID des vollständigen
content-free Plans, den Quellhash und einen geordneten, lückenlosen Präfix
konkreter Aktions-IDs. Beim CLI-Aufruf wird der Plan aus Quelle und
Profilregeln erneut aufgebaut; eine zwischenzeitliche Inhalts- oder
Regeländerung erzeugt eine andere Plan-ID und entwertet die Freigabe.

FCSA bleibt für Klassifikation und echten Dry-Run zuständig, wird aber nicht
als Einzeldokument-Live-Executor ausgegeben. Sein öffentlicher Einstieg scannt
einen ganzen Ordner, schreibt Processing Memory und kann Kollisionsziele
umbenennen. FolderHome kapselt deshalb eine engere
`folderhome.filesystem-transaction`: Sie klassifiziert nicht, akzeptiert nur
einen bereits freigegebenen exakten Move, überschreibt nie und bricht bei
Cross-Volume-Zielen ab. Planprovider und tatsächlicher Executor werden im
Audit getrennt ausgewiesen.

Vor der ersten Dateiveränderung wird ein unveränderliches Intent geschrieben.
Der Abschlussbericht enthält einen Ablagebeleg und wird beim späteren Lesen
gegen dieses Intent geprüft. Undo benötigt eine neue Freigabe und den
unveränderten Zielhash; ein vorhandener Ursprung, ein geändertes Ziel oder ein
umgelenkter Auditpfad blockiert die Rückführung.

## 2026-08-21: Ein Aufräumlauf wird vor jeder Freigabe ordnerweit geprüft

FolderHome erzeugt für jede unterstützte Datei denselben bereits geprüften
Einzeldokumentplan. Erst danach werden alle Zwischen- und Endziele gemeinsam
betrachtet. Mehrere Dokumente mit demselben Ziel, ein Ziel auf der Quelle
eines anderen Dokuments oder ein bereits belegtes Ziel blockieren sämtliche
beteiligten Pläne. Dateireihenfolge oder automatische Umbenennung lösen diese
Konflikte nicht stillschweigend.

Eine Batchfreigabe darf bewusst nur eine Teilmenge auswählen. Sie bindet sich
an Batch-ID und je Dokument erneut an Dokument-ID, Quellhash, Plan-ID und
Aktionspräfix. Scheitert die Ausführung später, nutzt FolderHome die bereits
geschriebenen Einzelberichte für einen Rückweg in umgekehrter Reihenfolge.
Nur ein vollständig erfolgreicher Batch liefert aktive Ablagebelege; nach
erfolgreichem Rollback bleibt der Fehlerbericht als Audit erhalten.

## 2026-08-21: Routinen komponieren Scan und Batch ohne implizite Automatik

Ein Routinenplan bleibt vollständig read-only. Im Modus `changes` werden nur
bei erreichtem Watch-Intervall neue, inhaltlich geänderte oder eindeutig
verschobene Dateien an den ordnerweiten Cleanup-Plan übergeben. Reine
Metadatenänderungen bleiben sichtbar im Scan, lösen aber keine erneute
Dokumentverarbeitung aus. `full` ist ein ausdrücklich gewählter Vollmodus.

Die Ausführung verwendet weiterhin die eigenständige Batchfreigabe und
benötigt gleichzeitig Datei- und State-Gate. Vor Änderungen werden letzter
Checkpoint und vollständige Scan-ID erneut geprüft. Ein neuer Checkpoint wird
erst nach erfolgreichem Batch ergänzt. Scheitert dieser Abschluss, werden die
Dateiaktionen über die bestehenden Undo-Verträge zurückgeführt. Ein Ziel im
beobachteten Root ist ausgeschlossen, um Wiederaufnahmeschleifen zu
verhindern. Phase 13 registriert bewusst keinen Betriebssystem-Scheduler.

## 2026-08-21: Watch-Beobachtung und Routinenziel bleiben getrennte Verträge

`folderhome.watched-folders.v1` bleibt für Quelle, Profil, Bereich,
Rekursion, Intervall und Aktivstatus zuständig. Eine separate
`folderhome.routine-bindings.v1` ordnet einem Watch Zielwurzel und
`changes`-/`full`-Modus zu. So kann derselbe Watch auch ohne Aufräumroutine
rein beobachtet werden und ein Scheduler erhält keine impliziten
Dateiberechtigungen.

Die Queue plant alle aktiven Watches read-only und schreibt weder Checkpoint
noch Berichtdatei. Fehlende Bindings werden sichtbar blockiert. Zusätzlich
prüft sie Eingangsüberlappungen, Ziele in anderen beobachteten Eingängen und
gemeinsame Aktionsziele über Routinen hinweg. Sie registriert selbst keine
Betriebssystemaufgabe; dieser Schritt bleibt eine spätere, gesondert
freizugebende Adaptergrenze.

## 2026-08-21: Scheduler-Plan, Queue-Lauf und Installation sind drei Grenzen

Der Handoff erzeugt eine portable Argumentliste und Windows-Task-XML nur als
JSON-Plan. FolderHome ruft weder `schtasks` noch eine andere
Registrierungsschnittstelle auf. Das Artefakt weist deshalb explizit
`registration_performed=false` und `installation_supported=false` aus.

Ein headless Lauf ist davon getrennt. Er berechnet die Schedule-ID erneut,
lädt aktuelle Konfigurationen und führt ausschließlich die read-only Queue
aus. Ein enges Gate erlaubt einen schedule-spezifischen Lock und einen
append-only Laufbericht im FolderHome-State. Vorhandene Locks werden nicht
automatisch als verwaist interpretiert oder entfernt. Exitcodes 0, 10, 20 und
30 unterscheiden Leerlauf, Freigabebedarf, Blockierung und Parallel-/
Restlock. Eine spätere Installation bleibt eine eigene Nutzerentscheidung.

## 2026-08-22: Dokumentkontakte sind evidenzgebundene Kandidaten

Ein allgemeines Kontakt-CRUD aus dem BACH-Altbestand wird nicht erneut
extrahiert. Es besitzt weder Dokumenthash-Evidenz noch Plan-/Aktionsfreigaben
oder einen atomaren Wechselvertrag. FolderHome verwendet stattdessen die
bereits extrahierte doc-services-Bridge, Profile und Dokumentidentität und
kapselt den neuen Registerkern unter `capabilities/contact_registry`.

V1 interpretiert ausschließlich deklarativ gelabelte Zeilen. Das verhindert,
dass beliebiger Freitext still als Kontaktdatum gespeichert wird. Ein
Kandidat bindet seine normalisierten Felder an Dokument-ID, SHA-256, Pfad und
Zeilennummern. Ordnerweit konkurrierende neueste Kandidaten werden vor einer
Registeraktion fail-closed geprüft.

Die Datenschutzampel bewertet eine mögliche Weitergabe. `review_required`
kann deshalb nur mit einem eigenen Gate für die rein lokale Kontaktextraktion
verarbeitet werden; das Gate erteilt keine Netzwerk- oder Mailfreigabe.
`blocked` und `not_checked` bleiben unzulässig.

Ein neuer Ansprechpartner ersetzt den alten nie durch Löschen. Eine einzige
SQLite-Transaktion legt den neuen Datensatz an, markiert den bisherigen als
`deletion_candidate` und ergänzt ein append-only Ereignis. Approval-Dateien
sind an Plan-ID, Registerrevision und konkrete Aktionen gebunden; vor der
Transaktion werden Revision und Quellhashes erneut gelesen.

## 2026-08-22: Kalenderwahl wird wiederverwendet, Kalenderzugriff nicht behauptet

Der vorhandene `kalender`-Skill beschreibt bereits eine adaptive Backendwahl
zwischen lokalem Store, UpToday, Routinika und Google. Sein Core implementiert
jedoch nur lokal, ist nicht an eine Git-Revision gebunden und bietet direkte
Schreib-/Löschoperationen ohne FolderHome-Gates. FolderHome übernimmt daher
das Präferenzmodell als typisierte Konfiguration und Profilregel, nicht den
Core als Laufzeitadapter.

UpToday besitzt einen getesteten, lokalen ICS-Kanal. Die lose Kopplung über
eine neue ICS-Datei ist stabiler als ein Schreibzugriff auf das interne
SQLite-Schema. Phase 17 plant deshalb deterministische ICS-Handoffs mit
FolderHome-UID und Inhaltshash, ruft den Import aber nicht auf. Ein vorhandenes
Ziel oder eine Überlappung mit dem Dokumentroot blockiert.

Für Routinika wurde nur eine alte, ausdrücklich ungenutzte UpToday-Bridge
gefunden, die SQLite nicht read-only öffnet. Das Backend bleibt auswählbar,
damit kein stiller Fallback erfolgt, sein Plan ist aber `blocked`. Google
bleibt wegen Netzwerk- und Datenschutzgrenze ebenfalls blockiert.

Die lokale Ausführung verwendet einen eigenen Approval-Vertrag und zwei
gekapselte Capabilities. `folderhome_local` schreibt transaktional in einen
FolderHome-eigenen SQLite-Store. `uptoday_ics` publiziert ausschließlich neue,
hashgeprüfte ICS-Dateien und schreibt das Ergebnis in ein append-only Audit;
es ruft weder UpToday noch dessen Datenbank auf. Beide Pfade prüfen Revision
und Quellhash erneut. ICS benötigt zusätzlich zum State-Gate ein Output-Gate
und nimmt bei Teilfehlern nur eigene, unveränderte Dateien zurück.

## 2026-08-22: FindCall übernimmt das Muster, nicht das Restaurantmodell

HungryCall belegt bereits die entscheidende Orchestrierung: Kandidaten
vorfiltern und ordnen, seriell anfragen, strukturierte Resultate gegen harte
Grenzen prüfen und nach dem ersten Erfolg stoppen. Seine öffentlichen
Datentypen sind jedoch bewusst Gastronomie-, Bestell- und
Tischreservierungsmodelle. Arztpraxen oder Werkstätten als Restaurants
abzubilden wäre falsche Wiederverwendung.

FindCall kapselt deshalb einen neuen generischen Vertrag und weist HungryCall
als Musterquelle aus. Ringedingeding bleibt das ergänzende Plugin für
Mehrpersonen-Polls; seine Parallel-/Gruppenlogik wird nicht in eine
Anbieterkaskade umgedeutet. FolderHome prüft beide realen Checkouts und lädt
nur ihre lokalen Dry-Run-Einstiege.

Phase 18 führt ausschließlich explizite Fixtures aus. Kandidatennummern werden
vor jeder Serialisierung maskiert, Call-Status nicht zusammengelegt und
Notfall-/Diagnoseinhalte abgelehnt. Die einzige Autorität lautet
`inquiry_only`. Eine spätere echte Anfrage, Buchung oder Zusage braucht einen
separaten Live-Connector-, Datenschutz-, Kosten- und Approval-Vertrag; es
existiert dafür absichtlich kein CLI-Flag.

## 2026-08-22: Virtuelle Konten zeigen nur belegte Finanzzustände

Der extrahierte Steuer-Assistent belegt centgenaue lokale SQLite-Verarbeitung,
ist aber eine selbst kategorisierte Beleg-Arbeitsunterlage. Ein Bankauszug,
Kontostand oder Abo ist kein Steuerbeleg. FolderHome übernimmt deshalb das
Cent-/Privacy-Prinzip, nicht das steuerfachliche Schema. Ein bereits
extrahierter AboTracker oder Kontoauszugsparser war lokal nicht vorhanden;
die Lücke wird als `capabilities.finance_store` gekapselt.

V1 verlangt ein deklaratives Format mit ganzzahligen Cent, Zeitraum,
Anfangs-/Endsaldo und eindeutiger Buchungsreferenz. Freie Banklayouts werden
nicht geraten. Ein Auszug ist nur Kandidat, wenn seine Buchungssumme den
Endsaldo exakt erklärt. Angrenzende Auszüge müssen zudem dieselbe Saldo-Kette
fortsetzen; sonst blockiert der Plan.

Der Store importiert ausschließlich nach Plan-, Revisions-, Aktions-,
Quellhash- und State-Freigabe. Er ergänzt Daten und Audit, löscht nichts und
spricht mit keiner Bank. Abdeckung wird aus Zeiträumen berechnet. Ohne
lückenlose, kontinuierliche Kette gibt FolderHome keine Grenzsalden aus.

Eine centgleiche ungefähr monatliche Belastung wird nur als
`active_candidate` oder `inactive_candidate` bezeichnet. Das beweist weder
einen Vertrag noch eine Kündigung oder die nächste Abbuchung; Jahreswerte
sind reine Hochrechnungen aus den belegten Monatskosten.

## 2026-08-22: Das Artefaktstudio routet Spezialisten statt Renderer zu kopieren

Präsentationen, Tabellen, Word-Dokumente und Medien besitzen bereits eigene
Skills oder Module mit unterschiedlichen Qualitätsverträgen. Ein gemeinsamer
FolderHome-Renderer würde diese Regeln duplizieren und insbesondere
Inhaltsprüfung, Formeln, Office-Rendering, visuelle Abnahme und Medienrechte
verflachen. Phase 25 führt deshalb einen providerneutralen Artefaktplan ein.

Jede Artefaktart erhält genau einen ausgewiesenen Providerstatus. `blocked`
darf nicht durch eine ähnliche Systembibliothek umgangen werden;
`review_required` ist keine Fertigbehauptung. Der Plan ruft keinen Provider
auf. PPTX, Spreadsheets und DOCX bleiben an ihre vorhandenen Skills gebunden,
ODT bleibt ohne Renderer blockiert. ai-media-editor wird an Revision
`4e4c79d8c16a117bf69c0f72ad946575110a6b84` ausgewiesen, aber reale Medien,
Schnittstrategie und Ausgabe behalten getrennte Freigaben.

Nur der bislang fehlende, allgemein wiederverwendbare Designkern wird neu
gebaut. Er erzeugt kontrastgeprüfte JSON-/CSS-Tokens und eine escaped
SVG-Visitenkarte. Sensitivitäts- und Output-Gate sind getrennt; drei Dateien
werden niemals überschrieben und bei einem eigenen Teilfehler hashgebunden
zurückgerollt. Jede konkrete Karte benötigt vor Druck oder Veröffentlichung
eine erneute visuelle Prüfung.

## 2026-08-22: Korrespondenz trennt Vorschau, Ausgabe und Office-Handoff

Briefinhalte enthalten regelmäßig personenbezogene Daten und können später
rechtliche oder finanzielle Wirkung entfalten. Eine direkte Kopplung von
Dokumentfund, freier LLM-Formulierung, Office-Rendering und Versand würde
diese Wirkungen unsichtbar vermischen. Phase 24 führt deshalb einen eigenen,
providerneutralen Korrespondenzkern ein.

Anfrage, Vorlage und Design sind explizite Verträge. Die Designauflösung ist
deterministisch; freie fuzzy Zuordnung findet nicht statt. Vorlagen dürfen nur
einfache Variablennamen verwenden. Fehlende oder zusätzliche Variablen sowie
Python-Attribut-, Index-, Konvertierungs- und Formatsyntax blockieren.

Die erste Stufe ist eine read-only Vorschau nach Sensitivitätsfreigabe. Eine
zweite Freigabe erlaubt ausschließlich neue Markdown- und TXT-Dateien als
hashgeprüften Batch. Bestehende Ziele werden nie überschrieben; ein eigener
Teilfehler rollt nur selbst angelegte Dateien zurück. Versand, Druck und
Veröffentlichung sind keine impliziten Folgeschritte.

report-forge bleibt an Revision
`355acb5ff1abe41b384a0d1e3a00925e6ac86215` inventarisiert, wird aber wegen
Distribution `1.1.4` gegenüber Runtime `1.1.0` nicht aufgerufen. Ohne
vollständige visuelle Office-Abnahme wird auch das lokal vorhandene
python-docx nicht als fertige DOCX-Funktion ausgegeben. ODT besitzt keinen
revisionsgebundenen Renderer. Beide Formate bleiben sichtbare, nicht
ausgeführte Handoffs.

## 2026-08-22: Vertragscockpits verbinden nur explizit zugeordnete Evidenz

Dokumente, Kontakte, Buchungen und Termine besitzen bislang verschiedene,
fachlich sinnvolle Identitäten. Ähnliche Namen allein beweisen nicht, dass
eine Abbuchung oder ein Ansprechpartner zu einem bestimmten Vertrag gehört.
Ein impliziter fuzzy oder LLM-basierter Join würde aus Korrelation eine
Vertragsbehauptung machen.

Phase 23 führt deshalb einen expliziten Anfragevertrag ein. Er nennt
Dokumentensuche, Vertragsobjekt, Gegenparteibegriffe, Kalenderbegriffe,
Kontokennungen, Zeitraum und Archivierungspräferenz. Erst diese Zuordnung darf
die vorhandenen read-only Ansichten zusammensetzen. Fehlende oder mehrdeutige
Evidenz bleibt als Komponentenhinweis sichtbar.

Das Cockpit besitzt keinen eigenen Fachstore. Es verwendet Versionsanalyse,
Kontaktregister, wiederkehrende Kosten, Kalenderstore und Finanzabdeckung in
deren bestehenden Verträgen. Ältere Dokumente werden bei aktivierter
Präferenz nur als ungefreigte reversible Archivierungsvorschläge gezeigt.
Kontaktwechsel, Kalenderaktion, Zahlung, Bankzugriff und Vertragsstatus werden
nicht ausgeführt oder behauptet. Der CLI-End-to-End-Test hält den gemeinsamen
State bytegenau unverändert.

## 2026-08-22: Gesundheitsdossiers bleiben lokal, extraktiv und unvollständig

doc-services klassifiziert Gesundheitsbegriffe absichtlich ROT, weil seine
Ampel die Weitergabe an Dritte absichert. FolderHome benötigt diese Inhalte
jedoch für einen ausdrücklich gewählten lokalen Dossierlauf. Ein pauschales
Überstimmen von ROT würde zugleich Zugangsdaten, Bankkennungen oder private
Schlüssel freigeben und ist deshalb ausgeschlossen.

Nach dem lokalen Sensitivitäts-Gate wird ein roter Inhalt nur verarbeitet,
wenn sämtliche roten Fundzeilen des Providerberichts ausschließlich
`Gesundheitsdaten` betreffen. Jeder zusätzliche rote Befund blockiert die
inhaltliche Übernahme. Es gibt keinen Netzwerk- oder LLM-Aufruf.

Die Synthese bleibt extraktiv. Aussagen werden anhand eines expliziten
Dokumentdatums sortiert und mit Dokument-ID, Quellhash, Relativpfad und Zeile
belegt. Gleich bezeichnete dokumentierte Felder mit verschiedenen Werten
werden nicht aufgelöst, sondern als Konfliktkandidaten gezeigt. Zeitabstände
zwischen Quellen sind keine behaupteten Versorgungslücken. Undatierte,
zukünftige, blockierte und nicht lesbare Dateien bleiben sichtbar.

Markdown und JSON sind die kanonischen Phase-22-Ausgaben. Der optionale
Berichtshandoff ist nicht ausführend und blockiert report-forge solange dessen
Distribution `1.1.4`, die Runtime aber `1.1.0` meldet. Diagnose,
Therapieentscheidung und Vollständigkeitsbehauptung sind keine
Produktfunktionen dieses Dossiers.

## 2026-08-22: Der Wettbewerbsfahrplan umfasst 36 Phasen

Die zuvor rollierende Phasenzahl wird auf 36 Wettbewerbsphasen konkretisiert,
damit „Vollausbau“ einen überprüfbaren Umfang besitzt. Phasen 1 bis 22 sind
abgeschlossen, Phase 23 startet mit dem Versicherungs- und Vertragscockpit.
Die später geplante Integration in FolderHome-Sovereign liegt nach dem
Wettbewerb und ist keine zusätzliche FolderHome-Wettbewerbsphase.

## 2026-08-22: Medikamenteneinnahmen sind bestätigte Tatsachen, keine Empfehlungen

UpToday Health belegt die nützliche Trennung von Medikament, Zeitplan und
Einnahmeprotokoll. Der öffentliche `gesundheit`-Skill ergänzt die Grenze,
bereitgestellte Gesundheitsinformationen zu organisieren, ohne Diagnose oder
Therapieentscheidung. FolderHome weist beide Quellen aus, lädt aber keine
alte Runtime und kopiert keinen Quellcode.

Ein V1-Plan verwendet deshalb ausschließlich eng gelabelte, vom Menschen
bereitgestellte Angaben. Dosis, Einheit, Zeitpunkt, Zeitzone, Wochentage und
Gültigkeit werden zusammen mit Dokument-ID, Quellhash und Zeilenevidenz als
append-only Zeitplanversion gespeichert. Freitextangaben wie „bei Bedarf“
werden nicht in einen Einnahmezeitpunkt umgedeutet, sondern blockieren zur
Prüfung.

Die Tagesansicht ist eine reine Leseprojektion. Sie stellt einen geplanten
Zeitpunkt nicht als erfolgte Einnahme dar. Erst eine separate, an Planrevision
und stabile Dosis-ID gebundene Bestätigung erzeugt ein Einnahmeereignis. Ein
Bestandsbezug ist ebenfalls nur ein Hinweis; weder Bestandsmenge noch Kalender
werden automatisch verändert. Diagnose, Verordnung, Dosierungsentscheidung,
Erinnerung und medizinische Vollständigkeit bleiben ausdrücklich außerhalb
dieser Phase.

## 2026-08-22: Haushaltsbestand ist eine Ereignishistorie

UpToday enthält bereits ein lokales Vorratsmodell mit Artikeln, Bereichen,
Orten, Einheiten, Mindestbeständen und Einkaufsableitung. Diese Fachbegriffe
werden als Designreferenz an Revision `7582ca8` ausgewiesen. Der bestehende
Engine wird nicht geladen: Fließkommazahlen, globaler DB-Singleton, direkte
Bestandsupdates, Löschoperation und implizites Tagesdatum verletzen den
deterministischen FolderHome-Vertrag. Es wird kein UpToday-Quellcode kopiert.

FolderHome V1 liest deshalb ein enges, gelabeltes Beobachtungsformat über den
bereits gepinnten doc-services-Provider. Mengen besitzen höchstens drei
Nachkommastellen und werden ohne Rundung als ganzzahlige Tausendstel der
angegebenen Einheit gespeichert. Ein Gegenstand wird stabil aus Profil,
Bereich, Name und Einheit identifiziert; Ort, Menge, Mindestbestand und
Ablaufdatum gehören zur jeweiligen Beobachtung.

Der Inventarstore besitzt keine still überschriebene aktuelle Menge. Jede
freigegebene Bestandsaufnahme wird mit Dokument-ID, Hash, Zeilenevidenz und
Audit als neues Ereignis ergänzt. Die aktuelle Sicht ergibt sich aus der
neuesten belegten Beobachtung. Widersprüchliche Beobachtungen desselben Tages
blockieren; Plan, Approval, Revision, Aktionen, Quellhash und State-Gate
müssen vor dem atomaren Import übereinstimmen.

Unterbestand, abgelaufen und läuft-bald-ab sind ausschließlich
prüfpflichtige Kandidaten. Es gibt keine Bestellung, keinen
Lieferantenkontakt, keine automatische Löschung und kein Versprechen, dass
der erfasste Haushalt vollständig ist. Familienprofile ordnen Ansichten,
ändern aber nicht die Sicherheitsgrenze des Betriebssystemkontos.

## 2026-08-22: Der Steueragent bleibt Belegablage und private Arbeitsunterlage

Der gepinnte `steuer-assistent` besitzt eine kleine, getestete API für vom
Nutzer eingeordnete Werbungskostenbelege und einen ZIP-Export. Das ist eine
geeignete Wiederverwendungsgrenze; eine zusätzliche Steuerengine würde
dieselbe Ablage doppelt bauen.

FolderHome ergänzt nur fehlende Verbindungen zu Dokumentkatalog,
Finanzbuchung, Profil und Freigabe. Ein Kategorienkandidat bleibt sichtbar,
aber nicht ausführbar. Erst die menschlich bestätigte Eingabegruppe darf nach
exakter Plan-, Dokumenthash-, Providerstore- und Statebindung gespeichert
werden. Die Bestätigung ist ausdrücklich keine Aussage über steuerliche
Abziehbarkeit.

Weil der Provider kein Profilfeld besitzt, erhält jedes organisatorische
Profil einen eigenen Store. Diese Aufteilung trennt Arbeitsunterlagen, ändert
aber nicht die Sicherheitsgrenze: Sie bleibt das Betriebssystemkonto.

Der ZIP-Export ist eine private, nicht-amtliche Arbeitsunterlage und besitzt
ein eigenes Approval sowie State- und Output-Gate. Steuerberatung,
Steuerberechnung, ELSTER, ERiC, Finanzamtübermittlung, Netzwerk und Versand
werden weder über den Provider noch als FolderHome-Fallback angeboten.

## 2026-08-22: Der tägliche Brief beginnt mit lokalen Snapshots

Die Produktsuche fand keinen bereits extrahierten Wetter- oder
Newspaper-Provider. BACH enthält zwar Wetterdienst, Newspaper-Generator und
Daily Agent, koppelt sie aber an BACH-Datenbank, implizite Systemzeit,
festen Ort, Netzwerk, Edge sowie direkte Desktop- und Telegramwirkungen. Der
Gesamtcheckout ist zudem fremd verändert. Eine Runtime-Anbindung oder erneute
Extraktion würde die gewünschte Modulgrenze verletzen.

FolderHome definiert deshalb zuerst einen providerneutralen Snapshotvertrag.
Wetter und Meldungen müssen Quellen- und Abrufzeit tragen; das Briefing bindet
beide Dateien per Hash und verarbeitet nur explizite Kategorien. Veraltete
Daten werden nicht verworfen oder als aktuell ausgegeben, sondern bleiben als
prüfpflichtiger Offline-Fallback sichtbar.

Rendern und Desktopzustellung sind getrennte Aktionen. Eine Renderfreigabe
darf keine Desktopdatei erzeugen; eine Desktopfreigabe kopiert nur den exakt
gerenderten Hash und überschreibt nichts. Live-Connectoren und
Schedulerregistrierung bleiben offen, weil eine Einzelfreigabe keine
dauerhafte Netzwerk- oder Schreibvollmacht begründet.

## 2026-08-22: Bescheidverständnis bleibt von Rechtsprüfung getrennt

Der vorhandene law-checker formuliert bereits eine konservative erste
Orientierung mit amtlichen Quellen und Eskalation bei Fristen. Der geprüfte
lokale Checkout ist jedoch einen Commit hinter Upstream, fremd verändert und
besitzt kein hinreichend vollständiges allgemeines Sozialverwaltungs- und
Sozialgerichtsrechtskorpus für beliebige Bescheide. Ihn trotzdem auszuführen,
würde eine nicht belegte Rechtsprüfung suggerieren.

Phase 31 lädt law-checker deshalb nicht. FolderHome verwendet die
Vorsichtsmethodik nur als Designreferenz und baut eine fachlich kleinere
Dokumentenverständniskapsel. Sie übernimmt ausschließlich bekannte,
ausdrücklich beschriftete Felder und bindet jedes Ergebnis an Zeilennummer,
Dokument-ID und Quellhash. Fehlende oder widersprüchliche Einzelfelder bleiben
sichtbar.

Ein vom Menschen genanntes Zugangsdatum wird als Nutzerangabe markiert. Ein
ausdrücklich gedrucktes Fristdatum darf gegen einen expliziten
Analysezeitpunkt gezählt werden; diese Kalenderarithmetik ist keine
gesetzliche Fristberechnung. Relative Texte wie „innerhalb eines Monats“
werden nicht umgedeutet. Die Ausgabe sagt ausdrücklich, dass keine
Rechtsprüfung stattgefunden hat, und erzeugt weder Widerspruch noch Versand.

## 2026-08-22: Verwaltungsentwürfe verwenden den Briefkern und bleiben lokal

Phase 24 besitzt bereits die sichere Briefmechanik: Parteien, profilabhängige
Designauflösung, geprüfte Platzhalter, deterministische Vorschau,
Ausgabehashes und Never-overwrite. Phase 32 baut deshalb keinen zweiten
Renderer. Die neue Kapsel erzeugt eine streng gebundene
`CorrespondenceRequest` und übernimmt die vorhandene Vorschau und Ausgabe.

Der amtliche Gegencheck von § 84 SGG, § 36 SGB X und § 16 SGB I zeigt, dass
Frist, Form, Rechtsbehelf und zuständige Stelle kontextabhängige rechtliche
Folgen besitzen. FolderHome übernimmt diese Normen nicht als allgemeine
Entscheidungsregeln. Ein Widerspruchsentwurf wird nur zugelassen, wenn der
bereitgestellte Bescheid selbst `Widerspruch` nennt; Rechtzeitigkeit und
Zulässigkeit bleiben ungeprüft. Ein Antragsentwurf prüft weder
Leistungsberechtigung noch Zuständigkeit.

Nutzeraussagen heißen bis zur Ausgabe `user_provided`. Eine separate Approval
bindet den vollständig gelesenen Brief an beide Ausgabehashes und bestätigt
nur die lokale Ausgabe. Der sichtbare Entwurfshinweis ist ein erzwungener
Vorlagenplatzhalter. Es existiert kein Sende-Kommando; E-Mail, Portal, Druck
und Post bleiben getrennte spätere Nutzerentscheidungen.

## 2026-08-22: Leistungsprüfung wird an amtliche Lotsen übergeben

Der zentrale `foerderplaner` ist eine pädagogische Planungshilfe und kein
Sozialleistungsmodul. BACH enthält lediglich allgemeine alte Wikiartikel.
Ein lokaler Nachbau komplexer Anspruchs- und Höhenberechnungen wäre daher
Doppelbau ohne belastbare Aktualitäts- und Vollständigkeitsgrundlage.

Die Sozialplattform weist ihren eigenen Sozialleistungsfinder als
Orientierung aus. Bundesagentur und BMWSB bieten mit KiZ-Lotse und
Wohngeld-Plus-Rechner amtliche Vorchecks. Phase 33 modelliert deshalb nur
grobe lokale Routingkriterien und verweist anschließend bewusst auf diese
amtlichen Angebote. Persönliche Daten werden nicht automatisch übermittelt.

Der lokale Katalog muss `complete=false` bleiben. Jede Quelle trägt einen
Prüfzeitpunkt und einen Hash ihrer kurzen Evidenzzusammenfassung. Veraltete
Quellen blockieren. `routing_mismatch` ist ausdrücklich keine Ablehnung und
`official_handoff_recommended` kein Anspruch. Leistungsberechtigung, Höhe,
Antrag und Portalzugriff bleiben außerhalb des Vorchecks.

## 2026-08-22: Rechtsänderungen erzeugen Prüfkandidaten, keine Rechtsurteile

Der aktuelle saubere `law-checker`-Checkout ist als quellengebundener Skill,
Registry und Fetcher verifiziert. Er bietet jedoch keine stabile Python-API,
die FolderHome als automatische Einzelfallprüfung aufrufen könnte. Eine
Agentenantwort als Runtimevertrag auszugeben, würde Fähigkeiten und
Prüfabdeckung überzeichnen.

FolderHome bindet deshalb nur unveränderliche Provideridentität, Registry und
Quellenmetadaten an. Die neue Bridge verlangt eine saubere exakt gepinnte
Revision und startet weder Fetcher noch Rechtsagent. Ein registrierter
Gesetzesschlüssel kann einen Snapshot zusätzlich qualifizieren; fehlende oder
deaktivierte Schlüssel blockieren.

Der neue Monitor vergleicht bereits beschaffte, datierte Normabschnitte
technisch. Profil- und Vertragsbezug entsteht ausschließlich aus expliziten
`user_provided`-Themen. Auch bei einer Überschneidung bleibt das Ergebnis
`review_candidate` und `affected_determined=false`. Entwürfe erhalten einen
eigenen Status und werden nicht als verkündet oder geltend beschrieben.

Automatische Webbeschaffung, Rechtswirkung, Übergangsrecht,
Fristberechnung, Bescheidantwort und Benachrichtigung bleiben separate
Folgeschritte. Das ermöglicht spätere wiederverwendbare Provider, ohne einen
Textdiff in Rechtsberatung oder einen Tag-Treffer in persönliche
Betroffenheit umzudeuten.

## 2026-08-22: Die lokale GUI ist eine schmale Serviceoberfläche, kein zweiter Kern

Die 34 vorhandenen Phasen besitzen bereits gekapselte Application-Services
und eine breite CLI. Ein allgemeiner HTTP-Befehlsrouter oder frei übergebbare
Dateipfade würden deren Side-Effect-, Sensitivitäts- und Approval-Grenzen
unterlaufen. Phase 35 exponiert deshalb nur Status, Profile, Fähigkeiten,
Dokumentensuche und Themendossier über eine feste read-only Allowlist.

Die Standardbibliothek reicht für den Wettbewerbsumfang aus und vermeidet eine
zweite Web-Runtime. Der Listener entsteht nur nach explizitem Gate auf
`127.0.0.1`. Ein kurzlebiges Token, exakter Host, Same-Origin, CSP und harte
Requestgrenzen schützen die lokale Browsersitzung. Das Token ist eine
Prozesshürde, keine neue Identitätsverwaltung.

Familienprofile ordnen Regeln und Ergebnisse, trennen aber keine Daten
innerhalb desselben Betriebssystemkontos. Die GUI sagt diese Grenze sichtbar.
Reale Isolation entsteht weiterhin ausschließlich durch getrennte OS-Konten
und deren Dateirechte. Schreibende, rechtliche, medizinische und finanzielle
Aktionen bleiben in ihren getrennten Fachworkflows und werden nicht durch die
neue Oberfläche freigeschaltet.
