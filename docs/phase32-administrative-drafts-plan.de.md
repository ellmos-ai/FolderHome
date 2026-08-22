# Phase 32: Kontrollierte Verwaltungsentwürfe

[English](./phase32-administrative-drafts-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Zweck:** Widerspruchs-, Behördenantwort- und Leistungsantragsentwürfe aus
Profilangaben, Bescheidevidenz und bereitgestellten Nutzeraussagen erzeugen,
ohne Rechtsprüfung, Leistungsprüfung oder Versand zu behaupten.

## Wiederverwendungsabgleich

Phase 32 baut keinen zweiten Briefgenerator. Der Phase-24-Kern übernimmt
weiterhin:

- Absender, Empfänger und Anschriften,
- Designauflösung nach Bereich, Zweck und Profil,
- streng geprüfte Vorlagen und Platzhalter,
- deterministische Markdown-/TXT-Vorschauen,
- Ausgabehashes, Never-overwrite und teilweises Rollback,
- sichtbare, weiterhin blockierte DOCX-/ODT-Handoffs.

Phase 31 liefert Bescheidart, Behörde, Aktenzeichen, Bescheiddatum,
Rechtsbehelf und weitere Felder mit Zeile, Dokument-ID und Quellhash. Neu ist
nur die Kapsel `contracts.administrative_drafts` und
`application.administrative_drafts`, welche beide Bestände sicher verbindet.

## Aktueller amtlicher Gegencheck

Für die Produktgrenze wurden am 2026-08-22 drei amtliche Normseiten geprüft:

- [§ 84 SGG](https://www.gesetze-im-internet.de/sgg/__84.html) zur Form,
  Einreichungsstelle und grundsätzlich an die Bekanntgabe geknüpften
  Widerspruchsfrist,
- [§ 36 SGB X](https://www.gesetze-im-internet.de/sgb_10/__36.html) zu den
  Angaben einer Rechtsbehelfsbelehrung,
- [§ 16 SGB I](https://www.gesetze-im-internet.de/sgb_1/__16.html) zur
  Antragstellung und Weiterleitung.

Diese Quellen werden nicht als pauschale Einzelfallentscheidung in den
Entwurf geschrieben. Welcher Rechtsweg, welche Frist, welche Form und welcher
Träger tatsächlich gelten, benötigt eine aktuelle fachliche Prüfung. Phase 32
berechnet deshalb keine Frist und bestätigt keine Zuständigkeit.

## Neuer gekapselter Entwurfsvertrag

Eine Anfrage nennt genau eine Art:

- `objection` für einen Widerspruchsentwurf,
- `authority_response` für einen Behördenantwortentwurf,
- `benefit_application` für einen Leistungsantragsentwurf.

Bescheidbezogene Entwürfe müssen an den erwarteten Quell-SHA-256 gebunden
sein. FolderHome analysiert die Quelle erneut und verlangt dasselbe Profil,
eindeutige Behörde, Aktenzeichen, Bescheidart und Bescheiddatum. Der Empfänger
muss der gelesenen Behörde entsprechen. Ein Widerspruchsentwurf wird nur
vorbereitet, wenn das Dokument ausdrücklich den Rechtsbehelf
`Widerspruch` nennt. Diese Prüfung ist keine Aussage darüber, ob er im
Einzelfall zulässig oder rechtzeitig ist.

Nutzeraussagen und gewünschtes Ergebnis heißen in der Vorschau
`user_provided`. Sie werden nicht als Dokumenttatsache ausgegeben. Erst eine
separate Approval bestätigt den konkreten Vorschauinhalt für eine lokale
Ausgabe. Dokumentfakten bleiben an ihre Phase-31-Evidenz gebunden.

## Ablauf und Side-Effect-Grenze

```text
Anfrage + Profil + Sensitivitätsfreigabe
  → bei Bescheidentwurf Quelle erneut analysieren und Hash prüfen
  → Dokumentevidenz und bereitgestellte Nutzeraussagen getrennt sammeln
  → Zweck und sichere Verwaltungsbriefvorlage fest binden
  → Phase-24-Korrespondenzvorschau nur im Speicher erzeugen
  → sichtbaren ENTWURF-/Prüfhinweis in den Brief aufnehmen
  → Plan, Briefhashes, offene Punkte und Warnungen anzeigen
  → Mensch prüft den vollständigen Inhalt
  → exakte Approval + Output-Gate schreibt neue Markdown-/TXT-Dateien
```

Es gibt kein Sende-Kommando. `send_supported`, `sent`,
`eligibility_assessed` und `deadline_legally_calculated` bleiben `false`.
Die lokale Freigabe ist keine Freigabe für E-Mail, Upload, Behördenportal,
Druck oder Postversand.

## Abnahme

Die synthetische Abnahme prüft Widerspruchs-, Antwort- und Antragsgrenzen,
Dokument-/Nutzerprovenienz, Profil- und Behördenbindung, expliziten
Rechtsbehelf, portable Quellhashbindung, boolesche Freigabefelder,
Quelländerung, Output-Gate und Never-overwrite. Der CLI-Test führt
Bescheidanalyse, Vorschau, hashgebundene Bestätigung und lokale Ausgabe Ende
zu Ende aus und bestätigt, dass keine Außenwirkung erfolgte.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
