# BACH Weather, Newspaper and Daily Agent — Design Reference

**English** | [Deutsch](./README.de.md)

The local BACH checkout was verified at commit
`9ff3df23d6e8e27b9c9eaad71f2430923224d4d9`, repository
`https://github.com/ellmos-ai/bach.git`, license MIT. The relevant weather,
newspaper, and daily‑agent files are unchanged relative to Git; the
overall checkout, however, contains foreign changes and is not loaded as
a FolderHome runtime. The focused newspaper tests were 11/11
green.

BACH embodies the product idea of a weather segment, a grouped
HTML/PDF newspaper, and a desktop delivery. FolderHome does not copy the code:
the BACH inventory is tied to a central database, implicit system time,
a hard‑coded location, direct network access, Edge, and immediate
desktop/Telegram side‑effects.

Newly encapsulated FolderHome contracts instead use local,
hash‑bound snapshots, explicit timestamps, and separate render and
desktop releases. Live network and scheduler remain visibly blocked.

---
