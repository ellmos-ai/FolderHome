# Fähigkeitsrezepte — ganze Abläufe und getrennt freigegebene Abschnitte

[English](./capability-recipes.md) | **Deutsch**

> **Last verified:** 2026-09-09

## Warum es Rezepte gibt

Eine echte Alltagsaufgabe ist selten ein einzelner Endpunkt. Nach einem
Autounfall braucht man den zuständigen Kontakt, ein Schadensschreiben, dieses
Schreiben im eigenen Entwurfsordner und den Folgetermin im Kalender. Vor den
Rezepten konnte FolderHome alle vier Dinge — aber man musste viermal fragen und
viermal bestätigen, und nichts stellte sicher, dass Schritt drei dasselbe
Schreiben verwendet wie Schritt zwei.

Ein Rezept ist diese Geschichte, aufgeschrieben. Bei v1 löst der Master sie in
**einen** Plan mit mehreren geordneten Schritten auf; die ganze Kette wird einmal
bestätigt. Ergebnisgebundene v2-Rezepte brauchen **eine eigene Freigabe für jeden
konkreten Abschnitt**. Der mitgelieferte Katalog enthält bisher v1-Rezepte;
Anwendung und Sitzungs-CLI unterstützen auch ergebnisgebundene v2-Rezepte.

## Was ein Rezept nicht ist

Ein Rezept verleiht keine neue Fähigkeit. Jeder Schritt ist ein vorhandener
typisierter Endpunkt mit eigenem Adapter, eigenem Anfrageschema und eigenen
Gates. Wenn `mail-connector` die Freigabe `--approve-mail-draft` braucht, dann
braucht er sie auch im Rezept. Ist ein Endpunkt in der eigenen Installation
nicht verbunden, scheitert das Rezept fail-closed, statt den Schritt still zu
überspringen.

## Die drei Regeln, die das sicher halten

**Ein Endpunkt, ein Eigentümer.** Jeder Schritt deklariert die Fachrolle, zu der
er gehört, und die Abnahme weist das Rezept zurück, wenn der Fähigkeitskatalog
widerspricht. Ein Rezept darf deshalb mehrere Domänen umspannen, ohne die Regel
aufzuweichen, dass ein Endpunkt nur von seiner eigenen Fachrolle genutzt werden
darf — die Regel wird lediglich pro Schritt geprüft statt einmal pro Plan.

**Bei v1 fließen Daten nur als logische Ressourcen-IDs.** Eine Übergabekante
deklariert, dass ein benanntes Feld eines früheren und ein benanntes Feld eines
späteren Schrittes dieselbe logische Ressource bezeichnen müssen: einen Speicher,
den ein Schritt schreibt und ein späterer liest, oder eine Quelle, auf die sich
beide einigen müssen. Kein Wert aus einem Schrittbericht wird jemals in eine
spätere Anfrage eingesetzt. Jede Anfrage ist damit vollständig, bevor irgendetwas
läuft — genau das macht einen einzigen Hash über die ganze Kette möglich.

**Die Abnahme ist Teil der Bestätigung.** Bevor der Plan sichtbar wird, läuft
eine deterministische Prüfung:

| Prüfung | Weist zurück, wenn |
| --- | --- |
| `endpoint_owned_by_declared_expert` | das Rezept die falsche Fachrolle für einen Endpunkt nennt |
| `endpoint_connected_at_runtime` | ein Endpunkt in dieser Installation nicht verbunden ist |
| `side_effects_have_approval_gates` | ein Schritt wirkt, aber kein Gate nennt |
| `referenced_resources_are_registered` | eine Anfrage eine Ressource nennt, die das Register nicht kennt |
| `handoffs_bind_the_same_logical_resource` | eine Übergabekante zwei verschiedene Ressourcen verbindet |

Jede beteiligte Fachrolle zeichnet das Ergebnis: eine bei einem Rezept aus einer
Domäne, alle bei einem domänenübergreifenden Rezept. Die Abnahme geht in den
Planhash ein; wer den Plan bestätigt, bestätigt die Abnahme mit.

## Planintegrität

Bei der Bestätigung wird der Hash aus dem aktuellen Planinhalt neu berechnet;
übereinstimmende gespeicherte Hashwerte reichen nicht aus. Der Hash umfasst das
vollständige öffentliche Masterplan-Objekt außer `plan_id` und `plan_sha256`,
kodiert als UTF-8-JSON mit sortierten Schlüsseln, ohne zusätzliche Leerzeichen
und ohne nichtendliche Zahlen. `approval_context` enthält Rezept-ID und
Rezepthash, Übergabekanten, Abnahme und geordnete Schrittverweise.

