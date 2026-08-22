# Reused components

Dieser Bereich enthält keine kopierten Quellen. Runtime-Provider verweisen auf
ein separat versioniertes Repository und ihr kanonisches Manifest unter
`manifests/components/`. Reine Designreferenzen ohne Runtime-Anbindung nennen
stattdessen Checkout, Revision, Lizenz, Prüfstand und die bewusst nicht
übernommenen Eigenschaften direkt auf ihrer Unterseite.

Phase 27 dokumentiert UpToday, Routinika und den Google-Calendar-Skill unter
[`calendar-providers/`](calendar-providers/) ohne kopierten Providercode.

Phase 28 dokumentiert den unveränderten lokalen Notizspeicher unter
[`llm-note/`](llm-note/). FolderHome ergänzt Führung und Freigabe als neue
Kapsel und schreibt ausschließlich über die öffentliche Provider-API.

Phase 29 dokumentiert den unveränderten lokalen Belegprovider unter
[`steuer-assistent/`](steuer-assistent/). FolderHome ergänzt Dokument-,
Profil-, Approval- und Hashbindungen, ohne Steuerberatung oder einen
Portalpfad hinzuzufügen.

Phase 30 dokumentiert BACHs Wetter-, Newspaper- und Daily-Agent-Bestand unter
[`bach-daily-briefing/`](bach-daily-briefing/) ausschließlich als
Designreferenz. Der fremd veränderte Monolith wird nicht geladen und sein
Quellcode nicht kopiert.

Phase 31 dokumentiert den vorhandenen `law-checker` unter
[`law-checker/`](law-checker/) zunächst als Methodenreferenz. Phase 34 ergänzt
einen getrennten sauberen Checkout als gepinnten read-only Registry- und
Quellenprovider. Der frühere fremd veränderte Checkout bleibt unangetastet;
eine automatische Rechtsprüf-API wird nicht behauptet.

Phase 33 dokumentiert unter [`benefit-routing/`](benefit-routing/) drei
amtliche, manuell zu öffnende Leistungsfinder-Handoffs. Kein Portalcode wird
kopiert, kein Profil übertragen und der pädagogische `foerderplaner` nicht
als Sozialleistungsmodul fehlverwendet.
