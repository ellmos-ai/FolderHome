# Manifeste

[English](./README.md) | **Deutsch**

`components/` ist die aktuelle Laufzeitautorität für wiederverwendete
Plugins. Jedes Manifest muss `folderhome.component-manifest.v1` erfüllen,
seine Herkunft auf eine exakte Git-Revision pinnen und derzeit
`default_mode = "dry-run"` sowie `live_enabled = false` setzen.

FCSA und die weiteren Runtime-Bridges prüfen den lokalen Provider-Checkout
zusätzlich zur Laufzeit gegen diesen Pin. Das Phase-34-Manifest bindet
`law-checker` nur für read-only Registry- und Quellenmetadaten; es deklariert
keine automatische Rechtsprüf-API. Spätere Stack-Manifeste werden ergänzt,
sobald weitere Bridge-Verträge real implementiert und separat freigegeben
sind.