Die App prüft diese Bindung vor Annahme der Freigabe, die Kette erneut vor jedem
Schritt. Veränderte Inhalte stoppen den nächsten Schritt; bereits ausgeführte
Wirkungen und ihre Berichte bleiben erhalten. Verschachtelte Anfrage-, Plan- und
Berichtsdaten werden an ihren Eingabe-/Exportgrenzen kopiert. Ein exportiertes
Objekt lässt sich dadurch bearbeiten, ohne seine Quelle still zu verändern.
Das ist eine Integritätsprüfung, keine zusätzliche Sicherheitsgrenze gegenüber
Code unter demselben Betriebssystemkonto.

Pläne nach der älteren Hashformel müssen nach dem Update neu vorgeschlagen und
geprüft werden. Sie werden weder still umgerechnet noch unter dem neuen Hash
freigegeben.

Ein Ausführungsbericht muss außerdem zur angeforderten Hülle, zum Workflow und
zum Adapter gehören. Ein fremder Bericht wird weder gespeichert noch diesem
Schritt als Erfolg zugerechnet; die Kette stoppt. Die lokale API kennzeichnet
diesen Fall mit `execution_outcome_unknown: true` und
`result_delivery_incomplete: true`. `execution_performed` zählt nur verifizierte
Berichte: Bei unklarem Ergebnis beweist `false` **nicht**, dass nichts gewirkt hat.
Vor einem manuellen Wiederholungsversuch den tatsächlichen Fachzustand prüfen;
der aktuelle Rezeptversuch lässt sich nicht erneut starten.

## In App und Chat

Ein organisatorisches Profil und darunter eine **Mehrschritt-Aufgabe** auswählen.
**Gesamte Aufgabe vorbereiten** erzeugt nur einen Vorschlag. Die vorbereiteten
Schritte und ihre genauen Fachpläne prüfen und anschließend getrennt
**Freigeben und ausführen** wählen. Eine nicht verfügbare Aufgabe bleibt sichtbar,
kann aber nicht über die Auswahl vorbereitet werden. Die Ressourcen-IDs des
mitgelieferten Rezepts müssen für dieses Profil eingerichtet sein; die App
erfindet keine Bindungen und umgeht keine Freigabe einzelner Adapter.

Der Strands-Master kann außerdem `list_home_recipes` und `propose_home_recipe`
nutzen. Diese Werkzeuge listen oder planen nur; keines kann bestätigen oder
ausführen. Die Auswahl durch ein Live-Modell hängt weiterhin vom Modell ab;
deterministische Tests belegen die Werkzeuganbindung, nicht die Qualität der
Live-Modell-Auswahl. Die Rezeptprüfung ist ein **deterministischer Katalog- und
Ressourcenabgleich**, keine unabhängige Prüfung durch Menschen oder Modelle.

Die authentifizierte lokale API bietet:

- `GET /api/v1/agent/recipes?profile_id=lukas&language=en`
- `POST /api/v1/agent/recipes/plan` mit Schema
  `folderhome.local-recipe-plan-request.v1`, `profile_id`, `recipe_id` und `language`.
- `POST /api/v1/agent/confirm` mit zurückgegebener Plan-ID, genauem Hash und **allen** Schritt-IDs.

Pläne liegen nur im laufenden Prozess. Ein Gesprächsreset entfernt unbestätigte
Pläne; gleichzeitige oder wiederholte Bestätigungen starten keine Kette erneut.
Eine gescheiterte Kette erhält die Berichte abgeschlossener Schritte, stoppt den
Rest und macht andere Vorschläge mit denselben Ausführungshüllen ungültig.
Schrittübergreifendes Zurückrollen gibt es nicht. Adapter-Fehlerdetails werden an
dieser API-Grenze redigiert. Eine neue App-Sitzung ersetzt nicht die dauerhaften
Idempotenzprüfungen der einzelnen Adapter.

Die lokale Adapterintegration ist mit synthetischen Daten und synthetischem
Mailtransport getestet, einschließlich fehlender Mailfreigabe. Browser-Klickabnahme
und echte Postfach-/Kalendereffekte sind getrennte Prüfungen und dadurch nicht belegt.

## Eines über die CLI ausführen

