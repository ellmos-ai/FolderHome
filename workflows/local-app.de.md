# Workflow: Lokale FolderHome-App starten

[English](./local-app.md) | **Deutsch**

> **Zuletzt geprüft:** 2026-08-22
> **Häufigkeit:** pro lokaler Arbeitssitzung
> **Dauer:** wenige Sekunden zuzüglich der interaktiven Nutzung

## Zweck

Die gemeinsame FolderHome-Chatoberfläche auf dem aktuellen Betriebssystemkonto
starten. Die GUI ruft denselben Master-Agentendienst wie die CLI auf, zeigt
Nur-Lese-Ergebnisse, vorgeschlagene Pläne, Executor-Abdeckung und
Ausführungsberichte und trennt das Gespräch von der exakten Bestätigung. Der
Ablauf erzeugt weder eine zweite Profil-Zugriffskontrolle noch einen allgemeinen
Datei- oder Befehlszugang.

## Voraussetzungen

- Profil- und Index-State-Verzeichnis gehören dem aktuellen OS-Konto.
- Der KnowledgeDigest-Checkout stimmt mit dem gepinnten Manifest überein.
- Für chatgesteuerte persönliche Notizen stimmt der llm-note-Checkout mit
  seinem gepinnten Manifest überein und das State-Verzeichnis ist beschreibbar.
- Der gewünschte Port ist auf `127.0.0.1` frei oder `0` wird für einen
  dynamischen Port verwendet.
- Es wird verstanden, dass Familienprofile nur organisatorisch trennen.

## Schritte

1. **Preflight read-only ausführen.**

   ```powershell
   folderhome app plan --profiles-dir <profiles-dir> --state-dir <state-dir> --json
   ```

2. **Grenzen im Plan prüfen.** `security_boundary` muss
   `operating_system_account` sein; Serverstart, Shell, CORS, freie Pfade und
   externe Ressourcen müssen `false` bleiben.
3. **Loopback-Server bewusst freigeben.**

   ```powershell
   folderhome app serve --profiles-dir <profiles-dir> --state-dir <state-dir> --port 8765 --approve-loopback-server --json
   ```

4. **Nur die ausgegebene Sitzungs-URL öffnen.** Das Token ist kurzlebig und
   gehört weder in Logs noch in Nachrichten oder dauerhafte Browser-Lesezeichen.
5. **Profil organisatorisch wählen.** Die Auswahl steuert den Arbeitskontext,
   aber erteilt innerhalb des OS-Kontos keine neuen Leserechte.
6. **Mit dem FolderHome-Agenten sprechen.** Einfache Such- und Dossieranfragen
   verwenden begrenzte Nur-Lese-Werkzeuge. Folgenachrichten verwenden für das
   gewählte organisatorische Profil eine begrenzte, prozessgebundene
   Unterhaltung. Facharbeit kann einen sichtbaren Fachplan erzeugen.
7. **Bei Bedarf neu beginnen.** **Neue Unterhaltung** löscht die behaltenen
   Nachrichten dieses Profils und verwirft dessen unbestätigte Pläne samt noch
   nicht ausgeführter typisierter Hüllen. Dokumente, Indizes, abgeschlossene
   Belege und Unterhaltungen anderer Profile bleiben erhalten.
8. **Modellzustand und Executor-Abdeckung prüfen.** Das Fixture ist ausdrücklich
   kein Live-LLM. Konfiguriertes Bedrock bleibt bis zu einem erfolgreichen
   Agententurn im aktuellen Prozess unverifiziert. Ein verbundener Schritt ist
   mit **Freigeben und ausführen** gekennzeichnet. Ein fehlender Adapter ist nur
   als Übergabe markiert und darf keine Ausführung behaupten.
9. **Bewusst bestätigen.** Den Planbutton erst nach Prüfung von Plan-ID, Hash,
   exakten Schritten und möglichen Effekten verwenden. Der Beleg weist die
   Freigabe nach. Ein verbundener Schritt liefert zusätzlich einen eigenen
   Fach-Ausführungsbericht und kann nur einmal ausgeführt werden.
10. **Server nach der Sitzung beenden.** Im startenden Terminal `Strg+C`
   drücken und prüfen, dass der Listener nicht weiterläuft.

## Abschlusskriterien

- [ ] Der Preflight meldet Loopback und die OS-Kontogrenze.
- [ ] Der Server wurde nur mit explizitem Gate gestartet.
- [ ] HTML, Assets und API waren ohne gültiges Sitzungstoken blockiert.
- [ ] Die Oberfläche verwendete keine externen Ressourcen.
- [ ] Die Modellstatus-Karte stellte weder das Fixture noch unverifiziertes
  Bedrock als funktionierende Live-Modellverbindung dar.
- [ ] Chat und Bestätigung verwendeten getrennte token-geschützte API-Aktionen.
- [ ] Folgenachrichten verwendeten nur begrenzten Prozessspeicher und **Neue
  Unterhaltung** löschte den Kontext des gewählten Profils.
- [ ] Vor einer getrennten exakten Bestätigung wurde kein State verändert.
- [ ] Jeder bestätigte Schreibvorgang besitzt einen typisierten
  Fach-Ausführungsbericht und deklarierte Nebenwirkungen.
- [ ] Das Sitzungstoken wurde nicht dauerhaft gespeichert oder geteilt.
- [ ] Der lokale Listener ist nach der Nutzung beendet.

## Fallstricke

- Ein Profilwechsel ist **kein** Benutzerwechsel. Für echte Trennung ist ein
  anderes Betriebssystemkonto mit eigenen Dateirechten erforderlich.
- `localhost` ist absichtlich nicht gleichwertig zu `127.0.0.1`; der exakte
  Host-Vertrag schützt gegen uneindeutige Browser- und Proxyauflösung.
- Ein kopierter Link enthält das Sitzungstoken. Er darf den lokalen Rechner
  und die aktive Sitzung nicht verlassen.
- Eine Chatnachricht ist niemals eine Freigabe; nur die eigene hashgebundene
  Bestätigungsaktion kann eine verbundene Ausführungshülle ausführen oder einen
  Übergabebeleg erzeugen.
- Der Gesprächsverlauf ist kein dauerhafter Speicher. Er geht beim Beenden der
  App verloren, ist auf das konfigurierte Nachrichtenfenster begrenzt und
  Profile bleiben eine organisatorische Hilfe statt einer Berechtigungsgrenze.
- `not_connected` ist eine Laufzeitgrenze und kein Versprechen, dass ein
  vorhandener CLI-Workflow ausgeführt wurde.
- Schreibende oder fachlich sensible Funktionen bleiben in ihren jeweiligen
  Approval- und Gate-Workflows; die GUI umgeht sie nicht.

## Verwandte

- [`../docs/phase35-local-app-plan.md`](../docs/phase35-local-app-plan.de.md)
- [`../skills/folderhome-local-app/SKILL.md`](../skills/folderhome-local-app/SKILL.md)
- [`./document-library.md`](document-library.de.md)
- [`./document-action-execution.md`](document-action-execution.de.md)

## Historie

- **2026-08-22** — lokale API, GUI, OS-Kontogrenze und Laufzeitvertrag abgenommen
- **2026-08-22** — Executor-Katalog und erster typisierter Ausführungspfad für persönliche Notizen ergänzt
- **2026-08-22** — begrenzte prozessgebundene Unterhaltung pro Profil und ausdrückliches Zurücksetzen ergänzt

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
