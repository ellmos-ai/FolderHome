# Workflow: Verwaltungsentwurf sicher erstellen

> **Last verified:** 2026-08-22
> **Frequency:** pro Widerspruchs-, Antwort- oder Antragsentwurf
> **Duration:** wenige Sekunden zuzüglich vollständiger menschlicher Prüfung

## Purpose

Einen sichtbar ungeprüften und unversandten Verwaltungsbrief aus belegter
Bescheidstruktur und bereitgestellten Angaben vorbereiten. Der Workflow
erzeugt nur lokale Markdown-/TXT-Dateien.

## Preconditions

- Profil, Absender, Empfänger, gewünschtes Ergebnis und Nutzeraussagen wurden
  ausdrücklich bereitgestellt.
- Bei Widerspruch oder Behördenantwort liegt eine aktuelle Phase-31-Analyse
  derselben unveränderten Quelle vor.
- Die Anfrage enthält den SHA-256 der erwarteten Bescheidquelle.
- Briefdesign und spezielle Verwaltungsbriefvorlagen sind geprüft.
- Frist, Rechtsweg, Zuständigkeit und Inhalt werden fachlich separat geprüft.

## Steps

1. **Vorschau read-only erzeugen.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome drafts preview `
     --request-file examples\notices\objection-draft-request.json `
     --source-file examples\notices\Bescheid.txt `
     --designs-file examples\correspondence\designs.json `
     --templates-file examples\notices\administrative-templates.json `
     --profiles-dir examples\profiles `
     --received-on 2026-08-15 `
     --as-of 2026-08-22T06:00:00+02:00 `
     --approve-sensitive-local-read --json
   ```

2. **Provenienz prüfen.** Dokumentfakten müssen Zeile, Dokument-ID und
   Quellhash nennen. Nutzeraussagen müssen `user_provided` bleiben.
3. **Offene Punkte prüfen.** Insbesondere Frist, Zuständigkeit,
   Rechtsbehelfsart, Aktenzeichen, Empfänger und Anlagen gegen das Original
   kontrollieren. `review_required` wird nicht zu „rechtlich geprüft“.
4. **Brief vollständig lesen.** Der sichtbare `ENTWURF`-Hinweis muss in
   Markdown und TXT enthalten sein.
5. **Approval erzeugen.** Plan-ID, Markdownhash und TXThash aus genau dieser
   Vorschau übernehmen. Inhalt geprüft, fehlende Rechtsprüfung verstanden und
   ausschließlich lokale Ausgabe jeweils boolesch bestätigen.
6. **Lokale Ausgabe hinter eigenem Gate schreiben.**

   ```powershell
   python -m folderhome drafts render <Argumente aus Schritt 1> `
     --approval-file <draft-approval.json> `
     --markdown-file <Ausgabe\Verwaltungsentwurf.md> `
     --text-file <Ausgabe\Verwaltungsentwurf.txt> `
     --approve-output-write --json
   ```

7. **Außenwirkung separat entscheiden.** FolderHome Phase 32 besitzt keinen
   Versand. Vor jeder realen Verwendung ist die aktuelle fachliche Prüfung
   einschließlich Frist, Form, Stelle und Anlagen erforderlich.

## Exit-Criteria

- [ ] Bescheidquelle, Profil, Empfänger und Quellhash stimmen überein.
- [ ] Dokumentevidenz und bereitgestellte Angaben sind getrennt.
- [ ] Der konkrete Briefinhalt und beide Ausgabehashes wurden bestätigt.
- [ ] Markdown und TXT tragen sichtbar den Entwurfs-/Prüfhinweis.
- [ ] Vorhandene Dateien wurden nicht überschrieben.
- [ ] Rechtsprüfung, Leistungsprüfung und Fristberechnung blieben aus.
- [ ] Keine E-Mail, kein Portal, kein Druck und kein Versand wurde ausgelöst.

## Fallstricke

- Ein im Bescheid gedruckter Rechtsbehelf beweist nicht dessen Richtigkeit
  oder Anwendbarkeit im Einzelfall.
- Ein berechneter Resttagewert aus Phase 31 ist keine gesetzliche Frist.
- `user_provided` bedeutet nicht bereits bestätigt oder belegt.
- Eine lokale Output-Freigabe ist keine Versandfreigabe.
- Ein Leistungsantragsentwurf ist kein Leistungs- oder Fördervorcheck.

## Verwandte

- [`../docs/phase32-administrative-drafts-plan.md`](../docs/phase32-administrative-drafts-plan.md)
- [`./official-notice-understanding.md`](./official-notice-understanding.md)
- [`./correspondence-studio.md`](./correspondence-studio.md)
- [`../skills/folderhome-administrative-drafts/SKILL.md`](../skills/folderhome-administrative-drafts/SKILL.md)

## Historie

- **2026-08-22** — evidenzgebundene lokale Verwaltungsentwürfe abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
