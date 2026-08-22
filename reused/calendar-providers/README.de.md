# Kalenderprovider — unveränderte Referenzen

[English](./README.md) | **Deutsch**

FolderHome kopiert keinen Quellcode von UpToday, Routinika oder dem
Google-Calendar-Skill. Phase 27 hält nur geprüfte Rollen und Revisionen fest:

| Projekt | Revision oder Hash | Verwendung |
|---|---|---|
| UpToday | `7582ca87e17e458bb99a7379d2c54003c15415a4` | RFC-5545-ICS-Dateihandoff ohne Live-Sync |
| Routinika `portable_bundle.py` | SHA-256 `3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2` | dateibasierte Bundle-Designreferenz; kein Live-Connector |
| Routinika `EXPORTFORMAT.md` | SHA-256 `94cfdf42cc2b45e5a4260a43788f03041ebfb99aea8d8b3ef900debdc5314f8d` | Formatnachweis |
| Routinika `README.md` | SHA-256 `2461b05a7c5b17dc311fea42adb2b88cead70dd765b0f53d50c7e8bbc7a8bc60` | Produkt- und Grenznachweis |
| Google Calendar Skill | `google-calendar-skill@1.2.5` | agentischer Handoff mit gesonderter Nutzerfreigabe |

UpToday ist MIT-lizenziert. Der Routinika-Bestand ist eine lokale,
dateibasierte Designreferenz; vor einer Distribution muss seine Lizenzlage
gesondert geprüft werden. Der Google-Skill wird nicht in dieses Repository
kopiert. Phase 27 hat keinen realen Kalenderconnector ausgeführt.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
