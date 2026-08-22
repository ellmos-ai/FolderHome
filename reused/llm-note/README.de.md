# llm-note — unverändert wiederverwendeter Notizspeicher

[English](./README.md) | **Deutsch**

FolderHome lädt den eigenständigen Provider nur aus einem sauberen Checkout
auf Commit `b5fe59fc155ded9603566aa0fb920a53181a2426` und Paketversion `1.0.3`.
Kanonisches Repository ist `https://github.com/doc-bricks/llm-note.git`, die
Lizenz ist MIT.

Wiederverwendet werden die lokale SQLite-Ablage und die öffentliche
`NoteStore.write()`-API. FolderHome kopiert oder verändert keinen
Providerquellcode. Geführte Fragen, menschliche Freigabe, Profilkontext,
explizite Referenzen und append-only Revisionen sind neuer FolderHome-Code.

Lesen erfolgt über einen schema- und revisionsgebundenen read-only Adapter,
weil die öffentliche Providerklasse beim Erzeugen auch in einem fehlenden
Store das Schema initialisiert. Schreiben ist nur mit exakter Plan-, Inhalts-
und Statefreigabe erlaubt. Weder Provider noch Phase-28-Bridge verwenden das
Netzwerk oder eine externe Synchronisierung.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
