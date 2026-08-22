# Bridges

**English** | [Deutsch](./README.de.md)

This section documents the new FolderHome connection code. The installable adapters are located under `src/folderhome/bridges/` and translate stable FolderHome contracts into the APIs of separately versioned components. Local write paths exist only behind the documented plan, approval, and side-effect gates. Network, telephone, and external transmission remain blocked or synthetic in the competitive acceptance.

| Bridge | Target component | Status |
|---|---|---|
| `fcsa_plugin/` | file-collect-sort-action | Pinned dry-run bridge implemented; live remains blocked |
| `hungrycall_plugin/` | HungryCall | Pinned dry-run probe present, live adapter missing |
| `ringedingeding_plugin/` | Ringedingeding | Pinned fixture probe present, live adapter missing |
| `src/folderhome/bridges/doc_services.py` | doc-services | Pinned local extraction |
| `src/folderhome/bridges/knowledge_digest.py` | KnowledgeDigest | Pinned local search and indexing |
| `src/folderhome/bridges/llm_note.py` | llm-note | Read-only history and approved append-only writes |
| `src/folderhome/bridges/tax_assistant.py` | steuer-assistent | Read-only planning, approved receipts and private ZIP tax worksheet |
| `src/folderhome/bridges/law_checker.py` | law-checker | Pinned package, module and registry check without legal agent call |
