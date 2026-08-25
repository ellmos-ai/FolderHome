# ellmos mail-connector — patterns, not code

**English** | [Deutsch](./README.de.md)

FolderHome does not import, vendor or pin the ellmos `mail-connector` module. The
draft-only IMAP transport in `folderhome/capabilities/mail_draft` is FolderHome's
own code, written for a single append-only case that the source module does not
cover: it has no draft APPEND at all.

Three approaches were reused as design, reimplemented here:

| Pattern | Source file | Why it matters here |
|---|---|---|
| Connect and close as a context manager | `mail_connector/imap_client.py` | one place that guarantees the session is closed, including on failure |
| Modified UTF-7 mailbox names (RFC 3501) | `mail_connector/imap_client.py` | a German drafts folder is `Entwürfe` on screen but `Entw&APw-rfe` on the wire; without the encoding an append fails on every mailbox that has one |
| Two credential sources, value never logged | `mail_connector/secrets.py` | the operating system keyring or a local file, whichever the account declares |

`tests/test_imap_safety.py` of that module was the model for the fake-IMAP tests
in `tests/test_mail_draft.py`, which assert what actually reaches the wire
without opening a socket.

The module is MIT-licensed and written by the same author. Because nothing is
imported, there is no pinned revision to record and no checkout that can drift
out from under this repository.

---
