# Changelog

Alle nennenswerten Änderungen werden hier nach Keep-a-Changelog-Prinzipien
dokumentiert. Das Projekt verwendet Semantic Versioning.

## [Unreleased]

### Hinzugefügt

- Gemeinsame lokale `LocalApplication` mit expliziter read-only
  Handler-Allowlist für Status, Profile, Fähigkeiten, Dokumentensuche und
  Themendossier
- Dependency-freier `ThreadingHTTPServer` auf `127.0.0.1` hinter bewusstem
  Startgate sowie CLI `app plan` und `app serve`
- Kurzlebiges Sitzungstoken, exakte Host-/Origin-Prüfung, deaktiviertes CORS,
  Größen-/Schema-/Profilgrenzen und sanitisierte Providerfehler
- Responsive, eigenständige FolderHome-GUI mit lokaler Ablagelasche,
  paketierten Assets, CSP, Tastaturfokus und Reduced-Motion-Unterstützung
- Sichtbare Trennung zwischen Betriebssystemkonto als Sicherheitsgrenze und
  rein organisatorischen Familienprofilen
- Workflow `local-app` und validierter Skill `folderhome-local-app`
- Reale synthetische Desktop-/390-Pixel-Mobilabnahme ohne Überlauf,
  Konsolenfehler, fehlgeschlagene Requests oder Außenwirkung
- Phase-35-Abnahme mit 297 FolderHome-Tests, Ruff und Compileall

- Sauberer, exakt gepinnter `law-checker`-Checkout als read-only Registry-
  und Quellenprovider ohne behauptete Rechtsprüf-API
- Neue `LawCheckerBridge` für Git-, Paket-, Modul- und Registryidentität sowie
  aktive Gesetzesschlüssel ohne Import des Agentenworkflows oder Netzwerk
- Providerneutrale Rechtsquellen-, Interessen-, Änderungs-, Prüfkandidaten-
  und Ausgabeverträge mit vollständiger Datei- und Wortlauthashbindung
- Strikte Trennung von `legislative_proposal`, `promulgated` und
  `consolidated_current` sowie Allowlist amtlicher Produktivdomains
- Technischer Normabschnittsvergleich und ausschließlich explizite
  `user_provided`-Themenzuordnung als `review_candidate`
- CLI `legal providers`, `legal compare` und `legal render`, isolierter
  synthetischer Usecase und Skill `folderhome-legal-change-monitor`
- Phase-34-Abnahme mit 288 FolderHome-Tests, Ruff und Compileall

- Revisionsgenauer Negativabgleich vorhandener Förderbestände: pädagogischer
  `foerderplaner`, alte BACH-Wikiseiten und kein extrahierter
  Sozialleistungsprovider
- Amtlicher Quellengegencheck für Sozialleistungsfinder, KiZ-Lotse und
  Wohngeld-Plus-Rechner mit datierten, hashgebundenen Evidenzzusammenfassungen
- Fachlich getrenntes lokales Leistungsprofil mit ausschließlich
  `user_provided`-Fakten und vollständiger Datei-Hashbindung
- Providerneutraler `complete=false`-Routingkatalog für amtliche Information,
  amtlichen Vorcheck, grobe Kriterien und nicht modellierte Anforderungen
- Vier fail-closed Routingzustände für empfohlenen Handoff, fehlende Angaben,
  Mismatch und veraltete Quellen ohne Anspruchs- oder Ablehnungsbehauptung
- CLI `benefits check` und `benefits render`, synthetisches Profil, realer
  amtlicher Handoff-Katalog und validierter Skill
  `folderhome-benefit-screening`
- Phase-33-Abnahme mit 277 FolderHome-Tests, Ruff, Compileall, Skill-,
  Workflow-, Doku- und Umlautvalidierung
- Wiederverwendung des Phase-24-Korrespondenzstudios für Design,
  Vorlagenprüfung, Markdown-/TXT-Vorschau, Hashes und Never-overwrite statt
  eines zweiten Briefgenerators
- Gekapselte Verwaltungsentwurfsverträge für Widerspruch, Behördenantwort
  und Leistungsantrag mit Profil-, Empfänger-, Bescheid- und Quellhashbindung
- Getrennte Provenienz `document_evidence` und `user_provided` für gelesene
  Bescheidangaben, Nutzeraussagen und gewünschtes Ergebnis
- Widerspruchsentwurfs-Gate für ausdrücklich gelesenen Rechtsbehelf,
  eindeutige Behörde und übereinstimmenden Empfänger
- Sichtbarer `ENTWURF`-/Prüfhinweis in jeder Ausgabe sowie eigene boolesche,
  hashgebundene Inhaltsfreigabe vor lokalem Schreiben
- CLI `drafts preview` und `drafts render`, synthetische Widerspruchs-,
  Antwort- und Antragsvorlagen sowie validierter Skill
  `folderhome-administrative-drafts`
- Phase-32-Abnahme mit 270 FolderHome-Tests, Ruff, Compileall, Skill-,
  Workflow-, Doku- und Umlautvalidierung
