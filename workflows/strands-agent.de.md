# Workflow: Strands-Agent und Wettbewerbsdemo ausführen

[English](./strands-agent.md) | **Deutsch**

> **Last verified:** 2026-08-22
> **Frequency:** pro Demo- oder Agentenabnahme
> **Duration:** wenige Sekunden ohne Bedrock; providerabhängig mit Bedrock

## Purpose

Den echten Strands-Agents-Loop von FolderHome begrenzt planen, mit
synthetischen Daten reproduzierbar ausführen und einen hashgebundenen
Wettbewerbsnachweis erzeugen. Der Ablauf trennt No-Network-Evidenz von einem
optional freigegebenen Bedrock-Lauf.

## Preconditions

- Python 3.11 oder neuer und `strands-agents==1.53.0` sind installiert.
- Für einen produktiven lokalen Indexlauf existieren Profilverzeichnis,
  KnowledgeDigest-State und exakt gepinnter Providercheckout.
- Für die selbstenthaltene Wettbewerbsdemo werden keine Providerzugänge oder
  echten personenbezogenen Daten benötigt.
- Ein Bedrock-Lauf besitzt getrennte Netzwerk-, Datenweitergabe- und
  Kostenentscheidungen.

## Steps

1. **Agentenoberfläche read-only planen.**

   ```powershell
   folderhome agent plan --profiles-dir <profiles-dir> --state-dir <state-dir> --model-provider fixture --json
   ```

2. **Plan prüfen.** Framework muss `strands-agents` sein, Toolausführung
   `sequential`, die Tools müssen exakt allowlistet und alle Limits endlich
   sein. Ein Plan führt keinen Modellaufruf aus.
3. **Lokale Anfrage über den Fixture-Agenten ausführen.**

   ```powershell
   folderhome agent run --profiles-dir <profiles-dir> --state-dir <state-dir> --profile-id lukas --prompt "Gib mir alles zum Thema Krankenversicherung." --model-provider fixture --json
   ```

4. **Agentenreport lesen.** Prüfe `stop_reason=end_turn`, mindestens ein
   ausgeführtes Toolereignis, korrekte Ein-/Ausgabehashes,
   `network_used=false` und eine leere Side-Effect-Liste.
5. **Selbstenthaltene Wettbewerbsdemo erzeugen.** Das Ziel muss neu sein.

   ```powershell
   folderhome demo run --output-dir <new-demo-dir> --approve-output-write --json
   ```

6. **Evidence zurücklesen.** Verifiziere `EVIDENCE.json`, die drei dort
   genannten Artefakthashes, beide Szenarien und die sichtbare Kennzeichnung
   synthetischer Daten in `DEMO.md`.
7. **Optionalen Bedrock-Lauf getrennt entscheiden.** Nur nach ausdrücklicher
   Nutzerfreigabe Modell-ID, Region, `--allow-network` und
   `--approve-sensitive-cloud-data` angeben. Ergebnis als Bedrock- und nicht
   als Fixture-Nachweis protokollieren.

## Exit-Criteria

- [ ] Der echte Strands-SDK-Loop hat mindestens ein FolderHome-Tool ausgeführt.
- [ ] Toolreihenfolge, Turnzahl und Ergebnisgröße waren begrenzt.
- [ ] Der reproduzierbare Lauf benötigte weder Netzwerk noch Zugangsdaten.
- [ ] Demoartefakte enthalten ausschließlich synthetische Daten.
- [ ] `EVIDENCE.json` und die darin genannten SHA-256-Werte stimmen.
- [ ] Kein bestehendes Ziel wurde überschrieben.
- [ ] Ein Bedrock- oder anderer Außenlauf wurde ohne Nutzerfreigabe nicht gestartet.

## Fallstricke

- Der Fixture-Provider belegt die Strands-Orchestrierung, aber keine
  Modellqualität oder AWS-Verfügbarkeit.
- `--allow-network` ist nur das technische Laufgate. Die Weitergabe lokaler
  Suchergebnisse benötigt zusätzlich `--approve-sensitive-cloud-data`; beide
  Gates autorisieren weder Kosten, Upload noch Veröffentlichung.
- Familienprofile teilen innerhalb desselben OS-Kontos dieselben Dateirechte.
- Die Agentenallowlist enthält absichtlich keine schreibenden Fachworkflows.

## Verwandte

- [`../skills/folderhome-strands-agent/SKILL.md`](../skills/folderhome-strands-agent/SKILL.md)
- [`./local-app.md`](local-app.de.md)
- [`./document-library.md`](document-library.de.md)
- [`../docs/phase36-completion-audit.md`](../docs/phase36-completion-audit.de.md)

## Historie

- **2026-08-22** — Strands-Agent, Fixture-Modell, getrennte Bedrock-Gates und Demoabnahme ergänzt

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
