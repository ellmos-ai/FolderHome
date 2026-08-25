# WORKFLOWS.md — Router zu Multi-Step-Playbooks

[English](./WORKFLOWS.md) | **Deutsch**

> **Zweck:** Navigation. „Welcher Workflow für welches Problem?"
> **Content:** Siehe `workflows/*.md` — hier steht **kein** Prozedur-Detail.
> **Abgrenzung zu PATTERNS.md:** Patterns = einzelne Code-Snippets.
> Workflows = Multi-Step-Prozeduren mit Side-Effects.
> **Auto-generiert:** Die Tabelle im AUTOGEN-Block unten wird von
> `_tools/workflows-sync` gepflegt. Handgeschriebene Inhalte oberhalb und
> unterhalb der Marker bleiben unangetastet.

---

## Verfügbare Workflows (auto-generated)

<!-- @auto-generated:workflow-index -->
<!-- last-updated: 2026-08-25 02:42 -->
<!-- tool: _tools/workflows-sync -->
<!-- count: 33 workflows in 1 categories -->

## Allgemein (33)

| Workflow | Zweck | Häufigkeit | Dauer |
|---|---|---|---|
| **Artefakte sicher planen und gestalten** [`artifact-studio.de.md`](./workflows/artifact-studio.de.md) | Eine gewünschte Präsentation, Tabelle, Datei, Visitenkarte oder Medienausgabe dem vorhandenen Spezialisten zuordnen, fehlende Qualitätsgates sichtb... | ad-hoc | wenige Sekunden für Plan und lokale Designausgabe |
| **Begrenzte Anbieteranfrage mit FindCall vorbereiten** [`findcall.de.md`](./workflows/findcall.de.md) | Eine serielle Anfrage für einen Termin oder ein Angebot bei ausdrücklich konfigurierten Kandidaten vorbereiten. FindCall wendet Zeit-, Orts- und Pr... | bei Bedarf für Termin- oder Angebotssuchen | Sekunden für lokale Planung und Fixture-Simulation |
| **Beobachteten Ordner geplant aufräumen** [`folder-routine.de.md`](./workflows/folder-routine.de.md) | Einen deklarierten Beobachtungsordner gegen seinen letzten Checkpoint prüfen, eine fällige Änderungsmenge oder den vollständigen Bestand planen und... | nach einem explizit ausgelösten Scanzeitpunkt | abhängig von Dateizahl und Extraktionsformaten |
| **Beobachteten Ordner scannen und Korrektur prüfen** [`directory-observation.de.md`](./workflows/directory-observation.de.md) | Einen deklarierten Ordner ohne Dokumentrohtext gegen seinen letzten verifizierten Checkpoint prüfen, Änderungen erklären und belegte manuelle Versc... | ad-hoc, später pro geplantem Scanlauf | abhängig von Dateizahl und Dateigröße |
| **Dokumentaktion freigeben und rückgängig machen** [`document-action-execution.de.md`](./workflows/document-action-execution.de.md) | Einen vorher geprüften Rename-/Move-Präfix für genau ein Dokument plan-, hash- und aktionsgebunden ausführen, lückenlos protokollieren und bei Beda... | ad-hoc nach menschlicher Planprüfung | wenige Sekunden pro Dokument auf demselben Datenträger |
| **Dokumentaktionsplan aus Profilregeln erstellen** [`document-action-plan.de.md`](./workflows/document-action-plan.de.md) | Ein synthetisches oder ausdrücklich gewähltes Dokument gegen die Regeln eines Organisationsprofils prüfen und einen nachvollziehbaren Plan erzeugen... | ad-hoc oder vor jeder späteren Dateiausführung | wenige Sekunden pro Dokument |
| **Dokumente als TXT oder PDF bündeln** [`document-bundle.de.md`](./workflows/document-bundle.de.md) | Einen ausdrücklich gewählten Ordner als eine neue TXT- oder PDF-Datei zusammenführen, ohne Originale zu verändern, zu archivieren oder zu löschen. | ad-hoc | abhängig von Dokumentzahl, Seitenzahl und Bildgröße |
| **Dokumentenbibliothek lokal aufbauen** [`document-library.de.md`](./workflows/document-library.de.md) | Einen ausdrücklich gewählten Ordner lokal indexieren, natürlich durchsuchen und daraus ein Themendossier oder einen Ordnerbericht erzeugen, ohne Qu... | ad-hoc | abhängig von Dokumentzahl und Dateigröße |
| **Dokumentkontakt prüfen und lokal registrieren** [`contact-register.de.md`](./workflows/contact-register.de.md) | Beschriftete Kontaktdaten aus ausdrücklich ausgewählten Dokumenten lokal erkennen, gegen das zuständige Profil und ein revisionsgebundenes Register... | bei neuen oder geänderten Dokumenten mit Zuständigkeitsdaten | wenige Sekunden pro Dokumentordner |
| **Dokumenttermin sicher an Kalender übergeben** [`calendar-handoff.de.md`](./workflows/calendar-handoff.de.md) | Gelabelte Termindaten aus einem ausdrücklich gewählten Dokumentordner prüfen und nach exakter Freigabe in den lokalen FolderHome-Kalender oder als ... | bei neuen oder geänderten Dokumenten mit Terminangaben | wenige Sekunden pro Dokumentordner |
| **Ein Dokument pro Dateityp als ZIP-Paket erzeugen** [`document-package.de.md`](./workflows/document-package.de.md) | Einen verschachtelten Ordner deterministisch nach Dateitypen gruppieren und als ein neues ZIP mit je einem Dokument pro Gruppe sowie einem Prüfmani... | ad-hoc | abhängig von Dokumentzahl, Seitenzahl und Bildgröße |
| **Einen Los Ordner sicher aufräumen** [`folder-cleanup.de.md`](./workflows/folder-cleanup.de.md) | Einen ausdrücklich gewählten Ordner vollständig planen, Zielkonflikte über alle Dokumente erkennen und anschließend nur eine bewusst ausgewählte Te... | ad-hoc, später als Teil einer beobachteten Routine | abhängig von Dokumentzahl und Extraktionsformaten |
| **FCSA-Sortierplan erstellen** [`fcsa-dry-run.de.md`](./workflows/fcsa-dry-run.de.md) | Einen vorhandenen Dokumentordner mit der gepinnten FCSA-Komponente prüfen und einen nachvollziehbaren Sortierplan erstellen, ohne den Eingangsordne... | ad-hoc | abhängig von der Ordnergröße |
| **FolderHome-Master-Agent verwenden** [`master-agent.de.md`](./workflows/master-agent.de.md) | Einen modellgesteuerten Agenten in GUI und CLI für FolderHome-Fähigkeitssuche, lokale Nur-Lese-Werkzeuge und begrenzte Fachplanung verwenden. Seman... | — | — |
| **Haushaltsbestand lokal ergänzen** [`inventory-import.de.md`](./workflows/inventory-import.de.md) | Bereitgestellte Bestandsbeobachtungen prüfen, revisionsgebunden in den lokalen Append-only-Inventarstore übernehmen und anschließend aktuelle Bestä... | nach einer ausdrücklich dokumentierten Bestandsaufnahme | wenige Sekunden pro Bestandsordner |
| **Kalenderconnector sicher planen und simulieren** [`calendar-connectors.de.md`](./workflows/calendar-connectors.de.md) | Aus belegten Phase-17-Terminkandidaten einen providerneutralen Connectorplan für UpToday, Routinika oder Google erzeugen und den Ablauf optional oh... | bei ausdrücklich gewünschter Kalenderübergabe | Planung wenige Sekunden; ein realer Connectorlauf ist nicht Teil der Abnahme |
| **Kontoauszüge lokal und centgenau übernehmen** [`finance-import.de.md`](./workflows/finance-import.de.md) | Ausdrücklich bereitgestellte Kontoauszüge prüfen, revisionsgebunden in den lokalen Finanzstore übernehmen und anschließend Abdeckung, Bewegungen un... | nach Bereitstellung neuer Kontoauszüge | wenige Sekunden pro Auszugsordner |
| **Korrespondenz sicher erstellen** [`correspondence-studio.de.md`](./workflows/correspondence-studio.de.md) | Einen Brief aus einer kontrollierten Vorlage und einem eigenen, vererbbaren Design zunächst vollständig lokal ansehen und anschließend als neue Mar... | ad-hoc | wenige Sekunden pro Brief |
| **Leistungsvorcheck lokal ausführen** [`benefit-screening.de.md`](./workflows/benefit-screening.de.md) | Ein lokales Leistungsprofil mit groben, datierten Routingkriterien abgleichen und passende amtliche Vorchecks anzeigen. Das Ergebnis ist eine Orien... | bei geänderter Lebenssituation oder frischem Katalog | wenige Sekunden zuzüglich amtlichem Vorcheck |
| **Lokale FolderHome-App starten** [`local-app.de.md`](./workflows/local-app.de.md) | Die gemeinsame FolderHome-Chatoberfläche auf dem aktuellen Betriebssystemkonto starten. Die GUI ruft denselben Master-Agentendienst wie die CLI auf... | — | — |
| **Mail sicher lesen, zuordnen und freigeben** [`mail-connector.de.md`](./workflows/mail-connector.de.md) | Einen Postfachabruf ohne Postfachänderung planen, eingehende Nachrichtenreferenzen providerneutral übernehmen und ein vorbereitetes Schreiben als E... | bei ausdrücklich ausgelöstem Mailabruf oder Entwurfsablage | Plan unter einer Sekunde; Providerlauf abhängig vom Postfach |
| **Medikamentenplan und bestätigte Einnahme** [`medication-intake.de.md`](./workflows/medication-intake.de.md) | Einen bereitgestellten Medikamentenplan lokal und evidenzgebunden übernehmen, die organisatorische Tagesansicht lesen und eine ausdrückliche Einnah... | nach ausdrücklich bereitgestelltem Plan oder einer Einnahmebestätigung | wenige Sekunden |
| **Mehrere Beobachtungsroutinen read-only bewerten** [`routine-queue.de.md`](./workflows/routine-queue.de.md) | Alle aktivierten Watches zu einem expliziten Zeitpunkt planen, Zustände vergleichbar bündeln und Konflikte über Watch-Grenzen erkennen, ohne Dateie... | bei jedem geplanten Scheduler- oder manuellen Prüflauf | abhängig von Watch- und Dokumentzahl |
| **Persönliche Notiz geführt und revisionssicher ablegen** [`personal-notes.de.md`](./workflows/personal-notes.de.md) | Einen menschlich formulierten Notizinhalt mit getrennten Fragen und Vorschlägen prüfen, exakt freigeben und als neue Version im gepinnten lokalen `... | bei ausdrücklich gewünschter persönlicher Notiz | Planung und lokale Ablage wenige Sekunden |
| **Private Steuer-Arbeitsunterlage aus bestätigten Belegen** [`tax-workpaper.de.md`](./workflows/tax-workpaper.de.md) | Einen katalogisierten Beleg nach menschlicher Kategorienbestätigung lokal in den gepinnten Steueragenten übernehmen und daraus optional eine privat... | nach ausdrücklich bereitgestellten und eingeordneten Belegen | wenige Sekunden pro Beleg und Export |
| **Read-only Queue für einen Scheduler vorbereiten** [`scheduler-handoff.de.md`](./workflows/scheduler-handoff.de.md) | Einen portablen Aufruf und ein Windows-Task-Artefakt erzeugen und einen headless Queue-Lauf sicher koordinieren, ohne eine Betriebssystemaufgabe zu... | einmal pro Zeitplan sowie bei Konfigurationsänderungen | Plan unter einer Sekunde; Lauf abhängig von Dokumentzahl |
| **Rechtsänderungen als Prüfkandidaten erfassen** [`legal-change-monitor.de.md`](./workflows/legal-change-monitor.de.md) | Zwei lokale, datierte Rechtsquellenstände technisch vergleichen und geänderte Themen mit ausdrücklich hinterlegten Profil- oder Vertragsinteressen ... | nach fachlich erstelltem neuen Rechtsquellensnapshot | wenige Sekunden ohne Beschaffung oder Rechtsprüfung |
| **Sozialrechtlichen Bescheid verstehen** [`official-notice-understanding.de.md`](./workflows/official-notice-understanding.de.md) | Ausdrücklich beschriftete Angaben eines lokalen Bescheids nachvollziehbar erfassen und als prüfbaren Markdown-/JSON-Bericht ausgeben. Dieser Workfl... | pro bereitgestelltem Bescheid | wenige Sekunden zuzüglich menschlicher Prüfung |
| **Strands-Agent und Wettbewerbsdemo ausführen** [`strands-agent.de.md`](./workflows/strands-agent.de.md) | Den echten Strands-Agents-Loop von FolderHome begrenzt planen, mit synthetischen Daten reproduzierbar ausführen und einen hashgebundenen Wettbewerb... | — | — |
| **Verwaltungsentwurf sicher erstellen** [`administrative-drafts.de.md`](./workflows/administrative-drafts.de.md) | Einen sichtbar ungeprüften und unversandten Verwaltungsbrief aus belegter Bescheidstruktur und bereitgestellten Angaben vorbereiten. Der Workflow e... | pro Widerspruchs-, Antwort- oder Antragsentwurf | wenige Sekunden zuzüglich vollständiger menschlicher Prüfung |
| **Wetter- und Newspaper-Brief lokal zustellen** [`daily-briefing.de.md`](./workflows/daily-briefing.de.md) | Einen Wetter- und Nachrichtensnapshot nachvollziehbar zu einem HTML-Brief bündeln und exakt diese Ausgabe nach einer zweiten Freigabe in einen gewä... | nach Bereitstellung eines neuen, datierten Snapshotpaars | wenige Sekunden |
| **Workflow — Gesundheitsdossier** [`health-dossier.de.md`](./workflows/health-dossier.de.md) | Aus einem ausdrücklich gewählten lokalen Ordner ein evidenzgebundenes Gesundheitsdossier als Markdown und JSON erstellen. Der Workflow ist extrakti... | — | — |
| **Workflow — Versicherungs- und Vertragscockpit** [`contract-cockpit.de.md`](./workflows/contract-cockpit.de.md) | Eine Anfrage wie „Was ist meine neueste KFZ-Versicherung für meinen Hyundai i10?“ als read-only Überblick beantworten. Das Cockpit setzt vorhandene... | — | — |

<!-- @end:workflow-index -->

## Beispiel (handschriftlich, zur Orientierung)

Falls du lieber ohne Auto-Generator arbeitest, kann die Tabelle so aussehen:

| Du willst... | Öffne |
|---|---|
| [Vom Beispiel auf einen echten Workflow starten] | [`workflows/_example-workflow.md`](workflows/_example-workflow.de.md) |
| [Einen Release-Prozess dokumentieren] | `workflows/release.md` (falls angelegt) |
| [Ein Security-Playbook dokumentieren] | `workflows/security-audit.md` (falls angelegt) |
| [Einen Hotfix-Ablauf dokumentieren] | `workflows/hotfix.md` (falls angelegt) |
| [Ein Admin-Playbook für Force-Push pflegen] | `workflows/force-push.md` (falls angelegt) |

(Diesen Beispiel-Block kannst du löschen wenn `workflows-sync` eingerichtet ist.)

## Wann welcher Workflow?

- **Nach Dependabot-Alert** → vorhandenes Security-Playbook nutzen oder neu anlegen
- **Nach Feature-Branch-Merge** → Release-Workflow nutzen oder anlegen
- **Bei Crash in Production** → Hotfix-Workflow nutzen oder anlegen
- **Bei Neuem Team-Mitglied** → Orientierungs- oder Onboarding-Workflow anlegen
- **Bei History-Bereinigung** → eigenes Admin-Force-Push-Playbook des Projekts

## Wann einen neuen Workflow anlegen

Ein neuer Workflow ist gerechtfertigt wenn:
- Mindestens **5 Schritte** mit **Side-Effects** (nicht nur „docs lesen")
- Das Prozedere mindestens **alle 3 Monate** wiederkehrt
- Es **Fallstricke** gibt, die ein LLM-Agent spontan nicht rekonstruieren kann
- Ein **klares Exit-Criterion** existiert (wann ist der Workflow fertig?)

Wenn einer dieser Punkte fehlt: **kein eigener Workflow**, sondern Abschnitt
in einem existierenden oder Pattern in `PATTERNS.md`.

## Konventionen

Siehe [`workflows/README.md`](workflows/README.de.md) für:
- Datei-Struktur eines einzelnen Workflows
- Namens-Konvention (kein `WORKFLOW-A.md` — sprechende Namen!)
- Pflicht-Abschnitte (Purpose, Steps, Exit-Criteria, Fallstricke)