```powershell
$env:PYTHONPATH = "src"
python -m folderhome recipes list --json

python -m folderhome recipes plan `
  --profiles-dir examples\profiles --state-dir .local-state `
  --resources-file $env:LOCALAPPDATA\FolderHome\resources.json `
  --profile-id lukas --recipe-id accident-aftercare --json
```

Der Plan gibt seinen eigenen Bestätigungsbefehl aus. Wer ihn zurückgibt, führt
die Kette der Reihe nach aus:

```powershell
python -m folderhome recipes run `
  --profiles-dir examples\profiles --state-dir .local-state `
  --resources-file $env:LOCALAPPDATA\FolderHome\resources.json `
  --profile-id lukas --recipe-id accident-aftercare `
  --approve-mail-draft `
  --confirm plan_<id> --approved-at 2026-08-25T09:05:00+02:00 --json
```

Ein v1-Rezeptplan ist deterministisch: Gleiche Eingaben und gleicher Fachzustand
ergeben mit demselben Code dieselbe Plan-ID. Genau das erlaubt einer zustandslosen
Kommandozeile, einen zuvor
ausgegebenen Plan zu bestätigen, ohne eine Sitzung offen zu halten.

Für getrennt freigegebene Abschnitte bleibt ein Prozess geöffnet. Verwende das
vorhandene Profil, Ressourcenregister und Zustandsverzeichnis aus der Einrichtung;
`--state-dir` muss bereits existieren:

```powershell
python -m folderhome agent session `
  --profiles-dir examples\profiles --state-dir .local-state `
  --resources-file $env:LOCALAPPDATA\FolderHome\resources.json `
  --profile-id lukas --model-provider fixture --language de --json
