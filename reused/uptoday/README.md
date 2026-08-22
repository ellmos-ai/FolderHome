# UpToday — declared design reuse

**English** | [Deutsch](./README.de.md)

FolderHome does not copy any UpToday source code and does not load the existing
`InventoryEngine` as a runtime provider.

- local checkout: `C:\_Local_DEV\repos\UpToday`
- verified revision: `7582ca87e17e458bb99a7379d2c54003c15415a4`
- commit time: `2026-08-18T23:44:13+02:00`
- License: MIT
- state at inspection: clean
- focused inspection: `tests/test_flutter_inventory_contract.py`, 4 tests green

The already extracted domain terms for item, area, location, unit, stock, minimum stock, and purchase derivation, as well as the separation of medication, dosage schedule, and confirmed dose, are reused. New and encapsulated features that arise in FolderHome are integer precision, document evidence, append‑only events, revision, approval, and explicit timestamps.

The scope and reasons for adaptation are documented in
[`../../docs/phase20-household-inventory-reuse-and-plan.md`](../../docs/phase20-household-inventory-reuse-and-plan.md).
The medication boundary is additionally documented in
[`../../docs/phase21-medication-intake-reuse-and-plan.md`](../../docs/phase21-medication-intake-reuse-and-plan.md).
