# Phase 15: Portabler Scheduler-Handoff

[English](./phase15-scheduler-handoff-plan.md) | **Deutsch**

**Stand:** 2026-09-09  
**Status:** Handoff und Runner implementiert; Registrierungsanbindung bleibt offen

## Nutzerziel

FolderHome soll die read-only Routinenqueue regelmäßig headless prüfen können,
ohne bei der Planung eigenständig eine Windows-Aufgabe zu registrieren oder
Dateiaktionen freizugeben.

## Funktionaler Vertrag

1. `scheduler plan` erzeugt einen deterministischen Handoff mit Zeitplan,
   portabler Argumentliste und Windows-Task-XML ausschließlich auf stdout.
2. Der Plan weist `registration_performed=false` aus und enthält keinen
   Installations- oder `schtasks /Create`-Aufruf.
3. `scheduler run` lädt dieselben Watch-, Binding- und Profilverträge und
   erzeugt genau eine read-only Mehrfach-Watch-Queue.
4. Ein Lauf benötigt ein ausdrückliches Gate, um ausschließlich operativen
   Scheduler-State und einen append-only Laufbericht zu schreiben.
5. Ein schedule-spezifisches Lock verhindert gleichzeitige Läufe. Es sperrt
   weder beobachtete Ordner noch Nutzerdokumente.
6. Ein vorhandenes Lock wird nicht automatisch entfernt oder übernommen;
   der Lauf endet fail-closed als `already_running`.
7. Das Lock wird nach einem eigenen abgeschlossenen Lauf wieder entfernt.
8. Exitcodes unterscheiden `idle`, `attention`, `blocked`,
   `already_running` und ungültige Eingaben.

## Exitcodes

| Code | Bedeutung |
|---:|---|
| 0 | Queue enthält weder freigabefähige noch blockierte Einträge |
| 10 | Mindestens ein Queue-Eintrag ist `ready` und benötigt menschliche Freigabe |
| 20 | Mindestens ein Eintrag oder der Queue-Lauf ist `blocked`/`failed` |
| 30 | Derselbe Zeitplan läuft bereits oder hinterließ ein ungeklärtes Lock |
| 2 | CLI-Eingabe oder Konfiguration ist ungültig |

## Sicherheitsgrenzen

- Vor operativen Schreibzugriffen rekonstruiert der Runner den vollständigen
  Handoff, vergleicht ihn und behält einen unabhängigen Snapshot. Das State-Gate
  muss der boolesche Wert `true` sein; Intervalle benötigen ganze Minuten.
- Vorhandene Umleitungen in Lock-/Berichtsordnern werden abgewiesen. Berichtspfade
  werden nach der Extraktion erneut geprüft und Zeitstempel-Dateinamen
  normalisiert. Die Bereinigung erhält ersetzte Besitzer und entfernt nur den
  eigenen Lock. Ein gescheiterter Auditschreibvorgang behauptet keine
  gespeicherte `completed_file`.
- Diese Prüfungen bilden keine Isolationsgrenze gegen bösartigen Code oder
  gleichzeitige Dateisystemmanipulationen im selben Betriebssystemkonto.
  Der Handoff bindet Konfigurationspfade, nicht spätere Inhaltsänderungen;
  dauerhafte Registrierung benötigt eine gesonderte inhaltsgebundene Freigabe.
- Keine Installation oder Registrierung eines Betriebssystem-Schedulers.
- Keine automatische Batchfreigabe und keine Dokumentaktion.
- Kein Checkpoint-Schreiben durch den Schedulerlauf.
- Keine automatische Entfernung fremder oder verwaister Locks.
- Absolute Pfade werden als einzelne `argv`-Elemente gespeichert, nicht als
  zusammengesetzter Shellbefehl.
- Der Zeitplan bindet Watch-, Binding-, Profil-, State- und Providerpfade in
  eine deterministische Schedule-ID.

## Usecases

### Registrierungserweiterung in Arbeit

Die private Python-Planungsgrenze in `application.scheduler_registration`
bindet jetzt den vollständigen Handoff, die Scheduler-Checkout-Revision,
Store-/Ledgerpfade, aufgelöste Watch-/Bindingverzeichnisse sowie Dateiauswahl und
SHA-256-Inhalte von Watch-, Binding-, Profil- und Komponentenmanifest-Dateien.
Erneute Validierung weist auch umgehängte Verzeichnislinks ab; neue Dokumente
im genehmigten Watch ändern diesen Konfigurationssnapshot
nicht. Die Planung erzeugt weder Store noch Ledger oder Ausführungsdienst.
Der gemeinsame Provider-Loader unterstützt gepinnte `src`-Layouts und weist
vorab geladene fremde Module der gesamten benannten Paketfamilie zurück.

