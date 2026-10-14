# Datenschutz und Datenflüsse

[English](./PRIVACY.md) | **Deutsch**

**Geprüft:** 14. September 2026. Beschrieben werden die Datenflüsse der Software,
keine rechtliche Konformitätsbescheinigung oder Datenschutzerklärung eines Hosters.

## Was auf diesem Computer bleibt

FolderHome liest ausdrücklich ausgewählte Ressourcen. Lokale Extraktion,
Dokumentensuche, Haushaltsstores, Briefrendering und Freigabeprüfungen laufen
unter deinem Betriebssystemkonto. Profile organisieren Haushaltsarbeit; sie
trennen Personen innerhalb desselben Kontos **nicht** sicher voneinander.

| Daten | Speicherung / Lebensdauer |
|---|---|
| Quelldokumente | Deine ausgewählten Ordner; Ingest verändert sie nicht |
| Suchindex und Fachzustand | Konfigurierte lokale SQLite-Datenbanken und Zustandsordner |
| Erzeugte Briefe, Bündel und Belege | Lokale Ausgabedateien; Schließen der App löscht sie nicht |
| Chatverlauf, offene Pläne, Rezeptläufe und Ergebnisansichten | Begrenzter Prozessspeicher; kein Wiederaufnahmearchiv nach Neustart |
| Google-Terminversionen und Kalender-/Mail-Versuchsledger | Privater dauerhafter Zustand gegen unsicheres Wiederholen |
| Provider-Zugangsdaten | Konfigurierte private Dateien; kein Bestandteil modellseitiger Ressourcenkataloge |

Lokale Dateien können selbst in einem synchronisierten oder gesicherten Ordner
liegen. **Lokale Verarbeitung schaltet die Cloud-Synchronisierung deines
Betriebssystems nicht ab.** Dateirechte und Speicherschutz gehören zur Grenze
des Betriebssystemkontos, nicht zum FolderHome-Profilwähler.

## Was den Computer verlassen kann

| Optionaler Weg | Offenlegung und Grenze |
|---|---|
| Gehostetes Modell oder Ollama außerhalb von Loopback | Prompt, gespeicherter Gesprächskontext und ausgewählter Werkzeugkontext gehen nach Netzwerk- und Datenfreigabe an den konfigurierten Modellendpunkt |
| Google-Kalender | Freigegebene Termindaten und authentifizierte API-Anfragen gehen an Google; Token-Erneuerung kontaktiert zusätzlich Googles OAuth-Endpunkt |
| Eigener Mailentwurf | Die vorbereitete Nachricht einschließlich Empfängerheadern und Inhalt geht an den konfigurierten IMAP-Anbieter; **ungesendet heißt nicht ungeteilt** |
| Statischer öffentlicher Showcase | Der Hostingdienst erhält gewöhnliche Webanfragen; der Showcase liest keine lokalen Haushaltsdokumente |

Das deterministische Fixture führt keinen Modell-Netzwerkaufruf aus.
Loopback-Ollama verwendet einen lokalen Endpunkt; eine private Netzwerkadresse
liegt trotzdem außerhalb dieses Computers. Vor Remote-Modellaufrufen ersetzt
die standardmäßig aktive Cloud-Pseudonymisierung bekannte lokale Identitäten
und konservativ erkannte sensible Muster durch stabile, prozesslokale
Platzhalter und stellt sie lokal wieder her. Das verringert die Offenlegung,
ist aber keine Anonymisierung: unbekannte Kennungen in Freitext können erhalten
bleiben. Die ausdrücklichen Netzwerk- und Sensitivdatenfreigaben bleiben Pflicht.
Google-Metadatenabfrage benötigt
eine eigene Lesefreigabe. Kalenderschreibvorgänge und Mailentwürfe benötigen
eigene Startgates **und** exakte Planbestätigungen. Die optionale
AgentCore-Wettbewerbslaufzeit nimmt die synthetische Demo an, keine privaten
Dokumentuploads. Aufbewahrungsregeln der Provider liegen außerhalb der Kontrolle
von FolderHome; ein lokaler Reset löscht keine Kopien bei einem externen Dienst.

## Was Reset und Schließen nicht löschen

Gesprächsreset löscht den gespeicherten Chat und offene Pläne des gewählten
Profils und schließt seine Rezeptläufe. Er nimmt bestätigte Wirkungen nicht
zurück und löscht weder Quelldokumente noch gespeicherte Ausgaben, Fachstores
oder dauerhafte Connector-Ledger. Schließen der App signalisiert ihren eigenen
Scheduler-Workern; eine laufende begrenzte Prüfung kann noch enden. Das ist
kein globaler Stopp anderer App-Instanzen.

Es gibt keinen universellen Befehl zum Löschen aller personenbezogenen Daten
oder externer Konten. Insbesondere **kein Versuchsledger entfernen, um einen
unklaren Vorgang erneut zu versuchen**: Die externe Wirkung kann bereits
existieren. Zuerst Providerzustand und gespeicherte Nachweise abgleichen.
Lokalen Zustand zu löschen widerruft weder eine OAuth-Zustimmung noch entfernt
es einen IMAP-Entwurf oder Google-Termin.

## Diagnosedaten weitergeben

Für Issues, Screenshots und öffentliche Nachweise synthetische Beispiele
verwenden. OAuth-JSON, API-Schlüssel, Postfachpasswörter, Sitzungstoken und echte
Haushaltsdateien nicht weitergeben. Berichte und erzeugte Artefakte können
private Fachinhalte enthalten, auch wenn Ressourcenpfade verborgen sind.
Vor einer Weitergabe prüfen.

Implementierungsgrenzen und vertrauliche Meldungen:
[Sicherheit](./SECURITY.de.md). Ausführliche Gates:
[Kalender](./docs/phase27-calendar-connector-plan.de.md),
[Mail](./docs/phase26-mail-connector-plan.de.md),
[Scheduler](./docs/phase15-scheduler-handoff-plan.de.md).
