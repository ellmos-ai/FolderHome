# THIRD_PARTY_LICENSES — Registry of reused components

**English** | [Deutsch](./THIRD_PARTY_LICENSES.de.md)

**Version:** 0.21  
**Updated:** 2026-09-09  
**Reason:** Installed dependency versions and bundled-license boundaries verified  
**Purpose:** Documents external or pre‑existing components with exact revision.

| Component | Repository | Revision | License | Integration |
|---|---|---|---|---|
| ellmos-scheduler 0.3.1 | `https://github.com/ellmos-ai/ellmos-scheduler.git` | `d5103b9a733701f6db80dd08cfae408bf0af8ac5` | MIT | Unmodified optional provider; gated app registration, single-job consumer and read-only job/history schema seam; no copied code or automatic service start |
| file-collect-sort-action | `https://github.com/ellmos-ai/file-collect-sort-action.git` | `8ebac2739c11c6a041abdd7b30131cef648b4753` | MIT | Pinned plugin manifest |
| HungryCall | `https://github.com/ellmos-ai/hungrycall.git` | `9ae58c4acb31070dcf2e3fc468cff1c80c9a7e9c` | MIT | Pinned plugin manifest |
| Ringedingeding | `https://github.com/ellmos-ai/ringedingeding.git` | `94ae1f1e028be5aaf100baafadc18b64ff0940a2` | MIT | Pinned plugin manifest |
| doc-services | Local checkout without remote | `e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2` | MIT | Pinned plugin manifest and extraction bridge |
| KnowledgeDigest | `https://github.com/file-bricks/knowledgedigest.git` | `7040c66aa9326975ad81c156acf0d49fd5dca60f` | MIT | Pinned plugin manifest and index/search bridge |
| report-forge | `https://github.com/ellmos-ai/report-forge.git` | `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | MIT | Pinned local correspondence rendering; distribution version 1.1.4 and runtime version 1.1.0 checked separately; no source copied |
| ai-media-editor | `https://github.com/ellmos-ai/ai-media-editor.git` | `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | MIT | Revision‑bound media handoff; no media execution in artifact plan |
| MailProcessor | `https://github.com/doc-bricks/MailProcessor.git` | `704575901b8b526dcd1436a86d6f42818b4079cd` | MIT | Suite launcher; no FolderHome runtime connector |
| UniversalDocsGrabber | `https://github.com/doc-bricks/UniversalDocsGrabber.git` | `0ccd03455b63acbca6e71cc48ba464f208a759cd` | MIT | Intended IMAP document provider; local checkout currently blocked |
| UniversalMailCleaner | `https://github.com/doc-bricks/UniversalMailCleaner.git` | `85de4dd2e84c499152b09d4e5688332ff3bb2ed4` | MIT | Separate mailbox cleaning; not part of the read‑only ingest |
| UniversalInvoiceMail | `https://github.com/doc-bricks/UniversalInvoiceMail.git` | `c58be4cdf92d8265694037cf1dbf7f14c84b39f9` | MIT | Specialized invoice reference; no runtime import |
| PDFtoPDFocr | `https://github.com/doc-bricks/PDFtoPDFocr.git` | `c89ae00982d7597b663c99527298363b9e2fce58` | MIT | Inventoried; GUI monolith and shifting merge function not directly integrated |
| MarkItDown | `https://github.com/microsoft/markitdown.git` | `fd239d5d2be43d9b68329730206b9312c7d5a388` | MIT | Indirect via doc-services; no own FolderHome bridge |
| pypdf | PyPI package `pypdf` | `>=4.0`, checked with `6.18.0` | BSD-3-Clause | Optional PDF assembly in `document_transform` |
| Pillow | PyPI package `Pillow` | `>=10.0`, checked with `12.3.0` | MIT-CMU | Optional local image‑to‑PDF rasterization |
| ReportLab | PyPI package `reportlab` | `>=4.0`, checked with `5.0.1` | BSD | Optional deterministic text‑to‑PDF re‑creation |
| resvg-py | `https://github.com/baseplate-admin/resvg-py` | `resvg-py==0.5.0` | MIT | Development-only local SVG-to-PNG exporter; package source/binary and system fonts are not vendored |
| llm-note | `https://github.com/doc-bricks/llm-note.git` | `b5fe59fc155ded9603566aa0fb920a53181a2426` | MIT | Pinned local note store via public write API and schema‑fixed read‑only adapter |
| steuer-assistent | `https://github.com/ellmos-ai/steuer-assistent.git` | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` | MIT | Pinned local receipt store and private ZIP tax worksheet via public provider API |
| BACH Wetter/Newspaper/Daily Agent | `https://github.com/ellmos-ai/bach.git` | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` | MIT | Design reference only; externally modified monolith is not loaded as FolderHome runtime and no code is copied |
| law-checker | `https://github.com/ellmos-ai/law-checker.git` | `a5b0cd51bc3666962f2fae8017c855dea0a712a2` | MIT | Unchanged read‑only registry/source provider; no code copied, no agent workflow imported |
| UpToday | Local checkout without remote | `7582ca87e17e458bb99a7379d2c54003c15415a4` | MIT | Design reference for inventory/medication and tested ICS file handoff; no runtime import |
| Routinika | Local OneDrive inventory | `portable_bundle.py` SHA-256 `3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2` | to be checked before distribution | Hash‑bound bundle design reference; no live connector and no copied code |
| Google Calendar Skill 1.2.5 | Local plugin package | `google-calendar-skill@1.2.5` | package‑bound asset | Agentic handoff; no copied code and no live call in phase 27 |
| google-auth | `https://github.com/googleapis/google-cloud-python/tree/main/packages/google-auth` | `>=2.38,<3`, checked with `2.57.1` | Apache-2.0 | Optional `folderhome[calendar]`; loads an existing private OAuth grant and performs gated token refresh; native Calendar-v3 HTTPS transport is FolderHome code, not copied skill code |
| gesundheit-Skill 2.0.0 | `https://github.com/ellmos-ai/skills.git` | `0317f32310eed11d21f603cb6f22a689485af226` | MIT | Design reference for provided health information and organizational boundaries |
| docs-analysis 1.0.0 | Local skill extracted from BACH | Status 2026-03-15 | MIT / project‑internal asset | Requirement and code‑difference method for phase 22; no runtime import |
| project-docs | Local internal project-docs template | Status 2026-08-21 | Project‑internal asset | Documentation base skeleton |
| ellmos mail-connector | Local module `.MODULES/.CONNECTORS/mail-connector` | Design reference, deliberately not pinned | MIT | Connection lifecycle, modified UTF-7 mailbox names and two-way credential lookup reused as patterns; no code imported and no revision pinned, so no checkout can drift |
| Strands Agents SDK | `https://github.com/strands-agents/sdk-python.git` | PyPI `strands-agents==1.53.0` | Apache-2.0 | Mandatory agent loop; fixture by default without network, Bedrock only after gate |
| MCP Python SDK | PyPI package `mcp` | Direct requirement `>=1.29,<2`, checked with `1.30.0` | MIT | stdio server for `folderhome mcp serve`; also required by Strands |
| ollama | PyPI package `ollama` | `>=0.4`, checked with `0.6.2` | MIT | Optional extra `folderhome[ollama]`; HTTP client for the local Ollama provider, loaded only for `--model-provider ollama` |
| anthropic | PyPI package `anthropic` | `>=0.40`, checked with `1.4.0` | MIT | Optional extra `folderhome[anthropic]`; SDK for the hosted Anthropic provider, loaded only for `--model-provider anthropic` |
| openai | PyPI package `openai` | `>=1.60`, checked with `3.10.0` | Apache-2.0 | Optional extra `folderhome[openai]`; SDK for the hosted OpenAI provider and OpenAI-compatible endpoints, loaded only for `--model-provider openai` |
| tzdata | PyPI package `tzdata` | `==2026.3` on Windows | Apache-2.0 | IANA time‑zone data for reproducible calendar, medication, and scheduler contracts on Windows |
| actions/checkout | `https://github.com/actions/checkout` | `11d5960a326750d5838078e36cf38b85af677262` (`v4`) | MIT | SHA-pinned Pages build action |
| actions/configure-pages | `https://github.com/actions/configure-pages` | `983d7736d9b0ae728b81ab479565c72886d7745b` (`v5`) | MIT | SHA-pinned Pages configuration action |
| actions/upload-pages-artifact | `https://github.com/actions/upload-pages-artifact` | `56afc609e74202658d3ffba0e8f6dda462b719fa` (`v3`) | MIT | SHA-pinned bounded artifact upload action |
| actions/deploy-pages | `https://github.com/actions/deploy-pages` | `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e` (`v4`) | MIT | SHA-pinned Pages deployment action |
| Python Docker Official Image | `https://hub.docker.com/_/python` | `python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7` | Python PSF and included Debian package licenses | Digest-pinned ARM64 build and runtime base; not vendored |