Die private API `register_scheduler_job` verlangt jetzt die genaue Plan-ID und
eine getrennte boolesche Schreibfreigabe. Vor Öffnen des Provider-Stores wird ein
unveränderlicher Versuchsnachweis veröffentlicht. Anschließend trägt die gepinnte
API von `ellmos-scheduler` 0.3.1 einen deterministischen Job ein und liest dessen
Definition und Fälligkeit zurück. Die Registrierung startet **keinen**
Ausführungsdienst; `consumer_status` bleibt `not_observed`. Store, Nachweise und
Laufberichte dürfen nicht innerhalb beobachteter Eingaben liegen.

Wiederholte Bestätigungen lesen ausschließlich denselben Job zurück. Eine
verlorene Antwort nach erfolgreichem Einfügen lässt sich so aufklären; fehlt der
Job nach einem früheren Versuch, bleibt der Ausgang `uncertain`, ohne zweiten
automatischen Insert. Unbekannte vorhandene Datenbanken und verwaiste
SQLite-Begleitdateien bleiben erhalten und werden nicht initialisiert oder
migriert. Jede spätere Beobachtung erhält einen eigenen unveränderlichen
Nachweis. Scheitert dessen Speicherung, wird der Ausgang auch dann als unklar
gemeldet, wenn der Job bereits vorhanden sein könnte.

Die Fälligkeitsprüfung liest Job und Laufhistorie in einer Transaktion. Sie
akzeptiert belegte Intervallfortschreibungen und verlassene Wiederholungsslots,
keine beliebige manuelle Neuplanung. Das schützt kooperierende Prozesse, nicht
vor bösartigem Code mit denselben Betriebssystemrechten.

Die private API `application.scheduler_consumer.create_scheduler_consumer`
erzeugt nach getrennter genauer Planfreigabe jetzt einen **gestoppten**, auf einen
Job begrenzten Ausführungsdienst. Ein ausdrückliches `tick()` prüft einen fälligen
Job; ein ausdrückliches `serve()` nutzt die vorhandene Schleife des Providers.
Registrierung und Konstruktion starten keinen dieser Vorgänge. Vor jeder
Übernahme werden Konfiguration und gespeicherter Job erneut geprüft. Das isolierte
Executorregister führt keine beliebigen Shelljobs aus und übernimmt keine anderen
Jobs desselben Stores.

Die Queue läuft mit Zeitlimit in einem an diese FolderHome-Installation gebundenen
Kindprozess, auch wenn das Arbeitsverzeichnis einen anderen Checkout enthält.
Exit 0 oder 10 gilt nur mit passendem strukturiertem Queue-Bericht, dessen
gespeicherter Datei und einer frischen Aufruf-ID mit eigenem unveränderlichem
Nachweis als Erfolg. Ein alter gültiger Bericht belegt keinen neuen Lauf.
Timeouts und fehlende Nachweise sind kein Erfolg; ein gescheiterter
Beobachtungsnachweis wird getrennt vom Laufergebnis als `uncertain` gemeldet.
Dokumente bleiben unverändert; weder Checkpoint noch Aufräumaktion werden freigegeben.

Bestätigungsadapter, Ressourceneinrichtung und App-/CLI-Anbindung bleiben in Arbeit.
Das bisherige Verhalten von
`scheduler plan/run` und der öffentliche Capability-Katalog bleiben unverändert.
Integrationstests verwenden temporäre Stores und benötigen den sauberen gepinnten
Scheduler-Checkout; es wird kein echter Nutzerjob registriert.

### USECASE 015-1: Installationsfreien Handoff prüfen

- **Vorbedingung:** Synthetische Konfigurationspfade und expliziter Startzeitpunkt.
- **Eingabe:** Intervall, Zeitzone, Taskname und lokale Pfade.
- **Erwartung:** Portables `argv`, Windows-XML, stabile ID und keine Dateischreibung.

### USECASE 015-2: Headless Queue-Lauf

- **Vorbedingung:** Ein aktiver synthetischer Watch und freier Scheduler-Lock.
- **Eingabe:** Handoff, explizite Laufzeit und Scheduler-State-Gate.
- **Erwartung:** Queue-Bericht, Exitcode 10 bei `ready`, freigegebenes Lock,
  unveränderte Dokumente und keine Zielordner.

### USECASE 015-3: Gleichzeitigen Lauf blockieren

- **Vorbedingung:** Schedule-spezifisches Lock existiert bereits.
- **Eingabe:** Derselbe Handoff.
- **Erwartung:** Exitcode 30, kein Queue-Lauf, keine Übernahme oder Löschung
  des vorhandenen Locks.
