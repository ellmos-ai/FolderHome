---
name: folderhome-administrative-drafts
description: Bereitet deutlich markierte Widerspruchs-, Behördenantwort- und Leistungsantragsentwürfe aus Bescheidevidenz und bereitgestellten Nutzerangaben vor und schreibt sie erst nach exakter Bestätigung lokal, ohne Rechtsprüfung, Fristberechnung oder Versand.
---

# FolderHome Administrative Drafts

[English](./SKILL.md) | **Deutsch**

Nutze diesen Skill, wenn ein Mensch aus einem bereitgestellten Bescheid oder
aus eigenen Angaben einen kontrollierten Verwaltungsbrief entwerfen möchte.

## Ablauf

1. Bestimme `objection`, `authority_response` oder `benefit_application`.
2. Bestätige Profil, Absender, Empfänger, gewünschtes Ergebnis und die
   ausdrückliche Sensitivitätsfreigabe.
3. Analysiere bei bescheidbezogenen Entwürfen die unveränderte Quelle erneut.
   Prüfe Quellhash, Behörde, Aktenzeichen, Bescheiddatum und Evidenzzeilen.
4. Erzeuge `drafts preview` ohne Write. Zeige Dokumentfakten und
   `user_provided`-Angaben getrennt sowie alle offenen Punkte und Warnungen.
5. Weise darauf hin, dass weder Rechtsweg, Frist, Zuständigkeit,
   Leistungsberechtigung noch Erfolgsaussicht geprüft wurden.
6. Lass den Menschen den vollständigen Brief und beide Hashes bestätigen.
7. Schreibe mit exakter Approval und `--approve-output-write` ausschließlich
   neue lokale Markdown-/TXT-Dateien.
8. Beende den Skill vor jeder Außenwirkung. Eine spätere Verwendung benötigt
   eine eigene aktuelle fachliche Prüfung und eine separate Nutzerhandlung.

## Verbindliche Grenzen

- Kein Widerspruchsentwurf ohne ausdrücklich gelesenen Rechtsbehelf
  `Widerspruch`, eindeutige Behörde und passende Empfängerbindung.
- Keine gesetzliche Frist aus Zugangsdatum, Dateidatum oder Fristtext
  berechnen.
- Keine Rechtsmeinung, Erfolgsaussicht oder Leistungsberechtigung erfinden.
- Nutzeraussagen nie als Dokumentevidenz darstellen.
- Der sichtbare `ENTWURF`-/Prüfhinweis muss im Brief bleiben.
- Kein LLM-, Web- oder law-checker-Aufruf innerhalb des lokalen Entwurfslaufs.
- Keine vorhandene Ausgabe oder Quelle überschreiben.
- Keine E-Mail, kein Behördenportal, kein Upload, Druck oder Versand.
- Profile sind organisatorisch; das Betriebssystemkonto bleibt die
  Sicherheitsgrenze.
- Keine echten Bescheide oder persönlichen Daten in Repository-Beispiele
  schreiben.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