- Revisionsgenauer Abgleich des zentralen `law-checker`-Skills und des lokalen
  `law-checker`-Checkouts; Rückstand, fremde Änderungen und unvollständiges
  allgemeines Sozialrechtskorpus sichtbar dokumentiert
- Providerneutrale Verträge für Bescheidanalyse, Feldevidenz, Konflikte und
  lokale Ausgabebelege mit Profil-, Zeit-, Dokument- und Quellhashbindung
- Strikte Extraktion ausdrücklich gelabelter Bescheid-, Behörden-,
  Entscheidungs-, Rechtsbehelfs- und Fristangaben über gepinntes doc-services
- Trennung von relativem Fristtext, ausdrücklich gedrucktem Fristdatum und
  rein rechnerischer Resttageanzeige ohne gesetzliche Fristberechnung
- Sichtbare fehlende Felder, Mehrdeutigkeiten und `review_required` statt
  stiller Auswahl oder rechtlicher Behauptung
- CLI `notices providers`, `notices inspect` und `notices render`,
  synthetischer Bescheidfall, Workflow und validierter Skill
  `folderhome-official-notices`
- Phase-31-Abnahme mit 264 FolderHome-Tests, Ruff, Compileall, Skill-,
  Workflow-, Doku- und Umlautvalidierung
- Revisionsgenauer Designabgleich von BACH-Wetterservice,
  Newspaper-Generator und Daily Agent auf Commit `9ff3df23…` ohne Runtimeimport
  aus dem fremd veränderten Monolithen
- Providerneutrale lokale Wetter- und Nachrichtensnapshots mit HTTPS-Quellen,
  Abrufzeitpunkten, Profil, Briefingdatum und expliziter Zeitzone
- Deterministische Altersprüfung mit sichtbaren `fresh`-/`stale`-Grenzen und
  prüfpflichtigem Fallback statt einer falschen Aktualitätsbehauptung
- Kategorieauswahl, Obergrenzen und deterministische Artikelsortierung ohne
  Rohinhalt, Webabruf oder LLM-Zusammenfassung
- Escaptes, responsives UTF-8-HTML mit Wetter, Meldungen, Quellen und
  Datenstandsgrenzen
- Getrennte Render- und Desktopapprovals mit Eingabe-, Plan-, HTML- und
  Zielbindung sowie Never-overwrite
- CLI `briefing providers`, `briefing plan`, `briefing render` und
  `briefing deliver`, synthetische Beispiele, Workflow und validierter Skill
  `folderhome-daily-briefing`
- Phase-30-Abnahme mit 257 FolderHome-Tests, Ruff, Compileall, Skill-,
  Workflow- und Dokuvalidierung sowie visueller HTML-Prüfung
- Revisionsgenaue Inventur des sauberen `steuer-assistent`-Checkouts auf
  Version `0.2.3`, Commit `5d39aeec…`, MIT und kanonischem `ellmos-ai`-Repository
- Gepinntes Komponentenmanifest für Belegerfassung und private
  Arbeitsunterlagen mit expliziten Schreibgates
- Providerneutrale Steuerbeleg-, Approval-, Bericht- und Exportverträge mit
  Dokument-, Finanz-, Profil- und Providerstore-Bindung
- Strikte Trennung von Kategorienkandidat und menschlich bestätigter
  Eingabegruppe; Vorschläge sind nicht ausführbar
- Profilgetrennte Providerstores innerhalb des gemeinsamen
  Betriebssystemkontos
- Read-only Planung sowie exakte Plan-, Aktions-, Store- und
  Dokumenthashprüfung vor dem Providerwrite
- Separates Export-Approval, State-Gate und Output-Gate für eine neue private
  ZIP-Arbeitsunterlage ohne amtliches Format
- CLI `tax providers`, `tax receipt-plan`, `tax receipt-apply`,
  `tax export-plan` und `tax export`, synthetisches Beispiel, Workflow und
  validierter Skill `folderhome-tax-workpaper`
- Phase-29-Abnahme mit 249 FolderHome-Tests, Ruff, Compileall, Skill- und
  Dokuvalidierung sowie 35/35 grünen Providertests
- Revisionsgenaue Inventur des sauberen `llm-note`-Checkouts auf Version
  `1.0.3`, Commit `b5fe59fc…`, MIT und kanonischem `doc-bricks`-Repository
- Gepinntes `llm-note`-Manifest mit getrennten read-/write-Fähigkeiten und
  korrigierter Provenienz
- Providerneutrale persönliche Notizverträge für Profil, Bereich, Notizbuch,
  menschliche Autorschaft, explizite Dokument-/Kalenderreferenzen und
  append-only Revisionen
- Strikte Trennung von Guide-Fragen und Vorschlägen gegenüber dem
  bestätigbaren menschlichen Inhalt
- Read-only SQLite-Seam ohne Write-on-read und freigegebener
  `NoteStore.write()`-Pfad ohne zweite Notizdatenbank
- Create, Edit und Revert als neue Versionen mit exakter Plan-, Aktions-,
  Inhalts- und Storebindung sowie Replay-Schutz
