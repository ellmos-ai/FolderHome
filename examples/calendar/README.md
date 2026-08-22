# Calendar connector examples

**English** | [Deutsch](./README.de.md)

`calendar-config.json` demonstrates the existing UpToday-ICS-Handoff from Phase 17.  
`calendar-config-google.json`, `connector-accounts.json` and  
`connector-request-google.json` demonstrate the provider‑neutral connector plan from  
Phase 27. The Google account contains only a connector reference, no credentials.

`calendar connector-plan` remains side‑effect free. For a local end‑to‑end acceptance  
the same plan can be prepared with `--use-synthetic-provider` and executed with  
`calendar connector-simulate` as well as `--approve-synthetic-calendar` exclusively against  
the No‑Network‑Fixture provider. A real Google calendar will not be modified in the process.
