# Cloud-Pseudonymisierung: Abschlussbericht vom 13. September 2026

## Ergebnis

**Status: vollständig umgesetzt und im vereinbarten Testkorridor grün.** Jeder Modelltransport, der laut `StrandsAgentSettings.network_used` die Maschine verlässt, wird standardmäßig an einer gemeinsamen Modellgrenze pseudonymisiert. Antworten und Werkzeugargumente werden vor der lokalen Weiterverarbeitung wieder zurückgetauscht. Fixture und Loopback-Ollama bleiben unverändert.

Die Pseudonymisierung ist ein zusätzliches Zwischen-Gate. Sie ersetzt weder `--allow-network` noch `--approve-sensitive-cloud-data` und behauptet keine Anonymität. Der Nutzer kann sie mit `--cloud-pseudonymization off` oder dem gleichnamigen Feld in `launch.json` bewusst deaktivieren; Remote-Betrieb zeigt dann eine Klartextwarnung.

Der Hackathon-Auftrag blieb auf diesen Privacy-Scope begrenzt. Es gab keine Routine-Synchronisierung, keinen Push, Merge oder Deploy und keine AWS-Mutation.

## Architektur und Datenfluss

Der zentrale Einbaupunkt ist `src/folderhome/application/pseudonymization.py`:

- `PseudonymVault` hält die Zuordnung Original ↔ Platzhalter ausschließlich im laufenden lokalen Prozess. In der App besitzt jedes Profil eine sitzungsstabile Vault; ein Gesprächsreset verwirft sie. Einmalige Agent-Aufrufe erhalten eine eigene Vault.
- `PseudonymizingModel` dekoriert das jeweilige Strands-Modell. `_build_model` wendet den Wrapper auf Bedrock, Anthropic, OpenAI und Ollama an einem fremden Host an, sofern der Schalter auf `on` steht. Fixture und Loopback-Ollama werden nicht gewrappt.
- Hauptagent und Spezialist verwenden innerhalb eines Durchlaufs dieselbe Vault. Ein direkt aufgerufener Spezialist initialisiert seine eigene Vault.
- Bekannte Werte werden über die vorhandenen Profil-, Kontaktregister- und Dokumentkatalog-Dienste geladen; es gibt keinen neuen Dateiscan. Ist dieses lokale Laden nicht sicher möglich, wird der Remote-Chat mit Status `unavailable` blockiert.

Hinweg zum Remote-Modell:

1. Bekannte Werte und Mustertreffer werden zunächst auf dem vollständigen Originaltext gesammelt.
2. Längste, nicht überlappende Treffer werden ausgewählt; bei gleicher Spanne gewinnt der bekannte Wert.
3. Nutzertext, Verlauf, System-Prompt, System-Prompt-Inhalte und Werkzeugergebnisse werden rekursiv verarbeitet.
4. Das Remote-Modell erhält nur Platzhalter wie `⟨PERSON_1⟩` oder `⟨EMAIL_1⟩`; die lokale Zuordnung wird nicht in den Payload aufgenommen.

Rückweg in die lokale Anwendung:

1. Text-Deltas und über mehrere Deltas verteilte Werkzeugargumente werden vollständig gepuffert.
2. Antworttext sowie JSON-Werte und -Schlüssel der Werkzeugargumente werden zurückgetauscht.
3. Auch veränderte Schreibweisen wie `PERSON_1`, `[PERSON_1]` und `<PERSON_1>` werden tolerant erkannt.
4. Lokale Werkzeuge und dadurch erzeugte `proposed_plans` arbeiten wieder mit den ursprünglichen lokalen Werten.

`count_tokens()` und `structured_output()` verwenden dieselbe Grenze. Report und Status enthalten nur Aktivitätszustand und Zähler, niemals die Zuordnungstabelle.

## Erkannte Klassen

Bekannte lokale Werte werden zuerst berücksichtigt:

- Profil-Anzeigenamen und ihre Namensteile, zum Beispiel `Lea Beispiel`
- Kontaktnamen, E-Mail-Adressen und Telefonnummern
- Dokument-IDs, zum Beispiel `doc_` gefolgt von einem 64-stelligen Hash
- Versicherungs-, Policen- und Vertragsnummern aus dem Dokumentkatalog
- Name des Betriebssystemkontos

Danach greifen vorsichtige Muster für:

