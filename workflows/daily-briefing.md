# Workflow: Wetter- und Newspaper-Brief lokal zustellen

> **Last verified:** 2026-08-22
> **Frequency:** nach Bereitstellung eines neuen, datierten Snapshotpaars
> **Duration:** wenige Sekunden

## Purpose

Einen Wetter- und Nachrichtensnapshot nachvollziehbar zu einem HTML-Brief
bündeln und exakt diese Ausgabe nach einer zweiten Freigabe in einen
gewählten Desktopordner kopieren.

## Preconditions

- Wetter- und Nachrichtensnapshot folgen den FolderHome-V1-Schemas.
- Profil, Briefingdatum, `as_of`, Zeitzone und Kategorien sind ausdrücklich
  gesetzt.
- Snapshotquellen verwenden HTTPS und besitzen Abrufzeitpunkte.
- Der Desktopordner existiert bereits und ist ausdrücklich gewählt.
- Ein Live-Abruf oder eine automatische Schedulerregistrierung wird nicht
  erwartet.

## Steps

1. **Providergrenzen prüfen.**

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome briefing providers --json
   ```

2. **Plan read-only erzeugen.** Zwischenablage und Desktopziel müssen
   verschiedene Ordner sein.

   ```powershell
   python -m folderhome briefing plan `
     --request-file examples\briefing\briefing-request.json `
     --profiles-dir examples\profiles `
     --output-file <ausgabe\Morgenbrief.html> `
     --desktop-file <Desktop\Morgenbrief.html> `
     --approve-sensitive-local-read --json
   ```

3. **Datenstand prüfen.** Wetterort, Beobachtungszeit, Nachrichtenquellen,
   Kategorien, ausgelassene Artikel und jede `stale`-Warnung kontrollieren.
4. **Render separat freigeben.** Approval bindet Plan-ID, Planhash,
   HTML-Hash und Zwischenausgabe.
5. **Neue HTML-Datei rendern.**

   ```powershell
   python -m folderhome briefing render <Argumente aus Schritt 2> `
     --approval-file <render-approval.json> --approve-output-write --json
   ```

6. **Gerenderte Datei lokal öffnen und prüfen.** Links, Umlaute, Wetterwerte,
   Warnungen und Quellenstand kontrollieren.
7. **Desktopkopie separat freigeben.** Approval bindet denselben Plan- und
   HTML-Hash sowie exakt das Desktopziel.
8. **Exakten Hash zustellen.**

   ```powershell
   python -m folderhome briefing deliver <Argumente aus Schritt 2> `
     --approval-file <desktop-approval.json> --approve-desktop-write --json
   ```

## Exit-Criteria

- [ ] Profil, Datum, Zeitzone und beide Snapshot-Hashes sind sichtbar.
- [ ] Veraltete Daten sind als `stale` und `review_required` markiert.
- [ ] Rendern hat keine Desktopdatei erzeugt.
- [ ] Desktopzustellung hat exakt den freigegebenen HTML-Hash kopiert.
- [ ] Keine vorhandene Datei wurde überschrieben.
- [ ] Kein Netzwerk oder Scheduler wurde verwendet oder registriert.

## Fallstricke

- Ein lokaler Snapshot ist kein Beleg für einen aktuell erfolgreichen
  Live-Abruf.
- `review_required` darf nicht als aktuelle oder vollständige Zeitung
  dargestellt werden.
- Das Render-Gate ersetzt nicht das Desktop-Gate.
- Eine Einzelfreigabe ist keine dauerhafte Scheduler- oder Netzwerkvollmacht.
- Profile ordnen Briefings; das Betriebssystemkonto bleibt die
  Sicherheitsgrenze.

## Verwandte

- [`../docs/phase30-daily-briefing-plan.md`](../docs/phase30-daily-briefing-plan.md)
- [`../skills/folderhome-daily-briefing/SKILL.md`](../skills/folderhome-daily-briefing/SKILL.md)
- [`../reused/bach-daily-briefing/README.md`](../reused/bach-daily-briefing/README.md)

## Historie

- **2026-08-22** — lokales Snapshotbriefing und getrennte Desktopzustellung abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
