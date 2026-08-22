# BACH Wetter, Newspaper und Daily Agent — Designreferenz

[English](./README.md) | **Deutsch**

Geprüft wurde der lokale BACH-Checkout auf Commit
`9ff3df23d6e8e27b9c9eaad71f2430923224d4d9`, Repository
`https://github.com/ellmos-ai/bach.git`, Lizenz MIT. Die relevanten Wetter-,
Newspaper- und Daily-Agent-Dateien sind gegenüber Git unverändert; der
Gesamtcheckout enthält jedoch fremde Änderungen und wird nicht als
FolderHome-Runtime geladen. Die fokussierten Newspaper-Tests waren 11/11
grün.

BACH belegt die Produktidee eines Wetterabschnitts, einer gruppierten
HTML-/PDF-Zeitung und einer Desktopzustellung. FolderHome kopiert den Code
nicht: Der BACH-Bestand ist an eine zentrale Datenbank, implizite Systemzeit,
einen fest codierten Ort, direkten Netzwerkzugriff, Edge und unmittelbare
Desktop-/Telegram-Side-Effects gekoppelt.

Neu gekapselte FolderHome-Verträge verwenden stattdessen lokale,
hashgebundene Snapshots, explizite Zeitpunkte und getrennte Render- und
Desktopfreigaben. Live-Netzwerk und Scheduler bleiben sichtbar blockiert.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
