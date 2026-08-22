# Reused components

**English** | [Deutsch](./README.de.md)

This section contains no copied source code. Runtime providers refer to a separately versioned repository and their canonical manifest at `manifests/components/`. Pure design references without runtime binding instead name checkout, revision, license, test bench, and the deliberately not adopted properties directly on their subpage.

Phase 27 documents UpToday, Routinika, and the Google Calendar skill at [`calendar-providers/`](calendar-providers/) without copied provider code.

Phase 28 documents the unchanged local note storage at [`llm-note/`](llm-note/). FolderHome adds leadership and approval as a new capsule and writes exclusively via the public provider API.

Phase 29 documents the unchanged local evidence provider at [`steuer-assistent/`](steuer-assistent/). FolderHome adds document, profile, approval, and hash bindings, without adding tax advice or a portal path.

Phase 30 documents BACH's weather, newspaper, and daily agent inventory at [`bach-daily-briefing/`](bach-daily-briefing/) solely as a design reference. The externally modified monolith is not loaded and its source code is not copied.

Phase 31 documents the existing `law-checker` at [`law-checker/`](law-checker/) initially as a method reference. Phase 34 adds a separate clean checkout as a pinned read‑only registry and source provider. The earlier externally modified checkout remains untouched; an automatic legal‑review API is not claimed.

Phase 33 documents, at [`benefit-routing/`](benefit-routing/), three official, manually opened benefit‑finder handoffs. No portal code is copied, no profile is transferred, and the pedagogical `foerderplaner` is not misused as a social benefit module.
