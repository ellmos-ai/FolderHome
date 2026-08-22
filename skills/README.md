# FolderHome Skills

Hier entstehen neue, agentisch steuerbare Skill-Pakete. Die geplante Familie
umfasst unter anderem Dokumentenpflege, Ordnerberichte, Themendossiers,
FindCall sowie administrative Haushalts-, Gesundheits- und Finanzabläufe.

Der Phase-18-FindCall-Service liefert bereits den gekapselten Kern für einen
späteren agentischen Skill, bleibt im Wettbewerbsstand aber eine strikt lokale
Fixture-Simulation ohne Telefon- oder Netzwerkzugriff.

Der Phase-21-Medikamentenservice liefert außerdem einen wiederverwendbaren,
evidenzgebundenen Kern für bereitgestellte Zeitpläne, Tagesansichten und
explizit bestätigte Einnahmen. Er ist bewusst kein Diagnose-, Verordnungs-,
Dosierungs- oder Erinnerungsagent.

Der Phase-22-Gesundheitsdossier-Kern bündelt lokale Dokumente extraktiv und
evidenzgebunden. Er zeigt direkte Konflikte, Quellenabstände und Fehlerstatus,
bleibt aber bewusst ohne Diagnose, Therapieentscheidung, Remote-LLM oder
Vollständigkeitsversprechen.

Der Phase-23-Vertragscockpit-Kern kombiniert vorhandene Dokument-, Kontakt-,
Kosten-, Termin- und Abdeckungsansichten über einen expliziten Join-Vertrag.
Er ist eine read-only Orchestrierung und führt weder Archivierung noch
Kommunikations-, Kalender- oder Finanzaktionen aus.

Der Phase-24-Korrespondenzkern kapselt kontrollierte Vorlagen, explizite
Designvererbung und deterministische Markdown-/TXT-Ausgabe. Er kann später
von agentischen Brief- oder Behördenworkflows verwendet werden, ohne
Versand, Rechtsentscheidung oder Office-Rendering still mitzuliefern.

Der Phase-25-Skill `folderhome-artifact-studio` routet Präsentationen,
Tabellen, Dokumente und Medien zu vorhandenen Spezialisten und respektiert
deren eigene Runtime- und Sichtprüfungen. FolderHome selbst erzeugt nur den
neuen gekapselten Designset-/SVG-Kern; blockierte Provider werden nicht
ersetzt oder als fertig ausgegeben.

Der Phase-26-Skill `folderhome-mail-assistant` trennt read-only Postfachabruf,
lokale Anhangsausgabe, Postfachmutationen und Versand. Er verlangt eine
explizite Kontakt-/Korrespondenzbindung und ein einmaliges Versandledger; der
abgenommene Gateway ist rein synthetisch und sendet keine E-Mail.

Der Phase-27-Skill `folderhome-calendar-connectors` baut ausschließlich auf
dem vorhandenen Kalenderhandoff auf. Er unterscheidet UpToday-ICS,
Routinika-Bundle, Google-Skill und einen synthetischen No-Network-Provider,
verlangt exakte Kalender- und Operationsbindungen und behauptet keinen
Live-Kalendereintrag.

Der Phase-28-Skill `folderhome-personal-notes` führt Menschen mit getrennten
Fragen und Vorschlägen durch persönliche Notizen. Nur der exakt bestätigte
Inhalt wird append-only im gepinnten `llm-note`-Store ergänzt; Remote-LLM,
externe Synchronisierung, Überschreiben und Löschen bleiben ausgeschlossen.

Der Phase-29-Skill `folderhome-tax-workpaper` übernimmt ausschließlich
menschlich eingeordnete, kataloggebundene Belege in den gepinnten lokalen
Steueragenten. Er erzeugt nach eigener Freigabe private Arbeitsunterlagen,
aber keine Steuerberatung, amtliche Erklärung oder Portalübermittlung.

Der Phase-30-Skill `folderhome-daily-briefing` bündelt lokale Wetter- und
Nachrichtensnapshots zu einem quellenbewussten HTML-Brief. Rendern und
Desktopkopie bleiben getrennt freigegeben; Live-Netzwerk und Scheduler werden
nicht still vorgetäuscht.

Der Phase-31-Skill `folderhome-official-notices` erfasst ausdrücklich
beschriftete Bescheidangaben mit Zeilen- und Hashbeleg. Relative Fristtexte
werden nicht in gesetzliche Daten umgerechnet; Rechtsprüfung, Antwort und
Außenwirkung bleiben ausgeschlossen.

Der Phase-32-Skill `folderhome-administrative-drafts` verbindet diese Evidenz
mit dem vorhandenen Korrespondenzstudio. Widerspruchs-, Antwort- und
Antragsentwürfe bleiben sichtbar ungeprüft, benötigen eine separate
Inhaltsfreigabe und besitzen keinen Versandpfad.

Der Phase-33-Skill `folderhome-benefit-screening` ordnet wenige lokale
Nutzerangaben grob amtlichen Vorchecks zu. Er blockiert veraltete Quellen,
weist Kataloglücken aus und behauptet weder Leistungsberechtigung noch Höhe,
Vollständigkeit oder Antrag.

Der Phase-34-Skill `folderhome-legal-change-monitor` vergleicht datierte,
hashgebundene Rechtsquellensnapshots und ordnet Änderungen ausschließlich
explizit hinterlegten Themen als Prüfkandidaten zu. Entwürfe, Verkündung,
Rechtswirkung, Betroffenheit, Fristen und Benachrichtigung bleiben getrennt.

Der Phase-36-Skill `folderhome-strands-agent` stellt den verpflichtenden
Strands-Agents-Loop bereit. Er routet ausschließlich auf profilgebundene
read-only Dokumentensuche und Themendossiers, begrenzt Turns, Tools und
Ergebnisse und trennt den reproduzierbaren No-Network-Fixture-Lauf von einem
explizit freizugebenden Bedrock-Lauf.
