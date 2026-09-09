# Phase 27 — Kalender-Connectoren und Erinnerungs-Handoffs

[English](./phase27-calendar-connector-plan.md) | **Deutsch**

**Status:** Google-v3-Gateway, private Zugangsdaten und App-/CLI-Adapter implementiert; Live-Abnahme offen  
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
Readback. Die App-/Zugangsdatenimplementierung ist unten beschrieben;
die Live-Abnahme bleibt offen.

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
Das belegt keine OAuth- oder Live-Kontenabnahme. Der folgende Adapter ergänzt diese
Basis; erstmalige Anmeldung, Live-Tests und Referenz-/ETag-basierte Änderungen bleiben offen.

### Private Zugangsdaten und normale App-/CLI-Ausführung

Installiere die optionale Abhängigkeit aus diesem Checkout mit
`python -m pip install ".[calendar]"`. Google-`authorized_user`-JSON bleibt in einer
privaten Datei des Betriebssystemkontos außerhalb von Repository und Dokumentordnern.
FolderHome verwendet `google-auth`, um die bestehende Zustimmung zu laden und ein
abgelaufenes Token zu erneuern. Es startet keine Anmeldung und schreibt erneuerte
Zugangsdaten nicht zurück. Die Erneuerung ist auf eine Anfrage an
`https://oauth2.googleapis.com/token` begrenzt; umgeleitete, fehlgeschlagene oder
übergroße Antworten werden abgewiesen. Angefragte und ausdrücklich gewährte Scopes
müssen `https://www.googleapis.com/auth/calendar.events` enthalten.

Der Workflow benötigt diese fünf Ressourcenzwecke:

| Zweck | Art | Operationen |
|---|---|---|
| `calendar.source` | `directory` | `list`, `read`; `sensitive_read` nur nach Freigabe |
| `calendar.configuration` | `file` | `read` |
| `calendar.connector_accounts` | `file` | `read` |
| `calendar.google_credentials` | `file` | `read` |
| `calendar.connector_ledger` | `directory` | `read`, `state_write` |

Deklariere Quelle, Zugangsdaten und Ledger ausdrücklich im privaten Register.
Konfigurations- und Kontendateien können stattdessen über `--calendar-config` und
`--connector-accounts` angegeben werden, auch über gespeicherte Einrichtungsoptionen.
Diese Optionen ergänzen ausschließlich lesbare Bindungen für die jeweiligen Profile;
sie speichern keine neuen Registereinträge und erteilen keine Google-Schreibfreigabe.

Jede Vorbereitung liest das private Register erneut. Eine gespeicherte Ressource
mit gleicher ID ersetzt die gesamte Startbindung. Ein überlappender Zweck ersetzt
sie nur für die angegebenen Profile; andere Profile bleiben nutzbar. Auch schwächere
gespeicherte Rechte haben Vorrang. Bereits beim Start gespeicherte Ressourcen werden
nach Entfernen niemals aus Startoptionen wiederhergestellt. Geänderte Dateien oder
Registerinhalte machen eine alte Freigabe ungültig: Einen frisch vorbereiteten Plan
prüfen und bestätigen.

Die Kontoreferenz muss `connector://google-calendar/<credential_resource_id>` lauten.
Das konfigurierte Konto benötigt `google-calendar@v3` und eine konkrete Kalender-ID
statt `primary`; die Profilrichtlinie muss Google auswählen. Der normale App-/CLI-
Einstieg bietet dann das geschlossene Anfrageschema `calendar-connectors` an.
Starte mit `--approve-calendar-write` und bestätige den genauen vorbereiteten Plan
separat. Chatwunsch, konfiguriertes Konto oder Start-JSON erteilen diese Schreibfreigabe nicht.

Die Vorbereitung liest keine Zugangsdaten und erzeugt kein Ledger. Die Ausführung
rekonstruiert den Plan aus aktuellen Profilen, Quellen, Konfigurationen und
Ressourcenrechten vor der Zugangsdatenauflösung sowie vor/nach jeder Kalenderanfrage.
Geänderte Eingaben oder entzogene Rechte stoppen weitere Wirkungen, auch lokale
Bestätigungsschreibvorgänge. Unklare/teilweise Ergebnisse bleiben an der Workflow-
Grenze typisiert; bestätigte Referenzen bleiben an der Ausnahme erhalten und werden
wie unten beschrieben zugestellt. Die Unterstützung bei der Konteneinrichtung folgt unten.
Nur ausdrücklich beim Start gebundene lesbare Konfigurations- und Kontendateien
bleiben beim erneuten Registerlesen erhalten; Rechte für Zugangsdaten, Quellen und
Ledger ergänzt dieser Adapter niemals automatisch.

