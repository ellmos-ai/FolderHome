---
name: folderhome-official-notices
description: Erfasst ausdrücklich beschriftete Angaben aus einem lokalen Bescheid mit Zeilen- und Hashbeleg und erzeugt nach Freigabe einen Prüfbericht, ohne Rechtsprüfung, gesetzliche Fristberechnung oder Antwort zu behaupten.
---

# FolderHome Official Notices

Nutze diesen Skill, wenn ein Mensch einen bereitgestellten Behörden- oder
Sozialleistungsbescheid zunächst verständlich und nachvollziehbar erfassen
möchte.

## Ablauf

1. Prüfe `folderhome notices providers --json`. Verwende die Analyse nur,
   wenn `document_extraction` bereit ist; behandle die blockierte
   Rechtsprüfung als echte Produktgrenze.
2. Bestätige Quelle, Profil, Analysezeitpunkt und die ausdrückliche
   Sensitivitätsfreigabe. Frage ein Zugangsdatum nur als Nutzerangabe ab.
3. Führe `notices inspect` read-only aus und zeige Bescheidart, Behörde,
   Aktenzeichen, Entscheidung, Fristtext, fehlende Felder, Konflikte und alle
   Evidenzzeilen.
4. Stelle klar, dass nur ausdrücklich gelabelte Angaben übernommen wurden.
   Wandle relative Fristtexte nicht in Daten um.
5. Erzeuge Markdown und JSON nur nach `--approve-output-write` in zwei neuen
   Pfaden. Prüfe Quellhash und Never-overwrite.
6. Übergib bei laufender, unklarer oder möglicherweise abgelaufener Frist
   Original und Bericht unverzüglich an qualifizierte sozialrechtliche Hilfe.

## Verbindliche Grenzen

- Keine Rechtsberatung oder Bewertung der Rechtmäßigkeit.
- Keine gesetzliche Frist berechnen oder verbindlich bestätigen.
- Kein Zugangsdatum aus Datei-, Scan-, E-Mail- oder OCR-Metadaten ableiten.
- Keine stillen Web-, LLM- oder law-checker-Aufrufe.
- Keine Antwort, keinen Widerspruch und keinen Antrag erzeugen oder versenden.
- Keine vorhandene Datei überschreiben oder das Quelldokument verändern.
- Fehlende und widersprüchliche Felder sichtbar lassen.
- `ready_for_review` nur als Bereitschaft zur menschlichen Prüfung erklären.
- Familienprofile sind organisatorisch; das Betriebssystemkonto bleibt die
  Sicherheitsgrenze.
- Keine echten Bescheide oder privaten Profildaten in Repository-Beispiele
  übernehmen.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