- CLI `notes providers`, `notes guide`, `notes apply`, `notes list` und
  `notes history`, synthetisches Beispiel, Workflow und validierter Skill
  `folderhome-personal-notes`
- Phase-28-Abnahme mit 241 FolderHome-Tests, Ruff, Compileall, Skill- und
  Dokuvalidierung sowie 19/19 grünen Providertests
- Revisionsgenaue Inventur von UpToday, Routinika und dem Google-Calendar-Skill
- Providerneutrale Kalenderkonten, Erinnerungen, Ereignispayloads, Routen,
  Operationsfreigaben und Provider-Ereignisreferenzen
- Wiederverwendung des vollständigen Phase-17-Handoffs einschließlich
  Profilregelquelle, Evidenz, Zeitzone, UID, lokalem Store und ICS-Ausgabe
- Explizite Trennung von `create`, `update`, `delete` und `remind`; Update und
  Löschen bleiben ohne vorhandene Providerreferenz blockiert
- Google-Handoff mit expliziter Kalender-ID, `attendees=[]`, Offsetzeiten,
  blockierender Transparenz und strukturierter Reminderkonfiguration
- Hashgebundene, aber blockierte Routinika-Bundle-Referenz statt behauptetem
  Live-Connector
- No-Network `SyntheticCalendarConnectorGateway` mit exakter Plan-/Aktions-
  und Operationsfreigabe sowie Idempotenzprüfung
- CLI `calendar connectors`, `calendar connector-plan` und
  `calendar connector-simulate`, synthetische Beispiele, Workflow und
  validierter Skill `folderhome-calendar-connectors`
- Phase-27-Abnahme mit 233 FolderHome-Tests, Ruff, Compileall, Skill- und
  Dokuvalidierung
- Providerneutrale Mailkonten, Ordner-, Nachrichten- und Anhangsreferenzen mit
  Secret-Referenzen statt eingebetteter Zugangsdaten
- Revisionsgenaue Inventur von MailProcessor, UniversalDocsGrabber,
  UniversalMailCleaner, UniversalInvoiceMail und dem extrahierten
  Messaging-Connector-Modul
- Read-only IMAP-Ingest-Plan mit getrennten Netzwerk- und
  Anhangs-Schreibfreigaben sowie fest leerer Postfachmutationsliste
- Explizite Entwurfsbindung an aktiven Kontakt, Empfängeradresse,
  Korrespondenz-Vorschau-ID und Texthash
- Exaktes Versandgate mit deterministischem Idempotenzschlüssel und lokalem
  SQLite-Reservierungsledger
- No-Network `SyntheticMailGateway`, der Abruf und genau einen simulierten
  Versand ohne echte E-Mail end-to-end belegt
- CLI `mail providers` und `mail ingest-plan`, synthetische Beispiele,
  Workflow und validierter Skill `folderhome-mail-assistant`
- Phase-26-Abnahme mit 225 FolderHome-Tests, Ruff, Compileall, Skill- und
  Dokuvalidierung
- Providerneutraler Office-/Medienplan für Präsentation, Tabelle, DOCX, ODT,
  Designset, Visitenkarte und Medien mit Status, Gründen und Gates
- Deklarierte Wiederverwendung der spezialisierten `pptx`, `academic-pptx`,
  `Spreadsheets`- und `documents`-Skills ohne kopierte Renderer
- Revisionsgebundener ai-media-editor-Handoff an
  `4e4c79d8c16a117bf69c0f72ad946575110a6b84` ohne Medienaufruf
- Fail-closed Status für fehlenden Spreadsheet-Workspace-Loader, fehlendes
  `soffice`, report-forge-Versionsdrift und fehlenden ODT-Renderer
- Designstudio mit strengem Schema, sicheren Schriftbezeichnungen und
  WCAG-Kontrastprüfung von mindestens 4,5:1
- Deterministische JSON-/CSS-Designtokens und escaped SVG-Visitenkarte
- Getrenntes Sensitivitäts- und Output-Gate sowie Drei-Dateien-
  Never-overwrite-Batch mit hashgebundenem Rollback
- CLI `artifacts plan`, `artifacts design-preview` und
  `artifacts design-render` samt synthetischem Beispiel
- Validierter agentischer Skill `folderhome-artifact-studio`
- Phase-25-Abnahme mit 218 FolderHome-Tests, Ruff, Compileall, Skill- und
  Dokuvalidierung sowie visueller Prüfung der synthetischen Karte
- Kontrollierte Briefdesigns mit deterministischer Vererbung über Standard,
  Bereich, Zweck, Profil und Profil-Zweck
- Sichere Briefvorlagen ohne Attribut-, Index-, Konvertierungs- oder
  Formatsyntax sowie exakte Prüfung fehlender und zusätzlicher Variablen
- Korrespondenzanfrage und read-only Vorschau mit Absender, Empfänger,
  Anlagen, Evidenzreferenzen, Designauflösung und Ausgabehashes
- Getrenntes Sensitivitäts- und Output-Gate sowie atomare Never-overwrite-
  Ausgabe für Markdown und TXT
