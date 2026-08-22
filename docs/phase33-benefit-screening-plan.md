# Phase 33: Leistungs- und Fördervorcheck mit amtlichen Handoffs

**Stand:** 2026-08-22  
**Zweck:** Nutzerbereitgestellte Profilfakten gegen einen datierten,
unvollständigen Routingkatalog prüfen und passende amtliche Lotsen als
nächsten Schritt anzeigen, ohne Leistungsberechtigung, Höhe oder Antrag zu
behaupten.

## Bestandsabgleich

Es existiert kein passender extrahierter Leistungsprüfer:

| Bestand | Revision | Befund | Verwendung |
|---|---|---|---|
| `ellmos-ai/skills` | `0317f32310eed11d21f603cb6f22a689485af226` | `foerderplaner` plant pädagogische Förderung | keine fachliche Runtime |
| BACH | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` | allgemeine alte Sozialrechts-Wikiseiten, keine sichere Vorcheck-API | kein Import, kein kopierter Code |
| extrahierte OneDrive-Module | gezielte Namenssuche 2026-08-22 | kein Förder-/Sozialleistungsprovider gefunden | neue Kapsel erforderlich |

Der neue Kern liegt in `contracts.benefit_screening` und
`application.benefit_screening`. Er ist unabhängig von konkreten
Leistungsarten und kann später in Sovereign oder weiteren Modulen verwendet
werden.

## Amtliche Handoffs

Der am 2026-08-22 geprüfte Beispielkatalog enthält:

- den [Sozialleistungsfinder der Sozialplattform](https://sozialplattform.de/inhalt/sozialleistungen-finden),
- den [KiZ-Lotsen der Bundesagentur für Arbeit](https://www.arbeitsagentur.de/familie-und-kinder/kinderzuschlag-verstehen/kiz-lotse),
- den [Wohngeld-Plus-Rechner des BMWSB](https://www.bmwsb.bund.de/DE/wohnen/wohngeld/wohngeldrechner/wohngeldrechner-2025_artikel.html).

Die Sozialplattform beschreibt ihren Finder selbst als Orientierung und
verweist die verbindliche Entscheidung an die zuständige Stelle. Auch KiZ-
Lotse und Wohngeldrechner sind amtliche Vorchecks beziehungsweise
Orientierungen. FolderHome verlinkt sie deshalb, statt ihre komplexen und
änderungsanfälligen Einzelfallberechnungen zu duplizieren.

## Daten- und Quellenmodell

Das Leistungsprofil ist fachlich vom organisatorischen FolderHome-Profil
getrennt. Es enthält ausschließlich `user_provided`-Fakten mit stabilen
Schlüsseln und ist per Datei-SHA-256 gebunden. FolderHome extrahiert diese
Angaben in Phase 33 nicht automatisch aus Bescheiden, Kontoauszügen oder
anderen Dokumenten.

Jede Katalogquelle besitzt Herausgeber, Titel, HTTPS-URL, geprüften Zeitpunkt,
eine kurze Evidenzzusammenfassung und deren SHA-256. Nur als amtlich
bestätigte Quellen werden akzeptiert. Jedes Programm nennt:

- offizielle Information und amtlichen Vorcheck,
- die verwendeten Quellen,
- wenige grobe Routingkriterien,
- ausdrücklich alle nicht modellierten Einzelfallanforderungen.

Der Katalog muss `complete=false` ausweisen. Ein späterer Updateprozess darf
diese Grenze nur mit einem fachlich belegten Vollständigkeitsvertrag ändern.

## Auswertung

```text
Sensitivitätsfreigabe + bekanntes Profil + Leistungsprofil + Katalog
  → Profil- und Kataloghash prüfen
  → amtliche Quellen und Evidenzhashes validieren
  → checked_at gegen explizites as_of und Altersgrenze prüfen
  → pro Programm ausschließlich Routingkriterien auswerten
  → fehlende Fakten, Mismatch oder veraltete Quelle sichtbar halten
  → amtlichen Vorcheck als nächsten Schritt empfehlen
  → optional neuen Markdown-/JSON-Bericht hinter Output-Gate schreiben
```

Die vier Statuswerte sind:

- `official_handoff_recommended`: Die grobe Route passt; amtlichen Vorcheck
  öffnen und vollständige Angaben dort prüfen.
- `needs_information`: Mindestens eine Routingangabe fehlt.
- `routing_mismatch`: Eine grobe Route passt nicht. Das ist keine Ablehnung.
- `blocked_source_stale`: Mindestens eine verwendete Quelle ist älter als die
  konfigurierte Grenze; keine Regel wird ausgewertet.

Alle Berichte bleiben `review_required`. `eligibility_assessed`,
`amount_estimated`, `application_generated` und `network_used` sind immer
`false`.

## Abnahme

Die synthetische Abnahme prüft amtlichen Handoff, fehlende Fakten, Mismatch,
veraltete Quellen, HTTPS-/Amtlichkeitsgate, Sensitivitätsgate,
Evidenzzusammenfassungshash, veränderten Katalog, Output-Gate und
Never-overwrite. Der CLI-Test prüft alle drei realen amtlichen Handoffs ohne
Netzwerkaufruf oder Antrag.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
