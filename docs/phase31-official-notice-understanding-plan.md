# Phase 31: Sozialrechtliche Bescheide sicher verstehen

**Stand:** 2026-08-22  
**Zweck:** Aus einem bereitgestellten Bescheid ausdrücklich beschriftete
Angaben mit Evidenz extrahieren, Widersprüche sichtbar machen und einen
verständlichen lokalen Prüfbericht erzeugen, ohne eine Rechtsprüfung,
Fristberechnung oder Antwort zu behaupten.

## Bestandsabgleich

Für Phase 31 wurden der zentrale Skills-Bestand und der vorhandene
`law-checker` geprüft:

| Bestand | Revision | Befund | Verwendung |
|---|---|---|---|
| `ellmos-ai/skills` | `0317f32310eed11d21f603cb6f22a689485af226` | lokaler Checkout sauber, aber einen Commit hinter Upstream | Methodenreferenz über den `law-checker`-Pointer |
| `ellmos-ai/law-checker` | `330fe47b3621c69ec824cd05ca5b283e107f9eaf` | Checkout einen Commit hinter Upstream und fremd verändert | keine Runtime-Anbindung |
| `doc-services` | `037a432bbec94ac6db5dfa53941745fda7c2f38a` | gepinnter, sauberer Provider | lokale Textextraktion ohne OCR |

Der vorhandene `law-checker` ist für eine erste rechtliche Orientierung
konzipiert und verlangt genaue Quellen, Fristprüfung und menschliche
Eskalation. Sein lokales Gesetzesregister deckt jedoch kein vollständiges
allgemeines Verfahrens- und Sozialgerichtsrecht für beliebige Bescheidarten
ab. Außerdem ist der Checkout nicht sauber und nicht aktuell. FolderHome lädt
ihn deshalb in Phase 31 nicht als Runtime und kopiert keinen Code.

## Neuer gekapselter Kern

`contracts.official_notices` und `application.official_notices` sind neuer,
wiederverwendbarer Wettbewerbscode. Sie kapseln:

- die Profil-, Zeit-, Dokument- und Quellhashbindung einer Bescheidanalyse,
- streng beschriftete Felder für Bescheidart, Behörde, Aktenzeichen,
  Bescheiddatum, Leistungszeitraum, Entscheidung und Begründung,
- ausdrücklich gedruckte Rechtsbehelfs-, Frist- und Stellenangaben,
- Evidenz pro Feld mit Zeilennummer, Dokument-ID und Quellhash,
- sichtbare Mehrdeutigkeiten statt willkürlicher Auswahl,
- fehlende Felder, Warnungen und einen eindeutigen Prüfstatus,
- getrennte Markdown-/JSON-Ausgabe mit Schreibgate und Never-overwrite.

Die Kapsel kann später auch in Sovereign verwendet werden. Der vorhandene
`doc-services`-Provider übernimmt ausschließlich die lokale Extraktion; die
fachliche Bescheidstruktur gehört FolderHome.

## Ablauf

```text
Bescheid + Profil + explizite Sensitivitätsfreigabe
  → gepinnten doc-services-Checkout prüfen
  → Text lokal extrahieren und Quellhash bestätigen
  → ausschließlich bekannte, ausdrücklich gelabelte Felder lesen
  → jedes Feld an Zeile, Dokument-ID und Quellhash binden
  → Konflikte und fehlende Angaben sichtbar machen
  → gedrucktes Fristdatum optional gegen explizites as_of zählen
  → read-only Analyse ausgeben
  → nach separatem Schreibgate neue Markdown-/JSON-Dateien erzeugen
```

Ein optionales Zugangsdatum ist immer als Nutzerangabe ausgewiesen. Es wird
nicht aus Metadaten erraten. Ein ausdrücklich gedrucktes Fristdatum darf zur
Orientierung gegen `as_of` gezählt werden; das Ergebnis ist keine gesetzliche
Fristberechnung. Relative Fristtexte werden nicht in Daten umgerechnet.

## Rechts- und Sicherheitsgrenze

Phase 31 führt keine Rechtsprüfung durch. Sie bestimmt weder, ob ein Bescheid
rechtmäßig ist, noch wann eine gesetzliche Frist tatsächlich beginnt oder
endet. Sie erstellt keinen Widerspruch, keinen Antrag und keine Nachricht an
eine Behörde. OCR ist in dieser Anbindung deaktiviert, damit ein unsicheres
Erkennungsergebnis nicht still als belastbare Fristangabe erscheint.

Der Bericht weist diese Grenzen sichtbar aus. Fehlende oder widersprüchliche
Kernangaben führen zu `review_required`. Laufende oder unklare Fristen
erfordern unverzügliche qualifizierte sozialrechtliche Hilfe. Eine spätere
Rechtsprüfung muss den `law-checker` zuerst aktualisieren, bereinigen,
fachlich erweitern und an aktuelle amtliche Quellen binden.

## Abnahme

Die synthetische Abnahme prüft Feld- und Evidenzbindung, relative Fristtexte,
Konflikte, Sensitivitäts- und Ausgabegates, geänderte Quellen und
Never-overwrite. Der CLI-Test führt Providerinventar, read-only Analyse und
Berichtsausgabe Ende zu Ende aus. Er bestätigt ausdrücklich, dass keine
Rechtsprüfung, Antwort oder Außenwirkung stattgefunden hat.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
