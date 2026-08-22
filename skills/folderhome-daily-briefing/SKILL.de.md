---
name: folderhome-daily-briefing
description: Bündelt belegte lokale Wetter- und Nachrichtensnapshots zu einem quellenbewussten HTML-Brief und stellt ihn nach getrennter Freigabe in einen gewählten Desktopordner zu, ohne Live-Netzwerk oder Scheduler zu behaupten.
---

# FolderHome Daily Briefing

[English](./SKILL.md) | **Deutsch**

Nutze diesen Skill, wenn ein Mensch einen lokalen Wetter- und Newspaper-Brief
aus bereits bereitgestellten Snapshots planen, prüfen, rendern oder auf den
Desktop kopieren möchte.

## Ablauf

1. Prüfe `folderhome briefing providers --json`. Behandle blockierte
   Live-Connectoren als echte Produktgrenze.
2. Prüfe Briefingdatum, `as_of`, Zeitzone, Profil, Wetterort, Kategorien und
   die beiden Snapshotpfade.
3. Erzeuge `briefing plan` nur nach Sensitivitätsfreigabe. Dieser Schritt darf
   keine Ausgabe- oder Desktopdatei anlegen.
4. Zeige Datenstand, Warnungen, Quellen, ausgelassene Artikel, Planhash und
   HTML-Hash. Ein veralteter Snapshot bleibt ausdrücklich veraltet.
5. Rendere erst nach eigener Render-Approval und `--approve-output-write` in
   einen Nicht-Desktopordner.
6. Lass den Menschen die lokale HTML-Datei prüfen.
7. Kopiere erst nach separater Desktop-Approval und
   `--approve-desktop-write` exakt diesen Hash auf den gewählten Desktop.

## Verbindliche Grenzen

- Keine stillen Wetter-, RSS-, Web- oder LLM-Aufrufe.
- Keine Aktualitäts- oder Vollständigkeitsbehauptung ohne frischen Snapshot.
- Nur HTTPS-Quellen ohne eingebettete Zugangsdaten.
- Keine HTML-Übernahme unescapter Titel, Zusammenfassungen oder Links.
- Keine vorhandene Ausgabe oder Desktopdatei überschreiben.
- Render- und Desktopziel dürfen nicht im selben Zielordner liegen.
- Keine Schedulerregistrierung oder dauerhafte Freigabe aus einer
  Einzelfreigabe ableiten.
- Familienprofile sind organisatorisch; das Betriebssystemkonto bleibt die
  Sicherheitsgrenze.
- Keine echten privaten Standort- oder Profildaten in Repository-Beispiele
  schreiben.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
