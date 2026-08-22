---
name: folderhome-legal-change-monitor
description: Vergleicht zwei datierte lokale Rechtsquellensnapshots, ordnet technische Normänderungen explizit hinterlegten Profil- oder Vertragsthemen als Prüfkandidaten zu und trennt Entwürfe, Verkündung, Rechtswirkung und Benachrichtigung strikt.
---

# FolderHome Legal Change Monitor

Nutze diesen Skill, wenn neue, bereits beschaffte Rechtsquellenstände mit
einem früheren Stand verglichen und mögliche Profil- oder Vertragsbezüge zur
späteren fachlichen Prüfung gesammelt werden sollen.

## Ablauf

1. Qualifiziere den gepinnten `law-checker`-Checkout über
   `legal providers`; importiere keinen nicht ausgewiesenen Rechtsprüfer.
2. Verlange zwei chronologische Snapshots, Interessen, `as_of`,
   Altersgrenze und Sensitivitätsfreigabe.
3. Akzeptiere im Produktivpfad nur zugelassene amtliche HTTPS-Domains,
   `authoritative=true` und `complete=false`.
4. Prüfe Datei- und Wortlauthashes vor dem Vergleich.
5. Vergleiche Normabschnitte technisch als hinzugefügt, geändert oder
   entfernt.
6. Gleiche ausschließlich explizite `user_provided`-Themen ab und nenne jeden
   Treffer `review_candidate`.
7. Weise `legislative_proposal` sichtbar als Entwurf aus.
8. Schreibe Berichte nur hinter eigenem Output-Gate und als neue Dateien.
9. Übergib Rechtsprüfung und Benachrichtigung an getrennte, bewusst
   freizugebende Folgeschritte.

## Verbindliche Grenzen

- Keine Rechtswirkung, Geltung, Betroffenheit oder Anspruchsänderung ableiten.
- Keine gesetzliche oder verfahrensrechtliche Frist berechnen.
- Themen-Tags nicht aus sensiblen Dokumenten erraten.
- Entwürfe niemals als geltendes oder verkündetes Recht ausgeben.
- Veraltete, zukünftige, unvollständig gebundene oder nichtamtliche Quellen
  nicht auswerten.
- Keine automatische Webrecherche, Rechtsprüfung, Mail, Warnung oder
  Schedulerregistrierung im Vergleichslauf.
- Testfixtures nur mit explizitem Testgate und niemals als Rechtsquelle nutzen.
- Keine vorhandenen Quellen oder Ausgaben überschreiben.
- Das Betriebssystemkonto bleibt die Sicherheitsgrenze.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
