# Fähigkeitsrezepte — eine Bestätigung für eine ganze Geschichte

[English](./capability-recipes.md) | **Deutsch**

> **Last verified:** 2026-09-09

## Warum es Rezepte gibt

Eine echte Alltagsaufgabe ist selten ein einzelner Endpunkt. Nach einem
Autounfall braucht man den zuständigen Kontakt, ein Schadensschreiben, dieses
Schreiben im eigenen Entwurfsordner und den Folgetermin im Kalender. Vor den
Rezepten konnte FolderHome alle vier Dinge — aber man musste viermal fragen und
viermal bestätigen, und nichts stellte sicher, dass Schritt drei dasselbe
Schreiben verwendet wie Schritt zwei.

Ein Rezept ist diese Geschichte, aufgeschrieben. Der Master löst sie in **einen**
Plan mit mehreren geordneten Schritten auf, und die ganze Kette wird einmal
bestätigt.

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

**Daten fließen nur als logische Ressourcen-IDs.** Eine Übergabekante
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

Ein Rezeptplan ist deterministisch: Gleiche Eingaben und gleicher Fachzustand
ergeben mit demselben Code dieselbe Plan-ID. Genau das erlaubt einer zustandslosen
Kommandozeile, einen zuvor
ausgegebenen Plan zu bestätigen, ohne eine Sitzung offen zu halten.

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

## Bekannte Grenze dieser Fassung

Übergabekanten binden Ressourcen, keine Werte. Ein Rezept kann noch keinen Wert
aus dem Bericht eines Schrittes in die Anfrage des nächsten setzen — das würde
verlangen, Anfragen erst während der Ausführung aufzulösen, und würde den einen
Hash über die Kette brechen. Die Kanten sind ausdrücklich deklariert, damit eine
spätere Fassung Wertersetzung in deklarierte Slots ergänzen kann, ohne das
Rezeptformat zu ändern.

## Wo Rezepte liegen

Rezepte werden im Paket ausgeliefert (`folderhome/recipes/*.json`), nicht neben
dem Checkout, damit auch eine installierte FolderHome-Fassung sie besitzt. Der
Loader ist streng: unbekannte Felder, unbekannte Endpunkte und Übergabekanten in
falscher Reihenfolge scheitern fail-closed.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
