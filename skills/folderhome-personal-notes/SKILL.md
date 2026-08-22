---
name: folderhome-personal-notes
description: Führt Menschen mit getrennten Fragen und Vorschlägen durch lokale FolderHome-Notizen, lässt bestätigte Inhalte revisionssicher in llm-note ablegen und liest Historien ohne Remote-LLM oder Synchronisierung.
---

# FolderHome Personal Notes

Nutze diesen Skill, wenn ein Mensch eine persönliche Notiz anlegen,
überarbeiten, strukturiert durchdenken oder zu einer früheren Fassung
zurückkehren möchte.

## Ablauf

1. Prüfe zuerst den gepinnten Speicherprovider.

   ```powershell
   python -m folderhome notes providers --json
   ```

2. Formuliere den vom Menschen gewünschten Inhalt im Feld `human_content`.
   Trage Dokumente oder Termine nur als ausdrücklich gewählte Referenzen ein.
3. Erzeuge einen Guide-Plan. Fragen und Vorschläge sind Hilfen und dürfen
   `proposed_content` nicht still verändern.

   ```powershell
   python -m folderhome notes guide `
     --request-file <request.json> --profiles-dir <profiles-dir> `
     --state-dir <state-dir> --provider-root <llm-note-checkout> --json
   ```

4. Zeige dem Menschen Inhalt, Referenzen, Fragen, Vorschläge und Hashbindung.
   Erzeuge die Approval-Datei erst nach seiner ausdrücklichen Bestätigung.
5. Speichere genau den freigegebenen Plan mit `notes apply`,
   `--approval-file` und `--approve-state-write`.
6. Prüfe mit `notes history --note-id <id>`, dass eine neue Revision ergänzt
   und keine frühere Fassung verändert wurde.

## Verbindliche Grenzen

- Der Mensch ist Autor; der Guide ist kein Mitautor.
- Vorschläge bleiben getrennt von `human_content` und `proposed_content`.
- Remote-LLMs, Netzwerk und externe Synchronisierung sind in Phase 28 aus.
- `create`, `edit` und `revert` ergänzen immer eine Version. Es gibt keinen
  Überschreib- oder Löschbefehl.
- Plan-ID, Planhash, Aktion, Inhaltshash und Store-Revision müssen exakt
  passen; Wiederholungen und veraltete Pläne blockieren.
- Dokument- und Kalenderreferenzen werden nicht automatisch erzeugt oder als
  vollständig behauptet.
- Familienprofile ordnen Notizen. Die Sicherheitsgrenze bleibt das
  Betriebssystemkonto.
- Speichere keine Secrets in Anfrage, Approval, Beispielen oder Repository.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
