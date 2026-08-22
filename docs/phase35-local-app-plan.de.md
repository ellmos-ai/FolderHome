# Phase 35: Gemeinsame lokale API, GUI und Betriebssystemkonto-Grenze

[English](./phase35-local-app-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Zweck:** Bestehende FolderHome-Fähigkeiten über eine kleine lokale
Anwendungsgrenze bedienbar machen, ohne einen zweiten Fachkern oder eine
scheinbare Profil-Zugriffskontrolle zu bauen.

## Ist-Stand

Die Phasen 1 bis 34 besitzen bereits gemeinsame Python-Verträge und eine
umfangreiche CLI. Dokumentensuche und Themendossier verwenden den gepinnten
KnowledgeDigest-Index read-only. Familienprofile teilen laut bestehendem
Vertrag genau ein `os_account` und sind ausdrücklich nur organisatorisch.

Es gibt noch keinen gemeinsamen Server und keine visuelle Oberfläche. Die
neue Schicht soll deshalb bestehende Application-Services aufrufen und keine
Fachlogik duplizieren.

## Funktionaler Umfang

Die erste lokale Oberfläche bietet:

- Systemstatus und sichtbare Sicherheitsgrenze,
- organisatorische Profilauswahl,
- Capability-Übersicht über den vorhandenen Stack,
- natürliche lokale Dokumentensuche,
- lokales Themendossier als extraktive Fundstellenliste.

Weitere schreibende oder fachlich sensible Abläufe bleiben zunächst in ihren
vorhandenen CLI-, Approval- und Gate-Verträgen. Die API darf deren Grenzen
nicht durch einen allgemeinen Befehls- oder Pfadparameter umgehen.

## Sicherheitsvertrag

```text
explizites Server-Gate + 127.0.0.1 + konfigurierte Roots
  → aktuelles Prozesskonto erfassen
  → kurzlebiges kryptografisches Sitzungstoken erzeugen
  → URL nur an den startenden Prozess ausgeben
  → jeden HTML-/Asset-/API-Aufruf am Token prüfen
  → Host und Browser-Origin auf die konkrete Loopback-Adresse begrenzen
  → JSON-Größe, Schema, Profil-ID, Query und Limit fail-closed validieren
  → ausschließlich allowlistete read-only Handler aufrufen
  → keine CORS-Freigabe, Shell, freien Pfade oder externen Ressourcen anbieten
```

Das Sitzungstoken ist eine zusätzliche lokale Prozesshürde, aber kein zweites
Benutzer- oder Rechteverwaltungssystem. Die dauerhafte Datenisolation bleibt
Aufgabe des Betriebssystemkontos und seiner Dateirechte. Profile wie Lukas,
Hanna oder Simon ordnen Inhalte und Regeln; sie trennen keine Geheimnisse
innerhalb desselben Kontos.

## Technische Form

- Python-Standardbibliothek `ThreadingHTTPServer`, keine neue Runtimeabhängigkeit
- gebundener Host ausschließlich `127.0.0.1`; dynamischer Testport `0` erlaubt
- eine testbare `LocalApplication` zwischen HTTP und vorhandenen Services
- paketierte statische HTML-/CSS-/JS-Dateien ohne CDN oder Telemetrie
- Content-Security-Policy, `no-store`, `nosniff`, Frame- und Referrer-Schutz
- `app plan` für read-only Preflight und `app serve` hinter explizitem Gate

## Visuelle Richtung

**Gegenstand:** private Dokumentarbeit für Menschen, die nicht erst ein
Dokumentenmanagementsystem lernen möchten. **Einzige Hauptaufgabe:** einen
bekannten lokalen Bestand verständlich durchsuchen oder zu einem Thema
bündeln.

- **Farben:** Desktopgrau `#edf2f5`, Papierweiß `#fbfdfe`, Tinte `#152638`,
  Aktenschrankblau `#194d68`, Ordnertürkis `#25796d` und Ablagegelb `#f2b84b`.
- **Typografie:** `Bahnschrift`/`Aptos Display` für prägnante Überschriften,
  `Segoe UI` für ruhigen Lesetext und eine Monospace-Schrift für technische
  Statuslabels.
- **Layout:** großzügiger Kopf, darunter ein einziger aktiver Arbeitsordner;
  die Fähigkeiten stehen wie geordnete Registerkarten im unteren Raster.
- **Signatur:** Die gelbe Lasche „Aktiver Arbeitsordner“ verbindet die
  physische Alltagserfahrung einer Ablage mit der lokalen digitalen Suche.

Die erste Creme-/Serifenrichtung wurde verworfen, weil sie austauschbar wirkte
und den funktionalen Dokumentgegenstand nicht sichtbar machte. Bewegung bleibt
auf einen kurzen Ergebniszustand begrenzt und respektiert
`prefers-reduced-motion`.

## Abnahmekriterien

- Nicht-Loopback-Bindung blockiert vor dem Start.
- Ohne explizites Server-Gate wird kein Listener erzeugt.
- Fehlendes/falsches Token, falscher Host und fremder Origin blockieren.
- Requests können keine Dateipfade oder Befehle einschleusen.
- Nur bekannte Profile desselben OS-Konto-Vertrags werden akzeptiert.
- Suche und Dossier verwenden den vorhandenen Search-Service.
- Die GUI funktioniert ohne externe Assets und ist tastatur-/mobil nutzbar.
- API und GUI verändern keine Dokumente und schreiben keinen State.
- Ein echter Loopback-End-to-End-Test belegt Status, Suche und Schutzheader.

## Abnahmenachweis

- `297 passed in 89.60s` im vollständigen FolderHome-Testlauf
- Ruff über `src` und `tests` ohne Befund; `compileall` ohne Fehler
- Realer temporärer Index mit zwei synthetischen Dokumenten, davon eine
  Krankenversicherungsfundstelle im GUI-Lauf
- Desktop-Viewport `1440 × 1100` und Mobil-Viewport `390 × 844` mit
  `scrollWidth == innerWidth`
- In beiden Viewports: eine Fundstelle, Profil `lukas`, Fokus zurück auf der
  Suchaktion, `aria-busy=false`, keine Konsolenfehler und keine HTTP-Fehler
- Abnahmelistener nach dem Lauf verifiziert beendet
- Isolierter Wheel-Build `folderhome-0.1.0-py3-none-any.whl`; alle vier
  GUI-Assets (`index.html`, `app.css`, `app.js`, `favicon.svg`) in der
  Paketdatei zurückgelesen

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