- Sichtbare, nicht ausgeführte DOCX-/ODT-Handoffs mit begründeter
  Providerblockade statt falscher Formatbehauptung
- CLI `correspondence preview` und `correspondence render`, synthetische
  Kündigungsvorlage, Designbeispiele und wiederholbarer Workflow
- Gekapselte Module `contracts.correspondence` und
  `application.correspondence` für spätere agentische Wiederverwendung
- Phase-24-Abnahme mit 213 FolderHome-Tests, Ruff und Compileall
- Expliziter `folderhome.contract-cockpit-request.v1`-Join-Vertrag für
  Vertragsobjekt, Dokumentensuche, Gegenparteien, Kalenderbegriffe und Konten
- Read-only `folderhome.contract-cockpit.v1` über vorhandenen Dokument-,
  Kontakt-, Finanz- und Kalenderbausteinen
- Neueste und ältere Vertragsfassungen ohne Rohtext sowie konfigurierbare,
  ungefreigte Archivierungsvorschläge
- Aktuelle/frühere Kontakte, wiederkehrende Kostenkandidaten, zukünftige
  Termine und Kontoauszugslücken mit vorhandenen Evidenz-IDs
- Sichtbare fehlende oder mehrdeutige Komponenten statt erratener Verknüpfung
- CLI `contracts cockpit`, synthetischer Hyundai-i10-Fall und dokumentierter
  Vertragscockpit-Workflow
- Phase-23-Abnahme mit 208 FolderHome-Tests, Ruff und Compileall
- Revisionsgenauer Phase-22-Abgleich für doc-services, KnowledgeDigest,
  `gesundheit`, docs-analysis, report-forge und llm-note
- Providerneutrale Gesundheitsverträge für Quellen, Zeilenevidenz, Zeitlinie,
  direkte Feldkonflikte, Quellenabdeckung und Dossierbericht
- Explizites lokales Sensitivitäts-Gate mit eng begrenzter Gesundheitsdaten-
  Ausnahme für rote doc-services-Befunde
- Sichtbare Status für blockierte, nicht lesbare, undatierte und zukünftige
  Gesundheitsquellen
- Deterministische Markdown-/JSON-Synthese mit Never-overwrite und Ausgaben
  außerhalb des analysierten Quellordners
- Nicht ausführender DOCX-/ODT-Handoff-Vertrag, der den aktuellen
  report-forge-Versionsdrift blockiert
- CLI `health dossier`, synthetische Gesundheitsdokumente und dokumentierter
  Gesundheitsdossier-Workflow
- Phase-22-Abnahme mit 204 FolderHome-Tests, Ruff und Compileall
- Konkretisierter Wettbewerbsgesamtfahrplan mit 36 Phasen
- Deklarierte Wiederverwendung des UpToday-Health-Designs und des öffentlichen
  `gesundheit`-Skills ohne alte Runtime oder kopierten Quellcode
- Providerneutrale Medikamentenverträge für Plan, Zeitplanversion, Tagesdosis,
  Approval, Einnahmebestätigung, Ergebnis und Bestandsbezug
- Exakte Dosisnormalisierung in ganzzahlige Tausendstel ohne stille Rundung
- Revisionsgebundener, atomarer und append-only SQLite-Medikamentenstore
- Schreibfreie Tagesansicht mit stabilen Dosis-IDs, IANA-Zeitzone und
  Bestätigungsstatus
- CLI `medication plan`, `medication apply`, `medication day`,
  `medication confirm` und `medication history`
- Synthetischer Medikamentenplan und dokumentierter Einnahme-Workflow
- Phase-21-Abnahme mit 198 FolderHome-Tests, Ruff und Compileall
- Deklarierte UpToday-Design-Wiederverwendung an sauberer Revision `7582ca8`
  ohne Runtime-Import oder kopierten Quellcode
- Providerneutrale Inventarverträge für Beobachtung, Evidenz, Plan, Approval,
  Ereignis, Ergebnis und Bedarfskandidat
- Exakte Dezimalnormalisierung in ganzzahlige Tausendstel ohne stille Rundung
- Revisionsgebundener, atomarer und append-only SQLite-Inventarstore
- Dokumentgebundene Gegenstände nach Profil, Bereich, Ort und Einheit
- Aktuelle Bestandsansicht und vollständige Ereignishistorie
- Review-only Mindestbestands-, Ablauf- und Fehlmengenkandidaten
- CLI `inventory plan`, `inventory apply`, `inventory current`,
  `inventory history` und `inventory needs`
- Synthetischer Bestandsordner und dokumentierter Inventar-Workflow
- Phase-20-Abnahme mit 189 FolderHome-Tests, Ruff und Compileall
- Lokales FolderHome-Repository auf `phase1-foundation`
- FULL-Projektdokumentation aus dem geprüften `project-docs`-Template
- Wettbewerbs-Codekarte und Drittanbieter-Lizenzregister
- Phase-1-Ausführungsplan für Verträge, Manifeste, Audit und CLI
- Gemeinsame Verträge für Status, Plugins, Fähigkeiten, Evidenz, Gates, Undo,
  Entscheidungen, Aktionen und Laufberichte
