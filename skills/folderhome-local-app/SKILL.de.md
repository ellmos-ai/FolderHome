---
name: folderhome-local-app
description: Prüft und startet die gemeinsame lokale FolderHome-Oberfläche ausschließlich auf 127.0.0.1, schützt sie mit einem kurzlebigen Sitzungstoken und nutzt vorhandene Dokumentensuche sowie Themendossiers read-only unter der Sicherheitsgrenze des Betriebssystemkontos.
---

# FolderHome Local App

[English](./SKILL.md) | **Deutsch**

Nutze diesen Skill, wenn ein Mensch die lokale FolderHome-Oberfläche für
Dokumentensuche, Themendossiers und die Übersicht vorhandener Fähigkeiten
bedienen möchte.

## Ablauf

1. Verlange ein vorhandenes Profilverzeichnis und einen vorhandenen lokalen
   KnowledgeDigest-State des aktuellen Betriebssystemkontos.
2. Führe zuerst `folderhome app plan` aus und prüfe Providerrevision,
   Loopback-Bindung, Profilvertrag und deaktivierte Nebenwirkungen.
3. Erkläre sichtbar, dass Profile nur organisatorisch sind und keine
   Zugriffsgrenzen innerhalb desselben OS-Kontos darstellen.
4. Starte `folderhome app serve` nur nach bewusster lokaler Freigabe mit
   `--approve-loopback-server`.
5. Verwende ausschließlich die vom Startlauf ausgegebene Token-URL.
6. Nutze in der GUI nur die allowlisteten read-only Funktionen Suche und
   Themendossier.
7. Beende den Server nach der Sitzung und behandle das Sitzungstoken als
   kurzlebiges lokales Geheimnis.

## Verbindliche Grenzen

- Niemals auf `0.0.0.0`, eine LAN-Adresse oder einen externen Host binden.
- Kein Port-Forwarding, Reverse-Proxy, CORS oder externer Browserzugriff.
- Sitzungstoken nicht protokollieren, versenden oder dauerhaft speichern.
- Keine freien Pfade, Shellbefehle oder allgemeinen Pluginaufrufe an die API
  übergeben.
- Keine Profilwahl als Authentifizierung oder Zugriffsschutz ausgeben.
- Keine Dokumente, Profile oder Indexdaten aus der GUI verändern.
- Providerfehler ohne interne Pfade oder technische Geheimnisse anzeigen.
- Schreibende, rechtliche, medizinische und finanzielle Aktionen nur über
  ihre getrennten Fach-, Approval- und Ausführungsworkflows weiterführen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
