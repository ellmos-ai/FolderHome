# Workflow: Leistungsvorcheck lokal ausführen

[English](./benefit-screening.md) | **Deutsch**

> **Last verified:** 2026-08-22
> **Frequency:** bei geänderter Lebenssituation oder frischem Katalog
> **Duration:** wenige Sekunden zuzüglich amtlichem Vorcheck

## Purpose

Ein lokales Leistungsprofil mit groben, datierten Routingkriterien abgleichen
und passende amtliche Vorchecks anzeigen. Das Ergebnis ist eine Orientierung,
kein Anspruchs- oder Ablehnungsbescheid.

## Preconditions

- Das organisatorische Profil existiert.
- Leistungsprofilfakten wurden vom Menschen bereitgestellt und lokal geprüft.
- Der Katalog nennt ausschließlich amtliche HTTPS-Quellen mit Prüfzeitpunkt.
- `complete=false` und nicht modellierte Anforderungen sind sichtbar.
- Der gewünschte Analysezeitpunkt und das maximale Quellenalter sind gesetzt.

## Steps

1. **Vorcheck read-only ausführen.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome benefits check `
     --profile-facts-file examples\benefits\Lukas-benefit-profile.json `
     --catalog-file examples\benefits\official-routing-catalog.json `
     --profiles-dir examples\profiles `
     --as-of 2026-08-22T07:00:00+02:00 `
     --max-source-age-days 30 `
     --approve-sensitive-local-read --json
   ```

2. **Quellenstand prüfen.** Herausgeber, URL, `checked_at`, Quellenalter,
   Evidenzzusammenfassung und Katalogabdeckung kontrollieren.
3. **Ergebnisse einordnen.** `official_handoff_recommended` ist nur eine
   Route. `needs_information` fordert fehlende Fakten an.
   `routing_mismatch` ist keine Ablehnung. `blocked_source_stale` verlangt
   zuerst einen neuen fachlich geprüften Snapshot.
4. **Optional lokalen Bericht schreiben.**

   ```powershell
   python -m folderhome benefits render <Argumente aus Schritt 1> `
     --markdown-file <Ausgabe\Leistungsvorcheck.md> `
     --json-file <Ausgabe\Leistungsvorcheck.json> `
     --approve-output-write --json
   ```

5. **Amtlichen Vorcheck bewusst öffnen.** Persönliche Daten erst nach eigener
   Entscheidung direkt auf der amtlichen Seite eingeben. FolderHome öffnet
   die URL nicht automatisch.
6. **Verbindliche Entscheidung abwarten.** Nur die zuständige Stelle
   entscheidet über Anspruch, Höhe und erforderliche Nachweise.

## Exit-Criteria

- [ ] Profil- und Kataloghash sowie explizites `as_of` sind sichtbar.
- [ ] Keine Quelle ist neuer als `as_of` oder älter als die Altersgrenze.
- [ ] Fehlende Fakten und nicht modellierte Anforderungen sind sichtbar.
- [ ] Der Katalog weist `complete=false` aus.
- [ ] Keine Leistungsberechtigung oder Höhe wurde behauptet.
- [ ] Kein Antrag, Webaufruf oder sonstiger externer Schritt erfolgte.
- [ ] Vorhandene Ausgabedateien wurden nicht überschrieben.

## Fallstricke

- Ein passendes Routingmerkmal ist keine Anspruchsvoraussetzung.
- Ein Mismatch beweist weder Ausschluss noch fehlenden Anspruch.
- Ein amtlicher Rechner ist weiterhin nur so aktuell wie die konkrete Seite.
- Ein lokaler Katalog wird nicht durch sein Dateidatum automatisch aktuell.
- Leistungsprofile enthalten sensible Angaben und bleiben lokal.

## Verwandte

- [`../docs/phase33-benefit-screening-plan.md`](../docs/phase33-benefit-screening-plan.de.md)
- [`../skills/folderhome-benefit-screening/SKILL.md`](../skills/folderhome-benefit-screening/SKILL.md)
- [`../reused/benefit-routing/README.md`](../reused/benefit-routing/README.de.md)
- [`./administrative-drafts.md`](administrative-drafts.de.md)

## Historie

- **2026-08-22** — quellengebundener Vorcheck mit amtlichen Handoffs abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
