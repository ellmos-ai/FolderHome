# THIRD_PARTY_LICENSES — Register wiederverwendeter Komponenten

[English](./THIRD_PARTY_LICENSES.md) | **Deutsch**

**Version:** 0.16
**Aktualisiert:** 2026-08-23
**Grund:** Abhängigkeiten des öffentlichen Showcases und des optionalen AgentCore-Builds erfasst
**Zweck:** Dokumentiert externe oder vorbestehende Komponenten mit genauer Revision.

| Komponente | Repository | Revision | Lizenz | Einbindung |
|---|---|---|---|---|
| file-collect-sort-action | `https://github.com/ellmos-ai/file-collect-sort-action.git` | `8ebac2739c11c6a041abdd7b30131cef648b4753` | MIT | Gepinntes Plugin-Manifest |
| HungryCall | `https://github.com/ellmos-ai/hungrycall.git` | `9ae58c4acb31070dcf2e3fc468cff1c80c9a7e9c` | MIT | Gepinntes Plugin-Manifest |
| Ringedingeding | `https://github.com/ellmos-ai/ringedingeding.git` | `94ae1f1e028be5aaf100baafadc18b64ff0940a2` | MIT | Gepinntes Plugin-Manifest |
| doc-services | Lokaler Checkout ohne Remote | `e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2` | MIT | Gepinntes Plugin-Manifest und Extraktions-Bridge |
| KnowledgeDigest | `https://github.com/file-bricks/knowledgedigest.git` | `7040c66aa9326975ad81c156acf0d49fd5dca60f` | MIT | Gepinntes Plugin-Manifest sowie Index- und Such-Bridge |
| report-forge | `https://github.com/ellmos-ai/report-forge.git` | `355acb5ff1abe41b384a0d1e3a00925e6ac86215` | MIT | Inventarisiert; Runtime-Version vor Bridge-Anbindung zu bereinigen |
| ai-media-editor | `https://github.com/ellmos-ai/ai-media-editor.git` | `4e4c79d8c16a117bf69c0f72ad946575110a6b84` | MIT | Revisionsgebundener Medien-Handoff; keine Medienausführung im Artefaktplan |
| MailProcessor | `https://github.com/doc-bricks/MailProcessor.git` | `704575901b8b526dcd1436a86d6f42818b4079cd` | MIT | Suite-Launcher; kein FolderHome-Runtime-Connector |
| UniversalDocsGrabber | `https://github.com/doc-bricks/UniversalDocsGrabber.git` | `0ccd03455b63acbca6e71cc48ba464f208a759cd` | MIT | Vorgesehener IMAP-Dokumentprovider; lokaler Checkout aktuell blockiert |
| UniversalMailCleaner | `https://github.com/doc-bricks/UniversalMailCleaner.git` | `85de4dd2e84c499152b09d4e5688332ff3bb2ed4` | MIT | Getrennte Postfachbereinigung; nicht Teil des read-only Ingests |
| UniversalInvoiceMail | `https://github.com/doc-bricks/UniversalInvoiceMail.git` | `c58be4cdf92d8265694037cf1dbf7f14c84b39f9` | MIT | Spezialisierte Rechnungsreferenz; kein Runtime-Import |
| PDFtoPDFocr | `https://github.com/doc-bricks/PDFtoPDFocr.git` | `c89ae00982d7597b663c99527298363b9e2fce58` | MIT | Inventarisiert; GUI-Monolith und verschiebende Merge-Funktion nicht direkt angebunden |
| MarkItDown | `https://github.com/microsoft/markitdown.git` | `fd239d5d2be43d9b68329730206b9312c7d5a388` | MIT | Indirekt über doc-services; keine eigene FolderHome-Bridge |
| pypdf | PyPI-Paket `pypdf` | `>=4.0`, geprüft mit `6.16.1` | BSD-3-Clause | Optionale PDF-Montage in `document_transform` |
| Pillow | PyPI-Paket `Pillow` | `>=10.0`, geprüft mit `12.3.0` | MIT-CMU | Optionale lokale Bild-zu-PDF-Rasterung |
| ReportLab | PyPI-Paket `reportlab` | `>=4.0`, geprüft mit `5.0.1` | BSD | Optionale deterministische Text-zu-PDF-Neusetzung |
| llm-note | `https://github.com/doc-bricks/llm-note.git` | `b5fe59fc155ded9603566aa0fb920a53181a2426` | MIT | Gepinnter lokaler Notizstore über öffentliche Write-API und schemafesten read-only Adapter |
| steuer-assistent | `https://github.com/ellmos-ai/steuer-assistent.git` | `5d39aeec98bf0a5734bf07dc35a58aa9e1331309` | MIT | Gepinnter lokaler Belegstore und private ZIP-Arbeitsunterlage über öffentliche Provider-API |
| BACH Wetter/Newspaper/Daily Agent | `https://github.com/ellmos-ai/bach.git` | `9ff3df23d6e8e27b9c9eaad71f2430923224d4d9` | MIT | Ausschließlich Designreferenz; fremd veränderter Monolith wird nicht als FolderHome-Runtime geladen und kein Code kopiert |
| law-checker | `https://github.com/ellmos-ai/law-checker.git` | `a5b0cd51bc3666962f2fae8017c855dea0a712a2` | MIT | Unveränderter read-only Registry-/Quellenprovider; kein Code kopiert, kein Agentenworkflow importiert |
| UpToday | Lokaler Checkout ohne Remote | `7582ca87e17e458bb99a7379d2c54003c15415a4` | MIT | Designreferenz für Inventar/Medikation und getesteter ICS-Dateihandoff; kein Runtime-Import |
| Routinika | Lokaler OneDrive-Bestand | `portable_bundle.py` SHA-256 `3168d7bca9d1fdfcb8cf437a60fa475fa39fa58a6804fe50a132ea03df35b7e2` | vor Distribution zu prüfen | Hashgebundene Bundle-Designreferenz; kein Live-Connector und kein kopierter Code |
| Google Calendar Skill 1.2.5 | Lokales Plugin-Paket | `google-calendar-skill@1.2.5` | paketgebundener Bestand | Agentischer Handoff; kein kopierter Code und kein Live-Aufruf in Phase 27 |
| gesundheit-Skill 2.0.0 | `https://github.com/ellmos-ai/skills.git` | `0317f32310eed11d21f603cb6f22a689485af226` | MIT | Designreferenz für bereitgestellte Gesundheitsinformationen und Organisationsgrenzen |
| docs-analysis 1.0.0 | Lokaler, aus BACH extrahierter Skill | Stand 2026-03-15 | MIT / projektinterner Bestand | Anforderungs- und Code-Differenzmethode für Phase 22; kein Runtime-Import |
| project-docs | Lokales internes project-docs-Template | Stand 2026-08-21 | Projektinterner Bestand | Doku-Grundgerüst |
| ellmos mail-connector | Lokales Modul `.MODULES/.CONNECTORS/mail-connector` | Designreferenz, bewusst nicht gepinnt | MIT | Verbindungslebenszyklus, Modified-UTF-7-Ordnernamen und zweiwegige Passwortauflösung als Muster übernommen; kein Code importiert und keine Revision gepinnt, daher kann kein Checkout wegdriften |
| Strands Agents SDK | `https://github.com/strands-agents/sdk-python.git` | PyPI `strands-agents==1.53.0` | Apache-2.0 | Verpflichtender Agentenloop; Fixture standardmäßig ohne Netzwerk, Bedrock nur nach Gate |
| tzdata | PyPI-Paket `tzdata` | `==2026.3` auf Windows | Apache-2.0 | IANA-Zeitzonendaten für reproduzierbare Kalender-, Medikamenten- und Scheduler-Verträge auf Windows |
| actions/checkout | `https://github.com/actions/checkout` | `11d5960a326750d5838078e36cf38b85af677262` (`v4`) | MIT | SHA-gepinnte Action für den Pages-Build |
| actions/configure-pages | `https://github.com/actions/configure-pages` | `983d7736d9b0ae728b81ab479565c72886d7745b` (`v5`) | MIT | SHA-gepinnte Action für die Pages-Konfiguration |
| actions/upload-pages-artifact | `https://github.com/actions/upload-pages-artifact` | `56afc609e74202658d3ffba0e8f6dda462b719fa` (`v3`) | MIT | SHA-gepinnte Action für den begrenzten Artefakt-Upload |
| actions/deploy-pages | `https://github.com/actions/deploy-pages` | `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e` (`v4`) | MIT | SHA-gepinnte Action für das Pages-Deployment |
| Python Docker Official Image | `https://hub.docker.com/_/python` | `python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7` | Python-PSF- und enthaltene Debian-Paketlizenzen | Digest-gepinnte ARM64-Build- und Runtimebasis; nicht vendort |

Die Tabelle ist ein Register, kein Ersatz für die vollständigen Lizenztexte
der jeweiligen Komponenten. Werden Quellen später vendort oder als Submodule
eingebunden, müssen deren Original-Lizenzdateien mitgeführt werden.

Die lokale App aus Phase 35 selbst verwendet weiterhin nur die
Python-Standardbibliothek und neuen FolderHome-Code. Phase 36 ergänzt das
Apache-2.0-lizenzierte Strands Agents SDK als exakt gepinnte
Projektabhängigkeit. Der Fixture-Modelladapter benötigt keine Cloud; der
optionale Bedrock-Provider bleibt hinter einem ausdrücklichen Netzwerk-Gate.
Windows installiert zusätzlich das exakt gepinnte `tzdata`-Paket, weil die
Python-Standardinstallation dort keine systemweite IANA-Datenbank garantiert.
Microsoft Edge und Playwright dienten ausschließlich der lokalen visuellen
Abnahme; sie werden weder ausgeliefert noch zur Laufzeit von FolderHome
importiert.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
