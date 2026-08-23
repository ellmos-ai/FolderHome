# Workflow: Begrenzte Anbieteranfrage mit FindCall vorbereiten

[English](./findcall.md) | **Deutsch**

> **Last verified:** 2026-08-23  
> **Frequency:** bei Bedarf für Termin- oder Angebotssuchen  
> **Duration:** Sekunden für lokale Planung und Fixture-Simulation

## Zweck

Eine serielle Anfrage für einen Termin oder ein Angebot bei ausdrücklich konfigurierten Kandidaten vorbereiten. FindCall wendet Zeit-, Orts- und Preisgrenzen des Nutzers an, stoppt nach dem ersten gültigen Ergebnis und geht niemals eigenständig eine Verpflichtung ein.

Der aktuelle FolderHome-Masteragent verbindet deterministische Planung und die
strikt lokale Fixture-Simulation über einen typisierten, freigabegebundenen
Adapter. Er telefoniert nicht, greift nicht auf das Netzwerk zu, bucht keinen
Termin und nimmt kein Angebot an.

## Voraussetzungen

- Profil, Anfrageart, Leistung, Ort, Zeitfenster und eine optionale Preisobergrenze sind ausdrücklich festgelegt.
- Kandidaten- und Fixture-Dateien verwenden die dokumentierten FindCall-Schemata.
- HungryCall- und Ringedingeding-Probes entsprechen bei einer Prüfung ihren gepinnten, sauberen Revisionen.
- Ein späterer Live-Lauf benötigt zusätzlich einen ausdrücklich konfigurierten Connector und eine workflowspezifische Freigabe.
- Notfallanfragen und Diagnosewünsche sind keine FindCall-Anwendungsfälle.

## Schritte

1. **Auftrag prüfen** — fehlende Grenzen, Verpflichtungen, Notfallinhalte und Diagnosewünsche zurückweisen.
2. **Kandidaten laden** — nur die ausdrücklich konfigurierte Kandidatenmenge verwenden; keine versteckte Verzeichnis- oder Kontaktquelle ableiten.
3. **Plan bilden** — passende Kandidaten deterministisch ordnen und maskierte Rufnummern, Zeitfenster, Entfernung, Preisgrenze und Stoppbedingungen anzeigen.
4. **Exakten Plan prüfen** — Plan-ID, ausgewählte Aktionen, Kandidatenreihenfolge und sämtliche Grenzen kontrollieren.
5. **Live-Wirkung gesondert freigeben** — eine gewöhnliche Chatbestätigung reicht nicht; ein späterer Connector muss die exakte Workflow-Freigabe erhalten.
6. **Seriell ausführen** — jeweils nur einen Kandidaten anfragen und nach dem ersten Ergebnis stoppen, das alle harten Grenzen erfüllt.
7. **Evidenz berichten** — Versuche, Ablehnungsgründe, gegebenenfalls das akzeptierte Ergebnis und ausdrückliche Wirkungsflags zurückgeben.

## Abnahmekriterien

- [ ] Es wurde kein unkonfigurierter Kandidat, kein Verzeichnis und kein Connector verwendet.
- [ ] Rufnummern sind in Plänen und Berichten maskiert.
- [ ] Zeit-, Leistungs-, Orts- und Preisgrenzen bleiben erhalten.
- [ ] Es wurde keine Buchung, Bestellung, Diagnose oder finanzielle Verpflichtung ausgelöst.
- [ ] Lokale Fixture-Berichte weisen `simulated=true`, `network_used=false` und `phone_calls_placed=false` aus.
- [ ] Eine Live-Anfrage wird nur berichtet, wenn Connector und exakte Freigabe unabhängig nachgewiesen sind.

## Fallstricke

- Ein Masteragenten-Plan ist keine Erlaubnis für einen Telefonanruf.
- Der lokale Fixture-Provider belegt die Orchestrierung, nicht Telefonie oder Anbietererreichbarkeit.
- HungryCall liefert das serielle Early-Stop-Muster; sein Restaurantmodell wird nicht für Arztpraxen oder Werkstätten wiederverwendet.
- Ringedingeding bleibt ein eigener Koordinations-Plugin und ist kein Live-Anruftransport.
- Geänderte oder unsaubere Plugin-Checkouts entwerten revisionsgebundene Probes.

## Verwandte Dokumente

- [`../docs/phase18-findcall-reuse-and-plan.de.md`](../docs/phase18-findcall-reuse-and-plan.de.md)
- [`../ARCHITECTURE.de.md`](../ARCHITECTURE.de.md) — FindCall-Sicherheitsgrenze
- [`./master-agent.de.md`](./master-agent.de.md) — semantisches Routing und exakte Freigabe

## Historie

- **2026-08-23** — Strikt lokalen Fixture-Executor über eine exakte Freigabe verbunden
- **2026-08-23** — Als ausdrücklicher, fail-closed Masteragenten-Endpunkt ergänzt
