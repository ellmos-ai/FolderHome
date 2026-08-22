# Changelog

[English](./CHANGELOG.md) | **Deutsch**

**Aktuelle Kurzfassung:** 0.36 / 2026-08-22  
**Direkter Vorläufer:**
[`docs/archive/CHANGELOG-through-phase35.md`](docs/archive/CHANGELOG-through-phase35.de.md)

Alle relevanten Änderungen werden in dieser Datei dokumentiert. Der
ausführliche phasenweise Verlauf bis Phase 35 bleibt unverändert im Archiv.

## [Unreleased]

### Hinzugefügt

- echter, endlich begrenzter Strands-Agent mit profilspezifischer
  Dokumentensuche und Themendossier
- deterministischer No-network-Modelladapter über das öffentliche Strands-
  `Model`-Interface
- optionaler Amazon-Bedrock-Pfad mit getrennten Netzwerk- und
  Datenweitergabegates
- reproduzierbare synthetische Wettbewerbsdemo mit vier gehashten Artefakten
- `agent plan`, `agent run` und `demo run` in der CLI
- wiederverwendbarer Ressourcenbudget-Vertrag für Dateizahl, Bytes und Laufzeit
- publishergebundene HTTPS-Vertrauensprüfung für amtliche Leistungs-Handoffs
- Verbindungsgrenzen, Sockettimeout und Überlastabweisung im Loopbackserver
- `SECURITY.md`, englisches Submission-Paket und 36-Phasen-Completion-Audit
- neuer Skill `folderhome-strands-agent` und zugehöriger Workflow
- Windows-Runtimeabhängigkeit `tzdata==2026.3`

### Geändert

- Runtime bindet `strands-agents==1.53.0` exakt ein
- Dev-Abhängigkeit verlangt mindestens `pytest 9.0.3`
- Ingest, Snapshot, Transformation, Paket, Kontakte, Kalender, Finanzen,
  Cleanup, Gesundheit, Inventar und Medikation verwenden gemeinsame Budgets
- README, Architektur, Featureanalyse, Herkunfts- und Lizenzregister auf
  Phase 36 aktualisiert
- überlange Projektdokumente archiviert und durch kurze aktuelle Fassungen mit
  direktem Vorläuferverweis ersetzt
- Workflowrouter auf 31 Playbooks aktualisiert
- Englisch ist jetzt für 122 Dokumentationsseiten die Standardsprache; die
  erhaltenen deutschen Fassungen tragen das Suffix `.de.md` und verlinken
  wechselseitig auf die jeweilige Sprachfassung
- die Workflowrouter-Erzeugung synchronisiert nun 31 englische und 31 deutsche
  Playbooks, ohne lokalisierte Spiegel doppelt zu zählen
- lokale Agentenanweisungen, Aufgabenlisten, Statusdateien und Ausführungspläne
  bleiben lokal erhalten, werden aber aus Git ausgeschlossen

### Sicherheit

- Security-Scan über 357 Dateien und 12/12 Oberflächen abgeschlossen
- drei Befunde behoben: unbeschränkte Dokumentarbeit, beliebige amtliche Hosts
  und unbeschränkte Loopback-Threads
- zusätzliche adversariale URL-Fälle für Trailing dot, percent-encoding und
  expliziten Port ergänzt
- potenziell sensible lokale Suchtreffer dürfen Bedrock erst nach einer vom
  technischen Netzwerkgate getrennten Datenweitergabefreigabe erreichen
- der nachgelagerte 66-Dateien-Delta-Audit bestätigte diese Freigabelücke als
  vierten, inzwischen behobenen Befund
- `pip-audit` nach Update der lokalen Prüfwerkzeuge ohne bekannte
  Schwachstellen

### Verifiziert

- 333/333 automatisierte Tests
- Ruff und Compileall ohne Befund
- 8/8 Pluginmanifeste und 12/12 Skills gültig
- 31 Workflows synchron
- synthetischer Strands-Lauf: zwei Szenarien, kein Netzwerk, keine
  Side-Effects; Wiederholung blockiert am Never-overwrite-Gate
- Wheel enthält Agent, Demo, Ressourcenbudget, Hostprüfung und GUI

## Historische Meilensteine

| Phasen | Ergebnis |
|---|---|
| 1–8 | Integrationskern, FCSA, Dokumentenbibliothek, Versionen, Profile, Aktionen, Transformation und Typpakete |
| 9–15 | Ordnerbeobachtung, Korrekturlernen, Scans, Ausführung/Undo, Routinen, Queue und Scheduler-Handoff |
| 16–21 | Kontakte, Kalender, FindCall, Finanzen, Haushalt und Medikation |
| 22–30 | Gesundheit, Verträge, Korrespondenz, Office/Design, Mail, Kalenderconnectoren, Notizen, Steuern und Daily Brief |
| 31–35 | Bescheide, Verwaltungsentwürfe, Leistungsvorcheck, Rechtsänderungen und lokale GUI/API |
| 36 | Härtung, Strands-Agent, Wettbewerbsdemo und einreichungsfertiges lokales Paket |

Die einzelnen Änderungen und damaligen Teststände stehen im direkten
Vorläufer; der aktuelle Requirement-Nachweis steht in
[`docs/phase36-completion-audit.md`](docs/phase36-completion-audit.de.md).

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
