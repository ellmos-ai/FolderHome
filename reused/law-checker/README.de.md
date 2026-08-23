# law-checker — gepinnter Quellen-Provider und Methodengrenze

[English](./README.md) | **Deutsch**

Der frühere synchronisierte Checkout bleibt wegen Rückstand und fremden
Änderungen read-only. Phase 34 verwendet stattdessen einen getrennten sauberen
Checkout von `https://github.com/ellmos-ai/law-checker.git`, gepinnt auf Revision
`06fb8d57ff90638cc50f5e33c50dbba455ac6f1b`. Die vier Provider-Tests
bestanden am 2026-08-22.

Der zugehörige Pointer im zentralen Repository
`https://github.com/ellmos-ai/skills.git` wurde auf Revision
`0317f32310eed11d21f603cb6f22a689485af226` geprüft. Auch dieser lokale
Checkout ist einen Commit hinter Upstream. Der Skill beschreibt den
`law-checker` als erste Orientierung, nicht als Anwalt oder verlässlichen
Fristenkalender, und verlangt für Normen amtliche Quellen.

Die Risikoregeln des Bestands stützen die Produktgrenze von Phase 31:
Eingehende rechtliche Schreiben und Fristen sind früh zu prüfen, das Original
bleibt erhalten und unklare Fristen werden eskaliert. Das lokale
Gesetzesregister deckt derzeit jedoch kein vollständiges allgemeines
Sozialverwaltungs- und Sozialgerichtsrecht für beliebige Bescheidarten ab.

Phase 34 bindet nur Identität, Registry und Quellenmetadaten über
`bridges.law_checker` an. Der Provider besitzt keine stabile Python-API für
eine automatische Rechtsprüfung; FolderHome behauptet keine solche API und
startet weder Fetcher noch Agentenworkflow. Der neue gekapselte
Rechtsänderungsmonitor verarbeitet ausschließlich vorher bereitgestellte
Snapshots und erzeugt unverbindliche Prüfkandidaten. Rechtswirkung,
Betroffenheit, Fristen und Benachrichtigung bleiben getrennt.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
