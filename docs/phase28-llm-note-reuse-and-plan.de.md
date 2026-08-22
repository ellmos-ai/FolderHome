# Phase 28: llm-note-Wiederverwendung und persönlicher Notizdienst

[English](./phase28-llm-note-reuse-and-plan.md) | **Deutsch**

**Stand:** 2026-08-22  
**Zweck:** Den vorhandenen Notizspeicher wiederverwenden und die fehlende
menschlich kontrollierte Führung gekapselt ergänzen.

## Verifizierter Bestand

Der lokale Checkout `C:\_Local_DEV\repos\llm-note` wurde read-only geprüft:

| Merkmal | Befund |
|---|---|
| Repository | `https://github.com/doc-bricks/llm-note.git` |
| Revision | `b5fe59fc155ded9603566aa0fb920a53181a2426` |
| Paketversion | `1.0.3` |
| Lizenz | MIT |
| Checkout | sauber, exakt auf der gepinnten Revision |
| Providertests | 19/19 grün |
| Laufzeit | Python-Standardbibliothek, lokale SQLite-/Textablage, kein Netzwerk |

Die frühere FolderHome-Tabelle nannte noch `ellmos-ai/llm-note`. Der reale
Checkout, sein Manifest und seine README weisen inzwischen `doc-bricks` als
Repository aus. Phase 28 korrigiert deshalb die Provenienz, ohne den
Providerstand zu verändern.

## Was wiederverwendet wird

FolderHome nutzt `llm_note.NoteStore.write()` als einzige schreibende
Notizablage. Jede bestätigte FolderHome-Fassung wird als neuer
`folderhome_note_version`-Eintrag gespeichert. Der Providerquellcode wird
weder kopiert noch verändert.

Der öffentliche Provider-Readpfad initialisiert bei einem fehlenden Store eine
Datenbank und führt Schema-DDL aus. Ein FolderHome-Plan muss jedoch read-only
bleiben. Die Bridge liest bestehende FolderHome-Versionen deshalb über einen
eng begrenzten SQLite-Adapter mit `mode=ro&immutable=1`, prüft das erwartete
`note_entries`-Schema und verwendet die öffentliche Provider-API nur beim
freigegebenen Anhängen. Das entspricht dem bereits bewährten
KnowledgeDigest-Seam: Write-on-read wird vermieden, ohne einen zweiten
Notizspeicher zu bauen.

## Fehlende Funktionen des Bestands

`llm-note` ist ein kleiner Agenten- und Menschennotizspeicher. Es modelliert
noch nicht:

- Profil, Bereich und logisches Notizbuch als FolderHome-Kontext,
- Fragen und Vorschläge getrennt vom bestätigten Inhalt,
- Plan-, Inhalts-, State- und Approval-Bindung,
- eine explizite Dokument- oder Kalenderreferenz,
- Bearbeitung und Rückkehr als nachvollziehbare Versionsfolge,
- die Betriebssystemkonto-Grenze des Familienprofils.

Diese Lücke schließt neuer, wiederverwendbarer Code in
`contracts.personal_notes`, `application.personal_notes`,
`bridges.llm_note` und `capabilities.personal_note_guide`.

## Verbindlicher Ablauf

```text
menschliche Anfrage
  → strikte Schema- und Profilprüfung
  → gepinnter read-only llm-note-Readback
  → synthetische Fragen und Vorschläge, kein Inhaltsumbau
  → review_required-Plan mit Store- und Inhaltshash
  → menschliche Freigabe exakt dieses Inhalts
  → llm-note.NoteStore.write() ergänzt genau eine Version
  → read-only Readback und Ausführungsbericht
```

`create` beginnt bei Revision 1. `edit` hängt eine neue Revision an. `revert`
kopiert den Inhalt einer früheren Revision in eine neue Revision; es löscht
oder überschreibt keine Fassung. Ein wiederholter Plan, ein veralteter
Storehash oder ein abweichender Inhaltshash blockiert vor dem Write.

## Autorschaft und LLM-Grenze

Der Plan speichert `author_kind=human`. Der Guide liefert ausschließlich
`questions` und `suggestions`; `confirmed_content_changed` muss `false` sein.
Die Phase-28-Abnahme verwendet einen deterministischen No-Network-Guide. Ein
späterer echter LLM-Provider benötigt eine eigene Offenlegung der zu
übertragenden Daten, eine gesonderte Nutzerfreigabe und einen nachgewiesenen
Providervertrag. Remote-Aufrufe sind in Phase 28 auch mit einem allgemeinen
Schalter nicht ausführbar.

## Referenzen und Sicherheitsgrenze

Dokumente und Termine werden niemals automatisch gesucht oder verknüpft. Eine
Referenz muss in der Anfrage mit Art, Ziel-ID, Bezeichnung und bei Dokumenten
optionalem SHA-256 stehen. FolderHome prüft nur die Form; die Referenz ist
keine Behauptung, dass das Ziel noch existiert oder fachlich vollständig ist.

Profile wie Lukas, Hanna oder Simon sind Ansichts- und Organisationsmerkmale
innerhalb desselben Betriebssystemkontos. Sie sind keine Zugriffsbarriere.
Phase 28 führt weder Netzwerksynchronisierung noch Kontenfreigabe ein.

## Abnahme

Der synthetische Ende-zu-Ende-Fall führt Providerinventur, Guide-Plan,
inhaltshashgebundene Freigabe, lokale Ablage und Historien-Readback aus. Vor
der Freigabe existiert kein State-Ordner. Nach der Freigabe existiert genau
eine neue Providerrevision; `network_invoked` und `external_sync_invoked`
bleiben `false`.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
