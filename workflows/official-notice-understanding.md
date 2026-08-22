# Workflow: Sozialrechtlichen Bescheid verstehen

> **Last verified:** 2026-08-22
> **Frequency:** pro bereitgestelltem Bescheid
> **Duration:** wenige Sekunden zuzüglich menschlicher Prüfung

## Purpose

Ausdrücklich beschriftete Angaben eines lokalen Bescheids nachvollziehbar
erfassen und als prüfbaren Markdown-/JSON-Bericht ausgeben. Dieser Workflow
ist Dokumentenverständnis und keine Rechtsprüfung.

## Preconditions

- Der Bescheid liegt lokal in einem von `doc-services` unterstützten Format.
- Das betroffene Profil existiert in der gewählten Profilkonfiguration.
- Ein optionales Zugangsdatum stammt vom Menschen und ist als solches bekannt.
- Der gepinnte `doc-services`-Checkout ist sauber und revisionsgenau.
- Für laufende oder unklare Fristen ist qualifizierte Hilfe erreichbar.

## Steps

1. **Providergrenzen prüfen.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome notices providers --json
   ```

   `document_extraction` muss `ready` sein. `legal_review` bleibt in Phase 31
   erwartungsgemäß `blocked_not_integrated`.

2. **Bescheid read-only analysieren.** Das Zugangsdatum nur angeben, wenn es
   der Mensch tatsächlich bestätigt hat.

   ```powershell
   python -m folderhome notices inspect `
     --source-file examples\notices\Bescheid.txt `
     --profiles-dir examples\profiles `
     --profile lukas `
     --received-on 2026-08-21 `
     --as-of 2026-08-22T12:00:00+02:00 `
     --approve-sensitive-local-read --json
   ```

3. **Evidenz und Grenzen prüfen.** Quellhash, Zeilen, fehlende Felder,
   Konflikte, gedruckten Fristtext und jedes ausdrücklich gedruckte
   Fristdatum kontrollieren. Resttage sind nur Kalenderarithmetik zu diesem
   gedruckten Datum.
4. **Bericht separat freigeben.** Zwei neue, noch nicht vorhandene Ziele
   wählen und die Quelle unverändert lassen.
5. **Markdown und JSON rendern.**

   ```powershell
   python -m folderhome notices render `
     --source-file examples\notices\Bescheid.txt `
     --profiles-dir examples\profiles `
     --profile lukas `
     --received-on 2026-08-21 `
     --as-of 2026-08-22T12:00:00+02:00 `
     --markdown-file <Ausgabe\Bescheidbericht.md> `
     --json-file <Ausgabe\Bescheidbericht.json> `
     --approve-sensitive-local-read --approve-output-write --json
   ```

6. **Menschlich entscheiden.** Bei `review_required`, unklarer Frist oder
   gewünschter rechtlicher Bewertung den Bericht mit dem Original an eine
   qualifizierte Stelle geben. Keine Antwort aus Phase 31 versenden.

## Exit-Criteria

- [ ] Profil, Analysezeit, Dokument-ID und Quellhash sind sichtbar.
- [ ] Jedes übernommene Feld nennt seine genaue Quellzeile.
- [ ] Konflikte und fehlende Angaben wurden nicht versteckt.
- [ ] Relative Fristtexte wurden nicht zu gesetzlichen Daten umgerechnet.
- [ ] Bericht und JSON sind neu angelegt; das Original blieb unverändert.
- [ ] `legal_review_status` lautet `not_performed`.
- [ ] Keine Antwort, E-Mail, Behördenaktion oder sonstige Außenwirkung erfolgte.

## Fallstricke

- Ein gedrucktes Datum kann falsch, unvollständig oder rechtlich nicht das
  tatsächliche Fristende sein.
- Datei- und Scanzeitpunkte sind kein Zugangsdatum.
- OCR ist in dieser Phase absichtlich deaktiviert.
- `ready_for_review` bedeutet bereit für menschliche Prüfung, nicht rechtlich
  richtig oder vollständig.
- Ein relativer Fristtext wie „innerhalb eines Monats“ benötigt eine aktuelle
  Rechtsprüfung und darf nicht automatisiert umgedeutet werden.

## Verwandte

- [`../docs/phase31-official-notice-understanding-plan.md`](../docs/phase31-official-notice-understanding-plan.md)
- [`../skills/folderhome-official-notices/SKILL.md`](../skills/folderhome-official-notices/SKILL.md)
- [`../reused/law-checker/README.md`](../reused/law-checker/README.md)

## Historie

- **2026-08-22** — evidenzgebundenes Bescheidverständnis lokal abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