| Klasse | Synthetisches Beispiel | Platzhalter |
|---|---|---|
| Person | `Lea Beispiel` | `⟨PERSON_1⟩` |
| E-Mail | `lea.beispiel@example.invalid` | `⟨EMAIL_1⟩` |
| Telefon, deutsch/international | `+49 30 12345678` | `⟨PHONE_1⟩` |
| IBAN | `DE89 3704 0044 0532 0130 00` | `⟨IBAN_1⟩` |
| Postanschrift | `Musterstraße 12, 10115 Berlin` | `⟨ADDRESS_1⟩` |
| Geburtsdatum im Kontext | `geboren am 01.02.1990` | Kontext plus `⟨ID_1⟩` |
| deutsches Kennzeichen | `B-AB 1234` | `⟨ID_2⟩` |
| synthetische/vertragliche ID | `SYN-POLICE-4711` | `⟨ID_3⟩` |
| Dokument-ID | `doc_0123…` | `⟨DOC_1⟩` |

Ein Original erhält während derselben Sitzung stabil denselben Platzhalter. Der Zähler `replacements` bezeichnet die Zahl unterschiedlicher, im letzten Durchlauf verwendeter Platzhalter; `kinds` gruppiert diese Zahl nach Klasse.

## Schalter

Der Vertrag lautet:

```text
StrandsAgentSettings.cloud_pseudonymization: Literal["on", "off"] = "on"
```

- CLI: `--cloud-pseudonymization on|off` ist für die gemeinsamen Agent-/App-Argumente verfügbar.
- Launch-Konfiguration: `cloud_pseudonymization` wird geladen, validiert und bei fehlendem Feld als `on` behandelt. Das Setup erhält oder schreibt diesen Wert in `launch.json`.
- `off` hat bei Fixture und Loopback keine zusätzliche Wirkung. Bei einem Remote-Provider deaktiviert es den Wrapper, setzt den Status auf `off` und gibt im lokalen Startprotokoll sowie Status die Warnung aus: `Cloud pseudonymization OFF: names, contacts and identifiers leave this machine in clear text`.
- Eine Änderung über `launch.json` wird nach einem Neustart wirksam. Ein neuer Laufzeit-Reload-Endpunkt wurde nicht erfunden.
- Die beiden bestehenden Remote-Freigabegates bleiben unabhängig vom Schalter zwingend.

## Statusvertrag und Oberfläche

`FolderHomeAgentReport.pseudonymization` liefert:

```json
{
  "active": true,
  "replacements": 3,
  "kinds": {"PERSON": 1, "EMAIL": 1, "ID": 1}
}
```

Die Werte sind reine Zähler. Originale oder Zuordnungen werden dort nicht ausgegeben.

`GET /api/v1/status` ergänzt:

- `cloud_pseudonymization`: `active`, `not_needed_local`, `unavailable` oder `off`
- `cloud_pseudonymization_replacements`: Anzahl unterschiedlicher Werte im letzten Durchlauf
- `cloud_pseudonymization_kinds`: Zähler je Klasse
- `cloud_pseudonymization_warning`: nur bei bewusst deaktivierter Remote-Pseudonymisierung

Die EN/DE-Weboberfläche zeigt unter dem bestehenden Modellstatus genau eine zusätzliche Zeile. `active` wird türkis dargestellt; `off` und `unavailable` erscheinen als Warnzustand. Der letzte Agent-Report aktualisiert dort den Durchlaufzähler ohne Layoutumbau.

README EN/DE, Root- und Site-`llms.txt` sowie der Kommentar im Contract Cockpit wurden an denselben Vertrag angepasst. Beide `llms.txt`-Dateien sind bytegleich.

## Cloud-Demo und AgentCore

Die AgentCore-Unfallreise bleibt synthetisch und deterministisch. Der Remote-Bedrock-Pfad wurde im Test mit einem Offline-Modellstub durch die echte `_build_model`-Grenze geführt. Dabei war `PseudonymizingModel` tatsächlich aktiv; der Standardprompt erzeugte weiterhin den unveränderten Vier-Schritt-Plan und nach genauer Bestätigung vier lokale Ergebnisdateien. Es wurde kein AWS-Endpunkt aufgerufen und keine Cloud-Ressource verändert.

## Pflicht-Baseline vor dem Umbau

Der frühere Abbruchbericht im Commit `a8b22fa` ermittelte im unveränderten Ausgangsstand:

```text
1 failed, 146 passed, 1673 deselected, 2 errors in 444.47s
```

Eine isolierte Wiederholung bestätigte `1 failed, 2 errors in 6.82s`:

```text
FAILED tests/test_cli.py::test_strands_agent_cli_plans_bounded_fixture_without_model_call
ERROR tests/test_scheduler_control.py::test_preview_and_status_do_not_start_a_worker_or_modify_registration
ERROR tests/test_scheduler_control_api.py::test_api_preview_start_status_stop_and_server_close_own_real_worker
```

Der Nutzer hat diese drei Fälle geprüft und das Abbruchgate ausdrücklich als erfüllt erklärt:

