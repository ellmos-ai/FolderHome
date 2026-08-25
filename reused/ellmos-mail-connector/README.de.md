# ellmos mail-connector — Muster, kein Code

[English](./README.md) | **Deutsch**

FolderHome importiert, kopiert und pinnt das ellmos-Modul `mail-connector`
nicht. Der reine Entwurfstransport in `folderhome/capabilities/mail_draft` ist
eigener FolderHome-Code für einen Fall, den das Quellmodul gar nicht abdeckt: Es
besitzt kein Draft-APPEND.

Drei Ansätze wurden als Entwurfsmuster übernommen und hier neu umgesetzt:

| Muster | Quelldatei | Warum es hier zählt |
|---|---|---|
| Verbinden und Schließen als Context-Manager | `mail_connector/imap_client.py` | eine Stelle, die den Sitzungsschluss garantiert, auch im Fehlerfall |
| Modified-UTF-7-Ordnernamen (RFC 3501) | `mail_connector/imap_client.py` | ein deutscher Entwurfsordner heißt am Bildschirm `Entwürfe`, auf der Leitung aber `Entw&APw-rfe`; ohne die Kodierung scheitert die Ablage in jedem Postfach, das einen solchen Ordner hat |
| Zwei Passwortquellen, Wert nie geloggt | `mail_connector/secrets.py` | Schlüsselbund des Betriebssystems oder lokale Datei, je nachdem was das Konto deklariert |

`tests/test_imap_safety.py` jenes Moduls war das Vorbild für die Fake-IMAP-Tests
in `tests/test_mail_draft.py`, die prüfen, was wirklich auf der Leitung landet,
ohne einen Socket zu öffnen.

Das Modul steht unter MIT und stammt vom selben Autor. Da nichts importiert
wird, gibt es keine gepinnte Revision zu führen und keinen Checkout, der sich
unter diesem Repository wegbewegen kann.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
