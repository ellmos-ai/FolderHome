# Phase 27 — Kalender-Connectoren und Erinnerungs-Handoffs

[English](./phase27-calendar-connector-plan.md) | **Deutsch**

**Status:** Google-v3-Gateway und Planausführung implementiert; App-/Zugangsdatenanbindung offen  
**Aktualisiert:** 2026-09-09 (ursprüngliche Phasenabnahme: 233 Tests am 2026-08-22)  
**Produktname im Wettbewerb:** FolderHome

## Ziel

FolderHome verbindet den vorhandenen Phase-17-Kalenderkern mit expliziten
Kalenderkonten und providerneutralen Operationen. Ereignisse aus Dokumenten
werden weiterhin nur als belegte Kandidaten behandelt. Erstellen,
Aktualisieren, Löschen und Erinnern sind getrennte Operationen; ein Plan ruft
keinen Connector auf.

## Revisionsinventur

| Baustein | Revisionsbefund | Phase-27-Rolle |
|---|---|---|
| UpToday | sauberer lokaler Checkout `7582ca87e17e458bb99a7379d2c54003c15415a4`; 21 ICS-Tests grün | vorhandenen RFC-5545-Dateihandoff aus Phase 17 wiederverwenden, kein Live-Sync |
| Routinika | dateibasierter `routinika-bundle-v1`-Vertrag; `portable_bundle.py` SHA-256 `3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2` | hashgebundene Designreferenz, bis zu einem Live-Connector-Vertrag blockiert |
| Google Calendar | lokaler Skill `google-calendar` 1.2.5 | agentischer, gesondert freizugebender Handoff; kein Lauf im Wettbewerbscode |
| FolderHome Phase 17 | lokaler Kalenderstore und UpToday-ICS-Ausgabe | Quelle für Kandidaten, Profilauflösung und lokalen Handoff; kein Doppelbau |
| FolderHome Synthetic Calendar | `working-tree`, neu im Wettbewerbszeitraum | deterministischer No-Network-Fixture-Provider für die lokale Abnahme |

Die Inventur ist ein Snapshot vom 22. August 2026. Der Routinika-Bestand in
OneDrive wurde nur über FileCommander gelesen und gehasht. Kein fremder
Checkout, Kalender oder Benutzerkonto wurde verändert.

## Neuer gekapselter Kern

- `folderhome.contracts.calendar_connectors`
- `folderhome.application.calendar_connectors`
- `folderhome.capabilities.calendar_connector_gateway`
- `folderhome-calendar-connectors`-Skill

Der Vertrag modelliert Konto, Erinnerung, Anfrage, Route, Ereignispayload,
Operation, Freigabe, Provider-Ereignisreferenz und Ausführungsreport. Die
Konfiguration darf nur eine `connector://`-Referenz enthalten, keine Tokens.
Unbekannte Felder werden fail-closed abgewiesen.

## Wiederverwendung statt Doppelbau

Der Connectorplan wird ausschließlich auf einem vollständigen
`folderhome.calendar-handoff-plan.v1` aus Phase 17 aufgebaut. Dadurch bleiben
Dokumentextraktion, Zeilenevidenz, Profil-/Bereichsregel, Zeitzone,
Duplikaterkennung, lokaler Store und ICS-Ausgabe an einer Stelle.

- UpToday-Erstellung wird an den bestehenden ICS-Handoff delegiert.
- Der lokale FolderHome-Kalender bleibt der vorhandene Phase-17-Store.
- Routinika bleibt eine Dateiübergabe-Referenz und wird nicht als Live-Sync
  ausgegeben.
- Google erhält ein explizites, prüfbares Handoff-Payload, aber der Skill wird
  im Plan nicht aufgerufen.

`backend_source` und `source_rule_ids` werden in den Connectorplan übernommen.
Damit ist sichtbar, ob das Ziel aus Konfigurationsstandard oder Profilregel
stammt.

## Google-Handoff

Ein Google-Erstellungspayload enthält immer eine explizite `calendar_id`, eine
leere Teilnehmerliste, `transparency=opaque`, strukturierte Popup-Reminder und
Start-/Endzeiten mit UTC-Offset sowie IANA-Zeitzone. Update und Löschen bleiben
blockiert, bis eine bestehende Provider-Ereignisreferenz vorliegt. Wiederholte
Ereignisse benötigen später zusätzlich das bewusste Auswählen von Master oder
Einzelinstanz.

## Synthetische Abnahme

Der synthetische Provider akzeptiert nur exakt hash- und aktionsgebundene
Freigaben für `create` und optional `remind`. Er besitzt keinen Netzwerkpfad,
schreibt keinen Live-Kalender und gibt ausschließlich synthetische
Provider-Ereignisreferenzen zurück. Doppelte Idempotenzschlüssel werden
innerhalb eines Gateway-Laufs abgewiesen. Ein als netzwerkpflichtig
deklarierter Gateway wird ohne Netzwerkfreigabe vor dem Aufruf gestoppt.

## Produktgrenzen

### Freigabeintegrität — 9. September 2026

