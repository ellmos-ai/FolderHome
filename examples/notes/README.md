# Persönliche Notizen — synthetisches Beispiel

`create-request.json` beschreibt einen ausschließlich synthetischen,
menschlich formulierten Notizinhalt. Dokument- und Kalenderverweise sind
explizit angegeben; FolderHome sucht oder ergänzt keine Verknüpfung selbst.

Zuerst wird nur ein Guide-Plan erzeugt:

```powershell
python -m folderhome notes guide `
  --request-file examples\notes\create-request.json `
  --profiles-dir examples\profiles `
  --state-dir "$env:TEMP\folderhome-note-demo" `
  --provider-root ..\llm-note --json
```

Der Mensch prüft `proposed_content`, Fragen, Vorschläge, Referenzen und Hashes.
Aus genau diesem Plan wird anschließend eine separate
`folderhome.personal-note-approval.v1`-Datei erstellt. Erst
`notes apply --approval-file <Datei> --approve-state-write` hängt eine Version
an die lokale `llm-note`-Datenbank an.

Für `edit` werden `note_id` und die aktuelle `expected_revision` übernommen
und neuer menschlicher Inhalt angegeben. Für `revert` bleibt `human_content`
`null`; `revert_to_revision` nennt die ältere Fassung. Auch eine Rückkehr ist
eine neue Version und keine Löschung.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