## Installed dependencies and distribution boundaries

The table is a registry, not a substitute for the full license texts of the
respective components. Package-level license labels do not describe every
bundled font, native library or vendored module.

The Windows/Python 3.12.10 acceptance installation was inspected on 2026-09-09
with the `calendar`, `transform`, `ollama`, `anthropic` and `openai` extras.
Following active dependency markers and requested transitive extras identified
**64 external runtime distributions**, plus FolderHome. All had readable
license/notice files. This excludes dev-only tools, separate provider checkouts,
the Python/OS distribution and a complete native-library inventory. It is an
installed-version snapshot, not a dependency lock or legal clearance.

| Installed component | Additional license material to preserve when bundling |
|---|---|
| certifi 2026.7.22 | MPL-2.0 certificate-bundle notice; review covered-source obligations for the actual redistributed form |
| ReportLab 5.0.1 | BSD library license **plus** `DarkGarden-copying.txt` / `DarkGarden-copying-gpl.txt` (GPL-2.0-or-later font with a document-embedding exception) and `bitstream-vera-license.txt` |
| Pillow 12.3.0 | Its combined `LICENSE` includes native-library notices beyond MIT-CMU, including FreeType; preserve the complete file |
| pywin32 312 | PSF package metadata plus component-specific notices, including Scintilla and MAPIStubLibrary |
| anthropic 1.4.0 / openai 3.10.0 | Separate notices under `_vendor/httpx_aiohttp/`, in addition to the SDK license |
| Strands / boto3 / botocore / s3transfer | Supplied `LICENSE` and `NOTICE` files, not just the registry label |

