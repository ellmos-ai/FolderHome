# Feature-Analyse: FolderHome

[English](./Feature_Analyse_FolderHome.md) | **Deutsch**

**Version:** 0.36  
**Stand:** 2026-08-22  
**Wettbewerbsname:** FolderHome

FolderHome ist ein lokaler Dokument- und Assistenzservice-Agent. Der neue
Wettbewerbskern verbindet deklarierte Bestandsmodule, kapselt neue
Alltagsfähigkeiten und führt natürliche Dokumentanfragen über einen echten,
endlich begrenzten Strands-Agenten aus.

## Statuslegende

- **Lokal umgesetzt:** ausführbarer FolderHome-Code mit automatisiertem
  Erfolgs- und Fail-closed-Nachweis.
- **Handoff:** geprüfter Plan oder Providergrenze, aber bewusst kein
  behaupteter Live-Dienst.
- **Teilweise:** der sichere Kern ist vorhanden; ein gewünschter Renderer,
  Connector, OCR-/LLM-Provider oder eine fachliche Entscheidung bleibt offen.
- **Außerhalb:** nur mit späterer Produktentscheidung oder externer Freigabe.

## Featuredeckung

| Gewünschter Bereich | Stand | Umsetzung und ehrliche Grenze |
|---|---|---|
| Dokumente einsammeln | Lokal umgesetzt | Gepinnter doc-services-Ingest, Datenschutzgate, lokaler Index; Quelldateien bleiben unverändert |
| Foto-/PDF-OCR | Teilweise | Providergrenze ist vorbereitet; OCR realer Fotos wurde im Wettbewerbsnachweis nicht ausgeführt |
| Natürliche Dokumentensuche | Lokal umgesetzt | Schreibgeschützte Suche, unter anderem „Ich suche nach einem Dokument, in dem …“ |
| Verstreute Themen finden | Lokal umgesetzt | Evidenzgebundenes Themendossier, etwa zu Krankenversicherung, mit sichtbarer Abdeckung |
| Ordnerzusammenfassungen | Lokal umgesetzt | Dokumentname plus zwei bis drei extraktive Sätze und frei erzeugbares Ordnerdossier |
| Berichte aus Ordnern | Lokal umgesetzt | Deterministischer Markdown-Bericht; externe LLM-Synthese bleibt ein separater Provider |
| Dokumentversionen vergleichen | Lokal umgesetzt | Erklärte Neueste-Fassung-Heuristik, Satzvergleich und revisionsgebundener Archivierungsplan |
| „Neueste KFZ-Versicherung“ | Lokal umgesetzt | Vertragscockpit verbindet Version, Objekt, Kontakt, Kosten, Termine und Datenabdeckung; Archivierung bleibt freigabepflichtig |
| Lose Ordner ordnen | Lokal umgesetzt | FCSA-Dry-Run, Profilregeln, Gesamtplan, Zielkonflikte und selektive Ausführung |
| Vorhandene Ordnung fortführen | Lokal umgesetzt | Regelvererbung und beobachtete Ordnerzustände; keine unbelegte Musterbehauptung |
| Aus Nutzerkorrekturen lernen | Lokal umgesetzt | Hashgebundene Korrekturbeispiele werden zu prüfpflichtigen Regelkandidaten, nie still aktiviert |
| Regelmäßige Verzeichnisscans | Lokal umgesetzt | Deklarierte Watches, unveränderliche Checkpoints, Queue und portabler Scheduler-Handoff |
| Falsch sortierte Dateien korrigieren | Lokal umgesetzt | Plan, Freigabe, frischer Quellhash, Never-overwrite, Ablagebeleg und geprüftes Undo |
| Globale/bereichsspezifische Regeln | Lokal umgesetzt | Benennung, Archiv, Papierkorb, Dateityp und Ziel als feste Vererbung global → Bereich → Profil → Profilbereich |
| Ein Zielformat pro Ordner | Lokal umgesetzt | PDF-/TXT-Transformation mit Verlusthinweisen; andere Formate blockieren ohne Provider |
| Dokumente bündeln | Lokal umgesetzt | Ein TXT oder PDF sowie ein Dokument pro Typ in deterministischem ZIP; Videos werden nicht als Inhalt vorgetäuscht |
| Familienprofile | Lokal umgesetzt | Lukas/Hanna/Simon-Fixtures und bereichsspezifische Regeln; Profile sind keine Sicherheitskonten |
| Audit- und Aufräumberichte | Lokal umgesetzt | Atomare JSON-Berichte, Entscheidungen, Hashes, Checkpoints und Rollbackstatus |
| Kontakte aus Dokumenten | Lokal umgesetzt | Evidenzkandidaten, lokales Register, Objektzuordnung und sicherer Kontaktwechsel ohne automatische Löschung |
| Termine aus Dokumenten | Lokal umgesetzt | Kandidaten mit Zeilenbeleg, lokaler Kalender und atomarer ICS-Handoff; keine Erkennungsgarantie |
| Kalenderwahl | Handoff | UpToday-ICS geprüft; Routinika sichtbar blockiert; Google nur nach eigener Live-Freigabe |
| Kontoauszüge/virtuelle Konten | Lokal umgesetzt | Centgenaue Buchungen, Kontobezug, Perioden, Kontostand und sichtbare Lücken; kein Banking-Zugriff |
| Abo- und Kostenanalyse | Lokal umgesetzt | Wiederkehrende Kosten, aktiv/inaktiv-Kandidat, Monats-/Jahressumme und vorsichtige Folgemonatsprognose |
| Versicherungsübersicht | Lokal umgesetzt | Objektgebundene Policen-, Kontakt-, Kosten-, Termin- und Versionssicht |
| Haushalts-/Lagerbestand | Lokal umgesetzt | Append-only Bestandsereignisse, Orte, Mindestbestand sowie Einkaufs- und Ablaufkandidaten |
| Medikamentenplan/-einnahme | Lokal umgesetzt | Evidenzgebundener Plan und getrennte bestätigte Einnahme; keine Dosierungsentscheidung |
| Arztberichte synthetisieren | Lokal umgesetzt | Extraktive Gesundheitszeitlinie, Konflikte, Medikamente, Termine und Fragen; keine Diagnose |
| Bescheide verstehen | Lokal umgesetzt | Arten, beschriftete Angaben, Konflikte und bereitgestellte Fristen; keine Rechtsprüfung |
| Bescheide beantworten/Anträge | Lokal umgesetzt | Kontrollierte Widerspruchs-, Antwort- und Antragsentwürfe aus Profil und Evidenz; kein Versand |
| Leistungsvorcheck | Lokal umgesetzt | Datierter Routingkatalog und amtliche nächste Prüfschritte; kein Anspruchs- oder Höhenbescheid |
| Rechtsänderungen | Lokal umgesetzt | Vergleich lokaler Snapshots und Betroffenheitskandidaten; kein Webmonitoring oder Rechtsurteil |
| Law-Checker | Handoff | Sauber gepinnte, read-only Quellen-/Registry-Bridge; keine erfundene Rechtsprüf-API |
| Präsentation/Tabelle/Word/ODT | Handoff | Providerneutraler Artefaktplan und Qualitätsgates; spezialisierte Renderer werden nicht kopiert oder als lokal ausgeführt behauptet |
| Briefdesign/Designset | Lokal umgesetzt | Profil-/Zweckvorlagen, Kontrastprüfung, JSON-/CSS-Tokens und kontrollierte Markdown-/TXT-Ausgabe |
| Visitenkarte | Lokal umgesetzt | Escaped SVG-Vorschau, visuelle Freigabe und Never-overwrite-Batch |
| Medienerstellung | Handoff | Revisionsgebundener ai-media-editor-Handoff ohne behauptete Medienausführung |
| Mail-Ingest/-Versand | Handoff | IMAP-Plan, Entwurf, exakte Versandfreigabe und synthetisches Idempotenzledger; kein Live-Postfachtest |
| Persönliche LLM-Notizen | Lokal umgesetzt | Geführte Anfrage, Freigabe und append-only Versionen über den gepinnten llm-note-Provider |
| Steueragent | Lokal umgesetzt | Gekapselte Belegablage und private ZIP-Arbeitsunterlage; keine Steuerberatung oder Portalübermittlung |
| Wetter/Newspaper am Desktop | Lokal umgesetzt | Lokale Snapshots, Frischekennzeichnung, HTML-Render und getrennte Desktopfreigabe; keine Live-Feeds |
| HungryCall/Ringedingeding | Handoff | Revisionsgebundene lokale Dry-Run-Probes, keine Telefonie |
| FindCall | Lokal umgesetzt | Generische serielle Angebots-/Terminplanung mit Zeit-, Preis- und Stoppgrenzen; nur Fixture-Provider |
| Strands-Agent | Lokal umgesetzt | Echte `strands.Agent`-Schleife mit zwei read-only Tools für Suche und Themendossier |
| Amazon Bedrock | Handoff | Derselbe Agent unterstützt `BedrockModel`, aber nur mit Modell-ID, Region und getrennten Netzwerk-/Datenweitergabegates; nicht live getestet |
| Lokales Modell (Ollama) | Lokal umgesetzt | `OllamaModel`-Provider auf derselben Agentenschleife; ein Loopback-Host braucht kein Gate, ein entfernter dieselben zwei Gates wie Bedrock. Gegen einen entfernten Ollama-Host smoke-getestet; der Loopback-Smoke ist offen und der Client hat kein HTTP-Timeout |
| MCP-Adapter | Lokal umgesetzt | `mcp serve` reicht elf Lese- und Bestätigungswerkzeuge über stdio an ein laufendes `app serve` weiter; jede Nicht-Loopback-Adresse wird abgelehnt und auf stdout steht nur Protokoll |
| Ergebnisansicht | Lokal umgesetzt | Ausgeführte Berichte bleiben in einem begrenzten Ringpuffer und werden je Profil aufgelistet; Artefakte werden über den Index geholt, nie über einen Pfadparameter, begrenzt auf 25 MB |
| Einrichtungsprogramm | Lokal umgesetzt | Ein getrenntes Loopback-Einrichtungsprogramm ist der einzige Ort, der Konfiguration schreibt; das Speichern schreibt `resources.json` vollständig neu, von Hand ergänzte Einträge gehen verloren und nur die `.bak-<Zeitstempel>`-Kopie bewahrt sie |
| API/GUI/CLI | Lokal umgesetzt | Gemeinsamer Application Service, Loopback-API, responsive lokale GUI und umfassende CLI |
| OS-Kontotrennung | Lokal umgesetzt | Betriebssystemkonto und Dateirechte sind die Sicherheitsgrenze; keine Scheinsicherheit zwischen Profilen |

