# Kalenderconnector-Beispiele

`calendar-config.json` demonstriert den bestehenden UpToday-ICS-Handoff aus Phase 17.
`calendar-config-google.json`, `connector-accounts.json` und
`connector-request-google.json` demonstrieren den providerneutralen Connectorplan aus
Phase 27. Das Google-Konto enthält nur eine Connector-Referenz, keine Zugangsdaten.

`calendar connector-plan` bleibt nebenwirkungsfrei. Für eine lokale Ende-zu-Ende-Abnahme
kann derselbe Plan mit `--use-synthetic-provider` vorbereitet und mit
`calendar connector-simulate` sowie `--approve-synthetic-calendar` ausschließlich gegen
den No-Network-Fixture-Provider ausgeführt werden. Ein echter Google-Kalender wird dabei
nicht verändert.