The checked FolderHome wheel contains only `folderhome/` and its own
`folderhome-0.3.0.dist-info/`; dependency packages and font files are not embedded.
Pip installs dependencies separately with their own license material. The local
text-to-PDF adapter selects Helvetica/Helvetica-Bold, not DarkGarden. Neither
fact clears redistribution of an entire environment: before shipping a frozen
app, dependency bundle or container, inventory that exact artifact, retain its
original license/notice material and resolve any corresponding-source duties.
See the [MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) for the distinction
between using MPL software and distributing covered files.

### Brand graphics and system fonts

Brand PNGs use locally rendered Windows system fonts; font binaries are not
shipped. SVG/CSS font-family names are references, not embedded webfonts.
Microsoft's [font FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
permits text graphics such as logos and banners under its stated conditions;
that does **not** grant permission to redistribute font files or bitmap fonts.
This assessment does not cover a future embedded-font PDF or installer.

## Runtime scope

Current mandatory dependencies are `strands-agents`, `mcp` and, on Windows,
`tzdata`; the exact constraints and optional extras are in
[`pyproject.toml`](./pyproject.toml). Connected local providers may require
separate pinned checkouts. The earlier standard-library-only app description
applied to phase 35, not to the complete current installation.

The fixture model adapter requires no cloud. External model providers remain
behind explicit network and data-disclosure gates; calendar OAuth is optional
and separately gated. Microsoft Edge and Playwright were used for earlier local
visual checks; neither is shipped or imported by FolderHome at runtime. Those
earlier checks do not establish browser acceptance of later features.

---
