# Synthetic Legal Change Case

**English** | [Deutsch](./README.de.md)

These files demonstrate exclusively the local comparison contract.  
They contain no real law and are clearly separated from the production path by `fixture_only=true`, `authoritative=false` and the reserved domain `example.invalid`.

```powershell
$env:PYTHONPATH = "src"
python -m folderhome legal compare `
  --before-file examples\legal\before.json `
  --after-file examples\legal\after.json `
  --interests-file examples\legal\Lukas-interests.json `
  --as-of 2026-08-22T08:00:00+02:00 `
  --max-source-age-days 7 `
  --approve-sensitive-local-read `
  --allow-test-fixture --json
```


`--allow-test-fixture` is intended solely for this synthetic use case. Production versions must reside on an authorized official HTTPS domain and display `authoritative=true`.

---