Der Planhash umfasst den vollständigen öffentlichen Plan einschließlich Konto,
Profil, Route, Ereignisfeldern und Operationen. Ein `input_sha256` bindet
zusätzlich die vollständige Anfrage, Kontokonfiguration und den Phase-17-Handoff-
Snapshot, ohne deren private Quellpfade oder Connectorreferenzen im öffentlichen
Plan offenzulegen. Das bindet einen Snapshot; Quelldateien werden bei der
Ausführung **nicht** erneut gelesen.

Die Ausführung berechnet den Inhaltshash beim Einstieg sowie vor und nach jedem
Ereignis neu. Provideridentität, Revision und simulierte/Netzwerk-/Live-Effekte
müssen zur freigegebenen Route passen. Eine synthetische Route kann auch mit
Netzwerkfreigabe nicht zur Live-Route werden. Der genaue Payload wird vor dem
Gateway-Aufruf gehasht und danach erneut geprüft, auch wenn nicht freigegebene
Erinnerungen daraus entfernt wurden.

**Ältere Freigaben benötigen einen neuen Vorschlag und eine erneute Prüfung.**
Ein nach dem Gateway-Aufruf erkannter Fehler macht eine mögliche Wirkung nicht
rückgängig. Nicht automatisch wiederholen oder fehlende Erfolgsnachweise als
Beweis ausbleibender Wirkung behandeln. Die nachfolgende Gateway-Implementierung
ergänzt dauerhafte Idempotenz, Behandlung unklarer Ergebnisse und Provider-
Readback. App-/Zugangsdatenanbindung und Live-Abnahme bleiben offen.

Lokale Verifikation: 19 neue Rot-Grün-Integritätsregressionen, 38 fokussierte
Kalendertests und eine Gesamtsuite mit **831 bestanden in 251,39 Sekunden**,
Warnungen als Fehler behandelt. Die reale CLI `calendar connector-simulate`
lieferte eine synthetische Ereignisreferenz mit beiden Live-Kalender- und
Netzwerkflags auf false.

### Google-v3-Implementierung — 9. September 2026

Die Anwendung kann genaue `create`/`remind`-Freigaben über
`folderhome.bridges.google_calendar.GoogleCalendarGateway` ausführen. Nur die native
Route `google-calendar@v3` mit konkreter Kalender-ID wird ausführbar;
historische Skillrouten bleiben prüfpflichtig. Ein typisierter Marker
`external_connector_required` erlaubt das Ersetzen einer fehlenden Route, ohne
Zeitkonfliktsperren der Dokumente aufzuheben. Unbekannte oder unmarkierte Sperren
bleiben bestehen.

Der Gateway liest eine stabile entfernte Ereignis-ID, reserviert einen Versuch
atomar in einem privaten SQLite-Ledger, versucht höchstens ein POST und vergleicht
danach die tatsächlichen Ereignisfelder. Ein fehlgeschlagenes erstes GET verbraucht
keinen Schreibversuch. Ein möglicherweise ausgeführtes POST wird niemals automatisch
wiederholt. Umbenannte lokale Konten oder gewechselte Zugangsdatenreferenzen setzen
das Ledger nicht zurück. Der tokenabhängige Alias `primary` muss durch die spätere
Kontenanbindung zunächst in eine konkrete Kalender-ID aufgelöst werden.

Sowohl die genaue Freigabe als auch das getrennte Netzwerk-Gate des Gateways müssen
die Ausführung ausdrücklich erlauben. Der Transport bindet den Google-HTTPS-Host,
folgt keinen Redirects, begrenzt Antwortinhalte auf 1 MiB und hält vertrauliche
Zugangsdaten-/Providerfehler aus sichtbaren Fehlermeldungen heraus. Tokens und
Ereignistexte werden nicht im Ledger gespeichert. `CalendarConnectorOutcomeUnknown`
erhält bestätigte Referenzen, wenn ein späteres Ereignis fehlschlägt; fehlender
Erfolg bedeutet kein Zurückrollen.

Lokale Verifikation: **107 Kalendertests** und **102 Workflow-, Rezept- und
Ressourcentests bestanden**, Warnungen als Fehler behandelt. Die Tests verwenden
echten Gateway, Executor und temporäres Ledger hinter einer HTTP-In-Memory-Grenze.
Das belegt keine OAuth- oder Live-Kontenabnahme. App-/CLI-Ressourcenbindung, private
Zugangsdatenauflösung, Live-Tests und Referenz-/ETag-basierte Änderungen bleiben offen.

### Verbleibende Grenzen

- `ready` oder `review_required` bedeutet nicht, dass ein Kalender verändert
  wurde.
- Eine synthetische Ereignisreferenz ist kein Live-Kalendereintrag.
- Es wurden weder Google-Zugangsdaten gelesen noch Google-Tools aufgerufen.
- UpToday erhält eine ICS-Datei erst über den getrennt freigegebenen
  Phase-17-Handoff.
- Routinika-Live-Sync, Update, Löschen und Serienereignisse bleiben offen.
- Automatische Terminerkennung ist best effort und besitzt keine
  Vollständigkeitsgarantie.
- Profile innerhalb eines Betriebssystemkontos sind organisatorische Regeln,
  keine kryptografische Mandantentrennung.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