- Fail-closed Manifest-Host mit Schema-, Pin-, Dry-Run-, Gate- und
  Eindeutigkeitsprüfung
- Atomare UTF-8-JSON-Berichte im Schema `ellmos.home-agent.run-report.v1`
- Synthetischer Run-Service für Erfolg, Blockierung, Fehler und Wiederaufnahme
- CLI für die Prüfung aller Manifeste und synthetische Berichtsläufe
- Testgetriebene Abnahme mit 22 Tests sowie Ruff-, Compile- und Doku-Prüfungen
- Gepinnte FCSA-Dry-Run-Bridge mit Versions-, Revisions- und Clean-Checkout-Prüfung
- Temporärer FCSA-Schattenzustand ohne produktive Dry-Run-Bestätigung
- Übersetzung von FCSA-Kategorien und Aktionsplänen in atomare FolderHome-Laufberichte
- CLI-Befehl `run fcsa-plan` und vollständig synthetisches Dokumentenbeispiel
- Providertext-Normalisierung für echte deutsche Umlaute im Endnutzerbericht
- Phase-2-Abnahme mit 27 FolderHome- und 63 FCSA-Tests
- Providerneutraler `DocumentRecord` mit stabiler ID, Inhalts-Hash,
  Extraktionsherkunft, Datenschutzampel und explizitem Indexstatus
- Gepinnte Bridges für doc-services und KnowledgeDigest mit sauberer
  Checkout-, Versions- und Revisionsprüfung
- OCR-freie Extraktion ohne Lernschreibzugriff und KnowledgeDigest-Ingest mit
  festem `archive=False`
- Schreibgeschützte KnowledgeDigest-Suche über einen versionsgeprüften
  SQLite-`ro`/`immutable`-Seam
- Natürliche deutsche Dokumentensuche und lokale Themendossiers mit sichtbarer
  Abdeckungsgrenze
- Deterministische Ordnerberichte mit Dokumentname und höchstens drei
  belegten Sätzen; sensible Inhalte werden nicht übernommen
- CLI-Befehle `documents ingest`, `documents search` und `documents dossier`
  einschließlich explizitem Index-Gate und synthetischer End-to-End-Abnahme
- Phase-3-Abnahme mit 50 FolderHome-Tests, Ruff und Compileall
- Atomarer FolderHome-Dokumentkatalog mit Metadaten, Provenienz und ohne
  extrahierten Rohtext
- Dokumentfamilien- und Versionsverträge mit erklärbarer Datumsbasis und
  konservativer Konfidenz
- Satzbasierter Versionsvergleich ohne semantische, rechtliche oder fachliche
  Interpretation
- CLI-Befehl `documents versions` für Fragen wie „Was ist meine neueste
  KFZ-Versicherung für meinen Hyundai i10?“
- Ungefreigte, reversible Archivierungsvorschläge für ältere Fassungen
- Validierung jedes Vorschlags durch die echte gepinnte FCSA-Dry-Run-Pipeline
  mit `duplicate_check` und `move`
- Phase-4-Abnahme mit 59 FolderHome-Tests, Ruff und Compileall
- Typisierte Profilregeln für Benennung, Archivierung, Löschen, Zielformat,
  Originalbehandlung, Sortierziel und Scanintervall
- Feste Vererbung global → Bereich → Profil → Profilbereich mit fail-closed
  Konflikterkennung auf gleicher Stufe
- Organisatorische Profile mit explizitem OS-Konto-Hinweis statt behaupteter
  Nutzerrechte innerhalb eines gemeinsamen Kontos
- Vertragliches Verbot von `hard_delete`; nur deaktivierte, prüfpflichtige
  oder Papierkorb-Löschregeln sind zulässig
- CLI-Befehle `profiles validate` und `profiles resolve` sowie synthetische
  Beispielprofile für Lukas, Hanna und Simon
- Phase-5-Abnahme mit 64 FolderHome-Tests, Ruff und Compileall
- Providerneutraler Dokumentaktionsplan mit Benennungs-, Sortier-,
  Konvertierungs-, Original-, Archivierungs-, Papierkorb- und Review-Schritten
- Vollständige Regelprovenienz je Aktion einschließlich überstimmter Regeln,
  explizitem Dateisystem-Gate und Undo-Beschreibung
- Sichere Benennungsvorlagen mit festen Platzhaltern, Pfadschutz und
  automatischem Erhalt der Dateiendung, wenn `{ext}` nicht verwendet wird
- Deterministische Fristprüfung gegen einen expliziten `as_of`-Stichtag sowie
  fail-closed Zielkonflikte ohne stille Aktionspriorität
- Echte FCSA-Dry-Run-Bestätigung für reversible Archivierung und
  Papierkorbablage bei fest deaktiviertem Hard Delete
- CLI-Befehl `documents plan` mit gepinnter read-only Extraktion, Profil- und
  Regelauflösung sowie optionaler neuer JSON-Ausgabedatei
- Phase-6-Abnahme mit 77 FolderHome-Tests, Ruff und Compileall
- Belegter Transformationsprovider-Abgleich für doc-services, MarkItDown,
  report-forge, PDFtoPDFocr, FCSA, Batch-Skill und ai-media-editor
