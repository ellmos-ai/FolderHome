# Workflow: Lokale FolderHome-App starten

> **Last verified:** 2026-08-22
> **Frequency:** pro lokaler Arbeitssitzung
> **Duration:** wenige Sekunden zuzüglich der interaktiven Nutzung

## Purpose

Die gemeinsame FolderHome-Oberfläche auf genau dem aktuellen
Betriebssystemkonto starten und vorhandene Dokumentensuche sowie
Themendossiers read-only bedienen. Der Ablauf erzeugt weder eine zweite
Profil-Zugriffskontrolle noch einen allgemeinen Datei- oder Befehlszugang.

## Preconditions

- Profil- und Index-State-Verzeichnis gehören dem aktuellen OS-Konto.
- Der KnowledgeDigest-Checkout stimmt mit dem gepinnten Manifest überein.
- Der gewünschte Port ist auf `127.0.0.1` frei oder `0` wird für einen
  dynamischen Port verwendet.
- Es wird verstanden, dass Familienprofile nur organisatorisch trennen.

## Steps

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
6. **Suche oder Themendossier verwenden.** Beide Funktionen lesen nur den
   vorhandenen lokalen Index und geben keine Quellpfade aus.
7. **Server nach der Sitzung beenden.** Im startenden Terminal `Strg+C`
   drücken und prüfen, dass der Listener nicht weiterläuft.

## Exit-Criteria

- [ ] Der Preflight meldet Loopback und die OS-Kontogrenze.
- [ ] Der Server wurde nur mit explizitem Gate gestartet.
- [ ] HTML, Assets und API waren ohne gültiges Sitzungstoken blockiert.
- [ ] Die Oberfläche verwendete keine externen Ressourcen.
- [ ] Es wurden keine Dokumente, Profile oder Indexdaten verändert.
- [ ] Das Sitzungstoken wurde nicht dauerhaft gespeichert oder geteilt.
- [ ] Der lokale Listener ist nach der Nutzung beendet.

## Fallstricke

- Ein Profilwechsel ist **kein** Benutzerwechsel. Für echte Trennung ist ein
  anderes Betriebssystemkonto mit eigenen Dateirechten erforderlich.
- `localhost` ist absichtlich nicht gleichwertig zu `127.0.0.1`; der exakte
  Host-Vertrag schützt gegen uneindeutige Browser- und Proxyauflösung.
- Ein kopierter Link enthält das Sitzungstoken. Er darf den lokalen Rechner
  und die aktive Sitzung nicht verlassen.
- Schreibende oder fachlich sensible Funktionen bleiben in ihren jeweiligen
  Approval- und Gate-Workflows; die GUI umgeht sie nicht.

## Verwandte

- [`../docs/phase35-local-app-plan.md`](../docs/phase35-local-app-plan.md)
- [`../skills/folderhome-local-app/SKILL.md`](../skills/folderhome-local-app/SKILL.md)
- [`./document-library.md`](./document-library.md)
- [`./document-action-execution.md`](./document-action-execution.md)

## Historie

- **2026-08-22** — lokale API, GUI, OS-Kontogrenze und Laufzeitvertrag abgenommen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