Das Kalenderkontoformular der Einrichtung kann jetzt eine **vorhandene private
OAuth-Datei** und einen **vorhandenen privaten Nachweisordner** binden. Wähle Google,
`google-calendar`, `v3`, eine konkrete Kalender-ID und
`connector://google-calendar/<credential_resource_id>`. Gib beide absoluten Pfade
an und aktiviere den getrennten Schalter für private Ressourcen. Prüfe vor der
Bestätigung des Setup-Plans die erzeugte Lesebindung für Zugangsdaten und
`read`/`state_write` für den Nachweisordner. Zugangsdaten müssen außerhalb von
Setup-, Profil-, Dokument- und Ausgabeordnern liegen; Nachweise getrennt von
Zugangsdaten und Dokument-/Ausgabeordnern. Diese Prüfung umfasst neue
Schedulerordner und spätere Ordneränderungen auch bei unveränderten Google-Einstellungen.

Die Setup-Planung prüft nur Dateimetadaten: Sie öffnet die OAuth-Datei nicht, validiert kein
Token, erzeugt keine Kalenderdatenbank und meldet sich weder an noch fragt es
Google ab. Pfade sind private Einrichtungsdaten, kein Modellkontext. Bestehende
widersprüchliche Rechte oder Aliasbindungen ersetzt dieses Formular nicht. Beim
erneuten Öffnen ist der Bindungsschalter aus; nicht ausgewählte Felder verändern
bestehende Rechte nicht. Das Entfernen eines Kontos löscht weder seine privaten
Dateien noch seinen Ausführungsnachweis. Die erste OAuth-Anmeldung bleibt offen.
Die Auflösung von `primary` ist jetzt eine ausdrückliche, separat freigegebene
Metadatenabfrage, keine Nebenwirkung der Setup-Planung oder Speicherung.

### Konkrete Google-Kalender-ID lesen

Starte `folderhome setup serve --approve-loopback-server --approve-calendar-read` mit der gewünschten
vorhandenen Setup-Konfiguration. Trage im Google-Kontoformular die private
OAuth-Datei, Zugangsreferenz und `primary` ein und wähle **Kalender-ID bei Google
lesen**. Das ausgewählte Profil muss bereits gespeichert sein. Die konkrete ID
ändert nur das Formular; prüfe und speichere die Einrichtung separat. Weder dieser
Knopf noch das Speichern erlaubt das Erzeugen von Kalenderereignissen. Geänderte
Kontofelder und ein neu aufgebautes Formular verwerfen verspätete Antworten;
erneute Klicks während einer laufenden Abfrage werden ignoriert.

Derselbe Dienst ist ohne Oberfläche verfügbar:

```powershell
folderhome calendar resolve-id --credential-file "C:\private\google-oauth.json" --credential-ref connector://google-calendar/google_private --calendar-id primary --approve-calendar-read --json
```

**Getrennter OAuth-Scope:** Die vorhandene Zustimmung muss
`https://www.googleapis.com/auth/calendar.calendars.readonly` enthalten.
`calendar.events` allein erlaubt diesen Endpunkt nicht. FolderHome holt keine
Zustimmung automatisch ein und erweitert sie nicht. Ereignisausführung benötigt
weiterhin ihren eigenen Ereignis-Scope, `--approve-calendar-write` und die genaue
Planbestätigung.