```

Direkte Rezeptbefehle rufen kein Modell auf. Die vom jeweiligen Rezept benötigten
Adapterschreibfreigaben bleiben erforderlich; dieses Beispiel erteilt keine.

| Sitzungsbefehl | Bedeutung |
| --- | --- |
| `/recipes` | Rezepte und Verfügbarkeit dieses Profils anzeigen |
| `/recipe <recipe_id>` | v1-Ablauf oder ersten v2-Abschnitt vorbereiten |
| `/confirm <plan_id>` | Genau den angezeigten Plan einmal ausführen |
| `/runs` | Prozesslokale Läufe, bestätigte Schritte und Status anzeigen |
| `/next <run_id>` | Offenen oder nächsten konkreten Abschnitt prüfen; keine Ausführung |
| `/close <run_id>` | Offene Abschnitte verwerfen, bestätigte Wirkungen bleiben bestehen |
| `/reset`, `/quit` | Profil zurücksetzen oder Sitzung samt offenen Läufen schließen |

Der Textmodus (ohne `--json`) zeigt vor dem Bestätigungsbefehl den vollständigen
öffentlichen Plan einschließlich Fachwerten und Ergebnisherkunft. Der JSON-Modus
liefert ein Ereignis je Zeile. Ein erfolgreicher Abschnitt kann den Lauf `ready`
statt `completed` hinterlassen: Mit `/next` den neuen Plan prüfen und separat
mit `/confirm` freigeben. Auch EOF und Strg+C während der Eingabewartezeit schließen
die Sitzung. Die Bereinigung läuft selbst bei Ausgabefehlern; ein Bereinigungsfehler
darf nicht als erfolgreich geschlossene Sitzung erscheinen.

`recipes plan|run` bleibt die zustandslose v1-Schnittstelle. V2-Läufe lassen sich
nicht durch Import eines gespeicherten JSON-Berichts in einem neuen Prozess fortsetzen.

## Wenn ein Schritt scheitert

Ungültige Planintegrität vor dem Kettenstart wird ohne Ausführung abgelehnt.
Nach dem Start hält die Kette beim ersten Fehler an. Ein Bericht wird zurückgegeben
statt
geworfen, denn wer nur eine Ausnahme sähe, wüsste nicht, was bereits gewirkt hat.
Er benennt drei Gruppen ausdrücklich:

- `executed_step_refs` — diese liefen, ihre Wirkung bleibt bestehen
- `failed_step_refs` — genau ein Schritt, mit Adapter- oder Integritätsfehler
- `not_attempted_step_refs` — alles danach, unberührt

Über Schrittgrenzen hinweg wird nichts zurückgenommen: Jeder Adapter behält
seine eigene Atomizitätsgarantie, und ein abgeschlossener Schritt bleibt
abgeschlossen. Der Bericht sagt genau, wo fortzusetzen ist.

## Grenzen von Rezepten mit einer Bestätigung

Übergabekanten binden Ressourcen, keine Werte. Ein v1-Rezept kann keinen Wert
aus dem Bericht eines Schrittes in die Anfrage des nächsten setzen — das würde
verlangen, Anfragen erst während der Ausführung aufzulösen, und würde den einen
Hash über die Kette brechen. Bestehende Ressourcenübergaben bleiben unverändert;
Ergebnisfelder verwenden ein eigenes versioniertes Format.

## Ergebnisübergaben: v2-Laufzeit, API, Chat und GUI

Der Parser erkennt zusätzlich `folderhome.capability-recipe.v2` mit einer
expliziten Liste `result_bindings`. Jede Übergabe nennt einen früheren
`from_step`, einen späteren `to_step`, einen wörtlichen `source_path`
(JSON-Schlüssel und nichtnegative Listenindizes), ein oberstes Anfragefeld
`target_field` und einen `value_type`:
`string`, `integer`, `number`, `boolean`, `object`, `array` oder `null`.

Übergaben dürfen weder statische Anfragewerte noch andere Übergaben
überschreiben. Reservierte Berechtigungsfelder, darunter Profile, Konten,
Ressourcen und Freigaben, sind als Ergebnisziele ausgeschlossen. Der spätere
Zieladapter muss zusätzlich die vollständig aufgelöste Anfrage prüfen;
die Formatprüfung erlaubt für sich weder ein Feld noch eine Operation.

Die Wertauswahl wandelt nichts um: `false` ist keine Ganzzahl, fehlende Daten
sind nicht `null`, und nichtendliche Zahlen werden abgelehnt. Ausgewählte Werte
sind unabhängige Kopien, begrenzt auf 64 KiB UTF-8-JSON, 16 Verschachtelungsebenen
und 4.096 besuchte Knoten einschließlich Objektschlüsseln. Pfade haben höchstens
acht Segmente; v2-Rezepte höchstens 32 Schritte und 32 Übergaben.

Der bisherige Planer mit einer Bestätigung lehnt v2 vor jeder Adaptervorbereitung
ab. Die getrennte Python-Laufzeit `create_recipe_run()` führt v2 jetzt in
Abschnitten aus:

1. `plan_next()` bereitet nur die nächsten zusammenhängenden Schritte vor, deren
   Eingabewerte bereits bekannt sind. Ein innerhalb dieses Abschnitts erzeugtes
   Ergebnis steht erst für einen späteren Abschnitt bereit.
2. `confirm()` verlangt die exakte Freigabe dieses Abschnitts und verbraucht sie
   vor dem Adapteraufruf. Passende Ausführungsberichte bleiben erhalten; Fehler
   oder unklare Wirkungen stoppen die Kette. Der nächste Abschnitt wird weder
   automatisch geplant noch ausgeführt.
3. Ein weiterer Aufruf von `plan_next()` löst Ergebnisfelder aus gespeicherten
   Berichten desselben Laufs auf. Der neue Plan bindet Lauf, Profil, Rezept,
   vorherige Pläne, Berichtsherkunft und ausgewählte Werte. Rohe Anfragen werden
   gehasht, nicht entgegen einer absichtlichen Adapterredaktion erneut offengelegt.
   Der neue Plan benötigt eine eigene Freigabe.

Jeder Lauf hat einen unabhängigen Vorbereitungsspeicher und nutzt die
konfigurierten Fachadapter. Das Schließen eines Laufs kann identische Hüllen
eines anderen Laufs nicht verwerfen. Dauerhafte Idempotenz, Ressourcenprüfungen
und Effektfreigaben der Adapter gelten weiter. Gescheiterte Bereinigung behält
ihre Ziele für einen weiteren `close()`-Versuch; sie erlaubt keine Wiederholung
unklarer Wirkungen. Zustandsansichten sind unabhängige Kopien.

Diese Python-Laufzeit wurde mit dem echten lokalen Notizadapter geprüft:
Notiz anlegen, bestätigte ID und Revision in eine Änderung übernehmen und
Revision 2 getrennt freigeben. Kein Netzwerk oder externer Abgleich ist beteiligt.

Die normale Anwendung verarbeitet ein paketiertes v2-Rezept jetzt über dieselben
Grenzen `POST /api/v1/agent/recipes/plan` und die exakte Bestätigung
`POST /api/v1/agent/confirm`. Ein Abschnittsvorschlag verwendet
`folderhome.recipe-stage-plan.v1`, enthält seinen Zustand `run` und gibt nur den
zurückgegebenen Plan frei. Katalogeinträge nennen
`approval_mode: per_section` oder `whole_chain`.

| Aktion | Authentifizierter Endpunkt / Anfrage |
| --- | --- |
| Läufe dieses Profils anzeigen | `GET /api/v1/agent/recipes/runs?profile_id=lukas` |
| Nächsten Abschnitt vorbereiten | `POST /api/v1/agent/recipes/next`; Schema `folderhome.local-recipe-next-request.v1`, `profile_id`, `run_id` |
| Lauf ohne Rücknahme schließen | `POST /api/v1/agent/recipes/close`; Schema `folderhome.local-recipe-close-request.v1`, `profile_id`, `run_id` |

Die Strands-Werkzeuge `list_home_recipe_runs` und `propose_next_recipe_stage`
nutzen denselben prozesslokalen Zustand. Sie geben niemals Wirkungen frei.
Die Bestätigung liefert `recipe_run` und die tatsächlichen Abschnittsergebnisse
in `recipe_execution`. Erfolgreiche Berichte und ausdrücklich unsichere
Providerbelege erscheinen auch in der normalen Ergebnisliste. Scheitert die
zusätzliche Ergebnisablage, bleiben Wiederholungswarnung und
`result_delivery_incomplete` erhalten; das darf nicht wie eine unversuchte Aktion wirken.

Höchstens 128 Läufe werden behalten. Alte Läufe schließen, um Platz freizugeben.
Reset, Planverdrängung und App-Ende verwerfen betroffene offene Abschnitte, nicht
abgeschlossene Wirkungen. Gescheiterte Bereinigung bleibt für einen ausdrücklichen
Schließversuch erreichbar. Ein Bereinigungsfehler verhindert nicht den Stopp
des eigenen Scheduler-Consumers.
Scheitert ein Modellturn beim Vorschlagen eines Folgeabschnitts, wird nur dieser
unversuchte Vorschlag verworfen. Bestätigte Quellberichte bleiben im selben Lauf;
der Abschnitt lässt sich ohne Wiederholung früherer Wirkungen neu vorbereiten.

Der GUI-Bereich **Begonnene Abläufe** zeigt die Läufe des gewählten Profils,
bestätigte Schritte und den aktuellen Zustand. **Nächsten Abschnitt vorbereiten**
schlägt nur den nächsten konkreten Abschnitt vor; **Offenen Abschnitt prüfen**
öffnet einen bestehenden Vorschlag erneut. **Ablauf schließen** verwirft die
offene Vorbereitung, ohne frühere Wirkungen zurückzunehmen. Die Abschnittsprüfung
zeigt jeden übernommenen Wert, Berichtspfad, Quellausführung und Zielfeld vor
**Diesen Abschnitt bestätigen und ausführen**.

Nur die getrennte Bestätigung führt aus. Gleichzeitiges Schließen und Bestätigen
ist in der UI gesperrt. Profil-, Sprach- und Gesprächswechsel verwerfen verspätete
Vorschläge; eine frische Abfrage gleicht Aktionen ab, die erst nach Rückkehr zum
selben Profil enden. Reset entfernt alte sichtbare Freigabeknöpfe sofort.
Stoppt ein Abschnitt mit unklarer Wirkung, zeigt die Ansicht trotzdem bestätigte,
gescheiterte und unversuchte Schritte und warnt vor unvollständiger Ergebnisablage.

**Noch offen:** ein sinnvolles paketiertes v2-Rezept.
API-/Strands-/Sitzungs-CLI-Integrationstests verwenden synthetische Fachadapter; GUI-Verhaltenstests
führen das echte Skript mit wirkungslosen DOM-/Netzwerk-Testumgebungen aus.
Beides belegt weder Layout-/Tastaturabnahme im Browser noch die Auswahlqualität
eines Live-Modells. Läufe lassen sich nach einem Prozessneustart nicht wiederherstellen
oder mit vom Client gelieferten Berichten befüllen. Ein ausgewählter JSON-Wert
allein belegt weder Ausführung noch Herkunft.

## Wo Rezepte liegen

Rezepte werden im Paket ausgeliefert (`folderhome/recipes/*.json`), nicht neben
dem Checkout, damit auch eine installierte FolderHome-Fassung sie besitzt. Der
Loader ist streng: unbekannte Felder, unbekannte Endpunkte und Übergabekanten in
falscher Reihenfolge scheitern fail-closed.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
