# ARCHITECTURE.md — Architektur und Grenzen

[English](./ARCHITECTURE.md) | **Deutsch**

**Version:** 0.39  
**Stand:** 2026-08-23  
**Direkter Vorläufer:**
[`docs/archive/ARCHITECTURE-v0.34.md`](docs/archive/ARCHITECTURE-v0.34.de.md)

> Projektregel: Der ausführliche, phasenweise gewachsene Vorläufer wurde
> unverändert archiviert. Diese Fassung beschreibt den aktuellen Gesamtbau
> und verweist für den Requirement-Nachweis auf den Completion-Audit.

## Systemzweck

FolderHome ist ein lokaler Dokument- und Assistenzservice-Agent. Er verbindet
Dokumentverständnis, reversible Dateiarbeit und gekapselte Haushaltsdomänen,
ohne aus einer Analyse automatisch eine Außenwirkung abzuleiten.

```text
Mensch / OS-Konto
  ├─ CLI
  ├─ responsive lokale GUI
  └─ Strands-Agent
       ↓
LocalApplication — einzige gemeinsame Anwendungsgrenze
       ↓
Application Workflows — Orchestrierung, Gates, Evidence, Reports
       ↓
Contracts + Capabilities — stabile Datenmodelle und kleine lokale Stores
       ↓
Bridges / Provider — revisionsgebunden, kleinste nötige Berechtigung
       ↓
lokale Dateien / SQLite / neue Ausgabeartefakte
```

## Schichten

| Schicht | Ort | Verantwortung |
|---|---|---|
| Bedienung | `cli.py`, `local_server.py`, `web_ui/`, `demo_site/`, `agentcore_server.py` | Eingabe validieren, schmale Handler anbieten, keine zweite Fachlogik |
| Agent | `application/strands_agent.py`, `application/master_agent.py` | Endliche Master-Schleife, semantische Fachwahl, explizite Endpunkte und begrenzte Planungs-Fachagenten |
| Executor-Gateway | `application/workflow_execution.py` | Typisierte einmalige Übergabe eines exakt bestätigten Masterschritts an einen vorhandenen Fach-Executor |
| Anwendung | `application/` | Workflows komponieren, Zustände prüfen, Freigaben erzwingen, Reports erzeugen |
| Verträge | `contracts/` | Unveränderliche, validierende Datenobjekte und Statusbegriffe |
| Fähigkeiten | `capabilities/` | Kleine wiederverwendbare Stores, Transaktionen, Provider-Gateways und Ressourcenbudgets |
| Bridges | `src/folderhome/bridges/`, `bridges/` | Exakte öffentliche API oder dokumentierter read-only Seam zu gepinnten Komponenten |
| Deklaration | `manifests/`, `reused/` | Herkunft, Revision, Capability, Side-Effects und Runtimegrenzen |

Direkte Zugriffe von UI oder Agent auf Provider sind unzulässig. Beide gehen
durch `LocalApplication`, damit CLI, API, GUI und Agent dieselben Regeln
verwenden.

Die interaktive `agent session` ruft denselben Dienst
`LocalApplication.run_agent_chat` wie die GUI auf und bewahrt vorgeschlagene
Pläne nur im aktuellen Prozess. Das Gespräch kann nichts freigeben;
`/confirm <plan_id>` verwendet denselben exakten, hashgebundenen
Bestätigungsdienst wie der HTTP-Endpunkt.

`LocalApplication` bewahrt die SDK-Nachrichtenliste je organisatorischem Profil
ausschließlich im aktuellen Prozess. Ein endliches Sliding Window erhält gültige
Tool-use-Paare und ist standardmäßig auf 24 Nachrichten begrenzt.
`/api/v1/agent/conversation/reset` löscht den Verlauf und die unbestätigten Pläne
eines Profils. Diese Trennung organisiert Kontext; sie ist keine zweite
Autorisierungsgrenze.

## Wettbewerbs-Demooberflächen

`demo accident-serve` erzeugt einen begrenzten synthetischen Arbeitsbereich und
stellt die echte lokale Strands-Geschichte auf Loopback hinter einem zufälligen
Sitzungstoken bereit. Der Browser bereitet einen pfadfreien Plan vor und
verlangt die exakte Plan-ID, bevor vier vorhandene Adapter das synthetische
Kontaktregister, den lokalen Kalender, das Vertragscockpit und die
Korrespondenzausgabe aktualisieren. Der Reset löscht ausschließlich
demoeigene Fixture-Ausgaben.

