---
name: folderhome-calendar-connectors
description: Plane FolderHome-Kalenderübergaben auf Basis belegter Dokumenttermine, route sie zu UpToday, Routinika oder Google und prüfe sie ohne Live-Kalender gegen einen synthetischen Provider.
---

# FolderHome Calendar Connectors

Beginne mit der revisionsgenauen Providerinventur:

```powershell
python -m folderhome calendar connectors --json
```

Baue jeden Connectorplan auf dem bestehenden Phase-17-Kalenderhandoff auf.
Erzeuge niemals parallel eine zweite Dokument-, Profil-, Zeitzonen- oder
Duplikatlogik.

```powershell
python -m folderhome calendar connector-plan `
  --source-dir <documents-dir> `
  --calendar-config <calendar-config.json> `
  --profiles-dir <profiles-dir> --state-dir <state-dir> `
  --profile <profile-id> --area <area> --planned-at <timestamp-with-offset> `
  --connector-accounts <calendar-accounts.json> `
  --connector-request <connector-request.json> `
  --approve-sensitive-local-read --json
```

## Verbindliche Grenzen

- Konfigurationen dürfen nur `connector://`-Referenzen enthalten, niemals
  Tokens, Passwörter oder Cookies.
- Konto, Profil, Backend und Phase-17-Handoff müssen exakt zusammenpassen.
- Ein Plan ruft keinen Connector auf und schreibt keinen Kalender.
- UpToday-Erstellung bleibt beim vorhandenen ICS-Handoff; sie ist kein
  Live-Sync.
- Routinika bleibt ohne geprüften Live-Vertrag blockiert.
- Ein Google-Handoff benötigt eine explizite `calendar_id`, `attendees=[]`,
  `transparency=opaque`, Offsetzeiten und explizite Reminder.
- Update und Löschen benötigen zuerst eine bestehende
  Provider-Ereignisreferenz. Bei Serienereignissen muss später zusätzlich
  Master oder Einzelinstanz gewählt werden.
- Der synthetische Provider benötigt `--use-synthetic-provider` und
  `--approve-synthetic-calendar`. Er beweist nur den Ablauf ohne Netzwerk und
  ohne echten Kalendereintrag.
- Terminerkennung und Reminderzustellung besitzen keine
  Vollständigkeitsgarantie.

Für einen echten Google-Lauf übergib den geprüften Payload erst nach einer
gesonderten Nutzerfreigabe an den `google-calendar`-Skill. Wiederhole vorher
die Prüfung von Kalender-ID, Ereigniszeit, Reminder, Teilnehmern und
Operationsumfang. Ein `review_required`-Plan ist keine Ausführungsfreigabe.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