- Wiederverwendbare Capability `folderhome.capabilities.document_transform`
  mit getrenntem Application Service und providerneutralen Verträgen
- Deterministische UTF-8-TXT-Bündel mit relativen Quellüberschriften
- PDF-Bündel aus erhaltenen PDF-Seiten, lokal gerasterten Bildern und
  layoutverlustbehaftet neu gesetztem Extraktionstext
- Qualitäts-, Datenschutz- und Verluststatus pro Bündelquelle ohne Rohtext im
  Plan sowie reproduzierbare PDF-Ausgabehashes
- Erneute Quellhashprüfung, expliziter Output-Gate, atomare Veröffentlichung
  und striktes Never-overwrite für jede Transformation
- Verifiziertes `DocumentBundleResult` als einzige Freischaltgrundlage für
  die weiterhin ungefreigte Originalbehandlung
- CLI-Befehl `documents bundle` für reines Planen oder ausdrücklich
  freigegebene TXT-/PDF-Ausgabe
- Phase-7-Abnahme mit 87 FolderHome-Tests, Ruff und Compileall
- Typgruppenverträge für Bilder, PDF, TXT, Markdown und weitere durch
  doc-services extrahierbare Dateiendungen
- Sichtbare `unsupported`-Einträge mit Relativpfad, Größe, Endung, SHA-256 und
  Begründung statt stillem Überspringen
- Wiederverwendung des Transformationskerns für genau ein Dokument pro Gruppe
- Deterministisches `manifest.json` mit Quellmetadaten, Verlusthinweisen und
  Hashes aller internen Ausgaben
- Atomare, nie überschreibende ZIP-Veröffentlichung ohne persistenten
  Zwischenordner und mit stabilen ZIP-Metadaten
- CLI-Befehl `documents package` mit reinem Planmodus und explizitem
  `--approve-output-write`-Gate
- Phase-8-Abnahme mit 92 FolderHome-Tests, Ruff und Compileall
- Inhaltsfreie, deterministisch identifizierte Ordner-Snapshots mit relativen
  Pfaden, SHA-256, Größe, `mtime_ns` und sichtbaren Symlink-Auslassungen
- Explizites State-Gate und atomare Never-overwrite-Historie für Snapshots
- Erklärbarer Snapshot-Diff für neue, entfernte, inhaltlich geänderte und nur
  in Metadaten geänderte Dateien
- Konservative Move-Erkennung ausschließlich für eindeutige
  Eins-zu-eins-Hashpaare; mehrdeutige Duplikate erzeugen keinen Move-Claim
- Lernkandidaten aus Nutzerkorrekturen nur bei passendem früherem
  Ablagebeleg und immer mit `automatic_promotion=false`
- CLI-Befehle `folders snapshot`, `folders diff` und `folders learning`
- Phase-9-Abnahme mit 98 FolderHome-Tests, Ruff und Compileall
- Striktes Schema `folderhome.watched-folders.v1` für aktivierbare lokale
  Beobachtungen mit Profil-, Bereichs-, Rekursions- und Intervallbezug
- Wiederholbarer Scanlauf gegen den letzten identitätsgeprüften Checkpoint
- Auditbericht mit Intervallfälligkeit, inhaltsfreiem Snapshot, Diff,
  Lernkandidaten und explizitem State-Gate
- Fail-closed Verhalten bei deaktivierten Beobachtungen, nicht monotonen
  Zeitpunkten, Rekursionswechseln und konkurrierenden Checkpoint-Änderungen
- CLI-Befehl `folders scan` sowie synthetisches Beobachtungsprofil
- Phase-10-Abnahme mit 104 FolderHome-Tests, Ruff und Compileall
- Deterministische `plan_id` über alle serialisierten, rohtextfreien Felder
  eines Dokumentaktionsplans
- Plan-, Quellhash- und Aktions-ID-gebundene Ausführungsfreigabe für einen
  lückenlosen Rename-/Move-Präfix
- Wiederverwendbarer Same-Volume-Dateitransaktionskern mit Zielhashprüfung,
  Symlink-Schutz und striktem Never-overwrite ohne stillen Fallback
- Append-only Intent, Abschlussbericht und Ablagebeleg mit getrennter
  Provenienz von Planprovider und tatsächlichem Executor
- Eigene Undo-Freigabe gegen Ausführungs-ID und unveränderten Zielhash sowie
  Rückweg ohne Überschreiben
- Audit-Readback gegen das frühere Intent, sodass manipulierte Zielpfade
  fail-closed blockieren
- CLI-Befehle `documents execute` und `documents undo`
- Phase-11-Abnahme mit 111 FolderHome-Tests, Ruff und Compileall
- Deterministischer `folderhome.folder-cleanup-plan.v1` für einen ganzen
  verschachtelten Quellordner ohne Rohtext oder implizite Dateiveränderung
- Sichtbare `skipped`-/`failed`-Einträge für Symlinks, unbekannte Formate und
  Extraktionsfehler statt stillem Weglassen