`site/` ist ein getrennter statischer, zweisprachiger Rundgang für GitHub Pages.
Er hat kein Backend, ruft keine API auf und ist sichtbar als skriptbasierter
Nachweis gekennzeichnet; er ersetzt die ausführbare lokale Demo nicht.

`application/agentcore_runtime.py` bildet dieselbe synthetische Geschichte auf
den aktuellen HTTP-Vertrag von Amazon Bedrock AgentCore (`/ping`,
`/invocations`) ab. Der Zustand wird durch einen SHA-256-Fingerabdruck des
Runtime-Sitzungsheaders getrennt. Der ARM64-Container ohne Rootrechte unter
`deploy/agentcore/` akzeptiert weder Uploads noch Modellzugangsdaten, beliebige
Ressourcen-IDs oder externe Effekte.

## Strands-Agent

```mermaid
flowchart LR
  U[Prompt + Profil] --> V[Schema- und Budgetprüfung]
  V --> A[strands.Agent 1.53.0]
  A --> M[Fixture Model]
  A -. Netzwerk- und Datenweitergabegate .-> B[Amazon Bedrock]
  A --> T1[search_home_documents]
  A --> T2[build_home_theme_dossier]
  A --> T3[list_home_capabilities]
  A --> T4[consult_home_specialist]
  T4 --> S[Begrenzter Fachagent: ein Planungswerkzeug]
  S --> P[Hashgebundener Masterplan]
  P --> C[Getrennte exakte Bestätigung]
  C --> E[Typisierter Executor-Katalog]
  E --> N[Vorhandener llm-note-Workflow]
  E --> M[Vorhandener Medikamenteneinnahme-Workflow]
  T1 --> L[LocalApplication]
  T2 --> L
  L --> K[KnowledgeDigest read-only]
  A --> R[Report: Toolereignisse, Hashes, keine Side-Effects]
```

Der Master-Agent besitzt absichtlich vier begrenzte Werkzeuge. Zwei sind
profilspezifisch und nur lesend, eines zeigt den geprüften Rollen- und
Endpoint-Katalog und eines erzeugt einen kurzlebigen Fachagenten mit genau
einem Planungswerkzeug. Der Fachagent kann weder freigeben noch ausführen. Nach
einer getrennten exakten Bestätigung darf der typisierte Executor-Katalog nur
eine vorbereitete Ausführungshülle aufrufen und liefert den vorhandenen
Fachbericht zurück. Mit vollständig konfiguriertem Register sind 27 Workflows
verbunden, ein Workflow direkt nur lesend, drei Systemendpunkte nur planend und
zwei externe Connectorlücken sichtbar. Verbundene Fachagenten erhalten das
exakte geschlossene JSON-Anfrageschema ihres einzelnen Endpunkts; unbekannte
Felder und beliebige Pfade werden blockiert. Alle 22 ressourcenabhängigen
Endpunkte, die lokale Kalenderalternative und der reine Entwurfsendpunkt für
Mail sind umgesetzt. Der Mailendpunkt verbindet sich nur, wenn das Register ein
Entwurfspostfach deklariert; sonst bleibt er ehrlich unverbunden. Externe
Kalender und Scheduler-Registrierung warten weiterhin auf ausdrücklich
konfigurierte externe Connectoren samt Live-Effekt-Freigaben.

Der Mailendpunkt besitzt keinen Versandweg. Er legt ein vorbereitetes Schreiben
im Entwurfsordner des eigenen IMAP-Postfachs des Nutzers ab, hinter der
getrennten Live-Effekt-Freigabe `--approve-mail-draft`. Kein Empfänger wird
kontaktiert, das Postfachpasswort wird erst zur Ausführung aus seinem
konfigurierten lokalen Fundort gelesen, und ein lokales Ledger hält die Ablage
höchstens einmal.

Der lokale Kalenderendpunkt kann die festgehaltenen Termine auf Wunsch als eine
private RFC-5545-Datei in ein registergebundenes Ausgabeverzeichnis exportieren.
Der Dateiinhalt ist durch dieselbe Bestätigung hashgebunden wie der
Statusschreibvorgang, eine vorhandene Zieldatei bricht den Lauf ab, und ein
fehlgeschlagener Statusschreibvorgang nimmt die publizierte Datei zurück;
Status und Datei entstehen gemeinsam oder gar nicht. FolderHome schreibt eine
lokale Datei; der Nutzer importiert sie von Hand in sein Kalenderprogramm, ein
Kalender-Connector ist also nicht beteiligt. Turnzahl,
Toolaufrufe, Prompt, Antwort, Toolresultat und
Ausgabetokens sind endlich begrenzt. Der deterministische Fixture-Adapter
durchläuft den echten Strands-Agenten und den echten Tool-Executor ohne
Zugangsdaten oder Netzwerk. Bedrock verlangt Modell-ID, AWS-Region, ein
ausdrückliches Netzwerkgate und eine davon getrennte Freigabe für die
Weitergabe lokaler Suchergebnisse; ein Live-Lauf ist nicht Teil der lokalen
Abnahme.
Status-API und GUI unterscheiden die Modellzustände `fixture_only`,
`configured_not_verified` und `verified_in_process`. Erst ein erfolgreicher
Bedrock-Agententurn setzt die Laufzeit auf den verifizierten Zustand. Sie weisen
außerdem die Laufzeittopologie aus: FolderHome, Dokumentzustand, Freigaben und
Workflow-Ausführung bleiben lokal; nur die Modellinferenz nutzt bei aktiviertem
Bedrock die AWS-Cloud.

