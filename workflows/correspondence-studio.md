# Workflow: Korrespondenz sicher erstellen

> **Last verified:** 2026-08-22
> **Frequency:** ad-hoc
> **Duration:** wenige Sekunden pro Brief

## Purpose

Einen Brief aus einer kontrollierten Vorlage und einem eigenen, vererbbaren
Design zunächst vollständig lokal ansehen und anschließend als neue
Markdown- und TXT-Dateien ausgeben. Vorhandene Dateien werden nicht ersetzt.

## Preconditions

- Anfrage, Designs und Vorlagen sind lokale UTF-8-JSON-Dateien.
- Das angegebene Profil existiert in der Profilkonfiguration.
- Personenbezogene Inhalte dürfen für diesen lokalen Lauf gelesen werden.
- Beide geplanten Ausgabepfade sind neu und verschieden.

## Steps

1. **Vorschau erzeugen** — Designauflösung, Inhalt, Hashes und blockierte
   Office-Handoffs prüfen.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome correspondence preview `
     --request-file examples\correspondence\insurance-cancellation.json `
     --designs-file examples\correspondence\designs.json `
     --templates-file examples\correspondence\templates.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --json
   ```

2. **Inhalt kontrollieren** — Absender, Empfänger, Datum, Betreff,
   Vertragskennung, Frist, Anlagen und ausgewähltes Design mit den Quellen
   vergleichen. Der Preview-Lauf schreibt keine Datei.

3. **Neue Zielpfade wählen** — einen eigenen Ausgabeordner und zwei noch
   nicht vorhandene Dateinamen festlegen.

   ```powershell
   $demoOutput = Join-Path $env:TEMP "folderhome-correspondence-demo"
   New-Item -ItemType Directory -Force $demoOutput | Out-Null
   ```

4. **Ausgabe freigeben** — erst nach der Sichtprüfung Markdown und TXT als
   zusammengehörigen Batch schreiben.

   ```powershell
   python -m folderhome correspondence render `
     --request-file examples\correspondence\insurance-cancellation.json `
     --designs-file examples\correspondence\designs.json `
     --templates-file examples\correspondence\templates.json `
     --profiles-dir examples\profiles `
     --approve-sensitive-local-read `
     --markdown-file "$demoOutput\Versicherungskuendigung.md" `
     --text-file "$demoOutput\Versicherungskuendigung.txt" `
     --approve-output-write `
     --json
   ```

5. **Hashes und Grenzen prüfen** — Reporthashes mit den beiden Dateien
   vergleichen und verifizieren, dass kein Office-, LLM- oder Remote-Provider
   ausgeführt wurde.

## Exit-Criteria

- [ ] Vorschau nennt das erwartete Design und `read_only=true`.
- [ ] Absender, Empfänger, Inhalt, Anlagen und Evidenzreferenzen sind geprüft.
- [ ] Beide neuen Dateien besitzen die im Ausgabereport genannten Hashes.
- [ ] `provider_invoked=false`; Versand, Druck und Veröffentlichung blieben aus.

## Fallstricke

- Unsichere Platzhalter mit Attribut-, Index-, Konvertierungs- oder
  Formatsyntax werden absichtlich blockiert.
- Fehlende und zusätzliche Variablen sind Konfigurationsfehler.
- Alle Designbindungen sind explizit; es gibt keine fuzzy Zuordnung.
- Die Zweierausgabe wird vorab geprüft und bei einem eigenen Teilfehler
  zurückgerollt.
- DOCX/ODT werden erst freigegeben, wenn Provideridentität und visuelle
  Renderprüfung nachweislich stimmen.
- Ein zweiter Lauf mit denselben Zielpfaden überschreibt nichts.

## Verwandte

- [`../docs/phase24-correspondence-studio-plan.md`](../docs/phase24-correspondence-studio-plan.md)
- [`../examples/correspondence/README.md`](../examples/correspondence/README.md)

## Historie

- **2026-08-22** — Synthetischen Preview-/Render-Ablauf erstellt und geprüft

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
