# Synthetischer Rechtsänderungsfall

Diese Dateien demonstrieren ausschließlich den lokalen Vergleichsvertrag.
Sie enthalten kein echtes Gesetz und sind durch `fixture_only=true`,
`authoritative=false` und die reservierte Domain `example.invalid` eindeutig
vom Produktivpfad getrennt.

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

`--allow-test-fixture` ist ausschließlich für diesen synthetischen Usecase
vorgesehen. Produktivstände müssen auf einer zugelassenen amtlichen HTTPS-
Domain liegen und `authoritative=true` ausweisen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
