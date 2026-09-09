# Optionale Provider-Checkouts

[English](./provider-checkouts.md) | **Deutsch**

Die synthetischen Wettbewerbsdemos benötigen keine privaten Provider-Repositories.
Die echte Dokumentextraktion verwendet die optionale `doc-services`-Bridge.
Ihr Manifest legt einen exakten Commit fest; Revision und sauberer Arbeitsstand
sind verpflichtend. Ein neuerer Checkout ist kein Ersatz für diesen Stand.

## Festgelegte Version isolieren

Wenn du bereits berechtigten Zugriff auf den Provider-Quellcode hast, lasse seine
Arbeitskopie unverändert und erstelle einen separaten Checkout in FolderHome.
Aus dem FolderHome-Repository, in PowerShell:

```powershell
$providerSource = 'C:\path\to\your\doc-services'
git clone --no-hardlinks --no-checkout $providerSource .providers/doc-services
git -C .providers/doc-services switch --detach e5f46f53d0a19c7d49229bcf049c1b5f0045f0c2
git -C .providers/doc-services status --porcelain
```

Bei einem Fehler abbrechen. Der letzte Befehl darf nichts ausgeben. Kein
bestehendes Ziel wiederverwenden und keine fremde Arbeitskopie zurücksetzen.

FolderHome bevorzugt automatisch `.providers/doc-services`, sofern vorhanden.
Sonst gilt weiterhin der benachbarte Provider-Ordner. Dasselbe gilt für
`.providers/file-collect-sort-action` und `.providers/law-checker`. Öffentliche
Quellen und exakte Revisionen stehen in
[`manifests/components/`](../manifests/components/); dafür dieselben Clone-/Detach-
Schritte mit passendem Namen und passender Revision verwenden. Ein ungültiger isolierter
Checkout scheitert an der normalen Prüfung; es gibt keinen stillen Rückfall auf
eine andere Quelle. Ein explizites `--doc-services-root` hat weiterhin Vorrang.

`.providers/` wird von Git ignoriert. Das ist lokaler Abhängigkeitsspeicher,
**keine Freigabe zur Weitergabe privaten Quellcodes**. Ein `local://`-Manifest
ist keine öffentliche Downloadadresse. Den Ordner nicht in Releases oder
Wettbewerbsuploads aufnehmen.

## Grenzen der Prüfung

```powershell
.venv\Scripts\python.exe -m pytest tests/test_doc_services_bridge.py -q
```

Zwei erfolgreiche Bridge-Tests belegen echte lokale Extraktion und die
Datenschutzprüfung dieses Checkouts. Provider-abhängige Tests benötigen die
passenden Quellcode-Checkouts; einige werden bei fehlendem Provider ausdrücklich
übersprungen. Vorhandene falsche oder geänderte Provider führen zu Fehlern.
Ein übersprungener Integrationstest belegt nicht, dass die entsprechende
Funktion mit echten Daten arbeitet.
