# Workflow: Rechtsänderungen als Prüfkandidaten erfassen

> **Last verified:** 2026-08-22
> **Frequency:** nach fachlich erstelltem neuen Rechtsquellensnapshot
> **Duration:** wenige Sekunden ohne Beschaffung oder Rechtsprüfung

## Purpose

Zwei lokale, datierte Rechtsquellenstände technisch vergleichen und geänderte
Themen mit ausdrücklich hinterlegten Profil- oder Vertragsinteressen
abgleichen. Das Ergebnis ist eine Prüfliste, keine Feststellung rechtlicher
Betroffenheit.

## Preconditions

- Der saubere `law-checker`-Checkout stimmt mit dem gepinnten Manifest überein.
- Produktivsnapshots stammen von zugelassenen amtlichen HTTPS-Domains.
- Wortlaut, Themen-Tags und Snapshotdatei sind per SHA-256 gebunden.
- `complete=false` und die fachliche Abdeckung sind sichtbar.
- Rechtsinteressen wurden vom Menschen bereitgestellt.
- Sensitivitätsfreigabe, `as_of` und maximales Quellenalter sind gesetzt.

## Steps

1. **Providergrenze prüfen.** `folderhome legal providers --json` muss den
   gepinnten Checkout und `legal_review_api_available=false` ausweisen.
2. **Snapshots beschaffen und fachlich prüfen.** FolderHome lädt in diesem
   Workflow keine Gesetze oder Parlamentsdaten selbst herunter.
3. **Vergleich read-only ausführen.** `folderhome legal compare` prüft Hashes,
   Chronologie, Alter, Veröffentlichungsstufe und Normabschnittsänderungen.
4. **Treffer einordnen.** Eine Themenüberschneidung erzeugt ausschließlich
   `review_candidate`; `affected_determined=false` bleibt unveränderlich.
5. **Entwurf von geltendem Recht trennen.** Bei
   `legislative_proposal` lautet der Gesamtstatus
   `proposal_review_required`; der Entwurf wird nie als verkündet bezeichnet.
6. **Optional Bericht ausgeben.** `legal render` schreibt nur nach eigenem
   Output-Gate neue Markdown-/JSON-Dateien und überschreibt nichts.
7. **Fachliche Prüfung separat beauftragen.** Rechtswirkung, Übergangsrecht,
   Einzelfallanwendung, Fristen und Reaktion bleiben außerhalb des Monitors.
8. **Benachrichtigung separat entscheiden.** Dieser Lauf sendet weder Mail
   noch Desktopwarnung und registriert keinen Scheduler.

## Exit-Criteria

- [ ] Providerrevision und Registryabdeckung sind sichtbar.
- [ ] Beide Snapshot- und der Interessenhash wurden erneut gelesen.
- [ ] Nichtamtliche, zukünftige oder veraltete Produktivquellen blockieren.
- [ ] Entwurf, Verkündung und konsolidierter Stand bleiben unterscheidbar.
- [ ] Jeder Treffer ist nur ein `review_candidate`.
- [ ] Rechtswirkung, Betroffenheit und Fristberechnung bleiben `false`.
- [ ] Kein Netzwerkzugriff und keine Benachrichtigung wurden ausgeführt.
- [ ] Vorhandene Ausgabedateien wurden nicht überschrieben.

## Verwandte

- [`../docs/phase34-legal-change-monitor-plan.md`](../docs/phase34-legal-change-monitor-plan.md)
- [`../skills/folderhome-legal-change-monitor/SKILL.md`](../skills/folderhome-legal-change-monitor/SKILL.md)
- [`../reused/law-checker/README.md`](../reused/law-checker/README.md)
- [`./official-notice-understanding.md`](./official-notice-understanding.md)

## Historie

- **2026-08-22** — gepinnter Provider und lokaler Snapshotvergleich abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
