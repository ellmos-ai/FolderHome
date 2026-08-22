# UpToday — deklarierte Design-Wiederverwendung

[English](./README.md) | **Deutsch**

FolderHome kopiert keinen UpToday-Quellcode und lädt den bestehenden
`InventoryEngine` nicht als Runtime-Provider.

- lokaler Checkout: `C:\_Local_DEV\repos\UpToday`
- geprüfte Revision: `7582ca87e17e458bb99a7379d2c54003c15415a4`
- Commit-Zeit: `2026-08-18T23:44:13+02:00`
- Lizenz: MIT
- Zustand bei Prüfung: sauber
- fokussierte Prüfung: `tests/test_flutter_inventory_contract.py`, 4 Tests grün

Wiederverwendet werden die bereits extrahierten Fachbegriffe für Artikel,
Bereich, Ort, Einheit, Bestand, Mindestbestand und Einkaufsableitung sowie die
Trennung von Medikament, Einnahmezeitplan und bestätigter Dosis. Neu und
gekapselt entstehen in FolderHome Ganzzahlexaktheit, Dokumentevidenz,
Append-only-Ereignisse, Revision, Approval und explizite Zeitpunkte.

Die Abgrenzung und Anpassungsgründe stehen in
[`../../docs/phase20-household-inventory-reuse-and-plan.md`](../../docs/phase20-household-inventory-reuse-and-plan.de.md).
Die Medikamentengrenze steht zusätzlich in
[`../../docs/phase21-medication-intake-reuse-and-plan.md`](../../docs/phase21-medication-intake-reuse-and-plan.de.md).