- Ordnerweite Konfliktprüfung für doppelte Ziele, bestehende Ziele und Ziele,
  die Quellen anderer Dokumentpläne belegen
- Selektive Batchfreigabe je Dokument-ID, Quellhash, Plan-ID und Aktionspräfix
- Batch-Intent und Abschlussbericht sowie automatische Rückführung bereits
  ausgeführter Dokumente nach einem späteren Teilfehler
- CLI-Befehle `folders cleanup-plan` und `folders cleanup-execute`
- Phase-12-Abnahme mit 117 FolderHome-Tests, Ruff und Compileall
- Read-only Vertrag `folderhome.folder-routine-plan.v1`, der Watch,
  Checkpoint, Fälligkeit und gefilterten Cleanup-Plan verbindet
- Änderungsmodus für fällige neue, inhaltlich geänderte und eindeutig
  verschobene Dateien sowie ausdrücklicher Vollmodus für den Gesamtbestand
- Erwartete-Checkpoint-Prüfung vor Routinenaktionen und vor dem anschließenden
  unveränderlichen Checkpoint
- Gemeinsames Datei- und State-Gate, Routine-Intent und Abschlussbericht sowie
  automatisches Datei-Undo bei gescheitertem Checkpoint
- Schutz vor Routinenzielen innerhalb des beobachteten Eingangsordners
- CLI-Befehle `folders routine-plan` und `folders routine-execute`
- Phase-13-Abnahme mit 124 FolderHome-Tests, Ruff und Compileall
- Deklaratives Schema `folderhome.routine-bindings.v1` für Zielwurzel,
  `changes`-/`full`-Modus und Aktivstatus pro Watch
- Deterministische `folderhome.folder-routine-queue.v1` für alle aktiven
  Watches mit `ready`, `not_due`, `empty` und `blocked`
- Sichtbare Blockierung fehlender/deaktivierter Bindings und fail-closed
  Ablehnung mehrfacher oder auf unbekannte Watches gerichteter Bindings
- Cross-Watch-Prüfung für überlappende Eingänge, Ziele in einem anderen
  beobachteten Eingang und gemeinsame Aktionsziele
- CLI-Befehl `folders routine-queue` ohne Schreib-, Approval- oder
  Scheduler-Installationsoption
- Phase-14-Abnahme mit 128 FolderHome-Tests, Ruff und Compileall
- Deterministischer `folderhome.scheduler-handoff-plan.v1` mit portabler
  Argumentliste und nicht registriertem Windows-Task-XML
- Least-Privilege-/`IgnoreNew`-/Laufzeitgrenzen im geplanten Windows-Artefakt
  ohne Installations- oder Registrierungsbefehl
- Headless `scheduler run` mit neu berechneter Schedule-ID, explizitem
  Scheduler-State-Gate und aktuellem Konfigurations-Readback
- Schedule-spezifischer atomarer Lock ausschließlich im operativen State;
  bestehende Locks bleiben fail-closed unangetastet
- Append-only `folderhome.scheduler-run-report.v1` ohne Dokument- oder
  Checkpoint-Side-Effects
- Eindeutige Exitcodes für `idle`, `attention`, `blocked` und
  `already_running`
- CLI-Befehle `scheduler plan` und `scheduler run`
- Phase-15-Abnahme mit 133 FolderHome-Tests, Ruff und Compileall
- Providerneutrale Kontaktverträge mit Dokument-ID, Quellhash, Zeilenevidenz,
  Profil, Bereich, Zweck, Objektbezug und normalisierten Kontaktkanälen
- Eigene Freigabe für rein lokale sensible Kontaktextraktion bei
  `review_required`; `blocked` und `not_checked` bleiben gesperrt
- Ordnerweite Auswahl des eindeutig neuesten Kontaktkandidaten und
  fail-closed Blockierung widersprüchlicher Kontakte mit gleichem Datum
- Revisionsgebundene `create`-/`replace`-Pläne mit erneuter Quellhashprüfung,
  Approval-Datei und explizitem State-Gate
- Gekapseltes SQLite-Kontaktregister mit read-only Abfrage, atomarem Wechsel,
  append-only Ereignissen und ohne automatische Löschoperation
- CLI-Befehle `contacts plan`, `contacts apply` und `contacts list` sowie
  synthetische End-to-End-Abnahme für die Zuständigkeit am Hyundai i10
- Phase-16-Abnahme mit 146 FolderHome-Tests, Ruff und Compileall
- Wiederverwendungsinventur für den Kalender-Skill 0.1.0, UpToday-ICS,
  die ungenutzte RoutineMaster-Bridge und den fachlich getrennten TerminPilot
- Profilregeln `calendar.backend` und `calendar.timezone` sowie
  `folderhome.calendar-config.v1` mit UpToday-ICS-Beispielfallback
- Evidenzgebundene Terminkandidaten aus expliziten Labels mit stabiler UID,
  IANA-Zeitzone und ehrlicher Nichtvollständigkeitskennzeichnung
