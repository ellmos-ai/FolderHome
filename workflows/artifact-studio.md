# Workflow: Artefakte sicher planen und gestalten

> **Last verified:** 2026-08-22
> **Frequency:** ad-hoc
> **Duration:** wenige Sekunden für Plan und lokale Designausgabe

## Purpose

Eine gewünschte Präsentation, Tabelle, Datei, Visitenkarte oder
Medienausgabe dem vorhandenen Spezialisten zuordnen, fehlende Qualitätsgates
sichtbar halten und ein lokales Designset kontrolliert erzeugen.

## Preconditions

- Anfrage und Profilkonfiguration liegen lokal als UTF-8-Dateien vor.
- Personenbezogene Inhalte dürfen für diesen Lauf gelesen werden.
- Für lokale Designausgaben sind drei neue, verschiedene Zielpfade gewählt.

## Steps

1. **Artefaktplan erzeugen** — keine Provider oder Skills werden ausgeführt.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome artifacts plan `
     --request-file examples\artifacts\artifact-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```

2. **Routen prüfen** — `blocked` stoppen, bei `review_required` alle genannten
   Gates erfüllen und nur `ready` ohne zusätzliche Providerabhängigkeit
   weiterführen.

3. **Designvorschau erzeugen** — Designtokens, Kontrastchecks und SVG-Inhalt
   kontrollieren; dieser Schritt schreibt nichts.

   ```powershell
   python -m folderhome artifacts design-preview `
     --request-file examples\artifacts\design-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```

4. **Lokale Ausgabe freigeben** — erst nach der Inhaltsprüfung drei neue
   Dateien als zusammengehörigen Batch schreiben.

   ```powershell
   $artifactOutput = Join-Path $env:TEMP "folderhome-artifact-demo"
   New-Item -ItemType Directory -Force $artifactOutput | Out-Null
   python -m folderhome artifacts design-render `
     --request-file examples\artifacts\design-request.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json-file "$artifactOutput\design-set.json" `
     --css-file "$artifactOutput\design-set.css" `
     --business-card-file "$artifactOutput\visitenkarte.svg" `
     --approve-output-write `
     --json
   ```

5. **Visuell prüfen** — jede konkrete SVG-Karte rasterisieren oder in einem
   vertrauenswürdigen lokalen Viewer vollständig ansehen. Erst danach darf
   eine separate Druckfreigabe erwogen werden.

## Exit-Criteria

- [ ] Jede angeforderte Artefaktart besitzt eine begründete Route.
- [ ] Kein blockierter Provider wurde aufgerufen oder ersetzt.
- [ ] Designkontraste sind bestanden und nutzerbezogene Inhalte korrekt.
- [ ] Drei neue Dateien stimmen mit den Reporthashes überein.
- [ ] Versand, Upload, Druck, Veröffentlichung und Remote-Verarbeitung blieben aus.

## Fallstricke

- Ein installierter Skill beweist nicht, dass sein Runtime- oder Render-Gate
  in der aktuellen Sitzung verfügbar ist.
- Poppler kann Office-Dateien nicht selbst rendern; ohne `soffice` ist die
  entsprechende Office-Sichtprüfung nicht erfüllt.
- Eine synthetisch geprüfte Beispielkarte beweist nicht die visuelle Qualität
  einer späteren Karte mit anderen Textlängen.
- Ein zweiter Ausgabelauf mit denselben Pfaden überschreibt nichts.

## Verwandte

- [`../docs/phase25-artifact-studio-plan.md`](../docs/phase25-artifact-studio-plan.md)
- [`../skills/folderhome-artifact-studio/SKILL.md`](../skills/folderhome-artifact-studio/SKILL.md)

## Historie

- **2026-08-22** — Providerplan, Designset und SVG-Visitenkarte erstmals abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
