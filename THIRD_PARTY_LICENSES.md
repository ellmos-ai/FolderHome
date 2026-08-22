# THIRD_PARTY_LICENSES — Registry of reused components

**English** | [Deutsch](./THIRD_PARTY_LICENSES.de.md)

**Version:** 0.15  
**Updated:** 2026-08-22  
**Reason:** Dependency boundary of the local app and its acceptance documented  
**Purpose:** Documents external or pre‑existing components with exact revision.

| Component | Repository | Revision | License | Integration |
|---|---|---|---|---|
| file-collect-sort-action | `https://github.com/ellmos-ai/file-collect-sort-action.git` | `8ebac2739c11c6a041abdd7b30131cef648b4753` | MIT | Pinned plugin manifest |
| HungryCall | `https://github.com/ellmos-ai/hungrycall.git` | `d2138476d23234cf1d23ec9609f124c58455b8e7` | MIT | Pinned plugin manifest |
| Ringedingeding | `https://github.com/ellmos-ai/ringedingeding.git` | `01b269d1f76ac83ed64ff14eb0cc7bd4ccc9b5bf` | MIT | Pinned plugin manifest |
| doc-services | Local checkout without remote | `037a432bbec94ac6db5dfa53941745fda7c2f38a` | MIT | Pinned plugin manifest and extraction bridge |
| KnowledgeDigest | `https://github.com/file-bricks/knowledgedigest.git` | `7040c66aa9326975ad81c156acf0d49fd5dca60f` | MIT | Pinned plugin manifest and index/search bridge |
| report-forge | `https://github.com/ellmos-ai/report-forge.git` | `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | MIT | Inventoried; runtime version to be cleaned up before bridge integration |
| ai-media-editor | `https://github.com/ellmos-ai/ai-media-editor.git` | `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | MIT | Revision‑bound media handoff; no media execution in artifact plan |
| MailProcessor | `https://github.com/doc-bricks/MailProcessor.git` | `704575901b8b526dcd1436a86d6f42818b4079cd` | MIT | Suite launcher; no FolderHome runtime connector |
| UniversalDocsGrabber | `https://github.com/doc-bricks/UniversalDocsGrabber.git` | `0ccd03455b63acbca6e71cc48ba464f208a759cd` | MIT | Intended IMAP document provider; local checkout currently blocked |
| UniversalMailCleaner | `https://github.com/doc-bricks/UniversalMailCleaner.git` | `85de4dd2e84c499152b09d4e5688332ff3bb2ed4` | MIT | Separate mailbox cleaning; not part of the read‑only ingest |
| UniversalInvoiceMail | `https://github.com/doc-bricks/UniversalInvoiceMail.git` | `c58be4cdf92d8265694037cf1dbf7f14c84b39f9` | MIT | Specialized invoice reference; no runtime import |
| PDFtoPDFocr | `https://github.com/doc-bricks/PDFtoPDFocr.git` | `c89ae00982d7597b663c99527298363b9e2fce58` | MIT | Inventoried; GUI monolith and shifting merge function not directly integrated |
| MarkItDown | `https://github.com/microsoft/markitdown.git` | `fd239d5d2be43d9b68329730206b9312c7d5a388` | MIT | Indirect via doc-services; no own FolderHome bridge |
| pypdf | PyPI package `pypdf` | `>=4.0`, checked with `6.16.1` | BSD-3-Clause | Optional PDF assembly in `document_transform` |
| Pillow | PyPI package `Pillow` | `>=10.0`, checked with `12.3.0` | MIT-CMU | Optional local image‑to‑PDF rasterization |
| ReportLab | PyPI package `reportlab` | `>=4.0`, checked with `5.0.1` | BSD | Optional deterministic text‑to‑PDF re‑creation |
| llm-note | `https://github.com/doc-bricks/llm-note.git` | `b5fe59fc155ded9603566aa0fb920a53181a2426` | MIT | Pinned local note store via public write API and schema‑fixed read‑only adapter |
| steuer-assistent | `https://github.com/ellmos-ai/steuer-assistent.git` | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` | MIT | Pinned local receipt store and private ZIP tax worksheet via public provider API |
| BACH Wetter/Newspaper/Daily Agent | `https://github.com/ellmos-ai/bach.git` | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` | MIT | Design reference only; externally modified monolith is not loaded as FolderHome runtime and no code is copied |
| law-checker | `https://github.com/ellmos-ai/law-checker.git` | `06fb8d57ff90638cc50f5e33c50dbba455ac6f1b` | MIT | Unchanged read‑only registry/source provider; no code copied, no agent workflow imported |
| UpToday | Local checkout without remote | `7582ca87e17e458bb99a7379d2c54003c15415a4` | MIT | Design reference for inventory/medication and tested ICS file handoff; no runtime import |
| Routinika | Local OneDrive inventory | `portable_bundle.py` SHA-256 `3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2` | to be checked before distribution | Hash‑bound bundle design reference; no live connector and no copied code |
| Google Calendar Skill 1.2.5 | Local plugin package | `google-calendar-skill@1.2.5` | package‑bound asset | Agentic handoff; no copied code and no live call in phase 27 |
| gesundheit-Skill 2.0.0 | `https://github.com/ellmos-ai/skills.git` | `0317f32310eed11d21f603cb6f22a689485af226` | MIT | Design reference for provided health information and organizational boundaries |
| docs-analysis 1.0.0 | Local skill extracted from BACH | Status 2026-03-15 | MIT / project‑internal asset | Requirement and code‑difference method for phase 22; no runtime import |
| project-docs | Local template `OneDrive/.TOPICS/.AI/_templates/project-docs` | Status 2026-08-21 | Project‑internal asset | Documentation base skeleton |
| Strands Agents SDK | `https://github.com/strands-agents/sdk-python.git` | PyPI `strands-agents==1.53.0` | Apache-2.0 | Mandatory agent loop; fixture by default without network, Bedrock only after gate |
| tzdata | PyPI package `tzdata` | `==2026.3` on Windows | Apache-2.0 | IANA time‑zone data for reproducible calendar, medication, and scheduler contracts on Windows |

The table is a registry, not a substitute for the full license texts of the respective components. If sources are later vendored or included as submodules, their original license files must be carried along.

The local app from phase 35 itself continues to use only the Python standard library and the new FolderHome code. Phase 36 adds the Apache‑2.0‑licensed Strands Agents SDK as an exactly pinned project dependency. The fixture model adapter requires no cloud; the optional Bedrock provider remains behind an explicit network gate. Windows additionally installs the exactly pinned `tzdata` package, because the Python standard installation there does not guarantee a system‑wide IANA database. Microsoft Edge and Playwright were used solely for local visual acceptance; they are neither shipped nor imported at runtime by FolderHome.

---
