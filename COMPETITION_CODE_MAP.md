# COMPETITION_CODE_MAP — Herkunft des Wettbewerbscodes

**Version:** 0.36
**Aktualisiert:** 2026-08-22
**Grund:** Strands-Agent, Wettbewerbsdemo und Phase-36-Härtung eingeordnet
**Zweck:** Ordnet jeden relevanten Repository-Bereich einer Herkunftsklasse zu.

> Wenn du veraltete Passagen oder Verweise entdeckst, korrigiere diese Datei
> und die zugehörigen Manifeste. Die Git-Historie bleibt der technische Beleg.

| Bereich | Klasse | Bedeutung |
|---|---|---|
| `src/folderhome/` | `NEW_CORE` | Im Wettbewerbszeitraum neu gebauter Kern |
| `src/folderhome/bridges/` | `NEW_BRIDGE` | Installierbarer Verbindungscode zu offengelegten Komponenten |
| `bridges/` | `NEW_BRIDGE` | Dokumentierte Provider-Grenzen des neuen Verbindungscodes |
| `skills/` | `NEW_CORE` | Neue agentisch nutzbare FolderHome-Skills |
| `manifests/` | `NEW_CORE` | Neue maschinenlesbare Komponenten- und Stackverträge |
| `reused/` | `REUSED_UNCHANGED` / `REUSED_DESIGN_REFERENCE` | Gepinnte Runtime-Referenzen oder klar markierte lokale Designquellen, kein kopierter Quellcode |
| `tests/` | `NEW_CORE` | Neue Vertrags-, Sicherheits- und Integrationstests |
| `examples/synthetic/`, `examples/fcsa/`, `examples/documents/`, `examples/profiles/`, `examples/inventory/`, `examples/medication/`, `examples/health/`, `examples/contracts/`, `examples/correspondence/`, `examples/artifacts/`, `examples/mail/`, `examples/calendar/`, `examples/notes/`, `examples/tax/`, `examples/briefing/`, `examples/notices/`, `examples/benefits/`, `examples/legal/`, `examples/competition/` | `GENERATED_OR_TEST_DATA` | Synthetische Demo-/Testdaten, reproduzierbare Agentenevidenz sowie gekennzeichnete amtliche Handoff-Metadaten ohne kopierten Portalcode |
| `_tools/`, Root-Projektdokumente | `REUSED_UNCHANGED` | Aus dem lokalen `project-docs`-Template instanziiert und projektspezifisch angepasst |

## Wettbewerbsgrenze

- FCSA, HungryCall und Ringedingeding bleiben eigene Repositories.
- UpToday bleibt eine lokale, revisionsgenau dokumentierte Designreferenz. Der
  vorhandene Inventar-Engine wird nicht importiert und kein Quellcode kopiert.
- Der öffentliche Gesundheit-Skill bleibt eine revisionsgenaue
  Designreferenz für Organisations- und Sicherheitsgrenzen; er speichert im
  FolderHome-Lauf nichts selbst.
- FolderHome kopiert keinen Quellcode dieser Projekte. Neue Bridges importieren
  ausschließlich exakt gepinnte, saubere Checkouts über deren öffentliche API
  oder einen dokumentierten, schreibgeschützten Schema-Seam.
- FCSA bleibt Dry-Run-only. doc-services liest Quellen; KnowledgeDigest darf
  nur nach explizitem Gate in einen angegebenen FolderHome-Zustandsordner
  schreiben. Quelldokumente bleiben unverändert.
- Der neue Profil-Aktionsplanner liegt gekapselt unter `src/folderhome/`.
  FCSA bestätigt nur seine eigenen Move-/Papierkorb-Capabilities; ein noch
  fehlender Konvertierungsprovider wird nicht als Wiederverwendung ausgegeben.
- Der neue Transformationskern liegt unter
  `src/folderhome/capabilities/document_transform/` und ist `NEW_CORE`.
  pypdf, Pillow und ReportLab werden nur als optionale Bibliotheken genutzt;
  ihr Quellcode wird nicht in das Repository kopiert.
- Der neue Korrespondenzkern liegt unter `contracts.correspondence` und
  `application.correspondence` und ist `NEW_CORE`. report-forge ist nur als
  gepinnte, derzeit blockierte Providerreferenz inventarisiert; es wird kein
  Quellcode kopiert und keine Runtime geladen.
- Artefaktplan, Designset und SVG-Visitenkarte unter
  `contracts.artifact_studio` und `application.artifact_studio` sind
  `NEW_CORE`. ai-media-editor bleibt eine revisionsgebundene
  `REUSED_UNCHANGED`-Referenz; die spezialisierten Office-Skills werden nicht
  in dieses Repository kopiert.
- Mailverträge, Ingest-/Entwurfslogik, synthetischer Gateway und Ledger unter
  `contracts.mail`, `application.mail_connector` und
  `capabilities.mail_gateway` sind `NEW_CORE`. Die vier doc-bricks-
  Mailprojekte bleiben unveränderte, revisionsgenaue Referenzen; kein
  Quellcode wurde kopiert oder ein veränderter Checkout geladen.
- Kalenderconnector-Verträge, Routing und synthetischer Gateway unter
  `contracts.calendar_connectors`, `application.calendar_connectors` und
  `capabilities.calendar_connector_gateway` sind `NEW_CORE`. UpToday,
  Routinika und der Google-Calendar-Skill bleiben unveränderte beziehungsweise
  hashgebundene Referenzen. Der vorhandene Phase-17-Handoff wird referenziert,
  nicht dupliziert.
