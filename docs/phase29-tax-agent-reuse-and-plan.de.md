# Phase 29: Steueragent wiederverwenden und sicher begrenzen

[English](./phase29-tax-agent-reuse-and-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Zweck:** Vorhandene Beleg- und Arbeitsunterlagenfunktionen des extrahierten
Steueragenten wiederverwenden, ohne Steuerberatung oder Behördenübermittlung
zu behaupten.

## Verifizierter Bestand

Der lokale Checkout `C:\_Local_DEV\repos\steuer-assistent` wurde read-only
geprüft:

| Merkmal | Befund |
|---|---|
| Repository | `https://github.com/ellmos-ai/steuer-assistent.git` |
| Revision | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` |
| Paketversion | `0.2.3` |
| Lizenz | MIT |
| Checkout | sauber und exakt auf der gepinnten Revision |
| Providertests | 35/35 grün |
| Laufzeit | lokale SQLite-Ablage und ZIP-Ausgabe, kein Netzwerk |

Der Provider erfasst nutzerseitig eingeordnete Belege aus dem Bereich
Werbungskosten und erzeugt eine private Arbeitsunterlage. Er prüft weder die
steuerliche Abziehbarkeit noch einen Steuerfall und übermittelt nichts an
ELSTER, ERiC, Finanzamt oder ein anderes Portal.

## Wiederverwendung und neuer Verbindungscode

Unverändert wiederverwendet werden:

- `SteuerAssistent.add_beleg()` für einen ausdrücklich bestätigten Beleg,
- `SteuerAssistent.export_arbeitsunterlage()` für eine private ZIP-Datei,
- die vom Provider unterstützten Eingabegruppen Arbeitsmittel, Fahrtkosten,
  Fortbildung, Homeoffice, Kommunikation und Sonstiges.

Neu und gekapselt sind die FolderHome-Verträge, die Orchestrierung und die
Bridge unter `contracts.tax`, `application.tax_workpaper` und
`bridges.tax_assistant`. Es wird kein Providerquellcode kopiert oder
verändert.

## Beleg- und Profilbindung

Ein Belegplan benötigt eine katalogisierte Dokument-ID, den aktuellen
Dokumenthash, ein bekanntes Familienprofil und optional eine vorhandene
FolderHome-Finanzbuchung desselben Profils. Wenn eine Buchung angegeben wird,
muss ihr absoluter Centbetrag mit dem Beleg übereinstimmen. Ein Dateiname oder
ein freier Suchtreffer genügt nicht als Belegbindung.

Providerstores werden pro Profil in
`tax-workpaper/<profile_id>/steuer.db` getrennt. Das verhindert vermischte
Arbeitsunterlagen innerhalb einer Haushaltsansicht. Es ist keine
Zugriffskontrolle: Alle Profile bleiben innerhalb desselben
Betriebssystemkontos lesbar.

## Vorschlag ist keine steuerliche Einordnung

`category_candidate` ist nur ein prüfpflichtiger Vorschlag. Solange
`confirmed_category` fehlt, besitzt der Plan den Status `review_required`
und `provider_write_allowed=false`. FolderHome überführt den Vorschlag nicht
selbstständig in eine bestätigte Kategorie.

Auch eine bestätigte Eingabegruppe bedeutet nicht, dass die Ausgabe
steuerlich abziehbar ist. Alle Pläne und Berichte weisen daher
`deductibility_assessed=false` und `tax_advice=false` aus.

## Getrennte Gates

```text
katalogisierter Beleg + optional passende Finanzbuchung
  → Sensitivitätsfreigabe
  → read-only Plan mit Dokument- und Providerstore-Hash
  → menschlich bestätigte Eingabegruppe
  → exakte Approval-Datei + lokales State-Gate
  → Provider schreibt genau einen Beleg
  → separater read-only Exportplan pro Profil und Steuerjahr
  → Export-Approval + State-Gate + Output-Gate
  → neue private ZIP-Arbeitsunterlage
```

Belegerfassung und Export sind getrennte Entscheidungen. Der Export
überschreibt keine vorhandene Datei. Portalzugriff, Netzwerk, Versand,
amtliches Format und Einreichung sind in Phase 29 nicht implementiert und
können durch keinen allgemeinen CLI-Schalter aktiviert werden.

## Abnahme

Die Tests verwenden ausschließlich einen synthetischen Beleg. Sie prüfen den
read-only Plan, die Hash- und Statebindung, Idempotenz, blockierte geänderte
Dokumente, getrennte Exportfreigaben und den echten gepinnten Provider. Seine
eigene Testsuite wurde zusätzlich unverändert ausgeführt.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
