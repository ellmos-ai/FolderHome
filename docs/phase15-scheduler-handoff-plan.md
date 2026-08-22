# Phase 15: Portabler Scheduler-Handoff

**Stand:** 2026-08-21  
**Status:** implementiert und mit 133 FolderHome-Tests abgenommen

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

- Keine Installation oder Registrierung eines Betriebssystem-Schedulers.
- Keine automatische Batchfreigabe und keine Dokumentaktion.
- Kein Checkpoint-Schreiben durch den Schedulerlauf.
- Keine automatische Entfernung fremder oder verwaister Locks.
- Absolute Pfade werden als einzelne `argv`-Elemente gespeichert, nicht als
  zusammengesetzter Shellbefehl.
- Der Zeitplan bindet Watch-, Binding-, Profil-, State- und Providerpfade in
  eine deterministische Schedule-ID.

## Usecases

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
