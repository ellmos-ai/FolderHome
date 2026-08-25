# Fähigkeitsrezepte — eine Bestätigung für eine ganze Geschichte

[English](./capability-recipes.md) | **Deutsch**

> **Last verified:** 2026-08-25

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

## Eines ausführen

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

Ein Rezeptplan ist deterministisch; eine erneute Vorbereitung ergibt dieselbe
Plan-ID. Genau das erlaubt einer zustandslosen Kommandozeile, einen zuvor
ausgegebenen Plan zu bestätigen, ohne eine Sitzung offen zu halten.

## Wenn ein Schritt scheitert

Die Kette hält beim ersten Fehler an. Der Bericht wird zurückgegeben statt
geworfen, denn wer nur eine Ausnahme sähe, wüsste nicht, was bereits gewirkt hat.
Er benennt drei Gruppen ausdrücklich:

- `executed_step_refs` — diese liefen, ihre Wirkung bleibt bestehen
- `failed_step_refs` — genau ein Schritt, mit der Meldung des Adapters
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
