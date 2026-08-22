# Bridges

Dieser Bereich dokumentiert den neuen FolderHome-Verbindungscode. Die
installierbaren Adapter liegen unter `src/folderhome/bridges/` und übersetzen
stabile FolderHome-Verträge in die APIs separat versionierter Komponenten.
Lokale Schreibpfade existieren ausschließlich hinter den dokumentierten
Plan-, Approval- und Side-Effect-Gates. Netzwerk, Telefon und externe
Übermittlung bleiben in der Wettbewerbsabnahme gesperrt oder synthetisch.

| Bridge | Zielkomponente | Status |
|---|---|---|
| `fcsa_plugin/` | file-collect-sort-action | Gepinnte Dry-Run-Bridge implementiert; Live bleibt gesperrt |
| `hungrycall_plugin/` | HungryCall | Gepinnte Dry-Run-Probe vorhanden, Live-Adapter fehlt |
| `ringedingeding_plugin/` | Ringedingeding | Gepinnte Fixture-Probe vorhanden, Live-Adapter fehlt |
| `src/folderhome/bridges/doc_services.py` | doc-services | Gepinnte lokale Extraktion |
| `src/folderhome/bridges/knowledge_digest.py` | KnowledgeDigest | Gepinnte lokale Suche und Indexierung |
| `src/folderhome/bridges/llm_note.py` | llm-note | Read-only Historie und freigegebene append-only Writes |
| `src/folderhome/bridges/tax_assistant.py` | steuer-assistent | Read-only Planung, freigegebene Belege und private ZIP-Arbeitsunterlage |
| `src/folderhome/bridges/law_checker.py` | law-checker | Gepinnte Paket-, Modul- und Registryprüfung ohne Rechtsagentenaufruf |