## Wiederverwendung

| Rolle | Bestand | FolderHome-Anpassung |
|---|---|---|
| Sammeln und Sortieren | file-collect-sort-action | Dry-Run-Bridge, Hash-/Freigabevertrag und FolderHome-Regelmodell |
| Extraktion und Suche | doc-services, KnowledgeDigest | Gepinnter Ingest sowie read-only Such- und Dossieradapter |
| Telefonmuster | HungryCall, Ringedingeding | Capabilities prüfen; generische FindCall-Domäne bleibt neuer Kern |
| Kalender | UpToday, Routinika, Google-Calendar-Skill | Providerneutrale Konten und getrennte Live-Gates |
| Notizen/Steuern | llm-note, steuer-assistent | Enge öffentliche API, profilspezifische Stores und FolderHome-Audit |
| Medizin/Analyse | gesundheit, docs-analysis | Sicherheits- und Extraktionsmuster; kein kopierter Runtimecode |
| Recht/Briefing | law-checker, BACH | Read-only Registry beziehungsweise Designreferenz; neue Workflows bleiben gekapselt |
| Medien/Office/Mail | ai-media-editor und doc-bricks | Revisionsgebundene Handoffs statt duplizierter Renderer/Connectoren |

Die exakten Revisionen und Herkunftsklassen stehen in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.de.md) und
[`COMPETITION_CODE_MAP.md`](./COMPETITION_CODE_MAP.md).

