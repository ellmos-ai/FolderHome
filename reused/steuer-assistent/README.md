# steuer-assistent — unchanged reusable receipt provider

**English** | [Deutsch](./README.de.md)

FolderHome loads the standalone provider exclusively from a clean checkout at commit `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` and package version `0.2.3`. The canonical repository is `https://github.com/ellmos-ai/steuer-assistent.git`, the license is MIT.

`SteuerAssistent.add_beleg()` and `SteuerAssistent.export_arbeitsunterlage()` are reused. The provider source code is neither copied nor modified. Document, finance, profile, approval, and hash bindings are new FolderHome code.

The provider creates a private tax worksheet for expense receipts classified by the user. It does not check tax deductibility, does not provide advice, and does not offer any ELSTER, ERiC, tax office, or other portal procedure. FolderHome explicitly enforces this boundary also in the plan, CLI, and report.

---
