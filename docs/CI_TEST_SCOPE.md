# CI test scope

FolderHome keeps source-dependent tests in the normal pytest collection. Test-level
requires_provider markers identify only cases that need a named pinned checkout;
the registry is in tests/conftest.py. Mixed test modules still run their other
cases. There are no module-wide provider skips or catch-all pytest -k exclusions.

The current 108 Python test modules were classified from the isolated baseline:

| Module class | Count | CI treatment |
| --- | ---: | --- |
| Core-only | 73 | Run in every Core job |
| Core with existing optional skips | 7 | Run; existing import/availability skips keep their case-specific reasons |
| Provider-only | 6 | Run when their declared source pin is available |
| Mixed | 22 | Run all cases; only individually marked source-dependent cases may skip |

Provider requirements are attached to individual collected test functions. A complete
collection fails if a registry entry no longer matches a collected test; explicit test
paths and selection filters remain usable for targeted runs.

CI has six jobs:

| Job group | Jobs | Coverage |
| --- | ---: | --- |
| Core | 4 | Full pytest collection and Ruff on Ubuntu and Windows, Python 3.11 and 3.13 |
| Public source integration | 1 | Full pytest collection on Ubuntu/Python 3.13 with all seven public pins checked out and verified |
| JavaScript fixtures | 1 | Existing Node fixture tests on Ubuntu; no live provider or cloud calls |

The baseline run on 2026-10-12 identified 195 failed/error cases whose traces
required a pinned provider checkout. The function-level registry records those
requirements; parametrized cases inherit the requirement of their test function.
The one separate Windows App Control failure in that local baseline remains in
the suite and has no skip marker.

The public-source integration job requires these exact public manifest entries:

| Plugin ID | Public repository | Required revision |
| --- | --- | --- |
| ellmos-scheduler | ellmos-ai/ellmos-scheduler | d5103b9a733701f6db80dd08cfae408bf0af8ac5 |
| KnowledgeDigest | file-bricks/knowledgedigest | 7040c66aa9326975ad81c156acf0d49fd5dca60f |
| llm-note | doc-bricks/llm-note | b5fe59fc155ded9603566aa0fb920a53181a2426 |
| steuer-assistent | ellmos-ai/steuer-assistent | 5d39aeec98bf0a5734bf07dc35a58aa9e1331309 |
| law-checker | ellmos-ai/law-checker | a5b0cd51bc3666962f2fae8017c855dea0a712a2 |
| hungrycall | ellmos-ai/hungrycall | 9ae58c4acb31070dcf2e3fc468cff1c80c9a7e9c |
| ringedingeding | ellmos-ai/ringedingeding | 94ae1f1e028be5aaf100baafadc18b64ff0940a2 |

The Core and public-source jobs keep `TEMP`, `TMPDIR`, and pytest's `--basetemp`
under the short synthetic `HOME`/`USERPROFILE`. Setup tests intentionally reject
data folders outside the configured user home, so placing pytest's temporary
folders beside the synthetic home would invalidate otherwise local test fixtures.

The integration job fails if a public checkout is missing, dirty, has the wrong
origin, or is not at the required revision. The two non-public source IDs,
doc-services and file-collect-sort-action, are not fetched by public CI. Only
cases that explicitly require those sources remain skipped there, with the
missing plugin ID in the reason. A local full-pin run uses the two private
sources without exporting them to CI or package artifacts.

Existing optional SDK skips are unchanged. For example, tests that use optional
Strands model adapters continue to skip only when the corresponding Ollama,
Anthropic, or OpenAI adapter package is unavailable. The CI install includes the
dev and transform extras, so the existing pypdf and Pillow cases run.

The Ubuntu/Python 3.13 Core job also builds the real wheel and source archive,
checks that coordination/private provider files are absent, installs the wheel,
and runs the installed CLI manifest-validation and synthetic-run smokes outside
the checkout. The Node job runs the existing tests/js fixture suite directly
with node --test; it does not install npm packages or contact remote services.