## Bewertung der Wettbewerbsfassung

| Kategorie | Bewertung (1–5) | Begründung |
|---|:---:|---|
| Funktionsumfang | 4 | Alle gewünschten Bereiche besitzen mindestens einen ehrlichen lokalen Kern oder klaren Handoff; Live-Provider bleiben getrennt |
| Agentik | 4 | Echter, endlich begrenzter Strands-Loop; zur Wettbewerbsabnahme bewusst nur zwei read-only Tools |
| UI/UX | 4 | Responsive Loopback-GUI und CLI auf demselben Service, dazu ein getrenntes browserbasiertes Einrichtungsprogramm; noch kein nativer Desktop-Installer |
| Stabilität | 5 | Erfolgs-, Missbrauchs-, Gate-, Rollback- und Never-overwrite-Pfade werden breit automatisiert geprüft |
| Dokumentation | 5 | Architektur, Entscheidungen, Herkunft, Sicherheit, aktueller Stand und Submission-Paket sind getrennt dokumentiert |
| Datenschutz/Sicherheit | 5 | Local-first, OS-Kontogrenze, Default deny, Ressourcenbudgets, Provenienz und explizite Außenwirkungsgates |
| Live-Integration | 2 | Absichtlich konservativ: keine Cloud-, Telefon-, Mail-, Kalender- oder Portalwirkung ohne gesonderte Freigabe. Ein echtes lokales Modell über das Netz ist der eine erprobte Live-Pfad |

## Was nach dem lokalen Vollausbau verbleibt

Die 36 Wettbewerbsphasen liefern den lokalen, demonstrierbaren FolderHome-
Vollausbau. Nicht als unerledigter Kernfehler, sondern als getrennte
Produkt-/Außenwirkungsgates verbleiben:

1. öffentliche Repository- und Videoveröffentlichung sowie Devpost-Submit;
2. reale Bedrock-, IMAP/SMTP-, Kalender-, Telefon-, OCR- und Webconnector-Tests;
3. visuelle Abnahme zusätzlicher Office-/Medienrenderer;
4. spätere Integration in FolderHome-Sovereign und mögliches Light-Rebranding.

## Technischer Kern

- Python 3.11+, `strands-agents==1.53.0`
- auf Windows `tzdata==2026.3`
- Einstieg: `python -m folderhome`
- Agent: `src/folderhome/application/strands_agent.py`
- reproduzierbare Demo: `python -m folderhome demo run`
- Sicherheitsmodell: [`SECURITY.md`](SECURITY.de.md)
- Architektur: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- vollständiger Phasennachweis: [`docs/phase36-completion-audit.md`](docs/phase36-completion-audit.de.md)

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
