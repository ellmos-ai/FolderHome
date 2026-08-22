# llm-note — unchanged reusable note storage

**English** | [Deutsch](./README.de.md)

FolderHome loads the standalone provider only from a clean checkout at commit `b5fe59fc155ded9603566aa0fb920a53181a2426` and package version `1.0.3`.  
The canonical repository is `https://github.com/doc-bricks/llm-note.git`, the license is MIT.

The local SQLite storage and the public `NoteStore.write()` API are reused. FolderHome does not copy or modify any provider source code. Guided questions, human approval, profile context, explicit references, and append‑only revisions are new FolderHome code.

Reading is performed via a schema‑ and revision‑bound read‑only adapter, because the public provider class also initializes the schema in a missing store when instantiated. Writing is allowed only with exact plan, content, and state approval. Neither the provider nor the Phase‑28 bridge use the network or any external synchronization.

---
