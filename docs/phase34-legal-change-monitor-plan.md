# Phase 34: Law-Checker-Anbindung und Rechtsänderungsmonitor

**Stand:** 2026-08-22  
**Zweck:** Einen vorhandenen quellengebundenen Rechtsworkflow revisionsgenau
qualifizieren und technische Änderungen zwischen lokalen Rechtsquellenständen
als begründete, aber unverbindliche Profil-/Vertragsprüfkandidaten ausgeben.

## Bestandsabgleich

Der frühere OneDrive-Checkout war zurückliegend und durch fremde Änderungen
nicht als Runtime qualifizierbar. Für Phase 34 wurde deshalb ein separater,
sauberer Checkout unter `C:\_Local_DEV\repos\law-checker` angelegt und auf
Revision `06fb8d57ff90638cc50f5e33c50dbba455ac6f1b` geprüft. Seine vier Tests
bestanden am 2026-08-22.

`law-checker` Version 0.2.2 stellt einen Skill, eine versionierte
Gesetzesregistry und einen Fetcher bereit. Es besitzt keine stabile Python-API
für eine automatische Einzelfallprüfung. FolderHome importiert daher keinen
Agentenlauf. Die neue read-only Bridge prüft stattdessen:

- saubere, exakt gepinnte Git-Revision,
- Paketname und Version,
- stabile Modul-ID und deklarierte Quellenfunktionen,
- Registryversion und aktivierte Gesetzesschlüssel.

Ein Snapshot kann einen aktiven Registryschlüssel binden. Ein fehlender oder
deaktivierter Schlüssel blockiert. Die derzeitige Registry enthält SGB V,
aber kein vollständiges allgemeines Sozialverwaltungs- und
Sozialgerichtsrecht. FolderHome behauptet deshalb keine umfassende
Sozialrechtsprüfung.

## Amtliche Veröffentlichungswege

Für Produktivsnapshots sind nur ausdrücklich zugelassene amtliche Domains
erlaubt. Die [Verkündungsplattform des Bundes](https://www.recht.bund.de/de/home/home_node.html)
stellt die amtliche Fassung des Bundesgesetzblatts bereit. Das
[DIP des Deutschen Bundestages](https://www.bundestag.de/dokumente/parlamentsdokumentation)
dokumentiert parlamentarische Vorgänge bis zur Verkündung. Konsolidierte
Bundesgesetze können aus `gesetze-im-internet.de` stammen.

Diese Quellen erfüllen unterschiedliche Rollen: Ein parlamentarischer
Entwurf ist keine Verkündung; eine Verkündung ist nicht automatisch derselbe
Darstellungstyp wie ein konsolidierter Normstand. Das Snapshotmodell hält
deshalb `legislative_proposal`, `promulgated` und `consolidated_current`
getrennt. Die Beschaffung selbst gehört nicht in den lokalen Vergleichslauf.

## Neuer gekapselter Kern

`contracts.legal_change_monitor` und `application.legal_change_monitor` sind
providerunabhängig und später wiederverwendbar. Sie modellieren:

- unvollständige, quellen- und hashgebundene Normabschnittssnapshots,
- explizite `user_provided`-Interessen für Profil oder Vertrag,
- technische Änderungen `added`, `modified` und `removed`,
- reine `review_candidate`-Zuordnungen über gemeinsame Themen-Tags,
- lokale Markdown-/JSON-Ausgaben hinter einem Never-overwrite-Gate.

Die Dateien werden vor Vergleich und Ausgabe erneut gehasht. Quellen dürfen
nicht in der Zukunft liegen und die konfigurierte Altersgrenze nicht
überschreiten. Produktivquellen außerhalb der Allowlist blockieren. Der
synthetische Wettbewerbscase ist durch `fixture_only=true`,
`authoritative=false`, `example.invalid` und ein explizites CLI-Testgate
isoliert.

## Nicht verklebte Folgeschritte

Der Monitor verbindet bewusst nicht automatisch:

- Bescheidextraktion oder Verwaltungsentwurf,
- rechtliche Einzelfallprüfung,
- Übergangs- und Fristberechnung,
- periodische Webbeschaffung,
- Desktop-, Kalender- oder Mailbenachrichtigung.

Diese Trennung verhindert, dass ein technischer Textdiff als Rechtswirkung
oder ein Tag-Match als persönliche Betroffenheit erscheint. Künftige
Provider können den gekapselten Snapshotvertrag speisen; Freigaben und
Fachprüfung bleiben eigene Grenzen.

## Abnahme

Die Phase-34-Tests decken Provideridentität, falsche Revision, fehlenden
Registryschlüssel, geänderten Wortlaut, nicht passendes Interesse, Entwurf,
Quellenalter, nichtamtliche Domain, Sensitivitäts-/Fixture-Gates,
Hashänderung, Output-Gate und Never-overwrite ab. Der CLI-Usecase qualifiziert
den Provider, vergleicht den synthetischen Stand und schreibt einen lokalen
Bericht ohne Netzwerkzugriff oder Außenwirkung.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
