# Security Policy

[English](./SECURITY.md) | **Deutsch**

FolderHome verarbeitet potenziell sensible Haushalts-, Gesundheits-, Finanz-
und Verwaltungsdokumente. Der Wettbewerbsstand ist deshalb local-first,
fail-closed und trennt Planung, Freigabe und Ausführung.

## Unterstützter Stand

Sicherheitskorrekturen werden im aktuellen Wettbewerbsstand auf dem Branch
`main` gepflegt. Es gibt keinen produktiven Cloudbetrieb.

## Sicherheitsgrenzen

- Das Betriebssystemkonto samt Dateirechten ist die Sicherheitsgrenze.
  Familienprofile organisieren Regeln und Ansichten, sind aber keine ACLs.
- Der lokale HTTP-Adapter bindet ausschließlich an `127.0.0.1`, benötigt ein
  kurzlebiges Sitzungstoken, prüft Host und Origin exakt und erlaubt kein CORS.
- Gleichzeitige HTTP-Anfragen und unvollständige Verbindungen besitzen harte
  Obergrenzen und Timeouts.
- Die synthetische Unfalllaufzeit erstellt und leert ausschließlich ihren
  markierten Arbeitsbereich. Sie verweigert Dateisystemwurzeln, symbolische
  Links und bereits vorhandene, nicht leere Verzeichnisse ohne den exakten
  FolderHome-Eigentumsmarker.
- Datei-, Parser- und Rendererarbeit ist durch nicht abschaltbare Budgets für
  Einträge, Dateien, Bytes, PDF-Seiten, Bildframes, Pixel, Text und Ausgaben
  begrenzt.
- Der Strands-Master besitzt fünf begrenzte Werkzeuge: zwei profilgebundene
  Nur-Lese-Dokumentwerkzeuge, die Fähigkeitssuche, die Suche nach logischen
  Ressourcen und die Fachagentenberatung. Physische Ressourcen-Locator gelangen
  weder in den öffentlichen Katalog noch in einen ressourcengebundenen Plan.
  Ein Fachagent erhält genau einen Planungsendpunkt und keinen Executor. Turns,
  Toolaufrufe, Prompt, Toolergebnis und Antwort sind endlich begrenzt;
  Toolausführung erfolgt sequenziell.
- Ein Gespräch erteilt niemals eine Freigabe. Der Browser muss Plan-ID,
  SHA-256 und die exakte Schrittmenge über einen getrennten Endpunkt senden.
  Nur ein Plan mit vorbereiteter typisierter Ausführungshülle kann höchstens
  einmal laufen; die Ausführung weist ein eigener Fachbericht nach.
- Die Laufzeitabdeckung ist explizit: verbunden, direkt nur lesend, nur planend
  und nicht verbunden sind verschiedene Zustände. Fehlende Adapter blockieren
  und fallen weder auf Shell noch auf beliebige Pfade, allgemeines HTTP oder
  allgemeine CLI-Ausführung zurück.
- Der Gesprächsverlauf lebt ausschließlich im Prozessspeicher, ist nach Profil
  organisiert, aber keine Autorisierungsgrenze, und standardmäßig auf 24
  Nachrichten begrenzt. Ein ausdrücklicher Reset verwirft zusätzlich die
  unbestätigten Pläne dieses Profils.
- Das deterministische Agenten-Fixture verwendet kein Netzwerk. Amazon
  Bedrock benötigt Modell-ID, Region sowie getrennte ausdrückliche Freigaben
  für Netzwerkzugriff und die Weitergabe potenziell sensibler lokaler
  Suchergebnisse. Jeder Modellaufruf verwendet begrenzte Verbindungs- und
  Lese-Timeouts sowie insgesamt genau einen SDK-Versuch.
- Jeder Provider, der über HTTP spricht, teilt sich ein endliches Budget:
  `model_timeout_seconds` (Standard 120, zulässiger Bereich 5 bis 900). Ein
  Modell, das darin nicht antwortet, erzeugt einen benannten Fehlschlag mit
  Nennung des Budgets statt einer hängenden Anfrage. Bedrock behält sein eigenes
  Paar aus Verbindungs- und Lese-Timeout.
- Ein API-Schlüssel ist nie eine Einstellung. Gelesen und geschrieben werden
  ausschließlich die zwei Namen `ANTHROPIC_API_KEY` und `OPENAI_API_KEY`, in
  einer `.env`-Datei neben `launch.json`; jede andere Zeile dieser Datei bleibt
  unangetastet und wird nie ausgewertet. Der Schlüssel reist außerhalb des
  Plans, kommt also in keinen Plan-Hash, keine Vorschau, keinen Status, keinen
  Bericht und kein Log, und der Zustand meldet ausschließlich, ob einer
  hinterlegt ist. Die Datei wird atomar mit Modus `0o600` und ohne Sicherung
  geschrieben, denn die Sicherung eines Schlüssels wäre eine zweite Kopie eines
  Schlüssels. Dieser Modus greift dort, wo die Plattform ihn durchsetzt; unter
  Windows schützt die Datei die Grenze des Benutzerkontos.
