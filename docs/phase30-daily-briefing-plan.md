# Phase 30: Lokaler Wetter- und Newspaper-Desktopbrief

**Stand:** 2026-08-22  
**Zweck:** Wetter und ausgewählte Nachrichten aus belegten lokalen Snapshots
zu einem täglichen HTML-Brief bündeln und nach separater Freigabe auf einen
ausdrücklich gewählten Desktop kopieren.

## Bestandsabgleich

Unter den bereits extrahierten lokalen Modulen und Skills wurde kein
eigenständiger Wetter- oder Newspaper-Provider gefunden. Der einzige
passende Altbestand liegt weiterhin im BACH-Monolithen:

| Merkmal | Befund |
|---|---|
| Repository | `https://github.com/ellmos-ai/bach.git` |
| geprüfter Checkout | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` |
| relevante Dateien | Wetterservice, Newspaper-Generator, Daily Agent |
| relevanter Pfadstatus | unverändert gegenüber Git |
| Gesamtcheckout | fremd verändert; nicht als Runtime geladen |
| Newspaper-Tests | 11/11 grün |
| Lizenz | MIT |

Der Wetterservice ruft `wttr.in` direkt auf. Der Newspaper-Generator liest
die BACH-Datenbank, rendert HTML, startet optional Edge für PDF und kopiert
oder sendet Ergebnisse direkt. Der Daily Agent enthält einen fest codierten
Ort. Diese Kopplungen, impliziten Zeiten und direkten Side-Effects passen
nicht zum FolderHome-Vertrag. Eine erneute Extraktion wurde deshalb nicht
vorgenommen; BACH bleibt nur ausgewiesene Designreferenz.

## Neuer gekapselter Kern

`contracts.daily_briefing` und `application.daily_briefing` sind neuer,
wiederverwendbarer Wettbewerbscode. Sie definieren:

- einen profilierten Briefingauftrag mit explizitem `as_of` und Zeitzone,
- ganzzahlige Wetterwerte und genaue Beobachtungs-/Abrufzeitpunkte,
- Nachrichtenartikel mit HTTPS-Quellen, Publikations- und Abrufzeit,
- Kategorieauswahl und Obergrenzen pro Kategorie,
- Altersgrenzen und sichtbare Warnungen für veraltete Snapshots,
- deterministisches, vollständig escaptes UTF-8-HTML,
- getrennte Render- und Desktopfreigaben mit Hashbindung und Never-overwrite.

Die lokalen Eingabeschemas sind Providerseams. Ein späterer Wetter- oder
RSS-Connector muss genau solche Snapshots schreiben und erhält ein eigenes
Netzwerkgate. Phase 30 erfindet keinen stillen Live-Provider.

## Ablauf und Datenstand

```text
Briefinganfrage + bekanntes Profil + Sensitivitätsfreigabe
  → Wetter- und Nachrichtensnapshot strikt lesen und hashen
  → Zeitstempel gegen explizites as_of prüfen
  → Datenstand fresh oder stale ausweisen
  → Kategorien deterministisch filtern und begrenzen
  → HTML und Planhash ausschließlich im Speicher erzeugen
  → Render-Approval + Output-Gate schreibt eine neue Zwischenausgabe
  → Desktop-Approval + Desktop-Gate kopiert exakt diesen Hash
```

Ein veralteter Snapshot blockiert die Lesbarkeit nicht, wird aber mit
`review_required` und einer konkreten Alterswarnung ausgegeben. Daten aus der
Zukunft, Nicht-HTTPS-Quellen, unbekannte Profile, geänderte Eingabedateien und
vorhandene Ziele blockieren.

Zwischenausgabe und Desktopziel müssen in getrennten Ordnern liegen. Dadurch
kann das Render-Gate nicht still die Desktopzustellung ersetzen. Die
Desktopkopie verwendet exakt den zuvor freigegebenen Ausgabehash.

## Bewusst offene Connector- und Automationsgrenze

`briefing providers` weist Live-Wetter- und Live-News-Connectoren als
`blocked_not_implemented` aus. Der aktuelle Lauf ruft kein Netzwerk auf. Er
registriert auch keinen Betriebssystem-Scheduler. Eine tägliche autonome
Ausführung würde eine dauerhafte Netz-, Ausgabe- und Desktopberechtigung
benötigen; eine solche wiederkehrende Vollmacht wird nicht aus einer
Einzelfreigabe abgeleitet.

Der vorhandene FolderHome-Scheduler bleibt unverändert auf Dokumentroutinen
begrenzt. Ein späterer Briefing-Scheduler muss zuerst Snapshot-Erzeugung,
Fehlerverhalten, Wiederholungen und die wiederkehrende Nutzerfreigabe als
eigenen Vertrag festlegen.

## Abnahme

Die synthetische Abnahme prüft frische und veraltete Snapshots,
Kategoriefilter, Zukunfts- und URL-Grenzen, HTML- und Quellhashbindung,
Never-overwrite sowie separate Render- und Desktop-Gates. Der CLI-Test führt
Plan, Render und Desktopkopie Ende zu Ende aus; Netzwerk und Scheduler bleiben
aus.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
