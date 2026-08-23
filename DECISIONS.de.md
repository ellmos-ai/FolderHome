# DECISIONS.md — Aktuelle Architekturentscheidungen

[English](./DECISIONS.md) | **Deutsch**

**Version:** 0.37  
**Stand:** 2026-08-23  
**Direkter Vorläufer:**
[`docs/archive/DECISIONS-through-phase35.md`](docs/archive/DECISIONS-through-phase35.de.md)

> Der Vorläufer enthält Kontext, Entscheidung und Folgen jeder Phase bis 35.
> Diese kurze Fassung ist der aktuelle Entscheidungsindex und ergänzt die
> Phase-36-Entscheidungen.

## Gültige Leitentscheidungen

| Entscheidung | Konsequenz |
|---|---|
| FolderHome ist ein neues Integrations-Repository | Neuer Kern und neue Bridges bleiben sichtbar von gepinntem Bestand getrennt |
| Wettbewerbsname bleibt FolderHome | Light-/Sovereign-Branding erfolgt frühestens nach dem Wettbewerb |
| Default deny für Side-Effects | Analyse oder Agententool erteilt keine Datei-, Mail-, Kalender-, Telefon-, Netzwerk- oder Publikationsberechtigung |
| Plan und Ausführung sind getrennt | Approval bindet Operation, Quelle, Ziel und Hash; unmittelbar vor Ausführung erfolgt ein Recheck |
| Betriebssystemkonto ist die Sicherheitsgrenze | Familienprofile organisieren Regeln, ersetzen aber keine OS-Rechte |
| „Neueste Fassung“ bleibt eine erklärte Heuristik | Vertragsdaten schlagen Dateiname/Änderungszeit; Archivierung bleibt ein separater reversibler Plan |
| Nutzerlernen braucht belegte Korrekturen | Beispiele erzeugen nur prüfpflichtige Regelkandidaten |
| Ausgaben sind neu und hashgebunden | Never-overwrite, atomare Veröffentlichung und Rollback eigener Teilergebnisse |
| Bestandsmodule werden nicht neu etikettiert | Exakte Revision, Lizenz, API/Seam und Side-Effect-Grenze stehen in Manifesten |
| Domänenzustände sind evidenzgebunden | Kontakte, Termine, Finanzen, Bestand, Medikation, Gesundheit, Verträge und Bescheide behalten Quellenstatus und Unsicherheit |
| Fachassistenz ist kein Fachurteil | Keine Diagnose, Rechts-, Steuer-, Leistungs- oder Finanzentscheidung |
| UI, CLI und Agent verwenden dieselbe Anwendungsgrenze | Keine duplizierte Fachlogik und kein direkter Providerzugriff aus der Oberfläche |
| Live-Connectoren besitzen eigene Gates | Fixture-, Handoff- oder Dry-Run-Erfolg ist kein Live-Nachweis |

## 2026-08-22: Strands ist der begrenzte Agentenlayer

### Kontext

Die aktuellen Agents-for-Humans-Regeln verlangen einen neu gebauten Agenten
mit dem Strands Agents SDK. Der vorhandene FolderHome-Kern war bereits eine
breite deterministische Assistenzplattform, aber noch keine Strands-
Orchestrierung.

### Entscheidung

`strands-agents==1.53.0` ist eine verpflichtende Runtime-Abhängigkeit. Ein
echter `strands.Agent` erhält genau zwei profilspezifische read-only Tools:
Dokumentensuche und Themendossier. Beide rufen `LocalApplication` auf.

Turns, Toolaufrufe, Prompt, Antwort, Toolresultat und Ausgabetokens sind
begrenzt. Ein deterministischer Fixture-Modelladapter macht denselben Loop
ohne Zugangsdaten reproduzierbar. Bedrock ist optional und benötigt Modell-ID,
Region sowie getrennte Freigaben für Netzwerkzugriff und die Weitergabe
lokaler Suchergebnisse an das Cloudmodell.

### Folgen

- Der Agent erfüllt die Wettbewerbsanforderung, ohne die vorhandenen
  Sicherheitsgrenzen zu umgehen.
- Fixture-Evidenz belegt Orchestrierung, nicht Modellqualität.
- Schreibende Domänenfähigkeiten werden nicht vorschnell als Agententools
  freigeschaltet.
- Eine technische Netzwerkfreigabe allein autorisiert keine Weitergabe
  potenziell sensibler lokaler Dokumentdaten.

## 2026-08-22: Ressourcenbudgets sind ein gemeinsamer Vertrag

### Kontext

Der Phase-36-Security-Scan fand unbeschränkte Dokumentarbeit und parallele
Loopback-Verbindungen. Einzelne ad-hoc Grenzen würden bei neuen Modulen leicht
auseinanderlaufen.

### Entscheidung

`capabilities/resource_budget` kapselt Dateizahl, Bytes und Laufzeit für alle
betroffenen Workflows. Der Loopbackserver ergänzt Semaphore, Sockettimeout und
Überlastabweisung. Der Agent besitzt eigene endliche Modell-/Toolbudgets.

### Folgen

- Neue Fähigkeiten können dieselbe fail-closed Mechanik wiederverwenden.
- Budgetüberschreitung wird als kontrollierter Fehler statt als Teilresultat
  oder Ressourcenerschöpfung behandelt.

## 2026-08-22: Amtliche URLs sind publishergebunden

