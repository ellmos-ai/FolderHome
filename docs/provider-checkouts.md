# Optional provider checkouts

**English** | [Deutsch](./provider-checkouts.de.md)

The synthetic competition demos work without provider repositories. The
component-manifest directory has nine entries. Seven declare public GitHub
sources; their capability IDs and current manifest revisions are listed below.
A checkout used for one of these components must match the revision in its TOML
file and have a clean worktree.

The optional `doc-services` bridge provides local document extraction. An
explicit `--doc-services-root` value takes precedence over its configured
default.

| Manifest entry | Declared capability IDs | Public source | Revision in manifest |
|---|---|---|---|
| `ellmos-scheduler` | `scheduler.jobs.register`, `scheduler.jobs.consume` | [ellmos-ai/ellmos-scheduler](https://github.com/ellmos-ai/ellmos-scheduler) | `d5103b9a733701f6db80dd08cfae408bf0af8ac5` |
| `KnowledgeDigest` | `documents.index`, `documents.search` | [file-bricks/KnowledgeDigest](https://github.com/file-bricks/knowledgedigest) | `7040c66aa9326975ad81c156acf0d49fd5dca60f` |
| `llm-note` | `notes.read`, `notes.write` | [doc-bricks/llm-note](https://github.com/doc-bricks/llm-note) | `b5fe59fc155ded9603566aa0fb920a53181a2426` |
| `law-checker` | `legal.registry.read`, `legal.orientation.handoff` | [ellmos-ai/rechtsabteilung](https://github.com/ellmos-ai/rechtsabteilung) | `a5b0cd51bc3666962f2fae8017c855dea0a712a2` |
| `hungrycall` | `calls.hungry_cascade` | [ellmos-ai/hungrycall](https://github.com/ellmos-ai/hungrycall) | `9ae58c4acb31070dcf2e3fc468cff1c80c9a7e9c` |
| `ringedingeding` | `calls.ring_cascade` | [ellmos-ai/ringedingeding](https://github.com/ellmos-ai/ringedingeding) | `94ae1f1e028be5aaf100baafadc18b64ff0940a2` |
| `steuer-assistent` | `tax.receipts.write`, `tax.workpaper.export` | [ellmos-ai/steuer-assistent](https://github.com/ellmos-ai/steuer-assistent) | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` |

The other two manifest entries, `doc-services` and
`file-collect-sort-action`, do not have publicly accessible checkout sources.
This public guide does not list their source locations or private checkout
details. For an authorized local source, use the access instructions supplied
for that source.
The `law-checker` manifest source currently redirects to the linked
`rechtsabteilung` repository; keep using the revision declared in the manifest.

## Isolate a public pinned version

Keep an existing working copy unchanged and use a separate destination inside
FolderHome. This example checks out the manifest-pinned public scheduler source.
Run it from the FolderHome repository root in PowerShell:

```powershell
$providerSource = 'https://github.com/ellmos-ai/ellmos-scheduler.git'
git clone --no-hardlinks --no-checkout $providerSource .providers/ellmos-scheduler
git -C .providers/ellmos-scheduler switch --detach d5103b9a733701f6db80dd08cfae408bf0af8ac5
git -C .providers/ellmos-scheduler status --porcelain
```

Stop if any command fails. The final command must produce no output. Do not
reuse an existing destination or reset somebody else's working copy.

FolderHome prefers `.providers/<provider-id>` when that checkout exists;
otherwise it uses the configured sibling-directory default. The configured
roots are `doc-services`, `file-collect-sort-action`, `law-checker`,
`ellmos-scheduler`, `KnowledgeDigest`, `hungrycall`, `ringedingeding`,
`llm-note`, `steuer-assistent`, `ai-media-editor`, `UniversalDocsGrabber`, and
`UpToday`. Root selection does not make every path a component-manifest entry.

## Feature-specific provider roots

Three additional roots are described outside `manifests/components/`. Their
revision descriptors are separate from the nine component TOMLs:

| Provider root | Revision descriptor | Feature scope |
|---|---|---|
| `ai-media-editor` | `AI_MEDIA_EDITOR_REVISION` in [`src/folderhome/cli.py`](../src/folderhome/cli.py), currently `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | [Phase 25 plan](./phase25-artifact-studio-plan.md) |
| `UniversalDocsGrabber` | `UNIVERSAL_DOCS_GRABBER_REVISION` in [`src/folderhome/cli.py`](../src/folderhome/cli.py), currently `0ccd03455b63acbca6e71cc48ba464f208a759cd` | [Phase 26 plan](./phase26-mail-connector-plan.md) |
| `UpToday` | `UPTODAY_REVISION` in [`src/folderhome/cli.py`](../src/folderhome/cli.py), currently `7582ca87e17e458bb99a7379d2c54003c15415a4` | [Phase 17 plan](./phase17-calendar-reuse-and-plan.md) |

FolderHome has an optional mail-ingest provider path for UniversalDocsGrabber.
The CLI inventory marks it as a runtime connector and checks its configured
checkout revision. This source-level description is not a live mailbox test.
The UpToday path describes an ICS handoff; it does not claim that FolderHome
imports directly into UpToday's database.

## Local dependency storage

`.providers/` is Git-ignored. It is local dependency storage, **not permission
to redistribute private source**. A `local://` manifest source is not a public
download URL. Do not include private checkout contents in releases or competition
uploads.

## Verification boundaries

```powershell
.venv\Scripts\python.exe -m pytest tests/test_doc_services_bridge.py -q
```

Two passing bridge tests exercise local extraction and the privacy gate for the
configured checkout. Provider-dependent tests need their matching source
checkouts; some are explicitly skipped when a provider is absent. Present but
wrong or dirty manifest-backed providers fail their checkout checks. A skipped
integration test is not evidence that a real-data feature works.
