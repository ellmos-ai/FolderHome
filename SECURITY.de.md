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
Verfügbarkeit.

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
