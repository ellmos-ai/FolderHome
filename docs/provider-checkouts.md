# Optional provider checkouts

**English** | [Deutsch](./provider-checkouts.de.md)

The synthetic competition demos work without private provider repositories.
Real document extraction uses the optional `doc-services` bridge. Its manifest
pins an exact commit; both the revision and a clean worktree are mandatory.
A newer checkout is not interchangeable with that pin.

## Isolate the pinned version

If you already have authorized access to the provider source, keep its working
copy unchanged and create a separate checkout inside FolderHome. From the
FolderHome repository root, in PowerShell:

```powershell
$providerSource = 'C:\path\to\your\doc-services'
git clone --no-hardlinks --no-checkout $providerSource .providers/doc-services
git -C .providers/doc-services switch --detach e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2
git -C .providers/doc-services status --porcelain
```

Stop if any command fails. The final command must produce no output. Do not
reuse an existing destination or reset somebody else's working copy.

FolderHome automatically prefers `.providers/doc-services` when present;
otherwise it keeps the legacy sibling-directory default. The same selection
applies to `.providers/file-collect-sort-action` and `.providers/law-checker`.
Their public sources and exact pins are recorded in
[`manifests/components/`](../manifests/components/); use the same clone/detach
steps with the corresponding name and revision. An invalid isolated
checkout fails the normal provider gate; there is no silent fallback. An
explicit `--doc-services-root` still takes precedence.

`.providers/` is Git-ignored. It is local dependency storage, **not permission
to redistribute private source**. A `local://` manifest is not a public download
URL. Do not include the folder in releases or competition uploads.

## Verification boundaries

```powershell
.venv\Scripts\python.exe -m pytest tests/test_doc_services_bridge.py -q
```

Two passing bridge tests prove real local extraction and the privacy gate for
that checkout. Provider-dependent tests need their matching source checkouts;
some are explicitly skipped when a provider is absent. Present but wrong/dirty
providers fail. A skipped integration test is not proof that the corresponding
real-data feature works.
