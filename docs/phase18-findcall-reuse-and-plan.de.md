# Phase 18: FindCall-Wiederverwendung und Bauplan

[English](./phase18-findcall-reuse-and-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Status:** Providerinventur, generischer Vertrag und Fixture-CLI abgeschlossen

## Nutzerziel

FindCall soll nacheinander geeignete Anbieter kontaktieren, bis eine Anfrage
innerhalb vorher festgelegter Grenzen erfolgreich ist. Kernfälle sind ein
Arzttermin in einem Zeitfenster, ein Werkstatttermin samt Kostenvoranschlag
und das Einholen vergleichbarer Angebote. Reale Telefonate, Reservierungen
und finanzielle Zusagen bleiben außerhalb der lokalen Wettbewerbsabnahme.

## Verifizierter Bestand

### HungryCall, Revision `2c7db533f073d07eae6d758ceab91b9423ae1dc7`

- Checkout und Manifest sind sauber, Version `0.1.0`, MIT; 301 Provider-Tests
  liefen lokal grün.
- Wiederverwendbar ist das generalisierte Kaskadenprinzip: Kandidaten filtern
  und ordnen, seriell kontaktieren, strukturierte Ergebnisse gegen Muss-,
  Preis- und Zugeständnisgrenzen prüfen und nach dem ersten Erfolg stoppen.
- E.164-Prüfung, maskierte Ausgaben, Idempotency-Key, differenzierte
  Call-Status und ein netzloser Fixture-Client sind bereits belegt.
- Die konkrete Runtime ist absichtlich auf Restaurant, Bestellung, Abholung
  und Tischreservierung typisiert. Arzt-, Werkstatt- oder Angebotsmodelle
  dürfen nicht als Restaurantdaten hineingezwängt werden.

### Ringedingeding, Revision `d80dd81a6d7bf64298d4ef290c3b54ab5f50e990`

- Checkout und Manifest sind sauber, Version `0.1.0`, MIT; die vollständige
  Provider-Suite lief lokal grün.
- Wiederverwendbar sind schema-geführte Anfragen an mehrere bekannte
  Personen, stabile Idempotency-Keys, erhaltene Endstatus, maskierte Nummern
  und der lokale `FixtureTransport`.
- Das Produkt löst Gruppenverfügbarkeit, Auswahlfragen und offene
  Rückmeldungen. Das ist kein Anbieter-Suchlauf und besitzt keinen frühen
  Stopp nach dem ersten passenden Angebot.

## Verantwortungsgrenzen

```text
HungryCall
  behält seine Gastronomie-Runtime und liefert das geprüfte Kaskadenmuster

Ringedingeding
  behält Mehrpersonen-Polls und Terminabstimmungen mit bekannten Kontakten

FindCall
  modelliert generische Anbieter, Anfragegrenzen und den seriellen Suchlauf

FolderHome
  prüft Pins, wählt den Anwendungsfall und hält Live-Gates geschlossen
```

FolderHome lädt beide Provider nur aus dem exakt gepinnten, sauberen Checkout.
Eine Plugin-Probe darf ausschließlich lokale Klassen und Dry-Run-Eigenschaften
prüfen. Der neue FindCall-Kern liegt gekapselt unter
`folderhome.capabilities.findcall` und importiert keine Restaurant- oder
Poll-Datentypen in seine öffentlichen Verträge.

## FindCall-Vertrag V1

1. Ein Auftrag nennt organisatorisches Profil, Bereich, Anfrageart,
   Leistungsbeschreibung, Ort, mindestens ein Zeitfenster, optionale
   Preisobergrenze und ausdrücklich erlaubte Verbindlichkeit.
2. V1 unterstützt `appointment` und `quote`. Medizinische Angaben bleiben auf
   Fachrichtung und administrative Terminbedingungen beschränkt; Symptome,
   Diagnosen und Notfälle werden abgelehnt.
3. Kandidaten besitzen stabile lokale IDs, Name, maskierbare E.164-Nummer,
   optionale Distanz und Priorität. Klarnummern erscheinen nie in Plan oder
   Bericht.
4. Vorfilterung entfernt unpassende Leistung, zu große Entfernung oder
   fehlende Kontaktmöglichkeit. Die verbleibenden Kandidaten werden
   deterministisch nach Priorität, Distanz und ID geordnet.
5. Der Dry-Run arbeitet streng seriell. Er bewahrt `NO_ANSWER`, `BUSY`,
   `DECLINED`, `FAILED` und `COMPLETED`, prüft strukturierte Ergebnisse und
   stoppt nach dem ersten Ergebnis innerhalb aller Grenzen.
6. `inquiry_only` darf weder buchen noch einen Auftrag erteilen. Eine spätere
   verbindliche Aktion benötigt eine eigene, konkrete Live-Freigabe und wird
   in Phase 18 nicht implementiert.
7. Fixture-Ergebnisse sind ausdrücklich `simulated=true`, führen keinen
   Netzwerkzugriff aus und werden nicht als tatsächliche Verfügbarkeit oder
   Preiszusage ausgegeben.

## Usecases

### USECASE 018-1: Arzttermin suchen

- **Eingabe:** Fachrichtung Dermatologie, Ort, zwei Zeitfenster, drei
  synthetische Praxen, `inquiry_only`.
- **Erwartung:** Der erste nicht erreichbare Kandidat bleibt sichtbar; der
  zweite passende Fixture-Termin beendet die Kaskade. Keine Buchung erfolgt.

### USECASE 018-2: Werkstattangebot prüfen

- **Eingabe:** Bremsenprüfung für Hyundai i10, Zeitfenster und maximale
  Kostenschätzung.
- **Erwartung:** Ein unklares oder zu teures Angebot wird abgelehnt; das erste
  genaue Angebot innerhalb der Grenze wird als simulierter Treffer gemeldet.

### USECASE 018-3: Keine passende Option

- **Eingabe:** Mehrere synthetische Anbieter, deren Ergebnisse Status- oder
  Mussgrenzen verfehlen.
- **Erwartung:** Alle Versuche bleiben mit konkretem Grund erhalten; Erfolg
  und externe Nebenwirkungen sind `false`.

### USECASE 018-4: Plugin-Pins prüfen

- **Eingabe:** FolderHome-Manifeste und lokale Providercheckouts.
- **Erwartung:** HungryCall und Ringedingeding werden nur bei exakter Version,
  Revision, sauberem Git-Status und vorhandenem Dry-Run-Einstieg akzeptiert.

## Abnahmegrenze

Phase 18 ist mit 170 FolderHome-Tests abgeschlossen. Plugin-Probe,
FindCall-Plan, serieller Fixture-Lauf und CLI sind auf synthetischen Daten
grün. Es wurden keine echten Rufnummern, Konten, Netzwerke, Termine,
Werkstattaufträge oder Kosten ausgelöst.
