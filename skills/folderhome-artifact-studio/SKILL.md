---
name: folderhome-artifact-studio
description: Plane und erstelle FolderHome-Artefakte wie Präsentationen, Tabellen, Dokumente, Designsets, Visitenkarten oder Medien über vorhandene spezialisierte Skills und explizite Qualitätsgates.
---

# FolderHome Artifact Studio

Verwende zuerst den FolderHome-Plan. Er entscheidet nicht kreativ über den
Inhalt, sondern prüft, welcher bestehende Spezialist zuständig und in der
aktuellen Laufzeit nachweisbar verwendbar ist.

```powershell
python -m folderhome artifacts plan `
  --request-file <artifact-request.json> `
  --profiles-dir <profiles-dir> `
  --approve-sensitive-local-read `
  --json
```

## Routing

- `presentation`: Nutze den `pptx`-Skill; bei wissenschaftlichem Inhalt
  zusätzlich `academic-pptx`. Erzeuge keine PPTX, wenn die im Plan genannten
  Inhalts-, Render- oder Sichtprüfungen nicht erfüllbar sind.
- `spreadsheet`: Nutze den `Spreadsheets`-Skill ausschließlich mit dessen
  bereitgestelltem Workspace-Dependency-Loader. Prüfe Formeln und jede
  sichtbare Tabelle vor der Ausgabe.
- `document`: Nutze den `documents`-Skill und dessen strukturelle sowie
  visuelle DOCX-Abnahme. report-forge darf erst nach einheitlicher
  Distribution-/Runtime-Identität als Provider dienen.
- `odt`: Stoppe, solange der Plan keinen revisionsgebundenen ODT-Renderer mit
  visueller Abnahme ausweist.
- `design_set` und `business_card`: Nutze `artifacts design-preview`, prüfe
  Inhalt und Kontrast, dann `artifacts design-render` mit getrenntem
  Output-Gate. Betrachte jede SVG-Karte vor einer Druckfreigabe erneut.
- `media`: Nutze ai-media-editor nur an der im Plan genannten sauberen
  Revision. Reale Medien brauchen Lesefreigabe; eine Schnittstrategie muss
  vor dem Rendern bestätigt werden.

Ein Status `blocked` darf nicht durch eine ähnliche Bibliothek, einen
System-Python oder eine ungeprüfte Konvertierung umgangen werden. Ein Status
`review_required` erlaubt Vorbereitung, aber keine Fertigbehauptung ohne die
genannten Prüfungen.

Versand, Upload, Druck, Veröffentlichung und Remote-Verarbeitung sind eigene
Aktionen und werden aus einem Artefaktplan niemals automatisch abgeleitet.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
