---
name: folderhome-benefit-screening
description: Gleicht lokale nutzerbereitgestellte Profilfakten mit einem datierten unvollständigen Routingkatalog ab und verweist auf passende amtliche Sozialleistungs-Vorchecks, ohne Anspruch, Höhe, Vollständigkeit oder Antrag zu behaupten.
---

# FolderHome Benefit Screening

Nutze diesen Skill, wenn ein Mensch wissen möchte, welche amtlichen
Sozialleistungs-Lotsen aufgrund weniger bereitgestellter Lebenssituationsdaten
als nächster Prüfschritt sinnvoll sein könnten.

## Ablauf

1. Verlange Sensitivitätsfreigabe, ein bekanntes Profil, Leistungsprofil,
   Katalog, Analysezeitpunkt und maximale Quellenaltersgrenze.
2. Prüfe, dass der Katalog `complete=false` ausweist und jede Quelle amtlich,
   per HTTPS erreichbar, datiert und an eine Evidenzzusammenfassung gebunden
   ist.
3. Führe `benefits check` lokal aus. Öffne keine Website automatisch.
4. Erkläre pro Programm Routingstatus, fehlende Fakten, Quelle und alle nicht
   modellierten Anforderungen.
5. Empfehle bei passender Route ausschließlich den genannten amtlichen
   Vorcheck. Bezeichne ihn als nächsten Prüfschritt, nicht als Anspruch.
6. Schreibe Markdown/JSON nur nach eigenem Output-Gate als neue Dateien.
7. Überlasse persönliche Eingabe auf der amtlichen Seite und jeden späteren
   Antrag einer separaten bewussten Nutzerhandlung.

## Verbindliche Grenzen

- Keine Leistungsberechtigung, Leistungshöhe oder Erfolgsaussicht bestimmen.
- `routing_mismatch` niemals als Ablehnung oder Ausschluss ausgeben.
- Fehlende Profilangaben nicht aus Dokumenten, Kontoauszügen oder Metadaten
  erraten.
- Veraltete oder zukünftige Quellen nicht auswerten.
- Nur amtliche HTTPS-Handoffs ohne eingebettete Zugangsdaten zulassen.
- Katalogvollständigkeit nicht behaupten.
- Kein Live-Webabruf, Portalaufruf, Antrag, Upload oder Versand im lokalen Lauf.
- Keine vorhandene Quelle oder Ausgabe überschreiben.
- Profile sind organisatorisch; das Betriebssystemkonto bleibt die
  Sicherheitsgrenze.
- Keine echten sensiblen Profile in Repository-Beispiele schreiben.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
