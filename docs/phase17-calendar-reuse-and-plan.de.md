# Phase 17: Kalender-Wiederverwendung und Bauplan

[English](./phase17-calendar-reuse-and-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Status:** Kandidaten, Planung und freigegebene lokale/ICS-Ausführung abgeschlossen

Der Abschlussstand ist mit 159 FolderHome-Tests lokal abgenommen. Planung
bleibt read-only. Ausführung benötigt eine exakte Approval-Datei und ein
State-Gate; ICS zusätzlich ein Output-Gate. Weder UpToday noch ein anderer
externer Connector wird dabei aufgerufen.

## Nutzerziel

FolderHome soll Datums- und Terminangaben aus ausdrücklich ausgewählten
Dokumenten als prüfbare Kandidaten erfassen. Welcher Kalender verwendet wird,
soll über eine allgemeine Konfiguration und optional spezifischer über
Profilregeln festgelegt werden. Die Erkennung ist best effort und darf weder
Vollständigkeit behaupten noch ohne eigene Freigabe einen Kalender verändern.

## Wiederverwendungsprüfung

### Quell-Skill `assist/kalender` 0.1.0

- Der MIT-lizenzierte Skill definiert bereits das richtige Auswahlprinzip:
  lokaler SQLite-Kalender sowie optionale Backends für Google, Routinika und
  UpToday über eine Nutzerpräferenz.
- Sein Python-Core implementiert nur den lokalen Store. UpToday und Routinika
  sind im Skill ausdrücklich als „nicht implementiert“ ausgewiesen.
- Der Core ist keine sichere direkte Laufzeitabhängigkeit für FolderHome: Er
  besitzt keinen Git-Pin, legt den Store neben dem Skill an, erzeugt zufällige
  IDs, öffnet die Datenbank auch bei Lesezugriffen schreibend und erlaubt
  unmittelbares Hard-Delete ohne Plan-, Hash- oder Approval-Vertrag.
- Wiederverwendet werden deshalb Backend-Auswahl, lokale Grundfelder und der
  ICS-Gedanke, nicht der Core als schreibender Adapter.

### UpToday, Revision `7582ca87e17e458bb99a7379d2c54003c15415a4`

- Der lokale Checkout war bei der Inventur sauber, besitzt keinen
  konfigurierten Remote und steht unter MIT.
- UpToday implementiert einen dateibasierten RFC-5545-Kanal ohne Cloud-Sync.
  Importierte ICS-Quellen werden nicht zurückgeschrieben; UIDs und
  Inhaltshashes verhindern Duplikate und ermöglichen lokale Updates.
- `build_ics` und der atomare Dateiexport sind brauchbare Referenzen. Der
  direkte Import verändert jedoch die UpToday-Datenbank und ist kein stabiler
  FolderHome-Connectorvertrag.
- Phase 17 plant deshalb zunächst ein eigenes deterministisches ICS-Handoff.
  Ein späterer UpToday-Import bleibt eine separat freizugebende Adapteraktion.

### Routinika/RoutineMaster

- Es wurde kein eigenständiger extrahierter Routinika-Connector und kein
  implementierter Skill-Backendpfad gefunden.
- UpToday enthält nur eine als „deprecated / ungenutzt“ markierte
  RoutineMaster-Bridge. Sie sucht alte lokale Pfade und öffnet SQLite nicht
  read-only; ihr eigener Header verlangt vor einer Reaktivierung Nachrüstung.
- Das Backend bleibt im Vertrag auswählbar, aber bis zu einem versionierten,
  geprüften Adapter sichtbar `blocked`.

### TerminPilot und Google Calendar

- TerminPilot koordiniert Mehrpersonen-Abstimmungen und ist kein persönlicher
  Kalender. Sein Checkout enthält außerdem fremde, uncommittete Änderungen;
  FolderHome liest ihn nicht weiter ein und verändert ihn nicht.
- Google Calendar ist ein externer Connector mit eigener Datenschutz- und
  Netzwerkgrenze. Er gehört nicht in den lokalen Phase-17-Standardpfad.

## Deklaratives Dokumentformat V1

V1 wertet nur eindeutig beschriftete Einzelzeilen aus:

```text
Termin: Kontrolltermin
Datum: 2026-09-14
Uhrzeit: 10:30
Ende: 11:00
Ort: Praxis Beispiel
Zeitzone: Europe/Berlin
```

Erforderlich sind Titel und Datum. Eine fehlende Uhrzeit ergibt einen
Ganztagstermin; eine fehlende Endzeit wird nicht durch eine erfundene Dauer
ersetzt. Mehrdeutige Werte, ungültige Zeitpunkte oder eine unbekannte
Zeitzone erzeugen `review_required` statt eines ausführbaren Kandidaten.

## Konfigurations- und Profilauflösung

1. `folderhome.calendar-config.v1` legt `default_backend` und
   `default_timezone` für das aktuelle OS-Konto fest.
2. Die bestehende Profilvererbung erhält `calendar.backend` und
   `calendar.timezone` als typisierte Regeln.
3. Profilregeln überstimmen den allgemeinen Fallback nach derselben festen
   Reihenfolge global → Bereich → Profil → Profilbereich.
4. Unterstützte Werte sind zunächst `folderhome_local`, `uptoday_ics`,
   `routinika` und `google`; nur die ersten beiden können in Phase 17 zu einem
   lokalen Plan führen.
5. Der synthetische Beispiel-Fallback lautet `uptoday_ics`, wie vom Nutzer
   gewünscht. Das erzeugt nur ein Handoff-Artefakt und importiert nichts.

## Kandidaten- und Aktionsvertrag

1. Jeder Kandidat bindet Profil, Bereich, Titel, Datum/Zeit, Zeitzone, Ort,
   Dokument-ID, Quellhash, Pfad und Zeilenevidenz.
2. Eine stabile UID wird aus Kandidateninhalt und Dokumentidentität gebildet;
   Zufalls-IDs sind ausgeschlossen.
3. Planung bleibt read-only und nennt Backend, Providerstatus, Zielart,
   Side-Effects, Konflikte und benötigte Gates.
4. `folderhome_local` plant einen Eintrag im gekapselten lokalen Kalenderstore.
5. `uptoday_ics` plant eine neue Never-overwrite-ICS-Datei mit deterministischer
   UID; UpToday-Import ist nicht Bestandteil derselben Freigabe.
6. `routinika` und `google` bleiben blockiert, bis ein eigener gepinnter
   Connectorvertrag und seine Datenschutz-/Netzwerkfreigabe vorliegen.
7. Vor jeder Ausführung werden Plan-ID, Quellhash, Kalenderrevision,
   Zielkonflikt und Approval erneut geprüft.
8. Terminerkennung ist ausdrücklich nicht vollständig; ausgelassene oder
   unklare Dokumente bleiben sichtbar im Analysebericht.

## Ausführungsgrenze

1. `folderhome.calendar-handoff-approval.v1` bindet eine stabile Freigabe an
   Plan-ID, Kalenderrevision, konkrete Aktions-IDs und einen Zeitpunkt mit
   Zeitzone.
2. Jede Ausführung schreibt ein append-only Audit. Deshalb benötigen sowohl
   lokaler Kalender als auch ICS-Handoff `--approve-state-write`.
3. Der lokale Store schreibt ausgewählte Ereignisse und Auditzeilen in einer
   SQLite-Transaktion. Er bietet keine Löschoperation.
4. ICS benötigt zusätzlich `--approve-output-write`. Alle Dateien werden
   zunächst gehasht vorbereitet, dann per Never-overwrite veröffentlicht und
   erneut gelesen.
5. Scheitert ein späteres Element des Batches, entfernt FolderHome bereits
   veröffentlichte Dateien nur dann, wenn Pfad und Hash noch dem eigenen
   Ausführungsbeleg entsprechen.
6. Das Ergebnis nennt je Aktion Event-ID oder Ausgabepfad/-hash und den
   verfügbaren Rückweg. Ein UpToday-Import ist weiterhin ein anderer Vorgang.

## Usecases

### USECASE 017-1: Termin aus Dokument erkennen

- **Eingabe:** Synthetisches Dokument mit Titel, Datum, Zeit und Ort.
- **Erwartung:** Evidenzgebundener Kandidat; kein Kalender- oder Dateischreiben.

### USECASE 017-2: Profilbackend auflösen

- **Eingabe:** Fallback `uptoday_ics`, Profilregel `folderhome_local`.
- **Erwartung:** Profilregel gewinnt mit vollständiger Regelprovenienz.

### USECASE 017-3: UpToday-Handoff planen

- **Eingabe:** Eindeutiger Kandidat und `uptoday_ics`.
- **Erwartung:** Deterministische ICS-Vorschau und Zielpfad; kein Import und
  keine Veränderung der UpToday-Datenbank.

### USECASE 017-4: Nicht vorhandenes Routinika-Backend blockieren

- **Eingabe:** Profilregel `routinika`.
- **Erwartung:** Sichtbarer blockierter Plan mit fehlender Providerrevision;
  kein stiller Fallback auf einen anderen Kalender.

### USECASE 017-5: Lokalen Termin freigegeben übernehmen

- **Eingabe:** Eindeutiger Kandidat, aktueller Kalenderstand, exakte Approval-
  Datei und State-Gate.
- **Erwartung:** Ein aktives Ereignis und eine Auditzeile in derselben
  Transaktion; identische Neuplanung wird `noop`.

### USECASE 017-6: Mehrere ICS-Dateien sicher publizieren

- **Eingabe:** Zwei eindeutige Kandidaten sowie State- und Output-Gate.
- **Erwartung:** Beide Dateien besitzen den geplanten Hash. Ein synthetischer
  Fehler an Datei zwei entfernt Datei eins wieder und hinterlässt kein Audit.
