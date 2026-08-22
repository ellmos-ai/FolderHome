# Workflow: Kalenderconnector sicher planen und simulieren

> **Last verified:** 2026-08-22
> **Frequency:** bei ausdrücklich gewünschter Kalenderübergabe
> **Duration:** Planung wenige Sekunden; ein realer Connectorlauf ist nicht Teil der Abnahme

## Purpose

Aus belegten Phase-17-Terminkandidaten einen providerneutralen Connectorplan
für UpToday, Routinika oder Google erzeugen und den Ablauf optional ohne
Netzwerk gegen den synthetischen Provider prüfen.

## Preconditions

- Dokumentordner, Profil, Bereich und State-Ordner sind ausdrücklich gewählt.
- Das Konto gehört zum Profil und nennt eine konkrete Kalender-ID.
- Die Konfiguration enthält nur eine Connector-Referenz, keine Zugangsdaten.
- Reale Kalenderaktionen besitzen eine separate Nutzerfreigabe außerhalb
  dieses lokalen Workflows.

## Steps

1. **Provider inventarisieren** — Revision, Rolle und Live-Grenze prüfen.

   ```powershell
   $env:PYTHONPATH = "src"
   python -m folderhome calendar connectors --json
   ```

2. **Phase-17-Handoff erstellen** — Dokumente extrahieren, Profilfallback,
   Zeitzone und Evidenz prüfen. Dieser Schritt bleibt read-only.

3. **Connectorplan erzeugen** — Konto und Anfrage laden; Google bleibt
   `review_required`, Routinika bleibt blockiert und UpToday delegiert an ICS.

   ```powershell
   python -m folderhome calendar connector-plan `
     --source-dir examples\documents\calendar `
     --calendar-config examples\calendar\calendar-config-google.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-calendar-state" `
     --profile lukas --area gesundheit `
     --planned-at 2026-08-22T04:20:00+02:00 `
     --connector-accounts examples\calendar\connector-accounts.json `
     --connector-request examples\calendar\connector-request-google.json `
     --approve-sensitive-local-read --json
   ```

4. **Payload prüfen** — Kalender-ID, Solo-Teilnehmerliste, Zeitoffset,
   Endzeit, Transparenz, Reminder und Quellaktionsreferenz kontrollieren.

5. **Nur lokal simulieren** — der zusätzliche Provider- und Ausführungsschalter
   macht die Absicht sichtbar. Es wird kein Google-Skill aufgerufen.

   ```powershell
   python -m folderhome calendar connector-simulate `
     --source-dir examples\documents\calendar `
     --calendar-config examples\calendar\calendar-config-google.json `
     --profiles-dir examples\profiles `
     --state-dir "$env:TEMP\folderhome-calendar-state" `
     --profile lukas --area gesundheit `
     --planned-at 2026-08-22T04:20:00+02:00 `
     --connector-accounts examples\calendar\connector-accounts.json `
     --connector-request examples\calendar\connector-request-google.json `
     --approve-sensitive-local-read --use-synthetic-provider `
     --approval-id calendar-demo `
     --approved-at 2026-08-22T04:21:00+02:00 `
     --approve-synthetic-calendar --json
   ```

6. **Report prüfen** — nur `status=simulated`, `network_invoked=false` und
   `live_calendar_written=false` gelten als lokale Abnahme.

## Exit-Criteria

- [ ] Konto, Profil, Backend und Phase-17-Handoff stimmen überein.
- [ ] Providerrevision und Profilregelquelle sind sichtbar.
- [ ] Erstellen, Aktualisieren, Löschen und Erinnern sind getrennt modelliert.
- [ ] Google-Handoff enthält explizite Kalender-ID und Offsetzeiten.
- [ ] Ohne bestehende Providerreferenz bleiben Update und Löschen blockiert.
- [ ] Ohne reale Nutzerfreigabe wurden weder Netzwerk noch Kalender verändert.

## Fallstricke

- Eine vorhandene UpToday-Installation ist kein Live-Sync; FolderHome nutzt
  nur den nachgewiesenen ICS-Dateihandoff.
- Ein Routinika-Bundle ist kein Connectorvertrag.
- `primary` ist eine explizite Google-Kalender-ID, kein impliziter Ersatz für
  ein unbekanntes Ziel.
- Ein Reminder im Ereignispayload ist noch keine nachgewiesene Zustellung.
- Update oder Löschen ohne bestehende Provider-Ereignis-ID ist fail-closed.
- Serienereignisse benötigen später eine ausdrückliche Scope-Entscheidung.

## Verwandte

- [`../docs/phase27-calendar-connector-plan.md`](../docs/phase27-calendar-connector-plan.md)
- [`../skills/folderhome-calendar-connectors/SKILL.md`](../skills/folderhome-calendar-connectors/SKILL.md)
- [`calendar-handoff.md`](calendar-handoff.md)

## Historie

- **2026-08-22** — UpToday-, Routinika- und Google-Routen inventarisiert und
  synthetischen No-Network-Ablauf lokal abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