- Der Ordnerdialog des Einrichtungsprogramms läuft in einem Kindprozess, ist auf
  einen offenen Dialog serialisiert und gibt nach fünf Minuten auf, damit ein
  abgebrochener Dialog nicht der letzte bleibt. Erreichbar ist er nur über die
  tokengeprüfte Loopback-Route des Einrichtungsprogramms, nie aus der App. Er
  antwortet absichtlich mit dem gewählten Pfad: Ordner zu benennen ist der Zweck
  des Einrichtungsprogramms. Die Regel, dass physische Adressen aus Nutzdaten
  heraushalten, gilt der Anwendungs-API, die nie einen Pfad zurückgibt.
- Der optionale AgentCore-Adapter akzeptiert ausschließlich JSON-Prompts,
  verweigert Uploads, beliebige lokale Pfade, doppelte JSON-Schlüssel und
  nichtsynthetische Anfragen und gibt weder Hostpfade noch Secrets zurück.
  Laufzeitsitzungen, parallele Aufrufe, Anfragegrößen und Socket-Zeit sind
  begrenzt; ausgeschöpfte Kapazität blockiert mit einer ausdrücklichen
  Service-unavailable-Antwort.
- Der öffentliche statische Showcase besitzt kein Backend, führt keine
  Netzwerkanfrage aus und ändert keine Dateien. Er ist sichtbar als
  skriptbasierter synthetischer Rundgang gekennzeichnet und kein Nachweis eines
  bereitgestellten AgentCore-Endpunkts.
- Amtliche Leistungslinks werden per HTTPS, exaktem Host und Publisherbindung
  geprüft. IP-Adressen, Zugangsdaten, Ports und Domain-Lookalikes werden
  blockiert.
- Schreibende Aktionen benötigen fachlich getrennte Approvals und Gates,
  prüfen Quellhashes erneut und überschreiben vorhandene Ziele nicht. Verbundene
  Chat-Schreibpfade umfassen append-only persönliche Notizen,
  Medikamenteneinnahme-Evidenz, ressourcengebundene Dokumentbündel,
  Kontakt-State, lokale Korrespondenzdateien und den eigenen
  FolderHome-Kalender. Vollständige Korrespondenzinhalte bleiben lokal.
- Live-Mail, Live-Kalender, Telefon, Banking, Upload und Veröffentlichung sind
  keine impliziten Agentenfähigkeiten.

## Vertraulichkeit und Testdaten

Repository, Tests und Wettbewerbsdemo verwenden ausschließlich synthetische
Daten. Reale Dokumente, Zugangsdaten, Sitzungstoken, Mailadressen,
Kontokennungen oder Gesundheitsinformationen dürfen nicht committed,
hochgeladen oder in öffentliche Demoartefakte übernommen werden.

Die Demoausgabe nennt ausdrücklich, dass sie synthetisch ist. Ein Fixture-Lauf
belegt den Strands-Agentenloop, aber weder Modellqualität noch AWS-
Verfügbarkeit. Keine Demoaktion sendet eine E-Mail, führt einen Anruf aus,
erstellt einen externen Kalendereintrag, lädt ein Dokument hoch oder archiviert
eine ältere Police automatisch.

## Sicherheitsprüfung

Der Phase-36-Scan erfasste 357 Dateien auf 12 von 12 deklarierten Flächen und
meldete drei Befunde. Behoben wurden unbegrenzte Dokumentenarbeit, frei
behauptbare amtliche Leistungshosts und unbegrenzte Loopback-Verbindungen.
Der unveränderliche Vorfix-Scan und sein separater Fix-Report werden im lokalen
Scanartefakt aufbewahrt; der Abschlussaudit dokumentiert zusätzliche
Post-Fix- und Strands-Prüfungen.

Reproduzierbare lokale Prüfungen:

```powershell
python -m pytest
python -m ruff check .
python -m compileall -q src tests
python -m folderhome plugins validate --json
python _tools\doc-lint
python _tools\workflows-sync --check
```

## Meldung einer Schwachstelle

Bitte keine echten sensiblen Beispieldaten in ein öffentliches Issue stellen.
Bis ein öffentlicher Sicherheitskontakt freigegeben wurde, Schwachstellen
vertraulich an den Repository-Eigentümer melden. Eine Meldung sollte
betroffene Version, minimale Reproduktion, erwartete Auswirkung und bekannte
Workarounds enthalten.

## Keine Sicherheitsbehauptung über Fachentscheidungen

FolderHome ist keine medizinische Diagnose, Rechts-, Steuer-, Leistungs- oder
Finanzberatung. Evidenz, Fristenanzeigen, Konflikte und Kandidaten ersetzen
keine fachliche Prüfung. Ein technisch erfolgreiches Toolergebnis beweist
weder Vollständigkeit noch sachliche Richtigkeit eines Quelldokuments.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
