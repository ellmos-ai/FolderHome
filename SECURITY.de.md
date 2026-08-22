# Security Policy

[English](./SECURITY.md) | **Deutsch**

FolderHome verarbeitet potenziell sensible Haushalts-, Gesundheits-, Finanz-
und Verwaltungsdokumente. Der Wettbewerbsstand ist deshalb local-first,
fail-closed und trennt Planung, Freigabe und Ausführung.

## Unterstützter Stand

Sicherheitskorrekturen werden im aktuellen Wettbewerbsstand auf dem Branch
`phase1-foundation` gepflegt. Es gibt noch keine veröffentlichte Release-Serie
und keinen produktiven Cloudbetrieb.

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
- Der Strands-Agent besitzt ausschließlich zwei profilgebundene read-only
  Tools. Turns, Toolaufrufe, Prompt, Toolergebnis und Antwort sind endlich
  begrenzt; Toolausführung erfolgt sequenziell.
- Das deterministische Agenten-Fixture verwendet kein Netzwerk. Amazon
  Bedrock benötigt Modell-ID, Region sowie getrennte ausdrückliche Freigaben
  für Netzwerkzugriff und die Weitergabe potenziell sensibler lokaler
  Suchergebnisse.
- Amtliche Leistungslinks werden per HTTPS, exaktem Host und Publisherbindung
  geprüft. IP-Adressen, Zugangsdaten, Ports und Domain-Lookalikes werden
  blockiert.
- Schreibende Aktionen benötigen fachlich getrennte Approvals und Gates,
  prüfen Quellhashes erneut und überschreiben vorhandene Ziele nicht.
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
