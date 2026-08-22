# Synthetische Mailkonfiguration

Die Beispiele enthalten ausschließlich reservierte `example.invalid`-Adressen
und Secret-Referenzen. Es werden weder Zugangsdaten hinterlegt noch echte
Postfächer angesprochen.

Der normale Plan prüft den revisionsgenauen UniversalDocsGrabber-Checkout und
bleibt bei fehlendem, abweichendem oder verändertem Checkout blockiert:

```powershell
python -m folderhome mail ingest-plan `
  --accounts-file examples/mail/accounts.json `
  --request-file examples/mail/ingest-request.json `
  --profiles-dir examples/profiles `
  --approve-sensitive-local-read --json
```

Für die lokale Abnahme kann derselbe Plan mit
`--use-synthetic-provider` ohne Netzwerk freigegeben werden. Auch dieser Plan
ruft noch keinen Provider auf. Postfach-Löschen, Verschieben und Versand sind
keine Ingest-Operationen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
