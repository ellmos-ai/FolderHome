# Workflow — Versicherungs- und Vertragscockpit

## Zweck

Eine Anfrage wie „Was ist meine neueste KFZ-Versicherung für meinen Hyundai
i10?“ als read-only Überblick beantworten. Das Cockpit setzt vorhandene
Dokumentversionen, Kontaktregister, wiederkehrende Kosten, Kalenderereignisse
und Kontoauszugsabdeckung zusammen. Fehlende Evidenz bleibt sichtbar.

## Synthetischer Lauf

```powershell
$env:PYTHONPATH = "src"
$demoState = Join-Path $env:TEMP "folderhome-contract-demo"

python -m folderhome documents ingest `
  --source-dir examples\contracts\documents `
  --state-dir $demoState `
  --approve-index-write --json

python -m folderhome contracts cockpit `
  --request-file examples\contracts\cockpit-hyundai-i10.json `
  --state-dir $demoState `
  --profiles-dir examples\profiles `
  --approve-sensitive-local-read `
  --output-markdown "$env:TEMP\FolderHome-Vertragscockpit.md" `
  --output-json "$env:TEMP\FolderHome-Vertragscockpit.json" `
  --json
```

Wenn derselbe State zuvor über die freigegebenen Kontakt-, Finanz- oder
Kalenderworkflows befüllt wurde, erscheinen passende Einträge zusätzlich.
Das Cockpit erzeugt diese Zustände nicht selbst.

## Explizite Zuordnung

Die Anfrage deklariert:

- Dokumentensuchanfrage und Vertragsobjekt
- Gegenparteibegriffe für Kostenkandidaten
- Begriffe für Kalenderereignisse
- Kontokennungen und gewünschten Abdeckungszeitraum
- ob ältere Versionen als Archivierungskandidaten erscheinen sollen

Keine fuzzy oder LLM-basierte Verknüpfung wird still vorgenommen.

## Sicherheitsgrenzen

- Ohne Sensitivitätsfreigabe wird kein Dokument-, Kontakt-, Finanz- oder
  Kalenderzustand gelesen.
- Der Cockpit-Lauf verändert den gemeinsamen State nicht.
- Archivierungsvorschläge bleiben ungefreigt und werden nicht ausgeführt.
- Kontakte werden nicht gewechselt oder gelöscht.
- Termine werden nicht angelegt und Nachrichten nicht gesendet.
- Kosten sind belegte Kandidaten oder Hochrechnungen; Vertragsstatus,
  Deckung, Kündigung und künftige Abbuchung werden nicht bewiesen.
- Kontoauszugslücken bleiben sichtbar; Salden werden nicht interpoliert.
- JSON enthält keinen extrahierten Dokumentrohtext.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
