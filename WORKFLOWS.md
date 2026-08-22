# WORKFLOWS.md — Router zu Multi-Step-Playbooks

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
<!-- last-updated: 2026-08-22 09:51 -->
<!-- tool: _tools/workflows-sync -->
<!-- count: 31 workflows in 1 categories -->

## General (31)

| Workflow | Purpose | Frequency | Duration |
|---|---|---|---|
| **Artefakte sicher planen und gestalten** [`artifact-studio.md`](./workflows/artifact-studio.md) | Eine gewünschte Präsentation, Tabelle, Datei, Visitenkarte oder | ad-hoc | wenige Sekunden für Plan und lokale Designausgabe |
| **Beobachteten Ordner geplant aufräumen** [`folder-routine.md`](./workflows/folder-routine.md) | Einen deklarierten Beobachtungsordner gegen seinen letzten Checkpoint prüfen, | nach einem explizit ausgelösten Scanzeitpunkt | abhängig von Dateizahl und Extraktionsformaten |
| **Beobachteten Ordner scannen und Korrektur prüfen** [`directory-observation.md`](./workflows/directory-observation.md) | Einen deklarierten Ordner ohne Dokumentrohtext gegen seinen letzten | ad-hoc, später pro geplantem Scanlauf | abhängig von Dateizahl und Dateigröße |
| **Dokumentaktion freigeben und rückgängig machen** [`document-action-execution.md`](./workflows/document-action-execution.md) | Einen vorher geprüften Rename-/Move-Präfix für genau ein Dokument | ad-hoc nach menschlicher Planprüfung | wenige Sekunden pro Dokument auf demselben Datenträger |
| **Dokumentaktionsplan aus Profilregeln erstellen** [`document-action-plan.md`](./workflows/document-action-plan.md) | Ein synthetisches oder ausdrücklich gewähltes Dokument gegen die Regeln eines | ad-hoc oder vor jeder späteren Dateiausführung | wenige Sekunden pro Dokument |
| **Dokumente als TXT oder PDF bündeln** [`document-bundle.md`](./workflows/document-bundle.md) | Einen ausdrücklich gewählten Ordner als eine neue TXT- oder PDF-Datei | ad-hoc | abhängig von Dokumentzahl, Seitenzahl und Bildgröße |
| **Dokumentenbibliothek lokal aufbauen** [`document-library.md`](./workflows/document-library.md) | Einen ausdrücklich gewählten Ordner lokal indexieren, natürlich durchsuchen | ad-hoc | abhängig von Dokumentzahl und Dateigröße |
| **Dokumentkontakt prüfen und lokal registrieren** [`contact-register.md`](./workflows/contact-register.md) | Beschriftete Kontaktdaten aus ausdrücklich ausgewählten Dokumenten lokal | bei neuen oder geänderten Dokumenten mit Zuständigkeitsdaten | wenige Sekunden pro Dokumentordner |
| **Dokumenttermin sicher an Kalender übergeben** [`calendar-handoff.md`](./workflows/calendar-handoff.md) | Gelabelte Termindaten aus einem ausdrücklich gewählten Dokumentordner prüfen | bei neuen oder geänderten Dokumenten mit Terminangaben | wenige Sekunden pro Dokumentordner |
| **Ein Dokument pro Dateityp als ZIP-Paket erzeugen** [`document-package.md`](./workflows/document-package.md) | Einen verschachtelten Ordner deterministisch nach Dateitypen gruppieren und | ad-hoc | abhängig von Dokumentzahl, Seitenzahl und Bildgröße |
| **Einen Los Ordner sicher aufräumen** [`folder-cleanup.md`](./workflows/folder-cleanup.md) | Einen ausdrücklich gewählten Ordner vollständig planen, Zielkonflikte über | ad-hoc, später als Teil einer beobachteten Routine | abhängig von Dokumentzahl und Extraktionsformaten |
| **FCSA-Sortierplan erstellen** [`fcsa-dry-run.md`](./workflows/fcsa-dry-run.md) | Einen vorhandenen Dokumentordner mit der gepinnten FCSA-Komponente prüfen und | ad-hoc | abhängig von der Ordnergröße |
| **Haushaltsbestand lokal ergänzen** [`inventory-import.md`](./workflows/inventory-import.md) | Bereitgestellte Bestandsbeobachtungen prüfen, revisionsgebunden in den | nach einer ausdrücklich dokumentierten Bestandsaufnahme | wenige Sekunden pro Bestandsordner |
| **Kalenderconnector sicher planen und simulieren** [`calendar-connectors.md`](./workflows/calendar-connectors.md) | Aus belegten Phase-17-Terminkandidaten einen providerneutralen Connectorplan | bei ausdrücklich gewünschter Kalenderübergabe | Planung wenige Sekunden; ein realer Connectorlauf ist nicht Teil der Abnahme |
| **Kontoauszüge lokal und centgenau übernehmen** [`finance-import.md`](./workflows/finance-import.md) | Ausdrücklich bereitgestellte Kontoauszüge prüfen, revisionsgebunden in den | nach Bereitstellung neuer Kontoauszüge | wenige Sekunden pro Auszugsordner |
| **Korrespondenz sicher erstellen** [`correspondence-studio.md`](./workflows/correspondence-studio.md) | Einen Brief aus einer kontrollierten Vorlage und einem eigenen, vererbbaren | ad-hoc | wenige Sekunden pro Brief |
| **Leistungsvorcheck lokal ausführen** [`benefit-screening.md`](./workflows/benefit-screening.md) | Ein lokales Leistungsprofil mit groben, datierten Routingkriterien abgleichen | bei geänderter Lebenssituation oder frischem Katalog | wenige Sekunden zuzüglich amtlichem Vorcheck |
| **Lokale FolderHome-App starten** [`local-app.md`](./workflows/local-app.md) | Die gemeinsame FolderHome-Oberfläche auf genau dem aktuellen | pro lokaler Arbeitssitzung | wenige Sekunden zuzüglich der interaktiven Nutzung |
| **Mail sicher lesen, zuordnen und freigeben** [`mail-connector.md`](./workflows/mail-connector.md) | Einen Postfachabruf ohne Postfachänderung planen, eingehende | bei ausdrücklich ausgelöstem Mailabruf oder Versand | Plan unter einer Sekunde; Providerlauf abhängig vom Postfach |
| **Medikamentenplan und bestätigte Einnahme** [`medication-intake.md`](./workflows/medication-intake.md) | Einen bereitgestellten Medikamentenplan lokal und evidenzgebunden übernehmen, | nach ausdrücklich bereitgestelltem Plan oder einer Einnahmebestätigung | wenige Sekunden |
| **Mehrere Beobachtungsroutinen read-only bewerten** [`routine-queue.md`](./workflows/routine-queue.md) | Alle aktivierten Watches zu einem expliziten Zeitpunkt planen, Zustände | bei jedem geplanten Scheduler- oder manuellen Prüflauf | abhängig von Watch- und Dokumentzahl |
| **Persönliche Notiz geführt und revisionssicher ablegen** [`personal-notes.md`](./workflows/personal-notes.md) | Einen menschlich formulierten Notizinhalt mit getrennten Fragen und | bei ausdrücklich gewünschter persönlicher Notiz | Planung und lokale Ablage wenige Sekunden |
| **Private Steuer-Arbeitsunterlage aus bestätigten Belegen** [`tax-workpaper.md`](./workflows/tax-workpaper.md) | Einen katalogisierten Beleg nach menschlicher Kategorienbestätigung lokal in | nach ausdrücklich bereitgestellten und eingeordneten Belegen | wenige Sekunden pro Beleg und Export |
| **Read-only Queue für einen Scheduler vorbereiten** [`scheduler-handoff.md`](./workflows/scheduler-handoff.md) | Einen portablen Aufruf und ein Windows-Task-Artefakt erzeugen und einen | einmal pro Zeitplan sowie bei Konfigurationsänderungen | Plan unter einer Sekunde; Lauf abhängig von Dokumentzahl |
| **Rechtsänderungen als Prüfkandidaten erfassen** [`legal-change-monitor.md`](./workflows/legal-change-monitor.md) | Zwei lokale, datierte Rechtsquellenstände technisch vergleichen und geänderte | nach fachlich erstelltem neuen Rechtsquellensnapshot | wenige Sekunden ohne Beschaffung oder Rechtsprüfung |
| **Sozialrechtlichen Bescheid verstehen** [`official-notice-understanding.md`](./workflows/official-notice-understanding.md) | Ausdrücklich beschriftete Angaben eines lokalen Bescheids nachvollziehbar | pro bereitgestelltem Bescheid | wenige Sekunden zuzüglich menschlicher Prüfung |
| **Strands-Agent und Wettbewerbsdemo ausführen** [`strands-agent.md`](./workflows/strands-agent.md) | Den echten Strands-Agents-Loop von FolderHome begrenzt planen, mit | pro Demo- oder Agentenabnahme | wenige Sekunden ohne Bedrock; providerabhängig mit Bedrock |
| **Verwaltungsentwurf sicher erstellen** [`administrative-drafts.md`](./workflows/administrative-drafts.md) | Einen sichtbar ungeprüften und unversandten Verwaltungsbrief aus belegter | pro Widerspruchs-, Antwort- oder Antragsentwurf | wenige Sekunden zuzüglich vollständiger menschlicher Prüfung |
| **Wetter- und Newspaper-Brief lokal zustellen** [`daily-briefing.md`](./workflows/daily-briefing.md) | Einen Wetter- und Nachrichtensnapshot nachvollziehbar zu einem HTML-Brief | nach Bereitstellung eines neuen, datierten Snapshotpaars | wenige Sekunden |
| **Workflow — Gesundheitsdossier** [`health-dossier.md`](./workflows/health-dossier.md) | (kein Purpose-Abschnitt gefunden) | — | — |
| **Workflow — Versicherungs- und Vertragscockpit** [`contract-cockpit.md`](./workflows/contract-cockpit.md) | (kein Purpose-Abschnitt gefunden) | — | — |

<!-- @end:workflow-index -->

## Beispiel (handschriftlich, zur Orientierung)

Falls du lieber ohne Auto-Generator arbeitest, kann die Tabelle so aussehen:

| Du willst... | Öffne |
|---|---|
| [Vom Beispiel auf einen echten Workflow starten] | [`workflows/_example-workflow.md`](./workflows/_example-workflow.md) |
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

Siehe [`workflows/README.md`](./workflows/README.md) für:
- Datei-Struktur eines einzelnen Workflows
- Namens-Konvention (kein `WORKFLOW-A.md` — sprechende Namen!)
- Pflicht-Abschnitte (Purpose, Steps, Exit-Criteria, Fallstricke)
