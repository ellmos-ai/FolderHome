# Workflow: FolderHome-Master-Agent verwenden

[English](./master-agent.md) | **Deutsch**

> **Zuletzt geprüft:** 2026-08-23  
> **Häufigkeit:** je Gesprächsanfrage  
> **Dauer:** modellabhängig; die Fachausführung bleibt ein eigener Workflow

## Zweck

Einen modellgesteuerten Agenten in GUI und CLI für FolderHome-Fähigkeitssuche,
lokale Nur-Lese-Werkzeuge und begrenzte Fachplanung verwenden. Semantische Wahl,
deterministische Endpoint-Auflösung, Persona-Stil, Freigabe und Ausführung bleiben
getrennte Ebenen.

## Schritte

1. `folderhome agent plan` ausführen und die begrenzte Werkzeugoberfläche prüfen.
2. Denselben Dienst mit `folderhome agent session` oder der lokalen GUI starten.
   `folderhome agent chat` dient einem einzelnen nicht interaktiven Durchlauf.
3. Ein endliches Strands-Nachrichtenfenster je organisatorischem Profil im
   aktuellen Prozess bewahren, damit Folgebezüge Kontext besitzen. Über **Neue
   Unterhaltung** oder `/reset` Nachrichten und unbestätigte Pläne löschen.
4. Das Modell wählt nach Bedeutung die engste verbundene Fachrolle. Es gibt
   keine Schlüsselworttabelle in der Anwendung.
5. Den gewählten Workflow gegen den expliziten Live-Katalog auflösen. Unbekannte
   oder fachrollenfremde Endpunkte werden blockiert.
6. Für lokale Suche oder ein Themendossier direkt das Nur-Lese-Werkzeug nutzen.
7. Für Facharbeit einen kurzlebigen Fachagenten mit genau einem Planungsendpunkt
   und einer optionalen reinen Stilpersona erzeugen.
8. Werkzeugereignisse, Delegation, Route, Plan-ID, Hash, Gates und Effekte zeigen.
9. `/api/v1/agent/executors` prüfen. Ein verbundener Schritt trägt eine
   typisierte, hashgebundene Ausführungshülle; ein nicht verbundener Schritt
   bleibt für die Chat-Ausführung sichtbar blockiert.
10. Einen Plan ausschließlich über die eigene hashgebundene GUI-/API-Aktion oder
   im selben CLI-Prozess über `/confirm <plan_id>` bestätigen. Normale
   Gesprächssätze bestätigen keinen Plan. Der Bestätigungsbeleg selbst weist
   die Freigabe nach, nicht die Ausführung.
11. Bei einer verbundenen Ausführungshülle den vorhandenen typisierten
    Fachworkflow ausführen und dessen eigenen maßgeblichen Ausführungsbericht
    zurückgeben. Andernfalls nur einen Übergabebeleg ohne Ausführungsbehauptung
    erzeugen.

## Abschlusskriterien

- [ ] GUI und CLI rufen denselben Master-Agentendienst auf.
- [ ] Jeder Repository-Workflow wird über genau eine Fachrolle aufgelöst.
- [ ] Fähigkeitsdatensätze enthalten keine Prompt-Schlüsselwörter oder
  Routingbegriffe.
- [ ] Personas besitzen ausschließlich `style_only`-Autorität.
- [ ] Ein Fachagent sieht nur seinen ausgewählten Planungsendpunkt.
- [ ] Chat kann nicht als Freigabe wirken.
- [ ] Die CLI bewahrt Pläne nur im aktuellen Prozess und verlangt für
  `/confirm` die exakt angezeigte Plan-ID.
- [ ] Folgekontext bleibt profilbezogen, endlich und prozesslokal; ein Reset
  entfernt sowohl Nachrichten als auch unbestätigte Pläne.
- [ ] Veraltete Plan-Hashes werden blockiert.
- [ ] Eine Chatnachricht allein schreibt nichts; eine exakte Bestätigung führt
  eine verbundene Ausführungshülle höchstens einmal aus.
- [ ] Browser und Modell besitzen weder Shell noch beliebige Pfad-, allgemeine
  Plugin- oder offene Netzwerkwerkzeuge.

## Aktuelle Umsetzungsgrenze

Der Executor-Katalog meldet 33 Workflow-Endpunkte. Ohne privates
Ressourcenregister sind persönliche Notizen, die Bestätigung einer bereits
geplanten Medikamenteneinnahme und das strikt lokale FindCall-Fixture
verbunden. Ein konfiguriertes Register ergänzt 23 typisierte Adapter für den
vollständigen lokalen Dokument- und Assistenzstack. Diese Konfiguration meldet
26 `connected`, einen `direct_read_only`, drei `planning_only` und drei
`not_connected` Endpunkte. Verbundene Endpunkte veröffentlichen dem begrenzten
Fachagenten ein geschlossenes Anfrageschema. Die verbleibenden Lücken sind Mail,
externe Kalender und Scheduler-Registrierung; jede benötigt einen ausdrücklich
konfigurierten externen Connector mit getrenntem Live-Effekt-Gate. Eine
Bestätigung kann ausschließlich eine verbundene
Ausführungshülle ausführen; maßgeblich bleiben die Fach-Ausführungsberichte.
Der verbundene FindCall-Adapter führt nach exakter Freigabe ausschließlich das
deterministische lokale Fixture aus. Der Masteragent besitzt weiterhin keinen
Live-Telefonie-Executor und kann weder anrufen noch buchen, bestellen oder
Verpflichtungen eingehen.

## Verwandte Dokumente

- [`../skills/folderhome-master-agent/SKILL.de.md`](../skills/folderhome-master-agent/SKILL.de.md)
- [`./strands-agent.de.md`](./strands-agent.de.md)
- [`./local-app.de.md`](./local-app.de.md)
- [`../SECURITY.de.md`](../SECURITY.de.md)

---