- Persönliche Notizverträge, Führung und Freigabelogik unter
  `contracts.personal_notes`, `application.personal_notes` und
  `capabilities.personal_note_guide` sind `NEW_CORE`. `bridges.llm_note` ist
  `NEW_BRIDGE`; der Provider bleibt unverändert auf der Manifestrevision und
  sein Quellcode wird nicht kopiert. Die Bridge verwendet dessen öffentliche
  Write-API und einen eng begrenzten read-only Schema-Seam.
- Steuerbeleg-, Freigabe- und Exportverträge unter `contracts.tax` sowie die
  Orchestrierung unter `application.tax_workpaper` sind `NEW_CORE`.
  `bridges.tax_assistant` ist `NEW_BRIDGE`; der Provider bleibt unverändert
  auf der Manifestrevision. FolderHome nutzt dessen öffentliche Write- und
  Export-API, trennt Stores pro Profil und ergänzt keine Steuerberatung oder
  Portalübermittlung.
- Wetter-, Nachrichten-, Briefing-, Render- und Desktopverträge unter
  `contracts.daily_briefing` sowie die Orchestrierung unter
  `application.daily_briefing` sind `NEW_CORE`. BACH bleibt
  `REUSED_DESIGN_REFERENCE`: Der monolithische Code wird weder kopiert noch
  geladen. Live-Connectoren und Schedulerregistrierung werden nicht als
  Wettbewerbscode ausgegeben.
- Bescheid-, Evidenz-, Konflikt- und Ausgabeverträge unter
  `contracts.official_notices` sowie die Orchestrierung unter
  `application.official_notices` sind `NEW_CORE`. law-checker bleibt
  `REUSED_DESIGN_REFERENCE`: Der zurückliegende, fremd veränderte Checkout
  wird weder kopiert noch geladen. Phase 31 führt keine Rechtsprüfung oder
  gesetzliche Fristberechnung durch.
- Verwaltungsentwurfs-, Fakt-, Approval- und Ausgabeverträge unter
  `contracts.administrative_drafts` sowie die Verbindung unter
  `application.administrative_drafts` sind `NEW_CORE`. Phase 24 wird über
  seine öffentliche Korrespondenz-API wiederverwendet; kein Briefgenerator
  wird kopiert oder dupliziert. Rechtsprüfung und Versand sind nicht Teil des
  Wettbewerbscodes dieser Phase.
- Leistungsprofil-, Quellen-, Routing-, Katalog- und Berichtsverträge unter
  `contracts.benefit_screening` sowie die Auswertung unter
  `application.benefit_screening` sind `NEW_CORE`. Sozialleistungsfinder,
  KiZ-Lotse und Wohngeld-Plus-Rechner sind externe amtliche
  `REUSED_DESIGN_REFERENCE`-Handoffs; kein Portalcode wird kopiert, geladen
  oder automatisiert aufgerufen.
- Rechtsquellen-, Interessen-, Änderungs-, Kandidaten- und Ausgabeverträge
  unter `contracts.legal_change_monitor` sowie der lokale Vergleich unter
  `application.legal_change_monitor` sind `NEW_CORE`.
  `bridges.law_checker` ist `NEW_BRIDGE`; der Provider bleibt unverändert auf
  der Manifestrevision. FolderHome liest ausschließlich Identität, Registry
  und Quellenmetadaten und behauptet keine Rechtsprüf-API. Die Dateien unter
  `examples/legal/` sind deutlich isolierte synthetische Fixtures.
- Lokale App-Verträge, Handler-Allowlist und HTTP-Adapter unter
  `contracts.local_app`, `application.local_app` und `local_server` sowie die
  Assets unter `web_ui/` sind `NEW_CORE`. Sie verwenden nur die
  Python-Standardbibliothek und vorhandene FolderHome-Services; kein
  Webframework, Frontendpaket oder fremder Quellcode wird eingebettet.
- Strands-Verträge, Agentenadapter und Wettbewerbsdemo unter
  `contracts.strands_agent`, `application.strands_agent` und
  `application.competition_demo` sowie die ausschließlich synthetischen
  Paketfixtures unter `demo_data/` sind `NEW_CORE` beziehungsweise
  `GENERATED_OR_TEST_DATA`. Der Adapter instanziiert den
  echten `strands.Agent`, begrenzt Turns und Toolaufrufe und stellt genau zwei
  profilspezifische read-only FolderHome-Tools bereit. Das deterministische
  Fixture implementiert nur das öffentliche Strands-Modellinterface und ist
  ebenfalls neuer FolderHome-Code; es wird nicht als Modellqualitätsnachweis
  oder Bedrock-Ausführung ausgegeben.
- `strands-agents==1.53.0` ist eine verpflichtende Apache-2.0-
  Laufzeitabhängigkeit. `tzdata==2026.3` wird auf Windows benötigt, weil dort
  keine systemweite IANA-Zeitzonendatenbank vorausgesetzt werden kann. Beide
  Pakete werden installiert, nicht in das Repository kopiert.
- `examples/competition/evidence/` wird ausschließlich aus synthetischen
  internen Fixtures erzeugt. Die vier Artefakte belegen Toolwahl, Ausgabehash,
  No-network und fehlende Side-Effects; sie enthalten keine Personendaten.
- Spätere Submodule, Live-Connectoren, öffentliche Veröffentlichung und
  kostenpflichtige Aktionen benötigen eigene Entscheidungen und Gates.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
