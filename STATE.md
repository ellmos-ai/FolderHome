---
name: "folderhome-state"
type: state-snapshot
version: 0.36.0
updated: "2026-08-22 11:36"
updated_by: "Codex"
current_phase: "Alle 36 lokalen Wettbewerbsphasen abgeschlossen; externe Submission-Gates offen"
last_verified: 2026-08-22
description: |
  Current-state snapshot for FolderHome.
---

# STATE.md — Aktueller Projektstand

## Current Phase

Alle 36 lokalen Wettbewerbsphasen sind abgeschlossen. Der Stand umfasst die
gemeinsame Loopback-API/GUI, einen echten begrenzten Strands-Agenten, gehärtete
Ressourcen- und Vertrauensgrenzen, eine reproduzierbare synthetische Demo und
lokal vorbereitete Einreichungsunterlagen. Die aktuelle Gesamtsuite besteht
mit 333/333 Tests.

## Focus gerade

Nur noch externe menschliche Gates: AWS Builder ID, Videoaufnahme/-upload,
optionale Live-Demo-Entscheidung und ausdrücklicher Devpost-Submit. Sie sind
keine offenen lokalen Implementierungsphasen.

## Letzte bedeutsame Aktion

Phase 36 ergänzte `strands-agents==1.53.0`, zwei profilspezifische read-only
Agententools, gemeinsame Ressourcenbudgets, publishergebundene amtliche URLs,
begrenzte Loopback-Verbindungen und `tzdata` für Windows. Netzwerkzugriff und
Weitergabe sensibler lokaler Daten an Bedrock benötigen getrennte Freigaben.
Der synthetische Agentenlauf bestand ohne Netzwerk oder Side-Effects; vier
Demoartefakte wurden unabhängig gehasht und Never-overwrite praktisch belegt.
Baseline-Scan und aktueller 66-Dateien-Delta-Audit, Abhängigkeiten, Plugins,
Skills, Workflows, Dokumente, Wheel und 333 Tests wurden lokal geprüft. Das
öffentliche MIT-Repository `ellmos-ai/FolderHome` wurde vom Nutzer freigegeben;
Video, Live-Cloudbetrieb und Devpost-Submit wurden nicht ausgelöst.

## Next

- [ ] Human Gate: Teilnahmeberechtigung und AWS Builder ID bestätigen
- [ ] Human Gate: finales synthetisches Demo-Video aufnehmen und Upload autorisieren
- [ ] Human Gate: offizielle Regeln erneut lesen und Devpost-Submit autorisieren

## Aktuelle Blocker

- Keine lokalen technischen Blocker
- Reale Side-Effects, Cloudbetrieb, Video und Einreichung bleiben Nutzer-Gates

## Historie

- **2026-08-21** — Phase-1-Fundament mit 22 Tests lokal abgeschlossen
- **2026-08-21** — Phase-2-FCSA-Dry-Run-Bridge mit 27 Tests lokal abgeschlossen
- **2026-08-21** — Phase-3-Dokumentenbibliothek mit 50 Tests lokal abgeschlossen
- **2026-08-21** — Phase-4-Dokumentversionen mit 59 Tests lokal abgeschlossen
- **2026-08-21** — Phase-5-Profilregeln mit 64 Tests lokal abgeschlossen
- **2026-08-21** — Phase-6-Dokumentaktionspläne mit 77 Tests lokal abgeschlossen
- **2026-08-21** — Phase-7-Dokumenttransformation mit 87 Tests lokal abgeschlossen
- **2026-08-21** — Phase-8-Typpakete mit 92 Tests lokal abgeschlossen
- **2026-08-21** — Phase-9-Ordnerbeobachtung mit 98 Tests lokal abgeschlossen
- **2026-08-21** — Phase-10-Scanläufe mit 104 Tests lokal abgeschlossen
- **2026-08-21** — Phase-11-Aktionsausführung und Undo mit 111 Tests lokal abgeschlossen
- **2026-08-21** — Phase-12-Ordner-Aufräumlauf mit 117 Tests lokal abgeschlossen
- **2026-08-21** — Phase-13-Beobachtungsroutine mit 124 Tests lokal abgeschlossen
- **2026-08-21** — Phase-14-Mehrfach-Watch-Queue mit 128 Tests lokal abgeschlossen
- **2026-08-21** — Phase-15-Scheduler-Handoff mit 133 Tests lokal abgeschlossen
- **2026-08-22** — Phase-16-Kontaktregister mit 146 Tests lokal abgeschlossen
- **2026-08-22** — Phase-17-Kalender-Handoff mit 159 Tests lokal abgeschlossen
- **2026-08-22** — Phase-18-FindCall mit 170 Tests lokal abgeschlossen
- **2026-08-22** — Phase-19-Finanzstore und Abokandidaten mit 179 Tests lokal abgeschlossen
- **2026-08-22** — Phase-20-Haushaltsbestand mit 189 Tests lokal abgeschlossen
- **2026-08-22** — Phase-21-Medikamentenplan und Einnahmebestätigung mit 198 Tests lokal abgeschlossen
- **2026-08-22** — Phase-22-Gesundheitsdossier und extraktive Arztbericht-Synthese mit 204 Tests lokal abgeschlossen
- **2026-08-22** — Wettbewerbsfahrplan auf 36 Phasen konkretisiert; Phase 23 gestartet
- **2026-08-22** — Phase-23-Versicherungs- und Vertragscockpit mit 208 Tests lokal abgeschlossen
- **2026-08-22** — Phase-24-Korrespondenzstudio mit 213 Tests lokal abgeschlossen
- **2026-08-22** — Phase-25-Artefakt-, Medien- und Designstudio mit 218 Tests lokal abgeschlossen
- **2026-08-22** — Phase-26-Mail-Connector mit 225 Tests lokal abgeschlossen
- **2026-08-22** — Phase-27-Kalenderconnectoren mit 233 Tests lokal abgeschlossen
- **2026-08-22** — Phase-28-LLM-Note-Dienst mit 241 Tests lokal abgeschlossen
- **2026-08-22** — Phase-29-Steuerarbeitsunterlage mit 249 Tests lokal abgeschlossen
- **2026-08-22** — Phase-30-Wetter-/Newspaper-Desktopbrief mit 257 Tests lokal abgeschlossen
- **2026-08-22** — Phase-31-Bescheidverständnis mit 264 Tests lokal abgeschlossen
- **2026-08-22** — Phase-32-Verwaltungsentwürfe mit 270 Tests lokal abgeschlossen
- **2026-08-22** — Phase-33-Leistungs-/Fördervorcheck mit 277 Tests lokal abgeschlossen
- **2026-08-22** — Phase-34-Law-Checker-Anbindung und Rechtsänderungsmonitor mit 288 Tests lokal abgeschlossen
- **2026-08-22** — Phase-35-Loopback-API, GUI und OS-Kontogrenze mit 297 Tests lokal abgeschlossen
- **2026-08-22** — Phase-36-Härtung, Strands-Agent, Demo und Submission-Paket mit 333 Tests lokal abgeschlossen
- **2026-08-22** — Öffentliches Wettbewerbsrepository `ellmos-ai/FolderHome` freigegeben
- **2026-08-21** — Repository als neues, lokales Integrationsprojekt angelegt