### Entscheidung

Leistungs-Handoffs akzeptieren nur HTTPS und exakt geprüfte Hosts des
deklarierten Publishers. Ähnlich aussehende Subdomains, Userinfo, andere Ports,
Trailing-dot- und percent-encoding-Varianten blockieren.

### Folge

Ein Datenkatalog kann keinen beliebigen Host allein durch das Etikett
„amtlich“ vertrauenswürdig machen.

## 2026-08-22: Lokaler Abschluss und externe Submission bleiben getrennt

### Entscheidung

Die 36 Phasen enden mit einem lokal installierbaren, getesteten und
demonstrierbaren Wettbewerbspaket. Öffentliche Repositoryanlage,
Videoveröffentlichung, AWS Builder ID, Live-Demo und Devpost-Submit bleiben
eigenständige menschliche Gates.

### Folge

Ein lokal fertiger Build darf als lokal abgeschlossen gelten, aber niemals als
veröffentlicht oder eingereicht bezeichnet werden.

## 2026-08-23: Weiche Hackathon-Entscheidungen verwenden den autorisierten Entscheidungsavatar

### Entscheidung

Während der Hackathon-Operator-Phasen 0 bis 6 gilt für reversible Präferenz- und
Implementierungsentscheidungen diese Reihenfolge: Projektentscheidungen,
autorisierter Entscheidungsavatar mit ausgewiesener Konfidenz, danach
strukturiertes Operatorurteil. Der Operator dokumentiert die Begründung, statt
weiche Entscheidungen wiederholt zu Nutzerblockern zu machen. Öffentliche
Aktionen, Kosten, Nachrichten an Dritte, Uploads und Submission bleiben
menschliche Gates.

### Folge

Der Masteragent-Ausbau läuft innerhalb der vereinbarten Architektur autonom
weiter. Der Avatar prognostiziert Präferenzen; sein Ergebnis wird weder zu einer
Aussage des Nutzers noch zu einer Erweiterung der Ausführungsberechtigung.

## 2026-08-23: Logische Ressourcen sind lokale, fähigkeitsgebundene App-Konfiguration

### Entscheidung

Die kanonische private Zuordnung liegt je Betriebssystemkonto unter
`%LOCALAPPDATA%\FolderHome\resources.json`. Das Repository enthält nur das
versionierte Schema und anonyme Beispiele. Organisationsprofile referenzieren
logische Ressourcen-IDs und dürfen Defaults wählen, enthalten aber weder
physische Pfade noch Secrets. Jede Ressource deklariert Art, Rolle und erlaubte
Operationen; freie Pfade bleiben in Chatanfragen verboten.

Adapter werden in dieser Reihenfolge verbunden: Dokument-/Dateikern;
Versicherung, Kontakte, Kalender und Korrespondenz; Gesundheit, Finanzen und
Sozialrechtsassistenz; Bestand, Medikation, Steuer und Briefing. Ein
konfigurierter lokaler Kalender oder ein lokales ICS-Ziel darf nach der normalen
exakten Freigabe als lokale Ressource verwendet werden. Remote-Lesezugriffe und
alle Remote-Schreibzugriffe behalten connectorspezifische Gates.

FindCall bleibt ein eigenes Projekt und eine spätere Randintegration, nicht ein
wettbewerbskritischer FolderHome-Arbeitsstrang. Die bestehende strikt lokale
Fixture bleibt wahrheitsgemäß; ein späterer öffentlicher Such-Handoff kann
getrennt ergänzt werden.

### Folgen

- FolderHome-Konfiguration bleibt gekapselt, statt zu einem gemeinsamen
  modulübergreifenden Konfigurationsdienst zu werden.
- Profile bleiben organisatorische Overlays und werden nicht zur
  Sicherheitsgrenze.
- Ressourcen-IDs tragen Least Privilege und können von typisierten Adaptern
  wiederverwendet werden, ohne dem Modell Pfade offenzulegen.

## 2026-08-23: Lokale Fertigstellung vor Bedrock-Abnahme und Medienproduktion

### Entscheidung

Bedrock erhält nur den minimalen freigegebenen und bereinigten Kontext, der für
einen Zweck erforderlich ist; ganze Ordner oder Dokumente werden nie
standardmäßig weitergegeben. Zuerst werden lokaler Bau und Volltests
abgeschlossen. Danach erfolgt genau ein minimaler synthetischer Bedrock-Turn;
bei erneuter Drosselung stoppt der Lauf. Erst nach dieser Abnahme beginnt die
neue Videoproduktion.

Der Wettbewerbsweg ist Everyday Agents. Das Video ist englischsprachig, wird
öffentlich auf YouTube bereitgestellt und entsteht aus einer durchgehenden
synthetischen Haushaltsgeschichte mit Hackathon Operator, ai-media-editor und
dem storybasierten Music Composer. Eine isolierte synthetische AgentCore-Demo
gehört zum Umfang; personenbezogene Daten und reale externe Side-Effects nicht.
Der Teilnehmer reicht als berechtigte Einzelperson ein. FolderHome folgt dem
bewährten frühen Devpost-Vorgehen: einreichen, sobald das Projekt ausreichend
fortgeschritten ist, und den bis zur Frist bearbeitbaren Eintrag danach laufend
verbessern. Ein Builder-Artikel und die verfügbaren AWS-Credits werden als
übliche Wettbewerbspraxis verfolgt.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
