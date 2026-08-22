# steuer-assistent — unverändert wiederverwendeter Belegprovider

[English](./README.md) | **Deutsch**

FolderHome lädt den eigenständigen Provider ausschließlich aus einem sauberen
Checkout auf Commit `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` und
Paketversion `0.2.3`. Kanonisches Repository ist
`https://github.com/ellmos-ai/steuer-assistent.git`, die Lizenz ist MIT.

Wiederverwendet werden `SteuerAssistent.add_beleg()` und
`SteuerAssistent.export_arbeitsunterlage()`. Der Providerquellcode wird weder
kopiert noch verändert. Dokument-, Finanz-, Profil-, Approval- und
Hashbindungen sind neuer FolderHome-Code.

Der Provider erzeugt eine private Arbeitsunterlage zu vom Nutzer
eingeordneten Werbungskostenbelegen. Er prüft keine steuerliche
Abziehbarkeit, berät nicht und bietet kein ELSTER-, ERiC-, Finanzamt- oder
anderes Portalverfahren. FolderHome hält diese Grenze auch in Plan, CLI und
Bericht explizit fest.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
