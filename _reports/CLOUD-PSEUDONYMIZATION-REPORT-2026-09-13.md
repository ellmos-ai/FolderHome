# Cloud-Pseudonymisierung: Abbruchbefund vom 13. September 2026

## Ergebnis

**Status: Abbruch vor dem Umbau.** Der im Briefing vorgeschriebene Testkorridor war im unveränderten Ausgangsstand rot. Das Briefing verlangt in diesem Fall ausdrücklich „Befund statt Umbau“. Deshalb wurden weder Anwendungscode noch Tests, Frontend, README-Dateien oder `llms.txt` geändert.

Der Hackathon-Auftrag blieb auf diesen Privacy-Scope begrenzt. Es gab keine Routine-Synchronisierung, keinen Push, Merge oder Deploy und keine AWS-Mutation.

## Ausgangslage und Sperrprüfung

- Worktree: `C:\_Local_DEV\repos\folderhome-wt-privacy`
- Branch: `feature/cloud-pseudonymization`
- Ausgangscommit: `5a9575816eeefe48bcbc69d2d0076753153e0ae5`
- Fremde Sperren im Worktree, Haupt-Checkout und Hackathon-Bereich: keine gefunden
- Eigene Arbeitssperre: `LOCK.privacy.txt`, Scope `privacy`, angelegt am 13. September 2026 um 21:51:38 MESZ; sie wird nach dem lokalen Abschlusscommit wieder entfernt

## Pflicht-Baseline vor Änderungen

Ausgeführt mit dem im Briefing vorgegebenen Interpreter, `PYTHONPATH=src`, UTF-8-Ausgabe und ohne Pytest-Cache:

```powershell
C:\_Local_DEV\repos\folderhome\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider -W error -k "pseudonym or strands_agent or accident or agentcore or status or public_site"
```

Ergebnis nach 444,47 Sekunden:

```text
1 failed, 146 passed, 1673 deselected, 2 errors
```

Betroffen waren:

```text
FAILED tests/test_cli.py::test_strands_agent_cli_plans_bounded_fixture_without_model_call
ERROR tests/test_scheduler_control.py::test_preview_and_status_do_not_start_a_worker_or_modify_registration
ERROR tests/test_scheduler_control_api.py::test_api_preview_start_status_stop_and_server_close_own_real_worker
```

Eine isolierte Wiederholung genau dieser drei Fälle bestätigte den Befund in 6,82 Sekunden mit `1 failed, 2 errors`.

## Ursache

Die Fehler entstehen bereits bei der Prüfung zweier gemeinsam genutzter Provider-Checkouts. Ihre aktuellen Revisionen stimmen nicht mit den im Projekt gepinnten Revisionen überein:

| Provider | Erwartete Revision | Gefundene Revision | Folge |
|---|---|---|---|
| `KnowledgeDigest` | `7040c66aa9326975ad81c156acf0d49fd5dca60f` | `0bf36e7773fd65bfd2a8640aa9cf6875af78fd47` | CLI-Planung beendet sich mit Rückgabecode 2 |
| `ellmos-scheduler` | `d5103b9a733701f6db80dd08cfae408bf0af8ac5` | `a863b30a7ebe058903439521b96d040496a6a164` | Scheduler-Fixture bricht beim Setup ab |

Beide Provider-Checkouts waren auf `main...origin/main` ohne gemeldete lokale Änderungen. Sie wurden nur gelesen und nicht verändert. Eine Revision zurückzusetzen oder Manifest-Pins anzupassen wäre eine sachfremde Änderung außerhalb des Privacy-Auftrags.

## Nicht implementierte Zielarchitektur

Wegen des Abbruchgates wurde die im Briefing geforderte Modellgrenze nicht eingebaut. Damit gibt es in diesem Worktree weiterhin keine neue lokale Zuordnungstabelle, keine Pseudonymisierung ausgehender Modellinhalte und keine Rückauflösung eingehender Antworten oder Werkzeugargumente.

Die vorgesehenen Erkennungsklassen – unter anderem Personenname, E-Mail-Adresse, Telefonnummer, IBAN, Postanschrift, Geburtsdatum, deutsches Kennzeichen sowie `SYN-…`- und Policennummern – wurden nicht implementiert. Beispielwerte wie `lea.beispiel@example.invalid` oder `SYN-POLICE-4711` dienen daher ausdrücklich nicht als Nachweis einer vorhandenen Erkennung.

Ebenso wurde der vorgesehene Statusvertrag nicht ergänzt:

```text
FolderHomeAgentReport.pseudonymization
/api/v1/status.cloud_pseudonymization
```

Es wird folglich weder `active` noch eine Ersetzungszahl behauptet. Auch die fachliche Grenze bleibt unverändert: Mustererkennung wäre selbst nach einer Implementierung keine Anonymitätsgarantie; die beiden Cloud-Freigabegates müssten weiterhin verpflichtend bleiben.

## Commits

Es gibt keinen Implementierungscommit. Dieser Bericht und der kurze Handoff werden als benannter lokaler Befundcommit angelegt. Der Hash wird wegen der Selbstreferenz außerhalb dieses Commits im abschließenden Handoff genannt.

## Offene Punkte

1. Die zwei Provider-Checkouts müssen durch den zuständigen Owner auf die gepinnten Revisionen gebracht oder die Pins müssen in einem separat autorisierten Auftrag bewusst aktualisiert werden.
2. Danach muss der unveränderte Pflichtkorridor vollständig grün laufen.
3. Erst dann darf der Cloud-Pseudonymisierungsauftrag erneut begonnen werden: Modellgrenze, lokale Vault-Zuordnung, Hin- und Rücktausch, Statusanzeige, Dokumentation und die verlangten Tests.
4. Die Hackathon-Frist bleibt 15. September 2026, 02:00 MESZ. Dieser Befund wurde vor der Berichtsfrist am 14. September 2026, 12:00 MESZ erstellt.