- Der CLI-Test startet einen Subprozess über den Editable-Install, der auf `C:\_Local_DEV\repos\folderhome-main` statt auf diesen Worktree zeigt. Das ist kein Fehler des hier geprüften Codes.
- Die beiden `test_scheduler_control*`-Fehler stammen aus dem bekannten Provider-Checkout-Drift von `ellmos-scheduler`, dokumentiert in Ticket `T-20260913-610233740`.

Die Provider-Checkouts wurden in diesem Auftrag nicht verändert. Der nun verlangte Korridor des Nutzers selektiert den CLI-Fall ab und ignoriert die beiden Scheduler-Testmodule ausdrücklich.

Eine zusätzliche orientierende Ausführung von `tests/test_public_site.py tests/test_setup_app.py` ergab `119 passed, 1 failed`; der einzelne Test `test_saved_launch_config_drives_the_app_plan_command` traf ebenfalls den externen `KnowledgeDigest`-Checkout-Drift. Er liegt außerhalb des vereinbarten Korridors und ist kein Produktfehler dieses Umbaus.

## Verifikation nach dem Umbau

Ausgeführt im Worktree mit `C:\_Local_DEV\repos\folderhome\.venv\Scripts\python.exe`, dem in `pyproject.toml` gesetzten `pythonpath = ["src"]`, ohne Pytest-Cache und mit Warnungen als Fehler:

```powershell
python -m pytest tests -q -p no:cacheprovider -W error `
  -k 'pseudonym or strands_agent or accident or agentcore or status or public_site' `
  --deselect tests/test_cli.py::test_strands_agent_cli_plans_bounded_fixture_without_model_call `
  --ignore=tests/test_scheduler_control.py `
  --ignore=tests/test_scheduler_control_api.py
```

Ergebnis des finalen Projektinterpreter-Laufs:

```text
160 passed, 1650 deselected in 447.64s (0:07:27)
```

Zusätzliche Nachweise:

- `tests/test_pseudonymization.py`: `12 passed`
- AgentCore-Remote-Grenztest mit Offline-Bedrock-Stub: `1 passed`
- Strands-Agent-Tests im unabhängigen Retest: `25 passed`
- Status-Fokus: `25 passed, 23 deselected`
- Web-/Setup-JavaScript: `103 passed, 0 failed`
- Ruff auf allen geänderten Python-Dateien und Tests: `All checks passed!`
- `py_compile` auf allen geänderten Python-Produktdateien: Exit-Code 0
- Root-/Site-`llms.txt`: bytegleich
- Deutsch/Englisch: echte deutsche Umlaute vorhanden; keine Mojibake-Marker gefunden

Der unabhängige Read-only-Retest fand zunächst Abdeckungslücken für Überlappung von Kontoname und E-Mail, internationale Telefonnummern, Werkzeug-JSON-Schlüssel, `count_tokens`, `structured_output` und die echte AgentCore-Remote-Grenze. Diese Punkte wurden vor dem finalen Lauf geschlossen. Der abschließende Re-Review meldete keine blockierenden Code- oder Security-Findings.

## Grenzen und offene Punkte

1. Mustererkennung ist keine Garantie. Unbekannte Namen, ungewöhnliche Schreibweisen und neue Identifikatorformate können Freitext passieren. Der Status heißt deshalb bewusst `active`, nicht `anonymous`.
2. Falsch-positive Mustertreffer sind möglich. Der Rücktausch schützt die lokale Funktion, ersetzt aber keine Datenminimierung vor einer Remote-Freigabe.
3. Die Zuordnung ist absichtlich pro Prozess beziehungsweise Profilsitzung. Ein Neustart oder Gesprächsreset erzeugt neue Platzhalter.
4. Die zwei bestehenden Remote-Gates bleiben Pflicht, auch wenn die Pseudonymisierung aktiv ist.
5. Der sichtbare Schalter in Setup-Karte 3 bleibt entsprechend dem Addendum außerhalb dieses Auftrags und muss vom zuständigen Gemini-Worker ergänzt werden. Die Setup-Anwendungslogik erhält und validiert das `launch.json`-Feld bereits.
6. Es gab keinen Live-Aufruf eines externen Modells. Die Transportgrenze wurde mit deterministischen Offline-Stubs geprüft; damit ist die Datenflusslogik verifiziert, nicht die Verfügbarkeit eines konkreten Cloud-Anbieters.

## Commits

- `a8b22fa` — `docs(privacy): record blocked pseudonymization baseline`
- `26d9a72` — `feat(privacy):pseudonymize-remote-model-traffic`
- Abschlussbericht und Kurz-Handoff folgen in einem separaten lokalen Dokumentationscommit; dessen Hash steht wegen der Selbstreferenz in der äußeren Abschlussmeldung.