Nach ausdrücklicher Freigabe liest der Abruf die private Datei und führt einen
GET für Kalendermetadaten aus; ein abgelaufenes Token kann vorher eine begrenzte
OAuth-Erneuerung auslösen. Fehlt der erforderliche Scope ausdrücklich in deren
Antwort, wird der GET blockiert. Weder Zugangsdaten noch Konfiguration werden
geschrieben, Ereignisse weder abgerufen noch verändert, Providerfehler bleiben
redigiert. Die festen Google-Endpunkte erlauben keine eigenen Hosts oder Umleitungen.
[Google-Berechtigungen für Kalendermetadaten](https://developers.google.com/workspace/calendar/api/v3/reference/calendars/get).

Die OAuth-Tests verwenden echtes `google-auth 2.57.1` hinter einer synthetischen
HTTPS-Grenze. Tests des normalen App-Einstiegs decken das separate Gate und den
Entzug gespeicherter Registerrechte ab. Keine echte Google-Zustimmung oder echtes
Konto wurde verwendet. Protokollreferenz:
[Google-OAuth-Zugangsdaten](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html).

### Unvollständige und unklare Läufe

**Fehlender Erfolg ist kein Rollback.** Die normale Bestätigungs-API antwortet mit
HTTP 409, `execution_outcome_unknown: true`, `retry_safe: false` und
`uncertain_results`. Rezepte liefern ihren abgebrochenen Schrittbericht und dieselben
Teilnachweise. Eine möglicherweise wirksame Workflow-Ausführung verbraucht ihre
genaue Freigabe; deren Wiederholung löst keine weitere Provideranfrage aus.

Die prozesslokale Ergebnisliste erhält einen `uncertain`-Versuch unter seinem Profil,
ohne einen erfolgreichen Ausführungsbericht zu erfinden. `evidence` enthält nur
typisierte, bestätigte Ereignisreferenzen, niemals OAuth-Zugangsdaten, Quellpfade oder
rohe Providerfehler. Null bestätigte Einträge bedeutet **nicht** null externe
Schreibvorgänge. Zurückgegebene Nachweise sind unabhängig vom gespeicherten Eintrag
kopiert. Die bestehende Grenze von 128 Sitzungsergebnissen gilt; diese Liste ist
kein dauerhaftes Auditarchiv.

Die englische/deutsche Oberfläche zeigt eine Warnung und aufklappbare bestätigte
Referenzen als inerten Text. Auch nach verlorener Antwort verhindert sie eine
erneute Bestätigung; diese lokale Warnung behauptet weder eine Serverbestätigung
noch bestätigte Ereignisse. Vor jeder neuen Schreibfreigabe Zielkalender und
privaten Nachweis prüfen. Verspätete Ergebnisabrufe und Bestätigungsnachrichten sind
gegen Profilwechsel abgesichert. Automatisierte API- und Node-Tests decken diese
Übergänge ab; Browser-/Layoutabnahme bleibt offen.

In `agent session` erzeugen gewöhnliche unklare Ausführungen das NDJSON-Ereignis
`execution_uncertain` mit Plan-ID/-Hash, `retry_safe: false` und denselben
`uncertain_results`. Rezeptergebnisse behalten das Ereignis `confirmation` und
weisen Unsicherheit oder Abbruch unter `result` aus. Im Textmodus erscheinen Warnung
und bestätigte Referenzen; ein abgelehntes Rezept heißt abgebrochen, nicht unklar.
Unklare wie abgebrochene Ausführungen führen zum Sitzungs-Exitcode **2**, auch wenn
anschließend regulär `/quit` folgt. Kein Ausgabemodus wiederholt die Ausführung,
um Nachweise abzurufen.

### Geprüfte Änderungen und Löschung

Der native Adapter akzeptiert **bedingte Änderungs-/Löschanfragen über den normalen
Freigabeweg des Workflows `calendar-connectors`**. Beide Operationen benötigen die
getrennte Startfreigabe `--approve-calendar-write` und eine exakte Planbestätigung.
Der Plan zeigt den vollständigen bisherigen Termin, sein ETag, die Operation und
das Ersatzereignis (oder `null` zum Löschen). Die alte Erstellungsfreigabe
autorisiert keine Änderung.

Der Kern benötigt den zuvor bestätigten eigenen Solo-Termin, seinen Nutzdatenhash
und ein starkes ETag aus dem privaten Ledger. Bei Änderungen bleiben Profil,
Kalender und Ereignis-UID fest. Pro Zielversion wird ein bedingter PATCH oder
DELETE dauerhaft reserviert; spätere Aufrufe lesen nur zurück. HTTP 412 stoppt
als Versionskonflikt. Timeouts und verlorene lokale Nachweise bleiben unklar,
solange das Rücklesen den gewünschten Zustand nicht bestätigt. Löschen berichtet
**Abwesenheit**, keinen Beweis, dass genau dieser Aufruf sie verursacht hat.
Alte Erstellungsbestätigungen können weder neuere Ledger-Versionen noch einen
Löschvermerk überschreiben. Unbeteiligte Ereignisfelder bleiben beim PATCH erhalten.
[Bedingte Google-Änderungen](https://developers.google.com/workspace/calendar/api/guides/version-resources),
[PATCH-Feldsemantik](https://developers.google.com/workspace/calendar/api/v3/reference/events/patch).

Erfolgreiche Erstellungs- und Änderungsberichte enthalten `event_versions`:
vollständige typisierte Ereignisse mit Provider-IDs und starken ETags
(`folderhome.google-calendar-event-version.v1`). Die Sitzungsergebnisliste behält
sie unabhängig kopiert unter demselben Profil. Die englische/deutsche Oberfläche
zeigt aufklappbares, inertes JSON für Folgepläne; Löschen gibt eine leere
Versionsliste zurück. Das sind **zuvor bestätigte Versionen**, keine dauerhafte
Aktualitätsgarantie. Für die Anfragedaten ist kein privater Datenbankzugriff nötig.

`agent session` liefert diese Felder in NDJSON-Bestätigungsberichten und zeigt
Änderungsnachweis sowie Versionsreferenzen auch im normalen Textmodus. Die Ausgabe
erinnert daran, dass jede Folgeänderung eine erneute Prüfung und Freigabe benötigt.

Für eine Folgeanfrage `configuration_resource_id`, `accounts_resource_id`,
`credential_resource_id`, `ledger_resource_id`, `account_id` und `area` beibehalten.
`operation` auf `update` oder `delete`, `previous_event` auf das zurückgegebene
`event` und `expected_etag` auf das zurückgegebene `etag` setzen. Bei Änderungen
ist `replacement` das vollständige geänderte Ereignis mit unveränderter Identität;
zum Löschen ist es `null`. Keine erstellungsspezifischen Felder wie
`source_resource_id` oder `planned_at` mitsenden.

Die Vorschau liest nur Konfiguration, Profilrechte und bestätigten lokalen Nachweis;
sie liest keine OAuth-Zugangsdaten und kontaktiert Google nicht. Die ursprüngliche
Quelldatei muss nicht mehr existieren. Vor Ausführung werden der gesamte Plan und
der alte Nachweis erneut geprüft; vor und nach jedem HTTP-Aufruf zusätzlich Rechte
und Anfragebindung. Widerruf nach möglicher Wirkung bleibt unklar und verbraucht
die Freigabe. Hat der Kern das Ergebnis bereits bestätigt, bleibt dieser
Änderungsnachweis als Teilbeleg erhalten. Ein veränderter oder fehlender endgültiger
Versionsnachweis darf nicht als Erfolg ausgegeben werden.

### Verbleibende Grenzen

Automatisierte Adapter-, App-Fabrik-/API- und Node-Rendering-Tests verwenden
synthetische Kalenderantworten und private temporäre Daten. Sie belegen keine
Live-Kalender- oder Browserabnahme. Ein eigenes Termin-Auswahl-/Bearbeitungsformular
bleibt offen; der normale Workflow akzeptiert derzeit die oben beschriebene
explizite typisierte Anfrage.

- `ready` oder `review_required` bedeutet nicht, dass ein Kalender verändert
  wurde.
- Eine synthetische Ereignisreferenz ist kein Live-Kalendereintrag.
- Während der Abnahme wurden keine echten Google-Zugangsdaten oder Konten verwendet.
- UpToday erhält eine ICS-Datei erst über den getrennt freigegebenen
  Phase-17-Handoff.
- Routinika-Live-Sync, geführte Terminbearbeitung und Serienereignisse bleiben offen.
- Automatische Terminerkennung ist best effort und besitzt keine
  Vollständigkeitsgarantie.
- Profile innerhalb eines Betriebssystemkontos sind organisatorische Regeln,
  keine kryptografische Mandantentrennung.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