## Dokumentenfluss

```text
bereitgestellter Ordner
  → Sensitivitäts- und Schreibgate
  → doc-services Extraktion
  → FolderHome-Dokumentverträge
  → KnowledgeDigest-Index im angegebenen State-Ordner
  → read-only Suche / Themendossier / Ordnerbericht / Versionen
```

Quelldokumente werden beim Ingest nicht verändert. Suche öffnet den Index
read-only. Berichte geben Fundstellen, Quellstatus und Abdeckungsgrenzen aus.
„Neueste Fassung“ ist eine erklärte Heuristik: explizite Vertragsdaten haben
Vorrang, danach folgen schwächere Metadaten. Ältere Fassungen werden nur über
einen getrennten, freigabepflichtigen FCSA-Plan archiviert.

## Dateiaktionsfluss

```text
Profil + Bereich + Quelldatei
  → feste Regelvererbung
  → read-only Plan
  → Provider-/Konfliktprüfung
  → exakte Approval-ID + erwarteter SHA-256
  → frische Gesamtprüfung
  → neue Ausgabe oder reversible Aktion
  → Ablagebeleg + Audit + optionales Undo
```

Die Vererbung lautet global → Bereich → Profil → Profilbereich. Gleichrangige
Widersprüche blockieren. Hard-Delete ist keine zulässige Regel. Batch- und
Routinenläufe prüfen gemeinsame Ziele ordner- beziehungsweise watchübergreifend
und rollen nur eigene, nachweislich erzeugte Änderungen zurück.

## Dokumenttransformation

Der neue Kern unter `capabilities/document_transform/` erzeugt TXT- und
PDF-Bündel sowie ein Dokument pro Dateityp in einem deterministischen ZIP.
PDF-Seiten bleiben erhalten; Bilder werden gerastert; Textquellen werden neu
gesetzt und mit einem sichtbaren Verlusthinweis versehen. Videos werden nicht
in PDF-Inhalt umgedeutet. Jede Ausgabe ist neu, hashgebunden und
Never-overwrite. Andere Zielformate bleiben ohne geprüften Renderer blockiert.

## Domänenpakete

| Paket | Lokaler Kern | Harte Grenze |
|---|---|---|
| Kontakte | Evidenzkandidaten, Register, Objektbezug, Wechsel | keine automatische Löschung oder Kontaktaufnahme |
| Kalender | Kandidaten, lokaler Store, ICS, Connectorplan | kein stiller Live-Sync; UpToday/Routinika/Google getrennt |
| FindCall | Zeit-/Preisgrenzen, serielle Fixtures, früher Stopp | keine Telefonie, keine Buchung |
| Finanzen | Auszüge, virtuelle Konten, Lücken, wiederkehrende Kosten | kein Banking, keine Zahlungsbehauptung |
| Haushalt | append-only Bestand, Mindeststand, Ablaufkandidaten | keine Bestellung, keine Vollständigkeitsgarantie |
| Medikation | dokumentierter Plan, bestätigte Einnahme | keine Dosisentscheidung oder Einnahmebehauptung ohne Bestätigung |
| Gesundheit | extraktive Zeitlinie, Konflikte, Fragen, Handoff | keine Diagnose, Therapie oder Vollständigkeitsgarantie |
| Verträge | objektgebundene Versionen, Kontakte, Kosten, Termine | keine Deckungs- oder Rechtswirkungsaussage |
| Korrespondenz | Vorlagen, Designs, Vorschau, neue Ausgabe | kein Versand ohne getrennten Mailworkflow |
| Office/Medien | Artefaktplan, Designset, SVG-Visitenkarte | Spezialrenderer bleiben eigene Provider |
| Mail | Ingestplan, Entwurf, Approval, Idempotenz | Live-Postfach bleibt ein eigenes Gate |
| Notizen | geführte Anfrage, Freigabe, Versionen | nur profilspezifischer Providerstore |
| Steuern | Belegstore, private ZIP-Arbeitsunterlage | keine Beratung oder Portalübermittlung |
| Daily Brief | lokale Snapshots, Frische, Render, Desktopkopie | keine Live-Feeds oder Schedulerregistrierung |
| Bescheide | Typen, beschriftete Fakten, Konflikte | keine Rechtsprüfung oder erfundene Fristberechnung |
| Entwürfe | Antwort-, Widerspruchs-, Antragsvorlagen | kein Rechtsurteil oder Versand |
| Leistungen | datierter Katalog, amtliche Prüfschritte | kein Anspruch, keine Höhe, kein automatischer Webaufruf |
| Rechtsänderung | lokale Snapshot-Diffs, Review-Kandidaten | keine Betroffenheitsfeststellung oder Benachrichtigung |

