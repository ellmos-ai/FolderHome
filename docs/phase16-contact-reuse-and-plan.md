# Phase 16: Kontakt-Wiederverwendung und Bauplan

**Stand:** 2026-08-22  
**Status:** implementiert und mit 146 FolderHome-Tests abgenommen

## Wiederverwendungsprüfung

- Unter den bereits extrahierten lokalen Modulen existiert kein passendes
  Kontaktregister. `crm-cosmology` ist trotz seines Namens ein
  Kosmologieprojekt und fachlich unverbunden.
- Der Altbestand `BACH/system/hub/contact.py` verwaltet allgemeine Kontakte
  in der BACH-Datenbank. Er wird gemäß Projektentscheidung nicht erneut aus
  BACH extrahiert und nicht direkt gekoppelt.
- Der BACH-Handler besitzt keine Dokumenthash-Evidenz, keine Kandidatenphase,
  keine plan-/aktionsgebundene Freigabe und keinen atomaren Kontaktwechsel.
- Wiederverwendet werden deshalb die bereits extrahierten FolderHome-Bridges
  für `doc-services`, Profile, Dokumentidentität, Hashprüfung, Gates und Audit.
  Neu entsteht ausschließlich der gekapselte Kontaktkern.

## Nutzerziel

FolderHome soll aus einem Dokument erkennen können, wer für einen konkreten
Bereich und Gegenstand zuständig ist, etwa die Versicherung eines Hyundai i10.
Neue Kontaktdaten dürfen erst nach Prüfung übernommen werden. Wird später für
denselben Zweck ein anderer Kontakt belegt, wird der neue Kontakt angelegt und
der alte lediglich als Löschkandidat markiert.

## Deklaratives Dokumentformat V1

V1 wertet nur eindeutig beschriftete Einzelzeilen aus:

```text
Organisation: Beispiel Versicherung AG
Ansprechpartner: Erika Beispiel
Rolle: Kundenservice
Zuständig für: KFZ-Versicherung
Vertragsobjekt: Hyundai i10
E-Mail: erika@example.invalid
Telefon: +49 30 123456
Gültig ab: 2026-08-01
```

Mindestens Organisation, Zuständigkeit sowie E-Mail oder Telefon sind
erforderlich. Mehrdeutige Mehrfachwerte und ungültige Kanäle erzeugen keinen
freigabefähigen Kandidaten. `blocked` und `not_checked` sperren die lokale
Übernahme. `review_required` benötigt zusätzlich die ausdrückliche Freigabe
`--approve-sensitive-local-read`; sie erlaubt keine Weitergabe nach außen.

## Daten- und Freigabevertrag

1. Jeder Kandidat bindet Profil, Bereich, Zweck, optionalen Objektbezug,
   normalisierte Kanäle sowie Dokument-ID, Quellhash, Pfad und Zeilenevidenz.
2. Ein read-only Registerplan vergleicht Kandidaten gegen denselben Schlüssel
   aus Profil, Bereich, Zweck und Objektbezug.
3. Ohne Treffer wird `create`, bei identischem Kontakt `noop` geplant.
4. Ein abweichender neuer Kontakt erzeugt eine atomare `replace`-Aktion:
   neuen Kontakt aktiv anlegen und vorherigen Kontakt als
   `deletion_candidate` markieren.
5. Kein Workflow löscht einen Kontakt automatisch.
6. Eine Approval-Datei bindet Plan-ID, Registerrevision und konkrete
   Aktions-IDs.
7. Vor dem Schreiben werden Registerrevision und sämtliche Quelldokumenthashes
   erneut geprüft.
8. Registeränderung und append-only Ereignisse erfolgen in einer
   SQLite-Transaktion unter explizitem State-Gate.
9. Mehrere Dokumente mit demselben Zuständigkeitsschlüssel werden vor dem
   Registervergleich gemeinsam geprüft. Nur der eindeutig neueste Kontakt
   kann geplant werden; abweichende Kontakte mit demselben neuesten Datum
   blockieren fail-closed.
10. Dokumentordner und State dürfen sich nicht überlappen, damit das Register
    nicht als eigene Dokumentquelle eingelesen wird.

## Usecases

### USECASE 016-1: Ersten zuständigen Kontakt planen

- **Eingabe:** Synthetische Police mit beschriftetem Ansprechpartner.
- **Erwartung:** Ein evidenzgebundener Kandidat und eine ungefreigte
  `create`-Aktion; kein Register wird angelegt.

### USECASE 016-2: Kontakt freigeben und finden

- **Eingabe:** Exakte Approval-Datei für die `create`-Aktion.
- **Erwartung:** Aktiver Kontakt ist nach Profil, Bereich, Zweck und
  „Hyundai i10“ auffindbar; Dokument bleibt bytegleich.

### USECASE 016-3: Zuständigkeitswechsel

- **Eingabe:** Neueres Dokument mit anderem Ansprechpartner für denselben
  Schlüssel.
- **Erwartung:** `replace`-Vorschlag; nach Freigabe neuer Kontakt aktiv,
  vorheriger Kontakt `deletion_candidate`, keine Zeile gelöscht.

### USECASE 016-4: Widersprüchliche Ordnerkontakte blockieren

- **Eingabe:** Zwei Dokumente mit demselben Zuständigkeitsschlüssel und Datum,
  aber verschiedenen Kontakten.
- **Erwartung:** Beide Kandidaten bleiben sichtbar und `blocked`; es entsteht
  keine ausführbare Registeraktion.

## Implementierte Oberfläche

- `contacts plan` extrahiert gelabelte Kontaktkandidaten und vergleicht sie
  read-only mit der aktuellen Registerrevision.
- `contacts apply` baut den Plan erneut und verlangt Approval-Datei,
  Quellhash-Readback sowie `--approve-state-write`.
- `contacts list` sucht aktive oder optional auch als Löschkandidat markierte
  Kontakte nach Profil, Bereich und Objektbezug.
- Der wiederverwendbare Kern liegt getrennt unter
  `capabilities/contact_registry`; Application Service und Verträge bleiben
  providerneutral.
