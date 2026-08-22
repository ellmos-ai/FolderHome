# Workflow: Private Steuer-Arbeitsunterlage aus bestätigten Belegen

[English](./tax-workpaper.md) | **Deutsch**

> **Last verified:** 2026-08-22
> **Frequency:** nach ausdrücklich bereitgestellten und eingeordneten Belegen
> **Duration:** wenige Sekunden pro Beleg und Export

## Purpose

Einen katalogisierten Beleg nach menschlicher Kategorienbestätigung lokal in
den gepinnten Steueragenten übernehmen und daraus optional eine private,
nicht-amtliche ZIP-Arbeitsunterlage erstellen.

## Preconditions

- Der Beleg ist im FolderHome-Dokumentkatalog enthalten und unverändert.
- Profil und Steuerjahr wurden ausdrücklich gewählt.
- Der `steuer-assistent`-Checkout ist sauber und auf der Manifestrevision.
- Eine Kategorie wurde vom Menschen bestätigt; ein Kandidat allein genügt
  nicht.
- Es wird weder Steuerberatung noch eine Behördenübermittlung erwartet.

## Steps

1. **Provider prüfen.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome tax providers `
     --provider-root ..\steuer-assistent --json
   ```

2. **Beleganfrage vorbereiten.** Dokument-ID und optional die
   FolderHome-Buchungs-ID stammen aus den lokalen Katalogen. Betrag und Datum
   werden nicht aus dem Dateinamen geraten.
3. **Belegplan read-only erzeugen.**

   ```powershell
   python -m folderhome tax receipt-plan `
     --request-file <receipt-request.json> `
     --profiles-dir examples\profiles --state-dir <state-dir> `
     --provider-root ..\steuer-assistent `
     --approve-sensitive-local-read --json
   ```

4. **Plan prüfen.** Dokumenthash, Profil, Centbetrag, Eingabegruppe,
   Providerrevision und Store-Revision kontrollieren. Ein Plan mit
   `review_required` darf nicht ausgeführt werden.
5. **Beleg separat freigeben.** Approval bindet Plan-ID, Planhash,
   Aktions-ID und Store-Revision.
6. **Genau einen Beleg schreiben.**

   ```powershell
   python -m folderhome tax receipt-apply `
     --request-file <receipt-request.json> `
     --approval-file <receipt-approval.json> `
     --profiles-dir examples\profiles --state-dir <state-dir> `
     --provider-root ..\steuer-assistent `
     --approve-sensitive-local-read --approve-state-write --json
   ```

7. **Exportplan pro Profil und Jahr erzeugen.**

   ```powershell
   python -m folderhome tax export-plan --profile lukas --tax-year 2026 `
     --output-file <STEUER_UNTERLAGEN_2026.zip> `
     --profiles-dir examples\profiles --state-dir <state-dir> `
     --provider-root ..\steuer-assistent --json
   ```

8. **Export gesondert freigeben.** Erst `tax export` mit passender
   Export-Approval, `--approve-state-write` und `--approve-output-write`
   erzeugt eine neue ZIP-Datei.

## Exit-Criteria

- [ ] Checkout, Version und Revision sind bestätigt.
- [ ] Der Beleg ist an einen aktuellen Dokumenthash gebunden.
- [ ] Die Kategorie wurde vom Menschen bestätigt.
- [ ] Ohne Approval und State-Gate wurde kein Beleg geschrieben.
- [ ] Der Export besitzt eine eigene Approval und ein eigenes Output-Gate.
- [ ] Kein Netzwerk, Portal, Versand oder amtliches Format wurde verwendet.
- [ ] Die Ausgabe wird als private Arbeitsunterlage, nicht als Steuererklärung bezeichnet.

## Fallstricke

- Eine Eingabegruppe ist keine Aussage über steuerliche Abziehbarkeit.
- Familienprofile ordnen getrennte Stores, sind aber keine Sicherheitsgrenze.
- Ein veralteter Storehash oder ein veränderter Beleg blockiert den Lauf.
- Eine bestehende Exportdatei wird nicht überschrieben.
- ELSTER, ERiC und Finanzamtübermittlung gehören nicht zu diesem Workflow.

## Verwandte

- [`../docs/phase29-tax-agent-reuse-and-plan.md`](../docs/phase29-tax-agent-reuse-and-plan.de.md)
- [`../skills/folderhome-tax-workpaper/SKILL.md`](../skills/folderhome-tax-workpaper/SKILL.md)
- [`../reused/steuer-assistent/README.md`](../reused/steuer-assistent/README.de.md)

## Historie

- **2026-08-22** — gepinnte Belegerfassung und private Arbeitsunterlage lokal abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