- Read-only `folderhome.calendar-handoff-plan.v1` für lokalen Kalender oder
  deterministische ICS-Ziele; Routinika und Google bleiben sichtbar blockiert
- CLI-Befehl `calendar plan` und synthetische End-to-End-Abnahme ohne Datei-,
  Kalender-, UpToday- oder Connectoränderung
- Revisionsgebundene Kalenderfreigabe mit getrennten State- und Output-Gates
- Wiederverwendbarer lokaler SQLite-Kalenderstore mit transaktionalen
  Ereignissen, append-only Audit und ohne Löschoperation
- Wiederverwendbarer ICS-Publisher mit Quell-/Inhaltshashprüfung,
  Never-overwrite und hashgebundenem Rollback bei Batchfehlern
- CLI-Befehle `calendar apply` und `calendar list`; UpToday wird nur per neuer
  ICS-Datei beliefert und nicht direkt aufgerufen
- Phase-17-Abnahme mit 159 FolderHome-Tests, Ruff und Compileall
- Gepinnte lokale Plugin-Probes für HungryCall `DryRunCallClient` und
  Ringedingeding `FixtureTransport` ohne Live-Konstruktion
- Gekapselter providerneutraler FindCall-Kern für administrative Termin- und
  Angebotsanfragen mit serieller Kaskade und frühem Stopp
- Deterministische Leistungs-/Entfernungsfilterung und Reihenfolge nach
  Priorität, Distanz und Kandidaten-ID
- Maskierte E.164-Rufnummern, erhaltene terminale Call-Status und striktes
  `inquiry_only` ohne Buchung oder Zusage
- Lokale Fixture-Auswertung für Zeitfenster, exakte Preise und Preisobergrenzen
- CLI-Befehle `findcall plugins`, `findcall plan` und `findcall simulate`
- Phase-18-Abnahme mit 170 FolderHome-Tests, Ruff und Compileall
- Evidenzgebundene Kontoauszugsverträge mit ganzzahligen Centbeträgen,
  eindeutigen Buchungsreferenzen und strikter Saldoarithmetik
- Wiederverwendbarer lokaler `finance_store` für Konten, Auszüge, Buchungen
  und append-only Audit ohne Bank- oder Löschschnittstelle
- Revisions-/Approval-/Quellhashgebundener atomarer Finanzimport
- Fail-closed Kontinuitätsprüfung angrenzender Auszugssalden
- Abdeckungs- und Periodenberichte mit sichtbaren Lücken und Salden nur bei
  lückenlos belegter Kette
- Konservative monatliche Kostenkandidaten mit Transaktionsevidenz,
  Monats-/Jahressummen und Folgemonatsfenster
- CLI-Befehle `finance plan`, `apply`, `transactions`, `coverage`, `period`
  und `recurring`
- Phase-19-Abnahme mit 179 FolderHome-Tests, Ruff und Compileall

### Sicherheitsgrenzen

- Kein Remote, Push, Release oder öffentlicher Upload
- Keine ungefreigten Datei-, Netzwerk- oder Telefonaktionen; Live-Abnahmen
  der Phase 11 verwenden ausschließlich synthetische temporäre Ordner
- FCSA-Live-Ausführung bleibt trotz geplantem Dateisystembericht gesperrt
- Dokumentquellen bleiben unverändert; lokaler Indexschreibzugriff ist ohne
  `--approve-index-write` gesperrt
- OCR, externe LLM-Synthesen und formatierte report-forge-Ausgabe bleiben
  gesonderte Erweiterungen
- Versionsaussagen werden bei geändertem Katalogdokument blockiert; kein
  Archivierungsvorschlag wird live ausgeführt
- Dokumentaktionspläne verändern keine Quellen oder Zielordner; ein fehlender
  Konvertierungsprovider und konkurrierende Ziele bleiben sichtbar blockiert
- Transformationen verändern keine Originale; OCR bleibt deaktiviert und
  Ausgaben außerhalb von TXT/PDF bleiben ohne geprüften Provider blockiert
- Ordnerbeobachtung schreibt ohne State-Gate nichts, speichert keinen
  Dokumentrohtext und verändert weder Quellen noch Profilregeln
- Scanläufe führen keinen Scheduler und keine Dateiaktion aus; ein Intervall
  wird nur ausgewertet und ein Checkpoint nur nach enger Freigabe ergänzt
- Die Einzeldateiausführung unterstützt keinen Cross-Volume-Fallback, kein
  Überschreiben, keinen Papierkorb und keine automatische Regelübernahme
- Ein Batch führt konfliktbehaftete Dokumente nicht aus und aktiviert nach
  einem erfolgreichen Rollback keine Ablagebelege
- Routinen registrieren keinen Scheduler und führen ohne exakte Batch-,
  Datei- und State-Freigabe keine Datei- oder Checkpointaktion aus
- Die Mehrfach-Watch-Queue deklariert `side_effects=[]`, verändert State und
  Ziele nicht und meldet `scheduler_registered=false`
- Der Scheduler-Handoff registriert nichts; der Runner schreibt nur nach
  Gate eigenen Lock und Laufbericht und verändert weder Dokumente noch
  Checkpoints
