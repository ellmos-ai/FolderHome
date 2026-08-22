# Phase 19: Kontoauszüge, virtuelle Konten und Abos

[English](./phase19-finance-reuse-and-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Status:** Finanzkern, Approval-Import, Abdeckung und Kostenkandidaten abgeschlossen

## Nutzerziel

Aus ausdrücklich bereitgestellten Kontoauszügen soll FolderHome ein lokales
virtuelles Konto nachbauen: belegte Buchungen, Anfangs-/Endstände und
abgedeckte Zeiträume. Lücken müssen sichtbar bleiben. Wiederkehrende
Belastungen sollen als prüfpflichtige Abo-, Versicherungs- oder sonstige
Kostenkandidaten mit Monats-/Jahressumme und vorsichtiger Prognose erscheinen.

## Wiederverwendungsprüfung

### Dokumentpipeline

- Die gepinnte `doc-services`-Bridge liefert bereits Text, Dokument-ID,
  Quellhash, Extraktionsprovenienz und Datenschutzstatus für TXT, PDF und
  weitere Formate.
- FolderHome baut deshalb keinen zweiten PDF-/OCR- oder Datenschutzpfad.
  Phase 19 verarbeitet ausschließlich den bereits normalisierten
  `DocumentRecord` und prüft vor dem Schreiben den Quellhash erneut.

### Steuer-Assistent, Revision `5d39aeec98bf0a5734bf07dc35a58aa9e1331309`

- Der saubere MIT-Checkout ist aus BACH extrahiert und belegt lokale
  SQLite-Ablage, ganzzahlige Centbeträge, datensparsame CLI-Ausgabe und
  Never-overwrite-Export.
- Seine Runtime ist fachlich eine selbst kategorisierte private
  Steuer-Arbeitsunterlage für Belege. Sie importiert keine Kontoauszüge,
  rekonstruiert keine Kontostände und erkennt keine Abos.
- Wiederverwendet werden Centgenauigkeit, lokale Speicherung und
  Privacy-by-default als Architekturprinzip. Das steuerfachliche Datenmodell
  wird nicht kopiert oder für Bankbuchungen umgedeutet.

### AboTracker und Kontoauszugsparser

- In den bereits extrahierten lokalen Modulen, Bundles, Stacks, Connectoren
  und Skills wurde kein veröffentlichter AboTracker oder providerneutraler
  Kontoauszugsparser gefunden.
- Diese Lücke wird als neuer wiederverwendbarer Kern unter
  `folderhome.capabilities.finance_store` gekapselt. Es erfolgt keine erneute
  BACH-Extraktion.

## Deklaratives Auszugsformat V1

Der erste synthetische Pfad liest eindeutig beschriftete Zeilen:

```text
Kontokennung: giro-lukas
Institut: Beispielbank
Konto-Endung: 1234
Zeitraum: 2026-06-01 | 2026-06-30
Anfangssaldo: 150000 | EUR
Endsaldo: 148701 | EUR
Buchung: 2026-06-05 | -1299 | StreamFlix | abo | tx-juni-stream
```

Beträge sind ganzzahlige Cent, nie binäre Fließkommazahlen. V1 unterstützt
nur EUR. Jede Buchung benötigt eine aus dem Auszug stammende eindeutige
Referenz. Freie Bankformate werden nicht geraten; unklare Dokumente bleiben
`review_required` und können später über formatbezogene Adapter ergänzt werden.

## Verträge und Sicherheitsgrenzen

1. Ein Auszug bindet Kontokennung, Institut, maskierte Kontoendung,
   Zeitraum, Salden und Buchungen an Dokument-ID, Quellhash, Pfad und
   Zeilenevidenz.
2. Anfangssaldo plus alle Buchungen muss exakt dem Endsaldo entsprechen.
   Abweichungen werden nicht still ausgeglichen.
3. Eine Plan-ID bindet neue Auszüge und Buchungen an die aktuelle
   Finanzrevision. Überlappende Zeiträume sind erlaubt, doppelte
   Buchungsreferenzen aber nur bei identischem Inhalt.
4. State-Schreiben benötigt eine Approval-Datei, konkrete Aktions-IDs und
   `--approve-state-write`. Quellen und Revision werden vorher erneut geprüft.
5. Der SQLite-Store ergänzt Konten, Auszüge, Buchungen und append-only Audit
   in einer Transaktion. Er besitzt keine Lösch- oder Banking-Schnittstelle.
6. Abdeckung wird ausschließlich aus gespeicherten Auszugszeiträumen
   berechnet. Fehlende Tage erscheinen als Lücke; außerhalb belegter Daten
   wird kein Kontostand interpoliert.
7. Wiederkehrende Kosten sind Kandidaten, keine Vertragsfeststellungen. Eine
   Serie benötigt mindestens zwei passende Belastungen desselben Profils,
   Kontos, normalisierten Gegenübers, Centbetrags und Kostenbereichs.
8. `active` bedeutet nur: letzte belegte Belastung liegt relativ zum
   angegebenen Stichtag innerhalb des erkannten Intervalls plus Toleranz.
   Kündigung, Vertragsstatus und künftige Abbuchung sind damit nicht bewiesen.

## Usecases

### USECASE 019-1: Kontoauszug übernehmen

- **Eingabe:** Synthetischer, rechnerisch stimmiger Monatsauszug und exakte
  State-Freigabe.
- **Erwartung:** Ein Konto, ein Auszug und alle Buchungen werden atomar
  ergänzt; Quelldokument und Rohtext bleiben außerhalb des Stores.

### USECASE 019-2: Lücken darstellen

- **Eingabe:** Auszüge für Januar und März, Abfrage Januar bis März.
- **Erwartung:** Februar erscheint vollständig als unbelegter Zeitraum;
  FolderHome erfindet weder Saldo noch Buchungen.

### USECASE 019-3: Abo-Kandidat erkennen

- **Eingabe:** Drei monatliche, centgleiche Belastungen von „StreamFlix“.
- **Erwartung:** Monatlicher Kandidat mit belegten Transaktions-IDs,
  Monatssumme, hochgerechneter Jahressumme und nächstem erwarteten Fenster.

### USECASE 019-4: Unklare Wiederholung nicht behaupten

- **Eingabe:** Zwei unterschiedlich hohe oder unregelmäßige Belastungen.
- **Erwartung:** Kein aktives Abo; Buchungen bleiben einzeln abfragbar.

## Abnahmegrenze

Phase 19 ist mit 179 FolderHome-Tests abgeschlossen und verwendet
ausschließlich synthetische Dokumente und lokalen State. Es gibt keinen
Bankzugriff, keine Zahlung, keine Kündigung, keine Steuer- oder Finanzberatung
und keine Aussage über Zeiträume ohne belegten Auszug.
