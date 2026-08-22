---
name: folderhome-tax-workpaper
description: Plant und erfasst vom Menschen eingeordnete Steuerbelege evidenzgebunden im lokalen steuer-assistent und exportiert nach separater Freigabe private Arbeitsunterlagen ohne Steuerberatung oder Portalübermittlung.
---

# FolderHome Tax Workpaper

[English](./SKILL.md) | **Deutsch**

Nutze diesen Skill, wenn ein Mensch bereitgestellte Belege für eine private
Steuer-Arbeitsunterlage ordnen oder eine solche Unterlage exportieren möchte.

## Ablauf

1. Prüfe mit `folderhome tax providers --json` den gepinnten, sauberen
   Providercheckout.
2. Verwende nur eine Dokument-ID aus dem FolderHome-Katalog. Prüfe den
   aktuellen Dokumenthash und bei angegebener Finanzbuchung Profil und
   Centbetrag.
3. Behandle `category_candidate` ausschließlich als Vorschlag. Ohne
   `confirmed_category` bleibt der Plan nicht ausführbar.
4. Erzeuge `tax receipt-plan` erst nach lokaler Sensitivitätsfreigabe.
5. Zeige dem Menschen Profil, Betrag, Datum, Kategorie, Dokumentbindung,
   Planhash und Providerstore-Revision.
6. Führe `tax receipt-apply` nur mit exakt passender Approval und
   `--approve-state-write` aus.
7. Plane eine ZIP-Arbeitsunterlage mit `tax export-plan` separat für genau ein
   Profil und Steuerjahr.
8. Exportiere nur mit eigener Export-Approval sowie State- und Output-Gate.

## Verbindliche Grenzen

- Keine steuerliche Abziehbarkeitsprüfung, Steuerberatung oder Empfehlung.
- Keine Steuerberechnung, amtliche Steuererklärung oder Vollständigkeitszusage.
- Kein ELSTER-, ERiC-, Finanzamt-, Netzwerk- oder Versandzugriff.
- Keine automatische Übernahme eines Kategorienvorschlags.
- Keine Speicherung ohne Plan-, Approval-, Dokumenthash- und
  Providerstore-Bindung.
- Keine Vermischung verschiedener Profile in derselben Providerdatenbank.
- Profile sind organisatorisch; das Betriebssystemkonto bleibt die
  Sicherheitsgrenze.
- Keine vorhandene Exportdatei überschreiben.
- Keine echten Belege, Kontodaten oder Geheimnisse in Repository-Beispiele
  übernehmen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
