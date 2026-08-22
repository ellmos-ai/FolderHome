# Workflow — Gesundheitsdossier

## Zweck

Aus einem ausdrücklich gewählten lokalen Ordner ein evidenzgebundenes
Gesundheitsdossier als Markdown und JSON erstellen. Der Workflow ist
extraktiv: Er ordnet dokumentierte Aussagen zeitlich ein, weist aber keine
Diagnose, Therapieentscheidung oder medizinische Vollständigkeit aus.

## Lokaler Lauf

```powershell
$env:PYTHONPATH = "src"
python -m folderhome health dossier `
  --source-dir examples\health `
  --profiles-dir examples\profiles `
  --profile lukas `
  --as-of 2026-08-22 `
  --gap-threshold-days 90 `
  --approve-sensitive-local-read `
  --output-markdown .local-demo\Gesundheitsdossier.md `
  --output-json .local-demo\Gesundheitsdossier.json `
  --json
```

Die beiden Ausgabedateien müssen neu sein und außerhalb des analysierten
Quellordners liegen. Vorhandene Dateien werden nicht überschrieben.

## Eingabekonvention

Für die erste Version sind folgende Labels besonders aussagekräftig:

- `Dokumenttyp`, `Dokumentdatum`, `Fachbereich`
- `Befund`, `Ergebnis`, `Medikament`, `Termin`, `Offene Frage`
- `Dokumentierte Angabe: Feld = Wert`

Andere lesbare Dokumente können bis zu drei reine Quellenauszüge liefern.
Ohne eindeutiges Dokumentdatum bleibt eine Quelle sichtbar, wird aber nicht in
die Zeitlinie einsortiert. Direkte Konflikte werden nur bei gleich bezeichneten
`Dokumentierte Angabe`-Feldern erkannt.

## Sicherheitsgrenzen

- Das Sensitivitäts-Gate wird vor der ersten Extraktion geprüft.
- ROT klassifizierte Inhalte werden nur lokal übernommen, wenn der
  Providerbefund ausschließlich `Gesundheitsdaten` nennt.
- Weitere rote Befunde wie IBAN, API-Token oder Zugangsdaten bleiben blockiert.
- Nicht lesbare, blockierte, undatierte und zukünftige Quellen bleiben im
  Bericht sichtbar.
- Zeitlücken bedeuten nur, dass zwischen zwei datierten Quellen ein Abstand
  liegt; sie beweisen keine Versorgungslücke.
- Es gibt keinen Netzwerkzugriff, keinen LLM-Aufruf und keine automatische
  Kalender-, Medikamenten- oder Kontaktaktion.
- `report-forge` wird wegen seiner uneinheitlichen Provideridentität nicht
  aufgerufen; Markdown und JSON sind die kanonischen Ausgaben dieser Phase.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
