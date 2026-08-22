---
name: folderhome-strands-agent
description: Plant oder startet den begrenzten Strands-Agents-Loop von FolderHome über profilgebundene read-only Dokumentensuche und Themendossiers; nutzt für reproduzierbare Tests den No-Network-Fixture-Provider und Bedrock nur nach getrennten Netzwerk- und Datenweitergabefreigaben.
---

# FolderHome Strands Agent

Nutze diesen Skill, wenn eine natürliche Nutzeranfrage durch den echten
Strands-Agents-Loop an vorhandene FolderHome-Dokumentendienste geroutet werden
soll oder ein nachvollziehbarer Wettbewerbsnachweis benötigt wird.

## Ablauf

1. Prüfe, dass `strands-agents==1.53.0` und der gepinnte
   KnowledgeDigest-Checkout verfügbar sind.
2. Führe `folderhome agent plan` mit Profil- und State-Verzeichnis aus.
3. Prüfe im Plan die OS-Kontogrenze, den sequenziellen Toolmodus, endliche
   Turn-/Tool-/Ausgabelimits und `model_call_performed=false`.
4. Verwende `--model-provider fixture` für reproduzierbare No-Network-Läufe.
5. Starte `folderhome agent run` mit einem bekannten organisatorischen Profil
   und einem natürlichen Such- oder Dossierprompt.
6. Prüfe im Report Frameworkversion, Stopgrund, Toolereignisse, Hashbindungen,
   Netzwerkstatus und leere Side-Effect-Liste.
7. Verwende Bedrock nur auf ausdrücklichen Nutzerwunsch mit Modell-ID,
   AWS-Region, `--allow-network` und `--approve-sensitive-cloud-data`.
   Keine der Freigaben ersetzt eine Kosten- oder Veröffentlichungserlaubnis.

## Verbindliche Grenzen

- Keine freien Dateipfade, Shellbefehle oder allgemeinen Pluginaufrufe als
  Agententools bereitstellen.
- Nur die zwei freigegebenen read-only Tools `search_home_documents` und
  `build_home_theme_dossier` verwenden.
- Profile niemals als Zugriffs- oder Datenschutzgrenze ausgeben.
- Fixture-Ergebnisse deutlich als synthetisch und nicht als Bedrock-Lauf
  kennzeichnen.
- Keine medizinische, rechtliche, steuerliche oder sozialrechtliche
  Entscheidung aus Suchergebnissen ableiten.
- Keine Netzwerk-, Mail-, Kalender-, Telefon-, Datei- oder Kostenwirkung aus
  einer bloßen Agentenanfrage ableiten.
- `--allow-network` niemals als Freigabe zur Übertragung lokaler
  Dokumentinhalte oder Metadaten behandeln.
- Bei Limit-, Provider- oder Schemafehlern fail-closed stoppen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