## Daten- und Identitätsmodell

- Das Betriebssystemkonto und seine Dateirechte bilden die Sicherheitsgrenze.
- Profile wie Lukas, Hanna und Simon sind Organisations- und
  Präferenzobjekte innerhalb eines Kontos, keine Zugriffskontrollen.
- Reale personenbezogene Daten gehören nicht in Repository, Demo oder
  öffentliche Evidenz.
- Finanz-, Gesundheits-, Medikations-, Kontakt- und Bescheiddaten erfordern
  ein ausdrückliches lokales Lesegate.
- Schreibende Stores verwenden append-only Ereignisse oder neue Dateien;
  vorhandene Ausgaben werden nicht überschrieben.

## Persistenz

| Zustand | Technik | Eigenschaft |
|---|---|---|
| Dokumentindex | KnowledgeDigest/SQLite | Suche ausschließlich read-only |
| Snapshots/Checkpoints | JSON | unveränderlich, inhaltsarm, hashgebunden |
| Kontakte/Kalender/Finanzen/Bestand/Medikation | lokale SQLite-Stores | profilspezifisch, validiert, überwiegend append-only |
| Audit/Reports | JSON/Markdown | atomar erzeugt, Provenienz und Status sichtbar |
| Ausgaben | TXT/PDF/ZIP/SVG/HTML/ICS | neue Pfade, Never-overwrite, Hashnachweis |

## Sicherheitsmodell

Die ausführliche Richtlinie steht in [`SECURITY.md`](SECURITY.de.md).

- Default deny für Datei-, Netzwerk-, Mail-, Kalender-, Telefon- und
  Veröffentlichungswirkungen.
- Exakte Schemas, kanonische Pfade, Allowlisten und Quellhashes.
- Ressourcenbudgets für Dateizahl, Bytes, Laufzeit, Agententurns,
  Toolaufrufe, HTTP-Verbindungen und Ausgabegröße.
- Loopback bindet ausschließlich `127.0.0.1`, verwendet ein kurzlebiges Token
  sowie exakte Host- und Origin-Prüfung und begrenzt parallele Verbindungen.
- Amtliche Leistungslinks verwenden HTTPS und eine publishergebundene
  Host-Whitelist; Umleitungen oder ähnlich aussehende Hosts werden abgewiesen.
- Approval ist eng, zeitlich und inhaltlich gebunden; vor der Ausführung wird
  der Zustand erneut geprüft.

## Provider- und Wiederverwendungsgrenze

Bestandsmodule bleiben in ihren eigenen Repositories. FolderHome kopiert
keinen Providerquellcode. Ein Bridge-Lauf verlangt die deklarierte Revision,
einen sauberen Checkout, kompatible Runtime und eine erlaubte Capability.
Fremde Änderungen, fehlende Lizenzen oder Versionsdrift blockieren. Die
vollständige Zuordnung steht in
[`COMPETITION_CODE_MAP.md`](COMPETITION_CODE_MAP.de.md) und
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.de.md).

## Phasen- und Abnahmenachweis

Die historischen Einzelflüsse der Phasen 1–34 bleiben im archivierten
Vorläufer erhalten. Die kanonische 36-Zeilen-Matrix, Codeevidenz, Testergebnis,
Demo-Hashes und verbleibenden Außenwirkungsgates stehen in
[`docs/phase36-completion-audit.md`](docs/phase36-completion-audit.de.md).

Die öffentliche Repositoryanlage, Videoveröffentlichung, AWS-Registrierung
und Devpost-Einreichung sind keine Architekturautomatik und benötigen jeweils
eine ausdrückliche menschliche Freigabe.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
